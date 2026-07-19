# Why this is not another agent wrapper

An agent wrapper sends a prompt to a model, exposes a few tools, and presents the final answer as the product. CausalPilot puts the model behind a decision boundary. The model may propose a hypothesis, tool, or action, but it does not receive deployment authority merely because its explanation sounds confident.

## The contribution is a testable policy

CausalPilot asks a falsifiable question: under fixed experiment and human-attention budgets, does trajectory-aware evidence gating reduce harmful deployments and regret at matched coverage?

That claim can fail. The checked-in benchmark compares TRACE with direct, tool-using, fixed-pipeline, verbal-confidence, no-TRACE, always-deploy, and always-ask/abstain policies. It also removes the probe, human-query, dynamic-risk, and value-of-information components one at a time. If the components do not improve a frozen metric, the project does not relabel the result as success.

## Language proposes; code commits

The coordinator may:

- parse a goal and produce candidate hypotheses;
- select a relevant diagnostic;
- propose an information or deployment action;
- write a short, evidence-linked rationale.

Deterministic code owns:

- randomization, sample-ratio mismatch, balance, overlap, effect intervals, power, drift, and guardrail calculations;
- state-transition preconditions and budget accounting;
- model, causal, data, and environment risk indices;
- segment admissibility, action gates, rollback, and abstention;
- the in-memory transition trace consumed by the UI, plus the pure policy gate reused by the evaluator.

The coordinator cannot call a hidden commit path or overwrite a failed gate.

## The agent can buy evidence

When evidence is weak, CausalPilot does not have to guess. Its action space includes diagnostics, a bounded randomized probe, and one structured human question chosen for its decision value. Deploying, pausing, rolling back, and abstaining are explicit outcomes rather than prose at the end of a chat.

## The visualization is an audit view

The local 3D control room is driven by the API episode snapshot. The headless benchmark does not pretend to run the full API engine; it reuses the same pure TRACE policy gate and keeps hidden truth in a separate scorer. Cluster size encodes segment share, color encodes estimated effect/risk, particles encode simulated traffic batches, and gates encode policy checks. A two-dimensional table exposes the same state without color or animation.

## The evidence level never disappears

Every run is labeled as one of:

- `SIMULATED GROUND TRUTH`;
- `PUBLIC RCT — OFFLINE`;
- `LOGGED BANDIT — OPE`.

The system does not turn a deterministic demo, a historical randomized log, or an off-policy estimate into a claim about live customer impact.
