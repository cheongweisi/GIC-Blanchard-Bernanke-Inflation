"""The forecasting 'world' for Phase 4: model B*, the pinned data, the oil bridge and the baseline assumptions.

Forecast grid. Model B* is estimated on 1990Q1-2026Q2 (last complete quarter, unchanged from the Phase 3 supplement). The grid is the
13 quarters 2026Q3-2029Q3; history for the lags is 2025Q3-2026Q2.

Two information sets (switch `nowcast`):

  nowcast=True   (default, the operational baseline). 2026Q3 is only partly published (CPI, Cleveland Fed expectations, GSCPI, oil
                 are known; ECI, productivity and JOLTS are not). The published CPI inflation and expectations of 2026Q3 are imposed
                 as starting conditions, and the published nominal CPI energy and food growth and GSCPI drive the quarter.
                 Wages, V/U and productivity are still model/assumption values. Forecast quarters are 2026Q4-2029Q3.
  nowcast=False  strict: origin = last complete quarter, 2026Q3 is forecast like any other quarter (oil bridge for energy).

Baseline assumptions (every one is an assumption, not an estimate; the scenario library varies them):
  oil         Brent futures strip of the last futures date (EIA STEO and 'flat' as alternatives), Oct-Nov 2026 as documented in oil.py
  CPI energy  from oil through the monthly bridge (oil.py); relative energy price is an OUTPUT
  CPI food    nominal growth equal to baseline wage growth (relative food price constant: the authors' neutral convention, as in the
              Phase 3 unconditional forecasts), then FIXED as a nominal path in every scenario so that wage changes move relative prices
  GSCPI       AR(1) (1998Q1-2026Q2) from the last value; V/U and productivity growth held at the last complete quarter (Phase 3 convention)
  wage constant  estimated (validated in Phase 3's pseudo-out-of-sample); the authors' neutral constant is a sensitivity
  residuals   zero (pure model); an intercept correction is a sensitivity
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..estimation.inference import with_hac
from ..extension.models import fit, standard_models
from ..simulation.model import SimModel
from ..supplement import context as C
from ..supplement import irf_intuitive as I
from ..validation.ladder import GSCPI_STEADY
from . import engine as E
from . import oil as O
from . import pull as P
from .pin import PHASE4_PULL

LAGS = 4
H_SIM = 13
FIRST_Q = pd.Period("2026Q3", "Q")
LAST_COMPLETE = pd.Period("2026Q2", "Q")
N_DRAWS = 1000


def qend(s: pd.Series, q: pd.Period) -> float:
    """Value in the last month of quarter q (CPI, Cleveland: the authors' quarter-end convention)."""
    return float(s.loc[q.end_time.normalize().replace(day=1)])


def qmean(s: pd.Series, q: pd.Period) -> float:
    m = pd.date_range(q.start_time, periods=3, freq="MS")
    return float(s.loc[m].mean())


@dataclass
class World:
    nowcast: bool
    ctx: C.Ctx
    data: pd.DataFrame
    res: dict
    hac: dict
    cs_point: E.CoefSet
    cs_draws: E.CoefSet
    p4: dict[str, pd.Series]
    bridge: O.Bridge
    bridge_draws: np.ndarray
    quarters: pd.PeriodIndex               # the 13 grid quarters
    hist_q: pd.PeriodIndex                 # the 4 history quarters
    hist: dict[str, np.ndarray]
    gE_hist: np.ndarray
    gF_hist: np.ndarray
    base_exog: dict[str, np.ndarray]       # vu, magpty, shortagema2 on the full T grid (history + simulated)
    base_shortage: np.ndarray              # GSCPI level path on the T grid (history 4 + 13)
    ar1: tuple[float, float]
    known: dict[str, np.ndarray]
    q3: dict[str, float]                   # partial-quarter facts for 2026Q3
    oil_curve: dict[str, pd.Series]        # monthly baseline oil candidates (Oct 2026 on)
    oil_actual: pd.Series                  # monthly Brent actuals (World Bank), through 2026-09
    cpie_m: pd.Series
    fut_date: str
    gF_base: np.ndarray = None             # nominal food growth path (T), set by `finalise`
    notes: list[str] = field(default_factory=list)

    @property
    def T(self) -> int:
        return LAGS + len(self.quarters)

    @property
    def idx_all(self) -> pd.PeriodIndex:
        return self.hist_q.append(self.quarters)

    @property
    def months(self) -> pd.DatetimeIndex:
        return pd.date_range(self.quarters[0].start_time, self.quarters[-1].end_time.normalize().replace(day=1), freq="MS")

    def oil_series(self, kind: str = "futures") -> pd.Series:
        """Monthly oil levels: actuals through Sep 2026 then the chosen baseline curve."""
        return pd.concat([self.oil_actual.loc[:"2026-09-01"], self.oil_curve[kind]]).sort_index()

    def forecast_quarters(self) -> pd.PeriodIndex:
        return self.quarters[1:] if self.nowcast else self.quarters

    def first_sim_index(self) -> int:
        return LAGS


def neutral_wage_constant(cs: E.CoefSet, vu_star: float, magpty_star: float, short_star: float) -> np.ndarray:
    """Authors' wage constant (wage_constant.pdf) for the shortage block `shortagema2_L0`: the constant that makes the model's
    steady state neutral at V/U = vu_star, productivity growth magpty_star, shortage = short_star and constant relative prices.
    Returns one value per draw."""
    sum_vu, sum_a = cs.block_sum("gw", "vu"), cs.block_sum("gw", "gw")
    bm_w = cs.get("gw", "magpty_L1")
    den_p = 1.0 - cs.block_sum("gcpi", "gcpi")
    bm_p, b_s, c_p = cs.get("gcpi", "magpty_L0"), cs.block_sum("gcpi", "shortagema2"), cs.get("gcpi", "const")
    return (-sum_vu * vu_star - (1.0 - sum_a) * ((bm_p / den_p + bm_w / (1.0 - sum_a)) * magpty_star + b_s / den_p * short_star + c_p / den_p))


def _quarter_actuals(p4: dict[str, pd.Series], q: pd.Period, prev: pd.Period) -> dict[str, float]:
    cpi, e, f = p4["uspric2156"], p4["uspric2368"], p4["uspric2158"]
    g = lambda s: 400.0 * np.log(qend(s, q) / qend(s, prev))                       # noqa: E731
    return {"gcpi": g(cpi), "gE": g(e), "gF": g(f), "cf1": qend(p4["usfcst0101"], q), "cf10": qend(p4["usfcst0110"], q),
            "gscpi": qmean(p4["wotrad0027"], q)}


def qa_vs_pinned(w: "World") -> pd.DataFrame:
    """Phase 4 pull against the pinned Phase 3 raw data for every complete quarter of the sample (revisions would show here)."""
    raw = w.ctx.p3.raw
    rows = []
    for name, tick, col, how in (("CPI all items", "uspric2156", "CPIAUCSL", qend), ("CPI energy", "uspric2368", "CPIENGSL", qend),
                                 ("CPI food", "uspric2158", "CPIUFDSL", qend), ("Cleveland 1y", "usfcst0101", "EXPINF1YR", qend),
                                 ("Cleveland 10y", "usfcst0110", "EXPINF10YR", qend), ("GSCPI (quarterly mean)", "wotrad0027", "GSCPI", qmean)):
        diffs = []
        for q in pd.period_range("2015Q1", LAST_COMPLETE, freq="Q"):
            diffs.append(how(w.p4[tick], q) - float(raw.loc[q, col]))
        d = np.array(diffs)
        rows.append({"series": name, "quarters compared": len(d), "max |difference|": float(np.abs(d).max()),
                     "n revised (|diff|>1e-9)": int((np.abs(d) > 1e-9).sum())})
    return pd.DataFrame(rows)


def build(nowcast: bool = True, n_draws: int = N_DRAWS, seed: int = 0, pull_id: str = PHASE4_PULL) -> World:
    ctx = C.load()
    d = ctx.data_star
    ms = standard_models(ctx.last)
    res = fit(ms["B"], d, ctx.last)                                    # Model B*: unweighted, gscpi_ma2, V/U 2025Q4 bridged
    hac = {k: with_hac(r, d) for k, r in res.items()}
    cs_point = E.CoefSet.from_models([SimModel.from_results(res)])
    cs_draws = E.CoefSet.from_models(I.draws(hac, n_draws, seed))
    p4 = P.load(pull_id)
    tick = P.futures_tickers()

    hist_q = pd.period_range(LAST_COMPLETE - 3, LAST_COMPLETE, freq="Q")
    quarters = pd.period_range(FIRST_Q, periods=H_SIM, freq="Q")
    h = d.loc[hist_q]
    hist = {k: h[k].values.astype(float) for k in ("gw", "gcpi", "cf1", "cf10", "diffcpicf", "grpe", "grpf")}
    gE_hist, gF_hist = (h["grpe"] + h["gw"]).values, (h["grpf"] + h["gw"]).values        # grpe = gE - gw exactly

    # oil: actuals (World Bank monthly), baseline curves
    oil_actual = p4["wocaes0935"].dropna()
    fut = O.monthly_futures_curve(p4, tick, steo_oct=float(p4["eiasteo0002"].loc["2026-10-01"]))
    steo = O.steo_curve(p4, fut)
    months = pd.date_range("2026-10-01", "2029-12-01", freq="MS")
    curves = {"futures": fut, "steo": steo, "flat_sep": O.flat_curve(float(oil_actual.loc["2026-09-01"]), months),
              "flat_oct": O.flat_curve(float(fut.loc["2026-10-01"]), months)}
    cpie_m = p4["uspric2368"].dropna()
    bridge = O.estimate_bridge(cpie_m.loc[:"2026-06-01"], oil_actual.loc[:"2026-06-01"], end="2026-06")
    bdraws = bridge.draws(n_draws, seed + 1)

    # 2026Q3 partial quarter
    q3 = _quarter_actuals(p4, FIRST_Q, LAST_COMPLETE)
    # exogenous baseline: V/U and productivity held; GSCPI AR(1)
    vu0, mp0 = float(d.at[LAST_COMPLETE, "vu"]), float(d.at[LAST_COMPLETE, "magpty"])
    sh = d["shortage"].loc["1998Q1":ctx.last]
    X = np.column_stack([np.ones(len(sh) - 1), sh.values[:-1]])
    c, rho = np.linalg.lstsq(X, sh.values[1:], rcond=None)[0]
    T = LAGS + H_SIM
    short = np.full(T, np.nan)
    short[:LAGS] = d["shortage"].loc[hist_q].values
    for t in range(LAGS, T):
        short[t] = q3["gscpi"] if (nowcast and t == LAGS) else c + rho * short[t - 1]
    ma2 = pd.Series(short).rolling(2, min_periods=2).mean().values.copy()
    ma2[:LAGS] = d["shortagema2"].loc[hist_q].values
    exog = {"vu": np.r_[h["vu"].values, np.full(H_SIM, vu0)], "magpty": np.r_[h["magpty"].values, np.full(H_SIM, mp0)], "shortagema2": ma2}
    known = {}
    if nowcast:
        for k in ("gcpi", "cf1", "cf10"):
            known[k] = np.r_[np.full(LAGS, np.nan), q3[k], np.full(H_SIM - 1, np.nan)]
    w = World(nowcast, ctx, d, res, hac, cs_point, cs_draws, p4, bridge, bdraws, quarters, hist_q, hist, gE_hist, gF_hist, exog, short,
              (float(c), float(rho)), known, q3, curves, oil_actual, cpie_m, fut.attrs["futures_date"])
    w.notes.append(f"Phase 4 pull {pull_id}; futures date {w.fut_date}; model B* sample 1990Q1-{ctx.last}")
    return w
