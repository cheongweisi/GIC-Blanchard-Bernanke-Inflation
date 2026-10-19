"""Scenario specification, translation into engine inputs, and outputs.

A scenario states assumptions about *exogenous* drivers as deviations from the baseline of the same information set:

  oil          Brent (USD): a quarterly % deviation from the baseline curve (interpolated to months), or a full monthly level path
  CPI energy   by default derived from oil through the bridge; may alternatively be shifted directly (nominal level deviation, %)
  food         nominal CPI food level deviation (%), applied to the baseline nominal food path
  GSCPI, V/U   additive level deviations
  productivity growth deviation (pp, annualised; enters the 8-quarter average)
  expectations / price / wage shocks: additive equation shocks (pp) - the structural 'risk' scenarios; not drivers in the model's sense

Relative energy and food prices cannot be specified: they are outputs (engine.py). `scenario()` raises if asked to.
Deviations are defined on the 13 grid quarters (2026Q3-2029Q3); in the nowcast information set the first grid quarter (2026Q3) is
fixed by published data and any deviation there is ignored (set to zero).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import engine as E
from . import oil as O
from .world import H_SIM, LAGS, World, neutral_wage_constant

DRIVERS = ("Oil / energy", "Food", "Supply chains (GSCPI)", "Labour market (V/U)", "Productivity", "Expectations / price / wage shocks")
FORBIDDEN = ("rel_energy", "relative_energy", "rel_food", "relative_food", "grpe", "grpf", "relative_price")


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    description: str = ""
    category: str = ""
    oil_dev_pct: tuple | None = None            # quarterly % deviation of Brent from baseline, 13 values
    oil_monthly_usd: pd.Series | None = None    # alternative: full monthly Brent path (Oct 2026 on), overrides oil_dev_pct
    cpi_energy_dev_pct: tuple | None = None     # nominal CPI energy level deviation (%) added to the bridge result
    food_dev_pct: tuple | None = None
    gscpi_dev: tuple | None = None
    vu_dev: tuple | None = None
    prod_growth_dev: tuple | None = None        # pp (annualised) deviation of quarterly productivity growth
    cf1_shock: tuple | None = None              # additive shocks, pp
    cf10_shock: tuple | None = None
    price_shock: tuple | None = None
    wage_shock: tuple | None = None
    energy_scale: float = 1.0                   # multiplier on the price-equation energy coefficients (pass-through sensitivity)
    wage_constant: str = "estimated"            # 'estimated' | 'neutral'
    intercept_correction: float = 0.0           # pp added to the price equation in the first 4 forecast quarters (sensitivity)

    def only(self, driver: str) -> "Scenario":
        """The scenario with every other driver switched off (for the one-at-a-time attribution)."""
        keep = {"Oil / energy": ("oil_dev_pct", "oil_monthly_usd", "cpi_energy_dev_pct"), "Food": ("food_dev_pct",),
                "Supply chains (GSCPI)": ("gscpi_dev",), "Labour market (V/U)": ("vu_dev",), "Productivity": ("prod_growth_dev",),
                "Expectations / price / wage shocks": ("cf1_shock", "cf10_shock", "price_shock", "wage_shock")}[driver]
        allf = [f for f in ("oil_dev_pct", "oil_monthly_usd", "cpi_energy_dev_pct", "food_dev_pct", "gscpi_dev", "vu_dev", "prod_growth_dev",
                            "cf1_shock", "cf10_shock", "price_shock", "wage_shock")]
        return dataclasses.replace(self, **{f: None for f in allf if f not in keep})

    def active_drivers(self) -> list[str]:
        out = []
        for d in DRIVERS:
            s = self.only(d)
            if any(getattr(s, f) is not None for f in ("oil_dev_pct", "oil_monthly_usd", "cpi_energy_dev_pct", "food_dev_pct", "gscpi_dev",
                                                       "vu_dev", "prod_growth_dev", "cf1_shock", "cf10_shock", "price_shock", "wage_shock")):
                out.append(d)
        return out


def scenario(key: str, label: str, description: str = "", category: str = "", **kw) -> Scenario:
    bad = [k for k in kw if any(f in k.lower() for f in FORBIDDEN)]
    if bad:
        raise ValueError(f"{bad}: relative energy/food prices cannot be scenario inputs (wages are endogenous). Specify oil, CPI energy "
                         "(nominal) or CPI food (nominal); the relative price is derived in every quarter.")
    for k, v in list(kw.items()):
        if isinstance(v, (list, np.ndarray)):
            kw[k] = tuple(np.asarray(v, float))
    return Scenario(key, label, description, category, **kw)


def _vec(x, nowcast: bool, default: float = 0.0) -> np.ndarray:
    a = np.full(H_SIM, default) if x is None else np.asarray(x, float).copy()
    assert len(a) == H_SIM, "deviation paths have one value per grid quarter (13)"
    if nowcast:
        a[0] = default
    return a


def _growth_of_level_dev(dev_pct: np.ndarray) -> np.ndarray:
    """Annualised growth (400 dln) implied by a path of % level deviations from baseline (0 before the grid)."""
    ln = np.log1p(np.r_[0.0, dev_pct] / 100.0)
    return 400.0 * np.diff(ln)


@dataclass
class Run:
    scn: Scenario
    path: E.Path
    inputs: E.Inputs
    gE_q: np.ndarray                   # (n, 13) quarterly annualised CPI energy growth used
    oil_m: pd.Series                   # monthly oil path used
    cs: E.CoefSet


def make_inputs(w: World, scn: Scenario, n: int = 1, cs: E.CoefSet | None = None, bridge_coefs: np.ndarray | None = None,
                noise: dict | None = None, oil_baseline: str = "futures", record: bool = False) -> tuple[E.Inputs, np.ndarray, pd.Series, E.CoefSet]:
    nc = w.nowcast
    cs = cs if cs is not None else w.cs_point
    bc = bridge_coefs if bridge_coefs is not None else w.bridge.point()
    T = w.T

    # ---- oil -> CPI energy (nominal), per draw
    base_oil = w.oil_series(oil_baseline)
    months = w.months
    if scn.oil_monthly_usd is not None:
        oil_m = pd.concat([w.oil_actual.loc[:"2026-09-01"], scn.oil_monthly_usd]).sort_index()
    elif scn.oil_dev_pct is not None:
        dev = _vec(scn.oil_dev_pct, nc)[1:]                    # Q3 2026 oil is observed: deviations start with the first forecast quarter
        mult = pd.Series(O.deviation_to_monthly(dev, w.quarters[1], months), index=months)
        oil_m = base_oil.copy()
        common = months.intersection(oil_m.index)
        oil_m.loc[common] = oil_m.loc[common].values * mult.loc[common].values
    else:
        oil_m = base_oil
    # months actually simulated for oil: grid months; in nowcast mode Q3 is actual (oil actual through Sep 2026, same in all paths)
    nz = None if noise is None else noise.get("bridge")
    mg = O.monthly_energy_growth(bc, oil_m, str(months[0].date()), str(months[-1].date()), noise=nz)          # (n, 39)
    gEq = O.quarterly_energy_growth(mg)                                                                          # (n, 13)
    if scn.cpi_energy_dev_pct is not None:
        gEq = gEq + _growth_of_level_dev(_vec(scn.cpi_energy_dev_pct, nc))[None, :]
    if nc:
        gEq[:, 0] = w.q3["gE"]
    gE = np.concatenate([np.broadcast_to(w.gE_hist, (gEq.shape[0], LAGS)), gEq], axis=1)

    # ---- food: nominal path fixed
    gFq = w.gF_base[LAGS:].copy()
    if scn.food_dev_pct is not None:
        gFq = gFq + _growth_of_level_dev(_vec(scn.food_dev_pct, nc))
    gF = np.r_[w.gF_hist, gFq]

    # ---- other exogenous drivers
    vu = w.base_exog["vu"].copy()
    vu[LAGS:] += _vec(scn.vu_dev, nc)
    dg = _vec(scn.prod_growth_dev, nc)
    dgfull = np.r_[np.zeros(LAGS), dg]
    dmag = np.array([sum(dgfull[max(0, t - j)] if t - j >= 0 else 0.0 for j in range(8)) / 8.0 for t in range(T)])
    magpty = w.base_exog["magpty"] + dmag
    short = w.base_shortage.copy()
    short[LAGS:] += _vec(scn.gscpi_dev, nc)
    ma2 = pd.Series(short).rolling(2, min_periods=2).mean().values.copy()
    ma2[:LAGS] = w.base_exog["shortagema2"][:LAGS]
    exog = {"vu": vu, "magpty": magpty, "shortagema2": ma2}

    add: dict[str, np.ndarray] = {}
    for eq, f in (("cf1", scn.cf1_shock), ("cf10", scn.cf10_shock), ("gcpi", scn.price_shock), ("gw", scn.wage_shock)):
        if f is not None:
            add[eq] = np.r_[np.zeros(LAGS), _vec(f, nc)]
    if scn.intercept_correction:
        a = np.zeros(T)
        k0 = LAGS + (1 if nc else 0)
        a[k0:k0 + 4] = scn.intercept_correction
        add["gcpi"] = add.get("gcpi", np.zeros(T)) + a
    if noise is not None and "eq" in noise:                       # bootstrap residuals (n, T) per equation
        for eq, arr in noise["eq"].items():
            add[eq] = add.get(eq, 0.0) + arr
    cs_use = cs.scaled("gcpi", "grpe", scn.energy_scale) if scn.energy_scale != 1.0 else cs
    const_override = {}
    if scn.wage_constant == "neutral":
        short_star = -0.035                                       # GSCPI_STEADY (authors' convention)
        const_override = {"gw": neutral_wage_constant(cs_use, float(w.base_exog["vu"][LAGS - 1]), float(w.base_exog["magpty"][LAGS - 1]), short_star)}
    elif scn.wage_constant != "estimated":
        raise ValueError(scn.wage_constant)
    inp = E.Inputs(hist=w.hist, exog=exog, gE=gE, gF=gF, add=add, known=w.known, const_override=const_override)
    return inp, gEq, oil_m, cs_use


def run(w: World, scn: Scenario, n: int | None = None, oil_baseline: str = "futures", record: bool = False,
        noise: dict | None = None, bridge_coefs: np.ndarray | None = None) -> Run:
    """n=None: point estimate. n='all': the stored coefficient draws (with the stored bridge draws).
    bridge_coefs: alternative oil-bridge coefficients (1 x 5) for the point estimate (bridge sensitivities)."""
    if n is None:
        cs, bc = w.cs_point, (w.bridge.point() if bridge_coefs is None else np.asarray(bridge_coefs, float).reshape(1, -1))
    else:
        cs, bc = w.cs_draws, w.bridge_draws
    inp, gEq, oil_m, cs_use = make_inputs(w, scn, cs=cs, bridge_coefs=bc, noise=noise, oil_baseline=oil_baseline)
    p = E.simulate(cs_use, inp, record=record)
    return Run(scn, p, inp, gEq, oil_m, cs_use)


def finalise(w: World) -> World:
    """Fix the baseline nominal CPI food path: food keeps pace with baseline wages (relative food price constant)."""
    T = w.T
    rel = np.full(T, np.nan)
    rel[LAGS + (1 if w.nowcast else 0):] = 0.0
    w.gF_base = np.r_[w.gF_hist, np.zeros(H_SIM)]
    if w.nowcast:
        w.gF_base[LAGS] = w.q3["gF"]
    base = Scenario("peg", "peg")
    inp, _, _, cs = make_inputs(w, base)
    inp = inp.replace(rel_override={"grpf": rel})
    p = E.simulate(cs, inp)
    first = LAGS + (1 if w.nowcast else 0)
    w.gF_base[first:] = p["gw"][0, first:]
    return w


# ---------------------------------------------------------------------------------------------------------------
# Measures

def measures(w: World, r: Run, idx: int = 0) -> pd.DataFrame:
    """Quarterly table for draw `idx` of a run (grid quarters), model quantities and the energy transmission chain."""
    s = {k: v[idx] for k, v in r.path.s.items()}
    gc = s["gcpi"]
    yoy_log = np.array([gc[max(0, t - 3):t + 1].mean() if t >= 3 else np.nan for t in range(len(gc))])
    lvl = 100.0 * np.exp(np.cumsum(np.r_[0.0, gc[LAGS:]]) / 400.0)[1:]
    gEv = np.asarray(r.inputs.gE)[idx if np.ndim(r.inputs.gE) > 1 else slice(None)][LAGS:]
    lnE = np.cumsum(gEv / 400.0)
    gFv = np.asarray(r.inputs.gF)[LAGS:]
    lnF = np.cumsum(gFv / 400.0)
    lnW = np.cumsum(s["gw"][LAGS:] / 400.0)
    q = w.quarters
    oil = r.oil_m
    oil_q = [float(oil.loc[pd.date_range(p.start_time, periods=3, freq="MS")].mean()) for p in q]
    oil_e = [float(oil.loc[pd.date_range(p.start_time, periods=3, freq="MS")[-1]]) for p in q]
    df = pd.DataFrame({
        "gcpi_ann": gc[LAGS:], "yoy_log": yoy_log[LAGS:], "yoy_pct": 100.0 * (np.exp(yoy_log[LAGS:] / 100.0) - 1.0),
        "cpi_level": lvl, "gw": s["gw"][LAGS:], "cf1": s["cf1"][LAGS:], "cf10": s["cf10"][LAGS:], "diffcpicf": s["diffcpicf"][LAGS:],
        "gE_nominal": gEv,
        "gF_nominal": gFv, "grpe": s["grpe"][LAGS:], "grpf": s["grpf"][LAGS:],
        "oil_usd_qavg": oil_q, "oil_usd_qend": oil_e,
        "cpi_energy_level": 100.0 * np.exp(lnE), "cpi_food_level": 100.0 * np.exp(lnF), "eci_level": 100.0 * np.exp(lnW),
        "rel_energy_level": 100.0 * np.exp(lnE - lnW), "rel_food_level": 100.0 * np.exp(lnF - lnW),
    }, index=q)
    return df


def horizon_summary(m: pd.DataFrame, nowcast: bool) -> dict[str, float]:
    """1-3 year summary of a quarterly table: y/y at +4/+8/+12 quarters from the first grid quarter and Q4/Q4 calendar y/y."""
    out = {}
    for lab, k in (("1y", 4), ("2y", 8), ("3y", 12)):
        out[f"yoy {lab} ahead ({m.index[k]})"] = float(m["yoy_pct"].iloc[k])
    for yr in (2026, 2027, 2028):
        out[f"Q4/Q4 {yr}"] = float(m.loc[pd.Period(f"{yr}Q4", "Q"), "yoy_pct"])
    out["avg ann. inflation next 4q"] = float(m["gcpi_ann"].iloc[1:5].mean())
    out["avg ann. inflation q5-q8"] = float(m["gcpi_ann"].iloc[5:9].mean())
    out["avg ann. inflation q9-q12"] = float(m["gcpi_ann"].iloc[9:13].mean())
    return out
