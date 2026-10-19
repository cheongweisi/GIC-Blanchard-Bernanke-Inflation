"""Phase 3: weighted estimation, 2026 dataset construction, pseudo-out-of-sample design, selection rule, IRF statistics."""
import numpy as np
import pandas as pd
import pytest

from bb_inflation.config import PHASE3_PULL
from bb_inflation.data import phase3_data as P
from bb_inflation.estimation.inference import hac_cov, with_hac
from bb_inflation.estimation.rls import estimate
from bb_inflation.estimation.wls import effective_sample_size, estimate_weighted, exp_weights
from bb_inflation.extension import coefs as C
from bb_inflation.extension import irfs as I
from bb_inflation.extension import pseudo_oos as O
from bb_inflation.extension.models import ModelSpec, fit, specs_for_end, standard_models
from bb_inflation.simulation.model import SimModel


@pytest.fixture(scope="module")
def p3():
    return P.build(PHASE3_PULL)


# ---------------------------------------------------------------- weighted estimation
def test_unit_weights_reproduce_rls(p3):
    spec = specs_for_end("gscpi_ma2", "2023Q2")["gcpi"]
    a, b = estimate(spec, p3.data, "1990Q1", "2023Q2"), estimate_weighted(spec, p3.data, "1990Q1", "2023Q2", None)
    np.testing.assert_allclose(a.coef.values, b.coef.values, atol=1e-10)
    np.testing.assert_allclose(a.cov.values, b.cov.values, atol=1e-10)


def test_exponential_weights_halve_every_half_life():
    idx = pd.period_range("2000Q1", "2020Q4", freq="Q")
    w = exp_weights(idx, pd.Period("2020Q4", "Q"), 20)
    assert w[-1] / w[-21] == pytest.approx(2.0, rel=1e-9)               # 20 quarters older = half the weight
    assert exp_weights(idx, pd.Period("2020Q4", "Q"), None).tolist() == [1.0] * len(idx)


def test_weighted_estimates_respect_restrictions_and_hac(p3):
    r = fit(standard_models(str(p3.last_complete))["C10"], p3.data, str(p3.last_complete))
    for eq, res in r.items():
        assert res.weights is not None and res.weights.mean() == pytest.approx(1.0)
        assert effective_sample_size(res.weights) < res.nobs
        assert res.coef[res.spec.restriction_names()].sum() == pytest.approx(1.0, abs=1e-9)
        V = hac_cov(res, p3.data)
        assert np.allclose(V, V.T) and np.linalg.eigvalsh(V.values).min() > -1e-9
        assert with_hac(res, p3.data).cov.shape == res.cov.shape


# ---------------------------------------------------------------- dataset
def test_last_complete_quarter_and_partial_quarter_not_used(p3):
    assert str(p3.last_complete) == "2026Q2"
    assert p3.data.index[-1] == p3.last_complete and pd.Period("2026Q3", "Q") not in p3.data.index
    assert any("2026Q3 is partial" in n for n in p3.notes)


def test_only_known_hole_is_vu_2025q4(p3):
    cols = ["gcpi", "gw", "grpe", "grpf", "vu", "cf1", "cf10", "shortage", "shortagema2", "magpty", "diffcpicf"]
    x = p3.data.loc["1990Q1":, cols]
    assert x.isna().sum()[x.isna().sum() > 0].to_dict() == {"vu": 1}
    assert str(x.index[x.vu.isna()][0]) == "2025Q4"
    assert p3.flags["vu_bridged"].sum() == 1
    assert p3.data_bridged.loc["2025Q4", "vu"] == pytest.approx(0.8765, abs=1e-3)
    assert np.isnan(p3.data.loc["2025Q4", "vu"])                         # estimation data never contain the bridge


def test_wage_equation_loses_only_quarters_needing_missing_vu(p3):
    B = fit(standard_models("2026Q2")["B"], p3.data, "2026Q2")
    assert str(B["gw"].sample[1]) == "2025Q4" and B["gw"].nobs == 144
    for eq in ("gcpi", "cf1", "cf10"):
        assert str(B[eq].sample[1]) == "2026Q2" and B[eq].nobs == 146


def test_eci_splice_baseline_and_macrobond_sensitivity():
    base, alt = P.build(PHASE3_PULL), P.build(PHASE3_PULL, eci_history="macrobond")
    g0, g1 = base.data["gw"], alt.data["gw"]
    assert (g0.loc["2001Q2":] - g1.loc["2001Q2":]).abs().max() < 1e-9           # same data after the splice
    assert (g0.loc["1990Q1":"2000Q4"] - g1.loc["1990Q1":"2000Q4"]).abs().mean() > 0.3


def test_model_a5_reproduces_phase2_ladder_case_on_identical_data(p3):
    """Phase 1-2 ladder case L6 used the earlier (identical) pull; A5 must reproduce its price-equation sums."""
    from bb_inflation.data.authors_data import load_raw
    from bb_inflation.validation import ladder
    A5 = fit(standard_models("2026Q2")["A5"], p3.data, "2026Q2")
    L6 = ladder.run_case(load_raw(), [c for c in ladder.cases() if c.name.startswith("L6")][0])
    assert A5["gcpi"].summary().loc["gw", "sum"] == pytest.approx(L6["sum gcpi:gw"], abs=1e-6)
    assert A5["gcpi"].summary().loc["shortage", "sum"] == pytest.approx(L6["sum gcpi:shortage"], abs=1e-6)


# ---------------------------------------------------------------- pseudo-OOS design
def test_forecasts_at_an_origin_ignore_later_data(p3):
    origin = pd.Period("2015Q4", "Q")
    d, db = p3.data.copy(), p3.data_bridged.copy()
    rng = np.random.default_rng(1)
    later = d.index > origin
    d2, db2 = d.copy(), db.copy()
    for c in ["gw", "gcpi", "cf1", "cf10", "diffcpicf", "grpe", "grpf", "vu", "shortage", "magpty", "shortagema2", "shortagema4"]:
        noise = rng.normal(0, 3, later.sum())
        d2.loc[later, c] = d.loc[later, c] + noise
        db2.loc[later, c] = db.loc[later, c] + noise
    ms = ModelSpec("U", "u")
    r1, r2 = O._fit_origin(ms, d, origin), O._fit_origin(ms, d2, origin)
    m1, m2 = SimModel.from_results(r1), SimModel.from_results(r2)
    for eq in r1:
        np.testing.assert_allclose(r1[eq].coef.values, r2[eq].coef.values, atol=1e-10)
    f1 = O._forecast(m1, d, origin, 8, O.unconditional_exog(db, origin, 8))
    f2 = O._forecast(m2, d2, origin, 8, O.unconditional_exog(db2, origin, 8))
    np.testing.assert_allclose(f1.values, f2.values, atol=1e-9)                   # unconditional: no post-origin info
    c1 = O._forecast(m1, d, origin, 8, O.conditional_exog(db, origin, 8))
    c2 = O._forecast(m1, d2, origin, 8, O.conditional_exog(db, origin, 8))        # same realised exogenous, perturbed endogenous
    np.testing.assert_allclose(c1.values, c2.values, atol=1e-9)                   # conditional uses realised exogenous only
    assert not np.allclose(f1.values, c1.values)


def test_dummy_rule_by_origin():
    assert specs_for_end("gscpi_ma2", "2019Q4")["gw"].dummies == ()
    assert specs_for_end("gscpi_ma2", "2020Q2")["gw"].dummies == ("D2020Q2",)
    assert specs_for_end("gscpi_ma2", "2023Q2")["gw"].dummies == ("D2020Q2", "D2020Q3")


def test_selection_rule_keeps_baseline_unless_clearly_better():
    rows = []
    for m, r in {"U": 1.0, "W5": 1.1, "W10": 0.99, "W15": 0.98}.items():
        for h in ("h1", "h2-4", "h5-8", "h9-12"):
            rows.append({"model": m, "mode": "conditional", "var": "gcpi", "target bucket": "all targets", "horizon": h, "RMSE": r})
    s = pd.DataFrame(rows)
    assert O.select_half_life(s, ["W5", "W10", "W15"], "U")["chosen"] == "U"          # < 3% better: keep baseline
    s.loc[s.model == "W15", "RMSE"] = 0.90
    assert O.select_half_life(s, ["W5", "W10", "W15"], "U")["chosen"] == "W15"


def test_summarize_buckets_and_errors():
    rec = pd.DataFrame({"model": "U", "mode": "conditional", "origin": "2019Q3", "h": [1, 2], "target": ["2019Q4", "2020Q1"],
                        "var": "gcpi", "forecast": [2.0, 3.0], "actual": [1.0, 5.0]})
    s = O.summarize(rec)
    allr = s[(s["target bucket"] == "all targets") & (s.horizon == "h1")].iloc[0]
    assert allr.RMSE == pytest.approx(1.0) and allr.bias == pytest.approx(1.0)
    covid = s[(s["target bucket"] == "2020Q1-2023Q2") & (s.horizon == "h2-4")].iloc[0]
    assert covid.bias == pytest.approx(-2.0)


# ---------------------------------------------------------------- IRF statistics and flags
def test_irf_stats_peak_timing_and_halflife():
    path = np.array([[0, 2, 1.5, 0.9, 0.2, 0.0] + [0] * 22], float)
    st = I.stats_from_paths(path, permanent=False)
    assert st["peak (pp)"][0] == 2 and st["peak quarter"][0] == 1
    assert st["cum 0-4"][0] == pytest.approx(4.6) and st["half-life from peak (q)"][0] == 2   # |0.9|<=1 two quarters after peak


def test_flags_detect_implausible_and_unstable():
    def rows(model, lag, gw, e, f, sh, vu, gwlags, cf):
        data = [("gcpi", "gcpi", lag), ("gcpi", "gw", gw), ("gcpi", "grpe", e), ("gcpi", "grpf", f), ("gcpi", "shortagema2", sh),
                ("gw", "vu", vu), ("gw", "gw", gwlags), ("cf1", "cf10", cf), ("cf1", "gcpi", 0.1), ("cf10", "gcpi", 0.03)]
        return [{"model": model, "eq": eq, "block": b, "sum": v, "se_hac": 0.05} for eq, b, v in data]
    s = pd.DataFrame(rows("A", 0.15, 0.85, 0.08, 0.2, 0.3, 0.7, 0.5, 0.5) + rows("X", -0.02, 1.02, 0.08, 0.2, 0.3, 0.7, 0.5, 0.5))
    f = C.flags(s, "A")
    assert not f[(f.model == "A") & (f.kind == "plausibility")].flag.any()
    bad = f[(f.model == "X") & (f.kind == "plausibility") & f.flag].rule.tolist()
    assert any("lagged-inflation" in r for r in bad) and any("wage pass-through" in r for r in bad)
    assert f[(f.model == "X") & (f.kind != "plausibility") & f.flag].shape[0] >= 2
