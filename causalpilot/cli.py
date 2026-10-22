"""Command line: `causalpilot analyze`, `causalpilot hillstrom`, `causalpilot simulate`."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, hillstrom
from .analysis import Settings, analyze_csv
from .report import to_text, write_all


def _add_analysis_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--alpha", type=float, default=0.05, help="significance level (default 0.05)")
    p.add_argument(
        "--min-lift",
        type=float,
        default=None,
        help="smallest relative lift of the primary metric worth shipping, e.g. 0.02 for 2%% (default 0.01)",
    )
    p.add_argument("--peeking", action="store_true", help="you checked results repeatedly: use always-valid intervals")
    p.add_argument("--planned-n", type=int, help="total users you planned for; tunes the always-valid interval")
    p.add_argument("--max-extend", type=float, default=4.0, help="largest sample multiple worth waiting for (default 4)")
    p.add_argument("--out", help="folder for report.md, report.json and effects.png")
    p.add_argument("--json", action="store_true", help="print the full result as JSON instead of text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="causalpilot",
        description="Read an A/B test export and say whether to ship, hold or keep the test running.",
    )
    parser.add_argument("--version", action="version", version=f"causalpilot {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="analyze a CSV with one row per user")
    a.add_argument("csv", help="path to the CSV file")
    a.add_argument("--group", required=True, help="column holding the arm / variant name")
    a.add_argument("--control", required=True, help="value of --group that marks the control arm")
    a.add_argument("--treatment", action="append", help="treatment arm(s) to compare; default: all others")
    a.add_argument("--metric", action="append", required=True, help="outcome column; the first one decides")
    a.add_argument("--covariate", action="append", default=[], help="pre-experiment column for CUPED")
    a.add_argument(
        "--guardrail",
        action="append",
        default=[],
        help="metric that must not get worse; higher is better unless you add :lower, e.g. refunded:lower",
    )
    a.add_argument("--split", help='planned split, e.g. "50:50" (control first) or "control=1,treatment=1"')
    _add_analysis_options(a)

    h = sub.add_parser("hillstrom", help="download the MineThatData e-mail test and analyze it")
    h.add_argument("--cache", help="download folder (default ~/.cache/causalpilot)")
    _add_analysis_options(h)

    s = sub.add_parser("simulate", help="write a synthetic experiment with a known effect to CSV")
    s.add_argument("csv", help="output path")
    s.add_argument("--n", type=int, default=60_000, help="number of users (default 60000)")
    s.add_argument("--lift", type=float, default=0.08, help="true relative lift in conversion (default 0.08)")
    s.add_argument("--seed", type=int, default=7)
    s.add_argument("--lost-bounces", type=float, default=0.0, help="fraction of non-converting treatment users lost")
    return parser


def _settings(args: argparse.Namespace, **fields) -> Settings:
    min_lift = args.min_lift if args.min_lift is not None else fields.pop("min_lift", 0.01)
    fields.pop("min_lift", None)
    return Settings(
        alpha=args.alpha,
        min_lift=min_lift,
        peeking=args.peeking,
        planned_n=args.planned_n,
        max_extend=args.max_extend,
        **fields,
    )


def _emit(result: dict, args: argparse.Namespace) -> None:
    if args.json:
        print(json.dumps(result, indent=2, default=float))
    else:
        print(to_text(result), end="")
    if args.out:
        written = write_all(result, args.out)
        print(f"Wrote {', '.join(str(p) for p in written)}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            settings = _settings(
                args,
                group=args.group,
                control=args.control,
                treatments=args.treatment,
                metrics=args.metric,
                covariates=args.covariate,
                guardrails=args.guardrail,
                split=args.split,
            )
            _emit(analyze_csv(args.csv, settings), args)
        elif args.command == "hillstrom":
            path = hillstrom.fetch(args.cache)
            settings = _settings(args, **hillstrom.ANALYSIS)
            result = analyze_csv(path, settings)
            result["source"] = "Hillstrom MineThatData e-mail test (2008)"
            _emit(result, args)
        elif args.command == "simulate":
            from .simulate import simulate

            frame = simulate(n=args.n, true_lift=args.lift, seed=args.seed, lost_treatment_bounces=args.lost_bounces)
            frame.to_csv(args.csv, index=False)
            print(f"Wrote {len(frame):,} rows to {args.csv} (true lift {args.lift:+.1%}, synthetic data)")
    except (ValueError, OSError, RuntimeError) as error:
        print(f"causalpilot: error: {error}", file=sys.stderr)
        return 2
    return 0
