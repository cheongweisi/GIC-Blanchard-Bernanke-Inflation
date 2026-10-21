# Model B*: the four equations written out

Scalar form of the structural SVAR-X in [svarx_Bstar_note.md](svarx_Bstar_note.md). Notation follows that note: $\mathbf{y}_t=(g^w_t,\pi_t,\pi^{e,L}_t,\pi^{e,S}_t)'$, with exogenous drivers $\mathbf{x}_t$ as in its section 1. Each equation is estimated one at a time by restricted least squares, with four lags and a homogeneity (sum-to-one) restriction in each equation. Units follow section 7 of the note: $g^w$, $\pi$, $g^{\mathrm{rpe}}$ and $g^{\mathrm{rpf}}$ are qoq annualised; $\pi^{e,S}$ and $\pi^{e,L}$ are levels of an annual rate.

The coefficient symbols for the lag and exogenous terms ($\delta,\theta,\psi,\eta,\nu,\chi,\xi,\gamma,\rho,\sigma,\lambda,\mu$) are labels chosen for this file; the note itself only names $a_{ij}$, $\phi_i$ and $\kappa_i$. The last section maps every coefficient to its matrix entry in the note.

---

## Equation 1: Nominal wage inflation

$$
\boxed{
\begin{aligned}
g^{w}_{t} &= c_{g^{w}}
  + \sum_{i=1}^{4}\phi_{i}\,g^{w}_{t-i}
  + \sum_{i=1}^{4}\kappa_{i}\,\pi^{e,S}_{t-i} \\
&\quad + \sum_{i=1}^{4}\delta_{w,i}\,(V/U)_{t-i}
  + \sum_{i=1}^{4}\theta_{w,i}\,\mathrm{cu}_{t-i}
  + \lambda_{w}\,\bar{g}^{\,\mathrm{pty}}_{t-1} \\
&\quad + \mu_{1}\,D^{\mathrm{20Q2}}_{t}
  + \mu_{2}\,D^{\mathrm{20Q3}}_{t}
  + \varepsilon^{w}_{t}
\end{aligned}}
\tag{1}
$$

Homogeneity restriction:

$$
\sum_{i=1}^{4}\phi_i+\sum_{i=1}^{4}\kappa_i=1
$$

Wage growth depends on its own past (persistence), short-run inflation expectations, labour-market tightness, the catch-up term (workers recovering lost purchasing power) and trend productivity. There is no contemporaneous endogenous term, so wages respond to everything with a one-quarter lag.

| Variable | Definition |
|---|---|
| $g^{w}_t$ | Nominal wage growth (ECI wages and salaries, private industry, SA), % qoq annualised |
| $\pi^{e,S}_t$ | Short-run expected inflation (Cleveland Fed, 1-year), level in % per year |
| $(V/U)_t$ | Job openings per unemployed worker (JOLTS), a measure of labour-market tightness |
| $\mathrm{cu}_t$ | Wage catch-up term: $\tfrac14\sum_{k=0}^{3}\pi_{t-k}-\pi^{e,S}_{t-4}$, in percentage points |
| $\bar{g}^{\,\mathrm{pty}}_t$ | Trend productivity growth (8-quarter moving average), % annualised |
| $D^{\mathrm{20Q2}}_t,\ D^{\mathrm{20Q3}}_t$ | Dummies for 2020Q2 and 2020Q3 |
| $c_{g^w}$ | Constant |
| $\varepsilon^{w}_t$ | Wage-equation disturbance |

---

## Equation 2: CPI inflation

$$
\boxed{
\begin{aligned}
\pi_{t} &= c_{\pi}
  + a_{21}\,g^{w}_{t}
  + \sum_{i=1}^{4}\psi_{i}\,g^{w}_{t-i}
  + \sum_{i=1}^{4}\rho^{\pi}_{i}\,\pi_{t-i} \\
&\quad + \sum_{i=0}^{4}\eta_{i}\,g^{\mathrm{rpe}}_{t-i}
  + \sum_{i=0}^{4}\nu_{i}\,g^{\mathrm{rpf}}_{t-i} \\
&\quad + \sigma\,\bar{s}_{t}
  + \lambda_{\pi}\,\bar{g}^{\,\mathrm{pty}}_{t}
  + \varepsilon^{\pi}_{t}
\end{aligned}}
\tag{2}
$$

Homogeneity restriction:

$$
\sum_{i=1}^{4}\rho^{\pi}_i+a_{21}+\sum_{i=1}^{4}\psi_i=1
$$

Price inflation is a markup over labour costs, with some inertia from past inflation, plus supply shocks (energy, food, shortages) and productivity. There is no direct expectations term: expectations affect prices only through wages.

| Variable | Definition |
|---|---|
| $\pi_t$ | CPI inflation (CPI-U all items, SA, last month of the quarter), % qoq annualised |
| $g^{w}_t$ | Nominal wage growth (ECI), % qoq annualised; enters both currently and lagged |
| $g^{\mathrm{rpe}}_t$ | Growth of the relative price of energy (CPI energy relative to the ECI), % qoq annualised |
| $g^{\mathrm{rpf}}_t$ | Growth of the relative price of food (CPI food relative to the ECI), % qoq annualised |
| $\bar{s}_t$ | Supply-chain shortage term: GSCPI, two-quarter trailing mean $\tfrac12(s_t+s_{t-1})$, in standard deviations |
| $\bar{g}^{\,\mathrm{pty}}_t$ | Trend productivity growth (8-quarter moving average), % annualised |
| $a_{21}$ | Contemporaneous pass-through of wage growth to CPI inflation (from $A_0$) |
| $c_\pi$ | Constant |
| $\varepsilon^{\pi}_t$ | Price-equation disturbance |

---

## Equation 3: Long-run inflation expectations

$$
\boxed{
\pi^{e,L}_{t} = a_{32}\,\pi_{t}
  + \sum_{i=1}^{4}\chi_{i}\,\pi_{t-i}
  + \sum_{i=1}^{4}\rho^{L}_{i}\,\pi^{e,L}_{t-i}
  + \varepsilon^{L}_{t}}
\tag{3}
$$

Homogeneity restriction:

$$
\sum_{i=1}^{4}\rho^{L}_i+a_{32}+\sum_{i=1}^{4}\chi_i=1
$$

Long-run expectations are highly persistent and adjust slowly to current and past CPI inflation. There is no constant and no exogenous term.

| Variable | Definition |
|---|---|
| $\pi^{e,L}_t$ | Long-run expected inflation (Cleveland Fed, 10-year), level in % per year |
| $\pi_t$ | CPI inflation, % qoq annualised; enters both currently and lagged |
| $a_{32}$ | Contemporaneous response of long-run expectations to CPI inflation (from $A_0$) |
| $\varepsilon^{L}_t$ | Long-run-expectations disturbance |

---

## Equation 4: Short-run inflation expectations

$$
\boxed{
\begin{aligned}
\pi^{e,S}_{t} &= a_{42}\,\pi_{t}
  + a_{43}\,\pi^{e,L}_{t}
  + \sum_{i=1}^{4}\xi_{i}\,\pi_{t-i} \\
&\quad + \sum_{i=1}^{4}\gamma_{i}\,\pi^{e,L}_{t-i}
  + \sum_{i=1}^{4}\rho^{S}_{i}\,\pi^{e,S}_{t-i}
  + \varepsilon^{S}_{t}
\end{aligned}}
\tag{4}
$$

Homogeneity restriction:

$$
\sum_{i=1}^{4}\rho^{S}_i+a_{43}+\sum_{i=1}^{4}\gamma_i+a_{42}+\sum_{i=1}^{4}\xi_i=1
$$

Short-run expectations track the long-run level (the anchor) and respond to CPI inflation, with their own persistence. There is no constant and no exogenous term.

| Variable | Definition |
|---|---|
| $\pi^{e,S}_t$ | Short-run expected inflation (Cleveland Fed, 1-year), level in % per year |
| $\pi^{e,L}_t$ | Long-run expected inflation (Cleveland Fed, 10-year), level in % per year; enters both currently and lagged |
| $\pi_t$ | CPI inflation, % qoq annualised; enters both currently and lagged |
| $a_{42}$ | Contemporaneous response of $\pi^{e,S}$ to CPI inflation (from $A_0$) |
| $a_{43}$ | Contemporaneous response of $\pi^{e,S}$ to $\pi^{e,L}$ (from $A_0$) |
| $\varepsilon^{S}_t$ | Short-run-expectations disturbance |

---

## Mapping of coefficients to the matrices in the note

$A_0$ holds the contemporaneous links (written $-a_{ij}$ off the diagonal), $A_i$ the endogenous lags and $B_j$ the exogenous terms (columns ordered as $\mathbf{x}_t$). $[M]_{jk}$ is row $j$, column $k$ of $M$.

| Equation | Coefficient | Matrix entry | Term |
|---|---|---|---|
| (1) wage | $c_{g^w}$ | $\mathbf{c}_1$ | constant |
| | $\phi_i$ | $[A_i]_{11}$ | own lag of $g^w$ |
| | $\kappa_i$ | $[A_i]_{14}$ | lagged $\pi^{e,S}$ |
| | $\delta_{w,i}$ | $[B_i]_{12}$, $i=1..4$ | lagged $(V/U)$ |
| | $\theta_{w,i}$ | $[B_i]_{13}$, $i=1..4$ | lagged catch-up term |
| | $\lambda_w$ | $[B_1]_{11}$ | trend productivity, lag 1 only |
| | $\mu_1,\ \mu_2$ | $[B_0]_{17},\ [B_0]_{18}$ | 2020Q2 and 2020Q3 dummies |
| (2) CPI | $c_\pi$ | $\mathbf{c}_2$ | constant |
| | $a_{21}$ | $-[A_0]_{21}$ | current wage growth |
| | $\psi_i$ | $[A_i]_{21}$ | lagged wage growth |
| | $\rho^{\pi}_i$ | $[A_i]_{22}$ | own lag of $\pi$ |
| | $\eta_i$ | $[B_i]_{24}$, $i=0..4$ | relative energy price growth |
| | $\nu_i$ | $[B_i]_{25}$, $i=0..4$ | relative food price growth |
| | $\sigma$ | $[B_0]_{26}$ | shortage term, lag 0 only |
| | $\lambda_\pi$ | $[B_0]_{21}$ | trend productivity, lag 0 only |
| (3) long-run exp. | $a_{32}$ | $-[A_0]_{32}$ | current CPI inflation |
| | $\chi_i$ | $[A_i]_{32}$ | lagged CPI inflation |
| | $\rho^{L}_i$ | $[A_i]_{33}$ | own lag of $\pi^{e,L}$ |
| (4) short-run exp. | $a_{42}$ | $-[A_0]_{42}$ | current CPI inflation |
| | $a_{43}$ | $-[A_0]_{43}$ | current $\pi^{e,L}$ |
| | $\xi_i$ | $[A_i]_{42}$ | lagged CPI inflation |
| | $\gamma_i$ | $[A_i]_{43}$ | lagged $\pi^{e,L}$ |
| | $\rho^{S}_i$ | $[A_i]_{44}$ | own lag of $\pi^{e,S}$ |
