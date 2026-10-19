"""Phase 2b: swap ladder from the authors' data to Macrobond + GSCPI. Writes outputs/phase2/ladder.xlsx and figures.

Run:  .venv\Scripts\python.exe scripts\run_phase2b.py   (needs the Macrobond desktop app)
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.data.authors_data import load_raw  # noqa: E402
from bb_inflation.data.macrobond_loader import fetch_raw  # noqa: E402
from bb_inflation.simulation.irf import irf  # noqa: E402
from bb_inflation.validation import ladder as L  # noqa: E402
from bb_inflation.viz import figures as fg  # noqa: E402

OUT = OUTPUTS / "phase2"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    raw = load_raw()
    rows = L.run_all(raw)
    df = L.to_frame(rows)
    with pd.ExcelWriter(OUT / "ladder.xlsx") as w:
        df.T.to_excel(w, sheet_name="all metrics")
        for g in ("ladder", "sensitivity", "vintage", "alone"):
            sub = df[df.group == g].drop(columns="group")
            sub.T.to_excel(w, sheet_name=g)
    df.to_csv(OUT / "ladder.csv")
    by = {r["case"]: r for r in rows}
    key = lambda p: next(v for k, v in by.items() if k.startswith(p))   # noqa: E731
    l0, l5, l6, s1 = key("L0"), key("L5"), key("L6"), key("S1")

    def irfs(r):
        return {v: irf(r["_model"], v, r["_sizes"][v]) for v in ("grpe", "grpf", "shortage", "vu")}

    fg.fig_irf_compare({"L0 authors": irfs(l0), "L5 Macrobond, Google shortage": irfs(l5),
                        "L6 Macrobond, GSCPI": irfs(l6), "S1 L6 + Macrobond ECI history": irfs(s1)},
                       OUT / "fig_ladder_irfs.png")
    fg.fig_decomp_compare([("L0 authors (Google shortage)", l0["_dec"], l0["_data"]),
                           ("L5 Macrobond, Google shortage", l5["_dec"], l5["_data"]),
                           ("L6 Macrobond, GSCPI", l6["_dec"], l6["_data"])], OUT / "fig_ladder_decomposition.png")
    fg.fig_shortage_series(raw["SHORTAGE"], fetch_raw(None)["GSCPI"], OUT / "fig_google_vs_gscpi.png")
    lad = df[df.group == "ladder"]
    fg.fig_price_coefs(lad, OUT / "fig_ladder_price_coefs.png")
    print(df.filter(regex="^(sum gcpi|R2 gcpi)").round(3).to_string())
    print("written to", OUT)


if __name__ == "__main__":
    main()
