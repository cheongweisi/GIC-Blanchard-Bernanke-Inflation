# Phase 5 methodological note: pseudo-out-of-sample CPI forecasts from 2023Q2 with Model B*

Origin 2023Q2, forecast quarters 2023Q3-2026Q2 (12), realised CPI available for all. Phases 1-4c are unchanged (hash manifest `pre_phase5_manifest.sha256`, checked by a test). Obstacles and defaults decided before building are in `PRE_IMPLEMENTATION_REVIEW.md`.

## 1. Model and estimation

**Model.** Production Model B*: the authors' four equations (wage growth, CPI inflation, 10-year and 1-year expected inflation), four lags, homogeneity restrictions, shortage term = two-quarter trailing mean of the GSCPI, Q2/Q3-2020 wage dummies. In structural form A0 y_t = c + sum A_i y_(t-i) + sum B_j x_(t-j), with A0 lower triangular (CPI responds to current wages; expectations to current CPI).

**Re-estimation.** All four equations on 1990Q1-2023Q2 (134 observations each), restricted least squares, HAC standard errors. No lag selection or tuning; nothing after 2023Q2 enters. Coefficients: `coefficients/Bstar_coefficients_2023Q2.csv`; structural matrices `coefficients/svarx_matrices_Bstar_2023Q2.xlsx`. This fit equals the Phase 3 "Model A" (frozen at 2023Q2) to 1e-10.

**Change relative to the full-sample B* (to 2026Q2): immaterial.** Of 65 coefficients only two move by more than one HAC standard error (wage equation 1-year expectations lags 3 and 4, 0.18 to 0.05 and 0.04 to 0.16, which offset: the block sum is 0.467 against 0.460). Block sums: price-equation wage weight 0.853 (0.845 full sample), energy 0.077 (0.075), food 0.190 (0.179), shortage 0.300 (0.288); wage equation V/U 0.708 (0.672). Residual standard deviations (pp): wage 0.68, CPI 0.71, 10y 0.19, 1y 0.29. Full tables: `coefficients/coefficient_comparison_2023Q2_vs_2026Q2.csv`, `block_sum_comparison_2023Q2_vs_2026Q2.csv`. The comparison is a screening rule, not a test (the samples overlap).

**Sample, vintage, dummies.** Data: Macrobond pull `pull_20261017T112636Z` (oil series `p4_20261018T051241Z`), authors' V/U and ECI before 2001, truncated at 2023Q2: revised, current-vintage data. Sensitivity with the as-of 2023-09-15 vintage: block sums move by at most 0.03 (under 0.25 standard errors); see `coefficients/*vintage20230915*`. Both COVID dummies are in sample and zero in forecasts.

**Auxiliary models (not part of B*; estimated to 2023Q2 only).** (i) Oil bridge, quarterly: CPI-energy growth = 1.87 + 0.304 x Brent growth (400 x dln of the quarterly average), R2 0.62, residual s.d. 15 pp annualised. (ii) GSCPI AR(1): constant -0.008, persistence 0.861. (iii) Benchmarks on CPI inflation 1990Q1-2023Q2: AR(1) (constant 2.10, phi 0.197) and AR(4) (constant 1.66; phi 0.169, 0.058, 0.154, -0.015).

## 2. Workbook and engine

`Phase5_Assumptions.xlsx`: user-editable cells are light blue with red text; model-generated cells are green; historical realised data are grey. Inputs_A (pseudo-real-time) and Inputs_B (conditional; pre-filled with realised outturns) hold quarters 2023Q3-2029Q2, so the horizon can be extended by up to three years (Settings!forecast_end). Every input, unit, transformation and default is tabulated on the Variables sheet; Model_Inputs_A/B recomputes the transformed inputs live.

| Input (user unit) | Transformation into the model | If blank |
|---|---|---|
| Brent, US$/bbl (level) | 400 ln(P_t/P_(t-1)); CPI-energy growth via the bridge; grpe = gE - gw derived in the engine | carried forward |
| CPI energy, % q/q annualised (optional override) | gE = 100 ln(1+x/100) (= 400 dln); grpe = gE - gw | oil bridge |
| CPI food, % q/q annualised | gF = 100 ln(1+x/100); grpf = gF - gw | wage-linked (grpf = 0) |
| GSCPI, std devs | 2-quarter trailing mean | AR(1) |
| V/U (level) | none (wage equation lags 1-4) | carried forward |
| Productivity, % q/q annualised | 100 ln(1+x/100); 8-quarter trailing mean | trend held |
| Equation add-factors | added to the equation | 0 |

Entering Brent = 80 gives 400 ln(80/78.23) = 8.9, then 0.304 x that plus the constant; the number 80 never reaches an equation (tested). The history-to-forecast transition is explicit: the first forecast quarter's Brent growth uses the 2023Q2 average, the shortage mean uses the 2023Q2 GSCPI, the productivity trend uses the last eight historical growth rates.

`p5_forecast_engine.py` is standalone (numpy, pandas, openpyxl; no estimation code, no Macrobond). It reads the workbook and the coefficient CSV, never re-estimates, validates the coefficient file against the exact B* term set and homogeneity restrictions, simulates recursively from the 2023Q2 initial conditions, writes every default-rule use to an Engine_Log, and re-solves the system with A0^-1 as a check (difference 2e-15). Relative to the project's validated Phase 4 nominal-price simulator the paths agree to 1e-10. The Realised sheet is read only after the run, for errors.

## 3. The two exercises

**A: pseudo-real-time.** Only 2023Q2 information: oil flat at $78.2, V/U flat at 1.60, GSCPI mean-reverting, productivity trend held, food with wages, no add-factors.
**B: conditional.** Realised CPI energy, CPI food, GSCPI, V/U and productivity; wages and the four endogenous variables simulated; same 2023Q2 coefficients. (Realised V/U 2025Q4 is the flagged bridge.)

Realised and forecast paths: `output/forecasts_and_errors.xlsx` (and `.csv`), engine outputs `output/forecast_A.*`, `forecast_B.*`; charts in `output/charts/`.

| Quarter | Real q/q | A | B | AR(4) | Real y/y | A | B | AR(4) |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 2023Q3 | 4.27 | 4.27 | 6.06 | 2.86 | 3.69 | 3.69 | 4.15 | 3.32 |
| 2023Q4 | 1.90 | 3.96 | 2.01 | 2.87 | 3.32 | 3.85 | 3.81 | 3.20 |
| 2024Q1 | 4.64 | 3.77 | 3.92 | 2.69 | 3.49 | 3.79 | 3.79 | 2.87 |
| 2024Q2 | 0.89 | 3.69 | 1.45 | 2.68 | 2.97 | 4.00 | 3.42 | 2.82 |
| 2024Q3 | 2.15 | 3.72 | 1.69 | 2.67 | 2.43 | 3.86 | 2.30 | 2.76 |
| 2024Q4 | 3.63 | 3.72 | 3.57 | 2.63 | 2.87 | 3.79 | 2.69 | 2.70 |
| 2025Q1 | 2.74 | 3.70 | 2.25 | 2.63 | 2.38 | 3.78 | 2.27 | 2.69 |
| 2025Q2 | 2.06 | 3.72 | 2.14 | 2.62 | 2.68 | 3.78 | 2.44 | 2.67 |
| 2025Q3 | 3.48 | 3.76 | 3.01 | 2.62 | 3.02 | 3.79 | 2.78 | 2.66 |
| 2025Q4 | 2.20 | 3.77 | 3.07 | 2.62 | 2.65 | 3.81 | 2.65 | 2.66 |
| 2026Q1 | 5.20 | 3.80 | 5.94 | 2.62 | 3.29 | 3.83 | 3.61 | 2.65 |
| 2026Q2 | 2.75 | 3.84 | 3.50 | 2.62 | 3.46 | 3.86 | 3.96 | 2.65 |

## 4. Performance

Error = forecast - realised, pp. With one origin there is one forecast per horizon, so "4, 8, 12 quarters" is reported as statistics over the first h forecast quarters, plus the single y/y error exactly at h.

| CPI inflation, first h quarters | h | A ME / MAE / RMSE | B ME / MAE / RMSE | AR(4) ME / MAE / RMSE | AR(1) RMSE |
|:--|--:|:--|:--|:--|--:|
| q/q annualised | 4 | 1.00 / 1.43 / 1.79 | 0.44 / 0.79 / 1.01 | -0.15 / 1.53 / 1.57 | 1.59 |
| | 8 | 1.03 / 1.25 / 1.54 | 0.10 / 0.53 / 0.75 | -0.08 / 1.04 / 1.20 | 1.21 |
| | 12 | 0.82 / 1.20 / 1.43 | 0.23 / 0.59 / 0.74 | -0.32 / 1.02 / 1.26 | 1.27 |
| y/y | 4 | 0.47 / 0.47 / 0.60 | 0.43 / 0.43 / 0.43 | -0.31 / 0.31 / 0.37 | 0.47 |
| | 8 | 0.84 / 0.84 / 0.97 | 0.13 / 0.30 / 0.33 | -0.10 / 0.26 / 0.31 | 0.36 |
| | 12 | 0.80 / 0.80 / 0.91 | 0.14 / 0.29 / 0.33 | -0.21 / 0.32 / 0.41 | 0.43 |

Single y/y errors: at h = 4 (2024Q2) A +1.03, B +0.45, AR(4) -0.15; at h = 8 (2025Q2) A +1.10, B -0.24, AR(4) -0.01; at h = 12 (2026Q2) A +0.40, B +0.49, AR(4) -0.81. Full set: `output/metrics_windows.csv`, `errors_at_h4_h8_h12.csv`.

**Reading.**
- *Exercise A is not competitive with the AR benchmarks.* It over-predicts inflation by about 1 pp a year throughout (3.7-3.9% against 2.4-3.5% realised y/y); its y/y RMSE is two to three times that of AR(4) and its q/q RMSE 13-14% larger. The model's quarter-to-quarter noise is unforecastable (q/q RMSE of 1.2-1.8 pp for every method that does not know the realised drivers), so the difference lies in the level.
- *Exercise B is clearly better than the benchmarks in q/q terms* (RMSE 0.74 against 1.26 at 12 quarters) and modestly better in y/y beyond four quarters (0.33 against 0.41 at 12; worse than AR(4) at 4 and 8). It tracks the timing of the 2024Q2 dip, the 2026Q1 jump and the 2025 energy swings. A small positive bias (0.1-0.4 pp) remains.
- With 12 overlapping, serially correlated errors from one origin, no formal test is credible; read the ratios as descriptive.

## 5. Where the errors come from

The model is linear in its inputs and equation shocks, so the Exercise A error splits exactly into (A - B), the effect of wrong external assumptions, and (B - realised), the effect of the estimated relationships given the true drivers. The first is divided across the five drivers by a Shapley decomposition (all 32 coalitions of drivers switched between their A and B paths); the second across the four equations by feeding each equation's realised one-step residual into Exercise B (feeding all four reproduces the realised path to 7e-14, which is why the split is exact). Chart: `output/charts/fig4_error_A_decomposition.png`; table `output/error_decomposition_A.csv`. Mean contributions to the A error (pp, annualised):

| First h quarters | Total A error | **Assumptions (A-B)** | energy | food | GSCPI | V/U | productivity | **Relationships (B-real.)** | wage eq. | CPI eq. | 10y eq. | 1y eq. |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 4 | 1.00 | 0.56 | 0.06 | 0.21 | -0.13 | 0.22 | 0.20 | 0.44 | -0.15 | 0.64 | -0.04 | -0.01 |
| 8 | 1.03 | 0.93 | 0.16 | 0.22 | -0.14 | 0.42 | 0.27 | 0.10 | -0.06 | 0.29 | -0.09 | -0.03 |
| 12 | 0.82 | 0.59 | -0.29 | 0.22 | -0.18 | 0.56 | 0.27 | 0.23 | 0.02 | 0.38 | -0.13 | -0.04 |

1. **External assumptions dominate the persistent over-prediction.** Holding V/U at 1.60 while it fell to about 1.0 is the largest steady contributor (0.56 pp by 12 quarters, rising through the horizon); trend productivity held (0.27) and food rising with wages (0.22) add upward bias; GSCPI mean reversion is slightly too high (-0.18, i.e. offsetting). Oil explains little on average (-0.29 to +0.16) but a great deal quarter by quarter (-2.0 to +1.6 pp in single quarters, -3.4 in 2026Q1 when Brent jumped).
2. **The estimated relationships contribute less and mostly in the CPI equation.** Its realised residuals were negative in 8 of 12 quarters (inflation lower than the equation implies; -2.7 standard deviations in 2023Q3), contributing +0.4 pp on average. The wage and expectations equations are within one to two standard deviations (`output/forecasts_and_errors.xlsx`, sheet Equation_residual_z). There is no sign of a large structural break after 2023Q2 in the four equations, consistent with Phase 4c.
3. **Parameter staleness is minor.** Using the 2026Q2 coefficients (which have seen the outturns) improves B's 12-quarter RMSE only from 0.74 to 0.68 and leaves A at 1.42 against 1.43.
4. **The oil bridge is a weak link.** Replacing realised CPI energy in B by realised Brent through the bridge raises the 12-quarter RMSE from 0.74 to 1.45 (y/y 0.33 to 0.51): knowing the oil price does not pin down US CPI energy (bridge R2 0.62).
5. **Robustness.** Closure with realised relative prices (the authors') gives the same RMSE as the nominal closure (0.74); the as-of 2023-09-15 data vintage gives A 1.45 and B 0.74. Variants: `output/variants_metrics.csv`.

## 6. Limitations

- One origin and 12 quarters: precision is low, rankings can change with the origin (Phase 4's rolling-origin backtest found the structural model no better than AR(4) when its drivers must be assumed, which this exercise confirms).
- Pseudo-real-time on revised data; no true 2023 forecasts for oil, labour market or GSCPI were available, and the defaults (flat oil, flat V/U) are mechanical rather than forecasts a practitioner would have made. Exercise A therefore measures the model with naive drivers, not the best achievable real-time forecast.
- Exercise B is not a forecast: it uses ex-post information, includes the flagged 2025Q4 V/U bridge, and still simulates wages and expectations.
- Reduced form with exogenous oil, food, labour market and supply chains: no feedback from US inflation to those drivers, no forecast uncertainty bands, equation residuals set to zero in the forecasts.
- Add-factors and the oil-bridge pass-through let users impose judgment but are not estimated.

## 7. Reproduction

`python phase5/run_phase5.py` rebuilds everything from the stored data (about a minute; Excel is used only to store formula values). `python phase5/p5_forecast_engine.py --workbook phase5/Phase5_Assumptions.xlsx --scenario A --with-realised` runs an exercise from the workbook alone. Tests: `tests/test_phase5.py` (26 tests: no post-2023Q2 information in estimation or Exercise A, matrix-form solution, equality with the Phase 4 simulator, unit transformations, Excel-versus-Python agreement, decomposition additivity).
