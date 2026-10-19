"""Phase 4: pseudo-out-of-sample ladder separating conditional predictions (realised regressors) from real-time-feasible forecasts.
Writes outputs/phase4/backtest_*.csv."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.scenarios import backtest as B  # noqa: E402
from bb_inflation.scenarios import scenario as S  # noqa: E402
from bb_inflation.scenarios import world as W  # noqa: E402

OUT = OUTPUTS / "phase4"


def main() -> None:
    w = S.finalise(W.build(nowcast=True, n_draws=10))
    rec = B.run(w)
    rec.to_csv(OUT / "backtest_records.csv", index=False)
    q, y = B.summarize(rec)
    q.to_csv(OUT / "backtest_summary_quarterly.csv", index=False)
    y.to_csv(OUT / "backtest_summary_yoy.csv", index=False)
    # reproducibility: tiers A and F against the Phase 3 stored pseudo-OOS records (model U, unweighted); targets up to 2025Q3 are unaffected
    # by the 2025Q4 V/U bridge (estimation and realised V/U differ only in 2025Q4)
    p3 = pd.read_csv(OUTPUTS / "phase3" / "oos_records.csv")
    p3 = p3[(p3.model == "U") & (p3["var"] == "gcpi")]
    chk = []
    for tier, mode in (("A", "conditional"), ("F", "unconditional")):
        a = rec[rec.tier == tier][["origin", "h", "target", "forecast"]]
        b = p3[p3["mode"] == mode][["origin", "h", "target", "forecast"]].rename(columns={"forecast": "phase3"})
        m = a.merge(b, on=["origin", "h", "target"])
        m = m[pd.PeriodIndex(m["target"], freq="Q") <= pd.Period("2025Q3", "Q")]
        chk.append({"tier": tier, "Phase 3 mode": mode, "n compared": len(m), "max |difference| (pp)": float((m.forecast - m.phase3).abs().max())})
    pd.DataFrame(chk).to_csv(OUT / "backtest_reproduces_phase3.csv", index=False)
    pd.set_option("display.width", 220)
    print(pd.DataFrame(chk))
    print(q[q["target period"] == "all targets"].pivot_table(index="tier", columns="horizon", values="RMSE (pp, annualised qtr.)").round(2))
    print(y[y["target period"] == "all targets"].pivot_table(index="tier", columns="horizon (quarters)", values="RMSE of y/y (pp)").round(2))
    print(y[y["target period"] == "2023Q3-2026Q2"].pivot_table(index="tier", columns="horizon (quarters)", values="RMSE of y/y (pp)").round(2))
    print(y[y["target period"] == "all targets"].pivot_table(index="tier", columns="horizon (quarters)", values="bias of y/y").round(2))


if __name__ == "__main__":
    main()
