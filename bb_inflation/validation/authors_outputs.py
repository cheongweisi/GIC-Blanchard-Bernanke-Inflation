"""Readers for the authors' shipped output files (used as validation targets and to isolate simulation
code from estimation differences)."""
import pandas as pd

from ..config import CORE, OUT_FULL, OUT_PRECOVID
from ..estimation.equations import EquationSpec, base_equations
from ..simulation.model import SimModel

COEF_FILES = {"full": (OUT_FULL, "eq_coefficients.xlsx", True),
              "precovid": (OUT_PRECOVID, "eq_coefficients_restricted.xlsx", False)}


def authors_model(run: str = "full") -> SimModel:
    """SimModel built from the authors' coefficient workbook (positional match to our names)."""
    folder, fname, dummies = COEF_FILES[run]
    eqs: dict[str, EquationSpec] = base_equations(covid_dummies=dummies)
    coefs = {}
    for eq, spec in eqs.items():
        vals = pd.read_excel(folder / fname, sheet_name=eq).iloc[:, 1].values
        names = spec.regressors()
        assert len(vals) == len(names), (eq, len(vals), len(names))
        coefs[eq] = pd.Series(vals, index=names)
    return SimModel(coefs)


def authors_sim_data(run: str = "full") -> pd.DataFrame:
    folder = COEF_FILES[run][0]
    name = "eq_simulations_data.xls" if run == "full" else "eq_simulations_data_restricted.xls"
    d = pd.read_excel(folder / name)
    d.index = pd.PeriodIndex(d["period"], freq="Q", name="period")
    d = d.drop(columns="period").rename(columns={"dummyq2_2020": "D2020Q2", "dummyq3_2020": "D2020Q3"})
    return d


def read_core(sub: str, name: str) -> pd.DataFrame:
    return pd.read_excel(CORE / sub / "Output Data" / name)
