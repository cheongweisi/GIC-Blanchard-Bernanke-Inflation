"""Phase 3 supplement: V/U bridge (no look-ahead, one missing month), error attribution, IRF unit conversions, and that
Phase 1-3 outputs are unchanged."""
import hashlib

import numpy as np
import pandas as pd
import pytest

from bb_inflation.config import OUTPUTS, PROJECT_ROOT
from bb_inflation.estimation.rls import estimate
from bb_inflation.extension.models import fit, specs_for_end, standard_models
from bb_inflation.simulation.model import SimModel
from bb_inflation.supplement import context as C
from bb_inflation.supplement import diag_pull as D
from bb_inflation.supplement import irf_intuitive as I
from bb_inflation.supplement import residuals as R
from bb_inflation.supplement import vu_bridge as V
from bb_inflation.validation.specs import VARIANTS


@pytest.fixture(scope="module")
def ctx():
    return C.load("interp")


def test_supplement_pull_integrity_and_no_october_unemployment():
    S = D.load()                                            # raises if any file fails its SHA-256
    assert pd.Timestamp("2025-10-01") not in S["uslama1795"].index          # SA unemployment level: no October 2025 value exists
    assert pd.Timestamp("2025-10-01") in S["uslama1304"].index              # JOLTS openings: observed


def test_bridge_is_interpolation_of_one_month_and_keeps_all_observed_months(ctx):
    S = D.load(ctx.supp_pull)
    J, U = S["uslama1304"], S["uslama1795"]
    t = lambda s: pd.Timestamp(s)                           # noqa: E731
    u_oct = 0.5 * (U[t("2025-09-01")] + U[t("2025-11-01")])
    expected = J[[t("2025-10-01"), t("2025-11-01"), t("2025-12-01")]].mean() / np.mean([u_oct, U[t("2025-11-01")], U[t("2025-12-01")]])
    assert ctx.bridge_value == pytest.approx(expected, rel=1e-12)


def test_bridge_uses_no_information_after_2025_12(ctx):
    assert C.bridge_value("interp", ctx.supp_pull, truncate="2025-12-01") == pytest.approx(ctx.bridge_value, abs=1e-14)
    assert C.bridge_value("claims", ctx.supp_pull, truncate="2025-12-01") == pytest.approx(C.bridge_value("claims", ctx.supp_pull), abs=1e-9)


def test_bridged_data_differs_from_phase3_only_in_vu_2025q4(ctx):
    a, b = ctx.p3.data, ctx.data_star
    diff = (a.fillna(-999) != b.fillna(-999))
    assert list(diff.columns[diff.any()]) == ["vu"]
    assert list(diff.index[diff["vu"]]) == [pd.Period("2025Q4", "Q")]


def test_estimation_through_2025q4_unaffected_by_bridge(ctx):
    spec = specs_for_end("gscpi_ma2", "2025Q4")
    for eq in spec:
        a = estimate(spec[eq], ctx.p3.data, "1990Q1", "2025Q4")
        b = estimate(spec[eq], ctx.data_star, "1990Q1", "2025Q4")
        assert a.nobs == b.nobs
        np.testing.assert_allclose(a.coef.values, b.coef.values, atol=1e-12)


def test_bridged_estimation_adds_wage_equation_observations_only(ctx):
    ms = standard_models(ctx.last)
    a, b = fit(ms["B"], ctx.p3.data, ctx.last), fit(ms["B"], ctx.data_star, ctx.last)
    assert (a["gw"].nobs, b["gw"].nobs) == (144, 146)
    for eq in ("gcpi", "cf1", "cf10"):
        np.testing.assert_allclose(a[eq].coef.values, b[eq].coef.values, atol=1e-12)


def test_backtest_prefers_interpolation_to_dropping_the_month():
    S = D.load()
    J, U = S["uslama1304"], S["uslama1795"]
    CC = V.monthly_mean_weekly(S["uslama3350"])
    s = V.summarize_backtest(V.backtest(J, U, CC)).query("sample != 'all months'").set_index("method")
    assert s.loc["interp", "VU RMSE"] < 0.5 * s.loc["nov_dec", "VU RMSE"]


# ---------------------------------------------------------------- error attribution
def test_equation_shocks_reproduce_actual_path_and_split_additively(ctx):
    ms = standard_models(ctx.last)
    A = fit(ms["A"], ctx.data_star, ctx.last)
    fa = R.one_step(A, ctx.data_star)
    att = R.error_attribution(SimModel.from_results(A), ctx.data_star, fa, "2023Q2", 12)
    np.testing.assert_allclose(att["all four (check)"], att["error (actual - forecast)"], atol=1e-8)
    parts = att[["price-equation residual", "wage-equation residual", "1y-expectations residual", "10y-expectations residual"]].sum(axis=1)
    np.testing.assert_allclose(parts, att["error (actual - forecast)"], atol=1e-8)       # the model is linear in the shocks


# ---------------------------------------------------------------- IRF unit conversions
def test_yoy_and_price_level_conversions():
    a = np.array([[4.0, 4.0, 4.0, 4.0, 0.0, 0.0]])
    np.testing.assert_allclose(I.yoy(a)[0], [1, 2, 3, 4, 3, 2])          # y/y = mean of last four annualised quarterly rates
    np.testing.assert_allclose(I.price_level(a)[0], [1, 2, 3, 4, 4, 4])  # level % = cumulated annualised rates / 4
    pk, k = I._peak(np.array([[0.0, 3.0, -4.0, 0.0]]), sign=np.array([1.0]))
    assert (pk[0], k[0]) == (3.0, 1)                                    # peak taken in the direction of the shock effect


def test_energy_taxonomy_in_levels():
    for kind in I.KINDS:
        g = I.driver_input("Energy", kind, 10.0)
        lvl = np.cumsum(g) / 4.0                                         # relative price level, %
        np.testing.assert_allclose(lvl, 10.0 * I.level_path(kind), atol=1e-12)
    assert I.level_path("temporary")[1:].sum() == 0 and I.level_path("permanent").min() == 1


def test_irf_code_reproduces_phase3_responses(ctx):
    ms = standard_models(ctx.last)
    model = SimModel.from_results(fit(ms["B"], ctx.p3.data, ctx.last))
    derived = VARIANTS["gscpi_ma2"].derived_dict
    old = pd.read_pickle(OUTPUTS / "phase3" / "irfs_paths.pkl")
    sz = pd.read_csv(OUTPUTS / "phase3" / "irfs_shock_sizes.csv", index_col=0).iloc[:, 0]
    for drv, kind, size, label in (("V/U", "permanent", sz["vu"], "V/U permanent"), ("GSCPI", "persistent", sz["shortage"], "GSCPI persistent (rho 0.8)"),
                                   ("Energy", "permanent", sz["grpe"] / 4, "Energy one-off (level)")):
        np.testing.assert_allclose(I.simulate(model, drv, kind, size, derived)[:28], old[("B", label)]["point"], atol=1e-9)


def test_temporary_energy_shock_leaves_no_lasting_price_level_effect(ctx):
    ms = standard_models(ctx.last)
    model = SimModel.from_results(fit(ms["B"], ctx.data_star, ctx.last))
    a = I.simulate(model, "Energy", "temporary", 10.0, VARIANTS["gscpi_ma2"].derived_dict)
    L = I.price_level(a)[0]
    assert L[0] > 0.5 and abs(L[11]) < 0.1 * L[0]


# ---------------------------------------------------------------- Phase 1-3 outputs preserved
def test_phase1_to_3_outputs_unchanged():
    man = OUTPUTS / "phase3_supp" / "phase1-3_outputs_manifest.sha256"
    bad = []
    for line in man.read_text().splitlines():
        h, path = line.split(None, 1)
        p = PROJECT_ROOT / path.strip().lstrip("*")
        if hashlib.sha256(p.read_bytes()).hexdigest() != h:
            bad.append(str(p))
    assert not bad, bad
