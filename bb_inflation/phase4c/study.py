"""The Phase 4c study object: data, the four vintages' fits, their joint (stacked) covariance and joint coefficient draws.

HYB shares its wage, cf1 and cf10 equations with B19 by construction (same data end), so it is aliased to B19 there; only its price equation
(1990Q1-2023Q2) is a separate member of the price-equation stack.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..scenarios import engine as E
from . import samples as S
from . import stack as K

N_DRAWS = 2000
SEED = 20261018


@dataclass
class Study:
    ctx: object
    data: pd.DataFrame
    fits: dict[str, dict]                          # vintage -> eq -> EquationResult (classical covariance)
    hacs: dict[str, dict]                          # vintage -> eq -> EquationResult (HAC covariance)
    stacks: dict[str, K.Stacked]                   # eq -> stacked joint inference
    draws: dict[str, dict[str, np.ndarray]]        # eq -> vintage key -> (n, k) joint draws
    n: int
    notes: list[str] = field(default_factory=list)

    def key(self, eq: str, vint: str) -> str:
        return vint if vint in self.stacks[eq].keys else "B19"      # HYB wage/cf1/cf10 == B19

    def names(self) -> dict[str, list[str]]:
        return {eq: list(st.cols) for eq, st in self.stacks.items()}

    def coefset(self, vint: str, point: bool = False) -> E.CoefSet:
        vals = {}
        for eq, st in self.stacks.items():
            k = self.key(eq, vint)
            vals[eq] = st.beta[k][None, :] if point else self.draws[eq][k]
        return E.CoefSet(self.names(), vals)

    def block_draws(self, eq: str, vint: str, block) -> np.ndarray:
        st = self.stacks[eq]
        return self.draws[eq][self.key(eq, vint)] @ st.selector(block)

    def block_point(self, eq: str, vint: str, block) -> float:
        st = self.stacks[eq]
        return float(st.beta[self.key(eq, vint)] @ st.selector(block))


def build(n: int = N_DRAWS, seed: int = SEED) -> Study:
    ctx, data = S.load()
    fits = {k: S.fit(data, v) for k, v in S.VINTAGES.items()}
    hacs = {k: S.hac(f, data) for k, f in fits.items()}
    stacks, draws = {}, {}
    rng = np.random.default_rng(seed)
    for eq in S.EQS:
        keys = ["B19", "HYB", "B23", "B26"] if eq == "gcpi" else ["B19", "B23", "B26"]
        stacks[eq] = K.stack(eq, {k: fits[k][eq] for k in keys}, data)
        draws[eq] = stacks[eq].draws(n, rng)
    notes = [f"pull {ctx.p3.pull_id}; supplementary pull {ctx.supp_pull}; last complete quarter {ctx.last}; V/U 2025Q4 bridged ({ctx.bridge_method}, {ctx.bridge_value:.4f})",
             f"{n} joint coefficient draws per equation (seed {seed}); equations drawn independently"]
    return Study(ctx, data, fits, hacs, stacks, draws, n, notes)
