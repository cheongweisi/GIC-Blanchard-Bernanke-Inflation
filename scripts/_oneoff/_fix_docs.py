"""One-off documentation corrections made during the validation phase (kept for the audit trail)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def edit(rel: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (rel, old[:60])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


edit("docs/PHASE1-2_REPORT.md", [
    ("No model code has been written for the project yet. The only code run so far is throw-away feasibility checks (see §6).",
     "**Status update (2026-10-17).** This is the original planning report written before any code existed. Its plan "
     "has since been executed and several statements below are superseded; see `docs/replication_log.md` (Phase 1), "
     "`docs/phase2a_findings.md` and `docs/phase2b_findings.md` (Phase 2) and `docs/validation_report.md` (pre-Phase-3 "
     "validation). Corrections made inline are marked *[updated]*."),
    ("| Reading shipped `.xls` outputs | — | `xlrd` missing | add `xlrd` to the project environment (the only install needed for validation) |",
     "| Reading shipped `.xls` outputs | — | `xlrd` missing | *[updated]* installed in the project `.venv`, pinned in `requirements.txt` |"),
    ("## 6. What I have already verified (scratch checks only, nothing added to the project)",
     "## 6. Early feasibility checks *[updated: superseded by the automated tests, see `docs/replication_log.md`]*"),
    ("* Not yet checked: p-values, R², fitted values/residuals versus `eq_simulations_data.xls` (needs `xlrd`), the three simulation exercises, and the appendix variants.",
     "* *[updated]* Everything listed here as unchecked has since been checked and is covered by tests: p-values, R², fitted values and residuals, IRFs, decompositions, conditional forecasts and the GSCPI appendix variant. Still not done: Appendix PCE, SPF, V/U-in-price and non-linear V/U variants."),
    ("### 7.1 Series required and replacement status (Macrobond tickers to be searched and confirmed in Step 2.1; none are assumed here)",
     "### 7.1 Series required and replacement status *[updated: tickers now found and verified, see `docs/data_dictionary.md`]*"),
    ("| CPI all items SA (`CPIAUCSL`) | BLS/FRED, quarterly average | BLS CPI-U SA monthly → quarterly mean | Low. Note seasonal-factor revisions change history. |",
     "| CPI all items SA (`CPIAUCSL`) | BLS/FRED, **last month of the quarter** *[updated: not a quarterly average]* | BLS CPI-U SA monthly → last month of quarter | Low. Note seasonal-factor revisions change history. |"),
    ("| confirm whether Cleveland Fed model-based expectations are on Macrobond | **Unknown** |",
     "| *[updated]* on Macrobond (`usfcst0101`, `usfcst0110`), last month of quarter, exact match | Low |"),
    ("Needs your confirmation (see §9).", "*[updated]* Confirmed by the user on 2026-10-16."),
    ("## 9. Decisions needed from you", "## 9. Decisions *[updated: all resolved on 2026-10-16 or since]*"),
    ("1. **Pre-2001 history:**", "1. *(resolved: authors' public history through 2000Q4, Macrobond from 2001Q1)* **Pre-2001 history:**"),
    ("2. **Cleveland Fed expectations:**", "2. *(resolved: Cleveland Fed series are on Macrobond)* **Cleveland Fed expectations:**"),
    ("3. **GSCPI fill before 1997:**", "3. *(implemented: authors' convention, fill -0.035; post-1997 sensitivity not yet run)* **GSCPI fill before 1997:**"),
    ("4. **Which published baseline to treat as the \"answer\":**", "4. *(both replicated; the shipped IRF/decomposition/forecast outputs use the full-sample run)* **Which published baseline to treat as the \"answer\":**"),
    ("5. Install `xlrd`", "5. *(done)* Install `xlrd`"),
])
edit("docs/replication_log.md", [
    ("All checks are automated in `tests/` (34 tests; run", "All checks are automated in `tests/` (34 Phase-1 tests, part of a suite that now has 66; run"),
])
edit("docs/phase2a_findings.md", [("(44 tests in the suite pass)", "(the full suite, now 66 tests, passes)")])
edit("docs/phase2b_findings.md", [
    ("(48 tests in the\nsuite pass)", "(the full suite, now 66\ntests, passes)"),
    ("* Because GSCPI's own coefficients are poorly identified (t = 0.6 contemporaneous, sign flips), consider (as an\n  explicit, separately-labelled specification, not a silent change) a smoother functional form such as a\n  moving-average GSCPI term; this departs from the authors' lag structure and I have not tested it.",
     "* Because GSCPI's own coefficients are poorly identified (t = 0.6 contemporaneous, sign flips), a smoother or shorter\n  lag structure was proposed here; it has since been tested (and also genuine out-of-sample fit, HAC inference and\n  stability): see `docs/validation_report.md`. Note the in-sample comparison in §1-§4 above is one-sided: in a genuine\n  out-of-sample test (estimation through 2019Q4) GSCPI beats Google, not the reverse."),
])
print("docs corrected")
