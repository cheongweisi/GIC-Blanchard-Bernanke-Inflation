"""Phase 4c: the vintage comparison leaves Phase 1-4b untouched and its machinery is exact where it claims to be."""
import hashlib

import numpy as np
import pandas as pd
import pytest

from bb_inflation.config import PROJECT_ROOT
from bb_inflation.estimation.inference import hac_cov
from bb_inflation.phase4c import authors as AU
from bb_inflation.phase4c import ident as ID
from bb_inflation.phase4c import irf as I
from bb_inflation.phase4c import samples as S
from bb_inflation.phase4c import study as ST
from bb_inflation.scenarios import engine as E
from bb_inflation.simulation.general import irf_general
from bb_inflation.simulation.model import SimModel


@pytest.fixture(scope="module")
def st():
    return ST.build(n=400)


def test_phase1_to_4b_files_are_unchanged():
    man = PROJECT_ROOT / "outputs" / "phase4c" / "pre_phase4c_manifest.sha256"
    bad = []
    for line in man.read_text().splitlines():
        h, rel = line.split(" *", 1)
        f = PROJECT_ROOT / rel.strip()
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
            bad.append(rel)
    assert not bad, bad


def test_b2026_is_the_production_model(st):
    prod = S.production(st.data, st.ctx.last)
    for eq in S.EQS:
        np.testing.assert_allclose(st.fits["B26"][eq].coef.values, prod[eq].coef.values, atol=1e-12)


def test_samples_and_restrictions(st):
    ends = {"B19": "2019Q4", "B23": "2023Q4", "B26": "2026Q2"}
    for vk, end in ends.items():
        for eq in S.EQS:
            r = st.fits[vk][eq]
            assert str(r.sample[1]) == end and str(r.sample[0]) == "1990Q1"
            rn = r.spec.restriction_names()
            assert abs(r.coef[rn].sum() - 1.0) < 1e-10
    assert not st.fits["B19"]["gw"].spec.dummies and len(st.fits["B23"]["gw"].spec.dummies) == 2
    assert str(st.fits["HYB"]["gcpi"].sample[1]) == "2023Q2" and str(st.fits["HYB"]["gw"].sample[1]) == "2019Q4"


def test_stacked_diagonal_blocks_equal_hac(st):
    for eq in S.EQS:
        stk = st.stacks[eq]
        for k in stk.keys:
            r = st.fits[k][eq]
            H = hac_cov(r, st.data).values
            idx = [stk.cols.index(n) for n in r.coef.index]
            sub = stk.block_cov(k, k)[np.ix_(idx, idx)]
            np.testing.assert_allclose(sub, H, rtol=1e-9, atol=1e-12)


def test_joint_draws_satisfy_restrictions_and_reproduce_covariance(st):
    stk = st.stacks["gcpi"]
    dr = st.draws["gcpi"]["B26"]
    rn = stk.selector(["gcpi", "gw"])
    assert np.abs(dr @ rn - 1.0).max() < 1e-7
    big = stk.draws(40000, np.random.default_rng(1))
    emp = np.cov(np.hstack([big[k] for k in stk.keys]).T)
    assert np.abs(emp - stk.cov).max() < 0.05 * np.abs(stk.cov).max() + 1e-4


def test_overlap_adjustment_shrinks_se_of_nested_differences(st):
    stk = st.stacks["gcpi"]
    t = stk.change_test("B19", "B26", stk.selector("gw"))
    assert t["se"] < t["se_if_independent"]


def test_fwl_standard_error_equals_classical(st):
    r = st.fits["B26"]["gcpi"]
    o = ID.coefficient_identification(r, st.data, "shortagema2_L0")
    assert abs(o["s.e. from FWL (check)"] - o["classical s.e."]) < 1e-10


def test_irf_engine_relative_convention_reproduces_phase1_simulator(st):
    res = st.fits["B26"]
    sm = SimModel.from_results(res)
    cs = E.CoefSet.from_models([sm])
    sd = 0.97
    cat = I.shock_catalogue(sd)
    old_vu = irf_general(sm, "vu", 0.5, derived={"shortagema2": ("shortage", 2)}, rho=1.0, horizon=45)
    new_vu = I.run(cs, cat["V1"], "relative")
    np.testing.assert_allclose(new_vu["gcpi"][0], old_vu["gcpi_simul"].values[4:45], atol=1e-12)
    old_g = irf_general(sm, "shortage", sd, derived={"shortagema2": ("shortage", 2)}, rho=0.0, horizon=45)
    new_g = I.run(cs, cat["G1"], "relative")
    np.testing.assert_allclose(new_g["gcpi"][0], old_g["gcpi_simul"].values[4:45], atol=1e-12)


def test_wage_shock_conventions(st):
    cs = st.coefset("B26", point=True)
    cat = I.shock_catalogue(1.0)
    rel = I.run(cs, cat["W2"], "relative")["gcpi"][0]
    nom = I.run(cs, cat["W2"], "nominal")["gcpi"][0]
    assert abs(rel[-1] - 1.0) < 1e-6                       # homogeneity: sustained wage growth passes through one-for-one when relative prices are fixed
    expected = (cs.block_sum("gcpi", "gw") - cs.block_sum("gcpi", "grpe") - cs.block_sum("gcpi", "grpf")) / (1 - cs.block_sum("gcpi", "gcpi"))
    assert abs(nom[-1] - float(expected[0])) < 1e-6        # nominal energy and food: only the net wage weight passes through


def test_oil_bridge_arithmetic():
    b = I.bridge().coef.values[1:]
    g = I.oil_energy_growth(b, 10.0, "sustained", 8)
    x = 100 * np.log(1.1)
    assert abs(g[0] - 4 * (b[0] + b[1] + b[2]) * x) < 1e-12
    assert abs(g[1] - 4 * b[3] * x) < 1e-12 and np.abs(g[2:]).max() < 1e-12
    assert abs(g.sum() / 4 - b.sum() * x) < 1e-12           # cumulative CPI-energy level effect = elasticity x log shock
    e = I.oil_energy_growth(b, 10.0, "episode", 8)
    assert abs(e.sum()) < 1e-12                             # the episode reverses completely
    # bridge is the Phase 4 headline
    assert abs(I.bridge().elasticity - 0.29680561944615713) < 1e-9


def test_authors_irfs_reproduce_shipped_files():
    summ, _, _, _ = AU.irf_replication()
    assert summ["max |our replication (full-sample coefficients) - shipped file|"].max() < 5e-4


def test_irf_stats_are_consistent(st):
    cs = st.coefset("B26", point=True)
    cat = I.shock_catalogue(1.0)
    r = I.run(cs, cat["W1"], "nominal")
    s = I.statistics(r)
    assert abs(s[("gcpi", "price level, cumulative to h=12 (%)")][0] - r["gcpi"][0, :13].sum() / 4) < 1e-12
    assert s[("gcpi", "h=4")][0] == r["gcpi"][0, 4]
