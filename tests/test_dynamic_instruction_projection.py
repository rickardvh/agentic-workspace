from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from tests.workspace_cli_support import cli

from agentic_workspace.operating_decision import compile_operating_decision
from agentic_workspace.runtime_compatibility import READER_CONTRACT_EPOCH

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
        target = _public_target(tmp_path, capsys)
        return compile_operating_decision(inputs={**inputs, "consumer": "implement", "target_root": str(target)}), 2
    if runner == "incompatible-runtime":
        target = _public_target(tmp_path, capsys)
        config = target / ".agentic-workspace" / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8")
            + "\n[cli_compatibility]\n"
            + f"minimum_reader_epoch = {READER_CONTRACT_EPOCH + int(inputs['minimum_reader_epoch_delta'])}\n",
            encoding="utf-8",
        )
        assert cli.main(["start", "--target", str(target), "--task", "inspect runtime compatibility", "--format", "json"]) == 0
        return json.loads(capsys.readouterr().out), 2
    if runner == "causal-block":
        target = _public_target(tmp_path, capsys)
        config = target / ".agentic-workspace" / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8") + "\n[cli_compatibility]\n" + f"minimum_reader_epoch = {READER_CONTRACT_EPOCH + 1}\n",
            encoding="utf-8",
        )
        assert cli.main(["implement", "--target", str(target), "--task", "implement runtime contract", "--format", "json"]) == 0
        return json.loads(capsys.readouterr().out), 2
    if runner == "coherence":
        target = _public_target(tmp_path, capsys)
        assert (
            cli.main(
                [
                    "planning",
                    "new-plan",
                    "--id",
                    "coherence-plan",
                    "--title",
                    "Coherence plan",
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
        common = ["--target", str(target), "--task", "Continue Coherence plan", "--format", "json"]
        assert cli.main(["start", *common]) == 0
        first = _find_planning_route(json.loads(capsys.readouterr().out))
        assert cli.main(["implement", *common]) == 0
        second = _find_planning_route(json.loads(capsys.readouterr().out))
        return {"first": first, "second": second}, 4
    if runner == "memory-boundary":
        target = _public_target(tmp_path, capsys)
        assert (
            cli.main(
                [
                    "start",
                    "--target",
                    str(target),
                    "--task",
                    "avoid memory rediscovery trap",
                    "--select",
                    "memory_decision_packet",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        return json.loads(capsys.readouterr().out)["values"]["memory_decision_packet"], 2
    if runner == "source-guidance":
        target = _public_target(tmp_path, capsys)
        (target / "SYSTEM_INTENT.md").write_text(
            "# System Intent\n\n## Governing intents\n\nGenerated runtime contract architecture.\n",
            encoding="utf-8",
        )
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
        assert payload["cli_compatibility"]["status"] == expected["status"]
        assert payload["context"]["installed_state_drift_triage"]["status"] == expected["triage_status"]
        assert expected["changed_signal"] in payload["action_signals"]["changed_signals"]
    elif runner == "causal-block":
        effect = _find_claim_effect_boundary(payload)
        assert effect["installed_payload_dependency"] == expected["installed_payload_dependency"]
        assert expected["claim_class"] in effect["claim_classes"]
    elif runner == "coherence":
        assert (payload["first"]["selected_owner_identity"] == payload["second"]["selected_owner_identity"]) is expected[
            "same_revision_same_identity"
        ]
    elif runner == "memory-boundary":
        assert payload["use"]["status"] == expected["memory_status"]
        assert payload["use"]["contributions"] == []
        assert "semantic conclusions" in payload["why_visible"]
        assert "agent_owns" in payload["authority_boundary"]
    elif runner == "source-guidance":
        assert payload["status"] == expected["status"]
        assert len(payload["contributions"]) == expected["contribution_count"]
        assert payload["contributions"][0]["full_body_loaded"] is expected["full_body_loaded"]


def _first_line_projection(scenario: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    runner = scenario["runner"]
    if runner == "planning-route":
        return {key: payload.get(key) for key in ("task_relation", "owner_posture", "required_transition", "implementation_allowed")}
    if runner == "operating-decision":
        return {
            "decision_id": payload.get("decision_id"),
            "status": payload.get("status"),
            "terminal_state": payload.get("terminal_state"),
            "primary_action": payload.get("primary_action"),
            "external_blocker": payload.get("external_blocker"),
            "source_guidance": payload.get("source_guidance"),
            "memory_contributions": payload.get("memory_effectiveness", {}).get("projected_contributions", []),
        }
    if runner == "causal-block":
        effect = _find_claim_effect_boundary(payload)
        return {
            "claim_effect_boundary": effect,
        }
    if runner == "incompatible-runtime":
        return {
            "cli_compatibility": payload.get("cli_compatibility"),
            "installed_state_drift_triage": payload.get("context", {}).get("installed_state_drift_triage"),
            "changed_signals": payload.get("action_signals", {}).get("changed_signals"),
        }
    if runner == "memory-boundary":
        return {
            "stage": payload.get("stage"),
            "force": payload.get("force"),
            "use": payload.get("use"),
            "authority_boundary": payload.get("authority_boundary"),
        }
    if runner == "coherence":
        return {
            "selected_owner_identity": payload["first"]["selected_owner_identity"],
            "repeat_selected_owner_identity": payload["second"]["selected_owner_identity"],
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


def _find_claim_effect_authority(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        authority = payload.get("claim_effect_authority")
        if isinstance(authority, dict):
            return authority
        for value in payload.values():
            found = _find_claim_effect_authority(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_claim_effect_authority(value)
            if found:
                return found
    return {}


def _find_claim_effect_boundary(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        boundary = payload.get("claim_effect_boundary")
        if isinstance(boundary, dict) and "installed_payload_dependency" in boundary:
            return boundary
        for value in payload.values():
            found = _find_claim_effect_boundary(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_claim_effect_boundary(value)
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
    test_path = target / "tests" / "test_bounded.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("def test_bounded():\n    assert True\n", encoding="utf-8")
    common = [
        "--target",
        str(target),
        "--task",
        "Continue Generic loop",
        "--changed",
        "src/bounded.py",
        "tests/test_bounded.py",
        "--format",
        "json",
    ]
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

    start_route = _find_planning_route(phases["start"])
    implement_route = _find_planning_route(phases["implement"])
    assert start_route["selected_owner_identity"] == implement_route["selected_owner_identity"]
    selected_proof_command = phases["proof"]["required_commands"][0]
    assert selected_proof_command == "uv run pytest tests/test_bounded.py -q"
    subprocess.run(selected_proof_command, cwd=target, check=True, shell=True)
    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "src/bounded.py",
                "tests/test_bounded.py",
                "--record-receipt",
                "--receipt-command",
                selected_proof_command,
                "--receipt-result",
                "passed",
                "--receipt-plan",
                "generic-loop",
                "--format",
                "json",
            ]
        )
        == 0
    )
    recorded = json.loads(capsys.readouterr().out)["receipt"]
    assert recorded["command"] == selected_proof_command
    assert recorded["plan_id"] == "generic-loop"
    assert recorded["proof_subject"]["identity_complete"] is True
    assert [item["path"] for item in recorded["proof_subject"]["source_inputs"]] == ["src/bounded.py", "tests/test_bounded.py"]

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
                "last",
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
    assert "proof receipt" in json.dumps(closeout).lower()

    assert cli.main(["summary", "--target", str(target), "--select", "planning_record", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["values"]["planning_record"]["status"] == "unavailable"

    assert cli.main(["start", "--target", str(target), "--task", "Begin unrelated follow-up", "--format", "json"]) == 0
    resumed = json.loads(capsys.readouterr().out)
    assert resumed["context"]["active_state"].get("planning_record", {"status": "unavailable"})["status"] == "unavailable"
    assert "continuation_capsule" not in resumed
