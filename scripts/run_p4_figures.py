"""Phase 4 figures, from the CSVs in outputs/phase4 (run run_p4_main.py and run_p4_backtest.py first).

Colour rules (dataviz skill): fixed hue per entity, same in every chart (validated reference order); thin lines; recessive grid; direct labels
or legends; no dual axes. Entities: oil/energy = orange, food = yellow, supply chains = aqua, labour market = blue, productivity = violet,
expectations/shocks = magenta; layers: direct = blue, wages = orange, expectations = aqua; baseline = dark grey."""
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

OUT = OUTPUTS / "phase4"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d9d8d3"
BASE = "#4a4945"
DRV = {"Oil / energy": "#eb6834", "Food": "#eda100", "Supply chains (GSCPI)": "#1baf7a", "Labour market (V/U)": "#2a78d6",
       "Productivity": "#6250d6", "Expectations / price / wage shocks": "#e87ba4"}
LAY = {"direct": "#2a78d6", "wages": "#eb6834", "expectations": "#1baf7a"}
SC = ["#2a78d6", "#eb6834", "#1baf7a", "#e87ba4", "#6250d6", "#e34948", "#eda100", "#008300"]
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": .6,
                     "axes.titlesize": 9.5, "axes.titleweight": "bold", "axes.titlecolor": INK, "legend.frameon": False, "figure.facecolor": "white"})

summ = pd.read_csv(OUT / "scenario_summary.csv")
paths = pd.read_csv(OUT / "scenario_paths_long.csv")
base = pd.read_csv(OUT / "baseline_path.csv", index_col=0)
hist = pd.read_csv(OUT / "history_context.csv", index_col=0)
lib = pd.read_csv(OUT / "scenario_library.csv").set_index("key")
QL = list(base.index)


def xt(ax, labels, every=2):
    ax.set_xticks(range(0, len(labels), every))
    ax.set_xticklabels([labels[i] for i in range(0, len(labels), every)], rotation=0, fontsize=8)


def label(key):
    return lib.loc[key.split("__")[0], "label"]


def pth(key, variant="baseline model"):
    return paths[(paths.scenario == key) & (paths.variant == variant)].reset_index(drop=True)


# ---------------------------------------------------------------------------------------------------- 1. baseline
def fig_baseline():
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.6))
    hq = list(hist.index[-10:]) + QL
    x_h = np.arange(len(hist.index[-10:]))
    x_f = np.arange(len(hist.index[-10:]), len(hq))
    a = ax[0]
    a.plot(x_h, hist["yoy_pct"].iloc[-10:], color=MUTED, lw=2, label="actual (to 2026Q2)")
    a.fill_between(x_f, base["yoy_pct_q5"], base["yoy_pct_q95"], color=BASE, alpha=.14, label="model fan: 90% (parameters, residuals, bridge)")
    a.fill_between(x_f, base["yoy_pct_q16"], base["yoy_pct_q84"], color=BASE, alpha=.18)
    a.plot(x_f, base["yoy_pct"], color=BASE, lw=2.2, label="baseline (nowcast information set)")
    bt = pd.read_csv(OUT / "backtest_summary_yoy.csv")
    e = bt[(bt.tier == "D") & (bt["target period"] == "all targets")].set_index("horizon (quarters)")["RMSE of y/y (pp)"]
    for h, c in ((4, 4), (8, 8), (12, 12)):
        a.errorbar(x_f[c], base["yoy_pct"].iloc[c], yerr=e[h], color="#e34948", capsize=4, lw=1.4, zorder=5,
                   label="± 1 RMSE of past real-time-feasible forecasts" if h == 4 else None)
    a.axvline(x_f[0] - .5, color=MUTED, lw=.8, ls=":")
    a.annotate("2026Q3: published CPI\ninflation imposed", (x_f[0], base["yoy_pct"].iloc[0]), xytext=(x_f[0] - 3.2, 4.6), fontsize=7.5, color=MUTED,
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=.7))
    a.set_xticks(range(0, len(hq), 3)); a.set_xticklabels([hq[i] for i in range(0, len(hq), 3)], fontsize=8)
    a.set_ylabel("CPI inflation, y/y (%)")
    a.set_title("Baseline y/y CPI inflation: model fan is conditional on the assumed drivers")
    a.legend(fontsize=7.5, loc="lower left")
    # right: drivers
    d = pd.read_csv(OUT / "baseline_driver_contributions.csv", index_col=0).iloc[1:]
    b = ax[1]
    ordr = [("Energy", DRV["Oil / energy"]), ("Supply chains", DRV["Supply chains (GSCPI)"]), ("Labour market (V/U vs 2019Q4)", DRV["Labour market (V/U)"]),
            ("Productivity", DRV["Productivity"])]
    xs = np.arange(len(d))
    pos = np.zeros(len(d)); neg = np.zeros(len(d))
    for nm, col in ordr:
        v = d[nm].values
        bot = np.where(v >= 0, pos, neg)
        b.bar(xs, v, bottom=bot, color=col, width=.78, edgecolor="white", linewidth=1.2, label=nm)
        pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
    b.plot(xs, d["Baseline model inflation"] - d["Other (initial conditions, constants, expectations)"], color=INK, lw=1.8, marker="o", ms=3,
           label="sum of the four drivers")
    b.axhline(0, color=INK, lw=.7)
    xt(b, QL[1:], 2)
    b.set_ylabel("contribution to annualised inflation (pp)")
    b.set_title("What the baseline drivers add, vs a neutral reference\n(energy and food relative prices constant, GSCPI at 0, V/U at its 2019Q4 value)")
    b.legend(fontsize=7.5, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_p4_baseline.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------------- 2. three energy concepts in the baseline
def fig_energy_concepts():
    ass = pd.read_csv(OUT / "baseline_assumptions.csv", index_col=0)
    ch = pd.read_csv(OUT / "baseline_path.csv", index_col=0)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    x = np.arange(len(QL))
    a = ax[0]
    a.plot(x, ass["oil, Brent (USD, quarter avg)"], color=DRV["Oil / energy"], lw=2.2, label="baseline: futures curve (16 Oct 2026)")
    pa = pd.read_csv(OUT / "scenario_assumptions_by_quarter.csv")
    for key, col, lab in (("oil_steo", "#6250d6", "EIA STEO"), ("oil_flat", "#2a78d6", "flat at Oct 2026"), ("oil_norm", "#1baf7a", "to $70 by Jun 2027")):
        t = pa[(pa.scenario == key) & (pa.variant == "baseline model")]
        a.plot(x, t["oil_usd_qavg"].values, lw=1.6, color=col, label=lab)
    a.set_title("1. Oil: Brent, USD per barrel (quarter average)")
    a.legend(fontsize=7.5); xt(a, QL, 3)
    b = ax[1]
    b.plot(x, ch["gE_nominal"], color=DRV["Oil / energy"], lw=2.2, label="2. CPI energy, nominal (bridge from oil)")
    b.plot(x, ch["gw"], color=DRV["Labour market (V/U)"], lw=2.2, label="wage growth (ECI, model)")
    b.plot(x, ch["grpe"], color=INK, lw=1.6, ls="--", label="3. relative energy price = CPI energy − wages (output)")
    b.axhline(0, color=INK, lw=.7)
    b.set_title("Annualised growth: nominal CPI energy, wages, and the relative price")
    b.legend(fontsize=7.5, loc="upper right"); xt(b, QL, 3)
    c = ax[2]
    c.plot(x, ch["rel_energy_level"], color=INK, lw=2.2, label="relative energy price (index, 2026Q2 = 100)")
    c.plot(x, ch["cpi_energy_level"], color=DRV["Oil / energy"], lw=1.6, label="CPI energy (nominal index)")
    c.plot(x, ch["eci_level"], color=DRV["Labour market (V/U)"], lw=1.6, label="ECI wages (index)")
    c.set_title("Levels: the relative price falls on the backwardated curve")
    c.legend(fontsize=7.5); xt(c, QL, 3)
    fig.suptitle("Three energy price concepts: oil → CPI energy (bridge) → relative energy price (derived each quarter, never an input)", fontsize=10.5, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p4_energy_concepts.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------------- 3. scenario paths
def fig_scenarios():
    keys = ["oil_flat", "oil_up30", "oil_dn30", "oil_norm", "vu_tight", "gscpi_up", "adverse_supply", "benign"]
    fig, axes = plt.subplots(2, 4, figsize=(16, 7), sharey=True, sharex=True)
    x = np.arange(len(QL))
    for a, k in zip(axes.ravel(), keys):
        p = pth(k)
        pb = pth(k, "baseline model")
        lo = p["yoy_pct"] - p["dev_yoy"] + p["dev_yoy_lo90"]
        hi = p["yoy_pct"] - p["dev_yoy"] + p["dev_yoy_hi90"]
        a.fill_between(x, lo, hi, color=SC[1], alpha=.16)
        a.plot(x, p["yoy_pct_baseline"], color=BASE, lw=2, label="baseline")
        a.plot(x, p["yoy_pct"], color=SC[1], lw=2.2, label="scenario")
        if k + "__x0.8" in set(paths.scenario):
            q = pth(k + "__x0.8", "pass-through x0.8")
            a.plot(x, q["yoy_pct"], color=SC[1], lw=1.3, ls="--", label="scenario, energy pass-through ×0.8")
        a.set_title(label(k), fontsize=8.5)
        xt(a, QL, 4)
    axes[0, 0].legend(fontsize=7.5, loc="upper right")
    axes[0, 0].set_ylabel("CPI inflation, y/y (%)"); axes[1, 0].set_ylabel("CPI inflation, y/y (%)")
    fig.suptitle("Scenario paths against the baseline (band: 90% parameter uncertainty of the deviation; dashed: alternative assumption of 20% lower energy pass-through)",
                 fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p4_scenarios_yoy.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------------- 4. oil chain
def fig_oil_chain():
    ch = pd.read_csv(OUT / "energy_transmission_chain.csv")
    cols = ["oil, Brent (% dev., quarter average)", "CPI energy, nominal (% dev., level)", "relative energy price (% dev., level)", "CPI price level (% dev.)",
            "inflation, y/y (pp)"]
    ttl = ["oil, Brent\n(log % dev. from baseline)", "CPI energy, nominal\n(log % dev., level)", "relative energy price\n(log % dev., level)", "CPI price level\n(% dev.)",
           "CPI inflation, y/y\n(pp dev.)"]
    fig, axes = plt.subplots(2, 5, figsize=(17, 6.2), sharex=True)
    for r, (k, nm) in enumerate((("oil_up30", "Oil +30%, persistent"), ("oil_spike", "Oil spike +50% in 2027H1, fading"))):
        for j, c in enumerate(cols):
            a = axes[r, j]
            for v, col, ls, lab in (("baseline model", SC[1], "-", "estimated pass-through"), ("pass-through x0.8", SC[1], "--", "energy pass-through ×0.8")):
                t = ch[(ch.scenario == (k if v == "baseline model" else k + "__x0.8")) & (ch.variant == v)]
                if len(t):
                    a.plot(range(len(t)), t[c].values, color=col, ls=ls, lw=2 if ls == "-" else 1.3, label=lab)
            a.axhline(0, color=INK, lw=.7)
            if r == 0:
                a.set_title(ttl[j], fontsize=8.5)
            if j == 0:
                a.set_ylabel(nm, fontsize=8.5)
            xt(a, QL, 4)
    axes[0, 4].legend(fontsize=7.5)
    fig.suptitle("Transmission chain, oil → CPI energy → relative energy price → prices (wages are endogenous, so the relative price is below the CPI-energy deviation)",
                 fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p4_oil_chain.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------------- 5. attribution by driver
def stacked(ax, df, groups, colors, xlab, total=None, width=.78):
    xs = np.arange(len(df))
    pos = np.zeros(len(df)); neg = np.zeros(len(df))
    for g in groups:
        v = df[g].values
        bot = np.where(v >= 0, pos, neg)
        ax.bar(xs, v, bottom=bot, color=colors[g], width=width, edgecolor="white", linewidth=1.2, label=g)
        pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
    if total is not None:
        ax.plot(xs, total, color=INK, lw=1.6, marker="o", ms=3, label="total")
    ax.axhline(0, color=INK, lw=.7)
    xt(ax, xlab, 3)


def fig_attr_driver():
    d = pd.read_csv(OUT / "attribution_by_driver.csv")
    keys = ["adverse_supply", "benign", "overheating"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.4), sharey=False)
    for a, k in zip(axes, keys):
        t = d[(d.scenario == k) & (d.variant == "baseline model")]
        piv = t.pivot(index="h", columns="driver", values="yoy_pp").reindex(range(13)).fillna(0)
        stacked(a, piv.iloc[1:], [c for c in DRV if c in piv.columns], DRV, QL[1:], total=piv.iloc[1:].sum(axis=1).values)
        a.set_title(label(k), fontsize=9)
        a.set_ylabel("deviation of y/y inflation from baseline (pp)")
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in DRV.values()] + [plt.Line2D([0], [0], color=INK, lw=1.6, marker="o", ms=3)]
    fig.legend(hs, list(DRV) + ["total"], loc="lower center", ncol=7, fontsize=7.5)
    fig.suptitle("Contribution of each driver to the y/y inflation deviation (exactly additive: one driver at a time)", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT / "fig_p4_attribution_driver.png", dpi=140)
    plt.close(fig)


def fig_attr_layer():
    d = pd.read_csv(OUT / "attribution_by_layer.csv")
    keys = ["oil_up30", "oil_spike", "vu_tight", "adverse_supply"]
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.2))
    for a, k in zip(axes, keys):
        t = d[(d.scenario == k) & (d.variant == "baseline model") & (d.scope == "All drivers")]
        piv = t.pivot(index="h", columns="layer", values="yoy_pp").reindex(range(13)).fillna(0)
        stacked(a, piv.iloc[1:], ["direct", "wages", "expectations"], LAY, QL[1:], total=piv.iloc[1:].sum(axis=1).values)
        a.set_title(label(k), fontsize=8.5)
    axes[0].set_ylabel("deviation of y/y inflation (pp)")
    axes[0].legend(fontsize=7.5, loc="upper right")
    fig.suptitle("Transmission layers: direct (price equation incl. inflation persistence) → wage-price loop → expectations", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p4_attribution_layer.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------------- 6. overview dot plot
def fig_overview():
    s = summ[summ.variant == "baseline model"].copy()
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.6), sharey=True)
    s = s.sort_values("y/y dev. 1y (pp)")
    y = np.arange(len(s))
    for a, h in zip(axes, ("1y", "2y", "3y")):
        a.hlines(y, s[f"y/y dev. {h} lo90"], s[f"y/y dev. {h} hi90"], color=GRID, lw=5)
        cols = [DRV.get(d.split("; ")[0], BASE) if "; " not in d else "#4a4945" for d in s["drivers"]]
        a.scatter(s[f"y/y dev. {h} (pp)"], y, color=cols, s=40, zorder=3, edgecolor="white", linewidth=1)
        hc = summ[summ.variant == "pass-through x0.8"].set_index("scenario")
        for i, key in enumerate(s["scenario"]):
            k2 = key + "__x0.8"
            if k2 in hc.index:
                a.scatter(hc.loc[k2, f"y/y dev. {h} (pp)"], i, marker="|", color=INK, s=90, zorder=4)
        a.axvline(0, color=INK, lw=.7)
        a.set_title(f"{h} ahead: y/y deviation from baseline (pp)")
        a.set_yticks(y)
        a.set_yticklabels(s["label"], fontsize=8)
    fig.suptitle("Scenario effects on y/y CPI inflation (dot: estimate; grey bar: 90% parameter band; black tick: energy pass-through ×0.8, oil scenarios). "
                 "Colour: driver.", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p4_scenario_overview.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------------- 7. backtest ladder
def fig_backtest():
    bt = pd.read_csv(OUT / "backtest_summary_yoy.csv")
    names = {"A": "A: realised\nrelative prices\n(Phase 3)", "B": "B: realised\nnominal prices,\nwages endogenous", "C": "C: realised oil\n(via bridge)",
             "D": "D: real-time-\nfeasible baseline\n(oil held flat)", "F": "F: Phase 3\nunconditional", "AR4": "AR(4)"}
    tiers = ["A", "B", "C", "D", "F", "AR4"]
    cols = {4: "#2a78d6", 8: "#eb6834", 12: "#1baf7a"}
    fig, axes = plt.subplots(1, 2, figsize=(17, 4.8), sharey=True)
    for a, per in zip(axes, ("all targets", "2023Q3-2026Q2")):
        t = bt[bt["target period"] == per]
        w = .26
        for i, h in enumerate((4, 8, 12)):
            v = [float(t[(t.tier == k) & (t["horizon (quarters)"] == h)]["RMSE of y/y (pp)"].iloc[0]) for k in tiers]
            a.bar(np.arange(len(tiers)) + (i - 1) * w, v, width=w * .92, color=cols[h], edgecolor="white", linewidth=1, label=f"{h} quarters ahead")
        a.set_xticks(range(len(tiers))); a.set_xticklabels([names[k] for k in tiers], fontsize=7.5)
        a.set_title(f"RMSE of y/y CPI inflation (pp), targets: {per}")
    axes[0].legend(fontsize=8)
    fig.suptitle("Pseudo-out-of-sample ladder (86 origins 2004Q4-2026Q1): what each kind of forecast statement is worth", fontsize=10.5, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_p4_backtest_ladder.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    for f in (fig_baseline, fig_energy_concepts, fig_scenarios, fig_oil_chain, fig_attr_driver, fig_attr_layer, fig_overview, fig_backtest):
        f()
        print("ok", f.__name__)
