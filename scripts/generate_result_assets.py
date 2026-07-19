"""Generate checked-in visual and paper snippets from benchmark artifacts.

This script intentionally uses only the Python standard library. It never invents
numbers: missing methods or columns are fatal, and every output names its source.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evaluation" / "results" / "summary.csv"
SVG_OUT = ROOT / "docs" / "assets" / "benchmark-risk-coverage.svg"
MARKDOWN_OUT = ROOT / "docs" / "generated_results.md"
TEX_OUT = ROOT / "paper" / "results_macros.tex"

METHODS = [
    ("trace", "TRACE", "#73fbd3"),
    ("causalpilot_no_trace", "No TRACE", "#ffb454"),
    ("fixed_pipeline", "Fixed pipeline", "#a58cff"),
    ("direct_proxy", "Direct proxy", "#ff6b8a"),
    ("always_deploy", "Always deploy", "#ff4d5f"),
    ("always_ask_human", "Always escalate", "#83a8ff"),
]


def load_rows() -> dict[str, dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = {row["method"]: row for row in csv.DictReader(handle)}
    missing = [method for method, _, _ in METHODS if method not in rows]
    if missing:
        raise KeyError(f"Missing benchmark methods: {missing}")
    required = {
        "runs",
        "coverage_mean",
        "false_deployment_rate_gt_mean",
        "false_deployment_rate_gt_ci95_low",
        "false_deployment_rate_gt_ci95_high",
        "policy_regret_gt_mean",
        "policy_regret_gt_ci95_low",
        "policy_regret_gt_ci95_high",
        "constraint_violation_rate_gt_mean",
    }
    absent = required.difference(next(iter(rows.values())))
    if absent:
        raise KeyError(f"Missing benchmark columns: {sorted(absent)}")
    return rows


def make_svg(rows: dict[str, dict[str, str]]) -> str:
    width, height = 1040, 600
    left, top, plot_w, plot_h = 112, 78, 760, 420

    def point(coverage: float, false_deploy: float) -> tuple[float, float]:
        return left + coverage * plot_w, top + (1.0 - false_deploy) * plot_h

    trace = rows["trace"]
    trace_runs = int(float(trace["runs"]))
    trace_false_rate = float(trace["false_deployment_rate_gt_mean"])
    trace_false_count = round(trace_runs * trace_false_rate)
    trace_coverage = float(trace["coverage_mean"])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>Safety versus deployment coverage in the {trace_runs}-seed synthetic engineering benchmark</title>",
        f"<desc>TRACE has {trace_false_count} false-deployment episodes in {trace_runs} controlled episodes at {trace_coverage:.0%} mean coverage. Deterministic proxies cover more opportunities but make more unsafe deployments. This is simulated evidence, not a live result.</desc>",
        "<defs><radialGradient id=\"bg\"><stop stop-color=\"#18243b\"/><stop offset=\"1\" stop-color=\"#070b14\"/></radialGradient><filter id=\"glow\"><feGaussianBlur stdDeviation=\"4\" result=\"b\"/><feMerge><feMergeNode in=\"b\"/><feMergeNode in=\"SourceGraphic\"/></feMerge></filter></defs>",
        f'<rect width="{width}" height="{height}" rx="28" fill="url(#bg)"/>',
        '<text x="54" y="42" fill="#f4f7ff" font-family="Inter,Segoe UI,sans-serif" font-size="22" font-weight="700">Safety–coverage mechanism check</text>',
        f'<text x="54" y="66" fill="#8f9db5" font-family="Inter,Segoe UI,sans-serif" font-size="13">{trace_runs} seeds · {sum(int(float(row["runs"])) for row in rows.values())} deterministic policy runs · simulated ground truth</text>',
    ]
    for tick in range(6):
        value = tick / 5
        x = left + value * plot_w
        y = top + (1 - value) * plot_h
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" stroke="#233149" stroke-width="1"/>')
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#233149" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_h + 24}" text-anchor="middle" fill="#8390a6" font-family="Inter,Segoe UI,sans-serif" font-size="12">{value:.1f}</text>')
        parts.append(f'<text x="{left - 18}" y="{y + 4:.1f}" text-anchor="end" fill="#8390a6" font-family="Inter,Segoe UI,sans-serif" font-size="12">{value:.1f}</text>')
    parts.extend(
        [
            f'<text x="{left + plot_w / 2:.1f}" y="{height - 36}" text-anchor="middle" fill="#b9c4d7" font-family="Inter,Segoe UI,sans-serif" font-size="14">Mean deployment coverage →</text>',
            f'<text x="28" y="{top + plot_h / 2:.1f}" transform="rotate(-90 28 {top + plot_h / 2:.1f})" text-anchor="middle" fill="#b9c4d7" font-family="Inter,Segoe UI,sans-serif" font-size="14">False-deployment episode rate →</text>',
        ]
    )
    label_offsets = {
        "trace": (14, -10),
        "causalpilot_no_trace": (14, 23),
        "fixed_pipeline": (-14, -16),
        "direct_proxy": (-14, 22),
        "always_deploy": (-14, -14),
        "always_ask_human": (14, -8),
    }
    for method, label, color in METHODS:
        row = rows[method]
        coverage = float(row["coverage_mean"])
        false_deploy = float(row["false_deployment_rate_gt_mean"])
        x, y = point(coverage, false_deploy)
        dx, dy = label_offsets[method]
        anchor = "end" if dx < 0 else "start"
        radius = 13 if method == "trace" else 9
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{color}" fill-opacity="0.18" stroke="{color}" stroke-width="3" filter="url(#glow)"/>')
        parts.append(f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" fill="{color}" font-family="Inter,Segoe UI,sans-serif" font-size="13" font-weight="700">{html.escape(label)}</text>')
        parts.append(f'<text x="{x + dx:.1f}" y="{y + dy + 16:.1f}" text-anchor="{anchor}" fill="#8795ab" font-family="Inter,Segoe UI,sans-serif" font-size="11">coverage {coverage:.0%} · false deploy {false_deploy:.0%}</text>')
    parts.extend(
        [
            '<rect x="892" y="88" width="120" height="92" rx="12" fill="#0c1321" stroke="#26354f"/>',
            '<text x="908" y="113" fill="#73fbd3" font-family="Inter,Segoe UI,sans-serif" font-size="12" font-weight="700">TRACE</text>',
            f'<text x="908" y="136" fill="#f4f7ff" font-family="Inter,Segoe UI,sans-serif" font-size="22" font-weight="700">{trace_false_count} / {trace_runs}</text>',
            '<text x="908" y="156" fill="#8997ad" font-family="Inter,Segoe UI,sans-serif" font-size="11">false-deploy episodes</text>',
            '<text x="54" y="568" fill="#718097" font-family="Inter,Segoe UI,sans-serif" font-size="11">Controlled-simulation engineering benchmark. Proxies are decision rules, not executions of named LLMs. Source: evaluation/results.</text>',
            "</svg>",
        ]
    )
    return "".join(parts)


def make_markdown(rows: dict[str, dict[str, str]]) -> str:
    trace = rows["trace"]
    no_trace = rows["causalpilot_no_trace"]
    fixed = rows["fixed_pipeline"]
    return f"""# Generated benchmark summary

> Generated by `scripts/generate_result_assets.py` from `evaluation/results/summary.csv`. Do not edit numeric values by hand.

This is a **controlled synthetic mechanism check**, not evidence from a live customer experiment. Across {int(float(trace['runs']))} paired seeds:

- TRACE produced a false-deployment episode rate of **{float(trace['false_deployment_rate_gt_mean']):.0%}** (Wilson 95% CI {float(trace['false_deployment_rate_gt_ci95_low']):.1%}–{float(trace['false_deployment_rate_gt_ci95_high']):.1%}) at **{float(trace['coverage_mean']):.0%}** mean deployment coverage.
- The no-TRACE point-estimate policy produced **{float(no_trace['false_deployment_rate_gt_mean']):.0%}** false-deployment episodes (Wilson 95% CI {float(no_trace['false_deployment_rate_gt_ci95_low']):.1%}–{float(no_trace['false_deployment_rate_gt_ci95_high']):.1%}) at **{float(no_trace['coverage_mean']):.0%}** coverage.
- The fixed causal pipeline produced **{float(fixed['false_deployment_rate_gt_mean']):.0%}** false-deployment episodes (Wilson 95% CI {float(fixed['false_deployment_rate_gt_ci95_low']):.1%}–{float(fixed['false_deployment_rate_gt_ci95_high']):.1%}) at **{float(fixed['coverage_mean']):.0%}** coverage.
- TRACE mean ground-truth regret was **{float(trace['policy_regret_gt_mean']):.4f}** (95% CI {float(trace['policy_regret_gt_ci95_low']):.4f}–{float(trace['policy_regret_gt_ci95_high']):.4f}).

Because coverage differs, these point comparisons do **not** establish superiority at matched coverage. They verify the intended safety/coverage trade-off under the checked-in simulator. See the raw runs and all 12 methods in [`evaluation/results`](../evaluation/results/RESULTS.md).
"""


def make_tex(rows: dict[str, dict[str, str]]) -> str:
    trace = rows["trace"]
    no_trace = rows["causalpilot_no_trace"]
    fixed = rows["fixed_pipeline"]
    direct = rows["direct_proxy"]
    always_deploy = rows["always_deploy"]
    always_ask = rows["always_ask_human"]
    no_dynamic = rows["trace_no_dynamic_calibration"]
    no_human = rows["trace_no_human_query"]
    no_experiment = rows["trace_no_experiment"]

    def percent(row: dict[str, str], key: str, digits: int = 0) -> str:
        return f"{100 * float(row[key]):.{digits}f}\\%"

    def number(row: dict[str, str], key: str, digits: int = 4) -> str:
        return f"{float(row[key]):.{digits}f}"

    values = {
        "TraceRuns": f"{int(float(trace['runs']))}",
        "TraceFalseDeployCount": f"{round(float(trace['runs']) * float(trace['false_deployment_rate_gt_mean']))}",
        "TraceFalseDeploy": percent(trace, "false_deployment_rate_gt_mean"),
        "TraceFalseDeployLow": percent(trace, "false_deployment_rate_gt_ci95_low", 1),
        "TraceFalseDeployHigh": percent(trace, "false_deployment_rate_gt_ci95_high", 1),
        "TraceCoverage": percent(trace, "coverage_mean"),
        "TraceRegret": number(trace, "policy_regret_gt_mean"),
        "NoTraceFalseDeploy": percent(no_trace, "false_deployment_rate_gt_mean"),
        "NoTraceCoverage": percent(no_trace, "coverage_mean"),
        "NoTraceRegret": number(no_trace, "policy_regret_gt_mean"),
        "FixedFalseDeploy": percent(fixed, "false_deployment_rate_gt_mean"),
        "FixedCoverage": percent(fixed, "coverage_mean"),
        "FixedRegret": number(fixed, "policy_regret_gt_mean"),
        "DirectFalseDeploy": percent(direct, "false_deployment_rate_gt_mean"),
        "DirectCoverage": percent(direct, "coverage_mean"),
        "DirectRegret": number(direct, "policy_regret_gt_mean"),
        "AlwaysDeployFalseDeploy": percent(always_deploy, "false_deployment_rate_gt_mean"),
        "AlwaysDeployCoverage": percent(always_deploy, "coverage_mean"),
        "AlwaysDeployRegret": number(always_deploy, "policy_regret_gt_mean"),
        "AlwaysAskFalseDeploy": percent(always_ask, "false_deployment_rate_gt_mean"),
        "AlwaysAskCoverage": percent(always_ask, "coverage_mean"),
        "AlwaysAskRegret": number(always_ask, "policy_regret_gt_mean"),
        "NoDynamicFalseDeploy": percent(no_dynamic, "false_deployment_rate_gt_mean"),
        "NoHumanFalseDeploy": percent(no_human, "false_deployment_rate_gt_mean"),
        "NoHumanConstraintViolation": percent(no_human, "constraint_violation_rate_gt_mean", 1),
        "NoExperimentCoverage": percent(no_experiment, "coverage_mean"),
        "NoExperimentRegret": number(no_experiment, "policy_regret_gt_mean"),
    }
    lines = ["% Generated from evaluation/results/summary.csv; do not edit."]
    lines.extend(f"\\newcommand{{\\{key}}}{{{value}}}" for key, value in values.items())
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = load_rows()
    SVG_OUT.parent.mkdir(parents=True, exist_ok=True)
    TEX_OUT.parent.mkdir(parents=True, exist_ok=True)
    SVG_OUT.write_text(make_svg(rows), encoding="utf-8")
    MARKDOWN_OUT.write_text(make_markdown(rows), encoding="utf-8")
    TEX_OUT.write_text(make_tex(rows), encoding="utf-8")
    print(f"generated {SVG_OUT.relative_to(ROOT)}, {MARKDOWN_OUT.relative_to(ROOT)}, {TEX_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
