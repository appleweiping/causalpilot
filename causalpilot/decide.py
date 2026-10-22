"""Turn the numbers into a ship / hold / extend call with a plain explanation.

The rules follow the practical-significance table in Kohavi, Tang and Xu,
"Trustworthy Online Controlled Experiments" (2020), chapter 2, plus two checks
that should come before any effect is read: the sample ratio and the guardrails.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import NamedTuple

SHIP, HOLD, EXTEND = "ship", "hold", "extend"


class GuardrailHarm(NamedTuple):
    """A guardrail whose interval lies entirely on the wrong side of zero."""

    metric: str
    ci_low: float
    ci_high: float
    lower_is_better: bool = False
    unit: str = ""


@dataclass(frozen=True)
class Verdict:
    call: str
    headline: str
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _fmt(value: float, unit: str) -> str:
    if unit == "%":
        return f"{value * 100:+.2f} pp"
    return f"{value:+.4g}"


def decide(
    *,
    metric: str,
    effect: float,
    ci_low: float,
    ci_high: float,
    min_effect: float,
    srm_p: float,
    srm_alpha: float = 0.001,
    sample_factor: float | None = None,
    max_extend: float = 4.0,
    harmed_guardrails: tuple[GuardrailHarm, ...] = (),
    interval_name: str = "95% interval",
    unit: str = "",
) -> Verdict:
    """Decide from the interval of the primary metric.

    `min_effect` is the smallest absolute change worth shipping (in metric units).
    `sample_factor` is how many times the current sample would be needed to detect
    `min_effect` with 80% power; it decides between "extend" and "hold" when the
    interval is inconclusive. `harmed_guardrails` are the guardrails that clearly
    moved the wrong way (down for a higher-is-better metric, up for a
    lower-is-better one such as refunds); any of them blocks a ship.
    """
    span = f"{interval_name} {_fmt(ci_low, unit)} to {_fmt(ci_high, unit)}"
    bar = f"the smallest change you said is worth shipping ({_fmt(min_effect, unit)})"

    if srm_p < srm_alpha:
        return Verdict(
            HOLD,
            "Do not trust this result yet: the groups are not the size the design says.",
            [
                f"Sample ratio test p = {srm_p:.2g} (threshold {srm_alpha}). Some users were "
                "lost, duplicated or assigned unevenly, and that usually biases the effect.",
                "Check assignment and logging (bots, redirects, crashes in one arm, filters "
                "applied after assignment) before reading any metric.",
            ],
        )
    if harmed_guardrails:
        names = ", ".join(g.metric for g in harmed_guardrails)
        reasons = []
        for g in harmed_guardrails:
            g_span = f"{interval_name} {_fmt(g.ci_low, g.unit)} to {_fmt(g.ci_high, g.unit)}"
            if g.lower_is_better:
                reasons.append(f"{g.metric} went up, and lower is better: the {g_span} lies entirely above zero.")
            else:
                reasons.append(f"{g.metric} went down, and higher is better: the {g_span} lies entirely below zero.")
        return Verdict(HOLD, f"The change clearly hurts a guardrail metric ({names}).", reasons)
    if ci_high < 0:
        return Verdict(
            HOLD,
            f"The treatment makes {metric} worse.",
            [f"The whole {span} is below zero."],
        )
    if ci_low > 0:
        if min_effect > 0 and ci_high < min_effect:
            return Verdict(
                HOLD,
                f"The effect on {metric} is real but too small to matter.",
                [
                    f"The {span} excludes zero but stays under {bar}.",
                    "Ship anyway only if the change costs nothing to keep.",
                ],
            )
        if ci_low >= min_effect:
            return Verdict(
                SHIP,
                f"{metric} improves by more than the minimum worthwhile change.",
                [f"Even the low end of the {span} clears {bar}."],
            )
        return Verdict(
            SHIP,
            f"{metric} improves, though the size is uncertain.",
            [
                f"The {span} excludes zero; the point estimate is {_fmt(effect, unit)}.",
                f"The low end is below {bar}, so a repeat with more traffic would pin the size down.",
            ],
        )
    # The interval contains zero.
    if min_effect > 0 and ci_low > -min_effect and ci_high < min_effect:
        return Verdict(
            HOLD,
            f"No meaningful effect on {metric}.",
            [
                f"The {span} contains zero and rules out changes as large as {bar}.",
            ],
        )
    if sample_factor is not None and sample_factor <= max_extend:
        more = max(sample_factor - 1.0, 0.0)
        return Verdict(
            EXTEND,
            f"Not enough data yet to tell whether {metric} moves.",
            [
                f"The {span} contains zero but is too wide to rule out {bar}.",
                f"Detecting that change with 80% power needs about {sample_factor:.1f}x the "
                f"current sample ({more:.1f}x more users per arm).",
                "Decide the new end date now and look once at the end, or rerun with "
                "--peeking if you will keep checking.",
            ],
        )
    reasons = [f"The {span} contains zero and is too wide to rule out {bar}."]
    if sample_factor is not None:
        reasons.append(
            f"Detecting that change with 80% power would need about {sample_factor:.0f}x the "
            "current sample, which is beyond the --max-extend limit."
        )
    return Verdict(HOLD, f"The test cannot detect a worthwhile effect on {metric} at this traffic.", reasons)
