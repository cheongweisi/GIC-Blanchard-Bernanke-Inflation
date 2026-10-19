"""Phase 4b part 2: error decomposition of the real-time-feasible forecast (tier D) versus AR(4). Writes outputs/phase4b/forecast_*.csv."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.phase4b import common as K  # noqa: E402
from bb_inflation.phase4b import forecast as F  # noqa: E402
from bb_inflation.scenarios import backtest as BT  # noqa: E402

GROUPS = {"oil path (flat vs realised)": ["oil path"], "other assumed drivers (V/U, productivity, GSCPI, food)": ["V/U", "productivity", "GSCPI", "food closure"],
          "oil -> CPI energy bridge": ["oil bridge"], "structural: price eq.": ["price eq. residuals"], "structural: wage eq.": ["wage eq. residuals"],
          "structural: expectations eqs.": ["1y expectations residuals", "10y expectations residuals"]}
BUCKETS = {"targets to 2019Q4": ("1990Q1", "2019Q4"), "2020Q1-2023Q2": ("2020Q1", "2023Q2"), "2023Q3-2026Q2": ("2023Q3", "2026Q2"),
           "2024Q1-2026Q2": ("2024Q1", "2026Q2"), "all targets": ("1990Q1", "2026Q2")}


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    tgt = pd.PeriodIndex(df["target"], freq="Q")
    rows = []
    for b, (lo, hi) in BUCKETS.items():
        sub = df[(tgt >= pd.Period(lo, "Q")) & (tgt <= pd.Period(hi, "Q"))]
        for h in (1, 4, 8, 12):
            s = sub[sub.h == h]
            if len(s) < 4:
                continue
            e = s["error D"].values
            ar = (s["AR4"] - s["actual"]).values
            row = {"target period": b, "h (quarters)": h, "n": len(s), "RMSE tier D": float(np.sqrt((e ** 2).mean())), "RMSE AR4": float(np.sqrt((ar ** 2).mean())),
                   "bias tier D": float(e.mean()), "bias AR4": float(ar.mean())}
            for g, cols in GROUPS.items():
                c = s[cols].sum(axis=1).values
                row[f"mean: {g}"] = float(c.mean())
                row[f"MSE share: {g}"] = float((c * e).mean() / (e ** 2).mean())          # shares add to 1 exactly
                row[f"RMSE of D without: {g}"] = float(np.sqrt(((e - c) ** 2).mean()))
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    w = K.world(n_draws=50)
    comp, paths = F.decompose(w, BT.origins(w))
    assert comp["check (sum - error)"].abs().max() < 1e-8
    K.save(comp, "forecast_error_components.csv", index=False)
    K.save(paths, "forecast_paths_selected.csv", index=False)
    yo = comp[comp.measure == "y/y (log approx.)"]
    qu = comp[comp.measure == "quarterly (ann.)"]
    K.save(summarise(yo), "forecast_error_summary_yoy.csv", index=False)
    K.save(summarise(qu), "forecast_error_summary_quarterly.csv", index=False)
    # reproduce stored Phase 4 tier D
    rec = pd.read_csv(K.OUT.parent / "phase4" / "backtest_records.csv")
    rd = rec[rec.tier == "D"].merge(qu[["origin", "h", "tier D"]].assign(h=lambda x: x.h), on=["origin", "h"])
    print("tier D reproduces Phase 4 stored forecasts: max abs diff", float((rd["forecast"] - rd["tier D"]).abs().max()), "n", len(rd))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    s = pd.read_csv(K.OUT / "forecast_error_summary_yoy.csv")
    cols = ["target period", "h (quarters)", "n", "RMSE tier D", "RMSE AR4", "bias tier D", "bias AR4"] + [c for c in s.columns if c.startswith("mean:")]
    print(s[cols].round(2).to_string())
    cols = ["target period", "h (quarters)"] + [c for c in s.columns if c.startswith("MSE share")]
    print(s[cols].round(2).to_string())
    cols = ["target period", "h (quarters)", "RMSE tier D", "RMSE AR4"] + [c for c in s.columns if c.startswith("RMSE of D without")]
    print(s[cols].round(2).to_string())


def _nw_slope(y: np.ndarray, x: np.ndarray, L: int):
    X = np.column_stack([np.ones(len(x)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    A = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    S = u.T @ u
    for l in range(1, L + 1):
        G = u[l:].T @ u[:-l]
        S += (1 - l / (L + 1)) * (G + G.T)
    V = A @ S @ A
    return b[1], float(np.sqrt(V[1, 1])), b[0]


def oil_scenario_validation() -> pd.DataFrame:
    """Does the model's oil effect match what happened? Predicted oil effect on y/y inflation = forecast with realised oil minus forecast with oil held flat
    (all other drivers realised, bridge on). Outcome = actual minus the flat-oil forecast. Slope 1 = the model's oil scenario deviations are right on average;
    the intercept absorbs everything else. Origins are overlapping, so HAC with L = 2h."""
    c = pd.read_csv(K.OUT / "forecast_error_components.csv")
    y = c[c.measure.str.startswith("y/y")].copy()
    y["pred_oil"] = -y["oil path"]
    y["outcome"] = y["actual"] - (y["tier C (realised oil)"] + y["oil path"])
    tgt = pd.PeriodIndex(y["target"], freq="Q")
    rows = []
    for lab, mask in (("all targets", np.ones(len(y), bool)), ("targets to 2019Q4", tgt <= pd.Period("2019Q4", "Q")), ("targets 2020Q1-2026Q2", tgt >= pd.Period("2020Q1", "Q")),
                      ("excluding 2022", ~((tgt >= pd.Period("2022Q1", "Q")) & (tgt <= pd.Period("2022Q4", "Q"))))):
        for h in (1, 4, 8):
            s = y[mask & (y.h == h)].sort_values("origin")
            b, se, a = _nw_slope(s["outcome"].values, s["pred_oil"].values, L=max(2 * h, 2))
            rows.append({"sample": lab, "h": h, "n": len(s), "slope on predicted oil effect": b, "HAC s.e.": se, "intercept": a,
                         "s.d. of predicted oil effect (pp)": float(s["pred_oil"].std()), "slope=1 rejected at 5%": abs(b - 1) > 1.96 * se})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
    v = oil_scenario_validation()
    K.save(v, "forecast_oil_scenario_validation.csv", index=False)
    print(v.round(3).to_string())
