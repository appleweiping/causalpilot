"""Deterministic statistical tools used by the agent.

The coordinator never invents these quantities. Every displayed test statistic is
computed here from row-level data.
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Iterable

import numpy as np
import pandas as pd


EPS = 1e-12


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def rct_uplift(
    data: pd.DataFrame,
    treatment_col: str = "treatment",
    outcome_col: str = "outcome",
    confidence: float = 0.95,
) -> dict[str, float | int]:
    """Difference in binary means with a deterministic Wald interval."""
    treated = data.loc[data[treatment_col] == 1, outcome_col].astype(float)
    control = data.loc[data[treatment_col] == 0, outcome_col].astype(float)
    if treated.empty or control.empty:
        raise ValueError("RCT analysis requires non-empty treatment and control arms")
    p_t, p_c = float(treated.mean()), float(control.mean())
    uplift = p_t - p_c
    se = math.sqrt(
        max(p_t * (1.0 - p_t), EPS) / len(treated)
        + max(p_c * (1.0 - p_c), EPS) / len(control)
    )
    z_critical = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    z_score = uplift / max(se, EPS)
    p_value = 2.0 * (1.0 - _normal_cdf(abs(z_score)))
    return {
        "exposures": int(len(data)),
        "treatment_n": int(len(treated)),
        "control_n": int(len(control)),
        "treatment_rate": p_t,
        "control_rate": p_c,
        "uplift": uplift,
        "standard_error": se,
        "ci_low": uplift - z_critical * se,
        "ci_high": uplift + z_critical * se,
        "p_value": min(max(p_value, 0.0), 1.0),
    }


def segment_uplifts(data: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    return {
        str(segment): rct_uplift(frame)
        for segment, frame in data.groupby("segment", sort=True)
    }


def sample_ratio_mismatch(
    assignments: Iterable[int], expected_treatment_share: float = 0.5
) -> dict[str, float | int]:
    """Pearson SRM test. For two cells the chi-square survival is erfc(sqrt(x/2))."""
    values = np.asarray(list(assignments), dtype=int)
    n = len(values)
    if n == 0:
        raise ValueError("SRM test requires assignments")
    observed_t = int(values.sum())
    observed_c = n - observed_t
    expected_t = n * expected_treatment_share
    expected_c = n - expected_t
    chi_square = (observed_t - expected_t) ** 2 / max(expected_t, EPS)
    chi_square += (observed_c - expected_c) ** 2 / max(expected_c, EPS)
    return {
        "treatment_n": observed_t,
        "control_n": observed_c,
        "chi_square": float(chi_square),
        "p_value": float(math.erfc(math.sqrt(max(chi_square, 0.0) / 2.0))),
    }


def covariate_balance(
    data: pd.DataFrame,
    covariates: list[str],
    treatment_col: str = "treatment",
) -> dict[str, object]:
    """Absolute standardized mean differences, pooled-variance denominator."""
    treated = data[data[treatment_col] == 1]
    control = data[data[treatment_col] == 0]
    smd: dict[str, float] = {}
    for column in covariates:
        x_t = treated[column].astype(float)
        x_c = control[column].astype(float)
        pooled = math.sqrt(max((float(x_t.var(ddof=1)) + float(x_c.var(ddof=1))) / 2.0, EPS))
        smd[column] = abs(float(x_t.mean()) - float(x_c.mean())) / pooled
    return {"smd": smd, "max_smd": max(smd.values(), default=0.0)}


def propensity_overlap(
    propensity: Iterable[float], lower: float = 0.1, upper: float = 0.9
) -> dict[str, float]:
    values = np.asarray(list(propensity), dtype=float)
    if values.size == 0:
        raise ValueError("Overlap diagnostic requires propensity scores")
    in_support = (values >= lower) & (values <= upper)
    return {
        "fraction_in_support": float(in_support.mean()),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
    }


def power_for_two_proportions(
    n_total: int,
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
) -> dict[str, float | int]:
    """Normal approximation for equal-sized arms and a two-sided test."""
    if n_total < 4:
        return {"power": 0.0, "required_n": 4}
    p0 = min(max(baseline_rate, EPS), 1.0 - EPS)
    p1 = min(max(p0 + minimum_detectable_effect, EPS), 1.0 - EPS)
    n_arm = n_total / 2.0
    p_bar = (p0 + p1) / 2.0
    alternative_se = math.sqrt(p0 * (1 - p0) / n_arm + p1 * (1 - p1) / n_arm)
    null_se = math.sqrt(2.0 * p_bar * (1.0 - p_bar) / n_arm)
    z_alpha = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    critical_difference = z_alpha * null_se
    effect = abs(p1 - p0)
    power = 1.0 - _normal_cdf((critical_difference - effect) / max(alternative_se, EPS))
    power += _normal_cdf((-critical_difference - effect) / max(alternative_se, EPS))
    z_power = NormalDist().inv_cdf(0.8)
    required_per_arm = (
        (
            z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
            + z_power * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))
        )
        / max(abs(p1 - p0), EPS)
    ) ** 2
    return {
        "power": float(min(max(power, 0.0), 1.0)),
        "required_n": int(math.ceil(2.0 * required_per_arm)),
    }


def population_stability_index(
    reference: Iterable[float],
    current: Iterable[float],
    bins: int = 10,
) -> float:
    reference_values = np.asarray(list(reference), dtype=float)
    current_values = np.asarray(list(current), dtype=float)
    if reference_values.size < bins or current_values.size < bins:
        raise ValueError("PSI requires at least as many observations as bins")
    edges = np.unique(np.quantile(reference_values, np.linspace(0.0, 1.0, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    reference_counts, _ = np.histogram(reference_values, bins=edges)
    current_counts, _ = np.histogram(current_values, bins=edges)
    ref_share = np.clip(reference_counts / reference_counts.sum(), 1e-6, None)
    cur_share = np.clip(current_counts / current_counts.sum(), 1e-6, None)
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def multivariate_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    features: list[str],
) -> dict[str, object]:
    per_feature = {
        feature: population_stability_index(reference[feature], current[feature])
        for feature in features
    }
    return {
        "psi": per_feature,
        "max_psi": max(per_feature.values(), default=0.0),
        "mean_psi": float(np.mean(list(per_feature.values()))) if per_feature else 0.0,
    }


def bootstrap_sign_stability(
    data: pd.DataFrame, draws: int = 250, seed: int = 0
) -> float:
    """Fraction of bootstrap estimates sharing the full-sample effect sign."""
    estimate = float(rct_uplift(data)["uplift"])
    if abs(estimate) < EPS:
        return 0.5
    rng = np.random.default_rng(seed)
    same_sign = 0
    treatment = data[data["treatment"] == 1]
    control = data[data["treatment"] == 0]
    for _ in range(draws):
        t = treatment["outcome"].to_numpy()[rng.integers(0, len(treatment), len(treatment))]
        c = control["outcome"].to_numpy()[rng.integers(0, len(control), len(control))]
        same_sign += int(np.sign(t.mean() - c.mean()) == np.sign(estimate))
    return same_sign / draws


def describe_data(
    data: pd.DataFrame,
    treatment_col: str = "treatment",
    outcome_col: str = "outcome",
    segment_col: str = "segment",
) -> dict[str, object]:
    """Structured dataset card used before any inferential tool is authorized."""
    if data.empty:
        raise ValueError("Data description requires at least one row")
    required = {treatment_col, outcome_col, segment_col}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Data description is missing columns: {sorted(missing)}")
    treatment = data[treatment_col]
    outcome = data[outcome_col]
    if not treatment.dropna().isin([0, 1]).all() or not outcome.dropna().isin([0, 1]).all():
        raise ValueError("Treatment and outcome columns must be binary")
    return {
        "rows": len(data),
        "columns": len(data.columns),
        "missing_cells": int(data.isna().sum().sum()),
        "missing_by_column": {key: int(value) for key, value in data.isna().sum().items()},
        "treatment_share": float(treatment.mean()),
        "outcome_rate": float(outcome.mean()),
        "segments": int(data[segment_col].nunique()),
        "segment_rows": {
            str(key): int(value) for key, value in data[segment_col].value_counts().items()
        },
    }


def evaluate_guardrail(
    diversity_deltas: Iterable[float], max_diversity_loss: float
) -> dict[str, float | bool | int]:
    """Check row/cohort diversity changes against a hard maximum loss."""
    values = np.asarray(list(diversity_deltas), dtype=float)
    if values.size == 0:
        raise ValueError("Guardrail evaluation requires at least one diversity delta")
    if not np.isfinite(values).all():
        raise ValueError("Diversity deltas must be finite")
    if max_diversity_loss < 0 or not math.isfinite(max_diversity_loss):
        raise ValueError("max_diversity_loss must be finite and non-negative")
    violations = values < -max_diversity_loss
    return {
        "passed": bool(not violations.any()),
        "evaluated": int(values.size),
        "violations": int(violations.sum()),
        "violation_rate": float(violations.mean()),
        "mean_delta": float(values.mean()),
        "worst_delta": float(values.min()),
        "allowed_minimum": -float(max_diversity_loss),
    }


def off_policy_evaluate(
    rewards: Iterable[float],
    behavior_propensity: Iterable[float],
    target_propensity: Iterable[float],
    max_weight: float | None = None,
    confidence: float = 0.95,
) -> dict[str, float | int]:
    """IPS and self-normalized IPS for probabilities of each logged action."""
    reward = np.asarray(list(rewards), dtype=float)
    behavior = np.asarray(list(behavior_propensity), dtype=float)
    target = np.asarray(list(target_propensity), dtype=float)
    if reward.size < 2 or not (reward.size == behavior.size == target.size):
        raise ValueError("OPE inputs must have the same length and contain at least two rows")
    if not np.isfinite(reward).all() or not np.isfinite(behavior).all() or not np.isfinite(target).all():
        raise ValueError("OPE inputs must be finite")
    if ((reward < 0) | (reward > 1)).any():
        raise ValueError("Rewards must lie in [0, 1]")
    if ((behavior <= 0) | (behavior > 1)).any():
        raise ValueError("Behavior propensities must lie in (0, 1]")
    if ((target < 0) | (target > 1)).any():
        raise ValueError("Target propensities must lie in [0, 1]")
    if max_weight is not None and (max_weight <= 0 or not math.isfinite(max_weight)):
        raise ValueError("max_weight must be finite and positive")
    weights = target / behavior
    if max_weight is not None:
        weights = np.minimum(weights, max_weight)
    if weights.sum() <= 0:
        raise ValueError("Target propensities assign zero mass to every logged action")
    contributions = weights * reward
    ips = float(contributions.mean())
    snips = float(contributions.sum() / weights.sum())
    standard_error = float(contributions.std(ddof=1) / math.sqrt(len(contributions)))
    z_critical = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    ess = float(weights.sum() ** 2 / np.square(weights).sum())
    return {
        "rows": int(reward.size),
        "ips": ips,
        "snips": snips,
        "standard_error": standard_error,
        "ci_low": ips - z_critical * standard_error,
        "ci_high": ips + z_critical * standard_error,
        "effective_sample_size": ess,
        "max_observed_weight": float(weights.max()),
    }


def compute_evsi(
    effect_mean: float,
    current_standard_error: float,
    future_posterior_standard_error: float,
    deployment_value_scale: float = 1.0,
    experiment_cost: float = 0.0,
) -> dict[str, float | bool]:
    """Normal-normal expected value of sample information for a deploy/abstain choice.

    Before sampling, the future posterior mean has variance equal to the reduction
    in posterior variance. EVSI is the expected positive future decision value
    minus the current positive decision value.
    """
    numeric = (
        effect_mean,
        current_standard_error,
        future_posterior_standard_error,
        deployment_value_scale,
        experiment_cost,
    )
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("EVSI inputs must be finite")
    if current_standard_error <= 0:
        raise ValueError("current_standard_error must be positive")
    if future_posterior_standard_error < 0:
        raise ValueError("future_posterior_standard_error cannot be negative")
    if future_posterior_standard_error > current_standard_error:
        raise ValueError("Future posterior uncertainty cannot exceed current uncertainty")
    if deployment_value_scale <= 0 or experiment_cost < 0:
        raise ValueError("deployment_value_scale must be positive and experiment_cost non-negative")
    mean_sd = math.sqrt(
        max(current_standard_error**2 - future_posterior_standard_error**2, 0.0)
    )
    if mean_sd == 0:
        expected_future_positive = max(effect_mean, 0.0)
    else:
        z_score = effect_mean / mean_sd
        density = math.exp(-0.5 * z_score**2) / math.sqrt(2.0 * math.pi)
        expected_future_positive = mean_sd * density + effect_mean * _normal_cdf(z_score)
    current_positive = max(effect_mean, 0.0)
    gross_evsi = max(expected_future_positive - current_positive, 0.0) * deployment_value_scale
    net_evsi = gross_evsi - experiment_cost
    return {
        "gross_evsi": gross_evsi,
        "net_evsi": net_evsi,
        "experiment_cost": experiment_cost,
        "recommend_experiment": net_evsi > 0,
    }
