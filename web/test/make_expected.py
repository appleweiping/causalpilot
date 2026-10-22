"""Write web/test/expected.json from the Python package (run after changing the maths)."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from causalpilot import Settings, analyze_csv  # noqa: E402


def expected() -> dict:
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    return {c["name"]: analyze_csv(HERE.parent / "synthetic_example.csv", Settings(**c["settings"])) for c in cases}


if __name__ == "__main__":
    (HERE / "expected.json").write_text(json.dumps(expected(), indent=1, default=float) + "\n", encoding="utf-8")
