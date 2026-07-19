# Evaluation

> **Scope:** this is a controlled-simulation engineering benchmark. It validates
> executable policy gates, dynamic risk-index updates, and failure behavior. It is not
> a causal research conclusion and does not claim real-world business lift.

Run the deterministic benchmark from the repository root:

```bash
python evaluation/run_benchmark.py
```

The primary run uses 50 predeclared seeds (`0..49`). It writes row-level runs,
aggregate means with 95% intervals, full JSON, and a
Markdown table under `evaluation/results/`. The default benchmark uses seeded
potential outcomes, needs no API key, and makes no claim that a named LLM was
executed: `direct_proxy`, `react_like_proxy`, and `verbal_confidence` are disclosed
decision-rule proxies. `causalpilot_no_trace` holds the coordinator, experiment,
tools, and memory fixed while removing the four TRACE risk gates and maximizing
the point estimate.

Continuous-metric intervals use a percentile bootstrap over episode seeds
(2,000 resamples, fixed seed 20260719); proportions use Wilson score intervals,
so observing 0/50 harmful episodes does not produce a false `[0, 0]` interval.
Synthetic ground-truth metrics carry a
`_gt` suffix so they cannot be mistaken for surrogates available on real logs.

For a fast smoke check, explicitly choose a smaller seed set:

```bash
python evaluation/run_benchmark.py --seeds 11,23,37
```

## Optional real-data smoke checks

The official `st-tech/zr-obp` repository includes 10,000-row samples in each of
`obd/{random,bts}/{all,men,women}/{campaign}.csv`. Clone it outside this repository,
then parse a sample without copying the raw data here:

```bash
git clone --depth 1 https://github.com/st-tech/zr-obp.git ../zr-obp
python -c "from evaluation.adapters import summarize_open_bandit; print(summarize_open_bandit('../zr-obp/obd', 'random', 'all'))"
```

The optional Criteo adapter streams `criteo/criteo-uplift` only after an explicit
`pip install datasets`. That current unbiased release has 13,979,592 rows, about
297 MB compressed, and treatment ratio around 0.85. It must not be confused with
the older approximately 25M-row Criteo uplift release.
