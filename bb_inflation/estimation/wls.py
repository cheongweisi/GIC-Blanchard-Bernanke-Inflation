"""Exponentially weighted restricted least squares (recent-weighted estimation, Model C).

Weight of quarter t in a sample ending at `end`:  w_t = 0.5 ** ((end - t) / H),  H = half-life in quarters,
normalised to mean one over the observations actually used. The authors' homogeneity restrictions are imposed
exactly as in rls.py (restricted LS on sqrt(w)-transformed data). `half_life_q=None` reproduces rls.estimate.

Reported residuals/fitted values/R2 are unweighted (actual - X beta); the covariance is the classical WLS one and
`inference.with_hac` gives the weighted Newey-West version (it reads `weights`).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .equations import EquationSpec
from .rls import EquationResult, design


@dataclass
class WeightedResult(EquationResult):
    weights: np.ndarray | None = None
    half_life_q: float | None = None


def exp_weights(periods: pd.PeriodIndex, end: pd.Period, half_life_q: float | None) -> np.ndarray:
    if half_life_q is None:
        return np.ones(len(periods))
    age = np.array([(end - p).n for p in periods], float)
    w = 0.5 ** (age / half_life_q)
    return w / w.mean()


def estimate_weighted(spec: EquationSpec, data: pd.DataFrame, start: str, end: str,
                      half_life_q: float | None) -> WeightedResult:
    X = design(spec, data)
    frame = pd.concat([data[spec.dep].rename("__y"), X], axis=1).loc[start:end].dropna()
    names = list(frame.columns[1:])
    yv, Xv = frame["__y"].values, frame.drop(columns="__y").values
    w = exp_weights(frame.index, pd.Period(end, "Q"), half_life_q)
    w = w / w.mean()
    sw = np.sqrt(w)
    ys, Xs = yv * sw, Xv * sw[:, None]
    A = np.linalg.inv(Xs.T @ Xs)
    b_ols = A @ Xs.T @ ys
    rn = spec.restriction_names()
    if rn:
        R = np.zeros((1, len(names)))
        for n in rn:
            R[0, names.index(n)] = 1.0
        K = A @ R.T @ np.linalg.inv(R @ A @ R.T)
        beta = b_ols - K @ (R @ b_ols - spec.restriction_value)
        q, Vcore = 1, A - K @ R @ A
    else:
        beta, q, Vcore = b_ols, 0, A
    e_s = ys - Xs @ beta
    n, k = Xs.shape
    df = n - k + q
    s2 = float(e_s @ e_s) / df
    fitted = pd.Series(Xv @ beta, index=frame.index)
    resid = pd.Series(yv - Xv @ beta, index=frame.index)
    r2 = float(np.corrcoef(yv, fitted)[0, 1] ** 2)
    return WeightedResult(
        spec=spec, coef=pd.Series(beta, index=names), cov=pd.DataFrame(s2 * Vcore, index=names, columns=names),
        fitted=fitted, resid=resid, nobs=n, df_resid=df, sigma2=s2, r2_corr=r2,
        sample=(frame.index[0], frame.index[-1]), weights=w, half_life_q=half_life_q)


def effective_sample_size(w: np.ndarray) -> float:
    """Kish effective sample size of the weights (how many equally weighted observations they are worth)."""
    return float(w.sum() ** 2 / (w ** 2).sum())
