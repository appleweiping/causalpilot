# Contributing to CausalPilot

CausalPilot treats reproducibility and claim discipline as product features. A
change is complete when another contributor can run it, inspect its evidence,
and understand its limits.

## Set up the repository

Use Python 3.11 or newer, Node.js 22, and npm. The setup scripts create a local
Python environment and install the exact frontend dependency graph from
`frontend/package-lock.json`.

```powershell
# Windows PowerShell
.\scripts\setup.ps1
```

```bash
# macOS or Linux
./scripts/setup.sh
```

## Run checks

Run the same checks as CI before opening a pull request:

```bash
python -m pytest backend/tests evaluation/tests
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

`make check` runs the same group when GNU Make is available.

## Preserve the evidence boundary

- Keep deployment gates and statistical calculations deterministic and tested.
- Keep hidden simulator truth inside the evaluator. Runtime policies may read
  only observations that the API exposes.
- Label simulator-only scorer metrics with `_gt`.
- Never hand-edit generated benchmark values into prose. Regenerate the checked-in
  artifacts, then link to them.
- Describe LLM-shaped baselines as proxies unless the run actually calls and
  records a named model.
- Add a regression test when changing an action gate, state transition, metric,
  or data adapter.

For a quick check, run:

```bash
python evaluation/run_benchmark.py --seeds 11,23,37 --output-dir .cache/benchmark-smoke
```

Run the canonical benchmark before changing published results:

```bash
python evaluation/run_benchmark.py
```

The canonical output under `evaluation/results/` is **GENERATED**. Review the
configuration and row-level records with the summary.

## Protect data and credentials

The repository needs no API key for its default demo or benchmark. Do not commit
tokens, private keys, raw third-party datasets, personal data, or proprietary
logs. Keep local datasets under `data/raw/` or outside the repository. Follow
the source dataset's license and terms.

Report security issues through the private process in [SECURITY.md](SECURITY.md).

## Submit a focused change

1. Create a short-lived branch.
2. Keep unrelated formatting and generated-file changes out of the patch.
3. Update tests and the relevant page under `docs/`.
4. Run the checks above.
5. Explain the user-visible change, evidence impact, and remaining limits in the
   pull request.

By contributing, you agree that your contribution may be distributed under the
repository's MIT license.
