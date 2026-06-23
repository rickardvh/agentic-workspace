from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_completion_cost_json_corpus.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_completion_cost_json_corpus", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture_payload() -> dict:
    repeated = "Run agentic-workspace summary --target . --format json before claiming completion."
    return {
        "kind": "fixture/ordinary-output/v1",
        "status": "attention",
        "next_action": "Inspect the ranked output fields.",
        "diagnostics": {
            "warnings": [],
            "details": {},
            "repeated": repeated,
        },
        "planning": {
            "todo": [],
            "execplans": [],
            "residue": {
                "summary": repeated,
                "owner": "",
            },
        },
        "detail_commands": {
            "summary": "agentic-workspace summary --select planning_surface_health --format json",
            "verbose": "agentic-workspace summary --verbose --format json",
        },
        "large_advisory": {
            f"item_{index}": "This advisory text is intentionally long enough to count as prose in the actual JSON corpus measurement."
            for index in range(12)
        },
    }


def test_completion_cost_json_corpus_measures_fixture_output() -> None:
    checker = _load_checker()

    analysis = checker.analyze_payload("fixture", _fixture_payload(), owner_surface="workspace ordinary outputs")

    assert analysis["status"] == "measured"
    assert analysis["total_bytes"] > 0
    assert analysis["empty_default_ratio"] > 0
    assert analysis["selector_signal_count"] >= 1
    assert analysis["repeated_strings"]
    assert analysis["top_fields"]
    assert all(item["byte_share"] <= 1 for item in analysis["top_level_fields"])
    assert analysis["observations"]


def test_completion_cost_json_corpus_payload_has_issue_1691_contract() -> None:
    checker = _load_checker()
    sample = {
        "sample_id": "fixture",
        "description": "fixture sample",
        "command": ["fixture"],
        "owner_surface": "workspace ordinary outputs",
        "status": "captured",
        "payload": _fixture_payload(),
    }

    payload = checker.analyze_samples([sample])

    assert payload["kind"] == "agentic-workspace/completion-cost-json-corpus/v1"
    assert payload["ordinary_loop_surface"] is False
    assert payload["measurement_route"]["issue"] == "GitHub #1691"
    assert payload["analyzed_sample_count"] == 1
    assert payload["ranked_observations"]
    observation = payload["ranked_observations"][0]
    assert {
        "sample_id",
        "field_path",
        "observation_type",
        "suspected_cost_type",
        "owner_surface",
        "reason",
        "candidate_measurement",
        "candidate_reduction",
    }.issubset(observation)


def test_completion_cost_json_corpus_can_read_fixture_directory(tmp_path: Path) -> None:
    checker = _load_checker()
    fixture = tmp_path / "ordinary.json"
    fixture.write_text(json.dumps(_fixture_payload()), encoding="utf-8")

    samples = checker._load_samples_from_dir(tmp_path)
    payload = checker.analyze_samples(samples)

    assert payload["sample_count"] == 1
    assert payload["analyzed_sample_count"] == 1
    assert payload["observation_count"] >= 1


def test_completion_cost_json_corpus_main_does_not_fail_on_observations(tmp_path: Path, capsys) -> None:
    checker = _load_checker()
    fixture = tmp_path / "ordinary.json"
    fixture.write_text(json.dumps(_fixture_payload()), encoding="utf-8")

    status = checker.main(["--from-dir", str(tmp_path), "--format", "json", "--min-analyzed-samples", "1"])

    assert status == 0
    assert "completion-cost-json-corpus" in capsys.readouterr().out
