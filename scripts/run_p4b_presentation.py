"""Phase 4b: the four presentation corrections, as new tables (Phase 4 outputs are hash-locked and are not edited).
  p5_baseline_bands.csv   baseline y/y with (i) the conditional model band relabelled, (ii) the empirical real-time band, (iii) the neutral-wage-constant lower bound
  p5_scenario_table.csv   scenario deviations with the 90% parameter band AND the specification range (bridge elasticity 0.24-0.40 x wage catch-up 0 / 0.10 / 0.25);
                          the 0.8 pass-through overlay is a separate, labelled column
  p5_labels.csv           the wording to use next to each number in any report or dashboard
Decisions of 2026-10-18: headline bridge elasticity stays 0.297 (range 0.24-0.40), catch-up toggle 0 / 0.10 / 0.25 is a labelled sensitivity, baseline driver rules unchanged."""
import dataclasses
import itertools
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
from bb_inflation.scenarios import engine as E  # noqa: E402
from bb_inflation.scenarios import library as L  # noqa: E402
from bb_inflation.scenarios import scenario as S  # noqa: E402

H = {"1y": 4, "2y": 8, "3y": 12}
ELAST = (0.24, 0.297, 0.40)
PHIS = (0.0, 0.10, 0.25)


def dev(w, scn, cs, bc):
    ins, _, _, cu = S.make_inputs(w, scn, cs=cs, bridge_coefs=bc)
    base = S.Scenario("b", "b", energy_scale=scn.energy_scale, wage_constant=scn.wage_constant, intercept_correction=scn.intercept_correction)
    inb, _, _, cb = S.make_inputs(w, base, cs=cs, bridge_coefs=bc)
    return A._views(E.simulate(cu, ins)["gcpi"], E.simulate(cb, inb)["gcpi"])


def main():
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    w = K.world()
    lib = L.build(w)
    mean_cu = float(w.data["diffcpicf"].loc["1990Q1":"2026Q2"].mean())
    base_coef = w.bridge.coef.values.copy()

    def bridge(el):
        c = base_coef.copy()
        c[1:] = c[1:] * el / base_coef[1:].sum()
        return c.reshape(1, -1)

    # ---------------------------------------------------------------- scenario table
    p4 = pd.read_csv(K.OUT.parent / "phase4" / "scenario_summary.csv")
    p4 = p4[p4.variant == "baseline model"].set_index("scenario")
    rows = []
    for key, scn in lib.items():
        grid = {}
        for el, phi in itertools.product(ELAST, PHIS):
            cs = w.cs_point if phi == 0 else WG.overlay_coefs(w.cs_point, phi, mean_cu)
            grid[(el, phi)] = dev(w, scn, cs, bridge(el))
        hc = dev(w, dataclasses.replace(scn, energy_scale=0.8), w.cs_point, w.bridge.point())
        for hz, i in H.items():
            vals = [g["yoy"][0, i] for g in grid.values()]
            lv = [g["level"][0, i] for g in grid.values()]
            head = grid[(0.297, 0.0)]
            rows.append({"scenario": key, "label": scn.label, "horizon": hz, "headline y/y deviation (pp)": float(head["yoy"][0, i]),
                         "90% parameter band lo": float(p4.loc[key, f"y/y dev. {hz} lo90"]) if f"y/y dev. {hz} lo90" in p4.columns else np.nan,
                         "90% parameter band hi": float(p4.loc[key, f"y/y dev. {hz} hi90"]) if f"y/y dev. {hz} hi90" in p4.columns else np.nan,
                         "specification range lo (pp)": float(min(vals)), "specification range hi (pp)": float(max(vals)),
                         "at elasticity 0.24": float(grid[(0.24, 0.0)]["yoy"][0, i]), "at elasticity 0.40": float(grid[(0.40, 0.0)]["yoy"][0, i]),
                         "with catch-up 0.10": float(grid[(0.297, 0.10)]["yoy"][0, i]), "with catch-up 0.25": float(grid[(0.297, 0.25)]["yoy"][0, i]),
                         "alternative: pass-through x0.8 (labelled, not preferred)": float(hc["yoy"][0, i]),
                         "headline price level deviation (%)": float(head["level"][0, i]), "price level range lo (%)": float(min(lv)), "price level range hi (%)": float(max(lv)),
                         "specification range / parameter band width": float((max(vals) - min(vals)) / max(float(p4.loc[key, f"y/y dev. {hz} hi90"] - p4.loc[key, f"y/y dev. {hz} lo90"]), 1e-9))})
    sc = pd.DataFrame(rows)
    K.save(sc, "p5_scenario_table.csv", index=False)
    print(sc[sc.horizon == "1y"][["scenario", "headline y/y deviation (pp)", "90% parameter band lo", "90% parameter band hi", "specification range lo (pp)",
                                  "specification range hi (pp)", "specification range / parameter band width"]].round(2).to_string())

    # ---------------------------------------------------------------- baseline bands
    bp = pd.read_csv(K.OUT.parent / "phase4" / "baseline_path.csv", index_col=0)
    sens = pd.read_csv(K.OUT.parent / "phase4" / "baseline_sensitivities_yoy_paths.csv", index_col=0)
    comp = pd.read_csv(K.OUT / "forecast_error_components.csv")
    y = comp[comp.measure.str.startswith("y/y")]
    tg = pd.PeriodIndex(y.target, freq="Q")
    excl = ~((tg >= pd.Period("2020Q1", "Q")) & (tg <= pd.Period("2023Q2", "Q")))
    out = pd.DataFrame(index=bp.index)
    out["baseline y/y (%)"] = bp["yoy_pct"]
    out["conditional model band lo (5%)"] = bp["yoy_pct_q5"]
    out["conditional model band hi (95%)"] = bp["yoy_pct_q95"]
    for lab, mask in (("all targets", np.ones(len(y), bool)), ("excl. 2020-23", excl)):
        lo, hi = [], []
        for k, q in enumerate(out.index):
            h = min(k + 1, 12)
            e = y[mask & (y.h == h)]["error D"].values
            lo.append(float(out["baseline y/y (%)"].iloc[k] - np.quantile(e, 0.95)))
            hi.append(float(out["baseline y/y (%)"].iloc[k] - np.quantile(e, 0.05)))
        out[f"empirical real-time band lo ({lab}, 5%)"] = lo
        out[f"empirical real-time band hi ({lab}, 95%)"] = hi
    out.iloc[0, 3:] = np.nan                                    # 2026Q3 is published: no band
    out.iloc[0, 1:3] = np.nan
    out["lower bound: neutral wage constant (V/U 1.02 treated as neutral)"] = sens["Neutral wage constant (authors' correction at V/U = 1.02)"]
    K.save(out, "p5_baseline_bands.csv")
    print(out.round(2).to_string())

    labels = pd.DataFrame([
        ("baseline y/y", "Model projection conditional on assumed drivers (futures oil curve, V/U held at 1.02, GSCPI AR(1), food with wages). Not a forecast with demonstrated skill: real-time-feasible forecasts of this kind have not beaten AR(4) since 2023."),
        ("conditional model band", "Model band given the assumed drivers (parameters, equation residuals, bridge noise). It is NOT a forecast interval: at past origins the nominal 90% band contained 61-73% of outturns (29-43% in 2020-23)."),
        ("empirical real-time band", "Baseline minus the 5th and 95th percentiles of past real-time errors (tier D, 86 origins, same horizon). Includes driver surprises; wide because 2008-09 and 2020-23 are in the sample."),
        ("scenario deviation", "The model's response to a stated assumption, as a deviation from the baseline. The deviations are the product; the baseline level is not."),
        ("90% parameter band", "Parameter uncertainty only, conditional on the model being right. Excludes driver, specification and out-of-sample error."),
        ("specification range", "Range of the headline deviation across bridge elasticity 0.24-0.40 and wage catch-up 0 / 0.10 / 0.25. Catch-up 0.10 and 0.25 are calibrated overlays, not estimates (estimate: -0.002; upper 95% bound about +0.1); 0.25 is a stress."),
        ("pass-through x0.8", "Labelled alternative assumption (Phase 3 supplement asymmetry estimate, not significant out of sample). Evidence from realised oil responses and the bridge points the other way (1.4-1.5 times the model; elasticity 0.37 at today's oil price)."),
        ("wage constant", "The estimated wage constant is inflation-neutral only at V/U 0.59 (the 1990-2019 mean). The baseline therefore treats V/U 1.02 as a tight labour market and drifts up about 0.1 pp a year; the neutral-constant path is the lower bound (2.63% in 2029Q3 against 3.13%)."),
        ("horizon", "Read 1-3 years; the model has no inflation anchor."),
    ], columns=["item", "wording to use next to the number"])
    K.save(labels, "p5_labels.csv", index=False)


if __name__ == "__main__":
    main()
