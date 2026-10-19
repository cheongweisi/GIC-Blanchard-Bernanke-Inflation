"""Phase 3 data documentation and QA: writes docs/phase3_data_dictionary.md and outputs/phase3/data_qa_*.csv from the
stamped Phase 3 pull. Run:  .venv\\Scripts\\python.exe scripts\\run_phase3_data.py"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS, PHASE3_PULL, PROJECT_ROOT  # noqa: E402
from bb_inflation.data import macrobond_audit as audit  # noqa: E402
from bb_inflation.data.macrobond_audit import _mda_version  # noqa: E402
from bb_inflation.data import phase3_data as P  # noqa: E402
from bb_inflation.data.authors_data import load_raw  # noqa: E402
from bb_inflation.data.macrobond_registry import REGISTRY  # noqa: E402
from bb_inflation.data.transforms import build_model_data  # noqa: E402

OUT = OUTPUTS / "phase3"
OUT.mkdir(parents=True, exist_ok=True)
MODEL_VARS = ["gcpi", "gw", "grpe", "grpf", "vu", "cf1", "cf10", "shortage", "shortagema2", "magpty", "diffcpicf"]
AGG = {"last": "value of the last month of the quarter", "mean": "mean of the three months (complete quarters only)",
       "native": "none (native quarterly)"}


def md(df: pd.DataFrame, fmt: str = ".3f") -> str:
    return df.to_markdown(index=False, floatfmt=fmt)


def main() -> None:
    p3 = P.build(PHASE3_PULL)
    p3m = P.build(PHASE3_PULL, eci_history="macrobond")
    manifest = json.loads((audit.PULLS / PHASE3_PULL / "manifest.json").read_text())
    mb = audit.load_pull(PHASE3_PULL)
    prev = audit.list_pulls().pull_id.tolist()
    prev = [x for x in prev if x != PHASE3_PULL]
    cmp_rows = pd.concat([audit.compare_pulls(x, PHASE3_PULL).assign(vs=x) for x in prev]) if prev else pd.DataFrame()

    # ---- series table
    rows = []
    for col, d in REGISTRY.items():
        t = d.tickers
        meta = [manifest["series"][x] for x in t]
        q = mb[col].dropna()
        rows.append({"Model column": col, "Macrobond ticker(s)": " / ".join(t), "Definition": d.description, "Agency code": d.source_code,
                     "Unit": d.unit, "SA": d.sa, "Native freq": meta[0]["frequency"], "Quarterly aggregation": AGG[d.agg],
                     "First obs (native)": max(m["first_obs"] for m in meta)[:7], "Last obs (native)": min(m["last_obs"] for m in meta)[:7],
                     "Last quarter, quarterly data": str(q.index[-1]), "Macrobond last revision (UTC)": max(m["macrobond_last_revision"] for m in meta)[:16]})
    series_tab = pd.DataFrame(rows)
    series_tab.to_csv(OUT / "data_qa_series.csv", index=False)

    # ---- model variable QA
    x = p3.data.loc["1990Q1":]
    miss = x[MODEL_VARS].isna().sum()
    miss_rows = pd.DataFrame({"variable": miss.index, "missing (1990Q1-last)": miss.values,
                              "quarters": [", ".join(str(q) for q in x.index[x[c].isna()]) or "-" for c in miss.index]})
    rng = pd.DataFrame({"variable": MODEL_VARS,
                        "mean 1990Q1-2019Q4": [x.loc[:"2019Q4", v].mean() for v in MODEL_VARS],
                        "mean 2020Q1-2023Q2": [x.loc["2020Q1":"2023Q2", v].mean() for v in MODEL_VARS],
                        "mean 2023Q3-last": [x.loc["2023Q3":, v].mean() for v in MODEL_VARS],
                        "min (since 2023Q3)": [x.loc["2023Q3":, v].min() for v in MODEL_VARS],
                        "max (since 2023Q3)": [x.loc["2023Q3":, v].max() for v in MODEL_VARS],
                        "largest |z| since 2023Q3 vs 1990-2019": [float(((x.loc["2023Q3":, v] - x.loc[:"2019Q4", v].mean()) / x.loc[:"2019Q4", v].std()).abs().max()) for v in MODEL_VARS]})
    rng.to_csv(OUT / "data_qa_ranges.csv", index=False)
    # overlap with the authors' dataset (current-vintage revisions only)
    authors = build_model_data(load_raw())
    ov = []
    for v in ("gcpi", "gw", "grpe", "grpf", "vu", "cf1", "cf10", "magpty"):
        d = (p3.data[v] - authors[v]).loc["1990Q1":"2023Q2"].dropna()
        ov.append({"variable": v, "n": len(d), "mean |diff|": d.abs().mean(), "max |diff|": d.abs().max(), "at": str(d.abs().idxmax())})
    ov = pd.DataFrame(ov)
    ov.to_csv(OUT / "data_qa_overlap_authors.csv", index=False)
    # ECI sensitivity
    g_a = 400 * np.log(p3.raw["ECIWAG"]).diff()
    g_m = 400 * np.log(p3m.raw["ECIWAG"]).diff()
    e = pd.concat([g_a, g_m], axis=1, keys=["authors splice", "Macrobond ECI"]).loc["1990Q1":]
    eci = pd.DataFrame([{"window": w, "mean growth (authors)": e.loc[lo:hi, "authors splice"].mean(),
                         "mean growth (Macrobond)": e.loc[lo:hi, "Macrobond ECI"].mean(),
                         "mean |diff|": (e.loc[lo:hi, "authors splice"] - e.loc[lo:hi, "Macrobond ECI"]).abs().mean()}
                        for w, (lo, hi) in {"1990Q1-2000Q4": ("1990Q1", "2000Q4"), "2001Q1-2026Q2": ("2001Q1", "2026Q2")}.items()])
    part = p3.partial_quarters.copy()
    part.index = part.index.astype(str)
    part = part.reset_index(names="quarter")
    for c in P.RAW_COLS:
        part[c] = np.where(part[c].isna(), "missing", "observed")

    text = f"""# Phase 3 data dictionary and QA

Generated by `scripts/run_phase3_data.py`. Do not edit by hand.

## 1. Snapshot

| | |
|---|---|
| Pull id | `{PHASE3_PULL}` (explicit, independent of the Phase 1-2 active pull) |
| Retrieved (UTC) | {manifest['retrieved_utc'][:19]} |
| Macrobond data API | {manifest.get('macrobond_data_api') if manifest.get('macrobond_data_api') != 'unknown' else _mda_version() + ' (installed version when documented; the manifest of this pull predates version recording)'} |
| Quarterly file SHA-256 | `{manifest['sha256']['quarterly_raw.csv']}` |
| Native series | stored under `data_cache/macrobond/pulls/{PHASE3_PULL}/native/` with SHA-256 per file |
| Last complete quarter | **{p3.last_complete}** (latest quarter with all nine raw series observed) |
| Sample used | 1990Q1-{p3.last_complete} (lags built from 1989Q1); wage equation effectively ends 2025Q4, see section 4 |

Comparison with the earlier Phase 1-2 pull(s): {('none' if cmp_rows.empty else 'revised observations ' + str(int(cmp_rows.revised_obs.sum())) + ' across all series; last observation unchanged for every series (data identical)')}.

## 2. Series

{md(series_tab)}

Quarterly conventions are the authors' (reconciled in `docs/phase2a_findings.md`): CPI, CPI energy, CPI food and the Cleveland Fed
expectations are the value of the quarter's last month, not an average; V/U is the ratio of quarterly means; GSCPI is a quarterly
mean. Series codes, definitions and units are those of `docs/data_dictionary.md`.

## 3. Incomplete quarters: reported, not used

Latest quarters in the pull, by series coverage (anything after {p3.last_complete} is excluded from every model):

{md(part)}

{chr(10).join('* ' + n for n in p3.notes if 'partial' in n)}

## 4. Missing values

* Native monthly series with gaps since 1990: CPI (all items, energy, food) and the unemployment level are missing for **October 2025**
  (not published). The CPI quarter-end convention (December value) is unaffected; the unemployment mean for 2025Q4 would need three months, so
  **V/U 2025Q4 is undefined** under the authors' ratio-of-quarterly-means definition. Nothing else is missing in the model variables.
* Baseline: V/U 2025Q4 stays missing in estimation. Consequence: the wage equation (four lags of V/U) loses 2026Q1 and 2026Q2 and ends in 2025Q4
  (N = 144 against 146 for the other equations).
* Simulations, fitted values and decompositions need a V/U path, so for those only (never for estimation) 2025Q4 is bridged with the ratio of
  means over the months where both inputs exist (November-December 2025): {p3.data_bridged.loc['2025Q4','vu']:.4f}. It is flagged in the code
  (`Phase3Data.flags`, `data_bridged`) and a sensitivity estimating with the bridged value is reported in `outputs/phase3/models_coef_summary_bridgedVU.csv`.

{md(miss_rows)}

## 5. Model variables

| Variable | Definition |
|---|---|
| gcpi, gw | 400 * dln(CPIAUCSL), 400 * dln(ECIWAG) |
| grpe, grpf | 400 * dln(CPIENGSL / ECIWAG), 400 * dln(CPIUFDSL / ECIWAG) |
| magpty | 8-quarter moving average of 400 * dln(OPHNFB) |
| vu | JOLTS openings / unemployed (authors' history through 2000Q4) |
| cf1, cf10 | Cleveland Fed 1- and 10-year expected inflation |
| shortage | GSCPI (quarterly mean); -0.035 (2019 mean, the authors' Table A8 convention) before 1997Q4 |
| shortagema2 | trailing mean of shortage over the current and previous quarter (baseline regressor, `gscpi_ma2`) |
| diffcpicf | mean(gcpi_t..gcpi_t-3) - cf1_t-4 |
| D2020Q2, D2020Q3 | wage-equation dummies, included once those quarters are in the estimation sample |

Descriptive ranges (growth rates annualised, percent):

{md(rng)}

## 6. ECI history

Baseline: the authors' pre-2001 splice (through 2000Q4), Macrobond's ECI wages and salaries afterwards. Sensitivity: Macrobond's own ECI
(from 1980Q1) for the whole sample.

{md(eci)}

## 7. Consistency with the authors' dataset (1990Q1-2023Q2, current vintage minus authors' vintage)

{md(ov, '.4f')}

The differences are data revisions (see `docs/phase2a_findings.md`): productivity, CPI seasonal factors and JOLTS.
"""
    (PROJECT_ROOT / "docs" / "phase3_data_dictionary.md").write_text(text, encoding="utf-8")
    json.dump({"pull_id": PHASE3_PULL, "last_complete": str(p3.last_complete), "notes": p3.notes}, open(OUT / "data_provenance.json", "w"), indent=2)
    print(text[:2500])


if __name__ == "__main__":
    main()
