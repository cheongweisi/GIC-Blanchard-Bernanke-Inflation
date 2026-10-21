"""Evaluation stage of the Phase 5 pipeline: runs exercises A and B through the standalone engine, benchmarks, variants, decomposition,
tables and charts. Writes to phase5/output/."""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from . import charts as CH
from . import data as D
from . import estimate as E
from . import evaluate as EV
from .pipeline import COEF, ORIGIN, P5, stage_workbook

sys.path.insert(0, str(P5))
import p5_forecast_engine as eng  # noqa: E402

HORIZON = "2026Q2"
MA, MB = "A: pseudo-real-time", "B: conditional (realised drivers)"


def _idx(df: pd.DataFrame, name: str = "quarter") -> pd.DataFrame:
    out = df.copy()
    out.index = out.index.astype(str)
    out.index.name = name
    return out.reset_index()


def run(workbook=None) -> dict:
    OUT = P5 / "output"
    CHD = OUT / "charts"
    CHD.mkdir(parents=True, exist_ok=True)
    workbook = workbook or (P5 / "Phase5_Assumptions.xlsx")
    p = D.load()
    data = p.model
    wd = eng.read_workbook(workbook)
    coefs = eng.read_coefficients(COEF / "Bstar_coefficients_2023Q2.csv")
    q = pd.period_range("2023Q3", HORIZON, freq="Q")
    real = EV.realised_paths(p.levels, q)
    g_hist = data["gcpi"].loc[:ORIGIN]
    in_a, in_b = wd.inputs["A"].loc[q[0]:q[-1]], wd.inputs["B"].loc[q[0]:q[-1]]

    A = eng.run_scenario(wd, "A", coefs=coefs, horizon=HORIZON)
    B = eng.run_scenario(wd, "B", coefs=coefs, horizon=HORIZON)
    aux_j = json.loads((COEF / "auxiliary_models_2023Q2.json").read_text())
    ar1, ar4 = E.ar_forecast(g_hist, aux_j["ar1"], q), E.ar_forecast(g_hist, aux_j["ar4"], q)
    main = {MA: A.forecast["gcpi"], MB: B.forecast["gcpi"], "AR(4)": ar4, "AR(1)": ar1}

    # ---- variants and sensitivities
    coefs26 = eng.read_coefficients(COEF / "Bstar_coefficients_2026Q2_fullsample.csv")
    b_oil = wd.inputs["B"].copy()
    b_oil["cpie_qoq"] = np.nan
    rel = data.loc[q, ["grpe", "grpf"]]
    v = {
        "B-oil: realised Brent via the oil bridge": eng.run_scenario(wd, "B", coefs=coefs, horizon=HORIZON, inputs_override=b_oil).forecast["gcpi"],
        "B-rel: realised relative prices (authors' closure)": eng.run_scenario(
            wd, "B", coefs=coefs, horizon=HORIZON, grpe_override=rel["grpe"].values, grpf_override=rel["grpf"].values).forecast["gcpi"],
        "A with full-sample (2026Q2) coefficients": eng.run_scenario(wd, "A", coefs=coefs26, horizon=HORIZON).forecast["gcpi"],
        "B with full-sample (2026Q2) coefficients": eng.run_scenario(wd, "B", coefs=coefs26, horizon=HORIZON).forecast["gcpi"],
    }
    dv, lvv = D.load_vintage_2023()
    cv = pd.read_csv(COEF / "Bstar_coefficients_2023Q2_vintage20230915.csv")
    auxv = json.loads((COEF / "auxiliary_models_2023Q2_vintage20230915.json").read_text())["aux"]
    vpath = stage_workbook(OUT / "_vintage_workbook.xlsx", hist=lvv, aux=auxv, coef=cv,
                           meta_extra={"data_vintage": "as-of 2023-09-15 vintage (sensitivity)"})
    wdv = eng.read_workbook(vpath)
    cvd = {eq: g.set_index("term")["coef"] for eq, g in cv.groupby("eq")}
    v["A: as-of 2023-09-15 data vintage"] = eng.run_scenario(wdv, "A", coefs=cvd, horizon=HORIZON).forecast["gcpi"]
    v["B: as-of 2023-09-15 data vintage"] = eng.run_scenario(wdv, "B", coefs=cvd, horizon=HORIZON).forecast["gcpi"]
    (OUT / "_vintage_workbook.xlsx").unlink()

    tabs = EV.build_tables(main, real, g_hist)
    vtabs = EV.build_tables({MA: main[MA], MB: main[MB], **v, "AR(4)": ar4}, real, g_hist)

    # ---- decomposition: A error = assumptions (Shapley over drivers) + relationships (equation residuals)
    shap, _ = EV.shapley_drivers(wd, coefs, in_a, in_b, HORIZON)
    res23 = E.fit(data, ORIGIN)
    resid = EV.one_step_residuals(res23, data, q)
    rdec, b_path, allr = EV.residual_decomposition(wd, coefs, wd.inputs["B"], HORIZON, resid)
    check_all = float((allr["gcpi"] - real["gcpi"]).abs().max())
    dec = pd.DataFrame(index=q)
    dec["error A (forecast - realised)"] = tabs["errors_qoq"][MA]
    drv_cols = []
    for c in shap.columns[:-1]:
        dec[f"assumption: {c}"] = -shap[c]                      # contribution to (A - B)
        drv_cols.append(f"assumption: {c}")
    dec["= error from assumptions (A - B)"] = dec[drv_cols].sum(axis=1)
    rel_cols = []
    for e, lab in (("gw", "wage equation"), ("gcpi", "CPI (price) equation"), ("cf10", "10y expectations equation"), ("cf1", "1y expectations equation")):
        dec[f"relationship: {lab}"] = -rdec[e]                  # contribution to (B - realised)
        rel_cols.append(f"relationship: {lab}")
    dec["= error from relationships (B - realised)"] = dec[rel_cols].sum(axis=1)
    dec["check (should be 0)"] = dec["error A (forecast - realised)"] - dec["= error from assumptions (A - B)"] - dec["= error from relationships (B - realised)"]
    insample_sd = {eq: float(np.sqrt(r.sigma2)) for eq, r in res23.items()}
    z = resid.div(pd.Series(insample_sd))

    # share of squared error (over the first 12 quarters)
    sse = {"assumptions (A - B)": float((dec["= error from assumptions (A - B)"] ** 2).sum()),
           "relationships (B - realised)": float((dec["= error from relationships (B - realised)"] ** 2).sum()),
           "total A": float((dec["error A (forecast - realised)"] ** 2).sum())}

    # ---- tables
    tab = pd.DataFrame({"realised q/q": real["gcpi"], "realised y/y": real["yoy"]})
    for m in main:
        tab[f"{m} q/q"] = tabs["forecasts_qoq"][m]
        tab[f"{m} y/y"] = tabs["forecasts_yoy"][m]
    for m in main:
        tab[f"error {m} q/q"] = tabs["errors_qoq"][m]
        tab[f"error {m} y/y"] = tabs["errors_yoy"][m]
    with pd.ExcelWriter(OUT / "forecasts_and_errors.xlsx") as w:
        _idx(tab).to_excel(w, sheet_name="Forecasts_and_errors", index=False)
        tabs["metrics"].to_excel(w, sheet_name="Metrics_windows", index=False)
        tabs["horizon_errors"].to_excel(w, sheet_name="Errors_h4_h8_h12", index=False)
        tabs["window_average"].to_excel(w, sheet_name="Window_avg_inflation", index=False)
        _idx(dec).to_excel(w, sheet_name="Error_decomposition_A", index=False)
        _idx(z).to_excel(w, sheet_name="Equation_residual_z", index=False)
        _idx(vtabs["forecasts_qoq"]).to_excel(w, sheet_name="Variants_forecasts", index=False)
        vtabs["metrics"].to_excel(w, sheet_name="Variants_metrics", index=False)
        _idx(A.inputs_used).to_excel(w, sheet_name="Inputs_used_A", index=False)
        _idx(B.inputs_used).to_excel(w, sheet_name="Inputs_used_B", index=False)
    _idx(tab).to_csv(OUT / "forecasts_and_errors.csv", index=False)
    tabs["metrics"].to_csv(OUT / "metrics_windows.csv", index=False)
    tabs["horizon_errors"].to_csv(OUT / "errors_at_h4_h8_h12.csv", index=False)
    _idx(dec).to_csv(OUT / "error_decomposition_A.csv", index=False)
    _idx(vtabs["forecasts_qoq"]).to_csv(OUT / "variants_forecasts.csv", index=False)
    vtabs["metrics"].to_csv(OUT / "variants_metrics.csv", index=False)
    for sc, r in (("A", A), ("B", B)):
        eng.write_result(r, OUT, f"forecast_{sc}")

    # ---- charts
    hist_g = g_hist.loc["2021Q1":]
    yoy_all = 100.0 * (p.levels["cpi"] / p.levels["cpi"].shift(4) - 1.0)
    CH.actual_vs_forecast(real["gcpi"], tabs["forecasts_qoq"], hist_g, "CPI inflation, q/q annualised: realised vs forecasts from 2023Q2",
                          "% (400 x dln CPI)", CHD / "fig1_cpi_qoq_actual_vs_forecast.png",
                          "A: information at 2023Q2 only. B: realised drivers, same 2023Q2 coefficients. Realised = latest data vintage.")
    CH.actual_vs_forecast(real["yoy"], tabs["forecasts_yoy"], yoy_all.loc["2021Q1":ORIGIN], "CPI inflation, y/y: realised vs forecasts from 2023Q2",
                          "% y/y", CHD / "fig2_cpi_yoy_actual_vs_forecast.png", "Each forecast y/y chains the quarterly forecasts on the realised history.")
    CH.error_bars(tabs["errors_qoq"], "Forecast errors (forecast - realised), CPI q/q annualised", "pp", CHD / "fig3_forecast_errors_qoq.png")
    CH.decomposition_panels(dec, drv_cols, rel_cols, CHD / "fig4_error_A_decomposition.png",
                            "Exercise A error = (A - B) + (B - realised). Top: Shapley contribution of each driver. Bottom: effect of each equation's realised residual.")
    return {"A": A, "B": B, "tabs": tabs, "vtabs": vtabs, "dec": dec, "shap": shap, "rdec": rdec, "check_all_residuals_vs_realised": check_all,
            "z": z, "real": real, "insample_sd": insample_sd, "variants": v, "main": main, "sse": sse}
