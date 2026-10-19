"""Phase 4c: robustness classification tables and the coefficient-comparison workbook (every sheet is also a CSV in outputs/phase4c/)."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

from bb_inflation.phase4c import samples as S  # noqa: E402

OUT = S.OUT
rd = lambda n: pd.read_csv(OUT / n)                      # noqa: E731

# ---------------------------------------------------------------------------------------------------------------------------------
# robustness: coefficient blocks
fl = rd("ident_blocks.csv")
ch = rd("block_changes.csv")
nb = rd("block_changes_null_bootstrap.csv")
sh = rd("stability_shift_tests.csv")
rows = []
for _, f in fl.iterrows():
    eq, b = f["eq"], f["block"]

    def pv(frm, to, tab, col):
        r = tab[(tab["eq"] == eq) & (tab.block == b) & (tab["from"] == frm) & (tab["to"] == to)]
        return float(r[col].iloc[0]) if len(r) else np.nan
    p1926 = pv("B*-2019", "B*-2026", ch, "p (overlap-adjusted)")
    p1923 = pv("B*-2019", "B*-2023", ch, "p (overlap-adjusted)")
    p2326 = pv("B*-2023", "B*-2026", ch, "p (overlap-adjusted)")
    n1926 = pv("B*-2019", "B*-2026", nb, "p (observed vs null, bias-centred)")
    n1923 = pv("B*-2019", "B*-2023", nb, "p (observed vs null, bias-centred)")
    s = sh[(sh["eq"] == eq) & (sh.block == b) & (sh["sample end"] == "2026Q2")]
    ps = float(s.p.iloc[0]) if len(s) else np.nan
    moves = (min(p1926, p1923) < 0.10) or (min(n1926, n1923) < 0.10)
    if moves:
        cls = "Moves across samples (change unusual for constant parameters)"
    elif not f["significant at 5% in B*-2026"]:
        cls = "Stable, but not distinguishable from zero"
    elif f["weak in B*-2019"]:
        cls = "Identified precisely only once post-2019 data are added"
    else:
        cls = "Robust: stable, significant, identified pre-2020"
    rows.append({"eq": eq, "block": b, "label": f["label"], "sum B*-2019": f["sum B*-2019"], "sum B*-2023": f["sum B*-2023"], "sum B*-2026": f["sum B*-2026"],
                 "significant at 5% (B*-2026)": f["significant at 5% in B*-2026"], "weak in B*-2019": f["weak in B*-2019"], "sign stable": f["sign stable"],
                 "min p overlap-adjusted (2019->2023, 2019->2026)": min(p1926, p1923), "min p bootstrap null (2019->2023, 2019->2026)": min(n1926, n1923),
                 "p overlap-adjusted (2023->2026)": p2326, "p post-2019 shift test (B*-2026 sample)": ps,
                 "post-2019 shift flag (p<0.10; partial test, one test per block)": bool(ps < 0.10) if pd.notna(ps) else False, "classification": cls})
rb = pd.DataFrame(rows)
rb.to_csv(OUT / "robustness_blocks.csv", index=False)

# robustness: multipliers (headline convention)
st = rd("irf_stats.csv")
df = rd("irf_stat_differences.csv")
rows = []
KEYSTATS = [("gcpi", "h=4"), ("gcpi", "h=12"), ("gcpi", "price level, cumulative to h=4 (%)"), ("gcpi", "price level, cumulative to h=12 (%)"), ("gw", "h=12"), ("cf1", "h=12"), ("cf10", "h=12")]
for shock in ["W1", "W2", "O10", "O30", "V1", "V1P", "G1", "G1S", "E1", "E10"]:
    for var, stat in KEYSTATS:
        a = st[(st.convention == "nominal") & (st["shock"] == shock) & (st.variable == var) & (st.statistic == stat)].set_index("vintage")
        if "B*-2026" not in a.index:
            continue
        e26 = a.loc["B*-2026"]
        d = df[(df.convention == "nominal") & (df["shock"] == shock) & (df.variable == var) & (df.statistic == stat)].set_index("change")
        p1926 = float(d.loc["B*-2019 -> B*-2026", "p (two-sided, from draws)"])
        p2326 = float(d.loc["B*-2023 -> B*-2026", "p (two-sided, from draws)"])
        excl = bool(e26.lo90 > 0 or e26.hi90 < 0)
        cls = ("Moves across samples (p<0.10)" if min(p1926, p2326) < 0.10 else "Suggestive change, not conclusive (0.10<=p<0.20)" if min(p1926, p2326) < 0.20 else ("Robust: stable and 90% band excludes zero" if excl else "Stable, but band includes zero"))
        rows.append({"shock": shock, "variable": var, "statistic": stat, "B*-2019": a.loc["B*-2019", "point"], "B*-2023": a.loc["B*-2023", "point"], "B*-2026": e26.point,
                     "B*-2026 90% band": f"[{e26.lo90:.3f}, {e26.hi90:.3f}]", "p (2019->2026)": p1926, "p (2023->2026)": p2326, "classification": cls})
rm = pd.DataFrame(rows)
rm.to_csv(OUT / "robustness_multipliers.csv", index=False)

# ---------------------------------------------------------------------------------------------------------------------------------
README = [
    ("Phase 4c: historical parameter stability and impulse-response comparison of Model B*", ""),
    ("Status", "Diagnostic study. The production B* coefficients and the Phase 4 forecasting code are untouched; nothing here is a forecast."),
    ("Specification (held fixed)", "Model B*: four restricted-LS equations (authors' lags and homogeneity restrictions), shortage block = 2-quarter mean of GSCPI (lag 0), V/U 2025Q4 bridged, start 1990Q1, wage dummies for 2020Q2/Q3 only when those quarters are in the sample."),
    ("B*-2019 / B*-2023 / B*-2026", "All four equations estimated 1990Q1-2019Q4 / 1990Q1-2023Q4 / 1990Q1-2026Q2. B*-2026 equals production B* (checked to machine precision)."),
    ("Hybrid (B* data)", "Authors' hybrid design on B* data and specification: wage, cf1, cf10 to 2019Q4, price equation to 2023Q2. Reference only."),
    ("Authors (published hybrid)", "The authors' own data (Google 'shortage', 5 lags), their shipped coefficient files; wage/cf1/cf10 1990Q1-2019Q4, price 1990Q1-2023Q2. Reference only; not comparable for the supply-chain variable."),
    ("Standard errors", "Newey-West HAC (4 lags, small-sample factor), t critical values with residual df. Classical s.e. are also reported. 'overlap-adjusted' tests use the stacked influence-function covariance of the nested samples (bb_inflation/phase4c/stack.py)."),
    ("Bands", "90% (5th-95th percentile) over 2000 joint coefficient draws; parameter uncertainty only (not specification, residual, bridge or driver uncertainty); equations drawn independently."),
    ("IRF units", "gcpi, gw: annualised pp; cf1, cf10: pp. h = 0 is the shock quarter. Price level (%) = cumulative sum of annualised CPI responses / 4."),
    ("Energy and food convention", "'nominal' (headline, Phase 4): nominal energy/food growth exogenous, relative prices endogenous. 'relative': relative prices fixed (authors' convention). They differ for every shock that moves wages."),
    ("Oil bridge", "Phase 4 bridge (monthly, elasticity 0.297), identical for every vintage; calibrated assumption, not an estimate of this study. Sensitivity sheet: re-estimated by vintage and 0.24-0.40 range."),
    ("Sheets", "Checks; Coef_*; Block_sums; Block_changes; Changes_null_boot; Derived_multipliers; Ident_blocks; Ident_GSCPI; GSCPI_leave_out; Shift_tests; Recursive; Robust_blocks; Robust_multipliers; IRF_shocks; Multipliers_nominal; Multipliers_relative; IRF_stats; IRF_diffs; IRF_paths; Persistence_yoy; Oil_bridge; Authors_*"),
]
sheets = [("Checks", "est_checks.csv"), ("Coef_gw", "coef_gw.csv"), ("Coef_gcpi", "coef_gcpi.csv"), ("Coef_cf1", "coef_cf1.csv"), ("Coef_cf10", "coef_cf10.csv"),
          ("Block_sums", "blocks.csv"), ("Block_changes", "block_changes.csv"), ("Changes_null_boot", "block_changes_null_bootstrap.csv"),
          ("Derived_multipliers", "multipliers_derived.csv"), ("Ident_blocks", "ident_blocks.csv"), ("Ident_GSCPI", "ident_gscpi.csv"),
          ("GSCPI_leave_out", "ident_gscpi_leave_out.csv"), ("Shift_tests", "stability_shift_tests.csv"), ("Recursive", "stability_recursive.csv"),
          ("Robust_blocks", "robustness_blocks.csv"), ("Robust_multipliers", "robustness_multipliers.csv"), ("IRF_shocks", "irf_shock_catalogue.csv"),
          ("IRF_stats", "irf_stats.csv"), ("IRF_diffs", "irf_stat_differences.csv"), ("IRF_paths", "irf_paths.csv"), ("Persistence_yoy", "irf_persistence_yoy.csv"),
          ("Oil_bridge", "irf_oil_bridge_sensitivity.csv"), ("Price_spec_robustness", "robust_price_spec.csv"), ("Authors_samples", "authors_samples.csv"), ("Authors_IRF_check", "authors_irf_replication.csv"),
          ("Authors_IRF_text", "authors_irf_paper_text_check.csv"), ("Authors_multipliers", "authors_multipliers.csv"), ("Authors_published", "authors_published_summary_stats.csv")]
mult = rd("multipliers_comparable.csv")
with pd.ExcelWriter(OUT / "phase4c_coefficient_comparison.xlsx", engine="openpyxl") as xw:
    pd.DataFrame(README, columns=["item", "description"]).to_excel(xw, sheet_name="README", index=False)
    mult[mult.convention == "nominal"].to_excel(xw, sheet_name="Multipliers_nominal", index=False)
    mult[mult.convention == "relative"].to_excel(xw, sheet_name="Multipliers_relative", index=False)
    for name, f in sheets:
        rd(f).to_excel(xw, sheet_name=name, index=False)
    for ws in xw.book.worksheets:
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="2A78D6")
            c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        for i, col in enumerate(ws.columns, 1):
            w = max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:60])
            ws.column_dimensions[get_column_letter(i)].width = min(max(10, w + 2), 70 if ws.title == "README" else 45)
        if ws.title == "README":
            for r in ws.iter_rows(min_row=2):
                for c in r:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
print("workbook sheets:", len(sheets) + 3)
print(rb[["eq", "block", "classification"]].to_string())
print(rm.groupby("classification").size())
