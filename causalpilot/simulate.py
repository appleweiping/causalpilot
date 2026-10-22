"""Synthetic A/B tests where the true effect is known.

The population is the four shopper segments from the first version of this
project. Each segment has its own baseline conversion rate and reacts differently
to the change (one segment is hurt by it), so the average effect hides
heterogeneity, as real tests do. Used for the quickstart file and the benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Segment:
    name: str
    share: float
    baseline: float  # conversion rate in the test window without the change
    response: float  # relative reaction to the change, before scaling


SEGMENTS = (
    Segment("loyalists", 0.30, 0.115, 0.33),
    Segment("trend_seekers", 0.25, 0.096, 0.54),
    Segment("budget_shoppers", 0.25, 0.071, 0.41),
    Segment("new_arrivals", 0.20, 0.058, -0.36),
)


def simulate(
    n: int = 40_000,
    true_lift: float = 0.0,
    seed: int = 0,
    days: int = 14,
    treatment_share: float = 0.5,
    lost_treatment_bounces: float = 0.0,
) -> pd.DataFrame:
    """One experiment, one row per user.

    `true_lift` is the relative change in the population conversion rate. Segment
    reactions are scaled so their weighted average equals it exactly.
    `lost_treatment_bounces` drops that fraction of non-converting treatment
    users, imitating a logging bug in one arm (which shows up as a sample ratio
    mismatch and inflates the treatment's conversion rate).
    Columns: user_id, day, segment, arm, prior_orders, converted, revenue.
    """
    rng = np.random.default_rng(seed)
    shares = np.array([s.share for s in SEGMENTS])
    baseline = np.array([s.baseline for s in SEGMENTS])
    response = np.array([s.response for s in SEGMENTS])
    scale = true_lift * (shares @ baseline) / (shares @ (baseline * response))

    seg = rng.choice(len(SEGMENTS), size=n, p=shares)
    # Users differ within a segment; the same propensity drives past and future orders.
    propensity = baseline[seg] * np.exp(rng.normal(0.0, 0.9, n) - 0.405)
    prior_orders = rng.poisson(6.0 * propensity)
    treated = rng.random(n) < treatment_share
    rate = propensity * np.where(treated, 1.0 + scale * response[seg], 1.0)
    converted = rng.random(n) < np.clip(rate, 0.0, 1.0)
    revenue = np.where(converted, np.round(rng.lognormal(3.4, 0.6, n), 2), 0.0)
    day = rng.integers(1, days + 1, n)

    frame = pd.DataFrame(
        {
            "user_id": np.arange(1, n + 1),
            "day": day,
            "segment": np.array([s.name for s in SEGMENTS])[seg],
            "arm": np.where(treated, "treatment", "control"),
            "prior_orders": prior_orders,
            "converted": converted.astype(int),
            "revenue": revenue,
        }
    )
    if lost_treatment_bounces > 0:
        lost = treated & ~converted & (rng.random(n) < lost_treatment_bounces)
        frame = frame[~lost]
    return frame.sort_values(["day", "user_id"]).reset_index(drop=True)
