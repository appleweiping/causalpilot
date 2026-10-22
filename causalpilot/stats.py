"""The statistics behind a two-arm comparison.

Everything here works on plain NumPy arrays so the same functions serve the CLI,
the tests and the simulation benchmark. Intervals use the normal approximation,
which is fine for the sample sizes A/B tests usually have (hundreds of users per
arm and up); `analysis.py` warns when a binary metric has too few events.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from statistics import NormalDist

import numpy as np

_NORMAL = NormalDist()


def z_critical(alpha: float) -> float:
    """Two-sided critical value, e.g. 1.96 for alpha = 0.05."""
    return _NORMAL.inv_cdf(1.0 - alpha / 2.0)


def two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def chi2_sf(x: float, df: int) -> float:
    """P(X >= x) for a chi-square variable with an integer number of degrees of freedom.

    Uses the closed forms for integer df so the package does not need SciPy.
    """
    if df < 1:
        raise ValueError("df must be at least 1")
    if x <= 0:
        return 1.0
    half = x / 2.0
    if df % 2 == 0:
        term, total = 1.0, 1.0
        for k in range(1, df // 2):
            term *= half / k
            total += term
        return min(1.0, math.exp(-half) * total)
    # Odd df: start from df = 1 and step up with Q(v + 2) = Q(v) + h^(v/2) e^-h / Gamma(v/2 + 1).
    q = math.erfc(math.sqrt(half))
    term = math.sqrt(half) * math.exp(-half) / math.gamma(1.5)
    nu = 1
    while nu < df:
        q += term
        nu += 2
        term *= half / (nu / 2.0)
    return min(1.0, q)


@dataclass(frozen=True)
class SRMResult:
    observed: dict[str, int]
    expected: dict[str, float]
    chi_square: float
    df: int
    p_value: float

    def as_dict(self) -> dict:
        return asdict(self)


def sample_ratio_test(observed: dict[str, int], expected_share: dict[str, float]) -> SRMResult:
    """Pearson chi-square test of the observed arm sizes against the planned split."""
    if set(observed) != set(expected_share):
        raise ValueError("observed and expected_share must name the same groups")
    if len(observed) < 2:
        raise ValueError("need at least two groups for a sample ratio test")
    total_share = sum(expected_share.values())
    if total_share <= 0 or any(share <= 0 for share in expected_share.values()):
        raise ValueError("expected shares must be positive")
    n = sum(observed.values())
    expected = {g: n * expected_share[g] / total_share for g in observed}
    chi_square = sum((observed[g] - expected[g]) ** 2 / expected[g] for g in observed)
    df = len(observed) - 1
    return SRMResult(
        observed={g: int(v) for g, v in observed.items()},
        expected={g: float(v) for g, v in expected.items()},
        chi_square=float(chi_square),
        df=df,
        p_value=float(chi2_sf(chi_square, df)),
    )


@dataclass(frozen=True)
class Estimate:
    """Treatment minus control, with a two-sided normal-approximation interval."""

    effect: float
    se: float
    ci_low: float
    ci_high: float
    p_value: float

    def as_dict(self) -> dict:
        return asdict(self)


def _estimate(effect: float, se: float, alpha: float) -> Estimate:
    z = z_critical(alpha)
    if se > 0:
        p_value = two_sided_p(effect / se)
    else:
        p_value = 1.0 if effect == 0 else 0.0
    return Estimate(effect, se, effect - z * se, effect + z * se, p_value)


def _check_arms(y_t: np.ndarray, y_c: np.ndarray) -> None:
    if y_t.size < 2 or y_c.size < 2:
        raise ValueError("each arm needs at least two rows")


def difference_in_means(y_t: np.ndarray, y_c: np.ndarray, alpha: float = 0.05) -> Estimate:
    """Plain difference in means with a Welch (unequal variance) standard error."""
    y_t = np.asarray(y_t, dtype=float)
    y_c = np.asarray(y_c, dtype=float)
    _check_arms(y_t, y_c)
    effect = float(y_t.mean() - y_c.mean())
    se = math.sqrt(y_t.var(ddof=1) / y_t.size + y_c.var(ddof=1) / y_c.size)
    return _estimate(effect, se, alpha)


@dataclass(frozen=True)
class CupedResult:
    estimate: Estimate
    theta: list[float]
    variance_reduction: float


def cuped(
    y_t: np.ndarray,
    y_c: np.ndarray,
    x_t: np.ndarray,
    x_c: np.ndarray,
    alpha: float = 0.05,
) -> CupedResult:
    """CUPED (Deng et al., 2013): subtract the part of the metric explained by
    pre-experiment covariates, then compare the adjusted means.

    With one covariate this is the textbook theta = cov(X, Y) / var(X). With several
    it is the least-squares fit on the pooled, centred covariates. Because the
    covariates were fixed before assignment, the adjustment does not bias the effect;
    it only removes noise. The uncertainty in theta itself is ignored, which is
    standard and negligible at A/B-test sample sizes.
    """
    y_t = np.asarray(y_t, dtype=float)
    y_c = np.asarray(y_c, dtype=float)
    _check_arms(y_t, y_c)
    x_t = np.asarray(x_t, dtype=float).reshape(y_t.size, -1)
    x_c = np.asarray(x_c, dtype=float).reshape(y_c.size, -1)
    x = np.vstack([x_t, x_c])
    y = np.concatenate([y_t, y_c])
    x_centred = x - x.mean(axis=0)
    keep = x_centred.std(axis=0) > 0
    if not keep.any():
        raise ValueError("covariates are constant; CUPED has nothing to adjust with")
    x_centred = x_centred[:, keep]
    theta_kept, *_ = np.linalg.lstsq(x_centred, y - y.mean(), rcond=None)
    adjusted = y - x_centred @ theta_kept
    adj_t, adj_c = adjusted[: y_t.size], adjusted[y_t.size :]
    estimate = difference_in_means(adj_t, adj_c, alpha)
    var_y = y.var(ddof=1)
    reduction = float(1.0 - adjusted.var(ddof=1) / var_y) if var_y > 0 else 0.0
    theta = np.zeros(keep.size)
    theta[keep] = theta_kept
    return CupedResult(estimate, [float(v) for v in theta], reduction)


def rho_squared_for(planned_n: int, alpha: float) -> float:
    """Tuning constant that makes the confidence sequence tightest at `planned_n`."""
    log_term = -2.0 * math.log(alpha)
    return (log_term + math.log(log_term + 1.0)) / planned_n


def always_valid_interval(
    estimate: Estimate, n: int, alpha: float = 0.05, planned_n: int | None = None
) -> tuple[float, float]:
    """Interval that stays valid no matter how often you looked at the results.

    This is the asymptotic confidence sequence of Waudby-Smith et al. (2021,
    "Time-uniform central limit theory and asymptotic confidence sequences")
    applied to the difference in means, whose per-unit standard deviation is
    se * sqrt(n). `planned_n` only decides where the interval is tightest; it must
    be fixed before the test starts for the guarantee to hold.
    """
    if n < 2:
        raise ValueError("n must be at least 2")
    rho2 = rho_squared_for(planned_n or n, alpha)
    sigma = estimate.se * math.sqrt(n)
    radius = sigma * math.sqrt(
        2.0 * (n * rho2 + 1.0) / (n * n * rho2) * math.log(math.sqrt(n * rho2 + 1.0) / alpha)
    )
    return estimate.effect - radius, estimate.effect + radius


def relative_lift(y_t: np.ndarray, y_c: np.ndarray, alpha: float = 0.05) -> dict[str, float] | None:
    """(mean_t - mean_c) / mean_c with a delta-method interval. None if mean_c is 0."""
    y_t = np.asarray(y_t, dtype=float)
    y_c = np.asarray(y_c, dtype=float)
    m_t, m_c = float(y_t.mean()), float(y_c.mean())
    if m_c == 0:
        return None
    var_t = y_t.var(ddof=1) / y_t.size
    var_c = y_c.var(ddof=1) / y_c.size
    lift = m_t / m_c - 1.0
    se = math.sqrt(var_t / m_c**2 + m_t**2 * var_c / m_c**4)
    z = z_critical(alpha)
    return {"lift": lift, "ci_low": lift - z * se, "ci_high": lift + z * se}


def sample_size_factor(se: float, min_effect: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """How many times the current sample you need to detect `min_effect` with `power`.

    Standard errors shrink with 1/sqrt(n), so the factor is (se / target_se)^2.
    """
    if min_effect <= 0:
        return math.inf
    target_se = min_effect / (z_critical(alpha) + _NORMAL.inv_cdf(power))
    return (se / target_se) ** 2
