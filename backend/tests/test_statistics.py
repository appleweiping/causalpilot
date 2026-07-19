import numpy as np
import pandas as pd
import pytest

from causalpilot.scenario import FEATURES, generate_drift_population, generate_rct, generate_reference_population
from causalpilot.statistics import (
    compute_evsi,
    covariate_balance,
    describe_data,
    evaluate_guardrail,
    multivariate_drift,
    off_policy_evaluate,
    power_for_two_proportions,
    rct_uplift,
    sample_ratio_mismatch,
)


def test_rct_uplift_is_reproducible_and_positive():
    first = rct_uplift(generate_rct(seed=42, n=9_000))
    second = rct_uplift(generate_rct(seed=42, n=9_000))
    assert first == second
    assert first["treatment_n"] == first["control_n"] == 4_500
    assert first["uplift"] > 0.01
    assert first["ci_low"] > 0


def test_srm_and_covariate_balance_pass_for_seeded_rct():
    data = generate_rct(seed=7, n=8_000)
    srm = sample_ratio_mismatch(data["treatment"])
    balance = covariate_balance(data, FEATURES)
    assert srm["p_value"] == pytest.approx(1.0)
    assert balance["max_smd"] < 0.1


def test_srm_detects_large_assignment_failure():
    assignments = np.concatenate([np.ones(900), np.zeros(100)])
    assert sample_ratio_mismatch(assignments)["p_value"] < 1e-20


def test_population_shift_raises_psi():
    reference = generate_reference_population(seed=5, n=3_000)
    current = generate_drift_population(seed=5, severity=0.8, n=3_000)
    drift = multivariate_drift(reference, current, FEATURES)
    assert drift["max_psi"] > 0.1
    assert set(drift["psi"]) == set(FEATURES)


def test_population_shift_targets_requested_segment():
    current = generate_drift_population(
        seed=5,
        severity=0.8,
        segment_id="loyalists",
        n=3_000,
    )
    shares = current["segment"].value_counts(normalize=True)
    assert shares["loyalists"] > 0.50


def test_rct_rejects_missing_arm():
    frame = pd.DataFrame({"treatment": [1, 1], "outcome": [0, 1]})
    with pytest.raises(ValueError, match="non-empty"):
        rct_uplift(frame)


def test_structured_description_and_guardrail():
    data = generate_rct(seed=2, n=2_000)
    description = describe_data(data)
    guardrail = evaluate_guardrail([-0.01, -0.03, 0.002], max_diversity_loss=0.02)
    assert description["rows"] == 2_000
    assert description["segments"] == 4
    assert guardrail["passed"] is False
    assert guardrail["violations"] == 1
    with pytest.raises(ValueError, match="at least one"):
        evaluate_guardrail([], 0.02)


def test_off_policy_evaluation_and_validation():
    result = off_policy_evaluate(
        rewards=[1, 0, 1, 0],
        behavior_propensity=[0.5, 0.5, 0.5, 0.5],
        target_propensity=[0.5, 0.5, 0.5, 0.5],
    )
    assert result["ips"] == pytest.approx(0.5)
    assert result["snips"] == pytest.approx(0.5)
    assert result["effective_sample_size"] == pytest.approx(4.0)
    with pytest.raises(ValueError, match="Behavior propensities"):
        off_policy_evaluate([1, 0], [0, 0.5], [0.5, 0.5])


def test_evsi_is_positive_when_information_can_change_the_action():
    result = compute_evsi(
        effect_mean=0.001,
        current_standard_error=0.03,
        future_posterior_standard_error=0.01,
        deployment_value_scale=10_000,
        experiment_cost=5,
    )
    assert result["gross_evsi"] > 0
    assert result["recommend_experiment"] is True
    with pytest.raises(ValueError, match="cannot exceed"):
        compute_evsi(0.01, 0.02, 0.03)


def test_power_required_n_uses_pooled_null_variance_and_round_trips():
    design = power_for_two_proportions(
        n_total=100,
        baseline_rate=0.01,
        minimum_detectable_effect=0.01,
    )
    assert 4_500 <= design["required_n"] <= 4_800
    achieved = power_for_two_proportions(
        n_total=int(design["required_n"]),
        baseline_rate=0.01,
        minimum_detectable_effect=0.01,
    )
    assert achieved["power"] >= 0.79
