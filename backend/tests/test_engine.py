from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from causalpilot.engine import ALLOWED_ACTIONS, MissionRuntime
from causalpilot.schemas import ActionType, MissionState, StartMissionRequest


def make_mission(seed: int = 42) -> MissionRuntime:
    return MissionRuntime(StartMissionRequest(seed=seed))


def test_trace_happy_path_and_audit_chain():
    mission = make_mission()
    started = mission.snapshot()
    assert started.state == MissionState.DIAGNOSING
    assert started.evidence_mode.value == "simulated_scm"
    assert started.fixture_version == "causalpilot-synthetic-fashion-v1"
    assert len(started.fixture_hash) == 16
    assert len(started.config_hash) == 16
    assert started.metrics.metric_basis.startswith("randomized_or_logged_estimates")
    assert started.audit[0].details["fixture_hash"] == started.fixture_hash
    assert started.risks.causal.level.value == "high"
    assert started.decision.action == ActionType.EXPERIMENT

    experimented = mission.execute()
    assert experimented.state == MissionState.EXPERIMENTING
    assert experimented.budget_used == 9_000
    assert experimented.metrics.srm_p_value == pytest.approx(1.0)
    assert experimented.risks.causal.score < started.risks.causal.score

    waiting = mission.execute()
    assert waiting.state == MissionState.AWAITING_HUMAN
    assert waiting.pending_question.id == "margin_floor"

    ready = mission.answer_human("Preserve at least 15% margin", margin_floor=0.15)
    assert ready.state == MissionState.READY_TO_DEPLOY
    deployed = mission.execute()
    assert deployed.state == MissionState.DEPLOYED
    assert sum(segment.status.value == "deployed" for segment in deployed.segments) == 1
    assert all(event.sequence == index for index, event in enumerate(deployed.audit))


def test_drift_holds_undeployed_cohort_and_binds_subsidy_answer():
    mission = make_mission()
    mission.execute()
    mission.execute()
    mission.answer_human("15%", margin_floor=0.15)
    mission.execute()
    drifted = mission.inject_drift(0.8, "new_arrivals")
    assert drifted.state == MissionState.DRIFT_DETECTED
    assert drifted.risks.environment.level.value == "high"
    assert drifted.metrics.drift_psi > 0.1
    target = next(segment for segment in drifted.segments if segment.id == "new_arrivals")
    assert target.status.value == "held"
    assert drifted.audit[-1].details["target_was_deployed"] is False
    assert drifted.audit[-1].details["traffic_action"] == "none_not_deployed"
    waiting = mission.execute()
    assert waiting.pending_question.id == "drift_subsidy_cap"
    with pytest.raises(ValueError, match="requires a numeric subsidy_cap"):
        mission.answer_human("whatever")
    answered = mission.answer_human("At most eight", subsidy_cap=8.0)
    assert answered.state == MissionState.DEPLOYED


def test_post_probe_drift_can_recover_to_selective_deployment():
    mission = make_mission()
    mission.execute(ActionType.EXPERIMENT)
    drifted = mission.inject_drift(0.8, "new_arrivals")
    assert drifted.state == MissionState.DRIFT_DETECTED
    target = next(segment for segment in drifted.segments if segment.id == "new_arrivals")
    assert target.status.value == "held"

    waiting = mission.execute(ActionType.ASK_HUMAN)
    assert waiting.pending_question.id == "drift_subsidy_cap"
    ready = mission.answer_human(
        "Preserve 15% margin; cap the shifted-cohort subsidy at eight.",
        margin_floor=0.15,
        subsidy_cap=8.0,
    )
    assert ready.state == MissionState.READY_TO_DEPLOY
    assert ready.decision.action == ActionType.SEGMENT_DEPLOY

    deployed = mission.execute(ActionType.SEGMENT_DEPLOY)
    assert deployed.state == MissionState.DEPLOYED
    assert all(segment.id != "new_arrivals" for segment in deployed.segments if segment.status.value == "deployed")


def test_invalid_transition_is_rejected():
    mission = make_mission()
    with pytest.raises(ValueError, match="not allowed"):
        mission.execute(ActionType.SEGMENT_DEPLOY)


def test_diagnose_is_audited_without_changing_state():
    mission = make_mission()
    snapshot = mission.execute(ActionType.DIAGNOSE)
    assert snapshot.state == MissionState.DIAGNOSING
    assert snapshot.audit[-1].action == ActionType.DIAGNOSE
    assert snapshot.audit[-1].event == "diagnostics_recomputed"


def test_deploy_all_hard_gate_rejects_unsafe_cohort():
    mission = make_mission()
    mission.execute(ActionType.EXPERIMENT)
    mission.execute(ActionType.ASK_HUMAN)
    mission.answer_human("15%", margin_floor=0.15)
    with pytest.raises(ValueError, match="DEPLOY_ALL hard gate rejected"):
        mission.execute(ActionType.DEPLOY_ALL)


def test_pause_segment_requires_a_currently_deployed_target():
    mission = make_mission()
    mission.execute()
    mission.execute()
    mission.answer_human("15%", margin_floor=0.15)
    deployed = mission.execute()
    target = next(segment.id for segment in deployed.segments if segment.status.value == "deployed")
    paused = mission.execute(ActionType.PAUSE_SEGMENT, segment_id=target)
    assert paused.state == MissionState.DEPLOYED
    assert next(segment for segment in paused.segments if segment.id == target).status.value == "paused"
    with pytest.raises(ValueError, match="not currently deployed"):
        mission.execute(ActionType.PAUSE_SEGMENT, segment_id=target)


def test_human_answer_is_question_bound_and_margin_changes_eligibility():
    mission = make_mission()
    mission.execute()
    mission.execute()
    with pytest.raises(ValueError, match="requires a numeric margin_floor"):
        mission.answer_human("sounds good")
    ready = mission.answer_human("Require 20%", margin_floor=0.20)
    assert ready.decision.eligible_segments == ["loyalists"]
    with pytest.raises(ValueError, match="did not pass TRACE gates"):
        mission.execute(ActionType.SEGMENT_DEPLOY, segment_id="trend_seekers")
    deployed = mission.execute(ActionType.SEGMENT_DEPLOY, segment_id="loyalists")
    assert [s.id for s in deployed.segments if s.status.value == "deployed"] == ["loyalists"]


def test_deployed_state_requires_pause_or_rollback_and_abstained_is_terminal():
    mission = make_mission()
    mission.execute()
    mission.execute()
    mission.answer_human("15%", margin_floor=0.15)
    mission.execute()
    with pytest.raises(ValueError, match="not allowed"):
        mission.execute(ActionType.EXPERIMENT)
    with pytest.raises(ValueError, match="not allowed"):
        mission.execute(ActionType.ABSTAIN)

    terminal = make_mission(seed=9)
    stopped = terminal.execute(ActionType.ABSTAIN)
    assert stopped.state == MissionState.ABSTAINED
    assert stopped.allowed_actions == []
    with pytest.raises(ValueError, match="not allowed"):
        terminal.execute(ActionType.DIAGNOSE)


def test_rollback_rejects_when_no_deployment_exists():
    mission = make_mission()
    mission.execute(ActionType.ASK_HUMAN)
    with pytest.raises(ValueError, match="no deployed"):
        mission.execute(ActionType.ROLLBACK)


def test_pause_and_rollback_refresh_policy_metrics_and_rollback_is_terminal():
    mission = make_mission()
    mission.execute()
    mission.execute()
    mission.answer_human("15%", margin_floor=0.15)
    deployed = mission.execute()
    deployed_id = next(s.id for s in deployed.segments if s.status.value == "deployed")
    assert deployed.metrics.expected_incremental_conversions > 0
    paused = mission.execute(ActionType.PAUSE_SEGMENT, segment_id=deployed_id)
    assert paused.metrics.expected_incremental_conversions == 0
    rolled_back = mission.execute(ActionType.ROLLBACK)
    assert rolled_back.state == MissionState.ROLLED_BACK
    assert rolled_back.allowed_actions == []
    assert rolled_back.metrics.expected_incremental_conversions == 0
    with pytest.raises(ValueError, match="not allowed"):
        mission.execute(ActionType.EXPERIMENT)
    assert tuple(rolled_back.audit) == mission.audit_snapshot()


def test_concurrent_experiment_requests_cannot_double_spend_budget():
    mission = make_mission(seed=17)
    workers = 6
    barrier = Barrier(workers)

    def attempt() -> str:
        barrier.wait()
        try:
            return mission.execute(ActionType.EXPERIMENT).state.value
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: attempt(), range(workers)))
    snapshot = mission.snapshot()
    assert results.count("experimenting") == 1
    assert results.count("rejected") == workers - 1
    assert snapshot.budget_used == 9_000
    assert sum(event.action == ActionType.EXPERIMENT for event in snapshot.audit) == 1


def test_every_state_has_explicit_action_authorization():
    assert set(ALLOWED_ACTIONS) == set(MissionState)
    assert ALLOWED_ACTIONS[MissionState.ABSTAINED] == ()
    assert ALLOWED_ACTIONS[MissionState.ROLLED_BACK] == ()
    assert set(ActionType) == {
        ActionType.DIAGNOSE,
        ActionType.EXPERIMENT,
        ActionType.ASK_HUMAN,
        ActionType.SEGMENT_DEPLOY,
        ActionType.DEPLOY_ALL,
        ActionType.PAUSE_SEGMENT,
        ActionType.ROLLBACK,
        ActionType.ABSTAIN,
    }
