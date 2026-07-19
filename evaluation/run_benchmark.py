"""CLI entry point that writes JSON, CSV, and Markdown evidence artifacts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from evaluation.benchmark import benchmark_metadata, evaluate_seed  # noqa: E402


METRICS = [
    "normalized_policy_value_gt",
    "policy_regret_gt",
    "false_deployment_rate_gt",
    "harmful_deployment_rate_gt",
    "constraint_violation_rate_gt",
    "coverage",
    "interval_coverage_gt",
    "post_shift_transfer_brier_gt",
    "post_shift_transfer_ece_gt",
    "experiment_samples",
    "human_questions",
]

PROPORTION_COUNTS = {
    "false_deployment_rate_gt": ("false_deployment_rate_gt", None),
    "harmful_deployment_rate_gt": ("harmful_deployments_gt", "deployment_count"),
    "constraint_violation_rate_gt": ("constraint_violations_gt", "deployment_count"),
    "interval_coverage_gt": ("interval_covered_gt", "interval_total"),
}


def _quantize_json(value):
    """Normalize numeric evidence so JSON is byte-stable across Python/NumPy builds."""
    if isinstance(value, dict):
        return {key: _quantize_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_quantize_json(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("JSON evidence contains a non-finite number")
        quantized = float(f"{number:.8f}")
        return 0.0 if quantized == 0 else quantized
    return value


def wilson_interval(successes: float, trials: float, z_score: float = 1.959963984540054) -> tuple[float, float]:
    if not all(math.isfinite(value) for value in (successes, trials, z_score)):
        raise ValueError("Wilson inputs must be finite")
    if z_score <= 0:
        raise ValueError("z_score must be positive")
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("Wilson counts require 0 <= successes <= trials")
    if trials == 0:
        return 0.0, 1.0
    proportion = successes / trials
    denominator = 1.0 + z_score**2 / trials
    center = (proportion + z_score**2 / (2.0 * trials)) / denominator
    radius = (
        z_score
        * ((proportion * (1.0 - proportion) / trials + z_score**2 / (4.0 * trials**2)) ** 0.5)
        / denominator
    )
    lower = max(0.0, center - radius)
    upper = min(1.0, center + radius)
    if abs(lower) < 1e-15:
        lower = 0.0
    if abs(1.0 - upper) < 1e-15:
        upper = 1.0
    return lower, upper


def summarize(
    runs: pd.DataFrame,
    bootstrap_seed: int = 20_260_719,
    bootstrap_resamples: int = 2_000,
) -> pd.DataFrame:
    """Seed bootstrap for continuous metrics and Wilson intervals for proportions."""
    if not isinstance(bootstrap_resamples, int) or bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples must be a positive integer")
    seed_order = sorted(int(seed) for seed in runs["seed"].unique())
    if not seed_order:
        raise ValueError("Cannot summarize an empty benchmark")
    rng = np.random.default_rng(bootstrap_seed)
    resample_indices = rng.integers(
        0, len(seed_order), size=(bootstrap_resamples, len(seed_order))
    )
    records: list[dict[str, object]] = []
    for method, group in runs.groupby("method", sort=True):
        group = group.set_index("seed").loc[seed_order].reset_index()
        record: dict[str, object] = {
            "method": method,
            "method_type": group["method_type"].iloc[0],
            "runs": len(group),
        }
        for metric in METRICS:
            if metric in PROPORTION_COUNTS:
                numerator_column, denominator_column = PROPORTION_COUNTS[metric]
                successes = float(group[numerator_column].sum())
                trials = float(len(group) if denominator_column is None else group[denominator_column].sum())
                low, high = wilson_interval(successes, trials)
                record[f"{metric}_mean"] = successes / trials if trials else 0.0
                record[f"{metric}_ci95_low"] = low
                record[f"{metric}_ci95_high"] = high
                record[f"{metric}_trials"] = int(trials)
            else:
                values = group[metric].astype(float)
                bootstrap_means = values.to_numpy()[resample_indices].mean(axis=1)
                record[f"{metric}_mean"] = float(values.mean())
                record[f"{metric}_ci95_low"] = float(np.quantile(bootstrap_means, 0.025))
                record[f"{metric}_ci95_high"] = float(np.quantile(bootstrap_means, 0.975))
        records.append(record)
    return pd.DataFrame(records)


def markdown_report(metadata: dict[str, object], summary: pd.DataFrame) -> str:
    columns = [
        "method",
        "normalized_policy_value_gt_mean",
        "policy_regret_gt_mean",
        "false_deployment_rate_gt_mean",
        "constraint_violation_rate_gt_mean",
        "coverage_mean",
        "experiment_samples_mean",
        "human_questions_mean",
    ]
    display = summary[columns].copy()
    display.columns = [
        "Method",
        "Normalized value",
        "Regret",
        "False deploy",
        "Constraint violation",
        "Coverage",
        "Experiment n",
        "Human asks",
    ]
    for column in [
        "Normalized value",
        "Regret",
        "False deploy",
        "Constraint violation",
        "Coverage",
    ]:
        display[column] = display[column].map(lambda value: f"{value:.4f}")
    display["Experiment n"] = display["Experiment n"].map(lambda value: f"{value:.0f}")
    display["Human asks"] = display["Human asks"].map(lambda value: f"{value:.1f}")
    header = "| " + " | ".join(display.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in display.itertuples(index=False, name=None)
    ]
    seeds = ", ".join(str(seed) for seed in metadata["seeds"])
    return "\n".join(
        [
            "# CausalPilot benchmark results",
            "",
            f"Seeds: {seeds}. All values below are computed outputs, not hand-written claims.",
            "",
            f"> Disclosure: {metadata['llm_baseline_disclosure']}",
            "",
            f"> Scope: {metadata['claim_scope']}",
            f"> Evidence: `{metadata['evidence_mode']}` · fixture `{metadata['fixture_version']}` "
            f"(`{metadata['fixture_hash']}`) · split `{metadata['split']}`.",
            "",
            header,
            separator,
            *rows,
            "",
            "Normalized value counts only value from constraint-feasible oracle segments under "
            "known synthetic post-shift ground truth. Confidence intervals for every summary "
            "metric are available in `summary.csv` and `results.json`. Binary and count-based "
            "proportions use Wilson intervals; continuous metrics use seed bootstrap intervals.",
            "",
        ]
    )


def run(seeds: list[int], output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not seeds or any(seed < 0 for seed in seeds):
        raise ValueError("seeds must contain at least one non-negative integer")
    if len(seeds) != len(set(seeds)):
        raise ValueError("seeds must not contain duplicates")
    rows = [row for seed in seeds for row in evaluate_seed(seed)]
    runs = pd.DataFrame(rows).sort_values(["method", "seed"]).reset_index(drop=True)
    summary = summarize(runs)
    metadata = benchmark_metadata(seeds)
    output_dir.mkdir(parents=True, exist_ok=True)
    runs.to_csv(output_dir / "runs.csv", index=False, float_format="%.8f")
    summary.to_csv(output_dir / "summary.csv", index=False, float_format="%.8f")
    payload = _quantize_json({
        "metadata": metadata,
        "summary": summary.to_dict(orient="records"),
        "runs": runs.to_dict(orient="records"),
    })
    (output_dir / "results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_dir / "RESULTS.md").write_text(
        markdown_report(metadata, summary), encoding="utf-8"
    )
    return runs, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds",
        default=",".join(str(seed) for seed in range(50)),
        help="Comma-separated non-negative integers (default primary benchmark: 0..49)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "results",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    if not seeds or any(seed < 0 for seed in seeds):
        raise SystemExit("--seeds must contain at least one non-negative integer")
    if len(seeds) != len(set(seeds)):
        raise SystemExit("--seeds must not contain duplicates")
    runs, summary = run(seeds, args.output_dir)
    trace_row = summary.loc[summary["method"] == "trace"].iloc[0]
    print(
        f"wrote {len(runs)} runs across {len(summary)} methods to {args.output_dir}; "
            f"TRACE regret={trace_row['policy_regret_gt_mean']:.6f}, "
            f"false-deployment={trace_row['false_deployment_rate_gt_mean']:.3f}"
    )


if __name__ == "__main__":
    main()
