"""Phase 4c figures: IRF overlays (three B* vintages + the authors' hybrid model), coefficient stability, identification, replication, stable-parameter null.

Colours: categorical slots 1-3 of the reference palette (validated, all-pairs) for B*-2019 / -2023 / -2026; the authors' model is dashed neutral ink. The aqua slot is below 3:1
on the light surface, so every chart carries a legend and distinct line styles, and every plotted number is in a CSV (outputs/phase4c/irf_paths.csv etc.)."""
import sys
import textwrap
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.phase4c import compare as CP  # noqa: E402
from bb_inflation.phase4c import ident as ID  # noqa: E402
from bb_inflation.phase4c import irf as I  # noqa: E402
from bb_inflation.phase4c import samples as S  # noqa: E402
from bb_inflation.phase4c import study as ST  # noqa: E402
from bb_inflation.phase4c import tables as T  # noqa: E402

OUT = S.OUT
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
COL = {"B*-2019": "#2a78d6", "B*-2023": "#eb6834", "B*-2026": "#1baf7a"}
LS = {"B*-2019": "-", "B*-2023": "--", "B*-2026": "-"}
LW = {"B*-2019": 1.6, "B*-2023": 1.6, "B*-2026": 2.2}
AUTH = "Authors (published hybrid)"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "font.family": "sans-serif", "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False})

paths = pd.read_csv(OUT / "irf_paths.csv")
cat = pd.read_csv(OUT / "irf_shock_catalogue.csv").set_index("id")
UNITS = {"gcpi": "pp, annualised", "gw": "pp, annualised", "cf1": "pp", "cf10": "pp", "plevel": "% of price level"}
TITLE = {"gcpi": "CPI inflation", "gw": "Wage inflation", "cf1": "1-year expected inflation", "cf10": "10-year expected inflation", "plevel": "Cumulative CPI price level"}


def series(conv, shock, vint, var):
    d = paths[(paths.convention == conv) & (paths.shock == shock) & (paths.vintage == vint) & (paths.variable == var)].sort_values("h")
    return d


def draw_panel(ax, conv, shock, var, legend=False, small=False):
    for v in COL:
        d = series(conv, shock, v, var)
        ax.fill_between(d.h, d.q05, d.q95, color=COL[v], alpha=0.13, lw=0)
        ax.plot(d.h, d.point, color=COL[v], ls=LS[v], lw=LW[v] * (0.8 if small else 1), label=v)
    a = series(conv, shock, AUTH, var)
    if len(a):
        ax.plot(a.h, a.point, color=INK2, ls=":", lw=1.6 * (0.8 if small else 1), label="Authors (published hybrid), same shock")
    ax.axhline(0, color=MUTED, lw=0.7)
    ax.set_xlim(0, I.HREP)
    ax.set_xticks([0, 4, 8, 12])
    ax.set_title(TITLE[var] + ("" if small else f" ({UNITS[var]})"), loc="left", fontsize=8.5 if small else 10)
    if not small:
        ax.set_xlabel("quarters after the shock (h = 0 is the shock quarter)")


def shock_figure(shock, conv="nominal", name=None):
    s = cat.loc[shock]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7))
    for ax, var in zip(axes.flat, I.VARS):
        draw_panel(ax, conv, shock, var)
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l + [], loc="lower center", ncol=4, fontsize=8.5)
    band = "Shaded: 90% parameter bands (joint draws, overlap preserved)."
    conv_txt = "Energy and food prices nominal (relative prices endogenous)" if conv == "nominal" else "Relative energy/food prices held fixed (authors' convention)"
    fig.suptitle(f"{shock}: {s['shock']}", x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.935, textwrap.fill(f"{s['definition']}. {conv_txt}. {band}", 150), fontsize=8.5, color=INK2, ha="left", va="center")
    fig.tight_layout(rect=(0, 0.05, 1, 0.91))
    fig.savefig(FIG / (name or f"irf_{shock}_{conv}.png"), dpi=150)
    plt.close(fig)


for sh in cat.index:
    shock_figure(sh, "nominal")
for sh in ("W1", "W2", "V1", "V1P", "E1", "E10", "P1"):
    shock_figure(sh, "relative")


def overview(var, name, shocks):
    fig, axes = plt.subplots(3, 4, figsize=(13, 8.2))
    for ax, sh in zip(axes.flat, shocks):
        draw_panel(ax, "nominal", sh, var, small=True)
        ax.set_title(textwrap.fill(f"{sh}: {cat.loc[sh, 'shock']}", 34), loc="left", fontsize=8)
    for ax in axes.flat[len(shocks):]:
        ax.axis("off")
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=9)
    fig.suptitle(f"{TITLE[var]} response to each shock, by estimation sample ({UNITS[var]})", x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(FIG / name, dpi=140)
    plt.close(fig)


SH12 = ["W1", "W2", "O10", "O30", "O10T", "V1", "V1P", "G1", "G1S", "E1", "E10", "P1"]
overview("gcpi", "overview_cpi_inflation.png", SH12)
overview("plevel", "overview_cpi_price_level.png", SH12)

# ----------------------------------------------------------------------------------------------------------------------------------
# coefficient stability: forest of block sums
bt = pd.read_csv(OUT / "blocks.csv")
KEY = [("gcpi", "gw"), ("gw", "gw"), ("gw", "cf1"), ("gw", "diffcpicf"), ("gw", "vu"), ("cf1", "gcpi"), ("cf10", "gcpi"), ("gcpi", "grpe"), ("gcpi", "grpf"), ("gcpi", "shortagema2")]
fig, axes = plt.subplots(2, 5, figsize=(14, 6.2))
vs = [("B*-2019", COL["B*-2019"], "o"), ("B*-2023", COL["B*-2023"], "s"), ("B*-2026", COL["B*-2026"], "D"), (AUTH, INK2, "^")]
for ax, (eq, b) in zip(axes.flat, KEY):
    for i, (v, c, m) in enumerate(vs):
        r = bt[(bt["eq"] == eq) & (bt.block == b) & (bt.vintage == v)]
        if not len(r) or (v == AUTH and b == "shortagema2"):
            continue
        r = r.iloc[0]
        y = len(vs) - i
        ax.plot([r.ci95_lo, r.ci95_hi], [y, y], color=c, lw=1.6)
        ax.plot([r["sum"]], [y], marker=m, color=c, ms=6, mec=SURF, mew=1.0, ls="none")
    ax.axvline(0, color=MUTED, lw=0.7)
    ax.set_yticks([4, 3, 2, 1])
    ax.set_yticklabels(["B*-2019", "B*-2023", "B*-2026", "Authors"] if ax in axes[:, 0] else [""] * 4, fontsize=8)
    ax.set_title(textwrap.fill(T.LABEL[(eq, b)], 28), loc="left", fontsize=8)
    ax.grid(axis="y", visible=False)
fig.suptitle("Sums of lag coefficients with 95% HAC intervals, by estimation sample", x=0.01, ha="left", fontsize=12, fontweight="bold")
fig.text(0.01, 0.935, "Authors' interval: their published hybrid model re-estimated on their own data with HAC errors (omitted for the GSCPI panel: Google 'shortage' is a different variable).", fontsize=8.5, color=INK2)
fig.tight_layout(rect=(0, 0, 1, 0.92))
fig.savefig(FIG / "coef_forest_blocks.png", dpi=150)
plt.close(fig)

# recursive estimates
rec = pd.read_csv(OUT / "stability_recursive.csv")
fig, axes = plt.subplots(2, 5, figsize=(14, 6.2))
for ax, (eq, b) in zip(axes.flat, KEY):
    r = rec[(rec["eq"] == eq) & (rec.block == b)].reset_index(drop=True)
    x = np.arange(len(r))
    ax.fill_between(x, r["sum"] - 1.96 * r.se_hac, r["sum"] + 1.96 * r.se_hac, color=COL["B*-2019"], alpha=0.14, lw=0)
    ax.plot(x, r["sum"], color=COL["B*-2019"], lw=1.8)
    ax.axhline(0, color=MUTED, lw=0.7)
    ax.set_xticks([0, 4, 8, 12, 16, 20, 24, 28][:len(r) // 4 + 1])
    ax.set_xticklabels([r.end[i] for i in range(0, len(r), 4)], rotation=45, fontsize=7)
    ax.set_title(textwrap.fill(T.LABEL[(eq, b)], 28), loc="left", fontsize=8)
fig.suptitle("Recursive estimates: block sum when the sample ends at each quarter (1990Q1 start), with 95% HAC bands", x=0.01, ha="left", fontsize=12, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(FIG / "coef_recursive_blocks.png", dpi=150)
plt.close(fig)

# stable-parameter null: observed change vs bootstrap distribution
boot = pd.read_csv(OUT / "stability_null_bootstrap_draws.csv")
ns = pd.read_csv(OUT / "block_changes_null_bootstrap.csv")
fig, axes = plt.subplots(2, 5, figsize=(14, 6))
for ax, (eq, b) in zip(axes.flat, KEY):
    d = boot[f"{eq}:{b}:B26"] - boot[f"{eq}:{b}:B19"]
    d = d - d.mean()
    row = ns[(ns["eq"] == eq) & (ns.block == b) & (ns["from"] == "B*-2019") & (ns["to"] == "B*-2026")].iloc[0]
    ax.hist(d, bins=30, color=COL["B*-2019"], alpha=0.35, edgecolor=SURF)
    ax.axvline(row["observed change"], color=COL["B*-2023"], lw=2)
    ax.axvline(-row["observed change"], color=COL["B*-2023"], lw=1, ls=":")
    ax.set_title(textwrap.fill(T.LABEL[(eq, b)], 28) + f"\nobserved {row['observed change']:+.3f}, p = {row['p (observed vs null, bias-centred)']:.2f}", loc="left", fontsize=7.5)
    ax.grid(False)
    ax.set_yticks([])
fig.suptitle("Is the 2019 -> 2026 change in each block sum larger than sampling noise under constant parameters? (bootstrap null, B*-2026 as the true model)", x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.text(0.01, 0.93, "Histogram: B*-2026 minus B*-2019 estimate across replications (bias-centred). Orange line: the change actually observed (dotted: its mirror image).", fontsize=8.5, color=INK2)
fig.tight_layout(rect=(0, 0, 1, 0.91))
fig.savefig(FIG / "stability_null_bootstrap.png", dpi=150)
plt.close(fig)

# ----------------------------------------------------------------------------------------------------------------------------------
# GSCPI identification
st = ST.build(n=50)
d = st.data
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
ax = axes[0]
x = d["shortage"].loc["1998Q1":]
ax.plot(x.index.to_timestamp(), x.values, color=INK2, lw=1.2)
ax.axvspan(pd.Timestamp("1998-01-01"), pd.Timestamp("2019-12-31"), color=COL["B*-2019"], alpha=0.10, lw=0)
ax.axvspan(pd.Timestamp("2020-01-01"), pd.Timestamp("2023-12-31"), color=COL["B*-2023"], alpha=0.12, lw=0)
ax.set_title("GSCPI (quarterly mean, s.d. units): range\n-1.1 to +0.9 before 2020, to +4.3 after", loc="left", fontsize=9)
ax = axes[1]
for vk in S.MAIN:
    r = ID.partial_regressor(st.fits[vk]["gcpi"], d, "shortagema2_L0")
    ax.plot(r.index.to_timestamp(), (r ** 2).cumsum() / (r ** 2).sum(), color=COL[S.LABEL[vk]], ls=LS[S.LABEL[vk]], lw=1.8, label=S.LABEL[vk])
ax.set_title("Cumulative share of the identifying variation\n(squared FWL residual of GSCPI given the other regressors)", loc="left", fontsize=9)
ax.legend(fontsize=8)
lo = pd.read_csv(OUT / "ident_gscpi_leave_out.csv")
sub = fig.add_gridspec(1, 1)
axes[2].remove()
inner = axes[2].get_subplotspec().subgridspec(1, 2, wspace=0.9)
for k, (vint, c) in enumerate((("B*-2019", COL["B*-2019"]), ("B*-2026", COL["B*-2026"]))):
    ax = fig.add_subplot(inner[0, k])
    g = lo[lo.vintage == vint].reset_index(drop=True)
    ax.scatter(g.estimate, np.arange(len(g)), color=c, s=14)
    ax.axvline(g.estimate[0], color=c, lw=0.8, ls=":")
    ax.axvline(0, color=MUTED, lw=0.7)
    ax.set_yticks(range(len(g)))
    ax.set_yticklabels([v.replace("start 1998Q1 (drops constant-filled GSCPI)", "start 1998Q1").replace("drop ", "") for v in g.variant], fontsize=6)
    ax.set_title(f"{vint}: GSCPI coef.\nleave out 16q", loc="left", fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "ident_gscpi.png", dpi=150)
plt.close(fig)

# ----------------------------------------------------------------------------------------------------------------------------------
# authors' IRF replication
ap = pd.read_csv(OUT / "authors_irf_paths.csv")
from bb_inflation.simulation.irf import irf, shock_sizes  # noqa: E402
from bb_inflation.validation.authors_outputs import authors_model, authors_sim_data, read_core  # noqa: E402

adata = authors_sim_data("full")
resid = {k: adata[f"{k}_residuals"] for k in ("gw", "gcpi", "cf1", "cf10")}
sz = shock_sizes(adata, resid)
full, hyb = authors_model("full"), authors_model("precovid")
fig, axes = plt.subplots(1, 4, figsize=(14, 3.8))
for ax, (lab, (fname, var)) in zip(axes, {"Energy (rel. price, 1 s.d.)": ("results_energy.xls", "grpe"), "Food (rel. price, 1 s.d.)": ("results_food.xls", "grpf"),
                                          "Shortage index (1 s.d.)": ("results_shortage.xls", "shortage"), "V/U (1 s.d., permanent)": ("results_vu.xls", "vu")}.items()):
    ref = read_core("IRFs", fname)["gcpi_simul"].values[4:4 + 28]
    f = irf(full, var, sz[var])["gcpi_simul"].values[4:4 + 28]
    h = irf(hyb, var, sz[var])["gcpi_simul"].values[4:4 + 28]
    ax.plot(ref, color=INK, lw=3, alpha=0.35, label="authors' shipped file")
    ax.plot(f, color=COL["B*-2019"], lw=1.4, ls="--", label="our replication (their full-sample coefficients)")
    ax.plot(h, color=COL["B*-2023"], lw=1.4, label="their hybrid coefficients (paper's stated baseline)")
    ax.set_title(lab, loc="left", fontsize=9)
    ax.set_xlabel("quarters after the shock")
axes[0].set_ylabel("CPI inflation response (pp, annualised)")
axes[0].legend(fontsize=7, loc="upper right")
fig.suptitle("Replication of the authors' IRFs (Figures 10-11): the shipped files reproduce exactly from the full-sample coefficients, not the hybrid ones", x=0.01, ha="left", fontsize=11, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.92))
fig.savefig(FIG / "authors_irf_replication.png", dpi=150)
plt.close(fig)

# ----------------------------------------------------------------------------------------------------------------------------------
# persistence: normalised CPI response to one-period impulses, h = 0..40 (point estimates)
st = ST.build(n=50)
sd = CP.gscpi_sd(st.data)
cat2 = I.shock_catalogue(sd)
b = I.bridge().coef.values[1:]
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
for ax, vk in zip(axes, ("B19", "B26")):
    cs = st.coefset(vk, point=True)
    for sh, c, ls in (("V1P", "#2a78d6", "-"), ("G1", "#eb6834", "-"), ("O10", "#1baf7a", "-"), ("W1", INK2, "--"), ("E10", "#e87ba4", "-")):
        g = I.run(cs, cat2[sh], "nominal", b)["gcpi"][0]
        y = np.array([g[max(0, h - 3):h + 1].sum() / 4 for h in range(len(g))])
        pk = y[:13][np.abs(y[:13]).argmax()]
        ax.plot(np.arange(len(y)), y / abs(pk), color=c, ls=ls, lw=1.6, label=f"{sh}: {cat2[sh].label}")
    ax.axhline(0, color=MUTED, lw=0.7)
    ax.axvline(12, color=MUTED, lw=0.7, ls=":")
    ax.set_title(f"{S.LABEL[vk]}: y/y CPI response as a share of its peak\n(one-period shocks; O10 = sustained Brent level shift)", loc="left", fontsize=9)
    ax.set_xlabel("quarters after the shock")
axes[1].legend(fontsize=7, loc="upper right")
fig.tight_layout()
fig.savefig(FIG / "persistence_impulses.png", dpi=150)
plt.close(fig)
print("figures:", sorted(p.name for p in FIG.glob("*.png")))
