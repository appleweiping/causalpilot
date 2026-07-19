import json

import pandas as pd
import pytest

from evaluation.adapters import load_open_bandit, summarize_open_bandit
from evaluation.benchmark import METHODS, evaluate_seed, make_episode, trace
from evaluation.run_benchmark import _quantize_json, run, wilson_interval


def test_all_required_methods_execute_and_are_reproducible():
    first = evaluate_seed(11)
    second = evaluate_seed(11)
    assert first == second
    assert {row["method"] for row in first} == set(METHODS)
    assert all(row["llm_api_calls"] == 0 for row in first)
    assert all(row["token_count"] == 0 for row in first)
    assert all("policy_regret_gt" in row for row in first)
    assert "causalpilot_no_trace" in METHODS


def test_trace_respects_known_constraints():
    rows = {row["method"]: row for row in evaluate_seed(23)}
    trace = rows["trace"]
    assert len(trace["deployed_segments"].split(";")) <= 1
    assert trace["experiment_samples"] == 9_000
    assert trace["human_questions"] >= 1
    assert "false_deployment_rate_gt" in trace


def test_trace_policy_cannot_read_episode_truth():
    episode = make_episode(23)
    assert not hasattr(episode.observation, "seed")
    assert not hasattr(episode.observation, "post_shift_effects")
    assert not hasattr(episode.observation, "drift_segment")
    first = trace(episode.observation)
    # Truth is intentionally not an argument to the shared TRACE policy path.
    second = trace(episode.observation)
    assert first == second


def test_runner_writes_machine_and_human_readable_artifacts(tmp_path):
    runs, summary = run([11, 23, 37], tmp_path)
    assert len(runs) == len(METHODS) * 3
    assert len(summary) == len(METHODS)
    for name in ("runs.csv", "summary.csv", "results.json", "RESULTS.md"):
        assert (tmp_path / name).exists()
    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["api_keys_required"] is False
    assert "deterministic decision-rule proxies" in payload["metadata"]["llm_baseline_disclosure"]
    assert payload["metadata"]["confidence_intervals"]["resamples"] == 2_000
    assert "PolicyObservation only" in payload["metadata"]["truth_policy_separation"]
    assert payload["metadata"]["evidence_mode"] == "simulated_scm"
    assert payload["metadata"]["fixture_version"] == "causalpilot-synthetic-fashion-v1"
    assert len(payload["metadata"]["fixture_hash"]) == 16
    assert payload["metadata"]["split"] == "paired_seeded_episodes"
    assert "gate_thresholds" in payload["metadata"]
    assert "detector_parameters" in payload["metadata"]


def test_seed_bootstrap_summary_is_deterministic(tmp_path):
    _, first = run([11, 23, 37], tmp_path / "first")
    _, second = run([11, 23, 37], tmp_path / "second")
    pd.testing.assert_frame_equal(first, second)


def test_json_evidence_quantizes_cross_runtime_float_tails():
    above = _quantize_json({"score": 0.123456789012345, "zero": -1e-20})
    below = _quantize_json({"score": 0.123456789012344, "zero": 1e-20})
    assert above == below == {"score": 0.12345679, "zero": 0.0}


def test_zero_of_fifty_uses_nonzero_wilson_upper_bound():
    low, high = wilson_interval(0, 50)
    assert low == 0
    assert high == pytest.approx(0.07135, abs=1e-4)


def test_invalid_intervals_and_duplicate_seeds_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="positive"):
        wilson_interval(0, 10, z_score=0)
    with pytest.raises(ValueError, match="duplicates"):
        run([11, 11], tmp_path)


def test_open_bandit_adapter_parses_official_nested_layout(tmp_path):
    path = tmp_path / "random" / "all"
    path.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "timestamp": ["2020-01-01", "2020-01-02"],
            "item_id": [1, 2],
            "position": [1, 2],
            "click": [0, 1],
            "action_prob": [0.2, 0.4],
            "user_features": ["a", "b"],
            "user_item_affinity": [0.1, 0.9],
        }
    )
    frame.to_csv(path / "all.csv", index=False)
    loaded = load_open_bandit(tmp_path, "random", "all")
    summary = summarize_open_bandit(tmp_path, "random", "all")
    assert len(loaded) == 2
    assert summary.click_rate == 0.5
    assert 0 < summary.effective_sample_size <= 2
