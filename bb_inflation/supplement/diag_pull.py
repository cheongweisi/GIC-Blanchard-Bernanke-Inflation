"""Stamped, hash-checked pull of *diagnostic* series for the Phase 3 supplement (underlying inflation, shelter, oil, claims,
earnings) plus a read-only re-pull of the ten model series, used only to check Phase 3's pinned pull for revisions.

Stored under data_cache/macrobond/supplement/supp_<UTC>/ ; the Phase 3 pull and its pin (config.PHASE3_PULL) are untouched.
Nothing here feeds model estimation. Weekly series are stored as retrieved; monthly averages are formed in the analysis code.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import pandas as pd

from ..config import PROJECT_ROOT

SUPP = PROJECT_ROOT / "data_cache" / "macrobond" / "supplement"

DIAG = {
    "core_cpi": "uspric2373", "shelter_cpi": "uspric2170", "oer_cpi": "uspric2243", "rent_cpi": "uspric2239",
    "services_ex_energy_cpi": "uspric2403", "core_goods_cpi": "uspric2382", "gasoline_cpi": "uspric2345",
    "median_cpi_ar": "uspric0017", "trimmed_mean_cpi_ar": "uspric0018",
    "ahe": "uslama0001", "payrolls": "uslama1060", "unemp_rate_sa": "uslama1849", "unemp_level_nsa": "uslama2169",
    "labor_force_sa": "bls_lns11000000m", "unemp_rate_bls_sa": "bls_lns14000000m",
    "claims_continuing_w": "uslama3350", "claims_initial_w": "uslama3295", "brent_wb": "wocaes0935",
}
MODEL = ["uspric2156", "uspric2368", "uspric2158", "uslama0202", "uslama4604", "uslama1304", "uslama1795",
         "usfcst0101", "usfcst0110", "wotrad0027"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pull(note: str = "") -> str:
    import macrobond_data_api as mda
    now = dt.datetime.now(dt.timezone.utc)
    pid = now.strftime("supp_%Y%m%dT%H%M%SZ")
    folder = SUPP / pid
    (folder / "series").mkdir(parents=True)
    meta = {}
    for name, t in {**DIAG, **{m: m for m in MODEL}}.items():
        s = mda.get_one_series(t)
        df = s.values_to_pd_data_frame().set_index("date")["value"].dropna()
        df.rename("value").to_csv(folder / "series" / f"{t}.csv", index_label="date")
        md = mda.get_one_entity(t).metadata
        meta[t] = {"role": name, "first_obs": str(df.index[0])[:10], "last_obs": str(df.index[-1])[:10], "n": len(df),
                   "frequency": md.get("Frequency"), "macrobond_last_revision": str(md.get("LastRevisionTimeStamp")),
                   "description": md.get("FullDescription")}
    man = {"pull_id": pid, "retrieved_utc": now.isoformat(), "note": note, "series": meta,
           "sha256": {str(p.relative_to(folder)).replace("\\", "/"): _sha(p) for p in sorted(folder.rglob("*.csv"))}}
    (folder / "manifest.json").write_text(json.dumps(man, indent=2))
    return pid


def latest() -> str:
    return sorted(p.name for p in SUPP.iterdir() if p.is_dir())[-1]


def load(pid: str | None = None) -> dict[str, pd.Series]:
    """Series by ticker, integrity-checked against the manifest."""
    pid = pid or latest()
    folder = SUPP / pid
    man = json.loads((folder / "manifest.json").read_text())
    for rel, h in man["sha256"].items():
        if _sha(folder / rel) != h:
            raise RuntimeError(f"integrity check failed: {pid}/{rel}")
    out = {}
    for rel in man["sha256"]:
        t = Path(rel).stem
        s = pd.read_csv(folder / rel, index_col=0, parse_dates=True)["value"]
        out[t] = s
    return out


def manifest(pid: str | None = None) -> dict:
    return json.loads((SUPP / (pid or latest()) / "manifest.json").read_text())
