"""Oil -> CPI energy: the link between the first two of the three energy price concepts used in Phase 4.

    1. oil price         Brent, USD per barrel, monthly average (World Bank series on Macrobond; EIA STEO and futures for the future)
    2. CPI energy price  nominal CPI-U energy index (SA); this module maps 1 -> 2
    3. relative energy   CPI energy / ECI wages; NOT mapped here: it is an output of the engine (engine.py), because wages are endogenous

Bridge (monthly, so that the quarter-end timing of the CPI is respected):

    100 dln E_m = c + sum_{k=0..3} b_k * 100 dln Oil_{m-k} + e_m          1990-02 .. 2026-06

estimated by OLS with Newey-West (6 lags) covariance. E is the SA CPI energy index, Oil the monthly Brent average. The quarterly
growth the model needs is the sum of the three monthly changes (CPI is a quarter-end value): gE_q = 4 * sum_{m in q} (100 dln E_m).
The sum of the b_k is the long-run elasticity of CPI energy to the oil price (about 0.30); the constant is the drift in CPI energy
unrelated to oil. The bridge is an auxiliary reduced form: it does not enter the four estimated equations and is not part of Model B*.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

LAGS_OIL = 3
BRIDGE_START = "1990-02"


@dataclass
class Bridge:
    coef: pd.Series                 # const, o0..o3  (monthly, % per % )
    cov: pd.DataFrame               # Newey-West covariance
    resid_sd: float                 # monthly residual s.d. (pp)
    r2: float
    nobs: int
    sample: tuple[str, str]

    @property
    def elasticity(self) -> float:
        return float(self.coef.drop("const").sum())

    def elasticity_se(self) -> float:
        w = np.r_[0.0, np.ones(len(self.coef) - 1)]
        return float(np.sqrt(w @ self.cov.values @ w))

    def draws(self, n: int, seed: int = 0) -> np.ndarray:
        """(n, 5) coefficient draws from the HAC normal approximation; draw 0 is NOT the point estimate (use `point()`)."""
        rng = np.random.default_rng(seed)
        return rng.multivariate_normal(self.coef.values, self.cov.values, size=n)

    def point(self) -> np.ndarray:
        return self.coef.values[None, :]


def _dlog(s: pd.Series) -> pd.Series:
    return 100.0 * np.log(s).diff()


def _nw(X: np.ndarray, e: np.ndarray, L: int = 6) -> np.ndarray:
    u = X * e[:, None]
    S = u.T @ u
    for l in range(1, L + 1):
        G = u[l:].T @ u[:-l]
        S += (1 - l / (L + 1)) * (G + G.T)
    A = np.linalg.inv(X.T @ X)
    return A @ S @ A


def regressors(oil: pd.Series, lags: int = LAGS_OIL) -> pd.DataFrame:
    d = _dlog(oil)
    return pd.concat([d.shift(i).rename(f"o{i}") for i in range(lags + 1)], axis=1)


def estimate_bridge(cpi_energy: pd.Series, oil: pd.Series, end: str = "2026-06", start: str = BRIDGE_START) -> Bridge:
    y = _dlog(cpi_energy).rename("y")
    df = pd.concat([y, regressors(oil)], axis=1, sort=True).loc[start:end].dropna()
    X = np.column_stack([np.ones(len(df)), df.drop(columns="y").values])
    b = np.linalg.lstsq(X, df["y"].values, rcond=None)[0]
    e = df["y"].values - X @ b
    names = ["const"] + [c for c in df.columns if c != "y"]
    cov = _nw(X, e)
    r2 = 1.0 - float(e @ e) / float(((df["y"] - df["y"].mean()) ** 2).sum())
    return Bridge(pd.Series(b, index=names), pd.DataFrame(cov, index=names, columns=names),
                  float(np.sqrt(e @ e / (len(df) - X.shape[1]))), r2, len(df), (str(df.index[0])[:7], str(df.index[-1])[:7]))


def monthly_energy_growth(coef: np.ndarray, oil: pd.Series, first_month: str, last_month: str, noise: np.ndarray | None = None) -> np.ndarray:
    """Predicted monthly CPI-energy changes (% , 100 dln E) for first_month..last_month; coef is (n, 5).

    oil is the monthly oil series covering at least first_month - 3 .. last_month. noise: optional (n, n_months) additive residuals.
    Returns (n, n_months)."""
    months = pd.date_range(first_month, last_month, freq="MS")
    R = regressors(oil).loc[months].values                       # (months, 4)
    out = coef[:, [0]] + coef[:, 1:] @ R.T
    if noise is not None:
        out = out + noise
    return out


def quarterly_energy_growth(monthly_pct: np.ndarray) -> np.ndarray:
    """Annualised quarterly growth (400 dln) from monthly 100 dln changes: 4 * sum of the three months. Shape (n, months) -> (n, months/3)."""
    n, m = monthly_pct.shape
    assert m % 3 == 0
    return 4.0 * monthly_pct.reshape(n, m // 3, 3).sum(axis=2)


# ---------------------------------------------------------------------------------------------------------------
# Oil price paths

def last_futures_date(fut: dict[str, pd.Series]) -> pd.Timestamp:
    return max(s.index[-1] for k, s in fut.items())


def monthly_futures_curve(p4: dict[str, pd.Series], tick: dict[str, str], steo_oct: float | None = None) -> pd.Series:
    """Brent monthly curve Oct 2026 - Dec 2029 from the latest settlement of each delivery-month contract.

    Contracts for Oct and Nov 2026 have already expired (their last prices are stale and far below the market): Oct = EIA STEO estimate
    of the month, Nov = midpoint of Oct and the December contract. Dec 2026 onwards: the live contract (all dated the last futures date)."""
    live = {k: p4[t] for k, t in tick.items() if k >= "bz_202612"}
    ld = pd.Timestamp(max(s.index[-1] for s in live.values()))
    px = {}
    for k, s in live.items():
        assert s.index[-1] == ld, f"{k} last observed {s.index[-1]}, expected {ld}"
        px[pd.Timestamp(f"{k[3:7]}-{k[7:9]}-01")] = float(s.iloc[-1])
    cur = pd.Series(px).sort_index()
    dec = float(cur.loc["2026-12-01"])
    out = {pd.Timestamp("2026-10-01"): float(steo_oct if steo_oct is not None else p4[tick["bz_202611"]].iloc[-1]),
           pd.Timestamp("2026-11-01"): np.nan}
    out[pd.Timestamp("2026-11-01")] = 0.5 * (out[pd.Timestamp("2026-10-01")] + dec)
    s = pd.concat([pd.Series(out), cur]).sort_index()
    s.attrs["futures_date"] = str(ld.date())
    return s


def steo_curve(p4: dict[str, pd.Series], fut_curve: pd.Series) -> pd.Series:
    """EIA STEO monthly Brent (to Dec 2027), continued for 2028-29 with the month-to-month changes of the futures curve."""
    steo = p4["eiasteo0002"].loc["2026-10-01":"2027-12-01"]
    ext = fut_curve.loc["2028-01-01":]
    path = list(steo.values)
    prev = float(steo.iloc[-1])
    last_f = float(fut_curve.loc["2027-12-01"])
    for d, v in ext.items():
        prev = prev * v / last_f
        last_f = v
        path.append(prev)
    return pd.Series(path, index=pd.date_range("2026-10-01", periods=len(path), freq="MS"))


def flat_curve(level: float, months: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(float(level), index=months)


def deviation_to_monthly(dev_pct_q: np.ndarray, first_quarter: pd.Period, months: pd.DatetimeIndex) -> np.ndarray:
    """Quarterly oil deviations from baseline (% of the baseline level, one per quarter from first_quarter) -> monthly multipliers.

    The deviation is a knot at the FIRST month of its quarter (so a constant deviation is in force from the first month of
    first_quarter); months before the first knot are untouched (multiplier 1: observed oil is never changed), months between knots
    are interpolated linearly in log(1 + dev), months after the last knot hold the last deviation."""
    n = len(dev_pct_q)
    knots = [(first_quarter + i).start_time for i in range(n)]
    ys = np.log1p(np.asarray(dev_pct_q, float) / 100.0)
    x = np.array([(k.year * 12 + k.month) for k in knots], float)
    xm = np.array([(m.year * 12 + m.month) for m in months], float)
    return np.exp(np.interp(xm, x, ys, left=0.0))
