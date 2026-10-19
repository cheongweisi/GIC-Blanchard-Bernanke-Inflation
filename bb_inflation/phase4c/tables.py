"""Coefficient-comparison tables (Tasks 2-3): estimation checks, coefficient and block-sum tables, overlap-adjusted change tests, derived multipliers."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ..config import OUT_FULL, OUT_PRECOVID
from ..data.phase3_data import GSCPI_FILL
from ..estimation.rls import design
from . import samples as S
from .study import Study

BLOCKS = {"gw": ["gw", "cf1", "vu", "diffcpicf", "magpty"],
          "gcpi": ["gcpi", "gw", "grpe", "grpf", "shortagema2", "magpty"],
          "cf1": ["cf1", "cf10", "gcpi"],
          "cf10": ["cf10", "gcpi"]}
LABEL = {("gw", "gw"): "Wage eq: lagged wage growth (L1-4)",
         ("gw", "cf1"): "Wage eq: 1-year expected inflation (L1-4)",
         ("gw", "vu"): "Wage eq: V/U (L1-4)",
         ("gw", "diffcpicf"): "Wage eq: catch-up from unanticipated inflation (L1-4)",
         ("gw", "magpty"): "Wage eq: trend productivity growth (L1)",
         ("gcpi", "gcpi"): "Price eq: lagged CPI inflation (L1-4)",
         ("gcpi", "gw"): "Price eq: wage growth (L0-4), direct wage-to-CPI",
         ("gcpi", "grpe"): "Price eq: relative energy-price inflation (L0-4)",
         ("gcpi", "grpf"): "Price eq: relative food-price inflation (L0-4)",
         ("gcpi", "shortagema2"): "Price eq: GSCPI, 2-quarter mean (L0)",
         ("gcpi", "magpty"): "Price eq: trend productivity growth (L0)",
         ("cf1", "cf1"): "1y-expectations eq: own lags (L1-4)",
         ("cf1", "cf10"): "1y-expectations eq: 10-year expectations (L0-4)",
         ("cf1", "gcpi"): "1y-expectations eq: CPI inflation (L0-4)",
         ("cf10", "cf10"): "10y-expectations eq: own lags (L1-4)",
         ("cf10", "gcpi"): "10y-expectations eq: CPI inflation (L0-4)"}
KEY_BLOCKS = [("gcpi", "gw"), ("gw", "gw"), ("gw", "cf1"), ("gw", "diffcpicf"), ("gw", "vu"), ("cf1", "gcpi"), ("cf10", "gcpi"),
              ("gcpi", "grpe"), ("gcpi", "grpf"), ("gcpi", "shortagema2")]
PAIRS = [("B19", "B23"), ("B23", "B26"), ("B19", "B26")]
AUTH_ORDER = {"gw": ["gw", "cf1", "vu", "diffcpicf", "magpty"], "gcpi": ["gcpi", "gw", "grpe", "grpf", "shortage", "magpty"],
              "cf1": ["cf1", "cf10", "gcpi"], "cf10": ["cf10", "gcpi"]}


def vlabel(k: str) -> str:
    return S.LABEL.get(k, k)


def authors_published() -> pd.DataFrame:
    """Sums and classical p-values published in the authors' shipped summary_stats files (hybrid design: wage/cf1/cf10 pre-COVID, price full)."""
    rows = []
    for eq in S.EQS:
        x = pd.read_excel(OUT_PRECOVID / "summary_stats_restricted.xlsx", sheet_name=eq, header=None)
        blocks = AUTH_ORDER[eq]
        for i, b in enumerate(blocks):
            rows.append({"eq": eq, "block": b, "published sum": float(x.iloc[1 + i, 1]), "published p(sum)": x.iloc[1 + i, 2], "published p(joint)": x.iloc[1 + i, 3]})
        r2 = x[x[0] == "R2"].iloc[0, 1]
        n = x[x[0] == "number of observations"].iloc[0, 1]
        rows.append({"eq": eq, "block": "R2", "published sum": float(r2)})
        rows.append({"eq": eq, "block": "N", "published sum": float(n)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------------------
def estimation_checks(st: Study) -> pd.DataFrame:
    data = st.data
    bridged = pd.Period("2025Q4", "Q")
    rows = []
    for vk, v in S.VINTAGES.items():
        for eq in S.EQS:
            r = st.fits[vk][eq]
            names = list(r.coef.index)
            X = design(r.spec, data)[names].loc[r.resid.index]
            Xs = X / np.linalg.norm(X.values, axis=0)
            rn = r.spec.restriction_names()
            q = 1 if rn else 0
            window = data.loc[S.START:v.end(eq)]
            sample_idx = r.resid.index
            gs = data["shortage"].loc[sample_idx]
            filled = int(((gs - GSCPI_FILL).abs() < 1e-12).sum())
            bridged_obs = 0
            if eq == "gw":
                bridged_obs = int(sum(1 for t in sample_idx if any(t - k == bridged for k in (1, 2, 3, 4))))
            rows.append({"vintage": vlabel(vk), "equation": eq, "sample": f"{r.sample[0]}-{r.sample[1]}", "N": r.nobs,
                         "coefficients": len(names), "free parameters (after restriction)": len(names) - q,
                         "residual df": r.df_resid, "rank of X": int(np.linalg.matrix_rank(X.values)), "full column rank": bool(np.linalg.matrix_rank(X.values) == len(names)),
                         "condition number (unit-norm columns)": float(np.linalg.cond(Xs.values)),
                         "restriction sum (target 1)": float(r.coef[rn].sum()) if rn else np.nan,
                         "wage dummies in model": ", ".join(d for d in r.spec.dummies) or "none",
                         "quarters in window 1990Q1-end": len(window), "quarters not used (missing or lost to lags)": len(window) - r.nobs,
                         "obs. using bridged V/U 2025Q4": bridged_obs,
                         "obs. using constant-filled GSCPI (pre-1998)": filled if eq == "gcpi" else np.nan,
                         "R2 (squared corr)": r.r2_corr, "residual s.d.": float(np.sqrt(r.sigma2))})
    return pd.DataFrame(rows)


def coef_table(st: Study, eq: str, auth_hyb=None) -> pd.DataFrame:
    """Every coefficient of one equation, by vintage: estimate, HAC s.e., HAC p-value (t, residual df); authors' published coefficient alongside."""
    keys = ["B19", "HYB", "B23", "B26"] if eq == "gcpi" else ["B19", "B23", "B26"]
    cols = st.stacks[eq].cols
    out = pd.DataFrame(index=cols)
    for vk in keys:
        r = st.hacs[vk][eq]
        se = pd.Series(np.sqrt(np.diag(r.cov.values)), index=r.coef.index)
        cl = pd.Series(np.sqrt(np.diag(st.fits[vk][eq].cov.values)), index=r.coef.index)
        t = r.coef / se
        out[f"{vlabel(vk)}: estimate"] = r.coef
        out[f"{vlabel(vk)}: HAC s.e."] = se
        out[f"{vlabel(vk)}: HAC p"] = pd.Series(2 * stats.t.sf(t.abs().values, r.df_resid), index=r.coef.index)
        out[f"{vlabel(vk)}: classical s.e."] = cl
    if auth_hyb is not None:
        from ..validation.authors_outputs import authors_model
        am = authors_model("precovid").coefs[eq]
        out["Authors (published, hybrid): estimate"] = am.reindex(out.index)
        extra = am[[n for n in am.index if n not in out.index]]
        for n, v in extra.items():
            out.loc[n, "Authors (published, hybrid): estimate"] = v
    return out


def block_table(st: Study, auth) -> pd.DataFrame:
    """Sum of lag coefficients by block and vintage with HAC s.e., t, p and 95% CI (t, residual df); plus classical p and the authors' published values."""
    rows = []
    for eq, blocks in BLOCKS.items():
        keys = ["B19", "HYB", "B23", "B26"] if eq == "gcpi" else ["B19", "B23", "B26"]
        stk = st.stacks[eq]
        for b in blocks:
            c = stk.selector(b)
            for vk in keys:
                est, se = stk.combo({vk: c})
                df = stk.df[vk]
                tcrit = stats.t.ppf(0.975, df)
                res = st.fits[vk][eq]
                names = res.block_names(b)
                pc = res.sum_and_pvalues(b)["p_sum"] if len(names) > 1 else np.nan
                rows.append({"eq": eq, "block": b, "label": LABEL[(eq, b)], "vintage": vlabel(vk), "N": res.nobs, "sum": est, "se_hac": se,
                             "t": est / se if se > 0 else np.nan, "p_hac": float(2 * stats.t.sf(abs(est / se), df)) if se > 0 else np.nan,
                             "ci95_lo": est - tcrit * se, "ci95_hi": est + tcrit * se, "p_classical": pc})
    t = pd.DataFrame(rows)
    pub = authors_published()
    pub = pub[~pub.block.isin(["R2", "N"])].rename(columns={"block": "block_auth"})
    # authors' re-estimation on their own data with HAC (reference column)
    from ..estimation.inference import with_hac
    from ..extension.coefs import sum_se
    ad = S.authors_data()
    ar = S.fit_authors("hybrid", ad)
    arows = []
    for eq, blocks in AUTH_ORDER.items():
        h = with_hac(ar[eq], ad)
        for i, b in enumerate(blocks):
            names = ar[eq].block_names(b)
            s, se, p = sum_se(h, names)
            bb = "shortagema2" if b == "shortage" else b
            pr = pub[(pub["eq"] == eq) & (pub["block_auth"] == b)].iloc[0]
            arows.append({"eq": eq, "block": bb, "label": LABEL[(eq, bb)], "vintage": vlabel("AUTH"), "N": ar[eq].nobs, "sum": s, "se_hac": se,
                          "t": s / se, "p_hac": p, "ci95_lo": s - stats.t.ppf(0.975, h.df_resid) * se, "ci95_hi": s + stats.t.ppf(0.975, h.df_resid) * se,
                          "p_classical": pr["published p(sum)"], "published sum (authors' files)": pr["published sum"],
                          "note": "Google 'shortage', 5 lags (not comparable with GSCPI)" if b == "shortage" else ""})
    return pd.concat([pd.DataFrame(arows), t], ignore_index=True)


def change_table(st: Study) -> pd.DataFrame:
    rows = []
    for eq, blocks in BLOCKS.items():
        stk = st.stacks[eq]
        pairs = PAIRS + ([("B19", "HYB")] if eq == "gcpi" else [])
        for b in blocks:
            c = stk.selector(b)
            for a, bb in pairs:
                t = stk.change_test(a, bb, c)
                rows.append({"eq": eq, "block": b, "label": LABEL[(eq, b)], "from": vlabel(a), "to": vlabel(bb), "sum (from)": float(c @ stk.beta[a]),
                             "sum (to)": float(c @ stk.beta[bb]), "change": t["change"], "se (overlap-adjusted HAC)": t["se"], "t": t["t"],
                             "p (overlap-adjusted)": t["p"], "se if estimates were independent": t["se_if_independent"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------------------
def derived_functions():
    """Multipliers that are nonlinear in the coefficients: name -> (description, function of per-equation block-sum getter g(eq, block))."""
    return {
        "Wage->CPI: direct pass-through (price eq., sum of wage coefficients = 1 - lagged-inflation sum)": lambda g, c: g("gcpi", "gw"),
        "Wage->CPI: impact coefficient (same-quarter wage growth)": lambda g, c: c("gcpi", "gw_L0"),
        "Wage->CPI: net wage weight when energy and food are nominal (wage sum - energy sum - food sum)": lambda g, c: g("gcpi", "gw") - g("gcpi", "grpe") - g("gcpi", "grpf"),
        "Energy: long-run price-level elasticity (energy sum / (1 - lagged-inflation sum))": lambda g, c: g("gcpi", "grpe") / (1 - g("gcpi", "gcpi")),
        "Food: long-run price-level elasticity (food sum / (1 - lagged-inflation sum))": lambda g, c: g("gcpi", "grpf") / (1 - g("gcpi", "gcpi")),
        "GSCPI: price-equation coefficient (pp of annualised CPI inflation per GSCPI unit, same quarter / 2-quarter mean)": lambda g, c: g("gcpi", "shortagema2"),
        "V/U: long-run effect on wage growth per unit V/U (V/U sum / (1 - lagged-wage sum))": lambda g, c: g("gw", "vu") / (1 - g("gw", "gw")),
        "Expectations -> wages: weight on 1-year expectations (= 1 - lagged-wage sum)": lambda g, c: g("gw", "cf1"),
        "Catch-up -> wages: sum of catch-up coefficients": lambda g, c: g("gw", "diffcpicf"),
        "CPI -> 1-year expectations: sum of CPI coefficients (same-quarter and four lags)": lambda g, c: g("cf1", "gcpi"),
        "CPI -> 10-year expectations: sum of CPI coefficients": lambda g, c: g("cf10", "gcpi"),
        "10-year expectations: own-lag persistence (sum)": lambda g, c: g("cf10", "cf10"),
    }


def derived_table(st: Study) -> pd.DataFrame:
    rows = []
    fns = derived_functions()
    for name, f in fns.items():
        vals = {}
        for vk in S.MAIN:
            def g_pt(eq, b, vk=vk):
                return st.block_point(eq, vk, b)

            def c_pt(eq, cname, vk=vk):
                stk = st.stacks[eq]
                return float(stk.beta[st.key(eq, vk)][stk.cols.index(cname)])

            def g_dr(eq, b, vk=vk):
                return st.block_draws(eq, vk, b)

            def c_dr(eq, cname, vk=vk):
                stk = st.stacks[eq]
                return st.draws[eq][st.key(eq, vk)][:, stk.cols.index(cname)]
            pt, dr = f(g_pt, c_pt), f(g_dr, c_dr)
            vals[vk] = (pt, dr)
            rows.append({"multiplier": name, "vintage": vlabel(vk), "estimate": pt, "lo90": float(np.quantile(dr, .05)), "hi90": float(np.quantile(dr, .95)),
                         "draw s.d.": float(np.std(dr))})
        for a, b in PAIRS:
            d = vals[b][1] - vals[a][1]
            rows.append({"multiplier": name, "vintage": f"change {vlabel(a)} -> {vlabel(b)}", "estimate": vals[b][0] - vals[a][0], "lo90": float(np.quantile(d, .05)),
                         "hi90": float(np.quantile(d, .95)), "draw s.d.": float(np.std(d)),
                         "p (two-sided, from draws)": float(min(1.0, 2 * min((d >= 0).mean(), (d <= 0).mean())))})
    return pd.DataFrame(rows)
