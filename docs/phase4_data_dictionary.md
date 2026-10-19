# Phase 4 data dictionary

Pull `p4_20261018T051241Z` (retrieved 2026-10-18T05:12:41 UTC, SHA-256 per file in `data_cache/macrobond/phase4/p4_20261018T051241Z/manifest.json`; pinned in `bb_inflation/scenarios/pin.py`).
Model estimation data are NOT from this pull: they remain the Phase 3 pinned pull plus the flagged V/U bridge (Model B*). This pull supplies oil series and information dated after the estimation sample (2026Q3 partial quarter).
All 46 quarters from 2015Q1 to 2026Q2 of CPI, CPI energy, CPI food, Cleveland 1y/10y and GSCPI agree with the pinned pull to 1e-9 (`outputs/phase4/data_qa_vs_pinned_pull.csv`).

Conventions (as in Phase 3): CPI and Cleveland expectations = value of the last month of the quarter; GSCPI = quarterly mean; nominal CPI energy / food growth = 400 dln of the quarter-end index.
Brent: World Bank monthly average (history); futures: latest settlement per delivery month on 2026-10-16 (daily closes since 2025-10 stored); Oct 2026 = EIA STEO estimate; Nov 2026 = midpoint of Oct and Dec; Dec 2026-Dec 2029 = live contracts.
Futures contracts for each of the 39 delivery months Oct 2026-Dec 2029 are stored (`bz<year><month code>_cl`); only the first two are listed below.

| Ticker | Role | Frequency | Observations | Description |
|---|---|---|---|---|
| `wocaes0935` | brent_wb_monthly | monthly | 1960-01-01 to 2026-09-01 | World, World Bank, Crude Oil, Brent, Average Price, End of Period, USD |
| `eiasteo0002` | eia_steo_brent_monthly | monthly | 1990-01-01 to 2027-12-01 | United States, EIA, Short Term Energy Outlook, Crude Oil, Brent Spot Average, Estimate, USD |
| `steo_brepuus_q` | eia_steo_brent_quarterly | quarterly | 1990-01-01 to 2027-10-01 | United States, EIA, Short Term Energy Outlook, Crude Oil, Brent Spot Average, Estimate, USD |
| `b_c1_cl` | brent_front_daily | daily | 2025-10-01 to 2026-10-16 | Crude Oil, Future, ICE Brent Crude, 1st Position, Close, USD |
| `uscaes0301` | wti_spot_daily | daily | 2025-10-01 to 2026-10-15 | United States, Crude Oil, Cushing OK WTI Spot Price FOB, USD |
| `uspric2156` | cpi | monthly | 1947-01-01 to 2026-09-01 | United States, Consumer Price Index, All Urban Consumers, U.S. City Average, All Items, SA, Ind |
| `uspric2368` | cpi_energy | monthly | 1957-01-01 to 2026-09-01 | United States, Consumer Price Index, All Urban Consumers, U.S. City Average, Energy, SA, Index |
| `uspric2158` | cpi_food | monthly | 1947-01-01 to 2026-09-01 | United States, Consumer Price Index, All Urban Consumers, U.S. City Average, Food & Beverages,  |
| `wotrad0027` | gscpi | monthly | 1997-09-01 to 2026-09-01 | World, Foreign Trade, Global Supply Chain Pressure Index, Total, Index |
| `usfcst0101` | cleveland_1y | monthly | 1982-01-01 to 2026-10-01 | United States, Federal Reserve Bank of Cleveland, Inflation Expectations, Expected Inflation, E |
| `usfcst0110` | cleveland_10y | monthly | 1982-01-01 to 2026-10-01 | United States, Federal Reserve Bank of Cleveland, Inflation Expectations, Expected Inflation, E |
| `uslama1304` | jolts_openings | monthly | 2000-12-01 to 2026-08-01 | United States, Labor Market Dynamics, Labor Turnover, Openings (Worker Flows), Nonfarm, Total,  |
| `uslama1795` | unemployment_level_sa | monthly | 1948-01-01 to 2026-09-01 | United States, Unemployment, National, 16 Years & Over, SA |
| `uslama0202` | productivity_q | quarterly | 1947-01-01 to 2026-04-01 | United States, Productivity, Costs & Hours Worked, Labor Productivity & Costs, Nonfarm Business |
| `uslama4604` | eci_wages_q | quarterly | 1980-01-01 to 2026-04-01 | United States, Productivity, Costs & Hours Worked, Employment Cost Index, Wages & Salaries, Pri |
| `bz2026z_cl` | bz_202612 | daily | 2025-10-01 to 2026-10-16 | Crude Oil, Future, Brent Last Day, December, 2026, Close, USD |
| `bz2027f_cl` | bz_202701 | daily | 2025-10-01 to 2026-10-16 | Crude Oil, Future, Brent Last Day, January, 2027, Close, USD |
