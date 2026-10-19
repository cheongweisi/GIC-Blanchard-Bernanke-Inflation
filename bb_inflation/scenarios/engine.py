"""Scenario engine: the Phase 1-3 four-equation model, driven by NOMINAL energy and food prices.

Why a new simulator. Phase 1-3 simulations take the *relative* price growth rates `grpe`, `grpf` (CPI energy / food relative to the
wage index, ECI) as exogenous. Wages are endogenous, so a scenario that moves wages (a labour-market or expectations shock)
while holding the relative price fixed would silently let the nominal energy price move one-for-one with US wages, which no
oil-market assumption justifies. Here the inputs are the nominal CPI energy and food growth rates `gE`, `gF` and, in every quarter,
after the wage equation has been solved,

        grpe_t = gE_t - gW_t ,        grpf_t = gF_t - gW_t ,        (exact: grpe = 400 dln(CPI energy / ECI))

so relative prices are *outputs*. Because the price equation has the same lags (0-4) on wage growth and on both relative prices,
this is the same equation written in nominal terms, homogeneous of degree one:

  gcpi = sum_k (b_w,k - b_e,k - b_f,k) gw_{t-k}  +  sum_k b_e,k gE_{t-k}  +  sum_k b_f,k gF_{t-k}  +  lagged gcpi (sum b)  + ...

with weights (0.59, 0.075, 0.18, 0.155 in Model B*) that add to one.

Solution order inside a quarter (as in simulation/model.py): gw -> grpe, grpf -> gcpi -> diffcpicf -> cf10 -> cf1.
Everything is vectorised over a leading "draw" dimension (coefficient draws, bootstrap residuals, bridge draws); n = 1 is the point
estimate. With relative prices supplied through `rel_override` and nothing else switched on, the engine reproduces
`SimModel.simulate` exactly (tested).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..simulation.model import ENDO, LAGS, SimModel

EQ = ("gw", "gcpi", "cf10", "cf1")          # solution order; diffcpicf is computed between gcpi and cf10
_TERM = re.compile(r"^(?P<var>[A-Za-z0-9]+)_L(?P<lag>\d+)$")
STATE = ("gw", "gcpi", "cf1", "cf10", "diffcpicf", "grpe", "grpf")


def _catchup(gcpi: np.ndarray, cf1: np.ndarray, t: int) -> np.ndarray:
    return 0.25 * (gcpi[:, t] + gcpi[:, t - 1] + gcpi[:, t - 2] + gcpi[:, t - 3]) - cf1[:, t - 4]


@dataclass
class CoefSet:
    """Coefficients by equation as arrays (n_draws x n_terms); names are shared across draws."""
    names: dict[str, list[str]]
    values: dict[str, np.ndarray]

    @classmethod
    def from_models(cls, models: list[SimModel]) -> "CoefSet":
        names = {eq: list(models[0].coefs[eq].index) for eq in models[0].coefs}
        return cls(names, {eq: np.vstack([m.coefs[eq].reindex(names[eq]).values.astype(float) for m in models]) for eq in names})

    @property
    def n(self) -> int:
        return next(iter(self.values.values())).shape[0]

    def point(self) -> "CoefSet":
        return CoefSet(self.names, {k: v[:1] for k, v in self.values.items()})

    def get(self, eq: str, name: str) -> np.ndarray:
        return self.values[eq][:, self.names[eq].index(name)]

    def scaled(self, eq: str, var: str, factor: float) -> "CoefSet":
        """Multiply every coefficient `<var>_L*` of equation `eq` by `factor` (the energy pass-through sensitivity)."""
        v = {k: a.copy() for k, a in self.values.items()}
        for j, nm in enumerate(self.names[eq]):
            m = _TERM.match(nm)
            if m and m["var"] == var:
                v[eq][:, j] *= factor
        return CoefSet(self.names, v)

    def block_sum(self, eq: str, var: str) -> np.ndarray:
        cols = [j for j, nm in enumerate(self.names[eq]) if (m := _TERM.match(nm)) and m["var"] == var]
        return self.values[eq][:, cols].sum(axis=1)

    def effective_nominal_weights(self) -> dict[str, np.ndarray]:
        """Price-equation weights in nominal form: wages net of the relative-price terms, nominal energy, nominal food, lagged inflation."""
        w, e, f, c = (self.block_sum("gcpi", v) for v in ("gw", "grpe", "grpf", "gcpi"))
        return {"wages (net)": w - e - f, "nominal energy": e, "nominal food": f, "lagged inflation": c}


@dataclass
class Inputs:
    """Everything the simulator needs, on a grid of T = LAGS + H quarters (the first LAGS are history).

    hist: first LAGS values of every state variable (gw, gcpi, cf1, cf10, diffcpicf, grpe, grpf).
    exog: full-length vu, magpty, shortagema2 (shape (T,) or (n, T)).
    gE, gF: full-length nominal CPI energy / food growth (annualised, %); the history part is the actual growth.
    add: additive equation shocks / add-factors by equation (shape (T,) or (n, T)).
    known: values to force for an endogenous variable (NaN = solve normally), e.g. a published CPI in a partly observed quarter.
    frozen: endogenous variable held on a given path (its equation is switched off) - used for the transmission-layer closures.
    rel_override: exogenous relative-price growth (NaN = derive from nominal growth and wages). Internal use only: reproduces the
        Phase 1-3 simulations and builds reference decompositions; scenarios may not use it.
    """
    hist: dict[str, np.ndarray]
    exog: dict[str, np.ndarray]
    gE: np.ndarray
    gF: np.ndarray
    add: dict[str, np.ndarray] = field(default_factory=dict)
    known: dict[str, np.ndarray] = field(default_factory=dict)
    frozen: dict[str, np.ndarray] = field(default_factory=dict)
    rel_override: dict[str, np.ndarray] = field(default_factory=dict)
    const_override: dict[str, float] = field(default_factory=dict)

    @property
    def T(self) -> int:
        return len(self.gE) if np.ndim(self.gE) == 1 else self.gE.shape[1]

    def replace(self, **kw) -> "Inputs":
        d = {f: getattr(self, f) for f in self.__dataclass_fields__}
        d.update(kw)
        return Inputs(**d)


@dataclass
class Path:
    """Simulated paths, each (n, T)."""
    s: dict[str, np.ndarray]
    terms: dict[str, dict[str, np.ndarray]] | None = None      # eq -> block -> (n, T) contribution, if recorded

    def __getitem__(self, k: str) -> np.ndarray:
        return self.s[k]


def _row(x, n: int, T: int) -> np.ndarray:
    a = np.asarray(x, float)
    return np.broadcast_to(a[None, :] if a.ndim == 1 else a, (n, T))


def simulate(cs: CoefSet, inp: Inputs, record: bool = False) -> Path:
    n, T = cs.n, inp.T
    s = {k: np.full((n, T), np.nan) for k in STATE}
    for k in STATE:
        s[k][:, :LAGS] = np.asarray(inp.hist[k], float)[None, :LAGS]
    ex = {k: _row(v, n, T) for k, v in inp.exog.items()}
    gE, gF = _row(inp.gE, n, T), _row(inp.gF, n, T)
    add = {k: _row(v, n, T) for k, v in inp.add.items()}
    known = {k: np.asarray(v, float) for k, v in inp.known.items()}
    frozen = {k: np.asarray(v, float) for k, v in inp.frozen.items()}
    rel = {k: np.asarray(v, float) for k, v in inp.rel_override.items()}
    series = {**s, **ex}

    terms: dict[str, list[tuple[str, int, int]]] = {}
    for eq, nm in cs.names.items():
        tl = []
        for j, name in enumerate(nm):
            m = _TERM.match(name)
            if m:
                tl.append((m["var"], int(m["lag"]), j))
        terms[eq] = tl
    const_col = {eq: (nm.index("const") if "const" in nm else None) for eq, nm in cs.names.items()}
    rec: dict[str, dict[str, np.ndarray]] = {eq: {} for eq in cs.names} if record else {}

    def blk(var: str) -> str:
        return {"grpe": "energy (relative price)", "grpf": "food (relative price)", "gw": "wages", "gcpi": "lagged inflation",
                "shortagema2": "supply chains", "shortage": "supply chains", "magpty": "productivity", "vu": "labour market (V/U)",
                "cf1": "1y expectations", "cf10": "10y expectations", "diffcpicf": "catch-up"}.get(var, var)

    def value(eq: str, t: int) -> np.ndarray:
        B = cs.values[eq]
        v = np.zeros(n)
        for var, lag, j in terms[eq]:
            x = series[var][:, t - lag]
            c = B[:, j] * x
            v = v + c
            if record:
                r = rec[eq].setdefault(blk(var), np.zeros((n, T)))
                r[:, t] += c
        if eq in inp.const_override:
            c0 = np.broadcast_to(np.asarray(inp.const_override[eq], float), (n,)).copy()   # scalar, or one value per draw
        elif const_col[eq] is not None:
            c0 = B[:, const_col[eq]]
        else:
            c0 = np.zeros(n)
        v = v + c0
        if record:
            rec[eq].setdefault("constant", np.zeros((n, T)))[:, t] += c0
        if eq in add:
            v = v + add[eq][:, t]
            if record:
                rec[eq].setdefault("add-factor / shock", np.zeros((n, T)))[:, t] += add[eq][:, t]
        return v

    for t in range(LAGS, T):
        for eq in ("gw",):
            series["gw"][:, t] = frozen["gw"][t] if "gw" in frozen else value("gw", t)
            if "gw" in known and np.isfinite(known["gw"][t]):
                series["gw"][:, t] = known["gw"][t]
        series["grpe"][:, t] = rel["grpe"][t] if ("grpe" in rel and np.isfinite(rel["grpe"][t])) else gE[:, t] - series["gw"][:, t]
        series["grpf"][:, t] = rel["grpf"][t] if ("grpf" in rel and np.isfinite(rel["grpf"][t])) else gF[:, t] - series["gw"][:, t]
        series["gcpi"][:, t] = frozen["gcpi"][t] if "gcpi" in frozen else value("gcpi", t)
        if "gcpi" in known and np.isfinite(known["gcpi"][t]):
            series["gcpi"][:, t] = known["gcpi"][t]
        series["diffcpicf"][:, t] = _catchup(series["gcpi"], series["cf1"], t)
        for eq in ("cf10", "cf1"):
            series[eq][:, t] = frozen[eq][t] if eq in frozen else value(eq, t)
            if eq in known and np.isfinite(known[eq][t]):
                series[eq][:, t] = known[eq][t]
    out = {k: series[k] for k in STATE}
    return Path(out, rec if record else None)


# ----------------------------------------------------------------------------------------------------------------
# Nominal-form accounting of the price equation (for the transmission tables)

def nominal_price_blocks(cs: CoefSet, p: Path, gE: np.ndarray, gF: np.ndarray, t0: int) -> pd.DataFrame:
    """Contribution of each nominal block to gcpi_t for t >= t0 (point estimate, n = 1), exact up to the constant/add-factor:

    wages (net of relative-price terms), nominal energy, nominal food, lagged inflation, supply chains, productivity, constant+add-factors.
    `p.terms` must have been recorded. History quarters of grpe/grpf are the actual values (grpe = gE - gw holds in history too).
    """
    assert p.terms is not None and cs.n == 1
    pr = p.terms["gcpi"]
    T = p.s["gcpi"].shape[1]
    zero = np.zeros((1, T))
    g = lambda k: pr.get(k, zero)[0]                                              # noqa: E731
    # wage-linked relative-price parts: the relative-price terms contain -b*gw, move them to the wage block
    be = {k: cs.get("gcpi", f"grpe_L{k}")[0] for k in range(5)}
    bf = {k: cs.get("gcpi", f"grpf_L{k}")[0] for k in range(5)}
    gw = p.s["gw"][0]
    off = np.zeros(T)
    for t in range(t0, T):
        off[t] = sum((be[k] + bf[k]) * gw[t - k] for k in range(5))
    nomE = np.zeros(T)
    nomF = np.zeros(T)
    for t in range(t0, T):
        nomE[t] = sum(be[k] * np.asarray(gE).reshape(-1)[t - k] for k in range(5))
        nomF[t] = sum(bf[k] * np.asarray(gF).reshape(-1)[t - k] for k in range(5))
    df = pd.DataFrame({"wages (net of relative-price offset)": g("wages") - off, "nominal energy": nomE, "nominal food": nomF,
                       "lagged inflation": g("lagged inflation"), "supply chains": g("supply chains"),
                       "productivity": g("productivity"),
                       "constant and add-factors": g("constant") + g("add-factor / shock")})
    return df.iloc[t0:]
