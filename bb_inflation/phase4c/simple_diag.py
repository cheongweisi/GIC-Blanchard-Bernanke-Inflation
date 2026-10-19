"""Diagnostics behind the clarifications in docs/phase4c_simple.md. Nothing here changes B*, the Phase 4c outputs or the simplified headline numbers.

Variant price equations (food lags 0-3, 0-2, observation dropped) are DIAGNOSTIC fits used only to see whether a feature of the B* food response is robust; they are not alternative models.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
from scipy import stats

from ..estimation.equations import Block
from ..estimation.rls import estimate
from ..extension.models import specs_for_end
from ..scenarios import engine as E
from ..simulation.model import SimModel
from . import irf as I
from . import samples as S
from . import simple as SM
from . import stability as SB
from .study import Study

BASKET_SHARE = {"energy": 7.4, "food": 14.4}      # % of the CPI basket as quoted by Bernanke-Blanchard (2023, p.25); not recomputed here
LOG10 = 100 * np.log(1.1)


def definitions_detailed(st: Study, sd: float) -> pd.DataFrame:
    b = I.bridge()
    bc = b.coef.values[1:]
    g = I.oil_energy_growth(bc, 10.0, "sustained", 4)
    lvl = 100 * (np.exp(np.cumsum(g) / 400) - 1)          # CPI-energy level change in %, from annualised growth (400 dln)
    cs = st.coefset("B26", point=True)
    w = I.run(cs, I.shock_catalogue(sd)["W1"], "nominal", bc)
    wlev = np.cumsum(w["gw"][0, :SM.NQ]) / 4
    return pd.DataFrame([
        {"shock": "Energy", "what is shocked": "Brent crude price level (USD)", "size": "+10% = +9.53 log points", "duration": "permanent: level stays 10% higher from the first month of Q0",
         "model input (units)": f"nominal CPI-energy growth, annualised pp, via the calibrated oil bridge (elasticity {b.elasticity:.3f}): +{g[0]:.1f} in Q0, +{g[1]:.1f} in Q1, ~0 after",
         "implied change in the shocked CPI component": f"CPI energy level +{lvl[0]:.1f}% by end-Q0, +{lvl[1]:.1f}% from Q1 on (not +10%)"},
        {"shock": "Food", "what is shocked": "CPI food price level (index, SA)", "size": "+10% = +9.53 log points", "duration": "permanent: one jump in Q0, no further change",
         "model input (units)": f"nominal CPI-food growth, annualised pp: +{4 * LOG10:.1f} in Q0 (= 400 x ln 1.1), 0 afterwards",
         "implied change in the shocked CPI component": "CPI food level +10.0% from Q0 on"},
        {"shock": "Wages", "what is shocked": "residual of the wage equation (ECI wages)", "size": "+1pp of annualised wage growth", "duration": "one quarter (Q0); wage growth afterwards is determined by the model",
         "model input (units)": "additive shock to the wage equation in Q0, annualised pp",
         "implied change in the shocked CPI component": f"ECI wage level +0.25% in Q0; wage growth responds +{w['gw'][0, 1]:.2f}pp in Q1 and fades; wage level +{wlev[-1]:.2f}% after 12 quarters"},
        {"shock": "Supply chains", "what is shocked": "NY Fed GSCPI (standard-deviation units)", "size": f"+1 s.d. = +{sd:.3f} (1998Q1-2026Q2)", "duration": "one quarter (Q0)",
         "model input (units)": f"GSCPI +{sd:.3f} in Q0; the price equation uses the 2-quarter mean, so +{sd / 2:.3f} in Q0 and Q1",
         "implied change in the shocked CPI component": "none: an index of pressure, not a price"}])


# ---------------------------------------------------------------------------------------------------------------------------------
def _coefset_with_price_eq(st: Study, coef: pd.Series) -> E.CoefSet:
    cd = {eq: pd.Series(stk.beta["B26"], index=stk.cols) for eq, stk in st.stacks.items()}
    cd["gcpi"] = coef
    return E.CoefSet.from_models([SimModel(cd)])


def food_lag_table(st: Study) -> pd.DataFrame:
    rows = []
    for vk in ("B19", "B23", "B26"):
        r = st.hacs[vk]["gcpi"]
        se = pd.Series(np.sqrt(np.diag(r.cov.values)), index=r.coef.index)
        row = {"sample": S.LABEL[vk]}
        for k in range(5):
            n = f"grpf_L{k}"
            row[f"L{k}"] = f"{r.coef[n]:+.3f} ({se[n]:.3f})"
        row["sum"] = f"{sum(r.coef[f'grpf_L{k}'] for k in range(5)):+.3f}"
        rows.append(row)
    return pd.DataFrame(rows)


def food_lag_tests(st: Study) -> dict:
    r = st.hacs["B26"]["gcpi"]
    out = {}
    for lab, names in (("L4 = 0", ["grpf_L4"]), ("L3 = L4 = 0", ["grpf_L3", "grpf_L4"]), ("L2 = L3 = L4 = 0", ["grpf_L2", "grpf_L3", "grpf_L4"])):
        idx = [list(r.coef.index).index(n) for n in names]
        R = np.zeros((len(idx), len(r.coef)))
        for i, j in enumerate(idx):
            R[i, j] = 1
        d = R @ r.coef.values
        F = float(d @ np.linalg.solve(R @ r.cov.values @ R.T, d)) / len(idx)
        out[lab] = float(stats.f.sf(F, len(idx), r.df_resid))
    return out


def food_variants(st: Study, sd: float) -> pd.DataFrame:
    """Does the Q4 echo of the food response survive small changes to the food lag structure or to the sample? (diagnostic fits of the price equation, B*-2026 sample)"""
    b = I.bridge().coef.values[1:]
    spec = specs_for_end(S.VARIANT, "2026Q2")["gcpi"]
    d = st.data
    P = lambda a, c: list(pd.period_range(a, c, freq="Q"))            # noqa: E731
    cases = [("B*-2026 as estimated (food lags 0-4)", None, None), ("food lags 0-3", (0, 1, 2, 3), None), ("food lags 0-2", (0, 1, 2), None),
             ("B*-2026 without the 2021Q2 observation", None, P("2021Q2", "2021Q2")), ("B*-2026 without 2021Q1-Q2", None, P("2021Q1", "2021Q2")),
             ("B*-2026 without 2022Q1-Q4", None, P("2022Q1", "2022Q4"))]
    rows = []
    for lab, lags, drop in cases:
        sp = spec
        if lags is not None:
            sp = dataclasses.replace(spec, blocks=tuple(Block("grpf", lags) if bl.var == "grpf" else bl for bl in spec.blocks))
        c = SB._rls_masked(sp, d, "2026Q2", drop=drop)
        cs = _coefset_with_price_eq(st, c)
        path = SM.responses(cs, "food", b, sd)
        m = SM.metrics(path)
        gl = {k: float(c[f"grpf_L{k}"]) if f"grpf_L{k}" in c.index else np.nan for k in range(5)}
        rows.append({"price equation": lab, "food L3": gl[3], "food L4": gl[4], "sum of food lags": float(sum(v for v in gl.values() if not np.isnan(v))),
                     "response Q3 (pp)": float(path[0, 3]), "response Q4 (pp)": float(path[0, 4]), "Q4 as % of Q0": float(100 * path[0, 4] / path[0, 0]),
                     "rebound above half-peak?": "yes" if m[SM.REBOUND][0] == 1 else "no", "price level after 12 quarters (%)": float(path.sum() / 4)})
    return pd.DataFrame(rows)


def food_decomposition(st: Study, sd: float) -> pd.DataFrame:
    b = I.bridge().coef.values[1:]
    cs = st.coefset("B26", point=True)
    path = SM.responses(cs, "food", b, sd)[0]
    direct = np.array([float(cs.get("gcpi", f"grpf_L{k}")[0]) * 4 * LOG10 if k < 5 else 0.0 for k in range(SM.NQ)])
    return pd.DataFrame({"quarter": range(SM.NQ), "direct food-coefficient term (L_k x 38.1)": direct, "total CPI response": path, "feedback through wages, expectations and lagged CPI": path - direct})


def food_episode(st: Study) -> pd.DataFrame:
    x = st.data.loc["2020Q1":"2021Q4", ["grpf", "gw", "gcpi"]].copy()
    x["nominal food growth"] = x.grpf + x.gw
    return x.rename(columns={"grpf": "relative food growth", "gw": "wage growth", "gcpi": "CPI inflation"}).round(1).reset_index().rename(columns={"period": "quarter"}).astype({"quarter": str})


# ---------------------------------------------------------------------------------------------------------------------------------
def _smooth(g: np.ndarray, w: int) -> np.ndarray:
    return np.stack([g[:, max(0, t - w + 1):t + 1].mean(axis=1) for t in range(g.shape[1])], axis=1)


def rebound_sensitivity(st: Study, sd: float) -> pd.DataFrame:
    """Share of coefficient draws flagged as rebounding, on the quarterly response and on 2-quarter and 4-quarter (year-on-year) averages of it."""
    b = I.bridge().coef.values[1:]
    cs = st.coefset("B26")
    rows = []
    for k in SM.ORDER:
        g = SM.responses(cs, k, b, sd)
        row = {"shock": SM.SHORT[k]}
        for lab, w in (("quarterly response (as flagged)", 1), ("2-quarter average", 2), ("4-quarter average (y/y)", 4)):
            m = SM.metrics(_smooth(g, w))
            row[lab] = f"{m[SM.REBOUND].mean():.0%}"
        m = SM.metrics(g)
        pers = m[SM.PERSIST]
        row["draws first below half in Q1-Q3 after the peak"] = f"{np.nanmean(pers <= 3):.0%}"
        row["median persistence across draws (quarters)"] = f"{np.nanmedian(pers):.0f}"
        rows.append(row)
    return pd.DataFrame(rows)


def wage_path_table(st: Study, sd: float) -> pd.DataFrame:
    b = I.bridge().coef.values[1:]
    g = SM.responses(st.coefset("B26"), "wages", b, sd)
    pt = SM.responses(st.coefset("B26", point=True), "wages", b, sd)[0]
    pk = pt.max()
    half = 0.5 * pk
    below_half = (g < half).mean(axis=0)
    return pd.DataFrame({"quarter": [f"Q{h}" for h in range(SM.NQ)], "point estimate (pp)": pt, "as % of peak": 100 * pt / pk,
                         "90% band low": np.quantile(g, .05, axis=0), "90% band high": np.quantile(g, .95, axis=0),
                         "share of draws below half the point-estimate peak": below_half})


def wage_lag_coefficients(st: Study) -> dict:
    out = {}
    for vk in ("B19", "B26"):
        r = st.hacs[vk]["gcpi"]
        se = pd.Series(np.sqrt(np.diag(r.cov.values)), index=r.coef.index)
        out[vk] = {n: (float(r.coef[n]), float(se[n])) for n in ("gcpi_L1", "gcpi_L2", "gcpi_L3", "gcpi_L4")}
    return out


# ---------------------------------------------------------------------------------------------------------------------------------
def _level_shock(component: str, pct: float, b: np.ndarray, sd: float):
    base = SM.inputs("food", b, sd)
    arr = np.zeros_like(np.asarray(base.gF, float))
    arr[I.LAGS] = 400 * np.log1p(pct / 100)
    return base.replace(gF=arr) if component == "food" else base.replace(gF=np.zeros_like(arr), gE=arr)


def comparability(st: Study, sd: float) -> pd.DataFrame:
    """Energy and food shocks restated in the same terms: the % change they imply in their own CPI component, its basket share, and the model's price-level effect."""
    b = I.bridge()
    bc = b.coef.values[1:]
    energy_own = 100 * (np.exp(b.elasticity * LOG10 / 100) - 1)          # CPI energy level change implied by Brent +10% after the bridge's lags
    cases = [("Energy, as standardised: Brent +10%", "energy", energy_own, None),
             ("Food, as standardised: CPI food +10%", "food", 10.0, ("food", 10.0)),
             ("Energy, like-for-like with food: CPI energy +10%", "energy", 10.0, ("energy", 10.0)),
             (f"Food, like-for-like with energy: CPI food +{energy_own:.1f}%", "food", energy_own, ("food", energy_own))]
    rows = []
    for lab, comp, own, lv in cases:
        draws, point = {}, {}
        for name, cs in (("pt", st.coefset("B26", point=True)), ("dr", st.coefset("B26"))):
            if lv is None:
                path = SM.responses(cs, "energy", bc, sd)
            else:
                path = np.asarray(E.simulate(cs, _level_shock(lv[0], lv[1], bc, sd))["gcpi"])[:, I.LAGS:I.LAGS + SM.NQ]
            draws[name] = path.sum(axis=1) / 4
        direct = BASKET_SHARE[comp] / 100 * own
        pl = float(draws["pt"][0])
        rows.append({"shock": lab, "change in own CPI component (%)": own, "basket share (%, authors' quote)": BASKET_SHARE[comp],
                     "direct arithmetic: share x change (%)": direct, "model: price level after 12 quarters (%)": pl,
                     "90% band": f"[{np.quantile(draws['dr'], .05):.2f}, {np.quantile(draws['dr'], .95):.2f}]", "model / direct": pl / direct,
                     "model effect per 1% rise in own component": pl / own})
    return pd.DataFrame(rows)


SENS_KEY = "food_lags03"
SENS_NAME = "Food, SENSITIVITY: same +10% shock, food lags 0-3 only (not B*)"


def food_lags03_stat_rows(st: Study, sd: float, lags=(0, 1, 2, 3), seed: int = 20261025) -> pd.DataFrame:
    """Statistics (same layout as `simple.run`'s stats) for the food shock under a price equation whose food block has lags 0-3 instead of 0-4.

    Diagnostic sensitivity, NOT B*: only the price equation is re-fitted (B*-2026 sample, same restrictions). Its bands are 90% over draws from that fit's own HAC covariance; the other three
    equations use the B*-2026 joint draws, so the band is comparable in kind but not in construction with the B* rows (no overlap with other samples is involved)."""
    from ..estimation.inference import _draw, hac_cov
    b = I.bridge().coef.values[1:]
    spec = specs_for_end(S.VARIANT, "2026Q2")["gcpi"]
    sp = dataclasses.replace(spec, blocks=tuple(Block("grpf", lags) if bl.var == "grpf" else bl for bl in spec.blocks))
    r = estimate(sp, st.data, S.START, "2026Q2")
    V = hac_cov(r, st.data)
    names = {eq: (list(r.coef.index) if eq == "gcpi" else list(stk.cols)) for eq, stk in st.stacks.items()}
    dr = _draw(r.coef.values, V.values, st.n, np.random.default_rng(seed))
    cs_draw = E.CoefSet(names, {eq: (dr if eq == "gcpi" else st.draws[eq]["B26"]) for eq in st.stacks})
    cs_pt = E.CoefSet(names, {eq: ((r.coef.values[None, :]) if eq == "gcpi" else stk.beta["B26"][None, :]) for eq, stk in st.stacks.items()})
    mp, md_ = SM.metrics(SM.responses(cs_pt, "food", b, sd)), SM.metrics(SM.responses(cs_draw, "food", b, sd))
    rows = []
    for name, arr in md_.items():
        rows.append({"shock": SENS_KEY, "vintage": S.LABEL["B26"], "statistic": name, "point": float(mp[name][0]), "lo90": float(np.nanquantile(arr, .05)), "hi90": float(np.nanquantile(arr, .95)),
                     "share of draws undefined": float(np.isnan(arr).mean()), "mean over draws": float(np.nanmean(arr))})
    return pd.DataFrame(rows)
