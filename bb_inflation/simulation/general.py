"""IRFs and historical decompositions that also work when an equation uses a *derived* exogenous regressor
(e.g. a moving average of the shortage index). Same dynamics, shocks, steady states and removal logic as
irf.py / decomposition.py (which are left untouched); with `derived={}` the results coincide with them.

derived: {derived column: (source column, window)}  -> trailing mean of the source over `window` quarters.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .decomposition import DECOMP_START, REMOVABLE, STEADY, Decomposition
from .irf import EXOG, HORIZON, SHOCK_T
from .model import ENDO, LAGS, SimModel

Derived = dict[str, tuple[str, int]]


def add_derived(data: pd.DataFrame, derived: Derived) -> pd.DataFrame:
    out = data.copy()
    for name, (src, w) in derived.items():
        out[name] = out[src].rolling(w, min_periods=w).mean()
    return out


def _trail_mean(x: np.ndarray, w: int) -> np.ndarray:
    return pd.Series(x).rolling(w, min_periods=1).mean().values


def irf_general(model: SimModel, shock: str, size: float, derived: Derived | None = None, rho: float | None = None,
                horizon: int = HORIZON) -> pd.DataFrame:
    derived = derived or {}
    default_rho = {"grpe": 0.0, "grpf": 0.0, "vu": 1.0, "shortage": 0.0}
    rho = default_rho.get(shock, 0.0) if rho is None else rho
    zeros = np.zeros(horizon)
    exog = {v: zeros.copy() for v in (*EXOG, "magpty")}
    add = None
    if shock in EXOG:
        x = exog[shock]
        for t in range(LAGS, horizon):
            x[t] = rho * x[t - 1] + (size if t == SHOCK_T else 0.0)
    else:
        e = zeros.copy()
        e[SHOCK_T] = size
        add = {shock: e}
    for name, (src, w) in derived.items():
        exog[name] = _trail_mean(exog[src], w)
    out = model.simulate({k: np.zeros(LAGS) for k in ENDO}, exog, use_const=False, add_shocks=add)
    df = pd.DataFrame({f"{k}_simul": out[k] for k in ("gw", "gcpi", "cf1", "cf10", "diffcpicf")})
    df.index = np.arange(1, horizon + 1)
    df.index.name = "period"
    return df


def _run(model: SimModel, data: pd.DataFrame, remove: tuple[str, ...], steady: dict, derived: Derived) -> pd.DataFrame:
    d = data.copy()
    t0 = d.index.get_loc(pd.Period(DECOMP_START, "Q")) + LAGS
    for v in remove:
        if v in ("grpe", "grpf", "shortage", "magpty"):
            d.iloc[t0:, d.columns.get_loc(v)] = steady[v]
        elif v == "vu":
            d.iloc[t0:, d.columns.get_loc("vu")] = d["vu"].iloc[t0]
        else:
            d.iloc[t0:, d.columns.get_loc(v)] = 0.0       # COVID dummies
    d = add_derived(d, derived)
    w = d.loc[DECOMP_START:]
    exog_names = ["grpe", "grpf", "vu", "shortage", "magpty", *derived]
    exog = {v: w[v].values.astype(float) for v in exog_names}
    dummies = {n: w[n].values.astype(float) for n in ("D2020Q2", "D2020Q3")}
    hist = {k: w[k].values[:LAGS].astype(float) for k in ENDO}
    return pd.DataFrame(model.simulate(hist, exog, dummies=dummies), index=w.index)


def decompose_general(model: SimModel, data: pd.DataFrame, derived: Derived | None = None,
                      steady: dict | None = None) -> Decomposition:
    derived = derived or {}
    steady = {**STEADY, **(steady or {})}
    data = add_derived(data, derived)
    base = _run(model, data, (), steady, derived)
    dec = Decomposition(index=base.index, baseline=base)
    sets = {v: (v,) for v in REMOVABLE}
    sets["all"] = REMOVABLE
    for name, rem in sets.items():
        cf = _run(model, data, rem, steady, derived)
        dec.runs[name] = cf
        dec.contributions[name] = base[["gw", "gcpi", "cf1", "cf10"]] - cf[["gw", "gcpi", "cf1", "cf10"]]
    return dec
