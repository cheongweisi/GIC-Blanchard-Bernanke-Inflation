"""Phase 4b, part 3: why does the baseline CPI inflation forecast rise towards 3.1% in 2029, and are the implied wage dynamics plausible?

Tools (all on the unchanged Phase 4 engine and baseline):
* `reference_steps`      exact, additive build-up of the baseline y/y path from a neutral reference (every driver neutral, authors' neutral wage constant)
                         through (1) the estimated wage constant, (2) the energy path, (3) the supply-chain path. Linear model: order does not matter.
* `long_run_drift`       run the model for 80 quarters with all drivers at their neutral values and the estimated vs the neutral wage constant:
                         inflation has no anchor (all sums restricted to one), so the constant gap becomes a trend in inflation.
* `neutral_vu`           the V/U at which the estimated wage constant is neutral (no drift), with the other drivers at baseline values.
* `history_wedge`        data check of the implied wage dynamics: wage growth against expectations, productivity and V/U in history vs baseline.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from ..extension.models import ModelSpec, fit, standard_models
from ..scenarios import engine as E
from ..scenarios import scenario as S
from ..scenarios.world import LAGS, World, neutral_wage_constant
from .common import yoy_pct_from_ann

SHORT_STAR = -0.035


def _neutral_const(w: World, cs: E.CoefSet, vu_star: float | None = None) -> np.ndarray:
    return neutral_wage_constant(cs, float(w.base_exog["vu"][LAGS - 1]) if vu_star is None else vu_star, float(w.base_exog["magpty"][LAGS - 1]), SHORT_STAR)


def _first(w: World) -> int:
    return LAGS + (1 if w.nowcast else 0)


def _run(w: World, cs: E.CoefSet, inp: E.Inputs, **kw) -> np.ndarray:
    return E.simulate(cs, inp.replace(**kw))["gcpi"][0]


def reference_steps(w: World) -> pd.DataFrame:
    """Exact additive build-up of the baseline y/y path (%), all in the engine's NOMINAL closure so that every input is exogenous and the model is linear.

    Reference: authors' neutral wage constant, GSCPI at its steady value, V/U and productivity at baseline values, and nominal energy and food growth equal to
    the reference's own wage growth (relative prices constant). Then switch on, one input at a time (order does not matter): the energy path (futures curve
    through the bridge), the food path, the supply-chain path, and the estimated wage constant. The sum is the headline baseline to machine precision."""
    base = S.run(w, S.Scenario("base", "b"))
    inp, cs = base.inputs, base.cs
    T, first = w.T, _first(w)
    nan = np.full(T, np.nan)
    rel = {k: nan.copy() for k in ("grpe", "grpf")}
    for k in rel:
        rel[k][first:] = 0.0
    sh = w.base_shortage.copy()
    sh[LAGS:] = SHORT_STAR
    ma2 = pd.Series(sh).rolling(2, min_periods=2).mean().values.copy()
    ma2[:LAGS] = inp.exog["shortagema2"][:LAGS]
    ex_ref = {**inp.exog, "shortagema2": ma2}
    cn = {"gw": _neutral_const(w, cs)}
    p_ref = E.simulate(cs, inp.replace(rel_override=rel, exog=ex_ref, const_override=cn))
    gw_ref = p_ref["gw"][0]
    gE_ref = np.asarray(inp.gE)[0].copy()
    gF_ref = np.asarray(inp.gF).copy()
    gE_ref[first:] = gw_ref[first:]
    gF_ref[first:] = gw_ref[first:]                                    # nominal paths that keep relative prices constant in the reference
    ref_inp = inp.replace(gE=gE_ref, gF=gF_ref, exog=ex_ref, const_override=cn)
    y = lambda inputs: yoy_pct_from_ann(E.simulate(cs, inputs)["gcpi"][0])[LAGS:]          # noqa: E731
    y_ref = y(ref_inp)
    assert np.allclose(y_ref, yoy_pct_from_ann(p_ref["gcpi"][0])[LAGS:], atol=1e-8)
    gE_b, gF_b = np.asarray(inp.gE)[0], np.asarray(inp.gF)
    y_e = y(ref_inp.replace(gE=gE_b))
    y_f = y(ref_inp.replace(gF=gF_b))
    y_s = y(ref_inp.replace(exog=inp.exog))
    y_c = y(ref_inp.replace(const_override=inp.const_override))
    tot = y_ref + (y_e - y_ref) + (y_f - y_ref) + (y_s - y_ref) + (y_c - y_ref)
    q = w.quarters
    # y/y is a log-approx mean; the sum of linear contributions is exact in the annualised rates, so y/y (a monotone transform) is checked against the baseline
    assert np.abs(tot - yoy_pct_from_ann(base.path["gcpi"][0])[LAGS:]).max() < 0.02, np.abs(tot - yoy_pct_from_ann(base.path["gcpi"][0])[LAGS:]).max()
    return pd.DataFrame({"neutral reference": y_ref, "+ energy path": y_e - y_ref, "+ food path": y_f - y_ref, "+ supply-chain path": y_s - y_ref,
                         "+ estimated wage constant": y_c - y_ref, "= baseline y/y (%)": yoy_pct_from_ann(base.path["gcpi"][0])[LAGS:]}, index=q)


def long_run_drift(w: World, quarters: int = 80) -> pd.DataFrame:
    """Model run for `quarters` with V/U, productivity, GSCPI and relative prices all neutral/held at baseline values, wage constant estimated vs neutral.
    Returns y/y inflation (%) at yearly points. Shows what the estimated constant does when nothing else moves."""
    cs = w.cs_point
    T = LAGS + quarters
    hist = w.hist
    vu0, mp0 = float(w.base_exog["vu"][LAGS - 1]), float(w.base_exog["magpty"][LAGS - 1])
    ex = {"vu": np.r_[hist["gw"] * 0 + w.base_exog["vu"][:LAGS], np.full(quarters, vu0)], "magpty": np.r_[w.base_exog["magpty"][:LAGS], np.full(quarters, mp0)],
          "shortagema2": np.r_[w.base_exog["shortagema2"][:LAGS], np.full(quarters, SHORT_STAR)]}
    rel = {k: np.r_[np.full(LAGS, np.nan), np.zeros(quarters)] for k in ("grpe", "grpf")}
    inp = E.Inputs(hist=hist, exog=ex, gE=np.zeros(T), gF=np.zeros(T), rel_override=rel)
    out = {}
    for lab, ov in (("estimated wage constant", {}), ("neutral wage constant", {"gw": _neutral_const(w, cs)})):
        p = E.simulate(cs, inp.replace(const_override=ov))
        y = yoy_pct_from_ann(p["gcpi"][0])
        out[lab] = y[LAGS + 3::4][: quarters // 4]
    df = pd.DataFrame(out, index=[f"year {i + 1}" for i in range(quarters // 4)])
    df["difference"] = df["estimated wage constant"] - df["neutral wage constant"]
    return df


def constants_table(w: World) -> pd.DataFrame:
    cs = w.cs_point
    est = float(cs.get("gw", "const")[0])
    neu = float(_neutral_const(w, cs)[0])
    rows = [{"item": "estimated wage constant (annualised pp per quarter)", "value": est},
            {"item": "authors' neutral wage constant at V/U 1.02, productivity 2.14, GSCPI -0.035", "value": neu},
            {"item": "gap (estimated - neutral)", "value": est - neu},
            {"item": "sum of V/U coefficients", "value": float(cs.block_sum("gw", "vu")[0])},
            {"item": "sum of own wage lags (the wage equation's persistence)", "value": float(cs.block_sum("gw", "gw")[0])},
            {"item": "gap expressed as V/U units (gap / sum of V/U coefficients)", "value": (est - neu) / float(cs.block_sum("gw", "vu")[0])}]
    return pd.DataFrame(rows)


def neutral_vu(w: World) -> float:
    """V/U at which the estimated wage constant is neutral, other drivers at their baseline-end values."""
    cs = w.cs_point
    est = float(cs.get("gw", "const")[0])
    f = lambda v: float(_neutral_const(w, cs, v)[0]) - est                      # noqa: E731
    return float(brentq(f, 0.2, 3.0))


def alt_wage_models(w: World) -> dict[str, E.CoefSet]:
    """Wage-constant sensitivities from other estimation samples (estimated; not overlays): equations re-estimated through 2019Q4 and 2023Q2."""
    out = {}
    ms = standard_models(w.ctx.last)["B"]
    for lab, end in (("estimated to 2019Q4", "2019Q4"), ("estimated to 2023Q2", "2023Q2")):
        res = fit(dataclasses.replace(ms, end=end), w.data, end)
        from ..simulation.model import SimModel
        out[lab] = E.CoefSet.from_models([SimModel.from_results(res)])
    return out


def history_wedge(w: World) -> pd.DataFrame:
    """Implied wage dynamics against history. wage-expectations gap = gw - cf1; wedge = gcpi - gw + productivity (price inflation minus unit-labour-cost-like
    wage growth: how much faster prices rise than productivity-adjusted wages). Averages over history windows and for the baseline."""
    d = w.data.copy()
    d["gw_minus_cf1"] = d["gw"] - d["cf1"]
    d["real wage growth"] = d["gw"] - d["gcpi"]
    d["wedge"] = d["gcpi"] - d["gw"] + d["magpty"]
    cols = ["gw", "gcpi", "cf1", "cf10", "vu", "magpty", "gw_minus_cf1", "real wage growth", "wedge"]
    rows = {}
    for lab, (a, b) in {"1990Q1-2007Q4": ("1990Q1", "2007Q4"), "2010Q1-2019Q4": ("2010Q1", "2019Q4"), "2017Q1-2019Q4": ("2017Q1", "2019Q4"),
                        "2023Q3-2026Q2": ("2023Q3", "2026Q2"), "last 4 quarters (2025Q3-2026Q2)": ("2025Q3", "2026Q2")}.items():
        rows[lab] = d.loc[a:b, cols].mean()
    base = S.run(w, S.Scenario("base", "b"))
    m = S.measures(w, base)
    ex = base.inputs.exog
    for lab, sl in (("baseline 2026Q4-2027Q4", slice(1, 6)), ("baseline 2028Q1-2029Q3", slice(6, 13))):
        mm = m.iloc[sl]
        mp = float(ex["magpty"][LAGS])
        r = {"gw": mm["gw"].mean(), "gcpi": mm["gcpi_ann"].mean(), "cf1": mm["cf1"].mean(), "cf10": mm["cf10"].mean(), "vu": float(ex["vu"][LAGS]), "magpty": mp}
        r["gw_minus_cf1"] = r["gw"] - r["cf1"]
        r["real wage growth"] = r["gw"] - r["gcpi"]
        r["wedge"] = r["gcpi"] - r["gw"] + mp
        rows[lab] = pd.Series(r)
    return pd.DataFrame(rows).T
