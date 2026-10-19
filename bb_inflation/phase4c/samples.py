"""Estimation vintages of Model B*, all with the production B* specification.

Specification held fixed across vintages (it is the Phase 3 supplement's Model B*): the authors' four equations and restrictions, the
shortage block = 2-quarter trailing mean of GSCPI (`shortagema2`, lag 0 only), V/U 2025Q4 bridged, estimation start 1990Q1, Q2/Q3-2020 wage
dummies included only when those quarters are in the estimation sample (the same rule the production model uses).

  B19  all four equations 1990Q1-2019Q4                       (pre-pandemic sample)
  B23  all four equations 1990Q1-2023Q4                       (through the pandemic and its immediate aftermath)
  B26  all four equations 1990Q1-2026Q2                       (= production Model B*, checked against `extension.models.fit`)
  HYB  wage, cf1, cf10 to 2019Q4, price equation to 2023Q2    (the authors' hybrid design, on B* data and specification: reference)
  AUTH the authors' published hybrid model: their data (Google 'shortage', 5 lags), their coefficient files, 1990Q1-2023Q2 (reference)
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..config import OUTPUTS
from ..data.authors_data import load_raw
from ..data.transforms import build_model_data
from ..estimation.inference import with_hac
from ..estimation.replication import fit_full, fit_precovid
from ..estimation.rls import EquationResult, estimate
from ..extension.models import ModelSpec, fit as production_fit, specs_for_end
from ..supplement import context as C

OUT = OUTPUTS / "phase4c"
OUT.mkdir(parents=True, exist_ok=True)
EQS = ("gw", "gcpi", "cf1", "cf10")
VARIANT = "gscpi_ma2"
START = "1990Q1"


@dataclass(frozen=True)
class Vintage:
    key: str
    label: str
    ends: dict

    def end(self, eq: str) -> str:
        return self.ends[eq]


def _all(end: str) -> dict:
    return {eq: end for eq in EQS}


VINTAGES = {
    "B19": Vintage("B19", "B*-2019", _all("2019Q4")),
    "B23": Vintage("B23", "B*-2023", _all("2023Q4")),
    "B26": Vintage("B26", "B*-2026", _all("2026Q2")),
    "HYB": Vintage("HYB", "Hybrid (B* data)", {"gw": "2019Q4", "cf1": "2019Q4", "cf10": "2019Q4", "gcpi": "2023Q2"}),
}
MAIN = ("B19", "B23", "B26")
LABEL = {**{k: v.label for k, v in VINTAGES.items()}, "AUTH": "Authors (published hybrid)"}

_CACHE: dict = {}


def load() -> tuple[C.Ctx, pd.DataFrame]:
    """The Phase 3 supplement context (pinned pull) and `data_star`, the dataset behind production Model B*."""
    if "ctx" not in _CACHE:
        _CACHE["ctx"] = C.load()
    ctx = _CACHE["ctx"]
    return ctx, ctx.data_star


def fit(data: pd.DataFrame, v: Vintage) -> dict[str, EquationResult]:
    """Restricted-LS fit of every equation to its own sample end; classical covariance (use `hac` for robust)."""
    return {eq: estimate(specs_for_end(VARIANT, v.end(eq))[eq], data, START, v.end(eq)) for eq in EQS}


def hac(res: dict[str, EquationResult], data: pd.DataFrame) -> dict[str, EquationResult]:
    return {eq: with_hac(r, data) for eq, r in res.items()}


def production(data: pd.DataFrame, last: str) -> dict:
    """Production Model B* exactly as Phase 3/4 fit it (for the identity check against B26)."""
    return production_fit(ModelSpec("B", "B"), data, last)


def authors_data() -> pd.DataFrame:
    return build_model_data(load_raw())


def fit_authors(kind: str = "hybrid", data: pd.DataFrame | None = None) -> dict[str, EquationResult]:
    """Re-estimation on the authors' own data (matches their shipped coefficient files to ~5e-6).
    'hybrid' = wage/cf1/cf10 to 2019Q4 + price to 2023Q2 (paper baseline); 'full' = all to 2023Q2 with dummies (what their IRF code reads)."""
    data = authors_data() if data is None else data
    return fit_precovid(data) if kind == "hybrid" else fit_full(data)
