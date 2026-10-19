"""Phase 2a: build docs/data_dictionary.md and the reconciliation tables from live Macrobond data.

Run:  .venv\\Scripts\\python.exe scripts\\run_phase2a.py       (needs the Macrobond desktop app)
Outputs: docs/data_dictionary.md, outputs/phase2/reconciliation_*.csv
"""
import datetime as dt
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import macrobond_data_api as mda  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS, PROJECT_ROOT  # noqa: E402
from bb_inflation.data import macrobond_audit as audit  # noqa: E402
from bb_inflation.data.authors_data import load_raw  # noqa: E402
from bb_inflation.data.macrobond_loader import fetch_raw, observed_release_lag  # noqa: E402
from bb_inflation.data.macrobond_registry import AUTHORS_VINTAGE, NOT_ON_MACROBOND, REGISTRY  # noqa: E402
from bb_inflation.validation import macrobond_recon as R  # noqa: E402

OUT = OUTPUTS / "phase2"
OUT.mkdir(parents=True, exist_ok=True)
DOCS = PROJECT_ROOT / "docs"


def md(df: pd.DataFrame, floatfmt: str = ".4f") -> str:
    return df.to_markdown(index=False, floatfmt=floatfmt)


def series_table() -> pd.DataFrame:
    cur = fetch_raw(None)
    rows = []
    for col, d in REGISTRY.items():
        meta = mda.get_one_entity(d.tickers[0])
        ends = [mda.get_one_series(t).values_to_pd_data_frame()["date"].iloc[[0, -1]] for t in d.tickers]
        first_obs = max(x.iloc[0] for x in ends)                      # ratio: both series must exist
        binding = min(range(len(d.tickers)), key=lambda i: ends[i].iloc[-1])   # earliest-ending series limits the ratio
        last_obs, first_seen = observed_release_lag(d.tickers[binding])
        freq = meta.metadata.get("Frequency", "")
        period_end = last_obs + (pd.offsets.MonthEnd(0) if freq == "monthly" else pd.offsets.QuarterEnd(0))
        lag = (first_seen - period_end).days if first_seen is not None else None
        if lag is not None and lag < 0:
            lag = "within period (nowcast)"
        qlast = cur[col].dropna()
        rows.append({
            "Model column": col, "Macrobond ticker(s)": " / ".join(d.tickers), "Description": d.description,
            "Agency code": d.source_code, "Unit": d.unit, "SA": d.sa, "Native freq": freq,
            "To quarterly": {"last": "last month of quarter", "mean": "mean of 3 months", "native": "none"}[d.agg],
            "First obs (native)": str(first_obs)[:7],
            "Latest obs (native)": str(last_obs)[:7],
            "Latest quarter in model data": str(qlast.index[-1]),
            "Observed release lag (days after period end)": lag if lag is not None else "n/a",
            "Notes": d.note})
    return pd.DataFrame(rows)


def main() -> None:
    raw = load_raw()
    today = dt.date.today().isoformat()
    pull = audit.describe_pull()
    st = series_table()
    sr = R.series_reconciliation(raw)
    eci = R.eci_history_check(raw)
    est = R.estimation_reconciliation(raw).reset_index()
    gg = R.gscpi_vs_google(raw)
    for name, df in (("series", sr), ("eci_history", eci), ("estimation", est), ("gscpi_vs_google", gg), ("dictionary", st)):
        df.to_csv(OUT / f"reconciliation_{name}.csv", index=False)

    v = dt.datetime(*AUTHORS_VINTAGE).date().isoformat()
    text = f"""# Data dictionary (Phase 2)

Generated {today} by `scripts/run_phase2a.py`. Series metadata is live from Macrobond; the "current vintage" data are the stamped,
hash-checked pull `{pull["pull_id"]}` (retrieved {pull["retrieved_utc"][:19]} UTC, SHA-256 {pull["quarterly_sha256"][:16]}...).
Do not edit by hand.

## 1. Series retrieved from Macrobond

{md(st, ".2f")}

Observed release lag = first date the latest observation appears in Macrobond's vintage history minus the end of its
observation period (resolution about one day). Cleveland Fed values for the current month are published during
that month (nowcasts), so for the quarter-end convention below the latest *complete* quarter is the last one with
a March/June/September/December value.

## 2. Model variables and transformations (identical to the authors' Stata code)

| Variable | Definition |
|---|---|
| gcpi | 400 * dln(CPIAUCSL), quarter-end-month CPI |
| gw | 400 * dln(ECIWAG) |
| gpty / magpty | 400 * dln(OPHNFB); magpty = 8-quarter moving average of gpty (current + 7 lags) |
| grpe, grpf | 400 * dln(CPIENGSL / ECIWAG), 400 * dln(CPIUFDSL / ECIWAG) |
| vu | VOVERU (JOLTS openings / unemployed; Barnichon before 2001) |
| cf1, cf10 | Cleveland Fed 1-year and 10-year expected inflation, quarter-end month |
| shortage | Google Trends 'shortage' (authors); 5 before 2004Q1. Phase 2b replaces it with GSCPI (fill -0.035 before 1997Q4 as in authors' Table A8 variant) |
| diffcpicf (catch-up) | mean(gcpi_t..gcpi_t-3) - cf1_t-4 |

## 3. Conventions discovered by reconciliation (not stated in the authors' documentation)

* The authors' CPI, CPI energy, CPI food, Cleveland 1y and 10y series are the **value of the last month of the quarter**
  (not the quarterly average that the data dictionary's "Quarterly" label suggests). Quarterly averages differ from the authors' data by up to 3 index points.
* V/U is the **ratio of quarterly means** of JOLTS openings and the unemployment level.
* GSCPI is the mean of the three monthly values (authors' `clean_shortages.R`).
* Productivity and ECI are native quarterly.
* The authors' dataset is a vintage (series pulled at different dates between 7 and 27 Sep 2023 for productivity, early
  Oct 2023 for GSCPI). Macrobond's revision history, queried as of **{v}**, reproduces it (section 4).
* Macrobond history starts 1980Q1 for ECI wages & salaries, 2000-12 for JOLTS openings, 1997-09 for GSCPI.

## 4. Not available on Macrobond

{chr(10).join('* ' + x for x in NOT_ON_MACROBOND)}

Handling (decision of 2026-10-16): V/U and ECI for 1989Q1-2000Q4 are taken from the authors' public `Regression_Data`,
Macrobond from 2001Q1 (ECI chain-linked at the join). The Google 'shortage' series is replaced by GSCPI in Phase 2b.

## 5. Reconciliation with the authors' dataset (Phase 2a)

### 5.1 Series level

{md(sr, ".5f")}

### 5.2 Pre-2001 ECI: authors' splice versus Macrobond's own ECI wages & salaries history

{md(eci, ".3f")}

### 5.3 End-to-end: sum of estimated coefficients (authors' specification, 1990Q1-2023Q2)

{md(est, ".4f")}

### 5.4 GSCPI versus the Google 'shortage' index

{md(gg, ".3f")}
"""
    (DOCS / "data_dictionary.md").write_text(text, encoding="utf-8")
    print("wrote", DOCS / "data_dictionary.md")


if __name__ == "__main__":
    main()
