"""Historical decomposition (decomp.m).

The model is simulated from actual initial conditions (first four quarters, 2018Q4-2019Q3) with all
exogenous inputs at their actual values (baseline) and, one at a time, with one input held at its
steady-state value from the fifth quarter (2019Q4) onward. Contribution = baseline - counterfactual.
Because the model is linear the contributions are additive; the remaining "initial conditions" piece is the
simulation with every input at steady state. Residuals are excluded, so the baseline differs from actual data.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .model import ENDO, LAGS, SimModel

# steady states used by the authors in decomp.m
STEADY = {"grpe": 0.0, "grpf": 0.0, "shortage": 5.0, "magpty": 2.0}
DECOMP_START = "2018Q4"
REMOVABLE = ("grpe", "grpf", "vu", "shortage", "magpty", "D2020Q2", "D2020Q3")


@dataclass
class Decomposition:
    index: pd.PeriodIndex
    baseline: pd.DataFrame
    runs: dict[str, pd.DataFrame] = field(default_factory=dict)       # counterfactual paths by removed set
    contributions: dict[str, pd.DataFrame] = field(default_factory=dict)  # baseline - counterfactual


def _run(model: SimModel, data: pd.DataFrame, remove: tuple[str, ...], steady: dict[str, float]):
    d = data.loc[DECOMP_START:]
    exog = {v: d[v].values.astype(float).copy() for v in ("grpe", "grpf", "vu", "shortage", "magpty")}
    dummies = {n: d[n].values.astype(float).copy() for n in ("D2020Q2", "D2020Q3")}
    for v in remove:
        if v in exog:
            val = d["vu"].values[LAGS] if v == "vu" else steady[v]
            exog[v][LAGS:] = val
        else:
            dummies[v][LAGS:] = 0.0
    hist = {k: d[k].values[:LAGS].astype(float) for k in ENDO}
    out = model.simulate(hist, exog, dummies=dummies)
    return pd.DataFrame(out, index=d.index)


def decompose(model: SimModel, data: pd.DataFrame, steady: dict[str, float] | None = None) -> Decomposition:
    steady = {**STEADY, **(steady or {})}
    base = _run(model, data, (), steady)
    dec = Decomposition(index=base.index, baseline=base)
    sets = {v: (v,) for v in REMOVABLE}
    sets["all"] = REMOVABLE
    for name, rem in sets.items():
        cf = _run(model, data, rem, steady)
        dec.runs[name] = cf
        dec.contributions[name] = base[["gw", "gcpi", "cf1", "cf10"]] - cf[["gw", "gcpi", "cf1", "cf10"]]
    return dec
