"""Run the shock catalogue for every vintage and both energy/food conventions; summary statistics with parameter bands; vintage-to-vintage differences.

Bands are 90% (5th-95th percentile) over joint coefficient draws (`study.Study.draws`), so the vintages' draws share the overlap of their samples and
a difference of two vintages' statistics has its own, honest, band. They reflect parameter (sampling) uncertainty in the four estimated equations only:
not specification uncertainty, not residual shocks, not uncertainty in the calibrated oil bridge, not future-driver uncertainty.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..scenarios import engine as E
from ..simulation.model import SimModel
from ..validation.authors_outputs import authors_model
from . import irf as I
from . import samples as S
from .study import Study

QS = (0.05, 0.16, 0.5, 0.84, 0.95)
VINTS = ("B19", "B23", "B26", "HYB")
DIFFS = (("B19", "B23"), ("B23", "B26"), ("B19", "B26"))


@dataclass
class Results:
    shocks: dict[str, I.Shock]
    paths: pd.DataFrame            # long: convention, shock, vintage, variable, h, point, q05, q16, q50, q84, q95
    stats: pd.DataFrame            # convention, shock, vintage, variable, statistic, point, lo90, hi90
    diffs: pd.DataFrame            # convention, shock, change, variable, statistic, difference, lo90, hi90, p
    path_diffs: pd.DataFrame       # long: difference of paths between vintages
    notes: list[str] = field(default_factory=list)


def gscpi_sd(data: pd.DataFrame, a: str = "1998Q1", b: str = "2026Q2") -> float:
    return float(data["shortage"].loc[a:b].std(ddof=1))


def authors_coefset() -> E.CoefSet:
    return E.CoefSet.from_models([SimModel(authors_model("precovid").coefs)])


def _add_level(path: dict) -> dict:
    out = dict(path)
    out["plevel"] = I.price_level(path["gcpi"])
    return out


def run_all(st: Study, conventions=("nominal", "relative"), bridge_end: str = "2026-06") -> Results:
    sd = gscpi_sd(st.data)
    shocks = I.shock_catalogue(sd)
    b = I.bridge(bridge_end).coef.values[1:]
    p_rows, s_rows, d_rows, pd_rows = [], [], [], []
    auth = authors_coefset()
    for conv in conventions:
        for key, sh in shocks.items():
            if sh.family == "oil" and conv == "relative":
                continue
            raw = {}
            for vk in VINTS:
                pt = I.run(st.coefset(vk, point=True), sh, conv, b)
                dr = I.run(st.coefset(vk), sh, conv, b)
                raw[vk] = (pt, dr)
            vsigns = I.point_signs(raw["B26"][0])
            stat_draws, point_stats = {}, {}
            for vk in VINTS:
                pt, dr = raw[vk]
                sp, sdr = I.statistics(pt, vsigns), I.statistics(dr, vsigns)
                stat_draws[vk], point_stats[vk] = sdr, sp
                for (v, name), arr in sdr.items():
                    s_rows.append({"convention": conv, "shock": key, "vintage": S.LABEL[vk], "variable": v, "statistic": name,
                                   "point": float(sp[(v, name)][0]), "lo90": float(np.nanquantile(arr, .05)), "hi90": float(np.nanquantile(arr, .95)),
                                   "share of draws with statistic undefined": float(np.isnan(arr).mean())})
                pa, da = _add_level(pt), _add_level(dr)
                for v in (*I.VARS, "plevel"):
                    q = np.quantile(da[v], QS, axis=0)
                    for h in range(I.HREP + 1):
                        p_rows.append({"convention": conv, "shock": key, "vintage": S.LABEL[vk], "variable": v, "h": h, "point": float(pa[v][0, h]),
                                       **{f"q{int(x * 100):02d}": float(q[i, h]) for i, x in enumerate(QS)}})
            for a, c in DIFFS:
                for (v, name), arr_c in stat_draws[c].items():
                    arr_a = stat_draws[a][(v, name)]
                    d = arr_c - arr_a
                    ok = ~np.isnan(d)
                    if ok.sum() < 20:
                        continue
                    pt_d = float(point_stats[c][(v, name)][0] - point_stats[a][(v, name)][0])
                    d_rows.append({"convention": conv, "shock": key, "change": f"{S.LABEL[a]} -> {S.LABEL[c]}", "variable": v, "statistic": name,
                                   "difference": pt_d, "lo90": float(np.quantile(d[ok], .05)), "hi90": float(np.quantile(d[ok], .95)),
                                   "p (two-sided, from draws)": float(min(1.0, 2 * min((d[ok] >= 0).mean(), (d[ok] <= 0).mean())))})
                pa_c, pa_a = _add_level(raw[c][1]), _add_level(raw[a][1])
                pp_c, pp_a = _add_level(raw[c][0]), _add_level(raw[a][0])
                for v in (*I.VARS, "plevel"):
                    dd = pa_c[v][:, :I.HREP + 1] - pa_a[v][:, :I.HREP + 1]
                    q = np.quantile(dd, QS, axis=0)
                    for h in range(I.HREP + 1):
                        pd_rows.append({"convention": conv, "shock": key, "change": f"{S.LABEL[a]} -> {S.LABEL[c]}", "variable": v, "h": h,
                                        "difference": float(pp_c[v][0, h] - pp_a[v][0, h]), **{f"q{int(x * 100):02d}": float(q[i, h]) for i, x in enumerate(QS)}})
            # authors' published hybrid model: point path only, where the shock is comparable (not GSCPI: Google 'shortage' is a different variable)
            if sh.family != "supply":
                pt = _add_level(I.run(auth, sh, conv, b))
                for v in (*I.VARS, "plevel"):
                    for h in range(I.HREP + 1):
                        p_rows.append({"convention": conv, "shock": key, "vintage": S.LABEL["AUTH"], "variable": v, "h": h, "point": float(pt[v][0, h])})
                sp = I.statistics(pt, vsigns)
                for (v, name), arr in sp.items():
                    s_rows.append({"convention": conv, "shock": key, "vintage": S.LABEL["AUTH"], "variable": v, "statistic": name, "point": float(arr[0])})
    return Results(shocks, pd.DataFrame(p_rows), pd.DataFrame(s_rows), pd.DataFrame(d_rows), pd.DataFrame(pd_rows))


def oil_bridge_sensitivity(st: Study) -> pd.DataFrame:
    """+10% sustained Brent under (a) the common Phase 4 bridge, (b) a bridge re-estimated through each vintage's own sample end, (c) the 0.24-0.40 elasticity range."""
    sh = I.shock_catalogue(1.0)["O10"]
    rows = []
    for vk, end in (("B19", "2019-12"), ("B23", "2023-12"), ("B26", "2026-06")):
        cs = st.coefset(vk, point=True)
        for lab, bridge in (("common Phase 4 bridge (to 2026-06)", I.bridge("2026-06")), (f"bridge re-estimated to {end}", I.bridge(end))):
            bb = bridge.coef.values[1:]
            p = I.run(cs, sh, "nominal", bb)
            L = I.price_level(p["gcpi"])
            rows.append({"vintage": S.LABEL[vk], "bridge": lab, "bridge elasticity (sum of lags)": float(bb.sum()),
                         "CPI inflation h=0 (pp)": float(p["gcpi"][0, 0]), "CPI inflation h=4": float(p["gcpi"][0, 4]),
                         "price level after 4q (%)": float(L[0, 4]), "price level after 12q (%)": float(L[0, 12]),
                         "price level per 1% of energy-price rise, 12q": float(L[0, 12] / (bb.sum() * 100 * np.log(1.1)))})
        for el in (0.24, 0.40):
            bb = I.bridge("2026-06").coef.values[1:] * el / I.bridge("2026-06").elasticity
            p = I.run(cs, sh, "nominal", bb)
            L = I.price_level(p["gcpi"])
            rows.append({"vintage": S.LABEL[vk], "bridge": f"calibrated elasticity {el:.2f} (Phase 4 standard range)", "bridge elasticity (sum of lags)": float(bb.sum()),
                         "CPI inflation h=0 (pp)": float(p["gcpi"][0, 0]), "CPI inflation h=4": float(p["gcpi"][0, 4]),
                         "price level after 4q (%)": float(L[0, 4]), "price level after 12q (%)": float(L[0, 12]),
                         "price level per 1% of energy-price rise, 12q": float(L[0, 12] / (bb.sum() * 100 * np.log(1.1)))})
    return pd.DataFrame(rows)


def persistence_table(st: Study, shocks=("W1", "V1P", "G1", "O10T", "E1", "E10", "P1", "V1", "W2", "O10", "G1S")) -> pd.DataFrame:
    """Persistence of the CPI response in year-on-year terms (4-quarter trailing mean of the annualised response), horizon 40 quarters, with 90% bands.

    peak y/y (h<=12); y/y at h=12, 24, 40 as % of the peak; half-life of the y/y response after its peak (NaN: not reached by h=40, i.e. still above half).
    Impulses are one-period shocks; 'sustained' shocks keep the driver at its new level, so a response that does not decay is mechanical there."""
    sd = gscpi_sd(st.data)
    cat = I.shock_catalogue(sd)
    b = I.bridge().coef.values[1:]
    rows = []
    for key in shocks:
        for vk in ("B19", "B23", "B26"):
            for lab, cs in (("point", st.coefset(vk, point=True)), ("draws", st.coefset(vk))):
                g = I.run(cs, cat[key], "nominal", b)["gcpi"]
                y = np.stack([g[:, max(0, h - 3):h + 1].sum(axis=1) / 4 for h in range(g.shape[1])], axis=1)
                sign = float(np.sign(y[0, :13][np.abs(y[0, :13]).argmax()])) or 1.0
                pk = (y[:, :13] * sign).max(axis=1) * sign
                kk = (y[:, :13] * sign).argmax(axis=1)
                hl = I.half_life(y, kk.astype(float), pk)
                st_ = {"peak y/y (h<=12), pp": pk, "quarter of peak": kk.astype(float), "y/y at h=12, % of peak": 100 * y[:, 12] / pk,
                       "y/y at h=24, % of peak": 100 * y[:, 24] / pk, "y/y at h=40, % of peak": 100 * y[:, 40] / pk, "half-life after peak (q)": hl}
                if lab == "point":
                    pts = st_
                else:
                    for name, arr in st_.items():
                        rows.append({"shock": key, "type": cat[key].kind, "vintage": S.LABEL[vk], "statistic": name, "point": float(pts[name][0]),
                                     "lo90": float(np.nanquantile(arr, .05)), "hi90": float(np.nanquantile(arr, .95))})
    return pd.DataFrame(rows)
