"""Phase 4b part 4: oil -> CPI energy bridge validation. Writes outputs/phase4b/bridge_*.csv."""
import dataclasses
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.phase4b import bridge as BR  # noqa: E402
from bb_inflation.phase4b import common as K  # noqa: E402
from bb_inflation.scenarios import attribution as A  # noqa: E402
from bb_inflation.scenarios import library as L  # noqa: E402
from bb_inflation.scenarios import scenario as S  # noqa: E402

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)


def main():
    w = K.world()
    cpie, oil = w.cpie_m.loc[:"2026-09-01"], w.oil_actual
    EP = {"2008 oil spike and collapse": ("2008-01", "2009-03", "2007-12"), "2020 pandemic": ("2020-01", "2020-12", "2019-12"),
          "2022 energy shock": ("2021-10", "2023-03", "2021-09"), "2026 shock": ("2025-10", "2026-09", "2025-09")}
    et = BR.episode_table(w.cpie_m, oil, {k: v for k, v in EP.items()})
    K.save(et, "bridge_episodes.csv", index=False)
    print(et.round(1).to_string())
    # 2022 and 2026 in detail: cumulative error over the episode
    cum = []
    for lab, a, b in (("2022Q1-2022Q4", "2022Q1", "2022Q4"), ("2026Q1-2026Q3 (Q3 bridge out-of-sample)", "2026Q1", "2026Q3")):
        s = et[(et.quarter >= a) & (et.quarter <= b)]
        cum.append({"episode": lab, "actual CPI energy level change (%)": float(s["actual CPI energy (ann. %)"].sum() / 4),
                    "bridge out-of-sample level change (%)": float(s["bridge out-of-sample (ann. %)"].sum() / 4),
                    "cumulative level error (%)": float(s["error out-of-sample (pp)"].sum() / 4),
                    "x 0.075 weight = headline price level (%)": float(0.075 * s["error out-of-sample (pp)"].sum() / 4)})
    K.save(pd.DataFrame(cum), "bridge_episode_level_errors.csv", index=False)
    print(pd.DataFrame(cum).round(2))
    # stability
    rec = BR.recursive_elasticity(w.cpie_m, oil)
    roll = BR.recursive_elasticity(w.cpie_m, oil, first_end="2005-12", window=180)
    K.save(rec, "bridge_recursive_elasticity.csv", index=False)
    K.save(roll, "bridge_rolling15y_elasticity.csv", index=False)
    ch = BR.chow_sum(w.cpie_m, oil, ["2000-01", "2008-01", "2015-01", "2020-01"])
    K.save(ch, "bridge_break_tests.csv", index=False)
    print(ch.round(3))
    al = BR.asymmetry_and_level(w.cpie_m, oil)
    K.save(al, "bridge_asymmetry_nonlinearity.csv", index=False)
    print(al.round(3).to_string())
    ll = BR.lag_length(w.cpie_m, oil)
    K.save(ll, "bridge_lag_length.csv", index=False)
    print(ll.round(3))
    ec = BR.error_correction(w.cpie_m, oil)
    K.save(pd.Series(ec, name="value").to_frame(), "bridge_error_correction.csv")
    print(pd.Series(ec).round(3))
    ep = BR.error_persistence(w.cpie_m, oil)
    K.save(ep, "bridge_error_persistence.csv", index=False)
    print(ep.round(3).to_string())
    # ------- what would change the scenario conclusions?
    base_coef = w.bridge.coef.values.copy()
    lib = L.build(w)
    keys = ("oil_up30", "oil_dn30", "oil_flat", "oil_spike", "adverse_supply")
    rows = []
    for el in (0.20, 0.24, 0.297, 0.34, 0.40, 0.50):
        c = base_coef.copy()
        c[1:] = c[1:] * el / base_coef[1:].sum()
        for key in keys:
            scn = lib[key]
            rs = S.run(w, scn, bridge_coefs=c)
            rb = S.run(w, S.Scenario("b", "b", energy_scale=scn.energy_scale), bridge_coefs=c)
            v = A._views(rs.path["gcpi"], rb.path["gcpi"])
            rows.append({"elasticity": el, "scenario": key, "y/y dev 1y (pp)": float(v["yoy"][0, 4]), "y/y dev 2y (pp)": float(v["yoy"][0, 8]), "y/y dev 3y (pp)": float(v["yoy"][0, 12]),
                         "price level dev 3y (%)": float(v["level"][0, 12])})
    K.save(pd.DataFrame(rows), "bridge_scenario_vs_elasticity.csv", index=False)
    print(pd.DataFrame(rows).pivot(index="scenario", columns="elasticity", values="y/y dev 1y (pp)").round(2))
    # additive bridge errors do not change deviations (linear) but move the baseline: replay the realised out-of-sample error patterns on the baseline
    rb = S.run(w, S.Scenario("b", "b"))
    e22 = et[(et.quarter >= "2022Q1") & (et.quarter <= "2022Q4")]["error out-of-sample (pp)"].values
    e26 = et[(et.quarter >= "2026Q1") & (et.quarter <= "2026Q3")]["error out-of-sample (pp)"].values
    # expected reversal of the current level error: AR(4) on quarterly bridge errors (no constant), applied to the last four errors (2025Q4-2026Q3)
    r = BR.fit_bridge(w.cpie_m, oil)
    qe = r["e"].resample("QS").sum()
    last3 = et[(et.quarter >= "2025Q4") & (et.quarter <= "2026Q3")]["error in-sample (pp)"].values / 4.0                      # pp of quarterly change
    df = pd.DataFrame({"y": qe, **{f"l{i}": qe.shift(i) for i in range(1, 5)}}).dropna()
    X = df[[f"l{i}" for i in range(1, 5)]].values
    ar = np.linalg.lstsq(X, df["y"].values, rcond=None)[0]
    hist4 = list(last3)                                   # oldest -> newest
    fc = []
    for _ in range(8):
        nxt = float(sum(ar[i] * hist4[-1 - i] for i in range(4)))
        hist4.append(nxt); fc.append(nxt)
    rows = []
    patterns = {"2022 realised out-of-sample errors (2022Q1-Q4, ann. pp: %s)" % ", ".join(f"{x:+.0f}" for x in e22): e22,
                "2026 realised out-of-sample errors (2026Q1-Q3, ann. pp: %s)" % ", ".join(f"{x:+.0f}" for x in e26): e26,
                "+10 pp ann. CPI energy for four quarters": np.full(4, 10.0), "-10 pp ann. CPI energy for four quarters": np.full(4, -10.0),
                "expected reversal of the 2026Q3 level error (AR(4) of bridge errors; ann. pp: %s)" % ", ".join(f"{4 * x:+.1f}" for x in fc[:4]): 4.0 * np.array(fc[:8])}
    for lab, pat in patterns.items():
        add = np.zeros(13)
        add[1:1 + len(pat)] = pat
        scn = S.Scenario("e", "e", cpi_energy_dev_pct=tuple(np.cumsum(add) / 4.0))        # level deviation (%) of CPI energy = cumulated error
        rs = S.run(w, scn)
        v = A._views(rs.path["gcpi"], rb.path["gcpi"])
        rows.append({"bridge error pattern": lab, "y/y effect at 4q (pp)": float(v["yoy"][0, 4]), "y/y effect at 8q (pp)": float(v["yoy"][0, 8]),
                     "price level effect at 12q (%)": float(v["level"][0, 12])})
    K.save(pd.DataFrame(rows), "bridge_error_replay_on_baseline.csv", index=False)
    print(pd.DataFrame(rows).round(2).to_string())
    print("AR(4) coefficients", ar.round(3), "expected next 4 quarterly errors (ann. pp)", (4 * np.array(fc[:4])).round(1))


if __name__ == "__main__":
    main()
