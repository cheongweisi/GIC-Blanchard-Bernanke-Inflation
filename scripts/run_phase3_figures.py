"""Phase 3 summary charts: pseudo-out-of-sample comparison and coefficient comparison across Models A, B, C."""
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

OUT = OUTPUTS / "phase3"
HZ = ["h1", "h2-4", "h5-8", "h9-12"]


def main() -> None:
    o = pd.read_csv(OUT / "oos_summary.csv")
    post = pd.read_csv(OUT / "oos_summary_post2023_origins.csv")
    g = o[(o["var"] == "gcpi") & (o["target bucket"] == "all targets")]
    fig, axes = plt.subplots(1, 4, figsize=(20, 4.2))
    cond = g[g["mode"] == "conditional"].pivot_table(index="model", columns="horizon", values="RMSE")[HZ]
    for m, c in (("U", "k"), ("W5", "#d62728"), ("W10", "#ff7f0e"), ("W15", "#2ca02c"), ("P15", "#9467bd"), ("U5", "#8c564b")):
        axes[0].plot(range(4), cond.loc[m].values, marker="o", color=c, lw=2 if m == "U" else 1.4, label=m)
    axes[0].set_title("Conditional (realised exogenous), all targets\nCPI inflation RMSE, pp", fontsize=9)
    unc = g[g["mode"] == "unconditional"].pivot_table(index="model", columns="horizon", values="RMSE")[HZ]
    for m, c in (("U", "k"), ("W15", "#2ca02c"), ("AR4", "#1f77b4")):
        axes[1].plot(range(4), unc.loc[m].values, marker="o", color=c, lw=2 if m == "U" else 1.4, label=m)
    axes[1].set_title("Unconditional (exogenous forecast at origin), all targets\nCPI inflation RMSE, pp", fontsize=9)
    b = o[(o["var"] == "gcpi") & (o["mode"] == "conditional") & (o.horizon == "h2-4") & (o["target bucket"] != "all targets")]
    bp = b.pivot_table(index="model", columns="target bucket", values="RMSE")
    models = ["U", "W5", "W10", "W15", "P15", "U5"]
    w = 0.13
    for i, m in enumerate(models):
        axes[2].bar(np.arange(3) + (i - 2.5) * w, bp.loc[m, ["targets to 2019Q4", "2020Q1-2023Q2", "2023Q3-2026Q2"]].values, w, label=m)
    axes[2].set_xticks(range(3))
    axes[2].set_xticklabels(["targets to 2019Q4", "2020Q1-23Q2", "2023Q3-26Q2"], fontsize=8)
    axes[2].set_title("Conditional, h = 2-4 quarters, by target period\nCPI inflation RMSE, pp", fontsize=9)
    pc = post[(post["var"] == "gcpi") & (post["mode"] == "conditional")].pivot_table(index="model", columns="horizon", values="RMSE")[HZ]
    for m, c in (("A", "#1f77b4"), ("U", "#ff7f0e"), ("W15", "#2ca02c")):
        axes[3].plot(range(4), pc.loc[m].values, marker="o", color=c, label={"A": "A frozen 2023Q2", "U": "B re-estimated", "W15": "C15"}[m])
    axes[3].set_title("Origins from 2023Q2: frozen A vs re-estimated\nconditional CPI inflation RMSE, pp", fontsize=9)
    for ax in axes[[0, 1, 3]]:
        ax.set_xticks(range(4))
        ax.set_xticklabels(HZ)
    for ax in axes:
        ax.grid(alpha=.25)
        ax.legend(frameon=False, fontsize=7)
    fig.suptitle("Expanding-window pseudo-out-of-sample evaluation (origins 2004Q4-2026Q1, horizons 1-12)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p3_oos.png", dpi=140)
    plt.close(fig)

    s = pd.read_csv(OUT / "models_coef_summary.csv")
    blocks = [("gcpi", "gw", "Price eq.: wage pass-through"), ("gcpi", "gcpi", "Price eq.: lagged inflation"), ("gcpi", "grpe", "Price eq.: energy"),
              ("gcpi", "grpf", "Price eq.: food"), ("gcpi", "shortagema2", "Price eq.: supply chains (GSCPI 2q mean)"), ("gw", "vu", "Wage eq.: V/U"),
              ("gw", "gw", "Wage eq.: own lags"), ("gw", "diffcpicf", "Wage eq.: catch-up"), ("cf1", "gcpi", "cf1 eq.: gcpi weight"),
              ("cf10", "gcpi", "cf10 eq.: gcpi weight")]
    models = ["A", "B", "C5", "C10", "C15"]
    fig, axes = plt.subplots(2, 5, figsize=(20, 7))
    for ax, (eq, bl, ttl) in zip(axes.ravel(), blocks):
        sub = s[(s["eq"] == eq) & (s.block == bl) & s.model.isin(models)].set_index("model").loc[models]
        ax.errorbar(range(len(models)), sub["sum"], yerr=1.645 * sub["se_hac"], fmt="o", capsize=4)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(models)
        ax.axhline(0, color="k", lw=.5)
        ax.set_title(ttl, fontsize=9)
        ax.grid(alpha=.25)
    fig.suptitle("Sums of coefficients with 90% HAC intervals (A frozen 2023Q2, B re-estimated, C5/C10/C15 exponentially weighted)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p3_coefficients.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
