"""Specification tests for the shortage block of the price equation (authors' Google 5-lag vs GSCPI variants).

For each variant the price equation is estimated twice: through 2019Q4 ('pre'), a genuine pre-COVID estimate,
and through 2023Q2 ('full'), the authors' design. Inference uses Newey-West (HAC) covariances. Selection is
never based on in-sample R2: R2, AIC and BIC are reported only as descriptions; the evidence used is
out-of-sample fit (oos.py), coefficient stability, economic plausibility and the dynamics (IRF, decomposition).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..estimation.inference import irf_bands_mc, recursive_sums, with_hac
from ..simulation.general import decompose_general, irf_general
from ..simulation.irf import shock_sizes
from ..simulation.model import SimModel
from . import oos
from .specs import Variant, equations_for

REC_ENDS = ["2019Q4", "2020Q4", "2021Q4", "2022Q4", "2023Q2"]
IRF_H = (0, 1, 2, 4, 8, 12, 27)


def block_table(v: Variant, res_price, data: pd.DataFrame, L: int = 4) -> pd.DataFrame:
    hac = with_hac(res_price, data, L)
    names = v.block.names()
    t = pd.DataFrame({"coef": res_price.coef[names], "se_classic": np.sqrt(np.diag(res_price.cov))[[list(res_price.coef.index).index(n) for n in names]],
                      "se_hac": np.sqrt(np.diag(hac.cov))[[list(res_price.coef.index).index(n) for n in names]]})
    t["t_classic"] = t.coef / t.se_classic
    t["t_hac"] = t.coef / t.se_hac
    return t


def equal_weights_p(res_hac, names: list[str]) -> float:
    """HAC F-test that the two shortage lag coefficients are equal (justifies a two-quarter moving average)."""
    R = np.zeros((1, len(res_hac.coef)))
    idx = [list(res_hac.coef.index).index(n) for n in names]
    R[0, idx[0]], R[0, idx[1]] = 1.0, -1.0
    return res_hac._f_test(R, np.zeros(1))


def implied_lag_weights(v: Variant, coefs: pd.Series, n: int = 5) -> np.ndarray:
    """Coefficients on the raw shortage index at lags 0..n-1 implied by the specification."""
    w = np.zeros(n)
    if v.block is None:
        return w
    if v.derived:
        (_, (_, win)), = v.derived
        w[:win] = coefs[v.block.names()[0]] / win
    else:
        for k in v.block.lags:
            w[k] = coefs[f"{v.block.var}_L{k}"]
    return w


def flags(v: Variant, tab: pd.DataFrame, s_pre: float, s_full: float) -> list[str]:
    """Rule-based warnings about economically implausible or unstable shortage patterns (full-sample estimate)."""
    out = []
    c = tab.coef.values
    if c.sum() <= 0:
        out.append("negative sum")
    if c[0] < 0:
        out.append("negative contemporaneous effect")
    neg_sig = [n for n, (b, t) in zip(tab.index, zip(tab.coef, tab.t_hac)) if b < 0 and t <= -1.65]
    if neg_sig:
        out.append("significantly negative lag(s): " + ",".join(n.split("_")[-1] for n in neg_sig))
    if len(c) >= 3:
        signs = np.sign(c)
        changes = int((signs[1:] != signs[:-1]).sum())
        if changes >= 2 and c.min() < -0.5 * c.max():
            out.append(f"sign alternation ({changes} changes)")
    if np.sign(s_pre) != np.sign(s_full) or abs(s_full - s_pre) > 0.5 * max(abs(s_full), abs(s_pre)):
        out.append(f"unstable sum (pre {s_pre:.2f} vs full {s_full:.2f})")
    return out


def ic(res) -> dict:
    n = res.nobs
    k = len(res.coef) - 1
    rss = float(res.resid @ res.resid)
    ll = n * np.log(rss / n)
    return {"AIC": ll + 2 * k, "BIC": ll + k * np.log(n), "adjR2 (not used for selection)":
            1 - (1 - res.r2_corr) * (n - 1) / (n - k - 1)}


def analyse(v: Variant, data: pd.DataFrame, n_mc: int = 1000, seed: int = 0) -> dict:
    full = oos.fit_regime(v, data, "insample")
    pre = oos.fit_regime(v, data, "genuine")
    out = {"variant": v, "data": data, "full": full, "pre": pre}
    if v.block is None:
        return out
    t_full, t_pre = block_table(v, full["gcpi"], data), block_table(v, pre["gcpi"], data)
    out["table_full"], out["table_pre"] = t_full, t_pre
    hf, hp = with_hac(full["gcpi"], data).summary(), with_hac(pre["gcpi"], data).summary()
    out["sum_full"], out["sum_pre"] = float(t_full.coef.sum()), float(t_pre.coef.sum())
    # a one-coefficient block has no separate "sum" test: the sum test equals the joint (t) test
    ps = lambda h: h.loc[v.block.var, "p_joint"] if np.isnan(h.loc[v.block.var, "p_sum"]) else h.loc[v.block.var, "p_sum"]  # noqa: E731
    out["p_sum_full"], out["p_joint_full"] = ps(hf), hf.loc[v.block.var, "p_joint"]
    out["p_sum_pre"], out["p_joint_pre"] = ps(hp), hp.loc[v.block.var, "p_joint"]
    if len(v.block.lags) == 2:
        out["equal_weights_p_full"] = equal_weights_p(with_hac(full["gcpi"], data), v.block.names())
        out["equal_weights_p_pre"] = equal_weights_p(with_hac(pre["gcpi"], data), v.block.names())
    out["flags_full"] = flags(v, t_full, out["sum_pre"], out["sum_full"])
    out["flags_pre"] = flags(v, t_pre, out["sum_pre"], out["sum_full"])
    out["ic_full"] = ic(full["gcpi"])
    spec = equations_for(v, False)["gcpi"]
    out["recursive"] = recursive_sums(spec, data, {"sum": v.block.names()}, REC_ENDS)["sum"]
    # impulse responses to a +1 s.d. shortage shock (s.d. of the raw index since 2020Q1), with HAC MC bands
    derived = v.derived_dict
    resid = {k: full[k].resid for k in ("gw", "gcpi", "cf1", "cf10")}
    size = shock_sizes(data, resid)["shortage"]
    out["shock_size"] = size
    fn = lambda m, s, z: irf_general(m, s, z, derived=derived)       # noqa: E731
    out["irf_full"] = fn(SimModel.from_results(full), "shortage", size)["gcpi_simul"].values
    out["irf_pre"] = fn(SimModel.from_results(pre), "shortage", size)["gcpi_simul"].values
    hac_full = {k: with_hac(r, data) for k, r in full.items()}
    out["irf_band_full"] = irf_bands_mc(hac_full, fn, {"shortage": size}, n=n_mc, seed=seed)["shortage"]
    # decomposition of CPI inflation (estimates through 2023Q2 and through 2019Q4)
    for tag, res in (("full", full), ("pre", pre)):
        dec = decompose_general(SimModel.from_results(res), data, derived, steady={"shortage": v.steady_shortage})
        out[f"dec_{tag}"] = dec
    return out


def summary_row(a: dict) -> dict:
    v = a["variant"]
    row = {"spec": v.name, "label": v.label}
    if v.block is None:
        return row
    row.update({"shortage sum (pre-2020 est.)": a["sum_pre"], "p_sum HAC (pre)": a["p_sum_pre"],
                "p_joint HAC (pre)": a["p_joint_pre"], "shortage sum (full est.)": a["sum_full"],
                "p_sum HAC (full)": a["p_sum_full"], "p_joint HAC (full)": a["p_joint_full"],
                "flags (full)": "; ".join(a["flags_full"]) or "none", "flags (pre)": "; ".join(a["flags_pre"]) or "none",
                "AIC (full)": a["ic_full"]["AIC"], "BIC (full)": a["ic_full"]["BIC"]})
    for h in IRF_H:
        row[f"IRF h{h}"] = float(a["irf_full"][4 + h])
    irf = a["irf_full"][4:]
    row["IRF peak"] = float(irf[np.argmax(np.abs(irf))])
    row["IRF cum 0-8"] = float(irf[:9].sum())
    b = a["irf_band_full"]
    row["share of h0-8 where 90% band excludes 0"] = float(((b["q05"][4:13] > 0) | (b["q95"][4:13] < 0)).mean())
    d = a["dec_full"]
    idx = d.index
    for per in ("2021Q2", "2022Q2"):
        row[f"decomp shortage {per} (full est.)"] = float(d.contributions["shortage"]["gcpi"].iloc[idx.get_loc(pd.Period(per, 'Q'))])
    sel = (idx >= pd.Period("2021Q1")) & (idx <= pd.Period("2022Q4"))
    row["decomp shortage avg 2021-22 (full est.)"] = float(d.contributions["shortage"]["gcpi"][sel].mean())
    dp = a["dec_pre"]
    row["decomp shortage avg 2021-22 (pre est.)"] = float(dp.contributions["shortage"]["gcpi"][sel].mean())
    act = a["data"]["gcpi"].reindex(idx)
    win = idx >= pd.Period("2020Q1")
    row["decomp baseline RMSE (full est.)"] = float(np.sqrt(((d.baseline["gcpi"] - act)[win] ** 2).mean()))
    row["decomp baseline RMSE (pre est.)"] = float(np.sqrt(((dp.baseline["gcpi"] - act)[win] ** 2).mean()))
    return row
