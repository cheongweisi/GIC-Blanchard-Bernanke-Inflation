"""Phase 3 supplement: re-run every Phase 3 check that touches the bridged V/U 2025Q4 (Model B*, estimation through 2026Q2 with the
flagged bridge). Phase 3 outputs are not overwritten; results go to outputs/phase3_supp/reval_*.csv.

 (a) coefficient sums and plausibility flags   (b) stability tests of the extended sample + Chow predictive failure of frozen A
 (c) historical decomposition windows           (d) pseudo-out-of-sample evaluation and the recent-weighting selection rule
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import run_phase3_oos as P3OOS  # noqa: E402
import run_phase3_stability as P3ST  # noqa: E402
from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.estimation.inference import chow_predictive, cusum_ols, sup_f_partial  # noqa: E402
from bb_inflation.estimation.rls import design  # noqa: E402
from bb_inflation.extension import coefs as CO  # noqa: E402
from bb_inflation.extension import history as HH  # noqa: E402
from bb_inflation.extension import pseudo_oos as O  # noqa: E402
from bb_inflation.extension.models import ModelSpec, fit, standard_models  # noqa: E402
from bb_inflation.supplement import context as C  # noqa: E402

OUT = OUTPUTS / "phase3_supp"
NB = 300


def main(run_oos: bool = True) -> None:
    ctx = C.load()
    p3, last, ds = ctx.p3, ctx.last, ctx.data_star
    ms = standard_models(last)

    # ---- (a) coefficients
    res = {"A": fit(ms["A"], ds, last), "B (Phase 3)": fit(ms["B"], p3.data, last), "B*": fit(ms["B"], ds, last),
           "C15*": fit(ms["C15"], ds, last), "B5*": fit(ms["B5"], ds, last)}
    var_of = {"A": "gscpi_ma2", "B (Phase 3)": "gscpi_ma2", "B*": "gscpi_ma2", "C15*": "gscpi_ma2", "B5*": "gscpi5"}
    summ = CO.coef_summary(res, ds, var_of)
    summ.to_csv(OUT / "reval_coef_summary.csv", index=False)
    fl = CO.flags(summ[~summ.model.isin(["B5*"])], "A")
    fl.to_csv(OUT / "reval_flags.csv", index=False)
    piv = summ[summ.model.isin(["A", "B (Phase 3)", "B*", "C15*"])].pivot_table(index=["eq", "block"], columns="model", values="sum", sort=False)
    piv["B* - B (Phase 3)"] = piv["B*"] - piv["B (Phase 3)"]
    se = summ[summ.model == "A"].set_index(["eq", "block"])["se_hac"]
    piv["(B* - B) in HAC se of A"] = piv["B* - B (Phase 3)"] / se
    piv.to_csv(OUT / "reval_coef_B_vs_Bstar.csv")
    print(piv.round(3).to_string())
    print("flags tripped:", fl[fl.flag][["model", "kind", "rule"]].to_string())

    # ---- (b) stability on the extended sample (Model B*), Chow predictive failure of frozen A
    B = res["B*"]
    rows = []
    for eq in ("gw", "gcpi", "cf1", "cf10"):
        r = B[eq]
        cus = cusum_ols(r)
        rows.append({"model": "B*", "equation": eq, "sample": f"{r.sample[0]}-{r.sample[1]}", "test": "CUSUM (OLS residuals)", "stat": cus["cusum_stat"],
                     "break after": "", "p": cus["p"]})
        for g, cols in P3ST.groups(eq, r).items():
            o = sup_f_partial(r, ds, cols, nboot=NB)
            rows.append({"model": "B*", "equation": eq, "sample": f"{r.sample[0]}-{r.sample[1]}", "test": f"sup-F: {g}", "stat": o["supF"],
                         "break after": o["break_after"], "p": o["p_boot"]})
    pd.DataFrame(rows).to_csv(OUT / "reval_stability_supF_Bstar.csv", index=False)
    A = res["A"]
    post = list(pd.period_range("2023Q3", ctx.p3.last_complete, freq="Q"))
    crows = []
    for eq in ("gw", "gcpi", "cf1", "cf10"):
        X = design(A[eq].spec, ds)[list(A[eq].coef.index)]
        ok = [q for q in post if not X.loc[q].isna().any() and not np.isnan(ds.loc[q, eq])]
        c = chow_predictive(A[eq], ds, ok)
        crows.append({"equation": eq, "test quarters": f"{ok[0]}-{ok[-1]} (n={len(ok)})", "F": c["F"], "df": f"({c['df1']},{c['df2']})", "p": c["p"]})
    pd.DataFrame(crows).to_csv(OUT / "reval_chow_post2023_A.csv", index=False)
    print(pd.DataFrame(rows).round(3).to_string())
    print(pd.DataFrame(crows).round(3).to_string())

    # ---- (c) decomposition windows
    windows = {"2021Q1-2023Q2": ("2021Q1", "2023Q2"), "2023Q3-2026Q2": ("2023Q3", "2026Q2"), "2026Q1-Q2": ("2026Q1", "2026Q2")}
    decs = HH.decompositions({"A": res["A"], "B*": res["B*"], "C15*": res["C15*"]}, {"A": ms["A"], "B*": ms["B"], "C15*": ms["C15"]}, ds, C.P.GSCPI_FILL)
    tab = HH.contribution_table(decs, ds, "gcpi", windows)
    tab.to_csv(OUT / "reval_decomp_gcpi.csv", index=False)
    print(tab.round(2).to_string())

    # ---- (d) pseudo-OOS with the bridged dataset
    if run_oos:
        cfgs = {k: v for k, v in P3OOS.configs().items() if k in ("U", "W5", "W10", "W15")}
        origins = list(pd.period_range("2004Q4", p3.last_complete - 1, freq="Q"))
        rec = O.run(ds, ds, last, cfgs, origins)
        Afz = fit(ModelSpec("A", "frozen", end="2023Q2"), ds, last)
        recA = O.run(ds, ds, last, {"A": ModelSpec("A", "frozen")}, [o for o in origins if o >= pd.Period("2023Q2", "Q")], frozen={"A": Afz},
                     include_ar4=False)
        rec.to_csv(OUT / "reval_oos_records.csv", index=False)
        recA.to_csv(OUT / "reval_oos_records_frozenA.csv", index=False)
        summ_new = O.summarize(rec)
        summ_new.to_csv(OUT / "reval_oos_summary.csv", index=False)
        sel = O.select_half_life(summ_new, ["W5", "W10", "W15"], "U")
        pd.Series({"chosen": sel["chosen"], "best_candidate": sel["best_candidate"], **{f"score {k}": v for k, v in sel["scores"].items()}}).to_csv(
            OUT / "reval_oos_selection.csv", header=["value"])
        old = pd.read_csv(OUTPUTS / "phase3" / "oos_summary.csv")
        key = ["model", "mode", "var", "target bucket", "horizon"]
        cmp = summ_new.merge(old, on=key, suffixes=(" new", " Phase3"))
        cmp["RMSE change"] = cmp["RMSE new"] - cmp["RMSE Phase3"]
        cmp.to_csv(OUT / "reval_oos_vs_phase3.csv", index=False)
        c = cmp[(cmp["var"] == "gcpi") & (cmp["target bucket"] == "all targets") & cmp["model"].isin(["U", "W15", "AR4"])]
        print(c.pivot_table(index=["model", "mode"], columns="horizon", values=["RMSE new", "RMSE Phase3"]).round(3).to_string())
        print("max |RMSE change| all rows:", cmp["RMSE change"].abs().max())
        print(sel)
        # frozen A, origins from 2023Q2
        post_rec = pd.concat([rec, recA], ignore_index=True)
        post_rec = post_rec[pd.PeriodIndex(post_rec["origin"], freq="Q") >= pd.Period("2023Q2", "Q")]
        O.summarize(post_rec, by_bucket=False).to_csv(OUT / "reval_oos_post2023_origins.csv", index=False)


if __name__ == "__main__":
    main()
