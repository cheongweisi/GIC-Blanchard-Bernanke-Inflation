"""Phase 3: structural stability on the extended sample, post-2023 predictive-failure tests for the frozen Model A,
and descriptive persistence measures. Writes outputs/phase3/stability_*.csv."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS, PHASE3_PULL  # noqa: E402
from bb_inflation.data import phase3_data as P  # noqa: E402
from bb_inflation.estimation.inference import chow_predictive, cusum_ols, sup_f_partial  # noqa: E402
from bb_inflation.extension.models import fit, specs_for_end, standard_models  # noqa: E402

OUT = OUTPUTS / "phase3"
OUT.mkdir(parents=True, exist_ok=True)
NB = 300


def groups(eq, r):
    n = lambda *vs: sum((r.block_names(x) for x in vs), [])        # noqa: E731
    if eq == "gw":
        return {"intercept + V/U": ["const"] + n("vu"), "persistence vs expectations (gw, cf1)": n("gw", "cf1")}
    if eq == "gcpi":
        return {"wage pass-through (gw, lagged gcpi)": n("gw", "gcpi"), "energy + food": n("grpe", "grpf"),
                "shortage (GSCPI 2q mean)": n("shortagema2"), "intercept + productivity": ["const"] + n("magpty")}
    if eq == "cf1":
        return {"expectations weights (cf1, cf10, gcpi)": n("cf1", "cf10", "gcpi")}
    return {"expectations weights (cf10, gcpi)": n("cf10", "gcpi")}


def main() -> None:
    p3 = P.build(PHASE3_PULL)
    last = str(p3.last_complete)
    ms = standard_models(last)
    B, A = fit(ms["B"], p3.data, last), fit(ms["A"], p3.data, last)
    rows = []
    for eq in ("gw", "gcpi", "cf1", "cf10"):
        r = B[eq]
        cus = cusum_ols(r)
        rows.append({"model": "B", "equation": eq, "sample": f"{r.sample[0]}-{r.sample[1]}", "test": "CUSUM (OLS residuals)",
                     "stat": cus["cusum_stat"], "break after": "", "p": cus["p"]})
        for g, cols in groups(eq, r).items():
            o = sup_f_partial(r, p3.data, cols, nboot=NB)
            rows.append({"model": "B", "equation": eq, "sample": f"{r.sample[0]}-{r.sample[1]}", "test": f"sup-F: {g}",
                         "stat": o["supF"], "break after": o["break_after"], "p": o["p_boot"]})
    pd.DataFrame(rows).to_csv(OUT / "stability_supF_B.csv", index=False)

    # Frozen A: do the equations estimated to 2023Q2 predict 2023Q3-2026Q2 (Chow predictive failure)?
    post = list(pd.period_range("2023Q3", p3.last_complete, freq="Q"))
    crows = []
    for eq in ("gw", "gcpi", "cf1", "cf10"):
        # keep only quarters whose regressors exist (the wage equation loses 2026Q1-Q2 because V/U 2025Q4 is missing)
        from bb_inflation.estimation.rls import design
        X = design(A[eq].spec, p3.data)[list(A[eq].coef.index)]
        ok = [q for q in post if not X.loc[q].isna().any() and not np.isnan(p3.data.loc[q, eq])]
        c = chow_predictive(A[eq], p3.data, ok)
        crows.append({"equation": eq, "estimated to": "2023Q2", "test quarters": f"{ok[0]}-{ok[-1]} (n={len(ok)})", "F": c["F"],
                      "df": f"({c['df1']},{c['df2']})", "p": c["p"]})
    pd.DataFrame(crows).to_csv(OUT / "stability_chow_post2023.csv", index=False)

    # descriptive persistence: AR(4) sums of gcpi, gw, cf1, cf10 over windows
    prow = []
    d = p3.data_bridged
    for lab, (lo, hi) in {"1990Q1-2019Q4": ("1990Q1", "2019Q4"), "1990Q1-2023Q2": ("1990Q1", "2023Q2"), "1990Q1-2026Q2": ("1990Q1", "2026Q2"),
                          "2010Q1-2019Q4": ("2010Q1", "2019Q4"), "2010Q1-2026Q2": ("2010Q1", "2026Q2"), "2015Q1-2026Q2": ("2015Q1", "2026Q2"),
                          "2023Q3-2026Q2 (n=12; indicative)": ("2023Q3", "2026Q2")}.items():
        for v in ("gcpi", "gw", "cf1", "cf10"):
            s = d[v]
            X = pd.concat([s.shift(i) for i in range(1, 5)], axis=1)
            X.columns = [f"l{i}" for i in range(1, 5)]
            X["c"] = 1.0
            fr = pd.concat([s.rename("y"), X], axis=1).loc[lo:hi].dropna()
            if len(fr) < 8:
                continue
            b = np.linalg.lstsq(fr.drop(columns="y").values, fr["y"].values, rcond=None)[0]
            prow.append({"window": lab, "var": v, "AR(4) sum": float(b[:4].sum()), "n": len(fr),
                         "mean level": float(s.loc[lo:hi].mean())})
    pd.DataFrame(prow).to_csv(OUT / "stability_ar4_persistence.csv", index=False)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).round(3).to_string())
    print(pd.DataFrame(crows).round(3).to_string())
    print(pd.DataFrame(prow).pivot_table(index="window", columns="var", values="AR(4) sum", sort=False).round(2).to_string())


if __name__ == "__main__":
    main()
