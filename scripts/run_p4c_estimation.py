"""Phase 4c, Tasks 1-3: authors' specification and IRFs, re-estimation on three historical samples, identification, coefficient comparison and stability.

Writes only to outputs/phase4c/. Phase 1-4b code and outputs and the production B* coefficients are untouched (tests/test_phase4c.py checks the hash manifest)."""
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.phase4c import authors as AU  # noqa: E402
from bb_inflation.phase4c import ident as ID  # noqa: E402
from bb_inflation.phase4c import samples as S  # noqa: E402
from bb_inflation.phase4c import stability as SB  # noqa: E402
from bb_inflation.phase4c import study as ST  # noqa: E402
from bb_inflation.phase4c import tables as T  # noqa: E402

OUT = S.OUT
N_BOOT = 1000


def save(df, name, index=False):
    df.to_csv(OUT / name, index=index)
    print(f"  {name}: {df.shape}")


t0 = time.time()
print("Task 1: authors")
save(AU.sample_confirmation(), "authors_samples.csv")
summ, paths, sizes, text = AU.irf_replication()
save(summ, "authors_irf_replication.csv")
save(paths, "authors_irf_paths.csv")
save(sizes, "authors_irf_shock_sizes.csv")
save(text, "authors_irf_paper_text_check.csv")
save(AU.authors_multipliers(), "authors_multipliers.csv")
save(T.authors_published(), "authors_published_summary_stats.csv")

print("Tasks 2-3: estimation")
st = ST.build()
for n in st.notes:
    print("  ", n)
save(T.estimation_checks(st), "est_checks.csv")
for eq in S.EQS:
    save(T.coef_table(st, eq, auth_hyb=True).reset_index(names="coefficient"), f"coef_{eq}.csv")
bt = T.block_table(st, None)
save(bt, "blocks.csv")
ch = T.change_table(st)
save(ch, "block_changes.csv")
save(T.derived_table(st), "multipliers_derived.csv")
flags = ID.block_flags(bt, S.LABEL)
save(flags, "ident_blocks.csv")

print("identification of the supply-chain coefficient")
W = {"1990Q1-1997Q4 (constant-filled GSCPI)": ("1990Q1", "1997Q4"), "1998Q1-2019Q4": ("1998Q1", "2019Q4"), "2008Q3-2009Q4 (global financial crisis)": ("2008Q3", "2009Q4"),
     "2020Q1-2023Q4": ("2020Q1", "2023Q4"), "2024Q1-2026Q2": ("2024Q1", "2026Q2")}
rows = []
for vk in S.MAIN:
    o = ID.coefficient_identification(st.fits[vk]["gcpi"], st.data, "shortagema2_L0", W)
    r = st.hacs[vk]["gcpi"]
    est = float(r.coef["shortagema2_L0"])
    se = float(np.sqrt(r.cov.loc["shortagema2_L0", "shortagema2_L0"]))
    rows.append({"vintage": S.LABEL[vk], "estimate": est, "HAC s.e.": se, "t (HAC)": est / se, "min detectable effect, 80% power (2.8 x s.e.)": 2.8 * se,
                 "GSCPI range in sample (min)": float(st.data["shortage"].loc[st.fits[vk]["gcpi"].resid.index].min()),
                 "GSCPI range in sample (max)": float(st.data["shortage"].loc[st.fits[vk]["gcpi"].resid.index].max()), **o})
save(pd.DataFrame(rows), "ident_gscpi.csv")
lo19 = SB.leave_out_gscpi(st, "2019Q4")
lo26 = SB.leave_out_gscpi(st, "2026Q2")
save(lo19.assign(vintage=S.LABEL["B19"]).pipe(lambda d: pd.concat([d, lo26.assign(vintage=S.LABEL["B26"])])), "ident_gscpi_leave_out.csv")

print("stability: shift tests, recursive estimates")
save(SB.shift_tests(st), "stability_shift_tests.csv")
save(SB.recursive(st), "stability_recursive.csv")
print(f"stability: stable-parameter null bootstrap ({N_BOOT} replications)")
boot = SB.null_bootstrap(st, n=N_BOOT)
save(boot, "stability_null_bootstrap_draws.csv")
ns = SB.null_summary(st, boot)
save(ns, "block_changes_null_bootstrap.csv")
print(f"done in {time.time() - t0:.0f}s")
