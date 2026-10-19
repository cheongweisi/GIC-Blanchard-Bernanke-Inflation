"""Is the sample-to-sample movement in coefficients more than sampling noise? Four complementary checks (none of them changes any estimate).

1. post-2019 shift tests   one regressor per block lets that block's coefficients move by a common amount from 2020Q1 (offset inside the restriction
                           where the block is restricted), HAC t-test. Known break date, 16 (to 2023Q4) or 26 (to 2026Q2) post-break quarters.
2. recursive estimates     expanding-window block sums (window end 2019Q4 ... 2026Q2) with HAC bands: WHEN did an estimate move.
3. stable-parameter null   recursive-design moving-block bootstrap from the B*-2026 model: re-estimate all three vintages on pseudo-data generated with
                           CONSTANT parameters and see how large the vintage-to-vintage differences are by sampling variation alone.
4. leave-out check         re-estimate the supply-chain coefficient dropping each 16-quarter block (and starting in 1998): does one episode drive it?
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
from scipy import stats

from ..estimation.equations import Block
from ..estimation.inference import hac_cov
from ..estimation.rls import design, estimate
from ..extension.models import specs_for_end
from ..simulation.model import ENDO, LAGS, SimModel
from . import samples as S
from . import tables as T
from .study import Study

BREAK = "2020Q1"

# (equation, label, [(variable, lags, weight)], index of the target term, number of lags of the target block)
SHIFTS = [
    ("gcpi", "gw", [("gw", (0, 1, 2, 3, 4), 1.0), ("gcpi", (1, 2, 3, 4), -1.25)], 0, 5),
    ("gw", "gw", [("gw", (1, 2, 3, 4), 1.0), ("cf1", (1, 2, 3, 4), -1.0)], 0, 4),
    ("gw", "diffcpicf", [("diffcpicf", (1, 2, 3, 4), 1.0)], 0, 4),
    ("gw", "vu", [("vu", (1, 2, 3, 4), 1.0)], 0, 4),
    ("cf1", "gcpi", [("gcpi", (0, 1, 2, 3, 4), 1.0), ("cf1", (1, 2, 3, 4), -1.25)], 0, 5),
    ("cf10", "gcpi", [("gcpi", (0, 1, 2, 3, 4), 1.0), ("cf10", (1, 2, 3, 4), -1.25)], 0, 5),
    ("gcpi", "grpe", [("grpe", (0, 1, 2, 3, 4), 1.0)], 0, 5),
    ("gcpi", "grpf", [("grpf", (0, 1, 2, 3, 4), 1.0)], 0, 5),
    ("gcpi", "shortagema2", [("shortagema2", (0,), 1.0)], 0, 1),
]


def shift_tests(st: Study, ends=("2023Q4", "2026Q2")) -> pd.DataFrame:
    rows = []
    d = st.data.copy()
    post = pd.Series((d.index >= pd.Period(BREAK, "Q")).astype(float), index=d.index)
    for end in ends:
        for eq, blk, terms, _, nl in SHIFTS:
            z = pd.Series(0.0, index=d.index)
            for var, lags, w in terms:
                for k in lags:
                    z = z + w * d[var].shift(k)
            d2 = d.copy()
            d2["ZSHIFT"] = post * z
            spec = specs_for_end(S.VARIANT, end)[eq]
            spec2 = dataclasses.replace(spec, blocks=spec.blocks + (Block("ZSHIFT", (0,)),))
            r = estimate(spec2, d2, S.START, end)
            V = hac_cov(r, d2)
            delta = float(r.coef["ZSHIFT_L0"])
            se = float(np.sqrt(V.loc["ZSHIFT_L0", "ZSHIFT_L0"]))
            pre = float(sum(r.coef[n] for n in r.block_names(blk)))
            t = delta / se
            rows.append({"eq": eq, "block": blk, "label": T.LABEL[(eq, blk)], "sample end": end, "post-2019 quarters": int(post.loc[S.START:end].sum()),
                         "sum of block before 2020Q1": pre, "shift from 2020Q1 (block sum)": delta * nl, "se_hac": se * nl, "t": t,
                         "p": float(2 * stats.t.sf(abs(t), r.df_resid)), "implied sum from 2020Q1": pre + delta * nl})
    return pd.DataFrame(rows)


def recursive(st: Study, ends: list[str] | None = None) -> pd.DataFrame:
    ends = ends or [str(p) for p in pd.period_range("2019Q4", "2026Q2", freq="Q")]
    rows = []
    d = st.data
    for e in ends:
        eqs = specs_for_end(S.VARIANT, e)
        for eq, blocks in T.BLOCKS.items():
            r = estimate(eqs[eq], d, S.START, e)
            V = hac_cov(r, d)
            for b in blocks:
                names = r.block_names(b)
                w = np.array([1.0 if n in names else 0.0 for n in r.coef.index])
                s = float(w @ r.coef.values)
                se = float(np.sqrt(w @ V.values @ w))
                rows.append({"end": e, "eq": eq, "block": b, "sum": s, "se_hac": se, "N": r.nobs})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------------------
def _rls_masked(spec, data: pd.DataFrame, end: str, drop=None, start: str = S.START) -> pd.Series:
    X = design(spec, data)
    frame = pd.concat([data[spec.dep].rename("__y"), X], axis=1).loc[start:end].dropna()
    if drop is not None:
        frame = frame.loc[~frame.index.isin(drop)]
    yv, Xv = frame["__y"].values, frame.drop(columns="__y").values
    names = list(frame.columns[1:])
    A = np.linalg.pinv(Xv.T @ Xv)
    b = A @ Xv.T @ yv
    rn = spec.restriction_names()
    if rn:
        R = np.zeros((1, len(names)))
        for n in rn:
            R[0, names.index(n)] = 1.0
        b = b - A @ R.T @ np.linalg.inv(R @ A @ R.T) @ (R @ b - spec.restriction_value)
    return pd.Series(b, index=names)


def leave_out_gscpi(st: Study, end: str, block: int = 16) -> pd.DataFrame:
    """Supply-chain coefficient re-estimated dropping each `block`-quarter window; plus a sample starting 1998Q1 (no constant-filled GSCPI)."""
    spec = specs_for_end(S.VARIANT, end)["gcpi"]
    base = _rls_masked(spec, st.data, end)["shortagema2_L0"]
    idx = pd.period_range(S.START, end, freq="Q")[4:]
    rows = [{"variant": "full sample", "estimate": float(base), "N dropped": 0}]
    rows.append({"variant": "start 1998Q1 (drops constant-filled GSCPI)", "estimate": float(_rls_masked(spec, st.data, end, start="1998Q1")["shortagema2_L0"]),
                 "N dropped": int((idx < pd.Period("1998Q1", "Q")).sum())})
    for i in range(0, len(idx) - block + 1, block // 2):
        w = idx[i:i + block]
        rows.append({"variant": f"drop {w[0]}-{w[-1]}", "estimate": float(_rls_masked(spec, st.data, end, drop=list(w))["shortagema2_L0"]), "N dropped": block})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------------------
def null_bootstrap(st: Study, n: int = 500, block: int = 6, seed: int = 7) -> pd.DataFrame:
    """Vintage-to-vintage differences of every block sum under CONSTANT parameters (= the B*-2026 estimates).

    Pseudo-data: gw, gcpi, cf1, cf10 (and the catch-up term) simulated recursively from the 1990Q1 initial conditions, B*-2026 coefficients, exogenous
    variables and wage dummies as observed, residuals = moving blocks of the B*-2026 residuals drawn jointly across equations. Each replication re-estimates
    B19, B23, B26 and records block sums. Returns one row per replication, columns '<eq>:<block>:<vintage>'."""
    rng = np.random.default_rng(seed)
    d = st.data
    res26 = st.fits["B26"]
    sample = pd.period_range(S.START, "2026Q2", freq="Q")
    resid = pd.DataFrame({eq: res26[eq].resid.reindex(sample) for eq in S.EQS}).dropna()
    resid = resid - resid.mean()
    Tn = len(resid)
    base = SimModel.from_results(res26)
    pos0 = d.index.get_loc(sample[0])
    window = d.iloc[pos0 - LAGS: pos0 + Tn]
    exog = {v: window[v].values.astype(float) for v in ("grpe", "grpf", "vu", "magpty", "shortage", "shortagema2") if v in window}
    dummies = {x: window[x].values.astype(float) for x in ("D2020Q2", "D2020Q3")}
    hist = {k: window[k].values[:LAGS].astype(float) for k in ENDO}
    nblocks = int(np.ceil(Tn / block))
    specs = {v: specs_for_end(S.VARIANT, e) for v, e in (("B19", "2019Q4"), ("B23", "2023Q4"), ("B26", "2026Q2"))}
    ends = {"B19": "2019Q4", "B23": "2023Q4", "B26": "2026Q2"}
    out = []
    for _ in range(n):
        starts = rng.integers(0, Tn - block + 1, nblocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:Tn]
        e = resid.values[idx]
        shocks = {eq: np.concatenate([np.zeros(LAGS), e[:, j]]) for j, eq in enumerate(S.EQS)}
        sim = base.simulate(hist, exog, dummies=dummies, add_shocks=shocks)
        d2 = d.copy()
        for k in ENDO:
            d2.loc[window.index[LAGS:], k] = sim[k][LAGS:]
        row = {}
        try:
            for v in ("B19", "B23", "B26"):
                for eq, blocks in T.BLOCKS.items():
                    r = estimate(specs[v][eq], d2, S.START, ends[v])
                    for b in blocks:
                        row[f"{eq}:{b}:{v}"] = float(r.coef[r.block_names(b)].sum())
        except np.linalg.LinAlgError:
            continue
        out.append(row)
    return pd.DataFrame(out)


def null_summary(st: Study, boot: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for eq, blocks in T.BLOCKS.items():
        for b in blocks:
            for a, c in T.PAIRS:
                obs = st.block_point(eq, c, b) - st.block_point(eq, a, b)
                dstar = boot[f"{eq}:{b}:{c}"] - boot[f"{eq}:{b}:{a}"]
                bias = float(dstar.mean())
                cen = dstar - bias
                rows.append({"eq": eq, "block": b, "label": T.LABEL[(eq, b)], "from": T.vlabel(a), "to": T.vlabel(c), "observed change": obs,
                             "null mean (finite-sample bias)": bias, "null s.d.": float(dstar.std()), "null 5%": float(cen.quantile(.05)), "null 95%": float(cen.quantile(.95)),
                             "p (observed vs null, bias-centred)": float((cen.abs() >= abs(obs)).mean()), "replications": len(dstar)})
    return pd.DataFrame(rows)


def price_spec_robustness(st: Study, variants=("gscpi_ma2", "gscpi5", "none")) -> pd.DataFrame:
    """Does the movement of the price-equation coefficients across samples depend on how supply-chain pressure enters the equation?
    Price equation only (the other three equations do not contain it), B*-2019 / -2023 / -2026 ends, shortage block = B* (2-quarter GSCPI mean), 5 lags of GSCPI
    (the authors' Table A8 style) or no supply-chain term at all. Overlap-adjusted HAC tests of the 2019 -> 2026 change."""
    from ..validation.specs import VARIANTS, equations_for
    from . import stack as K
    rows = []
    d = st.data
    d = d.copy()
    for v in variants:
        spec = equations_for(VARIANTS[v], covid_dummies=False)["gcpi"]
        fits = {k: estimate(spec, d, S.START, e) for k, e in (("B19", "2019Q4"), ("B23", "2023Q4"), ("B26", "2026Q2"))}
        stk = K.stack("gcpi", fits, d)
        blocks = ["gw", "gcpi", "grpe", "grpf"] + ([VARIANTS[v].block.var] if VARIANTS[v].block else [])
        for b in blocks:
            c = stk.selector(b)
            ch = stk.change_test("B19", "B26", c)
            for k in ("B19", "B23", "B26"):
                est, se = stk.combo({k: c})
                rows.append({"shortage specification": VARIANTS[v].label, "block": b, "vintage": S.LABEL[k], "sum": est, "se_hac": se, "t": est / se})
            rows.append({"shortage specification": VARIANTS[v].label, "block": b, "vintage": "change B*-2019 -> B*-2026", "sum": ch["change"], "se_hac": ch["se"],
                         "t": ch["t"], "p": ch["p"]})
    return pd.DataFrame(rows)
