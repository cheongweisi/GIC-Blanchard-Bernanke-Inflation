"""Validation 2: GSCPI specification tests. Writes outputs/validation/gscpi_*.csv and figures."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.data.authors_data import load_raw  # noqa: E402
from bb_inflation.validation import gscpi_tests as G  # noqa: E402
from bb_inflation.validation.specs import VARIANTS, data_for, datasets  # noqa: E402

OUT = OUTPUTS / "validation"
OUT.mkdir(parents=True, exist_ok=True)
NAMES = ["google5", "gscpi5", "gscpi3", "gscpi2", "gscpi1", "gscpi_ma4", "gscpi_ma2"]


def main() -> None:
    ds = datasets(load_raw())
    res = {n: G.analyse(VARIANTS[n], data_for(VARIANTS[n], ds), n_mc=1000) for n in NAMES}
    summ = pd.DataFrame([G.summary_row(res[n]) for n in NAMES])
    summ.to_csv(OUT / "gscpi_summary.csv", index=False)
    rows = []
    for n in NAMES:
        for tag in ("pre", "full"):
            t = res[n][f"table_{tag}"].copy()
            t.insert(0, "estimation", "to 2019Q4" if tag == "pre" else "to 2023Q2")
            t.insert(0, "spec", n)
            rows.append(t.reset_index(names="term"))
    pd.concat(rows).to_csv(OUT / "gscpi_coefficients.csv", index=False)
    rec = pd.DataFrame({n: res[n]["recursive"] for n in NAMES})
    rec.to_csv(OUT / "gscpi_recursive_sums.csv")
    pd.to_pickle({n: {k: v for k, v in r.items() if k in ("irf_full", "irf_pre", "irf_band_full", "shock_size")}
                  for n, r in res.items()}, OUT / "gscpi_irfs.pkl")
    pd.DataFrame({"equal_weights_p_pre": res["gscpi2"]["equal_weights_p_pre"], "equal_weights_p_full": res["gscpi2"]["equal_weights_p_full"]},
                 index=["gscpi2"]).to_csv(OUT / "gscpi_equal_weights_test.csv")
    print("equal-weights test (gscpi2):", res["gscpi2"]["equal_weights_p_pre"], res["gscpi2"]["equal_weights_p_full"])
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 40)
    print(summ[["spec", "shortage sum (pre-2020 est.)", "p_sum HAC (pre)", "p_joint HAC (pre)", "shortage sum (full est.)",
                "p_sum HAC (full)", "p_joint HAC (full)"]].round(3).to_string())
    print(summ[["spec", "flags (full)", "flags (pre)"]].to_string())
    print(summ[["spec", "IRF h0", "IRF h1", "IRF h4", "IRF h8", "IRF peak", "IRF cum 0-8",
                "share of h0-8 where 90% band excludes 0"]].round(2).to_string())
    print(summ[["spec", "decomp shortage 2021Q2 (full est.)", "decomp shortage avg 2021-22 (full est.)",
                "decomp shortage avg 2021-22 (pre est.)", "decomp baseline RMSE (full est.)",
                "decomp baseline RMSE (pre est.)", "AIC (full)", "BIC (full)"]].round(2).to_string())
    print(rec.round(3).to_string())

    # ---- figures
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    for ax, tag, ttl in zip(axes, ("pre", "full"), ("Estimated through 2019Q4", "Estimated through 2023Q2")):
        for n in NAMES:
            v = VARIANTS[n]
            w = G.implied_lag_weights(v, res[n][tag]["gcpi"].coef) * res[n]["shock_size"]   # pp per +1 s.d. of the index
            ax.plot(range(5), w, marker="o", label=n)
        ax.axhline(0, color="k", lw=.6)
        ax.set_title(ttl + "
(direct effect on CPI inflation, pp, of +1 s.d. in the index at each lag)", fontsize=9)
        ax.set_xlabel("lag (quarters)")
        ax.grid(alpha=.25)
    axes[0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_gscpi_lag_patterns.png", dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(2, 4, figsize=(16, 6.5), sharey=True)
    for ax, n in zip(axes.ravel(), NAMES):
        r = res[n]
        b = r["irf_band_full"]
        x = np.arange(-1, 20)
        sl = slice(3, 24)
        ax.fill_between(x, b["q05"].values[sl], b["q95"].values[sl], color="#9ecae1", alpha=.6, label="90% band (HAC MC)")
        ax.plot(x, r["irf_full"][sl], color="#08519c", lw=2, label="full est.")
        ax.plot(x, r["irf_pre"][sl], color="#cb181d", lw=1.6, ls="--", label="est. to 2019Q4")
        ax.axhline(0, color="k", lw=.6)
        ax.set_title(f"{n} (shock {r['shock_size']:.2f})", fontsize=9)
        ax.grid(alpha=.25)
    axes[0, 0].legend(frameon=False, fontsize=7)
    axes.ravel()[-1].axis("off")
    fig.suptitle("Response of CPI inflation (pp) to a +1 s.d. shortage shock", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_gscpi_irfs.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    idx = res["gscpi5"]["dec_full"].index
    keep = idx >= pd.Period("2020Q1")
    for n in NAMES:
        ax.plot(np.arange(keep.sum()), res[n]["dec_full"].contributions["shortage"]["gcpi"].values[keep], marker="o", ms=3, label=n)
    ax.set_xticks(range(keep.sum()))
    ax.set_xticklabels([str(i) for i in idx[keep]], rotation=90, fontsize=7)
    ax.axhline(0, color="k", lw=.6)
    ax.set_ylabel("pp of annualised CPI inflation")
    ax.set_title("Contribution of shortages to CPI inflation (estimates through 2023Q2)", fontsize=10)
    ax.legend(frameon=False, fontsize=7)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_gscpi_decomposition.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
