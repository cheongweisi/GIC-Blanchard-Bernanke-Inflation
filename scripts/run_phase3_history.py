"""Phase 3: historical fit and decompositions through 2026 for Models A, B, C. Writes outputs/phase3/history_*.csv
and figures (extended Figures 3, 7-9, 12, 13)."""
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

from bb_inflation.config import OUTPUTS, PHASE3_PULL  # noqa: E402
from bb_inflation.data import phase3_data as P  # noqa: E402
from bb_inflation.extension import history as H  # noqa: E402
from bb_inflation.extension.models import fit, standard_models  # noqa: E402

OUT = OUTPUTS / "phase3"
OUT.mkdir(parents=True, exist_ok=True)
SHOW = ["A", "B", "C15"]
COL = {"A": "#1f77b4", "B": "#ff7f0e", "C15": "#2ca02c", "A5": "#9467bd", "B5": "#8c564b", "C5": "#d62728", "C10": "#17becf"}
STEADY_SHORT = P.GSCPI_FILL
WINDOWS = {"2021": ("2021Q1", "2021Q4"), "2022": ("2022Q1", "2022Q4"), "2021Q1-2023Q2": ("2021Q1", "2023Q2"),
           "2023Q3-2026Q2": ("2023Q3", "2026Q2"), "2026Q1-Q2": ("2026Q1", "2026Q2")}
PALETTE = {"Supply chains (GSCPI)": "#f4d03f", "Energy": "#2e5eaa", "Food": "#7fb3e6", "Labour market (V/U)": "#d62728",
           "Productivity": "#8c6d1f", "COVID dummies": "#2d5a27", "Initial conditions": "#bdbdbd", "Residual (actual - model)": "#ffffff"}


def stacked(ax, d, data, var, lo="2019Q3", hi="2026Q2", title=""):
    idx = d.index
    sel = (idx >= pd.Period(lo, "Q")) & (idx <= pd.Period(hi, "Q"))
    x = np.arange(sel.sum())
    pos, neg = np.zeros(len(x)), np.zeros(len(x))
    parts = [("Initial conditions", d.runs["all"][var].values[sel])]
    for c in H.COMPONENTS:
        parts.append((H.COMP_LABEL[c], d.contributions[c][var].values[sel]))
    parts.append(("COVID dummies", (d.contributions["D2020Q2"][var] + d.contributions["D2020Q3"][var]).values[sel]))
    act = data[var].reindex(idx)
    parts.append(("Residual (actual - model)", (act - d.baseline[var]).values[sel]))
    for lab, v in parts:
        bottom = np.where(v >= 0, pos, neg)
        ax.bar(x, v, bottom=bottom, color=PALETTE[lab], label=lab, width=.75, edgecolor="#777777" if lab.startswith("Resid") else "none", lw=.4,
               hatch="//" if lab.startswith("Resid") else None)
        pos += np.where(v >= 0, v, 0)
        neg += np.where(v < 0, v, 0)
    ax.plot(x, act.values[sel], color="k", lw=2, label="Actual")
    ax.set_xticks(x)
    ax.set_xticklabels([str(i).replace("Q", " Q") for i in idx[sel]], rotation=90, fontsize=7)
    ax.axhline(0, color="k", lw=.6)
    ax.axvline(list(idx[sel]).index(pd.Period("2023Q2", "Q")) + .5, color="r", ls=":", lw=1)
    ax.set_title(title, fontsize=10)


def main() -> None:
    p3 = P.build(PHASE3_PULL)
    last = str(p3.last_complete)
    ms = standard_models(last)
    res = {k: fit(m, p3.data, last) for k, m in ms.items()}
    ends = {k: (m.end or last) for k, m in ms.items()}
    fitted = {k: H.fitted_one_step(r, p3.data_bridged) for k, r in res.items()}
    fe = H.fit_errors({k: fitted[k] for k in ("A", "B", "C5", "C10", "C15", "A5", "B5")}, p3.data_bridged, ends)
    fe.to_csv(OUT / "history_fit_errors.csv", index=False)
    pd.to_pickle(fitted, OUT / "history_fitted.pkl")

    decs = H.decompositions({k: res[k] for k in ("A", "B", "C5", "C10", "C15", "A5", "B5")}, ms, p3.data_bridged, STEADY_SHORT)
    for var in ("gcpi", "gw"):
        H.contribution_table(decs, p3.data_bridged, var, WINDOWS).to_csv(OUT / f"history_decomp_{var}.csv", index=False)
    H.baseline_rmse(decs, p3.data_bridged).to_csv(OUT / "history_baseline_rmse.csv", index=False)
    pd.to_pickle({k: {"index": d.index, "baseline": d.baseline, "contributions": d.contributions, "runs": d.runs} for k, d in decs.items()},
                 OUT / "history_decomp.pkl")

    # ---- figures
    names = {"gcpi": "Fig. 7  CPI inflation (annualised, %)", "gw": "Fig. 3  Wage growth (ECI, annualised, %)",
             "cf1": "Fig. 8  One-year expectations (%)", "cf10": "Fig. 9  Ten-year expectations (%)"}
    fig, axes = plt.subplots(2, 2, figsize=(14, 7.5))
    for ax, v in zip(axes.ravel(), names):
        act = p3.data_bridged[v].loc["2015Q1":]
        x = np.arange(len(act))
        ax.plot(x, act.values, color="k", lw=2.2, label="Actual")
        for m in SHOW:
            f = fitted[m][v].reindex(act.index)
            ax.plot(x, f.values, color=COL[m], lw=1.4, label=ms[m].label)
        ax.axvline(list(act.index).index(pd.Period("2023Q2", "Q")) + .5, color="r", ls=":", lw=1)
        pos = list(range(0, len(act), 8))
        ax.set_xticks(pos)
        ax.set_xticklabels([str(act.index[i]).replace("Q", " Q") for i in pos], rotation=45, fontsize=8)
        ax.set_title(names[v], fontsize=10)
        ax.grid(alpha=.25)
    axes[0, 0].legend(frameon=False, fontsize=7)
    fig.suptitle("One-step fitted values from Models A, B, C (dotted line: original sample end 2023Q2; fitted after it are out-of-sample for A)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p3_fit.png", dpi=140)
    plt.close(fig)

    for var, fname, ttl in (("gcpi", "fig_p3_decomp_price.png", "Fig. 12 extended: sources of CPI inflation"),
                            ("gw", "fig_p3_decomp_wage.png", "Fig. 13 extended: sources of wage growth")):
        fig, axes = plt.subplots(1, 3, figsize=(20, 5), sharey=True)
        for ax, m in zip(axes, SHOW):
            stacked(ax, decs[m], p3.data_bridged, var, title=ms[m].label)
        axes[0].legend(frameon=False, fontsize=7, ncol=2, loc="upper left")
        axes[0].set_ylabel("percentage points (annualised)")
        fig.suptitle(ttl + " (dotted line: 2023Q2; hatched = residual, actual minus model)", fontsize=11)
        fig.tight_layout()
        fig.savefig(OUT / fname, dpi=140)
        plt.close(fig)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 30)
    print(pd.read_csv(OUT / "history_decomp_gcpi.csv").query("model in ['A','B','C15']").round(2).to_string())
    print(pd.read_csv(OUT / "history_baseline_rmse.csv").query("var=='gcpi'").round(2).to_string())
    print(fe[(fe["var"] == "gcpi") & fe.model.isin(["A", "B", "C15"])].round(2).to_string())


if __name__ == "__main__":
    main()
