"""Phase 3: IRFs (V/U, energy, food, GSCPI, expectations, wage and price shocks) for Models A, B, C with
HAC Monte-Carlo intervals. Writes outputs/phase3/irfs_*.csv and figures (extended Figures 10-11)."""
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
from bb_inflation.extension import irfs as I  # noqa: E402
from bb_inflation.extension.models import fit, standard_models  # noqa: E402

OUT = OUTPUTS / "phase3"
OUT.mkdir(parents=True, exist_ok=True)
COL = {"A": "#1f77b4", "B": "#ff7f0e", "C15": "#2ca02c", "C5": "#d62728"}


def panel(paths, labels, fname, title, ncols=4):
    n = len(labels)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.6 * ncols, 3.3 * nrows))
    x = np.arange(0, I.H)
    for ax, lab in zip(np.atleast_1d(axes).ravel(), labels):
        b = paths[("B", lab)]
        ax.fill_between(x, b["q05"], b["q95"], color="#fdd0a2", alpha=.6, label="B 90% (HAC MC)")
        a = paths[("A", lab)]
        ax.plot(x, a["q05"], color=COL["A"], lw=.7, ls=":")
        ax.plot(x, a["q95"], color=COL["A"], lw=.7, ls=":", label="A 90%")
        for m in ("A", "B", "C15"):
            ax.plot(x, paths[(m, lab)]["point"], color=COL[m], lw=1.8, label=m)
        ax.axhline(0, color="k", lw=.5)
        ax.set_title(lab, fontsize=9)
        ax.grid(alpha=.25)
        ax.set_xlabel("quarters after shock", fontsize=8)
    for ax in np.atleast_1d(axes).ravel()[n:]:
        ax.axis("off")
    np.atleast_1d(axes).ravel()[0].legend(frameon=False, fontsize=7)
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=140)
    plt.close(fig)


def main() -> None:
    p3 = P.build(PHASE3_PULL)
    last = str(p3.last_complete)
    ms = standard_models(last)
    use = ["A", "B", "C5", "C10", "C15", "A5", "B5"]
    res = {k: fit(ms[k], p3.data, last) for k in use}
    sizes = I.shock_sizes(p3.data_bridged, res["B"] and {k: res["B"][k].resid for k in ("gw", "gcpi", "cf1", "cf10")})
    pd.Series(sizes).to_csv(OUT / "irfs_shock_sizes.csv")
    stats, paths = I.run(res, ms, p3.data_bridged, p3.data_bridged, sizes, n_mc=1000, which=use)
    stats.to_csv(OUT / "irfs_stats.csv", index=False)
    pd.to_pickle(paths, OUT / "irfs_paths.pkl")
    labs1 = [s[0] for s in I.SHOCKS[:9]]
    labs2 = [s[0] for s in I.SHOCKS[9:]]
    panel(paths, labs1, "fig_p3_irfs_exogenous.png", "Fig. 10-11 extended: response of CPI inflation (pp) to +1 s.d. shocks (A, B, C15; shaded: Model B 90% HAC Monte-Carlo band)", 5)
    panel(paths, labs2, "fig_p3_irfs_residual.png", "Response of CPI inflation (pp) to one-off +1 s.d. equation shocks", 4)
    pd.set_option("display.width", 250)
    t = stats[stats.model.isin(["A", "B", "C15"])].pivot_table(index=["shock", "stat"], columns="model", values="point", sort=False)
    print(t.round(2).to_string())


if __name__ == "__main__":
    main()
