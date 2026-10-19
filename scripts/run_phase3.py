"""Run the whole Phase 3 extension from the stamped pull `config.PHASE3_PULL` (about 12 minutes).

    .venv\\Scripts\\python.exe scripts\\run_phase3.py

Order: data QA -> pseudo-out-of-sample and half-life choice -> models/flags -> history -> IRFs -> stability -> figures.
Nothing here contacts Macrobond; a different pull is used by changing `PHASE3_PULL` explicitly.
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_phase3_data  # noqa: E402
import run_phase3_figures  # noqa: E402
import run_phase3_history  # noqa: E402
import run_phase3_irfs  # noqa: E402
import run_phase3_models  # noqa: E402
import run_phase3_oos  # noqa: E402
import run_phase3_stability  # noqa: E402

if __name__ == "__main__":
    for mod in (run_phase3_data, run_phase3_oos, run_phase3_models, run_phase3_history, run_phase3_irfs, run_phase3_stability,
                run_phase3_figures):
        print("=" * 20, mod.__name__)
        mod.main()
