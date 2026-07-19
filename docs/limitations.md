# Limitations and failure modes

CausalPilot demonstrates an auditable decision loop. It does not establish that
an autonomous agent is safe or effective in production.

## Evidence limits

- The default mission is synthetic. Its outcomes do not estimate real customer,
  advertiser, or platform impact.
- LLM-shaped benchmark policies are disclosed decision-rule proxies unless a run
  records a real model call.
- TRACE values are risk indices, not calibrated failure probabilities.
- A confidence interval and a passing gate remain conditional on the simulated
  assignment mechanism, estimand, data quality, and guardrail definition.
- Hidden simulator truth supports scoring only. It is unavailable in a real
  deployment.
- A fixed seed suite can expose regressions inside the checked-in generator, but
  it cannot prove universal superiority.

## System limits

- Missions and audit events live in process memory. A restart loses them.
- The API has no authentication, authorization, rate limiting, durable storage,
  tenant isolation, or distributed lock.
- The server-sent events route replays existing audit events and closes. It does
  not push future events as a durable stream.
- The UI falls back to a seeded browser simulator after an API error or timeout.
  A successful visual sequence may therefore hide a backend outage; inspect the
  source badge.
- The static hosted demo always uses the browser simulator.
- The default path calls no LLM and performs no external business action.
- Dependency ranges in the Python package allow compatible updates; CI does not
  yet install from a hash-locked Python environment.

## Decision risks

| Failure mode | Current control | Remaining exposure |
| --- | --- | --- |
| Unsupported causal conclusion | Deterministic diagnostics and causal-risk gate | The software cannot verify every identification assumption |
| Small or imbalanced probe | Budget, balance, overlap, and precision checks | Synthetic checks may miss real instrumentation bias |
| Constraint omitted in prose | Structured human fields and unified action validation | A real organization needs authoritative policy and identity systems |
| Distribution shift | Drift index, pause, rollback, and abstain actions | Unknown shifts may evade the checked detector |
| Convincing but wrong rationale | Code owns commit rights | Evidence code and thresholds can still contain defects |
| Concurrent budget use | Per-mission mutation lock and regression tests | The in-memory design does not coordinate multiple processes |
| Metric gaming | Frozen definitions, row-level outputs, and ablations | Benchmark design remains a human choice |

## Not evaluated

The checked-in work does not evaluate:

- production load, availability, or disaster recovery;
- adversarial clients, prompt injection, or tool-supply-chain attacks;
- privacy, fairness, or regulatory compliance on personal data;
- irreversible actions, money movement, or access to customer systems;
- long-horizon model drift or organizational adoption;
- live latency, token cost, or human-review workload;
- generalization beyond the declared scenarios and seeds.

## Appropriate use

Use CausalPilot as a portfolio artifact, research harness, teaching example, or
starting point for controlled offline studies. Keep it on a trusted local
machine, use synthetic or properly governed data, and require an external human
approval system before any real action.

See [Claims we do not make](claims_we_do_not_make.md) for the repository-wide
claim contract.
