"""Estimation reproduces the authors' Stata output (coefficients, sum/joint p-values, R2, N, fitted values)."""
import numpy as np
import pandas as pd
import pytest

from bb_inflation.config import OUT_FULL, OUT_PRECOVID

COEF_TOL = 5e-6   # authors' Excel output keeps ~6-7 significant digits
SUM_ROWS = {  # row label in summary_stats -> variable block
    "gw": ["gw", "cf1", "vu", "diffcpicf", "magpty"],
    "gcpi": ["gcpi", "gw", "grpe", "grpf", "shortage", "magpty"],
    "cf1": ["cf1", "cf10", "gcpi"],
    "cf10": ["cf10", "gcpi"],
}
RUNS = [("full", OUT_FULL, "eq_coefficients.xlsx", "summary_stats_full.xlsx"),
        ("precovid", OUT_PRECOVID, "eq_coefficients_restricted.xlsx", "summary_stats_restricted.xlsx")]


def _res(request, tag):
    return request.getfixturevalue(tag)


@pytest.mark.parametrize("tag,folder,coef_file,_", RUNS)
@pytest.mark.parametrize("eq", ["gw", "gcpi", "cf1", "cf10"])
def test_coefficients(request, tag, folder, coef_file, _, eq):
    res = _res(request, tag)[eq]
    ref = pd.read_excel(folder / coef_file, sheet_name=eq).iloc[:, 1].values
    assert len(ref) == len(res.coef)
    np.testing.assert_allclose(res.coef.values, ref, atol=COEF_TOL)


@pytest.mark.parametrize("tag,folder,_,sum_file", RUNS)
@pytest.mark.parametrize("eq", ["gw", "gcpi", "cf1", "cf10"])
def test_summary_stats(request, tag, folder, _, sum_file, eq):
    res = _res(request, tag)[eq]
    ref = pd.read_excel(folder / sum_file, sheet_name=eq, header=None)
    blocks = SUM_ROWS[eq]
    s = res.summary()
    for i, var in enumerate(blocks, start=1):
        r_sum, r_psum, r_pjoint = ref.iloc[i, 1], ref.iloc[i, 2], ref.iloc[i, 3]
        assert s.loc[var, "sum"] == pytest.approx(r_sum, abs=5e-6)
        assert s.loc[var, "p_joint"] == pytest.approx(r_pjoint, abs=5e-5), (tag, eq, var)
        if not np.isnan(r_psum):
            assert s.loc[var, "p_sum"] == pytest.approx(r_psum, abs=5e-5), (tag, eq, var)
    # R2 and N rows follow the block rows after a blank row
    r2_row = len(blocks) + 2
    assert res.r2_corr == pytest.approx(ref.iloc[r2_row, 1], abs=5e-6)
    assert res.nobs == int(ref.iloc[r2_row + 1, 1])


@pytest.mark.parametrize("tag,folder,_c,_s", RUNS)
def test_sample_lengths(request, tag, folder, _c, _s):
    res = _res(request, tag)
    expected = {"full": {"gw": 134, "gcpi": 134, "cf1": 134, "cf10": 134},
                "precovid": {"gw": 120, "gcpi": 134, "cf1": 120, "cf10": 120}}[tag]
    assert {k: r.nobs for k, r in res.items()} == expected
    assert all(str(r.sample[0]) == "1990Q1" for r in res.values())


def test_fitted_and_residuals_match_authors(data, full):
    ref = pd.read_excel(OUT_FULL / "eq_simulations_data.xls")
    ref.index = pd.PeriodIndex(ref["period"], freq="Q")
    for eq, fcol, rcol, sign in [("gw", "gwf1", "gw_residuals", 1), ("gcpi", "gcpif", "gcpi_residuals", 1),
                                 ("cf1", "cf1f", "cf1_residuals", 1), ("cf10", "cf10f", "cf10_residuals", -1)]:
        r = full[eq]
        m = ref[fcol].dropna()
        np.testing.assert_allclose(r.fitted.reindex(m.index).values, m.values, atol=1e-5)
        # authors define cf10_residuals as fitted - actual (sign flipped); the others actual - fitted
        np.testing.assert_allclose(sign * r.resid.reindex(m.index).values,
                                   ref[rcol].reindex(m.index).values, atol=1e-5)


def test_model_variables_match_authors(data):
    ref = pd.read_excel(OUT_FULL / "eq_simulations_data.xls")
    ref.index = pd.PeriodIndex(ref["period"], freq="Q")
    cols = ["gcpi", "gw", "magpty", "grpe", "grpf", "vu", "cf1", "cf10", "shortage", "diffcpicf"]
    for c in cols:
        a = data[c].reindex(ref.index)
        m = ref[c].notna() & a.notna()
        assert m.sum() >= 130
        # Stata `gen` creates float32 variables, so the authors' exported series carry ~1e-5 rounding
        np.testing.assert_allclose(a[m].values, ref[c][m].values, atol=2e-4, err_msg=c)


def test_out_of_sample_predictions_match_authors(data, precovid):
    """Figures 3, 7, 8, 9: pre-COVID equations predicting 2020Q1-2023Q2 (Stata `predict`)."""
    from bb_inflation.validation.authors_outputs import authors_sim_data
    ref = authors_sim_data("precovid")
    for eq, col in [("gw", "gwf1"), ("gcpi", "gcpif"), ("cf1", "cf1f"), ("cf10", "cf10f")]:
        pred = precovid[eq].predict(data).loc["2020Q1":"2023Q2"]
        np.testing.assert_allclose(pred.values, ref[col].loc["2020Q1":"2023Q2"].values, atol=2e-3, err_msg=eq)


def test_gscpi_variant_reproduces_table_A8(raw):
    """Appendix Table A8 / alternative_shortages.do: GSCPI replaces Google 'shortage' (fill -0.035 pre-sample)."""
    from bb_inflation.config import PACKAGE_DIR
    from bb_inflation.data.transforms import build_model_data
    from bb_inflation.estimation.replication import fit_full
    d = build_model_data(raw, shortage=raw["GSCPI"], shortage_fill=-0.035)
    r = fit_full(d)["gcpi"]
    ref = pd.read_excel(PACKAGE_DIR / "(5) Appendix" / "Shortage Alternatives" / "eq_coefficients.xlsx",
                        sheet_name="gcpi_nyfed").iloc[:, 1].values
    np.testing.assert_allclose(r.coef.values, ref, atol=COEF_TOL)
    s = r.summary()
    assert s.loc["shortage", "sum"] == pytest.approx(0.271, abs=5e-4)
    assert s.loc["shortage", "p_sum"] == pytest.approx(0.016, abs=5e-4)
    assert r.r2_corr == pytest.approx(0.940, abs=5e-4)
