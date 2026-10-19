"""Validation 4b: structural-stability checks (sup-F for partial breaks, CUSUM, Chow predictive failure, recursive
estimates). Writes outputs/validation/stability_*.csv and figures."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.data.authors_data import load_raw  # noqa: E402
from bb_inflation.estimation.inference import chow_predictive, cusum_ols, recursive_sums, sup_f_partial  # noqa: E402
from bb_inflation.validation import oos  # noqa: E402
from bb_inflation.validation.specs import VARIANTS, data_for, datasets, equations_for  # noqa: E402

OUT = OUTPUTS / "validation"
OUT.mkdir(parents=True, exist_ok=True)
SPECS = ["google5", "gscpi5", "gscpi_ma2"]
NB = 200
TEST_Q = list(pd.period_range("2020Q1", "2023Q2", freq="Q"))
TEST_Q_EX = [q for q in TEST_Q if str(q) not in ("2020Q2", "2020Q3")]


def names(res, var):
    return res.block_names(var)


def groups(eq, res, v):
    n = lambda *vs: sum((names(res, x) for x in vs), [])        # noqa: E731
    if eq == "gw":
        return {"intercept + V/U": ["const"] + n("vu"), "persistence vs expectations (gw, cf1)": n("gw", "cf1"),
                "catch-up + productivity": n("diffcpicf", "magpty")}
    if eq == "gcpi":
        g = {"wage pass-through (gw, lagged gcpi)": n("gw", "gcpi"), "energy + food": n("grpe", "grpf"),
             "intercept + productivity": ["const"] + n("magpty")}
        if v.block is not None:
            g["shortage block"] = n(v.block.var)
        return g
    if eq == "cf1":
        return {"expectations weights (cf1, cf10, gcpi)": n("cf1", "cf10", "gcpi")}
    return {"expectations weights (cf10, gcpi)": n("cf10", "gcpi")}


def main() -> None:
    ds = datasets(load_raw())
    rows, chow_rows, rec = [], [], {}
    for sp in SPECS:
        v = VARIANTS[sp]
        data = data_for(v, ds)
        genuine = oos.fit_regime(v, data, "genuine")          # all equations through 2019Q4
        full = oos.fit_regime(v, data, "hybrid")              # price eq through 2023Q2 (authors' design)
        for eq in ("gw", "gcpi", "cf1", "cf10"):
            if eq != "gcpi" and sp != "gscpi_ma2":
                continue                                      # wage/expectation equations do not depend on the shortage spec
            res = full[eq]                                    # gw/cf1/cf10: through 2019Q4; gcpi: through 2023Q2
            cus = cusum_ols(res)
            for gname, cols in groups(eq, res, v).items():
                out = sup_f_partial(res, data, cols, nboot=NB)
                rows.append({"spec": sp, "equation": eq, "sample": f"1990Q1-{res.sample[1]}", "test": f"sup-F: {gname}",
                             "stat": out["supF"], "break after": out["break_after"], "p (boot)": out["p_boot"],
                             "crit 5%": out["crit95"]})
            rows.append({"spec": sp, "equation": eq, "sample": f"1990Q1-{res.sample[1]}", "test": "CUSUM (OLS residuals)",
                         "stat": cus["cusum_stat"], "break after": "", "p (boot)": cus["p"], "crit 5%": float("nan")})
        # Chow predictive failure: equations estimated through 2019Q4 predict 2020Q1-2023Q2
        for eq in ("gw", "gcpi", "cf1", "cf10"):
            if eq != "gcpi" and sp != "gscpi_ma2":
                continue
            for lab, tq in (("2020Q1-2023Q2", TEST_Q), ("excl. 2020Q2-Q3", TEST_Q_EX)):
                c = chow_predictive(genuine[eq], data, tq)
                chow_rows.append({"spec": sp, "equation": eq, "estimated to": "2019Q4", "test quarters": lab,
                                  "F": c["F"], "df": f"({c['df1']},{c['df2']})", "p": c["p"]})
        # recursive (expanding window) estimates
        pspec = equations_for(v, False)["gcpi"]
        ends = [str(p) for p in pd.period_range("2005Q4", "2023Q2", freq="Q")]
        blocks = {"wage pass-through": names(full["gcpi"], "gw")}
        if v.block is not None:
            blocks["shortage sum"] = names(full["gcpi"], v.block.var)
        rec[(sp, "gcpi")] = recursive_sums(pspec, data, blocks, ends)
    wspec = equations_for(VARIANTS["gscpi_ma2"], False)["gw"]
    data = data_for(VARIANTS["gscpi_ma2"], ds)
    wres = oos.fit_regime(VARIANTS["gscpi_ma2"], data, "genuine")["gw"]
    ends_w = [str(p) for p in pd.period_range("2005Q4", "2019Q4", freq="Q")]
    rec[("gscpi_ma2", "gw")] = recursive_sums(wspec, data, {"V/U sum": names(wres, "vu"), "gw lags": names(wres, "gw"),
                                                           "catch-up": names(wres, "diffcpicf")}, ends_w)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "stability_tests.csv", index=False)
    ch = pd.DataFrame(chow_rows)
    ch.to_csv(OUT / "stability_chow.csv", index=False)
    pd.to_pickle(rec, OUT / "stability_recursive.pkl")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(df.round(3).to_string())
    print(ch.round(4).to_string())

    fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
    r = rec[("gscpi_ma2", "gw")]
    axes[0].plot(range(len(r)), r["V/U sum"], label="V/U sum")
    axes[0].plot(range(len(r)), r["gw lags"], label="gw lags sum")
    axes[0].plot(range(len(r)), r["catch-up"], label="catch-up sum")
    axes[0].set_title("Wage eq.: expanding windows from 1990Q1 (pre-COVID spec)", fontsize=9)
    for sp in SPECS:
        r = rec[(sp, "gcpi")]
        axes[1].plot(range(len(r)), r["wage pass-through"], label=sp)
        if "shortage sum" in r:
            axes[2].plot(range(len(r)), r["shortage sum"], label=sp)
    axes[1].set_title("Price eq.: wage pass-through (sum of gw coefficients)", fontsize=9)
    axes[2].set_title("Price eq.: shortage sum", fontsize=9)
    for ax, key in zip(axes, (("gscpi_ma2", "gw"), ("gscpi_ma2", "gcpi"), ("gscpi_ma2", "gcpi"))):
        idx = rec[key].index
        pos = list(range(0, len(idx), 8))
        ax.set_xticks(pos)
        ax.set_xticklabels([idx[i] for i in pos], rotation=45, fontsize=7)
        ax.grid(alpha=.25)
        ax.axhline(0, color="k", lw=.6)
        ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_stability_recursive.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
