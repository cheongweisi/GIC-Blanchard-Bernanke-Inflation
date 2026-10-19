"""Impulse responses for the Phase 4c vintage comparison.

Design (everything is a deviation from a common baseline; the model is linear, so initial conditions and the baseline path of the
exogenous drivers drop out and cannot differ across vintages: only the coefficients do):

* Units. gw, gcpi: annualised quarterly growth, pp. cf1, cf10: pp. A shock hits in quarter h = 0. Horizon h = 0..12 reported; 0..40 computed for persistence checks.
* Price level. Cumulative CPI price-level deviation after h quarters = (gcpi_0 + ... + gcpi_h)/4 (percent; annualised rate /4).
* Energy and food enter the price equation as growth of the price RELATIVE to wages. Headline convention ("nominal", the Phase 4 convention):
  nominal CPI-energy and CPI-food growth are exogenous and held at baseline unless the shock moves them; relative prices are outputs
  (grpe = gE - gw), so a wage shock lowers relative energy/food prices. The authors' convention ("relative") holds relative prices
  fixed instead, so energy and food prices move one-for-one with wages. Both are available; they differ for every shock that moves wages.
* Oil. Brent log-level deviation -> monthly CPI-energy growth through the Phase 4 bridge (100 dln E_m = c + sum_k b_k 100 dln Oil_{m-k}, k=0..3),
  quarterly gE = 4 x (sum of the three monthly changes) because CPI is a quarter-end value. The bridge is an auxiliary reduced form, identical
  for every vintage (so differences across vintages are due to the four estimated equations only); it is a calibrated assumption, not an estimate of Phase 4c.
* Shock sizes are identical across vintages. A +x% oil shock is a Brent level x% higher (log points 100 ln(1+x/100)).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..scenarios import engine as E
from ..scenarios import oil as O
from ..scenarios import pull as P
from ..scenarios.pin import PHASE4_PULL
from ..simulation.model import LAGS

H = 40                       # horizons h = 0..40 are computed
HREP = 12                    # horizons reported in the headline tables / charts
CONVENTIONS = ("nominal", "relative")
VARS = ("gcpi", "gw", "cf1", "cf10")
VAR_LABEL = {"gcpi": "CPI inflation (annualised, pp)", "gw": "Wage inflation (annualised, pp)",
             "cf1": "1-year expected inflation (pp)", "cf10": "10-year expected inflation (pp)"}
BANDS = (0.05, 0.95)


@dataclass(frozen=True)
class Shock:
    key: str
    label: str
    family: str               # wage | oil | labour | supply | expectations | price
    kind: str                 # impulse | sustained | episode
    size: float
    unit: str
    note: str = ""
    headline: bool = True     # False = supplementary (workbook only)


def shock_catalogue(gscpi_sd: float) -> dict[str, Shock]:
    s = [
        Shock("W1", "Wage equation shock +1pp (one quarter)", "wage", "impulse", 1.0, "pp", "additive residual in the wage equation at h=0"),
        Shock("W2", "Sustained wage path +1pp (exogenous)", "wage", "sustained", 1.0, "pp",
              "wage growth held 1pp above baseline every quarter from h=0 (wage equation switched off): a different exercise from W1"),
        Shock("O10", "Brent +10% (sustained level shift)", "oil", "sustained", 10.0, "%", "Brent 10% higher from the first month of h=0, no reversal"),
        Shock("O30", "Brent +30% (sustained level shift)", "oil", "sustained", 30.0, "%", "log points 26.2, not 3 x 9.5"),
        Shock("O10T", "Brent +10% for four quarters, then reverses", "oil", "episode", 10.0, "%", "temporary episode; supplementary", False),
        Shock("O30T", "Brent +30% for four quarters, then reverses", "oil", "episode", 30.0, "%", "temporary episode; supplementary", False),
        Shock("V1", "V/U +0.5 (sustained level shift)", "labour", "sustained", 0.5, "ratio", "permanent level shift, as the authors' V/U IRF"),
        Shock("V1P", "V/U +0.5 (one quarter)", "labour", "impulse", 0.5, "ratio", "impulse; different exercise from V1"),
        Shock("G1", "GSCPI +1 s.d. (one quarter)", "supply", "impulse", gscpi_sd, "GSCPI units", "impulse (the authors' shortage IRF convention)"),
        Shock("G1S", "GSCPI +1 s.d. (sustained level shift)", "supply", "sustained", gscpi_sd, "GSCPI units", "permanent; a stress test (the price equation takes GSCPI in levels)"),
        Shock("E1", "1-year expectations +1pp (one quarter)", "expectations", "impulse", 1.0, "pp", "additive residual in the cf1 equation at h=0"),
        Shock("E10", "10-year expectations +1pp (one quarter)", "expectations", "impulse", 1.0, "pp", "additive residual in the cf10 equation at h=0"),
        Shock("P1", "CPI price-equation shock +1pp (one quarter)", "price", "impulse", 1.0, "pp", "supplementary: second-round effects of a price surprise", False),
    ]
    return {x.key: x for x in s}


# ---------------------------------------------------------------------------------------------------------------------------------
# Oil bridge (identical for every vintage)

_BRIDGE: dict = {}


def bridge(end: str = "2026-06") -> O.Bridge:
    """Phase 4 bridge (stamped pull `PHASE4_PULL`), estimated through `end` (headline 2026-06 = the Phase 4 bridge)."""
    if end not in _BRIDGE:
        p4 = P.load(PHASE4_PULL)
        cpie, oil = p4["uspric2368"].dropna(), p4["wocaes0935"].dropna()
        _BRIDGE[end] = O.estimate_bridge(cpie.loc[:f"{end}-01"], oil.loc[:f"{end}-01"], end=end)
    return _BRIDGE[end]


def oil_energy_growth(b: np.ndarray, pct: float, kind: str, nq: int) -> np.ndarray:
    """Annualised quarterly CPI-energy growth deviation (pp) for quarters h = 0..nq-1 from a Brent shock of `pct` percent.
    b = bridge lag coefficients (o0..o3). kind 'sustained' (level shift for good) or 'episode' (four quarters, then back)."""
    nm = 3 * nq
    lvl = np.zeros(nm)
    x = 100.0 * np.log1p(pct / 100.0)
    lvl[:] = x if kind == "sustained" else 0.0
    if kind == "episode":
        lvl[:12] = x
    dl = np.diff(lvl, prepend=0.0)
    d = np.zeros(nm)
    for k, bk in enumerate(b):
        d[k:] += bk * dl[:nm - k]
    return 4.0 * d.reshape(nq, 3).sum(axis=1)


# ---------------------------------------------------------------------------------------------------------------------------------
def make_inputs(shock: Shock, convention: str, b: np.ndarray | None, horizon: int = H) -> E.Inputs:
    """Engine inputs for a shock hitting at h = 0 (array index LAGS), all baselines zero."""
    nq = horizon + 1
    T = LAGS + nq
    z = lambda: np.zeros(T)                                        # noqa: E731
    hist = {k: np.zeros(LAGS) for k in E.STATE}
    exog = {"vu": z(), "magpty": z(), "shortagema2": z(), "shortage": z()}
    gE, gF = z(), z()
    add: dict[str, np.ndarray] = {}
    frozen: dict[str, np.ndarray] = {}
    t0 = LAGS
    k = shock.key
    if k in ("W1", "E1", "E10", "P1"):
        eq = {"W1": "gw", "E1": "cf1", "E10": "cf10", "P1": "gcpi"}[k]
        add[eq] = z()
        add[eq][t0] = shock.size
    elif k == "W2":
        frozen["gw"] = z()
        frozen["gw"][t0:] = shock.size
    elif shock.family == "oil":
        if b is None:
            raise ValueError("oil shocks need the bridge coefficients")
        gE[t0:] = oil_energy_growth(b, shock.size, shock.kind, nq)
    elif shock.family == "labour":
        exog["vu"][t0:] = shock.size
        if shock.kind == "impulse":
            exog["vu"][t0 + 1:] = 0.0
    elif shock.family == "supply":
        g = z()
        g[t0:] = shock.size
        if shock.kind == "impulse":
            g[t0 + 1:] = 0.0
        exog["shortage"] = g
        exog["shortagema2"] = pd.Series(g).rolling(2, min_periods=1).mean().values        # trailing 2-quarter mean, baseline deviation 0 before h=0
    else:
        raise KeyError(k)
    rel = {"grpe": z(), "grpf": z()} if convention == "relative" else {}
    return E.Inputs(hist=hist, exog=exog, gE=gE, gF=gF, add=add, frozen=frozen, rel_override=rel,
                    const_override={"gw": 0.0, "gcpi": 0.0})


def run(cs: E.CoefSet, shock: Shock, convention: str = "nominal", b: np.ndarray | None = None, horizon: int = H) -> dict[str, np.ndarray]:
    """Responses (n x horizon+1) of every state variable, h = 0..horizon; `cs` may hold n coefficient draws."""
    p = E.simulate(cs, make_inputs(shock, convention, b, horizon))
    return {v: np.asarray(p[v])[:, LAGS:] for v in E.STATE}


def coefset(names: dict[str, list[str]], values: dict[str, np.ndarray]) -> E.CoefSet:
    return E.CoefSet(names, values)


# ---------------------------------------------------------------------------------------------------------------------------------
# Statistics

def price_level(gcpi: np.ndarray) -> np.ndarray:
    return np.cumsum(gcpi, axis=-1) / 4.0


def _peak(x: np.ndarray, sign: float, hmax: int = HREP) -> tuple[np.ndarray, np.ndarray]:
    seg = x[:, :hmax + 1] * sign
    k = seg.argmax(axis=1)
    return x[np.arange(len(x)), k], k.astype(float)


def half_life(x: np.ndarray, k: np.ndarray, peak: np.ndarray) -> np.ndarray:
    """Quarters after the peak until |x| first falls to half the peak (NaN if it does not within the computed horizon)."""
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        after = np.where(np.abs(x[i, int(k[i]):]) <= 0.5 * abs(peak[i]) + 1e-12)[0]
        if len(after):
            out[i] = after[0]
    return out


def statistics(path: dict[str, np.ndarray], signs: dict[str, float] | None = None) -> dict[tuple[str, str], np.ndarray]:
    """Per-draw statistics: (variable, statistic) -> (n,). `signs` fixes the direction of every peak (from the point estimate)."""
    out: dict[tuple[str, str], np.ndarray] = {}
    for v in VARS:
        x = path[v]
        sg = (signs or {}).get(v)
        if sg is None:
            sg = float(np.sign(x[0, np.abs(x[0, :HREP + 1]).argmax()])) or 1.0
        for h in (0, 1, 4, 8, 12):
            out[(v, f"h={h}")] = x[:, h]
        pk, kk = _peak(x, sg)
        out[(v, "peak (h<=12)")] = pk
        out[(v, "quarter of peak")] = kk
        out[(v, "h=40")] = x[:, 40]
        out[(v, "ratio h=12 / peak")] = x[:, 12] / pk
        out[(v, "half-life from peak (q)")] = half_life(x, kk, pk)
    L = price_level(path["gcpi"])
    W = np.cumsum(path["gw"], axis=-1) / 4.0
    for h in (4, 8, 12):
        out[("gcpi", f"price level, cumulative to h={h} (%)")] = L[:, h]
        out[("gw", f"wage level, cumulative to h={h} (%)")] = W[:, h]
    out[("gcpi", "price level, h=40 (%)")] = L[:, 40]
    out[("gcpi", "peak price level (h<=12, %)")] = _peak(L, float(np.sign(L[0, :HREP + 1][np.abs(L[0, :HREP + 1]).argmax()])) or 1.0)[0]
    return out


def point_signs(path: dict[str, np.ndarray]) -> dict[str, float]:
    return {v: (float(np.sign(path[v][0, np.abs(path[v][0, :HREP + 1]).argmax()])) or 1.0) for v in VARS}
