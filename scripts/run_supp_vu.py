"""Phase 3 supplement, part 3: the missing October 2025 unemployment observation (V/U 2025Q4).
Writes outputs/phase3_supp/vu_*.csv. Nothing in outputs/phase3 is touched."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.estimation.inference import with_hac  # noqa: E402
from bb_inflation.estimation.rls import estimate  # noqa: E402
from bb_inflation.extension import coefs as CO  # noqa: E402
from bb_inflation.extension import history as HH  # noqa: E402
from bb_inflation.extension.models import fit, specs_for_end, standard_models  # noqa: E402
from bb_inflation.supplement import context as C  # noqa: E402
from bb_inflation.supplement import diag_pull as D  # noqa: E402
from bb_inflation.supplement import vu_bridge as V  # noqa: E402

OUT = OUTPUTS / "phase3_supp"
OUT.mkdir(parents=True, exist_ok=True)


def summarise(res, data, label, vu_value, dec, ms):
    g, p = res["gw"], res["gcpi"]
    hv = with_hac(g, data)
    s_vu, se_vu, _ = CO.sum_se(hv, g.block_names("vu"))
    base = dec.baseline["gcpi"]
    vu_c = dec.contributions["vu"]["gcpi"]
    return {"case": label, "V/U 2025Q4": vu_value, "wage eq N": g.nobs, "wage eq sample end": str(g.sample[1]),
            "V/U sum": s_vu, "V/U sum HAC se": se_vu, "wage own lags + cf1": float(g.coef[g.block_names("gw")].sum()),
            "catch-up sum": float(g.coef[g.block_names("diffcpicf")].sum()),
            "price eq: wage pass-through": float(p.coef[p.block_names("gw")].sum()), "price eq N": p.nobs,
            "dynamic CPI baseline 2026Q1 (pp)": float(base.loc["2026Q1"]), "dynamic CPI baseline 2026Q2 (pp)": float(base.loc["2026Q2"]),
            "mean dynamic CPI baseline 2026Q1-Q2": float(base.loc["2026Q1":"2026Q2"].mean()),
            "V/U contribution to CPI, mean 2026Q1-Q2": float(vu_c.loc["2026Q1":"2026Q2"].mean()),
            "wage growth baseline 2026Q1-Q2": float(dec.baseline["gw"].loc["2026Q1":"2026Q2"].mean())}


def main() -> None:
    ctx = C.load("interp")
    p3, last = ctx.p3, ctx.last
    S = D.load(ctx.supp_pull)
    J, U = S["uslama1304"], S["uslama1795"]
    CC = V.monthly_mean_weekly(S["uslama3350"])

    # ---- 1. what exists and what does not
    status = pd.DataFrame([
        {"observation": "Unemployment level, Oct 2025 (SA, NSA, rate)", "status": "does not exist: CPS October 2025 never collected (BLS)",
         "found in": "BLS CPS (bls_lns13000000m), Macrobond uslama1795/2169/1849/2320: all blank"},
        {"observation": "JOLTS openings, Oct/Nov/Dec 2025", "status": "actual", "found in": "Macrobond uslama1304 (BLS JTS000000000000000JOL)"},
        {"observation": "Unemployment level, Sep/Nov/Dec 2025", "status": "actual", "found in": "Macrobond uslama1795"},
        {"observation": "V/U 2025Q4", "status": "ESTIMATED (one component: October unemployment level)", "found in": "bridge, see vu_bridge_alternatives.csv"},
        {"observation": "All other quarters 1990Q1-2026Q2", "status": "actual (authors' history to 2000Q4, Macrobond after)", "found in": "pinned Phase 3 pull"}])
    status.to_csv(OUT / "vu_observation_status.csv", index=False)
    ChecksRaw = {t: (S[t].index[S[t].index == pd.Timestamp("2025-10-01")].size) for t in ("uslama1795", "uslama2169", "uslama1849", "uslama1304")}
    pd.Series(ChecksRaw).to_csv(OUT / "vu_oct2025_observation_present.csv", header=["rows dated 2025-10-01 in series"])

    # ---- 2. bridge alternatives and back-test
    alt = V.bridge_all(J, U, CC)
    alt.to_csv(OUT / "vu_bridge_alternatives.csv", index=False)
    bt = V.backtest(J, U, CC)
    bt.to_csv(OUT / "vu_bridge_backtest_errors.csv", index=False)
    bts = V.summarize_backtest(bt)
    bts.to_csv(OUT / "vu_bridge_backtest_summary.csv", index=False)

    # cross-check with the vendor-supplied SA unemployment RATE for Oct 2025 (4.5%, first appears in the Aug-2026 Macrobond vintage;
    # BLS's own series page shows no October value) x interpolated SA labour force. Not used in estimation.
    LF = S["bls_lns11000000m"]
    lf_oct = 0.5 * (LF[pd.Timestamp("2025-09-01")] + LF[pd.Timestamp("2025-11-01")])
    xrows = []
    # Chicago Fed real-time (private-data) nowcasts as reported in the press (Reuters/Yahoo, Nov 2025): 4.35%, later update 4.36%
    for lab, rate in (("rate 4.45%", 4.45), ("rate 4.50% (as published by Macrobond)", 4.5), ("rate 4.55%", 4.55),
                      ("Chicago Fed nowcast 4.35% (press-reported)", 4.35), ("Chicago Fed nowcast 4.36% (press-reported)", 4.36)):
        u_oct = rate / 100 * lf_oct
        months = pd.date_range("2025-10-01", periods=3, freq="MS")
        u3 = pd.Series({months[0]: u_oct, months[1]: U[months[1]], months[2]: U[months[2]]})
        xrows.append({"case": lab, "U_oct implied (thousand)": u_oct / 1e3, "V/U 2025Q4": float(J[months].mean() / u3.mean())})
    pd.DataFrame(xrows).to_csv(OUT / "vu_rate_crosscheck.csv", index=False)
    print(pd.DataFrame(xrows).round(4).to_string())

    # ---- 3. sensitivity of the wage equation and CPI results
    ms = standard_models(last)
    rows = []
    # Phase 3 baseline: hole in estimation, Nov-Dec bridge in simulation
    res0 = fit(ms["B"], p3.data, last)
    dec0 = HH.decompositions({"B": res0}, {"B": ms["B"]}, p3.data_bridged, C.P.GSCPI_FILL)["B"]
    rows.append(summarise(res0, p3.data, "Phase 3 baseline (hole in estimation; Nov-Dec bridge in simulation)", float(p3.data_bridged.loc["2025Q4", "vu"]), dec0, ms))
    cases = [(r.method, float(r.VU_2025Q4)) for r in alt.itertuples()] + [("stress low (V/U 0.80)", 0.80), ("stress high (V/U 1.00)", 1.00)]
    for lab, val in cases:
        data = C.with_vu(p3, val)
        res = fit(ms["B"], data, last)
        dec = HH.decompositions({"B": res}, {"B": ms["B"]}, data, C.P.GSCPI_FILL)["B"]
        rows.append(summarise(res, data, f"B*: {lab}", val, dec, ms))
    sens = pd.DataFrame(rows)
    sens.to_csv(OUT / "vu_sensitivity_modelB.csv", index=False)
    # frozen Model A is unaffected in estimation; its simulation inputs change only through the bridged lag
    # ---- 4. look-ahead audit
    audit = []
    val_trunc = C.bridge_value("interp", ctx.supp_pull, truncate="2025-12-01")
    audit.append({"check": "bridge value computed from data truncated at 2025-12 equals full-data value",
                  "result": bool(np.isclose(val_trunc, ctx.bridge_value, atol=1e-12)), "detail": f"{val_trunc:.6f} vs {ctx.bridge_value:.6f}"})
    spec = specs_for_end("gscpi_ma2", "2025Q4")
    same = True
    for eq in spec:
        a = estimate(spec[eq], p3.data, "1990Q1", "2025Q4")
        b = estimate(spec[eq], ctx.data_star, "1990Q1", "2025Q4")
        same &= bool(np.allclose(a.coef.values, b.coef.values, atol=1e-12)) and a.nobs == b.nobs
    audit.append({"check": "estimation through 2025Q4 (origin 2025Q4) is identical with and without the bridge", "result": same, "detail": "all four equations"})
    spec = specs_for_end("gscpi_ma2", "2026Q1")
    nobs = {eq: (estimate(spec[eq], p3.data, "1990Q1", "2026Q1").nobs, estimate(spec[eq], ctx.data_star, "1990Q1", "2026Q1").nobs) for eq in spec}
    audit.append({"check": "first origin whose estimation sample uses the bridge", "result": True,
                  "detail": f"2026Q1: wage eq N {nobs['gw'][0]} -> {nobs['gw'][1]}; other equations unchanged {nobs['gcpi']}"})
    pd.DataFrame(audit).to_csv(OUT / "vu_lookahead_audit.csv", index=False)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(alt.round(4).to_string())
    print(bts.round(4).to_string())
    print(sens.round(4).T.to_string())
    print(pd.DataFrame(audit).to_string())


if __name__ == "__main__":
    main()
