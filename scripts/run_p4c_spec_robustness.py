"""Phase 4c supplement: do the price-equation changes across samples depend on the supply-chain specification? Writes outputs/phase4c/robust_price_spec.csv."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from bb_inflation.phase4c import samples as S  # noqa: E402
from bb_inflation.phase4c import stability as SB  # noqa: E402
from bb_inflation.phase4c import study as ST  # noqa: E402

st = ST.build(n=50)
df = SB.price_spec_robustness(st)
df.to_csv(S.OUT / "robust_price_spec.csv", index=False)
pd.set_option("display.width", 220)
print(df.round(3).to_string())
