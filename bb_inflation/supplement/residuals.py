"""Post-2023 over-prediction: where do the errors come from?

Everything is descriptive/diagnostic; the baseline model is never altered here. Pieces:
* quarter_table        actual vs one-step fitted (Model A frozen at 2023Q2, Model B*) and the fixed-origin conditional forecast
* error_attribution    exact additive split of the fixed-origin forecast error by equation shock (the model is linear in the shocks)
* energy_check         model energy contribution vs the mechanical direct contribution (CPI weight x energy CPI growth)
* shutdown_adjustment  size of the shelter measurement artifact of the 2025 shutdown (Q4 2025 understated, Q2 2026 catch-up)
* asymmetry_tests      is energy pass-through lower in large energy spikes? full-sample significance + one-step recursive OOS
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from ..estimation.equations import Block
from ..estimation.inference import with_hac
from ..estimation.rls import design, estimate
from ..extension import pseudo_oos as O
from ..extension.models import specs_for_end
from ..simulation.model import ENDO, LAGS, SimModel
from . import diag_pull as D

EQS = ("gw", "gcpi", "cf1", "cf10")
POST = ("2023Q3", "2026Q2")


def one_step(res: dict, data: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({k: res[k].predict(data) for k in EQS})


def quarter_table(data: pd.DataFrame, fitA: pd.DataFrame, fitB: pd.DataFrame, dynA: pd.DataFrame, sigma: float) -> pd.DataFrame:
    idx = pd.period_range(*POST, freq="Q")
    t = pd.DataFrame({"actual": data.gcpi, "fitted_A": fitA.gcpi, "fitted_Bstar": fitB.gcpi, "dyn_A_from_2023Q2": dynA.gcpi}).loc[idx]
    t["resid_A"] = t.actual - t.fitted_A
    t["resid_Bstar"] = t.actual - t.fitted_Bstar
    t["err_dyn_A"] = t.actual - t.dyn_A_from_2023Q2
    t["z_A (resid/sd pre-2020)"] = t.resid_A / sigma
    t["share of sum sq resid_A (%)"] = 100 * t.resid_A ** 2 / (t.resid_A ** 2).sum()
    return t


def fixed_origin_forecast(model: SimModel, data: pd.DataFrame, origin: str, h: int) -> pd.DataFrame:
    T0 = pd.Period(origin, "Q")
    return O._forecast(model, data, T0, h, O.conditional_exog(data, T0, h))


def error_attribution(model: SimModel, data: pd.DataFrame, fit_df: pd.DataFrame, origin: str, h: int) -> pd.DataFrame:
    """Fixed-origin conditional forecast error of CPI inflation split by the equation whose one-step residuals cause it.
    The four equations' residual series, added to the simulation, reproduce the actual path exactly (checked by the caller)."""
    T0 = pd.Period(origin, "Q")
    w = O._window(data, T0, h)
    exog = O.conditional_exog(data, T0, h)
    hist = {k: w[k].values.astype(float) for k in ENDO}
    idx = pd.period_range(T0 + 1, periods=h, freq="Q")

    def run(eqs: tuple[str, ...]) -> np.ndarray:
        add = None
        if eqs:
            add = {}
            for eq in eqs:
                arr = np.zeros(LAGS + h)
                arr[LAGS:] = (data[eq] - fit_df[eq]).reindex(idx).values
                add[eq] = arr
        return model.simulate(hist, exog, add_shocks=add)["gcpi"][LAGS:]

    base = run(())
    out = {"forecast": base, "actual": data.gcpi.reindex(idx).values}
    for eq, lab in (("gcpi", "price-equation residual"), ("gw", "wage-equation residual"),
                    ("cf1", "1y-expectations residual"), ("cf10", "10y-expectations residual")):
        out[lab] = run((eq,)) - base
    out["all four (check)"] = run(EQS) - base
    df = pd.DataFrame(out, index=idx)
    df["error (actual - forecast)"] = df.actual - df.forecast
    return df


# ------------------------------------------------------------------ energy / underlying inflation
def monthly_components(S: dict[str, pd.Series]) -> pd.DataFrame:
    g = lambda n: S[D.DIAG[n]]                          # noqa: E731
    return pd.DataFrame({"head": S["uspric2156"], "energy": S["uspric2368"], "food": S["uspric2158"], "core": g("core_cpi"),
                         "shelter": g("shelter_cpi"), "oer": g("oer_cpi"), "rent": g("rent_cpi"),
                         "services_ex_energy": g("services_ex_energy_cpi"), "core_goods": g("core_goods_cpi"),
                         "gasoline": g("gasoline_cpi")})


def quarterly_annualised(m: pd.DataFrame) -> pd.DataFrame:
    q = m[m.index.month.isin([3, 6, 9, 12])].copy()
    q.index = q.index.to_period("Q")
    return 400 * np.log(q).diff()


def cpi_weights(m: pd.DataFrame, lo: str = "2015-01-01", hi: str = "2025-09-01") -> dict[str, float]:
    """Implied relative weights of energy, food and core in headline CPI (monthly log changes, weights sum to one)."""
    d = 100 * np.log(m).diff()
    y = (d["head"] - d["core"])
    X = pd.DataFrame({"e": d["energy"] - d["core"], "f": d["food"] - d["core"]})
    ok = pd.concat([y.rename("y"), X], axis=1).loc[lo:hi].dropna()
    b = np.linalg.lstsq(ok[["e", "f"]].values, ok["y"].values, rcond=None)[0]
    return {"energy": float(b[0]), "food": float(b[1]), "core": float(1 - b.sum())}


def energy_check(data: pd.DataFrame, res_price, qa: pd.DataFrame, w: dict[str, float]) -> pd.DataFrame:
    """Model's energy block contribution to CPI inflation (all five lags of relative energy growth) next to the mechanical
    direct contribution of the energy CPI (weight x its annualised growth), and the same for core and food."""
    X = design(res_price.spec, data)[list(res_price.coef.index)]
    c = X * res_price.coef
    model_energy = c[[n for n in c if n.startswith("grpe_")]].sum(axis=1)
    model_food = c[[n for n in c if n.startswith("grpf_")]].sum(axis=1)
    out = pd.DataFrame({"actual CPI": data.gcpi, "model fitted": res_price.predict(data), "model: energy block": model_energy,
                        "model: food block": model_food,
                        "direct energy (w x energy CPI)": w["energy"] * qa["energy"],
                        "direct food (w x food CPI)": w["food"] * qa["food"],
                        "direct core (w x core CPI)": w["core"] * qa["core"],
                        "core CPI (annualised)": qa["core"], "energy CPI (annualised)": qa["energy"],
                        "relative energy price growth (grpe)": data["grpe"]})
    out["energy block minus direct energy"] = out["model: energy block"] - out["direct energy (w x energy CPI)"]
    out["model non-energy part"] = out["model fitted"] - out["model: energy block"]
    out["actual non-energy part"] = out["actual CPI"] - out["direct energy (w x energy CPI)"]
    return out.loc[POST[0]:POST[1]]


def shutdown_adjustment(m: pd.DataFrame, w_rent_oer: float = 0.335, bls_range: tuple[float, float] = (0.24, 0.59)) -> dict:
    """Shelter artifact (BLS: October 2025 rent/OER carried forward -> index levels too low until the April 2026 panel).
    Central size = excess of April 2026 rent/OER monthly change over the average of Jan-Mar and May-Jun 2026, a data-based
    measure of the catch-up; range = BLS Monthly Labor Review counterfactual October changes. Annualised effect on
    quarterly inflation = 4 x weight x (excess monthly change). The weight (rent + OER share of CPI) is an assumption."""
    d = 100 * np.log(m[["rent", "oer"]]).diff()
    ex = {}
    for c in d:
        ref = d[c].loc[["2026-01-01", "2026-02-01", "2026-03-01", "2026-05-01", "2026-06-01"]].mean()
        ex[c] = float(d[c].loc["2026-04-01"] - ref)
    mid = float(np.mean(list(ex.values())))
    f = lambda x: 4 * w_rent_oer * x                                          # noqa: E731
    return {"april_excess_monthly_pct": ex, "central_pp": f(mid), "low_pp": f(bls_range[0]), "high_pp": f(bls_range[1]),
            "w_rent_oer": w_rent_oer}


# ------------------------------------------------------------------ energy asymmetry
def add_energy_terms(data: pd.DataFrame, thr: float) -> pd.DataFrame:
    d = data.copy()
    d["grpepos"] = d["grpe"].clip(lower=0)
    d["grpebig"] = d["grpe"].where(d["grpe"] > thr, 0.0)
    return d


VARIANTS = {"baseline": None, "positive energy growth": "grpepos", "large energy spikes": "grpebig"}


def price_spec(end: str, extra: str | None):
    spec = specs_for_end("gscpi_ma2", end)["gcpi"]
    if extra:
        spec = dataclasses.replace(spec, blocks=spec.blocks + (Block(extra, (0,)),))
    return spec


def asymmetry_tests(data: pd.DataFrame, thr: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = add_energy_terms(data, thr)
    rows = []
    for end in ("2023Q2", "2026Q2"):
        base = estimate(price_spec(end, None), d, "1990Q1", end)
        for name, extra in VARIANTS.items():
            if not extra:
                continue
            r = estimate(price_spec(end, extra), d, "1990Q1", end)
            h = with_hac(r, d)
            b, se = float(r.coef[f"{extra}_L0"]), float(np.sqrt(h.cov.loc[f"{extra}_L0", f"{extra}_L0"]))
            rows.append({"variant": name, "sample end": end, "extra coefficient": b, "HAC se": se, "t": b / se,
                         "energy L0 coef (extended)": float(r.coef["grpe_L0"]), "energy L0 coef (baseline)": float(base.coef["grpe_L0"]),
                         "N": r.nobs, "resid sd extended": float(r.resid.std()), "resid sd baseline": float(base.resid.std())})
    sig = pd.DataFrame(rows)
    # one-step recursive pseudo-OOS: estimate through e, predict e+1
    ends = pd.period_range("2004Q3", "2026Q1", freq="Q")
    err = {k: [] for k in VARIANTS}
    for e in ends:
        tgt = e + 1
        for name, extra in VARIANTS.items():
            r = estimate(price_spec(str(e), extra), d, "1990Q1", str(e))
            err[name].append(float(d.at[tgt, "gcpi"] - r.predict(d).get(tgt, np.nan)))
    E = pd.DataFrame(err, index=ends + 1)
    per = {"2004Q4-2019Q4": ("2004Q4", "2019Q4"), "2020Q1-2023Q2": ("2020Q1", "2023Q2"), "2023Q3-2026Q2": ("2023Q3", "2026Q2"),
           "all": ("2004Q4", "2026Q2")}
    oos = pd.DataFrame({p: {k: float(np.sqrt((E.loc[lo:hi, k] ** 2).mean())) for k in E} for p, (lo, hi) in per.items()}).T
    oos.index.name = "target period (RMSE, pp)"
    return sig, oos, E
