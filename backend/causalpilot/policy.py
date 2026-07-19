"""Shared TRACE policy gate used by both the API engine and offline evaluation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SegmentEvidence:
    segment_id: str
    uplift: float
    ci_low: float
    ci_high: float
    diversity_delta: float
    contribution_margin: float
    required_subsidy: float


@dataclass(frozen=True)
class TracePolicyInput:
    segments: tuple[SegmentEvidence, ...]
    model_risk: float
    causal_risk: float
    data_risk: float
    environment_risk: float
    max_diversity_loss: float
    margin_floor: float | None
    subsidy_cap: float | None
    observed_drift_segment: str | None
    require_human_constraints: bool = True
    maximum_core_risk: float = 0.33
    maximum_environment_risk: float = 0.33


@dataclass(frozen=True)
class TracePolicyDecision:
    eligible_segments: tuple[str, ...]
    conservative_scores: dict[str, float]
    blocked_reasons: dict[str, tuple[str, ...]]


def evaluate_trace_policy(policy_input: TracePolicyInput) -> TracePolicyDecision:
    """Apply evidence, economic, diversity, and observed-support gates.

    This function accepts only policy-visible evidence. It has no potential-outcome
    or oracle fields, which keeps evaluation truth outside the decision path.
    """
    core_risks = {
        "model": policy_input.model_risk,
        "causal": policy_input.causal_risk,
        "data": policy_input.data_risk,
    }
    invalid_risks = [name for name, value in core_risks.items() if not 0 <= value <= 1]
    if invalid_risks or not 0 <= policy_input.environment_risk <= 1:
        raise ValueError("TRACE risks must lie in [0, 1]")
    if policy_input.max_diversity_loss < 0:
        raise ValueError("max_diversity_loss must be non-negative")
    global_blocks = [
        f"{name}_risk_above_gate"
        for name, value in core_risks.items()
        if value > policy_input.maximum_core_risk
    ]
    if policy_input.require_human_constraints and policy_input.margin_floor is None:
        global_blocks.append("missing_margin_floor")

    eligible: list[str] = []
    scores: dict[str, float] = {}
    blocked: dict[str, tuple[str, ...]] = {}
    for evidence in policy_input.segments:
        reasons = list(global_blocks)
        if evidence.ci_low <= 0:
            reasons.append("nonpositive_conservative_uplift")
        if evidence.diversity_delta < -policy_input.max_diversity_loss:
            reasons.append("diversity_guardrail")
        if (
            policy_input.margin_floor is not None
            and evidence.contribution_margin < policy_input.margin_floor
        ):
            reasons.append("margin_floor")
        if evidence.segment_id == policy_input.observed_drift_segment:
            if policy_input.environment_risk > policy_input.maximum_environment_risk:
                reasons.append("observed_support_shift")
            if policy_input.require_human_constraints and policy_input.subsidy_cap is None:
                reasons.append("missing_subsidy_cap")
            elif (
                policy_input.subsidy_cap is not None
                and evidence.required_subsidy > policy_input.subsidy_cap
            ):
                reasons.append("subsidy_cap")
        if reasons:
            blocked[evidence.segment_id] = tuple(dict.fromkeys(reasons))
        else:
            eligible.append(evidence.segment_id)
            scores[evidence.segment_id] = evidence.ci_low
    eligible.sort(key=lambda value: (scores[value], value), reverse=True)
    return TracePolicyDecision(tuple(eligible), scores, blocked)


def select_minimum_scope(
    decision: TracePolicyDecision, requested_segment: str | None = None
) -> str:
    """Select one conservative segment; full expansion is a separate action."""
    if not decision.eligible_segments:
        raise ValueError("No segment passed the TRACE policy gates")
    if requested_segment is not None:
        if requested_segment not in decision.eligible_segments:
            reasons = decision.blocked_reasons.get(requested_segment, ())
            raise ValueError(
                f"Segment '{requested_segment}' did not pass TRACE gates: {list(reasons)}"
            )
        return requested_segment
    return decision.eligible_segments[0]
