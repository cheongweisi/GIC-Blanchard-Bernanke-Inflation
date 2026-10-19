"""Explicit, vintage-stamped, auditable Macrobond pulls of *current* data.

A pull is a folder data_cache/macrobond/pulls/pull_<UTC timestamp>/ holding
    quarterly_raw.csv        the model's raw columns (authors' layout)
    native/<ticker>.csv      every native-frequency series exactly as retrieved
    manifest.json            retrieval time, API version, per-series metadata (first/last observation,
                             Macrobond LastRevisionTimeStamp), registry snapshot, SHA-256 of every file, note
and a line in pulls_index.csv. Nothing is ever fetched implicitly: `load_pull` reads (and integrity-checks) a
stored pull; `refresh_pull` is the only function that talks to Macrobond for current data and it never
changes the active pull. `set_active_pull` is the explicit switch, so a model run always states which data it used.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import platform
import shutil
from pathlib import Path

import pandas as pd

from . import macrobond_loader as ml
from .macrobond_registry import REGISTRY

PULLS = ml.CACHE / "pulls"
ACTIVE_FILE = ml.CACHE / "ACTIVE_PULL"
INDEX = ml.CACHE / "pulls_index.csv"


def _mda_version() -> str:
    from importlib import metadata
    try:
        return metadata.version("macrobond-data-api")
    except metadata.PackageNotFoundError:
        return "unknown"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_pulls() -> pd.DataFrame:
    if not INDEX.exists():
        return pd.DataFrame(columns=["pull_id", "retrieved_utc", "note"])
    return pd.read_csv(INDEX)


def active_pull() -> str:
    if not ACTIVE_FILE.exists():
        raise FileNotFoundError("No active Macrobond pull. Run refresh_pull() then set_active_pull(<id>).")
    return ACTIVE_FILE.read_text().strip()


def set_active_pull(pull_id: str) -> None:
    if not (PULLS / pull_id / "manifest.json").exists():
        raise FileNotFoundError(pull_id)
    ACTIVE_FILE.write_text(pull_id)


def _append_index(pull_id: str, retrieved: str, note: str) -> None:
    idx = list_pulls()
    idx = pd.concat([idx, pd.DataFrame([{"pull_id": pull_id, "retrieved_utc": retrieved, "note": note}])])
    idx.to_csv(INDEX, index=False)


def refresh_pull(note: str = "") -> str:
    """Retrieve current data for every registered series and store them as a new stamped pull. Returns its id.

    Does not change the active pull."""
    import macrobond_data_api as mda
    now = dt.datetime.now(dt.timezone.utc)
    pull_id = now.strftime("pull_%Y%m%dT%H%M%SZ")
    folder = PULLS / pull_id
    (folder / "native").mkdir(parents=True)
    natives: dict[str, pd.Series] = {}
    series_meta: dict[str, dict] = {}
    for d in REGISTRY.values():
        for t in d.tickers:
            if t in natives:
                continue
            s = ml.fetch_series(t)
            natives[t] = s
            s.rename("value").to_csv(folder / "native" / f"{t}.csv", index_label="date")
            md = mda.get_one_entity(t).metadata
            series_meta[t] = {"first_obs": str(s.index[0].date()), "last_obs": str(s.index[-1].date()), "n": len(s),
                              "frequency": md.get("Frequency"),
                              "macrobond_last_revision": str(md.get("LastRevisionTimeStamp")),
                              "description": md.get("FullDescription")}
    cols = {c: ml.quarterly_from_native(d, [natives[t] for t in d.tickers]) for c, d in REGISTRY.items()}
    q = pd.DataFrame(cols).sort_index()
    q.index.name = "period"
    q.to_csv(folder / "quarterly_raw.csv")
    files = {str(p.relative_to(folder)).replace("\\", "/"): _sha(p) for p in sorted(folder.rglob("*.csv"))}
    manifest = {"pull_id": pull_id, "retrieved_utc": now.isoformat(), "note": note,
                "macrobond_data_api": _mda_version(), "python": platform.python_version(),
                "host": platform.node(), "series": series_meta,
                "registry": {c: {"tickers": list(d.tickers), "agg": d.agg, "source_code": d.source_code}
                             for c, d in REGISTRY.items()},
                "sha256": files}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    _append_index(pull_id, now.isoformat(), note)
    return pull_id


def adopt_legacy_current() -> str | None:
    """One-time migration of the Phase-2 'current' cache (quarterly data only) into the stamped-pull layout."""
    legacy = ml.CACHE / "current"
    if not legacy.exists():
        return None
    meta = json.loads((legacy / "meta.json").read_text())
    stamp = dt.datetime.fromisoformat(meta["retrieved_utc"]).astimezone(dt.timezone.utc)
    pull_id = stamp.strftime("pull_%Y%m%dT%H%M%SZ")
    folder = PULLS / pull_id
    if folder.exists():
        return pull_id
    folder.mkdir(parents=True)
    shutil.copy2(legacy / "quarterly_raw.csv", folder / "quarterly_raw.csv")
    manifest = {"pull_id": pull_id, "retrieved_utc": meta["retrieved_utc"],
                "note": "migrated from the Phase-2 'current' cache; quarterly data only (native series not stored)",
                "registry": meta["series"], "sha256": {"quarterly_raw.csv": _sha(folder / "quarterly_raw.csv")}}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    _append_index(pull_id, meta["retrieved_utc"], manifest["note"])
    return pull_id


def load_pull(pull_id: str | None = None, verify: bool = True) -> pd.DataFrame:
    """Read a stored pull (default: the active pull), checking every file against the manifest."""
    pull_id = pull_id or active_pull()
    folder = PULLS / pull_id
    manifest = json.loads((folder / "manifest.json").read_text())
    if verify:
        for rel, h in manifest["sha256"].items():
            if _sha(folder / rel) != h:
                raise RuntimeError(f"Integrity check failed for {pull_id}/{rel}")
    df = pd.read_csv(folder / "quarterly_raw.csv", index_col=0)
    df.index = pd.PeriodIndex(df.index, freq="Q", name="period")
    return df


def describe_pull(pull_id: str | None = None) -> dict:
    pull_id = pull_id or active_pull()
    m = json.loads((PULLS / pull_id / "manifest.json").read_text())
    return {"pull_id": pull_id, "retrieved_utc": m["retrieved_utc"], "note": m.get("note", ""),
            "quarterly_sha256": m["sha256"]["quarterly_raw.csv"]}


def compare_pulls(a: str, b: str, tol: float = 1e-9) -> pd.DataFrame:
    """What changed between two pulls, per raw column: revised observations (existing quarters), new quarters."""
    x, y = load_pull(a), load_pull(b)
    rows = []
    for c in x.columns:
        common = x.index.intersection(y.index)
        d = (y.loc[common, c] - x.loc[common, c]).dropna()
        ch = d[d.abs() > tol]
        rows.append({"column": c, "revised_obs": len(ch), "max_abs_revision": d.abs().max() if len(d) else 0.0,
                     "first_revised": str(ch.index[0]) if len(ch) else "",
                     "last_obs_a": str(x[c].dropna().index[-1]), "last_obs_b": str(y[c].dropna().index[-1])})
    return pd.DataFrame(rows)


def write_provenance(path, **extra) -> dict:
    """Record exactly which data a run used (active pull, its hash, the as-of vintage, package versions)."""
    import json as _json
    import sys

    import numpy
    import pandas
    import scipy
    import statsmodels

    from .macrobond_registry import AUTHORS_VINTAGE
    info = {"written_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "active_pull": describe_pull(),
            "authors_vintage_cache": "asof_%04d%02d%02d" % AUTHORS_VINTAGE,
            "python": sys.version.split()[0], "numpy": numpy.__version__, "pandas": pandas.__version__,
            "scipy": scipy.__version__, "statsmodels": statsmodels.__version__, **extra}
    Path(path).write_text(_json.dumps(info, indent=2))
    return info
