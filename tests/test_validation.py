"""Validation-phase additions: no look-ahead in the out-of-sample design, simulator/derived-variable consistency,
data-pull integrity. (Data-pull tests only need the stored pulls, not a live Macrobond connection.)"""
import json
import shutil

import numpy as np
import pandas as pd
import pytest

from bb_inflation.data import macrobond_audit as audit
from bb_inflation.estimation.inference import with_hac
from bb_inflation.simulation.general import add_derived, irf_general
from bb_inflation.simulation.irf import shock_sizes
from bb_inflation.simulation.model import SimModel
from bb_inflation.validation import oos
from bb_inflation.validation.specs import VARIANTS, equations_for
from bb_inflation.estimation.equations import base_equations


# ---------------------------------------------------------------------------------------------------
# no look-ahead
# ---------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def perturbed(data):
    d = data.copy()
    rng = np.random.default_rng(0)
    cols = ["gw", "gcpi", "cf1", "cf10", "diffcpicf", "grpe", "grpf", "vu", "shortage", "magpty"]
    mask = d.index >= pd.Period("2020Q1", "Q")
    for c in cols:
        d.loc[mask, c] = d.loc[mask, c] + rng.normal(0, 5, mask.sum())
    return d


def test_genuine_regime_ignores_post_2019_data(data, perturbed):
    v = VARIANTS["google5"]
    a, b = oos.fit_regime(v, data, "genuine"), oos.fit_regime(v, perturbed, "genuine")
    for eq in a:
        assert str(a[eq].sample[1]) == "2019Q4"
        np.testing.assert_allclose(a[eq].coef.values, b[eq].coef.values, atol=1e-10, err_msg=eq)


def test_hybrid_price_equation_uses_post_2019_data(data, perturbed):
    v = VARIANTS["google5"]
    a, b = oos.fit_regime(v, data, "hybrid"), oos.fit_regime(v, perturbed, "hybrid")
    assert str(a["gcpi"].sample[1]) == "2023Q2"
    assert not np.allclose(a["gcpi"].coef.values, b["gcpi"].coef.values)         # price eq is NOT out-of-sample
    np.testing.assert_allclose(a["gw"].coef.values, b["gw"].coef.values, atol=1e-10)


def test_dynamic_forecast_uses_only_initial_conditions_from_actual_endogenous(data, perturbed):
    """Realised *exogenous* inputs are used (conditional forecast) but actual post-2019 endogenous values are not."""
    v = VARIANTS["gscpi1"]
    res = oos.fit_regime(v, data, "genuine")
    p3 = data.copy()
    for c in ("gw", "gcpi", "cf1", "cf10", "diffcpicf"):
        p3.loc[p3.index >= pd.Period("2020Q1", "Q"), c] = perturbed.loc[perturbed.index >= pd.Period("2020Q1", "Q"), c]
    f1, f3 = oos.dynamic_forecast(res, data, v), oos.dynamic_forecast(res, p3, v)
    np.testing.assert_allclose(f1.values, f3.values, atol=1e-10)


def test_dynamic_forecast_horizon_and_errors(data):
    v = VARIANTS["none"]
    res = oos.fit_regime(v, data, "genuine")
    fc = oos.dynamic_forecast(res, data, v)
    assert str(fc.index[0]) == "2020Q1" and str(fc.index[-1]) == "2023Q2" and len(fc) == 14
    m = oos.metrics(fc, data, {"x": 1})
    assert {r["variable"] for r in m} == {"gw", "gcpi", "cf1", "cf10"}
    assert all(r["RMSE"] >= r["MAE"] - 1e-12 for r in m)


def test_authors_specification_unchanged_by_variants():
    for covid in (True, False):
        a, b = base_equations(covid), equations_for(VARIANTS["google5"], covid)
        for k in a:
            assert a[k].regressors() == b[k].regressors() and a[k].restriction_names() == b[k].restriction_names()


# ---------------------------------------------------------------------------------------------------
# derived variables in simulation
# ---------------------------------------------------------------------------------------------------
def test_ma2_impact_effect_is_half_the_coefficient(data):
    v = VARIANTS["gscpi_ma2"]
    d = add_derived(data, v.derived_dict)
    res = oos.fit_regime(v, d.assign(shortage=d["shortage"]), "insample")
    model = SimModel.from_results(res)
    b = res["gcpi"].coef["shortagema2_L0"]
    path = irf_general(model, "shortage", 1.0, derived=v.derived_dict)["gcpi_simul"].values
    assert path[4] == pytest.approx(b * 0.5, abs=1e-12)          # shock quarter: MA2 moves by half the shock
    assert path[5] != pytest.approx(0.0)                          # and the second quarter carries the other half


def test_add_derived_trailing_mean(data):
    d = add_derived(data, {"m4": ("shortage", 4)})
    x = data["shortage"]
    assert d["m4"].iloc[20] == pytest.approx(x.iloc[17:21].mean())
    assert np.isnan(d["m4"].iloc[2])


# ---------------------------------------------------------------------------------------------------
# data pull integrity
# ---------------------------------------------------------------------------------------------------
def test_active_pull_integrity_and_description():
    d = audit.describe_pull()
    assert d["pull_id"].startswith("pull_") and len(d["quarterly_sha256"]) == 64
    df = audit.load_pull()
    assert {"CPIAUCSL", "GSCPI", "ECIWAG"} <= set(df.columns)


def test_pull_tamper_detected(tmp_path, monkeypatch):
    pid = audit.active_pull()
    shutil.copytree(audit.PULLS / pid, tmp_path / pid)
    monkeypatch.setattr(audit, "PULLS", tmp_path)
    audit.load_pull(pid)                                           # intact copy loads
    f = tmp_path / pid / "quarterly_raw.csv"
    f.write_text(f.read_text().replace("\n", "\n", 1) + "2099Q4,1,1,1,1,1,1,1,1,1\n")
    with pytest.raises(RuntimeError, match="Integrity"):
        audit.load_pull(pid)


def test_compare_pulls_same_pull_has_no_changes():
    pid = audit.active_pull()
    c = audit.compare_pulls(pid, pid)
    assert (c.revised_obs == 0).all()


def test_pull_index_lists_every_pull_folder():
    idx = audit.list_pulls()
    folders = {p.name for p in audit.PULLS.iterdir() if p.is_dir()}
    assert folders <= set(idx.pull_id)
    for pid in folders:
        m = json.loads((audit.PULLS / pid / "manifest.json").read_text())
        assert m["pull_id"] == pid and "retrieved_utc" in m and "sha256" in m
