export const STORY_DURATION_SECONDS = 90;

export const STORY_PHASES = [
  {
    id: "brief",
    label: "01 / Mandate",
    shortLabel: "Mandate",
    start: 0,
    end: 10,
    eyebrow: "MISSION ACCEPTED",
    title: "Profit has a safety constraint.",
    narrative:
      "TRACE translates the growth brief into a decision contract: conversion upside, 30,000 exposures, and no more than 2% diversity loss.",
    decision: "FORMALIZE CONSTRAINTS",
  },
  {
    id: "diagnose",
    label: "02 / Diagnose",
    shortLabel: "Diagnose",
    start: 10,
    end: 24,
    eyebrow: "EVIDENCE CHECK",
    title: "Correlation is not permission.",
    narrative:
      "Historical logs suggest lift, but overlap is thin and selection bias is visible. TRACE blocks the tempting full-market launch.",
    decision: "REJECT GLOBAL DEPLOY",
  },
  {
    id: "probe",
    label: "03 / Probe",
    shortLabel: "Probe",
    start: 24,
    end: 40,
    eyebrow: "RANDOMIZED PROBE",
    title: "Buy the smallest useful evidence.",
    narrative:
      "A budget-aware randomized probe splits traffic. Confidence tightens while treatment and control particles stream through the market.",
    decision: "RUN 8K RCT PROBE",
  },
  {
    id: "drift",
    label: "04 / Drift",
    shortLabel: "Drift",
    start: 40,
    end: 58,
    eyebrow: "ENVIRONMENT SHIFT",
    title: "The market just moved.",
    narrative:
      "A new-customer cohort arrives. Population stability breaks; TRACE isolates the segment while the baseline policy would keep shipping.",
    decision: "HOLD SHIFTED COHORT",
  },
  {
    id: "human",
    label: "05 / Escalate",
    shortLabel: "Escalate",
    start: 58,
    end: 74,
    eyebrow: "VALUE OF HUMAN INPUT",
    title: "Ask one question, not twenty.",
    narrative:
      "The remaining uncertainty is a business constraint, not a modeling problem. TRACE requests the margin floor and shifted-cohort subsidy cap with highest decision value.",
    decision: "REQUEST ECONOMIC BOUNDS",
  },
  {
    id: "deploy",
    label: "06 / Govern",
    shortLabel: "Govern",
    start: 74,
    end: 90,
    eyebrow: "SELECTIVE RELEASE",
    title: "Autonomy is earned by evidence.",
    narrative:
      "Only interval-supported cohorts enter the action scope; shifted and harmful cohorts remain held. Every action, tool result, and human boundary is preserved in the audit trail.",
    decision: "SELECTIVE DEPLOY / WITHHOLD",
  },
] as const;

export type StoryPhase = (typeof STORY_PHASES)[number];
export type StoryPhaseId = StoryPhase["id"];

export function phaseAtElapsed(elapsedSeconds: number): number {
  const index = STORY_PHASES.findIndex(
    (phase) => elapsedSeconds >= phase.start && elapsedSeconds < phase.end,
  );
  return index === -1 ? STORY_PHASES.length - 1 : index;
}

export function elapsedForPhase(index: number): number {
  return STORY_PHASES[Math.max(0, Math.min(STORY_PHASES.length - 1, index))].start;
}
