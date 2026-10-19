"""Phase 4b, part 4: validation of the monthly oil -> CPI energy bridge (Phase 4: 100 dln E_m = c + sum_{k=0..3} b_k 100 dln Oil_{m-k}, sum b = 0.297).

All regressions are OLS with Newey-West (6 lags) standard errors, on the same data as the Phase 4 bridge (World Bank Brent monthly, SA CPI energy).
Tests: stability (recursive and rolling elasticity, break tests), asymmetry (rises vs falls), price-level dependence, lag length and an error-correction
(levels) version, error persistence (does a level error such as the 2026Q3 one revert?), and the effect of elasticity/level errors on scenario conclusions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ..scenarios import oil as O


def dl(s: pd.Series) -> pd.Series:
    return 100.0 * np.log(s).diff()


def ols_nw(y: pd.Series, X: pd.DataFrame, L: int = 6) -> dict:
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    Xv = np.column_stack([np.ones(len(df)), df.drop(columns="y").values])
    names = ["const"] + list(df.columns[1:])
    b = np.linalg.lstsq(Xv, df["y"].values, rcond=None)[0]
    e = df["y"].values - Xv @ b
    A = np.linalg.inv(Xv.T @ Xv)
    u = Xv * e[:, None]
    S = u.T @ u
    for l in range(1, L + 1):
        G = u[l:].T @ u[:-l]
        S += (1 - l / (L + 1)) * (G + G.T)
    V = A @ S @ A
    return {"b": pd.Series(b, index=names), "V": pd.DataFrame(V, index=names, columns=names), "e": pd.Series(e, index=df.index), "n": len(df),
            "r2": 1 - float(e @ e) / float(((df["y"] - df["y"].mean()) ** 2).sum()), "rss": float(e @ e), "k": Xv.shape[1]}


def lin_comb(r: dict, names: list[str]) -> tuple[float, float]:
    w = np.array([1.0 if n in names else 0.0 for n in r["b"].index])
    return float(w @ r["b"].values), float(np.sqrt(w @ r["V"].values @ w))


def lagged(oil: pd.Series, lags: int, prefix: str = "o") -> pd.DataFrame:
    d = dl(oil)
    return pd.concat([d.shift(i).rename(f"{prefix}{i}") for i in range(lags + 1)], axis=1)


def fit_bridge(cpie: pd.Series, oil: pd.Series, lags: int = 3, start: str = "1990-02", end: str = "2026-06") -> dict:
    y = dl(cpie).loc[start:end]
    return ols_nw(y, lagged(oil, lags).loc[start:end])


def predict(cpie: pd.Series, oil: pd.Series, r: dict, lags: int = 3, first: str = "2022-01", last: str = "2022-12") -> pd.Series:
    X = lagged(oil, lags).loc[first:last]
    return pd.Series(r["b"]["const"] + X.values @ r["b"].drop("const").values, index=X.index)


def quarterly(sr: pd.Series) -> pd.Series:
    """Annualised quarterly growth (4 x sum of the three monthly dlogs)."""
    return 4.0 * sr.resample("QS").sum()


def episode_table(cpie: pd.Series, oil: pd.Series, episodes: dict[str, tuple[str, str, str]]) -> pd.DataFrame:
    """episodes: label -> (first month, last month, estimation end for the out-of-sample bridge). Quarterly annualised CPI energy growth."""
    rows = []
    act = dl(cpie)
    full = fit_bridge(cpie, oil, end="2026-06")
    for lab, (a, b, oos_end) in episodes.items():
        r_oos = fit_bridge(cpie, oil, end=oos_end)
        pi = predict(cpie, oil, full, first=a, last=b)
        po = predict(cpie, oil, r_oos, first=a, last=b)
        ya = act.loc[a:b]
        qa, qi, qo = quarterly(ya), quarterly(pi), quarterly(po)
        oq = 100 * np.log(oil.loc[a:b]).diff().resample("QS").sum() * 4
        for q in qa.index:
            rows.append({"episode": lab, "quarter": str(pd.Period(q, "Q")), "oil change (ann. %, sum of 3 monthly dlogs)": float(oq.loc[q]) if q in oq.index else np.nan,
                         "actual CPI energy (ann. %)": float(qa.loc[q]), "bridge in-sample (ann. %)": float(qi.loc[q]), "bridge out-of-sample (ann. %)": float(qo.loc[q]),
                         "error in-sample (pp)": float(qa.loc[q] - qi.loc[q]), "error out-of-sample (pp)": float(qa.loc[q] - qo.loc[q]),
                         "out-of-sample error x 0.075 CPI weight (pp of headline ann.)": float(0.075 * (qa.loc[q] - qo.loc[q])), "estimated to": oos_end})
    return pd.DataFrame(rows)


def recursive_elasticity(cpie: pd.Series, oil: pd.Series, first_end: str = "2005-12", window: int | None = None) -> pd.DataFrame:
    rows = []
    ends = pd.date_range(first_end + "-01", "2026-06-01", freq="MS")
    for e in ends[::3]:
        start = "1990-02" if window is None else str((e - pd.DateOffset(months=window - 1)).date())[:7]
        r = fit_bridge(cpie, oil, start=start, end=str(e.date())[:7])
        b, se = lin_comb(r, ["o0", "o1", "o2", "o3"])
        rows.append({"end": str(e.date())[:7], "elasticity": b, "s.e.": se, "n": r["n"]})
    return pd.DataFrame(rows)


def chow_sum(cpie: pd.Series, oil: pd.Series, breaks: list[str]) -> pd.DataFrame:
    """Is the sum of oil coefficients different after the break date? Interaction of the four oil lags with a post-break dummy (NW)."""
    y = dl(cpie).loc["1990-02":"2026-06"]
    X0 = lagged(oil, 3).loc["1990-02":"2026-06"]
    rows = []
    for b in breaks:
        post = (X0.index >= pd.Timestamp(b)).astype(float)
        X = pd.concat([X0, X0.mul(post, axis=0).add_suffix("_post"), pd.Series(post, index=X0.index, name="post")], axis=1)
        r = ols_nw(y, X)
        dsum, se = lin_comb(r, [f"o{i}_post" for i in range(4)])
        pre, sepre = lin_comb(r, [f"o{i}" for i in range(4)])
        rows.append({"break": b, "elasticity before": pre, "change after": dsum, "s.e. of change": se, "t": dsum / se, "p": float(2 * stats.norm.sf(abs(dsum / se)))})
    return pd.DataFrame(rows)


def asymmetry_and_level(cpie: pd.Series, oil: pd.Series) -> pd.DataFrame:
    y = dl(cpie).loc["1990-02":"2026-06"]
    d = dl(oil)
    rows = []
    # asymmetry: positive and negative oil changes separately (current and 3 lags)
    pos = pd.concat([d.clip(lower=0).shift(i).rename(f"up{i}") for i in range(4)], axis=1)
    neg = pd.concat([d.clip(upper=0).shift(i).rename(f"dn{i}") for i in range(4)], axis=1)
    r = ols_nw(y, pd.concat([pos, neg], axis=1).loc["1990-02":"2026-06"])
    bu, su = lin_comb(r, [f"up{i}" for i in range(4)])
    bd, sd = lin_comb(r, [f"dn{i}" for i in range(4)])
    diff_w = np.array([1.0 if n.startswith("up") else (-1.0 if n.startswith("dn") else 0.0) for n in r["b"].index])
    sdiff = float(np.sqrt(diff_w @ r["V"].values @ diff_w))
    rows.append({"test": "asymmetry: elasticity to oil rises", "estimate": bu, "s.e.": su, "n": r["n"]})
    rows.append({"test": "asymmetry: elasticity to oil falls", "estimate": bd, "s.e.": sd, "n": r["n"]})
    rows.append({"test": "asymmetry: rises minus falls (t = estimate / s.e.)", "estimate": bu - bd, "s.e.": sdiff, "n": r["n"]})
    # price-level dependence: elasticity x (log Brent relative to its trailing 10-year mean), centred
    lvl = np.log(oil) - np.log(oil).rolling(120, min_periods=60).mean()
    X0 = lagged(oil, 3)
    Xi = X0.mul(lvl.shift(1), axis=0).add_suffix("_x")
    r = ols_nw(y, pd.concat([X0, Xi], axis=1).loc["1990-02":"2026-06"])
    b0, s0 = lin_comb(r, ["o0", "o1", "o2", "o3"])
    b1, s1 = lin_comb(r, ["o0_x", "o1_x", "o2_x", "o3_x"])
    rows.append({"test": "price level: elasticity at trailing-10y mean oil price", "estimate": b0, "s.e.": s0, "n": r["n"]})
    rows.append({"test": "price level: change in elasticity per +1 in log(Brent / 10y mean)", "estimate": b1, "s.e.": s1, "n": r["n"]})
    cur = float(np.log(oil.iloc[-1]) - np.log(oil).rolling(120).mean().iloc[-1])
    rows.append({"test": f"price level: implied elasticity now (log Brent / 10y mean = {cur:.2f})", "estimate": b0 + b1 * cur,
                 "s.e.": float(np.sqrt(s0 ** 2 + (cur * s1) ** 2)), "n": r["n"]})
    # high-price regime: Brent above 1.5 x its trailing 10-year mean
    hi = (lvl.shift(1) > np.log(1.5)).astype(float)
    Xh = X0.mul(hi, axis=0).add_suffix("_hi")
    r = ols_nw(y, pd.concat([X0, Xh], axis=1).loc["1990-02":"2026-06"])
    b0, s0 = lin_comb(r, ["o0", "o1", "o2", "o3"])
    bh, sh = lin_comb(r, ["o0_hi", "o1_hi", "o2_hi", "o3_hi"])
    rows.append({"test": f"high-price regime (Brent > 1.5x 10y mean, {int(hi.loc['1990-02':'2026-06'].sum())} months): extra elasticity", "estimate": bh, "s.e.": sh, "n": r["n"]})
    return pd.DataFrame(rows)


def lag_length(cpie: pd.Series, oil: pd.Series) -> pd.DataFrame:
    rows = []
    y = dl(cpie).loc["1990-02":"2026-06"]
    for L in (0, 1, 3, 6, 9, 12):
        r = ols_nw(y, lagged(oil, L).loc["1990-02":"2026-06"])
        b, se = lin_comb(r, [f"o{i}" for i in range(L + 1)])
        k = r["k"]
        aic = r["n"] * np.log(r["rss"] / r["n"]) + 2 * k
        rows.append({"oil lags": L, "cumulative elasticity": b, "s.e.": se, "R2": r["r2"], "AIC": aic, "n": r["n"]})
    return pd.DataFrame(rows)


def error_correction(cpie: pd.Series, oil: pd.Series) -> dict:
    """Engle-Granger style levels check: ln E = a + k ln Oil + g t + u; then 100 dln E = c + sum b dOil + gamma u_{t-1}.
    Returns the static long-run elasticity, the speed of adjustment, and the impulse response of CPI energy to a permanent oil change from each version."""
    df = pd.concat([np.log(cpie).rename("e"), np.log(oil).rename("o")], axis=1).loc["1990-01":"2026-06"].dropna()
    t = np.arange(len(df)) / 12.0
    X = np.column_stack([np.ones(len(df)), df["o"].values, t])
    b = np.linalg.lstsq(X, df["e"].values, rcond=None)[0]
    u = pd.Series(df["e"].values - X @ b, index=df.index)
    adf_stat = _adf(u.values)
    y = dl(cpie).loc["1990-02":"2026-06"]
    Z = pd.concat([lagged(oil, 3), (100.0 * u.shift(1)).rename("ecm")], axis=1).loc["1990-02":"2026-06"]
    r = ols_nw(y, Z)
    short, sshort = lin_comb(r, ["o0", "o1", "o2", "o3"])
    gam, sg = lin_comb(r, ["ecm"])
    return {"static long-run elasticity (levels, with trend)": float(b[1]), "trend (% per year)": float(100 * b[2]), "ADF t-stat of levels residual": adf_stat,
            "short-run sum of oil lags in ECM": short, "short-run s.e.": sshort, "adjustment speed gamma (per month)": gam, "gamma s.e.": sg,
            "half-life of levels deviation (months)": float(np.log(0.5) / np.log(1 + gam)) if -1 < gam < 0 else np.nan,
            "current levels residual u (log pts)": float(u.iloc[-1]), "u in 2026-06 (log pts)": float(u.loc["2026-06-01"]),
            "u 2021-12 (log pts)": float(u.loc["2021-12-01"]), "u 2022-06 (log pts)": float(u.loc["2022-06-01"])}


def _adf(x: np.ndarray, lags: int = 6) -> float:
    dx = np.diff(x)
    Y = dx[lags:]
    cols = [x[lags:-1]] + [dx[lags - i:-i] for i in range(1, lags + 1)]
    X = np.column_stack([np.ones(len(Y))] + cols)
    b = np.linalg.lstsq(X, Y, rcond=None)[0]
    e = Y - X @ b
    s2 = e @ e / (len(Y) - X.shape[1])
    V = s2 * np.linalg.inv(X.T @ X)
    return float(b[1] / np.sqrt(V[1, 1]))


def error_persistence(cpie: pd.Series, oil: pd.Series) -> pd.DataFrame:
    """Do bridge errors revert? Regress the next quarter's (summed) error on the last quarter's and on the sum of the last two (level error)."""
    r = fit_bridge(cpie, oil)
    e = r["e"]
    qe = e.resample("QS").sum()                               # quarterly error, pp of quarterly change (sum of monthly)
    rows = []
    df = pd.DataFrame({"y": qe, "l1": qe.shift(1), "l2": qe.shift(2), "l3": qe.shift(3), "l4": qe.shift(4)}).dropna()
    for lab, cols in (("next quarter's error on last quarter's", ["l1"]), ("on last two quarters' (separately)", ["l1", "l2"]), ("on last four quarters' (separately)", ["l1", "l2", "l3", "l4"])):
        rr = ols_nw(df["y"], df[cols], L=4)
        for c in cols:
            rows.append({"regression": lab, "regressor": c, "coef": float(rr["b"][c]), "s.e.": float(np.sqrt(rr["V"].loc[c, c])), "n": rr["n"]})
    acf = [float(pd.Series(e.values).autocorr(l)) for l in (1, 2, 3, 6, 12)]
    rows.append({"regression": "monthly residual autocorrelation (lags 1, 2, 3, 6, 12)", "regressor": ", ".join(f"{a:.2f}" for a in acf), "coef": np.nan, "s.e.": np.nan, "n": len(e)})
    return pd.DataFrame(rows)
