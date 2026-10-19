# Phase 2a findings: Macrobond versus the authors' dataset

Date: 2026-10-16. Tables: `docs/data_dictionary.md` (generated), `outputs/phase2/reconciliation_*.csv`.
Code: `bb_inflation/data/macrobond_{registry,loader}.py`, `bb_inflation/validation/macrobond_recon.py`;
tests: `tests/test_macrobond_reconciliation.py` (the full suite, 66 tests at the time of writing, 80 after Phase 3, all pass).

## 1. Result

Eight of the nine series the model needs that are not the Google index are on Macrobond, found by searching
(using the BLS codes in Macrobond's `UsBlsCode` metadata, not guessed tickers). Retrieved **as of 15 Sep 2023**
through Macrobond's revision history, they reproduce the authors' dataset:

| Series | Macrobond | Match to authors' data (1990Q1/2001Q1/1998Q1 to 2023Q2) |
|---|---|---|
| CPI all items, energy, food (SA) | uspric2156, uspric2368, uspric2158 | exact (0) |
| Productivity (output per hour) | uslama0202 | exact growth rates |
| ECI wages & salaries, private (SA) | uslama4604 | exact growth rates from 2001Q2 |
| V/U = JOLTS openings / unemployed | uslama1304, uslama1795 | max difference 0.0002 (2001Q1 onward) |
| Cleveland Fed expected inflation 1y, 10y | usfcst0101, usfcst0110 | max difference 5e-5 (float32 rounding in the authors' file) |
| NY Fed GSCPI | wotrad0027 | mean 0.012, max 0.034 (see §5) |

End to end, estimating the authors' equations on Macrobond data (authors' vintage, authors' pre-2001 V/U and ECI,
authors' Google index) gives sums of coefficients identical to the authors' to 4 decimals (largest: pre-COVID V/U sum
0.6931 vs 0.6934). The price equation is identical to 5 decimals.

## 2. Conventions the authors did not document

* "Quarterly" CPI, CPI energy, CPI food, and the Cleveland expectations are **last-month-of-quarter values**, not
  quarterly averages (averages miss by up to 3 index points; the monthly Cleveland series match exactly at quarter ends).
* V/U is the ratio of quarterly means. GSCPI is a quarterly mean.
* The package is a vintage: productivity was pulled between 7 and 27 Sep 2023, GSCPI in early Oct 2023.

## 3. Data revisions matter

Re-estimating the same equations over the same 1990Q1-2023Q2 sample with **today's** Macrobond data (same
specification) moves coefficients noticeably (full sample, sums of coefficients):

| | authors | current vintage |
|---|---|---|
| price eq.: wage growth | 0.667 | 0.703 |
| price eq.: lagged inflation | 0.333 | 0.297 |
| price eq.: productivity | -0.144 | -0.169 |
| wage eq.: V/U | 0.688 | 0.708 |
| wage eq.: productivity | 0.038 | 0.051 |

The drivers are productivity revisions and CPI/ECI seasonal-factor revisions. Consequences: the "original
specification and sample" comparison in Phase 3 must state which vintage it uses; every data pull must be
vintage-stamped (done: `data_cache/macrobond/<vintage>/`, with retrieval time).

## 4. Pre-2001 history (decision: use the authors')

Not on Macrobond: Barnichon's composite help-wanted index (V/U before 2001) and the authors' ECI splice. Per the
decision of 2026-10-16 both are taken from the authors' public file through 2000Q4 and Macrobond afterwards.

New information for that decision: Macrobond has its own ECI wages & salaries series back to **1980Q1**. Over
1990Q1-2000Q4 it differs materially from the authors' spliced series (which uses a total-compensation series): mean
absolute difference in annualised growth 0.61 pp, correlation 0.58, mean growth 3.48% (authors) vs 3.36%
(Macrobond). Post-2000 the two agree (mean absolute difference 0.03 pp, correlation 0.996). Using Macrobond's own
history would give a pure-Macrobond, conceptually cleaner wage series for the whole sample, at the cost of departing
from the authors' definition. I kept the authors' history as the default and will include the Macrobond-only ECI as a
sensitivity case in 2b (not a replacement) unless you decide otherwise.

## 5. GSCPI as the 'shortage' substitute (input to Phase 2b)

* Correlation with the Google 'shortage' index is 0.04 in 2004-2019 and 0.38 in 2020-2023 (0.73 over the whole
  sample, driven by the pandemic spike). Google is flat (about 5) pre-COVID and GSCPI is not, so they are different
  signals; GSCPI mean/sd 2020-23 is 1.9/1.5 in its own units versus 21/10 for the Google index.
* The authors' GSCPI variant (their Table A8) reproduces exactly (`tests/test_estimation.py`): shortage sum 0.271,
  p 0.016, R² 0.940 versus 0.947 with Google.
* Macrobond's GSCPI as of 2023 differs from the authors' file by up to 0.034 (the NY Fed re-estimates the full history
  every month, so the series also revises as it updates). Current GSCPI differs by up to 0.33 over 1998-2023.

## 6. Limits of what has been checked

* Vintages: reconciliation depends on Macrobond's stored revision history; GSCPI and Cleveland vintages are not
  fully stored, hence the small residuals above.
* Release lags are approximate (about a day) and observed from Macrobond's history, not from official calendars.
* Model data now end at 2026Q2 for the complete set (ECI, productivity, V/U); CPI and Cleveland run to 2026Q3.
  Nothing has been estimated beyond 2023Q2 yet (Phase 3).
