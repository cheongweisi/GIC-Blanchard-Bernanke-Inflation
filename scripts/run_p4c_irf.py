"""Phase 4c, Task 4: impulse responses of the four endogenous variables to the shock catalogue, for B*-2019 / B*-2023 / B*-2026 (+ hybrid and the authors' model).

Same shock definitions and units for every vintage; deviations from a common baseline (the model is linear, so initial conditions drop out); the oil bridge is the
Phase 4 bridge for every vintage; bands are 90% over joint coefficient draws (overlap preserved). Writes only to outputs/phase4c/."""
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.phase4c import compare as CP  # noqa: E402
from bb_inflation.phase4c import irf as I  # noqa: E402
from bb_inflation.phase4c import samples as S  # noqa: E402
from bb_inflation.phase4c import study as ST  # noqa: E402

OUT = S.OUT


def save(df, name, index=False):
    df.to_csv(OUT / name, index=index)
    print(f"  {name}: {df.shape}")


t0 = time.time()
st = ST.build()
R = CP.run_all(st)
cat = pd.DataFrame([{"id": k, "shock": s.label, "family": s.family, "type": s.kind, "size": s.size, "unit": s.unit, "definition": s.note, "headline": s.headline}
                    for k, s in R.shocks.items()])
save(cat, "irf_shock_catalogue.csv")
save(R.paths, "irf_paths.csv")
save(R.stats, "irf_stats.csv")
save(R.diffs, "irf_stat_differences.csv")
save(R.path_diffs, "irf_path_differences.csv")
save(CP.oil_bridge_sensitivity(st), "irf_oil_bridge_sensitivity.csv")
save(CP.persistence_table(st), "irf_persistence_yoy.csv")

# shock-size reference: the GSCPI standard deviation depends on the window; IRFs are linear in size, so any other size is a rescaling
d = st.data
ref = pd.DataFrame([{"window": w, "GSCPI s.d. (quarterly mean)": float(d["shortage"].loc[a:b].std(ddof=1)), "scale factor vs headline": float(d["shortage"].loc[a:b].std(ddof=1)) / CP.gscpi_sd(d)}
                    for w, (a, b) in {"1998Q1-2026Q2 (headline, common to all vintages)": ("1998Q1", "2026Q2"), "1998Q1-2019Q4 (pre-pandemic)": ("1998Q1", "2019Q4"),
                                      "2020Q1-2023Q2 (authors' convention: pandemic window)": ("2020Q1", "2023Q2"), "2020Q1-2026Q2": ("2020Q1", "2026Q2")}.items()])
save(ref, "irf_gscpi_shock_size_reference.csv")
b = I.bridge()
save(pd.DataFrame([{"shock": "Brent +10%", "log points": 100 * np.log(1.1), "first-year CPI-energy level effect (%)": 100 * np.log(1.1) * b.elasticity,
                    "bridge elasticity (sum of lags)": b.elasticity, "bridge elasticity s.e. (HAC)": b.elasticity_se()},
                   {"shock": "Brent +30%", "log points": 100 * np.log(1.3), "first-year CPI-energy level effect (%)": 100 * np.log(1.3) * b.elasticity,
                    "bridge elasticity (sum of lags)": b.elasticity, "bridge elasticity s.e. (HAC)": b.elasticity_se()}]), "irf_oil_shock_sizes.csv")

# comparable-multiplier table (headline convention) -------------------------------------------------------------------------------
STATS = ["h=1", "h=4", "h=8", "h=12", "peak (h<=12)", "quarter of peak", "price level, cumulative to h=4 (%)", "price level, cumulative to h=8 (%)",
         "price level, cumulative to h=12 (%)", "wage level, cumulative to h=12 (%)", "ratio h=12 / peak", "half-life from peak (q)", "h=40", "price level, h=40 (%)"]
s = R.stats[R.stats.statistic.isin(STATS)].copy()
fmt = lambda r: (f"{r['point']:.3f} [{r['lo90']:.3f}, {r['hi90']:.3f}]" if pd.notna(r["lo90"]) else f"{r['point']:.3f}")       # noqa: E731
s["text"] = s.apply(fmt, axis=1)
wide = s.pivot_table(index=["convention", "shock", "variable", "statistic"], columns="vintage", values="text", aggfunc="first").reset_index()
d_ = R.diffs[R.diffs.statistic.isin(STATS)].copy()
d_["text"] = d_.apply(lambda r: f"{r['difference']:+.3f} [{r['lo90']:+.3f}, {r['hi90']:+.3f}] p={r['p (two-sided, from draws)']:.2f}", axis=1)
dw = d_.pivot_table(index=["convention", "shock", "variable", "statistic"], columns="change", values="text", aggfunc="first").reset_index()
mult = wide.merge(dw, on=["convention", "shock", "variable", "statistic"], how="left")
order = {k: i for i, k in enumerate(R.shocks)}
sorder = {k: i for i, k in enumerate(STATS)}
mult["_a"], mult["_b"] = mult["shock"].map(order), mult["statistic"].map(sorder)
mult = mult.sort_values(["convention", "_a", "variable", "_b"]).drop(columns=["_a", "_b"])
save(mult, "multipliers_comparable.csv")
print(f"done in {time.time() - t0:.0f}s")
