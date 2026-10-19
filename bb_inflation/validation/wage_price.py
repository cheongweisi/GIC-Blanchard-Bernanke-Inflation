"""Wage-price robustness: pre-2001 ECI splice versus Macrobond's own ECI history, and shorter estimation samples.

All cases keep the authors' specification (only the price equation's shortage block differs by `variant`). The
estimation sample starts in 1990Q1 (authors), 2001Q1 or 2005Q1; lags are built from earlier data, so the first
dependent observation is the start quarter. Runs: 'full' = everything through 2023Q2 (wage dummies), 'pre' = the
authors' pre-COVID wage/expectation equations (through 2019Q4) with the price equation through 2023Q2.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import FULL_END, PRECOVID_END
from ..data.transforms import build_model_data
from ..estimation.inference import irf_bands_mc, with_hac
from ..estimation.rls import estimate_model
from ..simulation.general import add_derived, irf_general
from ..simulation.irf import shock_sizes
from ..simulation.model import SimModel
from . import ladder
from .specs import Variant, equations_for

STARTS = ("1990Q1", "2001Q1", "2005Q1")
ECI = {"authors splice": "authors", "Macrobond ECI": "macrobond"}
ALL_MB = tuple(c for _, cols in ladder.MB_COLS_ORDER for c in cols)
IRF_H = (4, 8, 16, 27)


def build_data(authors_raw: pd.DataFrame, v: Variant, eci: str) -> pd.DataFrame:
    shortage = "google" if v.source == "google" else "gscpi_mb"
    case = ladder.Case(f"{eci}/{shortage}", ALL_MB, shortage, eci_history=ECI[eci], group="wp")
    raw, short, fill = ladder.assemble(authors_raw, case)
    return add_derived(build_model_data(raw, shortage=short, shortage_fill=fill), v.derived_dict)


def run_case(data: pd.DataFrame, v: Variant, start: str, n_mc: int = 500, seed: int = 0) -> dict:
    full = estimate_model(data, equations_for(v, True), {k: FULL_END for k in "gw gcpi cf1 cf10".split()}, start)
    eq_pre = equations_for(v, False)
    pre = estimate_model(data, eq_pre, {"gw": PRECOVID_END, "gcpi": FULL_END, "cf1": PRECOVID_END, "cf10": PRECOVID_END}, start)
    hac = {k: with_hac(r, data) for k, r in full.items()}
    hac_pre = {k: with_hac(r, data) for k, r in pre.items()}
    row: dict = {"N wage (full)": full["gw"].nobs, "N price": full["gcpi"].nobs, "N wage (pre)": pre["gw"].nobs}
    for tag, res, h in (("full", full, hac), ("pre", pre, hac_pre)):
        sw, sp = res["gw"].summary(), res["gcpi"].summary()
        hw, hp = h["gw"].summary(), h["gcpi"].summary()
        row[f"wage:V/U sum ({tag})"] = sw.loc["vu", "sum"]
        row[f"wage:V/U p HAC ({tag})"] = hw.loc["vu", "p_sum"]
        row[f"wage:gw lags ({tag})"] = sw.loc["gw", "sum"]
        row[f"wage:cf1 ({tag})"] = sw.loc["cf1", "sum"]
        row[f"wage:catch-up ({tag})"] = sw.loc["diffcpicf", "sum"]
        row[f"wage:LR effect of +0.5 V/U, pp ({tag})"] = 0.5 * sw.loc["vu", "sum"] / (1 - sw.loc["gw", "sum"])
        row[f"wage:R2 ({tag})"] = res["gw"].r2_corr
    sp = full["gcpi"].summary()
    hp = hac["gcpi"].summary()
    row["price:wage pass-through (sum gw)"] = sp.loc["gw", "sum"]
    row["price:lagged inflation (sum)"] = sp.loc["gcpi", "sum"]
    row["price:lagged inflation p HAC"] = hp.loc["gcpi", "p_sum"]
    row["price:energy"] = sp.loc["grpe", "sum"]
    row["price:food"] = sp.loc["grpf", "sum"]
    row["price:productivity"] = sp.loc["magpty", "sum"]
    sk = v.block.var if v.block else None
    if sk:
        row["price:shortage sum"] = sp.loc[sk, "sum"]
    row["price:R2"] = full["gcpi"].r2_corr
    # impulse responses and HAC Monte-Carlo bands
    derived = v.derived_dict
    resid = {k: full[k].resid for k in ("gw", "gcpi", "cf1", "cf10")}
    sizes = shock_sizes(data, resid)
    fn = lambda m, s, z: irf_general(m, s, z, derived=derived)      # noqa: E731
    model = SimModel.from_results(full)
    bands = {}
    for s in ("vu", "grpe"):
        pt = fn(model, s, sizes[s])
        bands[s] = irf_bands_mc(hac, fn, {s: sizes[s]}, n=n_mc, seed=seed)[s]
        for h in IRF_H:
            row[f"IRF {s} gcpi h{h}"] = float(pt["gcpi_simul"].values[4 + h])
            row[f"IRF {s} gcpi h{h} lo"] = float(bands[s]["q05"].values[4 + h])
            row[f"IRF {s} gcpi h{h} hi"] = float(bands[s]["q95"].values[4 + h])
        if s == "vu":
            for h in (8, 27):
                row[f"IRF vu gw h{h}"] = float(pt["gw_simul"].values[4 + h])
    return {"row": row, "full": full, "pre": pre, "bands": bands, "model": model, "sizes": sizes,
            "irf_vu": fn(model, "vu", sizes["vu"])["gcpi_simul"].values}
