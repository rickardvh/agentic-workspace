from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace.operating_decision import _project_source_owned_guidance, compile_operating_decision
from agentic_workspace.runtime_compatibility import READER_CONTRACT_EPOCH, admit_runtime_compatibility
from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

FIXTURE = Path(__file__).parent / "fixtures" / "dynamic_instruction_scenarios.json"


def _scenario_payload(scenario: dict[str, Any], tmp_path: Path) -> dict[str, Any]:
    runner = scenario["runner"]
    inputs = scenario["input"]
    if runner == "planning-route":
        return _planning_route_decision_payload(inputs, planning_revision={"revision_id": "planning-r1"})
    if runner == "operating-decision":
        return compile_operating_decision(inputs=inputs)
    if runner == "incompatible-runtime":
        config = tmp_path / ".agentic-workspace" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text(
            "schema_version = 1\n\n[cli_compatibility]\n"
            f"minimum_reader_epoch = {READER_CONTRACT_EPOCH + int(inputs['minimum_reader_epoch_delta'])}\n",
            encoding="utf-8",
        )
        return admit_runtime_compatibility(tmp_path)
    if runner == "causal-block":
        return compile_operating_decision(
            inputs={
                "denied_effect": True,
                "provenance": {"blocking_source_owner": inputs["owner"]},
            }
        )
    if runner == "coherence":
        first = compile_operating_decision(inputs=inputs)
        second = compile_operating_decision(inputs=inputs)
        return {"first": first, "second": second}
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
        )
    if runner == "source-guidance":
        return _project_source_owned_guidance(
            {
                "authorities": [
                    {
                        "surface": inputs["surface"],
                        "owner": "skill registry",
                        "authority_class": "canonical",
                        "decision_dimension": inputs["decision_dimension"],
                        "proof_route": "skill dependency proof",
                        "source": {
                            "id": inputs["source_ref"],
                            "revision": "sha256:" + "3" * 64,
                            "freshness": "current",
                        },
                    }
                ]
            }
        )
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


@pytest.mark.parametrize("scenario", json.loads(FIXTURE.read_text(encoding="utf-8"))["scenarios"], ids=lambda item: item["id"])
def test_dynamic_instruction_scenario(scenario: dict[str, Any], tmp_path: Path) -> None:
    payload = _scenario_payload(scenario, tmp_path)
    _assert_expected(scenario, payload)

    output_bytes = len(json.dumps(_first_line_projection(scenario, payload), sort_keys=True, separators=(",", ":")).encode("utf-8"))
    assert output_bytes <= scenario["burden"]["max_output_bytes"]
    assert scenario["burden"]["max_aw_invocations"] == 1


def test_generic_operating_loop_reaches_terminal_state_without_stale_continuation(tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "schema_version = 1\n\n[cli_compatibility]\n"
        f"minimum_reader_epoch = {READER_CONTRACT_EPOCH}\n"
        'required_reader_capabilities = ["pre-state-runtime-compatibility-v1"]\n',
        encoding="utf-8",
    )
    admission = admit_runtime_compatibility(tmp_path)
    assert admission["status"] == "admitted"

    route = _planning_route_decision_payload(
        {"task_relation": "continues-selected-owner", "owner_posture": "current", "implementation_allowed": True},
        planning_revision={"revision_id": "planning-r1"},
    )
    assert route["task_relation"] == "continues-selected-owner"

    base = {
        "revisions": {"compatibility": admission["identity_digest"], "planning": "planning-r1"},
        "current_work": {"id": "bounded-child", "task_relation": route["task_relation"]},
        "selected_owner": {"id": "generic-plan", "revision": "owner-r1"},
    }
    implement = compile_operating_decision(
        inputs={**base, "revisions": {**base["revisions"], "changed_surfaces": "src-r1"}, "terminal_state": "CONTINUE"}
    )
    proof = compile_operating_decision(
        inputs={**base, "revisions": {**base["revisions"], "proof": "focused-proof-r1"}, "terminal_state": "CONTINUE"}
    )
    handoff = compile_operating_decision(
        inputs={**base, "revisions": {**base["revisions"], "proof": "focused-proof-r1"}, "terminal_state": "HANDOFF"}
    )
    complete_inputs = {
        "revisions": {"compatibility": admission["identity_digest"], "planning": "planning-r2", "proof": "focused-proof-r1"},
        "current_work": {},
        "selected_owner": {},
        "terminal_state": "COMPLETE",
    }
    complete = compile_operating_decision(inputs=complete_inputs)

    assert implement["decision_id"] != proof["decision_id"] != handoff["decision_id"] != complete["decision_id"]
    resumed = compile_operating_decision(inputs=complete_inputs)
    assert resumed["decision_id"] == complete["decision_id"]
    assert resumed["selected_owner"] == {}
    assert resumed["current_work"] == {}
    assert resumed["terminal_state"] == "COMPLETE"
    assert resumed["blocked_claim_classes"] == []
