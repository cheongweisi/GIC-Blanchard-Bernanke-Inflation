"""Phase 4b helpers: the Phase 4 world (unchanged), output folder, small utilities. Nothing here modifies Phase 1-4 code or outputs."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from ..config import OUTPUTS
from ..scenarios import scenario as S
from ..scenarios import world as W

OUT = OUTPUTS / "phase4b"
OUT.mkdir(parents=True, exist_ok=True)
warnings.filterwarnings("ignore")


def world(nowcast: bool = True, n_draws: int = W.N_DRAWS) -> W.World:
    w = W.build(nowcast=nowcast, n_draws=n_draws)
    return S.finalise(w)


def save(df: pd.DataFrame, name: str, index: bool = True) -> None:
    df.to_csv(OUT / name, index=index)


def yoy_pct_from_ann(gc: np.ndarray) -> np.ndarray:
    """y/y inflation (%, compounded) at every t>=3 from annualised quarterly inflation (last 4 quarters averaged)."""
    out = np.full(len(gc), np.nan)
    for t in range(3, len(gc)):
        out[t] = 100.0 * (np.exp(np.mean(gc[t - 3:t + 1]) / 100.0) - 1.0)
    return out
