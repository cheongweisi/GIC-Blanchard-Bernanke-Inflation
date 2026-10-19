"""Phase 4c (simplified exercise): the four standardised shocks are what they claim to be, and agree with the full Phase 4c machinery."""
import hashlib

import numpy as np
import pytest

from bb_inflation.config import PROJECT_ROOT
from bb_inflation.phase4c import compare as CP
from bb_inflation.phase4c import irf as I
from bb_inflation.phase4c import simple as SM
from bb_inflation.phase4c import study as ST


@pytest.fixture(scope="module")
def st():
    return ST.build(n=300)


@pytest.fixture(scope="module")
def ctx(st):
    sd = CP.gscpi_sd(st.data)
    b = I.bridge().coef.values[1:]
    cs = st.coefset("B26", point=True)
    return sd, b, cs


def coef(cs, eq, name):
    return float(cs.get(eq, name)[0])


def test_q0_responses_are_coefficient_arithmetic(ctx):
    sd, b, cs = ctx
    # food: level +10% in Q0 = annualised growth 400 ln(1.1); wages do not move in Q0, so relative food growth equals nominal food growth
    food = SM.responses(cs, "food", b, sd)[0, 0]
    assert abs(food - coef(cs, "gcpi", "grpf_L0") * 400 * np.log(1.1)) < 1e-9
    # energy: Q0 energy growth from the bridge (3 monthly changes), times the contemporaneous relative-energy coefficient
    gE0 = I.oil_energy_growth(b, 10.0, "sustained", 4)[0]
    assert abs(SM.responses(cs, "energy", b, sd)[0, 0] - coef(cs, "gcpi", "grpe_L0") * gE0) < 1e-9
    # wages: +1pp residual, contemporaneous wage coefficient less the energy and food offsets are zero in Q0 (relative prices = nominal - wage)
    w = SM.responses(cs, "wages", b, sd)[0, 0]
    net = coef(cs, "gcpi", "gw_L0") - coef(cs, "gcpi", "grpe_L0") - coef(cs, "gcpi", "grpf_L0")
    assert abs(w - net) < 1e-9
    # supply: GSCPI +1 sd in Q0, price equation uses the 2-quarter mean, so half of it in Q0
    assert abs(SM.responses(cs, "supply", b, sd)[0, 0] - coef(cs, "gcpi", "shortagema2_L0") * sd / 2) < 1e-9


def test_agrees_with_full_phase4c_machinery(st, ctx):
    sd, b, cs = ctx
    cat = I.shock_catalogue(sd)
    for key, full in (("energy", "O10"), ("wages", "W1"), ("supply", "G1")):
        a = SM.responses(cs, key, b, sd)[0]
        f = I.run(cs, cat[full], "nominal", b)["gcpi"][0, :SM.NQ]
        np.testing.assert_allclose(a, f, atol=1e-12)


def test_food_level_shift_is_permanent_and_one_off(ctx):
    sd, b, cs = ctx
    inp = SM.inputs("food", b, sd)
    gF = np.asarray(inp.gF)
    assert abs(gF[I.LAGS] - 400 * np.log(1.1)) < 1e-12 and np.abs(np.delete(gF, I.LAGS)).max() == 0
    assert not inp.add and not inp.frozen
    assert abs(gF.sum() / 400 - np.log(1.1)) < 1e-12          # CPI food level +10% for good


def test_persistence_metric_definition():
    # peak in Q1 (0.25), threshold 0.125: first below half in Q7 (0.08) -> 6 quarters from the peak
    g = np.array([[0.2, 0.25, 0.19, 0.25 - 0.0001, 0.13, 0.15, 0.13, 0.08, 0.09, 0.07, 0.06, 0.06]])
    m = SM.metrics(g)
    assert m["peak response (pp)"][0] == 0.25 and m["quarter of peak"][0] == 1
    assert m[SM.PERSIST][0] == 6 and m[SM.REBOUND][0] == 0
    assert abs(m["price level after 12 quarters (%)"][0] - g.sum() / 4) < 1e-12
    # the user's example: peak in Q1, first below half in Q5 -> 4 quarters
    g = np.array([[0.3, 1.0, 0.8, 0.6, 0.5, 0.4, 0.2, 0.1, 0.0, 0.0, 0.0, 0.0]])
    m = SM.metrics(g)
    assert m["quarter of peak"][0] == 1 and m[SM.PERSIST][0] == 4        # 0.5 is not below half (strict); Q5 = 0.4 is the first below 0.5


def test_persistence_not_reached_and_rebound_flag():
    # never falls below half the peak inside the horizon: undefined (NaN), not "dissipated"
    g = np.array([[0.1, 0.5, 0.9, 1.0, 1.0, 1.0, 0.9, 0.9, 0.8, 0.8, 0.7, 0.7]])
    m = SM.metrics(g)
    assert np.isnan(m[SM.PERSIST][0]) and m[SM.REBOUND][0] == 0
    # falls below half in Q1, comes back above half in Q4: rebound flagged with its quarter
    g = np.array([[1.0, 0.2, 0.1, 0.3, 0.7, 0.2, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0]])
    m = SM.metrics(g)
    assert m[SM.PERSIST][0] == 1 and m[SM.REBOUND][0] == 1 and m[SM.REBOUND_Q][0] == 4


def test_food_response_is_flagged_as_rebounding(st, ctx):
    sd, b, cs = ctx
    m = SM.metrics(SM.responses(cs, "food", b, sd))
    assert m[SM.REBOUND][0] == 1 and m[SM.REBOUND_Q][0] == 4


def test_full_phase4c_outputs_untouched():
    man = PROJECT_ROOT / "outputs" / "phase4c" / "pre_phase4c_manifest.sha256"
    bad = []
    for line in man.read_text().splitlines():
        h, rel = line.split(" *", 1)
        f = PROJECT_ROOT / rel.strip()
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
            bad.append(rel)
    assert not bad, bad


def test_food_q4_echo_is_the_lag4_coefficient_and_hinges_on_2021q2(st, ctx):
    from bb_inflation.phase4c import simple_diag as DG
    sd, b, cs = ctx
    fd = DG.food_decomposition(st, sd)
    l4 = coef(cs, "gcpi", "grpf_L4")
    assert abs(fd.loc[4, "direct food-coefficient term (L_k x 38.1)"] - l4 * 400 * np.log(1.1)) < 1e-9
    assert fd["direct food-coefficient term (L_k x 38.1)"].iloc[5:].abs().max() == 0
    fv = DG.food_variants(st, sd).set_index("price equation")
    assert fv.loc["B*-2026 as estimated (food lags 0-4)", "food L4"] > 0.07
    assert fv.loc["B*-2026 without the 2021Q2 observation", "food L4"] < 0           # one observation removes the echo
    assert fv.loc["B*-2026 without the 2021Q2 observation", "rebound above half-peak?"] == "no"
    assert fv["price level after 12 quarters (%)"].between(2.0, 2.7).all()            # the cumulative effect is robust


def test_energy_food_comparability_identity(st, ctx):
    from bb_inflation.phase4c import simple_diag as DG
    sd, b, cs = ctx
    cp = DG.comparability(st, sd).set_index("shock")
    e, f = cp.iloc[0], cp.iloc[1]
    assert abs(f["model: price level after 12 quarters (%)"] / e["model: price level after 12 quarters (%)"]
               - (f["change in own CPI component (%)"] / e["change in own CPI component (%)"]) * (f["model effect per 1% rise in own component"] / e["model effect per 1% rise in own component"])) < 1e-9
    assert abs(e["change in own CPI component (%)"] - 100 * (np.exp(I.bridge().elasticity * 100 * np.log(1.1) / 100) - 1)) < 1e-9
    # the standardised energy shock equals the first row; the like-for-like energy shock is linear in size up to the log conversion
    assert abs(cp.iloc[2]["model effect per 1% rise in own component"] - e["model effect per 1% rise in own component"]) < 0.01


def test_rebound_flag_depends_on_quarterly_noise(st, ctx):
    from bb_inflation.phase4c import simple_diag as DG
    sd, b, cs = ctx
    rs = DG.rebound_sensitivity(st, sd).set_index("shock")
    pct = lambda x: float(x.strip("%")) / 100                                           # noqa: E731
    assert pct(rs.loc["Wages", "4-quarter average (y/y)"]) < pct(rs.loc["Wages", "quarterly response (as flagged)"])


def test_food_lags03_sensitivity_row_is_a_diagnostic_not_bstar(st, ctx):
    from bb_inflation.phase4c import simple_diag as DG
    sd, b, cs = ctx
    rows = DG.food_lags03_stat_rows(st, sd).set_index("statistic")
    base = SM.metrics(SM.responses(cs, "food", b, sd))
    assert rows.loc["Q0 response (pp)", "point"] < base["Q0 response (pp)"][0] + 0.5            # same shock, similar impact
    assert rows.loc[SM.REBOUND, "point"] == 0 and base[SM.REBOUND][0] == 1                       # lag 4 removed: no rebound; B* has one
    assert 2.0 < rows.loc["price level after 12 quarters (%)", "point"] < 2.2                     # cumulative effect close to B*'s 2.38
    # the production coefficients are untouched
    assert abs(float(cs.get("gcpi", "grpf_L4")[0]) - 0.078) < 0.001
