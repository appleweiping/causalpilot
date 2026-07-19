# Claims we do not make

CausalPilot is a research prototype and portfolio artifact. This page defines the boundary around every result shown in the repository.

## No live deployment claim

The included fashion mission is a seeded simulator. Its 30,000 impressions are simulated probe assignments, not real users, ads, or recommendation traffic. No external production action is performed.

## No inherited 49.28% claim

The 49.28% figure reported by KP-Agent is a historical-data simulation result against one regression baseline under that paper's assumptions. It is not a result produced by CausalPilot and is never presented as a live profit lift.

## No conversion claim from Open Bandit Dataset

Open Bandit Dataset records clicks. An OPE result on it estimates click-policy value under stated support and estimator assumptions; it does not establish conversion, revenue, or profit improvement.

## No individual counterfactual truth from Criteo

Criteo Uplift provides randomized treatment and observed outcomes, not both potential outcomes for each person. We report group or policy estimates with uncertainty. We do not call an estimated individual uplift “ground truth.” The default adapter targets the corrected 13,979,592-row version because the original 25,309,483-row release has a documented advertiser-leak issue.

## No calibrated probability without calibration evidence

The four TRACE values are called **risk indices** unless a held-out reliability artifact maps them to unsafe-action frequencies. A value such as `0.72` is not described as a 72% probability by default.

## No automatic causal guarantee

A passing software check does not prove that a business estimand is identified. Results remain conditional on the declared assignment mechanism, data quality, estimator, segmentation, guardrails, and environment stability.

## No universal or production-readiness claim

The benchmark supports evidence about the checked-in scenarios and seeds. It does not establish universal superiority, zero harmful deployment, industrial reliability, or readiness to control irreversible systems.

## Artifact rule

Any numeric comparison in the README or technical report must link to a versioned result artifact containing configuration, seeds, metric definitions, and code version. If that artifact does not exist, the correct result is `Not evaluated`.
