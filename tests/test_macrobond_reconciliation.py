"""Phase 2a: Macrobond data, retrieved as of the authors' vintage, reproduce the authors' dataset.

These tests need the Macrobond desktop app (COM API); they are skipped when it is not available.
"""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from bb_inflation.data.macrobond_registry import AUTHORS_VINTAGE
from bb_inflation.data.transforms import build_model_data
from bb_inflation.estimation.replication import fit_full, fit_precovid

try:
    from bb_inflation.data.macrobond_loader import fetch_raw, splice_authors_history
    fetch_raw(dt.datetime(*AUTHORS_VINTAGE))
    HAVE_MB = True
except Exception:  # noqa: BLE001
    HAVE_MB = False

pytestmark = pytest.mark.skipif(not HAVE_MB, reason="Macrobond API not available")

# (column, start, tolerance on level or on annualised log growth, use growth?)
CHECKS = [("CPIAUCSL", "1990Q1", 1e-6, False), ("CPIENGSL", "1990Q1", 1e-6, False),
          ("CPIUFDSL", "1990Q1", 1e-6, False), ("OPHNFB", "1990Q1", 1e-6, True),
          ("ECIWAG", "2001Q2", 1e-6, True), ("VOVERU", "2001Q1", 5e-4, False),
          ("EXPINF1YR", "1990Q1", 1e-4, False), ("EXPINF10YR", "1990Q1", 1e-4, False),
          ("GSCPI", "1998Q1", 5e-2, False)]


@pytest.fixture(scope="module")
def mb():
    return fetch_raw(dt.datetime(*AUTHORS_VINTAGE))


@pytest.mark.parametrize("col,start,tol,growth", CHECKS)
def test_series_match_authors(mb, raw, col, start, tol, growth):
    a, m = raw[col], mb[col]
    if growth:
        a, m = 400 * np.log(a).diff(), 400 * np.log(m).diff()
    d = (m.loc[start:"2023Q2"] - a.loc[start:"2023Q2"]).dropna()
    assert len(d) >= 85
    assert d.abs().max() < tol, (col, d.abs().max(), d.abs().idxmax())


def test_end_to_end_coefficients(mb, raw, full, precovid):
    """Macrobond-built raw data (+ authors' pre-2001 V/U and ECI, + authors' Google 'shortage')
    reproduce the authors' estimates."""
    spliced = splice_authors_history(mb, raw)
    spliced["SHORTAGE"] = raw["SHORTAGE"]
    spliced = spliced.loc[:"2023Q2"]
    d = build_model_data(spliced)
    for name, ours, ref in (("full", fit_full(d), full), ("precovid", fit_precovid(d), precovid)):
        for eq in ("gw", "gcpi", "cf1", "cf10"):
            diff = ours[eq].coef - ref[eq].coef
            # individual V/U lag coefficients are ill-conditioned (collinear lags of opposite sign) and amplify the
            # float32 rounding in the authors' file; block sums are the economically meaningful quantities
            assert diff.abs().max() < 1e-2, (name, eq, diff.abs().max())
            for v in {n.rsplit("_L", 1)[0] for n in diff.index if "_L" in n}:
                block = [n for n in diff.index if n.startswith(v + "_L")]
                assert abs(diff[block].sum()) < 1e-3, (name, eq, v, diff[block].sum())
