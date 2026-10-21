"""Forecast evaluation for Phase 5: errors, benchmarks, windows, and an exact additive error decomposition.

Conventions. Error = forecast - realised. The target is CPI-U inflation, quarter-end SA index, quarterly annualised (400*dln), the model's own
variable; y/y inflation = 100*(CPI_t/CPI_(t-4) - 1), built for EVERY method from the forecast quarterly path chained on the current-vintage history.
One forecast origin (2023Q2) means one forecast per horizon: "4-, 8- and 12-quarter horizons" are therefore reported as (i) statistics over the
first 4 / 8 / 12 forecast quarters (RMSE, MAE, mean error) and (ii) the single y/y error at horizon exactly 4, 8 and 12.

Decomposition (exact, because the model is linear in the inputs and the equation shocks):
    error_A = (A - B) + (B - realised)
    A - B   : external assumptions. Shapley value of each of five drivers (energy [oil/CPI energy], food, GSCPI, V/U, productivity) over the 2^5
              coalitions in which a driver takes its realised path (Exercise B input) or its Exercise-A default.
    B - real: deficiencies of the estimated relationships given the true drivers. Equals minus the sum of the effects of the realised one-step
              equation residuals (wage, CPI, 10y, 1y expectations equations), because feeding every realised residual into Exercise B
              reproduces the realised path exactly (checked).
"""
from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "phase5"))
import p5_forecast_engine as eng  # noqa: E402

DRIVERS = {"energy (oil / CPI energy)": ["brent", "cpie_qoq"], "food": ["cpif_qoq"], "supply chains (GSCPI)": ["gscpi"],
           "labour market (V/U)": ["vu"], "productivity": ["prod_qoq"]}
WINDOWS = (4, 8, 12)


def realised_paths(levels: pd.DataFrame, quarters: pd.PeriodIndex) -> pd.DataFrame:
    g = 400.0 * np.log(levels["cpi"]).diff()
    yy = 100.0 * (levels["cpi"] / levels["cpi"].shift(4) - 1.0)
    return pd.DataFrame({"gcpi": g.reindex(quarters), "yoy": yy.reindex(quarters)})


def yoy_from_gcpi(g_hist: pd.Series, g_fc: pd.Series) -> pd.Series:
    """y/y inflation from quarterly annualised inflation: 100*(exp(sum of the last four quarterly log changes) - 1)."""
    g = pd.concat([g_hist, g_fc])
    s = (g / 400.0).rolling(4).sum()
    return (100.0 * (np.exp(s) - 1.0)).reindex(g_fc.index)


def window_metrics(err: pd.Series, windows=WINDOWS) -> pd.DataFrame:
    rows = []
    for h in windows:
        e = err.iloc[:h]
        rows.append({"window (first h quarters)": h, "n": len(e), "ME": e.mean(), "MAE": e.abs().mean(), "RMSE": float(np.sqrt((e ** 2).mean()))})
    return pd.DataFrame(rows)


def build_tables(methods: dict[str, pd.Series], real: pd.DataFrame, g_hist: pd.Series) -> dict[str, pd.DataFrame]:
    """methods: name -> quarterly annualised forecast of CPI inflation (index = the forecast quarters)."""
    q = real.index
    fc_g = pd.DataFrame({m: s.reindex(q) for m, s in methods.items()})
    fc_y = pd.DataFrame({m: yoy_from_gcpi(g_hist, s.reindex(q)) for m, s in methods.items()})
    err_g = fc_g.sub(real["gcpi"], axis=0)
    err_y = fc_y.sub(real["yoy"], axis=0)
    mt = []
    for m in methods:
        for label, e, unit in (("CPI inflation q/q annualised", err_g[m], "pp"), ("CPI inflation y/y", err_y[m], "pp")):
            w = window_metrics(e)
            w.insert(0, "measure", label)
            w.insert(0, "method", m)
            mt.append(w)
    metrics = pd.concat(mt, ignore_index=True)
    # relative RMSE vs benchmarks
    for b in ("AR(1)", "AR(4)"):
        if b in methods:
            base = metrics[metrics.method == b].set_index(["measure", "window (first h quarters)"])["RMSE"]
            metrics[f"RMSE / RMSE {b}"] = [row["RMSE"] / base[(row["measure"], row["window (first h quarters)"])] for _, row in metrics.iterrows()]
    # horizon-specific y/y and q/q errors at h = 4, 8, 12 (single observation each)
    hz = []
    for h in WINDOWS:
        for m in methods:
            hz.append({"horizon h": h, "target quarter": str(q[h - 1]), "method": m, "q/q forecast": fc_g[m].iloc[h - 1], "q/q realised": real["gcpi"].iloc[h - 1],
                       "q/q error": err_g[m].iloc[h - 1], "y/y forecast": fc_y[m].iloc[h - 1], "y/y realised": real["yoy"].iloc[h - 1],
                       "y/y error": err_y[m].iloc[h - 1]})
    # average inflation over the window (= annualised price-level drift): forecast mean - realised mean
    av = []
    for h in WINDOWS:
        for m in methods:
            av.append({"window h": h, "method": m, "mean forecast infl. (q/q ann.)": fc_g[m].iloc[:h].mean(),
                       "mean realised": real["gcpi"].iloc[:h].mean(), "error (pp, annualised price-level drift)": err_g[m].iloc[:h].mean(),
                       "cumulative price-level error (%)": err_g[m].iloc[:h].sum() / 4.0})
    return {"forecasts_qoq": fc_g, "forecasts_yoy": fc_y, "errors_qoq": err_g, "errors_yoy": err_y, "metrics": metrics,
            "horizon_errors": pd.DataFrame(hz), "window_average": pd.DataFrame(av)}


# ---------------------------------------------------------------------------------------------------------------------
# Decomposition
# ---------------------------------------------------------------------------------------------------------------------
def shapley_drivers(wd, coefs, in_a: pd.DataFrame, in_b: pd.DataFrame, horizon: str) -> tuple[pd.DataFrame, dict]:
    """Shapley decomposition of gcpi(B) - gcpi(A) by driver. Returns (per-quarter contributions, {coalition: path})."""
    names = list(DRIVERS)
    n = len(names)
    cache: dict[frozenset, pd.Series] = {}

    def run(S: frozenset) -> pd.Series:
        if S in cache:
            return cache[S]
        df = in_a.copy()
        for nm in S:
            for col in DRIVERS[nm]:
                df[col] = in_b[col]
        r = eng.run_scenario(wd, "A", coefs=coefs, horizon=horizon, inputs_override=df)
        cache[S] = r.forecast["gcpi"]
        return cache[S]

    q = run(frozenset()).index
    contrib = {nm: pd.Series(0.0, index=q) for nm in names}
    for nm in names:
        others = [x for x in names if x != nm]
        for k in range(n):
            w = math.factorial(k) * math.factorial(n - k - 1) / math.factorial(n)
            for S in itertools.combinations(others, k):
                S = frozenset(S)
                contrib[nm] = contrib[nm] + w * (run(S | {nm}) - run(S))
    out = pd.DataFrame(contrib)
    out["total (B - A)"] = run(frozenset(names)) - run(frozenset())
    return out, cache


def residual_decomposition(wd, coefs, in_b: pd.DataFrame, horizon: str, resid: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Effect on gcpi of each equation's realised one-step residual, running Exercise B inputs. Returns (contributions, max |all-residual run - realised|)."""
    base = eng.run_scenario(wd, "B", coefs=coefs, horizon=horizon, inputs_override=in_b).forecast["gcpi"]
    q = base.index
    out = {}
    for e in ("gw", "gcpi", "cf10", "cf1"):
        r = eng.run_scenario(wd, "B", coefs=coefs, horizon=horizon, inputs_override=in_b,
                             extra_add={e: resid[e].reindex(q).values}).forecast["gcpi"]
        out[e] = r - base
    allr = eng.run_scenario(wd, "B", coefs=coefs, horizon=horizon, inputs_override=in_b,
                            extra_add={e: resid[e].reindex(q).values for e in ("gw", "gcpi", "cf10", "cf1")})
    df = pd.DataFrame(out)
    df["all four residuals (= realised - B)"] = allr.forecast["gcpi"] - base
    return df, base, allr.forecast


def one_step_residuals(res23: dict, data: pd.DataFrame, quarters: pd.PeriodIndex) -> pd.DataFrame:
    """Realised one-step residuals of the 2023Q2 equations over the out-of-sample quarters (actual - X*beta, with the realised regressors)."""
    out = {}
    for eq, r in res23.items():
        fit = r.predict(data)
        out[eq] = (data[eq] - fit).reindex(quarters)
    return pd.DataFrame(out)
