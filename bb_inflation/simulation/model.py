"""Dynamic simulation of the four-equation model.

Within each quarter the equations are solved in the authors' order (as in irf_simulations.m,
decomp.m and cond_forecast.m):

    gw_t -> gcpi_t -> diffcpicf_t -> cf10_t -> cf1_t

The first `p = 4` observations of every series are initial conditions (history); simulation starts at
index p. Exogenous variables (grpe, grpf, vu, shortage, magpty, dummies) must be supplied for the full
length. Equation residuals are zero unless `add_shocks` supplies additive terms.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

ENDO = ("gw", "gcpi", "cf1", "cf10", "diffcpicf")
EQ_ORDER = ("gw", "gcpi", "cf10", "cf1")   # diffcpicf is computed between gcpi and cf10
LAGS = 4
_TERM = re.compile(r"^(?P<var>[A-Za-z0-9]+)_L(?P<lag>\d+)$")


def catchup(gcpi: np.ndarray, cf1: np.ndarray, t: int) -> float:
    """diffcpicf_t = mean(gcpi_t..gcpi_{t-3}) - cf1_{t-4}."""
    return 0.25 * (gcpi[t] + gcpi[t - 1] + gcpi[t - 2] + gcpi[t - 3]) - cf1[t - 4]


@dataclass
class SimModel:
    """Coefficients of the four equations, keyed by equation name; each a Series indexed by
    `<var>_L<lag>`, `const` and dummy names."""
    coefs: dict[str, pd.Series]

    @classmethod
    def from_results(cls, results) -> "SimModel":
        return cls({k: r.coef.copy() for k, r in results.items()})

    def with_coefs(self, eq: str, coef: pd.Series) -> "SimModel":
        new = dict(self.coefs)
        new[eq] = coef
        return SimModel(new)

    def simulate(self, endo_hist: dict[str, np.ndarray], exog: dict[str, np.ndarray],
                 dummies: dict[str, np.ndarray] | None = None, use_const: bool = True,
                 const_override: dict[str, float] | None = None,
                 add_shocks: dict[str, np.ndarray] | None = None) -> dict[str, np.ndarray]:
        """Run the simulation.

        endo_hist: first LAGS values of gw, gcpi, cf1, cf10, diffcpicf.
        exog: full-length arrays for every exogenous variable named in the equations.
        dummies: full-length arrays for dummy regressors (default zeros).
        use_const: include equation constants (False for deviation-from-steady-state IRFs).
        const_override: replace an equation's constant (e.g. wage constant in the conditional forecast).
        add_shocks: additive equation shocks by equation name, full length.
        """
        T = len(next(iter(exog.values())))
        s = {k: np.full(T, np.nan) for k in ENDO}
        for k in ENDO:
            s[k][:LAGS] = endo_hist[k][:LAGS]
        series = {**s, **{k: np.asarray(v, float) for k, v in exog.items()}}
        dummies = dummies or {}
        const_override = const_override or {}
        add_shocks = add_shocks or {}

        terms = {}
        for eq, coef in self.coefs.items():
            tl = []
            for name, b in coef.items():
                m = _TERM.match(name)
                if m:
                    tl.append((m["var"], int(m["lag"]), float(b)))
            terms[eq] = tl

        def value(eq: str, t: int) -> float:
            v = sum(b * series[var][t - lag] for var, lag, b in terms[eq])
            coef = self.coefs[eq]
            for name in coef.index:
                if name in dummies:
                    v += coef[name] * dummies[name][t]
            if eq in const_override:
                v += const_override[eq]
            elif use_const and "const" in coef.index:
                v += coef["const"]
            if eq in add_shocks:
                v += add_shocks[eq][t]
            return v

        for t in range(LAGS, T):
            series["gw"][t] = value("gw", t)
            series["gcpi"][t] = value("gcpi", t)
            series["diffcpicf"][t] = catchup(series["gcpi"], series["cf1"], t)
            series["cf10"][t] = value("cf10", t)
            series["cf1"][t] = value("cf1", t)
        return {k: series[k] for k in ENDO}
