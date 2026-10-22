# Changelog

## 0.2.0 (2026-10-22)

Rewritten as a practical A/B test checker.

- `causalpilot analyze`: sample ratio test, difference in means, CUPED, always-valid
  intervals for peeking, guardrails, and a ship / hold / extend call with reasons.
- `causalpilot hillstrom`: downloads and analyzes the MineThatData e-mail experiment.
- `causalpilot simulate` and `benchmark/run_benchmark.py`: synthetic experiments with a
  known effect, built on the four-segment simulator from 0.1.0.
- Browser version on GitHub Pages, checked against the Python numbers in CI.
- Removed the FastAPI state machine, the Next.js 3D control room, the paper and the
  rule-based "LLM" baselines.

## 0.1.0 (2026-07-19)

Simulated experimentation "agent" with a 3D control room (see commit `2ceff2b`).
