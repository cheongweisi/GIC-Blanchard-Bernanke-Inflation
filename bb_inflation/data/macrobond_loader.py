"""Retrieval of the model's raw series from Macrobond (COM API) with local, vintage-stamped caching.

Public API
    fetch_raw(vintage=None, refresh=False)  -> DataFrame in the authors' raw-column layout (quarterly)
    splice_authors_history(mb_raw, authors_raw) -> adds the authors' V/U and ECI history before 2001

`vintage=None` retrieves the current data; a datetime retrieves the data as it stood on that date (Macrobond
revision history), e.g. AUTHORS_VINTAGE to compare with the authors' dataset. Every pull is cached under
data_cache/macrobond/<vintage>/ with the retrieval timestamp, so results stay reproducible when Macrobond data
are later revised.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import PROJECT_ROOT
from .macrobond_registry import REGISTRY, SPLICE_LAST_AUTHORS_QUARTER, SeriesDef

CACHE = PROJECT_ROOT / "data_cache" / "macrobond"


def _api():
    import macrobond_data_api as mda  # imported lazily: only needed when talking to Macrobond
    return mda


def _tag(vintage: dt.datetime | None) -> str:
    return "current" if vintage is None else vintage.strftime("asof_%Y%m%d")


def fetch_series(ticker: str, vintage: dt.datetime | None = None) -> pd.Series:
    """One native-frequency Macrobond series (DatetimeIndex, first day of period)."""
    mda = _api()
    s = mda.get_one_series(ticker) if vintage is None else mda.get_one_vintage_series(vintage, ticker)
    df = s.values_to_pd_data_frame().set_index("date")["value"].dropna()
    df.index = pd.DatetimeIndex(df.index)
    return df.rename(ticker)


def _quarter_end_complete(s: pd.Series) -> pd.Series:
    """Value of the last month of each quarter; only quarters whose final month (Mar/Jun/Sep/Dec) is observed."""
    g = s.groupby(s.index.to_period("Q"))
    last_month = g.apply(lambda x: x.index[-1].month)
    return g.last()[last_month.isin([3, 6, 9, 12])]


def to_quarterly(s: pd.Series, how: str) -> pd.Series:
    """Monthly -> quarterly with the authors' conventions ('last', 'mean') or pass-through ('native')."""
    if how == "native":
        q = s.copy()
        q.index = q.index.to_period("Q")
        return q
    if how == "last":
        return _quarter_end_complete(s)
    if how == "mean":
        g = s.groupby(s.index.to_period("Q"))
        return g.mean()[g.count() == 3]          # complete quarters only
    raise ValueError(how)


def quarterly_series(d: SeriesDef, vintage: dt.datetime | None = None) -> pd.Series:
    return quarterly_from_native(d, [fetch_series(t, vintage) for t in d.tickers])


def quarterly_from_native(d: SeriesDef, raw: list[pd.Series]) -> pd.Series:
    """Authors' monthly->quarterly conventions applied to already-retrieved native series."""
    if d.column == "VOVERU":
        num, den = (to_quarterly(x, "mean") for x in raw)   # ratio of quarterly means
        return (num / den).dropna().rename(d.column)
    return to_quarterly(raw[0], d.agg).rename(d.column)


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_raw(vintage: dt.datetime | None = None, refresh: bool = False,
              columns: tuple[str, ...] | None = None, pull_id: str | None = None) -> pd.DataFrame:
    """Quarterly DataFrame with the authors' raw column names, from Macrobond.

    vintage=None: *current* data, served from an explicit stamped pull (see macrobond_audit). By default the
        active pull is used, never a silent live refresh. `pull_id` selects another pull; `refresh=True` creates a
        new stamped pull (it only becomes the active one via macrobond_audit.set_active_pull).
    vintage=datetime: data as of that date from Macrobond's revision history, cached with a SHA-256 in meta.json.
    """
    if vintage is None:
        from . import macrobond_audit as audit
        if refresh:
            pull_id = audit.refresh_pull()
        df = audit.load_pull(pull_id)
        return df if columns is None else df[list(columns)]
    folder = CACHE / _tag(vintage)
    path = folder / "quarterly_raw.csv"
    if path.exists() and not refresh:
        meta = json.loads((folder / "meta.json").read_text())
        if "sha256" in meta and meta["sha256"] != _sha256(path):
            raise RuntimeError(f"Cached Macrobond vintage {path} fails its SHA-256 check")
        df = pd.read_csv(path, index_col=0)
        df.index = pd.PeriodIndex(df.index, freq="Q", name="period")
        return df if columns is None else df[list(columns)]
    cols = {c: quarterly_series(d, vintage) for c, d in REGISTRY.items() if columns is None or c in columns}
    df = pd.DataFrame(cols).sort_index()
    df.index.name = "period"
    folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
    meta = {"retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "vintage": vintage.isoformat(), "sha256": _sha256(path),
            "series": {c: {"tickers": list(d.tickers), "agg": d.agg} for c, d in REGISTRY.items()}}
    (folder / "meta.json").write_text(json.dumps(meta, indent=2))
    return df


def splice_authors_history(mb_raw: pd.DataFrame, authors_raw: pd.DataFrame,
                           last_authors_quarter: str = SPLICE_LAST_AUTHORS_QUARTER) -> pd.DataFrame:
    """Use the authors' V/U and ECI up to `last_authors_quarter`, Macrobond afterwards.

    V/U: levels are concatenated (authors' post-2000 values equal JOLTS/unemployment).
    ECI: chain-linked at the join so the level path is continuous; only log differences enter the model,
    so growth is the authors' through the join quarter and Macrobond's after it.
    """
    out = mb_raw.copy()
    cut = pd.Period(last_authors_quarter, "Q")
    nxt = cut + 1
    vu = pd.concat([authors_raw["VOVERU"].loc[:cut], mb_raw["VOVERU"].loc[nxt:]])
    out["VOVERU"] = vu
    a = authors_raw["ECIWAG"].dropna()
    scale = mb_raw["ECIWAG"].loc[nxt] / a.loc[nxt]
    out["ECIWAG"] = pd.concat([(a.loc[:cut] * scale), mb_raw["ECIWAG"].loc[nxt:]])
    return out.sort_index()


def latest_observation(ticker: str) -> pd.Timestamp:
    return fetch_series(ticker).index[-1]


def observed_release_lag(ticker: str, search_days: int = 150) -> tuple[pd.Timestamp, pd.Timestamp | None]:
    """(latest observation date, first date it appeared in Macrobond's revision history).

    Bisects over daily vintages; returns None for the second item when the series has no usable history
    (e.g. series whose vintages are not stored). The lag in days is first_seen - end of the observation period.
    """
    last = latest_observation(ticker)
    today = dt.datetime.now()
    lo, hi = today - dt.timedelta(days=search_days), today
    try:
        if fetch_series(ticker, lo).index[-1] >= last:
            return last, None            # appeared before the search window
    except Exception:  # noqa: BLE001
        return last, None
    while (hi - lo).days > 1:
        mid = lo + (hi - lo) / 2
        try:
            seen = fetch_series(ticker, mid).index[-1] >= last
        except Exception:  # noqa: BLE001
            return last, None
        lo, hi = (lo, mid) if seen else (mid, hi)
    return last, pd.Timestamp(hi.date())
