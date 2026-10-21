# Phase 5: pseudo-out-of-sample CPI forecasts from 2023Q2, with an Excel assumptions workbook

Start with `METHODOLOGY_NOTE.md` (method, results, error decomposition, limitations). `PRE_IMPLEMENTATION_REVIEW.md` lists the obstacles found in Model B* before building and the defaults chosen.

| Deliverable | File |
|---|---|
| 1. Editable assumptions workbook (light blue + red = editable; green = model-generated; grey = historical realised) | `Phase5_Assumptions.xlsx` |
| 2. Reproducible forecasting engine (standalone: numpy, pandas, openpyxl) | `p5_forecast_engine.py` |
| 3. Forecasts and forecast errors | `output/forecasts_and_errors.xlsx` / `.csv`; engine outputs `output/forecast_A.*`, `forecast_B.*` |
| 4. Charts | `output/charts/fig1..fig4*.png` |
| 5. Methodological note | `METHODOLOGY_NOTE.md` |
| Estimated 2023Q2 coefficients, comparison with full-sample B*, SVAR-X matrices, vintage sensitivity | `coefficients/` |
| Performance tables, decomposition, variants | `output/metrics_windows.csv`, `errors_at_h4_h8_h12.csv`, `error_decomposition_A.csv`, `variants_*.csv` |
| Hash manifest of everything that existed before Phase 5 (Phases 1-4c untouched) | `pre_phase5_manifest.sha256` |

## Use the engine on your own assumptions

1. Copy `Phase5_Assumptions.xlsx`, edit `Inputs_A` or `Inputs_B` (blank cell = documented default rule; see the Variables sheet), save in Excel.
2. From the project root:

```
.venv\Scripts\python.exe phase5\p5_forecast_engine.py --workbook phase5\Phase5_Assumptions.xlsx --scenario A --with-realised
.venv\Scripts\python.exe phase5\p5_forecast_engine.py --workbook phase5\Phase5_Assumptions.xlsx --scenario B --horizon 2029Q2
```

Coefficients are read from `coefficients/Bstar_coefficients_2023Q2.csv` and never re-estimated. The output Excel file has the forecast, the transformed inputs the engine used (compare with the workbook's `Model_Inputs_A/B`), a log of every default rule applied, and the checks.

## Reproduce everything

```
.venv\Scripts\python.exe phase5\run_phase5.py            # estimate -> workbook -> evaluate (stored data only)
.venv\Scripts\python.exe -m pytest tests\test_phase5.py -q
```

`run_phase5.py workbook` overwrites `Phase5_Assumptions.xlsx`; keep your own edited copies under another name. Research code is in `bb_inflation/phase5/`.
