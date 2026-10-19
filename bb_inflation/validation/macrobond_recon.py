"""Phase 2a reconciliation: Macrobond-built raw data versus the authors' dataset."""
import datetime as dt

import numpy as np
import pandas as pd

from ..data.macrobond_loader import fetch_raw, splice_authors_history
from ..data.macrobond_registry import AUTHORS_VINTAGE, REGISTRY
from ..data.transforms import build_model_data
from ..estimation.replication import fit_full, fit_precovid

GROWTH_COLS = ("OPHNFB", "ECIWAG")
WINDOWS = {"CPIAUCSL": "1990Q1", "CPIENGSL": "1990Q1", "CPIUFDSL": "1990Q1", "OPHNFB": "1990Q1",
           "ECIWAG": "2001Q2", "VOVERU": "2001Q1", "EXPINF1YR": "1990Q1", "EXPINF10YR": "1990Q1",
           "GSCPI": "1998Q1"}
END = "2023Q2"


def _cmp(a: pd.Series, m: pd.Series, col: str) -> dict:
    if col in GROWTH_COLS:
        a, m = 400 * np.log(a).diff(), 400 * np.log(m).diff()
    st = WINDOWS[col]
    d = (m.loc[st:END] - a.loc[st:END]).dropna()
    return {"n": len(d), "mean_abs": d.abs().mean(), "max_abs": d.abs().max(),
            "at_max": str(d.abs().idxmax()), "bias": d.mean()}


def series_reconciliation(authors_raw: pd.DataFrame) -> pd.DataFrame:
    """Per series: Macrobond at the authors' vintage vs authors, and current Macrobond vs authors."""
    vint = fetch_raw(dt.datetime(*AUTHORS_VINTAGE))
    cur = fetch_raw(None)
    rows = []
    for col in REGISTRY:
        basis = "growth (400*dln)" if col in GROWTH_COLS else "level"
        for tag, mb in (("as of authors' vintage", vint), ("current vintage", cur)):
            r = _cmp(authors_raw[col], mb[col], col)
            rows.append({"series": col, "compared_on": basis, "window": f"{WINDOWS[col]}-{END}", "macrobond": tag, **r})
    return pd.DataFrame(rows)


def eci_history_check(authors_raw: pd.DataFrame) -> pd.DataFrame:
    """Authors' spliced pre-2001 ECI versus Macrobond's own ECI wages & salaries history (1980Q1-)."""
    cur = fetch_raw(None)["ECIWAG"]
    g_a = 400 * np.log(authors_raw["ECIWAG"]).diff()
    g_m = 400 * np.log(cur).diff()
    rows = []
    for lab, a, b in (("1990Q1-2000Q4 (authors' splice vs Macrobond W&S)", "1990Q1", "2000Q4"),
                      ("2001Q1-2023Q2 (authors vs current Macrobond)", "2001Q1", "2023Q2")):
        x = pd.concat([g_a.loc[a:b], g_m.loc[a:b]], axis=1, keys=["authors", "macrobond"]).dropna()
        rows.append({"window": lab, "n": len(x), "mean_growth_authors": x.authors.mean(),
                     "mean_growth_macrobond": x.macrobond.mean(), "mean_abs_diff": (x.authors - x.macrobond).abs().mean(),
                     "corr": x.corr().iloc[0, 1]})
    return pd.DataFrame(rows)


SUMMARY_VARS = {"gw": ("gw", "cf1", "vu", "diffcpicf", "magpty"),
                "gcpi": ("gcpi", "gw", "grpe", "grpf", "shortage", "magpty"),
                "cf1": ("cf1", "cf10", "gcpi"), "cf10": ("cf10", "gcpi")}


def _spliced_data(mb: pd.DataFrame, authors_raw: pd.DataFrame) -> pd.DataFrame:
    sp = splice_authors_history(mb, authors_raw)
    sp["SHORTAGE"] = authors_raw["SHORTAGE"]       # Google Trends: not on Macrobond; kept for this check
    return build_model_data(sp.loc[:END])


def estimation_reconciliation(authors_raw: pd.DataFrame) -> pd.DataFrame:
    """Sum-of-coefficients and R2 for: authors' data, Macrobond (authors' vintage), Macrobond (current vintage),
    all estimated 1990Q1-2023Q2 with the authors' specification (full sample and pre-COVID)."""
    datasets = {"authors": build_model_data(authors_raw),
                "macrobond @ authors' vintage": _spliced_data(fetch_raw(dt.datetime(*AUTHORS_VINTAGE)), authors_raw),
                "macrobond current vintage": _spliced_data(fetch_raw(None), authors_raw)}
    rows = []
    for run, fitter in (("full sample", fit_full), ("pre-COVID", fit_precovid)):
        for dname, d in datasets.items():
            res = fitter(d)
            for eq, r in res.items():
                s = r.summary()
                for v in SUMMARY_VARS[eq]:
                    rows.append({"run": run, "data": dname, "equation": eq, "variable": v,
                                 "sum": s.loc[v, "sum"], "R2": r.r2_corr})
    long = pd.DataFrame(rows)
    return long.pivot_table(index=["run", "equation", "variable"], columns="data", values="sum", sort=False)


def gscpi_vs_google(authors_raw: pd.DataFrame) -> pd.DataFrame:
    """How similar are GSCPI (Macrobond) and the Google 'shortage' index over time?"""
    g = fetch_raw(None)["GSCPI"]
    x = pd.concat([authors_raw["SHORTAGE"], g], axis=1, keys=["google_shortage", "gscpi"])
    rows = []
    for lab, a, b in (("2004Q1-2019Q4", "2004Q1", "2019Q4"), ("2020Q1-2023Q2", "2020Q1", "2023Q2"),
                      ("2004Q1-2023Q2", "2004Q1", "2023Q2")):
        y = x.loc[a:b].dropna()
        rows.append({"window": lab, "n": len(y), "corr_levels": y.corr().iloc[0, 1],
                     "corr_changes": y.diff().corr().iloc[0, 1],
                     "google_mean": y.google_shortage.mean(), "google_sd": y.google_shortage.std(),
                     "gscpi_mean": y.gscpi.mean(), "gscpi_sd": y.gscpi.std()})
    return pd.DataFrame(rows)
