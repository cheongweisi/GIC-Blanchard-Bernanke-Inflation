# Phase 5: review of Model B* before building the forecasting framework

Written before implementation, as requested. For each obstacle: what it is, and the conservative default adopted (all defaults are user-editable in the workbook and logged by the engine). Nothing in this list needed a change to the Model B* specification.

## 1. What Model B* needs in order to forecast

Four equations, solved within each quarter in the order wage -> CPI -> catch-up term -> long-run expectations -> short-run expectations (the structural matrix A0 is lower triangular, so this is its exact solution). Initial conditions: the last four quarters of gw, gcpi, cf1, cf10, the catch-up term, grpe and grpf, plus lags of V/U and the shortage term.

Exogenous inputs required in every forecast quarter:

| Input in the equations | Where used | What the user supplies | Category |
|---|---|---|---|
| grpe (relative energy price growth) lags 0-4 | CPI eq. | Brent US$/bbl, or CPI-energy % change | user assumption |
| grpf (relative food price growth) lags 0-4 | CPI eq. | CPI-food % change | user assumption |
| shortagema2 (GSCPI 2-quarter mean), lag 0 | CPI eq. | GSCPI level | user assumption |
| vu (V/U) lags 1-4 | wage eq. | V/U level | user assumption |
| magpty (8-quarter trend productivity growth), lag 1 in wage eq., lag 0 in CPI eq. | both | productivity % change | user assumption |
| D2020Q2, D2020Q3 | wage eq. | nothing (fixed at 0) | model constant |
| catch-up term, gw, gcpi, cf1, cf10 | all | nothing | model-generated |

## 2. Obstacles and the default adopted

| # | Obstacle | Why it matters | Default adopted |
|---|---|---|---|
| 1 | **No future exogenous values exist.** All five drivers must be assumed. | The forecast is only as good as these paths; this is where most of the error will be (confirmed in the results). | Documented rules, applied only where the user leaves a cell blank: oil flat at the 2023Q2 average; V/U flat; GSCPI AR(1) estimated to 2023Q2; productivity trend held; food rises with wages (relative food price unchanged, the authors' neutral convention). Every use of a rule is written to the engine's log. |
| 2 | **Relative prices are not independent inputs.** grpe = gE - gw and grpf = gF - gw contain wage growth, which the model itself generates. Entering relative prices would silently let nominal energy and food prices move one-for-one with simulated US wages. | Wrong transmission in any scenario that moves wages. | Users enter nominal energy and food assumptions; the engine derives the relative prices every quarter after solving the wage equation (the Phase 4 closure). The authors' closure (realised relative prices) is run as a diagnostic: it changes the 12-quarter RMSE by 0.00-0.01 pp. |
| 3 | **Oil is not a regressor.** The equations use CPI energy relative to wages. A Brent assumption needs a link to CPI energy. | "Brent = $80" must not enter an equation that expects a growth rate. | A small auxiliary bridge, estimated on 1990Q2-2023Q2 only: CPI-energy growth = const + 0.304 x Brent growth (R2 0.62). It is not part of Model B*. Users can bypass it by entering CPI-energy growth directly. |
| 4 | **Transformations.** The model uses 400 x dln (annualised log changes), 2-quarter and 8-quarter trailing means, and a catch-up term built from lags. | Feeding levels or percentages into these slots would give nonsense. | The engine converts everything (formulas on the Variables sheet; Excel sheet Model_Inputs_A/B shows the result live; a test confirms the Excel formulas and the Python engine agree to 1e-8). |
| 5 | **Data leakage: estimation.** | Coefficients must not see post-2023Q2 data. | Every equation is estimated on 1990Q1-2023Q2 with the authors' lag lengths (no selection or tuning). A test replaces all post-origin data with garbage and confirms identical coefficients. |
| 6 | **Data leakage: revisions (vintage).** The pinned data are current vintage (pulled October 2026). GSCPI, JOLTS, productivity and the CPI seasonal factors have been revised since 2023. | A true real-time exercise would use 2023 vintages. | Headline = current-vintage data truncated at 2023Q2, so history and outturns are on one consistent basis (the Phase 3/4 pseudo-out-of-sample convention). Sensitivity: the project's stored as-of 2023-09-15 vintage is used for coefficients, auxiliary models and initial conditions; the forecasts barely move (12-quarter RMSE 1.45 vs 1.43). |
| 7 | **Data leakage: initial conditions and transformations.** | Trailing means must not use future values; nothing after 2023Q2 may seed the lags. | History sheet ends 2023Q2; all means are trailing. A test poisons the Realised sheet and confirms Exercise A is unchanged. The Realised sheet is read only to compute errors after a run. |
| 8 | **Information set at the origin.** 2023Q2 ECI, productivity and JOLTS were published only in late July/early August 2023. Futures curves and survey forecasts of 2023 are not in the project. | "Pseudo-real-time" is stricter on some inputs and weaker on others than true real time. | Strict 2023Q2 cut-off on every series (partial 2023Q3 data, which a September 2023 forecaster would have had, are ignored). Oil is held flat rather than using a 2023 futures curve (not available). |
| 9 | **COVID dummies.** The 2020Q2 and 2020Q3 wage-equation dummies are in the specification. | Both quarters lie inside a sample ending 2023Q2, so the dummies are estimated; they must not appear in forecasts. | Kept in estimation (same rule as the project's production model); fixed at 0 in every forecast quarter; they cannot enter the lag window because the dummy has lag 0 only. |
| 10 | **Wage constant.** The estimated constant embeds the 1990-2023 average and the post-pandemic labour market. | Long-horizon level is sensitive to it (Phase 4b). | Estimated constant used (Phase 4 decision). A per-equation add-factor row lets a user shift any intercept. |
| 11 | **V/U 2025Q4 does not exist** (October 2025 unemployment was never published). | Affects realised V/U in Exercise B only. | Uses the flagged interpolation bridge (0.8951) from the Phase 3 supplement; flagged in the workbook. |
| 12 | **Single forecast origin.** | Horizon-specific forecast-error statistics have n = 1 per horizon. | 4-, 8- and 12-quarter results are reported both as statistics over the first 4/8/12 forecast quarters and as the single y/y error at exactly h = 4, 8, 12. No significance tests are attempted (n <= 12, serially correlated errors). |
| 13 | **Realised target is a revised, quarter-end series.** | Errors include revision noise in the target. | Stated; CPI is the quarter-end SA index as in the estimation. |

## 3. Verdict

No obstacle prevented a faithful implementation. The framework therefore keeps Model B*, its restrictions, lags, GSCPI two-quarter mean and COVID dummies unchanged, and re-estimates only the coefficients. The two additions are auxiliary and labelled: the quarterly oil-to-CPI-energy bridge, and the GSCPI AR(1) used when a user leaves GSCPI blank.
