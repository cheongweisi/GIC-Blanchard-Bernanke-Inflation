"""Phase 4b part 5: uncertainty. Coverage of the baseline fan at past origins, parameter-band construction (HAC-normal independent vs joint block bootstrap),
specification envelope for scenario deviations, and an accounting of the four sources. Writes outputs/phase4b/uncertainty_*.csv."""
import dataclasses
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.phase4b import common as K  # noqa: E402
from bb_inflation.phase4b import uncertainty as U  # noqa: E402
from bb_inflation.phase4b import wage as WG  # noqa: E402
from bb_inflation.scenarios import attribution as A  # noqa: E402
from bb_inflation.scenarios import engine as E  # noqa: E402
from bb_inflation.scenarios import library as L  # noqa: E402
from bb_inflation.scenarios import scenario as S  # noqa: E402
from bb_inflation.scenarios.backtest import origins  # noqa: E402

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
KEYS = ("oil_up30", "oil_flat", "vu_tight", "expect_up", "food_up", "adverse_supply")
H = {"1y": 4, "2y": 8, "3y": 12}


def dev(w, scn, cs, bridge_coefs):
    """Deviation (scenario - baseline of the same options) in y/y, price level, for coefficient set cs (n draws or 1) and a given bridge coefficient row."""
    bc = bridge_coefs
    ins, _, _, cu = S.make_inputs(w, scn, cs=cs, bridge_coefs=bc)
    base = S.Scenario("b", "b", energy_scale=scn.energy_scale, wage_constant=scn.wage_constant, intercept_correction=scn.intercept_correction)
    inb, _, _, cb = S.make_inputs(w, base, cs=cs, bridge_coefs=bc)
    ps, pb = E.simulate(cu, ins)["gcpi"], E.simulate(cb, inb)["gcpi"]
    return A._views(ps, pb)


def band(v, k, i):
    x = v[k][:, i]
    return float(np.quantile(x, 0.05)), float(np.quantile(x, 0.5)), float(np.quantile(x, 0.95))


def main():
    w = K.world()
    lib = L.build(w)
    # ------------------------------------------------------------------ (1) coverage of the baseline fan at past origins
    t = time.time()
    cov = U.fan_coverage(w, origins(w), n=300)
    print("fan coverage run", round(time.time() - t), "s")
    K.save(cov, "uncertainty_fan_coverage_records.csv", index=False)
    cs_ = U.coverage_summary(cov)
    K.save(cs_, "uncertainty_fan_coverage.csv", index=False)
    print(cs_.round(2).to_string())
    # ------------------------------------------------------------------ (2) parameter bands: HAC-normal, equations independent vs joint block bootstrap
    boot = U.joint_bootstrap_coefs(w, n=500)
    hacd = E.CoefSet(w.cs_draws.names, {k: v[:500] for k, v in w.cs_draws.values.items()})
    pt_bridge = w.bridge.point()
    rows = []
    for key in KEYS:
        scn = lib[key]
        v_pt = dev(w, scn, w.cs_point, pt_bridge)
        v_h = dev(w, scn, hacd, pt_bridge)
        v_b = dev(w, scn, boot, pt_bridge)
        for hz, i in H.items():
            lo_h, md_h, hi_h = band(v_h, "yoy", i)
            lo_b, md_b, hi_b = band(v_b, "yoy", i)
            rows.append({"scenario": key, "horizon": hz, "point (pp)": float(v_pt["yoy"][0, i]), "HAC-normal lo90": lo_h, "HAC-normal hi90": hi_h, "HAC width": hi_h - lo_h,
                         "block-bootstrap lo90": lo_b, "block-bootstrap hi90": hi_b, "bootstrap width": hi_b - lo_b, "width ratio (bootstrap / HAC)": (hi_b - lo_b) / (hi_h - lo_h),
                         "bootstrap median - point": md_b - float(v_pt["yoy"][0, i])})
    pb = pd.DataFrame(rows)
    K.save(pb, "uncertainty_parameter_bands_hac_vs_bootstrap.csv", index=False)
    print(pb.round(3).to_string())
    # ------------------------------------------------------------------ (3) specification envelope
    variants: dict[str, tuple] = {"headline (B*, elasticity 0.297, no overlay)": (w.cs_point, pt_bridge, 1.0)}
    mean_cu = float(w.data["diffcpicf"].loc["1990Q1":"2026Q2"].mean())
    for phi in (0.10, 0.25):
        variants[f"wage catch-up overlay phi = {phi}"] = (WG.overlay_coefs(w.cs_point, phi, mean_cu), pt_bridge, 1.0)
    base_coef = w.bridge.coef.values.copy()
    for el in (0.24, 0.34, 0.37, 0.47):
        c = base_coef.copy()
        c[1:] = c[1:] * el / base_coef[1:].sum()
        variants[f"bridge elasticity {el}"] = (w.cs_point, c.reshape(1, -1), 1.0)
    variants["price-equation energy pass-through x 0.8 (Phase 4 alternative)"] = (w.cs_point, pt_bridge, 0.8)
    for lab, cs in U.spec_variants(w).items():
        variants[lab] = (cs, pt_bridge, 1.0)
    rows = []
    for lab, (cs, bc, esc) in variants.items():
        for key in KEYS:
            scn = dataclasses.replace(lib[key], energy_scale=esc)
            v = dev(w, scn, cs, bc)
            r = {"variant": lab, "scenario": key}
            for hz, i in H.items():
                r[f"y/y dev {hz} (pp)"] = float(v["yoy"][0, i])
            r["price level dev 3y (%)"] = float(v["level"][0, 12])
            rows.append(r)
    ev = pd.DataFrame(rows)
    K.save(ev, "uncertainty_specification_envelope.csv", index=False)
    head = ev[ev.variant.str.startswith("headline")].set_index("scenario")
    summ = []
    for key in KEYS:
        s = ev[ev.scenario == key]
        for col in ("y/y dev 1y (pp)", "y/y dev 3y (pp)", "price level dev 3y (%)"):
            h = float(head.loc[key, col])
            band_row = pb[(pb.scenario == key) & (pb.horizon == ("1y" if "1y" in col else "3y"))] if "price" not in col else None
            summ.append({"scenario": key, "measure": col, "headline": h, "min across specifications": float(s[col].min()), "max across specifications": float(s[col].max()),
                         "envelope width": float(s[col].max() - s[col].min()),
                         "HAC 90% parameter band width": float(band_row["HAC width"].iloc[0]) if band_row is not None else np.nan})
    sm = pd.DataFrame(summ)
    K.save(sm, "uncertainty_specification_vs_parameter.csv", index=False)
    print(sm.round(2).to_string())
    # ------------------------------------------------------------------ (4) accounting of sources at the baseline horizons
    bt = pd.read_csv(K.OUT.parent / "phase4" / "backtest_summary_yoy.csv")
    bt = bt[bt["target period"] == "all targets"].pivot_table(index="horizon (quarters)", columns="tier", values="RMSE of y/y (pp)")
    fan = pd.read_csv(K.OUT.parent / "phase4" / "baseline_path.csv", index_col=0)
    fw = (fan["yoy_pct_q95"] - fan["yoy_pct_q5"]) / (2 * 1.645)
    acc = pd.DataFrame({"model fan s.d. (parameters + residuals + bridge noise, drivers fixed)": [float(fw.iloc[i]) for i in (4, 8, 12)],
                        "RMSE tier B (realised drivers, structural only)": [bt.loc[h, "B"] for h in (4, 8, 12)],
                        "RMSE tier C (adds bridge)": [bt.loc[h, "C"] for h in (4, 8, 12)],
                        "RMSE tier D (real-time: adds driver assumptions)": [bt.loc[h, "D"] for h in (4, 8, 12)],
                        "RMSE AR(4)": [bt.loc[h, "AR4"] for h in (4, 8, 12)]}, index=["1y", "2y", "3y"])
    acc["implied bridge (sqrt(C^2 - B^2))"] = np.sqrt(acc["RMSE tier C (adds bridge)"] ** 2 - acc["RMSE tier B (realised drivers, structural only)"] ** 2)
    acc["implied drivers (sqrt(D^2 - C^2))"] = np.sqrt(acc["RMSE tier D (real-time: adds driver assumptions)"] ** 2 - acc["RMSE tier C (adds bridge)"] ** 2)
    K.save(acc, "uncertainty_sources_accounting.csv")
    print(acc.round(2).T.to_string())


if __name__ == "__main__":
    main()
