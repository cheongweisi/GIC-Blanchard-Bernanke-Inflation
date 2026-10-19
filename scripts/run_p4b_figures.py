"""Phase 4b figures. Reads outputs/phase4b/*.csv (and the pinned data) and writes outputs/phase4b/fig_p4b_*.png. Palette: the validated default categorical order."""
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
from bb_inflation.supplement import context as C  # noqa: E402

OUT = OUTPUTS / "phase4b"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 10,
                     "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": .6,
                     "legend.frameon": False, "figure.dpi": 130})


def per(q):
    return pd.Period(q, "Q")


def actual_yoy(d):
    return d["gcpi"].rolling(4).mean()


def forecast_panels(origins, title, fname, d, paths):
    ay = actual_yoy(d)
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharey=False)
    for ax, o in zip(axes.ravel(), origins):
        T0 = per(o)
        lo, hi = T0 - 6, min(T0 + 12, per("2026Q2"))
        a = ay.loc[lo:hi]
        x = lambda idx: [(p - T0).n for p in idx]          # noqa: E731
        ax.plot(x(a.index), a.values, color=INK, lw=2.4, label="Actual y/y")
        p = paths[(paths.origin == o)]
        for tier, col, lab, ls in (("D", ORANGE, "Real-time-feasible (tier D)", "-"), ("C", BLUE, "Realised drivers via bridge (tier C)", "-"), ("AR4", "#8a8985", "AR(4)", "--")):
            s = p[p.tier == tier].sort_values("h")
            ax.plot(s["h"].values, s["yoy"].values, color=col, lw=1.8, ls=ls, label=lab)
        ax.axvline(0, color=INK2, lw=.8, ls=":")
        ax.set_title(f"Origin {o}")
        ax.set_xlabel("quarters from origin")
        ax.set_ylabel("y/y CPI inflation, %")
    axes[0, 0].legend(fontsize=7.5, loc="best")
    fig.suptitle(title, fontsize=11, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, .96))
    fig.savefig(OUT / fname)
    plt.close(fig)


def fig_decomp():
    c = pd.read_csv(OUT / "forecast_error_components.csv")
    y = c[c.measure.str.startswith("y/y")].copy()
    tgt = pd.PeriodIndex(y.target, freq="Q")
    comps = [("oil path", "Oil path (flat vs realised)", BLUE), ("oil bridge", "Oil -> CPI energy bridge", AQUA), ("GSCPI", "GSCPI (AR(1) vs realised)", ORANGE),
             ("V/U", "V/U (held vs realised)", VIOLET), ("food closure", "Food (moves with wages vs realised)", YELLOW), ("productivity", "Productivity", "#8a8985"),
             ("price eq. residuals", "Price-equation residuals", MAGENTA), ("wage eq. residuals", "Wage-equation residuals", GREEN)]
    y["expectations residuals"] = y["1y expectations residuals"] + y["10y expectations residuals"]
    comps.append(("expectations residuals", "Expectations residuals", RED))
    B = {"targets to 2019Q4": ("1990Q1", "2019Q4"), "2020Q1-2023Q2": ("2020Q1", "2023Q2"), "2023Q3-2026Q2": ("2023Q3", "2026Q2")}
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.2), sharey=True)
    for ax, h in zip(axes, (4, 8, 12)):
        bottom_pos = np.zeros(len(B)); bottom_neg = np.zeros(len(B))
        for key, lab, col in comps:
            vals = []
            for b, (lo, hi) in B.items():
                s = y[(tgt >= per(lo)) & (tgt <= per(hi)) & (y.h == h)]
                vals.append(float(s[key].mean()))
            vals = np.array(vals)
            pos, neg = np.clip(vals, 0, None), np.clip(vals, None, 0)
            ax.bar(range(len(B)), pos, bottom=bottom_pos, color=col, width=.55, label=lab if h == 4 else None, edgecolor="white", linewidth=1)
            ax.bar(range(len(B)), neg, bottom=bottom_neg, color=col, width=.55, edgecolor="white", linewidth=1)
            bottom_pos += pos; bottom_neg += neg
        tot, ar = [], []
        for b, (lo, hi) in B.items():
            s = y[(tgt >= per(lo)) & (tgt <= per(hi)) & (y.h == h)]
            tot.append(float(s["error D"].mean())); ar.append(float((s["AR4"] - s["actual"]).mean()))
        ax.scatter(range(len(B)), tot, color=INK, zorder=5, s=46, marker="D", label="Tier D mean error (sum of bars)" if h == 4 else None)
        ax.scatter(range(len(B)), ar, color="#8a8985", zorder=5, s=46, marker="o", edgecolor=INK, label="AR(4) mean error" if h == 4 else None)
        ax.axhline(0, color=INK2, lw=.8)
        ax.set_xticks(range(len(B)))
        ax.set_xticklabels([f"{b}\n(n={int(((tgt >= per(lo)) & (tgt <= per(hi)) & (y.h == h)).sum())})" for b, (lo, hi) in B.items()], fontsize=8)
        ax.set_title(f"{h} quarters ahead")
        ax.set_ylim(-3.4, 2.1)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("mean error in y/y inflation, pp (forecast - actual)")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=4, fontsize=8)
    fig.suptitle("Where the real-time forecast error comes from: exact decomposition of tier D (mean error by target period)", fontsize=11, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, .1, 1, .95))
    fig.savefig(OUT / "fig_p4b_forecast_error_decomposition.png")
    plt.close(fig)


def fig_wage():
    p = pd.read_csv(OUT / "wage_overlay_paths.csv")
    cal = {"estimated (sum -0.002)": (INK, "Estimated catch-up (-0.002)", "-"), "phi = 0.10 (upper end of data)": (BLUE, "phi = 0.10 (upper end of the data)", "-"),
           "phi = 0.25 (stress, judgemental)": (ORANGE, "phi = 0.25 (stress)", "-")}
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    spec = [("oil_up30", "y/y dev (pp)", "Oil +30%: y/y inflation vs baseline, pp"), ("oil_up30", "price level dev (%)", "Oil +30%: CPI level vs baseline, %"),
            ("oil_up30", "wage level dev (%)", "Oil +30%: wage (ECI) level vs baseline, %"), ("adverse_supply", "y/y dev (pp)", "Adverse supply bundle: y/y inflation, pp"),
            ("vu_tight", "y/y dev (pp)", "V/U back to 1.19: y/y inflation, pp"), ("adverse_supply", "wage level dev (%)", "Adverse supply bundle: wage level, %")]
    for ax, (key, col, ttl) in zip(axes.ravel(), spec):
        for lab, (c, name, ls) in cal.items():
            s = p[(p.scenario == key) & (p.calibration == lab)]
            ax.plot(range(len(s)), s[col].values, color=c, lw=2, label=name)
        ax.set_title(ttl)
        ax.set_xticks(range(0, 13, 4))
        ax.set_xticklabels(["2026Q3", "2027Q3", "2028Q3", "2029Q3"])
        ax.axhline(0, color=INK2, lw=.6)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Wage catch-up overlay: even a stress coefficient leaves the first-year effect unchanged and adds under 0.25% to the price level by year three",
                 fontsize=10.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(OUT / "fig_p4b_wage_catchup_overlay.png")
    plt.close(fig)


def fig_baseline(d):
    kp = pd.read_csv(OUT / "baseline_key_paths.csv", index_col=0)
    st = pd.read_csv(OUT / "baseline_reference_steps.csv", index_col=0)
    dr = pd.read_csv(OUT / "baseline_long_run_drift.csv", index_col=0)
    hist = pd.read_csv(OUT / "wage_residual_history.csv", index_col=0)
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8))
    ax = axes[0, 0]
    h = hist.loc["2023Q1":]
    ax.plot(range(len(h)), h["gw actual"].values, color=INK, lw=2, label="ECI growth, actual")
    n0 = len(h)
    ax.plot(range(n0, n0 + len(kp)), kp["gw"].values, color=ORANGE, lw=2, label="baseline wage growth")
    ax.plot(range(len(h)), h["cf1"].values, color=BLUE, lw=1.4, ls="-", alpha=.9, label="1y expectations (Cleveland)")
    ax.plot(range(n0, n0 + len(kp)), kp["cf1"].values, color=BLUE, lw=1.4, ls="--")
    ax.plot(range(n0, n0 + len(kp)), kp["cf10"].values, color=VIOLET, lw=1.4, ls="--", label="baseline 10y expectations")
    idx = list(h.index) + list(kp.index)
    ax.set_xticks(range(0, len(idx), 4)); ax.set_xticklabels([idx[i] for i in range(0, len(idx), 4)], rotation=45, ha="right")
    ax.axvline(n0 - 1, color=INK2, lw=.8, ls=":")
    ax.set_title("Wages and expectations: history and baseline (annualised %)"); ax.legend(fontsize=7.5, loc="upper right")
    ax = axes[0, 1]
    ax.plot(range(len(kp)), kp["gE_nominal"].values, color=ORANGE, lw=2, label="CPI energy, nominal growth")
    ax.plot(range(len(kp)), kp["grpe"].values, color=BLUE, lw=2, label="relative to wages (output)")
    ax.axhline(0, color=INK2, lw=.6)
    ax.set_xticks(range(0, len(kp), 2)); ax.set_xticklabels([kp.index[i] for i in range(0, len(kp), 2)], rotation=45, ha="right")
    ax.set_title("Energy inflation in the baseline (annualised %)"); ax.legend(fontsize=8)
    ax = axes[1, 0]
    comp = ["+ energy path", "+ food path", "+ supply-chain path", "+ estimated wage constant"]
    cols = [BLUE, YELLOW, ORANGE, MAGENTA]
    pos = np.zeros(len(st)); neg = np.zeros(len(st))
    for c, col in zip(comp, cols):
        v = st[c].values
        ax.bar(range(len(st)), np.clip(v, 0, None), bottom=pos, color=col, width=.7, edgecolor="white", linewidth=.8, label=c[2:])
        ax.bar(range(len(st)), np.clip(v, None, 0), bottom=neg, color=col, width=.7, edgecolor="white", linewidth=.8)
        pos += np.clip(v, 0, None); neg += np.clip(v, None, 0)
    ax.plot(range(len(st)), st["= baseline y/y (%)"].values - st["neutral reference"].values, color=INK, lw=2, marker="o", ms=3.5, label="sum = baseline minus reference")
    ax.axhline(0, color=INK2, lw=.6)
    ax.set_xticks(range(len(st))); ax.set_xticklabels(st.index, rotation=60, ha="right", fontsize=7.5)
    ax.set_title("Baseline y/y minus its neutral reference (pp): what moves it"); ax.legend(fontsize=7.5, ncol=2, loc="lower left")
    ax = axes[1, 1]
    ax.plot(range(1, len(dr) + 1), dr["estimated wage constant"].values, color=ORANGE, lw=2, label="estimated wage constant")
    ax.plot(range(1, len(dr) + 1), dr["neutral wage constant"].values, color=BLUE, lw=2, label="authors' neutral constant")
    ax.set_title("No anchor: drivers held at baseline values for 20 years (y/y %)"); ax.set_xlabel("years from 2026Q3"); ax.legend(fontsize=8)
    fig.suptitle("Medium-term baseline: the rise to 3.1% is the energy drag fading plus a slow wage-constant drift", fontsize=11, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, .96))
    fig.savefig(OUT / "fig_p4b_baseline_mechanisms.png")
    plt.close(fig)


def fig_bridge():
    ep = pd.read_csv(OUT / "bridge_episodes.csv")
    rec = pd.read_csv(OUT / "bridge_recursive_elasticity.csv")
    rol = pd.read_csv(OUT / "bridge_rolling15y_elasticity.csv")
    sc = pd.read_csv(OUT / "bridge_scenario_vs_elasticity.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8))
    for ax, (lab, a, b) in zip(axes[0], (("2022 energy shock", "2021Q4", "2023Q1"), ("2026 shock", "2025Q4", "2026Q3"))):
        s = ep[(ep.quarter >= a) & (ep.quarter <= b)]
        x = np.arange(len(s))
        ax.bar(x - .2, s["actual CPI energy (ann. %)"], width=.38, color=INK, label="actual")
        ax.bar(x + .2, s["bridge out-of-sample (ann. %)"], width=.38, color=ORANGE, label="bridge, estimated before the episode")
        ax.set_xticks(x); ax.set_xticklabels(s.quarter)
        ax.axhline(0, color=INK2, lw=.6)
        ax.set_title(f"{lab}: CPI energy growth (annualised %)"); ax.legend(fontsize=8)
    ax = axes[1, 0]
    ax.plot(range(len(rec)), rec["elasticity"], color=BLUE, lw=2, label="expanding window from 1990")
    ax.fill_between(range(len(rec)), rec["elasticity"] - 1.96 * rec["s.e."], rec["elasticity"] + 1.96 * rec["s.e."], color=BLUE, alpha=.15)
    ax.plot(range(len(rol)), rol["elasticity"], color=ORANGE, lw=2, label="rolling 15 years")
    ax.fill_between(range(len(rol)), rol["elasticity"] - 1.96 * rol["s.e."], rol["elasticity"] + 1.96 * rol["s.e."], color=ORANGE, alpha=.15)
    ax.axhline(0.297, color=INK2, lw=.8, ls=":")
    ticks = list(range(0, len(rec), 8))
    ax.set_xticks(ticks); ax.set_xticklabels([rec["end"].iloc[i] for i in ticks], rotation=45, ha="right")
    ax.set_title("Bridge elasticity by estimation end date (95% bands)"); ax.legend(fontsize=8)
    ax = axes[1, 1]
    for key, col, lab in (("oil_up30", ORANGE, "Oil +30% persistent"), ("oil_flat", BLUE, "Oil stays at $111"), ("oil_dn30", AQUA, "Oil -30% persistent")):
        s = sc[sc.scenario == key].sort_values("elasticity")
        ax.plot(s["elasticity"], s["y/y dev 1y (pp)"], color=col, lw=2, marker="o", ms=4, label=lab)
    for el, t in ((0.297, "estimated"), (0.37, "implied at\ncurrent price")):
        ax.axvline(el, color=INK2, lw=.8, ls=":"); ax.text(el, ax.get_ylim()[1] * .92 if t == "estimated" else ax.get_ylim()[1] * .75, t, fontsize=7.5, ha="left", color=INK2)
    ax.axhline(0, color=INK2, lw=.6)
    ax.set_xlabel("long-run elasticity of CPI energy to Brent"); ax.set_title("Scenario effect on y/y inflation after one year (pp)"); ax.legend(fontsize=8)
    fig.suptitle("Oil-to-CPI-energy bridge: large quarterly misses that largely offset; elasticity 0.17 (1990s), 0.41 (2000s), 0.30 (since 2010)", fontsize=11, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, .96))
    fig.savefig(OUT / "fig_p4b_bridge_validation.png")
    plt.close(fig)


def fig_uncertainty():
    cov = pd.read_csv(OUT / "uncertainty_fan_coverage.csv")
    sp = pd.read_csv(OUT / "uncertainty_specification_vs_parameter.csv")
    acc = pd.read_csv(OUT / "uncertainty_sources_accounting.csv", index_col=0)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    ax = axes[0]
    per_cols = {"targets to 2019Q4": BLUE, "2020Q1-2023Q2": ORANGE, "2023Q3-2026Q2": VIOLET}
    for lab, col in per_cols.items():
        s = cov[(cov["target period"] == lab)]
        ax.plot(s["h"], s["coverage of 90% fan"], color=col, lw=2, marker="o", label=lab)
    ax.axhline(0.9, color=INK, lw=1, ls="--"); ax.text(1.1, .915, "nominal 90%", fontsize=8)
    ax.set_xticks([1, 4, 8, 12]); ax.set_ylim(0, 1); ax.set_xlabel("quarters ahead"); ax.set_ylabel("share of outturns inside the 90% fan")
    ax.set_title("Baseline-fan coverage at past origins"); ax.legend(fontsize=8, loc="lower left")
    ax = axes[1]
    s = sp[sp.measure == "y/y dev 1y (pp)"].reset_index(drop=True)
    for i, r in s.iterrows():
        ax.plot([i - .12] * 2, [r["headline"] - r["HAC 90% parameter band width"] / 2, r["headline"] + r["HAC 90% parameter band width"] / 2], color=BLUE, lw=6, solid_capstyle="butt",
                label="90% parameter band (what Phase 4 shows)" if i == 0 else None)
        ax.plot([i + .12] * 2, [r["min across specifications"], r["max across specifications"]], color=ORANGE, lw=6, solid_capstyle="butt",
                label="range across specifications" if i == 0 else None)
        ax.plot([i], [r["headline"]], color=INK, marker="D", ms=5, zorder=5, label="headline" if i == 0 else None)
    ax.set_xticks(range(len(s))); ax.set_xticklabels(s["scenario"], rotation=35, ha="right")
    ax.set_title("Scenario effect after 1 year (pp): parameter band vs specifications"); ax.legend(fontsize=7.5)
    ax = axes[2]
    cats = ["model fan s.d. (parameters + residuals + bridge noise, drivers fixed)", "RMSE tier B (realised drivers, structural only)", "RMSE tier C (adds bridge)",
            "RMSE tier D (real-time: adds driver assumptions)", "RMSE AR(4)"]
    names = ["model fan s.d.", "B: realised drivers", "C: + bridge", "D: real-time", "AR(4)"]
    cols = [BLUE, AQUA, YELLOW, ORANGE, "#8a8985"]
    w = .16
    for j, (c, n, col) in enumerate(zip(cats, names, cols)):
        ax.bar(np.arange(3) + (j - 2) * w, acc[c].values, width=w * .92, color=col, label=n, edgecolor="white", linewidth=.8)
    ax.set_xticks(range(3)); ax.set_xticklabels(["1 year", "2 years", "3 years"])
    ax.set_ylabel("pp of y/y inflation"); ax.set_title("What the error scale is made of (all targets)"); ax.legend(fontsize=7.5)
    fig.suptitle("Uncertainty: the Phase 4 bands cover parameters only; historical real-time errors are 2-3 times the model fan", fontsize=11, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(OUT / "fig_p4b_uncertainty.png")
    plt.close(fig)


def main():
    ctx = C.load()
    d = ctx.data_star
    paths = pd.read_csv(OUT / "forecast_paths_selected.csv")
    forecast_panels(["2019Q4", "2020Q4", "2021Q2", "2021Q4", "2022Q2", "2022Q4"], "Forecast vs actual, origins 2019Q4-2022Q4 (y/y CPI inflation)", "fig_p4b_forecast_vs_actual_2020_23.png", d, paths)
    forecast_panels(["2023Q4", "2024Q2", "2024Q4", "2025Q2", "2025Q4", "2026Q1"], "Forecast vs actual, origins 2023Q4-2026Q1 (y/y CPI inflation)", "fig_p4b_forecast_vs_actual_2024_26.png", d, paths)
    fig_decomp(); fig_wage(); fig_baseline(d); fig_bridge(); fig_uncertainty()


if __name__ == "__main__":
    main()
