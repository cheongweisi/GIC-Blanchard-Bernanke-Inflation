# Phase 4 report: an economically interpretable scenario framework for US CPI inflation

Date: 2026-10-18. Model: **Model B\*** from the Phase 3 supplement (unchanged: four equations, unweighted, GSCPI 2-quarter mean, estimated 1990Q1-2026Q2, flagged V/U 2025Q4 bridge).
Phase 1-3 outputs, documents, code and tests are untouched (221 files, SHA-256 manifest `outputs/phase4/pre_phase4_manifest.sha256`, checked by a test).
Phase 4 is separate: `bb_inflation/scenarios/`, `scripts/run_p4_*.py`, `outputs/phase4/`, `tests/test_phase4.py` (16 new tests; 109 pass). Data: new stamped pull `p4_20261018T051241Z`
(Brent history, EIA STEO, Brent futures strip of 16 Oct 2026, 2026Q3 partial-quarter series); it agrees with the pinned Phase 3 pull in all 46 quarters compared (no revisions).
Run: `scripts\run_p4_main.py` (9 s), `scripts\run_p4_backtest.py` (8 s), `scripts\run_p4_figures.py`.

## 0. Summary

1. **What kind of statement each number is** (your point 1; evidence in §1). Three kinds, labelled in every output (`kind` column) and tested in a pseudo-out-of-sample ladder:
   *conditional predictions with realised regressors* (Phase 3 style; y/y RMSE 0.8 pp at 1-3 years, a statement about the model, not a forecast),
   the *real-time baseline* (the model run on assumed drivers; its y/y RMSE has been 1.8-2.2 pp, **no better than an AR(4)** at 1.9-2.0 over 2004-26), and
   *scenarios* (deviations from that baseline: what the model says about the transmission of a stated assumption). **The scenario deviations are the product; the baseline level is not a forecast with demonstrated skill.**
2. **Model B\* is the baseline and no coefficient was changed** (your point 2). The flagged 2025Q4 V/U bridge is in. The estimated energy coefficients were not touched; the 20% lower pass-through is an overlay on top.
3. **Energy is handled in three separate concepts** (your point 4): *oil* (Brent, an input) -> *CPI energy* (nominal, from oil through a monthly bridge, elasticity 0.30 +/- 0.03; or specified directly) -> *relative energy price* (CPI energy / wages: **an output**, never an input). Because wages are endogenous,
   a relative price cannot be specified in a scenario (the code refuses). This matters: the price equation is the same equation in nominal form, homogeneous of degree one with weights wages (net of the relative-price terms) 0.59, nominal energy 0.075, nominal food 0.179, lagged inflation 0.155 (sum 1.000).
4. **Baseline (nowcast information set):** y/y CPI inflation 4.2% in 2026Q4 (Q4/Q4), 2.5% in 2027Q4, 3.0% in 2028Q4; 2.85% / 2.95% / 3.13% one / two / three years ahead (2027Q3 / 2028Q3 / 2029Q3). Driven by energy: +0.8 pp in 2026Q4, then **-0.5 to -0.9 pp** from 2027 as the futures curve (backwardated: $110 now, $87 end-2027, $73 end-2029) makes energy fall relative to wages.
   The 2-3 year level is soft (§3): the neutral wage constant gives 2.6% instead of 3.1%.
5. **Scenarios (y/y deviation from baseline, one / two / three years ahead; 90% parameter bands in `scenario_summary.csv`):** oil +30% persistent +0.75 / +0.04 / +0.06 pp (price level +0.75% then +0.85%); oil -30% -1.02 / -0.05 / -0.09; oil stays at $111 +0.53 / +0.41 / +0.26 (the gap to the falling curve keeps widening);
   temporary oil spike +0.87 / **-0.80** / +0.02 (base effect); V/U back to 1.19 +0.07 / +0.18 / +0.19; GSCPI +1 (decaying) +0.19 / +0.15 / +0.09; nominal food +8% +1.06 / +0.60 / +0.20; adverse supply bundle +0.98 / +0.28 / +0.23; benign bundle -0.97 / -0.05 / -0.27.
   **Rule of thumb:** Brent +10% persistent adds 0.27 pp to y/y inflation for a year and 0.27% to the price level (0.31% after three years). With 20% lower pass-through: 0.22 pp and 0.22% (0.25%).
6. **Transmission (§5).** An oil shock is a **first-round, price-level event**: 0.72 of its 0.75 pp in year one sits in the "direct" layer (price equation, including inflation persistence), the wage-price loop adds almost nothing (+0.01) because the wage equation has no direct energy term, and expectations add 0.02-0.07 pp later.
   Labour-market and expectations shocks are the reverse: nothing in year one, then slowly cumulating (V/U: entirely through wages). The drivers add exactly (gap 1e-14).
7. **Horizon.** Read 1-3 years. The model has no anchor for inflation: a permanent V/U change keeps raising y/y inflation to the end of the horizon, an expectations shock does not die out, and the baseline level 2-3 years out depends on the wage constant (§7).

## 1. What each number is worth: the pseudo-out-of-sample ladder (`backtest_*.csv`, `fig_p4_backtest_ladder.png`)

The model is re-estimated at 86 origins (2004Q4-2026Q1), forecasts are made 1-12 quarters ahead and compared with outturns to 2026Q2. The tiers differ only in what the drivers are assumed to be:

| Tier | Drivers | y/y RMSE, pp, 1y / 2y / 3y ahead | same, targets 2023Q3-2026Q2 |
|---|---|---|---|
| A. conditional, **realised relative prices** (Phase 3) | realised | 0.76 / 0.88 / 0.83 | 0.56 / 0.96 / 0.59 |
| B. conditional, realised **nominal** energy and food, wages endogenous (Phase 4 closure) | realised | 0.69 / 0.74 / 0.70 | 0.55 / 0.84 / 0.57 |
| C. conditional, **realised oil** through the bridge | realised oil | 0.99 / 1.04 / 0.94 | 0.64 / 0.93 / 0.60 |
| D. **real-time-feasible** (the baseline method: oil held at the origin level) | assumed | **1.84 / 2.20 / 2.10** | 1.13 / 1.99 / 2.35 |
| F. Phase 3 "unconditional" (relative prices zero) | assumed | 1.89 / 2.24 / 2.12 | 1.37 / 2.27 / 2.61 |
| AR(4) | none | 1.93 / 1.94 / 1.98 | 0.45 / 0.56 / 0.65 |

* **The new engine reproduces Phase 3's stored pseudo-out-of-sample forecasts to 1e-15** (tiers A and F, 930 forecasts each; `backtest_reproduces_phase3.csv`).
* Treating relative prices as endogenous (A to B) does **not** hurt; it helps slightly. The bridge (B to C) adds about 0.3 pp of y/y error. The step from conditional to real-time (C to D) is the large one: 1 pp. Knowing the oil price path is worth more than any refinement of the structure.
* Only tier D is a forecast of the kind the baseline is, and it has not beaten the AR(4) over the whole period (it did before 2020: 1.49 against 1.63; it did not after 2023: 1.13-2.35 against 0.45-0.65). That is the Phase 3 conclusion carried forward: the structural model earns its keep conditionally.
* **Consequences for presentation:** every chart and table says which tier it is; scenarios are always shown as deviations; the baseline fan (§3) is labelled *conditional on the assumed drivers* and the empirical real-time error is drawn next to it (red bars in `fig_p4_baseline.png`).
  Tier D errors were measured with oil held flat because futures curves are not available historically; the baseline uses the futures curve, which should be at least as good, but this is not demonstrated.

## 2. The framework

### 2.1 Three energy concepts, and wages (`engine.py`, `oil.py`)
| Concept | Role | Source |
|---|---|---|
| Oil: Brent, USD/bbl, monthly | **input** | World Bank monthly series (history); baseline curve: ICE/CME Brent futures settlements of 16 Oct 2026 (Dec 2026-Dec 2029); Oct 2026 = EIA STEO estimate of the month, Nov = midpoint of Oct and Dec (expired contracts are stale); EIA STEO and "flat" as alternatives |
| CPI energy, nominal | **derived** from oil by default (monthly bridge) or **input** (`cpi_energy_dev_pct`) | bridge: 100 dln E_m = c + sum_{k=0..3} b_k 100 dln Oil_{m-k}; 1990-02 to 2026-06, HAC; sum of b = 0.297 (s.e. 0.029), R2 0.53 monthly, residual s.d. 1.9 pp/month |
| Relative energy price (CPI energy / ECI) | **output** | grpe_t = gE_t - gW_t, computed each quarter after the wage equation (exact identity, as in the data); likewise food |

*Why.* In Phase 1-3 simulations grpe and grpf are inputs. With wages endogenous, a labour-market or expectations scenario that holds the relative price fixed would let the nominal energy price rise one-for-one with US wages, which no oil-market assumption justifies (and a nominal-price scenario can be set so that it does not). Here nominal energy and food paths are fixed in every scenario, and a wage change moves the relative price
(`test_wage_shock_moves_relative_price_not_nominal_energy`). The consequence is a lower **net** wage pass-through in the price equation: 0.85 - 0.075 - 0.179 = 0.59, with the nominal energy and food terms taking the rest.
The bridge is monthly because the CPI is a quarter-end value (a quarterly oil average mistimes the 2026Q3 move: oil fell on average, but the September level was up 37% on June).
The bridge is a separate auxiliary equation, not part of the estimated model. Its out-of-sample errors in 2026 (actual minus bridge) were +3, -12 and +15 pp (annualised CPI energy growth in Q1/Q2/Q3; `bridge_out_of_sample_2026.csv`), partly offsetting. The long-run elasticity is 0.24 before 2008 and 0.34 after (`bridge_subsamples.csv`).

### 2.2 Information set
Default (**nowcast**): 2026Q3 is partly published. Its CPI inflation (4.46% annualised), Cleveland expectations (2.66, 2.58), nominal CPI energy (+22.6%) and food (+1.0%) and the GSCPI mean (1.14) are imposed; wages, V/U and productivity are not published and are model/assumption values; forecast quarters are 2026Q4-2029Q3.
**Strict** variant: origin 2026Q2, 2026Q3 forecast like any other quarter (the model with the bridge gives 3.65% for Q3 against the published 4.46%; the whole gap is the bridge, which gives +8% for CPI energy against +22.6% published, times 0.075). Strict vs nowcast changes the 1-year y/y by +0.14 pp and the 3-year by 0.00.

### 2.3 Baseline assumptions (all assumptions, none estimated; `baseline_assumptions.csv`)
oil: futures curve; CPI energy: bridge; CPI food: grows with baseline wages (relative food price constant: the authors' convention and Phase 3's unconditional forecasts), then **fixed as a nominal path** in all scenarios; GSCPI: AR(1) from 1.14 (1998-2026 fit); V/U held at 1.02 and productivity growth held at 2.1% (last complete quarter, Phase 3 convention);
wage constant: estimated (the specification validated in Phase 3); residuals: zero.
Not used: the 2026Q3 V/U flash (JOLTS September and productivity are unpublished), October 2026 data (CPI is due in November).

## 3. The baseline (`baseline_path.csv`, `fig_p4_baseline.png`, `fig_p4_energy_concepts.png`)

| y/y CPI inflation, % | 2026Q4 | 2027Q3 (1y) | 2027Q4 | 2028Q3 (2y) | 2029Q3 (3y) |
|---|---|---|---|---|---|
| baseline | 4.18 | 2.85 | 2.54 | 2.95 | 3.13 |
| model fan, 90% (parameters, residuals, bridge) | 3.6-4.8 | 1.6-4.2 | 1.1-3.8 | 1.6-4.3 | 1.6-4.5 |
| +/- 1 RMSE of past real-time-feasible forecasts | | +/-1.8 | | +/-2.2 | +/-2.1 |

* **Drivers** (`baseline_driver_contributions.csv`, versus the Phase 3 neutral reference: relative energy and food prices constant, GSCPI at its fill value, V/U at its 2019Q4 value of 1.19): energy +0.77 pp in 2026Q4, then -0.9, -0.9, -0.8 (2027Q1-Q3), fading to -0.4 by 2029; supply chains +0.2-0.3; V/U -0.2 (it is 0.17 below 2019Q4); productivity about zero. The same path in nominal form is in `baseline_nominal_blocks.csv`.
* **The fan is narrow because it holds the drivers fixed.** It is the model's uncertainty given oil, V/U, productivity and GSCPI; the red bars are what forecasts of this kind have actually missed by. Use scenarios for driver uncertainty.
* **Sensitivities** (y/y at 1y / 2y / 3y, `baseline_sensitivities.csv`): headline 2.85 / 2.95 / 3.13; strict origin 2.99 / 2.99 / 3.13; **neutral wage constant 2.62 / 2.55 / 2.63** (authors' correction at V/U 1.02: the baseline stays near today's inflation instead of drifting up as the estimated constant implies); EIA STEO oil 2.43 / 2.81 / 3.09; oil flat at $111 3.40 / 3.38 / 3.39;
  energy pass-through x0.8 **3.01 / 3.09 / 3.23** (higher, not lower: a lower pass-through also shrinks the energy *drag* of the falling curve); intercept correction -0.3 pp for four quarters 2.54 / 2.88 / 3.08.
* The choice of oil curve moves the 1-year baseline by up to 0.5 pp, the wage constant the 2-3 year baseline by 0.5 pp. Neither is estimated; both are in the report because they matter more than any scenario of modest size.

## 4. Scenario library (`scenario_summary.csv`, `scenario_paths_long.csv`, `fig_p4_scenarios_yoy.png`, `fig_p4_scenario_overview.png`)

Definitions in `scenario_library.csv`; paths of the assumed inputs in `scenario_assumptions_by_quarter.csv`. Sizes: +/-30% Brent (the s.d. of 4-quarter Brent changes is 32%), V/U back to its 2019Q4 value, GSCPI +1 (about one s.d.). They illustrate mechanisms; they are not probabilities.
Deviations from the baseline of the same model and information set, y/y, pp [90% parameter band]:

| Scenario | 1y | 2y | 3y | price level 3y, % |
|---|---|---|---|---|
| Oil stays at $111 | +0.53 [0.43, 0.62] | +0.41 | +0.26 [0.14, 0.37] | +1.20 |
| Oil +30% persistent | +0.75 [0.58, 0.92] | +0.04 | +0.06 | +0.85 [0.59, 1.11] |
| Oil -30% persistent | -1.02 [-1.25, -0.79] | -0.05 | -0.09 | -1.16 |
| Temporary oil spike (+50%, 2027H1) | +0.87 | **-0.80** | +0.02 | +0.10 |
| Oil normalises to $70 by mid-2027 | -0.76 | +0.34 | +0.15 | -0.27 |
| Oil follows EIA STEO | -0.41 | -0.14 | -0.04 | -0.59 |
| V/U to 1.19 (2019Q4) | +0.07 | +0.18 | +0.19 [0.13, 0.25] | +0.44 |
| V/U -0.2 | -0.09 | -0.22 | -0.22 | -0.52 |
| GSCPI +1, decaying | +0.19 | +0.15 | +0.09 | +0.43 |
| Nominal food +8% | +1.06 [0.45, 1.71] | +0.60 | +0.20 | +1.87 |
| Productivity growth -1 pp, 2 years | +0.04 | +0.09 | +0.08 | +0.21 |
| Expectations de-anchor (1y +0.5, 10y +0.2) | +0.05 | +0.24 | +0.26 | +0.55 |
| Adverse supply bundle | +0.98 | +0.28 | +0.23 | +1.50 |
| Benign bundle | -0.97 | -0.05 | -0.27 | -1.29 |
| Overheating bundle (V/U up, oil stays, expectations) | +0.65 | +0.83 | +0.71 | +2.20 |

How to read it: a **level** shift in an input (oil, food) moves the price level once and y/y inflation for four quarters, then drops out (the base effect: a temporary spike gives -0.80 pp two years out). Shocks to the **labour market or expectations** cumulate and are still there at three years.
Oil +30% is not symmetric with -30% (1.02 against 0.75 in y/y) because the shocks are +/-30% in levels, i.e. +26% and -36% in logs. Rules of thumb per unit (`rules_of_thumb.csv`, linear): Brent +10% persistent 0.27 pp (1y) and 0.31% on the price level (3y); V/U +0.1 0.04 / 0.11 / 0.11 pp (1y/2y/3y);
nominal food +5% 0.67 / 0.38 / 0.13; GSCPI +1 decaying 0.19 / 0.15 / 0.09; 1y expectations +0.5 pp for four quarters 0.05 / 0.19 / 0.19.

### 4.1 Pass-through sensitivity (your point 3; labelled an alternative assumption, not statistically preferred)
Energy scenarios are also run with the price equation's energy coefficients multiplied by 0.8 (the Phase 3 supplement's asymmetry estimate implied about 20%, not significant out of sample; it brings the contemporaneous coefficient 0.092 to 0.074, the CPI energy weight). It scales rises and falls alike; deviations are measured against the baseline run with the same assumption,
and `y/y level vs headline baseline` in `scenario_summary.csv` gives the comparison with the headline baseline. Effect on the 1-year y/y deviation:

| | headline | x0.8 | bridge elasticity 0.34 (2008-26) | 0.24 (1990-2007) | +/-1 s.e. (0.33 / 0.27) |
|---|---|---|---|---|---|
| Oil +30% | 0.75 | 0.60 | 0.86 | 0.61 | 0.83 / 0.68 |
| Oil -30% | -1.02 | -0.82 | -1.16 | -0.83 | -1.12 / -0.92 |
| Oil stays at $111 | 0.53 | 0.42 | 0.60 | 0.43 | 0.58 / 0.48 |
| Spike | 0.87 | 0.70 | 0.99 | 0.71 | 0.96 / 0.79 |

The x0.8 overlay lowers every energy effect by 20% and nothing else; the uncertainty in the oil-to-CPI-energy link (elasticity 0.24-0.34) is of the same order as the overlay and is a second, distinct source (`oil_passthrough_sensitivity.csv`).

## 5. Transmission mechanisms and driver contributions

Three exact, additive views (`attribution.py`; checks in `attribution_checks.csv`, all gaps below 1e-14):
* **By driver** ("who"): one driver at a time (`attribution_by_driver.csv`, `fig_p4_attribution_driver.png`).
* **By layer** ("how"), closures switched on in order (`attribution_by_layer.csv`, `fig_p4_attribution_layer.png`): *direct* = price equation only, wages and expectations held at baseline (nominal energy and food, supply chains, productivity and the persistence of inflation itself); *wages* = the wage equation added (V/U, own lags, catch-up); *expectations* = the expectations equations added. The wages/expectations split depends on the order; the total does not.
* **Proximate, nominal form** (`attribution_proximate_nominal_blocks.csv`, `attribution_cumulative_price_level_blocks.csv`): where the deviation is booked in the price equation: wages net of the relative-price offset, nominal energy, nominal food, lagged inflation, supply chains, productivity. An accounting split, not a causal one.

What they show:
* **Oil +30% persistent, price level after one year +0.75%:** nominal energy 0.60 (CPI energy +8.1%, times the 0.075 weight), inflation persistence through the price equation's own lags 0.12, wages 0.03. After three years +0.85%: wages 0.15 (booked through the expectations layer raising wage growth), lagged inflation 0.12, energy 0.59.
  By layer, year one is 0.72 direct, 0.01 wages, 0.02 expectations; by year three y/y is back to baseline, with +0.07 pp from expectations. *The wage-price spiral channel is close to absent for energy: the wage equation has no direct energy term and the catch-up coefficient is zero (sum -0.003).* This is a property of the estimates; the 2026 wage residuals (negative) are consistent with it but are not evidence for it.
* **Relative-price offset.** The relative energy price rises by 8.0% after a year (CPI energy +8.1%, wages +0.07% higher) and 7.8% after three (wages +0.26% higher): the wage response erodes the relative price only slowly. `energy_transmission_chain.csv`, `fig_p4_oil_chain.png` give oil, CPI energy, wages, relative price, price level and inflation quarter by quarter.
* **V/U** is a pure wage-price loop: layers are 0 / 0.07 / 0.18 / 0.16 (wages) at 1, 4, 8, 12 quarters. **Expectations** shocks work through the expectations layer and feed wages with a lag. **Supply chains** are direct (0.19 of 0.19 in year one).
* **Bundles add up** (`fig_p4_attribution_driver.png`): in the adverse supply bundle, oil gives 0.75 of 0.98 pp in year one, GSCPI 0.19, productivity 0.04; by year three GSCPI and productivity dominate (0.09 and 0.08 of 0.23). In the overheating bundle oil is 0.53 of 0.65 pp in year one; by year three it is 0.26 of 0.71, with V/U (0.19) and the expectations shock (0.26) providing the rest.

## 6. Validation of the machinery (all in `tests/test_phase4.py`)
The engine reproduces the Phase 1-3 simulator to 1e-12 and the stored Phase 3 pseudo-out-of-sample forecasts to 1e-9; the price-equation nominal weights sum to 1; relative prices equal nominal growth minus wage growth every quarter; the nowcast quarter is the published one and cannot be shocked (observed oil is never changed);
a scenario with no deviations equals the baseline; oil effects are linear in log deviations and sign-symmetric; the 0.8 overlay scales only the energy coefficients; driver and layer attributions add up; proximate blocks sum to the total; the Phase 4 pull passes its integrity check and matches the pinned data; Phase 1-3 files are byte-identical to their pre-Phase-4 hashes.

## 7. Limits, and how to read long horizons (your point 5)
* **No anchoring.** The model has no natural rate and no inflation target: a permanent V/U change raises y/y inflation without limit (still +0.19 pp and flat-to-rising at three years), a ten-year expectations shock persists, and the wage constant decides where baseline inflation drifts. Keep to 1-3 years; the y/y deviations beyond two years should be read as direction and ordering, not magnitudes.
* **Baseline level.** Oil curve (+/-0.5 pp at one year) and wage constant (0.5 pp at 2-3 years) matter more than most scenarios; the baseline has not been shown to beat an AR(4).
* **Bands.** Scenario bands are parameter uncertainty only (HAC draws for the four equations and the bridge, 1,000 draws; equations independent; no cross-equation covariance). They exclude specification and driver uncertainty. The baseline fan adds residual and bridge noise but still holds the drivers fixed.
* **Bridge.** 0.30 elasticity is a log-linear average; the 2026 quarters show errors of 3-15 pp in annualised CPI energy growth, and pass-through looks higher after 2008. Oil above $100 is at the edge of what most of the sample covers.
* **Food baseline** (grows with wages) and **productivity and V/U held** are conventions, not forecasts. **CPI** is the seasonally adjusted series at quarter-end; y/y here differs slightly from published (NSA) y/y. **Current-vintage** data, not real-time vintages, as in earlier phases.
* **Shutdown artifact** (Phase 3 supplement): the index levels of December 2025 and March 2026 are about 0.4 pp too low (rents carried forward, corrected in April 2026), so y/y for 2026Q4 and 2027Q1 is overstated by about that much relative to underlying inflation; from 2027Q2 the base is clean.
* Not done: October 2026 data and the 2026Q3 V/U flash (unpublished inputs), policy-rate paths, a dashboard.

## 8. Decisions
**Decided 2026-10-18:** headline baseline = futures curve and estimated wage constant; the EIA STEO path and the neutral wage constant stay as sensitivities (`baseline_sensitivities.csv`). Still open: item 3.

1. Headline oil curve: futures (used; market-based, reproducible, but backwardated) or the EIA STEO (lower by 0.4 pp at one year)?
2. Headline wage constant: estimated (used; validated) or the authors' neutral constant (baseline 0.5 pp lower at 2-3 years)?
3. Should the 2026Q3 information set (nowcast) stay the default once ECI, productivity and JOLTS are published (about early November)? A refresh would be a new stamped pull, never silent.

## Files
`outputs/phase4/`: baseline (`baseline_path.csv`, `baseline_assumptions.csv`, `baseline_sensitivities*.csv`, `baseline_nominal_blocks.csv`, `baseline_driver_contributions.csv`, `price_equation_nominal_weights.csv`, `history_context.csv`);
scenarios (`scenario_library.csv`, `scenario_assumptions_by_quarter.csv`, `scenario_summary.csv`, `scenario_paths_long.csv`, `rules_of_thumb.csv`, `oil_passthrough_sensitivity.csv`); attribution (`attribution_*.csv`, `energy_transmission_chain.csv`);
oil bridge (`bridge_coefficients.csv`, `bridge_out_of_sample_2026.csv`, `bridge_subsamples.csv`, `anchors.csv`); data checks (`data_qa_vs_pinned_pull.csv`, `data_2026Q3_partial_quarter.csv`, `run_provenance.csv`); backtest (`backtest_*.csv`); figures `fig_p4_*.png`.
Code: `bb_inflation/scenarios/{pull,pin,oil,engine,world,scenario,library,attribution,uncertainty,backtest}.py`, `scripts/run_p4_{main,backtest,figures}.py`. Data: `data_cache/macrobond/phase4/p4_20261018T051241Z/`.
