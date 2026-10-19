"""Impulse-response analysis for Models A, B, C: shock catalogue, summary statistics, Monte-Carlo (HAC) intervals.

Exogenous shocks are shocks to the *series* x_t = rho * x_{t-1} + shock_t, hitting at the fifth quarter:
* rho = 0   temporary / one-off: the series moves for one quarter only. For the energy and food *growth rates* this
            is a one-off jump in the relative price LEVEL (the level stays higher; the rate returns to zero).
* rho = 0.8 persistent: a decaying run of further increases (rates) or a slowly fading level (V/U, GSCPI).
* rho = 1   permanent: the series stays at its new level (V/U, GSCPI).
Residual shocks (cf1, cf10, gw, gcpi) are one-off additions to that equation.
Sizes are +1 s.d. of the series over 2020Q1-last quarter (residual shocks: s.d. of Model B residuals over the same
window), identical for every model so that responses are comparable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..estimation.inference import irf_draws_mc, with_hac
from ..simulation.general import irf_general
from ..simulation.model import SimModel
from ..validation.specs import VARIANTS

H = 28                       # horizons 0..27, h = 0 is the shock quarter
SHOCKS = [
    ("V/U permanent", "vu", 1.0), ("V/U temporary", "vu", 0.0),
    ("Energy one-off (level)", "grpe", 0.0), ("Energy persistent (rho 0.8)", "grpe", 0.8),
    ("Food one-off (level)", "grpf", 0.0), ("Food persistent (rho 0.8)", "grpf", 0.8),
    ("GSCPI temporary", "shortage", 0.0), ("GSCPI persistent (rho 0.8)", "shortage", 0.8), ("GSCPI permanent", "shortage", 1.0),
    ("cf1 residual (1y expectations)", "cf1", None), ("cf10 residual (10y expectations)", "cf10", None),
    ("gw residual (wages)", "gw", None), ("gcpi residual (prices)", "gcpi", None)]


def shock_sizes(data_b: pd.DataFrame, resid_B: dict[str, pd.Series], since: str = "2020Q1") -> dict[str, float]:
    s = {v: float(data_b.loc[since:, v].std(ddof=1)) for v in ("grpe", "grpf", "vu", "shortage")}
    for eq in ("gw", "gcpi", "cf1", "cf10"):
        s[eq] = float(resid_B[eq].loc[since:].std(ddof=1))
    return s


def stats_from_paths(paths: np.ndarray, permanent: bool) -> dict[str, np.ndarray]:
    """paths: (n, H) responses of gcpi. Returns per-path statistics."""
    pk_idx = np.abs(paths).argmax(axis=1)
    peak = paths[np.arange(len(paths)), pk_idx]
    out = {"peak (pp)": peak, "peak quarter": pk_idx.astype(float),
           "cum 0-4": paths[:, :5].sum(axis=1), "cum 0-8": paths[:, :9].sum(axis=1), "cum 0-12": paths[:, :13].sum(axis=1),
           "level at h27": paths[:, -1]}
    half = []
    for p, k, pe in zip(paths, pk_idx, peak):
        after = np.where(np.abs(p[k:]) <= 0.5 * abs(pe))[0]
        half.append(float(after[0]) if len(after) else np.nan)
    out["half-life from peak (q)"] = np.array(half)
    return out


def run(models: dict[str, dict], specs: dict, data_b: pd.DataFrame, data_for_hac: pd.DataFrame, sizes: dict[str, float],
        n_mc: int = 1000, seed: int = 0, which: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    rows, paths = [], {}
    for mname in which or list(models):
        res = models[mname]
        v = VARIANTS[specs[mname].variant]
        derived = v.derived_dict
        point_model = SimModel.from_results(res)
        hac = {k: with_hac(r, data_for_hac) for k, r in res.items()}
        fn = lambda m, s, z, rho: irf_general(m, s, z, derived=derived, rho=rho, horizon=H + 4)       # noqa: E731
        for label, shock, rho in SHOCKS:
            size = sizes[shock]
            pt = fn(point_model, shock, size, rho)["gcpi_simul"].values[4:]          # drop the 4 initial-condition quarters
            dr = irf_draws_mc(hac, fn, shock, size, n=n_mc, seed=seed, rho=rho)[:, 4:]
            perm = rho == 1.0
            ps, ds = stats_from_paths(pt[None, :], perm), stats_from_paths(dr, perm)
            paths[(mname, label)] = {"point": pt, "q05": np.quantile(dr, .05, axis=0), "q95": np.quantile(dr, .95, axis=0),
                                     "q50": np.quantile(dr, .5, axis=0)}
            for k in ps:
                rows.append({"model": mname, "shock": label, "size": size, "stat": k, "point": float(ps[k][0]),
                             "lo90": float(np.nanquantile(ds[k], .05)), "hi90": float(np.nanquantile(ds[k], .95))})
    return pd.DataFrame(rows), paths
