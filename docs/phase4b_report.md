# Phase 4b: economic-validation review of the Phase 4 scenario framework

Date: 2026-10-18. Scope: the Phase 4 model (B\*, engine, bridge, baseline, scenarios) is **unchanged**; nothing was re-estimated or overwritten. Phase 1-4 files (423: outputs, docs, code, tests, data cache) are byte-identical to their state before this review (`outputs/phase4b/pre_phase4b_manifest.sha256`, checked by `tests/test_phase4b.py`).
New: `bb_inflation/phase4b/`, `scripts/run_p4b_{wage,forecast,baseline,bridge,uncertainty,figures}.py`, `outputs/phase4b/` (CSVs and `fig_p4b_*.png`), `tests/test_phase4b.py` (7 new tests; 116 pass in total). No new Macrobond pull was needed.

## 0. Findings

**No implementation error was found. Nothing needs a code or coefficient change before Phase 5. Four presentation corrections are needed (§6).** What the review did find, in order of importance:

1. **Uncertainty is understated, mostly by omission, not by error (§5).** The "90%" baseline fan covers only 61-73% of historical outturns (29-43% in 2020-23) because it holds the drivers fixed; real-time errors are 2-3 times the fan. The scenario bands are parameter-only (equations plus bridge coefficients). For oil scenarios at one year the spread across the agreed specification range (bridge elasticity 0.24-0.40, catch-up 0-0.25) is 1.2-1.5 times the Phase 4 band, and across a wider envelope (elasticity to 0.47, pass-through x0.8, other estimation samples) oil +30% spans 0.60-1.19 pp against an equation-only band of 0.26 pp.
2. **The post-2023 underperformance against AR(4) is a driver-assumption problem, not a structural one (§2).** For targets 2023Q3-26Q2 at 2 years, 60% of the squared error comes from holding V/U at its origin value, mean-reverting GSCPI by AR(1), and moving food with wages; 24% is the price-equation residual (prices softer than the equation). With realised drivers the model is close to AR(4).
3. **The oil effects are, if anything, understated, not overstated (§2, §4).** The realised response to oil moves has been 1.4-1.5 times the model's (s.e. 0.25-0.35), and the bridge elasticity is level-dependent (0.37 at today's oil price against 0.30 on average). The 20% pass-through haircut is the less-supported direction. Scenario deviations for oil are better read as a range of roughly 0.8x-1.3x the headline.
4. **Wage catch-up is a property of the data, not of the specification (§1).** Five catch-up definitions on four samples give -0.07 to +0.04, none significant. Imposing a catch-up of 0.10 (upper end of the data) or 0.25 (stress) leaves the one-year oil effect unchanged (0.75 to 0.77 pp) and adds 0.09-0.23% to the price level after three years.
5. **The baseline's rise to 3.1% is mostly the energy drag fading (§3).** Of the +0.59 pp from the 2027Q4 trough (2.54%) to 2029Q3 (3.13%): energy +0.41, estimated wage constant +0.22, food +0.08, supply chains -0.07. The 0.50 pp gap to the neutral-constant baseline is the model reading V/U 1.02 as tight (its inflation-neutral V/U is 0.59). The implied wage dynamics are within historical ranges.

## 1. Wage-price feedback and second-round effects

**What the model contains.** Wages = 0.54 own lags + 0.46 one-year expectations (restricted to sum to one) + V/U (sum 0.67) + catch-up (sum -0.002). Expectations respond to inflation weakly (one-year: 0.136 on current and lagged CPI inflation plus 0.54 on ten-year, which itself loads 0.028). The wage equation has no direct energy term. So an oil shock reaches wages only through expectations and catch-up.

**Is zero catch-up the data or the specification?** The data (`wage_catchup_evidence.csv`, `wage_postcovid_residual_test.csv`):

| Catch-up definition | 1990-2019 | 1990-2026 (B\*) | 2000-2026 |
|---|---|---|---|
| authors: 4 free lags of inflation minus lagged expectations | -0.024 (0.070) | -0.002 (0.048) | -0.042 (0.048) |
| single coefficient on their mean | -0.019 (0.070) | -0.018 (0.045) | -0.066 (0.043) |
| two-year surprise | -0.024 (0.053) | -0.010 (0.043) | -0.014 (0.045) |
| real-wage gap against productivity, 8 quarters (error-correction type) | +0.032 (0.043) | +0.015 (0.031) | -0.004 (0.029) |
| same, 12 quarters | +0.042 (0.053) | +0.025 (0.041) | +0.007 (0.037) |

HAC standard errors in brackets. The upper 95% bound in B\* is +0.09 (authors' definition) and +0.07 to +0.10 for the others; for 1990-2019 it is up to +0.15. The authors' own pre-COVID estimate is -0.024 (p = 0.77). The result does not depend on the form of the catch-up term. It also holds in the period most favourable to catch-up: the wage equation frozen at 2019Q4 shows no relation between its 2021Q1-26Q2 residuals and lagged inflation surprises (slope -0.016, s.e. 0.037). One window disagrees: the equation frozen at 2023Q2 gives a positive slope of 0.31 on 2023Q3-26Q2, but that is 12 overlapping quarters (about three independent four-quarter windows), and HAC standard errors are unreliable there. It is a watch item, not evidence.
The real wage did recover without estimated catch-up: ECI over CPI fell 2.8% from 2019Q4 to 2022Q2 and is back to its 2019Q4 level by 2026Q2 (still about 5% below the 2015-19 trend of 0.8% a year). The model attributes the recovery to V/U (1.5-2.0 in 2021-23) and expectations. The level was restored; the trend was not.

**Plausibility, from the literature (not from the data above).** The authors' own US estimate, replicated in Phase 1, is -0.024 (p = 0.77). The Belgian replication of the model, for an economy with automatic wage indexation, finds a large catch-up with weak pass-through of wages to prices ([NBB WP 447](https://www.nbb.be/doc/ts/publications/wp/wp447en.pdf); the 11-economy extension is [NBER w32532](https://www.nber.org/papers/w32532)); I read these from search summaries, not the full papers. Blanchard and Galí attribute the milder effect of the 2000s oil shocks partly to more flexible real wages and the absence of the generalised indexation of the 1970s ([Blanchard-Galí 2007](https://www.nber.org/system/files/chapters/c0517/c0517.pdf); [Blanchard-Riggi, NBER w15467](https://causalclaims.trfetzer.com/paper/w15467.html)). The pattern is institution-dependent: a positive catch-up is plausible in an economy with indexation or a de-anchored expectation regime, and not supported for post-1990 US data. I could not find a US series for the share of contracts with COLA clauses (only a Canadian one), so I do not quote a US coverage figure.

**Calibrated alternative (overlay; baseline coefficients untouched).** phi is the sum of the catch-up lags, spread equally over lags 1-4. It is also the share of a one-off price-level jump that is recovered in wages through the catch-up term alone. Wage constant re-centred so that fitted wage growth at the sample-average catch-up term is unchanged (tested). phi = 0.10 is the upper end of the B\* estimate and of the real-wage-gap estimates. phi = 0.25 is a judgemental stress, 2.5 times the upper end of the data; no US estimate supports it. (`wage_overlay_*.csv`, `fig_p4b_wage_catchup_overlay.png`)

| y/y deviation from baseline, pp (price level %), 1y / 3y | estimated | phi = 0.10 | phi = 0.25 |
|---|---|---|---|
| Oil +30% persistent | 0.75 / 0.06 (0.85) | 0.75 / 0.10 (0.94) | 0.77 / 0.15 (1.09) |
| Oil stays at $111 | 0.53 / 0.26 (1.20) | 0.53 / 0.31 (1.27) | 0.53 / 0.39 (1.40) |
| Adverse supply bundle | 0.98 / 0.23 (1.50) | 0.98 / 0.29 (1.62) | 1.00 / 0.38 (1.82) |
| V/U back to 1.19 | 0.07 / 0.19 (0.44) | 0.07 / 0.20 (0.46) | 0.07 / 0.22 (0.49) |
| Baseline y/y, 3y | 3.13 | 3.15 | 3.21 |

**Reading.** The Phase 4 conclusion that an oil shock is a first-round price-level event is robust to the catch-up coefficient: the one-year effect does not move, and even phi = 0.25 raises the three-year price-level effect of oil +30% by 0.23% (the wage level then ends 0.63% above baseline against 0.26%). The reason is arithmetic: oil +30% is a 7.8% rise in CPI energy times a 0.075 weight, about a 0.75% price-level jump, so a catch-up on it is small. Two limits remain. The estimated model has no error correction in real wages: a 1% price jump leaves real wages 1.0% lower three years later (0.8% at phi = 0.25), which is not what the 2022-26 recovery looks like. And the sample contains no episode with de-anchored expectations; the catch-up could be non-linear in that regime (the 2021-26 test above says no, but it is one episode). The catch-up overlay is a labelled sensitivity for Phase 5, not a recommendation to change the estimates.

## 2. Forecast performance (real-time-feasible baseline method, tier D, against AR(4))

**Method (`forecast.py`).** The model is linear, so the error of tier D (forecast minus actual, at each of 86 origins) splits exactly into: assumed versus realised drivers (oil path, V/U, productivity, GSCPI, food), the bridge error (realised oil through the bridge versus realised CPI energy), and structural error (the model's response to its own out-of-sample equation residuals, by equation). The split adds up to the error to 1e-8 at every origin and horizon; tier D reproduces the Phase 4 stored forecasts to 9e-16 (tested).

| y/y, mean error and share of squared error (target periods) | 2020Q1-23Q2, 2y | 2023Q3-26Q2, 1y | 2023Q3-26Q2, 2y | 2023Q3-26Q2, 3y |
|---|---|---|---|---|
| RMSE tier D / AR(4), pp | 3.93 / 3.47 | 1.13 / 0.45 | 1.99 / 0.56 | 2.35 / 0.65 |
| mean error tier D / AR(4) | -2.33 / -2.17 | +0.75 / -0.20 | +1.65 / -0.30 | +0.99 / -0.45 |
| of which: oil path (flat vs realised) | -0.25 | +0.05 | +0.11 | +0.08 |
| V/U held vs realised | -0.18 | +0.12 | +0.34 | +0.14 |
| GSCPI AR(1) vs realised | -0.70 | +0.05 | +0.42 | +0.42 |
| food moves with wages vs realised | -0.61 | +0.17 | +0.19 | +0.05 |
| productivity held | -0.07 | +0.08 | +0.09 | -0.10 |
| bridge | -0.39 | -0.07 | -0.06 | -0.08 |
| price-equation residuals | +0.26 | +0.32 | +0.48 | +0.48 |
| wage-equation residuals | -0.48 | +0.02 | +0.09 | +0.01 |
| share of squared error from driver assumptions | 0.44 + 0.22 oil | 0.43 + 0.10 oil | 0.60 + 0.08 oil | 0.95 + 0.09 oil |
| expectations residuals | +0.08 | 0.00 | -0.01 | 0.00 |
| RMSE of D without the V/U, GSCPI, food and productivity assumption errors | 2.5 | 0.68 | 1.00 | 0.73 |

(`forecast_error_summary_yoy.csv`, `forecast_error_components.csv`, `fig_p4b_forecast_error_decomposition.png`.)

* **Why it loses to AR(4) recently.** From the 2021Q4-2022Q4 origins the model was run with V/U held at 1.7-1.9 (1990-2019 mean 0.58), GSCPI starting at 4.3 (2021Q4) and decaying slowly (AR(1), rho 0.855), and food following wages. The drivers then moved faster than the assumptions, in the opposite direction (inflation rising before 2022, falling after). AR(4) has no drivers and so no assumed-driver error; in a calm period (2023Q3-26Q2) it is hard to beat. With realised drivers, the tier-C RMSE (0.64 / 0.93 / 0.60 for 1/2/3 years) is within 0.4 pp of AR(4) (0.45 / 0.56 / 0.65). The price-equation residual is the next largest term: mean +0.3 to +0.5, consistent with the Phase 3 supplement (prices softer than the equation since 2023Q3).
* **Before 2020 the model was not worse than AR(4)** (1.49 against 1.63 at one year). In 2020-23 neither could forecast (3.2-3.9 against 3.3-3.5).
* **Implementation is not the cause.** The bridge contributes -0.4 to +0.1 pp of mean error; the structural wage and expectations equations contribute under 0.1 pp after 2023.
* **Charts.** `fig_p4b_forecast_vs_actual_2020_23.png` (origins 2019Q4, 2020Q4, 2021Q2, 2021Q4, 2022Q2, 2022Q4) and `fig_p4b_forecast_vs_actual_2024_26.png` (origins 2023Q4, 2024Q2, 2024Q4, 2025Q2, 2025Q4, 2026Q1) show actual y/y, tier D, tier C (realised drivers through the bridge) and AR(4). Tier C picks up the 2021-22 rise from the 2019Q4 and 2020Q4 origins (it reaches 6-7% against an actual peak of 8.6%) and tier D does not; from 2021Q4 and 2022Q2 origins tier D stays at 5-6.5% while inflation falls to 3%, with tier C and AR(4) much closer.
* **Does the oil scenario machinery match what happened?** Regressing the outcome on the model's predicted oil effect (`forecast_oil_scenario_validation.csv`): slope 1.46 (s.e. 0.30) at one quarter, 1.48 (0.25) at one year, 1.40 (0.35) at two years; 1.64 and 1.75 for targets since 2020 (slope = 1 rejected). Oil moves co-move with other inflation drivers, so this is an association, not a clean estimate; it still does not support a smaller oil effect.

**Implication.** The structural model's conditional statements are not contradicted by this; its unconditional levels depend on driver assumptions that fail at turning points. This is the Phase 4 conclusion (scenarios are the product) with the cause now identified. The current baseline holds V/U at 1.02 (1990-2019 mean 0.58) and lets GSCPI (1.14 now) decay with rho 0.855; GSCPI is the driver class that produced the 2021-23 miss, and it adds +0.2-0.3 pp to the baseline. I did not change the driver rules: choosing them to improve this backtest would be the fitting the brief asks to avoid.

## 3. Medium-term baseline: why 3.1% in 2029

The y/y path is 4.18% (2026Q4), 2.54% (2027Q4), 2.95% (2028Q3), 3.13% (2029Q3). Exact additive build-up from a neutral reference (neutral wage constant, GSCPI at its steady value, nominal energy and food moving with the reference wages) in the engine's nominal closure (`baseline_reference_steps.csv`, `fig_p4b_baseline_mechanisms.png`):

| y/y, pp | 2026Q4 | 2027Q4 | 2028Q3 | 2029Q3 |
|---|---|---|---|---|
| neutral reference | 3.84 | 2.70 | 2.72 | 2.65 |
| + energy path (futures curve through the bridge) | +0.21 | -0.77 | -0.53 | -0.36 |
| + food path | +0.01 | +0.08 | +0.12 | +0.16 |
| + supply-chain path (GSCPI) | +0.08 | +0.25 | +0.23 | +0.18 |
| + estimated wage constant | +0.04 | +0.28 | +0.40 | +0.50 |
| = baseline | 4.18 | 2.54 | 2.95 | 3.13 |

**Mechanisms.** (i) *Energy.* The futures curve is backwardated ($110 now, $87 end-2027, $75 end-2029): CPI energy falls 4-6% annualised through 2027, the fall slows through 2028 and growth is +0.1% by 2029, while wages grow 3.7%. The drag on y/y peaks at -0.77 pp in 2027Q4 and fades as the fall slows, which contributes +0.41 pp of the +0.59 pp rise from the trough. (ii) *Wage constant.* In the nominal closure the constant adds 0.04, 0.28, 0.40, 0.50 pp, still rising about 0.1 pp a year at the end: it is a slow trend, +0.22 pp of the rise from the trough. (iii) *Supply chains and food* net to about zero (+0.01) and the reference itself drifts -0.05.
**Wage constant.** The estimated constant (-0.312) is 0.294 pp per quarter above the authors' neutral value at V/U 1.02 (-0.606), equal to 0.44 units of V/U. Put differently, the V/U at which the estimated constant is inflation-neutral is **0.59**, the 1990-2019 average (0.58). The baseline therefore treats V/U 1.02 as a tight labour market, not as a constant that can be removed. With drivers held fixed for 20 years, the estimated constant drifts to 3.0, 3.3, 3.4% in years 1, 3, 5 and 4.4% at year 20; with the neutral constant inflation converges to 2.48%, which is the current ten-year expectation (2.47). There is no anchor other than the constant (`baseline_long_run_drift.csv`); Phase 4's 3.13 against 2.63 sensitivity is this 0.50 pp.

**Are the implied wage dynamics plausible?** (`baseline_history_vs_implied_wages.csv`, `baseline_wage_residual_windows.csv`)

| annualised | wage growth | one-year expectations | wage minus expectations | real wage growth | V/U |
|---|---|---|---|---|---|
| 1990-2007 | 3.27 | 2.89 | 0.37 | 0.41 | 0.59 |
| 2010-19 | 2.24 | 1.65 | 0.59 | 0.50 | 0.62 |
| 2017-19 | 2.91 | 1.78 | 1.13 | 0.78 | 1.07 |
| 2023Q3-26Q2 | 3.51 | 2.62 | 0.89 | 0.52 | 1.10 |
| last four quarters | 3.09 | 2.83 | 0.26 | -0.31 | 0.95 |
| baseline 2026Q4-27Q4 | 3.62 | 2.69 | 0.93 | 0.82 | 1.02 |
| baseline 2028Q1-29Q3 | 3.68 | 2.68 | 1.00 | 0.66 | 1.02 |

The baseline's wage-expectations gap (0.9-1.0) matches 2017-19 (1.13 at V/U 1.07) and 2023-26 (0.89 at 1.10), and its real wage growth (0.7-0.8) is inside the historical range (0.4-0.8). The wage equation with its estimated constant fitted 2015-19 with a mean residual of +0.01 (V/U 0.93) and +0.02 in 2017-19, so there is no evidence from the wage data that the constant overstates wages at V/U near 1. Two cautions. The near-term wage path is 0.4-0.8 pp above the last four quarters (3.1%, residuals -0.30): if that run-rate persisted for four quarters the 2027Q4 y/y would be 0.22 pp lower and 2029Q3 0.11 lower. And the 2017-19 expansion had stable inflation at that wage gap because the price equation ran 0.20 pp soft (mean residual); the price residual is -0.28 in 2023Q3-26Q2 and -0.56 in the last four quarters, and the baseline sets it to zero. Sensitivities (`baseline_wage_sensitivities.csv`, y/y 2029Q3): headline 3.13; neutral constant 2.63; wage equation re-estimated to 2019Q4 3.04; to 2023Q2 3.15; all equations to 2019Q4 3.31.
**Verdict.** The medium-term rise is explained and the wage dynamics are plausible, but the 2-3 year level is a statement about a persistently tight (V/U 1.02) labour market with no anchor, 0.5 pp of it from the constant. This is already flagged in Phase 4; the new information is that the constant is the sample-average V/U, not a stray intercept, and that most of the rise is the energy curve.

## 4. Oil-to-CPI-energy bridge

**Fit (`bridge_episodes.csv`, `fig_p4b_bridge_validation.png`).** Monthly R2 0.53, residual s.d. 1.9 pp a month (0.85 in the 1990s, 2.5 in the 2000s, 1.6 since 2010). Errors are large in single quarters and mostly offset within an episode (annualised pp, actual minus bridge estimated before the episode):

| | quarterly errors | cumulative level error | on the headline price level |
|---|---|---|---|
| 2022 (2021Q4 to 2022Q4: +25.6, +15.9, +17.7, -27.1, +0.5) | up to 27 | +1.8% of CPI energy over 2022Q1-Q4 | +0.13% |
| 2026 (Q1 +3.1, Q2 -12.1, Q3 +14.9) | up to 15 | +1.5% | +0.11% |
| 2008Q4 | -83 | | |

Times the 0.075 weight, a 27 pp quarterly miss is about 2 pp of annualised headline inflation. In 2022 CPI energy moved more than the bridge both on the way up (three quarters) and on the way down (2022Q3: -46.6 actual against -19.6); in 2026 the errors alternate in sign. The 2008 and 2022 episodes suggest the bridge underestimates the amplitude of large swings; 2026 does not show it.

**Stability of the 0.30 elasticity (`bridge_subsamples_extended.csv`, `bridge_break_tests.csv`, `bridge_asymmetry_nonlinearity.csv`).**
* Not stable over the full sample, stable since 2010: 0.17 (1990s), 0.41 (2000s), 0.29 (2010-26), 0.30 (2015-26 and 2020-26), 0.34 (2021-26; s.e. 0.03-0.04). Breaks at 2000 (+0.17, t 5.1) and 2008 (+0.10, p 0.05); none at 2015 or 2020. Rolling 15-year estimates range 0.26-0.39.
* No asymmetry: 0.27 (rises) against 0.32 (falls); difference -0.05 (s.e. 0.05).
* **Level dependence:** elasticity 0.28 at the ten-year-average oil price plus 0.17 (s.e. 0.05) per unit of log(Brent/average); **0.37 (s.e. 0.03) at today's price**. In the 130 months where Brent exceeded 1.5 times its ten-year mean, an extra +0.19 (s.e. 0.07).
* Lag length: cumulative 0.30 with three lags, 0.32 with six, 0.34 with twelve (small).
* Levels check: a cointegration-type regression gives 0.32 with a 1.6% a year trend; the residual is borderline stationary (ADF -3.6) and CPI energy sits 11.7 log points above the oil-implied level, with a fitted half-life of 7 months. I do not rely on this: the direct test is that bridge errors mean-revert (next quarter's error on last quarter's: -0.28, s.e. 0.09). Applying that to the 2026Q3 level error (about +15 pp annualised) implies about -4, -2, +3, -3 pp in the next four quarters, a -0.15 pp effect on y/y: small.

**Could residual errors change the scenario conclusions?** (`bridge_scenario_vs_elasticity.csv`, `bridge_error_replay_on_baseline.csv`)
* Additive bridge errors move the **baseline, not the scenario deviations** (the system is linear). A sustained +10 pp annualised miss in CPI energy for four quarters moves baseline y/y by +0.9 pp and the price level by 1.0%. Replaying the realised 2022 and 2026 error patterns moves y/y by only +0.18 and +0.14 pp because the errors offset.
* A wrong **elasticity** scales the oil deviations in proportion. Oil +30% persistent, one-year y/y: 0.51 / 0.61 / **0.75** / 0.86 / 1.01 / 1.27 pp at elasticities 0.20 / 0.24 / **0.30** / 0.34 / 0.40 / 0.50. At the level-dependent 0.37 it is about 0.93. The sign and ordering of every oil scenario are unaffected; the magnitudes carry a -20% / +25% range, skewed up for a $100+ oil price.

## 5. Uncertainty: four sources, kept apart

| Source | In Phase 4's numbers? | Where, and what the evidence says |
|---|---|---|
| **Parameter** | Yes: only source in scenario bands (equations; Phase 4 bands also draw the bridge coefficients, the equation-only comparison below does not); one of four in the baseline fan | HAC-normal draws, equations independent. Tested against a joint moving-block bootstrap that keeps cross-equation dependence (500 draws, 6 scenarios x 3 horizons): band widths within 0.90-1.22 of the HAC bands (median 1.06); medians within 0.06 pp of the point estimate. **The independence assumption is immaterial.** |
| **Exogenous drivers** | No (held at baseline in every band) | Largest source. Implied driver error sqrt(D² - C²) = 1.6 / 1.9 / 1.9 pp for 1 / 2 / 3 years, against a fan s.d. of 0.8-0.9. |
| **Specification** | No (separate sensitivities) | Range across specifications for oil +30%, one year: 0.60-1.19 pp (parameter band 0.26); three-year price level 0.69-1.35%. Variants: bridge elasticity 0.24-0.47, pass-through x0.8, catch-up 0.10/0.25, equations estimated to 2019Q4, frozen at 2023Q2, or recent-weighted. For V/U and expectations scenarios the range is no wider than the parameter band (0.06 and 0.01 pp against 0.06 and 0.10 at one year); food is dominated by parameters (band 1.2 pp). |
| **Historical out-of-sample error** | Shown only as red bars (tier D RMSE) | RMSE of y/y: tier B (realised drivers, structure) 0.69 / 0.74 / 0.70; C (adds bridge) 0.99 / 1.04 / 0.94; D (real-time) 1.84 / 2.20 / 2.10; AR(4) 1.93 / 1.94 / 1.98. Empirical 5%-95% range of tier D y/y errors: -3.3 to +2.8 (1y), -4.5 to +3.1 (2y), -3.9 to +3.0 (3y) pp; excluding 2020-23: -2.2 to +2.5, -2.3 to +3.2, -2.6 to +3.6 (`uncertainty_empirical_error_quantiles.csv`). |

**Coverage of the baseline fan** (`uncertainty_fan_coverage.csv`; the Phase 4 recipe, parameter + residual + bridge noise, rerun at all 86 past origins under tier-D driver assumptions): the nominal-90% fan contains 73 / 66 / 61 / 61% of outturns at 1 / 4 / 8 / 12 quarters (68%-fan: 55 / 45 / 44 / 43%), and 29-43% for 2020-23 targets at one to three years. Realised errors are 2.2-2.4 times the fan's standard deviation overall, including 2.2 at one quarter (the flat-oil assumption contributes about a third of the one-quarter squared error). So the fan is a conditional band, not a forecast interval, and the Phase 4 text says so; the label "90%" is what misleads.
**What the scenario bands mean.** They are 90% intervals for the model's response to a stated assumption, conditional on the model being right, and exclude the other three sources; a reader should not take them as the uncertainty about what the outcome will be.

## 6. Classification and what to fix before Phase 5

**Genuine implementation errors: none found.** Checked: tier D reproduces Phase 4 to 9e-16; the decomposition is exact; the reference build-up equals the baseline and the constant's 0.50 pp equals Phase 4's sensitivity; the bridge helper reproduces the Phase 4 bridge (elasticity 0.297, s.e. 0.029); the joint bootstrap respects the authors' restrictions. Minor documentation inconsistency: Phase 4 §5 gives the catch-up sum as -0.003; B\* is -0.002.

**Economic modelling limitations (known, now quantified):** no anchor for inflation (constant = V/U 0.59); real wages are not error-corrected; driver rules (V/U held, GSCPI AR(1), food with wages) fail at turning points; bridge elasticity is regime- and level-dependent; the price equation has run soft since 2023Q3.

**Corrections required before Phase 5 (presentation only; no change to the model, its coefficients or the headline baseline):**
1. **Relabel the baseline fan** as a "conditional model band" (drivers fixed), show its coverage (61-73%), and add the empirical real-time band next to it.
2. **Report scenario deviations with a specification range, not only the parameter band**: at least bridge elasticity 0.24-0.40 and, for wage-sensitive scenarios, catch-up 0 / 0.10 / 0.25. The Phase 4 band already includes the bridge coefficient draws, so the agreed range is 1.2-1.5 times it for oil scenarios at one year (`p5_scenario_table.csv`); the wider envelope in §5 is larger.
3. **Reframe the 0.8 pass-through haircut.** It should stay as a labelled sensitivity, but the evidence (realised response 1.4-1.5 times the model, elasticity 0.37 at current prices) points to the other side; show the two together (0.8 x 1.25 is about 1.0).
4. **State the baseline's wage constant as "V/U 1.02 is tight"** (inflation-neutral V/U 0.59) next to the 3.13% figure, and give the neutral-constant 2.63% as the lower bound; the headline choice you made on 2026-10-18 stands.

## 7. Decisions taken (2026-10-18) and corrections applied

Decided: (1) headline bridge elasticity stays **0.297**, with **0.24-0.40** as the standard range; (2) the wage catch-up toggle **0 / 0.10 / 0.25** is a labelled sensitivity; (3) baseline driver rules stay (V/U held, GSCPI AR(1), food with wages) with the caveat in §2.
Phase 1-4 files are hash-locked, so the four corrections of §6 are delivered as new Phase 4b tables rather than edits (`scripts/run_p4b_presentation.py`):
1. **Fan relabelled and the empirical band added:** `p5_baseline_bands.csv` has the conditional model band (renamed, with its 61-73% coverage in `p5_labels.csv`), the empirical real-time band (all targets, and excluding 2020-23), and the neutral-constant lower bound. 2026Q3 is published and carries no band; 2026Q4 is the first band quarter (the empirical band was measured without a nowcast quarter, so it is conservative there).
2. **Specification range next to the parameter band:** `p5_scenario_table.csv`, all 15 scenarios, 1/2/3 years: headline, Phase 4 parameter band, range over elasticity {0.24, 0.297, 0.40} x catch-up {0, 0.10, 0.25}, each factor alone, price-level range. Oil scenarios at one year: oil +30% 0.75 (band 0.58-0.92; range 0.61-1.04), oil stays at $111 0.53 (0.43-0.62; 0.43-0.71), oil -30% -1.02 (-1.25 to -0.79; -1.41 to -0.83). V/U, expectations, food, supply-chain and productivity scenarios are unchanged by the two factors at one year (range under 0.01 pp).
3. **Haircut reframed:** a separate column "alternative: pass-through x0.8 (labelled, not preferred)" and the wording in `p5_labels.csv`.
4. **Wage constant stated as "V/U 1.02 is tight":** in `p5_labels.csv` and `p5_baseline_bands.csv` (neutral-constant lower bound 2.63% in 2029Q3).
Wording for every number is in `p5_labels.csv` and is the standard for any report or dashboard.

## Files
`outputs/phase4b/`: wage (`wage_catchup_evidence`, `wage_postcovid_residual_test`, `wage_overlay_{scenarios,baseline,paths}`, `wage_channel_coefficients`, `wage_oneoff_price_shock_real_wage`, `wage_residual_history`); forecast (`forecast_error_components`, `forecast_error_summary_{yoy,quarterly}`, `forecast_paths_selected`, `forecast_oil_scenario_validation`); baseline (`baseline_reference_steps`, `baseline_long_run_drift`, `baseline_wage_constant`, `baseline_history_vs_implied_wages`, `baseline_wage_residual_windows`, `baseline_wage_sensitivities`, `baseline_key_paths`); bridge (`bridge_episodes`, `bridge_episode_level_errors`, `bridge_recursive_elasticity`, `bridge_rolling15y_elasticity`, `bridge_break_tests`, `bridge_asymmetry_nonlinearity`, `bridge_subsamples_extended`, `bridge_lag_length`, `bridge_error_correction`, `bridge_error_persistence`, `bridge_scenario_vs_elasticity`, `bridge_error_replay_on_baseline`); uncertainty (`uncertainty_fan_coverage[_records]`, `uncertainty_parameter_bands_hac_vs_bootstrap`, `uncertainty_specification_envelope`, `uncertainty_specification_vs_parameter`, `uncertainty_sources_accounting`, `uncertainty_empirical_error_quantiles`); presentation (`p5_baseline_bands`, `p5_scenario_table`, `p5_labels`); figures `fig_p4b_*.png` (7).
Code: `bb_inflation/phase4b/{common,wage,forecast,baseline,bridge,uncertainty}.py`, `scripts/run_p4b_*.py`, `tests/test_phase4b.py`. Run order: wage, forecast, baseline, bridge, uncertainty, figures (each under a minute; uncertainty about 30 s).
