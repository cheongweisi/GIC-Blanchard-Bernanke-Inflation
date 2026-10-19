# Data dictionary (Phase 2)

Generated 2026-10-17 by `scripts/run_phase2a.py`. Series metadata is live from Macrobond; the "current vintage" data are the stamped,
hash-checked pull `pull_20261016T061219Z` (retrieved 2026-10-16T06:12:19 UTC, SHA-256 662280702e9b6a7d...).
Do not edit by hand.

## 1. Series retrieved from Macrobond

| Model column   | Macrobond ticker(s)     | Description                                                 | Agency code                             | Unit                                                          | SA   | Native freq   | To quarterly          | First obs (native)   | Latest obs (native)   | Latest quarter in model data   | Observed release lag (days after period end)   | Notes                                                                                    |
|:---------------|:------------------------|:------------------------------------------------------------|:----------------------------------------|:--------------------------------------------------------------|:-----|:--------------|:----------------------|:---------------------|:----------------------|:-------------------------------|:-----------------------------------------------|:-----------------------------------------------------------------------------------------|
| CPIAUCSL       | uspric2156              | CPI-U, all items, US city average                           | BLS CUSR0000SA0                         | Index 1982-84=100                                             | SA   | monthly       | last month of quarter | 1947-01              | 2026-09               | 2026Q3                         | 15                                             | FRED CPIAUCSL                                                                            |
| CPIENGSL       | uspric2368              | CPI-U, energy, US city average                              | BLS CUSR0000SA0E                        | Index 1982-84=100                                             | SA   | monthly       | last month of quarter | 1957-01              | 2026-09               | 2026Q3                         | 15                                             | FRED CPIENGSL                                                                            |
| CPIUFDSL       | uspric2158              | CPI-U, food, US city average                                | BLS CUSR0000SAF1                        | Index 1982-84=100                                             | SA   | monthly       | last month of quarter | 1947-01              | 2026-09               | 2026Q3                         | 15                                             | FRED CPIUFDSL                                                                            |
| OPHNFB         | uslama0202              | Nonfarm business labor productivity (output per hour)       | BLS PRS85006093                         | Index 2017=100 (authors' file: 2012=100; only growth is used) | SA   | quarterly     | none                  | 1947-01              | 2026-04               | 2026Q2                         | 38                                             | FRED OPHNFB                                                                              |
| ECIWAG         | uslama4604              | Employment Cost Index, wages & salaries, private industry   | BLS CIS2020000000000I                   | Index Dec 2005=100                                            | SA   | quarterly     | none                  | 1980-01              | 2026-04               | 2026Q2                         | 32                                             | FRED ECIWAG; Macrobond history starts 1980Q1                                             |
| VOVERU         | uslama1304 / uslama1795 | V/U = JOLTS job openings (nonfarm total) / unemployed (16+) | BLS JTS000000000000000JOL / LNS13000000 | Ratio                                                         | SA   | monthly       | mean of 3 months      | 2000-12              | 2026-08               | 2026Q2                         | 30                                             | Ratio of quarterly means. JOLTS starts 2000-12; authors use Barnichon (2010) before 2001 |
| EXPINF1YR      | usfcst0101              | Cleveland Fed expected inflation, 1 year                    | FRB Cleveland                           | Percent                                                       | NSA  | monthly       | last month of quarter | 1982-01              | 2026-10               | 2026Q3                         | within period (nowcast)                        | FRED EXPINF1YR; monthly, last month of quarter                                           |
| EXPINF10YR     | usfcst0110              | Cleveland Fed expected inflation, 10 year                   | FRB Cleveland                           | Percent                                                       | NSA  | monthly       | last month of quarter | 1982-01              | 2026-10               | 2026Q3                         | within period (nowcast)                        | FRED EXPINF10YR; monthly, last month of quarter                                          |
| GSCPI          | wotrad0027              | NY Fed Global Supply Chain Pressure Index                   | FRB New York                            | Std. dev. from mean                                           | n/a  | monthly       | mean of 3 months      | 1997-09              | 2026-09               | 2026Q3                         | 7                                              | Substitute for the Google Trends 'shortage' index; revised monthly                       |

Observed release lag = first date the latest observation appears in Macrobond's vintage history minus the end of its
observation period (resolution about one day). Cleveland Fed values for the current month are published during
that month (nowcasts), so for the quarter-end convention below the latest *complete* quarter is the last one with
a March/June/September/December value.

## 2. Model variables and transformations (identical to the authors' Stata code)

| Variable | Definition |
|---|---|
| gcpi | 400 * dln(CPIAUCSL), quarter-end-month CPI |
| gw | 400 * dln(ECIWAG) |
| gpty / magpty | 400 * dln(OPHNFB); magpty = 8-quarter moving average of gpty (current + 7 lags) |
| grpe, grpf | 400 * dln(CPIENGSL / ECIWAG), 400 * dln(CPIUFDSL / ECIWAG) |
| vu | VOVERU (JOLTS openings / unemployed; Barnichon before 2001) |
| cf1, cf10 | Cleveland Fed 1-year and 10-year expected inflation, quarter-end month |
| shortage | Google Trends 'shortage' (authors); 5 before 2004Q1. Phase 2b replaces it with GSCPI (fill -0.035 before 1997Q4 as in authors' Table A8 variant) |
| diffcpicf (catch-up) | mean(gcpi_t..gcpi_t-3) - cf1_t-4 |

## 3. Conventions discovered by reconciliation (not stated in the authors' documentation)

* The authors' CPI, CPI energy, CPI food, Cleveland 1y and 10y series are the **value of the last month of the quarter**
  (not the quarterly average that the data dictionary's "Quarterly" label suggests). Quarterly averages differ from the authors' data by up to 3 index points.
* V/U is the **ratio of quarterly means** of JOLTS openings and the unemployment level.
* GSCPI is the mean of the three monthly values (authors' `clean_shortages.R`).
* Productivity and ECI are native quarterly.
* The authors' dataset is a vintage (series pulled at different dates between 7 and 27 Sep 2023 for productivity, early
  Oct 2023 for GSCPI). Macrobond's revision history, queried as of **2023-09-15**, reproduces it (section 4).
* Macrobond history starts 1980Q1 for ECI wages & salaries, 2000-12 for JOLTS openings, 1997-09 for GSCPI.

## 4. Not available on Macrobond

* SHORTAGE
* VOVERU<2001
* ECIWAG<2001 (authors' splice)

Handling (decision of 2026-10-16): V/U and ECI for 1989Q1-2000Q4 are taken from the authors' public `Regression_Data`,
Macrobond from 2001Q1 (ECI chain-linked at the join). The Google 'shortage' series is replaced by GSCPI in Phase 2b.

## 5. Reconciliation with the authors' dataset (Phase 2a)

### 5.1 Series level

| series     | compared_on      | window        | macrobond              |   n |   mean_abs |   max_abs | at_max   |     bias |
|:-----------|:-----------------|:--------------|:-----------------------|----:|-----------:|----------:|:---------|---------:|
| CPIAUCSL   | level            | 1990Q1-2023Q2 | as of authors' vintage | 134 |    0.00000 |   0.00000 | 2022Q1   |  0.00000 |
| CPIAUCSL   | level            | 1990Q1-2023Q2 | current vintage        | 134 |    0.01222 |   0.22900 | 2022Q2   |  0.00223 |
| CPIENGSL   | level            | 1990Q1-2023Q2 | as of authors' vintage | 134 |    0.00000 |   0.00000 | 1990Q1   |  0.00000 |
| CPIENGSL   | level            | 1990Q1-2023Q2 | current vintage        | 134 |    0.15713 |   3.00000 | 2022Q1   |  0.07252 |
| CPIUFDSL   | level            | 1990Q1-2023Q2 | as of authors' vintage | 134 |    0.00000 |   0.00000 | 2020Q1   |  0.00000 |
| CPIUFDSL   | level            | 1990Q1-2023Q2 | current vintage        | 134 |    0.02067 |   0.44600 | 2023Q1   | -0.00564 |
| OPHNFB     | growth (400*dln) | 1990Q1-2023Q2 | as of authors' vintage | 134 |    0.00000 |   0.00000 | 1990Q1   |  0.00000 |
| OPHNFB     | growth (400*dln) | 1990Q1-2023Q2 | current vintage        | 134 |    0.34581 |   3.03496 | 2020Q2   |  0.09057 |
| ECIWAG     | growth (400*dln) | 2001Q2-2023Q2 | as of authors' vintage |  89 |    0.00000 |   0.00000 | 2021Q2   |  0.00000 |
| ECIWAG     | growth (400*dln) | 2001Q2-2023Q2 | current vintage        |  89 |    0.02430 |   0.29250 | 2019Q2   |  0.00000 |
| VOVERU     | level            | 2001Q1-2023Q2 | as of authors' vintage |  90 |    0.00004 |   0.00016 | 2022Q3   |  0.00000 |
| VOVERU     | level            | 2001Q1-2023Q2 | current vintage        |  90 |    0.00230 |   0.04248 | 2023Q2   | -0.00090 |
| EXPINF1YR  | level            | 1990Q1-2023Q2 | as of authors' vintage | 134 |    0.00003 |   0.00005 | 2022Q3   | -0.00000 |
| EXPINF1YR  | level            | 1990Q1-2023Q2 | current vintage        | 134 |    0.00000 |   0.00000 | 2020Q4   |  0.00000 |
| EXPINF10YR | level            | 1990Q1-2023Q2 | as of authors' vintage | 134 |    0.00002 |   0.00005 | 1993Q3   | -0.00000 |
| EXPINF10YR | level            | 1990Q1-2023Q2 | current vintage        | 134 |    0.00000 |   0.00000 | 2022Q1   | -0.00000 |
| GSCPI      | level            | 1998Q1-2023Q2 | as of authors' vintage | 102 |    0.01185 |   0.03355 | 1998Q4   | -0.00923 |
| GSCPI      | level            | 1998Q1-2023Q2 | current vintage        | 102 |    0.08518 |   0.32748 | 2001Q1   | -0.02701 |

### 5.2 Pre-2001 ECI: authors' splice versus Macrobond's own ECI wages & salaries history

| window                                           |   n |   mean_growth_authors |   mean_growth_macrobond |   mean_abs_diff |   corr |
|:-------------------------------------------------|----:|----------------------:|------------------------:|----------------:|-------:|
| 1990Q1-2000Q4 (authors' splice vs Macrobond W&S) |  44 |                 3.482 |                   3.357 |           0.610 |  0.579 |
| 2001Q1-2023Q2 (authors vs current Macrobond)     |  90 |                 2.743 |                   2.749 |           0.029 |  0.996 |

### 5.3 End-to-end: sum of estimated coefficients (authors' specification, 1990Q1-2023Q2)

| run         | equation   | variable   |   authors |   macrobond @ authors' vintage |   macrobond current vintage |
|:------------|:-----------|:-----------|----------:|-------------------------------:|----------------------------:|
| full sample | gw         | gw         |    0.5437 |                         0.5436 |                      0.5326 |
| full sample | gw         | cf1        |    0.4563 |                         0.4564 |                      0.4674 |
| full sample | gw         | vu         |    0.6879 |                         0.6879 |                      0.7077 |
| full sample | gw         | diffcpicf  |   -0.0211 |                        -0.0211 |                     -0.0153 |
| full sample | gw         | magpty     |    0.0383 |                         0.0383 |                      0.0511 |
| full sample | gcpi       | gw         |    0.6674 |                         0.6674 |                      0.7027 |
| full sample | gcpi       | magpty     |   -0.1441 |                        -0.1441 |                     -0.1692 |
| full sample | gcpi       | gcpi       |    0.3326 |                         0.3326 |                      0.2973 |
| full sample | gcpi       | grpe       |    0.0660 |                         0.0660 |                      0.0685 |
| full sample | gcpi       | grpf       |    0.1261 |                         0.1261 |                      0.1318 |
| full sample | gcpi       | shortage   |    0.0188 |                         0.0188 |                      0.0223 |
| full sample | cf1        | cf1        |    0.2948 |                         0.2948 |                      0.2930 |
| full sample | cf1        | gcpi       |    0.1358 |                         0.1358 |                      0.1361 |
| full sample | cf1        | cf10       |    0.5694 |                         0.5694 |                      0.5710 |
| full sample | cf10       | gcpi       |    0.0247 |                         0.0247 |                      0.0247 |
| full sample | cf10       | cf10       |    0.9753 |                         0.9753 |                      0.9753 |
| pre-COVID   | gw         | gw         |    0.4600 |                         0.4600 |                      0.4568 |
| pre-COVID   | gw         | cf1        |    0.5400 |                         0.5400 |                      0.5432 |
| pre-COVID   | gw         | vu         |    0.6931 |                         0.6934 |                      0.6784 |
| pre-COVID   | gw         | diffcpicf  |   -0.0239 |                        -0.0239 |                     -0.0243 |
| pre-COVID   | gw         | magpty     |    0.0313 |                         0.0312 |                      0.0339 |
| pre-COVID   | gcpi       | gw         |    0.6674 |                         0.6674 |                      0.7027 |
| pre-COVID   | gcpi       | magpty     |   -0.1441 |                        -0.1441 |                     -0.1692 |
| pre-COVID   | gcpi       | gcpi       |    0.3326 |                         0.3326 |                      0.2973 |
| pre-COVID   | gcpi       | grpe       |    0.0660 |                         0.0660 |                      0.0685 |
| pre-COVID   | gcpi       | grpf       |    0.1261 |                         0.1261 |                      0.1318 |
| pre-COVID   | gcpi       | shortage   |    0.0188 |                         0.0188 |                      0.0223 |
| pre-COVID   | cf1        | cf1        |    0.3694 |                         0.3694 |                      0.3694 |
| pre-COVID   | cf1        | gcpi       |    0.1245 |                         0.1245 |                      0.1246 |
| pre-COVID   | cf1        | cf10       |    0.5061 |                         0.5061 |                      0.5060 |
| pre-COVID   | cf10       | gcpi       |    0.0248 |                         0.0248 |                      0.0247 |
| pre-COVID   | cf10       | cf10       |    0.9752 |                         0.9752 |                      0.9753 |

### 5.4 GSCPI versus the Google 'shortage' index

| window        |   n |   corr_levels |   corr_changes |   google_mean |   google_sd |   gscpi_mean |   gscpi_sd |
|:--------------|----:|--------------:|---------------:|--------------:|------------:|-------------:|-----------:|
| 2004Q1-2019Q4 |  64 |         0.044 |          0.220 |         5.021 |       1.332 |       -0.218 |      0.441 |
| 2020Q1-2023Q2 |  14 |         0.377 |          0.306 |        21.060 |      10.067 |        1.871 |      1.483 |
| 2004Q1-2023Q2 |  78 |         0.728 |          0.279 |         7.900 |       7.546 |        0.157 |      1.087 |
