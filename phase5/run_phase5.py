#!/usr/bin/env python
"""Reproduce every Phase 5 deliverable from the stored (pinned) data. No Macrobond connection is needed.

    .venv\\Scripts\\python.exe phase5\\run_phase5.py            # all stages
    .venv\\Scripts\\python.exe phase5\\run_phase5.py estimate   # coefficients through 2023Q2 + auxiliary models + comparisons
    .venv\\Scripts\\python.exe phase5\\run_phase5.py workbook   # build Phase5_Assumptions.xlsx (and recalculate it in Excel if available)
    .venv\\Scripts\\python.exe phase5\\run_phase5.py evaluate   # exercises A and B, benchmarks, variants, decomposition, tables, charts

Stage 'workbook' overwrites Phase5_Assumptions.xlsx: save your own edited copy under another name first.
The forecasting engine itself is separate and standalone: p5_forecast_engine.py (see README.md).
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))

from bb_inflation.phase5 import pipeline as PL  # noqa: E402


def main(stages):
    if "estimate" in stages:
        r = PL.stage_estimate()
        print("estimate: coefficients written;", r["stats"][["eq", "nobs", "resid_sd"]].to_dict("records"))
    if "workbook" in stages:
        path = PL.stage_workbook()
        try:
            from bb_inflation.phase5 import excel_util
            excel_util.recalc(path)
            print("workbook: built and recalculated in Excel ->", path)
        except Exception as e:                                   # noqa: BLE001
            print("workbook: built, NOT recalculated (Excel automation unavailable:", e, ")")
    if "evaluate" in stages:
        from bb_inflation.phase5 import stage_eval
        r = stage_eval.run()
        print("evaluate: done; all-residual reproduction error", r["check_all_residuals_vs_realised"])
        print(r["tabs"]["metrics"].query("`window (first h quarters)` == 12").round(2).to_string())


if __name__ == "__main__":
    a = sys.argv[1:] or ["estimate", "workbook", "evaluate"]
    main(a)
