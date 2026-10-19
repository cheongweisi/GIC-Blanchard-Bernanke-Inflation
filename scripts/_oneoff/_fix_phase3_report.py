"""One-off corrections to docs/phase3_report.md after checking every quoted number against outputs/phase3."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "docs" / "phase3_report.md"
s = p.read_text(encoding="utf-8")
pairs = [
    ("(effective sample 59, 82, 99 of\n  146 observations in the price equation)", "(effective sample 57, 98, 119 of\n  146 observations)"),
    ("moves every sum of\n   coefficients by less than 0.1 HAC standard errors of the 2023Q2 estimate (Model A):",
     "moves every sum of\n   coefficients by at most 0.33 HAC standard errors of the 2023Q2 estimate (Model A; at most 0.19 in the price equation):"),
    ("* **A vs B:** no coefficient moves by more than 0.1 of its standard error's order; no instability flag trips.",
     "* **A vs B:** the largest change is 0.33 HAC standard errors (the cf10 weights); no instability flag trips."),
    ("AR(4) is at least as good as any structural variant (1.36 / 1.24 / 1.14 / 1.45 against 1.33 / 1.45 / 1.30 / 1.35 for A).",
     "AR(4) is at least as good as any structural variant (1.36 / 1.24 / 1.14 / 1.45 against 1.33 / 1.43 / 1.28 / 1.32 for A)."),
    ("at each of 86 origins (2004Q4-2025Q1+)", "at each of 86 origins (2004Q4-2026Q1)"),
    ("The pseudo-out-of-sample result holds before\n  COVID, during 2020-23 and after 2023 (`fig_p3_oos.png`).",
     "Weighting does not help in any of the three target periods (before 2020 it ties with the unweighted model at 2-4 quarters; during 2020-23\n  and after 2023 the unweighted model is better; `fig_p3_oos.png`)."),
    ("* Extreme values since 2023Q3: energy growth +35% annualised in 2026Q1 (relative price index, 3.7 s.d. beyond its 1990-2019\n  spread would be a large outlier, see `outputs/phase3/data_qa_ranges.csv`); no data errors found.",
     "* Outliers since 2023Q3 (`outputs/phase3/data_qa_ranges.csv`): relative energy prices rose 35% annualised in 2026Q1, the largest energy\n  move since 2022 but within the 1990-2019 range (z = 1.5); V/U (0.95-1.47) and GSCPI (peak 1.6 in 2026Q2) sit well above their pre-2020\n  distributions (z = 3.4 and 4.7). No data errors were found."),
    ("V/U -0.3 to -0.4, and the residual is -1.2 to -1.3 pp (see Answer 4).", "V/U -0.3 to -0.4, and the residual is -1.15 to -1.30 pp (see Answer 4)."),
    ("actual inflation came in 1.2-1.3 pp lower than the model implies;", "actual inflation came in 1.15-1.30 pp lower than the model implies;"),
    ("* The 2026 energy spike is a single large observation; the weaker-pass-through reading rests on 2026Q1 and 12 residuals.",
     "* The 2026 energy spike (the largest since 2022) is a single large observation; the weaker-pass-through reading rests on 2026Q1 and 12 residuals."),
]
for a, b in pairs:
    assert a in s, a[:70]
    s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("report corrected")
