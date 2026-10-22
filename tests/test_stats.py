import math

import numpy as np
import pytest
from scipy import stats as sp

from causalpilot import stats


@pytest.mark.parametrize("df", [1, 2, 3, 4, 5, 8, 11])
@pytest.mark.parametrize("x", [0.01, 0.5, 1.0, 3.84, 10.0, 40.0])
def test_chi2_sf_matches_scipy(df, x):
    assert stats.chi2_sf(x, df) == pytest.approx(sp.chi2.sf(x, df), rel=1e-9, abs=1e-15)


def test_sample_ratio_test_matches_scipy_chisquare():
    observed = {"control": 10_000, "treatment": 10_250}
    result = stats.sample_ratio_test(observed, {"control": 1, "treatment": 1})
    expected = sp.chisquare([10_000, 10_250])
    assert result.chi_square == pytest.approx(expected.statistic)
    assert result.p_value == pytest.approx(expected.pvalue)
    assert result.df == 1


def test_sample_ratio_test_uses_planned_split():
    # 90/10 design that came out exactly 90/10: no mismatch at all.
    result = stats.sample_ratio_test({"a": 9_000, "b": 1_000}, {"a": 0.9, "b": 0.1})
    assert result.chi_square == pytest.approx(0.0)
    assert result.p_value == pytest.approx(1.0)


def test_difference_in_means_is_welch():
    rng = np.random.default_rng(1)
    y_t = rng.normal(1.1, 2.0, 3_000)
    y_c = rng.normal(1.0, 1.0, 5_000)
    est = stats.difference_in_means(y_t, y_c)
    welch = sp.ttest_ind(y_t, y_c, equal_var=False)
    assert est.effect == pytest.approx(y_t.mean() - y_c.mean())
    assert est.effect / est.se == pytest.approx(welch.statistic)
    assert est.ci_low < est.effect < est.ci_high
    assert est.ci_high - est.ci_low == pytest.approx(2 * 1.959964 * est.se, rel=1e-5)


def test_cuped_single_covariate_theta_and_variance_cut():
    rng = np.random.default_rng(2)
    n = 40_000
    x = rng.normal(0, 1, n)
    treated = rng.random(n) < 0.5
    y = 2.0 * x + rng.normal(0, 1, n) + 0.1 * treated
    result = stats.cuped(y[treated], y[~treated], x[treated], x[~treated])
    assert result.theta[0] == pytest.approx(np.cov(x, y)[0, 1] / x.var(ddof=1), rel=1e-6)
    # corr(x, y)^2 = 4 / 5, so CUPED should remove about 80% of the variance.
    assert result.variance_reduction == pytest.approx(0.8, abs=0.01)
    raw = stats.difference_in_means(y[treated], y[~treated])
    assert result.estimate.se < 0.5 * raw.se
    assert result.estimate.ci_low < 0.1 < result.estimate.ci_high


def test_cuped_with_useless_covariate_changes_little():
    rng = np.random.default_rng(3)
    y_t, y_c = rng.normal(0, 1, 2_000), rng.normal(0, 1, 2_000)
    x_t, x_c = rng.normal(0, 1, 2_000), rng.normal(0, 1, 2_000)
    result = stats.cuped(y_t, y_c, x_t, x_c)
    assert abs(result.variance_reduction) < 0.01


def test_cuped_rejects_constant_covariate():
    with pytest.raises(ValueError):
        stats.cuped(np.arange(5.0), np.arange(5.0), np.ones(5), np.ones(5))


def test_always_valid_interval_is_wider_and_centred():
    est = stats.Estimate(effect=0.01, se=0.004, ci_low=0.01 - 0.00784, ci_high=0.01 + 0.00784, p_value=0.01)
    low, high = stats.always_valid_interval(est, n=20_000)
    assert low < est.ci_low and high > est.ci_high
    assert (low + high) / 2 == pytest.approx(0.01)


def test_always_valid_interval_controls_error_under_daily_peeking():
    """Under the null, stopping at the first 'significant' look should stay near alpha
    with the always-valid interval, while the fixed interval is far above it."""
    rng = np.random.default_rng(4)
    sims, looks, per_look = 400, 20, 250
    fixed_hits = valid_hits = 0
    for _ in range(sims):
        y_t = rng.normal(0, 1, looks * per_look)
        y_c = rng.normal(0, 1, looks * per_look)
        fixed_stop = valid_stop = False
        for k in range(1, looks + 1):
            m = k * per_look
            est = stats.difference_in_means(y_t[:m], y_c[:m])
            if not fixed_stop and (est.ci_low > 0 or est.ci_high < 0):
                fixed_stop = True
            low, high = stats.always_valid_interval(est, 2 * m, planned_n=2 * looks * per_look)
            if not valid_stop and (low > 0 or high < 0):
                valid_stop = True
        fixed_hits += fixed_stop
        valid_hits += valid_stop
    assert fixed_hits / sims > 0.15
    assert valid_hits / sims < 0.06


def test_relative_lift_delta_method():
    y_c = np.array([0.0] * 900 + [1.0] * 100)
    y_t = np.array([0.0] * 880 + [1.0] * 120)
    result = stats.relative_lift(y_t, y_c)
    assert result["lift"] == pytest.approx(0.2)
    assert result["ci_low"] < 0.2 < result["ci_high"]
    assert stats.relative_lift(y_t, np.zeros(10)) is None


def test_sample_size_factor():
    target = 0.01 / (stats.z_critical(0.05) + 0.8416212335729143)
    assert stats.sample_size_factor(target, 0.01) == pytest.approx(1.0)
    assert stats.sample_size_factor(2 * target, 0.01) == pytest.approx(4.0)
    assert math.isinf(stats.sample_size_factor(0.1, 0.0))
