"""Historical analysis through 2026: one-step fit, historical decompositions, and their comparison across models."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..simulation.general import decompose_general
from ..simulation.model import SimModel
from ..validation.specs import VARIANTS
from .models import ModelSpec

VARS = ("gcpi", "gw", "cf1", "cf10")
PERIODS = {"2020Q1-2023Q2": ("2020Q1", "2023Q2"), "2023Q3-last": ("2023Q3", "2099Q4")}
COMPONENTS = ("shortage", "grpe", "grpf", "vu", "magpty")
COMP_LABEL = {"shortage": "Supply chains (GSCPI)", "grpe": "Energy", "grpf": "Food", "vu": "Labour market (V/U)",
              "magpty": "Productivity"}


def fitted_one_step(res: dict, data_b: pd.DataFrame) -> pd.DataFrame:
    """One-step fitted values X*beta from actual lags (in-sample up to each model's estimation end, out-of-sample after)."""
    return pd.DataFrame({k: res[k].predict(data_b) for k in VARS})


def fit_errors(fitted: dict[str, pd.DataFrame], data: pd.DataFrame, ends: dict[str, str]) -> pd.DataFrame:
    rows = []
    for m, f in fitted.items():
        for v in VARS:
            for pname, (lo, hi) in PERIODS.items():
                e = (f[v] - data[v]).loc[lo:hi].dropna()
                rows.append({"model": m, "var": v, "period": pname, "RMSE": float(np.sqrt((e ** 2).mean())),
                             "MAE": float(e.abs().mean()), "bias": float(e.mean()), "n": len(e),
                             "in-sample?": "in-sample" if pd.Period(ends[m], "Q") >= pd.Period(hi.replace("2099Q4", "2026Q2"), "Q") else
                                           ("mixed" if pd.Period(ends[m], "Q") >= pd.Period(lo, "Q") else "out-of-sample")})
    return pd.DataFrame(rows)


def decompositions(res_by_model: dict[str, dict], specs: dict[str, ModelSpec], data_b: pd.DataFrame, steady_short: float) -> dict:
    out = {}
    for m, res in res_by_model.items():
        v = VARIANTS[specs[m].variant]
        dec = decompose_general(SimModel.from_results(res), data_b, v.derived_dict, steady={"shortage": steady_short})
        out[m] = dec
    return out


def contribution_table(decs: dict, data: pd.DataFrame, var: str, windows: dict[str, tuple[str, str]]) -> pd.DataFrame:
    """Average contributions (pp) over windows, incl. initial conditions, residual (actual - baseline) and actual."""
    rows = []
    for m, d in decs.items():
        idx = d.index
        act = data[var].reindex(idx)
        for wname, (lo, hi) in windows.items():
            sel = (idx >= pd.Period(lo, "Q")) & (idx <= pd.Period(hi, "Q"))
            r = {"model": m, "window": wname}
            for c in COMPONENTS:
                r[COMP_LABEL[c]] = float(d.contributions[c][var][sel].mean())
            dm = sum(d.contributions[c][var][sel].mean() for c in ("D2020Q2", "D2020Q3"))
            r["COVID dummies"] = float(dm)
            r["Initial conditions"] = float(d.runs["all"][var][sel].mean())
            r["Residual (actual - model)"] = float((act - d.baseline[var])[sel].mean())
            r["Model baseline"] = float(d.baseline[var][sel].mean())
            r["Actual"] = float(act[sel].mean())
            rows.append(r)
    return pd.DataFrame(rows)


def baseline_rmse(decs: dict, data: pd.DataFrame, lo: str = "2020Q1", hi: str = "2026Q2") -> pd.DataFrame:
    rows = []
    for m, d in decs.items():
        sel = (d.index >= pd.Period(lo, "Q")) & (d.index <= pd.Period(hi, "Q"))
        for v in VARS:
            e = (d.baseline[v] - data[v].reindex(d.index))[sel]
            rows.append({"model": m, "var": v, "dynamic baseline RMSE": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean())})
    return pd.DataFrame(rows)
