from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from tests.workspace_cli_support import cli

from agentic_workspace.operating_decision import compile_operating_decision
from agentic_workspace.runtime_compatibility import READER_CONTRACT_EPOCH, admit_runtime_compatibility

FIXTURE = Path(__file__).parent / "fixtures" / "dynamic_instruction_scenarios.json"


def _public_target(tmp_path: Path, capsys) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    return tmp_path


def _scenario_payload(scenario: dict[str, Any], tmp_path: Path, capsys) -> tuple[dict[str, Any], int]:
    runner = scenario["runner"]
    inputs = scenario["input"]
    if runner == "planning-route":
        target = _public_target(tmp_path, capsys)
        assert (
            cli.main(
                [
                    "planning",
                    "new-plan",
                    "--id",
                    "matrix-plan",
                    "--title",
                    "Matrix plan",
                    "--target",
                    str(target),
                    "--activate",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            cli.main(
                ["start", "--target", str(target), "--task", "Continue Matrix plan", "--select", "planning_safety_gate", "--format", "json"]
            )
            == 0
        )
        selected = json.loads(capsys.readouterr().out)
        return selected["values"]["planning_safety_gate"]["route_decision"], 3
    if runner == "operating-decision":
        return compile_operating_decision(inputs=inputs), 1
    if runner == "incompatible-runtime":
        config = tmp_path / ".agentic-workspace" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text(
            "schema_version = 1\n\n[cli_compatibility]\n"
            f"minimum_reader_epoch = {READER_CONTRACT_EPOCH + int(inputs['minimum_reader_epoch_delta'])}\n",
            encoding="utf-8",
        )
        return admit_runtime_compatibility(tmp_path), 1
    if runner == "causal-block":
        return compile_operating_decision(
            inputs={
                "denied_effect": True,
                "provenance": {"blocking_source_owner": inputs["owner"]},
            }
        ), 1
    if runner == "coherence":
        first = compile_operating_decision(inputs=inputs)
        second = compile_operating_decision(inputs=inputs)
        return {"first": first, "second": second}, 2
    if runner == "memory-boundary":
        contribution = {
            "kind": "agentic-memory/decision-contribution/v1",
            "status": "projected",
            "fact_id": inputs["fact_id"],
            "fact_revision": "sha256:" + "1" * 64,
            "source_revision": "sha256:" + "2" * 64,
            "freshness": "current",
            "owner": "memory",
            "authority_class": "advisory",
            "affected_decisions": ["planning-task-relation"],
            "guidance": "Check the structured Planning relation before proceeding.",
            "authority_boundary": "Planning owns relation correctness.",
        }
        return compile_operating_decision(
            inputs={"revisions": {"planning": inputs["planning_revision"]}, "memory_contributions": [contribution]}
        ), 1
    if runner == "source-guidance":
        target = _public_target(tmp_path, capsys)
        return compile_operating_decision(inputs={"consumer": "implement", "task": inputs["task"], "target_root": str(target)})[
            "source_guidance"
        ], 2
    raise AssertionError(f"unknown bounded scenario runner: {runner}")


def _assert_expected(scenario: dict[str, Any], payload: dict[str, Any]) -> None:
    expected = scenario["expected"]
    runner = scenario["runner"]
    if runner == "planning-route":
        assert payload["task_relation"] == expected["task_relation"]
        assert payload["required_transition"] == expected["required_transition"]
    elif runner == "operating-decision":
        assert payload["status"] == expected["status"]
        assert len(payload["source_guidance"]["contributions"]) == expected["source_guidance_count"]
        assert len(payload["memory_effectiveness"]["projected_contributions"]) == expected["memory_contribution_count"]
    elif runner == "incompatible-runtime":
        assert payload["status"] == expected["status"]
        assert payload["managed_state_interpreted"] is expected["managed_state_interpreted"]
        assert expected["unavailable_effect"] in payload["unavailable_effects"]
    elif runner == "causal-block":
        assert payload["status"] == expected["status"]
        assert bool(payload["primary_action"]) is expected["primary_action_present"]
        assert payload["external_blocker"]["reason_code"] == expected["reason_code"]
    elif runner == "coherence":
        assert (payload["first"]["decision_id"] == payload["second"]["decision_id"]) is expected["same_revision_same_identity"]
        assert payload["first"]["producer_module"] == expected["producer"]
    elif runner == "memory-boundary":
        contribution = payload["memory_effectiveness"]["projected_contributions"][0]
        assert contribution["status"] == expected["memory_status"]
        assert contribution["authority_class"] == expected["authority_class"]
        assert payload["input_revisions"]["planning"] == expected["planning_revision"]
    elif runner == "source-guidance":
        assert payload["status"] == expected["status"]
        assert len(payload["contributions"]) == expected["contribution_count"]
        assert payload["contributions"][0]["full_body_loaded"] is expected["full_body_loaded"]


def _first_line_projection(scenario: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    runner = scenario["runner"]
    if runner == "planning-route":
        return {key: payload.get(key) for key in ("task_relation", "owner_posture", "required_transition", "implementation_allowed")}
    if runner in {"operating-decision", "causal-block", "memory-boundary"}:
        return {
            "decision_id": payload.get("decision_id"),
            "status": payload.get("status"),
            "terminal_state": payload.get("terminal_state"),
            "primary_action": payload.get("primary_action"),
            "external_blocker": payload.get("external_blocker"),
            "source_guidance": payload.get("source_guidance"),
            "memory_contributions": payload.get("memory_effectiveness", {}).get("projected_contributions", []),
        }
    if runner == "coherence":
        return {
            "decision_id": payload["first"]["decision_id"],
            "repeat_decision_id": payload["second"]["decision_id"],
            "producer": payload["first"]["producer_module"],
        }
    return payload


def _find_planning_route(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        route = payload.get("route_decision")
        if isinstance(route, dict) and "task_relation" in route:
            return route
        for value in payload.values():
            found = _find_planning_route(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_planning_route(value)
            if found:
                return found
    return {}


@pytest.mark.parametrize("scenario", json.loads(FIXTURE.read_text(encoding="utf-8"))["scenarios"], ids=lambda item: item["id"])
def test_dynamic_instruction_scenario(scenario: dict[str, Any], tmp_path: Path, capsys) -> None:
    payload, actual_calls = _scenario_payload(scenario, tmp_path, capsys)
    _assert_expected(scenario, payload)

    output_bytes = len(json.dumps(_first_line_projection(scenario, payload), sort_keys=True, separators=(",", ":")).encode("utf-8"))
    assert output_bytes <= scenario["burden"]["max_output_bytes"]
    assert actual_calls <= scenario["burden"]["max_public_or_owner_calls"]


def test_generic_operating_loop_reaches_terminal_state_without_stale_continuation(tmp_path: Path, capsys) -> None:
    target = _public_target(tmp_path, capsys)
    assert cli.main(["start", "--target", str(target), "--select", "installed_state_compatibility", "--format", "json"]) == 0
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    assert compatibility["status"] == "compatible"

    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "generic-loop",
                "--title",
                "Generic loop",
                "--target",
                str(target),
                "--activate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    changed_path = target / "src" / "bounded.py"
    changed_path.parent.mkdir(parents=True)
    changed_path.write_text("VALUE = 1\n", encoding="utf-8")
    common = ["--target", str(target), "--task", "Continue Generic loop", "--changed", "src/bounded.py", "--format", "json"]
    phases: dict[str, dict[str, Any]] = {}
    for phase in ("start", "implement", "proof"):
        assert cli.main([phase, *common]) == 0
        phases[phase] = json.loads(capsys.readouterr().out)
        assert phases[phase]["projection_reuse"]["decision_id"]
        route = _find_planning_route(phases[phase])
        if phase != "proof":
            assert route["task_relation"] == "continues-selected-owner"
        else:
            assert '"required_commands"' in json.dumps(phases[phase])

    assert cli.main(["planning", "handoff", "--target", str(target), "--format", "json"]) == 0
    handoff = json.loads(capsys.readouterr().out)
    assert handoff.get("kind") != "agentic-workspace/planning-handoff-proof-route-gate/v1"

    assert (
        cli.main(
            [
                "planning",
                "closeout",
                "generic-loop",
                "--target",
                str(target),
                "--proof-from",
                "public start, implement, and proof projections passed",
                "--what-happened",
                "Completed the bounded generic operating loop.",
                "--scope-touched",
                "src/bounded.py",
                "--changed-surfaces",
                "src/bounded.py",
                "--review-summary",
                "Public boundary behavior verified.",
                "--outcome-summary",
                "Bounded work completed with no residue.",
                "--format",
                "json",
            ]
        )
        == 0
    )
    closeout = json.loads(capsys.readouterr().out)
    assert closeout["outcome"] == "applied"

    assert cli.main(["summary", "--target", str(target), "--select", "planning_record", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["values"]["planning_record"]["status"] == "unavailable"

    assert cli.main(["start", "--target", str(target), "--task", "Begin unrelated follow-up", "--format", "json"]) == 0
    resumed = json.loads(capsys.readouterr().out)
    assert resumed["context"]["active_state"].get("planning_record", {"status": "unavailable"})["status"] == "unavailable"
    assert "continuation_capsule" not in resumed
