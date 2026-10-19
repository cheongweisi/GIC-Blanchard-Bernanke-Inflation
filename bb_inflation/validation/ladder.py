"""Phase 2b: swap-ladder from the authors' data to Macrobond data, ending with GSCPI for `shortage`.

Every case re-estimates the authors' specification on the authors' sample (1990Q1-2023Q2, full-sample and
pre-COVID runs) and records coefficient sums, fit, impulse responses and the historical decomposition, so that the
effect of each swap can be read off.

Cases are cumulative ("ladder") or single swaps onto the authors' data ("alone").
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.macrobond_loader import fetch_raw
from ..data.macrobond_registry import AUTHORS_VINTAGE
from ..data.transforms import build_model_data
from ..estimation.replication import fit_full, fit_precovid
from ..simulation.decomposition import decompose
from ..simulation.irf import irf, shock_sizes
from ..simulation.model import SimModel

END = "2023Q2"
GSCPI_FILL = -0.035            # authors' pre-sample fill for GSCPI (2019 mean), alternative_shortages.do
GOOGLE_STEADY, GSCPI_STEADY = 5.0, GSCPI_FILL
MB_COLS_ORDER = [("prices", ("CPIAUCSL", "CPIENGSL", "CPIUFDSL")), ("productivity", ("OPHNFB",)),
                 ("ECI (2001+)", ("ECIWAG",)), ("V/U (2001+)", ("VOVERU",)),
                 ("Cleveland expectations", ("EXPINF1YR", "EXPINF10YR"))]
IRF_HORIZONS = (1, 4, 8, 16, 27)       # quarters after the shock quarter (0 = impact)


@dataclass(frozen=True)
class Case:
    name: str
    swap: tuple[str, ...] = ()           # raw columns taken from Macrobond
    shortage: str = "google"             # google | gscpi_authors_file | gscpi_mb | gscpi_mb_vintage
    vintage: bool = False                # Macrobond as of the authors' vintage instead of current
    eci_history: str = "authors"         # authors | macrobond (Macrobond's own pre-2001 ECI)
    group: str = "ladder"


def _splice_col(authors: pd.Series, mb: pd.Series, last_authors: str = "2000Q4") -> pd.Series:
    cut = pd.Period(last_authors, "Q")
    nxt = cut + 1
    a = authors.dropna()
    if authors.name == "ECIWAG":      # chain-link the level so log differences are continuous at the join
        a = a * (mb.loc[nxt] / a.loc[nxt])
    return pd.concat([a.loc[:cut], mb.loc[nxt:]]).rename(authors.name)


def assemble(authors_raw: pd.DataFrame, case: Case) -> tuple[pd.DataFrame, pd.Series | None, float]:
    """Raw frame for a case (authors' columns, selected ones replaced), the shortage series, its pre-sample fill."""
    mb = fetch_raw(dt.datetime(*AUTHORS_VINTAGE) if case.vintage else None)
    raw = authors_raw.loc[:END].copy()
    for col in case.swap:
        if col in ("ECIWAG", "VOVERU") and not (col == "ECIWAG" and case.eci_history == "macrobond"):
            raw[col] = _splice_col(authors_raw[col], mb[col]).reindex(raw.index)
        else:
            raw[col] = mb[col].reindex(raw.index)
    if case.shortage == "google":
        return raw, None, 5.0
    gs = {"gscpi_authors_file": authors_raw["GSCPI"],
          "gscpi_mb": fetch_raw(None)["GSCPI"],
          "gscpi_mb_vintage": fetch_raw(dt.datetime(*AUTHORS_VINTAGE))["GSCPI"]}[case.shortage]
    return raw, gs.reindex(raw.index), GSCPI_FILL


def cases() -> list[Case]:
    out = [Case("L0 authors' data (Google shortage)")]
    swap: tuple[str, ...] = ()
    for lab, cols in MB_COLS_ORDER:
        swap += cols
        out.append(Case(f"L{len(out)} + {lab}", swap))
    out.append(Case(f"L{len(out)} + GSCPI replaces Google (all Macrobond, current vintage)", swap, "gscpi_mb"))
    allcols = swap
    out.append(Case("S1 as L6 but Macrobond's own ECI history (1980Q1+)", allcols, "gscpi_mb", eci_history="macrobond",
                    group="sensitivity"))
    # controls at the authors' vintage: isolates the GSCPI effect from data revisions
    out.append(Case("V0 Macrobond @ authors' vintage, Google shortage (control)", allcols, "google", True, group="vintage"))
    out.append(Case("V1 authors' data + authors' GSCPI file (their Table A8)", (), "gscpi_authors_file", group="vintage"))
    out.append(Case("V2 Macrobond @ authors' vintage + Macrobond GSCPI @ authors' vintage", allcols, "gscpi_mb_vintage", True,
                    group="vintage"))
    out.append(Case("V3 Macrobond @ authors' vintage + current GSCPI", allcols, "gscpi_mb", True, group="vintage"))
    # single swaps onto the authors' data (current vintage)
    for lab, cols in MB_COLS_ORDER:
        out.append(Case(f"A {lab} alone", cols, group="alone"))
    out.append(Case("A GSCPI (current) alone", (), "gscpi_mb", group="alone"))
    return out


SUM_VARS = {"gw": ("gw", "cf1", "vu", "diffcpicf", "magpty"),
            "gcpi": ("gcpi", "gw", "grpe", "grpf", "shortage", "magpty"),
            "cf1": ("cf1", "cf10", "gcpi"), "cf10": ("cf10", "gcpi")}


def run_case(authors_raw: pd.DataFrame, case: Case) -> dict:
    raw, short, fill = assemble(authors_raw, case)
    data = build_model_data(raw, shortage=short, shortage_fill=fill)
    full, pre = fit_full(data), fit_precovid(data)
    row: dict = {"case": case.name, "group": case.group}
    for eq, vars_ in SUM_VARS.items():
        s = full[eq].summary()
        for v in vars_:
            row[f"sum {eq}:{v}"] = s.loc[v, "sum"]
        row[f"R2 {eq}"] = full[eq].r2_corr
    row["p_sum price:shortage"] = full["gcpi"].summary().loc["shortage", "p_sum"]
    row["p_joint price:shortage"] = full["gcpi"].summary().loc["shortage", "p_joint"]
    # pre-COVID run: out-of-sample fit 2020Q1-2023Q2 (gw, cf1, cf10); price equation is full-sample by construction
    for eq in ("gw", "cf1", "cf10"):
        e = data[eq].loc["2020Q1":END] - pre[eq].predict(data).loc["2020Q1":END]
        row[f"OOS RMSE {eq}"] = float(np.sqrt((e ** 2).mean()))
    row["RMSE price eq 2020Q1-2023Q2"] = float(np.sqrt((full["gcpi"].resid.loc["2020Q1":END] ** 2).mean()))
    # IRFs (full-sample coefficients), one-s.d. shocks sized from 2020Q1 onward
    model = SimModel.from_results(full)
    resid = {k: full[k].resid for k in ("gw", "gcpi", "cf1", "cf10")}
    sz = shock_sizes(data, resid)
    for var in ("grpe", "grpf", "shortage", "vu"):
        resp = irf(model, var, sz[var])["gcpi_simul"].values
        for h in IRF_HORIZONS:
            row[f"IRF gcpi {var} h{h}"] = float(resp[4 + h])
        row[f"shock size {var}"] = sz[var]
    # decomposition of CPI inflation
    steady = {"shortage": GSCPI_STEADY if short is not None else GOOGLE_STEADY}
    dec = decompose(model, data, steady=steady)
    act = data["gcpi"].reindex(dec.index)
    base = dec.baseline["gcpi"]
    win = dec.index >= pd.Period("2020Q1")
    row["decomp baseline RMSE vs actual gcpi 2020Q1-2023Q2"] = float(np.sqrt(((base - act)[win] ** 2).mean()))
    for per in ("2021Q2", "2022Q2"):
        i = dec.index.get_loc(pd.Period(per, "Q"))
        for v in ("shortage", "grpe", "grpf", "vu", "magpty"):
            row[f"decomp {per} {v}"] = float(dec.contributions[v]["gcpi"].iloc[i])
        row[f"decomp {per} initial conditions"] = float(dec.runs["all"]["gcpi"].iloc[i])
        row[f"decomp {per} actual"] = float(act.iloc[i])
    sel = (dec.index >= pd.Period("2021Q1")) & (dec.index <= pd.Period("2022Q4"))
    for v in ("shortage", "grpe", "grpf", "vu", "magpty"):
        row[f"decomp avg 2021-22 {v}"] = float(dec.contributions[v]["gcpi"][sel].mean())
    row["decomp avg 2021-22 initial conditions"] = float(dec.runs["all"]["gcpi"][sel].mean())
    row["decomp avg 2021-22 actual"] = float(act[sel].mean())
    row["_full"], row["_data"], row["_dec"], row["_model"], row["_sizes"] = full, data, dec, model, sz
    return row


def run_all(authors_raw: pd.DataFrame) -> list[dict]:
    return [run_case(authors_raw, c) for c in cases()]


def to_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]).set_index("case")
