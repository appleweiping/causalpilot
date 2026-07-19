"""Deterministic policy benchmark with strict truth/observation separation.

Policies receive :class:`PolicyObservation` only. Potential outcomes and oracle
constraints live in :class:`EpisodeTruth` and are passed exclusively to scoring.
Named LLM baselines remain disclosed decision-rule proxies, not fabricated runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist
from typing import Callable

import numpy as np

from causalpilot.policy import (
    SegmentEvidence,
    TracePolicyInput,
    evaluate_trace_policy,
    select_minimum_scope,
)
from causalpilot.scenario import (
    FIXTURE_HASH,
    FIXTURE_VERSION,
    SEGMENTS,
    generate_historical,
    generate_rct,
)
from causalpilot.statistics import power_for_two_proportions, rct_uplift, segment_uplifts


EXPOSURE_COST = 2e-7
HUMAN_QUERY_COST = 4e-4
MAX_DIVERSITY_LOSS = 0.02


@dataclass(frozen=True)
class DriftAlert:
    detected: bool
    segment_id: str | None
    psi: float


@dataclass(frozen=True)
class HumanConstraintObservation:
    margin_floor: float
    subsidy_cap: float


@dataclass(frozen=True)
class PolicyObservation:
    historical: dict[str, dict[str, float | int]]
    randomized: dict[str, dict[str, float | int]]
    drift_alert: DriftAlert
    human_response: HumanConstraintObservation
    model_risk: float
    causal_risk: float
    data_risk: float
    environment_risk: float


@dataclass(frozen=True)
class EpisodeTruth:
    pre_shift_effects: dict[str, float]
    post_shift_effects: dict[str, float]
    drift_segment: str
    margin_floor: float
    subsidy_cap: float


@dataclass(frozen=True)
class BenchmarkEpisode:
    seed: int
    observation: PolicyObservation
    truth: EpisodeTruth


@dataclass(frozen=True)
class PolicyOutput:
    deployed: tuple[str, ...]
    experiment_samples: int
    human_questions: int
    intervals: dict[str, tuple[float, float]]
    probabilities: dict[str, float]
    actions: tuple[str, ...]
    method_type: str


def _positive_probability(estimate: dict[str, float | int], overconfidence: float = 1.0) -> float:
    standard_error = max(float(estimate["standard_error"]), 1e-9)
    probability = NormalDist().cdf(float(estimate["uplift"]) / standard_error)
    return min(max(0.5 + (probability - 0.5) * overconfidence, 0.001), 0.999)


def _intervals(estimates: dict[str, dict[str, float | int]]) -> dict[str, tuple[float, float]]:
    return {
        segment: (float(result["ci_low"]), float(result["ci_high"]))
        for segment, result in estimates.items()
    }


def _probabilities(
    estimates: dict[str, dict[str, float | int]], overconfidence: float = 1.0
) -> dict[str, float]:
    return {
        segment: _positive_probability(result, overconfidence)
        for segment, result in estimates.items()
    }


def _diversity_safe(segment_id: str) -> bool:
    spec = next(segment for segment in SEGMENTS if segment.id == segment_id)
    return spec.diversity_delta >= -MAX_DIVERSITY_LOSS


def make_episode(seed: int) -> BenchmarkEpisode:
    historical_data = generate_historical(seed, n=4_000)
    randomized_data = generate_rct(seed, n=9_000)
    historical = segment_uplifts(historical_data)
    randomized = segment_uplifts(randomized_data)
    segment_ids = [segment.id for segment in SEGMENTS]

    # Hidden potential outcomes. Policies never receive this object.
    true_drift_segment = segment_ids[seed % len(segment_ids)]
    pre_shift = {segment.id: segment.treatment_effect for segment in SEGMENTS}
    post_shift = dict(pre_shift)
    post_shift[true_drift_segment] -= 0.055
    margin_floor = (0.12, 0.15, 0.18, 0.20)[(seed // 2) % 4]
    subsidy_cap = (3.0, 6.0, 9.0, 12.0)[(seed // 3) % 4]
    truth = EpisodeTruth(pre_shift, post_shift, true_drift_segment, margin_floor, subsidy_cap)

    # Policy-visible detector output is imperfect by construction: 82% correct,
    # 10% misses, and 8% wrong-cohort alerts under the seeded simulation.
    detector_rng = np.random.default_rng(seed + 20_260_719)
    detector_draw = float(detector_rng.random())
    if detector_draw < 0.82:
        observed_segment = true_drift_segment
    elif detector_draw < 0.92:
        observed_segment = None
    else:
        alternatives = [value for value in segment_ids if value != true_drift_segment]
        observed_segment = alternatives[int(detector_rng.integers(0, len(alternatives)))]
    drift_alert = DriftAlert(
        detected=observed_segment is not None,
        segment_id=observed_segment,
        psi=0.42 if observed_segment is not None else 0.08,
    )
    overall = rct_uplift(randomized_data)
    power = power_for_two_proportions(
        len(randomized_data), float(overall["control_rate"]), 0.025
    )["power"]
    observation = PolicyObservation(
        historical=historical,
        randomized=randomized,
        drift_alert=drift_alert,
        human_response=HumanConstraintObservation(margin_floor, subsidy_cap),
        model_risk=0.06,
        causal_risk=0.07,
        data_risk=0.10 + 0.40 * (1.0 - float(power)),
        environment_risk=0.90 if observed_segment is not None else 0.10,
    )
    return BenchmarkEpisode(seed, observation, truth)


def direct_proxy(observation: PolicyObservation) -> PolicyOutput:
    probabilities = _probabilities(observation.historical, overconfidence=1.8)
    deployed = tuple(segment for segment, probability in probabilities.items() if probability >= 0.70)
    return PolicyOutput(deployed, 0, 0, _intervals(observation.historical), probabilities,
                        ("recommend", "deploy"), "deterministic proxy for direct LLM recommendation")


def react_like_proxy(observation: PolicyObservation) -> PolicyOutput:
    probabilities = _probabilities(observation.randomized)
    deployed = tuple(
        segment for segment, result in observation.randomized.items()
        if float(result["uplift"]) > 0 and _diversity_safe(segment)
    )
    return PolicyOutput(deployed, 9_000, 0, _intervals(observation.randomized), probabilities,
                        ("inspect", "experiment", "reason", "deploy"),
                        "deterministic ReAct-like tool-use proxy")


def fixed_pipeline(observation: PolicyObservation) -> PolicyOutput:
    probabilities = _probabilities(observation.randomized)
    deployed = tuple(
        segment for segment, result in observation.randomized.items()
        if float(result["ci_low"]) > 0 and _diversity_safe(segment)
    )
    return PolicyOutput(deployed, 9_000, 0, _intervals(observation.randomized), probabilities,
                        ("experiment", "ci_gate", "deploy"), "fixed causal analysis pipeline")


def causalpilot_no_trace(observation: PolicyObservation) -> PolicyOutput:
    probabilities = _probabilities(observation.randomized)
    deployed = tuple(
        segment for segment, result in observation.randomized.items()
        if float(result["uplift"]) > 0 and _diversity_safe(segment)
    )
    return PolicyOutput(
        deployed, 9_000, 0, _intervals(observation.randomized), probabilities,
        ("hypothesize", "experiment", "analyze", "remember", "maximize_point_estimate"),
        "deterministic CausalPilot coordinator without TRACE risk gates",
    )


def verbal_confidence(observation: PolicyObservation) -> PolicyOutput:
    probabilities = _probabilities(observation.historical, overconfidence=2.4)
    deployed = tuple(segment for segment, probability in probabilities.items() if probability >= 0.80)
    return PolicyOutput(deployed, 0, 0, _intervals(observation.historical), probabilities,
                        ("verbalize_confidence", "threshold", "deploy"),
                        "verbalized-confidence proxy")


def _shared_trace_output(
    observation: PolicyObservation,
    *,
    use_experiment: bool = True,
    use_dynamic_risk: bool = True,
    use_human_query: bool = True,
) -> PolicyOutput:
    estimates = observation.randomized if use_experiment else observation.historical
    evidence = tuple(
        SegmentEvidence(
            segment_id=spec.id,
            uplift=float(estimates[spec.id]["uplift"]),
            ci_low=float(estimates[spec.id]["ci_low"]),
            ci_high=float(estimates[spec.id]["ci_high"]),
            diversity_delta=spec.diversity_delta,
            contribution_margin=spec.contribution_margin,
            required_subsidy=spec.required_subsidy,
        )
        for spec in SEGMENTS
    )
    observed_drift = (
        observation.drift_alert.segment_id
        if use_dynamic_risk and observation.drift_alert.detected
        else None
    )
    decision = evaluate_trace_policy(
        TracePolicyInput(
            segments=evidence,
            model_risk=observation.model_risk,
            causal_risk=observation.causal_risk if use_experiment else 0.82,
            data_risk=observation.data_risk,
            environment_risk=observation.environment_risk if use_dynamic_risk else 0.10,
            max_diversity_loss=MAX_DIVERSITY_LOSS,
            margin_floor=observation.human_response.margin_floor if use_human_query else None,
            subsidy_cap=observation.human_response.subsidy_cap if use_human_query else None,
            observed_drift_segment=observed_drift,
            require_human_constraints=use_human_query,
        )
    )
    deployed = () if not decision.eligible_segments else (select_minimum_scope(decision),)
    human_questions = int(use_human_query) + int(
        use_human_query and use_dynamic_risk and observation.drift_alert.detected
    )
    actions = ["experiment" if use_experiment else "diagnose_logs", "update_risk_indices"]
    if use_dynamic_risk:
        actions.append("detect_drift")
    if use_human_query:
        actions.append("ask_human")
    actions.append("segment_deploy" if deployed else "abstain")
    label_parts = ["TRACE"]
    if not use_dynamic_risk:
        label_parts.append("ablation: no dynamic risk update")
    if not use_experiment:
        label_parts.append("ablation: no randomized experiment")
    if not use_human_query:
        label_parts.append("ablation: no human query")
    return PolicyOutput(
        deployed=deployed,
        experiment_samples=9_000 if use_experiment else 0,
        human_questions=human_questions,
        intervals=_intervals(estimates),
        probabilities=_probabilities(estimates),
        actions=tuple(actions),
        method_type="; ".join(label_parts),
    )


def trace(observation: PolicyObservation) -> PolicyOutput:
    return _shared_trace_output(observation)


def always_deploy(observation: PolicyObservation) -> PolicyOutput:
    return PolicyOutput(tuple(segment.id for segment in SEGMENTS), 0, 0, {},
                        {segment.id: 0.99 for segment in SEGMENTS}, ("deploy",),
                        "always-deploy lower safety bound")


def always_ask_human(observation: PolicyObservation) -> PolicyOutput:
    return PolicyOutput((), 0, 1, {}, {segment.id: 0.01 for segment in SEGMENTS},
                        ("ask_human",), "always-escalate lower autonomy bound")


def trace_no_dynamic_risk(observation: PolicyObservation) -> PolicyOutput:
    return _shared_trace_output(observation, use_dynamic_risk=False)


def trace_no_experiment(observation: PolicyObservation) -> PolicyOutput:
    return _shared_trace_output(observation, use_experiment=False)


def trace_no_human_query(observation: PolicyObservation) -> PolicyOutput:
    return _shared_trace_output(observation, use_human_query=False)


def trace_static_threshold(observation: PolicyObservation) -> PolicyOutput:
    probabilities = _probabilities(observation.randomized)
    deployed = tuple(
        segment for segment, probability in probabilities.items()
        if probability >= 0.85 and _diversity_safe(segment)
    )
    return PolicyOutput(deployed, 9_000, 0, _intervals(observation.randomized), probabilities,
                        ("experiment", "global_threshold", "deploy"),
                        "TRACE ablation: static confidence threshold")


METHODS: dict[str, Callable[[PolicyObservation], PolicyOutput]] = {
    "direct_proxy": direct_proxy,
    "react_like_proxy": react_like_proxy,
    "fixed_pipeline": fixed_pipeline,
    "causalpilot_no_trace": causalpilot_no_trace,
    "verbal_confidence": verbal_confidence,
    "trace": trace,
    "always_deploy": always_deploy,
    "always_ask_human": always_ask_human,
    "trace_no_dynamic_calibration": trace_no_dynamic_risk,
    "trace_no_experiment": trace_no_experiment,
    "trace_no_human_query": trace_no_human_query,
    "trace_static_threshold": trace_static_threshold,
}


def _ece(probabilities: dict[str, float], labels: dict[str, int]) -> float:
    bins = np.linspace(0.0, 1.0, 6)
    error = 0.0
    total = len(probabilities)
    for left, right in zip(bins[:-1], bins[1:], strict=True):
        keys = [
            key for key, probability in probabilities.items()
            if left <= probability < right or (right == 1.0 and probability == 1.0)
        ]
        if keys:
            confidence = float(np.mean([probabilities[key] for key in keys]))
            accuracy = float(np.mean([labels[key] for key in keys]))
            error += len(keys) / total * abs(confidence - accuracy)
    return error


def score_policy(
    method: str,
    seed: int,
    observation: PolicyObservation,
    truth: EpisodeTruth,
    output: PolicyOutput,
) -> dict[str, object]:
    specs = {segment.id: segment for segment in SEGMENTS}
    deployed = set(output.deployed)
    oracle = {
        segment.id for segment in SEGMENTS
        if truth.post_shift_effects[segment.id] > 0
        and _diversity_safe(segment.id)
        and segment.contribution_margin >= truth.margin_floor
        and segment.id != truth.drift_segment
    }
    gross_value = sum(specs[value].share * truth.post_shift_effects[value] for value in deployed)
    oracle_value = sum(specs[value].share * truth.post_shift_effects[value] for value in oracle)
    net_value = gross_value - output.experiment_samples * EXPOSURE_COST - output.human_questions * HUMAN_QUERY_COST
    harmful = [value for value in deployed if truth.post_shift_effects[value] <= 0]
    violations = [
        value for value in deployed
        if not _diversity_safe(value)
        or specs[value].contribution_margin < truth.margin_floor
        or value == truth.drift_segment
        or (value == truth.drift_segment and specs[value].required_subsidy > truth.subsidy_cap)
    ]
    labels = {segment.id: int(truth.post_shift_effects[segment.id] > 0) for segment in SEGMENTS}
    brier = float(np.mean([
        (output.probabilities.get(segment.id, 0.5) - labels[segment.id]) ** 2
        for segment in SEGMENTS
    ]))
    covered = sum(
        int(interval[0] <= truth.post_shift_effects[segment] <= interval[1])
        for segment, interval in output.intervals.items()
    )
    interval_total = len(output.intervals)
    covered_oracle_value = sum(
        specs[value].share * truth.post_shift_effects[value]
        for value in deployed.intersection(oracle)
    )
    harmful_value = sum(specs[value].share * abs(truth.post_shift_effects[value]) for value in harmful)
    policy_regret_gt = max(oracle_value - covered_oracle_value, 0.0) + harmful_value
    false_deployment_rate_gt = float(bool(harmful))
    harmful_deployment_rate_gt = len(harmful) / max(len(deployed), 1)
    constraint_violation_rate_gt = len(violations) / max(len(deployed), 1)
    return {
        "seed": seed,
        "method": method,
        "method_type": output.method_type,
        "deployed_segments": ";".join(sorted(deployed)),
        "drift_segment_gt": truth.drift_segment,
        "observed_drift_segment": observation.drift_alert.segment_id or "",
        "margin_floor_observed": observation.human_response.margin_floor,
        "gross_policy_value_gt": gross_value,
        "net_policy_value_gt": net_value,
        "oracle_policy_value_gt": oracle_value,
        "normalized_policy_value_gt": covered_oracle_value / oracle_value if oracle_value > 0 else 0.0,
        "policy_regret_gt": policy_regret_gt,
        "false_deployment_rate_gt": false_deployment_rate_gt,
        "harmful_deployment_rate_gt": harmful_deployment_rate_gt,
        "constraint_violation_rate_gt": constraint_violation_rate_gt,
        "harmful_deployments_gt": len(harmful),
        "constraint_violations_gt": len(violations),
        "deployment_count": len(deployed),
        "coverage": sum(specs[value].share for value in deployed),
        "interval_coverage_gt": covered / interval_total if interval_total else 0.0,
        "interval_covered_gt": covered,
        "interval_total": interval_total,
        "post_shift_transfer_brier_gt": brier,
        "post_shift_transfer_ece_gt": _ece(output.probabilities, labels),
        "experiment_samples": output.experiment_samples,
        "human_questions": output.human_questions,
        "action_count": len(output.actions),
        "llm_api_calls": 0,
        "token_count": 0,
    }


def evaluate_seed(seed: int) -> list[dict[str, object]]:
    episode = make_episode(seed)
    return [
        score_policy(name, episode.seed, episode.observation, episode.truth, method(episode.observation))
        for name, method in METHODS.items()
    ]


def benchmark_metadata(seeds: list[int]) -> dict[str, object]:
    return {
        "benchmark": "CausalPilot synthetic selective-deployment benchmark",
        "evidence_mode": "simulated_scm",
        "fixture_version": FIXTURE_VERSION,
        "fixture_hash": FIXTURE_HASH,
        "dataset_version": FIXTURE_VERSION,
        "split": "paired_seeded_episodes",
        "estimator": {
            "segment_effect": "difference_in_means_wald_95",
            "continuous_interval": "seed_percentile_bootstrap",
            "proportion_interval": "wilson_score",
        },
        "assumptions": [
            "Known potential outcomes are used only by the scorer.",
            "Policies observe imperfect drift alerts rather than hidden drift truth.",
            "Risk values are engineering indices, not calibrated probabilities.",
            "Named LLM baselines are deterministic decision-rule proxies.",
        ],
        "gate_thresholds": {
            "maximum_core_risk": 0.33,
            "maximum_environment_risk": 0.33,
            "max_diversity_loss": MAX_DIVERSITY_LOSS,
            "positive_lower_confidence_bound_required": True,
        },
        "detector_parameters": {
            "correct_alert_probability": 0.82,
            "miss_probability": 0.10,
            "wrong_cohort_probability": 0.08,
            "alert_psi": 0.42,
            "no_alert_psi": 0.08,
        },
        "seeds": seeds,
        "n_methods": len(METHODS),
        "api_keys_required": False,
        "truth_policy_separation": (
            "Policies receive PolicyObservation only. EpisodeTruth is supplied solely to score_policy. "
            "TRACE calls causalpilot.policy.evaluate_trace_policy and select_minimum_scope, the same "
            "shared policy functions used by the backend engine."
        ),
        "llm_baseline_disclosure": (
            "direct_proxy, react_like_proxy, verbal_confidence, and causalpilot_no_trace are "
            "deterministic decision-rule proxies; they are not executions of a named language model."
        ),
        "confidence_intervals": {
            "continuous_method": "percentile bootstrap over episode seeds",
            "proportion_method": "Wilson score interval",
            "resamples": 2_000,
            "bootstrap_seed": 20_260_719,
            "level": 0.95,
        },
        "cost_model": {"exposure_cost": EXPOSURE_COST, "human_query_cost": HUMAN_QUERY_COST},
        "ground_truth": (
            "Known potential outcomes are simulation-only and use _gt fields. Detector observations "
            "are imperfect and distinct from hidden drift truth."
        ),
        "claim_scope": (
            "Controlled-simulation engineering benchmark only. These results validate executable "
            "gates and failure behavior; they are not a causal research conclusion or real-world lift claim."
        ),
    }
