"""Optional adapters for public randomized datasets.

No network access occurs on import or during the default benchmark. Users supply
local files (Open Bandit) or explicitly opt into Hugging Face streaming (Criteo).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd


@dataclass(frozen=True)
class OpenBanditSummary:
    behavior_policy: str
    campaign: str
    rows: int
    click_rate: float
    mean_action_probability: float
    effective_sample_size: float


def _resolve_obd_csv(root: Path, behavior_policy: str, campaign: str) -> Path:
    candidates = (
        root / behavior_policy / campaign / f"{campaign}.csv",
        root / behavior_policy / f"{campaign}.csv",
        root / f"{campaign}.csv",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find an Open Bandit log. Expected one of: "
        + ", ".join(str(path) for path in candidates)
    )


def load_open_bandit(
    root: str | Path,
    behavior_policy: str = "random",
    campaign: str = "all",
    nrows: int | None = None,
) -> pd.DataFrame:
    """Parse the official ``obd/{policy}/{campaign}/{campaign}.csv`` layout."""
    if behavior_policy not in {"random", "bts"}:
        raise ValueError("behavior_policy must be 'random' or 'bts'")
    if campaign not in {"all", "men", "women"}:
        raise ValueError("campaign must be 'all', 'men', or 'women'")
    path = _resolve_obd_csv(Path(root), behavior_policy, campaign)
    frame = pd.read_csv(path, nrows=nrows)
    required = {"timestamp", "item_id", "position", "click", "action_prob"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Open Bandit CSV is missing columns: {sorted(missing)}")
    if not frame["click"].isin([0, 1]).all():
        raise ValueError("click must be binary")
    if not frame["action_prob"].between(0, 1, inclusive="both").all():
        raise ValueError("action_prob must lie in [0, 1]")
    return frame


def summarize_open_bandit(
    root: str | Path,
    behavior_policy: str = "random",
    campaign: str = "all",
    nrows: int | None = None,
) -> OpenBanditSummary:
    frame = load_open_bandit(root, behavior_policy, campaign, nrows)
    weights = 1.0 / frame["action_prob"].clip(lower=1e-9)
    effective_sample_size = float(weights.sum() ** 2 / (weights.pow(2).sum()))
    return OpenBanditSummary(
        behavior_policy=behavior_policy,
        campaign=campaign,
        rows=len(frame),
        click_rate=float(frame["click"].mean()),
        mean_action_probability=float(frame["action_prob"].mean()),
        effective_sample_size=effective_sample_size,
    )


def stream_criteo_unbiased(limit: int | None = 100_000) -> Iterator[dict[str, object]]:
    """Explicit opt-in stream for ``criteo/criteo-uplift`` on Hugging Face.

    The current unbiased release is 13,979,592 rows (about 297 MB compressed,
    treatment ratio about 0.85). It is distinct from the older ~25M-row release.
    Install ``datasets`` separately; it is intentionally not a default dependency.
    """
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "Optional Criteo streaming needs `pip install datasets`; default synthetic runs do not."
        ) from exc
    stream = load_dataset("criteo/criteo-uplift", split="train", streaming=True)
    for index, row in enumerate(stream):
        if limit is not None and index >= limit:
            break
        yield row
