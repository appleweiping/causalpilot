import json

from causalpilot.cli import main


def test_simulate_then_analyze(tmp_path, capsys):
    data = tmp_path / "test.csv"
    assert main(["simulate", str(data), "--n", "30000", "--lift", "0.2", "--seed", "1"]) == 0
    out_dir = tmp_path / "report"
    code = main(
        [
            "analyze", str(data),
            "--group", "arm", "--control", "control",
            "--metric", "converted", "--metric", "revenue",
            "--covariate", "prior_orders",
            "--min-lift", "0.05",
            "--out", str(out_dir),
        ]
    )
    assert code == 0
    printed = capsys.readouterr().out
    assert "Sample ratio" in printed
    assert "SHIP" in printed
    assert (out_dir / "report.md").read_text(encoding="utf-8").startswith("# A/B test report")
    assert (out_dir / "effects.png").stat().st_size > 10_000
    result = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert result["comparisons"][0]["verdict"]["call"] == "ship"


def test_bad_column_returns_error_code(tmp_path, capsys):
    data = tmp_path / "test.csv"
    main(["simulate", str(data), "--n", "500"])
    code = main(["analyze", str(data), "--group", "variant", "--control", "control", "--metric", "converted"])
    assert code == 2
    assert "missing column" in capsys.readouterr().err


def test_guardrail_direction_suffix(tmp_path, capsys):
    data = tmp_path / "test.csv"
    main(["simulate", str(data), "--n", "20000", "--lift", "0.2", "--seed", "3"])
    capsys.readouterr()
    args =["analyze", str(data), "--group", "arm", "--control", "control", "--metric", "converted"]
    # Revenue rises with conversion, so it only counts as harm when lower is better.
    assert main([*args, "--guardrail", "revenue:lower", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["settings"]["guardrails"] == [{"metric": "revenue", "lower_is_better": True}]
    assert result["comparisons"][0]["verdict"]["call"] == "hold"
    assert main([*args, "--guardrail", "revenue"]) == 0
    assert "-> SHIP" in capsys.readouterr().out
