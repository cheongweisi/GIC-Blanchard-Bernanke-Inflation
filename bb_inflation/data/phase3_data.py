"""Model dataset for the 2026 extension, built from an explicit stamped Macrobond pull.

Rules (no silent substitution):
* The sample ends at the *last complete quarter*: the latest quarter in which every raw series is observed.
  Later quarters that are partly observed (e.g. CPI and GSCPI for 2026Q3 but no ECI, productivity or JOLTS) are
  reported, never used.
* The authors' V/U and ECI history is used through 2000Q4 and Macrobond afterwards (baseline); `eci_history=
  "macrobond"` uses Macrobond's own ECI for the whole sample (sensitivity).
* A quarter inside the sample that is missing because an input month was never published (the unemployment level
  for October 2025, hence V/U 2025Q4) stays NaN in `raw`/`data`; estimation drops the observations that need it.
  `bridge_vu=True` additionally returns a copy in which that V/U is filled with the ratio of the available
  months' means, flagged in `flags`; it is intended for simulations and diagnostics, and for a labelled
  sensitivity, never for the baseline estimation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import PHASE3_PULL
from . import macrobond_audit as audit
from .authors_data import load_raw
from .macrobond_loader import splice_authors_history
from .macrobond_registry import REGISTRY
from .transforms import build_model_data

GSCPI_FILL = -0.035          # authors' pre-sample fill for GSCPI (Table A8 convention)
RAW_COLS = ("CPIAUCSL", "CPIENGSL", "CPIUFDSL", "OPHNFB", "ECIWAG", "VOVERU", "EXPINF1YR", "EXPINF10YR", "GSCPI")


@dataclass
class Phase3Data:
    pull_id: str
    eci_history: str
    last_complete: pd.Period
    raw: pd.DataFrame                       # spliced raw series, through last_complete (NaN where unpublished)
    data: pd.DataFrame                      # model variables incl. dummies and shortagema2, through last_complete
    data_bridged: pd.DataFrame              # same with V/U 2025Q4 bridged (simulation/diagnostics only)
    flags: pd.DataFrame                     # boolean flags by quarter (bridged observations)
    partial_quarters: pd.DataFrame          # quarters after last_complete with partial coverage
    notes: list[str] = field(default_factory=list)


def last_complete_quarter(mb: pd.DataFrame) -> pd.Period:
    ok = mb[list(RAW_COLS)].notna().all(axis=1)
    return ok[ok].index[-1]


def _native(pull_id: str, ticker: str) -> pd.Series:
    s = pd.read_csv(audit.PULLS / pull_id / "native" / f"{ticker}.csv", index_col=0, parse_dates=True)["value"]
    return s


def vu_bridge_values(pull_id: str, quarters: list[pd.Period]) -> dict[pd.Period, float]:
    """For quarters where V/U is undefined only because some months are missing: ratio of the means of the
    JOLTS openings and unemployment level over the months in which *both* are observed."""
    num, den = REGISTRY["VOVERU"].tickers
    jo, un = _native(pull_id, num), _native(pull_id, den)
    out = {}
    for q in quarters:
        m = pd.date_range(q.start_time, periods=3, freq="MS")
        both = [d for d in m if d in jo.index and d in un.index]
        if both:
            out[q] = float(jo.loc[both].mean() / un.loc[both].mean())
    return out


def build(pull_id: str = PHASE3_PULL, eci_history: str = "authors", through: str | None = None) -> Phase3Data:
    mb = audit.load_pull(pull_id)
    last = pd.Period(through, "Q") if through else last_complete_quarter(mb)
    authors = load_raw()
    raw = splice_authors_history(mb, authors)
    if eci_history == "macrobond":
        raw["ECIWAG"] = mb["ECIWAG"]
    elif eci_history != "authors":
        raise ValueError(eci_history)
    raw = raw.loc[:last]
    notes = [f"pull {pull_id}; last complete quarter {last}",
             "V/U and ECI: authors' history through 2000Q4, Macrobond afterwards"
             + (" (ECI: Macrobond's own history for the whole sample)" if eci_history == "macrobond" else "")]

    holes = [q for q in raw.loc["1990Q1":].index if raw.loc[q, list(RAW_COLS)].isna().any()]
    bridged = raw.copy()
    flags = pd.DataFrame(False, index=raw.index, columns=["vu_bridged"])
    for q, v in vu_bridge_values(pull_id, [h for h in holes if np.isnan(raw.loc[h, "VOVERU"])]).items():
        bridged.loc[q, "VOVERU"] = v
        flags.loc[q, "vu_bridged"] = True
        notes.append(f"V/U {q} undefined (a monthly input was not published); bridged value {v:.4f} = ratio of means over "
                     f"the months where both JOLTS and unemployment exist (simulation/diagnostics only)")

    def model_data(r: pd.DataFrame) -> pd.DataFrame:
        d = build_model_data(r, shortage=r["GSCPI"], shortage_fill=GSCPI_FILL)
        d["shortagema2"] = d["shortage"].rolling(2, min_periods=2).mean()
        d["shortagema4"] = d["shortage"].rolling(4, min_periods=4).mean()
        return d

    data, data_b = model_data(raw), model_data(bridged)
    partial = mb.loc[last + 1:, list(RAW_COLS)]
    partial = partial[partial.notna().any(axis=1)]
    for q, row in partial.iterrows():
        notes.append(f"{q} is partial ({int(row.notna().sum())}/{len(RAW_COLS)} series observed; missing: "
                     f"{', '.join(c for c in RAW_COLS if np.isnan(row[c]))}) and is not used")
    return Phase3Data(pull_id, eci_history, last, raw, data, data_b, flags, partial, notes)
