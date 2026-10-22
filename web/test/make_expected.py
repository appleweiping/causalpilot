"""Write web/test/expected.json from the Python package (run after changing the maths).

Also writes web/test/refunds.csv, a small simulated test where the treatment lifts
conversion but triples refunds, for the lower-is-better guardrail case.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from causalpilot import Settings, analyze_csv  # noqa: E402


def refunds_example(n: int = 6_000, seed: int = 2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    treated = rng.random(n) < 0.5
    converted = rng.random(n) < np.where(treated, 0.12, 0.10)
    refunded = rng.random(n) < np.where(treated, 0.036, 0.012)
    return pd.DataFrame(
        {
            "arm": np.where(treated, "treatment", "control"),
            "converted": converted.astype(int),
            "refunded": refunded.astype(int),
        }
    )


def expected() -> dict:
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    out = {}
    for case in cases:
        csv = (HERE / case["csv"]) if "csv" in case else (HERE.parent / "synthetic_example.csv")
        out[case["name"]] = analyze_csv(csv, Settings(**case["settings"]))
    return out


if __name__ == "__main__":
    refunds_example().to_csv(HERE / "refunds.csv", index=False, lineterminator="\n")
    (HERE / "expected.json").write_text(json.dumps(expected(), indent=1, default=float) + "\n", encoding="utf-8")
