"""Impulse responses from an all-zero steady state (irf_simulations.m).

Variables are deviations from steady state, so constants and dummies are dropped. A one-s.d. shock hits
at the fifth quarter of a 32-quarter window. Exogenous shocks follow x_t = rho * x_{t-1} + shock_t
(rho = 0: a one-off change in the *rate*; rho = 1: a permanent level shift, used for V/U).
"""
import numpy as np
import pandas as pd

from .model import ENDO, LAGS, SimModel

EXOG = ("grpe", "grpf", "vu", "shortage")
EQ_SHOCKS = ("gw", "gcpi", "cf1", "cf10")
HORIZON = 32
SHOCK_T = LAGS            # 0-based index of the fifth quarter


def shock_sizes(data: pd.DataFrame, residuals: dict[str, pd.Series], since: str = "2020Q1") -> dict[str, float]:
    """One standard deviation (sample, ddof=1) of the exogenous variables and equation residuals
    from `since` onward, as in the MATLAB code (std omitting NaN)."""
    sz = {v: float(data.loc[since:, v].std(ddof=1)) for v in EXOG}
    for eq in EQ_SHOCKS:
        sz[eq] = float(residuals[eq].loc[since:].std(ddof=1))
    return sz


def irf(model: SimModel, shock: str, size: float, rho: float | None = None,
        horizon: int = HORIZON) -> pd.DataFrame:
    """Response to a shock to one exogenous variable or one equation residual."""
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
    out = model.simulate({k: np.zeros(LAGS) for k in ENDO}, exog, use_const=False, add_shocks=add)
    df = pd.DataFrame({f"{k}_simul": out[k] for k in ("gw", "gcpi", "cf1", "cf10", "diffcpicf")})
    for v in EXOG:
        df[f"{v}_shock_series"] = exog[v]
    df.index = np.arange(1, horizon + 1)
    df.index.name = "period"
    return df
