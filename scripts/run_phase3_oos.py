"""Phase 3 validation: expanding-window pseudo-out-of-sample evaluation and recent-weighting choice.
Writes outputs/phase3/oos_*.csv."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS, PHASE3_PULL  # noqa: E402
from bb_inflation.data import phase3_data as P  # noqa: E402
from bb_inflation.extension import pseudo_oos as O  # noqa: E402
from bb_inflation.extension.models import ModelSpec, fit  # noqa: E402

OUT = OUTPUTS / "phase3"
OUT.mkdir(parents=True, exist_ok=True)


def configs() -> dict[str, ModelSpec]:
    c = {"U": ModelSpec("U", "unweighted")}
    for h in (5, 10, 15):
        c[f"W{h}"] = ModelSpec(f"W{h}", f"all equations weighted, half-life {h}y", half_life_years=h)
    for h in (5, 10, 15):
        c[f"P{h}"] = ModelSpec(f"P{h}", f"price equation only weighted, half-life {h}y", half_life_years=h, weighted_eqs=("gcpi",))
    c["U5"] = ModelSpec("U5", "unweighted, gscpi5", variant="gscpi5")
    return c


def main() -> None:
    p3 = P.build(PHASE3_PULL)
    last = str(p3.last_complete)
    origins = list(pd.period_range("2004Q4", p3.last_complete - 1, freq="Q"))
    rec = O.run(p3.data, p3.data_bridged, last, configs(), origins)
    # Model A (frozen at 2023Q2) on origins from 2023Q2
    A = fit(ModelSpec("A", "frozen", end="2023Q2"), p3.data, last)
    recA = O.run(p3.data, p3.data_bridged, last, {"A": ModelSpec("A", "frozen")}, [o for o in origins if o >= pd.Period("2023Q2", "Q")],
                 frozen={"A": A}, include_ar4=False)
    rec.to_csv(OUT / "oos_records.csv", index=False)           # all origins, models without the frozen A
    recA.to_csv(OUT / "oos_records_frozenA.csv", index=False)  # frozen A: origins from 2023Q2 only
    summ = O.summarize(rec)
    summ.to_csv(OUT / "oos_summary.csv", index=False)
    post = pd.concat([rec, recA], ignore_index=True)
    post = post[pd.PeriodIndex(post["origin"], freq="Q") >= pd.Period("2023Q2", "Q")]
    O.summarize(post, by_bucket=False).to_csv(OUT / "oos_summary_post2023_origins.csv", index=False)
    cand = [f"W{h}" for h in (5, 10, 15)]
    sel_all = O.select_half_life(summ, cand, "U")
    sel_price = O.select_half_life(summ, [f"P{h}" for h in (5, 10, 15)], "U")
    pd.set_option("display.width", 250)
    s = summ[(summ["target bucket"] == "all targets") & (summ["var"] == "gcpi") & (summ["mode"] == "conditional")]
    print(s.pivot_table(index="model", columns="horizon", values="RMSE").round(2).to_string())
    print(sel_all)
    print(sel_price)
    pd.Series({"all_eq": sel_all["chosen"], "price_only": sel_price["chosen"]}).to_csv(OUT / "oos_selection.csv")
    pd.DataFrame({"all_eq_scores": sel_all["scores"]}).to_csv(OUT / "oos_selection_scores.csv")


if __name__ == "__main__":
    main()
