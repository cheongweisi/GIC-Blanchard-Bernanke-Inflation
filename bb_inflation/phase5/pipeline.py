"""Stage functions of the Phase 5 pipeline (called by phase5/run_phase5.py). Outputs go to the top-level `phase5/` folder only."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import PHASE3_PULL, PROJECT_ROOT
from ..scenarios.pin import PHASE4_PULL
from . import data as D
from . import estimate as E

P5 = PROJECT_ROOT / "phase5"
COEF = P5 / "coefficients"
ORIGIN = "2023Q2"


def stage_estimate() -> dict:
    COEF.mkdir(parents=True, exist_ok=True)
    p = D.load()
    data = p.model
    # ---- headline: current-vintage data truncated at 2023Q2
    res23 = E.fit(data, ORIGIN)
    c23 = E.coef_long(res23, data)
    c23.to_csv(COEF / "Bstar_coefficients_2023Q2.csv", index=False)
    stats23 = E.fit_stats(res23)
    stats23.to_csv(COEF / "estimation_summary_2023Q2.csv", index=False)
    # ---- reference: full-sample production B* (through 2026Q2)
    res26 = E.fit(data, "2026Q2")
    c26 = E.coef_long(res26, data)
    c26.to_csv(COEF / "Bstar_coefficients_2026Q2_fullsample.csv", index=False)
    cmp_c, cmp_b = E.compare(c23, c26, E.block_sums(res23, data), E.block_sums(res26, data))
    # block sums in the 2023Q2 fit are HAC with the 2023Q2 sample
    cmp_c.to_csv(COEF / "coefficient_comparison_2023Q2_vs_2026Q2.csv", index=False)
    cmp_b.to_csv(COEF / "block_sum_comparison_2023Q2_vs_2026Q2.csv", index=False)
    # ---- auxiliary models, information through 2023Q2 only
    lv = p.levels
    aux = {**E.oil_bridge_quarterly(lv, ORIGIN), **E.gscpi_ar1(data, ORIGIN)}
    ar1 = E.ar_benchmark(data["gcpi"], 1, ORIGIN)
    ar4 = E.ar_benchmark(data["gcpi"], 4, ORIGIN)
    (COEF / "auxiliary_models_2023Q2.json").write_text(json.dumps({"aux": aux, "ar1": ar1, "ar4": ar4}, indent=2))
    # ---- SVAR-X matrices
    mats = E.svarx_matrices_table(c23)
    with pd.ExcelWriter(COEF / "svarx_matrices_Bstar_2023Q2.xlsx") as w:
        for k, m in mats.items():
            m.to_excel(w, sheet_name=k)
    # ---- vintage sensitivity: as-of 2023-09-15 data
    dv, lvv = D.load_vintage_2023()
    resv = E.fit(dv, ORIGIN)
    cv = E.coef_long(resv, dv)
    cv.to_csv(COEF / "Bstar_coefficients_2023Q2_vintage20230915.csv", index=False)
    cvm, cvb = E.compare(c23, cv, E.block_sums(res23, data), E.block_sums(resv, dv))
    cvm.rename(columns=lambda c: c.replace("_2026Q2", "_vintage20230915")).to_csv(
        COEF / "coefficient_comparison_current_vs_vintage20230915.csv", index=False)
    cvb.rename(columns=lambda c: c.replace("_2026Q2", "_vintage20230915")).to_csv(
        COEF / "block_sum_comparison_current_vs_vintage20230915.csv", index=False)
    auxv = {**E.oil_bridge_quarterly(lvv, ORIGIN), **E.gscpi_ar1(dv, ORIGIN)}
    (COEF / "auxiliary_models_2023Q2_vintage20230915.json").write_text(json.dumps({"aux": auxv}, indent=2))
    meta = {
        "origin": ORIGIN, "estimation_sample": f"{START_Q}-{ORIGIN}", "specification": "Model B* (production): authors' four equations, "
        "4 lags, shortage = GSCPI 2-quarter trailing mean (lag 0), Q2/Q3-2020 wage dummies (in sample), restricted LS (sum-to-one)",
        "headline_data": {"phase3_pull": PHASE3_PULL, "oil_pull": PHASE4_PULL, "note": "current vintage (retrieved 2026-10-17/18), truncated at 2023Q2"},
        "vintage_sensitivity_data": "data_cache/macrobond/asof_20230915 (Macrobond as-of 2023-09-15)",
        "pre_2001_history": "authors' public V/U and ECI through 2000Q4 (spliced as in Phase 3)",
        "nobs": {r.eq: int(r.nobs) for r in stats23.itertuples()},
        "auxiliary": aux, "ar1": ar1, "ar4": ar4,
    }
    (COEF / "estimation_metadata.json").write_text(json.dumps(meta, indent=2))
    return {"c23": c23, "c26": c26, "cmp": cmp_c, "cmp_b": cmp_b, "stats": stats23, "aux": aux, "ar1": ar1, "ar4": ar4, "p": p,
            "cv": cv, "cvm": cvm, "cvb": cvb, "auxv": auxv}


START_Q = "1990Q1"


def realised_inputs(levels: pd.DataFrame) -> pd.DataFrame:
    """Realised outturns after the origin expressed in the units of the Inputs sheets (full precision)."""
    q = pd.period_range("2023Q3", "2026Q2", freq="Q")
    ann = lambda s: 100.0 * ((s / s.shift(1)) ** 4 - 1.0)          # noqa: E731
    out = pd.DataFrame(index=q)
    out["brent"] = levels["brent"].reindex(q)
    out["cpie_qoq"] = ann(levels["cpi_energy"]).reindex(q)
    out["cpif_qoq"] = ann(levels["cpi_food"]).reindex(q)
    out["gscpi"] = levels["gscpi"].reindex(q)
    out["vu"] = levels["vu"].reindex(q)
    out["prod_qoq"] = ann(levels["prod"]).reindex(q)
    for k in ("af_gw", "af_gcpi", "af_cf10", "af_cf1"):
        out[k] = np.nan
    return out


def stage_workbook(path: Path | None = None, hist=None, realised=None, aux=None, coef=None, coef_file=None, meta_extra=None) -> Path:
    from . import workbook as W
    p = D.load()
    lv = p.levels if hist is None else hist
    est = None
    if aux is None:
        meta_j = json.loads((COEF / "estimation_metadata.json").read_text())
        aux = meta_j["auxiliary"]
    if coef is None:
        coef = pd.read_csv(COEF / "Bstar_coefficients_2023Q2.csv")
    hist_df = lv.loc["2019Q1":"2023Q2"]
    real_df = p.levels.loc["2023Q3":"2026Q2"] if realised is None else realised
    path = path or (P5 / "Phase5_Assumptions.xlsx")
    meta = {"estimation_sample": "1990Q1-2023Q2",
            "data_vintage": f"Current-vintage Macrobond data (Phase 3 pull {PHASE3_PULL}; oil {PHASE4_PULL}) truncated at 2023Q2 for estimation and history; "
                            f"outturns 2023Q3-2026Q2 from the same pull. Revised data, not real-time vintages (see METHODOLOGY_NOTE.md).",
            "realised_flags": p.flags}
    meta.update(meta_extra or {})
    inputs_b = realised_inputs(pd.concat([p.levels.loc[:"2026Q2"]]))
    W.build_workbook(path, hist_df, real_df, aux, coef, inputs_b, coef_file or "coefficients/Bstar_coefficients_2023Q2.csv", meta)
    return path
