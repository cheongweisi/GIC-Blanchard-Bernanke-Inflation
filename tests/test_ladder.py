"""Phase 2b ladder invariants (need the Macrobond app; skipped otherwise)."""
import datetime as dt

import pytest

from bb_inflation.data.macrobond_registry import AUTHORS_VINTAGE

try:
    from bb_inflation.data.macrobond_loader import fetch_raw
    from bb_inflation.validation import ladder as L
    fetch_raw(dt.datetime(*AUTHORS_VINTAGE))
    HAVE_MB = True
except Exception:  # noqa: BLE001
    HAVE_MB = False

pytestmark = pytest.mark.skipif(not HAVE_MB, reason="Macrobond API not available")


@pytest.fixture(scope="module")
def res(raw):
    by = {c.name[:2]: L.run_case(raw, c) for c in L.cases() if c.group in ("ladder", "vintage")}
    return by


def test_vintage_control_reproduces_authors(res):
    """Macrobond as of the authors' vintage with Google shortage = authors' results (all sums within 1e-3)."""
    a, b = res["L0"], res["V0"]
    for k in a:
        if k.startswith("sum ") or k.startswith("R2 "):
            assert abs(a[k] - b[k]) < 1e-3, k


def test_authors_gscpi_variant_is_table_A8(res):
    v1 = res["V1"]
    assert v1["sum gcpi:shortage"] == pytest.approx(0.271, abs=5e-4)
    assert v1["R2 gcpi"] == pytest.approx(0.940, abs=5e-4)


def test_macrobond_gscpi_at_authors_vintage_close_to_authors_file(res):
    v1, v2 = res["V1"], res["V2"]
    assert abs(v1["sum gcpi:shortage"] - v2["sum gcpi:shortage"]) < 0.02
    assert abs(v1["sum gcpi:gw"] - v2["sum gcpi:gw"]) < 0.02


def test_gscpi_swap_is_the_big_step(res):
    """Swapping Google->GSCPI moves the price-equation shortage sum by an order of magnitude more than all data swaps."""
    data_swaps = abs(res["L5"]["sum gcpi:shortage"] - res["L0"]["sum gcpi:shortage"])
    gscpi = abs(res["L6"]["sum gcpi:shortage"] - res["L5"]["sum gcpi:shortage"])
    assert gscpi > 10 * data_swaps
