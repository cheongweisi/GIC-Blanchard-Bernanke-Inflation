"""What kind of statement is each forecast? A pseudo-out-of-sample ladder.

Four tiers, differing only in what the drivers are assumed to be. The model is re-estimated at every origin 2004Q4-2026Q1 on 1990Q1-origin
(unweighted, GSCPI 2-quarter mean, as Model B*), forecasts are 1-12 quarters, targets are the quarters to 2026Q2.

  A  conditional, realised relative prices   the Phase 3 'conditional forecast': realised relative energy / food growth, V/U, productivity,
                                             GSCPI (the relative prices contain the REALISED wage growth). Not a forecast of anything: it asks
                                             what the model says if told what the drivers did.
  B  conditional, realised nominal prices    realised nominal CPI energy and food growth; wages simulated, relative prices derived (the Phase 4
                                             closure). Isolates the effect of treating relative prices as endogenous.
  C  conditional, realised oil               realised Brent; CPI energy from the monthly bridge (estimated on data to the origin); realised nominal
                                             food. Adds the error of the oil -> CPI energy link.
  D  real-time-feasible baseline method      what Phase 4's baseline does with information available at the origin: Brent held at the origin month's
                                             level (the futures curve is not available historically), bridge, food with wages, V/U and productivity
                                             held, GSCPI AR(1). This is the only tier that is a genuine forecast of the kind the baseline is.
  F  Phase 3 'unconditional'                 relative energy and food growth zero (the authors' assumption), other drivers as in D.
  AR4  autoregression on each endogenous variable (benchmark).

Errors are forecast - actual. y/y = mean of the last four annualised quarterly values (log approximation) of the path including the
four actual history quarters.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..extension.models import ModelSpec, standard_models
from ..extension.pseudo_oos import _fit_origin, ar4_forecast, unconditional_exog
from ..simulation.model import SimModel
from . import engine as E
from . import oil as O
from .world import LAGS, World

H_MAX = 12
TIERS = ("A", "B", "C", "D", "F", "AR4")
BUCKETS = {"all targets": ("1990Q1", "2099Q4"), "targets to 2019Q4": ("1990Q1", "2019Q4"),
           "2020Q1-2023Q2": ("2020Q1", "2023Q2"), "2023Q3-2026Q2": ("2023Q3", "2026Q2")}


def _hist(data: pd.DataFrame, T0: pd.Period) -> dict[str, np.ndarray]:
    h = data.loc[T0 - 3:T0]
    return {k: h[k].values.astype(float) for k in ("gw", "gcpi", "cf1", "cf10", "diffcpicf", "grpe", "grpf")}


def _window(data: pd.DataFrame, T0: pd.Period, h: int, cols) -> dict[str, np.ndarray]:
    i = data.index.get_loc(T0)
    w = data.iloc[i - LAGS + 1: i + 1 + h]
    return {c: w[c].values.astype(float) for c in cols}


def _simulate(cs: E.CoefSet, hist, exog, gE, gF, rel=None) -> np.ndarray:
    inp = E.Inputs(hist=hist, exog=exog, gE=gE, gF=gF, rel_override=rel or {})
    return E.simulate(cs, inp)["gcpi"][0]


def _yoy(path: np.ndarray, k: int) -> float:
    return float(path[k - 3:k + 1].mean())


def origins(w: World, first: str = "2004Q4", last: str = "2026Q1") -> list[pd.Period]:
    return list(pd.period_range(first, last, freq="Q"))


def run(w: World, orig: list[pd.Period] | None = None) -> pd.DataFrame:
    data = w.data
    last = w.ctx.last
    ms = standard_models(last)["B"]
    gE_act = (data["grpe"] + data["gw"])
    gF_act = (data["grpf"] + data["gw"])
    rows = []
    for T0 in (orig or origins(w)):
        h = min(H_MAX, (pd.Period(last, "Q") - T0).n)
        if h < 1:
            continue
        res = _fit_origin(ms, data, T0)
        cs = E.CoefSet.from_models([SimModel.from_results(res)])
        hist = _hist(data, T0)
        win = _window(data, T0, h, ("grpe", "grpf", "vu", "magpty", "shortagema2", "gcpi"))
        exog_real = {k: win[k] for k in ("vu", "magpty", "shortagema2")}
        zeros = np.zeros(LAGS + h)
        gE_hist, gF_hist = gE_act.loc[T0 - 3:T0].values, gF_act.loc[T0 - 3:T0].values
        fut = pd.period_range(T0 + 1, periods=h, freq="Q")
        gE_real = np.r_[gE_hist, gE_act.loc[fut].values]
        gF_real = np.r_[gF_hist, gF_act.loc[fut].values]
        nan = np.full(LAGS + h, np.nan)
        paths: dict[str, np.ndarray] = {}
        # A
        paths["A"] = _simulate(cs, hist, exog_real, zeros, zeros, {"grpe": win["grpe"], "grpf": win["grpf"]})
        # B
        paths["B"] = _simulate(cs, hist, exog_real, gE_real, gF_real)
        # oil bridge to the origin
        end_m = T0.end_time.strftime("%Y-%m")
        mend = f"{end_m}-01"
        br = O.estimate_bridge(w.cpie_m.loc[:mend], w.oil_actual.loc[:mend], end=end_m)
        m0, m1 = (T0 + 1).start_time, (T0 + h).end_time.normalize().replace(day=1)
        months = pd.date_range(m0, m1, freq="MS")
        # C: realised oil
        oil_real = w.oil_actual.loc[:m1]
        gE_c = O.quarterly_energy_growth(O.monthly_energy_growth(br.point(), oil_real, str(m0.date()), str(m1.date())))[0]
        paths["C"] = _simulate(cs, hist, exog_real, np.r_[gE_hist, gE_c], gF_real)
        # D: real-time-feasible
        ue = unconditional_exog(data, T0, h)
        exog_d = {k: ue[k] for k in ("vu", "magpty", "shortagema2")}
        last_oil = float(w.oil_actual.loc[mend])
        oil_flat = pd.concat([w.oil_actual.loc[:mend], pd.Series(last_oil, index=months)])
        gE_d = O.quarterly_energy_growth(O.monthly_energy_growth(br.point(), oil_flat, str(m0.date()), str(m1.date())))[0]
        relf = nan.copy()
        relf[LAGS:] = 0.0
        paths["D"] = _simulate(cs, hist, exog_d, np.r_[gE_hist, gE_d], zeros, {"grpf": relf})
        # F: Phase 3 unconditional
        relz = {"grpe": np.r_[np.full(LAGS, np.nan), np.zeros(h)], "grpf": np.r_[np.full(LAGS, np.nan), np.zeros(h)]}
        paths["F"] = _simulate(cs, hist, exog_d, zeros, zeros, relz)
        ar = ar4_forecast(data, T0, h)["gcpi"].values
        paths["AR4"] = np.r_[hist["gcpi"], ar]
        act = np.r_[hist["gcpi"], data.loc[fut, "gcpi"].values]
        for tier, p in paths.items():
            for k in range(1, h + 1):
                t = LAGS - 1 + k
                tgt = fut[k - 1]
                if np.isnan(act[t]):
                    continue
                rows.append({"tier": tier, "origin": str(T0), "h": k, "target": str(tgt), "forecast": float(p[t]), "actual": float(act[t]),
                             "yoy_forecast": _yoy(p, t) if t >= 3 else np.nan, "yoy_actual": _yoy(act, t) if t >= 3 else np.nan})
    return pd.DataFrame(rows)


def summarize(rec: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rec = rec.copy()
    rec["err"] = rec["forecast"] - rec["actual"]
    rec["yerr"] = rec["yoy_forecast"] - rec["yoy_actual"]
    tgt = pd.PeriodIndex(rec["target"], freq="Q")
    hg = {"h1": (1, 1), "h2-4": (2, 4), "h5-8": (5, 8), "h9-12": (9, 12)}
    q, y = [], []
    for b, (lo, hi) in BUCKETS.items():
        sub = rec[(tgt >= pd.Period(lo, "Q")) & (tgt <= pd.Period(hi, "Q"))]
        for gname, (a, c) in hg.items():
            s = sub[(sub.h >= a) & (sub.h <= c)]
            for tier, g in s.groupby("tier"):
                q.append({"target period": b, "horizon": gname, "tier": tier, "RMSE (pp, annualised qtr.)": float(np.sqrt((g.err ** 2).mean())),
                          "bias": float(g.err.mean()), "n": len(g)})
        for hh in (4, 8, 12):
            s = sub[sub.h == hh]
            for tier, g in s.groupby("tier"):
                y.append({"target period": b, "horizon (quarters)": hh, "tier": tier, "RMSE of y/y (pp)": float(np.sqrt((g.yerr ** 2).mean())),
                          "bias of y/y": float(g.yerr.mean()), "n": len(g)})
    return pd.DataFrame(q), pd.DataFrame(y)
