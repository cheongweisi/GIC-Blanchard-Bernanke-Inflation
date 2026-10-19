"""Phase 4b, part 5: what do the Phase 4 intervals cover?

Four distinct sources are kept apart:
  (1) parameter uncertainty            HAC-normal draws of the four equations (and the bridge). The only source in the scenario-deviation bands.
  (2) exogenous-driver uncertainty     oil, V/U, productivity, GSCPI, food paths: held at the baseline in every band; scenarios are the tool.
  (3) specification uncertainty        different samples/weights, pass-through, bridge elasticity, wage catch-up: sensitivities only.
  (4) historical out-of-sample error   what real-time forecasts of this kind actually missed by (backtest tiers).
This module provides: `fan_coverage` (does the Phase 4 baseline-fan construction cover historical outturns when run at past origins, conditional on the
tier-D driver assumptions?), `joint_bootstrap_coefs` (a joint, block-bootstrap parameter distribution that keeps cross-equation dependence, to test the
'equations independent' assumption), `spec_variants` (alternative coefficient sets for the specification envelope).
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from ..estimation.inference import _draw, with_hac
from ..estimation.rls import design
from ..extension.models import fit, standard_models
from ..extension.pseudo_oos import _fit_origin, unconditional_exog
from ..scenarios import engine as E
from ..scenarios import oil as O
from ..scenarios.backtest import _hist
from ..scenarios.world import LAGS, World
from ..simulation.model import SimModel

EQS = ("gw", "gcpi", "cf1", "cf10")
H_MAX = 12


def _coefset_from_draws(res: dict, n: int, rng) -> E.CoefSet:
    names = {eq: list(r.coef.index) for eq, r in res.items()}
    return E.CoefSet(names, {eq: _draw(r.coef.values, r.cov.values, n, rng) for eq, r in res.items()})


def residual_frame(res: dict) -> pd.DataFrame:
    return pd.concat({eq: res[eq].resid for eq in EQS}, axis=1).dropna()


def fan_at_origin(w: World, ms, T0: pd.Period, n: int, seed: int) -> dict:
    """The Phase 4 baseline-fan recipe run at a past origin T0 under the tier-D driver assumptions: parameter draws (HAC), joint residual bootstrap by quarter
    from 1990Q1-T0, bridge coefficient draws and monthly bridge noise. Returns {h: (n,) y/y draws} for h = 1..H, in % (log approx. mean)."""
    data = w.data
    last = w.ctx.last
    h = min(H_MAX, (pd.Period(last, "Q") - T0).n)
    rng = np.random.default_rng(seed)
    res = _fit_origin(ms, data, T0)
    hac = {k: with_hac(r, data) for k, r in res.items()}
    cs = _coefset_from_draws(hac, n, rng)
    R = residual_frame(res)
    T = LAGS + h
    add = {eq: np.zeros((n, T)) for eq in EQS}
    for t in range(LAGS, T):
        pick = rng.integers(0, len(R), size=n)
        for eq in EQS:
            add[eq][:, t] = R[eq].values[pick]
    end_m = T0.end_time.strftime("%Y-%m")
    mend = f"{end_m}-01"
    br = O.estimate_bridge(w.cpie_m.loc[:mend], w.oil_actual.loc[:mend], end=end_m)
    m0, m1 = (T0 + 1).start_time, (T0 + h).end_time.normalize().replace(day=1)
    months = pd.date_range(m0, m1, freq="MS")
    oil_flat = pd.concat([w.oil_actual.loc[:mend], pd.Series(float(w.oil_actual.loc[mend]), index=months)])
    noise = rng.normal(0.0, br.resid_sd, size=(n, len(months)))
    gEq = O.quarterly_energy_growth(O.monthly_energy_growth(br.draws(n, seed + 1), oil_flat, str(m0.date()), str(m1.date()), noise=noise))
    hist = _hist(data, T0)
    gE_hist = (data["grpe"] + data["gw"]).loc[T0 - 3:T0].values
    gE = np.concatenate([np.broadcast_to(gE_hist, (n, LAGS)), gEq], axis=1)
    ue = unconditional_exog(data, T0, h)
    exog = {k: ue[k] for k in ("vu", "magpty", "shortagema2")}
    relf = np.full(T, np.nan)
    relf[LAGS:] = 0.0
    p = E.simulate(cs, E.Inputs(hist=hist, exog=exog, gE=gE, gF=np.zeros(T), add=add, rel_override={"grpf": relf}))["gcpi"]
    return {k: np.stack([p[:, LAGS - 1 + k - 3:LAGS - 1 + k + 1].mean(axis=1)]).ravel() for k in range(1, h + 1)}


def fan_coverage(w: World, origins: list[pd.Period], n: int = 300) -> pd.DataFrame:
    ms = standard_models(w.ctx.last)["B"]
    data = w.data
    rows = []
    for i, T0 in enumerate(origins):
        f = fan_at_origin(w, ms, T0, n, seed=1000 + i)
        for k, y in f.items():
            tgt = T0 + k
            a = data["gcpi"].loc[tgt - 3:tgt].mean()
            q = np.quantile(y, [0.05, 0.16, 0.5, 0.84, 0.95])
            rows.append({"origin": str(T0), "h": k, "target": str(tgt), "actual y/y (log)": float(a), "q05": q[0], "q16": q[1], "q50": q[2], "q84": q[3], "q95": q[4],
                         "pit": float((y < a).mean()), "fan sd": float(y.std())})
    return pd.DataFrame(rows)


def coverage_summary(df: pd.DataFrame) -> pd.DataFrame:
    tgt = pd.PeriodIndex(df["target"], freq="Q")
    rows = []
    for lab, (lo, hi) in {"all targets": ("1990Q1", "2026Q2"), "targets to 2019Q4": ("1990Q1", "2019Q4"), "2020Q1-2023Q2": ("2020Q1", "2023Q2"),
                          "2023Q3-2026Q2": ("2023Q3", "2026Q2")}.items():
        sub = df[(tgt >= pd.Period(lo, "Q")) & (tgt <= pd.Period(hi, "Q"))]
        for h in (1, 4, 8, 12):
            s = sub[sub.h == h]
            if len(s) < 4:
                continue
            inside90 = ((s["actual y/y (log)"] >= s["q05"]) & (s["actual y/y (log)"] <= s["q95"])).mean()
            inside68 = ((s["actual y/y (log)"] >= s["q16"]) & (s["actual y/y (log)"] <= s["q84"])).mean()
            err = s["actual y/y (log)"] - s["q50"]
            rows.append({"target period": lab, "h": h, "n": len(s), "coverage of 90% fan": float(inside90), "coverage of 68% fan": float(inside68),
                         "mean fan s.d. (pp)": float(s["fan sd"].mean()), "RMSE of median (pp)": float(np.sqrt((err ** 2).mean())),
                         "realised / fan s.d. (RMS of standardised error)": float(np.sqrt(((err / s["fan sd"]) ** 2).mean())),
                         "share of outturns above the fan": float((s["actual y/y (log)"] > s["q95"]).mean()), "share below the fan": float((s["actual y/y (log)"] < s["q05"]).mean())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------------------------------
def _rls(y: np.ndarray, X: np.ndarray, rn_idx: list[int], value: float) -> np.ndarray:
    A = np.linalg.pinv(X.T @ X)
    b = A @ X.T @ y
    if rn_idx:
        R = np.zeros((1, X.shape[1]))
        R[0, rn_idx] = 1.0
        K = A @ R.T @ np.linalg.inv(R @ A @ R.T)
        b = b - K @ (R @ b - value)
    return b


def joint_bootstrap_coefs(w: World, n: int = 500, block: int = 4, seed: int = 7) -> E.CoefSet:
    """Moving-block bootstrap of the regression rows, the SAME rows in all four equations (so cross-equation dependence is kept), restricted LS in every draw
    (authors' restrictions). Sample 1990Q1-2026Q2 (Model B*). Returns a CoefSet with n draws aligned to the point CoefSet."""
    rng = np.random.default_rng(seed)
    data = w.data
    last = w.ctx.last
    ms = standard_models(last)["B"]
    from ..extension.models import specs_for_end
    specs = specs_for_end(ms.variant, last)
    frames = {}
    for eq in EQS:
        X = design(specs[eq], data)
        fr = pd.concat([data[specs[eq].dep].rename("__y"), X], axis=1).loc["1990Q1":last].dropna()
        frames[eq] = fr
    idx = frames["gw"].index
    for eq in EQS:
        idx = idx.intersection(frames[eq].index)
    N = len(idx)
    names = {eq: list(frames[eq].columns[1:]) for eq in EQS}
    vals = {eq: np.zeros((n, len(names[eq]))) for eq in EQS}
    nb = int(np.ceil(N / block))
    for i in range(n):
        starts = rng.integers(0, N - block + 1, size=nb)
        rows = np.concatenate([np.arange(s, s + block) for s in starts])[:N]
        for eq in EQS:
            fr = frames[eq].loc[idx].iloc[rows]
            y, X = fr["__y"].values, fr.drop(columns="__y").values
            rn = [names[eq].index(c) for c in specs[eq].restriction_names()]
            vals[eq][i] = _rls(y, X, rn, specs[eq].restriction_value)
    pt = w.cs_point
    out = {}
    for eq in EQS:
        out[eq] = pd.DataFrame(vals[eq], columns=names[eq]).reindex(columns=pt.names[eq]).fillna(0.0).values
    return E.CoefSet(pt.names, out)


def spec_variants(w: World) -> dict[str, E.CoefSet]:
    """Alternative estimated coefficient sets (same equation structure): equations estimated on other samples/weights."""
    ms = standard_models(w.ctx.last)
    out = {}
    for lab, spec in (("all equations estimated 1990Q1-2019Q4 (pre-COVID)", dataclasses.replace(ms["B"], end="2019Q4")),
                      ("all equations frozen at 2023Q2 (the paper's sample end)", dataclasses.replace(ms["B"], end="2023Q2")),
                      ("exponential weights, half-life 15y (Model C15)", ms["C15"])):
        res = fit(spec, w.data, spec.end or w.ctx.last)
        pt = w.cs_point
        cs = E.CoefSet.from_models([SimModel.from_results(res)])
        # align names (the wage equation lacks the COVID dummies when the sample ends before 2020Q2): missing columns are zero
        vals = {eq: pd.DataFrame(cs.values[eq], columns=cs.names[eq]).reindex(columns=pt.names[eq]).fillna(0.0).values for eq in EQS}
        out[lab] = E.CoefSet(pt.names, vals)
    return out
