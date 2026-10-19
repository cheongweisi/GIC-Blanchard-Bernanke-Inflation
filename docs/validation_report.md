# Pre-Phase-3 validation report

Date: 2026-10-17. Scope: the Phase 1-2 replication, tested before extending estimation beyond 2023Q2 (not started).
The authors' specification and all earlier outputs are unchanged; everything new is additive (`outputs/validation/`,
`bb_inflation/validation/{specs,oos,gscpi_tests,wage_price}.py`, `bb_inflation/estimation/inference.py`,
`bb_inflation/simulation/general.py`). Data: Macrobond pull `pull_20261016T061219Z` (SHA-256 checked) and the
2023-09-15 as-of vintage; run record in `outputs/validation/data_provenance.json`. Full suite: 66 tests pass.
Re-run: `.venv\Scripts\python.exe scripts\run_validation.py` (several minutes).

## 1. Verdict

* **The authors' model replicates faithfully** and its core labour-market result is robust: a permanent +1 s.d. rise in V/U
  raises CPI inflation by about 1.0 pp after 8 quarters and about 1.4 pp after 27, with a 90% band of roughly 0.9-2.0 pp.
  This holds across shortage specifications, ECI histories, sample starts and inference methods.
* **The price equation's shortage block is the weak point, and the Google index is not the better measure out of
  sample.** Estimated only through 2019Q4, the Google specification cannot forecast 2020-23 (RMSE 5.8 pp, estimated
  shortage sum -0.15). Every GSCPI variant can (RMSE 2.0 pp, bias about zero, versus 2.6 pp with no shortage term).
  The authors' good fit for Google depends on the price equation being estimated on the 2020-23 data it then "predicts".
* **Carry into Phase 3:** the price equation with a **two-quarter trailing mean of GSCPI (`gscpi_ma2`, one coefficient)**,
  authors' lags everywhere else, the **authors' pre-2001 ECI splice as default** with Macrobond's ECI as a reported
  sensitivity, a **1990Q1 sample start**, and **HAC standard errors with bootstrap IRF bands**. Keep the authors'
  five-lag form (`gscpi5`) as the continuity benchmark. Reasons in §3-§5; evidence among the short GSCPI forms is
  not strong enough to say they differ materially from one another (§3).

## 2. Out-of-sample performance, 2020Q1-2023Q2 (14 quarters)

Dynamic forecasts: initial conditions the four actual quarters 2019Q1-Q4, **realised exogenous inputs**, zero residuals.
*Genuine* = all four equations estimated through 2019Q4 only (no wage dummies). Macrobond data throughout; RMSE in pp.

| Price equation shortage term | gcpi RMSE | gcpi MAE | gcpi bias | gw RMSE | cf1 RMSE | cf10 RMSE |
|---|---|---|---|---|---|---|
| none | 2.55 | 1.94 | -1.38 | 1.37 | 0.68 | 0.23 |
| Google, 5 lags (authors) | **5.78** | 5.08 | -4.84 | 1.78 | 1.55 | 0.59 |
| GSCPI, 5 lags | 2.04 | 1.44 | -0.02 | 1.23 | 0.66 | 0.33 |
| GSCPI, lags 0-2 / 0-1 / 0 | 2.03 / 2.01 / 2.03 | 1.46 / 1.40 / 1.37 | 0.01 / -0.10 / -0.17 | 1.23 | 0.65-0.67 | 0.32-0.33 |
| GSCPI, 4q / **2q mean** | 2.07 / **1.99** | 1.54 / 1.42 | -0.07 / -0.11 | 1.25 / 1.24 | 0.67 / 0.65 | 0.31 / 0.32 |
| AR(4) benchmark | 4.17 | 3.25 | -2.22 | 1.91 | 1.09 | 0.38 |

What this says, and does not say:

* **Not out-of-sample in the authors' design.** Their price equation uses 2020-23 data ("hybrid" regime): there Google
  gets RMSE 1.31-1.35 and GSCPI 1.60-1.72. That comparison is partly in-sample and should not be quoted as forecast skill.
* The Google result fails because 2004-2019 Google variation (s.d. 1.3 around 5) cannot identify the coefficients:
  pre-2020 sum -0.15, so a 2021 spike of up to 48 is extrapolated into deflation. GSCPI varies pre-2020 and gives a stable
  positive sum (0.33-0.40).
* Differences among GSCPI variants (RMSE 1.99-2.07) are well inside the noise of 14 overlapping quarters.
* Because exogenous inputs are realised, these are *conditional* forecasts; GSCPI is itself a realised global shock
  measure, so the result does not show it would help forecast unconditionally.
* **Expectations:** adding a working shortage term makes inflation right but cf10 worse (RMSE 0.32 vs 0.23, bias +0.28):
  the estimated feedback from inflation to expectations is too strong for 2020-23. Wage growth is under-forecast by about
  0.75 pp a year in every variant. These are weaknesses of the wage and expectation equations, not of the shortage choice.

## 3. GSCPI specification (price equation only; HAC inference)

| Spec | sum, est. to 2019Q4 (p) | sum, full (p) | lags (full) | flags | IRF h0-h1 (1 s.d.) | BIC (full) |
|---|---|---|---|---|---|---|
| Google 5 lags | **-0.15** (0.24) | 0.02 (0.18) | L1, L3 sig. negative | negative pre-2020 sum, sign alternation, unstable | 1.10, -0.27 | -10.7 |
| GSCPI 5 lags | 0.38 (0.08) | 0.27 (0.05) | +0.11 +0.26 +0.17 **-0.45** +0.18 | sign alternation | 0.16, 0.34 | +3.7 |
| GSCPI lags 0-2 | 0.40 (0.04) | 0.29 (0.01) | | none | 0.11, 0.44 | -1.3 |
| GSCPI lags 0-1 | 0.36 (0.03) | 0.30 (0.01) | | none | 0.12, 0.31 | -5.8 |
| GSCPI lag 0 | 0.33 (0.01) | 0.26 (0.05) | | none | 0.39, -0.08 | -8.8 |
| GSCPI 4q mean | 0.39 (0.06) | 0.27 (0.03) | | none | 0.10, 0.08 | -7.1 |
| **GSCPI 2q mean** | **0.36 (0.03)** | **0.30 (0.01)** | | none | 0.22, 0.18 | **-10.5** |

* The five-lag GSCPI form has an economically implausible third-lag coefficient (-0.45; t = -2.0 classical, -1.6 HAC) and
  individually insignificant lags (HAC joint p 0.26 through 2019Q4), so its sum is estimated with little precision. The authors' own
  lag structure is therefore not a good fit to this substitute.
* Lags 0-1 are not distinguishable from equal weights (HAC p = 0.56 through 2019Q4, 0.77 full), which supports the
  one-coefficient 2q mean. It has the lowest BIC among GSCPI forms, no flags, and a stable sum (0.36 pre vs 0.30 full;
  recursive estimates run 0.2-0.4 since late 2020 and 0.04-0.6 over the whole recursion from 2005, `fig_stability_recursive.png`).
* In-sample the Google five-lag fit is best (AIC -83); this was not used for selection because of its genuine
  out-of-sample failure.
* The shortage contribution to 2021-22 inflation is 0.87-1.04 pp across GSCPI variants (full estimation; 0.95 for `gscpi5`) versus 1.3 pp (Google); in 2021Q2
  0.6-1.1 pp versus 4.2 pp. The authors' finding that shortages dominated 2021Q2 depends on the Google series' timing.
  Estimated through 2019Q4, Google's decomposition gives -4.2 pp (meaningless), GSCPI +1.5 pp.

## 4. Wage-price robustness (HAC; `gscpi_ma2` unless stated)

| Case | V/U sum, wage eq. | LR wage effect of +0.5 V/U (pp) | gw lags | wage pass-through in price eq. | lagged-inflation sum (HAC p) | V/U IRF h27 (90% band) |
|---|---|---|---|---|---|---|
| authors' ECI, 1990Q1 | 0.71 | 0.76 | 0.53 | 0.85 | 0.15 (0.36) | 1.45 (0.87-2.01) |
| Macrobond ECI, 1990Q1 | 0.71 | 0.77 | 0.54 | **0.55** | 0.45 (0.005) | 1.39 (0.85-2.00) |
| either ECI, 2001Q1 | 1.11-1.12 | 0.69-0.70 | 0.19-0.21 | **1.23** | **-0.23** (0.26) | 1.35-1.36 (0.94-1.80) |
| either ECI, 2005Q1 | 1.01 | 0.69 | 0.27 | **1.14** | **-0.14** (0.55) | 1.36 (0.78-1.96) |

* **Robust:** the long-run wage effect of V/U (0.69-0.77 pp per +0.5), the V/U IRF (h27 1.35-1.45 pp), the energy IRF,
  and the expectation equations (sums unchanged to three decimals across all cases).
* **Not robust:** wage-to-price pass-through. With Google or GSCPI, the pre-2001 wage series moves it from 0.70-0.85
  (authors' splice) to 0.43-0.55 (Macrobond's wage-and-salary ECI). On 2001+ or 2005+ samples the price equation
  cannot identify inflation persistence: the lagged-inflation sum turns negative and pass-through exceeds 100%, which is
  not economically plausible. The 1990s data are doing most of the work in the price equation, so shorter samples
  should not be used for it. Wage persistence also falls sharply in short samples (gw lags 0.19-0.27 vs 0.53), offset by
  larger V/U coefficients, which is why the long-run V/U effect stays put.
* Genuine out-of-sample, the authors' ECI splice forecasts slightly better than Macrobond's (wage RMSE 1.24 vs 1.34,
  inflation 1.99 vs 2.10), a mild point in favour of keeping it as the default. This is not conclusive.

## 5. Inference, stability and data controls

* **HAC (Newey-West, 4 lags) covariances** respecting the homogeneity restriction are in `inference.py`. Classical
  Monte-Carlo IRF bands are wider than HAC and bootstrap bands for V/U (h27: classical 0.76-2.22, HAC 0.95-1.99,
  recursive block bootstrap 0.92-2.01), so the classical errors overstate uncertainty for V/U; HAC and bootstrap agree.
* **Stability** (sup-F for partial breaks with fixed-regressor bootstrap p-values, CUSUM, Chow predictive failure):
  - Wage, cf1, cf10 equations estimated to 2019Q4 predict 2020-23 without significant failure (Chow p 0.30-0.44;
    wage p = 0.42 excluding 2020Q2-Q3, 0.035 including them).
  - **Price equation: forecast failure for every shortage specification** (Chow p < 0.001 for GSCPI variants and 0.002 for Google, also when excluding 2020Q2-Q3):
    GSCPI improves the forecast but does not make the equation stable.
  - **Energy and food coefficients are unstable** (sup-F p < 0.005, i.e. 0 of 200 bootstrap draws exceed the statistic; break after 2018Q1) in all specifications; the
    wage pass-through and shortage blocks show no significant break.
  - cf1 shows mild instability around 2008Q1 (sup-F p = 0.045, CUSUM p = 0.027). With about 20 tests, one or two such
    rejections are expected by chance; treat as a flag, not a finding.
* **Data controls:** current Macrobond data now come only from stamped pulls under `data_cache/macrobond/pulls/`
  (manifest, SHA-256 per file, retrieval time, API version, per-series last revision), selected by an explicit
  `ACTIVE_PULL`; `refresh_pull()` never changes it, `compare_pulls()` reports revisions between pulls, tampering is
  detected (tested). A test refresh on 2026-10-17 reproduced the active pull exactly (no revisions in a day). The earlier
  silent "current" cache was migrated into the same layout and the old folder removed. Each validation run writes
  `data_provenance.json`.

## 6. What is faithful, what is substituted, what is new

| Faithful replication (authors' model, authors' data) | Data substitutions (Macrobond) | Proposed methodological additions (not in the authors' model) |
|---|---|---|
| Four equations, restrictions, samples, simulation order; coefficients, p-values, R², IRFs, decompositions, forecasts reproduce the shipped Stata/MATLAB outputs (tests) | CPI, energy, food, productivity, ECI (2001+), V/U (2001+), Cleveland expectations reproduce the authors' data at the 2023-09-15 vintage (exact to 5e-5; V/U 2e-4) | Genuine out-of-sample design, AR(4) benchmark |
| GSCPI appendix variant (Table A8) reproduced | GSCPI replaces Google "shortage": **material** change (§2-§3) | `gscpi_ma2`, shorter GSCPI lags |
| Paper Tables 2, 4, 5 reproduced; Table 3 within 0.002 (vintage) | ECI and V/U before 2001 are the authors' history by decision; Macrobond ECI as sensitivity | HAC errors, HAC/bootstrap IRF bands, stability tests |
| | Effect of using current-vintage data: price-equation lag sum 0.33 -> 0.30 (mostly productivity revisions) | Stamped pulls and provenance |

## 7. Open points before Phase 3

1. **Price-equation instability** (energy/food coefficients, forecast failure 2020-23) is the main modelling risk for the
   recent-data-sensitive specification: the Phase 3 weighting scheme should be evaluated on that equation first.
2. **Expectation equations over-react** in 2020-23 forecasts (cf10 bias +0.28); worth testing with recent-weighted estimation.
3. The GSCPI substitute is a realised global indicator; scenario work in Phase 4 needs a GSCPI assumption path in
   GSCPI units (the authors' "shortage = 10" has no direct equivalent; steady state -0.035).
4. Not done here: Appendix PCE/SPF/V-U variants; a GSCPI sample starting 1998; pre-COVID-coefficient simulations;
   cross-equation covariance in the Monte-Carlo bands (equations drawn independently; the bootstrap does include it).
5. Tests are small-sample: 14 forecast quarters, 8-9 distinct 2020-23 shock quarters. Rankings among GSCPI variants should
   not be over-read.

Figures and tables: `outputs/validation/` (`oos_*.csv`, `gscpi_*.csv`, `wageprice_*.csv`, `irfbands.csv`, `stability_*.csv`,
`fig_gscpi_{irfs,lag_patterns,decomposition}.png`, `fig_wageprice_*.png`, `fig_irf_bands.png`, `fig_stability_recursive.png`).
