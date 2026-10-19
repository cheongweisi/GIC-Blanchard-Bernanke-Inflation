# Phase 4c: historical parameter stability and impulse-response comparison

Status date: 2026-10-18. Scope: Phase 4c only. No forecasting extension and no Phase 5 work. The production Model B\* coefficients, the Phase 4 scenario/forecast code and every Phase 1-4b file are unchanged
(a SHA-256 manifest of 489 files taken before this phase is re-checked by `tests/test_phase4c.py`; the full suite, 129 tests, passes). All Phase 4c results are in `outputs/phase4c/`.

**Deliverables.** Coefficient-comparison workbook `outputs/phase4c/phase4c_coefficient_comparison.xlsx` (31 sheets; each sheet is also a CSV in the same folder); IRF overlay charts in `outputs/phase4c/figures/`
(one file per shock, plus overviews); table of comparable multipliers (`multipliers_comparable.csv`, §5); this report. Code: `bb_inflation/phase4c/`, `scripts/run_p4c_*.py`, `tests/test_phase4c.py`.

---------------------------------------------------------------------------------------------------

## 1. Executive summary

**Design in one paragraph.** Model B\* (the Phase 3/4 production specification: the authors' four restricted equations, supply chains measured by the 2-quarter mean of the NY Fed GSCPI) is re-estimated with
*everything else held fixed* on three samples: **B\*-2019** (1990Q1-2019Q4), **B\*-2023** (to 2023Q4) and **B\*-2026** (to 2026Q2, identical to production B\*). The authors' own hybrid model (wage and expectations equations
to 2019Q4, price equation to 2023Q2) is kept as a reference. Because the samples are nested, every test of "has this changed?" accounts for their overlap, and uncertainty bands come from joint coefficient draws. A second, independent
check asks whether the observed changes exceed what sampling variation would produce if parameters had been constant throughout.

**Findings.**

1. **Replication.** The authors' wage and both expectations equations are estimated on 1990Q1-2019Q4 (N = 120) and the price equation on a sample including the pandemic (paper: through 2023Q1, N = 133; package: 2023Q2, N = 134). Their
   published IRFs reproduce exactly (max difference 0.0) from the *full-sample* coefficients in their package, **not** from the pre-COVID (hybrid) coefficients the paper text describes; for the V/U IRF the two differ by up to 0.79 pp at some horizons
   (14% at 12 quarters). The paper's V/U numbers (0.7 / 1.0 / +0.15 per year) do not match either coefficient set exactly (shipped: 0.78 / 1.09 / +0.09). Shock sizes in the paper footnote also differ from the shipped data (earlier vintage). (§2)
2. **Most relationships are stable.** Of 16 coefficient blocks, 10 are classified robust (stable across samples, significant, identified pre-2020), 2 are stable but not distinguishable from zero (catch-up and productivity in the wage equation), 1 is identified
   precisely only once post-2019 data are added (CPI to 10-year expectations), and **3 move** (the price equation's split between lagged inflation, wages and energy). Adding 2024Q1-2026Q2 to the 2023 sample changes nothing material: the largest change in any block sum is 0.059 (V/U) and no change is significant. ("Moves" means the 2019-to-2023 or 2019-to-2026 change is unusual for constant parameters in the bootstrap test, p = 0.01 to 0.09; under the overlap-adjusted HAC test alone none would be flagged, p = 0.11 to 0.16.) (§4, §6)
3. **Wage-to-price pass-through is stronger when 2020-2023 is in the sample, but modestly and not conclusively.** The price equation's weight on wages rises from 0.689 to 0.871 (2023) and 0.845 (2026) while the weight on lagged inflation falls correspondingly (0.311 to 0.155): +0.156, p = 0.16 on an overlap-adjusted HAC test,
   p = 0.09 against the constant-parameter bootstrap. The same-quarter coefficient barely moves (0.39 to 0.44, p = 0.47): the change is lower price inertia, not a bigger impact response. A sustained +1pp wage path lifts the price level by 1.69% after three years in B\*-2019 and 2.00% in B\*-2026
   (difference +0.30, p = 0.15); a one-time +1pp wage shock, 0.32% versus 0.43% (p = 0.12). The *first-year* price-level effect is the clearest change: wage impulse 0.20% to 0.26% (p = 0.08), sustained V/U shift 0.32% to 0.57% (p = 0.06), sustained wage path 0.46% to 0.62% (p = 0.11), i.e. faster pass-through. The result is stronger with the GSCPI term than without it (+0.156 vs +0.095, p = 0.37), and the authors' own Google-based full-sample equation does not show it (0.667). (§4.4, §6)
4. **No evidence that wage catch-up has strengthened.** The catch-up sum is -0.024 (B\*-2019), -0.015 (2023) and -0.002 (2026), 95% interval [-0.097, +0.093] in B\*-2026; a post-2019 shift test gives -0.026 (p = 0.75). It is a stable zero, not a weak positive. (§6)
5. **Expectations are not more responsive to price shocks.** The 1-year expectations equation's weight on CPI inflation is 0.125 / 0.138 / 0.136 (p of change 0.59) and the 10-year weight 0.025 / 0.027 / 0.028 (p = 0.80). The 10-year coefficient is *more precisely* estimated
   with the pandemic data (s.e. halves) but is not larger. Anchoring in the authors' sense is intact; the 10-year expectations equation has persistence 0.972-0.975 in every sample. (§6)
6. **Oil: slightly more inflationary, not significantly. Supply chains: if anything smaller.** The relative-energy-price sum is 0.055 / 0.079 / 0.075 (+0.020, p = 0.15 HAC, 0.05 bootstrap). A sustained +10% Brent shock raises the CPI price level by 0.275% (B\*-2019), 0.317% (2023) and 0.315% (2026)
   after three years (difference +0.040, p = 0.34; the oil-to-CPI-energy bridge, a calibrated assumption, is the same in all). Persistence of the response is unchanged (half-life 1-2 quarters). The GSCPI coefficient is 0.359 / 0.308 / 0.288; a one-s.d. GSCPI pulse raises the price level by 0.148% / 0.104% / 0.101% (difference -0.047, p = 0.48). (§5, §6)
7. **Labour-market effects are more persistent than product-market effects, as the authors found, but because the driver is persistent, not because of stronger propagation.** A sustained +0.5 V/U shift keeps raising year-on-year inflation (still 1.37 times its 12-quarter peak at 40 quarters in B\*-2026), whereas a sustained oil level shift fades to
   4% of its peak. A one-quarter V/U impulse fades as fast as a one-quarter GSCPI impulse (half-lives 3 and 2 quarters). A sustained GSCPI level shift behaves like V/U (the equation takes GSCPI in levels), so the contrast holds only for shocks to price *levels* (oil, food) and for impulses. (§5.3)
8. **The pre-2020 sample identifies the supply-chain coefficient statistically but over a narrow range.** B\*-2019 gives 0.359 (HAC s.e. 0.164, t = 2.2), not weakly identified by our rules (s.e. ratio to B\*-2026 1.4), and it survives leaving out any 16-quarter block (range 0.18 to 0.49). But GSCPI ranges only from -1.1 to +0.9 before 2020 (pandemic peak +4.3),
   its pre-2020 variation is small (s.d. 0.35 against 0.82 in the full sample), 8.5% of the identifying variation sits in 1990-97, when GSCPI is a constant fill, and in B\*-2026 the 16 quarters of 2020-23 supply 41% of the information. Applying 0.29-0.36 to pandemic-sized values is extrapolation. (§3.3)
9. **What is robust enough for the forecasting framework** (§6, Q7): the wage-equation structure (lagged wages versus expected inflation, V/U), the food and GSCPI coefficients, the expectations equations and the *price-level* effect of oil on CPI (0.23-0.40% after three years for +10% Brent, bridge held fixed) are robust. Use with a range, not a point: the wage/lagged-inflation split in the price equation
   (wage price-level effect 1.7-2.0% per sustained 1pp) and the energy coefficient. Treat catch-up as zero with an upper bound of about +0.09. B\*-2026 coefficients are an adequate central choice, since adding 2024-26 changes nothing.

**Headline multipliers** (CPI price-level effect after 13 quarters, % ; headline energy/food convention; B\*-2026 with 90% parameter band; full table in §5):

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]   | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:---------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.322 |     0.430 | 0.431 [0.287, 0.658] | 0.375            | +0.109 (p=0.12)         |
| W2: Sustained wage path +1pp (exogenous)     |     1.694 |     1.993 | 1.997 [1.586, 2.297] | 1.962            | +0.303 (p=0.15)         |
| O10: Brent +10% (sustained level shift)      |     0.275 |     0.317 | 0.315 [0.226, 0.398] | 0.343            | +0.040 (p=0.34)         |
| O30: Brent +30% (sustained level shift)      |     0.756 |     0.873 | 0.867 [0.622, 1.096] | 0.945            | +0.111 (p=0.34)         |
| V1: V/U +0.5 (sustained level shift)         |     1.173 |     1.705 | 1.686 [1.166, 2.223] | 1.400            | +0.513 (p=0.12)         |
| V1P: V/U +0.5 (one quarter)                  |     0.111 |     0.165 | 0.157 [0.103, 0.223] | 0.132            | +0.045 (p=0.17)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.148 |     0.104 | 0.101 [0.039, 0.166] | n/a              | -0.047 (p=0.48)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     1.569 |     1.113 | 1.066 [0.422, 1.703] | n/a              | -0.503 (p=0.47)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.249 |     0.253 | 0.251 [0.140, 0.367] | 0.289            | +0.003 (p=0.94)         |
| E10: 10-year expectations +1pp (one quarter) |     0.900 |     0.972 | 0.926 [0.462, 1.308] | 1.054            | +0.026 (p=0.90)         |

**Caveats that matter most.** Bands are parameter uncertainty only. The price-equation findings (3, 6) depend on how supply-chain pressure is measured and on the HAC-versus-bootstrap choice. The wage-shock results depend on whether energy and food prices are held nominal (headline) or relative (authors'); both are reported. Long-horizon statistics for sustained shocks are mechanical consequences of the homogeneity restrictions
(inflation has no unique steady state). (§7)

---------------------------------------------------------------------------------------------------

## 2. Task 1: the authors' model, samples and impulse responses

### 2.1 Specification, identification, samples

Four equations, estimated one at a time by restricted least squares (Stata `cnsreg`; our Python reproduces the shipped coefficients to ~5e-6). Growth rates are 400 x dln (annualised, pp).

| equation | regressors | restriction | identifying assumption |
|---|---|---|---|
| wage `gw` | lags 1-4 of `gw`, `cf1`, V/U, catch-up (`diffcpicf` = 4-quarter CPI inflation less `cf1` four quarters earlier), lag 1 of trend productivity, constant (+ Q2/Q3-2020 dummies in the full sample) | sum of `gw` and `cf1` lags = 1 | wages respond only to lagged information (no contemporaneous terms) |
| price `gcpi` | lags 1-4 of `gcpi`, lags 0-4 of `gw`, relative energy `grpe`, relative food `grpf`, shortage; productivity (lag 0), constant | sum of `gcpi` lags and `gw` lags = 1 | wages, relative prices and shortages are not affected by same-quarter CPI |
| 1y expectations `cf1` | lags 1-4 of `cf1`, lags 0-4 of `cf10` and `gcpi`; no constant | all coefficients sum to 1 | |
| 10y expectations `cf10` | lags 1-4 of `cf10`, lags 0-4 of `gcpi`; no constant | all coefficients sum to 1 | |

Recursive order in simulation: `gw` -> `gcpi` -> catch-up -> `cf10` -> `cf1`. V/U, relative energy and food prices, shortage and productivity are exogenous. Homogeneity makes the long run vertical (a sustained wage or inflation increase is passed on one-for-one) and leaves steady-state inflation
indeterminate. IRF and decomposition exercises set residuals to zero.

**Samples (confirmed from the estimation code and by re-estimation on their data):**

| model                                                        | equation   | sample        |   N | pandemic-era observations used   |
|:-------------------------------------------------------------|:-----------|:--------------|----:|:---------------------------------|
| hybrid (paper baseline)                                      | gw         | 1990Q1-2019Q4 | 120 | no (ends 2019Q4)                 |
| hybrid (paper baseline)                                      | gcpi       | 1990Q1-2023Q2 | 134 | yes (through 2023Q2)             |
| hybrid (paper baseline)                                      | cf1        | 1990Q1-2019Q4 | 120 | no (ends 2019Q4)                 |
| hybrid (paper baseline)                                      | cf10       | 1990Q1-2019Q4 | 120 | no (ends 2019Q4)                 |
| full sample (what the authors' IRF/decomposition code reads) | gw         | 1990Q1-2023Q2 | 134 | yes (through 2023Q2)             |
| full sample (what the authors' IRF/decomposition code reads) | gcpi       | 1990Q1-2023Q2 | 134 | yes (through 2023Q2)             |
| full sample (what the authors' IRF/decomposition code reads) | cf1        | 1990Q1-2023Q2 | 134 | yes (through 2023Q2)             |
| full sample (what the authors' IRF/decomposition code reads) | cf10       | 1990Q1-2023Q2 | 134 | yes (through 2023Q2)             |
| price equation as in the paper's Table 3                     | gcpi       | 1990Q1-2023Q1 | 133 | yes (through 2023Q1)             |

The wage and both expectations equations in the paper's baseline use data through 2019Q4 (N = 120); the price equation uses the pandemic period (paper Table 3: 1990Q1-2023Q1, N = 133; package: 2023Q2, N = 134). The nominal "1989Q1" start is effectively 1990Q1 (lags are lost after the `keep`). The paper's Table 5 note says 2019Q1; the code uses 2019Q4.

### 2.2 The authors' quantitative findings and their interpretation

| channel | authors' estimate (paper tables; hybrid design) | authors' interpretation |
|---|---|---|
| direct wage-to-price | price eq.: sum on wages 0.665 (p<0.001), on lagged inflation 0.335 | fairly rapid pass-through of wages to prices |
| wage catch-up | wage eq.: -0.024 (p = 0.77); with SPF about +0.1, insignificant; full sample small and insignificant | no evidence of catch-up (real-wage rigidity limited) |
| labour market | V/U sum 0.693 (p = 0.03); V/U 1.0 to 1.5 raises long-run wage growth by 0.5 x 0.693/(1-0.460) = 0.64 pp | Phillips curve alive; effect on inflation builds slowly |
| expectations | wage eq.: weight on 1y expectations 0.540 (lagged wages 0.460). `cf1` eq.: CPI weight 0.124 (0.133 in the full sample); `cf10` eq.: CPI weight 0.025 (0.031 full sample) | short-run expectations feed quickly into wages; both expectations series well anchored, no de-anchoring in the pandemic |
| energy / food | energy sum 0.066 (long-run price-level effect 10%, share 7.4%); food 0.126 (19%, share 14.4%) | second-round price effects beyond direct shares |
| supply shortages | shortage sum 0.018 (p = 0.28), joint p<0.001 | strong but temporary effect on the price level |
| IRFs | relative energy, food and shortage shocks: effects mostly gone the quarter after, energy leaves about +0.1 pp; permanent +1 s.d. V/U: about 0.7 pp after 6 quarters, 1.0 after 12, then +0.15 pp per year | price shocks transitory; persistent labour-market tightness produces ever-rising inflation at a low rate |

Published versus shipped coefficient sums (our reproduction matches the shipped files; the price-equation differences in the third decimal come from the 2023Q1 vs 2023Q2 sample and data vintage):

| equation   | block (sum)   |   paper table |   shipped package (their files) |   p(sum) paper |   p(sum) shipped |
|:-----------|:--------------|--------------:|--------------------------------:|---------------:|-----------------:|
| gw         | gw            |         0.460 |                           0.460 |          0.008 |            0.008 |
| gw         | cf1           |         0.540 |                           0.540 |          0.002 |            0.002 |
| gw         | vu            |         0.693 |                           0.693 |          0.030 |            0.030 |
| gw         | diffcpicf     |        -0.024 |                          -0.024 |          0.765 |            0.762 |
| gw         | magpty        |         0.031 |                           0.031 |                |                  |
| gcpi       | gcpi          |         0.335 |                           0.333 |          0.037 |            0.037 |
| gcpi       | gw            |         0.665 |                           0.667 |          0.000 |            0.000 |
| gcpi       | grpe          |         0.066 |                           0.066 |          0.000 |            0.000 |
| gcpi       | grpf          |         0.126 |                           0.126 |          0.050 |            0.049 |
| gcpi       | shortage      |         0.018 |                           0.019 |          0.281 |            0.225 |
| gcpi       | magpty        |        -0.143 |                          -0.144 |                |                  |
| cf1        | cf1           |         0.369 |                           0.369 |          0.014 |            0.014 |
| cf1        | cf10          |         0.506 |                           0.506 |          0.000 |            0.000 |
| cf1        | gcpi          |         0.124 |                           0.124 |          0.001 |            0.001 |
| cf10       | cf10          |         0.975 |                           0.975 |          0.000 |            0.000 |
| cf10       | gcpi          |         0.025 |                           0.025 |          0.208 |            0.208 |

### 2.3 IRF replication and discrepancies

| IRF                             |   size (shipped-data s.d.) |   size in paper |   max abs. diff: our replication (their full-sample coefs) vs shipped file |   max abs. diff: their hybrid coefs vs shipped file |
|:--------------------------------|---------------------------:|----------------:|---------------------------------------------------------------------------:|----------------------------------------------------:|
| Energy (relative price, 1 s.d.) |                    29.0781 |         32.0000 |                                                                     0.0000 |                                              0.0301 |
| Food (relative price, 1 s.d.)   |                     3.8676 |          3.2000 |                                                                     0.0000 |                                              0.0046 |
| Shortage index (1 s.d.)         |                    10.0668 |         11.6000 |                                                                     0.0000 |                                              0.0170 |
| V/U (1 s.d., permanent)         |                     0.5791 |          0.5000 |                                                                     0.0000 |                                              0.7866 |

Reading: **the shipped IRF files reproduce exactly from the full-sample coefficients** (`Output Data (Full Sample)`), as logged in Phase 1 (D2). The paper says the wage and expectations equations are pre-COVID; with those (hybrid) coefficients the energy, food and shortage IRFs differ by at most 0.03 pp, but the V/U IRF differs by up to 0.79 pp
(figure `authors_irf_replication.png`). Other discrepancies, with the paper's own words checked against the numbers:

| claim in paper                                                                                |   paper |   shipped file (= full-sample coefs) |   hybrid coefs, same shock |   hybrid coefs, V/U +0.5 |
|:----------------------------------------------------------------------------------------------|--------:|-------------------------------------:|---------------------------:|-------------------------:|
| V/U IRF: inflation about 0.7 pp after 6 quarters                                              |   0.700 |                                0.781 |                      0.662 |                    0.571 |
| V/U IRF: about 1.0 pp after 12 quarters                                                       |   1.000 |                                1.086 |                      0.937 |                    0.809 |
| V/U IRF: keeps rising about 0.15 pp per year thereafter                                       |   0.150 |                                0.091 |                      0.079 |                    0.068 |
| Energy IRF: effects mostly gone the quarter after the shock (h=1 response relative to impact) |         |                                0.061 |                            |                          |
| Energy IRF: small sustained increase in inflation of about 0.1 pp (h=27)                      |   0.100 |                                0.064 |                      0.065 |                          |

* The paper's V/U figures (0.7 after 6, 1.0 after 12 quarters, +0.15 per year) are closest to the shipped file (0.78, 1.09, +0.09), not to the hybrid coefficients (0.66, 0.94, +0.08 for the same shock; 0.57, 0.81, +0.07 for a +0.5 shock), so the text reflects a different data vintage (Phase 1 D14).
* Shock sizes in footnote 15 (energy 32, food 3.2, shortage 11.6, V/U 0.5) differ from the shipped-data standard deviations (29.1, 3.87, 10.07, 0.579); the shipped IRFs use the latter (D9).
* The paper's derived multipliers are reproduced from published sums: V/U 1.0 to 1.5 gives 0.64 pp; energy 9.9%; food 18.9% (`authors_multipliers.csv`).
* **Comparability in Phase 4c overlays.** The authors' model enters the overlays with its hybrid (paper-baseline) coefficients and the *same* shock definitions and oil bridge as B\*. It is omitted for the GSCPI shocks, because their shortage variable is Google search intensity (a different variable, 5 lags).

---------------------------------------------------------------------------------------------------

## 3. Task 2: re-estimation on three historical samples

### 3.1 What is held fixed

Equation specifications, variable definitions, lag structures, the identification (timing) assumptions and the homogeneity restrictions are those of production B\*. The only things that change are the sample end and, in the wage equation, the presence of the Q2/Q3-2020 dummies (included only when those quarters are in the sample, as in production).
`B26` reproduces production B\* to machine precision (tested). Standard errors are Newey-West HAC (4 lags, small-sample factor); classical errors are in the workbook.

### 3.2 Sample sizes, restrictions, identifiability

| vintage          | equation   | sample        |   N |   free params |   residual df |   cond. no. |   obs. with bridged V/U |   obs. with filled GSCPI |
|:-----------------|:-----------|:--------------|----:|--------------:|--------------:|------------:|------------------------:|-------------------------:|
| B*-2019          | gw         | 1990Q1-2019Q4 | 120 |            17 |           103 |       177.9 |                       0 |                          |
| B*-2019          | gcpi       | 1990Q1-2019Q4 | 120 |            21 |            99 |        29.4 |                       0 |                     31.0 |
| B*-2019          | cf1        | 1990Q1-2019Q4 | 120 |            13 |           107 |       110.3 |                       0 |                          |
| B*-2019          | cf10       | 1990Q1-2019Q4 | 120 |             8 |           112 |        63.7 |                       0 |                          |
| B*-2023          | gw         | 1990Q1-2023Q4 | 136 |            19 |           117 |        86.9 |                       0 |                          |
| B*-2023          | gcpi       | 1990Q1-2023Q4 | 136 |            21 |           115 |        26.3 |                       0 |                     31.0 |
| B*-2023          | cf1        | 1990Q1-2023Q4 | 136 |            13 |           123 |       104.3 |                       0 |                          |
| B*-2023          | cf10       | 1990Q1-2023Q4 | 136 |             8 |           128 |        60.7 |                       0 |                          |
| B*-2026          | gw         | 1990Q1-2026Q2 | 146 |            19 |           127 |        89.6 |                       2 |                          |
| B*-2026          | gcpi       | 1990Q1-2026Q2 | 146 |            21 |           125 |        26.3 |                       0 |                     31.0 |
| B*-2026          | cf1        | 1990Q1-2026Q2 | 146 |            13 |           133 |       106.4 |                       0 |                          |
| B*-2026          | cf10       | 1990Q1-2026Q2 | 146 |             8 |           138 |        59.4 |                       0 |                          |
| Hybrid (B* data) | gw         | 1990Q1-2019Q4 | 120 |            17 |           103 |       177.9 |                       0 |                          |
| Hybrid (B* data) | gcpi       | 1990Q1-2023Q2 | 134 |            21 |           113 |        26.3 |                       0 |                     31.0 |
| Hybrid (B* data) | cf1        | 1990Q1-2019Q4 | 120 |            13 |           107 |       110.3 |                       0 |                          |
| Hybrid (B* data) | cf10       | 1990Q1-2019Q4 | 120 |             8 |           112 |        63.7 |                       0 |                          |

Every design has full column rank, restrictions hold to machine precision, and no quarter inside any window is missing. The condition numbers (unit-norm columns, 26-178) are moderate. Two wage-equation observations in B\*-2026 (2026Q1, 2026Q2) use the bridged V/U for 2025Q4 (interpolated October-2025 unemployment; the provenance
question from the Phase 3 supplement remains open); 31 price-equation observations use the constant-filled GSCPI (1990Q1-1997Q3).

### 3.3 Is the supply-chain coefficient identified before 2020?

Frisch-Waugh-Lovell diagnostics on the price equation (homogeneity substituted out; the FWL standard error equals the classical one to 1e-10, tested):

| vintage   |   N |   estimate |   HAC s.e. |   t (HAC) |   min. detectable (80% power) |   GSCPI min |   GSCPI max |   s.d. of GSCPI in sample |   s.d. of partialled GSCPI |   VIF |   share of ident. variation: 1990-97 (filled) |   1998-2019 |   2020-23 |   2024-26 |
|:----------|----:|-----------:|-----------:|----------:|------------------------------:|------------:|------------:|--------------------------:|---------------------------:|------:|----------------------------------------------:|------------:|----------:|----------:|
| B*-2019   | 120 |       0.36 |       0.16 |      2.19 |                          0.46 |       -1.14 |        0.87 |                      0.35 |                       0.31 |  1.23 |                                          0.09 |        0.91 |      0.00 |      0.00 |
| B*-2023   | 136 |       0.31 |       0.11 |      2.71 |                          0.32 |       -1.32 |        4.28 |                      0.84 |                       0.63 |  1.79 |                                          0.10 |        0.49 |      0.42 |      0.00 |
| B*-2026   | 146 |       0.29 |       0.12 |      2.50 |                          0.32 |       -1.32 |        4.28 |                      0.82 |                       0.62 |  1.74 |                                          0.08 |        0.47 |      0.41 |      0.04 |

* **Statistically identified.** HAC t = 2.2 in B\*-2019; HAC s.e. 0.164 against 0.115 in B\*-2026 (ratio 1.4, below our flag of 2); the detectable effect at 80% power (0.46) is larger than the estimate, so the pre-2020 sample can detect an effect of this size only marginally.
* **Not driven by one episode.** Dropping each 16-quarter window gives 0.18 (dropping 2009-12) to 0.49 (dropping 2005-08), median 0.36; starting in 1998Q1 gives 0.28 (figure `ident_gscpi.png`).
* **But narrow amplitude.** GSCPI stays between -1.1 and +0.9 before 2020 and reaches +4.3 in 2021. The pre-2020 coefficient is identified from fluctuations of a few tenths of a standard deviation (partialled s.d. 0.31), so a linear effect at pandemic magnitudes is an extrapolation.
  In B\*-2023 and B\*-2026 the 16 quarters of 2020-23 supply 41-42% of the identifying variation. 2024-26 supplies 4%.
* **Flag, not a substitution.** No estimate was replaced by a more recent one. The rule-based flags for all blocks are in `ident_blocks.csv` (flag "weak in B\*-2019": |t|<1.65 pre-2020 but significant later, or s.e. ratio >= 2). Only the **10-year-expectations equation's CPI coefficient** is flagged (t = 1.55 in B\*-2019, 3.4 in B\*-2026; s.e. ratio 2.0): its point estimate hardly moves (0.025 to 0.028), its precision does.
* The authors' own Google index was a constant (5) before 2004 and nearly flat before 2020, which is why they estimated the price equation through the pandemic; GSCPI is better behaved pre-2020 but still low-amplitude.

---------------------------------------------------------------------------------------------------

## 4. Task 3: coefficient comparison

Full tables (every coefficient of all four equations, HAC and classical s.e., p-values, 95% intervals): workbook sheets `Coef_*` and `Block_sums`. Entries below are sums of lag coefficients with HAC standard errors in brackets.

### 4.1 Key relationships

| coefficient block                                                 | Authors (published)   | B*-2019        | B*-2023        | B*-2026        |   change 2019->2026 |   p (overlap-adj. HAC) |   p (bootstrap null) | change 2023->2026   | post-2019 shift (p)   |
|:------------------------------------------------------------------|:----------------------|:---------------|:---------------|:---------------|--------------------:|-----------------------:|---------------------:|:--------------------|:----------------------|
| Price eq.: wage growth, direct pass-through (sum L0-4)            | 0.667 (0.143)         | 0.689 (0.118)  | 0.871 (0.170)  | 0.845 (0.163)  |               0.156 |                  0.160 |                0.090 | -0.027 (p=0.34)     | -0.069 (0.65)         |
| Price eq.: lagged CPI inflation (sum L1-4)                        | 0.333 (0.143)         | 0.311 (0.118)  | 0.129 (0.170)  | 0.155 (0.163)  |              -0.156 |                  0.160 |                0.090 | +0.027 (p=0.34)     | n/a                   |
| Price eq.: relative energy-price inflation (sum)                  | 0.066 (0.015)         | 0.055 (0.013)  | 0.079 (0.019)  | 0.075 (0.018)  |               0.020 |                  0.150 |                0.050 | -0.004 (p=0.36)     | +0.035 (0.13)         |
| Price eq.: relative food-price inflation (sum)                    | 0.126 (0.074)         | 0.196 (0.061)  | 0.182 (0.061)  | 0.179 (0.060)  |              -0.017 |                  0.700 |                0.580 | -0.003 (p=0.67)     | -0.156 (0.08)         |
| Price eq.: supply chains (GSCPI 2q mean; authors: Google, 5 lags) | 0.019 (0.016)         | 0.359 (0.164)  | 0.308 (0.114)  | 0.288 (0.115)  |              -0.071 |                  0.700 |                0.690 | -0.020 (p=0.46)     | +0.064 (0.82)         |
| Wage eq.: lagged wage growth (sum L1-4)                           | 0.460 (0.191)         | 0.457 (0.190)  | 0.540 (0.146)  | 0.540 (0.142)  |               0.083 |                  0.330 |                0.230 | -0.000 (p=1.00)     | +0.157 (0.22)         |
| Wage eq.: 1y expected inflation (sum L1-4)                        | 0.540 (0.191)         | 0.543 (0.190)  | 0.460 (0.146)  | 0.460 (0.142)  |              -0.083 |                  0.330 |                0.230 | +0.000 (p=1.00)     | n/a                   |
| Wage eq.: V/U (sum L1-4)                                          | 0.693 (0.256)         | 0.678 (0.257)  | 0.732 (0.229)  | 0.672 (0.210)  |              -0.006 |                  0.960 |                0.970 | -0.059 (p=0.29)     | +0.135 (0.38)         |
| Wage eq.: catch-up (sum L1-4)                                     | -0.024 (0.070)        | -0.024 (0.070) | -0.015 (0.049) | -0.002 (0.048) |               0.022 |                  0.570 |                0.590 | +0.012 (p=0.21)     | -0.026 (0.75)         |
| 1y-expectations eq.: CPI inflation (sum L0-4)                     | 0.124 (0.037)         | 0.125 (0.037)  | 0.138 (0.030)  | 0.136 (0.028)  |               0.011 |                  0.590 |                0.550 | -0.002 (p=0.64)     | +0.014 (0.71)         |
| 10y-expectations eq.: CPI inflation (sum L0-4)                    | 0.025 (0.016)         | 0.025 (0.016)  | 0.027 (0.008)  | 0.028 (0.008)  |               0.003 |                  0.800 |                0.810 | +0.000 (p=0.69)     | +0.003 (0.88)         |

*Columns.* "p (overlap-adj. HAC)": t-test of the 2019 to 2026 change using the stacked HAC covariance of the nested samples (ignoring the overlap would overstate the standard error of the change by a factor of 1.1 to 3, depending on the block). "p (bootstrap null)": share of replications, drawn under *constant* B\*-2026 parameters (1000 recursive-design block-bootstrap replications), in which
the change between the 2019 and 2026 estimators is at least as large as observed. "post-2019 shift": the shift in the block sum from 2020Q1, estimated within the B\*-2026 sample holding the other coefficients fixed (one test per block; 18 tests were run, so two or three p-values below 0.10 are expected by chance).
Authors' column: their published hybrid model on their own data (Google 'shortage', 5 lags for the supply-chain row).

### 4.2 Derived multipliers (model-implied, with 90% bands from joint draws)

| multiplier (model-implied from estimated coefficients)                                                           | B*-2019                | B*-2023                | B*-2026                | change 2019->2026 (p)   |
|:-----------------------------------------------------------------------------------------------------------------|:-----------------------|:-----------------------|:-----------------------|:------------------------|
| Wage->CPI: direct pass-through (price eq., sum of wage coefficients = 1 - lagged-inflation sum)                  | 0.689 [0.500, 0.887]   | 0.871 [0.602, 1.140]   | 0.845 [0.579, 1.101]   | +0.156 (p=0.16)         |
| Wage->CPI: impact coefficient (same-quarter wage growth)                                                         | 0.390 [0.247, 0.533]   | 0.428 [0.262, 0.599]   | 0.436 [0.272, 0.603]   | +0.046 (p=0.47)         |
| Wage->CPI: net wage weight when energy and food are nominal (wage sum - energy sum - food sum)                   | 0.437 [0.276, 0.614]   | 0.610 [0.390, 0.830]   | 0.590 [0.373, 0.801]   | +0.153 (p=0.10)         |
| Energy: long-run price-level elasticity (energy sum / (1 - lagged-inflation sum))                                | 0.081 [0.057, 0.102]   | 0.091 [0.067, 0.113]   | 0.089 [0.066, 0.112]   | +0.009 (p=0.44)         |
| Food: long-run price-level elasticity (food sum / (1 - lagged-inflation sum))                                    | 0.285 [0.145, 0.439]   | 0.209 [0.098, 0.328]   | 0.212 [0.101, 0.331]   | -0.073 (p=0.24)         |
| GSCPI: price-equation coefficient (pp of annualised CPI inflation per GSCPI unit, same quarter / 2-quarter mean) | 0.359 [0.091, 0.637]   | 0.308 [0.126, 0.490]   | 0.288 [0.105, 0.470]   | -0.071 (p=0.67)         |
| V/U: long-run effect on wage growth per unit V/U (V/U sum / (1 - lagged-wage sum))                               | 1.249 [0.629, 2.172]   | 1.590 [0.996, 2.642]   | 1.460 [0.950, 2.280]   | +0.212 (p=0.50)         |
| Expectations -> wages: weight on 1-year expectations (= 1 - lagged-wage sum)                                     | 0.543 [0.230, 0.856]   | 0.460 [0.213, 0.705]   | 0.460 [0.222, 0.697]   | -0.083 (p=0.30)         |
| Catch-up -> wages: sum of catch-up coefficients                                                                  | -0.024 [-0.143, 0.085] | -0.015 [-0.102, 0.064] | -0.002 [-0.087, 0.074] | +0.022 (p=0.58)         |
| CPI -> 1-year expectations: sum of CPI coefficients (same-quarter and four lags)                                 | 0.125 [0.064, 0.190]   | 0.138 [0.088, 0.188]   | 0.136 [0.090, 0.184]   | +0.011 (p=0.64)         |
| CPI -> 10-year expectations: sum of CPI coefficients                                                             | 0.025 [-0.001, 0.051]  | 0.027 [0.014, 0.041]   | 0.028 [0.014, 0.041]   | +0.003 (p=0.81)         |
| 10-year expectations: own-lag persistence (sum)                                                                  | 0.975 [0.949, 1.001]   | 0.973 [0.959, 0.986]   | 0.972 [0.959, 0.986]   | -0.003 (p=0.81)         |

### 4.3 Which relationships are stable, strengthen or weaken

* **Stable:** wage equation (lagged-wage weight 0.46 / 0.54 / 0.54 and expectations weight 0.54 / 0.46 / 0.46: p = 0.33 for the 2019 to 2026 change; V/U 0.68 / 0.73 / 0.67), food (0.196 / 0.182 / 0.179), both expectations equations, 10-year persistence.
* **Strengthen (modestly):** direct wage-to-CPI weight (0.689 to 0.845) with the mirror-image fall in lagged inflation; the energy sum (0.055 to 0.075). Both changes are borderline: p of 0.15-0.16 (HAC) and 0.05-0.09 (bootstrap null). Under HAC they are within sampling noise; the bootstrap, which accounts for the pandemic outliers in the residual draws, calls them unusual.
  We therefore describe them as suggestive, not as a structural break (§6).
* **Weaken:** food in the post-2019 shift test (shift -0.16, p = 0.08 in B\*-2026; -0.20, p = 0.03 in B\*-2023) although the vintage estimates barely move (0.196 to 0.179, p = 0.70): the pandemic years had a smaller food coefficient and the pre-2020 years a larger one, which averages out. One test among 18; treat with care.
* **Unchanged by 2024-26:** B\*-2023 versus B\*-2026 differ by at most 0.059 in any block sum, no change has p < 0.2.

### 4.4 Does the finding depend on how supply chains are measured?

Price-equation wage weight under three treatments of supply-chain pressure (same samples, same overlap-adjusted test):

| shortage specification in the price equation   |   B*-2019 |   B*-2023 |   B*-2026 | change 2019->2026 (s.e.)   |     p |
|:-----------------------------------------------|----------:|----------:|----------:|:---------------------------|------:|
| GSCPI, 2-quarter trailing mean                 |     0.689 |     0.871 |     0.845 | +0.156 (0.109)             | 0.160 |
| GSCPI, 5 lags (benchmark)                      |     0.683 |     0.855 |     0.833 | +0.149 (0.122)             | 0.220 |
| No shortage term                               |     0.652 |     0.758 |     0.747 | +0.095 (0.105)             | 0.370 |

The direction (higher wage weight, lower inertia once 2020 onward is included) is the same in all three but shrinks and loses even marginal significance without the GSCPI term. The authors' published Google-based price equation (to 2023Q2) has a wage weight of 0.667, equal to what B\*-2019 gives, and their own Table A8 with the NY Fed index reports 0.834:
the rise to 0.85 needs a supply-chain term that varies over the pandemic only in part: without any such term, 0.095 of the 0.156 rise remains. The comparison with the Google version cannot be made on a pre-2020 sample (Google is flat there).

### 4.5 Recursive estimates

`coef_recursive_blocks.png` plots each block sum as the sample end moves from 2019Q4 to 2026Q2 (table `stability_recursive.csv`). The movement happens while the pandemic quarters enter, not afterwards:

* price-equation wage weight 0.689 (2019Q4), 0.74 (2020Q3), 0.80 (2021Q2), 0.84 (2022Q1), 0.87 (2023Q4), then 0.87 until 2026Q1; the final quarter lowers it to 0.845. The lagged-inflation weight mirrors it (0.311 to 0.125-0.155);
* energy sum 0.055 to 0.077 by 2022Q1, then flat (0.079 at 2023Q4, 0.075 at 2026Q2);
* wage equation lagged-wage weight 0.457 to 0.595 (2021Q3), back to 0.53-0.54 from 2022Q1;
* the GSCPI coefficient collapses to 0.04 when only 2020Q1-Q2 are added (2020Q2 window; 0.07 in 2021Q1), then recovers to 0.31-0.41 from 2021Q2: a reminder that a few pandemic quarters can dominate a low-variance coefficient, in either direction.

---------------------------------------------------------------------------------------------------

## 5. Task 4: impulse-response comparison

### 5.1 Shocks, units and what is held constant

All responses are deviations from a common baseline over h = 0..12 (h = 0 is the shock quarter; "after quarter k" = response at h = k); the model is linear, so initial conditions and baseline driver paths cancel and cannot differ across vintages. Only the four estimated equations differ.
Units: CPI and wage inflation in annualised pp; expectations in pp; **price level** = cumulative sum of the annualised CPI responses / 4 (%), including the shock quarter. Bands: 90%, joint coefficient draws (2000), overlap preserved. Authors' model: same shocks, point estimates.

| id | shock | type | size |
|---|---|---|---|
| W1 | Wage equation shock +1pp (one quarter) | impulse | 1 pp |
| W2 | Sustained wage path +1pp (exogenous) | sustained | 1 pp |
| O10 | Brent +10% (sustained level shift) | sustained | 10 % |
| O30 | Brent +30% (sustained level shift) | sustained | 30 % |
| O10T | Brent +10% for four quarters, then reverses | episode | 10 % |
| O30T | Brent +30% for four quarters, then reverses | episode | 30 % |
| V1 | V/U +0.5 (sustained level shift) | sustained | 0.5 ratio |
| V1P | V/U +0.5 (one quarter) | impulse | 0.5 ratio |
| G1 | GSCPI +1 s.d. (one quarter) | impulse | 0.969 GSCPI units |
| G1S | GSCPI +1 s.d. (sustained level shift) | sustained | 0.969 GSCPI units |
| E1 | 1-year expectations +1pp (one quarter) | impulse | 1 pp |
| E10 | 10-year expectations +1pp (one quarter) | impulse | 1 pp |
| P1 | CPI price-equation shock +1pp (one quarter) | impulse | 1 pp |

*One-period impulse versus sustained change.* W1, V1P, G1, E1, E10, P1 are one-period impulses (V1P and G1 move the *driver* for one quarter; W1, E1, E10, P1 add a residual to one equation). W2, O10, O30, V1, G1S are sustained: W2 holds wage growth 1pp above baseline every quarter with the wage equation switched off (a different exercise from W1); O10/O30 are permanent
level shifts in Brent from the first month of h = 0 (the +30% shock is 26.2 log points, 2.75 times the +10% one, not 3 times); V1 and G1S are permanent level shifts of V/U and GSCPI. O10T/O30T (four-quarter episodes) and P1 (a CPI-equation shock, for second-round effects) are supplementary (workbook and figures). GSCPI s.d. = 0.969 (1998Q1-2026Q2, common to all vintages); other windows give factors 0.4 to 1.9 (`irf_gscpi_shock_size_reference.csv`), and responses scale linearly.

*Energy and food convention.* Headline ("nominal", the Phase 4 convention): nominal CPI-energy and food growth are exogenous and relative prices are outputs, so a wage shock lowers relative energy and food prices. The authors' convention ("relative") holds relative prices fixed, so energy and food move one-for-one with wages. This matters for every shock that moves wages
(W1, W2, V1, E1, E10); §5.4 reports both. *Oil bridge.* Brent log level to monthly CPI-energy growth with the Phase 4 bridge (elasticity 0.297, s.e. 0.029), identical for all vintages; **a calibrated assumption, not an estimate of this phase** (§5.5).

### 5.2 Comparable multipliers

CPI inflation response (annualised pp), by quarter. B\*-2026 shown with its 90% band; the last column is the 2019 to 2026 change with its p-value from the joint draws.

**After quarter 1**

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]    | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:----------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.203 |     0.233 | 0.252 [0.058, 0.442]  | 0.225            | +0.049 (p=0.55)         |
| W2: Sustained wage path +1pp (exogenous)     |     0.321 |     0.407 | 0.433 [0.262, 0.595]  | 0.363            | +0.112 (p=0.17)         |
| O10: Brent +10% (sustained level shift)      |     0.068 |     0.098 | 0.090 [0.022, 0.156]  | 0.119            | +0.022 (p=0.56)         |
| O30: Brent +30% (sustained level shift)      |     0.188 |     0.271 | 0.249 [0.061, 0.429]  | 0.328            | +0.061 (p=0.56)         |
| V1: V/U +0.5 (sustained level shift)         |     0.239 |     0.526 | 0.537 [0.148, 0.970]  | 0.308            | +0.298 (p=0.13)         |
| V1P: V/U +0.5 (one quarter)                  |     0.239 |     0.526 | 0.537 [0.148, 0.970]  | 0.308            | +0.298 (p=0.13)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.180 |     0.119 | 0.113 [0.044, 0.171]  | n/a              | -0.067 (p=0.40)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.354 |     0.268 | 0.252 [0.094, 0.392]  | n/a              | -0.102 (p=0.52)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.047 |     0.057 | 0.043 [-0.005, 0.110] | 0.056            | -0.004 (p=0.85)         |
| E10: 10-year expectations +1pp (one quarter) |     0.057 |     0.075 | 0.058 [-0.007, 0.155] | 0.067            | +0.002 (p=0.99)         |

**After quarter 4**

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]     | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:-----------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.193 |     0.134 | 0.131 [-0.041, 0.287]  | 0.155            | -0.062 (p=0.41)         |
| W2: Sustained wage path +1pp (exogenous)     |     0.558 |     0.639 | 0.638 [0.482, 0.747]   | 0.644            | +0.080 (p=0.35)         |
| O10: Brent +10% (sustained level shift)      |    -0.027 |    -0.008 | -0.008 [-0.068, 0.046] | 0.027            | +0.019 (p=0.46)         |
| O30: Brent +30% (sustained level shift)      |    -0.075 |    -0.021 | -0.021 [-0.187, 0.128] | 0.075            | +0.054 (p=0.46)         |
| V1: V/U +0.5 (sustained level shift)         |     0.240 |     0.602 | 0.602 [0.196, 1.034]   | 0.438            | +0.362 (p=0.15)         |
| V1P: V/U +0.5 (one quarter)                  |    -0.058 |     0.158 | 0.170 [-0.450, 0.772]  | 0.072            | +0.228 (p=0.50)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.038 |     0.017 | 0.018 [-0.005, 0.041]  | n/a              | -0.019 (p=0.25)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.488 |     0.342 | 0.326 [0.128, 0.510]   | n/a              | -0.161 (p=0.46)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.102 |     0.127 | 0.116 [0.026, 0.198]   | 0.140            | +0.014 (p=0.74)         |
| E10: 10-year expectations +1pp (one quarter) |     0.233 |     0.289 | 0.258 [0.062, 0.446]   | 0.298            | +0.025 (p=0.78)         |

**After quarter 8**

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]     | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:-----------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.054 |     0.094 | 0.094 [0.031, 0.209]   | 0.070            | +0.039 (p=0.17)         |
| W2: Sustained wage path +1pp (exogenous)     |     0.621 |     0.698 | 0.695 [0.569, 0.797]   | 0.708            | +0.074 (p=0.24)         |
| O10: Brent +10% (sustained level shift)      |     0.017 |     0.025 | 0.028 [0.005, 0.051]   | 0.024            | +0.011 (p=0.32)         |
| O30: Brent +30% (sustained level shift)      |     0.046 |     0.069 | 0.077 [0.015, 0.142]   | 0.066            | +0.030 (p=0.32)         |
| V1: V/U +0.5 (sustained level shift)         |     0.460 |     0.520 | 0.507 [0.206, 0.750]   | 0.491            | +0.047 (p=0.80)         |
| V1P: V/U +0.5 (one quarter)                  |     0.147 |    -0.092 | -0.095 [-0.567, 0.228] | 0.009            | -0.242 (p=0.28)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.011 |     0.010 | 0.010 [0.000, 0.024]   | n/a              | -0.001 (p=0.89)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.550 |     0.385 | 0.370 [0.145, 0.596]   | n/a              | -0.180 (p=0.46)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.098 |     0.087 | 0.094 [0.029, 0.153]   | 0.104            | -0.005 (p=0.90)         |
| E10: 10-year expectations +1pp (one quarter) |     0.399 |     0.404 | 0.399 [0.202, 0.555]   | 0.451            | -0.000 (p=0.97)         |

**After quarter 12**

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]    | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:----------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.034 |     0.044 | 0.046 [0.003, 0.132]  | 0.038            | +0.012 (p=0.64)         |
| W2: Sustained wage path +1pp (exogenous)     |     0.634 |     0.699 | 0.698 [0.578, 0.797]  | 0.712            | +0.064 (p=0.30)         |
| O10: Brent +10% (sustained level shift)      |     0.013 |     0.017 | 0.018 [0.005, 0.030]  | 0.020            | +0.005 (p=0.52)         |
| O30: Brent +30% (sustained level shift)      |     0.036 |     0.048 | 0.050 [0.013, 0.084]  | 0.055            | +0.014 (p=0.52)         |
| V1: V/U +0.5 (sustained level shift)         |     0.445 |     0.661 | 0.627 [0.413, 0.890]  | 0.529            | +0.181 (p=0.17)         |
| V1P: V/U +0.5 (one quarter)                  |    -0.013 |     0.049 | 0.044 [-0.049, 0.277] | 0.009            | +0.057 (p=0.39)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.009 |     0.007 | 0.007 [0.001, 0.017]  | n/a              | -0.002 (p=0.70)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.591 |     0.415 | 0.403 [0.156, 0.663]  | n/a              | -0.188 (p=0.48)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.057 |     0.055 | 0.059 [0.027, 0.105]  | 0.063            | +0.002 (p=0.79)         |
| E10: 10-year expectations +1pp (one quarter) |     0.420 |     0.446 | 0.430 [0.258, 0.562]  | 0.485            | +0.011 (p=0.85)         |

**Peak response within 12 quarters (CPI inflation, pp) and its timing**

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]   | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:---------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.203 |     0.248 | 0.252 [0.232, 0.466] | 0.225            | +0.049 (p=0.20)         |
| W2: Sustained wage path +1pp (exogenous)     |     0.634 |     0.701 | 0.699 [0.589, 0.839] | 0.712            | +0.065 (p=0.24)         |
| O10: Brent +10% (sustained level shift)      |     0.957 |     0.971 | 0.968 [0.886, 1.051] | 0.975            | +0.011 (p=0.68)         |
| O30: Brent +30% (sustained level shift)      |     2.635 |     2.674 | 2.666 [2.439, 2.892] | 2.685            | +0.030 (p=0.68)         |
| V1: V/U +0.5 (sustained level shift)         |     0.506 |     0.670 | 0.720 [0.590, 1.255] | 0.583            | +0.213 (p=0.31)         |
| V1P: V/U +0.5 (one quarter)                  |     0.267 |     0.526 | 0.537 [0.364, 1.095] | 0.308            | +0.270 (p=0.40)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.180 |     0.149 | 0.139 [0.051, 0.228] | n/a              | -0.041 (p=0.62)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.591 |     0.415 | 0.403 [0.156, 0.663] | n/a              | -0.188 (p=0.48)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.123 |     0.127 | 0.116 [0.084, 0.213] | 0.140            | -0.008 (p=0.78)         |
| E10: 10-year expectations +1pp (one quarter) |     0.420 |     0.446 | 0.433 [0.278, 0.605] | 0.485            | +0.012 (p=0.77)         |

Quarter of peak (point estimates):

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]   | Authors' model   |
|:---------------------------------------------|----------:|----------:|:---------------------|:-----------------|
| W1: Wage equation shock +1pp (one quarter)   |         1 |         3 | 1 [0, 4]             | 1                |
| W2: Sustained wage path +1pp (exogenous)     |        12 |        11 | 11 [3, 12]           | 12               |
| O10: Brent +10% (sustained level shift)      |         0 |         0 | 0 [0, 0]             | 0                |
| O30: Brent +30% (sustained level shift)      |         0 |         0 | 0 [0, 0]             | 0                |
| V1: V/U +0.5 (sustained level shift)         |         5 |         2 | 2 [1, 12]            | 2                |
| V1P: V/U +0.5 (one quarter)                  |         5 |         1 | 1 [1, 5]             | 1                |
| G1: GSCPI +1 s.d. (one quarter)              |         1 |         0 | 0 [0, 0]             | n/a              |
| G1S: GSCPI +1 s.d. (sustained level shift)   |        12 |        12 | 12 [12, 12]          | n/a              |
| E1: 1-year expectations +1pp (one quarter)   |         5 |         4 | 4 [2, 8]             | 4                |
| E10: 10-year expectations +1pp (one quarter) |        11 |        12 | 10 [7, 12]           | 12               |

**Cumulative CPI price-level change (%)**

After 4 quarters:

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]   | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:---------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.196 |     0.258 | 0.260 [0.184, 0.340] | 0.230            | +0.064 (p=0.08)         |
| W2: Sustained wage path +1pp (exogenous)     |     0.460 |     0.606 | 0.616 [0.439, 0.765] | 0.555            | +0.156 (p=0.11)         |
| O10: Brent +10% (sustained level shift)      |     0.249 |     0.275 | 0.271 [0.211, 0.325] | 0.296            | +0.022 (p=0.45)         |
| O30: Brent +30% (sustained level shift)      |     0.686 |     0.758 | 0.746 [0.581, 0.895] | 0.814            | +0.060 (p=0.45)         |
| V1: V/U +0.5 (sustained level shift)         |     0.318 |     0.560 | 0.573 [0.350, 0.795] | 0.424            | +0.254 (p=0.06)         |
| V1P: V/U +0.5 (one quarter)                  |     0.060 |     0.150 | 0.151 [0.049, 0.259] | 0.109            | +0.091 (p=0.15)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.122 |     0.086 | 0.082 [0.032, 0.127] | n/a              | -0.040 (p=0.46)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.463 |     0.338 | 0.320 [0.124, 0.497] | n/a              | -0.143 (p=0.48)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.076 |     0.087 | 0.078 [0.019, 0.134] | 0.094            | +0.002 (p=0.98)         |
| E10: 10-year expectations +1pp (one quarter) |     0.142 |     0.168 | 0.149 [0.031, 0.272] | 0.171            | +0.007 (p=0.92)         |

After 13 quarters (h = 0..12):

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]   | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:---------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.322 |     0.430 | 0.431 [0.287, 0.658] | 0.375            | +0.109 (p=0.12)         |
| W2: Sustained wage path +1pp (exogenous)     |     1.694 |     1.993 | 1.997 [1.586, 2.297] | 1.962            | +0.303 (p=0.15)         |
| O10: Brent +10% (sustained level shift)      |     0.275 |     0.317 | 0.315 [0.226, 0.398] | 0.343            | +0.040 (p=0.34)         |
| O30: Brent +30% (sustained level shift)      |     0.756 |     0.873 | 0.867 [0.622, 1.096] | 0.945            | +0.111 (p=0.34)         |
| V1: V/U +0.5 (sustained level shift)         |     1.173 |     1.705 | 1.686 [1.166, 2.223] | 1.400            | +0.513 (p=0.12)         |
| V1P: V/U +0.5 (one quarter)                  |     0.111 |     0.165 | 0.157 [0.103, 0.223] | 0.132            | +0.045 (p=0.17)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.148 |     0.104 | 0.101 [0.039, 0.166] | n/a              | -0.047 (p=0.48)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     1.569 |     1.113 | 1.066 [0.422, 1.703] | n/a              | -0.503 (p=0.47)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.249 |     0.253 | 0.251 [0.140, 0.367] | 0.289            | +0.003 (p=0.94)         |
| E10: 10-year expectations +1pp (one quarter) |     0.900 |     0.972 | 0.926 [0.462, 1.308] | 1.054            | +0.026 (p=0.90)         |

**Wage inflation after quarter 12 (pp)**

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]    | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:----------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.036 |     0.053 | 0.056 [0.024, 0.163]  | 0.041            | +0.020 (p=0.34)         |
| W2: Sustained wage path +1pp (exogenous)     |     1.000 |     1.000 | 1.000 [1.000, 1.000]  | 1.000            | +0.000 (p=1.00)         |
| O10: Brent +10% (sustained level shift)      |     0.019 |     0.025 | 0.026 [0.012, 0.039]  | 0.026            | +0.006 (p=0.55)         |
| O30: Brent +30% (sustained level shift)      |     0.053 |     0.068 | 0.070 [0.033, 0.106]  | 0.070            | +0.018 (p=0.55)         |
| V1: V/U +0.5 (sustained level shift)         |     0.741 |     0.962 | 0.911 [0.654, 1.207]  | 0.782            | +0.170 (p=0.35)         |
| V1P: V/U +0.5 (one quarter)                  |     0.010 |     0.024 | 0.024 [-0.024, 0.087] | 0.012            | +0.014 (p=0.71)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.012 |     0.009 | 0.009 [0.002, 0.016]  | n/a              | -0.003 (p=0.66)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.167 |     0.119 | 0.119 [0.021, 0.223]  | n/a              | -0.048 (p=0.63)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.062 |     0.062 | 0.066 [0.028, 0.123]  | 0.068            | +0.004 (p=0.84)         |
| E10: 10-year expectations +1pp (one quarter) |     0.664 |     0.633 | 0.611 [0.415, 0.749]  | 0.681            | -0.053 (p=0.43)         |

**1-year expected inflation after quarter 12 (pp)**

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]    | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:----------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.027 |     0.038 | 0.039 [0.020, 0.079]  | 0.031            | +0.012 (p=0.31)         |
| W2: Sustained wage path +1pp (exogenous)     |     0.243 |     0.286 | 0.289 [0.219, 0.359]  | 0.278            | +0.046 (p=0.39)         |
| O10: Brent +10% (sustained level shift)      |     0.016 |     0.020 | 0.020 [0.009, 0.032]  | 0.022            | +0.004 (p=0.58)         |
| O30: Brent +30% (sustained level shift)      |     0.045 |     0.055 | 0.055 [0.025, 0.087]  | 0.060            | +0.010 (p=0.58)         |
| V1: V/U +0.5 (sustained level shift)         |     0.170 |     0.251 | 0.246 [0.159, 0.353]  | 0.200            | +0.076 (p=0.20)         |
| V1P: V/U +0.5 (one quarter)                  |     0.009 |     0.012 | 0.010 [-0.005, 0.029] | 0.008            | +0.001 (p=0.85)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.010 |     0.007 | 0.007 [0.002, 0.014]  | n/a              | -0.003 (p=0.76)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.224 |     0.164 | 0.160 [0.061, 0.273]  | n/a              | -0.064 (p=0.58)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.041 |     0.041 | 0.044 [0.017, 0.087]  | 0.045            | +0.003 (p=1.00)         |
| E10: 10-year expectations +1pp (one quarter) |     0.635 |     0.627 | 0.614 [0.505, 0.736]  | 0.658            | -0.021 (p=0.66)         |

**10-year expected inflation after quarter 12 (pp)**

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]   | Authors' model   | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:---------------------|:-----------------|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.022 |     0.031 | 0.031 [0.016, 0.057] | 0.026            | +0.009 (p=0.38)         |
| W2: Sustained wage path +1pp (exogenous)     |     0.133 |     0.165 | 0.165 [0.104, 0.224] | 0.153            | +0.032 (p=0.48)         |
| O10: Brent +10% (sustained level shift)      |     0.017 |     0.021 | 0.021 [0.011, 0.032] | 0.022            | +0.004 (p=0.59)         |
| O30: Brent +30% (sustained level shift)      |     0.047 |     0.058 | 0.058 [0.029, 0.088] | 0.060            | +0.010 (p=0.59)         |
| V1: V/U +0.5 (sustained level shift)         |     0.092 |     0.142 | 0.139 [0.082, 0.211] | 0.110            | +0.047 (p=0.25)         |
| V1P: V/U +0.5 (one quarter)                  |     0.008 |     0.011 | 0.011 [0.004, 0.020] | 0.008            | +0.003 (p=0.50)         |
| G1: GSCPI +1 s.d. (one quarter)              |     0.010 |     0.007 | 0.007 [0.002, 0.013] | n/a              | -0.003 (p=0.77)         |
| G1S: GSCPI +1 s.d. (sustained level shift)   |     0.123 |     0.093 | 0.089 [0.030, 0.154] | n/a              | -0.034 (p=0.71)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.018 |     0.020 | 0.020 [0.009, 0.032] | 0.021            | +0.001 (p=0.81)         |
| E10: 10-year expectations +1pp (one quarter) |     0.694 |     0.672 | 0.661 [0.563, 0.780] | 0.707            | -0.034 (p=0.48)         |

Charts: `figures/irf_<shock>_nominal.png` (2x2: CPI inflation, wage inflation, 1y and 10y expectations, all four vintages and the authors' model with 90% bands); `overview_cpi_inflation.png`, `overview_cpi_price_level.png`; `_relative.png` variants for the wage, V/U, expectations and price shocks.

### 5.3 Persistence: labour-market versus product-market shocks

Year-on-year CPI response (4-quarter mean of the annualised response), horizon 40 quarters. "n/r": half-life not reached within 40 quarters. Each cell: B\*-2019 / B\*-2026.

| shock                                        | type      | peak y/y, pp (2019 / 2026)   | y/y at h=12, % of peak (2019 / 2026)   | y/y at h=40, % of peak (2019 / 2026)   | half-life (q) (2019 / 2026)   |
|:---------------------------------------------|:----------|:-----------------------------|:---------------------------------------|:---------------------------------------|:------------------------------|
| W1: Wage equation shock +1pp (one quarter)   | impulse   | 0.16 / 0.23                  | 27 / 26                                | 7 / 8                                  | 5 / 5                         |
| V1P: V/U +0.5 (one quarter)                  | impulse   | 0.12 / 0.18                  | -3 / 17                                | 3 / 3                                  | 2 / 3                         |
| G1: GSCPI +1 s.d. (one quarter)              | impulse   | 0.11 / 0.08                  | 9 / 11                                 | 4 / 5                                  | 2 / 2                         |
| E1: 1-year expectations +1pp (one quarter)   | impulse   | 0.10 / 0.11                  | 65 / 64                                | 10 / 12                                | 7 / 7                         |
| E10: 10-year expectations +1pp (one quarter) | impulse   | 0.41 / 0.42                  | 100 / 100                              | 85 / 88                                | n/r / n/r                     |
| V1: V/U +0.5 (sustained level shift)         | sustained | 0.44 / 0.60                  | 99 / 100                               | 134 / 137                              | n/r / n/r                     |
| G1S: GSCPI +1 s.d. (sustained level shift)   | sustained | 0.58 / 0.39                  | 100 / 100                              | 129 / 135                              | n/r / n/r                     |
| O10: Brent +10% (sustained level shift)      | sustained | 0.26 / 0.27                  | 5 / 8                                  | 3 / 4                                  | 2 / 1                         |
| W2: Sustained wage path +1pp (exogenous)     | sustained | 0.63 / 0.70                  | 100 / 100                              | 101 / 100                              | n/r / n/r                     |

(`persistence_impulses.png`; bands in `irf_persistence_yoy.csv`.) One-period impulses to V/U, GSCPI, wages and the CPI equation all die out within about two to six quarters (half-lives 2-3 for V1P and G1, 5-6 for W1, 7 for E1); a 10-year expectations impulse does not (88% of peak left after 40 quarters). Sustained shocks to V/U and GSCPI keep raising inflation; a sustained oil level shift does not, because the energy price enters the equation as a growth rate.

### 5.4 Wage and V/U shocks under the authors' (relative-price) convention

CPI price level after 13 quarters, relative convention:

| shock                                        |   B*-2019 |   B*-2023 | B*-2026 [90% band]   |   Authors' model | change 2019->2026 (p)   |
|:---------------------------------------------|----------:|----------:|:---------------------|-----------------:|:------------------------|
| W1: Wage equation shock +1pp (one quarter)   |     0.556 |     0.661 | 0.665 [0.485, 0.958] |            0.566 | +0.109 (p=0.22)         |
| W2: Sustained wage path +1pp (exogenous)     |     2.760 |     2.880 | 2.890 [2.651, 3.043] |            2.808 | +0.130 (p=0.21)         |
| V1: V/U +0.5 (sustained level shift)         |     2.021 |     2.587 | 2.564 [1.952, 3.230] |            2.099 | +0.543 (p=0.23)         |
| V1P: V/U +0.5 (one quarter)                  |     0.196 |     0.250 | 0.240 [0.173, 0.309] |            0.202 | +0.044 (p=0.36)         |
| E1: 1-year expectations +1pp (one quarter)   |     0.424 |     0.382 | 0.381 [0.214, 0.546] |            0.429 | -0.043 (p=0.42)         |
| E10: 10-year expectations +1pp (one quarter) |     1.546 |     1.465 | 1.397 [0.730, 1.917] |            1.572 | -0.149 (p=0.40)         |

and CPI inflation after quarter 4:

| shock                                    |   B*-2019 |   B*-2023 | B*-2026 [90% band]   |   Authors' model | change 2019->2026 (p)   |
|:-----------------------------------------|----------:|----------:|:---------------------|-----------------:|:------------------------|
| W2: Sustained wage path +1pp (exogenous) |     0.887 |     0.935 | 0.935 [0.810, 1.024] |            0.906 | +0.048 (p=0.36)         |
| V1: V/U +0.5 (sustained level shift)     |     0.606 |     0.799 | 0.796 [0.360, 1.222] |            0.685 | +0.189 (p=0.51)         |

Holding relative prices fixed raises every wage-driven response (energy and food move with wages) and delivers the one-for-one long-run pass-through (W2 at 12 quarters: 0.999 in every vintage); under the headline convention W2 converges to 0.70 (the net wage weight 0.59 over 1 - 0.155), not 1.

### 5.5 Oil bridge sensitivity (calibrated assumption)

| vintage   | bridge                                              |   bridge elasticity (sum of lags) |   CPI inflation h=0 (pp) |   price level after 4q (%) |   price level after 12q (%) |   price level per 1% of energy-price rise, 12q |
|:----------|:----------------------------------------------------|----------------------------------:|-------------------------:|---------------------------:|----------------------------:|-----------------------------------------------:|
| B*-2019   | common Phase 4 bridge (to 2026-06)                  |                             0.297 |                    0.957 |                      0.249 |                       0.275 |                                          0.097 |
| B*-2019   | bridge re-estimated to 2019-12                      |                             0.298 |                    0.969 |                      0.250 |                       0.276 |                                          0.097 |
| B*-2019   | calibrated elasticity 0.24 (Phase 4 standard range) |                             0.240 |                    0.774 |                      0.201 |                       0.222 |                                          0.097 |
| B*-2019   | calibrated elasticity 0.40 (Phase 4 standard range) |                             0.400 |                    1.290 |                      0.336 |                       0.370 |                                          0.097 |
| B*-2023   | common Phase 4 bridge (to 2026-06)                  |                             0.297 |                    0.971 |                      0.275 |                       0.317 |                                          0.112 |
| B*-2023   | bridge re-estimated to 2023-12                      |                             0.298 |                    0.960 |                      0.276 |                       0.318 |                                          0.112 |
| B*-2023   | calibrated elasticity 0.24 (Phase 4 standard range) |                             0.240 |                    0.785 |                      0.223 |                       0.256 |                                          0.112 |
| B*-2023   | calibrated elasticity 0.40 (Phase 4 standard range) |                             0.400 |                    1.309 |                      0.371 |                       0.427 |                                          0.112 |
| B*-2026   | common Phase 4 bridge (to 2026-06)                  |                             0.297 |                    0.968 |                      0.271 |                       0.315 |                                          0.111 |
| B*-2026   | bridge re-estimated to 2026-06                      |                             0.297 |                    0.968 |                      0.271 |                       0.315 |                                          0.111 |
| B*-2026   | calibrated elasticity 0.24 (Phase 4 standard range) |                             0.240 |                    0.783 |                      0.219 |                       0.255 |                                          0.111 |
| B*-2026   | calibrated elasticity 0.40 (Phase 4 standard range) |                             0.400 |                    1.305 |                      0.365 |                       0.424 |                                          0.111 |

Re-estimating the bridge through each vintage's own end date leaves the elasticity at 0.297-0.298, so the oil results are not a bridge artefact. Scaling the bridge to the 0.24-0.40 range scales the price-level effect of +10% Brent after 12 quarters in B\*-2026 from 0.255% to 0.424%, far wider than the 2019 to 2026 difference in the four estimated equations (0.275% to 0.315%).
The long-run price-level effect per 1% of CPI-energy price rise is 0.097 (B\*-2019) and 0.111 (B\*-2026).

---------------------------------------------------------------------------------------------------

## 6. Task 5: economic interpretation

Three kinds of statement are kept apart: **estimated** (coefficient sums, p-values: §4), **model-implied** (IRFs, long-run elasticities, price-level effects: §4.2, §5) and **calibrated/assumed** (homogeneity restrictions, shock sizes, the oil bridge, the energy/food convention, the GSCPI standard deviation, bridged V/U 2025Q4).

**Q1. Is wage-to-price pass-through stronger when 2020-2023 is included?** Directionally yes, modestly. Estimated: the wage weight in the price equation 0.689 (s.e. 0.118) to 0.871 (0.170) to 0.845 (0.163); lagged-inflation weight 0.311 to 0.155. Model-implied: a sustained +1pp wage path reaches 0.56 / 0.64 / 0.64pp of CPI inflation after four quarters
and 1.69% / 2.00% / 2.00% on the price level after three years (B\*-2019 / 2023 / 2026); long-run pass-through is one by construction. Evidence: p = 0.16 (overlap-adjusted HAC) and 0.09 (bootstrap null) for the coefficient; the first-year price-level effect of a wage impulse rises from 0.20% to 0.26% (p = 0.08) and of a sustained wage path from 0.46% to 0.62% (p = 0.11), so the speed of pass-through is the best-supported change; it shrinks without the GSCPI term (§4.4). The mechanism is lower price inertia, not a larger impact coefficient (0.39 to 0.44, p = 0.47). "Stronger" is
therefore a statement about what the 2020-23 data pulled the estimate towards, not a demonstrated structural change.

**Q2. Has wage catch-up strengthened?** No. Catch-up is -0.024 / -0.015 / -0.002 (s.e. 0.070 / 0.049 / 0.048), the post-2019 shift is -0.026 (p = 0.75), and the upper bound of the B\*-2026 95% interval is +0.092. Consistent with the authors (no catch-up) and Phase 4b (five definitions, four samples). What changed in the wage equation, weakly, is the weight on own lagged wages versus expected
inflation (0.457 to 0.540, p = 0.33), i.e. wages are a little more backward-looking, and the long-run V/U effect per unit (1.25 to 1.46, p = 0.5). Neither is significant.

**Q3. Are inflation expectations more responsive to price shocks?** No. CPI weights 0.125 / 0.138 / 0.136 (1-year) and 0.025 / 0.027 / 0.028 (10-year), changes insignificant. In the IRFs, a +10% oil shock moves 1-year expectations by 0.011 / 0.017 / 0.015 pp after four quarters and a CPI-equation shock by 0.054 / 0.039 / 0.040 pp: no increase. A sustained wage path lifts 10-year expectations by 0.133 / 0.165 / 0.165 pp after 12
quarters (p = 0.48). The pandemic data tightened the 10-year coefficient (s.e. 0.016 to 0.008) without raising it: there is no de-anchoring signal in this model.

**Q4. Have oil and supply-chain shocks become more inflationary or persistent?** Oil: slightly more inflationary (energy sum +0.020; +10% Brent price level 0.275% to 0.315%), not statistically distinguishable (p = 0.15-0.34), not more persistent (half-life 1-2 quarters; CPI response 5-8% of peak after 12 quarters). Supply chains: coefficient 0.359 to 0.288 and a one-s.d.
pulse's price-level effect 0.148% to 0.101% (p = 0.48): not more inflationary; the B\*-2019 value rests on narrow-amplitude pre-2020 variation (§3.3). A sustained GSCPI shift gives larger but much less precise effects (price level after three years 1.57% / 1.11% / 1.07%).

**Q5. Are labour-market shocks more persistent than product-market shocks (the authors' finding)?** Yes in the authors' sense, with a qualification (§5.3). Sustained V/U tightness has an ever-rising effect (year-on-year response 137% of its 12-quarter peak after 40 quarters) while sustained oil or one-off food/energy price shocks fade; impulses to V/U, GSCPI, wages and prices are similarly short-lived. The persistence
of the labour-market channel comes from persistence of V/U itself plus expectations feedback (the 10-year expectations impulse is the most persistent shock in the model), not from larger propagation of a given shock. The conclusion is the same in all three samples.

**Q6. Does 2024-2026 data materially alter these findings?** No. B\*-2023 versus B\*-2026: largest block-sum change 0.059 (V/U, p = 0.29), IRF differences in the price-level effect 0.00-0.05 pp (p >= 0.28 for every shock). The GSCPI coefficient moves 0.308 to 0.288, the wage weight 0.871 to 0.845. Ten quarters of a 146-quarter nested
sample, 4% of the GSCPI identifying variation, and little new variation in wages or energy explain why.

**Q7. Which coefficients and multipliers are robust enough for the forecasting framework?**

| coefficient block                                     |   sum B*-2019 |   sum B*-2023 |   sum B*-2026 |   min p (HAC) |   min p (bootstrap) | classification                                                |
|:------------------------------------------------------|--------------:|--------------:|--------------:|--------------:|--------------------:|:--------------------------------------------------------------|
| Wage eq: lagged wage growth (L1-4)                    |         0.457 |         0.540 |         0.540 |         0.304 |               0.162 | Robust: stable, significant, identified pre-2020              |
| Wage eq: 1-year expected inflation (L1-4)             |         0.543 |         0.460 |         0.460 |         0.304 |               0.162 | Robust: stable, significant, identified pre-2020              |
| Wage eq: V/U (L1-4)                                   |         0.678 |         0.732 |         0.672 |         0.680 |               0.760 | Robust: stable, significant, identified pre-2020              |
| Wage eq: catch-up from unanticipated inflation (L1-4) |        -0.024 |        -0.015 |        -0.002 |         0.572 |               0.595 | Stable, but not distinguishable from zero                     |
| Wage eq: trend productivity growth (L1)               |         0.034 |         0.048 |         0.047 |         0.427 |               0.516 | Stable, but not distinguishable from zero                     |
| Price eq: lagged CPI inflation (L1-4)                 |         0.311 |         0.129 |         0.155 |         0.113 |               0.036 | Moves across samples (change unusual for constant parameters) |
| Price eq: wage growth (L0-4), direct wage-to-CPI      |         0.689 |         0.871 |         0.845 |         0.113 |               0.036 | Moves across samples (change unusual for constant parameters) |
| Price eq: relative energy-price inflation (L0-4)      |         0.055 |         0.079 |         0.075 |         0.109 |               0.013 | Moves across samples (change unusual for constant parameters) |
| Price eq: relative food-price inflation (L0-4)        |         0.196 |         0.182 |         0.179 |         0.700 |               0.584 | Robust: stable, significant, identified pre-2020              |
| Price eq: GSCPI, 2-quarter mean (L0)                  |         0.359 |         0.308 |         0.288 |         0.701 |               0.695 | Robust: stable, significant, identified pre-2020              |
| Price eq: trend productivity growth (L0)              |        -0.116 |        -0.136 |        -0.133 |         0.638 |               0.535 | Robust: stable, significant, identified pre-2020              |
| 1y-expectations eq: own lags (L1-4)                   |         0.369 |         0.295 |         0.322 |         0.344 |               0.177 | Robust: stable, significant, identified pre-2020              |
| 1y-expectations eq: 10-year expectations (L0-4)       |         0.506 |         0.567 |         0.542 |         0.420 |               0.277 | Robust: stable, significant, identified pre-2020              |
| 1y-expectations eq: CPI inflation (L0-4)              |         0.125 |         0.138 |         0.136 |         0.525 |               0.440 | Robust: stable, significant, identified pre-2020              |
| 10y-expectations eq: own lags (L1-4)                  |         0.975 |         0.973 |         0.972 |         0.802 |               0.811 | Robust: stable, significant, identified pre-2020              |
| 10y-expectations eq: CPI inflation (L0-4)             |         0.025 |         0.027 |         0.028 |         0.802 |               0.811 | Identified precisely only once post-2019 data are added       |

*The GSCPI row is "robust" in the statistical sense only; the amplitude caveat of §3.3 applies.* (Classification rules: "moves" if the overlap-adjusted or bootstrap p for 2019 to 2023 or 2019 to 2026 is below 0.10; "stable but not distinguishable from zero" if |t|<1.96 in B\*-2026; "identified only once post-2019 data are added" if the pre-2020 t is below 1.65 and B\*-2026's above 1.96 or the s.e. ratio is at least 2.)
For IRF statistics (`robustness_multipliers.csv`; 70 shock x statistic pairs): 51 are robust (90% band excludes zero, no change with p<0.2), 8 are stable but their band includes zero (mostly short-horizon and impulse responses), 9 show a suggestive, inconclusive difference (0.10<=p<0.20: price-level effects of wage and V/U shocks, the 4- and 12-quarter response to sustained V/U) and 2 move at p<0.10: W1 price level, cumulative to h=4 (%) (p=0.08); V1 price level, cumulative to h=4 (%) (p=0.06). The first-year price-level effect of wage and V/U shocks is larger when 2020-23 is in the sample. **Recommendation:** B\*-2026 for the central case; carry the 2019-to-2026 range as a sensitivity on the wage-price transmission (price level 1.7-2.0% per sustained 1pp wages; V/U +0.5 sustained: 1.2-1.7% after three years) and on the energy coefficient; keep catch-up at zero with an upper bound near +0.09; treat GSCPI effects at pandemic magnitudes as extrapolated.

*Sample instability is not evidence of a structural break.* A break would show up as a shift concentrated at 2020Q1 that the other coefficients cannot absorb. The partial shift tests find none for the wage-to-price weight (-0.07 / -0.07, p = 0.65-0.69) even though the estimate rose between B\*-2019 and B\*-2023: the movement comes from re-weighting across correlated coefficients (lagged inflation, wages, energy,
food, GSCPI) when 16 pandemic quarters with extreme energy, food and GSCPI readings enter a 120-quarter sample. The equations are not stable to the sample, but the data do not reject constant parameters either.

---------------------------------------------------------------------------------------------------

## 7. Methodological limitations

1. **Parameter uncertainty only.** Bands exclude specification uncertainty, residual shocks, uncertainty in the calibrated oil bridge, and uncertainty about future driver paths. Equations are drawn independently (cross-equation covariance is not estimated).
2. **Inference in small samples.** 120-146 quarterly observations, 14-22 coefficients, HAC with 4 lags. The stacked (overlap-adjusted) covariance is first-order asymptotic. HAC and the constant-parameter bootstrap disagree for the price equation (p = 0.16 versus 0.09 for the wage weight); we report both and do not choose. The bootstrap's DGP is B\*-2026 with its pandemic residuals reshuffled across the whole sample, which is conservative for pre-2020 variation.
3. **Linearity and homogeneity.** The restrictions are imposed, not tested; they imply no unique steady state, so statistics at h = 40 for sustained shocks are mechanical and the 12-quarter horizon is the one to quote. Linear effects at pandemic magnitudes (GSCPI +4, energy +40% a quarter) are extrapolated from fewer, smaller observations.
4. **Identification of the supply-chain term** rests on GSCPI, a revised, estimated index; 31 sample quarters use a constant fill. The authors' Google variable is not comparable, so no published benchmark exists for that coefficient, and results on the wage weight depend on the supply-chain specification (§4.4).
5. **Overlapping samples.** B\*-2023 versus B\*-2026 comparisons are weak tests of "recent change" because ten of 146 quarters differ; their near-identity is partly mechanical.
6. **Post-2019 shift tests** use a break date chosen ex post, one block at a time, with 18 tests; they diagnose, not prove.
7. **Conventions matter.** Wage-driven responses differ between the nominal (headline) and relative-price (authors') treatment of energy and food; the authors' published IRFs use full-sample, not hybrid, coefficients; the oil bridge, the +10/+30% sizes and the GSCPI standard deviation (window-dependent; factor 0.4-1.9) are assumptions.
8. **Data.** Pinned pulls (CPI, ECI, productivity, JOLTS, Cleveland Fed, GSCPI as of 2026-10); authors' V/U and ECI history before 2001; V/U 2025Q4 bridged (two wage-equation observations); revisions to GSCPI and productivity are not modelled.
9. **Not done by design:** no new forecasts, no change to production B\*, no Phase 5 work, no change to the catch-up overlay or the oil elasticity decided in Phase 4b.

---------------------------------------------------------------------------------------------------

## 8. Files

| file (outputs/phase4c/) | content |
|---|---|
| `phase4c_coefficient_comparison.xlsx` | workbook, 31 sheets (README first) |
| `blocks.csv`, `coef_<eq>.csv`, `est_checks.csv` | block sums, every coefficient, sample checks |
| `block_changes.csv`, `block_changes_null_bootstrap.csv`, `stability_*.csv` | overlap-adjusted tests, stable-parameter bootstrap, shift tests, recursive estimates |
| `ident_*.csv`, `robust_price_spec.csv` | identification diagnostics, leave-out, specification robustness |
| `multipliers_derived.csv`, `multipliers_comparable.csv`, `irf_*.csv` | multipliers, IRF paths, statistics, differences, persistence, oil-bridge sensitivity |
| `robustness_blocks.csv`, `robustness_multipliers.csv` | classification (§6 Q7) |
| `authors_*.csv` | Task 1 tables |
| `figures/*.png` | IRF overlays, coefficient forest, recursive estimates, null bootstrap, GSCPI identification, authors' IRF replication, persistence |
| `pre_phase4c_manifest.sha256` | hashes of 489 pre-existing files, re-verified by the test suite |

Scripts: `run_p4c_estimation.py` (Tasks 1-3), `run_p4c_spec_robustness.py`, `run_p4c_irf.py` (Task 4), `run_p4c_figures.py`, `run_p4c_workbook.py`, `run_p4c_report.py`.
