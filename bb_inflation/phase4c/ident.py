"""Identification diagnostics for single coefficients (the supply-chain coefficient above all) and for block sums.

Single coefficient. With the homogeneity restriction substituted out (b_pivot = 1 - sum of the other restricted coefficients) the equation is an
unrestricted regression in free parameters, so the Frisch-Waugh-Lovell theorem applies: the coefficient on x_j is identified by the variation in
x_j that is NOT explained by the other regressors, r_j = x_j - Z(Z'Z)^-1 Z'x_j, and  var(b_j) = s^2 / sum(r_j^2)  (checked against the classical
covariance of `estimation.rls`). The diagnostics report how large that residual variation is, how concentrated it is in a few quarters, and
how much of it comes from the pandemic years, which is the question 'does the pre-2020 sample identify the coefficient?'.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..estimation.rls import EquationResult, design


def free_regression(res: EquationResult, data: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame, list[str]]:
    """(y*, Z, names): the restriction substituted out. Columns of Z keep the original regressor names except the pivot, which disappears."""
    names = list(res.coef.index)
    X = design(res.spec, data)[names].loc[res.resid.index]
    y = pd.Series(res.resid.values + res.fitted.values, index=X.index)
    rn = res.spec.restriction_names()
    if not rn:
        return y, X, names
    pivot = rn[0]
    Z = X.copy()
    for n in rn[1:]:
        Z[n] = X[n] - X[pivot]
    Z = Z.drop(columns=pivot)
    return y - X[pivot] * res.spec.restriction_value, Z, list(Z.columns)


def partial_regressor(res: EquationResult, data: pd.DataFrame, target: str) -> pd.Series:
    """FWL residual of `target` on all other free regressors (target must not be in the restricted set)."""
    y, Z, _ = free_regression(res, data)
    others = Z.drop(columns=target)
    x = Z[target].values
    O = others.values
    r = x - O @ np.linalg.lstsq(O, x, rcond=None)[0]
    return pd.Series(r, index=Z.index)


def coefficient_identification(res: EquationResult, data: pd.DataFrame, target: str, windows: dict[str, tuple[str, str]] | None = None) -> dict:
    """Diagnostics for one coefficient in one fitted equation."""
    r = partial_regressor(res, data, target)
    y, Z, _ = free_regression(res, data)
    x = Z[target]
    ss = float((r ** 2).sum())
    n = len(r)
    se_fwl = float(np.sqrt(res.sigma2 / ss))
    se_cls = float(np.sqrt(res.cov.loc[target, target]))
    out = {"N": n, "sd(x) raw": float(x.std(ddof=1)), "sd(x) 1998Q1+ (genuine GSCPI)": float(x.loc["1998Q1":].std(ddof=1)) if x.index[-1] >= pd.Period("1998Q1", "Q") else np.nan,
           "sd of partialled x (FWL)": float(np.sqrt(ss / n)), "partial R2 of x on other regressors": float(1 - ss / ((x - x.mean()) ** 2).sum()),
           "VIF": float(((x - x.mean()) ** 2).sum() / ss), "classical s.e.": se_cls, "s.e. from FWL (check)": se_fwl,
           "effective N (sum r^2)^2 / sum r^4": float(ss ** 2 / (r ** 4).sum())}
    share = (r ** 2) / ss
    top = share.sort_values(ascending=False).head(5)
    out["top-5 quarters' share of identifying variation"] = float(top.sum())
    out["top-5 quarters"] = ", ".join(f"{p} ({100 * s:.0f}%)" for p, s in top.items())
    for lab, (a, b) in (windows or {}).items():
        sub = share.loc[(share.index >= pd.Period(a, "Q")) & (share.index <= pd.Period(b, "Q"))]
        out[f"share from {lab}"] = float(sub.sum()) if len(sub) else np.nan
    return out


def block_flags(bt: pd.DataFrame, labels: dict[str, str]) -> pd.DataFrame:
    """Rule-based identification and stability flags for every block sum, from the block table (HAC inference, t critical values).

    flags (documented in the report): 
      se ratio            HAC s.e. of the B*-2019 estimate / s.e. of the B*-2026 estimate (>= 1.5: the pre-2020 sample is materially less informative)
      weak in B*-2019     |t| < 1.65 in B*-2019 while |t| >= 1.96 in B*-2026 (identified only once post-2019 data are added), or se ratio >= 2
      sign stable         B*-2019, B*-2023 and B*-2026 estimates share a sign
      CIs overlap         each vintage's 95% interval contains the others' point estimates (mutual consistency)
    """
    rows = []
    b19, b23, b26 = labels["B19"], labels["B23"], labels["B26"]
    for (eq, blk), g in bt[bt.vintage.isin([b19, b23, b26])].groupby(["eq", "block"], sort=False):
        d = g.set_index("vintage")
        e19, e23, e26 = d.loc[b19], d.loc[b23], d.loc[b26]
        ratio = e19.se_hac / e26.se_hac
        weak = (abs(e19.t) < 1.65 and abs(e26.t) >= 1.96) or ratio >= 2
        sign_ok = np.sign(e19["sum"]) == np.sign(e23["sum"]) == np.sign(e26["sum"])
        ov = all(d.loc[a, "ci95_lo"] <= d.loc[b, "sum"] <= d.loc[a, "ci95_hi"] for a in d.index for b in d.index)
        rows.append({"eq": eq, "block": blk, "label": e26.label, "sum B*-2019": e19["sum"], "sum B*-2023": e23["sum"], "sum B*-2026": e26["sum"],
                     "t B*-2019": e19.t, "t B*-2023": e23.t, "t B*-2026": e26.t, "se ratio (2019 / 2026)": ratio,
                     "significant at 5% in B*-2026": bool(abs(e26.t) >= 1.96), "weak in B*-2019": bool(weak), "sign stable": bool(sign_ok), "CIs overlap": bool(ov)})
    return pd.DataFrame(rows)
