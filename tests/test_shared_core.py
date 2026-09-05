from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace.decision import DecisionContractError, admit_invocation, answer_decision, compile_source_decision, prepare_request

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
        {"dependency_revision": "p1", "operation_id": "planning.advance", "arguments": {"item": "a"}, "effects": ["planning-state"]},
        {"dependency_revision": "p1", "operation_id": "planning.advance", "arguments": {"item": "b"}, "effects": ["planning-state"]},
    ]
    ambiguous = compile_source_decision(
        [{"owner": "planning", "revision": "p1", "actions": actions}], capability_contract=CAPABILITY_CONTRACT
    )
    pending = ambiguous["pending_consequences"]["actions"]
    assert pending[0]["consequence_id"] != pending[1]["consequence_id"]

    scoped_contract = deepcopy(CAPABILITY_CONTRACT)
    scoped_contract["restriction_authorities"] = [{"owner": "planning", "affects": [pending[0]["consequence_id"]]}]
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
        capability_contract=scoped_contract,
    )
    assert selected["primary_action"]["consequence_id"] == pending[1]["consequence_id"]

    next_revision = compile_source_decision(
        [{"owner": "planning", "revision": "p2", "actions": [{**actions[1], "arguments": pending[1]["arguments"]}]}],
        capability_contract=CAPABILITY_CONTRACT,
    )
    assert next_revision["primary_action"]["consequence_id"] == pending[1]["consequence_id"]


def test_semantic_routes_do_not_infer_from_task_text_or_widen_authority(shared_core_binary: Path) -> None:
    contribution = {
        "owner": "workspace",
        "revision": "w1",
        "actions": [{"dependency_revision": "w1", "operation_id": "workspace.inspect", "effects": ["workspace-read"]}],
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
        assert len(source.splitlines()) <= 95
        assert not any(token in source for token in forbidden)


def test_authority_bearing_contributions_require_an_admitted_capability_owner(shared_core_binary: Path) -> None:
    with pytest.raises(DecisionContractError, match="requires a current capability owner declaration"):
        compile_source_decision(
            [{"owner": "workspace", "revision": "w1", "actions": [{"dependency_revision": "w1", "operation_id": "workspace.inspect"}]}]
        )


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
    mixed_response["capability_contract"]["restriction_authorities"].append({"owner": "example.external", "affects": ["task"]})
    mixed_response["contributions"][0]["blockers"] = [{"code": "also-blocked", "message": "competing response", "affects": ["task"]}]
    assert _compile(mixed_response)["request_resolution"] == resolved["request_resolution"]


def test_current_work_does_not_require_semantic_classification_or_module_context(shared_core_binary: Path) -> None:
    decision = compile_source_decision([], intent={"current_work": {"kind": "current-work", "id": "direct-1"}})
    assert decision["status"] == "direct"
    assert "semantic_task_routes" not in decision
    assert "capability_revision" not in decision


def test_action_lifetimes_and_exact_admission(shared_core_binary: Path) -> None:
    payload = _expanded(next(v["input"] for v in VECTORS["cases"] if v["id"] == "action-material-dependencies"))
    first = _compile(payload)
    action = first["primary_action"]
    unrelated = deepcopy(payload)
    unrelated["contributions"][0]["revision"] = "owner-advice-changed"
    unrelated["contributions"].append({"owner": "memory", "revision": "new-advice", "facts": {"advice": "optional"}})
    unrelated["capability_contract"]["revision"] = "sha256:" + "e" * 64
    current = _compile(unrelated)
    assert current["input_revision"] != first["input_revision"]
    assert current["primary_action"] == action
    assert admit_invocation(current, action)["disposition"] == "execute"

    relevant = deepcopy(unrelated)
    relevant["contributions"][0]["actions"][0]["dependency_revision"] = "proof-2"
    changed = _compile(relevant)
    assert changed["primary_action"]["idempotency_key"] == action["idempotency_key"]
    assert changed["primary_action"]["consequence_id"] != action["consequence_id"]
    with pytest.raises(DecisionContractError, match="stale or differs"):
        admit_invocation(changed, action)
    assert admit_invocation(changed, changed["primary_action"], action)["disposition"] == "replay"

    repeat = deepcopy(relevant)
    repeat["contributions"][0]["actions"][0]["effect_generation"] = "owner-authorized-repeat-2"
    assert _compile(repeat)["primary_action"]["idempotency_key"] != action["idempotency_key"]
    for field, value in (
        ("arguments", {"item": "wider"}),
        ("effects", []),
        ("authority", "other"),
        ("idempotency_key", "fresh"),
        ("source_owner", "other"),
        ("expected_dependency_revision", "other"),
        ("unexpected", True),
    ):
        with pytest.raises(DecisionContractError, match="stale or differs"):
            admit_invocation(current, {**action, field: value})

    removed = deepcopy(unrelated)
    removed["contributions"][0]["actions"] = []
    with pytest.raises(DecisionContractError, match="stale or differs"):
        admit_invocation(_compile(removed), action)
    # A trusted exact receipt permits a read-only replay after owner completion.
    assert admit_invocation(_compile(removed), action, action)["disposition"] == "replay"


def test_client_can_invoke_an_exact_choice_from_ready_set(shared_core_binary: Path) -> None:
    payload = next(v["input"] for v in VECTORS["cases"] if v["id"] == "two-independent-ready-actions")
    decision = _compile(payload)
    assert decision["primary_action"] is None
    for action in decision["ready_actions"]:
        assert admit_invocation(decision, action)["disposition"] == "execute"
        with pytest.raises(DecisionContractError, match="stale or differs"):
            admit_invocation(decision, {**action, "arguments": {"widen": True}})
    changed = deepcopy(payload)
    changed["capability_contract"]["owners"][1]["operations"][0]["reads"] = ["a"]
    with pytest.raises(DecisionContractError, match="stale or differs"):
        admit_invocation(_compile(changed), decision["ready_actions"][0])


def test_request_identity_and_local_response_are_publicly_constructible(shared_core_binary: Path) -> None:
    payload = _expanded(next(v["input"] for v in VECTORS["cases"] if v["id"] == "typed-public-request-returns-an-exact-owner-action"))
    intent = payload["intent"]
    prepared = prepare_request(intent["public_request"], intent["current_work"], payload["capability_contract"])
    assert prepared["request"] == intent["public_request"]
    assert prepared["identity"] == payload["contributions"][0]["request_response"]["request_identity"]
    # A source owner can derive exact consequence IDs without a hash algorithm
    # or public request dispatch loop in a binding.
    owner = deepcopy(payload["contributions"][0])
    owner.pop("request_response")
    derived = compile_source_decision([owner], capability_contract=payload["capability_contract"])
    owner["request_response"] = {
        "request_identity": prepared["identity"],
        "status": "action",
        "consequence_ids": [derived["primary_action"]["consequence_id"]],
    }
    owner["actions"].append({**deepcopy(owner["actions"][0]), "arguments": {"subject": "unrelated"}})
    answer = compile_source_decision([owner], intent=intent, capability_contract=payload["capability_contract"])
    assert answer["request_resolution"]["consequence_ids"] == owner["request_response"]["consequence_ids"]
    assert len(answer["pending_consequences"]["actions"]) == 2
    changed = deepcopy(intent)
    changed["public_request"]["arguments"]["subject"]["name"] = "other-valid-subject"
    with pytest.raises(DecisionContractError, match="references a different request"):
        compile_source_decision([owner], intent=changed, capability_contract=payload["capability_contract"])
    with pytest.raises(DecisionContractError, match="exact current owner consequences"):
        invalid = deepcopy(owner)
        invalid["request_response"]["consequence_ids"] = ["action:absent"]
        compile_source_decision([invalid], intent=intent, capability_contract=payload["capability_contract"])


def test_human_answer_uses_only_current_returned_authority(shared_core_binary: Path) -> None:
    payload = _expanded(next(v["input"] for v in VECTORS["cases"] if v["id"] == "task-decision-is-current-and-bounded"))
    decision = _compile(payload)
    question = decision["pending_consequences"]["decisions"][0]
    prepared = answer_decision(decision, question["consequence_id"], "mit", payload["capability_contract"])
    assert prepared["request"] == {**question["response_request"], "arguments": {"answer": "mit"}}
    direct = _direct(
        shared_core_binary,
        {
            "answer_decision": {
                "decision": decision,
                "question": question["consequence_id"],
                "answer": "mit",
                "capability_contract": payload["capability_contract"],
            }
        },
    )
    assert direct.returncode == 0
    assert json.loads(direct.stdout) == prepared
    with pytest.raises(DecisionContractError, match="not a returned bounded choice"):
        answer_decision(decision, question["consequence_id"], "hidden-choice", payload["capability_contract"])
    changed = deepcopy(payload)
    changed["contributions"][0]["revision"] = "r3"
    with pytest.raises(DecisionContractError, match="stale or absent"):
        answer_decision(_compile(changed), question["consequence_id"], "mit", payload["capability_contract"])
    contract = deepcopy(payload["capability_contract"])
    contract["revision"] = "sha256:" + "f" * 64
    with pytest.raises(DecisionContractError, match="stale for the current capability"):
        answer_decision(decision, question["consequence_id"], "mit", contract)
    tampered = _direct(
        shared_core_binary,
        {
            "answer_decision": {
                "decision": decision,
                "question": question["consequence_id"],
                "answer": "mit",
                "capability_contract": payload["capability_contract"],
                "effects": ["other"],
            }
        },
    )
    assert tampered.returncode != 0
    assert "unknown field" in tampered.stderr
    opened = deepcopy(payload)
    opened["contributions"][0]["decisions"][0].pop("choices")
    current = _compile(opened)
    key = current["pending_consequences"]["decisions"][0]["consequence_id"]
    assert answer_decision(current, key, "human judgment", payload["capability_contract"])["request"]["arguments"] == {
        "answer": "human judgment"
    }
    with pytest.raises(DecisionContractError, match="violate input_schema"):
        answer_decision(current, key, {"hidden_target": "other"}, payload["capability_contract"])
