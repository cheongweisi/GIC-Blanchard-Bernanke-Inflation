"""Phase 4b, part 2: why does the real-time-feasible forecast (tier D) lose to AR(4)? Exact error decomposition.

The model is linear in its inputs and shocks, so the error of tier D (forecast - actual, annualised quarterly CPI inflation or y/y) splits EXACTLY into

    D - actual = [D - C]                         assumed drivers vs realised drivers (via the bridge):
                   oil path (flat vs realised), V/U (held vs realised), productivity (held vs realised),
                   GSCPI (AR(1) vs realised), food (relative price zero, i.e. food grows with wages, vs realised nominal food)
               + [C - B]                         the oil -> CPI energy bridge error (realised oil through the bridge vs realised CPI energy)
               + [B - actual]                    structural-model error: B uses realised nominal energy and food, V/U, productivity, GSCPI;
                                                 the remainder is the response of the model to its own equation residuals, split by equation
                                                 (price, wage, 1y expectations, 10y expectations), exactly, by running the B-world with each
                                                 equation's out-of-sample residuals added.

Tier definitions are those of scenarios/backtest.py (A-F); tier D here reproduces the Phase 4 stored forecasts to 1e-9 (asserted).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..extension.models import standard_models
from ..extension.pseudo_oos import _fit_origin, ar4_forecast, unconditional_exog
from ..scenarios import engine as E
from ..scenarios import oil as O
from ..scenarios.backtest import _hist, _window
from ..scenarios.world import LAGS, World
from ..simulation.model import SimModel

H_MAX = 12
EQS = ("gw", "gcpi", "cf10", "cf1")
COMPONENTS = ("oil path", "V/U", "productivity", "GSCPI", "food closure", "oil bridge", "price eq. residuals", "wage eq. residuals",
              "1y expectations residuals", "10y expectations residuals")


def _sim(cs, hist, exog, gE, gF, rel=None, add=None) -> E.Path:
    return E.simulate(cs, E.Inputs(hist=hist, exog=exog, gE=gE, gF=gF, rel_override=rel or {}, add=add or {}))


def actual_shocks(cs: E.CoefSet, data: pd.DataFrame, T0: pd.Period, h: int) -> dict[str, np.ndarray]:
    """Out-of-sample equation residuals over T0+1..T0+h computed on ACTUAL lags with the origin-T0 coefficients (full-length arrays, zeros in history)."""
    i = data.index.get_loc(T0)
    win = data.iloc[i - LAGS + 1: i + 1 + h]
    n = len(win)
    out = {}
    import re
    term = re.compile(r"^(?P<var>[A-Za-z0-9]+)_L(?P<lag>\d+)$")
    for eq in EQS:
        arr = np.zeros(n)
        names = cs.names[eq]
        for t in range(LAGS, n):
            v = 0.0
            for j, nm in enumerate(names):
                m = term.match(nm)
                if m:
                    v += cs.values[eq][0, j] * float(win[m["var"]].iloc[t - int(m["lag"])])
                elif nm == "const":
                    v += cs.values[eq][0, j]
            arr[t] = float(win[eq].iloc[t]) - v
        out[eq] = arr
    return out


def _yoy(p: np.ndarray, t: int) -> float:
    return float(p[t - 3:t + 1].mean())


def decompose(w: World, origins: list[pd.Period]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (components, paths). components: one row per origin, horizon, measure with every component's contribution to (forecast - actual).
    paths: forecasts (tiers B, C, D, D with realised oil, AR4) and actuals for charts."""
    data = w.data
    last = w.ctx.last
    ms = standard_models(last)["B"]
    gE_act = data["grpe"] + data["gw"]
    gF_act = data["grpf"] + data["gw"]
    rows, prow = [], []
    for T0 in origins:
        h = min(H_MAX, (pd.Period(last, "Q") - T0).n)
        if h < 1:
            continue
        res = _fit_origin(ms, data, T0)
        cs = E.CoefSet.from_models([SimModel.from_results(res)])
        hist = _hist(data, T0)
        win = _window(data, T0, h, ("grpe", "grpf", "vu", "magpty", "shortagema2", "gcpi"))
        real = {k: win[k] for k in ("vu", "magpty", "shortagema2")}
        fut = pd.period_range(T0 + 1, periods=h, freq="Q")
        gE_hist, gF_hist = gE_act.loc[T0 - 3:T0].values, gF_act.loc[T0 - 3:T0].values
        gE_real, gF_real = np.r_[gE_hist, gE_act.loc[fut].values], np.r_[gF_hist, gF_act.loc[fut].values]
        # bridge
        end_m = T0.end_time.strftime("%Y-%m")
        mend = f"{end_m}-01"
        br = O.estimate_bridge(w.cpie_m.loc[:mend], w.oil_actual.loc[:mend], end=end_m)
        m0, m1 = (T0 + 1).start_time, (T0 + h).end_time.normalize().replace(day=1)
        months = pd.date_range(m0, m1, freq="MS")
        gE_c = np.r_[gE_hist, O.quarterly_energy_growth(O.monthly_energy_growth(br.point(), w.oil_actual.loc[:m1], str(m0.date()), str(m1.date())))[0]]
        oil_flat = pd.concat([w.oil_actual.loc[:mend], pd.Series(float(w.oil_actual.loc[mend]), index=months)])
        gE_d = np.r_[gE_hist, O.quarterly_energy_growth(O.monthly_energy_growth(br.point(), oil_flat, str(m0.date()), str(m1.date())))[0]]
        ue = unconditional_exog(data, T0, h)
        assumed = {k: ue[k] for k in ("vu", "magpty", "shortagema2")}
        nan = np.full(LAGS + h, np.nan)
        relf = nan.copy()
        relf[LAGS:] = 0.0
        # tier D (as in backtest.py) and its wage path = the nominal food path implied by 'food grows with wages'
        pD = _sim(cs, hist, assumed, gE_d, np.zeros(LAGS + h), {"grpf": relf})
        gF_D = pD["gw"][0].copy()
        gF_D[:LAGS] = gF_hist
        # stepwise switches from the all-realised bridge world (C)
        steps = {}
        cur = dict(exog=dict(real), gE=gE_c, gF=gF_real)
        path_prev = _sim(cs, hist, cur["exog"], cur["gE"], cur["gF"])
        pC = path_prev
        order = [("oil path", lambda c: c.update(gE=gE_d)), ("V/U", lambda c: c["exog"].update(vu=assumed["vu"])),
                 ("productivity", lambda c: c["exog"].update(magpty=assumed["magpty"])),
                 ("GSCPI", lambda c: c["exog"].update(shortagema2=assumed["shortagema2"])), ("food closure", lambda c: c.update(gF=gF_D))]
        for nm, fn in order:
            fn(cur)
            pn = _sim(cs, hist, cur["exog"], cur["gE"], cur["gF"])
            steps[nm] = pn["gcpi"][0] - path_prev["gcpi"][0]
            path_prev = pn
        assert np.allclose(path_prev["gcpi"][0], pD["gcpi"][0], atol=1e-8), "stepwise D does not reproduce tier D"
        # B: realised nominal energy and food
        pB = _sim(cs, hist, real, gE_real, gF_real)
        steps["oil bridge"] = pC["gcpi"][0] - pB["gcpi"][0]
        sh = actual_shocks(cs, data, T0, h)
        ar = np.r_[hist["gcpi"], ar4_forecast(data, T0, h)["gcpi"].values]
        act = np.r_[hist["gcpi"], data.loc[fut, "gcpi"].values]
        tot_shock = np.zeros(LAGS + h)
        for eq, nm in (("gcpi", "price eq. residuals"), ("gw", "wage eq. residuals"), ("cf1", "1y expectations residuals"), ("cf10", "10y expectations residuals")):
            pe = _sim(cs, hist, real, gE_real, gF_real, add={eq: sh[eq]})
            steps[nm] = -(pe["gcpi"][0] - pB["gcpi"][0])                      # contribution to (forecast - actual) = minus the response to the residual
        pall = _sim(cs, hist, real, gE_real, gF_real, add=sh)
        assert np.allclose(pall["gcpi"][0], act, atol=1e-6), f"B + residuals does not reproduce actual at {T0}"
        # one row per target quarter and horizon
        for k in range(1, h + 1):
            t = LAGS - 1 + k
            for measure, f in (("quarterly (ann.)", lambda p: float(p[t])), ("y/y (log approx.)", lambda p: _yoy(p, t) if t >= 3 else np.nan)):
                err = f(pD["gcpi"][0]) - f(act)
                row = {"origin": str(T0), "h": k, "target": str(fut[k - 1]), "measure": measure, "actual": f(act), "tier D": f(pD["gcpi"][0]),
                       "tier C (realised oil)": f(pC["gcpi"][0]), "tier B (realised energy)": f(pB["gcpi"][0]), "AR4": f(ar), "error D": err}
                for c in COMPONENTS:
                    row[c] = _meas(steps[c], t, measure)
                row["check (sum - error)"] = sum(row[c] for c in COMPONENTS) - err
                rows.append(row)
        for tier, p in (("actual", act), ("D", pD["gcpi"][0]), ("C", pC["gcpi"][0]), ("B", pB["gcpi"][0]), ("AR4", ar)):
            for k in range(0, h + 1):
                t = LAGS - 1 + k
                prow.append({"origin": str(T0), "tier": tier, "h": k, "target": str(T0 + k), "annualised": float(p[t]), "yoy": _yoy(p, t) if t >= 3 else np.nan})
    return pd.DataFrame(rows), pd.DataFrame(prow)


def _meas(diff: np.ndarray, t: int, measure: str) -> float:
    """A component is a difference of annualised-quarterly paths indexed on the (LAGS + h) grid; contributions to y/y are the mean of 4 of them.
    History quarters have zero difference by construction."""
    return float(diff[t]) if measure.startswith("quarterly") else float(diff[t - 3:t + 1].mean())
