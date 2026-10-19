"""Phase 4: engine equivalence, nominal-price closure, attribution identities, oil bridge, scenario rules, data pins, and that
Phase 1-3 files (outputs, docs, code, tests) are byte-identical to their state before Phase 4 started."""
import dataclasses
import hashlib

import numpy as np
import pandas as pd
import pytest

from bb_inflation.config import OUTPUTS, PROJECT_ROOT
from bb_inflation.scenarios import attribution as A
from bb_inflation.scenarios import backtest as BT
from bb_inflation.scenarios import engine as E
from bb_inflation.scenarios import library as L
from bb_inflation.scenarios import oil as O
from bb_inflation.scenarios import pull as P
from bb_inflation.scenarios import scenario as S
from bb_inflation.scenarios import world as W
from bb_inflation.scenarios.pin import PHASE4_PULL
from bb_inflation.simulation.model import ENDO, SimModel

LAGS = 4


@pytest.fixture(scope="module")
def w():
    return S.finalise(W.build(nowcast=True, n_draws=50))


@pytest.fixture(scope="module")
def lib(w):
    return L.build(w)


def test_engine_reproduces_phase3_simulator(w):
    d = w.data.loc["2019Q4":"2026Q2"]
    m = SimModel({eq: pd.Series(w.cs_point.values[eq][0], index=w.cs_point.names[eq]) for eq in w.cs_point.names})
    ex = {v: d[v].values.astype(float) for v in ("grpe", "grpf", "vu", "magpty", "shortagema2")}
    dum = {n: d[n].values.astype(float) for n in ("D2020Q2", "D2020Q3")}
    hist = {k: d[k].values[:LAGS].astype(float) for k in ENDO}
    old = m.simulate(hist, {k: ex[k] for k in ("grpe", "grpf", "vu", "magpty", "shortagema2")}, dummies=dum)
    dm = sum(float(m.coefs["gw"][n]) * dum[n] for n in dum)
    inp = E.Inputs(hist={**hist, "grpe": d.grpe.values[:LAGS], "grpf": d.grpf.values[:LAGS]}, exog={k: ex[k] for k in ("vu", "magpty", "shortagema2")},
                   gE=np.zeros(len(d)), gF=np.zeros(len(d)), rel_override={"grpe": ex["grpe"], "grpf": ex["grpf"]}, add={"gw": dm})
    new = E.simulate(w.cs_point, inp)
    for k in ("gw", "gcpi", "cf1", "cf10"):
        np.testing.assert_allclose(new[k][0], old[k], atol=1e-12)


def test_price_equation_is_homogeneous_in_nominal_growth(w):
    wt = w.cs_point.effective_nominal_weights()
    assert sum(float(v[0]) for v in wt.values()) == pytest.approx(1.0, abs=1e-9)
    assert 0.55 < float(wt["wages (net)"][0]) < 0.65


def test_relative_prices_are_derived_from_wages(w):
    r = S.run(w, S.Scenario("b", "b"))
    gw, grpe, grpf = r.path["gw"][0], r.path["grpe"][0], r.path["grpf"][0]
    np.testing.assert_allclose(grpe[LAGS:], r.inputs.gE[0, LAGS:] - gw[LAGS:], atol=1e-12)
    np.testing.assert_allclose(grpf[LAGS:], r.inputs.gF[LAGS:] - gw[LAGS:], atol=1e-12)
    assert np.allclose(grpf[LAGS + 1:], 0.0, atol=1e-10)                # baseline convention: food keeps pace with baseline wages


def test_wage_shock_moves_relative_price_not_nominal_energy(w, lib):
    rb = S.run(w, S.Scenario("b", "b"))
    rs = S.run(w, lib["vu_tight"])
    np.testing.assert_allclose(rs.inputs.gE, rb.inputs.gE)             # nominal energy is unchanged by a labour-market scenario
    assert (rs.path["gw"][0, LAGS + 4:] > rb.path["gw"][0, LAGS + 4:]).all()
    assert (rs.path["grpe"][0, LAGS + 4:] < rb.path["grpe"][0, LAGS + 4:]).all()   # so the relative price falls: wages are endogenous


def test_scenarios_cannot_set_relative_prices():
    for k in ("rel_energy_dev", "grpe_path", "relative_food"):
        with pytest.raises(ValueError):
            S.scenario("x", "x", **{k: [0.0] * 13})


def test_empty_scenario_equals_baseline_and_nowcast_quarter_is_published(w):
    rb, r0 = S.run(w, S.Scenario("b", "b")), S.run(w, S.Scenario("z", "z"))
    np.testing.assert_allclose(rb.path["gcpi"], r0.path["gcpi"])
    assert rb.path["gcpi"][0, LAGS] == pytest.approx(w.q3["gcpi"])
    assert rb.path["cf1"][0, LAGS] == pytest.approx(w.q3["cf1"])


def test_scenarios_do_not_alter_the_nowcast_quarter(w):
    sc = S.scenario("x", "x", oil_dev_pct=[50.0] * 13, vu_dev=[0.5] * 13, gscpi_dev=[2.0] * 13, food_dev_pct=[20.0] * 13)
    rb, rs = S.run(w, S.Scenario("b", "b")), S.run(w, sc)
    assert rs.path["gcpi"][0, LAGS] == rb.path["gcpi"][0, LAGS]
    assert rs.path["gw"][0, LAGS] == rb.path["gw"][0, LAGS]
    assert (rs.oil_m.loc[:"2026-09-01"] == rb.oil_m.loc[:"2026-09-01"]).all()    # observed oil is never shocked


def test_driver_and_layer_attribution_are_exact(w, lib):
    for k in ("adverse_supply", "overheating", "benign"):
        _, g1 = A.by_driver(w, lib[k])
        _, g2 = A.by_layer(w, lib[k])
        assert g1 < 1e-9 and g2 < 1e-9


def test_proximate_blocks_sum_to_total_deviation(w, lib):
    pb = A.proximate_blocks(w, lib["adverse_supply"])
    tot = A.total_effect(w, lib["adverse_supply"])["annualised"][0]
    np.testing.assert_allclose(pb["total"].values, tot, atol=1e-9)


def test_haircut_scales_only_the_energy_block(w):
    cs = w.cs_point.scaled("gcpi", "grpe", 0.8)
    for j, nm in enumerate(cs.names["gcpi"]):
        ratio = cs.values["gcpi"][0, j] / w.cs_point.values["gcpi"][0, j]
        assert ratio == pytest.approx(0.8 if nm.startswith("grpe_L") else 1.0)
    assert cs.values["gw"] is not None and np.allclose(cs.values["gw"], w.cs_point.values["gw"])


def test_oil_effect_is_linear_in_the_shock_and_sign_symmetric(w):
    up = A.total_effect(w, S.scenario("u", "u", oil_dev_pct=L.step(10.0)))["level"][0, 4]
    dn = A.total_effect(w, S.scenario("d", "d", oil_dev_pct=L.step(-10.0)))["level"][0, 4]
    big = A.total_effect(w, S.scenario("b", "b", oil_dev_pct=L.step((1.1 ** 2 - 1) * 100)))["level"][0, 4]
    assert big == pytest.approx(2 * up, rel=1e-9)           # linear in the log deviation
    assert up > 0 > dn


def test_bridge_quarterly_aggregation_and_elasticity(w):
    assert 0.2 < w.bridge.elasticity < 0.4
    m = np.arange(6, dtype=float)[None, :]
    np.testing.assert_allclose(O.quarterly_energy_growth(m), [[4 * 3.0, 4 * 12.0]])
    mult = O.deviation_to_monthly(np.array([10.0, 10.0]), pd.Period("2026Q4", "Q"), pd.date_range("2026-07-01", "2027-03-01", freq="MS"))
    assert (mult[:3] == 1.0).all() and mult[3] == pytest.approx(1.1)


def test_baseline_oil_curve_uses_live_contracts(w):
    c = w.oil_curve["futures"]
    assert c.index[0] == pd.Timestamp("2026-10-01") and c.index[-1] == pd.Timestamp("2029-12-01")
    assert c.loc["2026-11-01"] == pytest.approx(0.5 * (c.loc["2026-10-01"] + c.loc["2026-12-01"]))
    assert c.loc["2026-12-01"] > c.loc["2028-12-01"] > c.loc["2029-12-01"]            # backwardation of the day


def test_phase4_pull_integrity_and_agreement_with_pinned_model_data(w):
    P.load(PHASE4_PULL)                                                      # raises on any hash mismatch
    qa = W.qa_vs_pinned(w)
    assert qa["max |difference|"].max() < 1e-9


def test_backtest_engine_reproduces_phase3_oos_records(w):
    rec = BT.run(w, [pd.Period("2010Q4", "Q"), pd.Period("2019Q4", "Q")])
    p3 = pd.read_csv(OUTPUTS / "phase3" / "oos_records.csv")
    p3 = p3[(p3.model == "U") & (p3["var"] == "gcpi")]
    for tier, mode in (("A", "conditional"), ("F", "unconditional")):
        a = rec[rec.tier == tier].merge(p3[p3["mode"] == mode], on=["origin", "h", "target"], suffixes=("", "_p3"))
        assert len(a) == 24
        np.testing.assert_allclose(a["forecast"], a["forecast_p3"], atol=1e-9)


def test_phase1_to_3_files_are_unchanged():
    man = PROJECT_ROOT / "outputs" / "phase4" / "pre_phase4_manifest.sha256"
    bad = []
    for line in man.read_text().splitlines():
        h, rel = line.split(" *", 1)
        f = PROJECT_ROOT / rel.strip()
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
            bad.append(rel)
    assert not bad, bad
