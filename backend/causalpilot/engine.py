"""TRACE state machine and risk-aware decision policy."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from threading import RLock
from typing import Any
from uuid import uuid4

import pandas as pd

from .policy import (
    SegmentEvidence,
    TracePolicyInput,
    evaluate_trace_policy,
    select_minimum_scope,
)
from .scenario import (
    FEATURES,
    FIXTURE_HASH,
    FIXTURE_VERSION,
    SEGMENTS,
    SEGMENT_MAP,
    generate_drift_population,
    generate_historical,
    generate_rct,
    generate_reference_population,
)
from .schemas import (
    ActionType,
    AuditEvent,
    DecisionView,
    EvidenceMode,
    EpisodeSnapshot,
    HumanQuestion,
    MetricSnapshot,
    MissionState,
    RiskLevel,
    RiskProfile,
    RiskScore,
    SegmentStatus,
    SegmentView,
    StartMissionRequest,
)
from .statistics import (
    bootstrap_sign_stability,
    covariate_balance,
    multivariate_drift,
    power_for_two_proportions,
    propensity_overlap,
    rct_uplift,
    sample_ratio_mismatch,
    segment_uplifts,
)


# Explicit, inspectable action/state authorization. External observations (drift and
# a human answer) are handled separately because they are not agent actions.
ALLOWED_ACTIONS: dict[MissionState, tuple[ActionType, ...]] = {
    MissionState.DIAGNOSING: (
        ActionType.DIAGNOSE,
        ActionType.EXPERIMENT,
        ActionType.ASK_HUMAN,
        ActionType.ABSTAIN,
    ),
    MissionState.EXPERIMENTING: (ActionType.DIAGNOSE, ActionType.ASK_HUMAN, ActionType.ABSTAIN),
    MissionState.AWAITING_HUMAN: (
        ActionType.PAUSE_SEGMENT,
        ActionType.ROLLBACK,
        ActionType.ABSTAIN,
    ),
    MissionState.READY_TO_DEPLOY: (
        ActionType.DIAGNOSE,
        ActionType.SEGMENT_DEPLOY,
        ActionType.DEPLOY_ALL,
        ActionType.ABSTAIN,
    ),
    MissionState.DEPLOYED: (
        ActionType.DIAGNOSE,
        ActionType.PAUSE_SEGMENT,
        ActionType.ROLLBACK,
    ),
    MissionState.DRIFT_DETECTED: (
        ActionType.DIAGNOSE,
        ActionType.ASK_HUMAN,
        ActionType.PAUSE_SEGMENT,
        ActionType.ROLLBACK,
    ),
    MissionState.ROLLED_BACK: (),
    MissionState.ABSTAINED: (),
}


def _risk_level(score: float) -> RiskLevel:
    if score < 0.34:
        return RiskLevel.LOW
    if score < 0.67:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def _risk(score: float, evidence: list[str]) -> RiskScore:
    bounded = min(max(float(score), 0.0), 1.0)
    return RiskScore(score=bounded, level=_risk_level(bounded), evidence=evidence)


class MissionRuntime:
    """A single deterministic episode; DataFrames stay server-side."""

    def __init__(
        self,
        config: StartMissionRequest,
        mission_id: str | None = None,
        parent_mission_id: str | None = None,
    ) -> None:
        self._lock = RLock()
        self.config = config
        self.config_hash = sha256(
            json.dumps(
                config.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()[:16]
        self.mission_id = mission_id or f"mission_{uuid4().hex[:12]}"
        self.state = MissionState.DIAGNOSING
        self.step_number = 0
        self.budget_used = 0
        self.historical = generate_historical(config.seed)
        self.reference_population = generate_reference_population(config.seed)
        self.trial: pd.DataFrame | None = None
        self.drift_population: pd.DataFrame | None = None
        self.drift_segment: str | None = None
        self.drift_severity = 0.0
        self.human_constraints: dict[str, Any] = {}
        self.pending_question: HumanQuestion | None = None
        self.audit: list[AuditEvent] = []
        self.metrics = MetricSnapshot()
        self.segments: list[SegmentView] = []
        self.risks = self._analyze_historical()
        self.decision = DecisionView(
            action=ActionType.EXPERIMENT,
            rationale=(
                "Historical uplift is confounded: assignment imbalance and weak propensity "
                "overlap do not justify deployment. Buy causal evidence with a randomized probe."
            ),
            eligible_segments=[],
        )
        self._record(
            event="mission_started",
            before=MissionState.DIAGNOSING,
            after=MissionState.DIAGNOSING,
            details={
                "evidence_mode": EvidenceMode.SIMULATED_SCM.value,
                "fixture_version": FIXTURE_VERSION,
                "fixture_hash": FIXTURE_HASH,
                "config_hash": self.config_hash,
                "estimator": "difference_in_means_wald_95",
                "gate_thresholds": {
                    "maximum_core_risk": 0.33,
                    "maximum_environment_risk": 0.33,
                    "max_diversity_loss": config.max_diversity_loss,
                },
                "seed": config.seed,
                "historical_rows": len(self.historical),
                "parent_mission_id": parent_mission_id,
            },
            advance=False,
        )

    def _record(
        self,
        event: str,
        before: MissionState,
        after: MissionState,
        action: ActionType | None = None,
        details: dict[str, Any] | None = None,
        advance: bool = True,
    ) -> None:
        if advance:
            self.step_number += 1
        self.audit.append(
            AuditEvent(
                sequence=len(self.audit),
                timestamp=datetime.now(UTC).isoformat(),
                event=event,
                action=action,
                state_before=before,
                state_after=after,
                details=details or {},
            )
        )

    def _metrics_from_data(self, data: pd.DataFrame) -> MetricSnapshot:
        effect = rct_uplift(data)
        srm = sample_ratio_mismatch(data["treatment"])
        balance = covariate_balance(data, FEATURES)
        overlap = propensity_overlap(data["propensity"])
        power = power_for_two_proportions(
            len(data), float(effect["control_rate"]), minimum_detectable_effect=0.025
        )
        drift_psi = self.metrics.drift_psi if hasattr(self, "metrics") else 0.0
        return MetricSnapshot(
            exposures=int(effect["exposures"]),
            treatment_n=int(effect["treatment_n"]),
            control_n=int(effect["control_n"]),
            treatment_rate=float(effect["treatment_rate"]),
            control_rate=float(effect["control_rate"]),
            uplift=float(effect["uplift"]),
            ci_low=float(effect["ci_low"]),
            ci_high=float(effect["ci_high"]),
            p_value=float(effect["p_value"]),
            srm_p_value=float(srm["p_value"]),
            max_balance_smd=float(balance["max_smd"]),
            overlap_fraction=float(overlap["fraction_in_support"]),
            power=float(power["power"]),
            drift_psi=drift_psi,
            expected_incremental_conversions=self.metrics.expected_incremental_conversions
            if hasattr(self, "metrics")
            else 0.0,
            policy_regret=self.metrics.policy_regret if hasattr(self, "metrics") else 0.0,
        )

    def _refresh_policy_summary(self) -> None:
        """Recompute estimated policy summaries from currently active segment views."""
        view_map = {segment.id: segment for segment in self.segments}
        deployed_ids = [
            segment.id for segment in self.segments if segment.status == SegmentStatus.DEPLOYED
        ]
        selected_value = sum(
            SEGMENT_MAP[segment_id].share * max(view_map[segment_id].uplift, 0.0)
            for segment_id in deployed_ids
        )
        feasible_ids = self._eligible_segments() if self.trial is not None else []
        feasible_value = sum(
            SEGMENT_MAP[segment_id].share * max(view_map[segment_id].uplift, 0.0)
            for segment_id in feasible_ids
        )
        remaining = max(self.config.budget - self.budget_used, 0)
        self.metrics = self.metrics.model_copy(
            update={
                "expected_incremental_conversions": selected_value * remaining,
                "policy_regret": max(feasible_value - selected_value, 0.0),
            }
        )

    def _segment_views(self, data: pd.DataFrame, randomized: bool) -> list[SegmentView]:
        estimates = segment_uplifts(data)
        views: list[SegmentView] = []
        for spec in SEGMENTS:
            result = estimates[spec.id]
            ci_low, ci_high = float(result["ci_low"]), float(result["ci_high"])
            if not randomized:
                status = SegmentStatus.OBSERVE
                sign_risk = 0.65
            elif ci_low > 0 and spec.diversity_delta >= -self.config.max_diversity_loss:
                status = SegmentStatus.CANDIDATE
                sign_risk = min(0.25, float(result["p_value"]) / 2.0)
            elif ci_high < 0:
                status = SegmentStatus.HARMFUL
                sign_risk = min(0.25, float(result["p_value"]) / 2.0)
            else:
                status = SegmentStatus.HELD
                sign_risk = 0.5
            views.append(
                SegmentView(
                    id=spec.id,
                    label=spec.label,
                    share=spec.share,
                    status=status,
                    uplift=float(result["uplift"]),
                    ci_low=ci_low,
                    ci_high=ci_high,
                    risk=sign_risk,
                    diversity_delta=spec.diversity_delta,
                    coordinates=spec.coordinates,
                )
            )
        return views

    def _analyze_historical(self) -> RiskProfile:
        self.metrics = self._metrics_from_data(self.historical)
        self.segments = self._segment_views(self.historical, randomized=False)
        stability = bootstrap_sign_stability(self.historical, seed=self.config.seed)
        causal_score = min(
            1.0,
            0.58
            + 0.22 * (1.0 - self.metrics.overlap_fraction)
            + 0.20 * min(self.metrics.max_balance_smd / 0.20, 1.0),
        )
        return RiskProfile(
            model=_risk(
                max(0.32, 1.0 - stability),
                [
                    f"Bootstrap sign stability is {stability:.1%}.",
                    "Segment effects disagree, so one global recommendation is underspecified.",
                ],
            ),
            causal=_risk(
                causal_score,
                [
                    "Treatment came from a feature-dependent logged policy, not randomization.",
                    f"Only {self.metrics.overlap_fraction:.1%} of propensities lie in [0.1, 0.9].",
                    f"Maximum covariate SMD is {self.metrics.max_balance_smd:.3f}.",
                ],
            ),
            data=_risk(
                0.54,
                [
                    "Historical sample size does not repair unmeasured confounding.",
                    f"Approximate power for a 2.5 pp RCT effect would be {self.metrics.power:.1%}.",
                ],
            ),
            environment=_risk(
                0.08,
                ["No population shift has been observed in the reference window."],
            ),
        )

    def _analyze_trial(self) -> RiskProfile:
        if self.trial is None:
            raise RuntimeError("No randomized data available")
        self.metrics = self._metrics_from_data(self.trial)
        self.segments = self._segment_views(self.trial, randomized=True)
        stability = bootstrap_sign_stability(self.trial, seed=self.config.seed + self.step_number)
        randomization_penalty = 0.0
        if self.metrics.srm_p_value < 0.01:
            randomization_penalty += 0.45
        randomization_penalty += min(self.metrics.max_balance_smd / 0.25, 1.0) * 0.2
        causal_score = 0.06 + randomization_penalty
        interval_penalty = 0.30 if self.metrics.ci_low <= 0 <= self.metrics.ci_high else 0.0
        data_score = 0.10 + 0.55 * (1.0 - self.metrics.power) + interval_penalty
        environment_score = (
            min(1.0, 0.1 + self.metrics.drift_psi / 0.25)
            if self.drift_population is not None
            else 0.07
        )
        return RiskProfile(
            model=_risk(
                max(0.03, 1.0 - stability),
                [
                    f"Bootstrap effect-sign stability is {stability:.1%}.",
                    "All numerical claims were recomputed by deterministic tools.",
                ],
            ),
            causal=_risk(
                causal_score,
                [
                    "Treatment was randomized with logged propensity 0.5.",
                    f"SRM p-value is {self.metrics.srm_p_value:.3f}.",
                    f"Maximum covariate SMD is {self.metrics.max_balance_smd:.3f}.",
                ],
            ),
            data=_risk(
                data_score,
                [
                    f"Overall 95% CI is [{self.metrics.ci_low:.3f}, {self.metrics.ci_high:.3f}].",
                    f"Approximate power for a 2.5 pp effect is {self.metrics.power:.1%}.",
                ],
            ),
            environment=_risk(
                environment_score,
                [
                    f"Maximum feature PSI is {self.metrics.drift_psi:.3f}."
                    if self.drift_population is not None
                    else "Current population matches the pre-experiment reference window."
                ],
            ),
        )

    def _trace_policy_decision(self):
        evidence = tuple(
            SegmentEvidence(
                segment_id=segment.id,
                uplift=segment.uplift,
                ci_low=segment.ci_low,
                ci_high=segment.ci_high,
                diversity_delta=segment.diversity_delta,
                contribution_margin=SEGMENT_MAP[segment.id].contribution_margin,
                required_subsidy=SEGMENT_MAP[segment.id].required_subsidy,
            )
            for segment in self.segments
        )
        return evaluate_trace_policy(
            TracePolicyInput(
                segments=evidence,
                model_risk=self.risks.model.score,
                causal_risk=self.risks.causal.score,
                data_risk=self.risks.data.score,
                environment_risk=self.risks.environment.score,
                max_diversity_loss=self.config.max_diversity_loss,
                margin_floor=self.human_constraints.get("margin_floor"),
                subsidy_cap=self.human_constraints.get("subsidy_cap"),
                observed_drift_segment=self.drift_segment,
            )
        )

    def _eligible_segments(self) -> list[str]:
        return list(self._trace_policy_decision().eligible_segments)

    def _recommended_action(self) -> ActionType | None:
        return {
            MissionState.DIAGNOSING: ActionType.EXPERIMENT,
            MissionState.EXPERIMENTING: ActionType.ASK_HUMAN,
            MissionState.AWAITING_HUMAN: None,
            MissionState.READY_TO_DEPLOY: self.decision.action,
            MissionState.DEPLOYED: None,
            MissionState.DRIFT_DETECTED: ActionType.ASK_HUMAN,
            MissionState.ROLLED_BACK: ActionType.EXPERIMENT,
            MissionState.ABSTAINED: None,
        }[self.state]

    def snapshot(self) -> EpisodeSnapshot:
        with self._lock:
            return EpisodeSnapshot(
                mission_id=self.mission_id,
                evidence_mode=EvidenceMode.SIMULATED_SCM,
                fixture_version=FIXTURE_VERSION,
                fixture_hash=FIXTURE_HASH,
                config_hash=self.config_hash,
                dataset_version=FIXTURE_VERSION,
                split="runtime_seeded_episode",
                seed=self.config.seed,
                estimator="difference_in_means_wald_95",
                assumptions=[
                    "Seeded synthetic fashion scenario with known simulation truth.",
                    "Runtime metrics use observed logged or randomized outcomes, never oracle effects.",
                    "Risk values are engineering indices, not calibrated probabilities.",
                ],
                state=self.state,
                step=self.step_number,
                goal=self.config.goal,
                budget=self.config.budget,
                budget_used=self.budget_used,
                max_diversity_loss=self.config.max_diversity_loss,
                risks=self.risks,
                metrics=self.metrics,
                segments=self.segments,
                decision=self.decision,
                allowed_actions=list(ALLOWED_ACTIONS[self.state]),
                pending_question=self.pending_question,
                audit=self.audit,
            )

    def audit_snapshot(self) -> tuple[AuditEvent, ...]:
        """Return an immutable catch-up view without racing concurrent appends."""
        with self._lock:
            return tuple(self.audit)

    def execute(
        self, requested: ActionType | None = None, segment_id: str | None = None
    ) -> EpisodeSnapshot:
        with self._lock:
            return self._execute_locked(requested, segment_id)

    def _execute_locked(
        self, requested: ActionType | None, segment_id: str | None
    ) -> EpisodeSnapshot:
        action = requested or self._recommended_action()
        if action is None:
            raise ValueError("This state has no automatic next action")
        if action not in ALLOWED_ACTIONS[self.state]:
            allowed = ", ".join(value.value for value in ALLOWED_ACTIONS[self.state])
            raise ValueError(f"Action '{action.value}' is not allowed from {self.state.value}; allowed: {allowed}")
        if segment_id is not None and action not in {
            ActionType.SEGMENT_DEPLOY,
            ActionType.PAUSE_SEGMENT,
        }:
            raise ValueError(f"segment_id is not valid for action '{action.value}'")
        if action == ActionType.DIAGNOSE:
            self._diagnose()
        elif action == ActionType.EXPERIMENT:
            self._experiment()
        elif action == ActionType.ASK_HUMAN:
            self._ask_human()
        elif action == ActionType.SEGMENT_DEPLOY:
            self._segment_deploy(segment_id)
        elif action == ActionType.DEPLOY_ALL:
            self._deploy_all()
        elif action == ActionType.PAUSE_SEGMENT:
            self._pause_segment(segment_id)
        elif action == ActionType.ROLLBACK:
            self._rollback()
        elif action == ActionType.ABSTAIN:
            self._abstain()
        return self.snapshot()

    def _diagnose(self) -> None:
        """Re-run deterministic diagnostics without silently changing action state."""
        before = self.state
        preserved_statuses = {segment.id: segment.status for segment in self.segments}
        if self.trial is None:
            self.risks = self._analyze_historical()
        else:
            self.risks = self._analyze_trial()
        for index, segment in enumerate(self.segments):
            previous = preserved_statuses.get(segment.id)
            if previous in {SegmentStatus.DEPLOYED, SegmentStatus.PAUSED}:
                self.segments[index] = segment.model_copy(update={"status": previous})
        self._record(
            "diagnostics_recomputed",
            before,
            self.state,
            ActionType.DIAGNOSE,
            {
                "data_source": "randomized_probe" if self.trial is not None else "logged_policy",
                "max_risk": round(
                    max(
                        self.risks.model.score,
                        self.risks.causal.score,
                        self.risks.data.score,
                        self.risks.environment.score,
                    ),
                    6,
                ),
            },
        )

    def _experiment(self) -> None:
        before = self.state
        available = self.config.budget - self.budget_used
        sample_size = min(9_000, available)
        if sample_size < 2_000:
            raise ValueError("Less than 2,000 exposure budget remains; cannot run a powered probe")
        self.trial = generate_rct(self.config.seed + self.budget_used, sample_size)
        self.budget_used += sample_size
        self.state = MissionState.EXPERIMENTING
        self.risks = self._analyze_trial()
        eligible = self._eligible_segments()
        self.decision = DecisionView(
            action=ActionType.ASK_HUMAN,
            rationale=(
                "The randomized probe resolves most causal risk. Before assigning business "
                "traffic, acquire the missing margin constraint from its owner."
            ),
            eligible_segments=eligible,
        )
        self._record(
            "randomized_probe_completed",
            before,
            self.state,
            ActionType.EXPERIMENT,
            {
                "sample_size": sample_size,
                "srm_p_value": round(self.metrics.srm_p_value, 6),
                "uplift": round(self.metrics.uplift, 6),
                "eligible_segments": eligible,
            },
        )

    def _ask_human(self) -> None:
        before = self.state
        if self.drift_segment:
            question = HumanQuestion(
                id="drift_subsidy_cap",
                text="What is the maximum first-order subsidy for the shifted new-arrival cohort?",
                why_it_matters=(
                    "The cohort is outside observed support. A hard subsidy cap determines "
                    "whether safe re-entry is economically possible."
                ),
            )
        else:
            question = HumanQuestion(
                id="margin_floor",
                text="What contribution-margin floor must every deployed segment preserve?",
                why_it_matters=(
                    "Conversion uplift alone cannot authorize deployment without a business loss bound."
                ),
            )
        self.pending_question = question
        self.state = MissionState.AWAITING_HUMAN
        self.decision = DecisionView(
            action=None,
            rationale="Autonomy is paused until the named business constraint is supplied.",
            eligible_segments=self._eligible_segments(),
        )
        self._record(
            "human_constraint_requested",
            before,
            self.state,
            ActionType.ASK_HUMAN,
            {"question_id": question.id, "value_of_information": "high"},
        )

    def answer_human(
        self,
        answer: str,
        margin_floor: float | None = None,
        subsidy_cap: float | None = None,
    ) -> EpisodeSnapshot:
        with self._lock:
            return self._answer_human_locked(answer, margin_floor, subsidy_cap)

    def _answer_human_locked(
        self,
        answer: str,
        margin_floor: float | None,
        subsidy_cap: float | None,
    ) -> EpisodeSnapshot:
        if self.state != MissionState.AWAITING_HUMAN or self.pending_question is None:
            raise ValueError("No human answer is currently expected")
        question_id = self.pending_question.id
        if question_id == "margin_floor" and margin_floor is None:
            raise ValueError("Question 'margin_floor' requires a numeric margin_floor")
        if question_id == "drift_subsidy_cap" and subsidy_cap is None:
            raise ValueError("Question 'drift_subsidy_cap' requires a numeric subsidy_cap")
        before = self.state
        answers = self.human_constraints.setdefault("answers", {})
        answers[question_id] = answer
        if margin_floor is not None:
            self.human_constraints["margin_floor"] = margin_floor
        if subsidy_cap is not None:
            self.human_constraints["subsidy_cap"] = subsidy_cap
        answered_question = question_id
        self.pending_question = None
        eligible = self._eligible_segments()
        if question_id == "drift_subsidy_cap":
            still_deployed = [
                segment.id for segment in self.segments if segment.status == SegmentStatus.DEPLOYED
            ]
            if still_deployed:
                self.state = MissionState.DEPLOYED
                self.decision = DecisionView(
                    action=None,
                    rationale=(
                        "The subsidy cap is recorded. Existing unaffected cohorts remain deployed; "
                        "the observed-shift cohort stays outside the autonomy boundary."
                    ),
                    eligible_segments=still_deployed,
                )
            elif self.trial is not None and eligible:
                self.state = MissionState.READY_TO_DEPLOY
                self.decision = DecisionView(
                    action=ActionType.SEGMENT_DEPLOY,
                    rationale=(
                        "The subsidy cap is recorded. The shifted cohort remains held; deploy only "
                        "the interval-supported cohorts that still satisfy the explicit margin floor."
                    ),
                    eligible_segments=eligible,
                )
            else:
                self.state = MissionState.DRIFT_DETECTED
                self.decision = DecisionView(
                    action=ActionType.ROLLBACK,
                    rationale=(
                        "No action-eligible cohort remains after the support shift. Buy fresh "
                        "randomized evidence before granting deployment rights."
                    ),
                    eligible_segments=[],
                )
        else:
            self.state = MissionState.READY_TO_DEPLOY
            self.decision = DecisionView(
                action=ActionType.SEGMENT_DEPLOY if eligible else ActionType.ABSTAIN,
                rationale=(
                    "The human-owned margin floor is now explicit. Deploy only interval-supported, "
                    "economically eligible segments; retain abstention elsewhere."
                ),
                eligible_segments=eligible,
            )
        self._record(
            "human_constraint_received",
            before,
            self.state,
            details={
                "question_id": answered_question,
                "margin_floor": margin_floor,
                "subsidy_cap": subsidy_cap,
            },
        )
        return self.snapshot()

    def _segment_deploy(self, segment_id: str | None) -> None:
        before = self.state
        eligible = self._eligible_segments()
        if not eligible:
            reasons = self._trace_policy_decision().blocked_reasons
            raise ValueError(f"SEGMENT_DEPLOY hard gate rejected: no eligible segment; {reasons}")
        if segment_id is not None and segment_id not in SEGMENT_MAP:
            raise ValueError(f"Unknown segment '{segment_id}'")
        try:
            selected = select_minimum_scope(self._trace_policy_decision(), segment_id)
        except ValueError as exc:
            raise ValueError(f"SEGMENT_DEPLOY hard gate rejected: {exc}") from exc
        for index, segment in enumerate(self.segments):
            if segment.id == selected:
                self.segments[index] = segment.model_copy(update={"status": SegmentStatus.DEPLOYED})
        deployed_ids = [
            segment.id for segment in self.segments if segment.status == SegmentStatus.DEPLOYED
        ]
        view_map = {segment.id: segment for segment in self.segments}
        selected_value_estimate = sum(
            SEGMENT_MAP[value].share * max(view_map[value].uplift, 0.0)
            for value in deployed_ids
        )
        feasible_estimated_value = sum(
            SEGMENT_MAP[value].share * max(view_map[value].uplift, 0.0)
            for value in eligible
        )
        remaining = max(self.config.budget - self.budget_used, 0)
        self.metrics = self.metrics.model_copy(
            update={
                "expected_incremental_conversions": selected_value_estimate * remaining,
                "policy_regret": max(feasible_estimated_value - selected_value_estimate, 0.0),
            }
        )
        self.state = MissionState.DEPLOYED
        self.decision = DecisionView(
            action=None,
            rationale=(
                "Selective deployment authorized. Unsupported and diversity-violating cohorts remain held."
            ),
            eligible_segments=deployed_ids,
        )
        self._record(
            "selective_policy_deployed",
            before,
            self.state,
            ActionType.SEGMENT_DEPLOY,
            {
                "deployed_segments": deployed_ids,
                "selected_segment": selected,
                "remaining_candidates": [value for value in eligible if value != selected],
            },
        )

    def _deploy_all(self) -> None:
        """Attempt full deployment, guarded by evidence and business constraints."""
        risk_scores = {
            "model": self.risks.model.score,
            "causal": self.risks.causal.score,
            "data": self.risks.data.score,
            "environment": self.risks.environment.score,
        }
        failed: list[str] = [
            f"{name}_risk={score:.3f}>0.200" for name, score in risk_scores.items() if score > 0.2
        ]
        if self.trial is None:
            failed.append("no randomized evidence")
        if self.drift_segment is not None:
            failed.append(f"active drift in {self.drift_segment}")
        trace_decision = self._trace_policy_decision()
        for segment in self.segments:
            if segment.ci_low <= 0:
                failed.append(f"{segment.id} lower CI={segment.ci_low:.3f}<=0")
            if segment.diversity_delta < -self.config.max_diversity_loss:
                failed.append(
                    f"{segment.id} diversity loss={-segment.diversity_delta:.3f} exceeds "
                    f"{self.config.max_diversity_loss:.3f}"
                )
            for reason in trace_decision.blocked_reasons.get(segment.id, ()):
                failed.append(f"{segment.id} {reason}")
        if failed:
            raise ValueError("DEPLOY_ALL hard gate rejected: " + "; ".join(failed))
        before = self.state
        for index, segment in enumerate(self.segments):
            self.segments[index] = segment.model_copy(update={"status": SegmentStatus.DEPLOYED})
        estimated_value = sum(
            SEGMENT_MAP[segment.id].share * max(segment.uplift, 0.0)
            for segment in self.segments
        )
        remaining = max(self.config.budget - self.budget_used, 0)
        self.metrics = self.metrics.model_copy(
            update={
                "expected_incremental_conversions": estimated_value * remaining,
                "policy_regret": 0.0,
            }
        )
        self.state = MissionState.DEPLOYED
        self.decision = DecisionView(
            action=None,
            rationale="All cohorts passed the causal, data, environment, model, and diversity gates.",
            eligible_segments=[segment.id for segment in self.segments],
        )
        self._record(
            "full_policy_deployed",
            before,
            self.state,
            ActionType.DEPLOY_ALL,
            {"deployed_segments": [segment.id for segment in self.segments]},
        )

    def _pause_segment(self, segment_id: str | None) -> None:
        if not segment_id:
            raise ValueError("PAUSE_SEGMENT requires segment_id")
        if segment_id not in SEGMENT_MAP:
            raise ValueError(f"Unknown segment '{segment_id}'")
        target_index = next(
            (index for index, segment in enumerate(self.segments) if segment.id == segment_id), None
        )
        if target_index is None or self.segments[target_index].status != SegmentStatus.DEPLOYED:
            raise ValueError(
                f"PAUSE_SEGMENT hard gate rejected: '{segment_id}' is not currently deployed"
            )
        before = self.state
        self.segments[target_index] = self.segments[target_index].model_copy(
            update={"status": SegmentStatus.PAUSED}
        )
        self._refresh_policy_summary()
        self.decision = DecisionView(
            action=None if self.state == MissionState.DEPLOYED else ActionType.ASK_HUMAN,
            rationale=f"Traffic to {segment_id} is paused while evidence is reviewed.",
            eligible_segments=[
                segment.id for segment in self.segments if segment.status == SegmentStatus.DEPLOYED
            ],
        )
        self._record(
            "segment_paused",
            before,
            self.state,
            ActionType.PAUSE_SEGMENT,
            {"segment_id": segment_id},
        )

    def inject_drift(self, severity: float, segment_id: str) -> EpisodeSnapshot:
        with self._lock:
            return self._inject_drift_locked(severity, segment_id)

    def _inject_drift_locked(self, severity: float, segment_id: str) -> EpisodeSnapshot:
        if segment_id not in SEGMENT_MAP:
            raise ValueError(f"Unknown segment '{segment_id}'")
        if self.state not in {
            MissionState.EXPERIMENTING,
            MissionState.READY_TO_DEPLOY,
            MissionState.DEPLOYED,
        }:
            raise ValueError(
                "Drift can be injected only after a randomized probe or while a policy is deployed"
            )
        before = self.state
        self.drift_segment = segment_id
        self.drift_severity = severity
        self.drift_population = generate_drift_population(
            self.config.seed, severity, segment_id=segment_id
        )
        drift = multivariate_drift(self.reference_population, self.drift_population, FEATURES)
        self.metrics = self.metrics.model_copy(update={"drift_psi": float(drift["max_psi"])})
        environment_score = min(1.0, 0.1 + float(drift["max_psi"]) / 0.25)
        target_was_deployed = any(
            segment.id == segment_id and segment.status == SegmentStatus.DEPLOYED
            for segment in self.segments
        )
        traffic_evidence = (
            f"The deployed {segment_id} cohort was automatically paused."
            if target_was_deployed
            else f"The {segment_id} cohort was not deployed; no traffic was falsely marked paused."
        )
        self.risks = self.risks.model_copy(
            update={
                "environment": _risk(
                    environment_score,
                    [
                        f"Maximum feature PSI rose to {float(drift['max_psi']):.3f}.",
                        traffic_evidence,
                    ],
                )
            }
        )
        for index, segment in enumerate(self.segments):
            if segment.id == segment_id:
                new_status = (
                    SegmentStatus.PAUSED if target_was_deployed else SegmentStatus.HELD
                )
                self.segments[index] = segment.model_copy(
                    update={"status": new_status, "risk": environment_score}
                )
        self._refresh_policy_summary()
        self.state = MissionState.DRIFT_DETECTED
        self.pending_question = None
        self.decision = DecisionView(
            action=ActionType.ASK_HUMAN,
            rationale=(
                "Population support changed. The affected cohort is held outside the action "
                "boundary; ask for its economic cap before any future re-entry."
            ),
            eligible_segments=self._eligible_segments(),
        )
        self._record(
            "population_drift_injected",
            before,
            self.state,
            details={
                "segment_id": segment_id,
                "target_was_deployed": target_was_deployed,
                "traffic_action": "paused" if target_was_deployed else "none_not_deployed",
                "severity": severity,
                "max_psi": round(float(drift["max_psi"]), 6),
                "per_feature_psi": {key: round(float(value), 6) for key, value in drift["psi"].items()},
            },
        )
        return self.snapshot()

    def _rollback(self) -> None:
        before = self.state
        rolled_back: list[str] = []
        for index, segment in enumerate(self.segments):
            if segment.status in {SegmentStatus.DEPLOYED, SegmentStatus.PAUSED}:
                rolled_back.append(segment.id)
                self.segments[index] = segment.model_copy(update={"status": SegmentStatus.HELD})
        if not rolled_back:
            raise ValueError("ROLLBACK hard gate rejected: no deployed or previously paused segment")
        self._refresh_policy_summary()
        self.state = MissionState.ROLLED_BACK
        self.decision = DecisionView(
            action=None,
            rationale=(
                "Traffic is rolled back and this mission is terminal. Reset to create a linked "
                "mission before buying fresh randomized evidence."
            ),
            eligible_segments=[],
        )
        self._record(
            "policy_rolled_back",
            before,
            self.state,
            ActionType.ROLLBACK,
            {"segments": rolled_back},
        )

    def _abstain(self) -> None:
        before = self.state
        if any(
            segment.status in {SegmentStatus.DEPLOYED, SegmentStatus.PAUSED}
            for segment in self.segments
        ):
            raise ValueError("ABSTAIN hard gate rejected: pause or roll back deployed traffic first")
        for index, segment in enumerate(self.segments):
            if segment.status != SegmentStatus.HARMFUL:
                self.segments[index] = segment.model_copy(update={"status": SegmentStatus.HELD})
        self._refresh_policy_summary()
        self.state = MissionState.ABSTAINED
        self.pending_question = None
        self.decision = DecisionView(
            action=None,
            rationale="Evidence or constraints are insufficient; no deployment is safer than a forced answer.",
            eligible_segments=[],
        )
        self._record("deployment_abstained", before, self.state, ActionType.ABSTAIN)
