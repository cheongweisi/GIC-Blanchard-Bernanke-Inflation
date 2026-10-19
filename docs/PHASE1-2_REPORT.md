# Bernanke–Blanchard (2023) replication — Phase 1/2 report and implementation plan

Status date: 2026-10-16. Scope: Phase 1 (literature, code, replication strategy) and Phase 2 (Macrobond-only data strategy).
**Status update (2026-10-17).** This is the original planning report written before any code existed. Its plan has since been executed and several statements below are superseded; see `docs/replication_log.md` (Phase 1), `docs/phase2a_findings.md` and `docs/phase2b_findings.md` (Phase 2) and `docs/validation_report.md` (pre-Phase-3 validation). Corrections made inline are marked *[updated]*.

---------------------------------------------------------------------------------------------------

## 1. Headline findings

1. The model is **four OLS equations estimated one at a time with linear coefficient restrictions** (Stata `cnsreg`, i.e. restricted least squares). It is not a jointly estimated SVAR. "SVAR" in the paper describes the recursive ordering and the way the equations are chained in simulation.
2. **Feasibility confirmed:** a ~40-line Python restricted-least-squares script reproduces the authors' Stata coefficients for all four equations, in both the full sample and the pre-COVID sample, to within 1e-6 (the precision stored in their Excel output). The equations, sample and constraints in §3 are therefore correct, not just my reading of them.
3. The package needs **Stata + MATLAB/Dynare + R + Python**. None of Stata, MATLAB, R or Dynare is installed here (Python 3.12, pandas, statsmodels, `macrobond_data_api` and `win32com` are). Strategy: **re-implement everything in Python and validate against the authors' shipped output files** (coefficients, `eq_simulations_data`, IRF, decomposition and forecast outputs) instead of re-running their software. Only the optional Dynare "simple model" cannot be re-run, and it is not part of the four-equation model.
4. Phase 2 is hard on **three series**, not just the Google Trends one: (i) `shortage` (Google Trends → GSCPI as you proposed), (ii) V/U before 2001 (Barnichon composite help-wanted index), (iii) wage ECI before 2001 (a spliced older BLS series from Reifschneider). The Cleveland Fed expectations series also need a Macrobond equivalent confirmed. See §7.
5. Several **undocumented quirks** in the authors' code matter for replication fidelity (§5). The most important: the "1989Q1" sample start is really 1990Q1, and the paper's baseline (pre-COVID wage/expectations equations) differs from what the replication package's IRF/decomposition/forecast code uses (all-full-sample coefficients with Q2/Q3-2020 dummies).

---------------------------------------------------------------------------------------------------

## 2. Replication package contents

Preserved untouched in `original_replication_package/` (zip + extracted tree; SHA-256 manifest in `original_replication_package_MANIFEST.sha256`, 210 files). The supplemental appendix PDF and the NBER paper PDF are in `original_replication_package/supplemental/`.

| Folder | Contents | Role |
|---|---|---|
| `README.pdf`, `Data Citations.docx` | Run order, software list, data availability | Documentation |
| `(1) Data/Public Data/` | `Regression_Data.dta/.xlsx` (306 quarters, 1947Q1–2023Q2, 16 columns + data dictionary), `SPF_data.xlsx`, `figure_6_car_data.xlsx`, `Shortage Alternatives/gscpi_cleaned.xlsx`, `gscpi_data.xls`, R helper scripts | **The estimation dataset** |
| `(1) Data/Private Data/` | `Bloomberg_Commodity_Data.xlsx`, `SP_GSCI.xlsx` (formulas, need Bloomberg/Haver add-ins) | Only for PCA (Figs 4–5), not the core model |
| `(2) Regressions/` | `regression_full.do`, `regression_pre_covid.do`; output folders with `eq_coefficients*.xlsx`, `summary_stats*.xlsx`, `eq_simulations_data*.xls`; `Predicted vs. Actual/plot_pred_v_actual.R` | **Core estimation** (Tables 2–5, A4/A5) |
| `(3) Core Results/IRFs` | `irf_simulations.m`, outputs `results_{energy,food,vu,shortage}.xls` | Figs 10–11 |
| `(3) Core Results/Decompositions` | `decomp.m`, outputs `remove_*.xls` | Figs 12–13 |
| `(3) Core Results/Conditional Forecasts` | `cond_forecast.m`, `wage_constant.pdf`, outputs `terminal_{low,mid,high}.xlsx` | Fig 14 |
| `(4) Other Results/` | `PCA/pca.py` (sklearn PCA on 19 commodities), `Shortages/`, `Simple Model/` (Dynare `.mod` files, `Simple_Model.m`) | Figs 1–2, 4–6 (not core) |
| `(5) Appendix/` | `.do` files + outputs for PCE, SPF, GSCPI ("NY Fed") shortage, V/U-in-price-equation, non-linear V/U | Tables A6–A10 |
| `Figures/` (PNG, PDF ×14), `Tables/` (`bb_tables_main.docx`) | Published figures and tables | **Comparison targets** |
| Junk | `.Rhistory`, `~$…` Word/RTF lock files | Ignore |

Authors' own validation targets we can compare against without any proprietary software: `eq_coefficients*.xlsx`, `summary_stats*.xlsx`, `eq_simulations_data*.xls` (includes the fitted values and residuals), `results_*.xls`, `remove_*.xls`, `terminal_*.xlsx`, plus the 14 published figures and the main tables.

---------------------------------------------------------------------------------------------------

## 3. The exact equations

Notation follows the Stata code. All growth rates are `400·Δln(X)` (quarterly, annualised). `L{k}.x` = k-th lag. `Σ` = sum of the listed coefficients.

### 3.1 Data transformations (`regression_full.do` lines 29–52)

```
gcpi      = 400·Δln(CPIAUCSL)
gw        = 400·Δln(ECIWAG)
gpty      = 400·Δln(OPHNFB)
magpty    = (1/8)·Σ_{i=0..7} gpty_{t-i}              # 8-quarter moving average
grpe      = 400·Δln(CPIENGSL / ECIWAG)               # relative price of energy
grpf      = 400·Δln(CPIUFDSL / ECIWAG)               # relative price of food
vu        = VOVERU                                   # vacancies / unemployed
cf1       = EXPINF1YR      cf10 = EXPINF10YR         # Cleveland Fed
shortage  = Google Trends "shortage" (quarterly mean, 2021 peak week = 100); = 5 before 2004Q1
diffcpicf = (1/4)·(gcpi_t + gcpi_{t-1} + gcpi_{t-2} + gcpi_{t-3}) − cf1_{t-4}     # "catch-up"
dummyq2_2020, dummyq3_2020 = 1 in 2020Q2 / 2020Q3 (full-sample version only)
```

### 3.2 Wage equation (dep. `gw`)

```
gw_t = Σ_{k=1..4} β_k gw_{t-k} + Σ_{k=1..4} β_{4+k} cf1_{t-k} + β_9 magpty_{t-1}
     + Σ_{k=1..4} β_{9+k} vu_{t-k} + Σ_{k=1..4} β_{13+k} diffcpicf_{t-k}
     + β_18 D2020Q2 + β_19 D2020Q3 + β_20 + ε
Restriction:  Σ_{k=1..4} β_k (gw)  +  Σ_{k=1..4} β_{4+k} (cf1)  =  1       # vertical long-run Phillips curve
```
No contemporaneous regressors (identification: wages respond with a one-quarter lag). Dummies exist only in the full-sample version.

### 3.3 Price equation (dep. `gcpi`)

```
gcpi_t = γ_1 magpty_t + Σ_{k=1..4} γ_{1+k} gcpi_{t-k} + Σ_{k=0..4} γ_{6+k} gw_{t-k}
       + Σ_{k=0..4} γ_{11+k} grpe_{t-k} + Σ_{k=0..4} γ_{16+k} grpf_{t-k}
       + Σ_{k=0..4} γ_{21+k} shortage_{t-k} + γ_26 + ε
Restriction:  Σ_{k=1..4} γ_{1+k} (gcpi lags)  +  Σ_{k=0..4} γ_{6+k} (gw)  =  1
```
Note `magpty` enters **contemporaneously** here (but lag 1 in the wage equation). Always estimated over the **full** sample 1990Q1–2023Q2, even in the "pre-COVID" run.

### 3.4 Short-run expectations (dep. `cf1`; **no constant**)

```
cf1_t = Σ_{k=1..4} a_k cf1_{t-k} + Σ_{k=0..4} b_k cf10_{t-k} + Σ_{k=0..4} c_k gcpi_{t-k} + ε
Restriction:  Σa + Σb + Σc = 1
```

### 3.5 Long-run expectations (dep. `cf10`; **no constant**)

```
cf10_t = Σ_{k=1..4} d_k cf10_{t-k} + Σ_{k=0..4} e_k gcpi_{t-k} + ε
Restriction:  Σd + Σe = 1
```

### 3.6 Estimation periods

| Item | Full-sample run | Pre-COVID run |
|---|---|---|
| Wage, cf1, cf10 | 1990Q1–2023Q2, N = 134 (wage has Q2/Q3-2020 dummies) | 1990Q1–2019Q4, N = 120 (no dummies) |
| Price | 1990Q1–2023Q2, N = 134 | identical to full-sample run |
| R² reported | squared correlation of actual and fitted from 1990Q1 | same, restricted to ≤2019Q4 |

Simulation order within a quarter (all three `.m` files): `gw_t → gcpi_t → diffcpicf_t → cf10_t → cf1_t`. Exogenous: `grpe, grpf, vu, shortage, magpty` (+ dummies). Equation residuals are set to zero in IRFs, decompositions and projections.

### 3.7 Simulation exercises

* **IRFs** (`irf_simulations.m`): 32 quarters from an all-zero steady state (variables are deviations; constants and dummies dropped). One-s.d. shock at t = 5, s.d. taken from 2020Q1-onward data (`grpe`, `grpf`, `vu`, `shortage`) or from model residuals. Persistence ρ: `grpe`, `grpf`, `shortage` one-time level shift of the *rate* (ρ = 0); `vu` ρ = 1 (permanent). Own-equation shocks *replace* the equation value at t = 5 (equivalent to adding a residual only because all lags are zero there).
* **Decomposition** (`decomp.m`): dynamic simulation from actual 2018Q4–2019Q3 initial conditions with *all* exogenous inputs actual (baseline) versus one input held at steady state (contribution = baseline − counterfactual). Steady states used: `grpe = grpf = 0`, `vu =` 2019Q4 value (1.2), `shortage = 5`, `magpty = 2`, dummies = 0. No residuals, so bars do not sum to actual inflation (the paper says so).
* **Conditional forecast** (`cond_forecast.m`, Fig. 14): start 2023Q2 from actual lags; `grpe = grpf = 0`, `shortage = 10`, `magpty = 1`; `vu` falls linearly over 8 quarters to 0.8 / 1.2 / 1.8, then flat; wage constant re-derived analytically so that steady-state `vu* = 1.2` (`wage_constant.pdf`):
  `β_20* = −(Σβ_{10..13})·vu* − (1−Σβ_{1..4})·[ (γ_1/(1−Σγ_{2..5}) + β_9/(1−Σβ_{1..4}))·magpty* + Σγ_{21..25}/(1−Σγ_{2..5})·shortage* + γ_26/(1−Σγ_{2..5}) ]`
  (the PDF has a typo, "γ4" twice in the price equation; the `.m` code is right).

---------------------------------------------------------------------------------------------------

## 4. Software dependencies

| Component | Authors used | Here | Plan |
|---|---|---|---|
| Regressions | Stata 17/18 (`cnsreg`, `putexcel`, `estout`/`outreg2`) | not installed | Python restricted LS (numpy; `statsmodels` for cross-checks and tests) |
| IRF / decomposition / forecast | MATLAB R2022a (+ Dynare 5.4 for the toy model) | not installed | Python linear-state-space simulator |
| Figures | R 4.3.1 (tidyverse, ggplot2, …) | not installed | matplotlib |
| PCA | Python 3.8 + pandas + sklearn | available | not needed for core model |
| Reading shipped `.xls` outputs | — | `xlrd` missing | *[updated]* installed in the project `.venv`, pinned in `requirements.txt` |
| Macrobond | — | `macrobond_data_api` imports and connects (a test call returned "Not found" for a guessed ticker, i.e. the connection works) | use for Phase 3 and Phase 2 |

---------------------------------------------------------------------------------------------------

## 5. Discrepancies and quirks found in the authors' materials

| # | Issue | Consequence for us |
|---|---|---|
| 1 | Sample says 1989Q1–2023Q2, but `keep if period>=1989q1` runs **before** the `l1.`–`l4.` operators are evaluated, so the first four quarters are lost: effective sample is **1990Q1–2023Q2** (N = 134; 120 pre-COVID). `magpty`/`diffcpicf` are built before the `keep`, so they are unaffected. | Must build all lags on the full series, then slice from 1990Q1. Reproduces N exactly. |
| 2 | The paper's **baseline** uses pre-COVID wage and expectation equations plus a full-sample price equation (Tables 2–5; Fig. 14 text), but the README says "for the remainder of the results, we use the full sample regressions", and `irf_simulations.m`, `decomp.m`, `cond_forecast.m` all read `Output Data (Full Sample)/eq_coefficients.xlsx` (wage equation with COVID dummies). | Two distinct coefficient sets. We will replicate both and say which one each published figure matches (Figs 3, 7–9 use pre-COVID; Figs 10–14 appear to use full sample; to be confirmed numerically in Phase 1 step 5). |
| 3 | Paper tables end in 2023Q1 (price N = 133); package ends in 2023Q2 (N = 134). Package price-equation sums (0.333 / 0.667 / 0.066 / 0.126 / 0.019 / −0.144) differ in the 3rd decimal from paper Table 3 (0.335 / 0.665 / …). Wage and cf1 pre-COVID results match Tables 2 and 4 exactly (0.460 / 0.693 / −0.024 / 0.540 / 0.031, R² 0.578; 0.369 / 0.506 / 0.124). | Explained by the extra quarter / data vintage; will verify by re-estimating to 2023Q1. |
| 4 | Paper Table 5 note says the cf10 sample ends 2019Q1 (typo; code uses 2019Q4). | Documented only. |
| 5 | Paper footnote 6: the pre-2001 ECI is a different BLS series (total compensation, ECS10001I) joined with a level-shift dummy. The `.do` files have no such dummy; the `ECIWAG` column in `Regression_Data` is already a spliced series starting 1982Q1. The data dictionary credits "Reifschneider". | Splice method is not reproducible from the package; see §7. |
| 6 | Appendix Table A1 swaps the FRED codes of `grpe`/`grpf` (lists PCE food code for energy and vice versa); the code actually uses **CPI** energy/food (`CPIENGSL`, `CPIUFDSL`), not PCE. | Documented only. |
| 7 | Steady-state assumptions are not consistent across exercises: `magpty` = 2 (decomposition) vs 1 (forecast); `shortage` = 5 (decomposition) vs 10 (forecast); `vu*` = 1.2 only through the re-derived constant in the forecast. | Make these explicit scenario parameters. |
| 8 | Decomposition code hard-codes dummy positions (7th and 8th quarter of a series starting 2018Q4), and the data start date. Dead code branch `else size(shocks_removed,2)==4;`. Forecast code computes dummy terms it never uses. | Harmless; avoid copying. |
| 9 | Paper IRF shock sizes (energy 32, food 3.2, shortage 11.6, v/u 0.5) are 2020Q1–2023Q1 standard deviations; the code uses 2020Q1–2023Q2 (package vintage). | Small differences expected. |
| 10 | The Google Trends series is normalised so its peak week = 100 and fills a constant 5 before 2004; pre-COVID variation is tiny, so the shortage coefficients are identified almost entirely by 2020–23. The authors state this themselves. | Central to Phase 2: see §7.3. |
| 11 | Folder names: code writes to `Output Data (Restricted Sample)`, shipped folder is `Output Data (Pre Covid Sample)`; many hard-coded `..\Replication Package\…` paths. | Cosmetic. |

---------------------------------------------------------------------------------------------------

## 6. Early feasibility checks *[updated: superseded by the automated tests, see `docs/replication_log.md`]*

* Rebuilt every variable from `Regression_Data.dta` in pandas and ran restricted least squares by the closed-form constrained-LS formula.
* Max absolute coefficient difference versus the authors' `eq_coefficients.xlsx` / `eq_coefficients_restricted.xlsx`:
  full sample gw 7e-7, cf1 9e-8, cf10 5e-8; pre-COVID gw 3e-6, cf1 1e-7, cf10 5e-8; price equation matches to six decimals (checked by inspection, same sample).
* Observation counts match (134 full, 120 pre-COVID).
* *[updated]* Everything listed here as unchecked has since been checked and is covered by tests: p-values, R², fitted values and residuals, IRFs, decompositions, conditional forecasts and the GSCPI appendix variant. Still not done: Appendix PCE, SPF, V/U-in-price and non-linear V/U variants.

---------------------------------------------------------------------------------------------------

## 7. Phase 2: Macrobond-only data strategy

### 7.1 Series required and replacement status *[updated: tickers now found and verified, see `docs/data_dictionary.md`]*

| Model variable | Authors' source | Macrobond route | Risk |
|---|---|---|---|
| CPI all items SA (`CPIAUCSL`) | BLS/FRED, **last month of the quarter** *[updated: not a quarterly average]* | BLS CPI-U SA monthly → last month of quarter | Low. Note seasonal-factor revisions change history. |
| CPI energy, CPI food SA | BLS/FRED | BLS CPI energy / food SA | Low |
| ECI wages & salaries, private SA | BLS (2001+), spliced older series pre-2001 | BLS ECI W&S private SA; pre-2001 needs a decision (below) | **Medium-high** |
| Productivity `OPHNFB` | BLS/FRED | BLS nonfarm business output per hour | Low (large revisions; vintage issue) |
| V/U | JOLTS openings ÷ unemployed (2001+), Barnichon (2010) composite HWI before | JOLTS openings and BLS unemployed level | **Medium-high before 2001** |
| `cf1`, `cf10` | Cleveland Fed expectations | *[updated]* on Macrobond (`usfcst0101`, `usfcst0110`), last month of quarter, exact match | Low |
| `shortage` | Google Trends "shortage" (US) | **GSCPI (NY Fed)** as agreed | **High: different variable, different scale** |
| (optional) SPF 1y/10y | Philadelphia Fed | check Macrobond | Only for the SPF robustness variant |

### 7.2 Proposed approach for history

The model starts in 1990 and several inputs have no Macrobond equivalent before 2001. Options: (A) **freeze the authors' public `Regression_Data` history** for 1989Q1–2000Q4 (V/U and ECI) and append Macrobond data from 2001Q1, with a series-level reconciliation of the overlap; (B) find a pure-Macrobond substitute (e.g. unemployment-rate–based tightness or a different wage series pre-2001) and accept a changed model. **I recommend A**, because it preserves the authors' definitions (your Phase 3 instruction) and the authors' file is public, but it does mean the "Macrobond-only" claim applies to updates from 2001 onward, not to the 1990s history. *[updated]* Confirmed by the user on 2026-10-16.

### 7.3 GSCPI as the `shortage` substitute — what to expect

* **Scale and sign conventions differ.** `shortage` is a 0–100 search-share index (pre-2020 ≈ 5; peak 48 quarterly; "normal" 5–10). GSCPI is in standard deviations from its mean (≈ −1 to +4.3). The authors' own GSCPI variant (Table A8; `alternative_shortages.do`) fills pre-sample missing values with −0.035 (the 2019 mean) instead of 5. All steady-state assumptions (5 / 10) and IRF shock sizes (11.6) must be re-expressed in GSCPI units.
* **GSCPI starts in 1997**, so 1990–1996 must be filled with a constant (as the authors did for pre-2004) or the sample must start later. I recommend the authors' approach (constant fill at the 2019 mean) for replication, and a sensitivity run with the sample starting 1998.
* **Authors' prior evidence:** the paper says the Google series had by far the most explanatory power among the supply-chain measures tried, including the NY Fed index; Table A8 reports GSCPI sum of coefficients 0.271 (p = 0.016), R² 0.940 versus 0.947 baseline, and the sum of price-equation lag weights on lagged inflation drops to 0.166. So expect a **worse fit, a larger shortage coefficient sum, and a changed split between "shortage" and other drivers in the decomposition**. This is a finding to report, not a bug.
* **Revisions:** GSCPI is re-estimated and revised monthly; the Google series is not. The update pipeline must store vintages.
* Possible complementary Macrobond-only series (ISM supplier deliveries, Baltic Dry, auto inventories) are *not* in the original specification; I will only evaluate them as clearly-labelled extensions in Phase 3, not in the replication.

### 7.4 Phase 2 acceptance criteria

* **2a — series reconciliation:** each Macrobond-built series compared with the corresponding column in `Regression_Data` over 2001Q1–2023Q2; report max/mean abs. difference of levels and of the growth rates the model actually uses. Tolerances to be agreed; I expect near-zero for CPI/ECI/productivity apart from revision effects.
* **2b — re-estimation:** Macrobond data + GSCPI through the original 2023Q2 sample, compared with the authors' coefficients, R², and the four published decompositions/IRFs; differences attributed, series by series (a data-swap ladder: swap one input at a time).

---------------------------------------------------------------------------------------------------

## 8. Proposed implementation plan

Project layout (new, independent; nothing from the ARDL project is touched or imported):

```
GIC Blanchard-Bernanke Inflation/
  original_replication_package/     # untouched originals (read-only; hashes in MANIFEST)
  docs/                             # this report, data dictionary, replication log
  bb_inflation/
    data/        retrieval.py (Macrobond), authors_data.py (reads Regression_Data), transforms.py, dictionary.py
    estimation/  equations.py (declarative eq specs), rls.py (restricted LS, tests, R²)
    simulation/  model.py (companion-form simulator), irf.py, decomposition.py, forecast.py
    viz/         figures.py
    validation/  compare_to_authors.py
  tests/         regression tests against shipped outputs
  notebooks|scripts/ run_replication.py, run_phase2.py
```
Equations are declared as data (dependent variable, regressor/lag lists, restriction, constant, sample) so one estimator and one simulator serve all variants (pre-COVID, full, GSCPI, PCE, SPF) and the later Phase 3/4 specs.

**Phase 1 steps (replication on the authors' data)**

1. Environment: venv with pandas, numpy, statsmodels, scipy, matplotlib, openpyxl, xlrd, pytest, `macrobond_data_api`. Pin versions.
2. Loader + transforms; test: derived variables equal the `eq_simulations_data` columns to 1e-9.
3. Restricted-LS estimator with sum-of-coefficient and joint Wald p-values (Stata `test` equivalents), R² as corr² from 1990Q1. Test: coefficients, sums, p-values, R², N for full and pre-COVID versus `eq_coefficients*`, `summary_stats*`; tolerance 1e-5. Reproduce Tables 2–5 and A4–A5.
4. Simulator in companion form; test: reproduce `results_*.xls`, `remove_*.xls`, `terminal_*.xlsx` to ~1e-6.
5. Reproduce Figs 3, 7–14 and compare with the published PNG/PDF (visual overlay plus numeric where the data are shipped); decide numerically which coefficient set (pre-COVID or full) each figure uses (quirk #2).
6. Appendix variants (PCE, SPF, GSCPI-NY Fed, V/U in price equation, non-linear V/U) as a secondary check; GSCPI variant is directly relevant to Phase 2.
7. Replication log: every discrepancy, explanation, and sign-off. **No change to specification until this is signed off.**

**Phase 2 steps**

1. Macrobond series search and data dictionary (ticker, source, unit, SA, frequency, publication lag, first/last obs); no guessed tickers.
2. Build quarterly dataset from Macrobond with option A history, plus GSCPI; vintage-stamp each pull and cache locally so results are reproducible if Macrobond data revise.
3. 2a reconciliation against authors' data; 2b data-swap ladder through 2023Q2; report with tables and charts.
4. Sign-off, then Phases 3–5 (updating to 2026, WLS/rolling/stability tests, forecasting engine, evaluation).

**Out of scope until you confirm:** any change to the specification, Phase 3–5 work, the PCA commodity exercise and the Dynare toy model (not needed for the four-equation model).

---------------------------------------------------------------------------------------------------

## 9. Decisions *[updated: all resolved on 2026-10-16 or since]*

1. *(resolved: authors' public history through 2000Q4, Macrobond from 2001Q1)* **Pre-2001 history:** use the authors' public `Regression_Data` for 1989Q1–2000Q4 V/U and ECI and Macrobond afterwards (recommended)? Or require a pure-Macrobond substitute and accept a changed model?
2. *(resolved: Cleveland Fed series are on Macrobond)* **Cleveland Fed expectations:** if they are not on Macrobond, would you accept the SPF 1y/10y (authors' own Table A7 variant) or another Macrobond expectations series as the Macrobond-only version?
3. *(implemented: authors' convention, fill -0.035; post-1997 sensitivity not yet run)* **GSCPI fill before 1997:** authors' convention (constant at 2019 mean) for the replication, with a post-1997 sensitivity run?
4. *(both replicated; the shipped IRF/decomposition/forecast outputs use the full-sample run)* **Which published baseline to treat as the "answer":** the paper's (pre-COVID wage/expectations, full-sample price) or the package's (all full-sample, with dummies)? I'll replicate both regardless.
5. *(done)* Install `xlrd` (and the other packages in §8 step 1) into a project virtual environment?
