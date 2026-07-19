# Data card

CausalPilot ships a synthetic, seeded fashion-recommendation scenario. The
default demo and benchmark need no downloaded dataset, user record, or API key.

## Default synthetic scenario

| Property | Description |
| --- | --- |
| Unit | One mission episode containing segment-level experiment observations |
| Generator | Deterministic code controlled by an integer seed |
| Objective | Improve a simulated conversion outcome under a diversity guardrail |
| Intervention budget | Declared by the mission request |
| Observed evidence | Treatment/control counts and rates, effect interval, balance, overlap, power, drift, and segment estimates |
| Hidden evaluation data | Potential outcomes and scenario labels used only by the scorer |
| Personal data | None |
| Production traffic | None |

The simulator supports software tests and policy comparisons. It does not
represent a real population, market, advertiser, recommender, or intervention.

## Evidence labels

Every result should retain one of these labels:

- `SIMULATED GROUND TRUTH` — scorer access to checked-in synthetic potential outcomes;
- `PUBLIC RCT — OFFLINE` — aggregate estimates from a public randomized log;
- `LOGGED BANDIT — OPE` — off-policy estimates from logged propensities and outcomes.

These labels are not interchangeable. An offline estimate does not establish a
live business effect.

## Leakage boundary

Runtime policies may inspect observations, declared constraints, past actions,
and structured human answers. They may not inspect hidden effect tables, harmful
segment labels, or future drift labels. The evaluator alone uses those fields to
score decisions. Ground-truth scorer metrics carry a `_gt` suffix.

## Optional external adapters

The repository contains optional adapters for public logged-bandit and randomized
uplift data. It does not redistribute raw source data. Users must obtain data from
the source, review its current license and terms, and keep it outside version
control.

Adapter smoke checks establish that a file can be parsed and summarized. They do
not establish external validity, individual counterfactual truth, production
lift, or policy safety. See `evaluation/README.md` for commands and
`docs/research_landscape.md` for source-specific notes.

## Provenance and reproducibility

A benchmark artifact should record:

- simulator and policy configuration;
- the complete predeclared seed list;
- metric definitions and evidence scope;
- row-level outcomes and aggregate intervals;
- the code revision used to produce it.

The checked-in result files under `evaluation/results/` are **GENERATED**. The
repository's prose must link to them instead of copying untraceable numbers.

## Known biases

The scenario encodes a small, hand-designed action space and segment structure.
Its outcomes, effect heterogeneity, drift patterns, and human questions reflect
the benchmark designer's choices. Policies may overfit these choices. Seed
variation measures only variation inside this generator.

Use the simulator to test implementation claims. Use prospective, governed field
experiments to test real-world claims.
