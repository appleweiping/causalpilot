import pytest

from causalpilot.policy import (
    SegmentEvidence,
    TracePolicyInput,
    evaluate_trace_policy,
    select_minimum_scope,
)


def evidence() -> tuple[SegmentEvidence, ...]:
    return (
        SegmentEvidence("safe", 0.04, 0.02, 0.06, -0.01, 0.24, 2.0),
        SegmentEvidence("thin_margin", 0.05, 0.03, 0.07, -0.01, 0.12, 8.0),
    )


def policy_input(**updates) -> TracePolicyInput:
    values = {
        "segments": evidence(),
        "model_risk": 0.1,
        "causal_risk": 0.1,
        "data_risk": 0.1,
        "environment_risk": 0.1,
        "max_diversity_loss": 0.02,
        "margin_floor": 0.15,
        "subsidy_cap": None,
        "observed_drift_segment": None,
    }
    values.update(updates)
    return TracePolicyInput(**values)


def test_shared_policy_uses_margin_and_minimum_scope():
    decision = evaluate_trace_policy(policy_input())
    assert decision.eligible_segments == ("safe",)
    assert "margin_floor" in decision.blocked_reasons["thin_margin"]
    assert select_minimum_scope(decision) == "safe"
    with pytest.raises(ValueError, match="did not pass"):
        select_minimum_scope(decision, "thin_margin")


def test_shared_policy_uses_drift_subsidy_and_environment_gates():
    decision = evaluate_trace_policy(
        policy_input(
            observed_drift_segment="safe",
            environment_risk=0.9,
            subsidy_cap=1.0,
        )
    )
    assert "observed_support_shift" in decision.blocked_reasons["safe"]
    assert "subsidy_cap" in decision.blocked_reasons["safe"]
