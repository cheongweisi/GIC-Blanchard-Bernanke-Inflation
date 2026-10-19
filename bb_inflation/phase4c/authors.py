"""Task 1: the authors' (Bernanke-Blanchard 2023) specification, samples and IRFs, replicated from their shipped files and compared with the paper's text.

Nothing is re-estimated on new data here: it uses the authors' data and coefficient files (validated in Phase 1) and the Phase 1 simulator.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import PRECOVID_END
from ..estimation.rls import estimate
from ..simulation.irf import irf, shock_sizes
from ..validation.authors_outputs import authors_model, authors_sim_data, read_core
from . import samples as S

IRF_FILES = {"Energy (relative price, 1 s.d.)": ("results_energy.xls", "grpe"), "Food (relative price, 1 s.d.)": ("results_food.xls", "grpf"),
             "Shortage index (1 s.d.)": ("results_shortage.xls", "shortage"), "V/U (1 s.d., permanent)": ("results_vu.xls", "vu")}
PAPER_SIZES = {"grpe": 32.0, "grpf": 3.2, "shortage": 11.6, "vu": 0.5}


def sample_confirmation() -> pd.DataFrame:
    """Estimation samples of the authors' hybrid design, from re-estimation on their data (reproduces their coefficient files to ~5e-6)."""
    ad = S.authors_data()
    hyb = S.fit_authors("hybrid", ad)
    full = S.fit_authors("full", ad)
    rows = []
    for eq, r in hyb.items():
        rows.append({"model": "hybrid (paper baseline)", "equation": eq, "sample": f"{r.sample[0]}-{r.sample[1]}", "N": r.nobs,
                     "pandemic-era observations used": "yes (through 2023Q2)" if eq == "gcpi" else "no (ends 2019Q4)"})
    for eq, r in full.items():
        rows.append({"model": "full sample (what the authors' IRF/decomposition code reads)", "equation": eq, "sample": f"{r.sample[0]}-{r.sample[1]}", "N": r.nobs,
                     "pandemic-era observations used": "yes (through 2023Q2)"})
    from ..extension.models import specs_for_end  # noqa: F401  (documentation only)
    from ..estimation.equations import base_equations
    p23q1 = estimate(base_equations(False)["gcpi"], ad, "1990Q1", "2023Q1")
    rows.append({"model": "price equation as in the paper's Table 3", "equation": "gcpi", "sample": f"{p23q1.sample[0]}-{p23q1.sample[1]}", "N": p23q1.nobs,
                 "pandemic-era observations used": "yes (through 2023Q1)"})
    return pd.DataFrame(rows)


def irf_replication(horizons=(0, 1, 2, 3, 4, 6, 8, 12, 16, 20, 27)) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(summary, paths, shock sizes, paper-text check)."""
    adata = authors_sim_data("full")
    resid = {k: adata[f"{k}_residuals"] for k in ("gw", "gcpi", "cf1", "cf10")}
    sizes = shock_sizes(adata, resid)
    full, hyb = authors_model("full"), authors_model("precovid")
    rows, paths = [], []
    for lab, (fname, var) in IRF_FILES.items():
        ref = read_core("IRFs", fname)
        f, h = irf(full, var, sizes[var]), irf(hyb, var, sizes[var])
        d_full = max(float(np.abs(f[c].values - ref[c].values).max()) for c in ("gw_simul", "gcpi_simul", "cf1_simul", "cf10_simul"))
        d_hyb = max(float(np.abs(h[c].values - ref[c].values).max()) for c in ("gw_simul", "gcpi_simul", "cf1_simul", "cf10_simul"))
        rows.append({"IRF": lab, "shock size (shipped data, 2020Q1-2023Q2 s.d.)": sizes[var], "size in paper footnote 15": PAPER_SIZES[var],
                     "max |our replication (full-sample coefficients) - shipped file|": d_full,
                     "max |hybrid coefficients - shipped file|": d_hyb})
        g = lambda df: df["gcpi_simul"].values[4:]                                   # noqa: E731
        for hh in horizons:
            paths.append({"IRF": lab, "h": hh, "shipped file": float(g(ref)[hh]), "replication (full-sample coefficients)": float(g(f)[hh]),
                          "hybrid coefficients (paper's stated baseline)": float(g(h)[hh])})
    summary = pd.DataFrame(rows)
    p = pd.DataFrame(paths)
    sz = pd.DataFrame([{"variable": k, "shipped-data s.d. 2020Q1-2023Q2": sizes[k], "paper footnote 15": PAPER_SIZES.get(k, np.nan)} for k in ("grpe", "grpf", "shortage", "vu")])
    vu_full, vu_hyb = irf(full, "vu", sizes["vu"])["gcpi_simul"].values[4:], irf(hyb, "vu", sizes["vu"])["gcpi_simul"].values[4:]
    vu_h5 = irf(hyb, "vu", 0.5)["gcpi_simul"].values[4:]
    en_full = irf(full, "grpe", sizes["grpe"])["gcpi_simul"].values[4:]
    slope = lambda g: float((g[27] - g[12]) / (15 / 4))                                # noqa: E731
    text = pd.DataFrame([
        {"claim in paper": "V/U IRF: inflation about 0.7 pp after 6 quarters", "paper": 0.7, "shipped file / full-sample coefficients": float(vu_full[6]),
         "hybrid coefficients, same shock": float(vu_hyb[6]), "hybrid coefficients, V/U +0.5": float(vu_h5[6])},
        {"claim in paper": "V/U IRF: about 1.0 pp after 12 quarters", "paper": 1.0, "shipped file / full-sample coefficients": float(vu_full[12]),
         "hybrid coefficients, same shock": float(vu_hyb[12]), "hybrid coefficients, V/U +0.5": float(vu_h5[12])},
        {"claim in paper": "V/U IRF: keeps rising about 0.15 pp per year thereafter", "paper": 0.15, "shipped file / full-sample coefficients": slope(vu_full),
         "hybrid coefficients, same shock": slope(vu_hyb), "hybrid coefficients, V/U +0.5": slope(vu_h5)},
        {"claim in paper": "Energy IRF: effects mostly gone the quarter after the shock (h=1 response relative to impact)", "paper": np.nan,
         "shipped file / full-sample coefficients": float(en_full[1] / en_full[0]), "hybrid coefficients, same shock": np.nan, "hybrid coefficients, V/U +0.5": np.nan},
        {"claim in paper": "Energy IRF: small sustained increase in inflation of about 0.1 pp (h=27)", "paper": 0.1, "shipped file / full-sample coefficients": float(en_full[27]),
         "hybrid coefficients, same shock": float(irf(hyb, "grpe", sizes["grpe"])["gcpi_simul"].values[4:][27]), "hybrid coefficients, V/U +0.5": np.nan},
    ])
    return summary, p, sz, text


def authors_multipliers() -> pd.DataFrame:
    """The paper's own derived quantities, recomputed from published sums (Tables 2-3) and from the shipped hybrid coefficients."""
    hyb = authors_model("precovid").coefs
    sg = lambda eq, var: float(sum(v for n, v in hyb[eq].items() if n.startswith(var + "_L")))        # noqa: E731
    rows = [
        {"quantity": "V/U 1.0 -> 1.5: long-run effect on wage growth, pp (paper: 0.5 x 0.693 / (1 - 0.460) = 0.64)", "paper": 0.5 * 0.693 / (1 - 0.460),
         "shipped hybrid coefficients": 0.5 * sg("gw", "vu") / (1 - sg("gw", "gw"))},
        {"quantity": "energy: long-run price-level effect (paper: 0.066 / (1 - 0.335) = 10%)", "paper": 100 * 0.066 / (1 - 0.335),
         "shipped hybrid coefficients": 100 * sg("gcpi", "grpe") / (1 - sg("gcpi", "gcpi"))},
        {"quantity": "food: long-run price-level effect (paper: 0.126 / (1 - 0.335) = 19%)", "paper": 100 * 0.126 / (1 - 0.335),
         "shipped hybrid coefficients": 100 * sg("gcpi", "grpf") / (1 - sg("gcpi", "gcpi"))},
    ]
    return pd.DataFrame(rows)


PRECOVID = PRECOVID_END
