"use client";

import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Check,
  ChevronRight,
  CircleGauge,
  DatabaseZap,
  Fingerprint,
  FlaskConical,
  Gauge,
  GitBranch,
  Hand,
  Network,
  Play,
  Radio,
  RefreshCcw,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  Sparkles,
  UserRoundCheck,
} from "lucide-react";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNarrative } from "@/hooks/use-narrative";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import {
  injectMissionDrift,
  resetMission,
  startMission,
  stepMission,
  submitHumanAnswer,
} from "@/lib/client";
import { createMockSnapshot } from "@/lib/mock";
import { STORY_DURATION_SECONDS, STORY_PHASES } from "@/lib/story";
import type { ClientResult, DataSource, EpisodeSnapshot, RiskSignal } from "@/lib/types";

const MarketScene = dynamic(
  () => import("./market-scene").then((module) => module.MarketScene),
  {
    ssr: false,
    loading: () => (
      <div className="market-scene market-scene--loading" role="status" aria-label="Initializing interactive market topology">
        <span>INITIALIZING CAUSAL TOPOLOGY</span>
      </div>
    ),
  },
);

const RISK_META = [
  { key: "model", label: "Model", code: "M", icon: BrainCircuit },
  { key: "causal", label: "Causal", code: "C", icon: GitBranch },
  { key: "data", label: "Data", code: "D", icon: DatabaseZap },
  { key: "environment", label: "Environment", code: "E", icon: Activity },
] as const;

const METRIC_META = [
  { key: "expected_incremental_conversions", label: "Expected lift", suffix: " conv.", format: "integer" },
  { key: "uplift", label: "Causal uplift", suffix: "", format: "percent" },
  { key: "policy_regret", label: "Policy regret", suffix: "", format: "decimal" },
  { key: "power", label: "Evidence power", suffix: "", format: "percent" },
] as const;

function formatCompact(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function formatMetric(value: number, format: string, suffix: string): string {
  if (format === "percent") return `${(value * 100).toFixed(1)}%`;
  if (format === "integer") return `${Math.round(value)}${suffix}`;
  return value.toFixed(3);
}

function formatClock(seconds: number): string {
  const safe = Math.max(0, Math.min(STORY_DURATION_SECONDS, seconds));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(Math.floor(safe % 60)).padStart(2, "0")}`;
}

function riskTone(signal: RiskSignal): string {
  if (signal.score >= 0.75) return "critical";
  if (signal.score >= 0.5) return "elevated";
  if (signal.score >= 0.25) return "guarded";
  return "low";
}

function segmentTone(status: string): string {
  if (status === "eligible") return "positive";
  if (status === "paused" || status === "held") return "negative";
  if (status === "abstain") return "warning";
  return "neutral";
}

export function ControlRoom() {
  const reducedMotion = useReducedMotion();
  const [snapshot, setSnapshot] = useState<EpisodeSnapshot>(() => createMockSnapshot(0));
  const snapshotRef = useRef(snapshot);
  const [source, setSource] = useState<DataSource>("simulation");
  const [latency, setLatency] = useState(0);
  const [warning, setWarning] = useState<string | undefined>(
    "Control room is ready. Live API handshake begins with the mission.",
  );
  const [isBusy, setIsBusy] = useState(false);
  const [answerFlash, setAnswerFlash] = useState(false);
  const [lastTransition, setLastTransition] = useState("Control room ready");
  const requestVersion = useRef(0);
  const autoStarted = useRef(false);

  useEffect(() => {
    snapshotRef.current = snapshot;
  }, [snapshot]);

  const applyResult = useCallback((result: ClientResult, phaseIndex: number, version: number) => {
    if (version !== requestVersion.current) return;
    const currentId = snapshotRef.current.mission_id;
    const data = result.source === "simulation"
      ? createMockSnapshot(phaseIndex, result.snapshot.mission_id || currentId)
      : result.snapshot;
    setSnapshot(data);
    setSource(result.source);
    setLatency(result.latencyMs);
    setWarning(result.warning);
  }, []);

  const executePhase = useCallback(
    async (phaseIndex: number) => {
      if (phaseIndex === 0) return;
      const missionId = snapshotRef.current.mission_id;
      const version = requestVersion.current;
      setSnapshot((current) => createMockSnapshot(phaseIndex, current.mission_id));
      setLastTransition(STORY_PHASES[phaseIndex].decision);

      let result: ClientResult;
      if (phaseIndex === 1) {
        result = await stepMission(missionId, phaseIndex, "diagnose");
      } else if (phaseIndex === 2) {
        result = await stepMission(missionId, phaseIndex, "experiment");
      } else if (phaseIndex === 3) {
        result = await injectMissionDrift(missionId, phaseIndex);
      } else if (phaseIndex === 4) {
        result = await stepMission(missionId, phaseIndex, "ask_human");
      } else if (phaseIndex === 5) {
        result = await submitHumanAnswer(
          missionId,
          {
            answer: "Preserve at least 15% contribution margin; first-order subsidy may not exceed $8.00.",
            margin_floor: 0.15,
            subsidy_cap: 8,
          },
          phaseIndex,
        );
        if (result.source === "api" && result.snapshot.state === "ready_to_deploy") {
          result = await stepMission(missionId, phaseIndex, "segment_deploy");
        }
      } else {
        // The backend owns its state transition policy. Keeping requested_action
        // optional makes this compatible as its ActionType vocabulary evolves.
        result = await stepMission(missionId, phaseIndex);
      }
      applyResult(result, phaseIndex, version);
    },
    [applyResult],
  );

  const narrative = useNarrative({ onPhaseChange: executePhase });
  const phase = STORY_PHASES[narrative.phaseIndex];

  const handleRun = useCallback(async () => {
    const version = ++requestVersion.current;
    setIsBusy(true);
    setSource("simulation");
    setWarning("Negotiating mission contract with localhost:8000…");
    setSnapshot(createMockSnapshot(0));
    setLastTransition("MISSION CONTRACT OPENED");
    narrative.start();
    const result = await startMission({ budget: 30000, max_diversity_loss: 0.02, seed: 42 });
    applyResult(result, 0, version);
    setIsBusy(false);
  }, [applyResult, narrative.start]);

  const handleInjectDrift = useCallback(() => {
    narrative.jumpTo(3);
    setLastTransition("DRIFT INJECTION REQUESTED");
  }, [narrative.jumpTo]);

  const handleHumanAnswer = useCallback(() => {
    setAnswerFlash(true);
    window.setTimeout(() => setAnswerFlash(false), 2200);
    narrative.jumpTo(5);
    setLastTransition("HUMAN BOUNDARY RECEIVED");
  }, [narrative.jumpTo]);

  const handleReset = useCallback(async () => {
    const version = ++requestVersion.current;
    narrative.reset();
    setSnapshot((current) => createMockSnapshot(0, current.mission_id));
    setLastTransition("MISSION RESET");
    setWarning("Control room reset. Ready for a new evidence trajectory.");
    const result = await resetMission(snapshotRef.current.mission_id);
    applyResult(result, 0, version);
  }, [applyResult, narrative.reset]);

  const handleTimelineJump = useCallback(
    (index: number) => {
      narrative.jumpTo(index, false, false);
      setSnapshot((current) => createMockSnapshot(index, current.mission_id));
      setLastTransition(`REVIEWING ${STORY_PHASES[index].shortLabel.toUpperCase()}`);
    },
    [narrative.jumpTo],
  );

  useEffect(() => {
    if (autoStarted.current) return;
    autoStarted.current = true;
    const timer = window.setTimeout(() => {
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) void handleRun();
    }, 1300);
    return () => window.clearTimeout(timer);
  }, [handleRun]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTyping = target?.matches("input, textarea, select, [contenteditable='true']");
      if (
        event.key.toLowerCase() !== "r"
        || event.altKey
        || event.ctrlKey
        || event.metaKey
        || event.shiftKey
        || isTyping
        || isBusy
      ) return;

      event.preventDefault();
      void handleRun();
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleRun, isBusy]);

  const budgetProgress = Math.min(1, snapshot.budget_used / Math.max(1, snapshot.budget));
  const dominantRisk = useMemo(() => {
    return RISK_META.reduce((highest, item) =>
      snapshot.risks[item.key].score > snapshot.risks[highest.key].score ? item : highest,
    );
  }, [snapshot.risks]);
  const scopeShares = useMemo(() => {
    const sum = (statuses: Set<string>) => snapshot.segments.reduce(
      (total, segment) => total + (statuses.has(segment.status.toLowerCase()) ? segment.share : 0),
      0,
    );
    return {
      safe: Math.round(sum(new Set(["eligible", "deployed"])) * 100),
      withheld: Math.round(sum(new Set(["held", "paused", "abstain", "abstained"])) * 100),
    };
  }, [snapshot.segments]);
  const phaseDecision = narrative.phaseIndex === 5
    ? `SAFE SCOPE ${scopeShares.safe}% / WITHHOLD ${scopeShares.withheld}%`
    : phase.decision;

  return (
    <main className="control-room">
      <a href="#mission-command" className="skip-link">
        Skip to mission controls
      </a>

      <header className="topbar">
        <div className="brand-lockup" role="group" aria-label="CausalPilot TRACE">
          <div className="brand-mark" aria-hidden="true">
            <Fingerprint size={23} strokeWidth={1.45} />
          </div>
          <div>
            <strong>CAUSALPILOT</strong>
            <span>TRACE / MARKET CONTROL ROOM</span>
          </div>
        </div>

        <div className="topbar__telemetry" role="group" aria-label="Mission telemetry">
          <span><Radio size={12} aria-hidden="true" /> Mission {snapshot.mission_id}</span>
          <span><ScanLine size={12} aria-hidden="true" /> Step {String(snapshot.step).padStart(2, "0")}</span>
          <span className={`api-state api-state--${source}`}>
            <i aria-hidden="true" />
            {source === "api"
              ? `LIVE API · SIMULATED SCM · ${latency} ms`
              : "STATIC REPLAY · SIMULATED SCM"}
          </span>
        </div>

        <div className="topbar__mode">
          <ShieldCheck size={14} aria-hidden="true" />
          <span>Governance envelope</span>
          <strong>ENFORCED</strong>
        </div>
      </header>

      <section className="story-rail" aria-label="90 second narrative progress">
        <div className="story-rail__clock">
          <span>AUTO STORY</span>
          <strong>{formatClock(narrative.elapsed)}</strong>
          <small>/ 01:30</small>
        </div>
        <div className="story-rail__track">
          <div className="story-rail__fill" style={{ width: `${narrative.progress * 100}%` }} />
          {STORY_PHASES.map((item, index) => (
            <button
              type="button"
              key={item.id}
              className={`story-marker ${index === narrative.phaseIndex ? "is-active" : ""} ${index < narrative.phaseIndex ? "is-complete" : ""}`}
              style={{ left: `${(item.start / STORY_DURATION_SECONDS) * 100}%` }}
              onClick={() => handleTimelineJump(index)}
              aria-label={`Review ${item.shortLabel} phase at ${item.start} seconds`}
              aria-current={index === narrative.phaseIndex ? "step" : undefined}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
            </button>
          ))}
        </div>
        <div className="story-rail__phase">
          <i className={narrative.isRunning ? "is-live" : ""} aria-hidden="true" />
          <span>{narrative.isRunning ? "PLAYING" : "READY"}</span>
          <strong>{phase.shortLabel}</strong>
        </div>
      </section>

      <div className="control-grid">
        <aside className="panel panel--mission" aria-labelledby="mission-title">
          <div className="panel-heading">
            <div>
              <span className="kicker">DECISION CONTRACT</span>
              <h1 id="mission-title">Mission envelope</h1>
            </div>
            <span className="panel-code">OBJ–01</span>
          </div>

          <div className="mission-brief">
            <div className="mission-brief__icon"><Sparkles size={16} aria-hidden="true" /></div>
            <p>{snapshot.goal}</p>
          </div>

          <div className="constraint-grid" role="group" aria-label="Mission constraints">
            <div>
              <span>Evidence budget</span>
              <strong>{formatCompact(snapshot.budget)}</strong>
              <small>exposures</small>
            </div>
            <div>
              <span>Diversity floor</span>
              <strong>−{(snapshot.max_diversity_loss * 100).toFixed(1)}%</strong>
              <small>max loss</small>
            </div>
          </div>

          <div className="budget-meter">
            <div className="budget-meter__labels">
              <span>Budget consumed</span>
              <strong>{formatCompact(snapshot.budget_used)} / {formatCompact(snapshot.budget)}</strong>
            </div>
            <div className="meter-track" role="progressbar" aria-label="Evidence budget used" aria-valuenow={Math.round(budgetProgress * 100)} aria-valuemin={0} aria-valuemax={100}>
              <span style={{ width: `${budgetProgress * 100}%` }} />
            </div>
          </div>

          <div className="section-label">
            <span>TRACE risk surface</span>
            <small>RISK INDEX / 0–1</small>
          </div>

          <div className="risk-list">
            {RISK_META.map(({ key, label, code, icon: Icon }) => {
              const risk = snapshot.risks[key];
              const tone = riskTone(risk);
              return (
                <article className={`risk-row risk-row--${tone}`} key={key}>
                  <div className="risk-row__icon"><Icon size={15} aria-hidden="true" /></div>
                  <div className="risk-row__content">
                    <div>
                      <strong>{label}</strong>
                      <span>{risk.evidence[0]}</span>
                    </div>
                    <div className="risk-row__meter" aria-hidden="true">
                      <span style={{ width: `${Math.min(100, risk.score * 100)}%` }} />
                    </div>
                  </div>
                  <div className="risk-row__score">
                    <small>{code}</small>
                    <strong>{risk.score.toFixed(2)}</strong>
                  </div>
                </article>
              );
            })}
          </div>

          <div className={`risk-callout risk-callout--${riskTone(snapshot.risks[dominantRisk.key])}`}>
            <AlertTriangle size={15} aria-hidden="true" />
            <div>
              <span>Binding risk</span>
              <strong>{dominantRisk.label} / {snapshot.risks[dominantRisk.key].level}</strong>
            </div>
          </div>
        </aside>

        <section className="viewport-column" aria-labelledby="topology-title">
          <div className="scene-shell">
            <div className="scene-corner scene-corner--tl" aria-hidden="true" />
            <div className="scene-corner scene-corner--tr" aria-hidden="true" />
            <div className="scene-corner scene-corner--bl" aria-hidden="true" />
            <div className="scene-corner scene-corner--br" aria-hidden="true" />

            <div className="viewport-label">
              <span className="kicker">LIVE CAUSAL TOPOLOGY</span>
              <h2 id="topology-title">Market evidence field</h2>
            </div>

            <div className="scene-meta scene-meta--left" aria-hidden="true">
              <span>X / USER LATENT</span>
              <span>Y / RESPONSE</span>
              <span>Z / UNCERTAINTY</span>
            </div>

            <div className="scene-legend" role="group" aria-label="Visualization legend">
              <span><i className="legend-dot legend-dot--safe" /> Evidence safe</span>
              <span><i className="legend-dot legend-dot--probe" /> Under probe</span>
              <span><i className="legend-dot legend-dot--risk" /> Risk isolated</span>
            </div>

            <MarketScene snapshot={snapshot} phaseIndex={narrative.phaseIndex} reducedMotion={reducedMotion} />

            <div className="viewport-scan" aria-hidden="true" />
            <div className="scene-readout">
              <div>
                <span>COHORTS</span>
                <strong>{String(snapshot.segments.length).padStart(2, "0")}</strong>
              </div>
              <div>
                <span>OVERLAP</span>
                <strong>{(snapshot.metrics.overlap_fraction * 100).toFixed(0)}%</strong>
              </div>
              <div>
                <span>DRIFT PSI</span>
                <strong className={snapshot.metrics.drift_psi > 0.25 ? "text-danger" : ""}>{snapshot.metrics.drift_psi.toFixed(2)}</strong>
              </div>
            </div>
          </div>

          <article className="narrative-card" aria-live="polite" aria-atomic="true">
            <div className="narrative-card__index">{String(narrative.phaseIndex + 1).padStart(2, "0")}</div>
            <div className="narrative-card__copy">
              <span>{phase.eyebrow}</span>
              <h2>{phase.title}</h2>
              <p>{phase.narrative}</p>
            </div>
            <div className="narrative-card__decision">
              <span>AGENT DECISION</span>
              <strong>{phaseDecision}</strong>
              <ChevronRight size={16} aria-hidden="true" />
            </div>
          </article>
        </section>

        <aside className="panel panel--evidence" aria-labelledby="evidence-title">
          <div className="panel-heading">
            <div>
              <span className="kicker">CAUSAL TELEMETRY</span>
              <h2 id="evidence-title">Evidence ledger</h2>
            </div>
            <span className="panel-code">EVD–07</span>
          </div>

          <div className="metric-grid">
            {METRIC_META.map((metric) => (
              <div className="metric-cell" key={metric.key}>
                <span>{metric.label}</span>
                <strong>{formatMetric(snapshot.metrics[metric.key], metric.format, metric.suffix)}</strong>
                <small>
                  {metric.key === "uplift"
                    ? `CI ${(snapshot.metrics.ci_low * 100).toFixed(1)}–${(snapshot.metrics.ci_high * 100).toFixed(1)}%`
                    : metric.key === "power"
                      ? `p = ${snapshot.metrics.p_value.toFixed(3)}`
                      : "trajectory-adjusted"}
                </small>
              </div>
            ))}
          </div>

          <div className="decision-block">
            <div className="decision-block__top">
              <span>CURRENT ACTION</span>
              <i aria-hidden="true" />
            </div>
            <strong>{snapshot.decision.action.replaceAll("_", " ")}</strong>
            <p>{snapshot.decision.rationale}</p>
          </div>

          {snapshot.pending_question && (
            <div className={`human-query ${answerFlash ? "is-answered" : ""}`}>
              <div><UserRoundCheck size={16} aria-hidden="true" /><span>HUMAN BOUNDARY NEEDED</span></div>
              <p>{snapshot.pending_question}</p>
              <small>VoI score 0.83 · one constraint can change the release policy</small>
            </div>
          )}

          {answerFlash && (
            <div className="answer-toast" role="status">
              <Check size={15} aria-hidden="true" /> Bounds accepted: 15% margin · $8 subsidy cap
            </div>
          )}

          <div className="section-label">
            <span>Segment policy</span>
            <small>SELECTIVE RELEASE</small>
          </div>
          <div className="segment-list">
            {snapshot.segments.map((segment) => (
              <div className="segment-row" key={segment.id}>
                <div className={`segment-row__status segment-row__status--${segmentTone(segment.status)}`} aria-hidden="true" />
                <div className="segment-row__name">
                  <strong>{segment.label}</strong>
                  <span>{Math.round(segment.share * 100)}% market · risk {segment.risk.toFixed(2)}</span>
                </div>
                <div className="segment-row__uplift">
                  <strong className={segment.uplift < 0 ? "text-danger" : ""}>{segment.uplift >= 0 ? "+" : ""}{(segment.uplift * 100).toFixed(1)}%</strong>
                  <span>{segment.status}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="section-label section-label--timeline">
            <span>Decision timeline</span>
            <small>AUDITABLE</small>
          </div>
          <ol className="decision-timeline">
            {STORY_PHASES.map((item, index) => (
              <li key={item.id} className={index === narrative.phaseIndex ? "is-active" : index < narrative.phaseIndex ? "is-complete" : ""}>
                <button type="button" onClick={() => handleTimelineJump(index)}>
                  <span className="decision-timeline__node">{index < narrative.phaseIndex ? <Check size={10} aria-hidden="true" /> : index + 1}</span>
                  <span>
                    <strong>{item.decision}</strong>
                    <small>T+{String(item.start).padStart(2, "0")} SEC · {item.shortLabel}</small>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </aside>
      </div>

      <footer className="command-deck" id="mission-command">
        <div className="command-deck__status">
          <div className="command-deck__status-icon"><Network size={17} aria-hidden="true" /></div>
          <div>
            <span>TRAJECTORY STATE / {snapshot.state}</span>
            <strong>{lastTransition}</strong>
          </div>
        </div>

        <div className="command-deck__buttons" role="group" aria-label="Mission controls">
          <button type="button" className="control-button control-button--primary" onClick={() => void handleRun()} disabled={isBusy}>
            {isBusy ? <RefreshCcw className="spin" size={16} aria-hidden="true" /> : <Play size={16} fill="currentColor" aria-hidden="true" />}
            <span>Run Mission</span>
            <kbd>R</kbd>
          </button>
          <button
            type="button"
            className="control-button control-button--danger"
            onClick={() => void handleInjectDrift()}
            disabled={isBusy || narrative.phaseIndex !== 2}
            title="Available after the randomized probe completes"
          >
            <FlaskConical size={16} aria-hidden="true" />
            <span>Inject Drift</span>
          </button>
          <button
            type="button"
            className={`control-button ${narrative.phaseIndex === 4 ? "is-recommended" : ""}`}
            onClick={() => void handleHumanAnswer()}
            disabled={isBusy || narrative.phaseIndex !== 4}
            title="Available when TRACE requests the economic bounds"
          >
            <Hand size={16} aria-hidden="true" />
            <span>Human Answer</span>
          </button>
          <button type="button" className="control-button control-button--icon" onClick={() => void handleReset()} aria-label="Reset mission">
            <RotateCcw size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="command-deck__guardrail">
          <div><Gauge size={15} aria-hidden="true" /><span>EPISODE HARM</span><strong>0</strong></div>
          <div><CircleGauge size={15} aria-hidden="true" /><span>WITHHELD</span><strong>{narrative.phaseIndex >= 5 ? `${scopeShares.withheld}%` : "—"}</strong></div>
        </div>
      </footer>

      <div className="sr-only" role="status" aria-live="polite">
        {warning} Current phase: {phase.shortLabel}. Current action: {snapshot.decision.action}.
      </div>
    </main>
  );
}
