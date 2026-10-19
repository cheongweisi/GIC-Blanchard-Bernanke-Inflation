"""Phase 4b: the supplementary validation leaves Phase 1-4 untouched and its machinery is exact where it claims to be."""
import hashlib

import numpy as np
import pandas as pd
import pytest

from bb_inflation.config import OUTPUTS, PROJECT_ROOT
from bb_inflation.phase4b import baseline as B
from bb_inflation.phase4b import bridge as BR
from bb_inflation.phase4b import forecast as F
from bb_inflation.phase4b import uncertainty as U
from bb_inflation.phase4b import wage as WG
from bb_inflation.scenarios import backtest as BT
from bb_inflation.scenarios import scenario as S
from bb_inflation.scenarios import world as W


@pytest.fixture(scope="module")
def w():
    return S.finalise(W.build(nowcast=True, n_draws=50))


def test_phase1_to_4_files_are_unchanged():
    man = PROJECT_ROOT / "outputs" / "phase4b" / "pre_phase4b_manifest.sha256"
    bad = []
    for line in man.read_text().splitlines():
        h, rel = line.split(" *", 1)
        f = PROJECT_ROOT / rel.strip()
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
            bad.append(rel)
    assert not bad, bad


def test_catchup_overlay_does_not_touch_estimates_and_is_recentred(w):
    before = {k: v.copy() for k, v in w.cs_point.values.items()}
    mean_cu = float(w.data["diffcpicf"].loc["1990Q1":"2026Q2"].mean())
    alt = WG.overlay_coefs(w.cs_point, 0.25, mean_cu)
    for k, v in w.cs_point.values.items():
        np.testing.assert_array_equal(v, before[k])                       # estimates untouched
    assert abs(alt.block_sum("gw", "diffcpicf")[0] - 0.25) < 1e-12
    # fitted wage growth at the sample-average catch-up term is unchanged by the overlay
    nm = w.cs_point.names["gw"]
    est_sum = w.cs_point.block_sum("gw", "diffcpicf")[0]
    delta_const = alt.get("gw", "const")[0] - w.cs_point.get("gw", "const")[0]
    assert abs(delta_const + (0.25 - est_sum) * mean_cu) < 1e-12
    other = [k for k in alt.values if k != "gw"]
    for k in other:
        np.testing.assert_array_equal(alt.values[k], w.cs_point.values[k])


def test_forecast_decomposition_is_exact_and_reproduces_phase4_tier_d(w):
    comp, _ = F.decompose(w, [pd.Period("2012Q4", "Q"), pd.Period("2021Q4", "Q"), pd.Period("2025Q2", "Q")])
    assert comp["check (sum - error)"].abs().max() < 1e-8
    rec = pd.read_csv(OUTPUTS / "phase4" / "backtest_records.csv")
    q = comp[comp.measure.str.startswith("quarterly")]
    m = rec[rec.tier == "D"].merge(q[["origin", "h", "tier D"]], on=["origin", "h"])
    assert len(m) == len(q)
    np.testing.assert_allclose(m["forecast"], m["tier D"], atol=1e-9)


def test_reference_steps_add_up_to_baseline(w):
    st = B.reference_steps(w)
    base = S.measures(w, S.run(w, S.Scenario("b", "b")))["yoy_pct"].values
    assert np.abs(st.iloc[:, :-1].sum(axis=1).values - base).max() < 0.02
    assert abs(st["+ estimated wage constant"].iloc[-1] - 0.50) < 0.02          # the Phase 4 neutral-constant sensitivity (3.13 vs 2.63)


def test_bridge_helpers_reproduce_phase4_bridge(w):
    r = BR.fit_bridge(w.cpie_m, w.oil_actual, end="2026-06")
    np.testing.assert_allclose(r["b"].values, w.bridge.coef.values, atol=1e-10)
    e, se = BR.lin_comb(r, ["o0", "o1", "o2", "o3"])
    assert abs(e - w.bridge.elasticity) < 1e-10 and abs(se - w.bridge.elasticity_se()) < 1e-10


def test_joint_bootstrap_respects_the_authors_restrictions(w):
    cs = U.joint_bootstrap_coefs(w, n=20, seed=3)
    own, cf1 = cs.block_sum("gw", "gw"), cs.block_sum("gw", "cf1")
    np.testing.assert_allclose(own + cf1, 1.0, atol=1e-8)
    np.testing.assert_allclose(cs.block_sum("gcpi", "gcpi") + cs.block_sum("gcpi", "gw"), 1.0, atol=1e-8)
    np.testing.assert_allclose(cs.block_sum("cf10", "cf10") + cs.block_sum("cf10", "gcpi"), 1.0, atol=1e-8)


def test_fan_quantiles_are_ordered(w):
    df = U.fan_coverage(w, [pd.Period("2015Q4", "Q")], n=60)
    assert (df["q05"] <= df["q50"]).all() and (df["q50"] <= df["q95"]).all()


def test_presentation_tables_are_consistent():
    sc = pd.read_csv(OUTPUTS / "phase4b" / "p5_scenario_table.csv")
    assert len(sc) == 15 * 3
    assert (sc["specification range lo (pp)"] <= sc["headline y/y deviation (pp)"] + 1e-9).all()
    assert (sc["specification range hi (pp)"] >= sc["headline y/y deviation (pp)"] - 1e-9).all()
    ph = pd.read_csv(OUTPUTS / "phase4b" / "p5_baseline_bands.csv", index_col=0)
    assert (ph["empirical real-time band lo (all targets, 5%)"].dropna() < ph["baseline y/y (%)"].iloc[1:]).all()
    assert (ph["conditional model band lo (5%)"].dropna() < ph["conditional model band hi (95%)"].dropna()).all()
