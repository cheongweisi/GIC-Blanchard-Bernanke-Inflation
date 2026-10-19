"""Phase 4b part 3: medium-term baseline. Writes outputs/phase4b/baseline_*.csv."""
import dataclasses
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.phase4b import baseline as B  # noqa: E402
from bb_inflation.phase4b import common as K  # noqa: E402
from bb_inflation.scenarios import scenario as S  # noqa: E402


def main():
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    w = K.world()
    base = S.run(w, S.Scenario("base", "b"))
    m = S.measures(w, base)
    K.save(m[["gcpi_ann", "yoy_pct", "gw", "cf1", "cf10", "gE_nominal", "grpe", "gF_nominal", "diffcpicf", "oil_usd_qavg"]], "baseline_key_paths.csv")
    steps = B.reference_steps(w)
    K.save(steps, "baseline_reference_steps.csv")
    print(steps.round(2).to_string())
    drift = B.long_run_drift(w)
    K.save(drift, "baseline_long_run_drift.csv")
    print(drift.round(2).head(12).to_string())
    ct = B.constants_table(w)
    ct.loc[len(ct)] = ["V/U at which the estimated constant is neutral (no drift)", B.neutral_vu(w)]
    K.save(ct, "baseline_wage_constant.csv", index=False)
    print(ct.round(3).to_string())
    K.save(B.history_wedge(w), "baseline_history_vs_implied_wages.csv")
    print(B.history_wedge(w).round(2).to_string())
    # wage sensitivities: other estimation samples, neutral constant, wage add-factor equal to the recent residual run-rate
    rows = {}
    H = {"2026Q4": 1, "2027Q4": 5, "2028Q3": 8, "2029Q3": 12}
    def add(lab, run):
        mm = S.measures(w, run)
        rows[lab] = {**{f"y/y {k}": float(mm["yoy_pct"].iloc[i]) for k, i in H.items()},
                     **{f"wage growth {k}": float(mm["gw"].iloc[i]) for k, i in H.items()}}
    add("headline baseline (estimated constant, residuals zero)", base)
    add("neutral wage constant", S.run(w, S.Scenario("n", "n", wage_constant="neutral")))
    for lab, cs in B.alt_wage_models(w).items():
        w2 = dataclasses.replace(w, cs_point=cs, cs_draws=cs)
        add(f"all equations {lab}", S.run(w2, S.Scenario("a", "a")))
        # keep B* equations but swap only the wage equation
        v = {k: a.copy() for k, a in w.cs_point.values.items()}
        v["gw"] = cs.values["gw"]
        nm = dict(w.cs_point.names); nm["gw"] = cs.names["gw"]
        from bb_inflation.scenarios.engine import CoefSet
        w3 = dataclasses.replace(w, cs_point=CoefSet(nm, v), cs_draws=CoefSet(nm, v))
        add(f"wage equation only {lab}", S.run(w3, S.Scenario("a", "a")))
    r = w.res["gw"].resid
    for lab, n in (("last 4 quarters", 4), ("last 8 quarters", 8)):
        resid_run = float(r.iloc[-n:].mean())
        sh = np.r_[0.0, np.full(4, resid_run), np.zeros(8)]
        add(f"wage residual run-rate of {lab} ({resid_run:+.2f} pp) persists 4 quarters", S.run(w, S.Scenario("r", "r", wage_shock=tuple(sh))))
    t = pd.DataFrame(rows).T
    K.save(t, "baseline_wage_sensitivities.csv")
    print(t.round(2).to_string())


if __name__ == "__main__":
    main()
