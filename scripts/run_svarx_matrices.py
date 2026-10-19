"""Expand production Model B* into the structural SVAR-X matrix form  A0 y_t = c + sum A_i y_{t-i} + sum B_j x_{t-j} + e_t.

Reads the B*-2026 (= production B*) columns of outputs/phase4c/coef_{gw,gcpi,cf1,cf10}.csv and
outputs/phase3_supp/reval_coef_summary.csv. Writes outputs/svarx/ (xlsx + csv) and docs/svarx_Bstar_note.md.
Nothing from Phases 1-4c is modified.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs" / "svarx"
OUT.mkdir(parents=True, exist_ok=True)

# usage: run_svarx_matrices.py [ma2 | l01]
#   ma2 = production B* (shortage = GSCPI 2-qtr mean, read from the stored Phase 4c tables)
#   l01 = variant B*(L0-1): same data/equations, shortage = GSCPI at lags 0 and 1 as separate regressors (estimated here)
VAR = sys.argv[1] if len(sys.argv) > 1 else "ma2"
TAG = "" if VAR == "ma2" else "_L01"
NAME = "Model B*" if VAR == "ma2" else "Model B*(L0-1) [variant, not production]"
SH = "shortagema2" if VAR == "ma2" else "shortage"

Y = ["gw", "gcpi", "cf10", "cf1"]                       # row/column order of the slide: wage, CPI, long-run, short-run
Y_LAB = ["g^w", "pi", "pi^e,L", "pi^e,S"]
X = ["magpty", "vu", "diffcpicf", "grpe", "grpf", SH, "D2020Q2", "D2020Q3"]
X_LAB = ["magpty", "V/U", "catchup", "grpe", "grpf", "shortage", "D20Q2", "D20Q3"]
NLAG = 4
PFX = "B*-2026"


def stored_long() -> pd.DataFrame:
    frames = []
    for eq, f in (("gw", "coef_gw"), ("gcpi", "coef_gcpi"), ("cf1", "coef_cf1"), ("cf10", "coef_cf10")):
        d = pd.read_csv(ROOT / "outputs" / "phase4c" / f"{f}.csv")
        d = d[["coefficient", f"{PFX}: estimate", f"{PFX}: HAC s.e.", f"{PFX}: HAC p", f"{PFX}: classical s.e."]].dropna()
        d.columns = ["name", "coef", "se_hac", "p_hac", "se_classical"]
        d.insert(0, "eq", eq)
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def estimated(variant: str):
    """Re-estimate B* for a shortage variant on the Phase 3 supplement dataset (V/U 2025Q4 bridged); HAC L=4."""
    from bb_inflation.estimation.inference import coef_table, with_hac
    from bb_inflation.extension import coefs as CO
    from bb_inflation.extension.models import ModelSpec, fit
    from bb_inflation.supplement import context as C
    ctx = C.load()
    ds = ctx.data_star
    res = fit(ModelSpec("B*", variant, variant=variant), ds, ctx.last)
    rows = []
    for eq in ("gw", "gcpi", "cf1", "cf10"):
        t = coef_table(res[eq], with_hac(res[eq], ds))
        for name, r in t.iterrows():
            rows.append({"eq": eq, "name": name, "coef": r.beta, "se_hac": r.se_hac, "p_hac": np.nan, "se_classical": r.se_classic})
    summ = CO.coef_summary({"B*": res}, ds, {"B*": variant})
    return pd.DataFrame(rows), summ


if VAR == "ma2":
    long = stored_long()
else:
    chk, _ = estimated("gscpi_ma2")      # sanity: the estimation path must reproduce the stored production coefficients
    st = stored_long().merge(chk, on=["eq", "name"], suffixes=("", "_re"))
    print("check vs stored B*: max |coef diff| =", float((st.coef - st.coef_re).abs().max()),
          "max |HAC se diff| =", float((st.se_hac - st.se_hac_re).abs().max()), "n =", len(st))
    long, VSUMS = estimated("gscpi2")

mats = {k: {"coef": np.zeros(shape), "se": np.zeros(shape), "se_cl": np.zeros(shape)}
        for k, shape in [("A0", (4, 4))] + [(f"A{i}", (4, 4)) for i in range(1, NLAG + 1)]
        + [(f"B{j}", (4, len(X))) for j in range(NLAG + 1)] + [("c", (4, 1))]}
where = []
for r in long.itertuples():
    row = Y.index(r.eq)
    if r.name == "const":
        key, col, sign = "c", 0, 1
        lab = "c"
    elif r.name.startswith("D2020"):
        key, col, sign, lab = "B0", X.index(r.name), 1, f"B0[{r.eq},{r.name}]"
    else:
        var, lag = r.name.rsplit("_L", 1)
        lag = int(lag)
        if var in Y:
            key, col = ("A0" if lag == 0 else f"A{lag}"), Y.index(var)
            sign = -1 if lag == 0 else 1
        else:
            key, col, sign = f"B{lag}", X.index(var), 1
        lab = f"{key}[{r.eq},{var}]"
    mats[key]["coef"][row, col] = sign * r.coef
    mats[key]["se"][row, col] = r.se_hac
    mats[key]["se_cl"][row, col] = r.se_classical
    where.append(lab)
long["matrix_position"] = where
for i in range(4):
    mats["A0"]["coef"][i, i] = 1.0
long["t_hac"] = long.coef / long.se_hac
long.to_csv(OUT / f"Bstar{TAG}_coefficients_long.csv", index=False)

a21 = -mats["A0"]["coef"][1, 0]; a32 = -mats["A0"]["coef"][2, 1]
a42 = -mats["A0"]["coef"][3, 1]; a43 = -mats["A0"]["coef"][3, 2]
se = mats["A0"]["se"]
if VAR == "ma2":
    sums = pd.read_csv(ROOT / "outputs" / "phase3_supp" / "reval_coef_summary.csv")
    sums = sums[sums.model == "B*"].set_index(["eq", "block"])
else:
    sums = VSUMS.set_index(["eq", "block"])


def S(eq, blk):
    r = sums.loc[(eq, blk)]
    return r["sum"], r["se_hac"], r["p_hac"]


# ---------------------------------------------------------------- Excel
def block_sheet(writer):
    rows, r0 = [], 0
    ws_name = "Matrices"
    parts = []
    for k in ["A0"] + [f"A{i}" for i in range(1, 5)] + [f"B{j}" for j in range(5)] + ["c"]:
        cols = Y_LAB if k.startswith("A") else (X_LAB if k.startswith("B") else ["const"])
        for kind, title in (("coef", "estimate"), ("se", "HAC s.e. (Newey-West, 4 lags)"), ("se_cl", "classical s.e.")):
            df = pd.DataFrame(mats[k][kind], index=[f"eq: {y}" for y in Y], columns=cols)
            parts.append((f"{k} - {title}", df))
    pd.DataFrame().to_excel(writer, sheet_name=ws_name)
    ws = writer.sheets[ws_name]
    r = 0
    for title, df in parts:
        ws.cell(row=r + 1, column=1, value=title)
        df.to_excel(writer, sheet_name=ws_name, startrow=r + 1)
        r += len(df) + 3


SHORT_TXT = ("shortage = GSCPI 2-qtr MA" if VAR == "ma2" else "shortage = GSCPI at lags 0 and 1 as separate regressors")
XL = OUT / f"svarx_Bstar{TAG}_matrices.xlsx"
TMP = XL.with_name(XL.stem + "_tmp.xlsx")
with pd.ExcelWriter(TMP) as w:
    pd.DataFrame({
        "item": ["model", "sample", "N", "y_t order", "x_t order", "s.e.", "units", "source"],
        "value": [f"{NAME}: unweighted restricted LS, {SHORT_TXT}, V/U 2025Q4 bridged",
                  "1990Q1-2026Q2", "146 per equation (wage eq. uses the bridged 2025Q4 V/U)",
                  "g^w (ECI wage), pi (CPI), pi^e,L (Cleveland 10y), pi^e,S (Cleveland 1y)",
                  f"magpty, V/U, catch-up, grpe, grpf, shortage{'(ma2)' if VAR == 'ma2' else ''}, D2020Q2, D2020Q3 (constant in c)",
                  "HAC = Newey-West, 4 lags, restriction-adjusted; classical also shown",
                  "gw, gcpi, grpe, grpf, magpty = quarterly annualised log growth (400*dln); V/U ratio; expectations and shortage in levels",
                  "outputs/phase4c/coef_*.csv, outputs/phase3_supp/reval_coef_summary.csv"]}).to_excel(w, sheet_name="ReadMe", index=False)
    block_sheet(w)
    long.to_excel(w, sheet_name="Coefficients_long", index=False)
    sums.reset_index().to_excel(w, sheet_name="Block_sums", index=False)


import os  # noqa: E402

try:
    os.replace(TMP, XL)
    print("wrote", XL)
except PermissionError:
    TMP.unlink(missing_ok=True)
    print("workbook", XL.name, "is open elsewhere (Excel?); left unchanged. Close it and re-run to refresh the workbook.")

# ---------------------------------------------------------------- markdown (LaTeX; see _svarx_note.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _svarx_note as N  # noqa: E402

text = N.render(VAR, mats, X, sums, S, {"a21": a21, "a32": a32, "a42": a42, "a43": a43}, se, mats["A1"]["coef"][0, 3], None)
(ROOT / "docs" / f"svarx_Bstar{TAG}_note.md").write_text(text, encoding="utf-8")
print("wrote docs/" + f"svarx_Bstar{TAG}_note.md")
print("a21 a32 a42 a43 =", a21, a32, a42, a43)
