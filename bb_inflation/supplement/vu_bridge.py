"""Bridging the V/U hole of 2025Q4 (no October 2025 unemployment level exists: the BLS household survey for October 2025 was
never collected, so SA, NSA, rate and level series all lack that month; JOLTS openings for October exist).

V/U for a quarter = mean(JOLTS openings over 3 months) / mean(unemployed over 3 months). Only the October unemployment level
is missing, so alternatives either (a) estimate that one month and keep every observed month, or (b) drop October altogether.

Methods (all use only data dated on or before 2025-12, i.e. what a forecaster at the end of 2025Q4 knows -> no look-ahead):
  nov_dec        drop October from numerator and denominator (Phase 3 simulation bridge)
  interp         U(Oct) = mean of U(Sep) and U(Nov)                      [parameter-free]
  carry_sep      U(Oct) = U(Sep)
  carry_nov      U(Oct) = U(Nov)
  claims         interpolation tilted by continuing claims: ln U(Oct) = interp + b * (dln CC(Oct) - half of the two-month dln CC),
                 b estimated by OLS on monthly data up to 2025-09 (excluding 2020-03..2021-06)
`backtest` hides one observed month and compares every method's error in quarterly V/U (and in ln U).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METHODS = ("nov_dec", "interp", "carry_sep", "carry_nov", "claims")
LABEL = {"nov_dec": "Nov-Dec ratio of means (Phase 3)", "interp": "Interpolate U(Oct) from Sep and Nov",
         "carry_sep": "Carry U(Sep) forward", "carry_nov": "Carry U(Nov) back",
         "claims": "Claims-tilted interpolation of U(Oct)"}
COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2021-06-01"))


def monthly_mean_weekly(w: pd.Series) -> pd.Series:
    m = w.groupby(w.index.to_period("M")).mean()
    m.index = m.index.to_timestamp()
    return m


def claims_beta(U: pd.Series, CC: pd.Series, upto: str = "2025-09-01") -> tuple[float, int]:
    """b in  dln U(t-1->t+1) - ... : regress the *tilt* (dln U_t - half of 2-month dln U) on (dln CC_t - half of 2-month dln CC)."""
    u, c = np.log(U.dropna()), np.log(CC.dropna())
    idx = u.index.intersection(c.index)
    rows = []
    for t in idx:
        p, n = t - pd.offsets.MonthBegin(1), t + pd.offsets.MonthBegin(1)
        if p in idx and n in idx and t <= pd.Timestamp(upto) and not (COVID[0] <= t <= COVID[1]):
            rows.append(((u[t] - 0.5 * (u[p] + u[n])), (c[t] - 0.5 * (c[p] + c[n]))))
    a = np.array(rows)
    b = float((a[:, 0] @ a[:, 1]) / (a[:, 1] @ a[:, 1]))
    return b, len(a)


def estimate_u(method: str, U: pd.Series, t: pd.Timestamp, CC: pd.Series | None = None, beta: float | None = None) -> float:
    p, n = t - pd.offsets.MonthBegin(1), t + pd.offsets.MonthBegin(1)
    if method == "interp":
        return 0.5 * (U[p] + U[n])
    if method == "carry_sep":
        return float(U[p])
    if method == "carry_nov":
        return float(U[n])
    if method == "claims":
        base = 0.5 * (np.log(U[p]) + np.log(U[n]))
        tilt = np.log(CC[t]) - 0.5 * (np.log(CC[p]) + np.log(CC[n]))
        return float(np.exp(base + beta * tilt))
    raise ValueError(method)


def quarter_vu(J: pd.Series, U: pd.Series, q: pd.Period, method: str, CC=None, beta=None) -> float:
    months = pd.date_range(q.start_time, periods=3, freq="MS")
    miss = [m for m in months if np.isnan(U.get(m, np.nan))]
    if method == "nov_dec":
        ok = [m for m in months if m not in miss and m in J.index]
        return float(J[ok].mean() / U[ok].mean())
    u = U.reindex(months).copy()
    for m in miss:
        u[m] = estimate_u(method, U.dropna(), m, CC, beta)
    return float(J[months].mean() / u.mean())


def bridge_all(J: pd.Series, U: pd.Series, CC: pd.Series, q: pd.Period = pd.Period("2025Q4", "Q")) -> pd.DataFrame:
    beta, n = claims_beta(U, CC)
    rows = []
    for m in METHODS:
        months = pd.date_range(q.start_time, periods=3, freq="MS")
        miss = [x for x in months if np.isnan(U.get(x, np.nan))]
        uo = (np.nan if m == "nov_dec" else estimate_u(m, U.dropna(), miss[0], CC, beta))
        rows.append({"method": m, "label": LABEL[m], "U_oct (thousand)": uo / 1e3, "VU_2025Q4": quarter_vu(J, U, q, m, CC, beta),
                     "claims beta": beta if m == "claims" else np.nan})
    return pd.DataFrame(rows)


def backtest(J: pd.Series, U: pd.Series, CC: pd.Series, first_month_only: bool = True, since: str = "2001-01-01",
             through: str = "2025-09-01") -> pd.DataFrame:
    """Hide the unemployment level of one month (the first month of a quarter if first_month_only) and bridge it with every
    method; error = bridged minus true quarterly V/U (and in ln U). The claims beta is re-estimated using data before the hidden month only."""
    Uf = U.dropna()
    rows = []
    for t in Uf.index:
        if t < pd.Timestamp(since) or t > pd.Timestamp(through):
            continue
        if first_month_only and t.month not in (1, 4, 7, 10):
            continue
        p, n = t - pd.offsets.MonthBegin(1), t + pd.offsets.MonthBegin(1)
        if p not in Uf.index or n not in Uf.index or t not in CC.index or p not in CC.index or n not in CC.index:
            continue
        q = t.to_period("Q")
        months = pd.date_range(q.start_time, periods=3, freq="MS")
        if any(m not in Uf.index or m not in J.index for m in months):
            continue
        truth = float(J[months].mean() / Uf[months].mean())
        Uh = Uf.drop(t)
        beta, _ = claims_beta(Uh, CC, upto=str(p.date()))
        row = {"month": t, "covid": bool(COVID[0] <= t <= COVID[1])}
        for m in METHODS:
            row[f"VU_err_{m}"] = quarter_vu(J, Uh, q, m, CC, beta) - truth
            if m != "nov_dec":
                row[f"lnU_err_{m}"] = np.log(estimate_u(m, Uh, t, CC, beta)) - np.log(Uf[t])
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_backtest(bt: pd.DataFrame) -> pd.DataFrame:
    out = []
    for name, d in (("all months", bt), ("excl. 2020-03..2021-06", bt[~bt.covid])):
        for m in METHODS:
            e = d[f"VU_err_{m}"]
            r = {"sample": name, "method": m, "n": len(e), "VU bias": e.mean(), "VU RMSE": float(np.sqrt((e ** 2).mean())),
                 "VU max |err|": e.abs().max()}
            if m != "nov_dec":
                le = d[f"lnU_err_{m}"]
                r["lnU RMSE (%)"] = 100 * float(np.sqrt((le ** 2).mean()))
            out.append(r)
    return pd.DataFrame(out)
