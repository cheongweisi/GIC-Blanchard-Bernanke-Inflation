# Bernanke–Blanchard US inflation model: replication, validation and 2026 extension

Independent Python project (no dependency on any other model). The authors' files are preserved, read-only, in
`original_replication_package/` (SHA-256 manifest in `original_replication_package_MANIFEST.sha256`). Status: Phases 1-3 complete;
Phase 4 (scenario framework) complete: see `docs/phase4_report.md`.

Phase 4 (2026-10-18): `docs/phase4_report.md` (baseline, scenario library, transmission and driver attribution, forecast-status ladder), `docs/phase4_data_dictionary.md`.
Phases 1-3 are untouched (hash manifest `outputs/phase4/pre_phase4_manifest.sha256`). Earlier phases:
Start with `docs/phase3_report.md` (Phase 3 results) and `docs/phase3_supplement_report.md` (supplement of 2026-10-18: post-2023 forecast
errors, interpretable IRFs, bridge for the missing October 2025 V/U, Model B*), then `docs/validation_report.md`.

```
bb_inflation/
  config.py            paths, sample dates, PHASE3_PULL (the Macrobond pull used for the 2026 extension)
  data/                authors_data.py, transforms.py; macrobond_registry/_loader/_audit.py (stamped, hash-checked pulls);
                       phase3_data.py (2026 dataset: last complete quarter, V/U hole handling, ECI history options)
  estimation/          equations.py (declarative specs), rls.py (restricted LS, F-tests), replication.py,
                       inference.py (HAC errors, IRF draws/bands, stability tests), wls.py (exponentially weighted restricted LS)
  simulation/          model.py (dynamic simulator), irf.py, decomposition.py, forecast.py, general.py (derived regressors)
  validation/          authors_outputs.py, macrobond_recon.py, ladder.py (Phase 2); specs.py, oos.py, gscpi_tests.py, wage_price.py
  extension/           Phase 3: models.py (A, B, C), pseudo_oos.py, coefs.py, history.py, irfs.py
  supplement/          Phase 3 supplement: diag_pull.py (stamped diagnostic pull), vu_bridge.py, context.py (Model B* data), residuals.py, irf_intuitive.py
  scenarios/           Phase 4: pull.py/pin.py (stamped oil + 2026Q3 data), oil.py (oil -> CPI energy bridge, oil paths), engine.py (nominal-price simulator,
                       relative prices derived), world.py (baseline), scenario.py, library.py, attribution.py, uncertainty.py, backtest.py
  viz/                 figures.py
tests/                 109 tests (80 + 13 supplement + 16 Phase 4): authors' outputs, Macrobond reconciliation, no-look-ahead, inference, pull integrity, Phase 3
scripts/               run_replication.py (Phase 1) | run_phase2a.py, run_phase2b.py | run_validation.py | run_phase3.py (and run_phase3_*.py parts)
                       mb_search.py (Macrobond series search); _oneoff/ (audit trail of documentation corrections)
docs/                  phase3_report.md, phase3_data_dictionary.md, validation_report.md, phase2a/2b_findings.md, replication_log.md,
                       data_dictionary.md, PHASE1-2_REPORT.md (original plan, annotated)
outputs/               phase1/, phase2/, validation/, phase3/, phase3_supp/, phase4/ (tables and charts; earlier phases are never overwritten by later ones)
data_cache/macrobond/  pulls/<pull_id>/ (manifest + SHA-256 + native series), ACTIVE_PULL, pulls_index.csv, asof_20230915/
```

Setup and run (Windows):

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts\run_replication.py     # Phase 1 figures and tables
.venv\Scripts\python.exe scripts\run_phase3.py          # Phase 3 (about 12 minutes; reads the stored pull, needs no Macrobond connection)
.venv\Scripts\python.exe scripts\run_p4_main.py         # Phase 4 baseline, scenarios, attribution (seconds; stored pulls only)
.venv\Scripts\python.exe scripts\run_p4_backtest.py     # Phase 4 forecast-status ladder
.venv\Scripts\python.exe scripts\run_p4_figures.py      # Phase 4 figures
```

Macrobond data refresh (explicit, never silent):

```
python -c "from bb_inflation.data import macrobond_audit as a; p=a.refresh_pull('note'); print(a.compare_pulls(a.active_pull(), p))"
python -c "from bb_inflation.data import macrobond_audit as a; a.set_active_pull('<pull_id>')"   # only after reviewing the comparison
```

Phases 1-2 use the *active* pull (`pull_20261016T061219Z`). Phase 3 pins its own pull in `config.PHASE3_PULL`
(`pull_20261017T112636Z`), so refreshing data never changes earlier results.
