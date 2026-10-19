"""Macrobond series used by the model: authors' raw column -> Macrobond ticker(s) and conventions.

Tickers were found by searching Macrobond (scripts/mb_search.py), using the BLS series codes carried in the
`UsBlsCode` metadata where available, then verified numerically against the authors' data
(see docs/data_dictionary.md and tests/test_macrobond_reconciliation.py).

`agg` is the monthly->quarterly rule that reproduces the authors' dataset:
  "last"   value of the last month of the quarter (CPI, Cleveland expectations; NOT a quarterly average)
  "mean"   mean of the three months (JOLTS, unemployment level, GSCPI)
  "native" series is already quarterly
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesDef:
    column: str                 # authors' raw column name
    tickers: tuple[str, ...]    # Macrobond primary names (two for a ratio: numerator, denominator)
    agg: str
    description: str
    unit: str
    sa: str                     # seasonal adjustment
    source_code: str            # official code at the originating agency
    note: str = ""


REGISTRY: dict[str, SeriesDef] = {d.column: d for d in [
    SeriesDef("CPIAUCSL", ("uspric2156",), "last", "CPI-U, all items, US city average", "Index 1982-84=100",
              "SA", "BLS CUSR0000SA0", "FRED CPIAUCSL"),
    SeriesDef("CPIENGSL", ("uspric2368",), "last", "CPI-U, energy, US city average", "Index 1982-84=100",
              "SA", "BLS CUSR0000SA0E", "FRED CPIENGSL"),
    SeriesDef("CPIUFDSL", ("uspric2158",), "last", "CPI-U, food, US city average", "Index 1982-84=100",
              "SA", "BLS CUSR0000SAF1", "FRED CPIUFDSL"),
    SeriesDef("OPHNFB", ("uslama0202",), "native", "Nonfarm business labor productivity (output per hour)",
              "Index 2017=100 (authors' file: 2012=100; only growth is used)", "SA", "BLS PRS85006093",
              "FRED OPHNFB"),
    SeriesDef("ECIWAG", ("uslama4604",), "native",
              "Employment Cost Index, wages & salaries, private industry", "Index Dec 2005=100", "SA",
              "BLS CIS2020000000000I", "FRED ECIWAG; Macrobond history starts 1980Q1"),
    SeriesDef("VOVERU", ("uslama1304", "uslama1795"), "mean",
              "V/U = JOLTS job openings (nonfarm total) / unemployed (16+)", "Ratio", "SA",
              "BLS JTS000000000000000JOL / LNS13000000",
              "Ratio of quarterly means. JOLTS starts 2000-12; authors use Barnichon (2010) before 2001"),
    SeriesDef("EXPINF1YR", ("usfcst0101",), "last", "Cleveland Fed expected inflation, 1 year", "Percent",
              "NSA", "FRB Cleveland", "FRED EXPINF1YR; monthly, last month of quarter"),
    SeriesDef("EXPINF10YR", ("usfcst0110",), "last", "Cleveland Fed expected inflation, 10 year", "Percent",
              "NSA", "FRB Cleveland", "FRED EXPINF10YR; monthly, last month of quarter"),
    SeriesDef("GSCPI", ("wotrad0027",), "mean", "NY Fed Global Supply Chain Pressure Index", "Std. dev. from mean",
              "n/a", "FRB New York", "Substitute for the Google Trends 'shortage' index; revised monthly"),
]}

# Not on Macrobond: Google Trends "shortage" (authors' SHORTAGE), Barnichon (2010) composite help-wanted index
# (V/U before 2001) and the BLS total-compensation ECI splice used for ECIWAG before 2001.
NOT_ON_MACROBOND = ("SHORTAGE", "VOVERU<2001", "ECIWAG<2001 (authors' splice)")

# Date at which Macrobond's revision history reproduces the authors' dataset: after the 7 Sep 2023 productivity
# revision and before the 28 Sep 2023 BEA annual revision (the authors' package is dated 12 Oct 2023, but its
# productivity series pre-dates that revision).
AUTHORS_VINTAGE = (2023, 9, 15)
SPLICE_LAST_AUTHORS_QUARTER = "2000Q4"   # authors' V/U and ECI history is used through this quarter
