"""Impulse responses restated in units a non-modeller can use.

The model's native IRF object is the response of `gcpi` = annualised quarterly CPI inflation (400 x dln CPI), in percentage
points, to a shock hitting at quarter h = 0 (no policy response, no feedback beyond the model's four equations). Two
derived views are added; neither changes the model:

* year-on-year inflation   yoy_h  = (a_h + a_{h-1} + a_{h-2} + a_{h-3}) / 4          [percentage points, log approximation]
* price-level deviation    L_h    = (a_0 + ... + a_h) / 4                            [percent of the baseline CPI level]

(a_h = annualised quarterly response; the factor 1/4 converts an annualised rate into a quarterly change. Summing annualised
rates, as Phase 3's "cumulative 0-8" statistic does, therefore overstates the price-level effect fourfold.)

Shock taxonomy (a shock to the *level* of the driver, in its own units):
  temporary   the driver rises for one quarter and returns to baseline in the next (spike and reversal)
  persistent  the driver rises and fades geometrically, level_h = X * rho^h with rho = 0.8 (half-life 3.1 quarters)
  permanent   the driver rises and stays at the new level
For energy and food the driver is a *relative price*; the model's input is its annualised growth rate g_h = 4 x (change in
level, %). A "permanent" energy shock is a one-off, un-reversed jump in the energy price (what Phase 3 called "one-off (level)").
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..estimation.inference import _draw
from ..simulation.general import _trail_mean
from ..simulation.irf import EXOG, SHOCK_T
from ..simulation.model import ENDO, LAGS, SimModel

HZ = 32                         # quarters after the shock (h = 0..31)
RHO = 0.8
DRIVERS = {"Energy": ("grpe", "growth"), "Food": ("grpf", "growth"), "GSCPI": ("shortage", "level"), "V/U": ("vu", "level")}
KINDS = ("temporary", "persistent", "permanent")


def level_path(kind: str, n: int = HZ) -> np.ndarray:
    if kind == "temporary":
        x = np.zeros(n)
        x[0] = 1.0
        return x
    if kind == "persistent":
        return RHO ** np.arange(n)
    if kind == "permanent":
        return np.ones(n)
    raise ValueError(kind)


def driver_input(driver: str, kind: str, size: float, n: int = HZ) -> np.ndarray:
    """Path of the model's exogenous input series, starting at h = 0."""
    _, mode = DRIVERS[driver]
    lvl = size * level_path(kind, n)
    if mode == "level":
        return lvl
    return 4.0 * np.diff(lvl, prepend=0.0)        # annualised growth of the relative price (grpe, grpf)


def simulate(model: SimModel, driver: str, kind: str, size: float, derived: dict, n: int = HZ) -> np.ndarray:
    """Annualised quarterly CPI inflation response (pp), length n, index 0 = shock quarter."""
    var = DRIVERS[driver][0]
    T = n + LAGS
    zeros = np.zeros(T)
    exog = {v: zeros.copy() for v in (*EXOG, "magpty")}
    exog[var][SHOCK_T:] = driver_input(driver, kind, size, n)
    for name, (src, w) in derived.items():
        exog[name] = _trail_mean(exog[src], w)
    out = model.simulate({k: np.zeros(LAGS) for k in ENDO}, exog, use_const=False)
    return np.asarray(out["gcpi"][LAGS:])


def yoy(a: np.ndarray) -> np.ndarray:
    a = np.atleast_2d(a)
    pad = np.concatenate([np.zeros((a.shape[0], 3)), a], axis=1)
    return sum(pad[:, 3 - j: 3 - j + a.shape[1]] for j in range(4)) / 4.0


def price_level(a: np.ndarray) -> np.ndarray:
    return np.cumsum(np.atleast_2d(a), axis=1) / 4.0


def _peak(x: np.ndarray, sign: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Extreme response in the direction `sign` (default: the sign of the largest |x|). Fixing the direction to the point
    estimate's keeps spike-and-reversal paths from switching to the reversal in some Monte-Carlo draws."""
    if sign is None:
        k = np.abs(x).argmax(axis=1)
    else:
        k = (x * sign[:, None]).argmax(axis=1)
    return x[np.arange(len(x)), k], k


def _fade(x: np.ndarray, k: np.ndarray, peak: np.ndarray, frac: float, stay: bool) -> np.ndarray:
    """First quarter after the peak at which |x| <= frac*|peak| (and, if stay, remains so to the end); NaN if never."""
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        ok = np.abs(x[i]) <= frac * abs(peak[i]) + 1e-12
        for h in range(k[i], x.shape[1]):
            if ok[h] and (not stay or ok[h:].all()):
                out[i] = h
                break
    return out


def statistics(a: np.ndarray, signs: dict[str, float] | None = None) -> dict[str, np.ndarray]:
    """Per-path statistics for responses a (n_paths x HZ). `signs` fixes the direction of each peak (from the point estimate)."""
    a = np.atleast_2d(a)
    y, L = yoy(a), price_level(a)
    sg = lambda k, n: None if signs is None else np.full(n, signs[k])          # noqa: E731
    pa, ka = _peak(a, sg("a", len(a)))
    py, ky = _peak(y, sg("y", len(a)))
    pl, kl = _peak(L, sg("L", len(a)))
    s = {"annualised: peak (pp)": pa, "annualised: quarter of peak": ka.astype(float),
         "y/y: peak (pp)": py, "y/y: quarter of peak": ky.astype(float),
         "y/y: half-life from peak (q)": _fade(y, ky, py, 0.5, stay=False) - ky,
         "y/y: faded to 25% of peak (q after shock)": _fade(y, ky, py, 0.25, stay=True),
         "y/y: faded to 10% of peak (q after shock)": _fade(y, ky, py, 0.10, stay=True),
         "price level: peak (%)": pl, "price level: quarter of peak": kl.astype(float),
         "y/y after 3 years, % of peak": 100 * y[:, 11] / py,
         "price level: after 1 year (%)": L[:, 3], "price level: after 2 years (%)": L[:, 7], "price level: after 3 years (%)": L[:, 11],
         "price level: after 8 years (%)": L[:, -1]}
    return s


def draws(results: dict, n: int = 1000, seed: int = 0) -> list[SimModel]:
    """Coefficient draws (HAC covariance, equations independent, restrictions preserved), the same scheme as Phase 3."""
    rng = np.random.default_rng(seed)
    d = {eq: _draw(r.coef.values, r.cov.values, n, rng) for eq, r in results.items()}
    return [SimModel({eq: pd.Series(d[eq][i], index=r.coef.index) for eq, r in results.items()}) for i in range(n)]


def run(point_model: SimModel, draw_models: list[SimModel], sizes: dict[str, float], derived: dict) -> tuple[pd.DataFrame, dict]:
    rows, paths = [], {}
    for driver in DRIVERS:
        for kind in KINDS:
            pt = simulate(point_model, driver, kind, sizes[driver], derived)
            dr = np.array([simulate(m, driver, kind, sizes[driver], derived) for m in draw_models])
            paths[(driver, kind)] = {"point": pt, "draws": dr}
            signs = {"a": float(np.sign(pt[np.abs(pt).argmax()])), "y": float(np.sign(yoy(pt)[0][np.abs(yoy(pt)[0]).argmax()])),
                     "L": float(np.sign(price_level(pt)[0][np.abs(price_level(pt)[0]).argmax()]))}
            sp, sd = statistics(pt, signs), statistics(dr, signs)
            r = {"driver": driver, "persistence": kind, "size": sizes[driver]}
            for k in sp:
                r[k] = float(sp[k][0])
                r[k + " | lo90"] = float(np.nanquantile(sd[k], .05)) if np.isfinite(sd[k]).any() else np.nan
                r[k + " | hi90"] = float(np.nanquantile(sd[k], .95)) if np.isfinite(sd[k]).any() else np.nan
            r["share of draws not faded to 25% within horizon"] = float(np.isnan(sd["y/y: faded to 25% of peak (q after shock)"]).mean())
            rows.append(r)
    return pd.DataFrame(rows), paths


def anchors(data: pd.DataFrame, since: str = "2020Q1") -> pd.DataFrame:
    """Context for shock sizes: how big were actual moves in 2020-26 (relative-price levels in %, V/U and GSCPI in own units)."""
    d = data.loc[since:]
    rows = []
    for name, v in (("Energy (relative price, %)", "grpe"), ("Food (relative price, %)", "grpf")):
        q = d[v] / 4.0
        four = q.rolling(4).sum()
        rows.append({"series": name, "largest 1-quarter rise": float(q.max()), "quarter": str(q.idxmax()),
                     "largest 4-quarter rise": float(four.max()), "4q ending": str(four.idxmax()), "sd of quarterly change": float(q.std())})
    for name, v in (("GSCPI (std. dev.)", "shortage"), ("V/U (ratio)", "vu")):
        x = d[v]
        rows.append({"series": name, "largest 1-quarter rise": float(x.diff().max()), "quarter": str(x.diff().idxmax()),
                     "largest 4-quarter rise": float((x - x.shift(4)).max()), "4q ending": str((x - x.shift(4)).idxmax()),
                     "sd of quarterly change": float(x.diff().std()), "level range 2020-26": f"{x.min():.2f} to {x.max():.2f}",
                     "latest": float(x.iloc[-1])})
    return pd.DataFrame(rows)
