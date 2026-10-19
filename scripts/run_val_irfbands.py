"""Validation 4a: uncertainty bands for key IRFs - classical vs HAC Monte Carlo vs recursive block bootstrap.
Writes outputs/validation/irfbands_*.csv and a figure."""
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
from bb_inflation.estimation.inference import irf_bands_bootstrap, irf_bands_mc, with_hac  # noqa: E402
from bb_inflation.simulation.general import irf_general  # noqa: E402
from bb_inflation.simulation.irf import shock_sizes  # noqa: E402
from bb_inflation.simulation.model import SimModel  # noqa: E402
from bb_inflation.validation import oos  # noqa: E402
from bb_inflation.validation.specs import VARIANTS, data_for, datasets, equations_for  # noqa: E402

OUT = OUTPUTS / "validation"
OUT.mkdir(parents=True, exist_ok=True)
SPECS = ["google5", "gscpi_ma2"]
SHOCKS = ("vu", "grpe", "grpf", "shortage")
H = (0, 1, 4, 8, 16, 27)
NMC, NBOOT = 2000, 500


def main() -> None:
    ds = datasets(load_raw())
    rows, store = [], {}
    for sp in SPECS:
        v = VARIANTS[sp]
        data = data_for(v, ds)
        full = oos.fit_regime(v, data, "insample")
        sizes = shock_sizes(data, {k: full[k].resid for k in ("gw", "gcpi", "cf1", "cf10")})
        shocks = {s: sizes[s] for s in SHOCKS}
        derived = v.derived_dict
        fn = lambda m, s, z: irf_general(m, s, z, derived=derived)       # noqa: E731
        point = {s: fn(SimModel.from_results(full), s, z)["gcpi_simul"].values for s, z in shocks.items()}
        classic = irf_bands_mc(full, fn, shocks, n=NMC, seed=1)
        hac = irf_bands_mc({k: with_hac(r, data) for k, r in full.items()}, fn, shocks, n=NMC, seed=1)
        boot = irf_bands_bootstrap(equations_for(v, True), data, full, fn, shocks, n=NBOOT, block=6, seed=2)
        store[sp] = {"point": point, "classic": classic, "hac": hac, "boot": boot}
        for s in SHOCKS:
            for h in H:
                i = 4 + h
                rows.append({"spec": sp, "shock": s, "h": h, "point": point[s][i],
                             "classic 5%": classic[s]["q05"][i], "classic 95%": classic[s]["q95"][i],
                             "HAC 5%": hac[s]["q05"][i], "HAC 95%": hac[s]["q95"][i],
                             "bootstrap 5%": boot[s]["q05"][i], "bootstrap 95%": boot[s]["q95"][i],
                             "bootstrap median": boot[s]["q50"][i]})
        rows.append({"spec": sp, "shock": "_bootstrap replications ok", "h": -1, "point": float(boot["_n_ok"]["n"][0])})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "irfbands.csv", index=False)
    pd.to_pickle(store, OUT / "irfbands.pkl")
    pd.set_option("display.width", 250)
    print(df[(df.shock.isin(["vu", "shortage"])) & (df.h.isin([1, 8, 27]))].round(2).to_string())

    fig, axes = plt.subplots(len(SPECS), 3, figsize=(15, 3.8 * len(SPECS)), sharex=True)
    x = np.arange(-1, 28)
    for i, sp in enumerate(SPECS):
        for j, s in enumerate(("vu", "grpe", "shortage")):
            ax = axes[i, j]
            st = store[sp]
            sl = slice(3, 32)
            ax.fill_between(x, st["boot"][s]["q05"].values[sl], st["boot"][s]["q95"].values[sl], color="#fdae6b", alpha=.4, label="bootstrap 90%")
            ax.plot(x, st["hac"][s]["q05"].values[sl], color="#08519c", lw=1, ls="--", label="HAC MC 90%")
            ax.plot(x, st["hac"][s]["q95"].values[sl], color="#08519c", lw=1, ls="--")
            ax.plot(x, st["classic"][s]["q05"].values[sl], color="#999999", lw=1, ls=":", label="classical MC 90%")
            ax.plot(x, st["classic"][s]["q95"].values[sl], color="#999999", lw=1, ls=":")
            ax.plot(x, st["point"][s][sl], color="k", lw=2, label="point")
            ax.axhline(0, color="k", lw=.5)
            ax.set_title(f"{sp}: {s}", fontsize=9)
            ax.grid(alpha=.25)
    axes[0, 0].legend(frameon=False, fontsize=7)
    fig.suptitle("CPI inflation IRFs (pp) to +1 s.d. shocks: classical vs HAC vs bootstrap bands", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_irf_bands.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
