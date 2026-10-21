"""Re-estimation of Model B* on data through 2023Q2 only, the auxiliary models the forecasts need, and the comparison with the
full-sample (through 2026Q2) production Model B*.

Specification: exactly production Model B* (the authors' four equations and restrictions, four lags, GSCPI two-quarter trailing mean as the
shortage term, estimation start 1990Q1). COVID: the 2020Q2 and 2020Q3 wage-equation dummies are included because both quarters lie inside
a sample ending 2023Q2 (the same rule `extension.models.specs_for_end` applies to every sample end); in a forecast they are zero.

Estimation uses no observation after 2023Q2: every equation is estimated on 1990Q1-2023Q2 (`rls.estimate(start, end)`); lags are built
from the series itself, no lag selection or tuning is done (lag lengths are the authors'). Equality with the dataset rebuilt from data
truncated at 2023Q2 is tested.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..estimation.inference import coef_table, with_hac
from ..estimation.rls import EquationResult, estimate
from ..extension.models import specs_for_end
from . import data as D

EQS = ("gw", "gcpi", "cf10", "cf1")
START = "1990Q1"
VARIANT = "gscpi_ma2"


def fit(data: pd.DataFrame, end: str) -> dict[str, EquationResult]:
    specs = specs_for_end(VARIANT, end)
    return {eq: estimate(specs[eq], data, START, end) for eq in EQS}


def coef_long(res: dict[str, EquationResult], data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for eq in EQS:
        t = coef_table(res[eq], with_hac(res[eq], data))
        for name, r in t.iterrows():
            rows.append({"eq": eq, "term": name, "coef": r.beta, "se_hac": r.se_hac, "se_classical": r.se_classic,
                         "t_hac": r.beta / r.se_hac if r.se_hac > 0 else np.nan})
    return pd.DataFrame(rows)


def fit_stats(res: dict[str, EquationResult]) -> pd.DataFrame:
    return pd.DataFrame([{"eq": eq, "sample_start": str(r.sample[0]), "sample_end": str(r.sample[1]), "nobs": r.nobs,
                          "n_terms": len(r.coef), "resid_sd": float(np.sqrt(r.sigma2)), "r2_corr": r.r2_corr,
                          "dummies": ",".join(r.spec.dummies) or "none"} for eq, r in res.items()])


def _blocks(eq: str) -> list[str]:
    return {"gw": ["gw", "cf1", "vu", "diffcpicf", "magpty"], "gcpi": ["gcpi", "gw", "grpe", "grpf", "shortagema2", "magpty"],
            "cf10": ["cf10", "gcpi"], "cf1": ["cf1", "cf10", "gcpi"]}[eq]


def block_sums(res: dict[str, EquationResult], data: pd.DataFrame) -> pd.DataFrame:
    """Sum of coefficients of each regressor block with HAC standard error."""
    rows = []
    for eq in EQS:
        r = with_hac(res[eq], data)
        for b in _blocks(eq):
            names = r.block_names(b)
            w = np.zeros(len(r.coef))
            for n in names:
                w[list(r.coef.index).index(n)] = 1.0
            s = float(w @ r.coef.values)
            se = float(np.sqrt(w @ r.cov.values @ w))
            rows.append({"eq": eq, "block": b, "sum": s, "se_hac": se})
    return pd.DataFrame(rows)


def compare(c23: pd.DataFrame, c26: pd.DataFrame, s23: pd.DataFrame, s26: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Coefficient-by-coefficient and block-sum comparison. 'material' = the change exceeds one HAC standard error of the 2023Q2
    estimate (a screening rule, not a test: the two samples overlap by construction, so differences are not independent draws)."""
    m = c23.merge(c26, on=["eq", "term"], how="outer", suffixes=("_2023Q2", "_2026Q2"))
    m["change"] = m["coef_2026Q2"] - m["coef_2023Q2"]
    m["change_in_se_2023Q2"] = m["change"] / m["se_hac_2023Q2"]
    m["material"] = m["change_in_se_2023Q2"].abs() > 1.0
    b = s23.merge(s26, on=["eq", "block"], suffixes=("_2023Q2", "_2026Q2"))
    b["change"] = b["sum_2026Q2"] - b["sum_2023Q2"]
    b["change_in_se_2023Q2"] = b["change"] / b["se_hac_2023Q2"]
    b["material"] = b["change_in_se_2023Q2"].abs() > 1.0
    return m, b


# ------------------------------------------------------------------------------------------------------------------------
# Auxiliary models (estimated on information through 2023Q2 only)
# ------------------------------------------------------------------------------------------------------------------------
def oil_bridge_quarterly(levels: pd.DataFrame, end: str = "2023Q2", start: str = "1990Q2") -> dict:
    """gE_t = c + b0 * gBrent_t + e_t   (both 400*dln; CPI energy = quarter-end index, Brent = quarterly mean), OLS, 1990Q2-end.
    Lags of Brent (1-3 quarters) add nothing (R2 0.62 -> 0.64, lag coefficients ~0), so the bridge is contemporaneous only."""
    gE = 400.0 * np.log(levels["cpi_energy"]).diff()
    gB = 400.0 * np.log(levels["brent"]).diff()
    df = pd.concat([gE.rename("y"), gB.rename("x")], axis=1).loc[start:end].dropna()
    X = np.column_stack([np.ones(len(df)), df["x"].values])
    b = np.linalg.lstsq(X, df["y"].values, rcond=None)[0]
    e = df["y"].values - X @ b
    s2 = e @ e / (len(df) - 2)
    V = s2 * np.linalg.inv(X.T @ X)
    return {"bridge_const": float(b[0]), "bridge_b0": float(b[1]), "bridge_b0_se_ols": float(np.sqrt(V[1, 1])),
            "bridge_r2": float(1 - e @ e / ((df["y"] - df["y"].mean()) ** 2).sum()), "bridge_resid_sd": float(np.sqrt(s2)),
            "bridge_n": int(len(df)), "bridge_sample": f"{df.index[0]}-{df.index[-1]}"}


def gscpi_ar1(model_data: pd.DataFrame, end: str = "2023Q2", start: str = "1998Q1") -> dict:
    """GSCPI level AR(1) with constant, 1998Q1-end (the Phase 4 baseline rule, estimated on data to the origin only)."""
    sh = model_data["shortage"].loc[start:end]
    X = np.column_stack([np.ones(len(sh) - 1), sh.values[:-1]])
    c, rho = np.linalg.lstsq(X, sh.values[1:], rcond=None)[0]
    e = sh.values[1:] - X @ np.array([c, rho])
    return {"gscpi_ar_const": float(c), "gscpi_ar_rho": float(rho), "gscpi_ar_resid_sd": float(e.std(ddof=2)),
            "gscpi_ar_mean": float(c / (1 - rho)), "gscpi_ar_sample": f"{sh.index[0]}-{sh.index[-1]}"}


def ar_benchmark(gcpi: pd.Series, p: int, end: str = "2023Q2", start: str = "1990Q1") -> dict:
    """AR(p) with constant on quarterly annualised CPI inflation, estimated on `start`-`end` (the same window as Model B*)."""
    d = pd.concat([gcpi.rename("y")] + [gcpi.shift(i).rename(f"l{i}") for i in range(1, p + 1)], axis=1).loc[start:end].dropna()
    X = np.column_stack([np.ones(len(d))] + [d[f"l{i}"].values for i in range(1, p + 1)])
    b = np.linalg.lstsq(X, d["y"].values, rcond=None)[0]
    return {"const": float(b[0]), "phi": [float(x) for x in b[1:]], "n": int(len(d))}


def ar_forecast(gcpi_hist: pd.Series, par: dict, quarters: pd.PeriodIndex) -> pd.Series:
    hist = list(gcpi_hist.iloc[-len(par["phi"]):].astype(float))
    out = []
    for _ in quarters:
        v = par["const"] + sum(ph * hist[-i - 1] for i, ph in enumerate(par["phi"]))
        out.append(v)
        hist.append(v)
    return pd.Series(out, index=quarters)


# ------------------------------------------------------------------------------------------------------------------------
# SVAR-X matrices
# ------------------------------------------------------------------------------------------------------------------------
def svarx_matrices_table(coef: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Estimated matrices A0 y_t = c + sum A_i y_{t-i} + sum B_j x_{t-j} (same layout as the project's SVAR-X note)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "phase5"))
    import p5_forecast_engine as eng
    coefs = {eq: g.set_index("term")["coef"] for eq, g in coef.groupby("eq")}
    A, B, c = eng.build_matrices(coefs)
    out = {}
    ylab = ["gw", "gcpi", "cf10 (long-run exp.)", "cf1 (short-run exp.)"]
    xlab = eng.XV
    for i, M in A.items():
        out[f"A{i}"] = pd.DataFrame(M, index=ylab, columns=ylab)
    for j, M in B.items():
        out[f"B{j}"] = pd.DataFrame(M, index=ylab, columns=xlab)
    out["c"] = pd.DataFrame(c, index=ylab, columns=["constant"])
    return out
