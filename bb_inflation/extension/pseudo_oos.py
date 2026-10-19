"""Expanding-window pseudo-out-of-sample evaluation.

At every origin T0 the four equations are re-estimated on 1990Q1-T0 only (weights, if any, are relative to T0) and
forecasts are made for T0+1 ... T0+H from the four actual quarters ending at T0:
* conditional    exogenous drivers (grpe, grpf, V/U, GSCPI, productivity) as *realised*
* unconditional  exogenous drivers forecast from information at T0: relative energy/food growth = 0 (the authors'
                 own assumption), V/U and productivity held at their T0 value, GSCPI from an AR(1) fitted to GSCPI
                 through T0 (mean-reverting); the derived 2-quarter mean is rebuilt from that path
* AR(4)          an autoregression on each endogenous variable, an unconditional benchmark
The V/U observation for 2025Q4 is bridged (flagged) in simulation inputs only; estimation never uses it.
Errors are forecast - actual; the target quarter decides the period bucket.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..estimation.wls import WeightedResult
from ..simulation.model import ENDO, LAGS, SimModel
from .models import EQS, ModelSpec, fit

H_MAX = 12
VARS = ("gw", "gcpi", "cf1", "cf10")
BUCKETS = {"targets to 2019Q4": ("1990Q1", "2019Q4"), "2020Q1-2023Q2": ("2020Q1", "2023Q2"),
           "2023Q3-2026Q2": ("2023Q3", "2099Q4")}
HGROUPS = {"h1": (1, 1), "h2-4": (2, 4), "h5-8": (5, 8), "h9-12": (9, 12)}
DERIVED = {"shortagema2": ("shortage", 2), "shortagema4": ("shortage", 4)}


def _window(data: pd.DataFrame, origin: pd.Period, h: int) -> pd.DataFrame:
    i = data.index.get_loc(origin)
    return data.iloc[i - LAGS + 1: i + 1 + h]


def conditional_exog(data_b: pd.DataFrame, origin: pd.Period, h: int) -> dict[str, np.ndarray]:
    w = _window(data_b, origin, h)
    return {v: w[v].values.astype(float) for v in ("grpe", "grpf", "vu", "shortage", "magpty", *DERIVED)}


def _ar1(series: pd.Series) -> tuple[float, float]:
    y = series.values
    X = np.column_stack([np.ones(len(y) - 1), y[:-1]])
    c, rho = np.linalg.lstsq(X, y[1:], rcond=None)[0]
    return float(c), float(rho)


def unconditional_exog(data_b: pd.DataFrame, origin: pd.Period, h: int) -> dict[str, np.ndarray]:
    hist = data_b.loc[:origin]
    hist4 = hist.iloc[-LAGS:]
    out = {"grpe": np.concatenate([hist4["grpe"].values, np.zeros(h)]),
           "grpf": np.concatenate([hist4["grpf"].values, np.zeros(h)]),
           "vu": np.concatenate([hist4["vu"].values, np.repeat(hist4["vu"].values[-1], h)]),
           "magpty": np.concatenate([hist4["magpty"].values, np.repeat(hist4["magpty"].values[-1], h)])}
    sh = hist["shortage"].loc["1998Q1":]
    c, rho = _ar1(sh)
    path = list(hist["shortage"].values[-8:])
    for _ in range(h):
        path.append(c + rho * path[-1])
    out["shortage"] = np.array(path[-(LAGS + h):])
    full = pd.Series(path)
    for name, (src, win) in DERIVED.items():
        out[name] = full.rolling(win, min_periods=win).mean().values[-(LAGS + h):]
    return out


def _forecast(model: SimModel, data: pd.DataFrame, origin: pd.Period, h: int, exog: dict) -> pd.DataFrame:
    w = _window(data, origin, 0)
    hist = {k: w[k].values.astype(float) for k in ENDO}
    out = model.simulate(hist, exog)
    idx = pd.period_range(origin + 1, periods=h, freq="Q")
    return pd.DataFrame({k: out[k][LAGS:] for k in VARS}, index=idx)


def ar4_forecast(data: pd.DataFrame, origin: pd.Period, h: int) -> pd.DataFrame:
    idx = pd.period_range(origin + 1, periods=h, freq="Q")
    out = {}
    for k in VARS:
        s = data[k]
        X = pd.concat([s.shift(i) for i in range(1, 5)], axis=1)
        X.columns = [f"l{i}" for i in range(1, 5)]
        X["c"] = 1.0
        fr = pd.concat([s.rename("y"), X], axis=1).loc["1990Q1":origin].dropna()
        b = np.linalg.lstsq(fr.drop(columns="y").values, fr["y"].values, rcond=None)[0]
        path = list(s.loc[:origin].iloc[-4:].values)
        f = []
        for _ in range(h):
            nxt = b[4] + sum(b[i] * path[-1 - i] for i in range(4))
            path.append(nxt)
            f.append(nxt)
        out[k] = f
    return pd.DataFrame(out, index=idx)


def run(data: pd.DataFrame, data_b: pd.DataFrame, last_complete: str, configs: dict[str, ModelSpec],
        origins: list[pd.Period], frozen: dict[str, dict[str, WeightedResult]] | None = None,
        include_ar4: bool = True) -> pd.DataFrame:
    """Long DataFrame of forecasts and actuals. `frozen` maps a config name to fixed estimates (Model A)."""
    last = pd.Period(last_complete, "Q")
    rows = []
    for T0 in origins:
        h = min(H_MAX, (last - T0).n)
        if h < 1:
            continue
        cond, unc = None, None
        for name, ms in configs.items():
            if frozen and name in frozen:
                res = frozen[name]
            else:
                res = _fit_origin(ms, data, T0)
            model = SimModel.from_results(res)
            for mode, ex in (("conditional", conditional_exog(data_b, T0, h)), ("unconditional", unconditional_exog(data_b, T0, h))):
                fc = _forecast(model, data, T0, h, ex)
                rows += _records(fc, data, T0, name, mode)
        if include_ar4:
            rows += _records(ar4_forecast(data, T0, h), data, T0, "AR4", "unconditional")
    return pd.DataFrame(rows)


def _fit_origin(ms: ModelSpec, data: pd.DataFrame, T0: pd.Period):
    import dataclasses
    return fit(dataclasses.replace(ms, end=str(T0)), data, str(T0))


def _records(fc: pd.DataFrame, data: pd.DataFrame, T0: pd.Period, name: str, mode: str) -> list[dict]:
    rows = []
    for k, tgt in enumerate(fc.index, start=1):
        for v in VARS:
            a = data.at[tgt, v]
            if np.isnan(a):
                continue
            rows.append({"model": name, "mode": mode, "origin": str(T0), "h": k, "target": str(tgt), "var": v,
                         "forecast": float(fc.at[tgt, v]), "actual": float(a)})
    return rows


def summarize(rec: pd.DataFrame, by_bucket: bool = True) -> pd.DataFrame:
    rec = rec.copy()
    rec["err"] = rec["forecast"] - rec["actual"]
    tgt = pd.PeriodIndex(rec["target"], freq="Q")
    rec["bucket"] = "all targets"
    out = []
    parts = [("all targets", np.ones(len(rec), bool))]
    if by_bucket:
        parts += [(b, (tgt >= pd.Period(lo, "Q")) & (tgt <= pd.Period(hi, "Q"))) for b, (lo, hi) in BUCKETS.items()]
    for bname, mask in parts:
        sub = rec[mask]
        for hname, (lo, hi) in HGROUPS.items():
            s2 = sub[(sub.h >= lo) & (sub.h <= hi)]
            g = s2.groupby(["model", "mode", "var"])["err"]
            t = pd.DataFrame({"RMSE": g.apply(lambda e: float(np.sqrt((e ** 2).mean()))), "MAE": g.apply(lambda e: float(e.abs().mean())),
                              "bias": g.mean(), "n": g.size()}).reset_index()
            t["target bucket"], t["horizon"] = bname, hname
            out.append(t)
    return pd.concat(out, ignore_index=True)


def select_half_life(summary: pd.DataFrame, candidates: list[str], baseline: str, var: str = "gcpi",
                     mode: str = "conditional", tie: float = 0.03) -> dict:
    """Pre-specified rule: lowest mean RMSE of `var` over horizons 1-12 groups (equal weight on h1, h2-4, h5-8, h9-12)
    across all pseudo-OOS targets. A candidate must beat the unweighted `baseline` by more than `tie` (3%) to be
    preferred; otherwise the baseline is kept. Uses forecast errors only, never in-sample fit."""
    s = summary[(summary["target bucket"] == "all targets") & (summary["var"] == var) & (summary["mode"] == mode)]
    score = s.groupby("model")["RMSE"].mean()
    best = min(candidates, key=lambda m: score[m])
    chosen = best if score[best] < score[baseline] * (1 - tie) else baseline
    return {"scores": score.to_dict(), "best_candidate": best, "chosen": chosen}
