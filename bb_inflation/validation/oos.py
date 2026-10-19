"""Out-of-sample forecast validation, 2020Q1-2023Q2, using realised exogenous inputs.

Three estimation regimes are kept apart:
  genuine    all four equations estimated through 2019Q4 only (no wage dummies): a true out-of-sample test
  hybrid     the authors' published design: wage/expectation equations through 2019Q4, price equation through
             2023Q2 (so its shortage coefficients use 2020-23 data: NOT out-of-sample for the price equation)
  insample   everything through 2023Q2 with the COVID dummies in the wage equation (fit, not forecast)
Forecasts are either dynamic (iterated from the four actual quarters 2019Q1-Q4; endogenous lags come from the
model's own forecasts, residuals zero, exogenous drivers as realised) or one-step-ahead (all lags actual).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import FULL_END, PRECOVID_END
from ..estimation.rls import EquationResult, estimate_model
from ..simulation.model import ENDO, LAGS, SimModel
from .specs import Variant, equations_for

VARS = ("gw", "gcpi", "cf1", "cf10")
START_FC, END_FC = "2020Q1", FULL_END


def fit_regime(v: Variant, data: pd.DataFrame, regime: str) -> dict[str, EquationResult]:
    eqs = equations_for(v, covid_dummies=(regime == "insample"))
    ends = {k: PRECOVID_END for k in eqs}
    if regime == "hybrid":
        ends["gcpi"] = END_FC
    if regime == "insample":
        ends = {k: END_FC for k in eqs}
    return estimate_model(data, eqs, ends, "1990Q1")


END_FC = FULL_END


def dynamic_forecast(results: dict[str, EquationResult], data: pd.DataFrame, v: Variant) -> pd.DataFrame:
    model = SimModel.from_results(results)
    first = data.index.get_loc(pd.Period(START_FC, "Q"))
    w = data.iloc[first - LAGS: data.index.get_loc(pd.Period(END_FC, "Q")) + 1]
    names = ["grpe", "grpf", "vu", "shortage", "magpty", *v.derived_dict]
    exog = {n: w[n].values.astype(float) for n in names}
    dummies = {n: w[n].values.astype(float) for n in ("D2020Q2", "D2020Q3")}
    hist = {k: w[k].values[:LAGS].astype(float) for k in ENDO}
    out = model.simulate(hist, exog, dummies=dummies)
    return pd.DataFrame({k: out[k][LAGS:] for k in VARS}, index=w.index[LAGS:])


def one_step(results: dict[str, EquationResult], data: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({k: results[k].predict(data).loc[START_FC:END_FC] for k in VARS})


def ar4_forecast(data: pd.DataFrame, end: str = PRECOVID_END) -> pd.DataFrame:
    """AR(4) with constant for each variable, estimated 1990Q1-`end` by OLS, iterated from 2019Q4."""
    out = {}
    h = pd.period_range(START_FC, END_FC, freq="Q")
    for k in VARS:
        s = data[k]
        X = pd.concat([s.shift(i) for i in range(1, 5)], axis=1)
        X.columns = [f"l{i}" for i in range(1, 5)]
        X["c"] = 1.0
        fr = pd.concat([s.rename("y"), X], axis=1).loc["1990Q1":end].dropna()
        b = np.linalg.lstsq(fr.drop(columns="y").values, fr["y"].values, rcond=None)[0]
        path = list(s.loc[:end].iloc[-4:].values)
        f = []
        for _ in h:
            nxt = b[4] + sum(b[i] * path[-1 - i] for i in range(4))
            path.append(nxt)
            f.append(nxt)
        out[k] = f
    return pd.DataFrame(out, index=h)


def metrics(fc: pd.DataFrame, data: pd.DataFrame, label: dict) -> list[dict]:
    rows = []
    act = data[list(VARS)].loc[START_FC:END_FC]
    err = fc.loc[START_FC:END_FC] - act
    ex = ~err.index.isin([pd.Period("2020Q2", "Q"), pd.Period("2020Q3", "Q")])
    for k in VARS:
        e = err[k]
        rows.append({**label, "variable": k, "RMSE": float(np.sqrt((e ** 2).mean())), "MAE": float(e.abs().mean()),
                     "RMSE ex 2020Q2-Q3": float(np.sqrt((e[ex] ** 2).mean())), "bias (fc-act)": float(e.mean()),
                     "RMSE h1-4": float(np.sqrt((e.iloc[:4] ** 2).mean())),
                     "RMSE h5-8": float(np.sqrt((e.iloc[4:8] ** 2).mean())),
                     "RMSE h9-14": float(np.sqrt((e.iloc[8:] ** 2).mean())),
                     "cum. error, pp (sum/4)": float(e.sum() / 4) if k in ("gcpi", "gw") else np.nan})
    return rows
