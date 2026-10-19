"""Time-series robust inference for the restricted-LS equations, and structural-stability tests.

Nothing here changes the point estimates in rls.py; it only supplies alternative covariance matrices and tests.

HAC covariance. With beta_c = P beta_ols + const, P = I - A R'(R A R')^-1 R and A = (X'X)^-1,
    V_c = P [ A S A ] P',    S = Newey-West long-run variance of the scores x_t e_t (restricted residuals e_t),
Bartlett weights, truncation L (default 4 = one year of quarterly data), small-sample factor T/(T-k+q).
"""
from __future__ import annotations

import dataclasses
from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats

from .equations import EquationSpec
from .rls import EquationResult, design, estimate


def _xy(res: EquationResult, data: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    X = design(res.spec, data)[list(res.coef.index)]
    X = X.loc[res.sample[0]:res.sample[1]]
    return X.values, res.resid.values + res.fitted.values


def hac_cov(res: EquationResult, data: pd.DataFrame, L: int = 4, small_sample: bool = True) -> pd.DataFrame:
    X, _ = _xy(res, data)
    e = res.resid.values
    w = getattr(res, "weights", None)          # weighted (Model C) results: HAC of the sqrt(w)-transformed scores
    if w is not None:
        X, e = X * np.sqrt(w)[:, None], e * np.sqrt(w)
    T, k = X.shape
    names = list(res.coef.index)
    A = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    S = u.T @ u / T
    for l in range(1, L + 1):
        G = u[l:].T @ u[:-l] / T
        S += (1 - l / (L + 1)) * (G + G.T)
    V = T * A @ S @ A
    rn = res.spec.restriction_names()
    if rn:
        R = np.zeros((1, k))
        for n in rn:
            R[0, names.index(n)] = 1.0
        P = np.eye(k) - A @ R.T @ np.linalg.inv(R @ A @ R.T) @ R
        V = P @ V @ P.T
        q = 1
    else:
        q = 0
    if small_sample:
        V *= T / (T - k + q)
    return pd.DataFrame(V, index=names, columns=names)


def with_hac(res: EquationResult, data: pd.DataFrame, L: int = 4) -> EquationResult:
    """Copy of the result whose covariance (and hence every F-test) is Newey-West robust."""
    return dataclasses.replace(res, cov=hac_cov(res, data, L))


def coef_table(res: EquationResult, robust: EquationResult | None = None) -> pd.DataFrame:
    """Coefficients with classical and HAC standard errors and t-statistics."""
    out = pd.DataFrame({"beta": res.coef, "se_classic": np.sqrt(np.diag(res.cov))})
    out["t_classic"] = out.beta / out.se_classic
    if robust is not None:
        out["se_hac"] = np.sqrt(np.diag(robust.cov))
        out["t_hac"] = out.beta / out.se_hac
    return out


# ---------------------------------------------------------------------------------------------------
# Uncertainty bands for impulse responses
# ---------------------------------------------------------------------------------------------------
def _draw(beta: np.ndarray, V: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    w, U = np.linalg.eigh((V + V.T) / 2)
    w = np.clip(w, 0.0, None)                 # restricted covariance is singular along the restriction direction
    z = rng.standard_normal((n, len(beta)))
    return beta + (z * np.sqrt(w)) @ U.T


def irf_bands_mc(results: dict[str, EquationResult], irf_fn: Callable, shocks: dict[str, float],
                 n: int = 1000, seed: int = 0, quantiles=(0.05, 0.16, 0.5, 0.84, 0.95),
                 var: str = "gcpi_simul") -> dict[str, pd.DataFrame]:
    """Monte-Carlo bands: draw each equation's coefficients from N(beta, V) (V as stored in `results`, so pass
    HAC results for robust bands; draws satisfy the homogeneity restrictions exactly). Equations are drawn
    independently (cross-equation covariance is not estimated). irf_fn(coefs_by_eq, shock, size) -> DataFrame."""
    from ..simulation.model import SimModel
    rng = np.random.default_rng(seed)
    draws = {eq: _draw(r.coef.values, r.cov.values, n, rng) for eq, r in results.items()}
    out = {}
    for shock, size in shocks.items():
        paths = []
        for i in range(n):
            model = SimModel({eq: pd.Series(draws[eq][i], index=r.coef.index) for eq, r in results.items()})
            paths.append(irf_fn(model, shock, size)[var].values)
        arr = np.array(paths)
        out[shock] = pd.DataFrame(np.quantile(arr, quantiles, axis=0).T, columns=[f"q{int(q*100):02d}" for q in quantiles])
    return out


def irf_bands_bootstrap(equations: dict[str, EquationSpec], data: pd.DataFrame, results: dict[str, EquationResult],
                        irf_fn: Callable, shocks: dict[str, float], n: int = 500, block: int = 6, seed: int = 0,
                        start: str = "1990Q1", end: str = "2023Q2", quantiles=(0.05, 0.16, 0.5, 0.84, 0.95),
                        var: str = "gcpi_simul") -> dict[str, pd.DataFrame]:
    """Recursive-design moving-block bootstrap: resample (jointly across the four equations) blocks of the
    restricted-LS residuals, rebuild gw, gcpi, cf1, cf10 recursively from the actual initial conditions with
    exogenous variables as observed, re-estimate all equations, recompute the IRFs. Shock sizes stay fixed."""
    from ..simulation.model import ENDO, LAGS, SimModel
    from .rls import estimate_model
    rng = np.random.default_rng(seed)
    sample = pd.period_range(start, end, freq="Q")
    resid = pd.DataFrame({eq: results[eq].resid.reindex(sample) for eq in ("gw", "gcpi", "cf1", "cf10")}).dropna()
    resid = resid - resid.mean()
    T = len(resid)
    base = SimModel.from_results(results)
    first = sample[0]
    pos0 = data.index.get_loc(first)
    window = data.iloc[pos0 - LAGS: pos0 + T]
    exog_names = {"grpe", "grpf", "vu", "shortage", "magpty"} | {c for c in data.columns if c.startswith("shortage")}
    exog = {v: window[v].values.astype(float) for v in exog_names if v in window}
    dummies = {d: window[d].values.astype(float) for d in ("D2020Q2", "D2020Q3") if d in window}
    hist = {k: window[k].values[:LAGS].astype(float) for k in ENDO}
    nblocks = int(np.ceil(T / block))
    paths = {s: [] for s in shocks}
    ok = 0
    for b in range(n):
        starts = rng.integers(0, T - block + 1, nblocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:T]
        e = resid.values[idx]
        shock_arrays = {eq: np.concatenate([np.zeros(LAGS), e[:, j]]) for j, eq in enumerate(("gw", "gcpi", "cf1", "cf10"))}
        sim = base.simulate(hist, exog, dummies=dummies, add_shocks=shock_arrays)
        d2 = data.copy()
        for k in ENDO:
            d2.loc[window.index[LAGS:], k] = sim[k][LAGS:]
        try:
            res_b = estimate_model(d2, equations, {k: end for k in equations}, start)
            model_b = SimModel.from_results(res_b)
            for s, size in shocks.items():
                paths[s].append(irf_fn(model_b, s, size)[var].values)
            ok += 1
        except np.linalg.LinAlgError:
            continue
    out = {}
    for s in shocks:
        arr = np.array(paths[s])
        out[s] = pd.DataFrame(np.quantile(arr, quantiles, axis=0).T, columns=[f"q{int(q*100):02d}" for q in quantiles])
    out["_n_ok"] = pd.DataFrame({"n": [ok]})
    return out


def irf_draws_mc(results: dict[str, EquationResult], irf_fn: Callable, shock: str, size: float, n: int = 1000,
                 seed: int = 0, var: str = "gcpi_simul", rho: float | None = None) -> np.ndarray:
    """Raw Monte-Carlo IRF paths (n x horizon) for one shock, same draws as irf_bands_mc, so summary statistics
    (peak, timing, cumulative effect) can be computed draw by draw. irf_fn(model, shock, size, rho) -> DataFrame."""
    from ..simulation.model import SimModel
    rng = np.random.default_rng(seed)
    draws = {eq: _draw(r.coef.values, r.cov.values, n, rng) for eq, r in results.items()}
    paths = []
    for i in range(n):
        model = SimModel({eq: pd.Series(draws[eq][i], index=r.coef.index) for eq, r in results.items()})
        paths.append(irf_fn(model, shock, size, rho)[var].values)
    return np.array(paths)


# ---------------------------------------------------------------------------------------------------
# Structural stability
# ---------------------------------------------------------------------------------------------------
def _rls_core(y: np.ndarray, X: np.ndarray, R: np.ndarray | None, r: np.ndarray | None):
    """Restricted LS on matrices (pseudo-inverse, so rank-deficient designs are tolerated). Returns beta, RSS, rank."""
    A = np.linalg.pinv(X.T @ X)
    b = A @ X.T @ y
    if R is not None and len(R):
        M = R @ A @ R.T
        b = b - A @ R.T @ np.linalg.pinv(M) @ (R @ b - r)
    e = y - X @ b
    rank = np.linalg.matrix_rank(X)
    q = 0 if R is None else np.linalg.matrix_rank(R)
    return b, float(e @ e), rank - q


def chow_predictive(res_pre: EquationResult, data: pd.DataFrame, test_periods: list[pd.Period]) -> dict:
    """Chow (1960) predictive-failure test: does the pre-break equation forecast the test quarters within its
    error variance? F = ((RSS_full - RSS_pre)/n2) / (RSS_pre/(n1 - k_free)), RSS_full from re-estimating on
    pre + test quarters with the same restriction (no dummies)."""
    spec = res_pre.spec
    X = design(spec, data)[list(res_pre.coef.index)]
    y = data[spec.dep]
    names = list(res_pre.coef.index)
    rn = spec.restriction_names()
    R = np.zeros((1, len(names)))
    for n in rn:
        R[0, names.index(n)] = 1.0
    pre = pd.concat([y.rename("y"), X], axis=1).loc[res_pre.sample[0]:res_pre.sample[1]].dropna()
    tst = pd.concat([y.rename("y"), X], axis=1).loc[test_periods].dropna()
    full = pd.concat([pre, tst])
    _, rss_pre, kfree = _rls_core(pre["y"].values, pre.drop(columns="y").values, R, np.array([1.0]))
    _, rss_full, _ = _rls_core(full["y"].values, full.drop(columns="y").values, R, np.array([1.0]))
    n1, n2 = len(pre), len(tst)
    F = ((rss_full - rss_pre) / n2) / (rss_pre / (n1 - kfree))
    return {"F": F, "df1": n2, "df2": n1 - kfree, "p": float(stats.f.sf(F, n2, n1 - kfree)), "n_test": n2}


def _shift_design(X: np.ndarray, names: list[str], cols: list[str], tau: int):
    Z = np.zeros_like(X)
    idx = [names.index(c) for c in cols]
    Z[tau:, idx] = X[tau:, idx]
    keep = [i for i in idx]
    return np.hstack([X, Z[:, keep]]), keep


def sup_f_partial(res: EquationResult, data: pd.DataFrame, shift_cols: list[str], trim: float = 0.15,
                  nboot: int = 300, seed: int = 0, end: str | None = None) -> dict:
    """Quandt-Andrews sup-F for a break in a *subset* of coefficients (the full parameter vector has too many
    parameters for a 15%-trimmed sample). The shifted coefficients may change at an unknown date; shifts in
    columns that enter the homogeneity restriction must sum to zero. p-value: fixed-regressor Gaussian
    bootstrap under the no-break model (Hansen 2000)."""
    X, y = _xy(res, data)
    if end is not None:
        n = len(res.resid.loc[:end])
        X, y = X[:n], y[:n]
    names = list(res.coef.index)
    k = len(names)
    T = len(y)
    rn = res.spec.restriction_names()
    R0 = np.zeros((1, k))
    for n_ in rn:
        R0[0, names.index(n_)] = 1.0
    r0 = np.array([res.spec.restriction_value])
    in_restr = [c for c in shift_cols if c in rn]

    def build(tau):
        Xa, keep = _shift_design(X, names, shift_cols, tau)
        m = Xa.shape[1] - k
        R = np.zeros((1 + (1 if in_restr else 0), k + m))
        R[0, :k] = R0[0]
        r = [res.spec.restriction_value]
        if in_restr:
            for c in in_restr:
                R[1, k + shift_cols.index(c)] = 1.0
            r.append(0.0)
        return Xa, R, np.array(r), m

    lo, hi = int(np.floor(trim * T)), int(np.ceil((1 - trim) * T))
    taus = range(lo, hi)

    def supF(yv):
        _, rss0, k0 = _rls_core(yv, X, R0, r0)
        best, arg = -np.inf, None
        for tau in taus:
            Xa, R, r, m = build(tau)
            _, rss1, k1 = _rls_core(yv, Xa, R, r)
            F = ((rss0 - rss1) / (k1 - k0)) / (rss1 / (T - k1))
            if F > best:
                best, arg = F, tau
        return best, arg

    stat, tau_hat = supF(y)
    rng = np.random.default_rng(seed)
    b0, rss0, _ = _rls_core(y, X, R0, r0)
    sig = np.sqrt(rss0 / (T - np.linalg.matrix_rank(X) + 1))
    sims = np.array([supF(X @ b0 + sig * rng.standard_normal(T))[0] for _ in range(nboot)])
    return {"supF": stat, "break_after": str(res.sample[0] + int(tau_hat)), "p_boot": float((sims >= stat).mean()),
            "crit95": float(np.quantile(sims, 0.95)), "n_shift": len(shift_cols)}


def cusum_ols(res: EquationResult) -> dict:
    from statsmodels.stats.diagnostic import breaks_cusumolsresid
    k_free = len(res.coef) - (1 if res.spec.restriction_names() else 0)
    stat, p, _ = breaks_cusumolsresid(res.resid.values, ddof=k_free)
    return {"cusum_stat": float(stat), "p": float(p)}


def recursive_sums(spec: EquationSpec, data: pd.DataFrame, blocks: dict[str, list[str]], ends: list[str],
                   start: str = "1990Q1") -> pd.DataFrame:
    """Expanding-window sums of coefficients (rows = window end)."""
    rows = []
    for e in ends:
        try:
            r = estimate(spec, data, start, e)
        except np.linalg.LinAlgError:
            continue
        rows.append({"end": e, **{lab: float(r.coef[cols].sum()) for lab, cols in blocks.items()}})
    return pd.DataFrame(rows).set_index("end")
