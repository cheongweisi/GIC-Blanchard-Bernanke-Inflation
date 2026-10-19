"""Restricted least squares (equivalent to Stata `cnsreg`) with F-tests.

beta_c = b_ols - (X'X)^-1 R' [R (X'X)^-1 R']^-1 (R b_ols - r)
Var(beta_c) = s^2 [ A - A R' (R A R')^-1 R A ],  A = (X'X)^-1,  s^2 = RSS / (N - k + q)
F-tests use the constrained covariance with residual df = N - k + q (Stata convention).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .equations import EquationSpec


@dataclass
class EquationResult:
    spec: EquationSpec
    coef: pd.Series
    cov: pd.DataFrame
    fitted: pd.Series          # over the estimation sample
    resid: pd.Series
    nobs: int
    df_resid: int
    sigma2: float
    r2_corr: float             # squared corr(actual, fitted), authors' R2 definition
    sample: tuple[pd.Period, pd.Period]

    def predict(self, data: pd.DataFrame) -> pd.Series:
        """One-step-ahead fitted values X*beta wherever the regressors exist (Stata `predict` after cnsreg),
        including out-of-sample quarters."""
        X = design(self.spec, data)[list(self.coef.index)].dropna()
        return pd.Series(X.values @ self.coef.values, index=X.index)

    # ---- hypothesis tests ------------------------------------------------------------------
    def _f_test(self, R: np.ndarray, r: np.ndarray) -> float:
        b = self.coef.values
        V = self.cov.values
        d = R @ b - r
        M = R @ V @ R.T
        m = np.linalg.matrix_rank(M, tol=1e-12 * max(1.0, np.abs(M).max()))
        F = float(d @ np.linalg.pinv(M) @ d) / m
        return float(stats.f.sf(F, m, self.df_resid))

    def _selector(self, names: list[str]) -> np.ndarray:
        idx = [self.coef.index.get_loc(n) for n in names]
        R = np.zeros((len(idx), len(self.coef)))
        for i, j in enumerate(idx):
            R[i, j] = 1.0
        return R

    def block_names(self, var: str) -> list[str]:
        for b in self.spec.blocks:
            if b.var == var:
                return b.names()
        raise KeyError(var)

    def sum_and_pvalues(self, var: str) -> dict:
        names = self.block_names(var)
        R = self._selector(names)
        out = {"sum": float(self.coef[names].sum()),
               "p_joint": self._f_test(R, np.zeros(len(names)))}
        out["p_sum"] = (self._f_test(R.sum(axis=0, keepdims=True), np.zeros(1))
                        if len(names) > 1 else np.nan)
        return out

    def summary(self) -> pd.DataFrame:
        rows = {v: self.sum_and_pvalues(v) for v in self.spec.summary_blocks}
        return pd.DataFrame(rows).T[["sum", "p_sum", "p_joint"]]


def design(spec: EquationSpec, data: pd.DataFrame) -> pd.DataFrame:
    """Regressor matrix on the full series (lags built before any sample selection)."""
    X = pd.DataFrame(index=data.index)
    for b in spec.blocks:
        for k in b.lags:
            X[f"{b.var}_L{k}"] = data[b.var].shift(k)
    for dname in spec.dummies:
        X[dname] = data[dname]
    if spec.constant:
        X["const"] = 1.0
    return X


def estimate(spec: EquationSpec, data: pd.DataFrame, start: str, end: str) -> EquationResult:
    """Estimate one equation by restricted OLS over [start, end]; lags are built on the full series."""
    X = design(spec, data)
    y = data[spec.dep]
    frame = pd.concat([y.rename("__y"), X], axis=1).loc[start:end].dropna()
    yv = frame["__y"].values
    Xv = frame.drop(columns="__y").values
    names = list(frame.columns[1:])

    A = np.linalg.inv(Xv.T @ Xv)
    b_ols = A @ Xv.T @ yv
    rn = spec.restriction_names()
    if rn:
        R = np.zeros((1, len(names)))
        for n in rn:
            R[0, names.index(n)] = 1.0
        r = np.array([spec.restriction_value])
        K = A @ R.T @ np.linalg.inv(R @ A @ R.T)
        beta = b_ols - K @ (R @ b_ols - r)
        q = R.shape[0]
        Vcore = A - K @ R @ A
    else:
        beta, q, Vcore = b_ols, 0, A
    resid = yv - Xv @ beta
    n, k = Xv.shape
    df = n - k + q
    s2 = float(resid @ resid) / df
    fitted = pd.Series(Xv @ beta, index=frame.index)
    actual = pd.Series(yv, index=frame.index)
    # authors' R2: squared correlation of actual and fitted from 1990Q1 (sample already starts there)
    r2 = float(np.corrcoef(actual, fitted)[0, 1] ** 2)
    return EquationResult(
        spec=spec,
        coef=pd.Series(beta, index=names),
        cov=pd.DataFrame(s2 * Vcore, index=names, columns=names),
        fitted=fitted, resid=pd.Series(resid, index=frame.index),
        nobs=n, df_resid=df, sigma2=s2, r2_corr=r2,
        sample=(frame.index[0], frame.index[-1]),
    )


def estimate_model(data: pd.DataFrame, equations: dict[str, EquationSpec],
                   ends: dict[str, str], start: str = "1990Q1") -> dict[str, EquationResult]:
    return {k: estimate(spec, data, start, ends[k]) for k, spec in equations.items()}
