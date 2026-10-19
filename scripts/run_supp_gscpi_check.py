"""Phase 3 supplement: routine source-data and timestamp check of the GSCPI input (treatment unchanged from Phase 3).
Writes outputs/phase3_supp/gscpi_source_check.csv and gscpi_monthly_recent.csv."""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS, PHASE3_PULL  # noqa: E402
from bb_inflation.data import macrobond_audit as audit  # noqa: E402
from bb_inflation.data import phase3_data as P  # noqa: E402
from bb_inflation.supplement import diag_pull as D  # noqa: E402

OUT = OUTPUTS / "phase3_supp"
T = "wotrad0027"


def main() -> None:
    old = pd.read_csv(audit.PULLS / PHASE3_PULL / "native" / f"{T}.csv", index_col=0, parse_dates=True)["value"]
    S = D.load()                                         # integrity-checked
    new = S[T]
    sm = D.manifest()
    om = json.loads((audit.PULLS / PHASE3_PULL / "manifest.json").read_text())
    audit.load_pull(PHASE3_PULL)                          # raises if the pinned pull fails its SHA-256 check
    common = old.index.intersection(new.index)
    p3 = P.build(PHASE3_PULL)
    q = old.groupby(old.index.to_period("Q")).mean()
    rows = [
        ("pinned Phase 3 pull passes SHA-256 integrity check", "yes"),
        ("pinned pull retrieved (UTC)", om["retrieved_utc"][:19]),
        ("supplement re-pull retrieved (UTC)", sm["retrieved_utc"][:19]),
        ("Macrobond series / description", f"{T}: {om['series'][T]['description']}"),
        ("Macrobond LastRevisionTimeStamp (pinned / re-pull)", f"{om['series'][T]['macrobond_last_revision'][:19]} / {sm['series'][T]['macrobond_last_revision'][:19]}"),
        ("first / last monthly observation", f"{old.index[0].date()} / {old.index[-1].date()}"),
        ("observations revised between pinned pull and re-pull", int(((new[common] - old[common]).abs() > 1e-9).sum())),
        ("new observations in re-pull", len(new.index.difference(old.index))),
        ("missing months between first and last observation", int(len(pd.date_range(old.index[0], old.index[-1], freq="MS")) - len(old))),
        ("quarterly mean 2026Q2 used in model (Phase 3 dataset)", round(float(p3.data.loc["2026Q2", "shortage"]), 4)),
        ("quarterly mean 2026Q2 recomputed from monthly pull", round(float(q.loc[pd.Period("2026Q2", "Q")]), 4)),
        ("last complete quarter in model", str(p3.last_complete)),
        ("2026Q3 monthly GSCPI observed, not used (quarter incomplete for other series)", ", ".join(f"{d.strftime('%Y-%m')}={v:.3f}" for d, v in old.loc["2026-07-01":].items())),
        ("external cross-check (press reports of NY Fed release of 6 Oct 2026; not a download)",
         "Sep 2026 = 1.28 (pull 1.284); Aug revised to 1.20 (pull 1.199); May peak 1.81 (pull 1.808); release date 6 Oct 2026 = Macrobond revision stamp 2026-10-06"),
    ]
    pd.DataFrame(rows, columns=["check", "result"]).to_csv(OUT / "gscpi_source_check.csv", index=False)
    old.loc["2025-09-01":].rename("GSCPI (monthly, pinned pull)").to_csv(OUT / "gscpi_monthly_recent.csv", index_label="month")
    print(pd.DataFrame(rows, columns=["check", "result"]).to_string())


if __name__ == "__main__":
    main()
