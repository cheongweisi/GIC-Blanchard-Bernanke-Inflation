"""Data for Phase 5: raw quarterly levels in the units the workbook uses, for the estimation/history window and the realised outturns.

Two data vintages:
  current   the pinned Phase 3 pull (retrieved 2026-10-17) plus the pinned Phase 4 oil series, truncated at 2023Q2 for estimation
            and initial conditions. These are REVISED data (see METHODOLOGY_NOTE: vintage caveat).
  vintage   the Macrobond as-of 2023-09-15 vintage (data_cache/macrobond/asof_20230915), the data that existed shortly after the
            2023Q2 origin; used only for the vintage-sensitivity check.
Raw-level keys (workbook columns): brent, cpi, cpi_energy, cpi_food, eci, prod, gscpi, vu, cf1, cf10.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..config import PROJECT_ROOT
from ..data import phase3_data as P3
from ..data.authors_data import load_raw as load_authors
from ..data.macrobond_loader import splice_authors_history
from ..scenarios import pull as P4
from ..scenarios.pin import PHASE4_PULL
from ..supplement import context as C

ORIGIN = pd.Period("2023Q2", "Q")
LAST_REALISED = pd.Period("2026Q2", "Q")
HIST_START = pd.Period("2019Q1", "Q")
RAW_MAP = {"cpi": "CPIAUCSL", "cpi_energy": "CPIENGSL", "cpi_food": "CPIUFDSL", "eci": "ECIWAG", "prod": "OPHNFB",
           "gscpi": "GSCPI", "vu": "VOVERU", "cf1": "EXPINF1YR", "cf10": "EXPINF10YR"}
RAW_KEYS = ("brent", "cpi", "cpi_energy", "cpi_food", "eci", "prod", "gscpi", "vu", "cf1", "cf10")
VINTAGE_FILE = PROJECT_ROOT / "data_cache" / "macrobond" / "asof_20230915" / "quarterly_raw.csv"


@dataclass
class P5Data:
    ctx: C.Ctx
    model: pd.DataFrame            # Model B* dataset (data_star), through 2026Q2, V/U 2025Q4 bridged
    levels: pd.DataFrame           # raw levels by workbook key, through 2026Q2; V/U 2025Q4 = bridged value
    brent_q_full: pd.Series        # quarterly mean Brent, 1960Q1-2026Q3
    flags: dict[str, list[str]]    # e.g. {'vu_bridged': ['2025Q4']}


def brent_quarterly(p4: dict[str, pd.Series]) -> pd.Series:
    """Quarterly mean of the World Bank monthly Brent price (US$/bbl); only complete quarters."""
    m = p4["wocaes0935"].dropna()
    q = m.groupby(m.index.to_period("Q")).agg(["mean", "count"])
    return q.loc[q["count"] == 3, "mean"].rename("brent")


def load() -> P5Data:
    ctx = C.load()
    p4 = P4.load(PHASE4_PULL)
    bq = brent_quarterly(p4)
    raw = ctx.p3.raw.loc[:LAST_REALISED].copy()
    lv = pd.DataFrame({k: raw[c] for k, c in RAW_MAP.items()})
    lv.insert(0, "brent", bq.reindex(lv.index))
    flags: dict[str, list[str]] = {}
    if lv["vu"].isna().loc[ORIGIN + 1:].any():
        for q in lv.index[lv["vu"].isna()]:
            if q > ORIGIN:
                lv.loc[q, "vu"] = float(ctx.data_star.loc[q, "vu"])
                flags.setdefault("vu_bridged", []).append(str(q))
    return P5Data(ctx, ctx.data_star, lv[list(RAW_KEYS)], bq, flags)


def load_vintage_2023() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(model data, raw levels) built from the as-of 2023-09-15 Macrobond vintage, authors' pre-2001 V/U and ECI history spliced
    exactly as in Phase 3. Brent is the current World Bank series (not revised). Through 2023Q2."""
    mb = pd.read_csv(VINTAGE_FILE, index_col=0)
    mb.index = pd.PeriodIndex(mb.index, freq="Q", name="period")
    raw = splice_authors_history(mb, load_authors()).loc[:ORIGIN]
    d = C.model_data(raw)
    lv = pd.DataFrame({k: raw[c] for k, c in RAW_MAP.items()})
    bq = brent_quarterly(P4.load(PHASE4_PULL))
    lv.insert(0, "brent", bq.reindex(lv.index))
    return d, lv[list(RAW_KEYS)]
