"""One-off (2026-10-18): when did a value for the October 2025 SA unemployment rate first appear in Macrobond's revision history?
BLS's own series page (data.bls.gov LNS14000000) shows no October 2025 value (footnote: unavailable due to the lapse in appropriations).
Output: outputs/phase3_supp/vu_oct2025_rate_vintages.csv"""
import datetime as dt
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import macrobond_data_api as mda  # noqa: E402
import pandas as pd  # noqa: E402

rows = []
d = dt.datetime(2025, 12, 1)
while d <= dt.datetime(2026, 9, 1):
    s = mda.get_one_vintage_series(d, "uslama1849")
    ser = s.values_to_pd_data_frame().set_index("date")["value"]
    rows.append({"vintage": d.date().isoformat(), "last_obs": str(ser.index[-1].date()), "Sep 2025": ser.get(pd.Timestamp("2025-09-01")),
                 "Oct 2025": ser.get(pd.Timestamp("2025-10-01")), "Nov 2025": ser.get(pd.Timestamp("2025-11-01"))})
    d += dt.timedelta(days=14)
df = pd.DataFrame(rows)
df.to_csv(Path(__file__).resolve().parents[2] / "outputs" / "phase3_supp" / "vu_oct2025_rate_vintages.csv", index=False)
print(df.to_string())
