export type RiskLevel = "low" | "guarded" | "elevated" | "critical";
export type EvidenceMode = "simulated_scm" | "public_rct_offline" | "logged_bandit_ope" | string;

export type MissionState =
  | "READY"
  | "DIAGNOSING"
  | "PROBING"
  | "DRIFT_DETECTED"
  | "AWAITING_HUMAN"
  | "DEPLOYED"
  | "ABSTAINED"
  | string;

export interface RiskSignal {
  score: number;
  level: RiskLevel;
  evidence: string[];
}

export interface TraceRisks {
  model: RiskSignal;
  causal: RiskSignal;
  data: RiskSignal;
  environment: RiskSignal;
}

export interface MissionMetrics {
  exposures: number;
  treatment_n: number;
  control_n: number;
  treatment_rate: number;
  control_rate: number;
  uplift: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
  srm_p_value: number;
  max_balance_smd: number;
  overlap_fraction: number;
  power: number;
  drift_psi: number;
  expected_incremental_conversions: number;
  policy_regret: number;
}

export type SegmentStatus = "eligible" | "probe" | "paused" | "abstain" | string;

export interface MissionSegment {
  id: string;
  label: string;
  share: number;
  status: SegmentStatus;
  uplift: number;
  ci_low: number;
  ci_high: number;
  risk: number;
  diversity_delta: number;
  coordinates: [number, number, number];
}

export interface MissionDecision {
  action: string;
  rationale: string;
  eligible_segments: string[];
}

export interface AuditEntry {
  id: string;
  step: number;
  timestamp: string;
  actor: "agent" | "tool" | "human" | string;
  action: string;
  detail: string;
  status: "complete" | "active" | "blocked" | string;
}

export interface EpisodeSnapshot {
  mission_id: string;
  evidence_mode: EvidenceMode;
  fixture_version: string;
  fixture_hash: string;
  config_hash: string;
  dataset_version: string;
  split: string;
  seed: number;
  estimator: string;
  assumptions: string[];
  state: MissionState;
  step: number;
  goal: string;
  budget: number;
  budget_used: number;
  max_diversity_loss: number;
  risks: TraceRisks;
  metrics: MissionMetrics;
  segments: MissionSegment[];
  decision: MissionDecision;
  allowed_actions: string[];
  pending_question: string | null;
  audit: AuditEntry[];
}

export type DataSource = "api" | "simulation";

export interface ClientResult {
  snapshot: EpisodeSnapshot;
  source: DataSource;
  latencyMs: number;
  warning?: string;
}
