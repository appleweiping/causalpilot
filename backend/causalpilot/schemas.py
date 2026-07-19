"""Public API schemas. These models are also the source of the OpenAPI contract."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MissionState(str, Enum):
    DIAGNOSING = "diagnosing"
    EXPERIMENTING = "experimenting"
    AWAITING_HUMAN = "awaiting_human"
    READY_TO_DEPLOY = "ready_to_deploy"
    DEPLOYED = "deployed"
    DRIFT_DETECTED = "drift_detected"
    ROLLED_BACK = "rolled_back"
    ABSTAINED = "abstained"


class ActionType(str, Enum):
    DIAGNOSE = "diagnose"
    EXPERIMENT = "experiment"
    ASK_HUMAN = "ask_human"
    SEGMENT_DEPLOY = "segment_deploy"
    DEPLOY_ALL = "deploy_all"
    PAUSE_SEGMENT = "pause_segment"
    ROLLBACK = "rollback"
    ABSTAIN = "abstain"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceMode(str, Enum):
    SIMULATED_SCM = "simulated_scm"


class SegmentStatus(str, Enum):
    OBSERVE = "observe"
    CANDIDATE = "candidate"
    DEPLOYED = "deployed"
    HELD = "held"
    PAUSED = "paused"
    HARMFUL = "harmful"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartMissionRequest(StrictModel):
    goal: str = Field(
        default=(
            "Increase fashion recommendation conversion without reducing content "
            "diversity by more than 2%."
        ),
        min_length=8,
        max_length=500,
    )
    budget: int = Field(default=30_000, ge=2_000, le=1_000_000)
    max_diversity_loss: float = Field(default=0.02, ge=0.0, le=0.25)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class StepMissionRequest(StrictModel):
    mission_id: str = Field(min_length=8, max_length=80)
    requested_action: ActionType | None = None
    segment_id: str | None = Field(default=None, min_length=2, max_length=80)


class InjectDriftRequest(StrictModel):
    mission_id: str = Field(min_length=8, max_length=80)
    severity: float = Field(default=0.55, ge=0.05, le=1.0)
    segment_id: str = Field(default="new_arrivals", min_length=2, max_length=80)


class HumanAnswerRequest(StrictModel):
    mission_id: str = Field(min_length=8, max_length=80)
    answer: str = Field(min_length=1, max_length=500)
    margin_floor: float | None = Field(default=None, ge=0.0, le=1.0)
    subsidy_cap: float | None = Field(default=None, ge=0.0, le=10_000.0)


class ResetMissionRequest(StrictModel):
    mission_id: str = Field(min_length=8, max_length=80)


class RiskScore(StrictModel):
    score: float = Field(ge=0.0, le=1.0)
    level: RiskLevel
    evidence: list[str]


class RiskProfile(StrictModel):
    model: RiskScore
    causal: RiskScore
    data: RiskScore
    environment: RiskScore


class MetricSnapshot(StrictModel):
    metric_basis: str = Field(
        default="randomized_or_logged_estimates; no hidden potential-outcome truth",
        description="Estimation basis for non-_gt runtime metrics.",
    )
    exposures: int = 0
    treatment_n: int = 0
    control_n: int = 0
    treatment_rate: float = 0.0
    control_rate: float = 0.0
    uplift: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    p_value: float = 1.0
    srm_p_value: float = 1.0
    max_balance_smd: float = 0.0
    overlap_fraction: float = 0.0
    power: float = 0.0
    drift_psi: float = 0.0
    expected_incremental_conversions: float = Field(
        default=0.0,
        description="Estimate from randomized segment uplift; never hidden potential-outcome truth.",
    )
    policy_regret: float = Field(
        default=0.0,
        description="Estimated regret versus the evidence-feasible policy, not oracle regret.",
    )


class SegmentView(StrictModel):
    id: str
    label: str
    share: float = Field(ge=0.0, le=1.0)
    status: SegmentStatus
    uplift: float
    ci_low: float
    ci_high: float
    risk: float = Field(ge=0.0, le=1.0)
    diversity_delta: float
    coordinates: tuple[float, float, float]


class DecisionView(StrictModel):
    action: ActionType | None
    rationale: str
    eligible_segments: list[str] = Field(default_factory=list)


class HumanQuestion(StrictModel):
    id: str
    text: str
    why_it_matters: str


class AuditEvent(StrictModel):
    sequence: int
    timestamp: str
    event: str
    action: ActionType | None = None
    state_before: MissionState
    state_after: MissionState
    details: dict[str, Any] = Field(default_factory=dict)


class EpisodeSnapshot(StrictModel):
    mission_id: str
    evidence_mode: EvidenceMode
    fixture_version: str
    fixture_hash: str
    config_hash: str
    dataset_version: str
    split: str
    seed: int
    estimator: str
    assumptions: list[str]
    state: MissionState
    step: int
    goal: str
    budget: int
    budget_used: int
    max_diversity_loss: float
    risks: RiskProfile
    metrics: MetricSnapshot
    segments: list[SegmentView]
    decision: DecisionView
    allowed_actions: list[ActionType]
    pending_question: HumanQuestion | None
    audit: list[AuditEvent]


class HealthResponse(StrictModel):
    status: str
    service: str
    version: str
    deterministic_mode: bool


class ErrorResponse(StrictModel):
    detail: str
