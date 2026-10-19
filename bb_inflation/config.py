"""Project paths. The original replication package is read-only and never written to."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = (
    PROJECT_ROOT / "original_replication_package" / "extracted"
    / "Replication Package" / "Code and Data"
)
PUBLIC_DATA = PACKAGE_DIR / "(1) Data" / "Public Data"
OUT_FULL = PACKAGE_DIR / "(2) Regressions" / "Output Data (Full Sample)"
OUT_PRECOVID = PACKAGE_DIR / "(2) Regressions" / "Output Data (Pre Covid Sample)"
CORE = PACKAGE_DIR / "(3) Core Results"
OUTPUTS = PROJECT_ROOT / "outputs"

# Estimation window used by the authors (effective start is 1990Q1, see docs/PHASE1-2_REPORT.md #1)
SAMPLE_START = "1990Q1"
FULL_END = "2023Q2"
PRECOVID_END = "2019Q4"

# Phase 3: fresh Macrobond pull used for the 2026 extension (explicit; independent of the ACTIVE_PULL used in Phases 1-2)
PHASE3_PULL = "pull_20261017T112636Z"
