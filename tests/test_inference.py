"""HAC inference, generalized simulators and stability tools (Phase 3 pre-validation additions)."""
import numpy as np
import pandas as pd
import pytest

from bb_inflation.estimation.inference import (chow_predictive, coef_table, cusum_ols, hac_cov, irf_bands_mc,
                                               recursive_sums, sup_f_partial, with_hac)
from bb_inflation.estimation.replication import fit_full, fit_precovid
from bb_inflation.simulation.decomposition import decompose
from bb_inflation.simulation.general import decompose_general, irf_general
from bb_inflation.simulation.irf import irf, shock_sizes
from bb_inflation.simulation.model import SimModel


def test_hac_cov_is_symmetric_psd_and_respects_restriction(data, full):
    for eq, r in full.items():
        V = hac_cov(r, data)
        assert np.allclose(V, V.T)
        assert np.linalg.eigvalsh(V.values).min() > -1e-10
        names = list(V.index)
        rn = r.spec.restriction_names()
        sel = np.array([n in rn for n in names], float)
        # variance of the restricted sum is zero
        assert float(sel @ V.values @ sel) < 1e-10


def test_hac_se_same_order_as_classical(data, full):
    r = full["gcpi"]
    tab = coef_table(r, with_hac(r, data))
    ratio = (tab.se_hac / tab.se_classic).median()
    assert 0.5 < ratio < 3.0


def test_general_irf_and_decomposition_reduce_to_originals(data, full):
    model = SimModel.from_results(full)
    sz = shock_sizes(data, {k: full[k].resid for k in ("gw", "gcpi", "cf1", "cf10")})
    for v in ("grpe", "vu", "shortage"):
        a = irf(model, v, sz[v])["gcpi_simul"].values
        b = irf_general(model, v, sz[v])["gcpi_simul"].values
        np.testing.assert_allclose(a, b, atol=1e-12)
    d1, d2 = decompose(model, data), decompose_general(model, data)
    for k in d1.contributions:
        np.testing.assert_allclose(d1.contributions[k]["gcpi"].values, d2.contributions[k]["gcpi"].values, atol=1e-10)


def test_mc_bands_contain_point_irf(data, full):
    model = SimModel.from_results(full)
    sz = shock_sizes(data, {k: full[k].resid for k in ("gw", "gcpi", "cf1", "cf10")})
    hac = {k: with_hac(r, data) for k, r in full.items()}
    bands = irf_bands_mc(hac, lambda m, s, size: irf_general(m, s, size), {"vu": sz["vu"]}, n=300, seed=1)
    point = irf_general(model, "vu", sz["vu"])["gcpi_simul"].values
    b = bands["vu"]
    inside = ((point >= b["q05"].values - 1e-9) & (point <= b["q95"].values + 1e-9)).mean()
    assert inside > 0.9
    assert (b["q05"] <= b["q95"]).all()


def test_chow_predictive_runs_and_cusum(data, precovid):
    c = chow_predictive(precovid["gw"], data, list(pd.period_range("2020Q1", "2023Q2", freq="Q")))
    assert c["df1"] == 14 and 0.0 <= c["p"] <= 1.0
    s = cusum_ols(precovid["cf10"])
    assert 0.0 <= s["p"] <= 1.0


def test_sup_f_detects_a_planted_break(data, full):
    """Plant a break in the price equation's V/U-free 'magpty' coefficient and check the test rejects."""
    r = full["gcpi"]
    d2 = data.copy()
    d2.loc["2008Q1":, "gcpi"] = d2.loc["2008Q1":, "gcpi"] + 3.0 * d2.loc["2008Q1":, "magpty"]
    from bb_inflation.estimation.rls import estimate
    r2 = estimate(r.spec, d2, "1990Q1", "2023Q2")
    out = sup_f_partial(r2, d2, ["magpty_L0"], nboot=100)
    assert out["p_boot"] < 0.05
    assert abs(pd.Period(out["break_after"]).year - 2008) <= 1


def test_recursive_sums_shape(data):
    from bb_inflation.estimation.equations import base_equations
    spec = base_equations(False)["cf10"]
    rs = recursive_sums(spec, data, {"gcpi": [f"gcpi_L{k}" for k in range(5)]}, ["2010Q4", "2019Q4"])
    assert list(rs.index) == ["2010Q4", "2019Q4"] and (rs["gcpi"] > 0).all()
