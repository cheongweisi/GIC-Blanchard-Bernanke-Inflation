"""Phase 4b, part 1: wage-price feedback. Is the near-zero second-round wage response a feature of the data or of the specification?

(a) `catchup_table`: re-estimate the wage equation (authors' restrictions, HAC) with alternative catch-up terms and samples.
(b) `postcovid_test`: do the wage residuals of an earlier-frozen equation line up with lagged inflation surprises afterwards?
(c) `overlay_coefs`: a labelled calibration overlay that puts a catch-up coefficient phi on the wage equation WITHOUT touching the estimates
    (the constant is re-centred so that fitted wage growth at the sample mean of the catch-up term is unchanged).
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from ..estimation.equations import Block, EquationSpec, L1_4
from ..estimation.inference import with_hac
from ..estimation.rls import estimate
from ..extension.models import specs_for_end


def _wage_spec(base: EquationSpec, catch: Block | None) -> EquationSpec:
    blocks = tuple(b for b in base.blocks if b.var != "diffcpicf")
    summ = tuple(v for v in base.summary_blocks if v != "diffcpicf")
    if catch is not None:
        blocks = blocks + (catch,)
        summ = summ + (catch.var,)
    return dataclasses.replace(base, blocks=blocks, summary_blocks=summ)


def augmented(d: pd.DataFrame) -> pd.DataFrame:
    """Data with alternative catch-up variables added (all built from gcpi, cf1, gw, magpty; nothing new is pulled)."""
    x = d.copy()
    x["cu_avg"] = x["diffcpicf"].shift(1).rolling(4).mean()                          # mean of the four lagged catch-up terms (one coefficient)
    x["diff8"] = x["gcpi"].rolling(8).mean() - x["cf1"].shift(8)                     # two-year inflation surprise
    x["cu8"] = x["diff8"].shift(1)
    gap = x["gcpi"] - x["gw"] + x["magpty"]                                          # shortfall of real wage growth vs productivity growth
    x["rwgap8"] = gap.rolling(8).mean().shift(1)
    x["rwgap12"] = gap.rolling(12).mean().shift(1)
    return x


VARIANTS = {
    "authors: diffcpicf lags 1-4 (free)": Block("diffcpicf", L1_4),
    "single coef: mean of lagged diffcpicf": Block("cu_avg", (0,)),
    "2-year surprise (8q infl. - cf1 8q ago), lag 1": Block("cu8", (0,)),
    "real-wage gap vs productivity, 8q mean, lag 1": Block("rwgap8", (0,)),
    "real-wage gap vs productivity, 12q mean, lag 1": Block("rwgap12", (0,)),
}


def catchup_table(d: pd.DataFrame, last: str) -> pd.DataFrame:
    """Catch-up evidence in the wage equation: variants x samples. Sum of the catch-up block, HAC s.e., 95% interval."""
    x = augmented(d)
    rows = []
    samples = {"1990Q1-2019Q4": ("1990Q1", "2019Q4"), f"1990Q1-{last} (B*)": ("1990Q1", last), f"1995Q1-{last}": ("1995Q1", last),
               f"2000Q1-{last}": ("2000Q1", last)}
    for sname, (a, b) in samples.items():
        base = specs_for_end("gscpi_ma2", b)["gw"]
        for vname, blk in VARIANTS.items():
            spec = _wage_spec(base, blk)
            r = estimate(spec, x, a, b)
            rh = with_hac(r, x)
            names = blk.names()
            s = float(r.coef[names].sum())
            R = np.zeros(len(r.coef))
            for n in names:
                R[list(r.coef.index).index(n)] = 1.0
            se = float(np.sqrt(R @ rh.cov.values @ R))
            rows.append({"sample": sname, "variant": vname, "N": r.nobs, "catch-up (sum)": s, "HAC s.e.": se, "t": s / se,
                         "95% lo": s - 1.96 * se, "95% hi": s + 1.96 * se,
                         "own-lag sum": float(r.coef[[f"gw_L{k}" for k in L1_4]].sum()),
                         "V/U sum": float(r.coef[[f"vu_L{k}" for k in L1_4]].sum())})
    return pd.DataFrame(rows)


def _hac_slope(res: np.ndarray, z: np.ndarray, L: int = 4) -> tuple[float, float, int]:
    X = np.column_stack([np.ones(len(z)), z])
    b = np.linalg.lstsq(X, res, rcond=None)[0]
    e = res - X @ b
    A = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    S = u.T @ u
    for l in range(1, L + 1):
        G = u[l:].T @ u[:-l]
        S += (1 - l / (L + 1)) * (G + G.T)
    V = A @ S @ A
    return float(b[1]), float(np.sqrt(V[1, 1])), len(z)


def postcovid_test(d: pd.DataFrame, last: str, frozen_end: str, start: str) -> pd.DataFrame:
    """One-step wage-equation residuals (actual - prediction of the equation frozen at `frozen_end`) from `start` to `last`, regressed on lagged
    catch-up variables. A positive slope = wages catch up with past inflation beyond what the frozen equation allows."""
    x = augmented(d)
    r0 = estimate(specs_for_end("gscpi_ma2", frozen_end)["gw"], x, "1990Q1", frozen_end)
    resid = (x["gw"] - r0.predict(x)).rename("res").loc[start:last]
    out = []
    for name in ("cu_avg", "cu8", "rwgap8"):
        df = pd.concat([resid, x[name].loc[start:last]], axis=1).dropna()
        s, se, n = _hac_slope(df["res"].values, df[name].values)
        out.append({"frozen at": frozen_end, "window": f"{start}-{last}", "regressor": name, "N": n, "slope": s, "HAC s.e.": se, "t": s / se,
                    "mean residual": float(df["res"].mean())})
    return pd.DataFrame(out)


def overlay_coefs(cs, phi: float, mean_catchup: float):
    """Copy of the CoefSet with a catch-up overlay: diffcpicf_L1..L4 = phi/4 each (replacing the estimated lags), wage constant re-centred
    (const <- const - (phi - estimated sum) * mean catch-up term) so fitted wage growth at the sample-average catch-up term is unchanged.
    The estimated CoefSet itself is never modified."""
    from ..scenarios.engine import CoefSet
    v = {k: a.copy() for k, a in cs.values.items()}
    nm = cs.names["gw"]
    est_sum = sum(v["gw"][:, nm.index(f"diffcpicf_L{k}")] for k in range(1, 5))
    for k in range(1, 5):
        v["gw"][:, nm.index(f"diffcpicf_L{k}")] = phi / 4.0
    v["gw"][:, nm.index("const")] = v["gw"][:, nm.index("const")] - (phi - est_sum) * mean_catchup
    return CoefSet(cs.names, v)
