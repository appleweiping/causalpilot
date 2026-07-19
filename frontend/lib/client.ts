import { createMockSnapshot } from "./mock";
import type {
  AuditEntry,
  ClientResult,
  EpisodeSnapshot,
  MissionMetrics,
  MissionSegment,
  RiskLevel,
  RiskSignal,
} from "./types";

const API_BASE_SETTING = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const FORCE_OFFLINE = API_BASE_SETTING.trim().toLowerCase() === "offline";
const API_BASE = (FORCE_OFFLINE ? "" : API_BASE_SETTING).replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = 2200;

type UnknownRecord = Record<string, unknown>;

export interface StartMissionInput {
  goal?: string;
  budget?: number;
  max_diversity_loss?: number;
  seed?: number;
}

export interface HumanAnswerInput {
  answer: string;
  margin_floor?: number;
  subsidy_cap?: number;
}

function record(value: unknown): UnknownRecord {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as UnknownRecord)
    : {};
}

function finite(value: unknown, fallback: number): number {
  const parsed = typeof value === "string" ? Number(value) : value;
  return typeof parsed === "number" && Number.isFinite(parsed) ? parsed : fallback;
}

function text(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function stringArray(value: unknown, fallback: string[] = []): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : fallback;
}

function riskLevel(value: unknown, score: number): RiskLevel {
  if (value === "low" || value === "guarded" || value === "elevated" || value === "critical") return value;
  if (score >= 0.75) return "critical";
  if (score >= 0.5) return "elevated";
  if (score >= 0.25) return "guarded";
  return "low";
}

function normalizeRisk(value: unknown, fallback: RiskSignal): RiskSignal {
  if (typeof value === "number") {
    return { score: value, level: riskLevel(undefined, value), evidence: fallback.evidence };
  }
  const source = record(value);
  const score = finite(source.score, fallback.score);
  return {
    score,
    level: riskLevel(source.level, score),
    evidence: stringArray(source.evidence, fallback.evidence),
  };
}

function normalizeCoordinates(value: unknown, fallback: [number, number, number]): [number, number, number] {
  if (Array.isArray(value) && value.length >= 2) {
    return [finite(value[0], fallback[0]), finite(value[1], fallback[1]), finite(value[2], fallback[2])];
  }
  const source = record(value);
  return [finite(source.x, fallback[0]), finite(source.y, fallback[1]), finite(source.z, fallback[2])];
}

function normalizeSegment(value: unknown, fallback: MissionSegment, index: number): MissionSegment {
  const source = record(value);
  return {
    id: text(source.id, fallback.id || `segment-${index}`),
    label: text(source.label, fallback.label),
    share: finite(source.share, fallback.share),
    status: text(source.status, fallback.status),
    uplift: finite(source.uplift, fallback.uplift),
    ci_low: finite(source.ci_low, fallback.ci_low),
    ci_high: finite(source.ci_high, fallback.ci_high),
    risk: finite(source.risk, fallback.risk),
    diversity_delta: finite(source.diversity_delta, fallback.diversity_delta),
    coordinates: normalizeCoordinates(source.coordinates, fallback.coordinates),
  };
}

function normalizeAudit(value: unknown, fallback: AuditEntry, index: number): AuditEntry {
  const source = record(value);
  const sequence = finite(source.sequence ?? source.step, fallback.step);
  const event = text(source.event, fallback.action);
  const details = record(source.details);
  const detailParts = [
    source.state_before && source.state_after
      ? `${String(source.state_before)} → ${String(source.state_after)}`
      : "",
    ...Object.entries(details)
      .slice(0, 3)
      .map(([key, item]) => `${key}: ${typeof item === "object" ? JSON.stringify(item) : String(item)}`),
  ].filter(Boolean);
  const actor = event.includes("human")
    ? "human"
    : /probe|drift|diagnostic|evidence/.test(event)
      ? "tool"
      : "agent";
  return {
    id: text(source.id, `audit-${sequence || index}`),
    step: sequence,
    timestamp: text(source.timestamp, fallback.timestamp),
    actor: text(source.actor, actor),
    action: text(source.action, event),
    detail: text(source.detail ?? source.rationale ?? source.message, detailParts.join(" · ") || fallback.detail),
    status: text(source.status, "complete"),
  };
}

function normalizeMetrics(value: unknown, fallback: MissionMetrics): MissionMetrics {
  const source = record(value);
  return Object.fromEntries(
    Object.entries(fallback).map(([key, fallbackValue]) => [key, finite(source[key], fallbackValue)]),
  ) as unknown as MissionMetrics;
}

function unwrapPayload(input: unknown): UnknownRecord {
  const root = record(input);
  const candidate = root.snapshot ?? root.data ?? root.episode ?? input;
  return record(candidate);
}

/** Converts direct, enveloped, and partially missing backend responses into one stable UI contract. */
export function normalizeEpisodeSnapshot(
  input: unknown,
  fallbackPhase = 0,
  fallbackMissionId?: string,
): EpisodeSnapshot {
  const fallback = createMockSnapshot(fallbackPhase, fallbackMissionId);
  const source = unwrapPayload(input);
  const risks = record(source.risks);
  const decision = record(source.decision);
  const rawSegments = Array.isArray(source.segments) ? source.segments : [];
  const rawAudit = Array.isArray(source.audit) ? source.audit : [];

  const segments = rawSegments.length
    ? rawSegments.map((item, index) => normalizeSegment(item, fallback.segments[index % fallback.segments.length], index))
    : fallback.segments;

  const audit = rawAudit.length
    ? rawAudit.map((item, index) => normalizeAudit(item, fallback.audit[index % fallback.audit.length], index))
    : fallback.audit;

  return {
    mission_id: text(source.mission_id, fallback.mission_id),
    evidence_mode: text(source.evidence_mode, fallback.evidence_mode),
    fixture_version: text(source.fixture_version, fallback.fixture_version),
    fixture_hash: text(source.fixture_hash, fallback.fixture_hash),
    config_hash: text(source.config_hash, fallback.config_hash),
    dataset_version: text(source.dataset_version, fallback.dataset_version),
    split: text(source.split, fallback.split),
    seed: finite(source.seed, fallback.seed),
    estimator: text(source.estimator, fallback.estimator),
    assumptions: stringArray(source.assumptions, fallback.assumptions),
    state: text(source.state, fallback.state),
    step: finite(source.step, fallback.step),
    goal: text(source.goal, fallback.goal),
    budget: finite(source.budget, fallback.budget),
    budget_used: finite(source.budget_used, fallback.budget_used),
    max_diversity_loss: finite(source.max_diversity_loss, fallback.max_diversity_loss),
    risks: {
      model: normalizeRisk(risks.model, fallback.risks.model),
      causal: normalizeRisk(risks.causal, fallback.risks.causal),
      data: normalizeRisk(risks.data, fallback.risks.data),
      environment: normalizeRisk(risks.environment, fallback.risks.environment),
    },
    metrics: normalizeMetrics(source.metrics, fallback.metrics),
    segments,
    decision: {
      action: text(decision.action, fallback.decision.action),
      rationale: text(decision.rationale, fallback.decision.rationale),
      eligible_segments: stringArray(decision.eligible_segments, fallback.decision.eligible_segments),
    },
    allowed_actions: stringArray(source.allowed_actions, fallback.allowed_actions),
    pending_question: source.pending_question === null
      ? null
      : text(record(source.pending_question).text ?? source.pending_question, fallback.pending_question ?? "") || null,
    audit,
  };
}

async function request(
  path: string,
  init: RequestInit,
  fallbackPhase: number,
  fallbackMissionId?: string,
): Promise<ClientResult> {
  const startedAt = performance.now();
  if (FORCE_OFFLINE) {
    return {
      snapshot: createMockSnapshot(fallbackPhase, fallbackMissionId),
      source: "simulation",
      latencyMs: 0,
      warning: "Static demo mode is active. Seeded evidence simulation is running locally.",
    };
  }
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init.headers },
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`API ${response.status}: ${response.statusText}`);
    const payload = (await response.json()) as unknown;
    return {
      snapshot: normalizeEpisodeSnapshot(payload, fallbackPhase, fallbackMissionId),
      source: "api",
      latencyMs: Math.max(1, Math.round(performance.now() - startedAt)),
    };
  } catch (error) {
    const reason = error instanceof Error ? error.message : "API unavailable";
    return {
      snapshot: createMockSnapshot(fallbackPhase, fallbackMissionId),
      source: "simulation",
      latencyMs: Math.max(1, Math.round(performance.now() - startedAt)),
      warning: `${reason}. Seeded evidence simulation is active.`,
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

function jsonPost(body: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body) };
}

export function startMission(input: StartMissionInput = {}): Promise<ClientResult> {
  return request(
    "/api/v1/mission/start",
    jsonPost({
      goal: input.goal ?? "Increase fashion recommendation conversion without sacrificing discovery",
      budget: input.budget ?? 30000,
      max_diversity_loss: input.max_diversity_loss ?? 0.02,
      seed: input.seed ?? 42,
    }),
    0,
  );
}

export function stepMission(
  missionId: string,
  fallbackPhase: number,
  requestedAction?: string,
): Promise<ClientResult> {
  return request(
    "/api/v1/mission/step",
    jsonPost({ mission_id: missionId, ...(requestedAction ? { requested_action: requestedAction } : {}) }),
    fallbackPhase,
    missionId,
  );
}

export function injectMissionDrift(missionId: string, fallbackPhase = 3): Promise<ClientResult> {
  return request(
    "/api/v1/mission/drift",
    jsonPost({ mission_id: missionId, severity: 0.82, segment_id: "new_arrivals" }),
    fallbackPhase,
    missionId,
  );
}

export function submitHumanAnswer(
  missionId: string,
  input: HumanAnswerInput,
  fallbackPhase = 5,
): Promise<ClientResult> {
  return request(
    "/api/v1/mission/human-answer",
    jsonPost({ mission_id: missionId, ...input }),
    fallbackPhase,
    missionId,
  );
}

export function resetMission(missionId: string): Promise<ClientResult> {
  return request(
    "/api/v1/mission/reset",
    jsonPost({ mission_id: missionId }),
    0,
    missionId,
  );
}

export function getMission(missionId: string, fallbackPhase = 0): Promise<ClientResult> {
  return request(`/api/v1/mission/${encodeURIComponent(missionId)}`, { method: "GET" }, fallbackPhase, missionId);
}

export function subscribeToMissionEvents(
  missionId: string,
  onSnapshot: (snapshot: EpisodeSnapshot) => void,
  onError?: () => void,
): () => void {
  if (FORCE_OFFLINE || typeof EventSource === "undefined") return () => undefined;
  const stream = new EventSource(`${API_BASE}/api/v1/mission/${encodeURIComponent(missionId)}/events`);
  stream.onmessage = (event) => {
    try {
      onSnapshot(normalizeEpisodeSnapshot(JSON.parse(event.data), 0, missionId));
    } catch {
      onError?.();
    }
  };
  stream.onerror = () => onError?.();
  return () => stream.close();
}
