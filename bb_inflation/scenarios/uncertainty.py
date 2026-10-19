"""Uncertainty bands, with their coverage stated.

SCENARIO DEVIATIONS (scenario minus baseline). The model and the bridge are linear, so equation shocks cancel: the band reflects PARAMETER
uncertainty only: 1,000 draws of the four equations' coefficients from the HAC normal approximation (equations independent, restrictions
preserved, as in Phase 3) jointly with 1,000 draws of the oil-bridge coefficients. It does not include uncertainty about the drivers
(that is what the scenarios are for) or about the model's specification (see the 20% pass-through sensitivity and the wage-constant sensitivity).

BASELINE FAN. Conditional on the baseline driver paths (oil curve, held V/U and productivity, AR(1) GSCPI, food with wages): parameter draws
as above, plus (i) the four equations' residuals resampled jointly by quarter from the 1990Q1-2026Q2 estimation sample (keeps their
cross-equation correlation; iid over time) and (ii) the bridge's monthly residual (normal, s.d. = estimate). It does NOT include uncertainty
about the oil path, V/U, productivity or GSCPI, so it is narrower than an unconditional forecast interval (see `backtest.py` for the empirical
errors of genuine real-time forecasts).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import attribution as A
from . import scenario as S
from .world import LAGS, H_SIM, World

QUANT = (0.05, 0.16, 0.5, 0.84, 0.95)


def residual_matrix(w: World) -> pd.DataFrame:
    r = pd.concat({eq: w.res[eq].resid for eq in ("gw", "gcpi", "cf1", "cf10")}, axis=1).dropna()
    return r


def noise_draws(w: World, n: int, seed: int = 123) -> dict:
    rng = np.random.default_rng(seed)
    R = residual_matrix(w)
    T = w.T
    eq = {k: np.zeros((n, T)) for k in R.columns}
    for t in range(LAGS, T):
        pick = rng.integers(0, len(R), size=n)
        for k in R.columns:
            eq[k][:, t] = R[k].values[pick]
    if w.nowcast:                              # published CPI inflation and expectations of the nowcast quarter are imposed
        for k in ("gcpi", "cf1", "cf10"):
            eq[k][:, LAGS] = 0.0
    nm = len(w.months)
    bridge = rng.normal(0.0, w.bridge.resid_sd, size=(n, nm))
    return {"eq": eq, "bridge": bridge}


def _yoy_pct(gc: np.ndarray) -> np.ndarray:
    """y/y inflation in % (compounded) for the grid quarters from simulated gcpi (n, T)."""
    y = np.stack([gc[:, t - 3:t + 1].mean(axis=1) for t in range(LAGS, gc.shape[1])], axis=1)
    return 100.0 * (np.exp(y / 100.0) - 1.0)


def baseline_fan(w: World, n: int | None = None, seed: int = 123, scn: S.Scenario | None = None) -> pd.DataFrame:
    n = n or w.cs_draws.n
    base = scn or S.Scenario("base", "baseline")
    nz = noise_draws(w, w.cs_draws.n, seed)
    r = S.run(w, base, n="all", noise=nz)
    y = _yoy_pct(r.path["gcpi"])
    q = np.quantile(y, QUANT, axis=0)
    out = pd.DataFrame(q.T, index=w.quarters, columns=[f"q{int(p * 100)}" for p in QUANT])
    out["mean"] = y.mean(axis=0)
    ann = np.quantile(r.path["gcpi"][:, LAGS:], QUANT, axis=0)
    for i, p in enumerate(QUANT):
        out[f"ann_q{int(p * 100)}"] = ann[i]
    return out


def deviation_bands(w: World, scn: S.Scenario) -> dict[str, pd.DataFrame]:
    """5/95% bands of the scenario deviation (parameter uncertainty only) for annualised inflation, y/y (pp) and the price level (%)."""
    rs = S.run(w, scn, n="all")
    rb = A.baseline_run(w, scn)
    rb_all = S.run(w, S.Scenario("base", "b", energy_scale=scn.energy_scale, wage_constant=scn.wage_constant,
                                 intercept_correction=scn.intercept_correction), n="all")
    v = A._views(rs.path["gcpi"], rb_all.path["gcpi"])
    pt = A._views(S.run(w, scn).path["gcpi"], rb.path["gcpi"])
    out = {}
    for k in v:
        lo, hi = np.quantile(v[k], [0.05, 0.95], axis=0)
        out[k] = pd.DataFrame({"point": pt[k][0], "lo90": lo, "hi90": hi}, index=w.quarters)
    return out
