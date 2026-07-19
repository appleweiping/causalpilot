"""Seeded synthetic fashion experiment with known potential-outcome ground truth."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json

import numpy as np
import pandas as pd


FEATURES = ["interest_score", "price_sensitivity", "novelty_affinity"]
FIXTURE_VERSION = "causalpilot-synthetic-fashion-v1"


@dataclass(frozen=True)
class SegmentSpec:
    id: str
    label: str
    share: float
    baseline_rate: float
    treatment_effect: float
    diversity_delta: float
    contribution_margin: float
    required_subsidy: float
    coordinates: tuple[float, float, float]
    feature_means: tuple[float, float, float]


SEGMENTS: tuple[SegmentSpec, ...] = (
    SegmentSpec("loyalists", "Brand Loyalists", 0.30, 0.115, 0.038, -0.007, 0.24, 2.0, (-3.2, 1.0, 1.8), (0.72, 0.34, 0.46)),
    SegmentSpec("trend_seekers", "Trend Seekers", 0.25, 0.096, 0.052, -0.013, 0.18, 5.0, (1.2, 3.1, 2.7), (0.82, 0.28, 0.88)),
    SegmentSpec("budget_shoppers", "Budget Shoppers", 0.25, 0.071, 0.029, -0.009, 0.135, 8.0, (3.4, -1.8, 0.5), (0.55, 0.86, 0.38)),
    SegmentSpec("new_arrivals", "New Arrivals", 0.20, 0.058, -0.021, -0.028, 0.10, 12.0, (-0.4, -3.0, 3.0), (0.48, 0.57, 0.76)),
)

SEGMENT_MAP = {segment.id: segment for segment in SEGMENTS}
FIXTURE_HASH = sha256(
    json.dumps(
        {
            "fixture_version": FIXTURE_VERSION,
            "features": FEATURES,
            "segments": [asdict(segment) for segment in SEGMENTS],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()[:16]


def _sample_population(
    seed: int,
    n: int,
    drift_severity: float = 0.0,
    drift_segment: str = "new_arrivals",
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    shares = np.array([segment.share for segment in SEGMENTS], dtype=float)
    if drift_severity:
        shares = shares.copy()
        if drift_segment not in SEGMENT_MAP:
            raise ValueError(f"Unknown drift segment '{drift_segment}'")
        drift_index = [segment.id for segment in SEGMENTS].index(drift_segment)
        shares *= 1.0 - 0.55 * drift_severity
        shares[drift_index] += 0.55 * drift_severity
        shares /= shares.sum()
    segment_ids = rng.choice([segment.id for segment in SEGMENTS], size=n, p=shares)
    rows: list[dict[str, float | str]] = []
    for segment_id in segment_ids:
        spec = SEGMENT_MAP[str(segment_id)]
        values = rng.normal(np.asarray(spec.feature_means), np.array([0.14, 0.16, 0.15]))
        if drift_severity and spec.id == drift_segment:
            values += np.array([-0.20, 0.24, 0.16]) * drift_severity
        values = np.clip(values, 0.0, 1.0)
        rows.append(
            {
                "segment": spec.id,
                "interest_score": float(values[0]),
                "price_sensitivity": float(values[1]),
                "novelty_affinity": float(values[2]),
            }
        )
    return pd.DataFrame(rows)


def generate_historical(seed: int, n: int = 4_000) -> pd.DataFrame:
    """Biased logged policy: treatment propensity depends on user features."""
    rng = np.random.default_rng(seed + 17)
    data = _sample_population(seed, n)
    logits = (
        -2.2
        + 4.2 * data["interest_score"].to_numpy()
        - 1.8 * data["price_sensitivity"].to_numpy()
        + 1.2 * data["novelty_affinity"].to_numpy()
    )
    propensity = 1.0 / (1.0 + np.exp(-logits))
    propensity = np.clip(propensity, 0.025, 0.975)
    treatment = rng.binomial(1, propensity)
    baseline = np.array([SEGMENT_MAP[str(value)].baseline_rate for value in data["segment"]])
    effects = np.array([SEGMENT_MAP[str(value)].treatment_effect for value in data["segment"]])
    feature_term = 0.025 * (data["interest_score"].to_numpy() - 0.5)
    outcome_probability = np.clip(baseline + feature_term + treatment * effects, 0.001, 0.95)
    data["propensity"] = propensity
    data["treatment"] = treatment
    data["outcome"] = rng.binomial(1, outcome_probability)
    return data


def generate_rct(seed: int, n: int = 9_000) -> pd.DataFrame:
    """Equal-allocation user-level RCT; potential outcome effect is segment-specific."""
    rng = np.random.default_rng(seed + 101)
    data = _sample_population(seed + 1, n)
    treatment = np.concatenate((np.zeros(n // 2, dtype=int), np.ones(n - n // 2, dtype=int)))
    rng.shuffle(treatment)
    baseline = np.array([SEGMENT_MAP[str(value)].baseline_rate for value in data["segment"]])
    effects = np.array([SEGMENT_MAP[str(value)].treatment_effect for value in data["segment"]])
    feature_term = 0.025 * (data["interest_score"].to_numpy() - 0.5)
    outcome_probability = np.clip(baseline + feature_term + treatment * effects, 0.001, 0.95)
    data["propensity"] = 0.5
    data["treatment"] = treatment
    data["outcome"] = rng.binomial(1, outcome_probability)
    return data


def generate_reference_population(seed: int, n: int = 3_000) -> pd.DataFrame:
    return _sample_population(seed + 1_003, n)


def generate_drift_population(
    seed: int,
    severity: float,
    segment_id: str = "new_arrivals",
    n: int = 3_000,
) -> pd.DataFrame:
    return _sample_population(
        seed + 2_003,
        n,
        drift_severity=severity,
        drift_segment=segment_id,
    )


def oracle_policy_value(max_diversity_loss: float) -> float:
    return sum(
        spec.share * spec.treatment_effect
        for spec in SEGMENTS
        if spec.treatment_effect > 0 and spec.diversity_delta >= -max_diversity_loss
    )
