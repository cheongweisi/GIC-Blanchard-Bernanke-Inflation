"""Shared dataset for the Phase 3 supplement.

`load()` returns the Phase 3 dataset (pinned pull, unchanged) plus `data_star`: the same model data in which the single
missing observation, V/U 2025Q4, is replaced by a flagged bridge (default: interpolate the October 2025 unemployment level
between September and November, keep all three observed JOLTS months). `data_star` is used for estimation ("Model B*"),
simulation, decompositions and IRFs; `p3.data` (hole left open) remains the Phase 3 baseline and is used to verify that the
supplement reproduces Phase 3 exactly when the bridge is switched off.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..config import PHASE3_PULL
from ..data import phase3_data as P
from ..data.transforms import build_model_data
from . import diag_pull
from . import vu_bridge as V

BRIDGE_Q = pd.Period("2025Q4", "Q")


@dataclass
class Ctx:
    p3: P.Phase3Data
    data_star: pd.DataFrame
    bridge_method: str
    bridge_value: float
    last: str
    supp_pull: str


def model_data(raw: pd.DataFrame) -> pd.DataFrame:
    d = build_model_data(raw, shortage=raw["GSCPI"], shortage_fill=P.GSCPI_FILL)
    d["shortagema2"] = d["shortage"].rolling(2, min_periods=2).mean()
    d["shortagema4"] = d["shortage"].rolling(4, min_periods=4).mean()
    return d


def with_vu(p3: P.Phase3Data, value: float) -> pd.DataFrame:
    raw = p3.raw.copy()
    raw.loc[BRIDGE_Q, "VOVERU"] = value
    return model_data(raw)


def bridge_value(method: str, supp_pull: str | None = None, truncate: str | None = None) -> float:
    """V/U 2025Q4 under `method`; `truncate` (a month, e.g. '2025-12-01') drops every observation after it, which
    demonstrates that the bridge uses no later information."""
    S = diag_pull.load(supp_pull)
    J, U = S["uslama1304"], S["uslama1795"]
    CC = V.monthly_mean_weekly(S["uslama3350"])
    if truncate:
        t = pd.Timestamp(truncate)
        J, U, CC = J[J.index <= t], U[U.index <= t], CC[CC.index <= t]
    return V.quarter_vu(J, U, BRIDGE_Q, method, CC, V.claims_beta(U, CC)[0])


def load(method: str = "interp", pull_id: str = PHASE3_PULL) -> Ctx:
    p3 = P.build(pull_id)
    sp = diag_pull.latest()
    val = bridge_value(method, sp)
    return Ctx(p3, with_vu(p3, val), method, val, str(p3.last_complete), sp)
