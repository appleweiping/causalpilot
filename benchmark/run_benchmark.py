"""How often does each decision rule ship, on simulated tests with a known answer?

Five scenarios, 200 simulated experiments each (40,000 users over 14 days, true
effect known). The smallest lift worth shipping is set to 10%, which this sample
size can detect with roughly 90% power. Four ways of deciding:

  p<0.05, one look      ship if the unadjusted test is significant and positive on day 14
  p<0.05, daily looks   check every day, ship on the first significant positive day
  causalpilot, one look the ship/hold/extend rule on day 14 (SRM check + CUPED)
  causalpilot, daily    the same rule every day with --peeking (always-valid
                        intervals); stop on the first ship or hold

Run:  python benchmark/run_benchmark.py            (about 10 minutes on one core)
      python benchmark/run_benchmark.py --runs 20  (quick check)
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from causalpilot import stats  # noqa: E402
from causalpilot.decide import decide  # noqa: E402
from causalpilot.simulate import simulate  # noqa: E402

N_USERS = 40_000
DAYS = 14
MIN_LIFT = 0.10
ALPHA = 0.05

SCENARIOS = [
    ("harmful (-10%)", -0.10, 0.0),
    ("no effect", 0.0, 0.0),
    ("too small (+3%)", 0.03, 0.0),
    ("worthwhile (+15%)", 0.15, 0.0),
    ("no effect + logging bug", 0.0, 0.08),
]
RULES = ["p<0.05, one look", "p<0.05, daily looks", "causalpilot, one look", "causalpilot, daily (--peeking)"]


def causalpilot_call(y_t, y_c, x_t, x_c, peeking: bool, final: bool = True) -> str:
    srm = stats.sample_ratio_test({"t": y_t.size, "c": y_c.size}, {"t": 1.0, "c": 1.0})
    est = stats.cuped(y_t, y_c, x_t, x_c, ALPHA).estimate
    low, high = est.ci_low, est.ci_high
    if peeking:
        low, high = stats.always_valid_interval(est, y_t.size + y_c.size, ALPHA, planned_n=N_USERS)
    min_effect = MIN_LIFT * y_c.mean()
    return decide(
        metric="converted",
        effect=est.effect,
        ci_low=low,
        ci_high=high,
        min_effect=min_effect,
        srm_p=srm.p_value,
        sample_factor=stats.sample_size_factor(est.se, min_effect, ALPHA),
        # Before the planned end an inconclusive interval means "keep going".
        max_extend=4.0 if final else float("inf"),
    ).call


def naive_ship(y_t, y_c) -> bool:
    est = stats.difference_in_means(y_t, y_c, ALPHA)
    return est.p_value < ALPHA and est.effect > 0


def run_episode(true_lift: float, lost: float, seed: int) -> dict[str, tuple[str, int]]:
    frame = simulate(n=N_USERS, true_lift=true_lift, seed=seed, days=DAYS, lost_treatment_bounces=lost)
    day = frame["day"].to_numpy()
    treated = (frame["arm"] == "treatment").to_numpy()
    y = frame["converted"].to_numpy(dtype=float)
    x = frame["prior_orders"].to_numpy(dtype=float)
    ends = np.searchsorted(day, np.arange(1, DAYS + 1), side="right")  # frame is sorted by day

    def arms(end):
        t, yy, xx = treated[:end], y[:end], x[:end]
        return yy[t], yy[~t], xx[t], xx[~t]

    out = {}
    y_t, y_c, x_t, x_c = arms(ends[-1])
    out[RULES[0]] = ("ship" if naive_ship(y_t, y_c) else "no ship", DAYS)
    out[RULES[2]] = (causalpilot_call(y_t, y_c, x_t, x_c, peeking=False), DAYS)

    out[RULES[1]] = ("no ship", DAYS)
    for d, end in enumerate(ends, start=1):
        y_t, y_c, _, _ = arms(end)
        if naive_ship(y_t, y_c):
            out[RULES[1]] = ("ship", d)
            break

    for d, end in enumerate(ends, start=1):
        call = causalpilot_call(*arms(end), peeking=True, final=d == DAYS)
        if call in ("ship", "hold") or d == DAYS:
            out[RULES[3]] = (call, d)
            break
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=200, help="simulated experiments per scenario")
    parser.add_argument("--out", default=str(ROOT / "benchmark"), help="folder for results.csv and results.md")
    args = parser.parse_args()

    started = time.time()
    rows = []
    for name, lift, lost in SCENARIOS:
        tallies = {rule: {"ship": 0, "hold": 0, "extend": 0, "no ship": 0, "days": 0} for rule in RULES}
        for seed in range(args.runs):
            for rule, (call, days) in run_episode(lift, lost, 10_000 + seed).items():
                tallies[rule][call] += 1
                tallies[rule]["days"] += days
        for rule in RULES:
            t = tallies[rule]
            rows.append(
                {
                    "scenario": name,
                    "true_lift": lift,
                    "rule": rule,
                    "runs": args.runs,
                    "ship_rate": t["ship"] / args.runs,
                    "hold_rate": t["hold"] / args.runs,
                    "extend_rate": t["extend"] / args.runs,
                    "mean_days": t["days"] / args.runs,
                }
            )
        print(f"{name}: done ({time.time() - started:.0f}s)", file=sys.stderr)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in row.items()})

    lines = [
        "# Simulation benchmark",
        "",
        f"{args.runs} simulated experiments per scenario, {N_USERS:,} users over {DAYS} days, "
        f"smallest worthwhile lift {MIN_LIFT:.0%}, alpha {ALPHA}. Generated by "
        "`python benchmark/run_benchmark.py`; the data is synthetic (see `causalpilot/simulate.py`).",
        "",
        "Share of experiments that ended in each call (for the p-value rules, \"hold\" means no ship):",
        "",
        "| Scenario | Rule | Ship | Hold | Extend | Mean days run |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        hold = row["hold_rate"] if row["rule"].startswith("causalpilot") else 1 - row["ship_rate"]
        lines.append(
            f"| {row['scenario']} | {row['rule']} | {row['ship_rate']:.1%} | {hold:.1%} | "
            f"{row['extend_rate']:.1%} | {row['mean_days']:.1f} |"
        )
    (out / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
