# Phase 5 plan (draft for approval): a conditional-scenario dashboard and a reproducible refresh path

Date: 2026-10-18. Status: **plan only; nothing built.** Inputs: Phase 4 (framework), Phase 4b (validation, `docs/phase4b_report.md`), decisions of 2026-10-18 (headline bridge elasticity 0.297 with 0.24-0.40 range; catch-up toggle 0 / 0.10 / 0.25 as a labelled sensitivity; baseline driver rules unchanged with caveat). Phase 1-4b files stay hash-locked; Phase 5 gets its own package and outputs folder.
You have not yet defined Phase 5 in your own words; the scope below is my reading of "possible dashboard for the boss" in the project notes. Please correct it before I build.

## 1. Purpose and the one rule

Make the model usable for **conditional scenario analysis**: "if oil/V/U/supply chains/food/expectations do X, inflation deviates from the baseline by Y over 1-3 years, and here is how sure the model is." The product is the deviations. The baseline is context, not a forecast with demonstrated skill (real-time-feasible forecasts have not beaten AR(4) since 2023; the cause is driver assumptions, Phase 4b §2). Every number carries the wording in `outputs/phase4b/p5_labels.csv`.

## 2. Deliverables

| # | Deliverable | Content |
|---|---|---|
| 1 | **Scenario dashboard** (single self-contained HTML page, no Python at view time) | Baseline view; scenario picker (the 15 Phase 4 scenarios plus size sliders for oil, V/U, GSCPI, food); y/y and price-level paths; transmission by layer and driver; mandatory uncertainty panel (below); one-page "how to read this" |
| 2 | **Refresh pipeline** | One command: new stamped Macrobond pull -> data QA against the pinned pull -> re-estimate B\* -> baseline, scenarios, bands, sensitivity grid -> `dashboard_data.json` -> dashboard rebuilt. Never silent: a refresh is a new pull ID and a diff report |
| 3 | **Method note for the reader** (2 pages) | What the model is, what each band means, what it cannot say; drawn from Phase 4/4b, no new analysis |
| 4 | **Tests** | Dashboard numbers equal engine output; labels present next to every band; refresh reproduces Phase 4 headline on the pinned pull; Phase 1-4b hash check |

## 3. Design decisions already fixed by Phase 4b

* **Three uncertainty layers shown together, never one alone:** (a) 90% parameter band; (b) specification range = bridge elasticity 0.24-0.40 x catch-up 0 / 0.10 / 0.25 (`p5_scenario_table.csv`); (c) for the baseline, the conditional model band *and* the empirical real-time band (`p5_baseline_bands.csv`) plus the neutral-constant lower bound. The 0.8 pass-through is a separate, labelled alternative shown beside the elasticity range, not inside it.
* **Toggles:** bridge elasticity (0.24 / 0.297 / 0.40), catch-up (0 / 0.10 / 0.25), energy pass-through x0.8 (off by default), wage constant (estimated default / neutral lower bound), oil curve (futures default / EIA STEO / flat), information set (nowcast default / strict). Each toggle states in one line what it changes and which one is the headline.
* **Precompute, do not run the model in the browser.** The model is linear in each driver's log or level deviation given the coefficients, so the page holds, per toggle combination (3 x 3 x 2 x 2 = 36), unit-size response paths per driver plus the baseline, and scales them to the slider size. Interactions between drivers are exactly additive; the bridge makes oil deviations linear in log(1 + deviation), which the scaling must use (tested against the engine). Output size is small (a few hundred KB).
* **Horizon:** 1-3 years; the page greys out beyond that and says why (no anchor; constant = V/U 0.59).
* **No dual axes; y/y and price level on separate charts; deviations in pp, levels in %.** Palette and chart rules from the dataviz skill; light and dark mode.

## 4. Refresh path (Macrobond only; the COM API is reachable here)

1. New stamped pull (`pull.py`/`diag_pull.py` pattern), integrity-checked; compare with the pinned pull for the overlapping quarters (revisions would show).
2. Pending inputs that change the information set: ECI, productivity and JOLTS for 2026Q3 (about early November), October CPI. **Open item from Phase 4 (still undecided):** keep the nowcast information set as default once these arrive (my recommendation: yes, with strict as a toggle).
3. Re-estimate B\* on the new last complete quarter; rerun Phase 4 outputs into `outputs/phase5/` (never over Phase 4's folder); diff report of coefficients, baseline path and headline deviations against the previous run, with flags when any coefficient sum moves by more than 0.5 HAC s.e. or the bridge elasticity leaves 0.24-0.40.
4. Known data issues to carry in the log: V/U 2025Q4 bridge (Oct-2025 unemployment does not exist; Macrobond's 4.5% rate remains unexplained, question to you still open), shutdown artifact in CPI levels until April 2026.

## 5. Work packages and order

| Step | Work | Depends on |
|---|---|---|
| A | Define `bb_inflation/phase5/` package, config, pin; port toggles (elasticity, catch-up overlay, haircut) from Phase 4b into a supported API | your approval |
| B | Sensitivity grid and `dashboard_data.json` generator, with engine-equality tests | A |
| C | Dashboard page (baseline, scenarios, transmission, uncertainty panel, reading guide) | B |
| D | Refresh pipeline and diff report; dry run on the current pinned pull (must reproduce Phase 4 headline) | A |
| E | Method note; review with you; publish as a private artifact only if you ask | C, D |
B and D can run in parallel. I estimate the page itself as the smallest part; the sensitivity grid and tests are most of the work.

## 6. Risks and what I would not do

* **Misreading the baseline as a forecast** is the main risk; hence the fixed wording and the empirical band on the same chart. I would not show the baseline fan without it.
* The catch-up and elasticity toggles are sensitivities, not estimates; the page must not present phi = 0.25 as a model result.
* I would not tune the baseline driver rules (V/U held, GSCPI AR(1), food with wages) to improve a backtest; if you want alternatives (for example V/U mean-reverting), they would be labelled alternatives chosen on economic grounds before looking at errors.
* Publishing: nothing is shared outside this folder unless you ask; a dashboard for others would be a private artifact for you to share.

## 7. What I need from you

1. Is "conditional-scenario dashboard plus refresh pipeline" the Phase 5 you intend, or do you want something else first (for example a wider scenario library, or a policy-rate channel, which the model does not have)?
2. Audience and format: an HTML page you open locally, or a private artifact link for your boss?
3. Nowcast as default after the November data (recommended yes)?
4. The Oct-2025 SA unemployment rate (4.5%) in Macrobond: do you know its provenance?
