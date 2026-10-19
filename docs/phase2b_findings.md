# Phase 2b findings: swap ladder from the authors' data to Macrobond + GSCPI

Date: 2026-10-16. Authors' specification and sample (1990Q1-2023Q2) throughout; nothing re-specified.
Code: `bb_inflation/validation/ladder.py`, `scripts/run_phase2b.py`; tests `tests/test_ladder.py` (the full suite: 66 tests at the
time of writing, 80 after Phase 3, all pass). Full tables (all 18 cases, ~120 metrics each): `outputs/phase2/ladder.xlsx` / `ladder.csv`.
Figures: `outputs/phase2/fig_ladder_{price_coefs,irfs,decomposition}.png`, `fig_google_vs_gscpi.png`.

## 1. Bottom line

1. **Swapping the data series for Macrobond changes little; swapping Google "shortage" for GSCPI changes a lot.**
   At the authors' vintage the Macrobond data reproduce every authors' result (control V0). With today's vintage the
   data swaps move the price-equation sums by at most 0.04 (mostly productivity revisions). The GSCPI swap moves the
   shortage sum from 0.022 to 0.265, the lagged-inflation sum from 0.297 to 0.149 and the wage sum from 0.703 to 0.851.
2. **GSCPI fits worse and attributes inflation differently.** Price-equation R² 0.945 → 0.939; the decomposition's
   dynamic baseline misses actual 2020Q1-2023Q2 CPI inflation by RMSE 1.26 pp instead of 0.99 pp. Shortages explain
   1.1 pp of 2021Q2 inflation instead of 4.1 pp; food prices and "initial conditions" pick up the difference.
3. **Interpretability is worse with GSCPI.** The contemporaneous coefficient is insignificant (t = 0.6, vs 5.2 with
   Google) and the lags alternate in sign (+0.11, +0.26, +0.17, -0.45, +0.18). Only the sum is significant
   (p = 0.015). A negative third-lag coefficient of -0.45 has no economic reading.
4. **Macrobond's own pre-2001 ECI history (sensitivity S1) matters more than expected**: it moves the price equation's
   wage sum from 0.851 to 0.553 and the wage-equation R² from 0.663 to 0.621, and worsens out-of-sample wage RMSE. The
   authors' wage-price pass-through is therefore sensitive to which pre-2001 wage series is spliced in.

## 2. Ladder (full-sample run; price equation and wage equation sums of coefficients)

| Case | gcpi lags | wage | energy | food | shortage | produc. | R² price | | wage eq: V/U | R² wage | OOS RMSE gw |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 authors | .333 | .667 | .066 | .126 | .019 | -.144 | .947 | | .688 | .660 | 1.20 |
| L1 + CPI, energy, food | .328 | .672 | .067 | .129 | .019 | -.148 | .944 | | .688 | .660 | 1.20 |
| L2 + productivity | .295 | .705 | .069 | .132 | .022 | -.170 | .945 | | .697 | .660 | 1.19 |
| L3 + ECI (2001+) | .297 | .703 | .069 | .132 | .022 | -.169 | .945 | | .681 | .660 | 1.15 |
| L4 + V/U (2001+) | .297 | .703 | .069 | .132 | .022 | -.169 | .945 | | .708 | .663 | 1.14 |
| L5 + Cleveland | .297 | .703 | .069 | .132 | .022 | -.169 | .945 | | .708 | .663 | 1.14 |
| **L6 + GSCPI (all Macrobond, current)** | **.149** | **.851** | .078 | .202 | **.265** | -.154 | **.939** | | .708 | .663 | 1.14 |
| S1 = L6 with Macrobond ECI history | .447 | .553 | .056 | .172 | .198 | -.094 | .936 | | .707 | .621 | 1.23 |

The expectation equations (cf1, cf10) are unchanged to three decimals at every step (sums 0.293 / 0.571 / 0.136 and
0.975 / 0.025): Cleveland data are identical, and the equations do not contain shortage.

Single swaps onto the authors' data (current vintage): productivity alone moves the price-equation lag sum
0.333 → 0.300 and the productivity sum -0.144 → -0.166 (the dominant revision effect); CPI/energy/food alone
0.333 → 0.328; ECI, V/U and Cleveland alone move nothing visible.

## 3. Controls at the authors' vintage (separating revisions from the GSCPI effect)

| Case | shortage sum | wage sum | R² price |
|---|---|---|---|
| V0 Macrobond @ authors' vintage, Google | .019 (= L0) | .667 | .947 |
| V1 authors' data + authors' GSCPI file (their Table A8) | .271 (p .016) | .834 | .940 |
| V2 Macrobond @ authors' vintage incl. its GSCPI vintage | .270 | .832 | .940 |
| V3 same data + *current* GSCPI | .256 | .831 | .940 |

GSCPI revisions are a small effect (0.015 on the shortage sum); the move from Google to GSCPI is the large one.

## 4. Impulse responses and decomposition

* **Energy, food, V/U IRFs barely change** across L0 → L6 (figure `fig_ladder_irfs.png`). The V/U response after 27
  quarters is 1.43 (L0), 1.44 (L5), 1.45 (L6): the labour-market channel, which carries the model's key message
  about slowly rising inflation under persistent tightness, is robust to this exercise. With Macrobond's own ECI
  history it is 1.39.
* **Shortage IRF**: a one-s.d. shortage shock (10.1 index points for Google, 1.48 for GSCPI) has a similar impact
  (+1.1 pp) but the follow-through differs in sign: with Google the response is negative at quarters 1 and 4
  (-0.27, -0.36, a payback), with GSCPI it is positive (+0.35, +0.52) and turns negative only at quarter 8 (-0.11).
* **Decomposition of CPI inflation** (pp, annualised):

| | L0 authors | L5 Macrobond, Google | L6 Macrobond, GSCPI |
|---|---|---|---|
| 2021Q2: shortages | 4.08 | 4.15 | 1.10 |
| 2021Q2: food | 0.47 | 0.52 | 1.27 |
| 2021Q2: initial conditions | 2.55 | 2.55 | 2.71 |
| 2021Q2: actual | 8.43 | 8.50 | 8.50 |
| average 2021-22: shortages | 1.23 | 1.32 | 0.95 |
| average 2021-22: energy | 1.30 | 1.27 | 1.23 |
| average 2021-22: V/U | 0.27 | 0.27 | 0.31 |
| average 2021-22: actual | 6.60 | 6.57 | 6.57 |
| baseline RMSE vs actual, 2020Q1-2023Q2 | 0.96 | 0.99 | 1.26 |

  The paper's headline (energy and shortages dominate 2021-22 inflation, V/U modest) survives in direction, but
  with GSCPI the shortage contribution drops by about a quarter on average and by three quarters in 2021Q2, the
  quarter where the authors found shortages dominant. That quarter is where Google "shortage" peaked (May 2021) while
  GSCPI peaked later (2021Q4; `fig_google_vs_gscpi.png`): the two series disagree on timing.

## 5. Why the substitute behaves differently

Google "shortage" is flat near 5 until 2020 and spikes in 2021; GSCPI moves throughout the sample (correlation 0.04
in 2004-19, 0.38 in 2020-23). The authors' price equation identifies the shortage coefficients almost entirely from
2020-23, so the coefficient is determined by how well the series times the pandemic episode, and Google timed it
better for CPI. This is a property of the data, not a coding choice: our GSCPI variant on the authors' own file
reproduces their Table A8 (0.271, R² 0.940).

## 6. Implications for Phases 3-5

* Keep the authors' Google-based result as the benchmark for "original specification" comparisons, and report
  the Macrobond/GSCPI version as the operational model, always with this attribution caveat.
* Because GSCPI's own coefficients are poorly identified (t = 0.6 contemporaneous, sign flips), a smoother or shorter
  lag structure was proposed here; it has since been tested (and also genuine out-of-sample fit, HAC inference and
  stability): see `docs/validation_report.md`. Note the in-sample comparison in §1-§4 above is one-sided: in a genuine
  out-of-sample test (estimation through 2019Q4) GSCPI beats Google, not the reverse.
* Shock sizes, steady states and scenario inputs for GSCPI must be in GSCPI units (1 s.d. 2020+ = 1.48;
  steady state -0.035 in the decomposition, following the authors' Table A8 convention). The authors'
  forecast assumption "shortage = 10" has no direct GSCPI equivalent; a mapping needs a decision.
* Every pull must be vintage-stamped; productivity and seasonal revisions alone move the price-equation lag sum by 0.03.

## 7. Limits

* Only the authors' sample (to 2023Q2) was used. Whether GSCPI fits better on the updated sample (the 2024-26
  data contain no comparable supply shock but a new energy spike in 2026Q3 CPI energy) is a Phase 3 question.
* IRFs and decompositions use full-sample coefficients (as the shipped code does). The pre-COVID wage and expectation
  equations were not run through the simulator for this ladder.
* The GSCPI fill (-0.035) before 1997Q4 follows the authors' variant; I have not tested a sample starting 1998.
* Macrobond's own ECI is a different series from the authors' pre-2001 splice, so S1 combines a data change and a
  definition change; I cannot separate them.
