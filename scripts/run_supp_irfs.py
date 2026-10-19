"""Phase 3 supplement, part 2: impulse responses in interpretable units (annualised inflation, y/y inflation, price level).
Writes outputs/phase3_supp/irf_*.csv and fig_s4_irf_intuitive.png. Phase 3 IRF outputs are not modified."""
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
from bb_inflation.estimation.inference import with_hac  # noqa: E402
from bb_inflation.extension.models import fit, standard_models  # noqa: E402
from bb_inflation.simulation.model import SimModel  # noqa: E402
from bb_inflation.supplement import context as C  # noqa: E402
from bb_inflation.supplement import irf_intuitive as I  # noqa: E402
from bb_inflation.validation.specs import VARIANTS  # noqa: E402

OUT = OUTPUTS / "phase3_supp"
OUT.mkdir(parents=True, exist_ok=True)
SIZES = {"Energy": 10.0, "Food": 5.0, "GSCPI": 1.0, "V/U": 0.1}          # % relative price, % relative price, std. dev., ratio
UNITS = {"Energy": "+10% in the relative price of CPI energy", "Food": "+5% in the relative price of CPI food",
         "GSCPI": "+1.0 on the NY Fed GSCPI (one standard deviation)", "V/U": "+0.1 on V/U (e.g. 0.95 to 1.05)"}
COL = {"temporary": "#1f77b4", "persistent": "#ff7f0e", "permanent": "#d62728"}


def regression_check(ctx) -> pd.DataFrame:
    """The new IRF code must reproduce Phase 3's Model B responses when given Phase 3's shock sizes (annualised, pp)."""
    ms = standard_models(ctx.last)
    B = fit(ms["B"], ctx.p3.data, ctx.last)                      # Phase 3 baseline (hole left open)
    model = SimModel.from_results(B)
    derived = VARIANTS["gscpi_ma2"].derived_dict
    old = pd.read_pickle(OUTPUTS / "phase3" / "irfs_paths.pkl")
    sz = pd.read_csv(OUTPUTS / "phase3" / "irfs_shock_sizes.csv", index_col=0).iloc[:, 0]
    cases = [("V/U", "temporary", sz["vu"], "V/U temporary"), ("V/U", "permanent", sz["vu"], "V/U permanent"),
             ("GSCPI", "temporary", sz["shortage"], "GSCPI temporary"), ("GSCPI", "permanent", sz["shortage"], "GSCPI permanent"),
             ("GSCPI", "persistent", sz["shortage"], "GSCPI persistent (rho 0.8)"),
             ("Energy", "permanent", sz["grpe"] / 4.0, "Energy one-off (level)"), ("Food", "permanent", sz["grpf"] / 4.0, "Food one-off (level)")]
    rows = []
    for drv, kind, size, label in cases:
        new = I.simulate(model, drv, kind, size, derived)[:28]
        ref = old[("B", label)]["point"]
        rows.append({"new scenario": f"{drv} {kind}", "Phase 3 IRF": label, "max abs difference (pp)": float(np.abs(new - ref).max())})
    return pd.DataFrame(rows)


def fmt_range(r, key, nd=2):
    return f"{r[key]:.{nd}f} [{r[key + ' | lo90']:.{nd}f}, {r[key + ' | hi90']:.{nd}f}]"


def main() -> None:
    ctx = C.load()
    last, d = ctx.last, ctx.data_star
    chk = regression_check(ctx)
    chk.to_csv(OUT / "irf_regression_check_vs_phase3.csv", index=False)
    assert chk["max abs difference (pp)"].max() < 1e-9, chk

    ms = standard_models(last)
    derived = VARIANTS["gscpi_ma2"].derived_dict
    out = {}
    for name, key in (("Bstar", "B"), ("A", "A")):
        res = fit(ms[key], d, last)
        hac = {k: with_hac(r, d) for k, r in res.items()}
        tab, paths = I.run(SimModel.from_results(res), I.draws(hac, 1000, 0), SIZES, derived)
        tab.insert(0, "model", name)
        out[name] = (tab, paths)
        tab.to_csv(OUT / f"irf_scenarios_{name}.csv", index=False)
        long = []
        for (drv, kind), p in paths.items():
            a = p["point"][None, :]
            ya, yy, ll = a[0], I.yoy(a)[0], I.price_level(a)[0]
            qa, qy, ql = (np.quantile(I.yoy(p["draws"]), [.05, .95], axis=0), np.quantile(I.price_level(p["draws"]), [.05, .95], axis=0),
                          np.quantile(p["draws"], [.05, .95], axis=0))
            for h in range(I.HZ):
                long.append({"model": name, "driver": drv, "persistence": kind, "h": h, "annualised_pp": ya[h], "annualised_lo90": ql[0, h],
                             "annualised_hi90": ql[1, h], "yoy_pp": yy[h], "yoy_lo90": qa[0, h], "yoy_hi90": qa[1, h],
                             "price_level_pct": ll[h], "price_level_lo90": qy[0, h], "price_level_hi90": qy[1, h]})
        pd.DataFrame(long).to_csv(OUT / f"irf_paths_{name}.csv", index=False)
    anc = I.anchors(d)
    anc.to_csv(OUT / "irf_shock_size_anchors.csv", index=False)
    pd.Series({k: v for k, v in SIZES.items()}).to_csv(OUT / "irf_shock_sizes_used.csv", header=["size"])

    tab = out["Bstar"][0]
    # compact headline table (Model B*)
    rows = []
    for _, r in tab.iterrows():
        rows.append({"shock": f"{r.driver}: {UNITS[r.driver]}", "persistence": r.persistence,
                     "annualised peak pp [90%] (quarter)": f"{fmt_range(r, 'annualised: peak (pp)')} (q{int(r['annualised: quarter of peak'])})",
                     "y/y peak pp [90%] (quarter)": f"{fmt_range(r, 'y/y: peak (pp)')} (q{int(r['y/y: quarter of peak'])})",
                     "y/y half-life (q)": r["y/y: half-life from peak (q)"], "y/y faded to 25% of peak (q)": r["y/y: faded to 25% of peak (q after shock)"],
                     "price level peak % (quarter)": f"{fmt_range(r, 'price level: peak (%)')} (q{int(r['price level: quarter of peak'])})",
                     "y/y after 3y as % of peak": r["y/y after 3 years, % of peak"],
                     "price level 1y %": fmt_range(r, "price level: after 1 year (%)"), "price level 2y %": fmt_range(r, "price level: after 2 years (%)"),
                     "price level 3y %": fmt_range(r, "price level: after 3 years (%)")})
    pd.DataFrame(rows).to_csv(OUT / "irf_headline_table_Bstar.csv", index=False)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 40)
    pd.set_option("display.max_colwidth", 60)
    print(chk.to_string())
    print(pd.DataFrame(rows).drop(columns=["shock"]).to_string())
    print(anc.round(2).to_string())
    cmp = out["A"][0].set_index(["driver", "persistence"])[["y/y: peak (pp)", "price level: after 3 years (%)"]].join(
        out["Bstar"][0].set_index(["driver", "persistence"])[["y/y: peak (pp)", "price level: after 3 years (%)"]], lsuffix=" A", rsuffix=" B*")
    print(cmp.round(3).to_string())
    figure(out["Bstar"][1])


def figure(paths):
    drivers = list(I.DRIVERS)
    fig, axes = plt.subplots(len(drivers), 3, figsize=(16, 3.2 * len(drivers)), sharex=True)
    x = np.arange(I.HZ)
    titles = ["Annualised quarterly CPI inflation (pp) — model's native response", "Year-on-year CPI inflation (pp)",
              "CPI price level (% above baseline)"]
    for i, drv in enumerate(drivers):
        for kind in I.KINDS:
            p = paths[(drv, kind)]
            views = (p["point"][None, :], I.yoy(p["point"][None, :]), I.price_level(p["point"][None, :]))
            dviews = (p["draws"], I.yoy(p["draws"]), I.price_level(p["draws"]))
            for j in range(3):
                ax = axes[i, j]
                lo, hi = np.quantile(dviews[j], [.05, .95], axis=0)
                ax.fill_between(x, lo, hi, color=COL[kind], alpha=.12)
                ax.plot(x, views[j][0], color=COL[kind], lw=2, label=kind)
                ax.axhline(0, color="k", lw=.5)
                ax.grid(alpha=.25)
                if i == 0:
                    ax.set_title(titles[j], fontsize=9)
                if i == len(drivers) - 1:
                    ax.set_xlabel("quarters after the shock (0 = shock quarter)")
        axes[i, 0].set_ylabel(f"{drv}\n{UNITS[drv]}", fontsize=8)
        axes[i, 0].set_xlim(0, 24)
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("Impulse responses of US CPI inflation, Model B* (90% HAC Monte-Carlo bands). Shocks are to the LEVEL of the driver; "
                 "price level = cumulated annualised response / 4", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_s4_irf_intuitive.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
