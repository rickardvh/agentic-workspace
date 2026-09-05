from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace.decision import DecisionContractError, compile_source_decision

ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads((ROOT / "tests/vectors/source_decision.json").read_text(encoding="utf-8"))
CAPABILITY_CONTRACT = json.loads((ROOT / "tests/vectors/capability_contract.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "src/agentic_workspace/contracts/schemas/source_decision_input.schema.json").read_text(encoding="utf-8"))


def _select(value: object, path: str) -> object:
    current = value
    for part in path.split("."):
        current = current[int(part)] if isinstance(current, list) else current[part]  # type: ignore[index]
    return current


def _direct(binary: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(binary)], input=json.dumps(payload), text=True, capture_output=True, check=False)


def _authority_bearing(payload: dict[str, Any]) -> bool:
    intent = payload.get("intent", {})
    if isinstance(intent, dict) and ("outcome" in intent or "public_request" in intent):
        return True
    for contribution in payload.get("contributions", []):
        if not isinstance(contribution, dict):
            continue
        if any(contribution.get(field) for field in ("actions", "blockers", "decisions", "outcome", "request_response")):
            return True
        claims = contribution.get("claims", {})
        if isinstance(claims, dict) and (claims.get("allowed") or claims.get("blocked")):
            return True
    return False


def _expanded(payload: dict[str, Any]) -> dict[str, Any]:
    expanded = deepcopy(payload)
    if _authority_bearing(expanded) and "capability_contract" not in expanded:
        expanded["capability_contract"] = deepcopy(CAPABILITY_CONTRACT)
    return expanded


def _compile(payload: dict[str, Any]) -> dict[str, Any]:
    return compile_source_decision(
        payload["contributions"],
        intent=payload.get("intent"),
        capability_contract=payload.get("capability_contract"),
    )


def test_declarative_schema_accepts_shared_success_vectors() -> None:
    validator = Draft202012Validator(SCHEMA)
    for vector in VECTORS["cases"]:
        assert list(validator.iter_errors(_expanded(vector["input"]))) == [], vector["id"]
    for vector in VECTORS["equivalent_inputs"]:
        for payload in vector["inputs"]:
            assert list(validator.iter_errors(_expanded(payload))) == [], vector["id"]


def test_python_and_json_execute_the_same_success_vectors(shared_core_binary: Path) -> None:
    for vector in VECTORS["cases"]:
        payload = _expanded(vector["input"])
        direct = _direct(shared_core_binary, payload)
        assert direct.returncode == 0, vector["id"]
        expected = json.loads(direct.stdout)
        actual = compile_source_decision(
            payload["contributions"], intent=payload["intent"], capability_contract=payload.get("capability_contract")
        )
        assert actual == expected
        for path, value in vector["expect"].items():
            assert _select(actual, path) == value, f"{vector['id']}: {path}"


def test_python_and_json_share_fail_closed_errors(shared_core_binary: Path) -> None:
    for vector in VECTORS["error_cases"]:
        payload = _expanded(vector["input"])
        direct = _direct(shared_core_binary, payload)
        assert direct.returncode == 2
        assert vector["error_contains"] in json.loads(direct.stderr)["error"]["message"]
        with pytest.raises(DecisionContractError, match=vector["error_contains"]):
            compile_source_decision(
                payload["contributions"], intent=payload["intent"], capability_contract=payload.get("capability_contract")
            )


def test_exact_action_identity_separates_arguments_and_currentness(shared_core_binary: Path) -> None:
    actions = [
        {"operation_id": "planning.advance", "arguments": {"item": "a"}, "effects": ["planning-state"]},
        {"operation_id": "planning.advance", "arguments": {"item": "b"}, "effects": ["planning-state"]},
    ]
    ambiguous = compile_source_decision(
        [{"owner": "planning", "revision": "p1", "actions": actions}], capability_contract=CAPABILITY_CONTRACT
    )
    pending = ambiguous["pending_consequences"]["actions"]
    assert pending[0]["consequence_id"] != pending[1]["consequence_id"]

    selected = compile_source_decision(
        [
            {
                "owner": "planning",
                "revision": "p1",
                "actions": actions,
                "blockers": [
                    {
                        "code": "first-not-ready",
                        "message": "only the first exact invocation is constrained",
                        "affects": [pending[0]["consequence_id"]],
                    }
                ],
            }
        ],
        capability_contract=CAPABILITY_CONTRACT,
    )
    assert selected["primary_action"]["consequence_id"] == pending[1]["consequence_id"]

    next_revision = compile_source_decision(
        [{"owner": "planning", "revision": "p2", "actions": [actions[1]]}], capability_contract=CAPABILITY_CONTRACT
    )
    assert next_revision["primary_action"]["consequence_id"] != pending[1]["consequence_id"]


def test_semantic_routes_do_not_infer_from_task_text_or_widen_authority(shared_core_binary: Path) -> None:
    contribution = {
        "owner": "workspace",
        "revision": "w1",
        "actions": [{"operation_id": "workspace.inspect", "effects": ["workspace-read"]}],
        "claims": {"allowed": ["workspace-progress"]},
    }
    lexical_only = compile_source_decision([contribution], capability_contract=CAPABILITY_CONTRACT)
    assert "semantic_task_routes" not in lexical_only

    route_intent = {
        "current_work": {"kind": "current-work", "id": "work-1"},
        "semantic_route_source": {
            "revision": "sha256:" + "a" * 64,
            "routes": ["github/issues/create"],
        },
        "semantic_task_routes": {
            "posture": "selected",
            "routes": ["github/issues/create"],
            "task_identity": {"kind": "current-work", "id": "work-1"},
            "source_revision": "sha256:" + "a" * 64,
            "provenance": "agent-selected",
            "authority_effect": "applicability-only",
        },
    }
    selected = compile_source_decision([contribution], intent=route_intent, capability_contract=CAPABILITY_CONTRACT)
    assert selected["primary_action"]["consequence_id"] == lexical_only["primary_action"]["consequence_id"]
    assert selected["primary_action"]["effects"] == lexical_only["primary_action"]["effects"]
    assert selected["claim_boundary"] == lexical_only["claim_boundary"]


def test_node_binding_executes_the_same_core(shared_core_binary: Path) -> None:
    subprocess.run(
        ["node", "--test", "bindings/node/test/semantic-decision.test.mjs"],
        cwd=ROOT,
        env={**os.environ, "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)},
        check=True,
    )


def test_target_bindings_cannot_hide_reducer_semantics() -> None:
    forbidden = ("terminal", "settled", "blockers", "affects", "operation_id", "priority", "consequence_id")
    for path in (ROOT / "src/agentic_workspace/decision.py", ROOT / "bindings/node/semantic-decision.mjs"):
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 80
        assert not any(token in source for token in forbidden)


def test_authority_bearing_contributions_require_an_admitted_capability_owner(shared_core_binary: Path) -> None:
    with pytest.raises(DecisionContractError, match="requires a current capability owner declaration"):
        compile_source_decision([{"owner": "workspace", "revision": "w1", "actions": [{"operation_id": "workspace.inspect"}]}])


def test_capability_domains_effects_and_claims_have_one_owner(shared_core_binary: Path) -> None:
    conflicting_domain = deepcopy(CAPABILITY_CONTRACT)
    conflicting_domain["owners"][0]["domains"] = ["workspace"]
    with pytest.raises(DecisionContractError, match="domain workspace has conflicting owners"):
        compile_source_decision([], capability_contract=conflicting_domain)

    conflicting_claim = deepcopy(CAPABILITY_CONTRACT)
    conflicting_claim["claim_authorities"].append({"claim": "complete", "owner": "workspace"})
    with pytest.raises(DecisionContractError, match="claim complete has conflicting authorities"):
        compile_source_decision([], capability_contract=conflicting_claim)


def test_public_request_is_revision_bound_typed_and_cannot_resolve_as_a_noop(shared_core_binary: Path) -> None:
    vector = next(item for item in VECTORS["cases"] if item["id"] == "typed-public-request-returns-an-exact-owner-action")
    payload = _expanded(vector["input"])
    resolved = _compile(payload)
    assert resolved["request_resolution"]["status"] == "action"
    assert resolved["request_resolution"]["consequence_ids"] == [resolved["primary_action"]["consequence_id"]]
    assert "operation_id" not in payload["intent"]["public_request"]
    assert resolved["primary_action"]["arguments"] != payload["intent"]["public_request"]["arguments"]
    assert resolved["primary_action"]["operation_id"] == "example.finish"

    mutations = [
        ("stale for the current task identity", lambda value: value["intent"]["public_request"]["task_identity"].update(id="other")),
        (
            "stale for the current capability contract revision",
            lambda value: value["intent"]["public_request"].update(capability_revision="sha256:" + "d" * 64),
        ),
        ("stale for capability owner", lambda value: value["intent"]["public_request"].update(owner_revision="ext2")),
        ("violate input_schema", lambda value: value["intent"]["public_request"]["arguments"].update(subject=17)),
        ("violate input_schema", lambda value: value["intent"]["public_request"]["arguments"].update(hidden_command="run")),
        ("stale for its source revision", lambda value: value["intent"]["public_request"].update(source_revision="ext2")),
    ]
    for message, mutate in mutations:
        changed = deepcopy(payload)
        mutate(changed)
        with pytest.raises(DecisionContractError, match=message):
            _compile(changed)

    no_response = deepcopy(payload)
    no_response["contributions"][0].pop("request_response")
    with pytest.raises(DecisionContractError, match="requires exactly one owner response"):
        _compile(no_response)

    mixed_response = deepcopy(payload)
    mixed_response["contributions"][0]["blockers"] = [{"code": "also-blocked", "message": "competing response", "affects": ["task"]}]
    with pytest.raises(DecisionContractError, match="one exact returned action without a competing consequence"):
        _compile(mixed_response)


def test_current_work_does_not_require_semantic_classification_or_module_context(shared_core_binary: Path) -> None:
    decision = compile_source_decision([], intent={"current_work": {"kind": "current-work", "id": "direct-1"}})
    assert decision["status"] == "direct"
    assert "semantic_task_routes" not in decision
    assert "capability_revision" not in decision
