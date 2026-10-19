# Phase 1 replication log

Date: 2026-10-16. Specification unchanged from the authors'. All checks are automated in `tests/` (34 Phase-1 tests, part of a suite that had 66 tests at the time of writing and 80 after Phase 3; run
`.venv\Scripts\python.exe -m pytest tests -q`). Figures/tables: `scripts/run_replication.py` → `outputs/phase1/`.

## 1. What was validated, and against what

| Component | Target | Result |
|---|---|---|
| Derived variables (gcpi, gw, magpty, grpe, grpf, diffcpicf …) | `eq_simulations_data.xls` | match to 2e-4 (Stata float32 rounding, D12) |
| Coefficients, all 4 equations, full and pre-COVID | `eq_coefficients*.xlsx` | max abs diff < 5e-6 |
| Sum of coefficients, p-values (sum and joint), R², N | `summary_stats_*.xlsx` | match (p-values to 5e-5) |
| Fitted values and residuals (in-sample) | `eq_simulations_data.xls` | match to 1e-5 |
| Out-of-sample predictions 2020Q1-2023Q2 (Figs 3, 7-9) | `eq_simulations_data_restricted.xls` | match to 2e-3 |
| Paper Tables 2, 4, 5 (pre-COVID) | published values | all sums, p-values, R², N reproduced (3 decimals; two p-values differ by 0.001-0.003) |
| Paper Table 3 (price equation, 1990Q1-2023Q1, N=133) | published values | sums within 0.002, R² .947, shortage p(sum) .275 vs .281 (D3/D15) |
| IRFs (energy, food, shortage, V/U; 32 quarters) | `results_*.xls` | match to 5e-4 |
| Historical decomposition (8 removal runs, 4 variables each) | `remove_*.xls` | match to 5e-4; additivity checked to 1e-9 |
| Conditional forecasts (V/U to 0.8/1.2/1.8; 405 quarters) | `terminal_*.xlsx` | match to 1e-3 |
| Paper's headline forecast numbers | text of paper | CPI inflation 2.67% (V/U→1.2) and 2.05% (V/U→0.8) after 8 quarters: "about 2.7" and "close to 2" ✓ |
| GSCPI variant (Phase 2 anchor), Appendix Table A8 | `Shortage Alternatives/eq_coefficients.xlsx` | all 26 coefficients < 5e-6; shortage sum .271, p .016, R² .940 ✓ |
| Figures 12 and 14 | published PNGs | visually identical bar heights / paths |
| Our own estimated coefficients vs authors' coefficients in simulations | | V/U IRF differs < 1e-3 |

## 2. Discrepancies (numbering continues docs/PHASE1-2_REPORT.md §5; D1-D11 there)

* **D1** (confirmed) Sample "1989Q1" is effectively 1990Q1 because Stata applies `keep` before the lag operators; N = 134 / 120 reproduced exactly only with a 1990Q1 start.
* **D2** (confirmed) Shipped IRF/decomposition/forecast outputs are generated from the **full-sample** coefficients with COVID dummies (our simulations from those coefficients reproduce the files). The paper text says the wage/expectation equations are pre-COVID. Figs 3, 7-9 use the pre-COVID run. Both are implemented (`fit_full`, `fit_precovid`).
* **D3** (explained) Paper tables end 2023Q1; package 2023Q2.
* **D9** (confirmed) Paper footnote 15 shock sizes and ranges (energy 32, food 3.2, shortage 11.6, V/U 0.5; food range -1.3…8.9, energy -52…45) do not match the shipped data (2020Q1-2023Q2 s.d. 29.1, 3.87, 10.1, 0.58; food -3.2…8.7, energy -46.8…40.1). The paper used an earlier data vintage. The shipped IRF files use the shipped-data s.d., which we reproduce.
* **D12** Stata `gen` makes float32 variables, so the authors' coefficients carry ~1e-6 noise relative to double-precision estimates. Not a substantive issue; test tolerances reflect it.
* **D13** Paper: the grey "initial conditions" bar in Figs 12-13 "also includes" productivity. Code: productivity is a separate bar and the grey bar is the simulation with productivity held at 2 (not the actual path), plus dummies off. Our figure follows the code.
* **D14** Paper text on the V/U IRF ("about 0.7 after 6 quarters, 1.0 after 12, then +0.15 pp per year") vs shipped output (0.78 after 6, 1.09 after 12, ≈ +0.09 pp per year thereafter). The shipped output is reproduced exactly, so the difference lies in the paper's text/vintage.
* **D15** Re-estimating the price equation to 2023Q1 gives sums 0.333/0.667/0.066/0.126/0.018/-0.144 vs published 0.335/0.665/0.066/0.126/0.018/-0.143; consistent with a slightly earlier CPI/ECI/productivity vintage in the paper. Cannot be resolved without that vintage.
* **D16** The pre-COVID price equation in the package is the full-sample one (identical numbers in both runs), as the paper states.

## 3. Not done yet (still Phase 1)

* Appendix variants other than GSCPI: PCE (A6), SPF (A7), V/U in the price equation (A9), non-linear V/U (A10); the pre-COVID-coefficient versions of IRFs/decompositions; Figures 1-2, 4-6 (simple model, PCA, shortages) are out of scope.
* Side-by-side numeric overlay with the published PNG/PDF figures (only visually compared for Figs 12 and 14 so far; Figs 3, 7-11, 13 outputs are generated but not yet inspected one by one).
* `docs/data_dictionary.md` (series, sources, units, SA, publication lags) — belongs to Phase 2 Step 1.
