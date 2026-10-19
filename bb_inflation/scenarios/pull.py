"""Stamped, hash-checked pull of the Phase 4 inputs: oil (history, EIA STEO, ICE/CME Brent futures strip) and a re-pull of the
monthly series needed to describe the partly observed quarter 2026Q3.

Stored under data_cache/macrobond/phase4/p4_<UTC>/ ; Phase 1-3 pulls and pins are untouched. The model's estimation data still
come from `config.PHASE3_PULL` (+ the flagged V/U bridge of the supplement); this pull only adds information dated after the
estimation sample and the oil series. Nothing is fetched implicitly: `load()` reads and integrity-checks a stored pull and
`PHASE4_PULL` (scenarios/pin.py) names the one in use.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import pandas as pd

from ..config import PROJECT_ROOT

P4 = PROJECT_ROOT / "data_cache" / "macrobond" / "phase4"
MONTH_CODE = dict(zip(range(1, 13), "fghjkmnquvxz"))

OIL = {"brent_wb_monthly": "wocaes0935", "eia_steo_brent_monthly": "eiasteo0002", "eia_steo_brent_quarterly": "steo_brepuus_q",
       "brent_front_daily": "b_c1_cl", "wti_spot_daily": "uscaes0301"}
MODEL = {"cpi": "uspric2156", "cpi_energy": "uspric2368", "cpi_food": "uspric2158", "gscpi": "wotrad0027",
         "cleveland_1y": "usfcst0101", "cleveland_10y": "usfcst0110", "jolts_openings": "uslama1304",
         "unemployment_level_sa": "uslama1795", "productivity_q": "uslama0202", "eci_wages_q": "uslama4604"}
FUT_START = "2025-10-01"                   # keep about a year of daily closes per contract


def futures_tickers() -> dict[str, str]:
    """ICE/CME Brent contracts by delivery month, Oct 2026 - Dec 2029 (Macrobond tickers bz<year><month code>_cl)."""
    out = {}
    for y in (2026, 2027, 2028, 2029):
        for m in range(1, 13):
            if (y, m) >= (2026, 10):
                out[f"bz_{y}{m:02d}"] = f"bz{y}{MONTH_CODE[m]}_cl"
    return out


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pull(note: str = "") -> str:
    import macrobond_data_api as mda
    now = dt.datetime.now(dt.timezone.utc)
    pid = now.strftime("p4_%Y%m%dT%H%M%SZ")
    folder = P4 / pid
    (folder / "series").mkdir(parents=True)
    meta = {}
    for role, t in {**OIL, **MODEL, **futures_tickers()}.items():
        s = mda.get_one_series(t)
        df = s.values_to_pd_data_frame().set_index("date")["value"].dropna()
        if role.startswith("bz_") or role in ("brent_front_daily", "wti_spot_daily"):
            df = df.loc[FUT_START:]
        df.rename("value").to_csv(folder / "series" / f"{t}.csv", index_label="date")
        md = mda.get_one_entity(t).metadata
        meta[t] = {"role": role, "first_obs": str(df.index[0])[:10], "last_obs": str(df.index[-1])[:10], "n": len(df),
                   "frequency": md.get("Frequency"), "macrobond_last_revision": str(md.get("LastRevisionTimeStamp")),
                   "description": md.get("FullDescription")}
    man = {"pull_id": pid, "retrieved_utc": now.isoformat(), "note": note, "series": meta,
           "sha256": {str(p.relative_to(folder)).replace("\\", "/"): _sha(p) for p in sorted(folder.rglob("*.csv"))}}
    (folder / "manifest.json").write_text(json.dumps(man, indent=2))
    return pid


def load(pid: str) -> dict[str, pd.Series]:
    """Series by ticker, integrity-checked against the manifest (raises on any hash mismatch)."""
    folder = P4 / pid
    man = json.loads((folder / "manifest.json").read_text())
    for rel, h in man["sha256"].items():
        if _sha(folder / rel) != h:
            raise RuntimeError(f"integrity check failed: {pid}/{rel}")
    return {Path(rel).stem: pd.read_csv(folder / rel, index_col=0, parse_dates=True)["value"] for rel in man["sha256"]}


def manifest(pid: str) -> dict:
    return json.loads((P4 / pid / "manifest.json").read_text())
