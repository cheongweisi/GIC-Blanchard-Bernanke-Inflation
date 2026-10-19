"""One-off (2026-10-18): live read-only Macrobond query of every unemployment series that could hold October 2025.
Result stored in outputs/phase3_supp/vu_oct2025_live_probe.csv. Not part of the model pipeline."""
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import macrobond_data_api as mda  # noqa: E402
import pandas as pd  # noqa: E402

rows = []
for n in ["uslama1795", "uslama2169", "uslama1849", "uslama2320", "bls_lns13000000m", "bls_lns14000000m", "bls_lnu03000000m",
          "uslama1304"]:
    s = mda.get_one_series(n)
    e = mda.get_one_entity(n)
    ser = pd.Series(s.values, index=pd.to_datetime(s.dates))
    rows.append({"ticker": n, "description": e.metadata.get("FullDescription"), "last_revision": str(e.metadata.get("LastRevisionTimeStamp"))[:19],
                 "Sep 2025": ser.get(pd.Timestamp("2025-09-01")), "Oct 2025": ser.get(pd.Timestamp("2025-10-01")), "Nov 2025": ser.get(pd.Timestamp("2025-11-01")),
                 "queried_utc": pd.Timestamp.now("UTC").isoformat()[:19]})
pd.DataFrame(rows).to_csv(Path(__file__).resolve().parents[2] / "outputs" / "phase3_supp" / "vu_oct2025_live_probe.csv", index=False)
print(pd.DataFrame(rows).drop(columns="description").to_string())
