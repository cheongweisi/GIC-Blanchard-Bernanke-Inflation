import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bb_inflation.data.authors_data import load_raw  # noqa: E402
from bb_inflation.data.transforms import build_model_data  # noqa: E402
from bb_inflation.estimation.replication import fit_full, fit_precovid  # noqa: E402


@pytest.fixture(scope="session")
def raw():
    return load_raw()


@pytest.fixture(scope="session")
def data(raw):
    return build_model_data(raw)


@pytest.fixture(scope="session")
def full(data):
    return fit_full(data)


@pytest.fixture(scope="session")
def precovid(data):
    return fit_precovid(data)
