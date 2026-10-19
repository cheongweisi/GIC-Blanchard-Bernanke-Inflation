"""Simplified transmission exercise (separate from the full Phase 4c analysis): four standardised shocks, headline CPI inflation, B*-2026 with B*-2019 / B*-2023 as robustness.
Writes outputs/phase4c_simple/ and docs/phase4c_simple.md. Nothing in outputs/phase4c/ or docs/phase4c_report.md is touched."""
import sys
import textwrap
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bb_inflation.config import OUTPUTS, PROJECT_ROOT  # noqa: E402
from bb_inflation.phase4c import compare as CP  # noqa: E402
from bb_inflation.phase4c import irf as I  # noqa: E402
from bb_inflation.phase4c import samples as S  # noqa: E402
from bb_inflation.phase4c import simple as SM  # noqa: E402
from bb_inflation.phase4c import simple_diag as DG  # noqa: E402
from bb_inflation.phase4c import study as ST  # noqa: E402

OUT = OUTPUTS / "phase4c_simple"
OUT.mkdir(exist_ok=True)
V26, V19, V23 = S.LABEL["B26"], S.LABEL["B19"], S.LABEL["B23"]

st = ST.build()
sd = CP.gscpi_sd(st.data)
R = SM.run(st, sd)
defs = DG.definitions_detailed(st, sd)
defs.to_csv(OUT / "simple_shock_definitions.csv", index=False)
R["paths"].to_csv(OUT / "simple_cpi_paths.csv", index=False)
R["stats"].to_csv(OUT / "simple_stats_long.csv", index=False)
R["diffs"].to_csv(OUT / "simple_differences_vs_2019_2023.csv", index=False)
stt, dif, pth = R["stats"], R["diffs"], R["paths"]
SENS = DG.food_lags03_stat_rows(st, sd)
SENS.to_csv(OUT / "simple_food_lags03_sensitivity_stats.csv", index=False)
stt = pd.concat([stt, SENS], ignore_index=True)
HEAD_KEYS = ["energy", "food", DG.SENS_KEY, "wages", "supply"]
HEAD_NAME = {**SM.NAME, DG.SENS_KEY: DG.SENS_NAME}


def g(shock, vint, stat):
    r = stt[(stt["shock"] == shock) & (stt.vintage == vint) & (stt.statistic == stat)].iloc[0]
    return r


def cell(shock, vint, stat, d=2, band=True, integer=False):
    r = g(shock, vint, stat)
    f = (lambda v: f"{v:.0f}") if integer else (lambda v: f"{v:.{d}f}")
    return f(r.point) + (f" [{f(r.lo90)}, {f(r.hi90)}]" if band else "")


def pers_cell(shock, vint, band=True):
    """Persistence: quarters from the peak until the response first falls below 50% of the peak; 'not reached within 12Q' if it never does inside the horizon."""
    r = g(shock, vint, SM.PERSIST)
    unreached = float(r["share of draws undefined"])
    if np.isnan(r.point):
        txt = "not reached within 12Q (>%dQ after the peak)" % (SM.NQ - 1 - int(g(shock, vint, "quarter of peak").point))
    else:
        txt = f"{r.point:.0f}Q"
        if band and not np.isnan(r.lo90):
            txt += f" [{r.lo90:.0f}, {r.hi90:.0f}]"
    if band and unreached >= 0.05:
        txt += f"; not reached in {unreached:.0%} of draws"
    return txt


def rebound_cell(shock, vint, band=True):
    """Flag: after first falling below half the peak, does the response come back to at least half the peak within the horizon?"""
    rb, rq, pe = g(shock, vint, SM.REBOUND), g(shock, vint, SM.REBOUND_Q), g(shock, vint, SM.PERSIST)
    share = f"{rb['mean over draws']:.0%} of draws rebound"
    if np.isnan(pe.point):
        return "n/a at point estimate (never falls below half); " + share
    if rb.point == 1:
        return f"YES: back above half-peak in Q{rq.point:.0f}; " + share
    return "no at point estimate; " + share


# ---- headline table (B*-2026) ------------------------------------------------------------------------------------------------
STATS = ["Q0 response (pp)", "peak response (pp)", "quarter of peak", SM.PERSIST, "price level after 12 quarters (%)"]
COLS = ["Q0 response (pp)", "Peak response (pp)", "Quarter of peak", "Persistence: quarters from peak until response first falls below 50% of peak", "Rebound above half-peak afterwards?",
        "CPI price-level effect after 3 years (%)"]
rows = []
for k in HEAD_KEYS:
    rows.append({"Shock": HEAD_NAME[k], COLS[0]: cell(k, V26, STATS[0], 2), COLS[1]: cell(k, V26, STATS[1], 2), COLS[2]: cell(k, V26, STATS[2], integer=True),
                 COLS[3]: pers_cell(k, V26), COLS[4]: rebound_cell(k, V26), COLS[5]: cell(k, V26, STATS[4], 2)})
T_HEAD = pd.DataFrame(rows)
T_HEAD.to_csv(OUT / "simple_headline_table_B2026.csv", index=False)

# ---- robustness tables ------------------------------------------------------------------------------------------------------
rows = []
for k in SM.ORDER:
    for v in (V26, V19, V23):
        rows.append({"Shock": SM.SHORT[k], "Sample": v, COLS[0]: cell(k, v, STATS[0], 2, band=False), COLS[1]: cell(k, v, STATS[1], 2), COLS[2]: cell(k, v, STATS[2], integer=True, band=False),
                     COLS[3]: pers_cell(k, v, band=False), COLS[4]: rebound_cell(k, v, band=False), COLS[5]: cell(k, v, STATS[4], 2)})
T_ROB = pd.DataFrame(rows)
T_ROB.to_csv(OUT / "simple_robustness_table_2019_2023.csv", index=False)
rows = []
for k in SM.ORDER:
    for stat, lab in (("peak response (pp)", "Peak response (pp)"), ("price level after 12 quarters (%)", "Price-level effect after 3 years (%)")):
        row = {"Shock": SM.SHORT[k], "Statistic": lab}
        for other in (V19, V23):
            r = dif[(dif["shock"] == k) & (dif.comparison == f"{V26} minus {other}") & (dif.statistic == stat)].iloc[0]
            row[f"B*-2026 minus {other}"] = f"{r['difference']:+.2f} [{r['lo90']:+.2f}, {r['hi90']:+.2f}], p = {r['p (two-sided, from draws)']:.2f}"
        rows.append(row)
T_DIF = pd.DataFrame(rows)

# ---- the one chart ---------------------------------------------------------------------------------------------------------
SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
COL = {V26: "#1baf7a", V19: "#2a78d6", V23: "#eb6834"}
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
                     "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False})
fig, axes = plt.subplots(2, 2, figsize=(10.5, 7))
for ax, k in zip(axes.flat, SM.ORDER):
    for v, lw, ls in ((V19, 1.2, "--"), (V23, 1.2, ":"), (V26, 2.4, "-")):
        d = pth[(pth["shock"] == k) & (pth.vintage == v)].sort_values("quarter")
        if v == V26:
            ax.fill_between(d.quarter, d.lo90, d.hi90, color=COL[v], alpha=0.16, lw=0)
        ax.plot(d.quarter, d.point, color=COL[v], lw=lw, ls=ls, label=v + (" (headline, 90% band)" if v == V26 else " (robustness)"), marker="o" if v == V26 else None, ms=3.5)
    ax.axhline(0, color=MUTED, lw=0.7)
    ax.set_title(textwrap.fill(SM.NAME[k], 44), loc="left")
    ax.set_xticks(range(0, 12))
    ax.set_xlabel("quarter (Q0 = shock quarter)")
    ax.set_ylabel("CPI inflation response (pp, annualised)")
h, l = axes.flat[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, fontsize=8.5)
fig.suptitle("Response of headline CPI inflation to four standardised, illustrative shocks", x=0.01, ha="left", fontsize=12, fontweight="bold")
fig.text(0.01, 0.935, "Shocks differ in kind and size, so the panels use different scales and responses must not be ranked across panels.", fontsize=8.5, color=INK2)
fig.tight_layout(rect=(0, 0.06, 1, 0.92))
fig.savefig(OUT / "simple_cpi_inflation_response.png", dpi=150)
plt.close(fig)

# ---- note -------------------------------------------------------------------------------------------------------------------
food = pth[(pth["shock"] == "food") & (pth.vintage == V26)].set_index("quarter")["point"]
q4 = {v: g("food", v, "response in Q4 as % of peak").point for v in (V19, V23, V26)}
md = lambda df: df.to_markdown(index=False)                                          # noqa: E731

fl, ft, fv, fd, fe = DG.food_lag_table(st), DG.food_lag_tests(st), DG.food_variants(st, sd), DG.food_decomposition(st, sd), DG.food_episode(st)
rs, wp, wl, cp = DG.rebound_sensitivity(st, sd), DG.wage_path_table(st, sd), DG.wage_lag_coefficients(st), DG.comparability(st, sd)
for name, df_ in (("diag_food_lag_coefficients", fl), ("diag_food_variants", fv), ("diag_food_decomposition", fd), ("diag_food_episode_2020_21", fe), ("diag_rebound_sensitivity", rs),
                  ("diag_wage_response_path", wp), ("diag_energy_food_comparability", cp)):
    df_.to_csv(OUT / f"{name}.csv", index=False)
fmt1 = lambda df_, cols: df_.assign(**{c: df_[c].map(lambda v: f"{v:.2f}") for c in cols})                            # noqa: E731
fv_t = fv.assign(**{c: fv[c].map(lambda v: "-" if pd.isna(v) else f"{v:+.3f}") for c in ("food L3", "food L4")}).assign(
    **{c: fv[c].map(lambda v: f"{v:.2f}") for c in ("response Q3 (pp)", "response Q4 (pp)", "Q4 as % of Q0", "price level after 12 quarters (%)", "sum of food lags")})
cp_t = cp.assign(**{c: cp[c].map(lambda v: f"{v:.2f}") for c in cp.columns if c not in ("shock", "90% band")})
wp_t = wp.assign(**{"point estimate (pp)": wp["point estimate (pp)"].map(lambda v: f"{v:.3f}"), "as % of peak": wp["as % of peak"].map(lambda v: f"{v:.0f}%"),
                    "90% band": wp.apply(lambda r: f"[{r['90% band low']:.2f}, {r['90% band high']:.2f}]", axis=1), "draws below half the peak": wp["share of draws below half the point-estimate peak"].map(lambda v: f"{v:.0%}")})[
    ["quarter", "point estimate (pp)", "as % of peak", "90% band", "draws below half the peak"]]
CLAR = f"""## Clarifications requested at review

**1. Definition, magnitude, duration and units of the shocks.** The table at the top of this note gives, for each shock, what is shocked, its size, how long it lasts, the units of the model input and the change it implies in the CPI component concerned. Two points on units. (i) Responses are annualised percentage-point rates for one quarter: food's Q0 response of {g('food', V26, 'Q0 response (pp)').point:.2f}pp is about {g('food', V26, 'Q0 response (pp)').point / 4:.1f}% on the price level in Q0, not 4.8% on the price level. (ii) **Food**: the CPI food price *level* is raised by 10% (9.53 log points) in Q0 and stays there; because the model takes nominal CPI food *growth* as an annualised rate, this enters as one jump of 400 x ln(1.1) = +38.1pp in Q0 and zero afterwards. Wages are not shocked, so the relative food price (food over wages) then drifts down again as wages grow.
**Energy** is a different kind of variable: the shock is to Brent, and the calibrated bridge turns it into a CPI-energy rise of only about 2.9% in total (2.7% by the end of Q0).

**2. Why does the food response rebound in Q4: transmission mechanism or specification artefact?** *Most likely an artefact of the unrestricted five-lag food block, identified by one observation; not a credible transmission channel.*

- *Mechanics.* The price equation has food-price growth at lags 0 to 4, so a one-off jump in Q0 reappears four quarters later through the lag-4 coefficient: {fd.loc[4, 'direct food-coefficient term (L_k x 38.1)']:.2f}pp of the {fd.loc[4, 'total CPI response']:.2f}pp Q4 response is that coefficient times 38.1 (the rest is feedback). The lag-3 coefficient is negative and offsets part of it one quarter earlier (Q3 = {fd.loc[3, 'total CPI response']:.2f}pp).
- *Estimates (HAC s.e. in brackets):*

{md(fl)}

- *Weak statistical support.* L4 alone: p = {ft['L4 = 0']:.2f}; L3 and L4 jointly: p = {ft['L3 = L4 = 0']:.2f}. The 90% band for the Q4 response, [{np.quantile(SM.responses(st.coefset('B26'), 'food', I.bridge().coef.values[1:], sd)[:, 4], .05):.1f}, {np.quantile(SM.responses(st.coefset('B26'), 'food', I.bridge().coef.values[1:], sd)[:, 4], .95):.1f}]pp, includes zero.
- *Not there before the pandemic.* L4 is 0.014 in B\\*-2019 (the recursive estimate is 0.008 as late as 2020Q3 and 0.107 by 2021Q2).
- *One observation.* Dropping only the 2021Q2 observation moves L4 from +0.078 to -0.013 and removes the echo (table below). That quarter's CPI inflation (8.5% annualised, in the 2021 reopening surge) came exactly four quarters after the 2020Q2 food-price spike (relative food growth +9.0pp), so the regression can read a coincidence of timing as a four-quarter lag. A lag of four quarters could be rationalised by annual repricing or contracts, but the alternating signs (L3 negative, L4 positive, net +0.017) and the absence of any pre-2020 evidence do not support that reading.

{md(fv_t)}

- *What is robust.* The cumulative effect: 2.07% to 2.58% across all variants (2.38% as estimated). The Q0 response and the sum of food coefficients (0.13 to 0.18) are also stable; the path from Q1 to Q4 is not.

The rebound flag therefore stays in the table (it describes the model as estimated), but read food's persistence from the cumulative effect. A food block with lags 0 to 3 or 0 to 2 gives no rebound and a cumulative effect of 2.07% or 2.24%; I have **not** adopted either as the headline, because that would depart from the authors' lag structure and from B\\*; the lags 0-3 version is shown as a clearly labelled sensitivity row in the headline table.

**3. Why does the wage shock rebound in 67% of coefficient draws when the point estimate does not?** *Because the point-estimate path is double-humped and sits within a few percentage points of the 50% threshold for three quarters, so almost any change in the imprecisely estimated lag coefficients moves the crossing, and the first crossing is usually followed by another hump.*

{md(wp_t)}

- At the point estimate the response peaks in Q1, dips in Q2 (75% of peak), is back at 99% in Q3, then runs at 52%, 59% and 51% of the peak in Q4 to Q6 (threshold 50%) before falling to 32% in Q7. The "6 quarters" is where the path happens to cross; a small change makes it cross in Q4 or Q6 or never.
- Across draws the median persistence is {rs.loc[rs.shock == 'Wages', 'median persistence across draws (quarters)'].iloc[0]} quarter, not 6: in {rs.loc[rs.shock == 'Wages', 'draws first below half in Q1-Q3 after the peak'].iloc[0]} of draws the response is below half its peak within three quarters of the peak. The first hump (Q1) is followed by a trough (Q2) and a second hump (Q3); in the draws that rebound, the average rebound quarter is Q4.
- The humps come from the lag structure. The price equation's own-lag coefficients are L1 = {wl['B26']['gcpi_L1'][0]:+.3f} ({wl['B26']['gcpi_L1'][1]:.3f}) and L3 = {wl['B26']['gcpi_L3'][0]:+.3f} ({wl['B26']['gcpi_L3'][1]:.3f}) in B\\*-2026, against {wl['B19']['gcpi_L1'][0]:+.3f} ({wl['B19']['gcpi_L1'][1]:.3f}) and {wl['B19']['gcpi_L3'][0]:+.3f} ({wl['B19']['gcpi_L3'][1]:.3f}) in B\\*-2019; the wage and expectations equations also have uneven, individually imprecise lag patterns. The sums of lag coefficients are well determined; their timing within the year is not.
- The flag is sensitive to quarter-to-quarter noise. Share of draws flagged as rebounding, on the quarterly response (as in the table) and on 2- and 4-quarter averages of it:

{md(rs[['shock', 'quarterly response (as flagged)', '2-quarter average', '4-quarter average (y/y)']])}

For wages the share falls from 67% to 30% and 12% when the response is averaged over two or four quarters, which supports reading it as jaggedness of an imprecisely estimated lag pattern, not a genuine second wave. Better read: the wage impulse takes roughly one to six quarters to fall to half its peak (point estimate 6, median draw 1, shape uncertain), with a more reliable cumulative effect of {cell('wages', V26, 'price level after 12 quarters (%)', 2)}%.

**4. Are the food and energy scenarios comparable price-level shifts?** *No: the standardised shocks move their own CPI components by very different amounts, and that accounts for most of the gap in cumulative effects.*

{md(cp_t)}

Basket shares are the ones quoted by Bernanke and Blanchard (about 7.4% energy, 14.4% food), not recomputed here; "direct arithmetic" is share x change, i.e. the price-level effect with no second-round effects.

- Brent +10% moves CPI energy by only {cp.iloc[0, 1]:.1f}%, whereas food is moved by 10%. Of the {cp.iloc[1, 4] / cp.iloc[0, 4]:.1f}-fold difference in cumulative effects, a factor of {10 / cp.iloc[0, 1]:.1f} is shock size and a factor of {cp.iloc[1, 7] / cp.iloc[0, 7]:.1f} is structure (effect per 1% rise in the component: {cp.iloc[1, 7]:.2f} for food, {cp.iloc[0, 7]:.2f} for energy).
- On a like-for-like basis (each component +10%, or each +{cp.iloc[0, 1]:.1f}%) food's effect is about {cp.iloc[1, 7] / cp.iloc[2, 7]:.1f} times energy's. That is close to the ratio of basket shares ({14.4 / 7.4:.1f}), plus a somewhat larger second-round multiplier for food ({cp.iloc[1, 6]:.2f} times direct, against {cp.iloc[2, 6]:.2f} for energy).
- So the standardised food shock is not a "bigger" shock in any economic sense; it is a larger price move in a larger part of the basket. The like-for-like rows are diagnostics for this note and are not added to the headline table.

"""
text = f"""# Phase 4c (simplified): speed, magnitude and persistence of CPI inflation responses

Separate from `docs/phase4c_report.md`; nothing there or in `outputs/phase4c/` is changed. Code: `bb_inflation/phase4c/simple.py`, `scripts/run_p4c_simple.py`, `tests/test_phase4c_simple.py`. Outputs: `outputs/phase4c_simple/`.

## What is standardised

Same model as before (B\\*, headline energy/food convention: nominal energy and food prices, relative prices endogenous; oil bridge elasticity 0.297, a calibrated assumption). Four shocks, hitting in Q0, followed for 12 quarters (Q0-Q11).
Units: annualised percentage points of CPI inflation; price level in % (sum of the annualised responses / 4). "After 3 years" is the cumulative effect over Q0-Q11, i.e. 12 quarters; the full report's price-level numbers span 13 quarters and are therefore slightly larger.

{md(defs)}

**These shocks are illustrative, not economically equivalent**: a 10% Brent move raises CPI energy by only about 2.9%, a 10% food-price move raises CPI food by 10%, the wage shock is one quarter of +1pp, and the GSCPI shock is a standard deviation of an index. A larger response says nothing about which driver matters more in practice; that depends on how large and how persistent such shocks actually are.

## Headline: B\\*-2026 (90% parameter bands)

{md(T_HEAD)}

![CPI inflation response](../outputs/phase4c_simple/simple_cpi_inflation_response.png)

*Food sensitivity row.* The row "Food, SENSITIVITY" is not B\\*: it repeats the food shock with a price equation whose food block has lags 0 to 3 instead of 0 to 4 (only the price equation is re-fitted, same sample and restrictions; the other equations are B\\*-2026). It is there because the Q4 rebound in the B\\* food row comes from the lag-4 coefficient (Clarification 2). Its band comes from that fit's own HAC covariance, so it is comparable in kind, not in construction, with the B\\* rows. With lag 4 removed: peak {cell(DG.SENS_KEY, V26, 'peak response (pp)', 2, band=False)}pp (B\\*: {cell('food', V26, 'peak response (pp)', 2, band=False)}pp), persistence {pers_cell(DG.SENS_KEY, V26, band=False)}, {rebound_cell(DG.SENS_KEY, V26, band=False).split(';')[0]}, price level after 3 years {cell(DG.SENS_KEY, V26, 'price level after 12 quarters (%)', 2, band=False)}% (B\\*: {cell('food', V26, 'price level after 12 quarters (%)', 2, band=False)}%). Removing lag 4 removes the point-estimate echo but not the rebounds across draws ({g(DG.SENS_KEY, V26, SM.REBOUND)['mean over draws']:.0%} of draws against {g('food', V26, SM.REBOUND)['mean over draws']:.0%} in B\\*): uncertainty in the remaining lag coefficients still produces a rebound in about a third of draws, so the path shape beyond Q0 stays uncertain either way. The headline food row remains the B\\* one.

*Persistence column.* Number of quarters from the peak until the CPI inflation response first falls below 50% of its peak (peak in Q1 and first below half in Q5 = 4 quarters). "Not reached within 12Q" means the response is still at or above half its peak at the end of the 12-quarter horizon, so it has not dissipated as far as this horizon shows. The next column **flags responses that fall below half the peak and later come back to at least half of it** within the horizon: for those the persistence figure alone overstates how quickly the effect fades. Percentages are the share of the 2000 coefficient draws in which the flag applies; persistence bands use the draws that do fall below half the peak (draws that never do are counted in "not reached in x% of draws").

## Reading the three questions

1. **Speed.** Energy, food and supply-chain shocks act almost immediately: the Q0 response is already {cell('energy', V26, 'Q0 response (pp)', 2, band=False)}pp (energy), {cell('food', V26, 'Q0 response (pp)', 2, band=False)}pp (food) and {cell('supply', V26, 'Q0 response (pp)', 2, band=False)}pp (supply chains), because their prices enter the CPI equation in the same quarter. The wage shock builds more slowly:
   {cell('wages', V26, 'Q0 response (pp)', 2, band=False)}pp in Q0 and {cell('wages', V26, 'Q1 response (pp)', 2, band=False)}pp in Q1.
2. **Magnitude.** Peaks are {cell('energy', V26, 'peak response (pp)', 2, band=False)}pp (energy), {cell('food', V26, 'peak response (pp)', 2, band=False)}pp (food), {cell('wages', V26, 'peak response (pp)', 2, band=False)}pp (wages) and {cell('supply', V26, 'peak response (pp)', 2, band=False)}pp (supply chains), for the shock sizes above only. Peaks are in annualised terms for one quarter; the price-level column shows what accumulates.
3. **Persistence and price level.** Energy: {pers_cell('energy', V26, band=False)} after the peak (no rebound), price level {cell('energy', V26, 'price level after 12 quarters (%)', 2, band=False)}%. Supply chains: {pers_cell('supply', V26, band=False)} after the peak, price level {cell('supply', V26, 'price level after 12 quarters (%)', 2, band=False)}%, but the flag applies in {g('supply', V26, SM.REBOUND)['mean over draws']:.0%} of draws. Wages: {pers_cell('wages', V26, band=False)} from the peak at the point estimate, with a price-level effect of {cell('wages', V26, 'price level after 12 quarters (%)', 2, band=False)}%; the wage response is jagged, falls below half its peak and returns to it in {g('wages', V26, SM.REBOUND)['mean over draws']:.0%} of draws, so the point estimate understates how long it can last, and the timing of its peak is flat between Q1 and Q3.
   Food: persistence {pers_cell('food', V26, band=False)} but **flagged** (back above half-peak in Q{g('food', V26, SM.REBOUND_Q).point:.0f}; {g('food', V26, SM.REBOUND)['mean over draws']:.0%} of draws), with a cumulative effect of {cell('food', V26, 'price level after 12 quarters (%)', 2, band=False)}% for a 10% rise in CPI food, about {food.sum() / 4 / 10 * 100:.0f}% of the food shock's size and more than food's CPI weight (roughly 14%), which the authors also found (second-round effects).
   No response is "not reached" at the point estimate: all four fall below half their peak within the horizon.

**One caution on food.** The headline persistence of 1 quarter is misleading: the food response has an echo four quarters later (Q4: {food.loc[4]:.1f}pp, {q4[V26]:.0f}% of the Q0 peak in B\\*-2026; {q4[V23]:.0f}% in B\\*-2023 and {q4[V19]:.0f}% in B\\*-2019), which is why it is flagged. It comes from the lag-4 food coefficient, 0.078 in B\\*-2026 and 0.014 in B\\*-2019, next to a negative lag-3 coefficient (-0.061): a four-quarter alternating pattern that the pandemic years introduced; it is most likely a specification artefact (Clarification 2 below).
Read the food path beyond Q0 as less reliable than its cumulative effect.

## Robustness: B\\*-2019 and B\\*-2023

{md(T_ROB)}

Differences from B\\*-2026 (joint coefficient draws, so the overlap of the samples is respected; 90% band and two-sided p):

{md(T_DIF)}

The qualitative answers are the same in all three samples. The differences that stand out run in the same direction as the full report: a larger wage price-level effect in the later samples (+0.11pp, p = 0.11), and smaller food (-0.73pp, p = 0.22) and supply-chain effects; none is significant at 10%. The B\\*-2019 supply-chain result rests on low-amplitude pre-pandemic GSCPI variation (§3.3 of the full report). Between B\\*-2023 and B\\*-2026 nothing changes.

{CLAR}## What this simplification drops

The expectations paths and wage responses to these shocks, the V/U and expectations shocks, the temporary oil episodes, the authors' relative-price convention (wage responses are larger under it), the authors' own model, persistence beyond 12 quarters and the formal tests of coefficient stability. All remain in the full report (`docs/phase4c_report.md`) and workbook.
"""
(PROJECT_ROOT / "docs" / "phase4c_simple.md").write_text(text, encoding="utf-8")
print(T_HEAD.to_string())
print(T_DIF.to_string())
