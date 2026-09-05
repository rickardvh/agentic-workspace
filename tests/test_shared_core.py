from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace.decision import (
    DecisionContractError,
    admit_attempt,
    admit_invocation,
    admit_stored_attempt,
    answer_decision,
    commit_attempt,
    commit_stored_attempt,
    compile_source_decision,
    operation_result,
    prepare_request,
)

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
        assert len(source.splitlines()) <= 140
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


def test_result_composition_is_shared_and_never_reuses_a_view(shared_core_binary: Path) -> None:
    payload = _expanded(next(v["input"] for v in VECTORS["cases"] if v["id"] == "action-material-dependencies"))
    current = _compile(payload)
    invocation = current["primary_action"]
    outcome = {"status": "applied", "effects": invocation["effects"], "value": {"exact": "committed"}}
    for view in (current, compile_source_decision([]), None):
        result = operation_result(invocation, outcome, view)
        direct = _direct(shared_core_binary, {"operation_result": {"invocation": invocation, "outcome": outcome, "decision": view}})
        assert direct.returncode == 0
        assert json.loads(direct.stdout) == result
        assert result["value"] == outcome["value"]
        assert result["next_decision"] == view
        assert result["continuation_status"] == ("unavailable" if view is None else "current")
    for invalid, message in (
        ({**outcome, "effects": ["unowned"]}, "widened"),
        ({**outcome, "status": "guessed"}, "status must"),
        ({**outcome, "next_decision": current}, "unknown field"),
    ):
        with pytest.raises(DecisionContractError, match=message):
            operation_result(invocation, invalid, current)


def test_replay_requires_current_exact_operation_semantics(shared_core_binary: Path) -> None:
    payload = _expanded(next(v["input"] for v in VECTORS["cases"] if v["id"] == "action-material-dependencies"))
    first = _compile(payload)
    original = first["primary_action"]
    for change in ("semantic_revision", "result_kind", "input_schema"):
        revised = deepcopy(payload)
        operation = next(
            op for owner in revised["capability_contract"]["owners"] for op in owner["operations"] if op["id"] == original["operation_id"]
        )
        operation[change] = {**operation[change], "description": "revised semantic contract"} if change == "input_schema" else "upgraded/v2"
        current = _compile(revised)
        assert current["primary_action"]["idempotency_key"] == original["idempotency_key"]
        assert current["primary_action"]["operation_revision"] != original["operation_revision"]
        for submitted in (original, current["primary_action"]):
            with pytest.raises(DecisionContractError, match="current operation semantics"):
                admit_invocation(current, submitted, original)
    removed = deepcopy(payload)
    removed["contributions"][0]["actions"] = []
    current = _compile(removed)
    assert admit_invocation(current, original, original)["disposition"] == "replay"
    current["operation_revisions"].pop(original["operation_id"])
    with pytest.raises(DecisionContractError, match="current operation semantics"):
        admit_invocation(current, original, original)
    malformed = {**original, "operation_revision": None}
    with pytest.raises(DecisionContractError, match="current operation semantics"):
        admit_invocation(first, malformed, malformed)


def test_attempt_identity_uncertainty_and_committed_replay(shared_core_binary: Path) -> None:
    payload = _expanded(next(v["input"] for v in VECTORS["cases"] if v["id"] == "action-material-dependencies"))
    decision = _compile(payload)
    action = decision["primary_action"]
    admitted = admit_attempt(decision, action)
    record = admitted["record"]
    assert admitted["disposition"] == "execute"
    assert admitted["logical_effect_id"] == action["idempotency_key"]
    assert admitted["attempt_id"] != admitted["logical_effect_id"]
    assert record["outcome"] is None
    assert admit_attempt(decision, action, record)["disposition"] == "uncertain"
    changed = deepcopy(payload)
    changed["contributions"][0]["revision"] = "unrelated-change"
    changed["contributions"][0]["actions"][0]["dependency_revision"] = "relevant-change"
    current = _compile(changed)
    assert admit_attempt(current, current["primary_action"], record)["record"] == record
    committed = commit_attempt(record, {"status": "applied", "effects": action["effects"], "value": {"count": 1}})
    replay = admit_attempt(current, current["primary_action"], committed)
    assert replay["disposition"] == "replay"
    assert replay["attempt_id"] == admitted["attempt_id"]
    assert "next_decision" not in committed
    direct = _direct(
        shared_core_binary, {"admit_attempt": {"decision": current, "invocation": current["primary_action"], "record": committed}}
    )
    assert json.loads(direct.stdout) == replay
    for mutate in (
        lambda r: r.update(attempt_id="retry-random"),
        lambda r: r["outcome"].update(value="hand-edited"),
        lambda r: r.update(next_decision=decision),
    ):
        invalid = deepcopy(committed)
        mutate(invalid)
        with pytest.raises(DecisionContractError):
            admit_attempt(current, current["primary_action"], invalid)
    with pytest.raises(DecisionContractError, match="cannot change its outcome"):
        commit_attempt(committed, {"status": "applied", "effects": action["effects"], "value": 2})
    changed["contributions"][0]["actions"][0]["effect_generation"] = "authorized-repeat"
    repeated = _compile(changed)
    assert admit_attempt(repeated, repeated["primary_action"])["attempt_id"] != admitted["attempt_id"]
    with pytest.raises(DecisionContractError):
        admit_attempt(repeated, repeated["primary_action"], committed)


def _stored_payload(target: Path) -> dict[str, Any]:
    # The responsible owner derives the target in its exact declared operation.
    payload = _expanded(next(v["input"] for v in VECTORS["cases"] if v["id"] == "action-material-dependencies"))
    action = payload["contributions"][0]["actions"][0]
    action["arguments"]["target"] = str(target)
    operation = next(
        op for owner in payload["capability_contract"]["owners"] for op in owner["operations"] if op["id"] == action["operation_id"]
    )
    operation["input_schema"]["properties"]["target"] = {"type": "string", "minLength": 1}
    return payload


def test_stored_attempt_requires_custody_and_replays_in_a_fresh_process(shared_core_binary: Path, tmp_path: Path) -> None:
    payload = _stored_payload(tmp_path)
    decision = _compile(payload)
    action = decision["primary_action"]
    admitted = admit_stored_attempt(str(tmp_path), decision, action)
    custody = admitted["custody"]
    schema = json.loads((ROOT / "src/agentic_workspace/contracts/schemas/effect_attempt.schema.json").read_text())
    Draft202012Validator(schema).validate(admitted["record"])
    Draft202012Validator(schema["$defs"]["evidence"]).validate(custody["attempt"])
    path = tmp_path / custody["attempt"]["path"]
    before = path.read_bytes()
    assert admitted["disposition"] == "execute"
    assert admit_stored_attempt(str(tmp_path), decision, action, custody)["disposition"] == "uncertain"
    with pytest.raises(DecisionContractError, match="requires exact custody"):
        admit_stored_attempt(str(tmp_path), decision, action)
    assert path.read_bytes() == before
    wrong = deepcopy(custody)
    wrong["attempt"]["owner"] = "invented-owner"
    with pytest.raises(DecisionContractError, match="different owner"):
        admit_stored_attempt(str(tmp_path), decision, action, wrong)
    outcome = {"status": "applied", "effects": action["effects"], "value": {"committed": True}}
    committed = commit_stored_attempt(str(tmp_path), custody, outcome)
    Draft202012Validator(schema).validate(committed["record"])
    assert path.read_bytes() == before
    # Losing the newly returned custody cannot authorize reading a result by shape.
    assert admit_stored_attempt(str(tmp_path), decision, action, custody)["disposition"] == "uncertain"
    replay = admit_stored_attempt(str(tmp_path), decision, action, committed["custody"])
    assert replay["disposition"] == "replay"
    assert replay["record"]["outcome"] == outcome
    direct = _direct(
        shared_core_binary,
        {"admit_stored_attempt": {"target": str(tmp_path), "decision": decision, "invocation": action, "custody": committed["custody"]}},
    )
    assert json.loads(direct.stdout) == replay
    changed = deepcopy(payload)
    changed["contributions"][0]["revision"] = "unrelated"
    current = _compile(changed)
    assert admit_stored_attempt(str(tmp_path), current, current["primary_action"], committed["custody"])["disposition"] == "replay"
    changed["contributions"][0]["actions"][0]["effect_generation"] = "owner-repeat"
    repeat = _compile(changed)
    repeated = admit_stored_attempt(str(tmp_path), repeat, repeat["primary_action"])
    assert repeated["custody"]["attempt"]["path"] != custody["attempt"]["path"]
    result_path = tmp_path / committed["custody"]["committed"]["path"]
    result_path.write_bytes(b'{"incomplete":')
    with pytest.raises(DecisionContractError, match="differs from exact custody"):
        admit_stored_attempt(str(tmp_path), decision, action, committed["custody"])
    assert result_path.read_bytes() == b'{"incomplete":'


@pytest.mark.parametrize("phase", ["before-effect", "after-effect"])
def test_interrupted_external_process_never_blindly_retries(shared_core_binary: Path, tmp_path: Path, phase: str) -> None:
    import sys

    payload = _stored_payload(tmp_path)
    decision = _compile(payload)
    action = decision["primary_action"]
    worker = """
import json, os, subprocess, sys
from pathlib import Path
request = json.loads(sys.stdin.read())
p = subprocess.run([sys.argv[1]], input=json.dumps(request), text=True, capture_output=True)
if p.returncode: sys.exit(p.returncode)
admission = json.loads(p.stdout)
print(json.dumps(admission), flush=True)
if sys.argv[3] == 'after-effect': Path(sys.argv[2]).write_text('effect occurred')
os._exit(29)
"""
    marker = tmp_path / "external-effect"
    request = {"admit_stored_attempt": {"target": str(tmp_path), "decision": decision, "invocation": action}}
    crashed = subprocess.run(
        [sys.executable, "-c", worker, str(shared_core_binary), str(marker), phase],
        input=json.dumps(request),
        text=True,
        capture_output=True,
    )
    assert crashed.returncode == 29
    admission = json.loads(crashed.stdout)
    assert marker.exists() == (phase == "after-effect")
    recovered = admit_stored_attempt(str(tmp_path), decision, action, admission["custody"])
    assert recovered["disposition"] == "uncertain"
    assert recovered["attempt_id"] == admission["attempt_id"]


def test_two_processes_cannot_acquire_the_same_effect(shared_core_binary: Path, tmp_path: Path) -> None:
    payload = _stored_payload(tmp_path)
    decision = _compile(payload)
    request = json.dumps(
        {"admit_stored_attempt": {"target": str(tmp_path), "decision": decision, "invocation": decision["primary_action"]}}
    )
    processes = [
        subprocess.Popen([str(shared_core_binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(2)
    ]
    for process in processes:
        assert process.stdin is not None
        process.stdin.write(request)
        process.stdin.close()
        process.stdin = None
    results = [process.communicate(timeout=20) for process in processes]
    assert sorted(process.returncode for process in processes) == [0, 2]
    successes = [json.loads(stdout) for process, (stdout, _) in zip(processes, results, strict=True) if process.returncode == 0]
    assert len(successes) == 1
    assert successes[0]["disposition"] == "execute"
    assert len(list(tmp_path.rglob("*.attempt.json"))) == 1


@pytest.mark.parametrize(
    "content",
    [{"kind": "planning", "status": "active"}, {"kind": "memory", "value": "retained"}, {"kind": "verification", "status": "passed"}],
)
def test_recognizable_unowned_content_cannot_be_acquired(shared_core_binary: Path, tmp_path: Path, content: dict[str, Any]) -> None:
    payload = _stored_payload(tmp_path)
    decision = _compile(payload)
    action = decision["primary_action"]
    admitted = admit_attempt(decision, action)
    # The artifact path is a deterministic public effect-key projection.
    import hashlib

    key = hashlib.sha256(action["idempotency_key"].encode()).hexdigest()
    path = tmp_path / ".agentic-workspace/local/effects" / f"{key}.attempt.json"
    path.parent.mkdir(parents=True)
    for value in (content, admitted["record"]):
        path.write_text(json.dumps(value))
        before = path.read_bytes()
        with pytest.raises(DecisionContractError, match="requires exact custody"):
            admit_stored_attempt(str(tmp_path), decision, action)
        assert path.read_bytes() == before


def test_stale_admission_creates_no_residue(shared_core_binary: Path, tmp_path: Path) -> None:
    payload = _stored_payload(tmp_path)
    current = _compile(payload)
    with pytest.raises(DecisionContractError, match="stale or differs"):
        admit_stored_attempt(
            str(tmp_path), current, {**current["primary_action"], "arguments": {"target": str(tmp_path), "other": "target"}}
        )
    assert list(tmp_path.iterdir()) == []
    assert compile_source_decision([])["status"] == "direct"
    assert list(tmp_path.iterdir()) == []


def test_effect_storage_rejects_parent_redirection(shared_core_binary: Path, tmp_path: Path) -> None:
    target = tmp_path / "repo"
    outside = tmp_path / "outside"
    target.mkdir()
    outside.mkdir()
    current = _compile(_stored_payload(target))
    link = target / ".agentic-workspace"
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(DecisionContractError):
        admit_stored_attempt(str(target), current, current["primary_action"])
    assert list(outside.iterdir()) == []


def test_stored_effect_cannot_move_to_another_target(shared_core_binary: Path, tmp_path: Path) -> None:
    first, other = tmp_path / "first", tmp_path / "other"
    first.mkdir()
    other.mkdir()
    decision = _compile(_stored_payload(first))
    with pytest.raises(DecisionContractError, match="storage target differs"):
        admit_stored_attempt(str(other), decision, decision["primary_action"])
    assert list(other.iterdir()) == []


@pytest.mark.parametrize("modified_ledger", [False, True])
def test_local_only_uninstall_preserves_usable_effect_custody(shared_core_binary: Path, tmp_path: Path, modified_ledger: bool) -> None:
    from agentic_workspace.config import load_workspace_config
    from agentic_workspace.workspace_runtime_core import _workspace_payload_bytes_for_target, _workspace_uninstall_report

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    decision = _compile(_stored_payload(tmp_path))
    action = decision["primary_action"]
    admitted = admit_stored_attempt(str(tmp_path), decision, action)
    committed = commit_stored_attempt(str(tmp_path), admitted["custody"], {"status": "applied", "effects": action["effects"], "value": 1})
    owner_reference = tmp_path / ".agentic-workspace/local/owner-custody.json"
    owner_reference.write_text(json.dumps(committed["custody"]))
    retained = {path: path.read_bytes() for path in (tmp_path / ".agentic-workspace/local").rglob("*") if path.is_file()}
    relative = Path(".agentic-workspace/WORKFLOW.md")
    package_file = tmp_path / relative
    package_file.write_bytes(_workspace_payload_bytes_for_target(relative, target_root=tmp_path))
    ledger_relative = Path(".agentic-workspace/OWNERSHIP.toml")
    ledger = tmp_path / ledger_relative
    ledger_bytes = _workspace_payload_bytes_for_target(ledger_relative, target_root=tmp_path)
    if modified_ledger:
        ledger_bytes += b"\n# repository-owned amendment\n"
    ledger.write_bytes(ledger_bytes)
    config = load_workspace_config(target_root=tmp_path)
    preview = _workspace_uninstall_report(
        target_root=tmp_path, selected_modules=[], descriptors={}, dry_run=True, config=config, local_only_repo_root=tmp_path
    )
    assert any(a["kind"] == "preserved" and a["path"] == ".agentic-workspace" for a in preview["actions"])
    assert package_file.exists()
    report = _workspace_uninstall_report(
        target_root=tmp_path, selected_modules=[], descriptors={}, dry_run=False, config=config, local_only_repo_root=tmp_path
    )
    expected = "skipped" if modified_ledger else "removed"
    assert any(a["kind"] == expected and a["path"] == relative.as_posix() for a in report["actions"])
    assert package_file.exists() is modified_ledger
    assert ledger.read_bytes() == ledger_bytes
    assert any(a["kind"] == "preserved" and a["path"] == ledger_relative.as_posix() for a in report["actions"])
    assert all(path.read_bytes() == value for path, value in retained.items())
    custody = json.loads(owner_reference.read_text())
    assert admit_stored_attempt(str(tmp_path), decision, action, custody)["disposition"] == "replay"
