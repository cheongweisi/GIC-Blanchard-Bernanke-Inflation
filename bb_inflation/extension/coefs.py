"""Coefficient summaries with HAC inference, and rule-based plausibility / stability flags."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ..estimation.inference import with_hac
from ..validation.specs import VARIANTS


def blocks_for(variant: str) -> dict[str, list[str]]:
    sh = VARIANTS[variant].block.var
    return {"gw": ["gw", "cf1", "vu", "diffcpicf", "magpty"],
            "gcpi": ["gcpi", "gw", "grpe", "grpf", sh, "magpty"],
            "cf1": ["cf1", "cf10", "gcpi"], "cf10": ["cf10", "gcpi"]}


def sum_se(res_hac, names: list[str]) -> tuple[float, float, float]:
    idx = [list(res_hac.coef.index).index(n) for n in names]
    R = np.zeros(len(res_hac.coef))
    R[idx] = 1.0
    s = float(R @ res_hac.coef.values)
    se = float(np.sqrt(max(R @ res_hac.cov.values @ R, 0.0)))
    p = float(2 * stats.t.sf(abs(s / se), res_hac.df_resid)) if se > 0 else np.nan
    return s, se, p


def coef_summary(models: dict[str, dict], data: pd.DataFrame, variant_of: dict[str, str]) -> pd.DataFrame:
    rows = []
    for name, res in models.items():
        blocks = blocks_for(variant_of[name])
        for eq, r in res.items():
            h = with_hac(r, data)
            for b in blocks[eq]:
                names = r.block_names(b)
                s, se, p = sum_se(h, names)
                rows.append({"model": name, "eq": eq, "block": b, "sum": s, "se_hac": se, "p_hac": p,
                             "N": r.nobs, "sample": f"{r.sample[0]}-{r.sample[1]}", "R2 (descriptive)": r.r2_corr})
    return pd.DataFrame(rows)


def flags(summary: pd.DataFrame, ref: str = "A") -> pd.DataFrame:
    """Plausibility rules (sign/range) per model, and instability relative to `ref` (|change| > 2 HAC s.e. of ref
    and > 0.05)."""
    S = summary.set_index(["model", "eq", "block"])
    out = []

    def val(m, eq, b):
        return S.loc[(m, eq, b), "sum"]

    for m in summary.model.unique():
        v = lambda eq, b: val(m, eq, b)               # noqa: E731
        shortage_block = [b for b in S.loc[m].loc["gcpi"].index if b.startswith("shortage")][0]
        rules = [("price: lagged-inflation sum outside (0,1)", not 0 < v("gcpi", "gcpi") < 1),
                 ("price: wage pass-through outside (0,1)", not 0 < v("gcpi", "gw") < 1),
                 ("price: energy sum <= 0", v("gcpi", "grpe") <= 0), ("price: food sum <= 0", v("gcpi", "grpf") <= 0),
                 ("price: shortage effect <= 0", v("gcpi", shortage_block) <= 0),
                 ("wage: V/U sum <= 0", v("gw", "vu") <= 0),
                 ("wage: own-lag + expectations weights outside (0,1)", not 0 < v("gw", "gw") < 1),
                 ("cf1: weight on cf10 or gcpi negative", v("cf1", "cf10") < 0 or v("cf1", "gcpi") < 0),
                 ("cf10: weight on gcpi negative", v("cf10", "gcpi") < 0)]
        for rule, hit in rules:
            out.append({"model": m, "kind": "plausibility", "rule": rule, "flag": bool(hit)})
        if m != ref and (ref, "gcpi", "gw") in S.index:
            for (eq, b), r in S.loc[m].iterrows():
                if (ref, eq, b) not in S.index:
                    continue
                a = S.loc[(ref, eq, b)]
                d = r["sum"] - a["sum"]
                out.append({"model": m, "kind": f"instability vs {ref}", "rule": f"{eq}:{b} changed by {d:+.3f} (ref s.e. {a['se_hac']:.3f})",
                            "flag": bool(abs(d) > 2 * a["se_hac"] and abs(d) > 0.05)})
    return pd.DataFrame(out)
