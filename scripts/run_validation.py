"""Run the whole pre-Phase-3 validation (outputs/validation/) against the active, hash-checked Macrobond pull.

Run:  .venv\Scripts\python.exe scripts\run_validation.py     (needs the Macrobond app only for the authors'-vintage
cache if it is missing; current data come from the stored pull, never from a silent refresh)
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_val_gscpi  # noqa: E402
import run_val_irfbands  # noqa: E402
import run_val_oos  # noqa: E402
import run_val_stability  # noqa: E402
import run_val_wageprice  # noqa: E402

from bb_inflation.config import OUTPUTS  # noqa: E402
from bb_inflation.data import macrobond_audit as audit  # noqa: E402

if __name__ == "__main__":
    out = OUTPUTS / "validation"
    out.mkdir(parents=True, exist_ok=True)
    print(audit.write_provenance(out / "data_provenance.json"))
    for mod in (run_val_oos, run_val_gscpi, run_val_wageprice, run_val_irfbands, run_val_stability):
        print("=" * 30, mod.__name__)
        mod.main()
