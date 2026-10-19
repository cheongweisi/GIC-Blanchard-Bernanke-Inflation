"""IRFs, decompositions and the conditional forecast reproduce the authors' MATLAB output files.

The authors' own coefficients are used as inputs (isolating simulation code from estimation); a second test
checks that our estimated coefficients give the same answers to within float32 rounding.
"""
import numpy as np
import pandas as pd
import pytest

from bb_inflation.simulation.decomposition import REMOVABLE, decompose
from bb_inflation.simulation.forecast import conditional_forecast, linear_path, wage_constant
from bb_inflation.simulation.irf import irf, shock_sizes
from bb_inflation.simulation.model import SimModel
from bb_inflation.validation.authors_outputs import authors_model, authors_sim_data, read_core

TOL = 5e-4   # float32 data in the authors' files


@pytest.fixture(scope="module")
def am():
    return authors_model("full")


@pytest.fixture(scope="module")
def adata():
    return authors_sim_data("full")


IRF_CASES = {  # results file -> shocked variable
    "results_energy.xls": "grpe", "results_food.xls": "grpf",
    "results_vu.xls": "vu", "results_shortage.xls": "shortage"}


@pytest.mark.parametrize("fname,var", IRF_CASES.items())
def test_irf_matches_authors(am, adata, fname, var):
    resid = {"gw": adata["gw_residuals"], "gcpi": adata["gcpi_residuals"],
             "cf1": adata["cf1_residuals"], "cf10": adata["cf10_residuals"]}
    sizes = shock_sizes(adata, resid)
    ours = irf(am, var, sizes[var])     # MATLAB passes rho_vu = 1 in every case; irrelevant unless vu shocked
    ref = read_core("IRFs", fname)
    for c in ["gw_simul", "gcpi_simul", "cf1_simul", "cf10_simul", "diffcpicf_simul"]:
        np.testing.assert_allclose(ours[c].values, ref[c].values, atol=TOL, err_msg=f"{fname}:{c}")


def test_irf_shock_sizes_vs_paper_footnote(adata):
    """Documented discrepancy (docs/replication_log.md D9): the paper's footnote-15 shock sizes
    (energy 32, food 3.2, shortage 11.6, v/u 0.5) and ranges come from an earlier data vintage than the
    shipped package (2020Q1-2023Q2 s.d.: 29.1, 3.87, 10.1, 0.58). We only require the same order of magnitude."""
    resid = {k: adata[f"{k}_residuals"] for k in ("gw", "gcpi", "cf1", "cf10")}
    s = shock_sizes(adata, resid)
    for k, paper in {"grpe": 32, "grpf": 3.2, "shortage": 11.6, "vu": 0.5}.items():
        assert s[k] == pytest.approx(paper, rel=0.25), k


DECOMP_FILES = {"grpe": "remove_grpe.xls", "grpf": "remove_grpf.xls", "vu": "remove_vu.xls",
                "shortage": "remove_shortage.xls", "magpty": "remove_magpty.xls",
                "D2020Q2": "remove_2020q2.xls", "D2020Q3": "remove_2020q3.xls"}


def test_decomposition_matches_authors(am, adata):
    dec = decompose(am, adata)
    allref = read_core("Decompositions", "remove_all.xls")
    np.testing.assert_allclose(dec.baseline["gcpi"].values, allref["gcpi_simul_baseline"].values, atol=TOL)
    np.testing.assert_allclose(dec.baseline["gw"].values, allref["gw_simul_baseline"].values, atol=TOL)
    for c in ("gw", "gcpi", "cf1", "cf10"):
        np.testing.assert_allclose(dec.runs["all"][c].values, allref[f"{c}_simul"].values, atol=TOL, err_msg=c)
    for var, fname in DECOMP_FILES.items():
        ref = read_core("Decompositions", fname)
        for c in ("gw", "gcpi", "cf1", "cf10"):
            np.testing.assert_allclose(dec.contributions[var][c].values, ref[f"{var if var in ('grpe','grpf','vu','shortage','magpty') else {'D2020Q2':'dummy2020_q2','D2020Q3':'dummy2020_q3'}[var]}_contr_{c}"].values,
                                       atol=TOL, err_msg=f"{var}:{c}")


def test_decomposition_additive(am, adata):
    """Linear model: individual contributions plus the all-removed ('initial conditions') path equal the baseline."""
    dec = decompose(am, adata)
    total = sum(dec.contributions[v]["gcpi"] for v in REMOVABLE) + dec.runs["all"]["gcpi"]
    np.testing.assert_allclose(total.values, dec.baseline["gcpi"].values, atol=1e-9)


@pytest.mark.parametrize("fname,target", [("terminal_low.xlsx", 0.8), ("terminal_mid.xlsx", 1.2),
                                          ("terminal_high.xlsx", 1.8)])
def test_conditional_forecast_matches_authors(am, adata, fname, target):
    hist = adata.loc["2022Q2":"2023Q1"]   # four initial quarters
    n = 401
    fut_idx = pd.period_range("2023Q2", periods=n, freq="Q")
    vu0 = hist["vu"].iloc[3]             # MATLAB: vu(4) = 2023Q1
    fut = pd.DataFrame({"grpe": 0.0, "grpf": 0.0, "shortage": 10.0, "magpty": 1.0,
                        "vu": linear_path(vu0, target, 8, n)}, index=fut_idx)
    wc = wage_constant(am, 1.2, 1.0, 10.0)
    out = conditional_forecast(am, hist, fut, const_wage=wc)
    ref = read_core("Conditional Forecasts", fname)
    assert len(out) == len(ref) == 405
    for c in ("gw", "gcpi", "cf1", "cf10"):
        np.testing.assert_allclose(out[c].values, ref[f"{c}_simul"].values, atol=1e-3, err_msg=f"{fname}:{c}")
    np.testing.assert_allclose(out["vu"].values, ref["vu_simul"].values, atol=1e-9)


def test_forecast_steady_state_consistency(am):
    """With vu* = 1.2 the corrected wage constant gives a stable steady state (cf1 = gcpi, constant paths)."""
    n = 400
    idx = pd.period_range("2023Q2", periods=n, freq="Q")
    fut = pd.DataFrame({"grpe": 0.0, "grpf": 0.0, "shortage": 10.0, "magpty": 1.0, "vu": 1.2}, index=idx)
    hist = pd.DataFrame({"gw": 2.5, "gcpi": 2.4, "cf1": 2.4, "cf10": 2.4, "diffcpicf": 0.0,
                         "grpe": 0.0, "grpf": 0.0, "vu": 1.2, "shortage": 10.0, "magpty": 1.0},
                        index=pd.period_range("2022Q2", periods=4, freq="Q"))
    out = conditional_forecast(am, hist, fut, const_wage=wage_constant(am, 1.2, 1.0, 10.0))
    # inflation and wage growth settle (derivative ~ 0) at the end of the horizon
    assert abs(out["gcpi"].iloc[-1] - out["gcpi"].iloc[-5]) < 1e-6
    assert abs(out["gcpi"].iloc[-1] - out["cf1"].iloc[-1]) < 1e-6


def test_estimated_coefs_give_same_simulations(am, adata, full):
    ours = SimModel.from_results(full)
    r = {k: adata[f"{k}_residuals"] for k in ("gw", "gcpi", "cf1", "cf10")}
    a = irf(am, "vu", shock_sizes(adata, r)["vu"])["gcpi_simul"].values
    b = irf(ours, "vu", shock_sizes(adata, r)["vu"])["gcpi_simul"].values
    np.testing.assert_allclose(a, b, atol=1e-3)
