"""The Phase 4 scenario library.

Every scenario is a deviation from the baseline of the same information set. Grid index 0 is 2026Q3 (published, never shocked in the
nowcast information set); index 1 is 2026Q4 (the first forecast quarter) ... index 12 is 2029Q3.

Sizes are anchored to history (computed in scripts/run_p4_main.py, `anchors.csv`): about one standard deviation of the year-on-year change
of the Brent price (0.3), 2019Q4 for the V/U 'tight' case (V/U 1.19 against 1.02 now), one standard deviation of GSCPI. They are illustrations
of a mechanism, not probabilities.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .scenario import Scenario, scenario
from .world import H_SIM, World

N = H_SIM


def step(size: float, start: int = 1) -> np.ndarray:
    a = np.zeros(N)
    a[start:] = size
    return a


def ramp(size: float, quarters: int, start: int = 1) -> np.ndarray:
    a = np.zeros(N)
    for i in range(start, N):
        a[i] = size * min((i - start + 1) / quarters, 1.0)
    return a


def decay(size: float, rho: float, start: int = 1) -> np.ndarray:
    a = np.zeros(N)
    for i in range(start, N):
        a[i] = size * rho ** (i - start)
    return a


def pulse(size: float, start: int, hold: int, fade: int) -> np.ndarray:
    """Rises to `size` in quarter `start`, stays for `hold` quarters, then fades linearly to zero over `fade` quarters."""
    a = np.zeros(N)
    for i in range(N):
        if start <= i < start + hold:
            a[i] = size
        elif start + hold <= i < start + hold + fade:
            a[i] = size * (1 - (i - start - hold + 1) / (fade + 1))
    return a


def oil_path_to(target_usd: float, by_month: str, start_usd: float, months: pd.DatetimeIndex) -> pd.Series:
    """Monthly Brent path: linear from start_usd (first month) to target_usd at `by_month`, flat afterwards."""
    m = np.array([(d.year * 12 + d.month) for d in months], float)
    t1 = pd.Timestamp(by_month)
    x1 = t1.year * 12 + t1.month
    return pd.Series(np.interp(m, [m[0], x1], [start_usd, target_usd]), index=months)


def build(w: World) -> dict[str, Scenario]:
    fm = pd.date_range("2026-10-01", "2029-12-01", freq="MS")
    oct_level = float(w.oil_curve["futures"].iloc[0])
    S: dict[str, Scenario] = {}

    def add(s: Scenario) -> None:
        S[s.key] = s

    # ---------------------------------------------------------------- oil / energy
    add(scenario("oil_flat", "Oil stays at today's level",
                 "Brent stays at the October 2026 level (about $111) instead of following the backwardated futures curve (about $95 in 2027, $75 in 2029).",
                 "Oil", oil_monthly_usd=w.oil_curve["flat_oct"]))
    add(scenario("oil_up30", "Oil +30% above the futures curve (persistent)",
                 "Brent 30% above the baseline curve from 2026Q4 and for the whole horizon: about one standard deviation of annual Brent changes, a persistent supply loss.",
                 "Oil", oil_dev_pct=step(30.0)))
    add(scenario("oil_dn30", "Oil 30% below the futures curve (persistent)",
                 "Mirror image: Brent 30% below the baseline curve from 2026Q4 (demand slowdown or supply recovery).",
                 "Oil", oil_dev_pct=step(-30.0)))
    add(scenario("oil_spike", "Temporary oil spike in 2027 (+50%, fading)",
                 "A new supply disruption: Brent 50% above the curve in 2027Q1-Q2, fading linearly to the curve over the next four quarters.",
                 "Oil", oil_dev_pct=pulse(50.0, 2, 2, 4)))
    add(scenario("oil_norm", "Oil normalises quickly to $70",
                 "Brent falls linearly from $111 to $70 by June 2027 and stays there (the pre-spike range was $62-71): the spike is reversed faster than the market curve implies.",
                 "Oil", oil_monthly_usd=oil_path_to(70.0, "2027-06-01", oct_level, fm)))
    add(scenario("oil_steo", "Oil follows the EIA STEO path",
                 "Brent follows the EIA Short-Term Energy Outlook of the pull (about $95 in 2027Q1, $74 in 2027Q4) and then the futures curve's month-to-month changes: below the futures curve.",
                 "Oil", oil_monthly_usd=w.oil_curve["steo"]))
    # ---------------------------------------------------------------- labour market, supply chains, food, productivity, expectations
    add(scenario("vu_tight", "Labour market tightens (V/U back to its 2019Q4 level)",
                 "V/U rises by 0.17 over four quarters, from 1.02 to 1.19, its 2019Q4 value, and stays: a demand-led tightening.",
                 "Labour market", vu_dev=ramp(0.17, 4)))
    add(scenario("vu_loose", "Labour market cools (V/U falls by 0.2)",
                 "V/U falls by 0.2 over four quarters, from 1.02 to 0.82, and stays.",
                 "Labour market", vu_dev=ramp(-0.2, 4)))
    add(scenario("gscpi_up", "Supply-chain pressure (GSCPI +1.0, persistent)",
                 "GSCPI 1.0 above baseline from 2026Q4, decaying with rho = 0.8 (half-life about 3 quarters): one standard deviation of GSCPI, a renewed but not extreme disruption.",
                 "Supply chains", gscpi_dev=decay(1.0, 0.8)))
    add(scenario("food_up", "Food prices +8% (nominal, permanent)",
                 "Nominal CPI food 8% above its baseline path, reached over four quarters and kept (the baseline path rises with wages).",
                 "Food", food_dev_pct=ramp(8.0, 4)))
    add(scenario("prod_dn", "Productivity growth 1 pp lower for two years",
                 "Trend productivity growth lower by 1 pp (annualised) in 2026Q4-2028Q3: slower supply growth.",
                 "Productivity", prod_growth_dev=np.r_[0.0, -np.ones(8), np.zeros(N - 9)]))
    add(scenario("expect_up", "Expectations de-anchor (1y +0.5 pp, 10y +0.2 pp)",
                 "A shock of +0.5 pp to one-year expected inflation in each of the next four quarters (not cumulated: the equation is persistent) and +0.05 pp per quarter to ten-year expectations: "
                 "a structural risk scenario; the shock is to the expectations equations, not to a driver.",
                 "Expectations", cf1_shock=pulse(0.5, 1, 4, 0), cf10_shock=pulse(0.05, 1, 4, 0)))
    # ---------------------------------------------------------------- combinations
    add(scenario("adverse_supply", "Adverse supply bundle",
                 "Oil +30% (persistent), GSCPI +1.0 (decaying), productivity growth 1 pp lower for two years.",
                 "Combined", oil_dev_pct=step(30.0), gscpi_dev=decay(1.0, 0.8), prod_growth_dev=np.r_[0.0, -np.ones(8), np.zeros(N - 9)]))
    add(scenario("benign", "Benign bundle (disinflation)",
                 "Oil normalises quickly to $70, V/U falls by 0.2, GSCPI 0.5 below baseline throughout.",
                 "Combined", oil_monthly_usd=oil_path_to(70.0, "2027-06-01", oct_level, fm), vu_dev=ramp(-0.2, 4), gscpi_dev=step(-0.5)))
    add(scenario("overheating", "Overheating bundle (demand-led, oil stays high)",
                 "V/U back to 1.19, oil stays at the October level, expectations drift up (as in the de-anchoring scenario).",
                 "Combined", vu_dev=ramp(0.17, 4), oil_monthly_usd=w.oil_curve["flat_oct"],
                 cf1_shock=pulse(0.5, 1, 4, 0), cf10_shock=pulse(0.05, 1, 4, 0)))
    return S


HEADLINE = ("oil_flat", "oil_up30", "oil_dn30", "oil_norm", "vu_tight", "gscpi_up", "adverse_supply", "benign")
HAIRCUT_SET = ("oil_flat", "oil_up30", "oil_dn30", "oil_spike", "oil_norm", "oil_steo", "adverse_supply", "benign", "overheating")
HAIRCUT = 0.8
