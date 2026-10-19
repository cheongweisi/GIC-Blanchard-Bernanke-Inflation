"""Alternative shortage specifications for the price equation and the datasets they run on.

Only the shortage block of the price equation changes; every other equation, restriction, lag and sample is the
authors'. 'google5' is the authors' specification (five-quarter distributed lag, lags 0-4).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pandas as pd

from ..data.transforms import build_model_data
from ..estimation.equations import L0_4, Block, EquationSpec, base_equations
from ..simulation.general import add_derived
from . import ladder


@dataclass(frozen=True)
class Variant:
    name: str
    label: str
    source: str                                   # 'google' | 'gscpi'
    block: Block | None                           # shortage block in the price equation (None = no shortage term)
    derived: tuple[tuple[str, tuple[str, int]], ...] = ()

    @property
    def derived_dict(self) -> dict[str, tuple[str, int]]:
        return dict(self.derived)

    @property
    def steady_shortage(self) -> float:
        return 5.0 if self.source == "google" else ladder.GSCPI_STEADY


VARIANTS: dict[str, Variant] = {v.name: v for v in [
    Variant("none", "No shortage term", "google", None),
    Variant("google5", "Google, 5 lags (authors)", "google", Block("shortage", L0_4)),
    Variant("gscpi5", "GSCPI, 5 lags (benchmark)", "gscpi", Block("shortage", L0_4)),
    Variant("gscpi3", "GSCPI, lags 0-2", "gscpi", Block("shortage", (0, 1, 2))),
    Variant("gscpi2", "GSCPI, lags 0-1", "gscpi", Block("shortage", (0, 1))),
    Variant("gscpi1", "GSCPI, contemporaneous only", "gscpi", Block("shortage", (0,))),
    Variant("gscpi_ma4", "GSCPI, 4-quarter trailing mean", "gscpi", Block("shortagema4", (0,)),
            (("shortagema4", ("shortage", 4)),)),
    Variant("gscpi_ma2", "GSCPI, 2-quarter trailing mean", "gscpi", Block("shortagema2", (0,)),
            (("shortagema2", ("shortage", 2)),)),
]}


def equations_for(v: Variant, covid_dummies: bool) -> dict[str, EquationSpec]:
    eqs = base_equations(covid_dummies=covid_dummies)
    p = eqs["gcpi"]
    blocks = tuple(b for b in p.blocks if b.var != "shortage") + ((v.block,) if v.block else ())
    summ = tuple(s for s in p.summary_blocks if s != "shortage") + ((v.block.var,) if v.block else ())
    eqs["gcpi"] = dataclasses.replace(p, blocks=blocks, summary_blocks=summ)
    return eqs


def datasets(authors_raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Model data by source: authors' data (Google), Macrobond current pull with Google, Macrobond with GSCPI.
    All use the authors' sample ending 2023Q2 and the authors' pre-2001 V/U and ECI history."""
    by = {c.name[:2]: c for c in ladder.cases()}
    out = {}
    for key, case in (("authors_google", by["L0"]), ("mb_google", by["L5"]), ("mb_gscpi", by["L6"])):
        raw, short, fill = ladder.assemble(authors_raw, case)
        out[key] = build_model_data(raw, shortage=short, shortage_fill=fill)
    return out


def data_for(v: Variant, ds: dict[str, pd.DataFrame], authors: bool = False) -> pd.DataFrame:
    base = ds["authors_google"] if authors else (ds["mb_google"] if v.source == "google" else ds["mb_gscpi"])
    return add_derived(base, v.derived_dict)
