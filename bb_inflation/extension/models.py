"""Models A, B, C for the 2026 extension. All use the authors' four-equation specification (the price equation's
shortage block is `gscpi_ma2` by default; `gscpi5` is the robustness benchmark) and the authors' restrictions.

A  coefficients frozen at an estimation ending 2023Q2 (the original paper's sample end), applied to later data
B  re-estimated through the last complete quarter, unweighted
C  re-estimated through the last complete quarter with exponential weights, half-life 5/10/15 years
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pandas as pd

from ..config import FULL_END
from ..estimation.equations import EquationSpec
from ..estimation.wls import WeightedResult, estimate_weighted
from ..simulation.model import SimModel
from ..validation.specs import VARIANTS, equations_for

EQS = ("gw", "gcpi", "cf1", "cf10")
Q = 4  # quarters per year


@dataclass(frozen=True)
class ModelSpec:
    name: str
    label: str
    variant: str = "gscpi_ma2"
    end: str | None = None                       # None = last complete quarter of the dataset
    half_life_years: float | None = None         # None = unweighted
    weighted_eqs: tuple[str, ...] = EQS          # equations that receive the weights

    def half_life_q(self, eq: str) -> float | None:
        if self.half_life_years is None or eq not in self.weighted_eqs:
            return None
        return self.half_life_years * Q


def specs_for_end(variant: str, end: str) -> dict[str, EquationSpec]:
    """Authors' equations with the Q2/Q3-2020 wage dummies included only once those quarters are in the sample."""
    eqs = equations_for(VARIANTS[variant], covid_dummies=False)
    e = pd.Period(end, "Q")
    dums = tuple(d for d, q in (("D2020Q2", "2020Q2"), ("D2020Q3", "2020Q3")) if e >= pd.Period(q, "Q"))
    eqs["gw"] = dataclasses.replace(eqs["gw"], dummies=dums)
    return eqs


def fit(ms: ModelSpec, data: pd.DataFrame, last_complete: str, start: str = "1990Q1") -> dict[str, WeightedResult]:
    end = ms.end or last_complete
    eqs = specs_for_end(ms.variant, end)
    return {eq: estimate_weighted(eqs[eq], data, start, end, ms.half_life_q(eq)) for eq in EQS}


def sim_model(res: dict) -> SimModel:
    return SimModel.from_results(res)


def standard_models(last_complete: str) -> dict[str, ModelSpec]:
    m = {"A": ModelSpec("A", "A: frozen at 2023Q2", end=FULL_END),
         "B": ModelSpec("B", f"B: re-estimated to {last_complete}"),
         "A5": ModelSpec("A5", "A (gscpi5): frozen at 2023Q2", "gscpi5", FULL_END),
         "B5": ModelSpec("B5", "B (gscpi5): re-estimated", "gscpi5")}
    for h in (5, 10, 15):
        m[f"C{h}"] = ModelSpec(f"C{h}", f"C: exp. weights, half-life {h}y", half_life_years=h)
    return m
