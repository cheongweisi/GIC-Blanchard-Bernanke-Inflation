"""Phase 4: scenario framework. Data QA, oil bridge, baseline and sensitivities, scenario library with bands, attribution tables.
Writes outputs/phase4/*.csv (Phase 1-3 outputs are never touched). Figures: scripts/run_p4_figures.py (reads the CSVs)."""
import dataclasses
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.scenarios import attribution as A  # noqa: E402
from bb_inflation.scenarios import library as L  # noqa: E402
from bb_inflation.scenarios import oil as O  # noqa: E402
from bb_inflation.scenarios import scenario as S  # noqa: E402
from bb_inflation.scenarios import uncertainty as U  # noqa: E402
from bb_inflation.scenarios import world as W  # noqa: E402
from bb_inflation.scenarios.pin import PHASE4_PULL  # noqa: E402

OUT = OUTPUTS / "phase4"
OUT.mkdir(parents=True, exist_ok=True)
H_IDX = {"1y": 4, "2y": 8, "3y": 12}


def save(df: pd.DataFrame, name: str, index: bool = True) -> None:
    df.to_csv(OUT / name, index=index)


# ---------------------------------------------------------------------------------------------------- data and bridge
def data_tables(w: W.World) -> None:
    save(W.qa_vs_pinned(w), "data_qa_vs_pinned_pull.csv", index=False)
    q3 = pd.Series(w.q3, name="2026Q3 published value")
    save(q3.to_frame(), "data_2026Q3_partial_quarter.csv")
    b = w.bridge
    tab = pd.DataFrame({"coefficient": b.coef, "HAC s.e.": np.sqrt(np.diag(b.cov))})
    tab.loc["sum of lags (long-run elasticity)"] = [b.elasticity, b.elasticity_se()]
    tab.loc["R2 (monthly)"] = [b.r2, np.nan]
    tab.loc["residual s.d. (monthly, pp)"] = [b.resid_sd, np.nan]
    tab.loc["observations"] = [b.nobs, np.nan]
    save(tab, "bridge_coefficients.csv")
    # out-of-sample behaviour of the bridge: estimated to 2025-12 (and the primary bridge to 2026-06), predicting 2026 quarters
    rows = []
    for end, label in (("2025-12", "estimated to 2025-12"), ("2026-06", "primary (estimated to 2026-06)")):
        br = O.estimate_bridge(w.cpie_m.loc[:f"{end}-01"], w.oil_actual.loc[:f"{end}-01"], end=end)
        pred = O.monthly_energy_growth(br.point(), w.oil_actual, "2026-01", "2026-09")[0]
        act = (100 * np.log(w.cpie_m).diff()).loc["2026-01":"2026-09"].values
        qa, qp = 4 * act.reshape(3, 3).sum(axis=1), 4 * pred.reshape(3, 3).sum(axis=1)
        for i, q in enumerate(("2026Q1", "2026Q2", "2026Q3")):
            rows.append({"bridge": label, "quarter": q, "actual CPI energy growth (ann. %)": qa[i], "bridge (ann. %)": qp[i],
                         "error (pp)": qa[i] - qp[i], "in estimation sample": q <= "2026Q2" and end == "2026-06"})
    save(pd.DataFrame(rows), "bridge_out_of_sample_2026.csv", index=False)
    # sub-sample stability of the elasticity
    sub = []
    for lo, hi in (("1990-02", "2007-12"), ("2008-01", "2026-06"), ("2000-01", "2026-06"), ("1990-02", "2019-12")):
        br = O.estimate_bridge(w.cpie_m.loc[:f"{hi}-01"], w.oil_actual.loc[:f"{hi}-01"], end=hi, start=lo)
        sub.append({"sample": f"{lo} to {hi}", "elasticity": br.elasticity, "s.e.": br.elasticity_se(), "R2": br.r2, "constant (%/month)": br.coef["const"],
                    "n": br.nobs})
    save(pd.DataFrame(sub), "bridge_subsamples.csv", index=False)


def anchors(w: W.World) -> pd.DataFrame:
    wb = w.oil_actual
    q = wb.resample("QE").mean()
    a4 = 100 * np.log(q).diff(4)
    rows = [{"item": "Brent, 4-quarter log change, s.d. 1990-2026Q2 (%)", "value": float(a4.loc["1990":"2026-06"].std())},
            {"item": "Brent, 4-quarter log change, s.d. 2010-2026Q2 (%)", "value": float(a4.loc["2010":"2026-06"].std())},
            {"item": "Brent, largest 4-quarter rise since 1990 (%)", "value": float(a4.loc["1990":].max())},
            {"item": "Brent, latest month, Sep 2026 (USD)", "value": float(wb.iloc[-1])},
            {"item": "Brent, 2026Q2 quarterly average (USD)", "value": float(q.loc["2026-06-30"])},
            {"item": "Brent, pre-spike 2025Q4 average (USD)", "value": float(q.loc["2025-12-31"])},
            {"item": "Brent futures, Dec 2026 / Dec 2027 / Dec 2028 / Dec 2029 (USD)",
             "value": " / ".join(f"{float(w.oil_curve['futures'].loc[d]):.1f}" for d in ("2026-12-01", "2027-12-01", "2028-12-01", "2029-12-01"))},
            {"item": "V/U 2019Q4 / 2026Q2 (baseline held at the latter)", "value": f"{float(w.data.at['2019Q4', 'vu']):.2f} / {float(w.data.at['2026Q2', 'vu']):.2f}"},
            {"item": "GSCPI, s.d. of quarterly level since 1998Q1", "value": float(w.data['shortage'].loc['1998Q1':].std())},
            {"item": "futures date", "value": w.fut_date}]
    return pd.DataFrame(rows)


def assumptions_table(w: W.World) -> pd.DataFrame:
    """Baseline driver assumptions by quarter (levels)."""
    base = S.Scenario("base", "base")
    r = S.run(w, base)
    m = S.measures(w, r)
    out = pd.DataFrame({"oil, Brent (USD, quarter avg)": m["oil_usd_qavg"], "oil, Brent (USD, quarter end month)": m["oil_usd_qend"],
                        "CPI energy, nominal growth (ann. %)": m["gE_nominal"], "CPI food, nominal growth (ann. %)": m["gF_nominal"],
                        "V/U": w.base_exog["vu"][W.LAGS:], "productivity growth, 8q average": w.base_exog["magpty"][W.LAGS:],
                        "GSCPI": w.base_shortage[W.LAGS:], "status": ["published (nowcast quarter)" if (w.nowcast and i == 0) else "assumption"
                                                                     for i in range(W.H_SIM)]}, index=w.quarters)
    out.loc[out.index[0], "V/U"] = np.nan if False else out.loc[out.index[0], "V/U"]
    return out


# ---------------------------------------------------------------------------------------------------- baseline
def baseline_tables(w: W.World, ws: W.World) -> dict:
    base = S.Scenario("base", "baseline")
    r = S.run(w, base)
    m = S.measures(w, r)
    fan = U.baseline_fan(w)
    full = m.join(fan[["q5", "q16", "q50", "q84", "q95"]].rename(columns=lambda c: f"yoy_pct_{c}"))
    full["status"] = ["published CPI inflation imposed" if (w.nowcast and i == 0) else "forecast" for i in range(len(full))]
    full["kind"] = "real-time baseline projection: model forecast CONDITIONAL on assumed drivers (not realised regressors, not a scenario)"
    save(full, "baseline_path.csv")
    h = w.data.loc["2022Q1":w.ctx.last, ["gcpi", "gw", "cf1", "cf10", "vu"]].copy()
    h["gE_nominal"] = (w.data["grpe"] + w.data["gw"]).loc["2022Q1":w.ctx.last]
    h["yoy_pct"] = 100 * (np.exp(w.data["gcpi"].rolling(4).mean() / 100) - 1).loc["2022Q1":w.ctx.last]
    save(h, "history_context.csv")
    save(A.baseline_blocks(w), "baseline_nominal_blocks.csv")
    save(A.baseline_driver_contributions(w, vu_ref=float(w.data.at["2019Q4", "vu"])), "baseline_driver_contributions.csv")
    # relation of the nominal weights
    wts = {k: float(v[0]) for k, v in w.cs_point.effective_nominal_weights().items()}
    wts["sum"] = sum(wts.values())
    save(pd.Series(wts, name="weight").to_frame(), "price_equation_nominal_weights.csv")

    # sensitivities of the baseline
    variants = {
        "Headline baseline": (w, base, "futures"),
        "Strict origin 2026Q2 (2026Q3 forecast, not nowcast)": (ws, base, "futures"),
        "Neutral wage constant (authors' correction at V/U = 1.02)": (w, dataclasses.replace(base, wage_constant="neutral"), "futures"),
        "Oil: EIA STEO path": (w, base, "steo"),
        "Oil: flat at October 2026 level": (w, base, "flat_oct"),
        "Energy pass-through x 0.8 (alternative assumption)": (w, dataclasses.replace(base, energy_scale=L.HAIRCUT), "futures"),
        "Intercept correction -0.3 pp for 4 quarters (price eq.)": (w, dataclasses.replace(base, intercept_correction=-0.3), "futures"),
    }
    rows, paths = [], {}
    for name, (ww, sc, ob) in variants.items():
        rr = S.run(ww, sc, oil_baseline=ob)
        mm = S.measures(ww, rr)
        rows.append({"variant": name, **S.horizon_summary(mm, ww.nowcast)})
        paths[name] = mm["yoy_pct"]
    save(pd.DataFrame(rows), "baseline_sensitivities.csv", index=False)
    save(pd.DataFrame(paths), "baseline_sensitivities_yoy_paths.csv")
    return {"m": m, "fan": fan}


# ---------------------------------------------------------------------------------------------------- scenarios
def scenario_outputs(w: W.World, lib: dict) -> None:
    base = S.Scenario("base", "baseline")
    rb_head = S.run(w, base)
    mb_head = S.measures(w, rb_head)
    summ, longrows, drv_rows, lay_rows, prox_rows, chain_rows, assum_rows = [], [], [], [], [], [], []
    gaps = []
    variants = [(k, lib[k], "baseline model") for k in lib] + \
               [(f"{k}__x0.8", dataclasses.replace(lib[k], energy_scale=L.HAIRCUT, key=f"{k}__x0.8",
                                                    label=lib[k].label + " [energy pass-through x0.8]"), "pass-through x0.8") for k in L.HAIRCUT_SET]
    for key, scn, variant in variants:
        rs = S.run(w, scn)
        ms = S.measures(w, rs)
        rb = A.baseline_run(w, scn)
        mb = S.measures(w, rb)
        bands = U.deviation_bands(w, scn)
        dv_yoy = bands["yoy"]
        dv_ann = bands["annualised"]
        dv_lvl = bands["level"]
        drv, gap1 = A.by_driver(w, scn)
        lay, gap2 = A.by_layer(w, scn)
        gaps.append((key, gap1, gap2))
        prox = A.proximate_blocks(w, scn)
        # summary
        yoy_dev_series = dv_yoy["point"].iloc[1:]
        peak_q = yoy_dev_series.abs().idxmax()
        row = {"scenario": key, "label": scn.label, "category": scn.category, "variant": variant,
               "kind": "forward-looking scenario: deviation from the real-time baseline (alternative assumption)" if variant != "baseline model" else
               "forward-looking scenario: deviation from the real-time baseline",
               "drivers": "; ".join(scn.active_drivers()),
               "peak y/y deviation (pp)": float(yoy_dev_series.loc[peak_q]), "quarter of peak": str(peak_q)}
        for lab, k in H_IDX.items():
            q = w.quarters[k]
            row[f"y/y dev. {lab} (pp)"] = float(dv_yoy["point"].iloc[k])
            row[f"y/y dev. {lab} lo90"] = float(dv_yoy["lo90"].iloc[k])
            row[f"y/y dev. {lab} hi90"] = float(dv_yoy["hi90"].iloc[k])
            row[f"price level dev. {lab} (%)"] = float(dv_lvl["point"].iloc[k])
            row[f"price level dev. {lab} lo90"] = float(dv_lvl["lo90"].iloc[k])
            row[f"price level dev. {lab} hi90"] = float(dv_lvl["hi90"].iloc[k])
            row[f"scenario y/y level {lab} (%)"] = float(ms["yoy_pct"].iloc[k])
            row[f"baseline y/y level {lab} (%)"] = float(mb["yoy_pct"].iloc[k])
            row[f"y/y level vs headline baseline {lab} (pp)"] = float(ms["yoy_pct"].iloc[k] - mb_head["yoy_pct"].iloc[k])
            row[f"CPI energy dev. {lab} (%)"] = float(100 * (ms["cpi_energy_level"].iloc[k] / mb["cpi_energy_level"].iloc[k] - 1))
            row[f"relative energy price dev. {lab} (%)"] = float(100 * (ms["rel_energy_level"].iloc[k] / mb["rel_energy_level"].iloc[k] - 1))
            row[f"wage level dev. {lab} (%)"] = float(100 * (ms["eci_level"].iloc[k] / mb["eci_level"].iloc[k] - 1))
        for lab, (a, b) in (("year 1", (1, 5)), ("year 2", (5, 9)), ("year 3", (9, 13))):
            row[f"avg annualised inflation dev. {lab} (pp)"] = float(dv_ann["point"].iloc[a:b].mean())
        row["driver attribution gap (pp)"] = gap1
        row["layer attribution gap (pp)"] = gap2
        summ.append(row)
        for i, q in enumerate(w.quarters):
            rec = {"scenario": key, "variant": variant, "kind": "forward-looking scenario", "quarter": str(q), "h": i}
            for c in ("gcpi_ann", "yoy_pct", "cpi_level", "gw", "cf1", "cf10", "grpe", "grpf", "gE_nominal", "oil_usd_qavg",
                      "cpi_energy_level", "rel_energy_level", "eci_level"):
                rec[c] = float(ms[c].iloc[i])
                rec[f"{c}_baseline"] = float(mb[c].iloc[i])
            for k2, bb in (("annualised", dv_ann), ("yoy", dv_yoy), ("level", dv_lvl)):
                rec[f"dev_{k2}"] = float(bb["point"].iloc[i])
                rec[f"dev_{k2}_lo90"] = float(bb["lo90"].iloc[i])
                rec[f"dev_{k2}_hi90"] = float(bb["hi90"].iloc[i])
            longrows.append(rec)
        for r_ in drv.to_dict("records"):
            drv_rows.append({"scenario": key, "variant": variant, **r_})
        for r_ in lay.to_dict("records"):
            lay_rows.append({"scenario": key, "variant": variant, **r_})
        for q, r_ in prox.iterrows():
            prox_rows.append({"scenario": key, "variant": variant, "quarter": str(q), **r_.to_dict()})
        if "Oil / energy" in scn.active_drivers():
            ch = A.energy_chain(w, scn)
            ch.insert(0, "scenario", key)
            ch.insert(1, "variant", variant)
            chain_rows.append(ch.reset_index().rename(columns={"index": "quarter"}).assign(quarter=lambda d: d["quarter"].astype(str)))
        # what the scenario assumes (levels of the inputs)
        for i, q in enumerate(w.quarters):
            assum_rows.append({"scenario": key, "variant": variant, "quarter": str(q), "oil_usd_qavg": float(ms["oil_usd_qavg"].iloc[i]),
                               "oil_usd_baseline": float(mb["oil_usd_qavg"].iloc[i]), "vu": float(rs.inputs.exog["vu"][W.LAGS + i]),
                               "vu_baseline": float(w.base_exog["vu"][W.LAGS + i]),
                               "gscpi": float(rs.inputs.exog["shortagema2"][W.LAGS + i]),
                               "cpi_food_level_vs_baseline_pct": float(100 * (ms["cpi_food_level"].iloc[i] / mb["cpi_food_level"].iloc[i] - 1)),
                               "productivity_growth_ma8": float(rs.inputs.exog["magpty"][W.LAGS + i]),
                               "cf1_shock": float(rs.inputs.add.get("cf1", np.zeros(w.T))[W.LAGS + i]) if "cf1" in rs.inputs.add else 0.0})
    save(pd.DataFrame(summ), "scenario_summary.csv", index=False)
    save(pd.DataFrame(longrows), "scenario_paths_long.csv", index=False)
    save(pd.DataFrame(drv_rows), "attribution_by_driver.csv", index=False)
    save(pd.DataFrame(lay_rows), "attribution_by_layer.csv", index=False)
    save(pd.DataFrame(prox_rows), "attribution_proximate_nominal_blocks.csv", index=False)
    save(pd.concat(chain_rows), "energy_transmission_chain.csv", index=False)
    save(pd.DataFrame(assum_rows), "scenario_assumptions_by_quarter.csv", index=False)
    save(pd.DataFrame(gaps, columns=["scenario", "driver additivity gap (pp)", "layer additivity gap (pp)"]), "attribution_checks.csv", index=False)


def oil_passthrough_sensitivity(w: W.World, lib: dict) -> pd.DataFrame:
    """Oil scenarios under alternative pass-through assumptions: structural energy coefficients x0.8; oil bridge fitted 2008-2026 (higher
    elasticity) or 1990-2007 (lower); bridge elasticity +/- 1 s.e. The x0.8 case is an alternative assumption, not a statistically preferred one."""
    b = w.bridge
    alt = {}
    for lab, (lo, hi) in {"bridge fitted 2008-2026": ("2008-01", "2026-06"), "bridge fitted 1990-2007": ("1990-02", "2007-12")}.items():
        alt[lab] = O.estimate_bridge(w.cpie_m.loc[:f"{hi}-01"], w.oil_actual.loc[:f"{hi}-01"], end=hi, start=lo)
    cases = {"headline (bridge 1990-2026, structural coefficients as estimated)": (1.0, b.point()),
             "structural energy coefficients x0.8 (alternative assumption)": (L.HAIRCUT, b.point())}
    for lab, br in alt.items():
        cases[f"{lab}: elasticity {br.elasticity:.2f}"] = (1.0, br.point())
    for sgn, lab in ((1, "+1 s.e."), (-1, "-1 s.e.")):
        c = b.coef.values.copy()
        c[1:] *= (b.elasticity + sgn * b.elasticity_se()) / b.elasticity
        cases[f"bridge elasticity {lab} ({b.elasticity + sgn * b.elasticity_se():.2f})"] = (1.0, c[None, :])
    rows = []
    for key in ("oil_up30", "oil_dn30", "oil_flat", "oil_spike"):
        for lab, (scale, bc) in cases.items():
            sc = dataclasses.replace(lib[key], energy_scale=scale)
            rs = S.run(w, sc, bridge_coefs=bc)
            rb = S.run(w, dataclasses.replace(S.Scenario("b", "b"), energy_scale=scale), bridge_coefs=bc)
            v = A._views(rs.path["gcpi"], rb.path["gcpi"])
            r = {"scenario": key, "label": lib[key].label, "pass-through assumption": lab}
            for hk, i in H_IDX.items():
                r[f"y/y dev. {hk} (pp)"] = float(v["yoy"][0, i])
                r[f"price level dev. {hk} (%)"] = float(v["level"][0, i])
            rows.append(r)
    return pd.DataFrame(rows)


def cumulative_blocks(w: W.World, lib: dict) -> pd.DataFrame:
    """Price-level deviation (%) by nominal block, cumulated (annualised contribution / 4) to the 1-, 2- and 3-year marks."""
    rows = []
    for key, scn in lib.items():
        pb = A.proximate_blocks(w, scn).drop(columns="total")
        for hk, i in H_IDX.items():
            cum = pb.iloc[:i + 1].sum() / 4.0
            rows.append({"scenario": key, "horizon": hk, **cum.to_dict(), "total price level dev. (%)": float(cum.sum())})
    return pd.DataFrame(rows)


def rules_of_thumb(w: W.World) -> pd.DataFrame:
    """Per-unit responses (persistent step from 2026Q4) used in the report; linear in the shock, so they scale."""
    unit = {"Brent +10% (persistent)": S.scenario("u1", "u1", oil_dev_pct=L.step(10.0)),
            "Nominal CPI food +5% (persistent)": S.scenario("u2", "u2", food_dev_pct=L.ramp(5.0, 4)),
            "V/U +0.1 (persistent)": S.scenario("u3", "u3", vu_dev=L.ramp(0.1, 4)),
            "GSCPI +1 (rho 0.8)": S.scenario("u4", "u4", gscpi_dev=L.decay(1.0, 0.8)),
            "Productivity growth -1 pp for 8 quarters": S.scenario("u5", "u5", prod_growth_dev=np.r_[0.0, -np.ones(8), np.zeros(W.H_SIM - 9)]),
            "1y expectations +0.5 pp for 4 quarters": S.scenario("u6", "u6", cf1_shock=L.pulse(0.5, 1, 4, 0))}
    rows = []
    for lab, sc in unit.items():
        for hv, sc2 in (("baseline model", sc), ("pass-through x0.8", dataclasses.replace(sc, energy_scale=L.HAIRCUT))):
            if hv != "baseline model" and "Oil / energy" not in sc.active_drivers():
                continue
            v = A.total_effect(w, sc2)
            r = {"shock": lab, "variant": hv}
            for k, i in H_IDX.items():
                r[f"y/y dev. {k} (pp)"] = float(v["yoy"][0, i])
                r[f"price level dev. {k} (%)"] = float(v["level"][0, i])
            r["peak y/y dev. (pp)"] = float(np.abs(v["yoy"][0, 1:]).max() * np.sign(v["yoy"][0, 1:][np.abs(v["yoy"][0, 1:]).argmax()]))
            rows.append(r)
    return pd.DataFrame(rows)


def main() -> None:
    w = S.finalise(W.build(nowcast=True))
    ws = S.finalise(W.build(nowcast=False, n_draws=50))
    data_tables(w)
    save(anchors(w), "anchors.csv", index=False)
    save(assumptions_table(w), "baseline_assumptions.csv")
    bt = baseline_tables(w, ws)
    lib = L.build(w)
    pd.DataFrame([{"key": k, "label": s.label, "category": s.category, "drivers": "; ".join(s.active_drivers()), "description": s.description}
                  for k, s in lib.items()]).to_csv(OUT / "scenario_library.csv", index=False)
    scenario_outputs(w, lib)
    save(rules_of_thumb(w), "rules_of_thumb.csv", index=False)
    save(oil_passthrough_sensitivity(w, lib), "oil_passthrough_sensitivity.csv", index=False)
    save(cumulative_blocks(w, lib), "attribution_cumulative_price_level_blocks.csv", index=False)
    pd.Series({"phase4_pull": PHASE4_PULL, "futures_date": w.fut_date, "model": "B* (unweighted, gscpi_ma2, V/U 2025Q4 bridged), 1990Q1-2026Q2",
               "draws": w.cs_draws.n, "information_set": "nowcast (2026Q3 CPI, expectations, energy, food, GSCPI published)"}).to_csv(
        OUT / "run_provenance.csv", header=["value"])
    print("done")
    print(bt["m"][["gcpi_ann", "yoy_pct"]].round(2).T.to_string())
    print(bt["fan"].round(2).iloc[[1, 4, 8, 12]].to_string())


if __name__ == "__main__":
    main()
