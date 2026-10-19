"""Replication figures (Figures 3, 7-14 of the paper). Plain matplotlib, one function per figure."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

COLORS = {"actual": "#1f3b73", "pred": "#b03a2e", "grpe": "#2e5eaa", "grpf": "#7fb3e6",
          "shortage": "#f4d03f", "vu": "#d62728", "magpty": "#8c6d1f", "init": "#bdbdbd", "D2020Q2": "#2d5a27", "D2020Q3": "#a8e6a1"}


def _x(idx: pd.PeriodIndex) -> np.ndarray:
    return np.arange(len(idx))


def _ticks(ax, idx, step=2):
    pos = list(range(0, len(idx), step))
    ax.set_xticks(pos)
    ax.set_xticklabels([str(idx[i]).replace("Q", " Q") for i in pos], rotation=45, ha="right")


def fig_actual_vs_predicted(data: pd.DataFrame, precovid: dict, path: Path) -> None:
    """Figures 3, 7, 8, 9: out-of-sample (pre-COVID) predictions 2020Q1-2023Q2; price eq is full sample."""
    spec = [("gw", "Fig. 3  Wage growth (gw)"), ("gcpi", "Fig. 7  Price inflation (gcpi)"),
            ("cf1", "Fig. 8  Short-run expectations (cf1)"), ("cf10", "Fig. 9  Long-run expectations (cf10)")]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for ax, (v, title) in zip(axes.ravel(), spec):
        pred = precovid[v].predict(data).loc["2020Q1":"2023Q2"]
        act = data[v].loc["2020Q1":"2023Q2"]
        x = _x(act.index)
        ax.plot(x, act.values, color=COLORS["actual"], lw=2, label="Actual")
        ax.plot(x, pred.values, color=COLORS["pred"], lw=2, label="Predicted")
        ax.set_title(title, fontsize=10)
        _ticks(ax, act.index)
        ax.set_ylabel("Percent")
        ax.grid(alpha=.25)
    axes[0, 0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_irfs(irfs: dict[str, pd.DataFrame], path: Path) -> None:
    """Figures 10 (energy, food, shortage) and 11 (V/U): response of gcpi, 28 quarters after the shock."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    t = np.arange(-1, 28)
    for name, c in [("grpe", "grpe"), ("grpf", "grpf"), ("shortage", "shortage")]:
        axes[0].plot(t, irfs[name]["gcpi_simul"].values[3:32], color=COLORS[c], lw=2, label=name)
    axes[0].set_title("Fig. 10  Inflation response to +1 s.d. price shocks")
    axes[1].plot(t, irfs["vu"]["gcpi_simul"].values[3:32], color=COLORS["vu"], lw=2, label="v/u (permanent)")
    axes[1].set_title("Fig. 11  Inflation response to +1 s.d. V/U")
    for ax in axes:
        ax.axhline(0, color="k", lw=.6)
        ax.set_xlabel("Quarters after shock")
        ax.set_ylabel("pp deviation")
        ax.legend(frameon=False)
        ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_decomposition(dec, data: pd.DataFrame, path: Path, var: str = "gcpi", title: str = "") -> None:
    """Figures 12 (gcpi) and 13 (gw): stacked contributions from 2019Q3 with the actual series."""
    idx = dec.index
    keep = idx >= pd.Period("2019Q3")
    order = [("shortage", "Shortages"), ("grpe", "Energy prices"), ("grpf", "Food prices"), ("vu", "V/U"),
             ("magpty", "Productivity"), ("D2020Q2", "Q2 dummy"), ("D2020Q3", "Q3 dummy")]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(keep.sum())
    pos = np.zeros(len(x))
    neg = np.zeros(len(x))
    parts = [("init", "Initial conditions", dec.runs["all"][var].values[keep])] + [
        (k, lab, dec.contributions[k][var].values[keep]) for k, lab in order]
    for k, lab, v in parts:
        col = COLORS[k]
        bottom = np.where(v >= 0, pos, neg)
        ax.bar(x, v, bottom=bottom, color=col, label=lab, width=.6)
        pos += np.where(v >= 0, v, 0)
        neg += np.where(v < 0, v, 0)
    act = data[var].reindex(idx)[keep]
    ax.plot(x, act.values, color="k", lw=2, label="Actual")
    ax.set_xticks(x)
    ax.set_xticklabels([str(i).replace("Q", " Q") for i in idx[keep]], rotation=45, ha="right")
    ax.axhline(0, color="k", lw=.6)
    ax.set_ylabel("Percent (annualised)")
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_forecast(paths: dict[str, pd.DataFrame], hist: pd.Series, path: Path, horizon: int = 16) -> None:
    """Figure 14: CPI inflation projections for alternative terminal V/U."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for lab, df in paths.items():
        s = df["gcpi"].iloc[3:3 + horizon]
        ax.plot(np.arange(len(s)), s.values, lw=2, label=lab)
    labels = [str(p).replace("Q", " Q") for p in list(paths.values())[0].index[3:3 + horizon]]
    ax.set_xticks(range(0, horizon, 2))
    ax.set_xticklabels(labels[::2], rotation=45, ha="right")
    ax.set_ylabel("CPI inflation, percent")
    ax.set_title("Fig. 14  Conditional projections, alternative terminal V/U")
    ax.legend(frameon=False)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_decomp_compare(panels: list[tuple[str, object, pd.DataFrame]], path: Path, var: str = "gcpi") -> None:
    """Side-by-side decomposition (Fig. 12 style) for several cases, common y-axis."""
    order = [("shortage", "Shortages"), ("grpe", "Energy prices"), ("grpf", "Food prices"), ("vu", "V/U"),
             ("magpty", "Productivity"), ("D2020Q2", "Q2 dummy"), ("D2020Q3", "Q3 dummy")]
    fig, axes = plt.subplots(1, len(panels), figsize=(6.2 * len(panels), 4.6), sharey=True)
    for ax, (title, dec, data) in zip(np.atleast_1d(axes), panels):
        idx = dec.index
        keep = (idx >= pd.Period("2020Q1"))
        x = np.arange(keep.sum())
        pos, neg = np.zeros(len(x)), np.zeros(len(x))
        parts = [("init", "Initial conditions", dec.runs["all"][var].values[keep])] + [
            (k, lab, dec.contributions[k][var].values[keep]) for k, lab in order]
        for k, lab, v in parts:
            bottom = np.where(v >= 0, pos, neg)
            ax.bar(x, v, bottom=bottom, color=COLORS[k], label=lab, width=.7)
            pos += np.where(v >= 0, v, 0)
            neg += np.where(v < 0, v, 0)
        ax.plot(x, data[var].reindex(idx)[keep].values, color="k", lw=2, label="Actual")
        ax.set_xticks(x)
        ax.set_xticklabels([str(i).replace("Q", " Q") for i in idx[keep]], rotation=90, fontsize=7)
        ax.axhline(0, color="k", lw=.6)
        ax.set_title(title, fontsize=10)
    np.atleast_1d(axes)[0].set_ylabel("Percent (annualised)")
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_irf_compare(cases: dict[str, pd.DataFrame], path: Path, horizon: int = 28) -> None:
    """gcpi responses to the four shocks across cases (each shock is 1 s.d. of 2020Q1+ data in that case's units)."""
    titles = {"grpe": "Energy", "grpf": "Food", "shortage": "Shortage (1 s.d., own units)", "vu": "V/U (permanent)"}
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.6))
    t = np.arange(-1, horizon)
    for ax, v in zip(axes, titles):
        for lab, irfs in cases.items():
            ax.plot(t, irfs[v]["gcpi_simul"].values[3:3 + horizon + 1][: len(t)], lw=2, label=lab)
        ax.axhline(0, color="k", lw=.6)
        ax.set_title(titles[v], fontsize=10)
        ax.set_xlabel("Quarters after shock")
        ax.grid(alpha=.25)
    axes[0].set_ylabel("gcpi, pp deviation")
    axes[0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_shortage_series(google: pd.Series, gscpi: pd.Series, path: Path) -> None:
    """Google 'shortage' versus GSCPI, each standardised on 2004Q1-2023Q2, with levels in the title."""
    x = pd.concat([google, gscpi], axis=1, keys=["Google 'shortage' (authors)", "GSCPI (Macrobond)"]).loc["2004Q1":"2023Q2"].dropna()
    z = (x - x.mean()) / x.std()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    xs = np.arange(len(z))
    ax.plot(xs, z.iloc[:, 0], color="#f1c40f", lw=2.2, label=z.columns[0])
    ax.plot(xs, z.iloc[:, 1], color="#2e5eaa", lw=2.2, label=z.columns[1])
    pos = list(range(0, len(z), 8))
    ax.set_xticks(pos)
    ax.set_xticklabels([str(z.index[i]).replace("Q", " Q") for i in pos], rotation=45, ha="right")
    ax.set_ylabel("Standard deviations")
    ax.legend(frameon=False)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def fig_price_coefs(df: pd.DataFrame, path: Path) -> None:
    """Price-equation sums of coefficients along the cumulative ladder."""
    cols = ["sum gcpi:gw", "sum gcpi:gcpi", "sum gcpi:grpe", "sum gcpi:grpf", "sum gcpi:shortage", "sum gcpi:magpty"]
    labs = ["wage growth", "lagged inflation", "energy", "food", "shortage", "productivity"]
    fig, axes = plt.subplots(1, 6, figsize=(16, 3.4))
    for ax, c, lab in zip(axes, cols, labs):
        ax.bar(range(len(df)), df[c].values, color=["#bdbdbd"] + ["#7fb3e6"] * (len(df) - 2) + ["#d62728"])
        ax.set_title(lab, fontsize=10)
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels([f"L{i}" for i in range(len(df))], fontsize=8)
        ax.axhline(0, color="k", lw=.6)
        ax.grid(alpha=.25, axis="y")
    fig.suptitle("Price-equation sum of coefficients: L0 authors -> L6 all-Macrobond (GSCPI)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
