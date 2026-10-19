# Phase 3 supplement: post-2023 forecast errors, interpretable impulse responses, and the missing October 2025 V/U

Date: 2026-10-18. Baseline model, specification and pinned data are unchanged (`pull_20261017T112636Z`, GSCPI 2-quarter mean).
New: a stamped diagnostic pull `supp_20261018T032016Z` (core/shelter CPI, claims, labour force; never used in estimation) and
**Model B\***, which is Phase 3's Model B re-estimated with a flagged bridge for the one missing observation (V/U 2025Q4).
Phase 1-3 outputs are untouched (91 files, SHA-256 manifest in `outputs/phase3_supp/phase1-3_outputs_manifest.sha256`, checked by a test).
Everything below is in `outputs/phase3_supp/`; run `scripts\run_supp_*.py`; 93 tests pass (80 earlier + 13 new). Phase 4 has not been started.

## 0. Summary

1. **No evidence of a systematic post-2023 over-prediction; four quarters account for it.** One-step errors average -0.34 pp
   (Newey-West t = -1.5) and +0.06 pp after removing 2023Q3, 2025Q4, 2026Q1 and 2026Q2. 2023Q3 alone is 48% of the sum of squared errors
   (z = -3.3); 2025Q4-2026Q2 are another 33% (z = -1.4 to -1.7 each). **Baseline model retained.**
2. **The causes differ by quarter.** 2023Q3: underlying inflation (core goods fell), not energy. 2025Q4: a shutdown measurement artifact plus a soft
   core. 2026Q1: mostly energy (the model's energy contribution is 0.6 pp above the mechanical direct effect of the energy CPI). 2026Q2:
   weaker core and wages, plus a shelter catch-up that hides about 0.4 pp of the miss. Wage-equation errors add -0.3 to -0.4 pp per quarter in 2025Q4-2026Q2.
3. **Impulse responses** are now given as annualised inflation (original), year-on-year inflation, and the CPI price level. Rule of thumb from the
   model: a permanent +10% relative energy price lifts y/y inflation by about 1.0 pp for four quarters and the price level by 1.0% after one year
   (1.2% after three); a temporary spike leaves the price level where it was after about a quarter. Phase 3's "cumulative 0-8" figures summed annualised rates, so
   they are four times the price-level effect (§2.5).
4. **October 2025 unemployment does not exist in any official series.** V/U 2025Q4 is bridged by interpolating the October unemployment level
   between September and November (V/U = 0.895 against 0.877 in Phase 3). The bridge has one third of the back-test error of Phase 3's Nov-Dec method,
   uses no data after December 2025, extends the wage equation to 2026Q2 (N 144 to 146) and changes no conclusion.
5. **GSCPI:** routine check passed (0 revisions, timestamps and values consistent). Phase 3 treatment kept.

## 1. Post-2023 inflation over-prediction (2023Q3-2026Q2)

**Measures.** "Predicted" can mean four things; they give different average errors (actual minus predicted, pp):

| Measure | Mean error |
|---|---|
| One-step, Model A (frozen at 2023Q2, genuinely out of sample) | -0.34 |
| One-step, Model B\* (re-estimated, in sample) | -0.28 |
| Conditional forecast made in 2023Q2 with realised drivers (A) | -0.16 |
| Free-running baseline from 2018Q4 (Phase 3's "0.5-0.7 pp over-prediction"; B\*: -0.63, A: -0.68) | -0.63 to -0.68 |

The Phase 3 figure is the last row: it carries every earlier miss through the lags. The one-step residual is the cleanest estimate of the price-setting error.

**By quarter** (`fig_s1_actual_vs_predicted.png`, `resid_quarter_table.csv`; z = residual / 0.57 pp, the pre-2020 residual s.d.):

| Quarter | Actual | Model A | Residual A | z | Residual B\* | Share of squared error |
|---|---|---|---|---|---|---|
| 2023Q3 | 4.27 | 6.18 | **-1.91** | -3.3 | -1.65 | 48% |
| 2023Q4 | 1.90 | 2.58 | -0.67 | -1.2 | -0.52 | 6% |
| 2024Q1 | 4.64 | 4.00 | +0.65 | 1.1 | +0.69 | 6% |
| 2024Q2-2025Q3 (6 qtrs) | | | -0.27 to +0.60 | | | 7% |
| 2025Q4 | 2.20 | 3.09 | **-0.89** | -1.6 | -0.85 | 11% |
| 2026Q1 | 5.20 | 6.18 | **-0.99** | -1.7 | -0.88 | 13% |
| 2026Q2 | 2.75 | 3.57 | **-0.83** | -1.4 | -0.74 | 9% |

**What the errors are associated with** (`fig_s2_error_sources.png`). The forecast error from 2023Q2 splits exactly by equation (the model is linear in its shocks):

| | 2023Q3 | 2025Q4 | 2026Q1 | 2026Q2 |
|---|---|---|---|---|
| Total error (actual - forecast) | -1.68 | -0.78 | -0.85 | -0.65 |
| of which price-equation residual | -1.91 | -0.91 | -0.91 | -0.76 |
| wage-equation residual (wage dynamics) | +0.23 | -0.26 | -0.41 | -0.32 |
| expectations residuals | +0.00 | +0.39 | +0.47 | +0.43 |
| Model B\* energy block minus mechanical direct energy contribution* | +0.22 | +0.11 | **+0.62** | +0.38 |
| Model B\* non-energy part minus actual non-energy part (headline less direct energy)* | +1.43 | +0.75 | +0.26 | +0.36 |
| Core CPI, annualised (actual) | 2.9 | 1.7 | 2.8 | 2.3 |

\*Mechanical direct energy contribution = CPI energy weight (0.074, estimated from monthly data 2015-25) x annualised energy-CPI growth; the model's
energy block is the sum of its five energy lag terms. Weights are implied, not published ones.

* **Energy pass-through (2026Q1):** the energy CPI rose 38% annualised (gasoline 67%). The model's contemporaneous energy coefficient (0.092) is 24% above the
  CPI weight, so it books about 0.6 pp more than the direct effect, which is roughly the whole miss (-0.9). It is not the story in 2023Q3 (+0.2 only) or 2025Q4.
  Core CPI did not accelerate after the spike (2.8% in Q1, 2.3% in Q2), so no second-round effect is visible yet.
* **Underlying inflation:** 2023Q3 is an underlying miss (core goods -3.6% annualised, core CPI 2.9%; the model's non-energy part was 3.9% against 2.5% actual). In 2025Q4 and 2026Q2 core was
  1.7% and 2.3%.
* **Wage dynamics:** ECI growth fell short of the wage equation in 2025Q4-2026Q2 (residuals -0.4, -0.5, -0.1); the pass-through into prices is -0.26, -0.41, -0.32 pp of CPI error per quarter, about a third of those errors.
* **Measurement (shutdown):** BLS carried October 2025 rents forward, leaving index levels too low until the April 2026 panel (BLS Monthly Labor Review counterfactuals put the missing October rent/OER change at
  0.24-0.59%). From the data, April 2026 rent and OER rose 0.33% and 0.28% faster than their Jan-Mar/May-Jun average. With rent+OER at about 33.5% of CPI (assumption), that is
  about **0.4 pp annualised (range 0.3-0.8)**: 2025Q4 understated, 2026Q2 overstated. Adjusting moves the residuals to -0.48 (2025Q4) and -1.23 (2026Q2), unchanged in 2026Q1 (-0.99). The adjustment cancels across the
  three quarters, so it changes the timing of the miss, not its size.
* **Supply chains:** the model books +0.3 pp from GSCPI in 2026Q2 (GSCPI 1.6) while core goods prices fell. Noted only; no investigation, as instructed.

**Is there evidence to change the model? No.**
* The errors are few and episodic: z-scores of -1.4 to -1.7 in three of the last four quarters are not unusual in 12 observations, 2023Q3 is the only large outlier, and the average is not significant.
* The frozen 2023Q2 equations pass the predictive-failure test on 2023Q3-2026Q2 for all four equations (Chow p = 0.88 wage, 0.37 price, 0.67 cf1, 0.80 cf10; `reval_chow_post2023_A.csv`).
* *Energy asymmetry candidate* (smaller pass-through for energy rises). Adding a positive-growth term to the price equation gives -0.019 (HAC t = -2.2) estimated only
  through 2023Q2, so the sign was already present before the episodes that prompted the question; it implies about 20% less pass-through on increases. The test of whether it helps forecasts says no:
  one-step recursive RMSE 2004Q4-2026Q2 is 1.144 against 1.100 for the baseline (worse by 4%; 15% worse before 2020; 4% better after 2023Q3: 0.753 vs 0.784). A "large spikes only" variant is similar (1.109).
  This is suggestive and not established, and it is not adopted. It is a sensitivity for Phase 4: for a large energy spike, a pass-through haircut of about 20% is within what the data allow.

## 2. Impulse responses in interpretable units (Model B\*)

### 2.1 How to read them
The model's native response is annualised quarterly CPI inflation (400 x change in log CPI), in pp, after a shock in quarter 0, with no policy response. Two derived views:
* **y/y inflation (pp)** = mean of the last four annualised quarterly responses. The base effect is visible: a one-off price jump lifts y/y for four quarters, then drops out.
* **Price level (% above baseline)** = cumulated annualised responses / 4. Never add up annualised rates and call it a price-level change: the sum is four times too big.

Percentage-point inflation effects and percent price-level effects are kept in separate columns throughout. Log approximation (exact within 0.01 pp at these sizes).

### 2.2 Shocks and assumptions
Shocks are to the **level** of the driver and the response is linear, so they scale proportionally (half the size, half the effect).
* **Temporary:** driver rises in the shock quarter and is back at baseline in the next (spike and reversal). **Persistent:** level fades geometrically, rho = 0.8 (half-life 3.1 quarters).
  **Permanent:** driver stays at its new level. For energy and food the driver is the relative price (CPI component / ECI wages); the model input is its annualised growth, 4 x the change in the level in %.
* Sizes: energy **+10%** (largest one-quarter rise in 2020-26: 11.2%, 2022Q1; 2026Q1: 8.8%); food **+5%** (largest four-quarter rise: 5.5%); GSCPI **+1.0** (units are standard deviations; largest quarterly rise 1.5);
  V/U **+0.1** (s.d. of quarterly change 0.22; moved from 0.95 to 1.02 in 2025Q3-2026Q2; `irf_shock_size_anchors.csv`).
* "After 1/2/3 years" = cumulated through quarters 3/7/11 after the shock quarter. Intervals: 90%, Monte-Carlo from HAC covariances, equations drawn independently (as Phase 3).
* Horizon 32 quarters. No monetary policy reaction, no change in other exogenous drivers, expectations as the model has them.

### 2.3 Results (`fig_s4_irf_intuitive.png`, `irf_scenarios_Bstar.csv`, `irf_headline_table_Bstar.csv`)

| Shock | Type | Annualised peak, pp (qtr) | y/y peak, pp (qtr) | y/y half-life; faded to 25% of peak | Price level, %: 1y / 2y / 3y |
|---|---|---|---|---|---|
| Energy +10% | temporary | 3.66 (q0) | 0.92 [0.84, 0.99] (q0) | 1 q; 5 q† | 0.03 / 0.03 / 0.03 |
| | persistent | 3.66 (q0) | 0.92 (q0) | 5 q; 8 q | 0.53 / 0.29 / 0.21 |
| | permanent | 3.66 (q0) | 0.99 [0.87, 1.15] (q3) | 1 q after peak; 4 q | 0.99 / 1.08 / 1.20 [0.86, 1.51] |
| Food +5% | temporary | 2.50 (q0) | 0.63 [0.36, 1.27] (q0) | 1 q; 9 q | -0.12 / 0.12 / 0.02 |
| | persistent | 2.50 (q0) | 0.63 (q0) | 3 q; 12 q | 0.31 / 0.49 / 0.29 |
| | permanent | 2.50 (q0) | 0.78 [0.58, 1.43] (q2) | 3 q; 11 q | 0.66 / 1.23 / 1.35 [0.60, 2.13] |
| GSCPI +1.0 | temporary | 0.14 (q0) | 0.08 [0.03, 0.13] (q3) | 2 q; 7 q | 0.08 / 0.10 / 0.11 |
| | persistent | 0.23 (q1) | 0.21 [0.08, 0.32] (q4) | 8 q; 23 q | 0.19 / 0.35 / 0.46 |
| | permanent | 0.63 (still rising) | 0.61 [0.23, 1.08] (still rising at 8y) | does not fade | 0.25 / 0.62 / 1.04 [0.40, 1.68] |
| V/U +0.1 | temporary | 0.21 (q1) | 0.05 [0.04, 0.08] (q1) | 2 q; 8 q | 0.02 / 0.04 / 0.05 |
| | persistent | 0.21 (q1) | 0.12 [0.08, 0.15] (q4) | 2 q; 17 q | 0.10 / 0.16 / 0.20 |
| | permanent | 0.27 (still rising) | 0.26 [0.18, 0.35] (still rising at 8y) | does not fade | 0.13 / 0.29 / 0.46 [0.35, 0.57] |

†After the one-quarter spike reverses, y/y inflation swings to -0.92 pp four quarters later when the spike drops out of the year-on-year window (base effect); the 5 quarters are the end of that swing. Annualised peaks are the shock quarter's value; "still rising" means no peak within 8 years.

### 2.4 In plain language
* **Energy.** The effect on *inflation* is immediate and short: about 3.7 pp annualised in the quarter (0.9 pp of y/y), and it is gone from the quarterly rate in the next. What differs by shock type is the **price level**: a temporary
  spike leaves almost nothing behind; a permanent one leaves the CPI about 1% higher after a year and drifts up to about 1.2% after three, which is second-round wage and expectations feedback adding to the direct effect (the
  energy coefficients alone give about 0.75%, close to the energy CPI weight). The model has no anchoring of expectations, so the permanent price shock keeps a small positive inflation tail (0.1 pp y/y after three years).
* **Food.** The same pattern, a smaller impact (0.63 pp of y/y per 5%) and wider uncertainty: food coefficients alternate in sign across lags, so the quarter-by-quarter profile is noisy; read the level columns.
* **GSCPI (supply chains).** Weak and slow: a one-standard-deviation, one-quarter blip adds 0.1% to the price level over three years. A persistent shock, closer to what a prolonged disruption looks like, adds 0.2 pp to y/y at the peak
  and 0.5% to the price level. A permanent shift is a theoretical bound that has not occurred (the index mean-reverts).
* **V/U (labour-market tightness).** The slowest channel and the only one that is genuinely cumulative. A +0.1 move that reverses next quarter does little (0.05 pp); a sustained +0.1 adds about 0.25 pp to inflation permanently
  (there is no natural rate in the model's wage equation), the price level rising 0.13% after a year and 0.46% after three.

### 2.5 Reconciliation with Phase 3 (originals preserved in `outputs/phase3/`)
* The new code reproduces seven Phase 3 responses of Model B to within 1e-9 pp when given Phase 3's shock sizes (`irf_regression_check_vs_phase3.csv`, `test_irf_code_reproduces_phase3_responses`).
* Phase 3 "cumulative 0-8" and "cumulative 0-12" statistics are sums of annualised rates in pp. Divide by 4 for the price-level effect in percent (energy one-off, +1 s.d.: 2.66 pp summed = 0.67% on the price level). The figures were correct as labelled, but "pp over 8 quarters" is not a
  price-level change and should not be quoted as one.
* Phase 3 "one-off (level)" for energy and food is the new **permanent** scenario. Phase 3 "persistent (rho 0.8)" for energy and food made the *growth rate* persistent (a run of price rises, five times the level change), a different object from the persistent level shock here.
* Models A and B\* give almost the same responses (`irf_scenarios_A.csv`; y/y peaks within 0.07 pp and three-year price levels within 0.04% in every scenario). B\* and Phase 3's B differ by at most 0.003 pp and 0.002%.

## 3. The missing October 2025 observation (V/U 2025Q4)

**Why it is missing.** BLS could not collect the October 2025 Current Population Survey during the lapse in appropriations and did not collect it retroactively, so
no October household estimate exists (BLS Employment Situation releases of 16 Dec 2025 and 9 Jan 2026; the BLS series page for LNS14000000 carries the footnote "data unavailable due to the 2025 lapse in appropriations").
JOLTS openings for October 2025 are published (7.17 million). V/U is a ratio of quarterly means, so 2025Q4 needs the October unemployment level.

**Is there an official or Macrobond substitute? No.** Checked live (`vu_oct2025_live_probe.csv`): unemployment level SA (`uslama1795`, BLS copy `bls_lns13000000m`), NSA level (`uslama2169`, `bls_lnu03000000m`) and NSA rate (`uslama2320`) are all blank for October 2025.
One oddity: the SA unemployment *rate* series carries 4.5% for October 2025 in Macrobond (both `uslama1849` and the BLS copy), first appearing between the Macrobond vintages of 3 and 10 Aug 2026 (the July employment report came out on 7 Aug) (`vu_oct2025_rate_vintages.csv`); BLS's own series page and tables show none, and I found no BLS notice
explaining it. I treat it as vendor-supplied and non-authoritative. It is used only as a cross-check: 4.5% x the interpolated labour force implies U = 7.71 million and V/U = 0.894 (range 0.891-0.898 for rounding), the same as the bridge below.
**Chicago Fed nowcast and the Macrobond rate (added after your note).** The Chicago Fed's real-time model (private data and claims) put October at 4.35%, later 4.36% (press: Reuters/Yahoo; I could not open the Business Times page). That is a model nowcast made in Nov 2025, before BLS's revised November rate (4.6% then 4.5%), and is not a BLS number. Converted to a level the same way it implies V/U = 0.904 (0.9037-0.9044), against 0.895 for the bridge and 0.894 for the Macrobond rate. The Macrobond 4.5% is unexplained, rounded to 0.1, exists only as a rate (no level or labour force), and equals the average of September (4.4) and November (4.5) rounded up, so it may be a mechanical interpolation. **Judgement:** all three sit within 0.01 of each other in V/U, and section 3's sensitivity shows +/-0.10 in V/U moves the 2026H1 CPI baseline by only 0.1 pp, so the choice is immaterial. I keep the level-based interpolation as the baseline because its source and rule are documented and it needs no unexplained series; using the Macrobond rate instead is acceptable as a labelled alternative (V/U 0.894, a 0.001 change) but should not be described as an official observation. Both are in `vu_rate_crosscheck.csv`.

**Methods compared** (`vu_bridge_alternatives.csv`, back-test `vu_bridge_backtest_summary.csv`; hide one observed first-month-of-quarter unemployment level 2001-2025Q3, 94 cases excluding 2020-03..2021-06, error in quarterly V/U):

| Method | V/U 2025Q4 | Back-test RMSE (V/U) |
|---|---|---|
| Drop October from both numerator and denominator (Nov-Dec ratio; Phase 3's simulation bridge) | 0.8765 | 0.021 (and 0.877 sits below the others because October's openings, the highest of the quarter, were dropped) |
| **Interpolate U(Oct) between Sep and Nov, keep all three JOLTS months** | **0.8951** | **0.006** |
| Carry September forward | 0.8985 | 0.008 |
| Carry November back | 0.8917 | 0.010 |
| Interpolation tilted by continuing claims (beta from pre-gap data) | 0.8943 | 0.006 |

Adopted: interpolation, since it is parameter-free, equals the claims-tilted version in accuracy, uses every observed month and only data to December 2025. The four defensible methods span 0.892-0.899.

**Observation status** (`vu_observation_status.csv`):

| Item | Status |
|---|---|
| V/U 1990Q1-2025Q3 and 2026Q1-2026Q2 | actual |
| JOLTS openings Oct, Nov, Dec 2025; unemployment level Sep, Nov, Dec 2025 | actual |
| Unemployment level October 2025 | **does not exist; estimated (7.693 million, interpolation)** |
| **V/U 2025Q4 = 0.8951** | **estimated (one of three monthly inputs)**; flagged `vu_bridged` |
| Wage-equation observations 2026Q1 (lag 1) and 2026Q2 (lag 2) | use the estimated V/U as a regressor; the dependent variable is actual |
| Price, expectations equations; all CPI inflation (end-of-quarter December value) | no estimated data |

**Sensitivity and re-run** (`vu_sensitivity_modelB.csv`, `reval_*.csv`). Wage-equation V/U sum is 0.6723 under all four methods (Phase 3 B: 0.689, HAC s.e. 0.21). Across them the free-running 2026H1 CPI baseline varies by 0.01 pp (5.190-5.196). Even an error
of +/-0.10 in V/U moves it only -0.09/+0.10 pp and the V/U sum to 0.661-0.664. Everything that touches the bridge was re-run on B\*:

* Coefficients: no sum differs from Phase 3's B by more than 0.07 HAC s.e. (V/U 0.689 to 0.672; own lags 0.534 to 0.540; price equation identical); no plausibility or instability flag trips (`reval_flags.csv`).
* Stability: same conclusions as Phase 3 (wage: no break, p = 0.25-0.37; price: wage pass-through and energy/food blocks unstable in 2020-21, p < 0.005; Chow predictive failure of frozen A: not rejected, wage equation now n = 12, p = 0.88).
* Decomposition of 2026Q1-Q2: energy 1.84, V/U -0.30, residual -1.22 pp (Phase 3, B: 1.8-1.9, -0.3 to -0.4, -1.15 to -1.30).
* Pseudo-out-of-sample (86 origins, horizons 1-12): largest change in any RMSE 0.010 pp; unweighted still beats half-lives 5, 10, 15 years (1.260 vs 1.299 best), so the selection rule gives the same answer.
* IRFs: §2 uses B\*; headline statistics differ from Phase 3's B by under 0.01 pp (y/y peaks and three-year price levels, all twelve scenarios).

**No look-ahead** (`vu_lookahead_audit.csv`, tests): the bridge uses only data dated up to December 2025 (recomputing it from data truncated there gives an identical value); estimation through any origin up to 2025Q4 is identical with and without the bridge; the
first estimation sample that contains it ends 2026Q1. Conditional forecasts use realised V/U by design, so for origins before 2025Q4 the bridged V/U is a stand-in for a realised value; unconditional forecasts hold V/U at its origin value.
Caveat inherited from Phase 3: data are current-vintage, not real-time.

## 4. GSCPI routine check (Phase 3 treatment unchanged)
`gscpi_source_check.csv`: pinned pull passes its integrity check; re-pull on 2026-10-18 has 0 revised and 0 new observations; Macrobond last-revision stamp 2026-10-06 equals the NY Fed release date; monthly series 1997-09 to 2026-09 with no gaps;
2026Q2 mean 1.5994 matches the model dataset; Sep 2026 (1.284), Aug (1.199, revised up) and the May peak (1.808) agree with press reports of the NY Fed release. (I did not download the NY Fed file; the web page text was not machine-readable.)
July-September 2026 (0.93, 1.20, 1.28) are listed, not used: 2026Q3 is incomplete for productivity, ECI and V/U.

## 5. Implications for inflation risks
* **Energy is the channel to be careful with.** The model's response to an energy spike is front-loaded and probably somewhat generous (0.6 pp over the direct effect in 2026Q1; about 20% lower pass-through on increases in the full sample, not established out of sample).
  A 10% rise in the energy price adds about 1 pp to y/y inflation and 1% to the price level within a year; treat that as an upper-middle estimate. Latest data: CPI energy rose again in 2026Q3 (+22.6% annualised, gasoline +38.5%, headline 4.5%, core 3.4%; the quarter is incomplete and not in the model).
* **Persistence is the real risk, not the first-round hit.** Temporary energy and supply-chain blips fade within a year and leave almost no price-level footprint; anything that makes a shock persistent or moves wage growth and expectations (a sustained V/U rise, a persistent
  energy or GSCPI shock) compounds, and the model has no mechanism that pulls inflation back. The 2026H1 outturns (core 2.3-2.8%, ECI below the wage equation) show no such second-round effect so far.
* **Downside surprises since 2025Q4 are partly measurement.** The shutdown artifact shifts about 0.4 pp between 2025Q4 and 2026Q2; year-on-year comparisons through 2026Q3 are affected, and BLS will not publish October 2026 12-month changes for series lacking October 2025.
* **Underlying inflation and wages are running a little below what the model implies** (core 1.7-2.8% in the last three quarters, wage residuals negative), which argues against reading the 2026H1 energy spike as the start of a wage-price spiral, subject to the small sample.
* Forecast error scale: one-step price-equation s.d. about 0.6 pp per quarter; errors of 1-2 s.d. in a given quarter are normal.

## 6. Limits
Twelve post-2023 observations cannot separate a regime change from noise; the energy-asymmetry and wage-dynamics readings are suggestive only. The shelter adjustment rests on an assumed rent+OER weight (0.335); the BLS range
(0.3-0.8 pp) is wide. Energy and core weights are estimated, not published. Model B\*'s wage equation uses two observations that depend on the bridged value (it moves coefficients by under 0.1 s.e.). Intervals exclude cross-equation covariance.
Not done, as instructed: Phase 4 scenarios; any investigation of the cause of the 2026 GSCPI rise.

## Files
`outputs/phase3_supp/`: `fig_s1_actual_vs_predicted.png`, `fig_s2_error_sources.png`, `fig_s3_residual_vs_energy.png`, `fig_s4_irf_intuitive.png`; `resid_*.csv` (part 1); `irf_*.csv` (part 2); `vu_*.csv`, `reval_*.csv` (part 3); `gscpi_source_check.csv`.
Code: `bb_inflation/supplement/` (`diag_pull`, `vu_bridge`, `context`, `residuals`, `irf_intuitive`), `scripts/run_supp_{residuals,irfs,vu,revalidate,gscpi_check}.py`, `scripts/_oneoff/probe_oct2025_*.py`, `tests/test_supplement.py`.
Data: `data_cache/macrobond/supplement/supp_20261018T032016Z/` (first stamp `supp_20261018T030950Z` was superseded after adding the labour-force series; same values).
