"""Phase 1 replication driver: estimate on the authors' data, simulate, compare with the paper and the
shipped outputs, and write tables/figures to outputs/phase1/.

Run:  .venv\\Scripts\\python.exe scripts\\run_replication.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.data.authors_data import load_raw  # noqa: E402
from bb_inflation.data.transforms import build_model_data  # noqa: E402
from bb_inflation.estimation.replication import fit_full, fit_precovid  # noqa: E402
from bb_inflation.simulation.decomposition import decompose  # noqa: E402
from bb_inflation.simulation.forecast import conditional_forecast, linear_path, wage_constant  # noqa: E402
from bb_inflation.simulation.irf import irf, shock_sizes  # noqa: E402
from bb_inflation.simulation.model import SimModel  # noqa: E402
from bb_inflation.viz import figures as fg  # noqa: E402

OUT = OUTPUTS / "phase1"
OUT.mkdir(parents=True, exist_ok=True)

# Published values (paper Tables 2-5): (sum, p_sum, p_joint) by variable; R2 and N
PAPER = {
    "gw": {"gw": (.460, .008, .071), "vu": (.693, .030, .023), "diffcpicf": (-.024, .765, .994),
           "cf1": (.540, .002, .022), "magpty": (.031, None, .608), "R2": .578, "N": 120},
    "gcpi": {"gcpi": (.335, .037, .066), "gw": (.665, .000, .000), "grpe": (.066, .000, .000),
             "grpf": (.126, .050, .050), "shortage": (.018, .281, .000), "magpty": (-.143, None, .026),
             "R2": .947, "N": 133},
    "cf1": {"cf1": (.369, .014, .001), "cf10": (.506, .000, .000), "gcpi": (.124, .001, .000), "R2": .908, "N": 120},
    "cf10": {"cf10": (.975, .000, .000), "gcpi": (.025, .208, .004), "R2": .931, "N": 120},
}


def table_vs_paper(pre: dict, price_2023q1) -> str:
    rows = []
    for eq, paper in PAPER.items():
        res = price_2023q1 if eq == "gcpi" else pre[eq]
        s = res.summary()
        for var, vals in paper.items():
            if var in ("R2", "N"):
                continue
            rows.append((eq, var, vals[0], s.loc[var, "sum"], vals[1], s.loc[var, "p_sum"], vals[2],
                         s.loc[var, "p_joint"]))
        rows.append((eq, "R2", paper["R2"], res.r2_corr, None, None, None, None))
        rows.append((eq, "N", paper["N"], res.nobs, None, None, None, None))
    t = pd.DataFrame(rows, columns=["eq", "var", "paper_sum", "ours_sum", "paper_p_sum", "ours_p_sum",
                                    "paper_p_joint", "ours_p_joint"])
    t.to_csv(OUT / "table_vs_paper.csv", index=False)
    return t.round(3).to_markdown(index=False) if hasattr(t, "to_markdown") else t.round(3).to_string(index=False)


def main() -> None:
    raw = load_raw()
    data = build_model_data(raw)
    full, pre = fit_full(data), fit_precovid(data)
    price_2023q1 = fit_full(data, end="2023Q1")["gcpi"]   # the paper's price-equation sample (N=133)

    # --- coefficient tables
    for tag, res in (("full", full), ("precovid", pre)):
        with pd.ExcelWriter(OUT / f"coefficients_{tag}.xlsx") as w:
            for eq, r in res.items():
                pd.DataFrame({"beta": r.coef, "se": np.sqrt(np.diag(r.cov))}).to_excel(w, sheet_name=eq)
    table = table_vs_paper(pre, price_2023q1)
    (OUT / "table_vs_paper.txt").write_text(table, encoding="utf-8")
    print(table)

    # --- simulations (full-sample coefficients, as in the package)
    model = SimModel.from_results(full)
    resid = {k: full[k].resid for k in ("gw", "gcpi", "cf1", "cf10")}
    sz = shock_sizes(data, resid)
    irfs = {v: irf(model, v, sz[v]) for v in ("grpe", "grpf", "shortage", "vu")}
    dec = decompose(model, data)
    hist = data.loc["2022Q2":"2023Q1"]
    n = 401
    idx = pd.period_range("2023Q2", periods=n, freq="Q")
    wc = wage_constant(model, 1.2, 1.0, 10.0)
    paths = {}
    for tgt in (0.8, 1.2, 1.8):
        fut = pd.DataFrame({"grpe": 0.0, "grpf": 0.0, "shortage": 10.0, "magpty": 1.0,
                            "vu": linear_path(hist["vu"].iloc[-1], tgt, 8, n)}, index=idx)
        paths[f"V/U -> {tgt}"] = conditional_forecast(model, hist, fut, const_wage=wc)

    # --- figures
    fg.fig_actual_vs_predicted(data, pre, OUT / "fig03_07_08_09_pred_vs_actual.png")
    fg.fig_irfs(irfs, OUT / "fig10_11_irfs.png")
    fg.fig_decomposition(dec, data, OUT / "fig12_price_decomposition.png", "gcpi",
                         "Fig. 12  Sources of price inflation")
    fg.fig_decomposition(dec, data, OUT / "fig13_wage_decomposition.png", "gw", "Fig. 13  Sources of wage growth")
    fg.fig_forecast(paths, data["gcpi"], OUT / "fig14_conditional_forecast.png")
    print("\nFigures and tables written to", OUT)


if __name__ == "__main__":
    main()
