# Phase 3 report: the Blanchard-Bernanke model extended through 2026Q2

Date: 2026-10-17. Data: fresh Macrobond pull `pull_20261017T112636Z` (retrieved 2026-10-17 11:26 UTC, SHA-256 checked).
Specification: the authors' four equations and restrictions, price equation with the 2-quarter GSCPI mean
(`gscpi_ma2`, the operational baseline); `gscpi5` kept as robustness. Phase 1-2 outputs are untouched.
Run everything: `.venv\Scripts\python.exe scripts\run_phase3.py`. Full test suite: 80 tests pass.
Detailed tables and charts are in `outputs/phase3/`; data documentation in `docs/phase3_data_dictionary.md`.

## 1. Answers

1. **Drivers since the 2023 paper: essentially unchanged.** Re-estimating through 2026Q2 (Model B) moves every sum of
   coefficients by at most 0.33 HAC standard errors of the 2023Q2 estimate (Model A; at most 0.19 in the price equation): price-equation wage pass-through
   0.853 → 0.845, lagged inflation 0.147 → 0.155, energy 0.077 → 0.075, food 0.190 → 0.179, supply chains 0.300 → 0.288,
   wage-equation V/U 0.708 → 0.689. The 2021-23 decomposition conclusion survives: energy and supply-chain pressures
   dominated, food and the COVID wage dummies mattered, labour-market tightness was a smaller but growing contributor.
   Since mid-2023 the decomposition attributes little to any driver (V/U about zero), and the model over-predicts inflation
   by 0.7 pp on average.
2. **Persistence: no evidence of greater structural persistence.** Own-lag weights are unchanged (price equation 0.15,
   wage equation 0.53, cf10 0.97). Reduced-form AR(4) persistence of CPI inflation is higher than before COVID (sum 0.11 over
   1990-2019, 0.37 to 2023Q2) but does not rise further to 2026Q2 (0.36). Long-term expectations stand about 0.45 pp
   above their 2015-19 mean (2.29 vs 1.83) but their equation's weights have not shifted (inflation weight 0.025 → 0.028,
   s.e. 0.009).
3. **Wage-price transmission: unchanged in the full-sample estimates, but the post-2020 period looks more wage-driven.**
   The sum of wage coefficients in the price equation is 0.85 in A and B. A break test finds a shift after 2020Q4
   (bootstrap p < 0.005; pass-through 0.80 before 2021, 0.93 after, lagged inflation 0.20 → 0.07, only 22 post-break
   observations). The 2023Q3-2026Q2 data pull this back from the 2023Q2 estimate (1.11 on 10 post-2020 observations to
   0.93), so the extension weakened rather than strengthened the shift; the frozen 2023Q2 equations pass a predictive-failure
   test on 2023Q3-2026Q2 (Chow p = 0.37). Recent-weighted models (C10: 1.00, C15: 0.96) suggest stronger transmission, but
   only by removing inflation persistence (lagged-inflation sum -0.001 for C10): a result the plausibility rules reject.
4. **Supply-chain, energy and food shocks: no sign of larger effects; weak evidence that energy is less inflationary.**
   Estimated sums are stable (§4). Impulse responses are almost identical across A, B, C15: a +1 s.d. one-off energy
   price-level shock raises annualised CPI inflation by 2.2 pp in the shock quarter and about 2.7 pp cumulatively over
   8 quarters; food 0.4 / 0.8 pp; a temporary GSCPI shock 0.2 / 0.6 pp. In 2026H1 the model attributes 1.9 pp of inflation
   to the energy spike but actual inflation came in 1.15-1.30 pp lower than the model implies; regressing Model A's price
   residuals on energy growth over 2023Q3-2026Q2 gives a slope of -0.023 (HAC t = -1.9, 12 observations, dominated by
   2026Q1) against a contemporaneous energy coefficient of 0.092, i.e. roughly a quarter less pass-through. This is
   suggestive, not established.
5. **Most credible specification for 1-3 year conditional forecasts: Model B, the unweighted re-estimate through 2026Q2
   (`gscpi_ma2`), with Model A as an essentially equivalent fallback.** Recent weighting does not improve pseudo-out-of-sample
   forecasts and, for short half-lives, breaks plausibility (§3-§4). Frozen A forecasts as well as re-estimated B after
   2023Q2. Caveat that must travel with any forecast: the unconditional performance is poor (§5).

## 2. Data and QA

* **Fresh pull, nothing from the old cache.** Retrieved 2026-10-17 11:26 UTC; compared with the earlier pull (2026-10-16):
  0 revised observations, same last observations. Series, codes, aggregation rules, observation dates and retrieval
  timestamps: `docs/phase3_data_dictionary.md`. Quarterly rules are the authors' (CPI and Cleveland expectations: last month
  of quarter; V/U: ratio of quarterly means; GSCPI: quarterly mean).
* **Last complete quarter: 2026Q2.** 2026Q3 is partial (CPI, CPI energy, CPI food, Cleveland expectations and GSCPI
  observed; productivity, ECI and V/U not yet published) and is excluded; it is listed, not substituted.
* **A real hole in the data: V/U for 2025Q4 is undefined.** October 2025 CPI and the October 2025 unemployment level
  were never published. CPI uses the December value, so inflation is unaffected; V/U (ratio of quarterly means) needs all
  three months. Baseline estimation leaves it missing, so the wage equation (four V/U lags) loses 2026Q1-Q2 (N = 144
  against 146). For simulations, fitted values and decompositions only, 2025Q4 is bridged with the Nov-Dec ratio of means
  (0.8765), flagged in code. A sensitivity that estimates with the bridged value (V/U sum 0.672 vs 0.689) does not change conclusions.
* **ECI.** Baseline: the authors' splice through 2000Q4. Sensitivity (Macrobond's own ECI for the whole sample), Models A / B:
  wage pass-through 0.55 / 0.54 instead of 0.85 / 0.85, lagged inflation 0.45 / 0.46, V/U sum 0.71 / 0.71. The A-to-B
  stability finding holds under either history; the level of pass-through depends on the pre-2001 series (as in the validation report).
* Outliers since 2023Q3 (`outputs/phase3/data_qa_ranges.csv`): relative energy prices rose 35% annualised in 2026Q1, the largest energy
  move since 2022 but within the 1990-2019 range (z = 1.5); V/U (0.95-1.47) and GSCPI (peak 1.6 in 2026Q2) sit well above their pre-2020
  distributions (z = 3.4 and 4.7). No data errors were found.

## 3. Models and the recent-weighting decision

* **A** frozen at estimates through 2023Q2 (current-vintage data), applied to later realised data. **B** re-estimated through
  2026Q2, unweighted. **C5 / C10 / C15** the same with weights 0.5^(age/H), H = 5, 10, 15 years (effective sample 57, 98, 119 of
  146 observations). Wage-equation COVID dummies enter once the dummy quarters are in the estimation sample.
* **Selection rule (set before looking at results, uses forecast errors only):** at each of 86 origins (2004Q4-2026Q1) re-estimate
  on information to that origin and forecast 1-12 quarters; choose the half-life with the lowest mean CPI-inflation RMSE over four
  horizon groups; it must beat the unweighted model by more than 3%, otherwise keep unweighted.
* **Result: unweighted wins.** Mean conditional RMSE (pp): unweighted 1.26; half-life 15y 1.30; 10y 1.32; 5y 1.39. Weighting
  only the price equation does no better (15y 1.30, 10y 1.32, 5y 1.38). No candidate is better, let alone 3% better. The
  weighted models fit the recent past better in-sample (dynamic baseline RMSE 0.69 for C5 vs 1.20 for B) and forecast it worse:
  the in-sample/out-of-sample reversal the selection rule is meant to guard against. Weighting does not help in any of the three target periods (before 2020 it ties with the unweighted model at 2-4 quarters; during 2020-23
  and after 2023 the unweighted model is better; `fig_p3_oos.png`). Model C is therefore reported (C15, the best weighted candidate, in the
  charts) but not recommended.

## 4. Coefficients: stability and plausibility

Sums of coefficients (HAC s.e. for A in parentheses); full tables with p-values in `outputs/phase3/models_coef_summary.csv`:

| | A | B | C5 | C10 | C15 | A5 | B5 |
|---|---|---|---|---|---|---|---|
| Price: wage pass-through | 0.853 (0.16) | 0.845 | 0.991 | 1.001 | 0.956 | 0.851 | 0.833 |
| Price: lagged inflation | 0.147 (0.16) | 0.155 | 0.009 | -0.001 | 0.044 | 0.149 | 0.167 |
| Price: energy | 0.077 (0.018) | 0.075 | 0.090 | 0.089 | 0.085 | 0.078 | 0.076 |
| Price: food | 0.190 (0.059) | 0.179 | 0.230 | 0.227 | 0.211 | 0.202 | 0.197 |
| Price: supply chains | 0.300 (0.116) | 0.288 | 0.183 | 0.228 | 0.248 | 0.265 | 0.232 |
| Price: productivity | -0.144 (0.071) | -0.133 | -0.096 | -0.130 | -0.133 | -0.154 | -0.143 |
| Wage: V/U | 0.708 (0.23) | 0.689 | 0.637 | 0.696 | 0.695 | 0.708 | 0.689 |
| Wage: own lags | 0.533 (0.15) | 0.534 | 0.463 | 0.475 | 0.493 | 0.533 | 0.534 |
| Wage: catch-up | -0.015 (0.05) | -0.003 | 0.017 | 0.000 | -0.003 | -0.015 | -0.003 |
| cf1: weight on inflation | 0.136 (0.03) | 0.136 | 0.133 | 0.136 | 0.136 | 0.136 | 0.136 |
| cf10: weight on inflation | 0.025 (0.009) | 0.028 | 0.033 | 0.030 | 0.029 | 0.025 | 0.028 |

* **A vs B:** the largest change is 0.33 HAC standard errors (the cf10 weights); no instability flag trips.
* **Plausibility rules** (signs and ranges; `models_flags.csv`): all of A, B, A5, B5, C15 pass. C10 fails (lagged inflation
  -0.001, wage pass-through 1.001); C5 sits at the boundary (0.009 / 0.991). Short half-lives are drifting to the same
  implausible corner found in the validation report for short samples: the price equation cannot identify inflation persistence
  on recent data alone.
* **Stability tests on the extended sample (Model B):** the wage and cf10 equations show no break (sup-F p = 0.25-0.37 and 0.98;
  CUSUM p = 0.22 and 0.049). In the price equation the wage pass-through block (break after 2020Q4) and the energy-and-food
  block (after 2020Q2) are unstable (p < 0.005), the supply-chain block is not (p = 0.23). cf1 shows instability (sup-F break
  after 2008Q1, p < 0.005; CUSUM p = 0.017). Against that, the frozen 2023Q2 equations are not rejected on 2023Q3-2026Q2
  (Chow predictive failure p = 0.80 wage, 0.37 price, 0.67 cf1, 0.80 cf10): the instabilities are a 2020-23 episode that has
  not recurred or grown. About 12 tests are run; one or two marginal rejections would occur by chance.
* **gscpi5 vs gscpi_ma2:** conclusions are the same; the five-lag form has larger standard errors and a sign-alternating
  lag pattern as before (`docs/validation_report.md`).

## 5. Forecast evaluation (pseudo-out-of-sample, 2004Q4-2026Q1 origins, horizons 1-12)

CPI inflation RMSE (pp), all targets; conditional = realised exogenous drivers, unconditional = drivers forecast at the origin
(relative energy and food growth zero, V/U and productivity held, GSCPI mean-reverting via AR(1)):

| Horizon | Conditional, B | Conditional, C15 | Unconditional, B | Unconditional, AR(4) |
|---|---|---|---|---|
| h1 | 1.19 | 1.22 | 2.93 | 3.09 |
| h2-4 | 1.26 | 1.32 | 3.10 | 3.09 |
| h5-8 | 1.31 | 1.35 | 3.18 | 2.99 |
| h9-12 | 1.28 | 1.30 | 3.13 | 3.04 |

* **Conditional and unconditional are different quantities and must not be mixed.** The structural model reproduces inflation well
  (RMSE 1.2-1.3) when told what energy, food, supply chains, V/U and productivity do, and no better than an AR(4) when it must
  forecast those drivers (3.1 vs 3.0-3.1; the AR(4) is better at 5-8 quarters).
* By target period (conditional, h2-4, model B): targets to 2019Q4 0.92; 2020Q1-2023Q2 2.32; 2023Q3-2026Q2 0.88.
* **Bias:** conditional forecasts are close to unbiased overall (-0.04 to -0.10) but overshoot after 2023 (0.3 pp at 2-4
  quarters, 0.8 at 9-12), consistent with the negative residuals in the 2023Q3-2026Q2 decomposition.
* **Frozen A vs re-estimated B on origins from 2023Q2 (conditional, h1/h2-4/h5-8/h9-12):** A 0.80 / 0.69 / 0.76 / 0.89, B
  0.80 / 0.68 / 0.77 / 0.93, C15 0.83 / 0.69 / 0.78 / 0.92. Re-estimating has added nothing measurable. Unconditionally post-2023 the
  AR(4) is at least as good as any structural variant (1.36 / 1.24 / 1.14 / 1.45 against 1.33 / 1.43 / 1.28 / 1.32 for A).
* Other equations (conditional, h2-4): wage growth RMSE 0.77, one-year expectations 0.57, ten-year expectations 0.25.

## 6. Historical analysis through 2026

* **Fit** (`fig_p3_fit.png`, extended Figs. 3, 7, 8, 9): one-step CPI RMSE is 0.79 for Model A out-of-sample on 2023Q3-2026Q2
  (B 0.71, in-sample); 2020Q1-2023Q2 1.16 / 1.19.
* **Decomposition of CPI inflation** (pp, annualised averages; `fig_p3_decomp_price.png`, extended Fig. 12; `fig_p3_decomp_wage.png`,
  Fig. 13). Residual = actual minus model baseline:

| 2021Q1-2023Q2 | A | B | C15 | Authors 2023 (Google, 2021-22 avg) |
|---|---|---|---|---|
| Supply chains | 0.92 | 0.90 | 0.71 | 1.23 |
| Energy | 0.76 | 0.74 | 0.75 | 1.30 |
| Food | 0.50 | 0.48 | 0.49 | 0.46 |
| Labour market (V/U) | 0.39 | 0.42 | 0.58 | 0.27 |
| Productivity | 0.08 | 0.08 | 0.05 | -0.01 (A 2021-22: 0.03) |
| COVID dummies | 0.49 | 0.48 | 0.49 | - |
| Initial conditions | 2.78 | 2.73 | 2.74 | 2.61 |
| Residual | 0.03 | 0.12 | 0.12 | - |
| Actual | 5.94 | 5.94 | 5.94 | 6.60 |

  Note the last column averages 2021-22 only, so compare it with Model A's 2021-22 averages (supply chains 1.04, energy 1.20,
  food 0.52, V/U 0.32): same ranking. **The 2021-23 conclusions do not change under B or C**; C15 raises the V/U share (0.58 vs 0.39)
  because it puts more weight on wage pass-through. For 2023Q3-2026Q2 all contributions are small (supply chains 0.2, energy 0.2, V/U
  -0.09 to 0.01) and the model baseline exceeds actual inflation by 0.5-0.7 pp. In 2026Q1-Q2, energy contributes 1.8-1.9 pp,
  V/U -0.3 to -0.4, and the residual is -1.15 to -1.30 pp (see Answer 4).
* The decomposition baselines contain no residuals, so the stacked bars sum to the model baseline, not to actual inflation; the residual is
  shown hatched.

## 7. Impulse responses (CPI inflation, pp; 90% HAC Monte-Carlo interval; `fig_p3_irfs_exogenous.png`, `fig_p3_irfs_residual.png`)

Shock sizes are +1 s.d. of the series over 2020Q1-2026Q2 (energy growth 23.7, food 3.2, V/U 0.44, GSCPI 1.50), equal for all models.
Temporary = the series moves for one quarter; persistent = decaying with rho 0.8; permanent = the new level is kept. For energy and food
growth rates a one-quarter shock is a one-off rise in the relative price **level**.

| Shock | Statistic | A | B | C15 |
|---|---|---|---|---|
| V/U permanent | level at h27 | 1.12 [0.69, 1.55] | 1.14 [0.77, 1.47] | 1.10 [0.81, 1.39] |
| | cumulative 0-12 | 8.8 [6.5, 11.0] | 9.1 [6.8, 11.2] | 9.6 [7.4, 11.7] |
| V/U temporary | peak (quarter 1) | 0.91 | 0.94 | 1.13 |
| | cumulative 0-8 | 0.77 [0.47, 1.01] | 0.78 [0.53, 1.01] | 0.82 [0.54, 1.14] |
| Energy one-off (level) | peak (h0) | 2.19 [1.99, 2.36] | 2.17 [1.99, 2.35] | 2.20 [2.01, 2.39] |
| | cumulative 0-8 | 2.66 [1.95, 3.32] | 2.65 [1.96, 3.29] | 2.72 [1.92, 3.46] |
| Energy persistent | cumulative 0-8 | 10.8 [8.5, 13.0] | 10.7 [8.3, 12.9] | 10.9 [8.2, 13.4] |
| Food one-off (level) | peak / cum 0-8 | 0.39 / 0.79 [0.39, 1.22] | 0.40 / 0.77 [0.33, 1.23] | 0.50 / 0.82 [0.41, 1.28] |
| GSCPI temporary | peak (h0) | 0.22 [0.08, 0.38] | 0.22 [0.08, 0.36] | 0.19 [0.06, 0.33] |
| | cumulative 0-8 | 0.62 [0.24, 1.05] | 0.61 [0.23, 1.00] | 0.48 [0.17, 0.82] |
| GSCPI persistent | cumulative 0-12; half-life from peak | 2.96 [1.13, 5.02]; 8 q | 2.89 [1.11, 4.79]; 8 q | 2.29 [0.81, 3.93]; 7 q |
| GSCPI permanent | level at h27 | 0.88 | 0.89 | 0.70 |
| cf1 shock (+0.28) | cumulative 0-8; half-life | 0.32 [0.16, 0.45]; 8 q | 0.31 [0.16, 0.46]; 9 q | 0.35 [0.20, 0.50]; 5 q |
| cf10 shock (+0.18) | level at h27 (permanent) | 0.13 [0.11, 0.16] | 0.12 [0.10, 0.14] | 0.12 [0.10, 0.14] |
| Wage shock (+0.54) | cumulative 0-8; peak | 1.17 [0.89, 1.57]; 0.23 | 1.18 [0.91, 1.58]; 0.23 | 1.21 [0.91, 1.64]; 0.26 |
| Price shock (+0.99) | cumulative 0-8; half-life | 1.41 [1.08, 1.88]; 1 q | 1.43 [1.10, 1.92]; 1 q | 1.31 [1.00, 1.75]; 1 q |

* **Peak magnitude, timing and persistence are the same under A, B and C15 within the intervals.** Price-level shocks (energy, food, GSCPI,
  price residual) peak on impact and have a half-life of one to two quarters unless the shock itself is persistent. Labour-market tightness and
  expectations are the persistent channels: a permanent V/U increase builds slowly (no peak, still rising at 27 quarters); a ten-year expectations
  shock never dies out (the equation is a near unit root by construction).
* **Temporary vs permanent matters more than the model:** a temporary V/U rise lifts inflation by about 0.8 pp cumulatively over 8 quarters; a permanent
  one by about 5.6-6.4 pp.
* Intervals: independent draws for each equation from the HAC covariance (restriction-consistent); cross-equation covariance is not included.
  The Phase-2 validation compared these with a block bootstrap and found them very close.

## 8. Weaknesses and open points

* Unconditional forecasts are no better than a simple autoregression; the structural model's value is conditional (scenario) analysis, as the
  authors intended. Phase 4 scenario work must carry that distinction.
* The 2026 energy spike (the largest since 2022) is a single large observation; the weaker-pass-through reading rests on 2026Q1 and 12 residuals.
* The price equation has unstable energy/food and pass-through blocks in-sample (2020-23). Frozen coefficients nonetheless forecast 2023Q3-2026Q2 acceptably.
* The V/U gap in 2025Q4 forced the wage equation to end in 2025Q4; the bridged value is a flagged assumption.
* The GSCPI substitute is revised by the NY Fed; stamped pulls make each result reproducible but results will move with later vintages.
* Not done (as instructed): Phase 4 scenario interface; Appendix variants (PCE, SPF); GSCPI sample starting 1998; cross-equation covariance in the intervals.
