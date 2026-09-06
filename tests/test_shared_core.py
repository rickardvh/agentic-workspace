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
        actual = _compile(payload)
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
    for path in (
        ROOT / "src/agentic_workspace/decision.py",
        ROOT / "src/agentic_workspace/native_core.py",
        ROOT / "bindings/node/semantic-decision.mjs",
    ):
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 180  # Bounded thin projections, including assignment admission.
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


def _decision_reconciliation(record: dict[str, Any], native: str | None) -> dict[str, Any]:
    return {"residue": [record["id"]], "native_owner": native, "fallback_owner": "memory", "destinations": [], "dismissals": []}


@pytest.mark.parametrize("native", [None, "repository-decisions"])
def test_explicit_decision_disposition_requires_current_destination_admission(shared_core_binary: Path, native: str | None) -> None:
    record = _material_decision()
    context = _admitted_decisions([record])
    context["reconciliation"] = _decision_reconciliation(record, native)
    payload = {"contributions": [], "decision_context": context}
    Draft202012Validator(SCHEMA).validate(payload)
    pending = _compile(payload)["decision_context"]
    assert pending["reconciliation"][0]["status"] == "pending"
    assert pending["consequences"][0]["source"] == record["source"]
    destination = deepcopy(context["admissions"][0])
    destination["source"] = {
        "owner": native or "memory",
        "reference": "native/decision-1" if native else ".agentic-workspace/fallback-1",
        "revision": "destination-1",
    }
    destination["rationale_reference"] = destination["source"]["reference"] + "#rationale"
    context["reconciliation"]["destinations"] = [destination]
    assert _compile(payload)["decision_context"]["reconciliation"][0]["status"] == "pending"
    context["current_dependencies"].append(deepcopy(destination["source"]))
    accepted = _compile(payload)
    assert accepted == json.loads(_direct(shared_core_binary, payload).stdout)
    assert accepted["decision_context"]["reconciliation"][0]["status"] == ("repo-native" if native else "fallback")
    assert accepted["decision_context"]["consequences"][0]["source"] == destination["source"]
    assert accepted["decision_context"]["states"][0]["rationale_reference"] == destination["rationale_reference"]
    # A later lost/stale stronger owner cannot hide the former current value.
    context["current_dependencies"][-1]["revision"] = "changed-or-unavailable"
    lost = _compile(payload)["decision_context"]
    assert lost["reconciliation"][0]["status"] == "pending"
    assert lost["consequences"][0]["source"] == record["source"]
    context["current_dependencies"][-1]["revision"] = "destination-1"
    destination["material_revision"] = "different-decision"
    assert _compile(payload)["decision_context"]["reconciliation"][0]["status"] == "pending"


def test_native_owner_prevents_fallback_shortcut_and_unrelated_residue_cannot_disappear(shared_core_binary: Path) -> None:
    record = _material_decision()
    context = _admitted_decisions([record])
    resolution = _decision_reconciliation(record, "repository-decisions")
    context["reconciliation"] = resolution
    fallback = deepcopy(context["admissions"][0])
    fallback["source"] = {"owner": "memory", "reference": "fallback", "revision": "1"}
    resolution["destinations"] = [fallback]
    context["current_dependencies"].append(fallback["source"])
    context["applicable_scope"] = ["path:unrelated"]
    result = _compile({"contributions": [], "decision_context": context})["decision_context"]
    assert result["consequences"] == []
    assert result["reconciliation"][0]["status"] == "pending"
    assert result["reconciliation"][0]["owner"] == "repository-decisions"
    context["records"] = []
    with pytest.raises(DecisionContractError, match="missing its admitted record"):
        _compile({"contributions": [], "decision_context": context})


def test_dismissal_is_an_explicit_current_authority_judgment(shared_core_binary: Path) -> None:
    record = _material_decision()
    context = _admitted_decisions([record])
    resolution = _decision_reconciliation(record, None)
    context["reconciliation"] = resolution
    dismissal = {
        "id": record["id"],
        "material_revision": context["records"][0]["material_revision"],
        "reason": "Temporary choice has no continuing value",
        "authority": {
            "actor": {"kind": "human", "id": "domain-owner"},
            "basis": [{"owner": "repository", "reference": "dismissal-confirmation", "revision": "1"}],
        },
    }
    resolution["dismissals"] = [dismissal]  # Independent host/owner admission, not an ordinary client record.
    pending = _compile({"contributions": [], "decision_context": context})["decision_context"]
    assert pending["reconciliation"][0]["status"] == "pending"
    assert pending["consequences"]
    context["current_dependencies"] += dismissal["authority"]["basis"]
    accepted = _compile({"contributions": [], "decision_context": context})
    assert accepted["decision_context"]["reconciliation"][0]["status"] == "dismissed"
    assert accepted["decision_context"]["consequences"] == []
    assert accepted["claim_boundary"] == {"allowed": [], "blocked": []}
    assert accepted["status"] == "direct"
    dismissal["material_revision"] = "old-revision"
    with pytest.raises(DecisionContractError, match="exact material decision"):
        _compile({"contributions": [], "decision_context": context})


def test_full_supersession_satisfies_known_decision_residue(shared_core_binary: Path) -> None:
    old = _material_decision()
    new = deepcopy(old)
    new["id"] = "replacement"
    new["supersedes"] = [{"id": old["id"], "material_revision": normalize_decision_record(old)["material_revision"], "scope": old["scope"]}]
    context = _admitted_decisions([old, new])
    context["reconciliation"] = _decision_reconciliation(old, None)
    value = _compile({"contributions": [], "decision_context": context})["decision_context"]
    assert value["reconciliation"][0]["status"] == "superseded"
    assert [item["id"] for item in value["consequences"]] == [new["id"]]


def _native_archive(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    import hashlib

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "authority.md").write_text("Human owner admits this bounded decision.\n", encoding="utf-8", newline="\n")
    record = _material_decision()
    record.pop("source")
    record.pop("rationale_reference")
    record["scope"] = ["path:src/core.rs"]
    record["authority"]["basis"] = [
        {
            "owner": "repository",
            "reference": "authority.md",
            "revision": "sha256:" + hashlib.sha256((tmp_path / "authority.md").read_bytes()).hexdigest(),
        }
    ]
    record["dependencies"] = []
    record["context"] = []
    (tmp_path / "design").mkdir()
    _write_native(tmp_path / "design/choice.md", record)
    revision = _commit_native(tmp_path)
    return {"target": str(tmp_path), "archive": "design", "admitted_revision": revision, "applicable_scope": ["path:src/core.rs"]}, record


def _write_native(path: Path, record: dict[str, Any]) -> None:
    path.write_text(
        "# Decision\n\n```aw-decision\n" + json.dumps(record, indent=2) + "\n```\n\nRationale stays in the repository.\n",
        encoding="utf-8",
        newline="\n",
    )


def _commit_native(root: Path) -> str:
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test source owner",
            "-c",
            "user.email=owner@example.test",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "Admit decision source",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def test_repo_native_source_is_current_relevant_and_transport_equivalent(shared_core_binary: Path, tmp_path: Path) -> None:
    from agentic_workspace.decision import repository_decision_view

    context, _ = _native_archive(tmp_path)
    actual = repository_decision_view(**context)
    assert actual == json.loads(_direct(shared_core_binary, {"repository_decision_view": context}).stdout)
    node = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import { repositoryDecisionView } from './bindings/node/semantic-decision.mjs'; console.log(JSON.stringify(repositoryDecisionView(JSON.parse(process.argv[1]))));",
            json.dumps(context),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(node.stdout) == actual
    assert actual["decision_context"]["states"][0]["status"] == "current"
    assert actual["decision_context"]["consequences"][0]["summary"] == "Python and Node transport owner facts to the shared reducer"
    assert actual["status"] == "direct"
    assert actual["claim_boundary"] == compile_source_decision([])["claim_boundary"]
    context["applicable_scope"] = ["path:unrelated.txt"]
    assert "decision_context" not in repository_decision_view(**context)
    context["target"] = str(tmp_path / "does-not-exist")
    context["applicable_scope"] = []
    assert "decision_context" not in repository_decision_view(**context)


@pytest.mark.parametrize("change", ["source", "authority", "forged-actor", "unadmitted-commit", "self-source", "effect-authority"])
def test_native_source_never_self_admits_or_replays_stale_authority(shared_core_binary: Path, tmp_path: Path, change: str) -> None:
    from agentic_workspace.decision import repository_decision_view

    context, record = _native_archive(tmp_path)
    if change == "authority":
        (tmp_path / "authority.md").write_text("Changed authority", encoding="utf-8")
        answer = repository_decision_view(**context)["decision_context"]
        assert answer["states"][0]["status"] == "stale"
        assert answer["consequences"] == []
        return
    if change == "source":
        (tmp_path / "design/choice.md").write_text("Unreviewed replacement", encoding="utf-8")
    elif change == "unadmitted-commit":
        context["admitted_revision"] = "HEAD"
    elif change == "forged-actor":
        record["authority"]["actor"] = {"kind": "human", "id": "invented-human"}
        _write_native(tmp_path / "design/choice.md", record)
        _commit_native(tmp_path)  # A new commit alone never advances host admission.
    else:
        record["source" if change == "self-source" else "claims"] = {"allowed": ["complete"]}
        _write_native(tmp_path / "design/choice.md", record)
        context["admitted_revision"] = _commit_native(tmp_path)
    with pytest.raises(DecisionContractError):
        repository_decision_view(**context)


@pytest.mark.parametrize("selected_scope", ["path:src/core.rs", "path:api.rs"])
def test_native_supersession_uses_existing_contract_and_keeps_rationale(
    shared_core_binary: Path, tmp_path: Path, selected_scope: str
) -> None:
    from agentic_workspace.decision import repository_decision_view

    context, record = _native_archive(tmp_path)
    old = repository_decision_view(**context)["decision_context"]["states"][0]
    successor = deepcopy(record)
    successor["id"] = "architecture/successor"
    successor["scope"] = [*record["scope"], "path:api.rs"]
    successor["consequence"] = "Use the replacement consequence"
    successor["supersedes"] = [{"id": record["id"], "material_revision": old["material_revision"], "scope": record["scope"]}]
    _write_native(tmp_path / "design/successor.md", successor)
    context["admitted_revision"] = _commit_native(tmp_path)
    context["applicable_scope"] = [selected_scope]
    output = repository_decision_view(**context)["decision_context"]
    assert [c["id"] for c in output["consequences"]] == [successor["id"]]
    if selected_scope == "path:src/core.rs":
        assert next(s for s in output["states"] if s["id"] == record["id"])["status"] == "superseded"
    assert (tmp_path / "design/choice.md").is_file()


@pytest.mark.parametrize("external_freshness", [False, True])
def test_ordinary_start_uses_native_decision_and_rechecks_before_cache(
    shared_core_binary: Path, tmp_path: Path, external_freshness: bool
) -> None:
    import sys

    context, _ = _native_archive(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text(
        'schema_version = 1\n[modules]\nenabled = []\n[assurance]\ndecision_record_target = "design"\ndecision_record_revision = "'
        + context["admitted_revision"]
        + '"\n',
        encoding="utf-8",
    )

    def start(path: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-c",
                "from agentic_workspace.cli import main; raise SystemExit(main())",
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                path,
                "--task",
                "bounded edit",
                "--format",
                "json",
            ],
            env={
                **{key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"},
                "AW_PROJECTION_EXTERNAL_STATE": "1" if external_freshness else "0",
            },
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    first = start("src/core.rs")
    assert first.returncode == 0, first.stdout + first.stderr
    packet = json.loads(first.stdout)["decision_packet"]
    authority = packet["identity"]
    assert authority["decision_id"].startswith("operating-decision:")
    assert packet["decision_context"]["consequences"][0]["id"] == "architecture/shared-authority"
    again = start("src/core.rs")
    assert json.loads(again.stdout)["decision_packet"]["decision_context"] == packet["decision_context"]
    assert json.loads(again.stdout)["decision_packet"]["identity"] == authority
    quiet = start("unrelated.txt")
    assert "decision_context" not in json.loads(quiet.stdout)["decision_packet"]
    (tmp_path / "authority.md").write_text("Changed decisive authority", encoding="utf-8")
    changed = start("src/core.rs")
    changed_payload = json.loads(changed.stdout)
    assert changed_payload["decision_packet"]["decision_context"]["states"][0]["status"] == "stale"
    changed_authority = changed_payload["decision_packet"]["identity"]
    assert changed_authority["decision_id"] != authority["decision_id"]
    assert changed_authority["revision"] != authority["revision"]
    (tmp_path / "design/choice.md").write_text("Unadmitted replacement", encoding="utf-8")
    stale = start("src/core.rs")
    assert stale.returncode != 0
    assert "stale decision source" in stale.stdout + stale.stderr


def test_native_exact_scope_does_not_depend_on_json_escaping(shared_core_binary: Path, tmp_path: Path) -> None:
    from agentic_workspace.decision import repository_decision_view

    context, _ = _native_archive(tmp_path)
    path = tmp_path / "design/choice.md"
    path.write_text(path.read_text(encoding="utf-8").replace("src/core.rs", "src\\/core.rs"), encoding="utf-8", newline="\n")
    context["admitted_revision"] = _commit_native(tmp_path)
    assert repository_decision_view(**context)["decision_context"]["states"][0]["status"] == "current"


def test_source_node_transport_builds_current_core_without_binary_override(shared_core_binary: Path) -> None:
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import { compileSourceDecision } from './bindings/node/semantic-decision.mjs'; console.log(JSON.stringify(compileSourceDecision([])));",
        ],
        cwd=ROOT,
        env={key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"},
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout) == compile_source_decision([])


def test_source_context_is_bound_before_finalization(shared_core_binary: Path, tmp_path: Path) -> None:
    """#2909: isolate source currentness from aggregate worktree/cache churn."""
    from agentic_workspace.decision import repository_decision_view
    from agentic_workspace.operating_decision import (
        admit_projection_surface_decision_input,
        consume_projection_surface_decision_input,
        finalize_projection_surface_operating_decision,
        revalidate_projection_surface_decision_input,
    )
    from agentic_workspace.projection_reuse import _operating_decision_revisions, admitted_projection_revisions

    source, _ = _native_archive(tmp_path)
    baseline, _, _ = admitted_projection_revisions(root=tmp_path, operation="start", query={"task": "edit"})

    def admit(view: dict[str, Any]) -> dict[str, Any]:
        revisions = dict(baseline)
        material: dict[str, Any] = {"task": "edit"}
        if "decision_context" in view:
            revisions["decision_context_revision"] = view["input_revision"]
            material["decision_context"] = view["decision_context"]
        return admit_projection_surface_decision_input(
            input_revisions=_operating_decision_revisions(revisions), consumer="start", material_inputs=material
        )

    def finish(admission: dict[str, Any], current: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = consume_projection_surface_decision_input(
            payload={"decision_packet": {"kind": "agentic-workspace/ordinary-start-decision/v1"}},
            admitted_input=admission,
            consumer="start",
        )
        payload = revalidate_projection_surface_decision_input(
            payload=payload, admitted_input=admission, current_input_revisions=current["input_revisions"], consumer="start"
        )
        return finalize_projection_surface_operating_decision(payload=payload, admitted_input=admission, consumer="start")

    view = repository_decision_view(**source)
    admitted = admit(view)
    payload, decision = finish(admitted, admitted)
    assert decision["decision_context"] == view["decision_context"]
    assert payload["decision_packet"]["identity"]["decision_id"] == decision["decision_id"]
    assert decision["admitted_input_revision"] == admitted["admitted_input_revision"]
    (tmp_path / "unrelated.txt").write_text("unrelated source churn", encoding="utf-8")
    unchanged = admit(repository_decision_view(**source))
    assert finish(unchanged, unchanged)[1]["decision_id"] == decision["decision_id"]
    quiet = admit(repository_decision_view(**{**source, "applicable_scope": ["path:unrelated.txt"]}))
    assert quiet == admit({})
    assert "decision_context" not in finish(quiet, quiet)[1]
    (tmp_path / "authority.md").write_text("changed authority basis", encoding="utf-8")
    stale = admit(repository_decision_view(**source))
    stale_decision = finish(stale, stale)[1]
    assert stale_decision["decision_id"] != decision["decision_id"]
    assert stale_decision["decision_context"]["consequences"] == []
    # A dependency change during materialization cannot finalize the old input.
    rejected_payload, rejected = finish(admitted, stale)
    assert rejected == {}
    assert "decision_context" not in rejected_payload["decision_packet"]


@pytest.mark.parametrize("destination", ["absent", "unadmitted", "different-value", "current", "changed-after-promotion"])
def test_memory_decision_fallback_promotes_only_to_exact_current_native_source(
    shared_core_binary: Path, tmp_path: Path, destination: str
) -> None:
    from agentic_workspace.decision import repository_decision_view

    context, record = _native_archive(tmp_path)
    # Test host admits the exact known agent-authored source to Memory. The
    # archive/path/actor alone do not create this source-owner admission.
    fallback = {"archive": context["archive"], "admitted_revision": context["admitted_revision"]}
    context.update(archive="", admitted_revision="", fallback=fallback)
    retained = repository_decision_view(**context)["decision_context"]
    assert retained["reconciliation"][0]["status"] == "fallback"
    assert retained["consequences"][0]["source"]["owner"] == "memory"
    original = (tmp_path / "design/choice.md").read_bytes()
    if destination != "absent":
        (tmp_path / "repo-decisions").mkdir()
        native = deepcopy(record)
        if destination == "different-value":
            native["consequence"] = "A different material value is not promotion"
        _write_native(tmp_path / "repo-decisions/choice.md", native)
        revision = _commit_native(tmp_path)
        context.update(
            archive="repo-decisions", admitted_revision=revision if destination != "unadmitted" else fallback["admitted_revision"]
        )
    if destination == "changed-after-promotion":
        assert repository_decision_view(**context)["decision_context"]["reconciliation"][0]["status"] == "repo-native"
        (tmp_path / "repo-decisions/choice.md").write_text("Destination disappeared", encoding="utf-8")
    output = repository_decision_view(**context)
    expected = "repo-native" if destination == "current" else "fallback" if destination == "absent" else "pending"
    assert output["decision_context"]["reconciliation"][0]["status"] == expected
    consequence = output["decision_context"]["consequences"][0]
    assert consequence["summary"] == record["consequence"]
    assert consequence["source"]["owner"] == ("repository" if destination == "current" else "memory")
    assert consequence["material_revision"] == retained["consequences"][0]["material_revision"]
    assert (tmp_path / "design/choice.md").read_bytes() == original
    assert json.loads(_direct(shared_core_binary, {"repository_decision_view": context}).stdout) == output
    context["applicable_scope"] = ["path:unrelated.txt"]
    assert "decision_context" not in repository_decision_view(**context)


def test_fallback_source_cannot_choose_its_owner_or_widen_admission(shared_core_binary: Path, tmp_path: Path) -> None:
    from agentic_workspace.decision import repository_decision_view

    context, _ = _native_archive(tmp_path)
    context["fallback"] = {"archive": "design", "admitted_revision": context["admitted_revision"], "owner": "human"}
    with pytest.raises(DecisionContractError, match="unknown field"):
        repository_decision_view(**context)


def test_known_agent_decision_survives_memory_to_native_ordinary_journey(shared_core_binary: Path, tmp_path: Path) -> None:
    import sys

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "SYSTEM_INTENT.md").write_bytes((ROOT / "SYSTEM_INTENT.md").read_bytes())
    archive = ".agentic-workspace/memory/repo/decisions"
    source = tmp_path / archive / "source-admission.md"
    source.parent.mkdir(parents=True)
    with source.open("xb") as output:
        output.write((ROOT / "tests/fixtures/decision_fallback.md").read_bytes())
    original = source.read_bytes()
    revision = _commit_native(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"

    def configure(native: str = "") -> None:
        config.write_text(
            "schema_version = 1\n[modules]\nenabled = []\n[assurance]\n"
            + native
            + '\n[assurance.decision_record_fallback]\narchive = "'
            + archive
            + '"\nadmitted_revision = "'
            + revision
            + '"\n',
            encoding="utf-8",
        )

    def start() -> dict[str, Any]:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from agentic_workspace.cli import main; raise SystemExit(main())",
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                "crates/agentic-workspace-core/src/decision_source.rs",
                "--task",
                "bounded edit",
                "--format",
                "json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)["decision_packet"]

    configure()
    fallback_packet = start()
    fallback = fallback_packet["decision_context"]
    assert start()["identity"] == fallback_packet["identity"]
    assert fallback["reconciliation"][0]["status"] == "fallback"
    assert fallback["consequences"][0]["authority"]["actor"]["kind"] == "agent"
    native_source = tmp_path / "docs/decisions/source-admission.md"
    native_source.parent.mkdir(parents=True)
    with native_source.open("xb") as output:
        output.write(original)
    configure('decision_record_target = "docs/decisions"\ndecision_record_revision = "' + revision + '"\n')
    pending_packet = start()
    assert pending_packet["decision_context"]["reconciliation"][0]["status"] == "pending"
    assert pending_packet["identity"] != fallback_packet["identity"]
    admitted_native = _commit_native(tmp_path)
    configure('decision_record_target = "docs/decisions"\ndecision_record_revision = "' + admitted_native + '"\n')
    promoted_packet = start()
    promoted = promoted_packet["decision_context"]
    assert promoted_packet["identity"] != pending_packet["identity"]
    assert start()["identity"] == promoted_packet["identity"]
    assert promoted["reconciliation"][0]["status"] == "repo-native"
    assert promoted["consequences"][0]["material_revision"] == fallback["consequences"][0]["material_revision"]
    assert promoted["consequences"][0]["source"]["reference"] == "docs/decisions/source-admission.md"
    native_source.write_text("unadmitted replacement", encoding="utf-8")
    lost_packet = start()
    assert lost_packet["decision_context"]["reconciliation"][0]["status"] == "pending"
    assert lost_packet["identity"] != promoted_packet["identity"]
    assert source.read_bytes() == original


@pytest.mark.parametrize("selection_state", ["selected", "none", "missing", "stale-work", "stale-source", "other-route"])
@pytest.mark.parametrize("exact", [False, True])
def test_decision_semantic_applicability_is_scoped(shared_core_binary: Path, selection_state: str, exact: bool) -> None:
    record = _material_decision()
    record["semantic_routes"] = ["architecture/authority"]
    context = _admitted_decisions([record])
    context["applicable_scope"] = ["owner:planning"] if exact else ["path:unrelated.py"]
    work = {"kind": "current-work", "id": "work-1"}
    source = {"revision": "sha256:" + "a" * 64, "routes": ["architecture/authority", "docs/style"]}
    intent: dict[str, Any] = {"current_work": work, "semantic_route_source": source}
    if selection_state != "missing":
        intent["semantic_task_routes"] = {
            "posture": "none" if selection_state == "none" else "selected",
            "routes": [] if selection_state == "none" else ["docs/style" if selection_state == "other-route" else "architecture/authority"],
            "task_identity": {**work, "id": "old-work"} if selection_state == "stale-work" else work,
            "source_revision": "sha256:" + "b" * 64 if selection_state == "stale-source" else source["revision"],
            "provenance": "agent-selected",
            "authority_effect": "applicability-only",
        }
    action = {
        "owner": "workspace",
        "revision": "w1",
        "actions": [{"dependency_revision": "w1", "operation_id": "workspace.inspect", "effects": ["workspace-read"]}],
    }
    baseline = compile_source_decision([action], capability_contract=CAPABILITY_CONTRACT)
    value = {"contributions": [action], "intent": intent, "decision_context": context, "capability_contract": CAPABILITY_CONTRACT}
    result = _compile(value)
    assert result == json.loads(_direct(shared_core_binary, value).stdout)
    assert result["primary_action"] == baseline["primary_action"]
    assert result["claim_boundary"] == baseline["claim_boundary"]
    assert result["blockers"] == []
    projected = result.get("decision_context", {})
    if exact or selection_state == "selected":
        assert projected["consequences"][0]["id"] == record["id"]
    elif selection_state in {"missing", "stale-work", "stale-source"}:
        assert projected["states"][0]["status"] == "applicability-unresolved"
        assert projected["consequences"] == []
    else:
        assert projected == {}


def _route_host() -> dict[str, Any]:
    return {
        "current_work": {"kind": "current-work", "id": "work-1"},
        "source": {"revision": "sha256:" + "a" * 64, "routes": ["architecture/authority", "docs/style"]},
    }


def test_public_semantic_route_roundtrip_is_cross_surface(shared_core_binary: Path) -> None:
    from agentic_workspace.decision import semantic_route_view

    host = _route_host()
    discovery = semantic_route_view(host)
    request = deepcopy(discovery["requests"][1])
    request["arguments"] = {"posture": "selected", "routes": ["architecture/authority"]}
    host["request"] = request
    selected = semantic_route_view(host)
    assert selected == json.loads(_direct(shared_core_binary, {"semantic_route_view": host}).stdout)
    node = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import {semanticRouteView} from './bindings/node/semantic-decision.mjs'; console.log(JSON.stringify(semanticRouteView(JSON.parse(process.argv[1]))));",
            json.dumps(host),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(node.stdout) == selected
    assert selected["decision"]["semantic_task_routes"]["routes"] == ["architecture/authority"]
    assert selected["decision"]["blockers"] == []
    assert selected["decision"]["claim_boundary"] == compile_source_decision([])["claim_boundary"]
    request["arguments"] = {"posture": "none", "routes": []}
    declined = semantic_route_view(host)
    assert declined["request_identity"] != selected["request_identity"]
    assert declined["decision"]["semantic_task_routes"]["posture"] == "none"


@pytest.mark.parametrize("change", ["work", "source", "removed"])
def test_public_semantic_route_staleness_is_scoped(shared_core_binary: Path, change: str) -> None:
    from agentic_workspace.decision import semantic_route_view

    host = _route_host()
    request = semantic_route_view(host)["requests"][1]
    request["arguments"] = {"posture": "selected", "routes": ["architecture/authority"]}
    host["request"] = request
    if change == "work":
        host["current_work"]["id"] = "work-2"
    elif change == "source":
        host["source"]["revision"] = "sha256:" + "b" * 64
    else:
        host["source"]["routes"] = ["docs/style"]
    result = semantic_route_view(host)
    assert result["status"] == "stale"
    assert result["decision"]["semantic_task_routes"]["status"] == "stale"
    assert result["decision"]["semantic_task_routes"]["routes"] == []
    assert result["decision"]["blockers"] == []


@pytest.mark.parametrize("field", ["owner", "effects", "claims", "proof", "custody", "actor", "authority_effect"])
def test_public_semantic_route_cannot_supply_authority(shared_core_binary: Path, field: str) -> None:
    from agentic_workspace.decision import semantic_route_view

    host = _route_host()
    request = semantic_route_view(host)["requests"][1]
    request["arguments"][field] = "human-authorized"
    with pytest.raises(DecisionContractError):
        semantic_route_view({**host, "request": request})


def test_public_semantic_route_discovery_is_bounded_and_complete(shared_core_binary: Path) -> None:
    from agentic_workspace.decision import semantic_route_view

    host = _route_host()
    host["source"]["routes"] = [f"work/choice-{index:02}" for index in range(35)]
    result = semantic_route_view(host)
    assert result["discovery"]["children"] == [{"id": "work", "leaf": False}]
    request = result["requests"][0]
    request["arguments"] = {"parent": "work"}
    seen = []
    while True:
        page = semantic_route_view({**host, "request": request})["discovery"]
        assert len(page["children"]) <= 16
        seen.extend(child["id"] for child in page["children"])
        if page["next_after"] is None:
            break
        request["arguments"]["after"] = page["next_after"]
    assert seen == host["source"]["routes"]


@pytest.mark.parametrize("source_owner", ["repository", "memory"])
def test_repo_decision_consumes_public_route_without_path_match(shared_core_binary: Path, tmp_path: Path, source_owner: str) -> None:
    from agentic_workspace.decision import repository_decision_view, semantic_route_view

    context, record = _native_archive(tmp_path)
    record["semantic_routes"] = ["architecture/authority"]
    _write_native(tmp_path / "design/choice.md", record)
    context["admitted_revision"] = _commit_native(tmp_path)
    context["applicable_scope"] = []
    if source_owner == "memory":
        fallback = {"archive": context["archive"], "admitted_revision": context["admitted_revision"]}
        context.update(archive="", admitted_revision="", fallback=fallback)
    host = _route_host()
    request = semantic_route_view(host)["requests"][1]
    request["arguments"] = {"posture": "selected", "routes": ["architecture/authority"]}
    host["request"] = request
    result = repository_decision_view(**context, semantic_routes=host)
    assert result["decision_context"]["consequences"][0]["id"] == record["id"]
    assert result["decision_context"]["consequences"][0]["source"]["owner"] == source_owner
    host["current_work"]["id"] = "changed-work"
    assert "decision_context" not in repository_decision_view(**context, semantic_routes=host)
    context["applicable_scope"] = ["path:src/core.rs"]
    assert repository_decision_view(**context, semantic_routes=host)["decision_context"]["consequences"]


def test_ordinary_start_public_route_is_current_scoped_and_quiet(shared_core_binary: Path, tmp_path: Path) -> None:
    import sys

    context, record = _native_archive(tmp_path)
    record["semantic_routes"] = ["architecture/authority"]
    _write_native(tmp_path / "design/choice.md", record)
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "architecture", "semantic_routes": ["architecture/authority"]}]}), encoding="utf-8")
    revision = _commit_native(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text(
        'schema_version = 1\n[modules]\nenabled = []\n[assurance]\ndecision_record_target = "design"\ndecision_record_revision = "'
        + revision
        + '"\n',
        encoding="utf-8",
    )

    def start(*extra: str, task: str = "consider design") -> dict[str, Any]:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from agentic_workspace.cli import main; raise SystemExit(main())",
                "start",
                "--target",
                str(tmp_path),
                "--task",
                task,
                "--format",
                "json",
                *extra,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    quiet = start(task="architecture authority design")
    assert "decision_context" not in quiet["decision_packet"]
    assert "semantic_route_result" not in quiet["decision_packet"]
    discovered = start("--select", "semantic_route_result")["values"]["semantic_route_result"]
    request = discovered["requests"][1]
    request["arguments"] = {"posture": "selected", "routes": ["architecture/authority"]}
    selected = start("--request", json.dumps(request))["decision_packet"]
    assert selected["decision_context"]["consequences"][0]["id"] == record["id"]
    assert selected["identity"]["decision_id"].startswith("operating-decision:")
    assert start("--request", json.dumps(request))["decision_packet"]["identity"] == selected["identity"]
    (tmp_path / "unrelated.md").write_text("Editorial churn", encoding="utf-8")
    _commit_native(tmp_path)
    churned = start("--request", json.dumps(request))["decision_packet"]
    assert churned["semantic_route_result"]["status"] == "current"
    assert churned["decision_context"]["consequences"] == selected["decision_context"]["consequences"]
    switched = start("--request", json.dumps(request), task="a different task")["decision_packet"]
    assert switched["semantic_route_result"]["status"] == "stale"
    assert "decision_context" not in switched
    registry.write_text(registry.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    stale = start("--request", json.dumps(request))["decision_packet"]
    assert stale["semantic_route_result"]["status"] == "stale"
    assert "decision_context" not in stale
    exact = start("--request", json.dumps(request), "--changed", "src/core.rs")["decision_packet"]
    assert exact["decision_context"]["consequences"][0]["id"] == record["id"]
    assert not (tmp_path / ".agentic-workspace/local/current-task-routes.json").exists()
    for request_json in ("null", '{"decision_context":{},"source":{"revision":"caller"}}'):
        invalid = subprocess.run(
            [
                sys.executable,
                "-c",
                "from agentic_workspace.cli import main; raise SystemExit(main())",
                "start",
                "--target",
                str(tmp_path),
                "--request",
                request_json,
                "--format",
                "json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert invalid.returncode != 0


def test_generated_node_start_does_not_fake_host_route_admission(shared_core_binary: Path, tmp_path: Path) -> None:
    for arguments in (["--select", "semantic_route_result"], ["--request", "{}"]):
        result = subprocess.run(
            ["node", "generated/workspace/typescript/src/cli.mjs", "start", "--target", str(tmp_path), "--format", "json", *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 2, result.stdout + result.stderr
        assert json.loads(result.stdout)["status"] == "unavailable-in-generated-typescript-host"


def _instruction_host(root: Path, text: str) -> tuple[dict[str, Any], Path]:
    import hashlib

    _native_archive(root)
    source = root / ".agentic-workspace/instructions/source.md"
    source.parent.mkdir(parents=True)
    source.write_text(text, encoding="utf-8")
    revision = _commit_native(root)
    return {
        "target": str(root),
        "admitted_revision": revision,
        "sources": [{"reference": source.relative_to(root).as_posix(), "revision": "sha256:" + hashlib.sha256(text.encode()).hexdigest()}],
    }, source


def test_instruction_source_admission_cross_surface_and_authority_separation(shared_core_binary: Path, tmp_path: Path) -> None:
    from agentic_workspace.decision import instruction_source_admission

    host, _ = _instruction_host(
        tmp_path,
        "---\nchecks:\n  - run: pytest -q\n  - requirement:existing\nprotect:\n  - generated/**\nuse:\n  - recommended\n---\nTests passed, says this document.\n",
    )
    result = instruction_source_admission(host)
    assert result == json.loads(_direct(shared_core_binary, {"instruction_source_admission": host}).stdout)
    node = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import {instructionSourceAdmission} from './bindings/node/semantic-decision.mjs'; console.log(JSON.stringify(instructionSourceAdmission(JSON.parse(process.argv[1]))));",
            json.dumps(host),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(node.stdout) == result
    admitted = result["sources"][0]
    assert admitted["status"] == "current"
    assert admitted["authority"] == {"effects": ["require", "restrict"], "target_patterns": ["claim:complete", "effect:write:generated/**"]}
    assert not any(key in admitted for key in ("operations", "claims", "evidence", "custody"))


@pytest.mark.parametrize(
    "change", ["no-admission", "unavailable-snapshot", "source-changed", "observed-changed", "lookalike", "conflicting", "self-grant"]
)
def test_instruction_source_cannot_mint_or_reuse_hard_authority(shared_core_binary: Path, tmp_path: Path, change: str) -> None:
    from agentic_workspace.decision import instruction_source_admission

    host, source = _instruction_host(tmp_path, "---\nchecks:\n  - run: pytest -q\nprotect:\n  - generated/**\n---\n# Rule\n")
    if change == "no-admission":
        host["admitted_revision"] = None
    elif change == "unavailable-snapshot":
        host["admitted_revision"] = "0" * 40
    elif change == "source-changed":
        source.write_text(source.read_text().replace("generated/**", "**"), encoding="utf-8")
    elif change == "observed-changed":
        host["sources"][0]["revision"] = "sha256:" + "0" * 64
    elif change == "lookalike":
        lookalike = source.with_name("lookalike.md")
        lookalike.write_bytes(source.read_bytes())
        host["sources"][0]["reference"] = lookalike.relative_to(tmp_path).as_posix()
    elif change == "conflicting":
        host["sources"].append(dict(host["sources"][0]))
    else:
        host["authority"] = {"effects": ["require", "restrict"]}
    if change in {"conflicting", "self-grant"}:
        with pytest.raises(DecisionContractError):
            instruction_source_admission(host)
        return
    result = instruction_source_admission(host)["sources"][0]
    assert result["status"] in {"stale", "unadmitted", "unavailable"}
    assert result["checks"] == result["protect"] == result["authority"]["effects"] == []


@pytest.mark.parametrize(
    "body,effects",
    [
        ("checks:\n  - run: pytest -q\n", ["require"]),
        ("protect:\n  - generated/**\n", ["restrict"]),
        ("paths: [src/**]\nchecks: ['check:lint']\nprotect: ['generated/**']\n", ["require", "restrict"]),
        ('checks:\n  - run: python -c "print(1)"\n', ["require"]),
        ("checks:\n  - requirement:existing\nuse:\n  - recommended\n", []),
    ],
)
def test_instruction_binding_scopes_are_distinct(shared_core_binary: Path, tmp_path: Path, body: str, effects: list[str]) -> None:
    from agentic_workspace.decision import instruction_source_admission

    host, _ = _instruction_host(tmp_path, "---\n" + body + "---\n# Scope\n")
    assert instruction_source_admission(host)["sources"][0]["authority"]["effects"] == effects


def test_real_instruction_transition_in_ordinary_start(shared_core_binary: Path, tmp_path: Path) -> None:
    import sys

    real_source = ROOT / ".agentic-workspace/instructions/workspace-operating.md"
    text = real_source.read_text(encoding="utf-8")
    host, source = _instruction_host(tmp_path, text)
    config = tmp_path / ".agentic-workspace/config.toml"
    base = "schema_version = 1\n[modules]\nenabled = []\n"
    config.write_text(base, encoding="utf-8")
    target = ".agentic-workspace/local/decision-point-intent/73a213e66cd48a33.json"

    def start(path: str = target) -> dict[str, Any]:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from agentic_workspace.cli import main; raise SystemExit(main())",
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                path,
                "--select",
                "instruction_clause_projection",
                "--format",
                "json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)["values"]["instruction_clause_projection"]

    assert start()["effects"]["restrict"] == []
    config.write_text(base + f'\n[assurance]\ninstruction_revision = "{host["admitted_revision"]}"\n', encoding="utf-8")
    current = start()
    assert current["effects"]["restrict"][0]["target"] == "effect:write:" + target
    assert any(row["reason_code"] == "denied-effect" for row in current["blockers"])
    assert start()["snapshot_revision"] == current["snapshot_revision"]
    assert start("unrelated.txt")["effects"]["restrict"] == []
    source.write_text(text + "\nUnadmitted edit\n", encoding="utf-8")
    assert start()["effects"]["restrict"] == []
    assert not (tmp_path / target).exists()


def test_generated_node_instruction_declarations_are_not_binding(tmp_path: Path) -> None:
    source = tmp_path / ".agentic-workspace/instructions/lookalike.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nchecks:\n  - run: pytest -q\nprotect:\n  - generated/**\n---\n# Declaration\n", encoding="utf-8")
    result = subprocess.run(
        ["node", "generated/workspace/typescript/src/cli.mjs", "instructions", "list", "--target", str(tmp_path), "--format", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    row = json.loads(result.stdout)["instructions"][0]
    assert row["checks"] == row["protect"] == []
    assert row["binding_admission"]["status"] == "unavailable-in-generated-typescript-host"


@pytest.mark.parametrize("transport", ["manual", "internal"])
def test_assignment_replacement_authority_and_cross_surface_currentness(tmp_path: Path, shared_core_binary: Path, transport: str) -> None:
    """#2909: source-owner inputs are distinct from public request intention."""
    from tests.test_external_operation_clients import _prepare_shared_worktree_assignment

    from agentic_workspace.decision import admit_assignment_packet, replace_assignment

    _prepare_shared_worktree_assignment(tmp_path, run_id="original-run")
    packet = json.loads((tmp_path / ".agentic-workspace/local/assignment-runs/original-run/export/packet.json").read_text())
    source = {"reference": "configured-human-source", "revision": "source-1"}
    work = {"id": "slice-1", "revision": "plan-rev-1"}
    execution = {
        "target": "codex_sol",
        "target_identity_ref": "user-local:codex-sol",
        "target_revision": "gpt-5.6-sol",
        "transport": transport,
        "adapter": {"kind": transport, "execution_methods": [transport], "host_parameter": "exact host-enforced value"},
    }
    admission = {
        "assignment_id": packet["assignment_id"],
        "assignment_revision": packet["assignment_revision"],
        "packet_integrity": packet["packet_integrity"],
        "work": work,
        "source": source,
        "execution": execution,
    }
    context = {
        "current": packet,
        "work": work,
        "source": source,
        "execution": execution,
        "admission": admission,
        "request": {"assignment_revision": packet["assignment_revision"], "target": "codex_sol", "transport": transport},
    }
    context["eligibility"] = {
        "owner": "assignment",
        "eligible": True,
        "work": work,
        "execution": execution,
        "packet_integrity": packet["packet_integrity"],
    }
    original = deepcopy(packet)
    result = replace_assignment(context)
    direct = _direct(shared_core_binary, {"replace_assignment": context})
    assert direct.returncode == 0, direct.stderr
    assert json.loads(direct.stdout) == result
    script = f"import {{replaceAssignment}} from {json.dumps((ROOT / 'bindings/node/semantic-decision.mjs').as_uri())}; console.log(JSON.stringify(replaceAssignment(JSON.parse(process.argv[1]))));"
    node = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps(context)], capture_output=True, text=True, check=False)
    assert node.returncode == 0, node.stderr
    assert json.loads(node.stdout) == result
    assert result["status"] == "replaced"
    replacement = result["packet"]
    assert packet == original
    assert replacement["target"] == "codex_sol"
    assert replacement["packet_integrity"] != packet["packet_integrity"]
    current = {"packet": replacement, "canonical": replacement, "work": work, "source": source, "execution": execution}
    assert admit_assignment_packet(current)["status"] == "current"
    assert admit_assignment_packet({**current, "packet": packet})["status"] == "blocked"
    for path in [("work", "revision"), ("source", "revision"), ("execution", "target_revision"), ("request", "assignment_revision")]:
        stale = deepcopy(context)
        stale[path[0]] = {**stale[path[0]], path[1]: "changed"}
        assert replace_assignment(stale)["status"] == "blocked", path
    missing = {**context, "admission": None}
    assert replace_assignment(missing)["reason_code"] == "assignment-override-authority-unavailable"
    forged = deepcopy(context)
    forged["current"]["assignment_identity"]["allowed_paths"] = ["**"]
    assert replace_assignment(forged)["status"] == "blocked"
    later = {**context, "current": replacement}
    assert replace_assignment(later)["status"] == "blocked"
    widened = deepcopy(current)
    widened["packet"]["scope"] = ["**"]
    assert admit_assignment_packet(widened)["status"] == "blocked"

    malformed = deepcopy(current)
    malformed["packet"]["return_contract"] = "not a return contract"
    assert admit_assignment_packet(malformed)["status"] == "blocked"

    for key, value in (("eligible", False), ("work", {"id": "other", "revision": "new"}), ("execution", {"target": "other"})):
        rejected = {**context, "eligibility": {**context["eligibility"], key: value}}
        assert replace_assignment(rejected)["status"] == "blocked"
    assert replace_assignment({**context, "eligibility": None})["reason_code"] == "assignment-replacement-eligibility-unavailable"


@pytest.mark.parametrize("constraint", ["capability", "proof", "human-control", "continuation"])
def test_replacement_consumes_full_assignment_owner_eligibility(constraint: str) -> None:
    """#2909: a constructible target is still subject to every owner hard gate."""
    from agentic_workspace.target_evidence import assignment_decision_from_policy, replacement_eligibility

    profile = {"name": "worker", "target_id": "host:worker", "target_revision": "v1", "location": "local", "execution_methods": ["cli"]}
    if constraint == "capability":
        profile["capability_mismatch"] = True
    if constraint == "proof":
        profile["proof_requirements"] = ["required-proof-missing"]
    if constraint == "human-control":
        profile["human_control_modes"] = ["off"]
    decision = assignment_decision_from_policy(
        assignment_policy={}, runtime_resolution={"profile_recommendations": [profile]}, target_evidence={}
    )
    if constraint == "continuation":
        decision["candidate_scores"][0]["permitted_continuation"] = "unsupported-result-class"
    execution = {"target": "worker", "target_identity_ref": "host:worker", "target_revision": "v1", "transport": "cli"}
    admission = replacement_eligibility(
        decision=decision, work={"id": "work", "revision": "v1"}, execution=execution, packet_integrity="seal"
    )
    assert admission["eligible"] is False
    assert admission["candidate"]["eligibility"] == decision["candidate_scores"][0]["eligibility"]

    changed_ranking = deepcopy(decision)
    changed_ranking["candidate_scores"][0]["score"] = 100000
    assert (
        replacement_eligibility(
            decision=changed_ranking, work={"id": "work", "revision": "v1"}, execution=execution, packet_integrity="seal"
        )
        == admission
    )
