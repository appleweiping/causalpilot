# CausalPilot benchmark results

Seeds: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49. All values below are computed outputs, not hand-written claims.

> Disclosure: direct_proxy, react_like_proxy, verbal_confidence, and causalpilot_no_trace are deterministic decision-rule proxies; they are not executions of a named language model.

> Scope: Controlled-simulation engineering benchmark only. These results validate executable gates and failure behavior; they are not a causal research conclusion or real-world lift claim.
> Evidence: `simulated_scm` · fixture `causalpilot-synthetic-fashion-v1` (`1cd2565ad964416b`) · split `paired_seeded_episodes`.

| Method | Normalized value | Regret | False deploy | Constraint violation | Coverage | Experiment n | Human asks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| always_ask_human | 0.0000 | 0.0170 | 0.0000 | 0.0000 | 0.0000 | 0 | 1.0 |
| always_deploy | 1.0000 | 0.0099 | 1.0000 | 0.6200 | 1.0000 | 0 | 0.0 |
| causalpilot_no_trace | 1.0000 | 0.0031 | 0.7600 | 0.4933 | 0.8000 | 9000 | 0.0 |
| direct_proxy | 0.9851 | 0.0037 | 0.7200 | 0.4897 | 0.7710 | 0 | 0.0 |
| fixed_pipeline | 0.8642 | 0.0042 | 0.5800 | 0.4715 | 0.6570 | 9000 | 0.0 |
| react_like_proxy | 1.0000 | 0.0031 | 0.7600 | 0.4933 | 0.8000 | 9000 | 0.0 |
| trace | 0.6670 | 0.0065 | 0.0400 | 0.0426 | 0.2580 | 9000 | 1.9 |
| trace_no_dynamic_calibration | 0.4367 | 0.0107 | 0.3800 | 0.3878 | 0.2670 | 9000 | 1.0 |
| trace_no_experiment | 0.0000 | 0.0170 | 0.0000 | 0.0000 | 0.0000 | 0 | 1.9 |
| trace_no_human_query | 0.4870 | 0.0087 | 0.0400 | 0.2653 | 0.2610 | 9000 | 0.0 |
| trace_static_threshold | 0.9728 | 0.0035 | 0.7400 | 0.4966 | 0.7740 | 9000 | 0.0 |
| verbal_confidence | 0.9851 | 0.0037 | 0.7200 | 0.4897 | 0.7710 | 0 | 0.0 |

Normalized value counts only value from constraint-feasible oracle segments under known synthetic post-shift ground truth. Confidence intervals for every summary metric are available in `summary.csv` and `results.json`. Binary and count-based proportions use Wilson intervals; continuous metrics use seed bootstrap intervals.
