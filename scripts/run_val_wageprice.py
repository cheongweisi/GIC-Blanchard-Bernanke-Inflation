"""Validation 3: ECI splice and sample-start robustness. Writes outputs/validation/wageprice_*.csv and figures."""
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
from bb_inflation.validation import wage_price as W  # noqa: E402
from bb_inflation.validation.specs import VARIANTS  # noqa: E402

OUT = OUTPUTS / "validation"
OUT.mkdir(parents=True, exist_ok=True)
SPECS = ["google5", "gscpi5", "gscpi_ma2"]


def main() -> None:
    raw = load_raw()
    rows, store = [], {}
    for sp in SPECS:
        v = VARIANTS[sp]
        for eci in W.ECI:
            data = W.build_data(raw, v, eci)
            for start in W.STARTS:
                r = W.run_case(data, v, start)
                store[(sp, eci, start)] = r
                rows.append({"shortage spec": sp, "ECI": eci, "start": start, **r["row"]})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "wageprice_robustness.csv", index=False)
    pd.to_pickle({k: {"irf_vu": r["irf_vu"], "band_vu": r["bands"]["vu"], "band_grpe": r["bands"]["grpe"]} for k, r in store.items()},
                 OUT / "wageprice_irfs.pkl")
    # genuine out-of-sample fit 2020Q1-2023Q2 (all equations estimated through 2019Q4) by ECI history
    from bb_inflation.validation import oos
    orows = []
    for sp in SPECS:
        v = VARIANTS[sp]
        for eci in W.ECI:
            d = W.build_data(raw, v, eci)
            res = oos.fit_regime(v, d, "genuine")
            fc = oos.dynamic_forecast(res, d, v)
            for r in oos.metrics(fc, d, {"shortage spec": sp, "ECI": eci, "forecast": "dynamic (genuine OOS)"}):
                orows.append(r)
            for r in oos.metrics(oos.one_step(res, d), d, {"shortage spec": sp, "ECI": eci, "forecast": "one-step (genuine OOS)"}):
                orows.append(r)
    odf = pd.DataFrame(orows)
    odf.to_csv(OUT / "wageprice_oos_by_eci.csv", index=False)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 40)
    print(odf[odf.variable.isin(["gw", "gcpi"])].pivot_table(index=["shortage spec", "ECI"], columns=["forecast", "variable"], values="RMSE").round(2).to_string())
    key = ["shortage spec", "ECI", "start", "N price", "wage:V/U sum (full)", "wage:V/U p HAC (full)",
           "wage:gw lags (full)", "wage:LR effect of +0.5 V/U, pp (full)", "price:wage pass-through (sum gw)",
           "price:lagged inflation (sum)", "price:lagged inflation p HAC", "price:shortage sum"]
    print(df[key].round(3).to_string())
    print(df[["shortage spec", "ECI", "start", "wage:V/U sum (pre)", "wage:V/U p HAC (pre)", "wage:R2 (pre)", "N wage (pre)",
              "wage:catch-up (full)", "wage:cf1 (full)"]].round(3).to_string())
    print(df[["shortage spec", "ECI", "start", "IRF vu gcpi h8", "IRF vu gcpi h8 lo", "IRF vu gcpi h8 hi", "IRF vu gcpi h27",
              "IRF vu gcpi h27 lo", "IRF vu gcpi h27 hi", "IRF vu gw h27", "IRF grpe gcpi h4"]].round(2).to_string())

    fig, axes = plt.subplots(len(SPECS), 3, figsize=(15, 3.6 * len(SPECS)), sharey="row")
    x = np.arange(-1, 28)
    cols = {"1990Q1": "#08519c", "2001Q1": "#cb181d", "2005Q1": "#238b45"}
    for i, sp in enumerate(SPECS):
        for j, start in enumerate(W.STARTS):
            ax = axes[i, j]
            for eci, ls in (("authors splice", "-"), ("Macrobond ECI", "--")):
                r = store[(sp, eci, start)]
                b = r["bands"]["vu"]
                ax.plot(x, r["irf_vu"][3:32], color=cols[start], ls=ls, lw=2, label=eci)
                if eci == "authors splice":
                    ax.fill_between(x, b["q05"].values[3:32], b["q95"].values[3:32], color=cols[start], alpha=.15)
            ax.axhline(0, color="k", lw=.6)
            ax.set_title(f"{sp}, sample from {start}", fontsize=9)
            ax.grid(alpha=.25)
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("CPI inflation response to a permanent +1 s.d. V/U shock (band: 90% HAC Monte Carlo, authors' ECI)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_wageprice_vu_irf.png", dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(1, 4, figsize=(16, 3.8))
    metrics = [("wage:V/U sum (full)", "V/U sum in wage equation"), ("wage:LR effect of +0.5 V/U, pp (full)", "LR wage effect of +0.5 V/U (pp)"),
               ("price:wage pass-through (sum gw)", "wage pass-through in price eq."), ("price:lagged inflation (sum)", "lagged inflation in price eq.")]
    sub = df[df["shortage spec"] == "gscpi_ma2"]
    for ax, (m, ttl) in zip(axes, metrics):
        for k, (eci, mk) in enumerate((("authors splice", "o"), ("Macrobond ECI", "s"))):
            s = sub[sub.ECI == eci]
            ax.plot(range(3), s[m].values, marker=mk, label=eci)
        ax.set_xticks(range(3))
        ax.set_xticklabels(W.STARTS)
        ax.set_title(ttl, fontsize=9)
        ax.grid(alpha=.25)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("gscpi_ma2 specification: sample start and ECI history", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_wageprice_coefficients.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
