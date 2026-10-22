import pandas as pd
import pytest

from causalpilot import Settings, analyze_frame
from causalpilot.analysis import parse_split
from causalpilot.simulate import simulate


def settings(**kw):
    base = dict(group="arm", control="control", metrics=["converted"], covariates=["prior_orders"], min_lift=0.05)
    base.update(kw)
    return Settings(**base)


def test_large_true_lift_ships():
    result = analyze_frame(simulate(n=60_000, true_lift=0.25, seed=1), settings())
    comp = result["comparisons"][0]
    assert result["srm"]["p_value"] > 0.001
    assert comp["verdict"]["call"] == "ship"
    metric = comp["metrics"][0]
    assert metric["binary"] is True
    assert metric["cuped"]["variance_reduction"] > 0.02
    assert metric["cuped"]["se"] < metric["raw"]["se"]


def test_logging_bug_is_caught_by_sample_ratio_test():
    frame = simulate(n=40_000, true_lift=0.0, seed=2, lost_treatment_bounces=0.08)
    result = analyze_frame(frame, settings())
    assert result["srm"]["p_value"] < 0.001
    verdict = result["comparisons"][0]["verdict"]
    assert verdict["call"] == "hold"
    assert "not the size the design says" in verdict["headline"]


def test_true_harm_holds():
    result = analyze_frame(simulate(n=60_000, true_lift=-0.25, seed=3), settings())
    assert result["comparisons"][0]["verdict"]["call"] == "hold"


def test_peeking_uses_wider_interval():
    frame = simulate(n=20_000, true_lift=0.1, seed=4)
    fixed = analyze_frame(frame, settings())
    peek = analyze_frame(frame, settings(peeking=True))
    m = fixed["comparisons"][0]["metrics"][0]
    assert m["always_valid"]["ci_low"] < m["cuped"]["ci_low"]
    assert "--peeking" in " ".join(fixed["notes"])
    assert "always-valid" in " ".join(peek["comparisons"][0]["verdict"]["reasons"])


def test_text_booleans_categorical_covariates_and_multiple_arms():
    frame = pd.DataFrame(
        {
            "variant": ["A", "B", "C"] * 400,
            "bought": ["yes", "no", "no", "no", "yes", "no"] * 200,
            "spend": [0.0, 10.0, 3.5, 1.0, 0.0, 2.0] * 200,
            "country": ["nl", "us", "cn", "us"] * 300,
        }
    )
    result = analyze_frame(
        frame,
        Settings(group="variant", control="A", metrics=["bought", "spend"], covariates=["country"]),
    )
    assert [c["treatment"] for c in result["comparisons"]] == ["B", "C"]
    assert result["settings"]["covariate_columns"] == ["country=nl", "country=us"]
    assert result["comparisons"][0]["metrics"][0]["binary"] is True
    assert any("treatments are compared" in n for n in result["notes"])


def test_missing_column_is_reported_clearly():
    with pytest.raises(ValueError, match="missing column"):
        analyze_frame(simulate(n=200, seed=5), settings(metrics=["clicks"]))


def test_unknown_control_is_reported_clearly():
    with pytest.raises(ValueError, match="control group 'ctrl' not found"):
        analyze_frame(simulate(n=200, seed=5), settings(control="ctrl"))


def test_split_parsing():
    assert parse_split("50:50", ["control", "treatment"]) == {"control": 50.0, "treatment": 50.0}
    assert parse_split("control=0.9,treatment=0.1", ["control", "treatment"]) == {"control": 0.9, "treatment": 0.1}
    with pytest.raises(ValueError):
        parse_split("1:1:1", ["control", "treatment"])


def test_unequal_planned_split_is_respected():
    frame = simulate(n=20_000, seed=6, treatment_share=0.2)
    equal = analyze_frame(frame, settings())
    planned = analyze_frame(frame, settings(split="80:20"))
    assert equal["srm"]["p_value"] < 1e-6
    assert planned["srm"]["p_value"] > 0.001
