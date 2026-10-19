"""Phase 3 supplement, part 1: post-2023 CPI over-prediction. Writes outputs/phase3_supp/resid_*.csv and fig_s1-s3."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.extension.models import fit, standard_models  # noqa: E402
from bb_inflation.simulation.model import SimModel  # noqa: E402
from bb_inflation.supplement import context as C  # noqa: E402
from bb_inflation.supplement import diag_pull as D  # noqa: E402
from bb_inflation.supplement import residuals as R  # noqa: E402

OUT = OUTPUTS / "phase3_supp"
OUT.mkdir(parents=True, exist_ok=True)
H = 12


def nw_mean_t(x: np.ndarray, L: int = 2) -> tuple[float, float]:
    x = np.asarray(x, float)
    m, e = x.mean(), x - x.mean()
    s = e @ e / len(x)
    for l in range(1, L + 1):
        s += 2 * (1 - l / (L + 1)) * (e[l:] @ e[:-l]) / len(x)
    se = np.sqrt(s / len(x))
    return m, m / se


def main() -> None:
    ctx = C.load()
    last, d = ctx.last, ctx.data_star
    ms = standard_models(last)
    A = fit(ms["A"], d, last)
    Bs = fit(ms["B"], d, last)
    fitA, fitB = R.one_step(A, d), R.one_step(Bs, d)
    sigma = float(A["gcpi"].resid.loc[:"2019Q4"].std())
    modelA = SimModel.from_results(A)
    dynA = R.fixed_origin_forecast(modelA, d, "2023Q2", H)
    qt = R.quarter_table(d, fitA, fitB, dynA, sigma)
    # Phase-3 style free-running baseline (simulation started 2018Q4 from actual lags), for comparison with the one-step measure
    from bb_inflation.extension import history as HH
    decs = HH.decompositions({"A": A, "B*": Bs}, {"A": ms["A"], "B*": ms["B"]}, d, C.P.GSCPI_FILL)
    for m_ in ("A", "B*"):
        qt[f"err_dynbase_2018Q4_{m_}"] = (d.gcpi - decs[m_].baseline["gcpi"]).reindex(qt.index)
    qt.to_csv(OUT / "resid_quarter_table.csv")
    pd.Series({"one-step A": qt.resid_A.mean(), "one-step B*": qt.resid_Bstar.mean(), "fixed-origin forecast from 2023Q2 (A)": qt.err_dyn_A.mean(),
               "free-running baseline from 2018Q4 (A)": qt["err_dynbase_2018Q4_A"].mean(), "free-running baseline from 2018Q4 (B*)": qt["err_dynbase_2018Q4_B*"].mean()}
              ).to_csv(OUT / "resid_mean_error_by_measure.csv", header=["mean actual - predicted, 2023Q3-2026Q2 (pp)"])

    # ---- significance of the post-2023 errors
    e = qt.resid_A.values
    m, t = nw_mean_t(e)
    top = qt.resid_A.abs().sort_values(ascending=False)
    stats_rows = [{"statistic": "mean one-step residual 2023Q3-2026Q2, Model A (pp)", "value": m},
                  {"statistic": "Newey-West t (L=2) of the mean", "value": t},
                  {"statistic": "sd of residuals, pre-2020 sample (pp)", "value": sigma},
                  {"statistic": "mean excluding 2023Q3", "value": float(qt.resid_A.drop(pd.Period('2023Q3', 'Q')).mean())},
                  {"statistic": "mean excluding 2023Q3, 2025Q4, 2026Q1, 2026Q2", "value": float(qt.resid_A.drop([pd.Period(q, 'Q') for q in ('2023Q3', '2025Q4', '2026Q1', '2026Q2')]).mean())},
                  {"statistic": "share of sum of squared residuals: 2023Q3", "value": float(qt.loc['2023Q3', 'share of sum sq resid_A (%)'])},
                  {"statistic": "share of sum of squared residuals: 2025Q4-2026Q2", "value": float(qt.loc['2025Q4':'2026Q2', 'share of sum sq resid_A (%)'].sum())},
                  {"statistic": "largest |z| (2023Q3)", "value": float(qt['z_A (resid/sd pre-2020)'].abs().max())}]
    pd.DataFrame(stats_rows).to_csv(OUT / "resid_significance.csv", index=False)

    # ---- attribution of the fixed-origin forecast error by equation
    att = R.error_attribution(modelA, d, fitA, "2023Q2", H)
    assert np.allclose(att["all four (check)"], att["error (actual - forecast)"], atol=1e-8), "residual shocks must reproduce actuals"
    att.to_csv(OUT / "resid_error_attribution_A.csv")

    # ---- energy / underlying / measurement
    S = D.load(ctx.supp_pull)
    mc = R.monthly_components(S)
    qa = R.quarterly_annualised(mc)
    w = R.cpi_weights(mc)
    ec = R.energy_check(d, Bs["gcpi"], qa, w)
    ec.to_csv(OUT / "resid_energy_check.csv")
    adj = R.shutdown_adjustment(mc)
    pd.Series({"w_energy": w["energy"], "w_food": w["food"], "w_core": w["core"], **{f"april_excess_{k}": v for k, v in adj["april_excess_monthly_pct"].items()},
               "adj_central_pp": adj["central_pp"], "adj_low_pp": adj["low_pp"], "adj_high_pp": adj["high_pp"], "w_rent_oer_assumed": adj["w_rent_oer"]}
              ).to_csv(OUT / "resid_shutdown_adjustment.csv", header=["value"])
    qt2 = qt[["actual", "fitted_A", "resid_A", "resid_Bstar"]].copy()
    qt2["measurement adj. (pp)"] = 0.0
    qt2.loc["2025Q4", "measurement adj. (pp)"] = adj["central_pp"]
    qt2.loc["2026Q2", "measurement adj. (pp)"] = -adj["central_pp"]
    qt2["resid_A adjusted"] = qt2.resid_A + qt2["measurement adj. (pp)"]
    qt2["resid_A adjusted (BLS low)"] = qt2.resid_A + qt2["measurement adj. (pp)"] / adj["central_pp"] * adj["low_pp"]
    qt2["resid_A adjusted (BLS high)"] = qt2.resid_A + qt2["measurement adj. (pp)"] / adj["central_pp"] * adj["high_pp"]
    qt2["core CPI"] = qa["core"].reindex(qt2.index)
    qt2["shelter CPI"] = pd.DataFrame({"s": mc["shelter"]}).pipe(R.quarterly_annualised)["s"].reindex(qt2.index)
    qt2["energy CPI"] = qa["energy"].reindex(qt2.index)
    qt2["gasoline CPI"] = qa["gasoline"].reindex(qt2.index)
    qt2["ECI wage growth (gw)"] = d["gw"].reindex(qt2.index)
    qt2["wage resid A"] = (d["gw"] - fitA["gw"]).reindex(qt2.index)
    qt2["GSCPI (qtr mean)"] = d["shortage"].reindex(qt2.index)
    qt2.to_csv(OUT / "resid_adjusted_and_drivers.csv")
    adj_stats = {"mean resid_A 2025Q4-2026Q2 unadjusted": float(qt2.loc["2025Q4":, "resid_A"].mean()),
                 "mean resid_A 2025Q4-2026Q2 adjusted": float(qt2.loc["2025Q4":, "resid_A adjusted"].mean()),
                 "mean resid_A 2026Q1-Q2 unadjusted": float(qt2.loc["2026Q1":, "resid_A"].mean()),
                 "mean resid_A 2026Q1-Q2 adjusted": float(qt2.loc["2026Q1":, "resid_A adjusted"].mean())}
    pd.Series(adj_stats).to_csv(OUT / "resid_adjusted_means.csv", header=["value"])

    # ---- energy asymmetry / nonlinearity
    thr = float(d["grpe"].loc[:"2019Q4"].std())
    sig, oos, E = R.asymmetry_tests(d, thr)
    sig.to_csv(OUT / "resid_energy_asymmetry_tests.csv", index=False)
    oos.to_csv(OUT / "resid_energy_asymmetry_oos.csv")
    E.to_csv(OUT / "resid_energy_asymmetry_oos_errors.csv")
    # residual vs energy in the price equation (post-2023 and earlier)
    rr = pd.DataFrame({"res": Bs["gcpi"].resid, "grpe": d.grpe})
    pd.Series({"threshold (1 sd of grpe 1990-2019)": thr, "n spikes above threshold 1990-2019": int((d.grpe.loc[:'2019Q4'] > thr).sum()),
               "n spikes above threshold 2020-2026Q2": int((d.grpe.loc['2020Q1':] > thr).sum())}).to_csv(OUT / "resid_energy_threshold.csv", header=["value"])
    big_post = rr.loc["2023Q3":]
    big_post[big_post.grpe > thr].to_csv(OUT / "resid_energy_spike_quarters_post2023.csv")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(qt.round(2).to_string())
    print(pd.DataFrame(stats_rows).round(3).to_string())
    print(att.round(2).to_string())
    print(w, adj)
    print(ec.round(2).T.to_string())
    print(qt2.round(2).T.to_string())
    print(adj_stats)
    print(sig.round(4).to_string())
    print(oos.round(3).to_string())
    print("threshold", thr)
    print(big_post[big_post.grpe > thr].round(2))
    figures(qt, qt2, att, ec, d, Bs, thr, adj)


def figures(qt, qt2, att, ec, d, Bs, thr, adj):
    # ---- Fig S1: actual vs predicted, residuals
    fig, ax = plt.subplots(1, 2, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.15, 1]})
    x = np.arange(len(qt))
    lab = [str(i).replace("Q", " Q") for i in qt.index]
    a = ax[0]
    a.plot(x, qt.actual, "k-o", lw=2.2, ms=4, label="Actual CPI inflation")
    a.plot(x, qt.fitted_A, color="#1f77b4", lw=1.6, marker="s", ms=3, label="Model A one-step (frozen at 2023Q2)")
    a.plot(x, qt.fitted_Bstar, color="#ff7f0e", lw=1.6, marker="^", ms=3, label="Model B* one-step (re-estimated)")
    a.plot(x, qt.dyn_A_from_2023Q2, color="#1f77b4", lw=1.2, ls="--", label="Model A conditional forecast from 2023Q2")
    a.set_xticks(x)
    a.set_xticklabels(lab, rotation=60, fontsize=8)
    a.set_ylabel("annualised quarterly CPI inflation, %")
    a.set_title("US CPI inflation: actual vs model-predicted, 2023Q3-2026Q2", fontsize=10)
    a.legend(frameon=False, fontsize=8)
    a.grid(alpha=.25)
    b = ax[1]
    w = 0.38
    b.bar(x - w / 2, qt.resid_A, w, color="#1f77b4", label="Model A residual (actual - predicted)")
    b.bar(x + w / 2, qt.resid_Bstar, w, color="#ff7f0e", label="Model B* residual")
    sg = qt.attrs.get("sigma", None)
    for k in (-1.96, 1.96):
        b.axhline(k * 0.571, color="grey", ls=":", lw=1)
    b.text(len(x) - 0.4, 1.96 * 0.571 + 0.04, "±1.96 pre-2020 s.d.", ha="right", fontsize=7, color="grey")
    b.axhline(0, color="k", lw=.6)
    b.set_xticks(x)
    b.set_xticklabels(lab, rotation=60, fontsize=8)
    b.set_ylabel("pp")
    b.set_title("One-step residuals (negative = model over-predicts)", fontsize=10)
    b.set_ylim(-2.7, 1.4)
    b.legend(frameon=False, fontsize=8, loc="lower center")
    b.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_s1_actual_vs_predicted.png", dpi=140)
    plt.close(fig)

    # ---- Fig S2: attribution + energy check + measurement
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.2))
    a = ax[0]
    cols = {"price-equation residual": "#d62728", "wage-equation residual": "#2ca02c", "1y-expectations residual": "#9467bd",
            "10y-expectations residual": "#8c564b"}
    pos, neg = np.zeros(len(att)), np.zeros(len(att))
    x = np.arange(len(att))
    for k, c in cols.items():
        v = att[k].values
        a.bar(x, v, bottom=np.where(v >= 0, pos, neg), color=c, label=k, width=.7)
        pos += np.where(v >= 0, v, 0)
        neg += np.where(v < 0, v, 0)
    a.plot(x, att["error (actual - forecast)"], "k-o", ms=4, lw=1.6, label="Total error (actual - forecast)")
    a.axhline(0, color="k", lw=.6)
    a.set_xticks(x)
    a.set_xticklabels([str(i).replace("Q", " Q") for i in att.index], rotation=60, fontsize=8)
    a.set_title("Model A forecast error from 2023Q2 by source (pp)", fontsize=10)
    a.legend(frameon=False, fontsize=7)
    a.grid(alpha=.25)
    b = ax[1]
    x = np.arange(len(ec))
    b.bar(x - .2, ec["model: energy block"], .4, color="#2e5eaa", label="Model energy contribution")
    b.bar(x + .2, ec["direct energy (w x energy CPI)"], .4, color="#9ecae1", label="Direct energy contribution (CPI weight x energy CPI)")
    b.plot(x, qt.resid_Bstar.reindex(ec.index).values, "r-o", ms=4, label="Model B* price residual")
    b.axhline(0, color="k", lw=.6)
    b.set_xticks(x)
    b.set_xticklabels([str(i).replace("Q", " Q") for i in ec.index], rotation=60, fontsize=8)
    b.set_title("Energy: model contribution vs mechanical direct contribution (pp)", fontsize=10)
    b.legend(frameon=False, fontsize=7)
    b.grid(alpha=.25)
    c = ax[2]
    sel = qt2.loc["2025Q1":]
    x = np.arange(len(sel))
    c.bar(x - .2, sel.resid_A, .4, color="#1f77b4", label="Model A residual")
    c.bar(x + .2, sel["resid_A adjusted"], .4, color="#aec7e8", label="after shutdown shelter adjustment (central)")
    c.errorbar(x[sel["measurement adj. (pp)"] != 0] + .2, sel.loc[sel["measurement adj. (pp)"] != 0, "resid_A adjusted"],
               yerr=None, fmt="none")
    c.axhline(0, color="k", lw=.6)
    c.set_xticks(x)
    c.set_xticklabels([str(i).replace("Q", " Q") for i in sel.index], rotation=60, fontsize=8)
    c.set_title(f"Residual before/after shutdown shelter artifact (±{adj['central_pp']:.2f}pp in 2025Q4 / 2026Q2)", fontsize=10)
    c.legend(frameon=False, fontsize=7)
    c.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_s2_error_sources.png", dpi=140)
    plt.close(fig)

    # ---- Fig S3: residual vs energy growth
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 5.2))
    rr = pd.DataFrame({"res": Bs["gcpi"].resid, "grpe": d.grpe}).dropna()
    old = rr.loc[:"2023Q2"]
    new = rr.loc["2023Q3":]
    ax.scatter(old.grpe, old.res, s=14, color="#9e9e9e", label="1990Q1-2023Q2")
    ax.scatter(new.grpe, new.res, s=36, color="#d62728", label="2023Q3-2026Q2")
    for q in new.index:
        if abs(new.loc[q, "res"]) > .8 or new.loc[q, "grpe"] > thr:
            ax.annotate(str(q), (new.loc[q, "grpe"], new.loc[q, "res"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.axvline(thr, color="grey", ls=":", lw=1)
    ax.axhline(0, color="k", lw=.6)
    ax.set_xlabel("relative energy price growth, annualised % (grpe)")
    ax.set_ylabel("Model B* price-equation residual, pp")
    ax.set_title("Price residual vs energy growth (dotted: 1 s.d. of 1990-2019 growth)", fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_s3_residual_vs_energy.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
