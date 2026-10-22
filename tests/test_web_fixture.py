"""web/test/expected.json is what the browser version is checked against, so it must
match what the Python package computes today. Regenerate it with
`python web/test/make_expected.py` after changing the maths."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_maker():
    spec = importlib.util.spec_from_file_location("make_expected", ROOT / "web" / "test" / "make_expected.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _compare(actual, wanted, path=""):
    if isinstance(wanted, dict):
        assert set(actual) == set(wanted), path
        for key in wanted:
            _compare(actual[key], wanted[key], f"{path}.{key}")
    elif isinstance(wanted, list):
        assert len(actual) == len(wanted), path
        for i, (a, w) in enumerate(zip(actual, wanted)):
            _compare(a, w, f"{path}[{i}]")
    elif isinstance(wanted, float):
        assert actual == pytest.approx(wanted, rel=1e-9, abs=1e-12), path
    else:
        assert actual == wanted, path


def test_fixture_is_up_to_date():
    current = json.loads(json.dumps(_load_maker().expected(), default=float))
    stored = json.loads((ROOT / "web" / "test" / "expected.json").read_text(encoding="utf-8"))
    _compare(current, stored)
