"""Joint (stacked) inference for estimators fitted on nested, overlapping samples.

Estimates for 1990Q1-2019Q4, -2023Q4 and -2026Q2 share most of their data, so their sampling errors are strongly correlated and the
usual 'difference of two independent estimates' is wrong. For restricted least squares
        b_c - beta ~= P A sum_t x_t u_t ,     A = (X'X)^-1,   P = I - A R' (R A R')^-1 R,
so each estimator has an influence vector  psi_t = P A x_t e_t  (restricted residual e_t, zero outside its own sample). Stacking the
influence vectors of every vintage and taking a Newey-West (Bartlett, 4 lags) long-run covariance gives the joint covariance of all
estimates. Its diagonal blocks equal `estimation.inference.hac_cov` (small-sample factor T/(T-k+q) included; tested), and the off-diagonal
blocks carry the overlap. Uses: overlap-adjusted tests of changes in any linear combination (e.g. a sum of lag coefficients), and
joint coefficient draws that keep the three vintages' sampling errors correlated, so IRF differences across vintages get honest bands.

First-order asymptotic approximation; with 120-146 quarterly observations and 20+ coefficients the HAC covariance is itself noisy
(Phase 4b: HAC and bootstrap parameter bands within 0.9-1.22x), and the stacked version inherits that. Equations are treated as independent.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from ..estimation.equations import EquationSpec
from ..estimation.rls import EquationResult, design


def influence(res: EquationResult, data: pd.DataFrame, cols: list[str], index: pd.PeriodIndex) -> np.ndarray:
    """(len(index) x len(cols)) influence vectors of the restricted-LS coefficients, zero outside the estimation sample / for absent columns."""
    names = list(res.coef.index)
    X = design(res.spec, data)[names].loc[res.resid.index].values
    e = res.resid.values
    T, k = X.shape
    A = np.linalg.inv(X.T @ X)
    rn = res.spec.restriction_names()
    if rn:
        R = np.zeros((1, k))
        for n in rn:
            R[0, names.index(n)] = 1.0
        P = np.eye(k) - A @ R.T @ np.linalg.inv(R @ A @ R.T) @ R
        q = 1
    else:
        P, q = np.eye(k), 0
    psi = (X * e[:, None]) @ A @ P.T * np.sqrt(T / (T - k + q))
    out = np.zeros((len(index), len(cols)))
    pos = index.get_indexer(res.resid.index)
    for j, n in enumerate(names):
        out[pos, cols.index(n)] = psi[:, j]
    return out


def newey_west(psi: np.ndarray, L: int = 4) -> np.ndarray:
    V = psi.T @ psi
    for l in range(1, L + 1):
        G = psi[l:].T @ psi[:-l]
        V += (1 - l / (L + 1)) * (G + G.T)
    return V


@dataclass
class Stacked:
    eq: str
    keys: list[str]
    cols: list[str]
    beta: dict[str, np.ndarray]
    cov: np.ndarray
    df: dict[str, int]
    spec: EquationSpec

    @property
    def k(self) -> int:
        return len(self.cols)

    def slc(self, key: str) -> slice:
        i = self.keys.index(key)
        return slice(i * self.k, (i + 1) * self.k)

    def block_cov(self, a: str, b: str) -> np.ndarray:
        return self.cov[self.slc(a), self.slc(b)]

    def selector(self, block: str | list[str] | None = None, names: list[str] | None = None) -> np.ndarray:
        """0/1 vector over `cols` picking a block of lag coefficients (or explicit names)."""
        if names is None:
            names = []
            for b in self.spec.blocks:
                if block == b.var or (isinstance(block, (list, tuple)) and b.var in block):
                    names += b.names()
        c = np.zeros(self.k)
        for n in names:
            c[self.cols.index(n)] = 1.0
        return c

    def combo(self, weights: dict[str, np.ndarray]) -> tuple[float, float]:
        """Estimate and standard error of  sum_v w_v' b_v  (weights: vintage key -> vector over cols)."""
        g = np.zeros(self.k * len(self.keys))
        est = 0.0
        for key, w in weights.items():
            g[self.slc(key)] = w
            est += float(w @ self.beta[key])
        var = float(g @ self.cov @ g)
        return est, float(np.sqrt(max(var, 0.0)))

    def change_test(self, a: str, b: str, c: np.ndarray) -> dict:
        """Overlap-adjusted test of H0: c'b_a = c'b_b (b is the later/larger sample); a t-test with the smaller sample's residual df."""
        est, se = self.combo({b: c, a: -c})
        df = min(self.df[a], self.df[b])
        z = est / se if se > 0 else np.nan
        return {"change": est, "se": se, "t": z, "p": float(2 * stats.t.sf(abs(z), df)) if se > 0 else np.nan,
                "se_if_independent": float(np.sqrt(c @ (self.block_cov(a, a) + self.block_cov(b, b)) @ c))}

    def draws(self, n: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
        """Joint draws of the vintages' coefficient vectors (n x k each); restrictions hold exactly (singular directions get zero variance)."""
        V = (self.cov + self.cov.T) / 2
        w, U = np.linalg.eigh(V)
        w = np.clip(w, 0.0, None)
        z = rng.standard_normal((n, len(w)))
        dev = (z * np.sqrt(w)) @ U.T
        return {key: self.beta[key][None, :] + dev[:, self.slc(key)] for key in self.keys}


def stack(eq: str, results: dict[str, EquationResult], data: pd.DataFrame, L: int = 4) -> Stacked:
    """Stack `results` (vintage key -> that vintage's result for equation `eq`)."""
    keys = list(results)
    last = max(results.values(), key=lambda r: r.sample[1])
    cols = list(last.coef.index)
    for r in results.values():
        assert set(r.coef.index) <= set(cols), "later sample must contain every coefficient of the earlier ones"
    index = pd.period_range(START_PERIOD, last.sample[1], freq="Q")
    psi = np.hstack([influence(results[k], data, cols, index) for k in keys])
    beta = {k: results[k].coef.reindex(cols).fillna(0.0).values for k in keys}
    return Stacked(eq, keys, cols, beta, newey_west(psi, L), {k: results[k].df_resid for k in keys}, last.spec)


START_PERIOD = pd.Period("1990Q1", "Q")
