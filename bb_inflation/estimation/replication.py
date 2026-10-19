"""The authors' two published estimation runs, expressed with the declarative equation specs."""
import pandas as pd

from ..config import FULL_END, PRECOVID_END, SAMPLE_START
from .equations import EquationSpec, base_equations
from .rls import EquationResult, estimate_model


def fit_full(data: pd.DataFrame, equations: dict[str, EquationSpec] | None = None,
             end: str = FULL_END) -> dict[str, EquationResult]:
    """regression_full.do: all four equations over 1990Q1-`end`, wage equation with Q2/Q3-2020 dummies."""
    eqs = equations or base_equations(covid_dummies=True)
    return estimate_model(data, eqs, {k: end for k in eqs}, SAMPLE_START)


def fit_precovid(data: pd.DataFrame, equations: dict[str, EquationSpec] | None = None,
                 end: str = FULL_END, precovid_end: str = PRECOVID_END) -> dict[str, EquationResult]:
    """regression_pre_covid.do: wage/cf1/cf10 end 2019Q4 (no dummies); price equation stays full-sample."""
    eqs = equations or base_equations(covid_dummies=False)
    ends = {k: precovid_end for k in eqs}
    ends["gcpi"] = end
    return estimate_model(data, eqs, ends, SAMPLE_START)


def coef_table(results: dict[str, EquationResult]) -> dict[str, pd.Series]:
    return {k: r.coef for k, r in results.items()}
