"""Validation 1: out-of-sample (and, clearly separated, in-sample) forecasts 2020Q1-2023Q2.
Writes outputs/validation/oos_*.csv and figures."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.data.authors_data import load_raw  # noqa: E402
from bb_inflation.estimation.inference import with_hac  # noqa: E402
from bb_inflation.validation import oos  # noqa: E402
from bb_inflation.validation.specs import VARIANTS, data_for, datasets  # noqa: E402

OUT = OUTPUTS / "validation"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    raw = load_raw()
    ds = datasets(raw)
    rows, one_rows, coef_rows, paths = [], [], [], {}
    plan = [("authors' data", True, ["none", "google5"]),
            ("Macrobond data", False, list(VARIANTS))]
    for dlabel, authors, names in plan:
        for name in names:
            v = VARIANTS[name]
            if authors is False and False:
                continue
            data = data_for(v, ds, authors=authors)
            for regime in ("genuine", "hybrid", "insample"):
                res = oos.fit_regime(v, data, regime)
                lab = {"data": dlabel, "spec": name, "regime": regime}
                fc = oos.dynamic_forecast(res, data, v)
                paths[(dlabel, name, regime)] = fc
                rows += oos.metrics(fc, data, {**lab, "forecast": "dynamic"})
                one_rows += oos.metrics(oos.one_step(res, data), data, {**lab, "forecast": "one-step"})
                if regime == "genuine":
                    hac = with_hac(res["gcpi"], data)
                    s = hac.summary()
                    if v.block is not None:
                        coef_rows.append({"data": dlabel, "spec": name, "est. end": "2019Q4",
                                          "shortage sum": s.loc[v.block.var, "sum"], "p_sum (HAC)": s.loc[v.block.var, "p_sum"],
                                          "p_joint (HAC)": s.loc[v.block.var, "p_joint"]})
    # AR(4) benchmark (same for both datasets: depends only on the endogenous series)
    ar = oos.ar4_forecast(ds["authors_google"])
    rows += oos.metrics(ar, ds["authors_google"], {"data": "authors' data", "spec": "AR(4)", "regime": "genuine",
                                                    "forecast": "dynamic"})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "oos_dynamic.csv", index=False)
    pd.DataFrame(one_rows).to_csv(OUT / "oos_onestep.csv", index=False)
    pd.DataFrame(coef_rows).to_csv(OUT / "oos_shortage_pre2020.csv", index=False)
    pd.to_pickle(paths, OUT / "oos_paths.pkl")
    pd.to_pickle(ar, OUT / "oos_ar4.pkl")
    pd.set_option("display.width", 250)
    pv = df[(df.variable == "gcpi")].pivot_table(index=["data", "spec"], columns="regime", values="RMSE")
    print(pv.round(2).to_string())


if __name__ == "__main__":
    main()
