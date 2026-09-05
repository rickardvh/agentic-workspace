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
    normalize_decision_record,
    operation_result,
    planning_view,
    prepare_request,
    reconcile_planning,
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
        decision_context=payload.get("decision_context"),
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
        assert len(source.splitlines()) <= 160
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
    from agentic_workspace.workspace_runtime_core import (
        LOCAL_ONLY_IGNORE_BLOCK,
        _workspace_payload_bytes_for_target,
        _workspace_uninstall_report,
    )

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    ignore_files = [tmp_path / ".git/info/exclude", tmp_path / ".gitignore"]
    for path in ignore_files:
        path.write_text(LOCAL_ONLY_IGNORE_BLOCK)
    ignored_before = {path: path.read_bytes() for path in ignore_files}
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
    assert all(path.read_bytes() == value for path, value in ignored_before.items())
    subprocess.run(["git", "check-ignore", "--quiet", str(owner_reference)], cwd=tmp_path, check=True)
    custody = json.loads(owner_reference.read_text())
    assert admit_stored_attempt(str(tmp_path), decision, action, custody)["disposition"] == "replay"


def _planning_context(tmp_path: Path, body: dict[str, Any] | None = None) -> dict[str, Any]:
    import hashlib

    # The test host creates an admitted Planning source from the actual selected
    # execplan, not an invented planning.json or a shape-recognition acquisition.
    source = tmp_path / ".agentic-workspace/planning/execplans/current.plan.json"
    source.parent.mkdir(parents=True)
    raw = (ROOT / "tests/vectors/planning_execplan.json").read_bytes() if body is None else json.dumps(body).encode()
    with source.open("xb") as stream:
        stream.write(raw)
    schema = json.loads((ROOT / "src/agentic_workspace/contracts/schemas/planning_reconciliation.schema.json").read_text())
    contract = deepcopy(CAPABILITY_CONTRACT)
    owner = next(owner for owner in contract["owners"] if owner["owner"] == "planning")
    arguments = {
        **schema["$defs"]["operation_arguments"],
        "$defs": {key: schema["$defs"][key] for key in ["evidence", "state", "subject", "coverage", "reconciliation"]},
        "$schema": schema["$schema"],
    }
    owner["operations"].append(
        {
            "id": "planning.reconcile",
            "semantic_revision": "planning-reconciliation-v1",
            "input_schema": arguments,
            "result_kind": "agentic-planning/reconciliation-result/v1",
            "effects": ["planning-state"],
            "reads": ["planning"],
        }
    )
    return {
        "target": str(tmp_path.resolve()),
        "relevant": True,
        "source": {
            "target": str(tmp_path.resolve()),
            "path": source.relative_to(tmp_path).as_posix(),
            "owner": "planning",
            "revision": "sha256:" + hashlib.sha256(raw).hexdigest(),
        },
        "capability_contract": contract,
    }


def _planning_call(binary: Path, surface: str, context: dict[str, Any], transport: str) -> dict[str, Any]:
    if transport == "python":
        return planning_view(context) if surface == "planning_view" else reconcile_planning(context)
    if transport == "json":
        result = _direct(binary, {surface: context})
    else:
        export = "planningView" if surface == "planning_view" else "reconcilePlanning"
        program = f"import {{ {export} }} from './bindings/node/semantic-decision.mjs'; import fs from 'node:fs'; console.log(JSON.stringify({export}(JSON.parse(fs.readFileSync(0,'utf8')))));"
        result = subprocess.run(
            ["node", "--input-type=module", "-e", program], input=json.dumps(context), capture_output=True, text=True, cwd=ROOT
        )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("transport", ["python", "node", "json"])
def test_real_planning_source_reconciles_and_resumes(shared_core_binary: Path, tmp_path: Path, transport: str) -> None:
    context = _planning_context(tmp_path)
    original = (tmp_path / context["source"]["path"]).read_bytes()
    before = _planning_call(shared_core_binary, "planning_view", context, transport)
    assert not (tmp_path / ".agentic-workspace/local").exists()
    operation = before["primary_action"]
    receipt = operation["arguments"]["reconciliation"]
    assert receipt["coverage"] == {"complete": True, "ambiguities": [], "omitted_history": []}
    source = json.loads(original)
    state = receipt["subject"]["state"]
    assert state["outcome"]["goals"] == source["goal"]
    assert state["scope"]["paths"] == source["touched_paths"]
    assert state["dependencies"]["references"] == source["references"]
    assert state["constraints"]["bounds"] == source["execution_bounds"]
    assert state["frontier"]["next_action"] == source["next_action"]
    assert state["proof"]["declared"] == source["proof"]
    assert state["proof"]["completion_criteria"] == source["completion_criteria"]
    assert state["handoff"]["delegation"] == source["relationships"]["delegation"]
    assert state["residual"]["continuation"] == source["continuation"]
    result = _planning_call(shared_core_binary, "reconcile_planning", {**context, "invocation": operation}, transport)
    assert result["status"] == "applied"
    assert result["value"] == receipt
    assert (tmp_path / context["source"]["path"]).read_bytes() == original
    # Every call starts a new Rust process. All public projections resume from
    # the exact durable custody returned by the completed owner operation.
    restored = {**context, "custody": result["custody"]}
    views = [_planning_call(shared_core_binary, "planning_view", restored, kind) for kind in ["python", "node", "json"]]
    assert views[0] == views[1] == views[2] == result["next_decision"]
    current = views[0]["planning"]
    assert current["current"] is True
    assert current["reconciliation"]["subject"] == receipt["subject"]
    assert views[0]["status"] != "terminal"
    assert views[0]["primary_action"] is None
    assert reconcile_planning({**restored, "invocation": operation})["value"] == receipt


@pytest.mark.parametrize("phase", ["active", "returned", "integration-pending"])
def test_planning_inflight_semantics_and_history_coverage(shared_core_binary: Path, tmp_path: Path, phase: str) -> None:
    body = json.loads((ROOT / "tests/vectors/planning_execplan.json").read_text())
    body["relationships"].update(
        dependencies={"subject": "verification-proof", "revision": "proof-7"},
        assignment={"id": "worker-1", "status": phase},
        returned={"result": "result-7", "status": "awaiting-admission"},
        integration_pending={"subject": "worker-1", "result": "result-7"},
    )
    body["drift_log"] = ["old closed work: must not import"]
    from jsonschema import Draft202012Validator

    former_schema = json.loads((ROOT / ".agentic-workspace/planning/schemas/planning-execplan.schema.json").read_text())
    Draft202012Validator(former_schema).validate(body)
    context = _planning_context(tmp_path, body)
    ambiguous = planning_view(context)
    assert ambiguous["primary_action"] is None
    assert ambiguous["planning"]["reconciliation"]["coverage"]["ambiguities"] == ["drift_log"]
    context["irrelevant_history"] = True  # Explicit agent judgment, not Rust text classification.
    decision = planning_view(context)
    result = reconcile_planning({**context, "invocation": decision["primary_action"]})
    restored = planning_view({**context, "custody": result["custody"]})
    state = restored["planning"]["reconciliation"]["subject"]["state"]
    assert state["frontier"]["phase"] == body["phase"]
    assert state["dependencies"]["declared"] == body["relationships"]["dependencies"]
    assert state["handoff"]["assignment"] == body["relationships"]["assignment"]
    assert state["handoff"]["returned"] == body["relationships"]["returned"]
    assert state["handoff"]["integration_pending"] == body["relationships"]["integration_pending"]
    record_bytes = (tmp_path / result["custody"]["committed"]["path"]).read_bytes()
    assert b"must not import" not in record_bytes
    assert restored["planning"]["reconciliation"]["coverage"]["omitted_history"] == ["drift_log"]


def test_planning_reconciliation_preserves_collisions_and_requires_source_custody(shared_core_binary: Path, tmp_path: Path) -> None:
    import hashlib

    context = _planning_context(tmp_path)
    for owner in ["unowned", "repository", "memory"]:
        with pytest.raises(DecisionContractError, match="not admitted as Planning-owned"):
            planning_view({**context, "source": {**context["source"], "owner": owner}})
    with pytest.raises(DecisionContractError, match="source admission required"):
        planning_view({**context, "source": None})
    decision = planning_view(context)
    operation = decision["primary_action"]
    path = (
        tmp_path / ".agentic-workspace/local/effects" / (hashlib.sha256(operation["idempotency_key"].encode()).hexdigest() + ".result.json")
    )
    path.parent.mkdir(parents=True)
    # Even a valid current Planning reconciliation is not acquisition evidence.
    raw = json.dumps(operation["arguments"]["reconciliation"]).encode()
    path.write_bytes(raw)
    with pytest.raises(DecisionContractError, match="unowned result evidence exists; preserved"):
        reconcile_planning({**context, "invocation": operation})
    assert path.read_bytes() == raw
    assert list(path.parent.iterdir()) == [path]


def test_material_planning_source_change_reopens_but_keeps_subject(shared_core_binary: Path, tmp_path: Path) -> None:
    import hashlib

    context = _planning_context(tmp_path)
    original = planning_view(context)
    operation = original["primary_action"]
    result = reconcile_planning({**context, "invocation": operation})
    unrelated = deepcopy(context)
    unrelated["capability_contract"]["revision"] = "sha256:" + "9" * 64
    assert planning_view(unrelated)["primary_action"] == operation
    source = tmp_path / context["source"]["path"]
    body = json.loads(source.read_text())
    body["next_action"] = "Reconcile returned verification evidence"
    raw = json.dumps(body).encode()
    source.write_bytes(raw)  # Test host updates its existing Planning-owned source.
    with pytest.raises(DecisionContractError, match="former source changed"):
        planning_view({**context, "custody": result["custody"]})
    refreshed = {**context, "source": {**context["source"], "revision": "sha256:" + hashlib.sha256(raw).hexdigest()}}
    current = planning_view(refreshed)["primary_action"]
    before = operation["arguments"]["reconciliation"]["subject"]
    after = current["arguments"]["reconciliation"]["subject"]
    assert before["id"] == after["id"]
    assert before["revision"] != after["revision"]
    with pytest.raises(DecisionContractError):
        reconcile_planning({**refreshed, "invocation": operation})


def test_direct_planning_view_is_quiet_and_interrupted_reconciliation_can_finish(shared_core_binary: Path, tmp_path: Path) -> None:
    direct = planning_view({"target": str(tmp_path), "relevant": False})
    assert direct["relevant_owners"] == []
    assert list(tmp_path.iterdir()) == []
    context = _planning_context(tmp_path)
    operation = planning_view(context)["primary_action"]
    import sys

    worker = """
import os, subprocess, sys
result = subprocess.run([sys.argv[1]], input=sys.stdin.read(), text=True, capture_output=True)
if result.returncode: sys.exit(result.returncode)
print(result.stdout, flush=True)
os._exit(29)
"""
    crashed = subprocess.run(
        [sys.executable, "-c", worker, str(shared_core_binary)],
        input=json.dumps({"admit_stored_attempt": {"target": str(tmp_path), "decision": planning_view(context), "invocation": operation}}),
        text=True,
        capture_output=True,
    )
    assert crashed.returncode == 29
    admission = json.loads(crashed.stdout)
    resumed = {**context, "custody": admission["custody"]}
    before = planning_view(resumed)
    assert before["planning"]["current"] is False
    assert before["primary_action"] == operation
    assert not list((tmp_path / ".agentic-workspace/local/effects").glob("*.result.json"))
    result = reconcile_planning({**resumed, "invocation": before["primary_action"]})
    record = json.loads((tmp_path / result["custody"]["committed"]["path"]).read_text())
    assert record["attempt_id"] == admission["attempt_id"]
    assert record["invocation"]["idempotency_key"] == admission["logical_effect_id"]
    assert result["status"] == "applied"
    assert (tmp_path / context["source"]["path"]).is_file()


def test_planning_unmapped_current_semantics_block_complete_reconciliation(shared_core_binary: Path, tmp_path: Path) -> None:
    body = json.loads((ROOT / "tests/vectors/planning_execplan.json").read_text())
    body["stop_conditions"] = {"human_choice": "Do not proceed before acceptance"}
    context = {**_planning_context(tmp_path, body), "irrelevant_history": True}
    decision = planning_view(context)
    assert decision["primary_action"] is None
    assert decision["planning"]["reconciliation"]["coverage"] == {
        "complete": False,
        "ambiguities": ["stop_conditions"],
        "omitted_history": [],
    }
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("residue", ["partial", "committed-reply-lost"])
def test_planning_recovery_preserves_result_without_exact_custody(shared_core_binary: Path, tmp_path: Path, residue: str) -> None:
    import hashlib

    context = _planning_context(tmp_path)
    decision = planning_view(context)
    action = decision["primary_action"]
    admitted = admit_stored_attempt(str(tmp_path), decision, action)
    resumed = {**context, "custody": admitted["custody"], "invocation": action}
    if residue == "committed-reply-lost":
        completed = reconcile_planning(resumed)
        path = tmp_path / completed["custody"]["committed"]["path"]
    else:
        path = (
            tmp_path
            / ".agentic-workspace/local/effects"
            / (hashlib.sha256(action["idempotency_key"].encode()).hexdigest() + ".result.json")
        )
        path.write_bytes(b'{"partial":')
    before = path.read_bytes()
    with pytest.raises(DecisionContractError, match="requires exact custody; preserved"):
        reconcile_planning(resumed)
    assert path.read_bytes() == before
    assert planning_view(resumed)["planning"]["current"] is False


def test_concurrent_planning_recovery_commits_one_same_attempt(shared_core_binary: Path, tmp_path: Path) -> None:
    context = _planning_context(tmp_path)
    decision = planning_view(context)
    action = decision["primary_action"]
    admitted = admit_stored_attempt(str(tmp_path), decision, action)
    request = json.dumps({"reconcile_planning": {**context, "invocation": action, "custody": admitted["custody"]}})
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
    completed = [json.loads(stdout) for process, (stdout, _) in zip(processes, results, strict=True) if process.returncode == 0][0]
    record = json.loads((tmp_path / completed["custody"]["committed"]["path"]).read_text())
    assert record["attempt_id"] == admitted["attempt_id"]
    assert record["invocation"]["idempotency_key"] == action["idempotency_key"]
    assert planning_view({**context, "custody": completed["custody"]})["planning"]["current"] is True
    assert len(list((tmp_path / ".agentic-workspace/local/effects").glob("*.result.json"))) == 1


def _material_decision() -> dict[str, Any]:
    return {
        "id": "architecture/shared-authority",
        "source": {"owner": "repository", "reference": "decisions/shared-authority", "revision": "source-1"},
        "decision": "Use one Rust executable semantic authority",
        "consequence": "Python and Node transport owner facts to the shared reducer",
        "rationale_reference": "decisions/shared-authority#rationale-and-alternatives",
        "authors": [{"kind": "agent", "id": "implementer"}],
        "contributors": [],
        "authority": {
            "actor": {"kind": "agent", "id": "implementer"},
            "basis": [{"owner": "assignment", "reference": "bounded-implementation", "revision": "authority-1"}],
        },
        "scope": ["owner:planning", "contract:operation-result"],
        "dependencies": [{"owner": "repository", "reference": "SYSTEM_INTENT", "revision": "intent-1"}],
        "context": [{"owner": "memory", "reference": "prior-cost-evidence", "revision": "evidence-1"}],
        "supersedes": [],
    }


def _admitted_decisions(records: list[dict[str, Any]]) -> dict[str, Any]:
    # Test host stands for independent source/provenance admission. Normalizing
    # the client's record does not perform this admission in the product.
    normalized = [normalize_decision_record(record) for record in records]
    references = {
        (item["owner"], item["reference"]): item
        for record in records
        for item in record["authority"]["basis"] + record["dependencies"] + record["context"]
    }
    return {
        "records": normalized,
        "admissions": [{key: record[key] for key in ["id", "material_revision", "source", "rationale_reference"]} for record in normalized],
        "current_dependencies": list(references.values()),
        "applicable_scope": ["owner:planning"],
    }


@pytest.mark.parametrize("provenance", ["agent-taken", "human-confirmed", "human-originated", "aw-informed"])
def test_decision_authorship_authority_and_context_remain_distinct(shared_core_binary: Path, provenance: str) -> None:
    record = _material_decision()
    if provenance in ["human-confirmed", "human-originated"]:
        record["authority"] = {
            "actor": {"kind": "human", "id": "domain-owner"},
            "basis": [{"owner": "repository", "reference": "human-decision-17", "revision": "confirmation-1"}],
        }
    if provenance == "human-originated":
        record["authors"] = [record["authority"]["actor"]]
        record["contributors"] = [{"kind": "agent", "id": "implementer"}]
    if provenance != "aw-informed":
        record["context"] = []
    context = _admitted_decisions([record])
    normalized = context["records"][0]
    assert normalized["authors"] == record["authors"]
    assert normalized["authority"] == record["authority"]
    assert normalized["context"] == record["context"]
    # Public Python/Node/JSON all run the same native compiler, not a second reducer.
    payload = {"contributions": [], "decision_context": context}
    Draft202012Validator(SCHEMA).validate(payload)
    python = _compile(payload)
    raw = _direct(shared_core_binary, payload)
    program = "import {compileSourceDecision} from './bindings/node/semantic-decision.mjs'; import fs from 'node:fs'; const p=JSON.parse(fs.readFileSync(0,'utf8')); console.log(JSON.stringify(compileSourceDecision(p.contributions,{},null,p.decision_context)));"
    node = subprocess.run(
        ["node", "--input-type=module", "-e", program], input=json.dumps(payload), capture_output=True, text=True, cwd=ROOT
    )
    assert node.returncode == raw.returncode == 0
    assert python == json.loads(node.stdout) == json.loads(raw.stdout)
    consequence = python["decision_context"]["consequences"][0]
    assert consequence["summary"] == record["consequence"]
    assert consequence["scope"] == ["owner:planning"]
    assert python["claim_boundary"] == {"allowed": [], "blocked": []}
    assert python["primary_action"] is None


def test_decision_semantic_revision_is_not_source_or_view_revision(shared_core_binary: Path) -> None:
    record = _material_decision()
    first = _admitted_decisions([record])
    original = first["records"][0]
    changed = deepcopy(record)
    changed["source"]["revision"] = "nonmaterial-source-edit"
    changed["rationale_reference"] = "relocated-source#same-rationale"
    current = _admitted_decisions([changed])
    assert current["records"][0]["material_revision"] == original["material_revision"]
    assert current["records"][0]["id"] == original["id"]
    before = _compile({"contributions": [], "decision_context": first})
    after = _compile({"contributions": [], "decision_context": current})
    assert before["input_revision"] != after["input_revision"]
    assert after["decision_context"]["states"][0]["status"] == "current"
    current["current_dependencies"][0]["revision"] = "material-change"
    stale = _compile({"contributions": [], "decision_context": current})["decision_context"]
    assert stale["consequences"] == []
    assert stale["states"][0]["status"] == "stale"
    assert stale["states"][0]["stale_dependencies"]
    for field in ["authority", "scope", "dependencies"]:
        revised = deepcopy(record)
        if field == "authority":
            revised[field]["actor"]["id"] = "different-decider"
        elif field == "scope":
            revised[field].append("path:new-scope")
        else:
            revised[field][0]["revision"] = "intent-2"
        normalized = normalize_decision_record(revised)
        assert normalized["id"] == original["id"]
        assert normalized["material_revision"] != original["material_revision"]
        forged = deepcopy(first)
        forged["records"] = [normalized]
        with pytest.raises(DecisionContractError, match="admission does not bind"):
            _compile({"contributions": [], "decision_context": forged})


def test_scoped_supersession_retains_rationale_without_reviving_old_constraint(shared_core_binary: Path) -> None:
    old = _material_decision()
    old_revision = normalize_decision_record(old)["material_revision"]
    new = deepcopy(old)
    new.update(id="architecture/shared-authority-2", decision="New decision", consequence="New consequence")
    new["supersedes"] = [{"id": old["id"], "material_revision": old_revision, "scope": ["owner:planning"]}]
    context = _admitted_decisions([old, new])
    result = _compile({"contributions": [], "decision_context": context})["decision_context"]
    assert [item["id"] for item in result["consequences"]] == [new["id"]]
    prior = next(item for item in result["states"] if item["id"] == old["id"])
    assert prior["status"] == "superseded"
    assert prior["rationale_reference"] == old["rationale_reference"]
    assert context["records"][0]["decision"] == old["decision"]
    context["applicable_scope"] = ["contract:operation-result"]
    unaffected = _compile({"contributions": [], "decision_context": context})["decision_context"]
    assert old["id"] in [item["id"] for item in unaffected["consequences"]]
    context["applicable_scope"] = ["owner:planning"]
    context["current_dependencies"] = []
    assert _compile({"contributions": [], "decision_context": context})["decision_context"]["consequences"] == []
    context["records"] = context["records"][1:]
    with pytest.raises(DecisionContractError, match="supersession closure is incomplete"):
        _compile({"contributions": [], "decision_context": context})


def test_decision_context_is_not_execution_or_provenance_authority(shared_core_binary: Path, tmp_path: Path) -> None:
    record = _material_decision()
    context = _admitted_decisions([record])
    context["admissions"] = []
    with pytest.raises(DecisionContractError, match="independent host provenance admission"):
        _compile({"contributions": [], "decision_context": context})
    for key in ["effects", "claims", "restrictions", "custody", "policy", "human_authority"]:
        forged = {**record, key: ["all"]}
        with pytest.raises(DecisionContractError, match="unknown field"):
            normalize_decision_record(forged)
    payload = _stored_payload(tmp_path)
    baseline = _compile(payload)
    payload["decision_context"] = _admitted_decisions([record])
    current = _compile(payload)
    for key in ["ready_actions", "primary_action", "claim_boundary", "terminal_authority", "blockers"]:
        assert current[key] == baseline[key]
    payload["decision_context"]["applicable_scope"] = ["path:unrelated"]
    assert _compile(payload) == baseline
    assert list(tmp_path.iterdir()) == []


def test_decision_supersession_scope_and_competing_heads_fail_closed(shared_core_binary: Path) -> None:
    old = _material_decision()
    replacement = deepcopy(old)
    replacement["id"] = "replacement"
    replacement["supersedes"] = [
        {"id": old["id"], "material_revision": normalize_decision_record(old)["material_revision"], "scope": ["owner:planning"]}
    ]
    competing = deepcopy(replacement)
    competing["id"] = "competing"
    with pytest.raises(DecisionContractError, match="competing decision supersession"):
        _compile({"contributions": [], "decision_context": _admitted_decisions([old, replacement, competing])})
    replacement["supersedes"][0]["scope"] = ["owner:unadmitted-scope"]
    with pytest.raises(DecisionContractError, match="within the new decision scope"):
        normalize_decision_record(replacement)
    forged = deepcopy(old)
    forged["authors"][0]["kind"] = "aw"
    with pytest.raises(DecisionContractError):
        normalize_decision_record(forged)


@pytest.mark.parametrize("shape", ["advanced-fork", "linear", "joined", "independent", "disjoint-scope"])
def test_supersession_current_heads_follow_scope_through_ancestry(shared_core_binary: Path, shape: str) -> None:
    old = _material_decision()

    def successor(identity: str, parents: list[dict[str, Any]], scope: str = "owner:planning") -> dict[str, Any]:
        record = deepcopy(old)
        record["id"] = identity
        record["supersedes"] = [
            {"id": parent["id"], "material_revision": normalize_decision_record(parent)["material_revision"], "scope": [scope]}
            for parent in parents
        ]
        return record

    a = successor("A", [old])
    b = successor("B", [old], "contract:operation-result" if shape == "disjoint-scope" else "owner:planning")
    c = successor("C", [a, b] if shape == "joined" else [a])
    records = [old, a, c]
    if shape in ["advanced-fork", "joined", "disjoint-scope"]:
        records.append(b)
    if shape == "independent":
        records.append(successor("independent", []))
    payload = {"contributions": [], "decision_context": _admitted_decisions(records)}
    if shape == "advanced-fork":
        with pytest.raises(DecisionContractError, match="competing decision supersession"):
            _compile(payload)
        direct = _direct(shared_core_binary, payload)
        assert direct.returncode == 2
        assert "competing decision supersession" in direct.stderr
        return
    result = _compile(payload)
    assert result == json.loads(_direct(shared_core_binary, payload).stdout)
    current = {item["id"] for item in result["decision_context"]["consequences"]}
    assert "C" in current
    assert "A" not in current and old["id"] not in current
    if shape == "independent":
        assert "independent" in current
    if shape == "joined":
        assert "B" not in current
    if shape == "disjoint-scope":
        payload["decision_context"]["applicable_scope"] = ["contract:operation-result"]
        assert "B" in {item["id"] for item in _compile(payload)["decision_context"]["consequences"]}
