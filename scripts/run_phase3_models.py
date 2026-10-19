"""Phase 3: estimate Models A, B, C (and gscpi5 robustness), HAC coefficient tables, flags, recursive stability.
Writes outputs/phase3/models_*.csv, fig_p3_recursive.png."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS, PHASE3_PULL  # noqa: E402
from bb_inflation.data import phase3_data as P  # noqa: E402
from bb_inflation.estimation.inference import recursive_sums  # noqa: E402
from bb_inflation.estimation.wls import effective_sample_size  # noqa: E402
from bb_inflation.extension import coefs as C  # noqa: E402
from bb_inflation.extension.models import fit, specs_for_end, standard_models  # noqa: E402

OUT = OUTPUTS / "phase3"
OUT.mkdir(parents=True, exist_ok=True)


def fits(p3: P.Phase3Data) -> tuple[dict, dict]:
    ms = standard_models(str(p3.last_complete))
    res = {k: fit(m, p3.data, str(p3.last_complete)) for k, m in ms.items()}
    return ms, res


def main() -> None:
    p3 = P.build(PHASE3_PULL)
    ms, res = fits(p3)
    var_of = {k: m.variant for k, m in ms.items()}
    summ = C.coef_summary(res, p3.data, var_of)
    summ.to_csv(OUT / "models_coef_summary.csv", index=False)
    fl = C.flags(summ, "A")
    fl.to_csv(OUT / "models_flags.csv", index=False)
    # individual price-equation coefficients (all models)
    rows = []
    for k, r in res.items():
        for eq, rr in r.items():
            for n, b in rr.coef.items():
                rows.append({"model": k, "eq": eq, "term": n, "coef": b})
    pd.DataFrame(rows).to_csv(OUT / "models_coefficients.csv", index=False)
    info = pd.DataFrame([{"model": k, "eq": eq, "N": r.nobs, "sample": f"{r.sample[0]}-{r.sample[1]}",
                          "R2 (descriptive)": r.r2_corr,
                          "effective N": effective_sample_size(r.weights) if r.weights is not None else r.nobs}
                         for k, rr in res.items() for eq, r in rr.items()])
    info.to_csv(OUT / "models_info.csv", index=False)
    # V/U-bridge sensitivity: Model B with the bridged 2025Q4 V/U used in estimation
    from bb_inflation.extension.models import ModelSpec
    Bb = fit(ModelSpec("Bb", "B with bridged V/U in estimation"), p3.data_bridged, str(p3.last_complete))
    sb = C.coef_summary({"Bb": Bb}, p3.data_bridged, {"Bb": "gscpi_ma2"})
    sb.to_csv(OUT / "models_coef_summary_bridgedVU.csv", index=False)
    # Macrobond ECI sensitivity for B
    p3m = P.build(PHASE3_PULL, eci_history="macrobond")
    Bm = fit(ms["B"], p3m.data, str(p3m.last_complete))
    A_m = fit(ms["A"], p3m.data, str(p3m.last_complete))
    sm = C.coef_summary({"A (Macrobond ECI)": A_m, "B (Macrobond ECI)": Bm}, p3m.data,
                        {"A (Macrobond ECI)": "gscpi_ma2", "B (Macrobond ECI)": "gscpi_ma2"})
    sm.to_csv(OUT / "models_coef_summary_macrobondECI.csv", index=False)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    show = summ[summ.model.isin(["A", "B", "C10", "C15", "A5", "B5"])].pivot_table(index=["eq", "block"], columns="model", values="sum", sort=False)
    print(show.round(3).to_string())
    print(info[info.model.isin(["A", "B", "C5", "C10", "C15"])].pivot_table(index="eq", columns="model", values="N").to_string())
    print(fl[fl.flag].to_string())

    # recursive (expanding window) estimates for B
    ends = [str(p) for p in pd.period_range("2005Q4", p3.last_complete, freq="Q")]
    rows = []
    for e in ends:
        spec = specs_for_end("gscpi_ma2", e)
        from bb_inflation.estimation.rls import estimate
        r = {eq: estimate(spec[eq], p3.data, "1990Q1", e) for eq in spec}
        rows.append({"end": e,
                     "price: wage pass-through": r["gcpi"].coef[r["gcpi"].block_names("gw")].sum(),
                     "price: lagged inflation": r["gcpi"].coef[r["gcpi"].block_names("gcpi")].sum(),
                     "price: energy": r["gcpi"].coef[r["gcpi"].block_names("grpe")].sum(),
                     "price: food": r["gcpi"].coef[r["gcpi"].block_names("grpf")].sum(),
                     "price: shortage (ma2)": r["gcpi"].coef["shortagema2_L0"],
                     "wage: V/U sum": r["gw"].coef[r["gw"].block_names("vu")].sum(),
                     "wage: own lags": r["gw"].coef[r["gw"].block_names("gw")].sum(),
                     "cf1: weight on gcpi": r["cf1"].coef[r["cf1"].block_names("gcpi")].sum(),
                     "cf10: weight on gcpi": r["cf10"].coef[r["cf10"].block_names("gcpi")].sum()})
    rec = pd.DataFrame(rows).set_index("end")
    rec.to_csv(OUT / "models_recursive_B.csv")
    fig, axes = plt.subplots(2, 5, figsize=(20, 6.5))
    for ax, c in zip(axes.ravel(), rec.columns):
        ax.plot(range(len(rec)), rec[c].values, lw=2)
        pos = list(range(0, len(rec), 12))
        ax.set_xticks(pos)
        ax.set_xticklabels([rec.index[i] for i in pos], rotation=45, fontsize=7)
        ax.axhline(0, color="k", lw=.5)
        ax.axvline(list(rec.index).index("2023Q2"), color="r", ls=":", lw=1)
        ax.set_title(c, fontsize=9)
        ax.grid(alpha=.25)
    fig.suptitle("Expanding-window estimates (Model B specification); dotted = original-paper sample end 2023Q2", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p3_recursive.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
