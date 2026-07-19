import { EpisodeSnapshot, MissionSegment, RiskLevel, RiskSignal } from "./types";

const PHASE_STATES = [
  "READY",
  "DIAGNOSING",
  "PROBING",
  "DRIFT_DETECTED",
  "AWAITING_HUMAN",
  "DEPLOYED",
] as const;

function signal(score: number, evidence: string[]): RiskSignal {
  let level: RiskLevel = "low";
  if (score >= 0.75) level = "critical";
  else if (score >= 0.5) level = "elevated";
  else if (score >= 0.25) level = "guarded";
  return { score, level, evidence };
}

function segment(
  id: string,
  label: string,
  share: number,
  coordinates: [number, number, number],
  phase: number,
): MissionSegment {
  const profiles = {
    loyal: { uplift: 0.036, risk: 0.13, diversity: -0.006, status: "eligible" },
    explorers: { uplift: 0.024, risk: 0.26, diversity: -0.014, status: "eligible" },
    new: { uplift: 0.004, risk: phase >= 3 ? 0.91 : 0.62, diversity: -0.008, status: "held" },
    price: { uplift: -0.012, risk: 0.57, diversity: -0.003, status: "abstain" },
  }[id] ?? { uplift: 0, risk: 0.5, diversity: 0, status: "probe" };

  const uncertainty = phase < 2 ? 0.038 : phase === 2 ? 0.019 : 0.012;
  const uplift = phase === 0 ? profiles.uplift * 0.45 : profiles.uplift;
  const status =
    phase < 2
      ? "probe"
      : phase === 3 && id === "new"
        ? "paused"
        : phase >= 5
          ? profiles.status
          : id === "new"
            ? "paused"
            : "probe";
  return {
    id,
    label,
    share,
    status,
    uplift,
    ci_low: uplift - uncertainty,
    ci_high: uplift + uncertainty,
    risk: profiles.risk,
    diversity_delta: profiles.diversity,
    coordinates,
  };
}

export function createMockSnapshot(phaseInput = 0, missionId = "TRACE-042-A"): EpisodeSnapshot {
  const phase = Math.max(0, Math.min(5, Math.round(phaseInput)));
  const exposures = [0, 2400, 8100, 14200, 19600, 30000][phase];
  const budgetUsed = [0, 1200, 8100, 14200, 19600, 30000][phase];
  const auditActions = [
    ["agent", "CONSTRAINTS_COMPILED", "Objective converted to an executable decision contract."],
    ["tool", "GLOBAL_DEPLOY_BLOCKED", "Overlap 0.58; observational lift is not decision-safe."],
    ["agent", "RCT_PROBE_ALLOCATED", "8,100 exposures assigned to a randomized evidence probe."],
    ["tool", "DRIFT_ISOLATED", "PSI 0.31 in new arrivals; segment traffic paused."],
    ["human", "MARGIN_BOUNDARY_REQUESTED", "One high-value question escalated to growth lead."],
    ["agent", "SELECTIVE_POLICY_RELEASED", "Eligible cohorts released; unsafe cohorts abstained."],
  ] as const;

  return {
    mission_id: missionId,
    evidence_mode: "simulated_scm",
    fixture_version: "causalpilot-browser-sim-v1",
    fixture_hash: "offline-seeded",
    config_hash: "browser-default",
    dataset_version: "causalpilot-browser-sim-v1",
    split: "static_demo_episode",
    seed: 42,
    estimator: "seeded_visual_narrative",
    assumptions: [
      "Browser-only deterministic fallback; not a live experiment.",
      "Displayed values illustrate the decision workflow and are not benchmark outputs.",
    ],
    state: PHASE_STATES[phase],
    step: phase,
    goal: "Increase fashion recommendation conversion without sacrificing discovery",
    budget: 30000,
    budget_used: budgetUsed,
    max_diversity_loss: 0.02,
    risks: {
      model: signal([0.42, 0.37, 0.24, 0.25, 0.2, 0.12][phase], [
        phase < 2 ? "Planner confidence is not evidence" : "Tool trace agrees across 3 seeds",
      ]),
      causal: signal([0.81, 0.78, 0.46, 0.38, 0.26, 0.14][phase], [
        phase < 2 ? "Treatment assignment is confounded" : "Random assignment verified",
      ]),
      data: signal([0.66, 0.62, 0.34, 0.3, 0.22, 0.16][phase], [
        phase < 2 ? "Weak propensity overlap" : "SRM p=0.71 · balance SMD=0.04",
      ]),
      environment: signal([0.18, 0.2, 0.22, 0.91, 0.76, 0.28][phase], [
        phase === 3 || phase === 4 ? "New-arrival PSI crossed 0.25" : "Population stable",
      ]),
    },
    metrics: {
      exposures,
      treatment_n: Math.round(exposures * 0.5),
      control_n: Math.round(exposures * 0.5),
      treatment_rate: phase < 2 ? 0 : 0.0834,
      control_rate: phase < 2 ? 0 : 0.0612,
      uplift: phase < 2 ? 0.031 : 0.0222,
      ci_low: phase < 2 ? -0.012 : phase === 2 ? 0.003 : 0.0104,
      ci_high: phase < 2 ? 0.074 : phase === 2 ? 0.0414 : 0.034,
      p_value: phase < 2 ? 0.42 : phase === 2 ? 0.041 : 0.006,
      srm_p_value: phase < 2 ? 0.19 : 0.71,
      max_balance_smd: phase < 2 ? 0.28 : 0.04,
      overlap_fraction: phase < 2 ? 0.58 : 0.94,
      power: [0.08, 0.22, 0.63, 0.78, 0.87, 0.93][phase],
      drift_psi: phase === 3 || phase === 4 ? 0.31 : phase === 5 ? 0.09 : 0.04,
      expected_incremental_conversions: [0, 0, 52, 87, 103, 133][phase],
      policy_regret: [0.186, 0.161, 0.094, 0.073, 0.052, 0.028][phase],
    },
    segments: [
      segment("loyal", "Loyal high-intent", 0.18, [-2.45, 0.7, 0.15], phase),
      segment("explorers", "Style explorers", 0.26, [1.6, 1.25, -0.75], phase),
      segment("new", "New arrivals", 0.34, [2.35, -1.25, 0.25], phase),
      segment("price", "Price sensitive", 0.22, [-1.25, -1.55, -0.65], phase),
    ],
    decision: {
      action: [
        "FORMALIZE_CONSTRAINTS",
        "REJECT_GLOBAL_DEPLOY",
        "RUN_RANDOMIZED_PROBE",
        "PAUSE_DRIFTED_SEGMENT",
        "ASK_HUMAN",
        "SELECTIVE_DEPLOY",
      ][phase],
      rationale: [
        "Convert the brief into machine-checkable risk and diversity limits.",
        "Historical uplift is confounded and overlap is below the deployment floor.",
        "The probe has positive expected value and fits within the evidence budget.",
        "Environment shift invalidates evidence for the new-arrival segment only.",
        "Margin floor is the only unresolved constraint that could change the policy.",
        "Deploy only where uplift is interval-supported and diversity-safe.",
      ][phase],
      eligible_segments: phase >= 5 ? ["loyal", "explorers"] : [],
    },
    allowed_actions:
      phase === 4 ? ["HUMAN_ANSWER", "ABSTAIN"] : phase === 5 ? ["ROLLBACK", "MONITOR"] : ["STEP", "ABSTAIN"],
    pending_question:
      phase === 4 ? "What margin floor and first-order subsidy cap bound the shifted cohort?" : null,
    audit: auditActions.slice(0, phase + 1).map(([actor, action, detail], index) => ({
      id: `audit-${index}`,
      step: index,
      timestamp: `T+${[0, 10, 24, 40, 58, 74][index]}s`,
      actor,
      action,
      detail,
      status: index === phase ? "active" : "complete",
    })),
  };
}
