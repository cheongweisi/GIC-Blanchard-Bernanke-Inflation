"""Loader for the authors' public estimation dataset (Regression_Data.dta).

Raw columns (see the 'Data Dictionary' sheet of Regression_Data.xlsx):
CPIAUCSL, CPIENGSL, CPIUFDSL (CPI all items / energy / food, SA, quarterly mean), OPHNFB (nonfarm
productivity), ECIWAG (ECI wages & salaries, private; spliced pre-2001), VOVERU (V/U; Barnichon
pre-2001), EXPINF1YR / EXPINF10YR (Cleveland Fed), SHORTAGE (Google Trends 'shortage', from 2004Q1),
GSCPI (NY Fed, quarterly mean), PCEPI, SPF1YR, SPF10YR.
"""
import pandas as pd

from ..config import PUBLIC_DATA


def load_raw() -> pd.DataFrame:
    """Raw quarterly data, PeriodIndex(freq='Q'), 1947Q1-2023Q2."""
    d = pd.read_stata(PUBLIC_DATA / "Regression_Data.dta")
    d.index = pd.PeriodIndex(d["Date"].str.replace(" ", ""), freq="Q", name="period")
    d = d.drop(columns="Date")
    # SPF columns are stored as strings in the .dta
    for c in ("SPF1YR", "SPF10YR"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d
