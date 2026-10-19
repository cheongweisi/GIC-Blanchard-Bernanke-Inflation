"""Model-variable construction, identical to regression_full.do lines 29-52.

All transformations are applied to the *full* raw series, and lags are formed afterwards. (The Stata
code applies `keep` before the lag operators in the regressions, which is why its effective sample
starts in 1990Q1 rather than 1989Q1; the estimator reproduces that explicitly.)
"""
import numpy as np
import pandas as pd

SHORTAGE_PRE_GOOGLE = 5.0  # authors' fill value before 2004Q1 (approx. pre-pandemic mean)


def growth(s: pd.Series) -> pd.Series:
    """Quarterly, annualised log growth: 400 * dln(x)."""
    return 400.0 * np.log(s).diff()


def build_model_data(raw: pd.DataFrame, shortage: pd.Series | None = None,
                     shortage_fill: float = SHORTAGE_PRE_GOOGLE) -> pd.DataFrame:
    """Return the model variables.

    `shortage` overrides the Google Trends column (e.g. GSCPI); missing values are set to `shortage_fill`.
    """
    d = pd.DataFrame(index=raw.index)
    d["gcpi"] = growth(raw["CPIAUCSL"])
    d["gw"] = growth(raw["ECIWAG"])
    gpty = growth(raw["OPHNFB"])
    d["magpty"] = sum(gpty.shift(i) for i in range(8)) / 8.0     # 8-quarter moving average
    d["grpe"] = growth(raw["CPIENGSL"] / raw["ECIWAG"])          # relative price of energy
    d["grpf"] = growth(raw["CPIUFDSL"] / raw["ECIWAG"])          # relative price of food
    d["vu"] = raw["VOVERU"]
    d["cf1"] = raw["EXPINF1YR"]
    d["cf10"] = raw["EXPINF10YR"]
    sh = raw["SHORTAGE"] if shortage is None else shortage.reindex(raw.index)
    d["shortage"] = sh.fillna(shortage_fill)
    # catch-up term: 4-quarter average CPI inflation minus one-year expectation four quarters earlier
    d["diffcpicf"] = sum(d["gcpi"].shift(i) for i in range(4)) / 4.0 - d["cf1"].shift(4)
    d["D2020Q2"] = (d.index == pd.Period("2020Q2")).astype(float)
    d["D2020Q3"] = (d.index == pd.Period("2020Q3")).astype(float)
    return d
