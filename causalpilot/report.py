"""Render an analysis result as terminal text, Markdown and a PNG chart."""

from __future__ import annotations

import json
from pathlib import Path

CALL_LABEL = {"ship": "SHIP", "hold": "HOLD", "extend": "EXTEND"}


def _value(x: float, binary: bool) -> str:
    return f"{x * 100:.2f}%" if binary else f"{x:.4g}"


def _diff(x: float, binary: bool) -> str:
    return f"{x * 100:+.2f} pp" if binary else f"{x:+.4g}"


def _interval(low: float, high: float, binary: bool) -> str:
    return f"[{_diff(low, binary)}, {_diff(high, binary)}]"


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def _srm_line(srm: dict) -> str:
    parts = ", ".join(f"{g}: {n:,}" for g, n in srm["observed"].items())
    status = "OK" if srm["p_value"] >= 0.001 else "MISMATCH"
    return f"Sample ratio: {parts}  (chi-square {srm['chi_square']:.2f}, p = {srm['p_value']:.3g})  {status}"


def to_text(result: dict) -> str:
    s = result["settings"]
    lines = [
        f"{result.get('source', 'data')}: {result['rows']:,} rows, control = {s['control']}",
        _srm_line(result["srm"]),
        "",
    ]
    for comp in result["comparisons"]:
        lines.append(f"{comp['treatment']} vs {s['control']}")
        for m in comp["metrics"]:
            b = m["binary"]
            est = m["cuped"] or m["raw"]
            tag = "CUPED" if m["cuped"] else "raw"
            rel = f"  ({_pct(m['relative']['lift'])})" if m["relative"] else ""
            lines.append(
                f"  {m['metric']:<14} {_value(m['mean_control'], b):>10} -> {_value(m['mean_treatment'], b):<10}"
                f" {tag} {_diff(est['effect'], b)} {_interval(est['ci_low'], est['ci_high'], b)}"
                f"  p = {est['p_value']:.3g}{rel}"
            )
        v = comp["verdict"]
        lines.append(f"  -> {CALL_LABEL[v['call']]}: {v['headline']}")
        for reason in v["reasons"]:
            lines.append(f"     {reason}")
        lines.append("")
    for note in result["notes"]:
        lines.append(f"Note: {note}")
    return "\n".join(lines).rstrip() + "\n"


def to_markdown(result: dict, chart_name: str | None = None) -> str:
    s = result["settings"]
    srm = result["srm"]
    out = [f"# A/B test report: {result.get('source', 'data')}", ""]
    out.append(
        f"{result['rows']:,} rows. Control: **{s['control']}**. Primary metric: **{s['primary_metric']}**. "
        f"Smallest worthwhile lift: {s['min_lift'] * 100:g}% of the control mean. "
        f"Alpha: {s['alpha']}."
        + (f" Covariates for CUPED: {', '.join(s['covariates'])}." if s["covariates"] else "")
    )
    out.append("")
    out.append("## Verdict")
    out.append("")
    for comp in result["comparisons"]:
        v = comp["verdict"]
        out.append(f"**{comp['treatment']}: {CALL_LABEL[v['call']]}.** {v['headline']}")
        out.append("")
        for reason in v["reasons"]:
            out.append(f"- {reason}")
        out.append("")
    out.append("## Sample ratio check")
    out.append("")
    out.append("| Group | Users | Expected |")
    out.append("| --- | ---: | ---: |")
    for g, n in srm["observed"].items():
        out.append(f"| {g} | {n:,} | {srm['expected'][g]:,.0f} |")
    out.append("")
    verdict = "no evidence of a mismatch" if srm["p_value"] >= 0.001 else "**mismatch: fix this before reading the results**"
    out.append(f"Chi-square = {srm['chi_square']:.2f} on {srm['df']} df, p = {srm['p_value']:.3g}: {verdict}.")
    out.append("")
    if chart_name:
        out.append(f"![Effects with intervals]({chart_name})")
        out.append("")
    for comp in result["comparisons"]:
        out.append(f"## {comp['treatment']} vs {s['control']}")
        out.append("")
        has_cuped = any(m["cuped"] for m in comp["metrics"])
        header = "| Metric | Control | Treatment | Difference (95% CI) | p |"
        sep = "| --- | ---: | ---: | --- | ---: |"
        if has_cuped:
            header += " CUPED difference (CI) | Variance cut |"
            sep += " --- | ---: |"
        header += " Always-valid CI | Relative lift |"
        sep += " --- | ---: |"
        out.extend([header, sep])
        for m in comp["metrics"]:
            b = m["binary"]
            raw = m["raw"]
            row = (
                f"| {m['metric']} | {_value(m['mean_control'], b)} | {_value(m['mean_treatment'], b)} "
                f"| {_diff(raw['effect'], b)} {_interval(raw['ci_low'], raw['ci_high'], b)} | {raw['p_value']:.3g} |"
            )
            if has_cuped:
                c = m["cuped"]
                row += (
                    f" {_diff(c['effect'], b)} {_interval(c['ci_low'], c['ci_high'], b)} "
                    f"| {c['variance_reduction'] * 100:.1f}% |"
                )
            av = m["always_valid"]
            rel = m["relative"]
            rel_text = f"{_pct(rel['lift'])} [{_pct(rel['ci_low'])}, {_pct(rel['ci_high'])}]" if rel else "n/a"
            row += f" {_interval(av['ci_low'], av['ci_high'], b)} | {rel_text} |"
            out.append(row)
        out.append("")
        out.append(
            f"Users: {comp['metrics'][0]['n_treatment']:,} treatment, {comp['metrics'][0]['n_control']:,} control."
        )
        out.append("")
    out.append("## How to read this")
    out.append("")
    out.append(
        "- **Difference** is treatment minus control. For 0/1 metrics it is in percentage points (pp)."
    )
    out.append(
        "- **CUPED** subtracts the part of each user's metric that the pre-experiment covariates "
        "predict. The effect estimate stays unbiased and the interval gets narrower; the "
        "variance cut column says by how much."
    )
    out.append(
        "- **Always-valid CI** is wider on purpose: it stays correct even if you looked at the "
        "results every day. Use it (pass `--peeking`) if you did."
    )
    out.append("- The verdict uses the CUPED interval of the primary metric when covariates are given.")
    out.append("")
    if result["notes"]:
        out.append("## Notes")
        out.append("")
        for note in result["notes"]:
            out.append(f"- {note}")
        out.append("")
    return "\n".join(out)


def plot(result: dict, path: str | Path) -> None:
    """Relative lift of every metric with the fixed and the always-valid interval."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = result["settings"]
    rows = []
    for comp in result["comparisons"]:
        for m in comp["metrics"]:
            base = m["mean_control"]
            if base == 0:
                continue
            est = m["cuped"] or m["raw"]
            av = m["always_valid"]
            rows.append(
                (
                    f"{m['metric']}\n{comp['treatment']}",
                    est["effect"] / base,
                    est["ci_low"] / base,
                    est["ci_high"] / base,
                    av["ci_low"] / base,
                    av["ci_high"] / base,
                    comp["verdict"]["call"],
                )
            )
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(7.5, 0.75 * len(rows) + 1.4), dpi=150)
    colors = {"ship": "#1b7f3b", "hold": "#b3261e", "extend": "#9a6700"}
    for i, (label, eff, lo, hi, alo, ahi, call) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([alo * 100, ahi * 100], [y, y], color="#b0b0b0", linewidth=6, solid_capstyle="butt", zorder=1)
        ax.plot([lo * 100, hi * 100], [y, y], color=colors[call], linewidth=2.5, zorder=2)
        ax.plot([eff * 100], [y], "o", color=colors[call], zorder=3)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=8)
    ax.axvline(0, color="black", linewidth=0.8)
    for sign in (1, -1):
        ax.axvline(sign * s["min_lift"] * 100, color="#555555", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Lift relative to control mean (%)")
    tag = "CUPED-adjusted" if s["covariates"] else "unadjusted"
    ax.set_title(
        f"{result.get('source', '')}\n"
        f"coloured: {tag} {100 * (1 - s['alpha']):.0f}% interval (green ship, red hold, amber extend); "
        "grey: always-valid interval; dotted: smallest worthwhile lift",
        fontsize=8,
    )
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def write_all(result: dict, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    chart = out / "effects.png"
    plot(result, chart)
    md = out / "report.md"
    md.write_text(to_markdown(result, chart.name if chart.exists() else None), encoding="utf-8")
    js = out / "report.json"
    js.write_text(json.dumps(result, indent=2, default=float) + "\n", encoding="utf-8")
    return [p for p in (md, js, chart) if p.exists()]
