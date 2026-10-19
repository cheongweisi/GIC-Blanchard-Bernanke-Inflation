"""Conditional forecast (cond_forecast.m) with the wage-constant correction (wage_constant.pdf).

Initial conditions are the last four observed quarters; from the fifth quarter the exogenous drivers
follow user-specified paths. The wage equation's constant is replaced by the value that makes the model's
steady state consistent with V/U = vu_star, magpty = magpty_star and shortage = shortage_star;
COVID dummies are zero.
"""
import numpy as np
import pandas as pd

from .model import ENDO, LAGS, SimModel


def wage_constant(model: SimModel, vu_star: float, magpty_star: float, shortage_star: float) -> float:
    """beta20* from wage_constant.pdf (grpe* = grpf* = 0, catch-up* = 0, cf1* = gcpi*)."""
    w, p = model.coefs["gw"], model.coefs["gcpi"]
    sum_w = lambda var: sum(w[f"{var}_L{k}"] for k in (1, 2, 3, 4))
    den_p = 1.0 - sum(p[f"gcpi_L{k}"] for k in (1, 2, 3, 4))
    short = sum(p[f"shortage_L{k}"] for k in range(5))
    one_minus_gw = 1.0 - sum_w("gw")
    return (-sum_w("vu") * vu_star
            - one_minus_gw * ((p["magpty_L0"] / den_p + w["magpty_L1"] / one_minus_gw) * magpty_star
                              + short / den_p * shortage_star + p["const"] / den_p))


def linear_path(start: float, target: float, quarters: int, n: int) -> np.ndarray:
    """Move linearly from `start` to `target` over `quarters`, then stay at target (n values)."""
    steps = np.arange(1, n + 1)
    return start + (target - start) * np.minimum(steps / quarters, 1.0)


def conditional_forecast(model: SimModel, hist: pd.DataFrame, exog_future: pd.DataFrame,
                         const_wage: float | None = None) -> pd.DataFrame:
    """Forecast from the last four rows of `hist` (columns: endogenous + exogenous variables).

    exog_future: DataFrame indexed by future quarters with columns grpe, grpf, vu, shortage, magpty.
    const_wage: replaces the wage-equation constant (None keeps the estimated constant).
    """
    h = hist.iloc[-LAGS:]
    idx = h.index.append(exog_future.index)
    exog = {v: np.concatenate([h[v].values, exog_future[v].values]).astype(float)
            for v in ("grpe", "grpf", "vu", "shortage", "magpty")}
    over = {"gw": const_wage} if const_wage is not None else None
    out = model.simulate({k: h[k].values.astype(float) for k in ENDO}, exog, const_override=over)
    df = pd.DataFrame({**out, **exog}, index=idx)
    return df
