# Run and verify the benchmark

The headless benchmark compares policies on predeclared, seeded simulator
episodes. It writes inspectable row-level data before any prose claim.

## Install the evaluator

```bash
python -m pip install -e "backend[test]"
```

No frontend dependency or API key is required.

## Run a smoke check

Use a separate output directory so the smoke check cannot overwrite canonical
artifacts:

```bash
python evaluation/run_benchmark.py \
  --seeds 11,23,37 \
  --output-dir .cache/benchmark-smoke
```

This command checks execution, not a publishable comparison.

## Run the canonical seed suite

```bash
python evaluation/run_benchmark.py
```

The default command uses the primary predeclared seed suite. Do not replace it
with a favorable subset when publishing a result.

## Inspect generated artifacts

The command writes these **GENERATED** files under `evaluation/results/`:

| File | Contents |
| --- | --- |
| `runs.csv` | One row per policy and seed |
| `summary.csv` | Aggregate metrics and uncertainty intervals |
| `results.json` | Metadata, summaries, and row-level records |
| `RESULTS.md` | Compact reader-facing table and scope disclosure |

Inspect `results.json` before quoting any number. Confirm the seed list, policy
disclosures, claim scope, and metric names.

## Verify deterministic regeneration

Start from a clean checkout, run the canonical command, then check:

```bash
git diff --exit-code -- evaluation/results
```

No diff means the checked-in artifacts match the current code and environment.
A diff requires review; do not discard it merely to make CI pass.

For a byte-level comparison outside Git:

```bash
python evaluation/run_benchmark.py --output-dir .cache/reproduction
```

Compare files only after confirming that both runs used the same code,
configuration, dependency environment, and seed list.

## Interpret metrics

Metrics ending in `_gt` use hidden synthetic ground truth and exist only for
controlled-simulation scoring. They are not runtime observations and must not
appear as production telemetry.

For proportions, inspect both the point estimate and its interval. Observing no
failures in a finite run does not prove a zero failure probability. For policy
comparisons, prefer paired per-seed differences when the report provides them.

## Update reader-facing assets

After the canonical artifacts pass review, regenerate the Markdown, figure, and
paper macros with the checked-in asset script:

```bash
python scripts/generate_result_assets.py
```

Treat `docs/generated_results.md`,
`docs/assets/benchmark-risk-coverage.svg`, and `paper/results_macros.tex` as
**GENERATED**. Never type replacement values into them by hand.

## Optional dataset smoke checks

The benchmark's default path uses no external data. Optional adapter commands
and their evidence limits are documented in `evaluation/README.md`. Keep raw
downloads outside Git and verify each source's current license before use.
