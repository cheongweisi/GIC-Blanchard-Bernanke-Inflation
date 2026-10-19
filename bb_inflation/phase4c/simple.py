"""Simplified transmission exercise: four standardised, illustrative shocks, three questions (speed, magnitude, persistence) about headline CPI inflation.

Separate from the full Phase 4c analysis (nothing there is changed; outputs go to outputs/phase4c_simple/). Same model, estimates, joint coefficient draws, oil bridge and headline
'nominal' energy/food convention as Phase 4c; the only new ingredient is the food-price shock.

Horizon: 12 quarters, Q0 (the shock quarter) to Q11. 'After 3 years' = cumulative over Q0-Q11 (12 quarters); the full report's price-level figures cover 13 quarters (Q0-Q12).
Units: CPI inflation in annualised percentage points; price level in %, = sum of the annualised responses / 4.

Shocks (illustrative, NOT economically equivalent; the sizes are chosen for convenience, so the responses must not be ranked as 'which driver is more powerful'):
  Energy  Brent level +10%, permanent. Through the calibrated oil bridge (elasticity 0.297) CPI energy ends about 2.8% higher.
  Food    CPI food price level +10%, permanent, in the quarter of the shock (annualised growth 400 ln 1.1 = 38.1pp in Q0, nothing afterwards).
  Wages   wage-equation residual +1pp in one quarter (wage inflation 1pp higher for one quarter; later wage growth responds through the model).
  Supply  GSCPI +1 standard deviation (0.969, 1998Q1-2026Q2) for one quarter.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..scenarios import engine as E
from . import irf as I
from . import samples as S
from .study import Study

NQ = 12                                  # Q0..Q11
HZ = NQ - 1
ORDER = ("energy", "food", "wages", "supply")
NAME = {"energy": "Energy: Brent +10% (permanent)", "food": "Food: CPI food +10% (permanent)", "wages": "Wages: +1pp for one quarter", "supply": "Supply chains: GSCPI +1 s.d. for one quarter"}
SHORT = {"energy": "Energy", "food": "Food", "wages": "Wages", "supply": "Supply chains"}
VINTS = ("B26", "B19", "B23")
FOOD_LOG_POINTS = 100 * np.log(1.1)


def inputs(key: str, b: np.ndarray, gscpi_sd: float, horizon: int = I.H) -> E.Inputs:
    cat = I.shock_catalogue(gscpi_sd)
    if key == "energy":
        return I.make_inputs(cat["O10"], "nominal", b, horizon)
    if key == "wages":
        return I.make_inputs(cat["W1"], "nominal", b, horizon)
    if key == "supply":
        return I.make_inputs(cat["G1"], "nominal", b, horizon)
    if key == "food":
        base = I.make_inputs(cat["W1"], "nominal", b, horizon)          # all-zero baseline plus a wage residual, which is removed below
        gF = np.zeros_like(np.asarray(base.gF, float))
        gF[I.LAGS] = 4 * FOOD_LOG_POINTS                                 # level +10% in Q0: annualised growth 400 ln(1.1) once
        return base.replace(add={}, gF=gF)
    raise KeyError(key)


def responses(cs: E.CoefSet, key: str, b: np.ndarray, gscpi_sd: float) -> np.ndarray:
    """CPI inflation response (n x NQ), annualised pp, Q0..Q11."""
    p = E.simulate(cs, inputs(key, b, gscpi_sd))
    return np.asarray(p["gcpi"])[:, I.LAGS:I.LAGS + NQ]


PERSIST = "persistence: quarters from peak until the response first falls below 50% of the peak"
REBOUND = "rebounds to at least 50% of the peak after first falling below it (1 = yes)"
REBOUND_Q = "quarter of the first rebound"


def metrics(g: np.ndarray) -> dict[str, np.ndarray]:
    """Per-path statistics for responses g (n x NQ): speed, magnitude, persistence.

    Persistence = quarters from the peak until the response FIRST falls below 50% of the peak (peak in Q1, first below half in Q5: 4 quarters). NaN = not reached within the
    12-quarter horizon (the response has NOT dissipated as far as we can see). Rebound: after that first fall, the response is again at or above 50% of the peak within the horizon.
    A path whose peak is not positive has no defined persistence."""
    n = len(g)
    pk_i = g.argmax(axis=1)
    pk = g[np.arange(n), pk_i]
    pers, reb, reb_q = np.full(n, np.nan), np.zeros(n), np.full(n, np.nan)
    for i in range(n):
        if pk[i] <= 0:
            continue
        half = 0.5 * pk[i]
        below = np.where(g[i, pk_i[i]:] < half)[0]
        if len(below):
            first = pk_i[i] + below[0]
            pers[i] = below[0]
            back = np.where(g[i, first + 1:] >= half)[0]
            if len(back):
                reb[i], reb_q[i] = 1.0, first + 1 + back[0]
    return {"Q0 response (pp)": g[:, 0], "Q1 response (pp)": g[:, 1], "peak response (pp)": pk, "quarter of peak": pk_i.astype(float),
            PERSIST: pers, REBOUND: reb, REBOUND_Q: reb_q,
            "response in Q4 as % of peak": 100 * g[:, 4] / pk, "response in Q11 as % of peak": 100 * g[:, 11] / pk,
            "price level after 12 quarters (%)": g.sum(axis=1) / 4.0, "price level after 4 quarters (%)": g[:, :5].sum(axis=1) / 4.0}


def run(st: Study, gscpi_sd: float) -> dict:
    b = I.bridge().coef.values[1:]
    out = {"paths": [], "stats": [], "diffs": []}
    for key in ORDER:
        draws, point = {}, {}
        for vk in VINTS:
            point[vk] = responses(st.coefset(vk, point=True), key, b, gscpi_sd)
            draws[vk] = responses(st.coefset(vk), key, b, gscpi_sd)
        stat_d = {vk: metrics(draws[vk]) for vk in VINTS}
        stat_p = {vk: metrics(point[vk]) for vk in VINTS}
        for vk in VINTS:
            q = np.quantile(draws[vk], (0.05, 0.5, 0.95), axis=0)
            for h in range(NQ):
                out["paths"].append({"shock": key, "vintage": S.LABEL[vk], "quarter": h, "point": float(point[vk][0, h]), "lo90": float(q[0, h]), "median": float(q[1, h]), "hi90": float(q[2, h])})
            for name, arr in stat_d[vk].items():
                out["stats"].append({"shock": key, "vintage": S.LABEL[vk], "statistic": name, "point": float(stat_p[vk][name][0]),
                                     "lo90": float(np.nanquantile(arr, .05)), "hi90": float(np.nanquantile(arr, .95)), "share of draws undefined": float(np.isnan(arr).mean()), "mean over draws": float(np.nanmean(arr))})
        for other in ("B19", "B23"):
            for name in stat_d["B26"]:
                d = stat_d["B26"][name] - stat_d[other][name]
                ok = ~np.isnan(d)
                out["diffs"].append({"shock": key, "comparison": f"{S.LABEL['B26']} minus {S.LABEL[other]}", "statistic": name,
                                     "difference": float(stat_p["B26"][name][0] - stat_p[other][name][0]), "lo90": float(np.quantile(d[ok], .05)) if ok.sum() > 20 else np.nan,
                                     "hi90": float(np.quantile(d[ok], .95)) if ok.sum() > 20 else np.nan,
                                     "p (two-sided, from draws)": float(min(1.0, 2 * min((d[ok] >= 0).mean(), (d[ok] <= 0).mean()))) if ok.sum() > 20 else np.nan})
    return {k: pd.DataFrame(v) for k, v in out.items()}


def definitions(st: Study, gscpi_sd: float) -> pd.DataFrame:
    """What exactly is shocked, and what that does to the driver's own CPI component (so the shocks are not mistaken for equivalent ones)."""
    b = I.bridge()
    x = 100 * np.log(1.1)
    cs = st.coefset("B26", point=True)
    return pd.DataFrame([
        {"shock": SHORT["energy"], "standardised shock": "Brent price level +10%, permanent", "what moves in the model": "nominal CPI energy growth, through the oil bridge (calibrated, elasticity %.3f)" % b.elasticity,
         "implied change in the shocked CPI component": f"CPI energy level +{100 * (np.exp(b.elasticity * x / 100) - 1):.1f}% after four months (bridge)"},
        {"shock": SHORT["food"], "standardised shock": "CPI food price level +10%, permanent", "what moves in the model": "nominal CPI food growth: +38.1pp annualised in Q0, zero afterwards",
         "implied change in the shocked CPI component": "CPI food level +10.0% in Q0"},
        {"shock": SHORT["wages"], "standardised shock": "wage inflation +1pp for one quarter", "what moves in the model": "residual added to the wage equation in Q0 (later wage growth is endogenous)",
         "implied change in the shocked CPI component": "ECI wage level about +0.25% in Q0 (1pp annualised); more later through expectations feedback"},
        {"shock": SHORT["supply"], "standardised shock": f"GSCPI +1 s.d. ({gscpi_sd:.3f}) for one quarter", "what moves in the model": "GSCPI in Q0 only; the price equation uses its 2-quarter mean, so it acts in Q0 and Q1",
         "implied change in the shocked CPI component": "not a price: an index of supply-chain pressure"}])
