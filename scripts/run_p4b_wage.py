"""Phase 4b part 1: wage-price feedback. Catch-up evidence (data vs specification) and a labelled calibration overlay compared with the baseline.
Writes outputs/phase4b/wage_*.csv. The estimated coefficients are never changed: the overlay lives in a copy of the CoefSet."""
import dataclasses
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.phase4b import common as K  # noqa: E402
from bb_inflation.phase4b import wage as WG  # noqa: E402
from bb_inflation.scenarios import attribution as A  # noqa: E402
from bb_inflation.scenarios import library as L  # noqa: E402
from bb_inflation.scenarios import scenario as S  # noqa: E402

PHIS = {"estimated (sum -0.002)": None, "phi = 0.10 (upper end of data)": 0.10, "phi = 0.25 (stress, judgemental)": 0.25}
KEYS = ("oil_up30", "oil_flat", "oil_spike", "oil_dn30", "expect_up", "vu_tight", "adverse_supply")
H = {"1y": 4, "2y": 8, "3y": 12}


def overlay_world(w, phi, mean_cu):
    if phi is None:
        return w
    return dataclasses.replace(w, cs_point=WG.overlay_coefs(w.cs_point, phi, mean_cu), cs_draws=WG.overlay_coefs(w.cs_draws, phi, mean_cu))


def wage_level_dev(rs, rb):
    d = rs.path["gw"] - rb.path["gw"]
    return np.cumsum(d[0, 4:]) / 4.0


def main():
    w = K.world()
    d = w.data
    # ---- (a) data evidence
    K.save(WG.catchup_table(d, "2026Q2"), "wage_catchup_evidence.csv", index=False)
    pc = pd.concat([WG.postcovid_test(d, "2026Q2", "2019Q4", "2021Q1"), WG.postcovid_test(d, "2026Q2", "2019Q4", "2023Q1"),
                    WG.postcovid_test(d, "2026Q2", "2023Q2", "2023Q3")])
    K.save(pc, "wage_postcovid_residual_test.csv", index=False)
    # ---- wage residual history: fitted vs actual, last years
    r = w.res["gw"]
    hist = pd.DataFrame({"gw actual": d["gw"], "fitted (B*)": r.fitted, "residual": r.resid, "catch-up term (diffcpicf)": d["diffcpicf"],
                         "cf1": d["cf1"], "gcpi (4q mean)": d["gcpi"].rolling(4).mean()}).loc["2019Q1":]
    K.save(hist, "wage_residual_history.csv")
    mean_cu = float(d["diffcpicf"].loc["1990Q1":"2026Q2"].mean())

    # ---- (b) structural size of the second-round channel in the estimated model
    cs = w.cs_point
    rows = []
    for nm, f in (("sum own wage lags", lambda: cs.block_sum("gw", "gw")[0]), ("sum cf1 lags (weight on expected inflation)", lambda: cs.block_sum("gw", "cf1")[0]),
                  ("sum catch-up lags", lambda: cs.block_sum("gw", "diffcpicf")[0]), ("sum V/U lags", lambda: cs.block_sum("gw", "vu")[0]),
                  ("price eq.: sum wage lags (gross)", lambda: cs.block_sum("gcpi", "gw")[0]),
                  ("cf1 eq.: sum gcpi lags", lambda: cs.block_sum("cf1", "gcpi")[0]), ("cf1 eq.: sum cf10 lags", lambda: cs.block_sum("cf1", "cf10")[0]),
                  ("cf10 eq.: sum gcpi lags", lambda: cs.block_sum("cf10", "gcpi")[0])):
        rows.append({"item": nm, "value": float(f())})
    K.save(pd.DataFrame(rows), "wage_channel_coefficients.csv", index=False)

    # ---- (c) overlay comparison
    lib = L.build(w)
    out, base_rows, paths = [], [], []
    for lab, phi in PHIS.items():
        w2 = overlay_world(w, phi, mean_cu)
        rbase = S.run(w2, S.Scenario("base", "b"))
        m = S.measures(w2, rbase)
        for k, i in H.items():
            base_rows.append({"calibration": lab, "horizon": k, "baseline y/y (%)": float(m["yoy_pct"].iloc[i]), "baseline wage growth (ann. %)": float(m["gw"].iloc[i])})
        for key in KEYS:
            scn = lib[key]
            rs, rb = S.run(w2, scn), A.baseline_run(w2, scn)
            v = A._views(rs.path["gcpi"], rb.path["gcpi"])
            wl = wage_level_dev(rs, rb)
            row = {"calibration": lab, "scenario": key}
            for k, i in H.items():
                row[f"y/y dev {k} (pp)"] = float(v["yoy"][0, i])
                row[f"price level dev {k} (%)"] = float(v["level"][0, i])
                row[f"wage level dev {k} (%)"] = float(wl[i])
            row["peak y/y dev (pp)"] = float(v["yoy"][0].max()) if abs(v["yoy"][0].max()) >= abs(v["yoy"][0].min()) else float(v["yoy"][0].min())
            out.append(row)
            for q, qq in enumerate(w.quarters):
                paths.append({"calibration": lab, "scenario": key, "quarter": str(qq), "y/y dev (pp)": float(v["yoy"][0, q]), "price level dev (%)": float(v["level"][0, q]),
                              "wage level dev (%)": float(wl[q])})
    K.save(pd.DataFrame(out), "wage_overlay_scenarios.csv", index=False)
    K.save(pd.DataFrame(base_rows), "wage_overlay_baseline.csv", index=False)
    K.save(pd.DataFrame(paths), "wage_overlay_paths.csv", index=False)
    # the 'catch-up' cumulative effect of a 1 pp (annualised) one-quarter price shock on the wage level
    shock = S.Scenario("p1", "price shock 4pp", price_shock=tuple(np.r_[0.0, 4.0, np.zeros(11)]))
    rows = []
    for lab, phi in PHIS.items():
        w2 = overlay_world(w, phi, mean_cu)
        rs, rb = S.run(w2, shock), A.baseline_run(w2, shock)
        v = A._views(rs.path["gcpi"], rb.path["gcpi"])
        wl = wage_level_dev(rs, rb)
        rows.append({"calibration": lab, "price level after shock (%)": float(v["level"][0, 1]), "wage level dev 1y (%)": float(wl[5]), "wage level dev 3y (%)": float(wl[12]),
                     "price level dev 3y (%)": float(v["level"][0, 12]), "real wage dev 3y (%)": float(wl[12] - v["level"][0, 12])})
    K.save(pd.DataFrame(rows), "wage_oneoff_price_shock_real_wage.csv", index=False)
    print(pd.DataFrame(out).round(3).to_string())
    print(pd.DataFrame(base_rows).round(3).to_string())
    print(pd.DataFrame(rows).round(3).to_string())
    print(pd.read_csv(K.OUT / "wage_channel_coefficients.csv"))


if __name__ == "__main__":
    main()
