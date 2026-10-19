"""Who and how: attribution of a scenario's deviation from the baseline.

All attribution is of the DEVIATION of the scenario from the baseline of the same information set, model and constant, in
(i) annualised quarterly CPI inflation, (ii) y/y inflation (log approximation of the difference, in pp) and (iii) the CPI price level (%).
The model is linear in its drivers (given the coefficients) so three exact, additive decompositions are available.

1. BY DRIVER ("who"): run the scenario with one driver at a time. Contributions add to the total (checked: the residual is ~1e-12).

2. BY TRANSMISSION LAYER ("how"), by closures that are switched on one after the other:
     direct        price equation only: wages, 1y and 10y expectations held on their baseline paths. First-round effects of
                   nominal energy / food, supply chains, productivity (and the persistence of inflation itself).
     wages         + the wage equation (V/U, expectations held, catch-up, own lags): the wage-price loop.
     expectations  + the two expectations equations: the full model.
   Layer effect = (this closure - previous closure). The split between wages and expectations depends on the order (interaction terms
   are assigned to the later layer); the total does not. For the relative-price offset see below.

3. PROXIMATE (nominal form) accounting of the price equation, from the full run: how much of the inflation deviation is booked through
   nominal energy, nominal food, wages (net of the relative-price offset), lagged inflation, supply chains and productivity. This is an
   accounting identity, not a causal split (wages and lagged inflation are themselves outcomes).

Relative-price offset. Because relative prices are derived from wages (grpe = gE - gw), a wage increase lowers the relative energy and food
prices and therefore *offsets* part of the wage pass-through (net wage weight 0.59 instead of 0.85 in Model B*). That offset sits inside
the 'wages' layer and the 'wages (net)' block, not in the energy block.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from . import engine as E
from . import scenario as S
from .world import LAGS, H_SIM, World

LAYERS = ("direct", "wages", "expectations")


def _views(path_s: np.ndarray, path_b: np.ndarray) -> dict[str, np.ndarray]:
    """Deviation of annualised inflation (grid quarters), y/y (log approx.), CPI price level (%) between two simulated gcpi arrays (n, T)."""
    d = (path_s - path_b)
    a = d[:, LAGS:]
    yoy = np.stack([d[:, t - 3:t + 1].mean(axis=1) for t in range(LAGS, d.shape[1])], axis=1)
    lvl = np.cumsum(a, axis=1) / 4.0
    return {"annualised": a, "yoy": yoy, "level": lvl}


def baseline_run(w: World, scn: S.Scenario | None = None, record: bool = False) -> S.Run:
    """Baseline with the same model options (pass-through scale, wage constant, intercept correction) as `scn`, no driver deviations."""
    base = S.Scenario("base", "baseline")
    if scn is not None:
        base = dataclasses.replace(base, energy_scale=scn.energy_scale, wage_constant=scn.wage_constant,
                                   intercept_correction=scn.intercept_correction)
    return S.run(w, base, record=record)


def total_effect(w: World, scn: S.Scenario) -> dict[str, np.ndarray]:
    rs, rb = S.run(w, scn), baseline_run(w, scn)
    return _views(rs.path["gcpi"], rb.path["gcpi"])


def by_driver(w: World, scn: S.Scenario) -> tuple[pd.DataFrame, float]:
    """Contribution of each active driver by grid quarter. Returns (long table, max |sum of drivers - total| in annualised pp)."""
    rb = baseline_run(w, scn)
    tot = _views(S.run(w, scn).path["gcpi"], rb.path["gcpi"])
    rows, acc = [], {k: 0.0 for k in tot}
    for d in scn.active_drivers():
        v = _views(S.run(w, scn.only(d)).path["gcpi"], rb.path["gcpi"])
        for i, q in enumerate(w.quarters):
            rows.append({"driver": d, "quarter": str(q), "h": i, "annualised_pp": v["annualised"][0, i], "yoy_pp": v["yoy"][0, i],
                         "price_level_pct": v["level"][0, i]})
        for k in acc:
            acc[k] = acc[k] + v[k]
    gap = max(float(np.abs(acc[k] - tot[k]).max()) for k in tot)
    return pd.DataFrame(rows), gap


def _closure_paths(w: World, scn: S.Scenario, rb: S.Run) -> dict[str, np.ndarray]:
    """gcpi deviation arrays under the three closures (point estimate)."""
    frozen_all = {"gw": rb.path["gw"][0], "cf1": rb.path["cf1"][0], "cf10": rb.path["cf10"][0]}
    out = {}
    for name, fr in (("direct", frozen_all), ("wages", {"cf1": frozen_all["cf1"], "cf10": frozen_all["cf10"]}), ("expectations", {})):
        rs = S.run(w, scn)
        inp = rs.inputs.replace(frozen=fr)
        p = E.simulate(rs.cs, inp)
        out[name] = p["gcpi"]
    return out


def by_layer(w: World, scn: S.Scenario) -> tuple[pd.DataFrame, float]:
    """Layers for the whole scenario and for each driver separately. Returns (long table, max |sum of layers - total|)."""
    rb = baseline_run(w, scn)
    rows, gap = [], 0.0
    for label, sc in [("All drivers", scn)] + [(d, scn.only(d)) for d in scn.active_drivers()]:
        cl = _closure_paths(w, sc, rb)
        prev = rb.path["gcpi"]
        tot = S.run(w, sc).path["gcpi"]
        parts = {}
        for name in LAYERS:
            parts[name] = _views(cl[name], prev)
            prev = cl[name]
        tv = _views(tot, rb.path["gcpi"])
        for k in tv:
            gap = max(gap, float(np.abs(sum(parts[n][k] for n in LAYERS) - tv[k]).max()))
        for name in LAYERS:
            for i, q in enumerate(w.quarters):
                rows.append({"scope": label, "layer": name, "quarter": str(q), "h": i, "annualised_pp": parts[name]["annualised"][0, i],
                             "yoy_pp": parts[name]["yoy"][0, i], "price_level_pct": parts[name]["level"][0, i]})
    return pd.DataFrame(rows), gap


def proximate_blocks(w: World, scn: S.Scenario) -> pd.DataFrame:
    """Nominal-form price-equation blocks: scenario minus baseline, annualised pp by grid quarter (point estimate)."""
    rs, rb = S.run(w, scn, record=True), baseline_run(w, scn, record=True)
    bs = E.nominal_price_blocks(rs.cs, rs.path, rs.inputs.gE[0], rs.inputs.gF, LAGS)
    bb = E.nominal_price_blocks(rb.cs, rb.path, rb.inputs.gE[0], rb.inputs.gF, LAGS)
    diff = bs - bb
    diff.index = w.quarters
    diff["total"] = diff.sum(axis=1)
    return diff


def baseline_blocks(w: World, scn: S.Scenario | None = None) -> pd.DataFrame:
    """What the baseline inflation path is made of, in the nominal form of the price equation (levels, annualised pp)."""
    rb = baseline_run(w, scn, record=True)
    df = E.nominal_price_blocks(rb.cs, rb.path, rb.inputs.gE[0], rb.inputs.gF, LAGS)
    df.index = w.quarters
    df["model inflation"] = df.sum(axis=1)
    pub = np.asarray(rb.path["gcpi"][0, LAGS:])
    df["published CPI minus model (nowcast quarter)"] = pub - df["model inflation"].values
    df["inflation used"] = pub
    return df


def baseline_driver_contributions(w: World, vu_ref: float, magpty_ref: float = 2.0, short_ref: float = -0.035) -> pd.DataFrame:
    """Phase 3-style decomposition of the BASELINE forecast: baseline minus a counterfactual in which one input sits at its neutral
    reference (Phase 3 conventions): relative energy / food prices constant (grpe = 0, grpf = 0), GSCPI at its fill/steady value, V/U at
    its 2019Q4 value, productivity growth 2%. Annualised pp by grid quarter; 'other' = what remains with every input neutral
    (initial conditions, constants, expectations)."""
    rb = baseline_run(w)
    T = w.T
    nanrel = np.full(T, np.nan)
    first = LAGS + (1 if w.nowcast else 0)

    def run_with(**kw) -> np.ndarray:
        inp = rb.inputs
        ex = dict(inp.exog)
        rel = {}
        if kw.get("energy"):
            r = nanrel.copy(); r[first:] = 0.0; rel["grpe"] = r
        if kw.get("food"):
            r = nanrel.copy(); r[first:] = 0.0; rel["grpf"] = r
        if kw.get("short"):
            sh = w.base_shortage.copy(); sh[LAGS:] = short_ref
            ma2 = pd.Series(sh).rolling(2, min_periods=2).mean().values.copy(); ma2[:LAGS] = ex["shortagema2"][:LAGS]
            ex["shortagema2"] = ma2
        if kw.get("vu"):
            v = ex["vu"].copy(); v[LAGS:] = vu_ref; ex["vu"] = v
        if kw.get("prod"):
            m = ex["magpty"].copy(); m[LAGS:] = magpty_ref; ex["magpty"] = m
        p = E.simulate(rb.cs, inp.replace(exog=ex, rel_override=rel))
        return p["gcpi"][0, LAGS:]

    base = rb.path["gcpi"][0, LAGS:]
    out = {}
    for lab, key in (("Energy", "energy"), ("Food", "food"), ("Supply chains", "short"), ("Labour market (V/U vs 2019Q4)", "vu"), ("Productivity", "prod")):
        out[lab] = base - run_with(**{key: True})
    out["Other (initial conditions, constants, expectations)"] = run_with(energy=True, food=True, short=True, vu=True, prod=True)
    out["Baseline model inflation"] = base
    return pd.DataFrame(out, index=w.quarters)


def energy_chain(w: World, scn: S.Scenario) -> pd.DataFrame:
    """Oil -> CPI energy -> relative energy price -> prices, as % deviations of LEVELS from the baseline, plus the inflation effects."""
    rs, rb = S.run(w, scn), baseline_run(w, scn)
    ms, mb = S.measures(w, rs), S.measures(w, rb)
    dev = lambda c: 100.0 * np.log(ms[c] / mb[c])                                          # noqa: E731
    v = _views(rs.path["gcpi"], rb.path["gcpi"])
    out = pd.DataFrame({"oil, Brent (% dev., quarter average)": 100.0 * np.log(ms["oil_usd_qavg"] / mb["oil_usd_qavg"]),
                        "CPI energy, nominal (% dev., level)": dev("cpi_energy_level"),
                        "wages, ECI (% dev., level)": dev("eci_level"),
                        "relative energy price (% dev., level)": dev("rel_energy_level"),
                        "CPI price level (% dev.)": v["level"][0],
                        "inflation, annualised (pp)": v["annualised"][0], "inflation, y/y (pp)": v["yoy"][0],
                        "wage growth, annualised (pp)": (ms["gw"] - mb["gw"]).values,
                        "1y expectations (pp)": (ms["cf1"] - mb["cf1"]).values}, index=w.quarters)
    return out
