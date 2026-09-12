"""Public native ingress consumed independently; no installed-platform claim."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("retired", ["close", "reassign"])
def test_retired_assignment_commands_do_not_become_hidden_owner_requests(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, retired: str
) -> None:
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        'schema_version=1\n[delegation_targets.worker]\ntarget_id="host:worker"\ntarget_revision="1"\n'
        'strength="weak"\nlocation="external"\ntransports=[{kind="manual"}]\n'
    )
    context = {"target": str(tmp_path), "task": "Inspect the current work"}
    initial = consume(surface, shared_core_binary, native_cli, context)
    request = initial["task_requirements"]["requests"][0]
    request["request_kind"] = f"assignment/{retired}/v1"
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(AssertionError, match="undeclared request kind"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_task_requirements_bind_current_judgment_and_preserve_owner_constraints(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = {"target": str(tmp_path), "task": "Inspect the policy links", "changed": ["docs/policy.md"]}
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert quiet["task_requirements"]["requests"] == []
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        'schema_version = 1\n[delegation]\nrequired_execution_guarantees = ["history.non-persisted"]\n'
        '[delegation_targets.worker]\ntarget_id = "host:worker"\ntarget_revision = "1"\n'
        'strength = "weak"\nlocation = "external"\ntransports = [{kind="manual"}]\n'
    )
    offered = consume(surface, shared_core_binary, native_cli, context)
    assert offered["task_requirements"]["result"]["requirements"] is None
    request = offered["task_requirements"]["requests"][0]
    request["arguments"]["required_result_classes"] = ["read-only"]
    resolved = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    result = resolved["task_requirements"]["result"]
    assert result["status"] == "resolved"
    assert result["requirements"]["required_execution_guarantees"] == ["history.non-persisted"]
    assert result["requirements"]["independent_context"] is False
    assert any("effect:implementation" in blocker["affects"] for blocker in resolved["decision_packet"]["blockers"])
    same = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert same["task_requirements"]["result"]["revision"] == result["revision"]
    request["arguments"]["role"] = "evaluator"
    evaluator = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert evaluator["task_requirements"]["result"]["requirements"] is None
    assert "current-evaluator-obligation-required" in evaluator["task_requirements"]["result"]["gaps"]
    request["arguments"]["role"] = "executor"
    request["arguments"]["task_identity"]["revision"] = "different-request"
    unbound = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert "task-judgment-identity-stale" in unbound["task_requirements"]["result"]["gaps"]
    source.write_text(source.read_text().replace("history.non-persisted", "history.never-visible"))
    with pytest.raises(AssertionError, match="stale for the current capability contract revision"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_requirements_preserve_planning_subject_but_stale_material_scope(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / plan_ref
    plan.parent.mkdir(parents=True)
    plan.write_bytes((ROOT / plan_ref).read_bytes())
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{plan_ref.as_posix()}"\nstatus="active"\n'
    )
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        'schema_version=1\n[delegation_targets.worker]\ntarget_id="host:worker"\ntarget_revision="1"\n'
        'strength="weak"\nlocation="external"\ntransports=[{kind="manual"}]\n'
    )
    context = {"target": str(tmp_path), "task": "Inspect the current delegation contract", "changed": ["docs/policy.md"]}
    initial = consume(surface, shared_core_binary, native_cli, context)
    continuation = initial["decision_packet"]["decision_request"]["response_request"]
    continuation["arguments"]["answer"] = "continue-selected"
    continued = consume(surface, shared_core_binary, native_cli, {**context, "request": continuation})
    request = continued["task_requirements"]["requests"][0]
    request["arguments"]["required_result_classes"] = ["read-only"]
    assert request["arguments"]["current_work"] != request["arguments"]["task_identity"]
    resolved = consume(surface, shared_core_binary, native_cli, {**context, "request": [continuation, request]})
    assert resolved["task_requirements"]["result"]["status"] == "resolved"
    record = json.loads(plan.read_text())
    record["intent"]["goal"] = "A materially different required outcome"
    plan.write_text(json.dumps(record))
    with pytest.raises(AssertionError, match="source changed"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": [continuation, request]})
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.fixture(scope="module")
def native_cli(shared_core_binary: Path) -> Path:
    subprocess.run(
        ["cargo", "build", "--locked", "-p", "agentic-workspace-core", "-p", "agentic-workspace-cli", "--bins"], cwd=ROOT, check=True
    )
    return shared_core_binary.with_name("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace")


def consume(
    surface: str,
    binary: Path,
    native: Path,
    context: dict,
    *,
    host_path: str = "",
    allow_failure: bool = False,
    reference_helper: bool = False,
) -> dict:
    context = {"projection": "full", **context}
    encoded = json.dumps(context)
    verb = "invoke" if "invocation" in context else "start"
    if surface == "native":
        command = [str(native), verb, "--format", "json"]
        for field in ("target", "task", "reference"):
            if field in context:
                command += [f"--{field}", context[field]]
        if "answer" in context:
            command += ["--answer", json.dumps(context["answer"])]
        command += ["--projection", context["projection"]]
        for reference in context.get("delivered", []):
            command += ["--delivered", reference]
        for path in context.get("changed", []):
            command += ["--changed", path]
        if context.get("request") or context.get("invocation"):
            command += ["--input", "-"]
        stdin = json.dumps(context.get("invocation", context.get("request")))
    elif surface == "json":
        command, stdin = [str(binary)], json.dumps({verb: context})
    elif surface == "python":
        command = [
            sys.executable,
            "-c",
            f"import json,sys; from agentic_workspace.decision import {verb}; print(json.dumps({verb}(json.load(sys.stdin))))",
        ]
        stdin = encoded
        if reference_helper:
            command[-1] = (
                "import json,sys; from agentic_workspace.decision import select_reference; "
                "c=json.load(sys.stdin); r=c.pop('reference'); "
                "a={'answer':c.pop('answer')} if 'answer' in c else {}; "
                "print(json.dumps(select_reference(c,r,**a)))"
            )
    else:
        module = (ROOT / "bindings/node/semantic-decision.mjs").as_uri()
        command = [
            "node",
            "--input-type=module",
            "-e",
            f"import {{{verb}}} from {json.dumps(module)}; import {{readFileSync}} from 'node:fs'; "
            f"console.log(JSON.stringify({verb}(JSON.parse(readFileSync(0, 'utf8')))));",
        ]
        stdin = encoded
        if reference_helper:
            module = (ROOT / "bindings/node/operating.mjs").as_uri()
            command[-1] = (
                f"import {{selectReference}} from {json.dumps(module)}; import {{readFileSync}} from 'node:fs'; "
                "const c=JSON.parse(readFileSync(0,'utf8')); const r=c.reference; delete c.reference; "
                "const a=Object.hasOwn(c,'answer')?[c.answer]:[]; delete c.answer; "
                "console.log(JSON.stringify(selectReference(c,r,...a)));"
            )
    environment = {**os.environ, "PATH": host_path} if surface == "native" else None
    result = subprocess.run(command, input=stdin, text=True, encoding="utf-8", capture_output=True, cwd=ROOT, check=False, env=environment)
    assert result.returncode == 0, result.stderr
    decoded = json.loads(result.stdout)
    if not allow_failure:
        assert decoded.get("status") not in {"rejected", "uncertain"}, json.dumps(decoded)
    return decoded


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_public_route_survives_fresh_process_but_not_source_change(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "inspect", "semantic_routes": ["repository/inspect"]}]}))
    context = {"target": str(tmp_path), "task": "Inspect the current repository"}
    initial = consume(surface, shared_core_binary, native_cli, context)
    assert initial["decision_packet"]["status"] == "direct"
    assert "detail" not in initial["semantic_routes"]["discovery"]
    discovery = next(item for item in initial["semantic_routes"]["requests"] if item["request_kind"] == "semantic-routes/discover/v1")
    discovery["arguments"] = {"parent": "repository/inspect"}
    detail = consume(surface, shared_core_binary, native_cli, {**context, "request": discovery})
    leaf = detail["semantic_routes"]["discovery"]["detail"]
    assert leaf["capabilities"] == ["skill:inspect"]
    assert leaf["sources"][0]["procedure"]["reason"] == "procedure-path-undeclared"
    request = next(item for item in initial["semantic_routes"]["requests"] if item["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "selected", "routes": ["repository/inspect"]}
    selected = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert selected["semantic_routes"]["status"] == "current"
    assert selected["decision_packet"]["semantic_task_routes"]["routes"] == ["repository/inspect"]
    registry.write_text(registry.read_text() + "\n")
    stale = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert stale["semantic_routes"]["status"] == "stale"
    assert stale["decision_packet"]["semantic_task_routes"]["status"] != "current"
    stale_detail = consume(surface, shared_core_binary, native_cli, {**context, "request": discovery})
    assert stale_detail["semantic_routes"]["status"] == "stale"
    assert "detail" not in stale_detail["semantic_routes"]["discovery"]
    assert not (tmp_path / ".agentic-workspace").exists()


@pytest.mark.parametrize("selection_source", ["local", "shared"])
@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_former_planning_native_invocation_and_fresh_continuation(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, selection_source: str
) -> None:
    plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / plan_ref
    plan.parent.mkdir(parents=True)
    original = (ROOT / plan_ref).read_bytes()
    plan.write_bytes(original)
    selection = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    if selection_source == "local":
        selection.parent.mkdir(parents=True)
        selection.write_text(
            json.dumps(
                {
                    "kind": "agentic-planning/owner-selection/v1",
                    "mode": "local",
                    "current_work_id": "default",
                    "selected_owner": {"id": "delegation-lane-sweep", "ref": plan_ref.as_posix()},
                }
            )
        )
    else:
        state = tmp_path / ".agentic-workspace/planning/state.toml"
        state.write_text(f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{plan_ref.as_posix()}"\nstatus="active"\n')
    context = {"target": str(tmp_path), "task": "Preserve the current reconstruction scope and returned work"}
    initial = consume(surface, shared_core_binary, native_cli, context)
    if selection_source == "shared":
        assert not selection.parent.exists(), "read-only discovery must not acquire local custody"
    question = initial["decision_packet"]["decision_request"]
    request = question["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    continued = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    if selection_source == "shared":
        assert not selection.parent.exists(), "constructing intention must not mutate state"
    if selection_source == "local":
        assert any(item["code"] == "planning-selection-custody-required" for item in continued["decision_packet"]["blockers"])
        assert not (tmp_path / ".agentic-workspace/local/effects").exists()
        assert "reconciliation" not in json.loads(selection.read_text())
        assert plan.read_bytes() == original
        return
    action = continued["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.reconcile"
    applied = consume(surface, shared_core_binary, native_cli, {**context, "invocation": action})
    assert applied["status"] == "applied"
    fresh = consume(surface, shared_core_binary, native_cli, context)
    assert fresh["planning"]["current_owner"]["current"] is True
    assert fresh["decision_packet"]["status"] != "terminal"
    assert plan.read_bytes() == original
    assert json.loads(selection.read_text())["reconciliation"]["custody"]["committed"]
    files = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    replayed = consume(surface, shared_core_binary, native_cli, {**context, "invocation": action})
    assert replayed["status"] == applied["status"]
    assert replayed["value"] == applied["value"]
    assert files == {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_former_planning_typed_assurance_facts(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    reference = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    path = tmp_path / reference
    path.parent.mkdir(parents=True)
    body = json.loads((ROOT / reference).read_bytes())
    # Real compact former owner plus exact existing typed assurance declarations
    # from the worker-context owner, and explicit fixture-owned risk/invariant refs.
    richer = json.loads((ROOT / ".agentic-workspace/planning/execplans/issue-2818-worker-context-cost.plan.json").read_bytes())
    body["adaptive_assurance"] = richer["adaptive_assurance"]
    body["risk_registry_refs"] = ["risk:fixture"]
    body["invariant_refs"] = ["invariant:fixture"]
    path.write_text(json.dumps(body))
    (path.parent.parent / "state.toml").write_text(
        f'[[active.execplans]]\nid="{body["id"]}"\npath="{reference.as_posix()}"\nstatus="active"\n'
    )
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version=1\n"
        '[assurance.requirements.profile]\nlevel="high"\nforce="blocking"\napplies_to_proof_profiles=["assignment lifecycle"]\n'
        '[assurance.requirements.risk]\nlevel="high"\nforce="blocking"\napplies_to_risk_refs=["risk:fixture"]\n'
        '[assurance.requirements.invariant]\nlevel="high"\nforce="blocking"\napplies_to_invariant_refs=["invariant:fixture"]\n'
        '[assurance.proof_profiles."assignment lifecycle"]\nrequired_commands=["echo bounded"]\n'
        '[assurance.proof_profiles."target evidence and best-fit selection"]\nrequired_commands=["echo contextual"]\n'
        '[assurance.proof_profiles."supported-host dogfood"]\nrequired_commands=["echo host"]\n'
    )
    context = {"target": str(tmp_path), "task": "Continue the bounded current outcome"}

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value)

    def statuses(value: dict) -> set[str]:
        return {r["status"] for r in value["verification"]["assurance_applicability"]["requirements"]}

    initial = call(context)
    assert statuses(initial) == {"unresolved"}
    continuation = initial["planning"]["requests"][0]
    continued = call({**context, "request": continuation})
    assert statuses(continued) == {"applicable"}
    assert continued["planning"]["current_owner"]["reconciliation"]["coverage"]["complete"] is True
    action = continued["decision_packet"]["primary_action"]
    call({**context, "invocation": action})
    fresh = call(context)
    assert statuses(fresh) == {"applicable"}
    old_subject = fresh["planning"]["current_owner"]["reconciliation"]["subject"]
    assert old_subject["state"]["proof"]["adaptive_assurance"] == richer["adaptive_assurance"]
    assert fresh["verification"]["evidence"] == []
    strategy = fresh["verification"]["strategy_control"]
    assert {r["id"] for r in strategy["selected_profiles"]} == set(richer["adaptive_assurance"]["proof_profiles"])
    assert all(
        r["selected_by"] == "planning-owner" and r["evidence_status"] == "not-established-by-selection"
        for r in strategy["selected_profiles"]
    )
    assert len(strategy["obligations"]) == 3
    assert "planning-assurance-profile-projection-unavailable" not in strategy["gaps"]
    assert fresh["decision_packet"]["status"] != "terminal"
    unrelated = {**fresh["planning"]["requests"][0], "arguments": {"answer": "unrelated-direct"}}
    assert statuses(call({**context, "request": unrelated})) == {"not-applicable"}
    old_claim = fresh["verification"]["requests"][0]
    body["adaptive_assurance"]["proof_profiles"].append("missing-current-profile")
    path.write_text(json.dumps(body))
    missing = call(context)
    missing = call({**context, "request": missing["planning"]["requests"][0]})
    assert "selected-proof-profile-unavailable:missing-current-profile" in missing["verification"]["strategy_control"]["gaps"]
    assert missing["verification"]["strategy_control"]["execution_blocked"] is True
    body["adaptive_assurance"]["proof_profiles"] = []
    body["risk_registry_refs"] = []
    del body["invariant_refs"]
    path.write_text(json.dumps(body))
    stale = call({**context, "request": old_claim})
    assert "verification-request-stale" in stale["verification"]["evidence_gaps"]
    current = call(context)
    request = current["planning"]["requests"][0]
    revised = call({**context, "request": request})
    rows = {r["id"]: r["status"] for r in revised["verification"]["assurance_applicability"]["requirements"]}
    assert rows == {"profile": "not-applicable", "risk": "not-applicable", "invariant": "unresolved"}
    assert revised["verification"]["strategy_control"]["selected_profiles"] == []
    assert "planning-assurance-profile-projection-unavailable" not in revised["verification"]["strategy_control"]["gaps"]
    assert revised["planning"]["current_owner"]["reconciliation"]["subject"]["revision"] != old_subject["revision"]
    body["risk_registry_refs"] = "not a typed list"
    path.write_text(json.dumps(body))
    preserved = path.read_bytes()
    with pytest.raises(AssertionError, match="invalid Planning assurance"):
        call({**context, "request": call(context)["planning"]["requests"][0]})
    assert path.read_bytes() == preserved


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_former_planning_returned_continuation_preserves_semantic_owner(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    # Real former owner, with controlled owner-authored return observations.
    # This proves continuation, not an actual delegated worker or admitted result.
    reference = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    body = json.loads((ROOT / reference).read_bytes())
    body["relationships"].update(
        dependencies={"subject": "verification", "revision": "fixture-obligation"},
        assignment={"subject": "bounded-work", "owner": "fixture-worker", "attempt": 1},
        returned={"subject": "bounded-work"},
        integration_pending={"subject": "bounded-work"},
    )
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    plan.write_text(json.dumps(body))
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{reference.as_posix()}"\nstatus="active"\n'
    )
    context = {"target": str(tmp_path), "task": "Continue the current reconstruction owner"}

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value)

    def reconcile():
        initial = call(context)
        answer = initial["decision_packet"]["decision_request"]["response_request"]
        answer["arguments"]["answer"] = "continue-selected"
        action = call({**context, "request": answer})["decision_packet"]["primary_action"]
        assert action["operation_id"] == "planning.reconcile"
        call({**context, "invocation": action})
        fresh = call(context)
        assert fresh["planning"]["current_owner"]["current"] is True
        assert fresh["decision_packet"]["status"] != "terminal"
        return fresh["planning"]["current_owner"]["reconciliation"]["subject"], action

    initial, _ = reconcile()
    for phase in ["returned", "integration-pending"]:
        body["phase"] = phase
        body["relationships"]["assignment"].update(attempt=2, status=phase)
        body["relationships"]["returned"].update(result="fixture-result", status="awaiting-admission")
        body["relationships"]["integration_pending"].update(result="fixture-result", status=phase)
        body["proof"]["refs"] = ["proof://unadmitted-return-observation"]
        raw = json.dumps(body).encode()
        plan.write_bytes(raw)
        current, prior_action = reconcile()
        assert (current["id"], current["revision"]) == (initial["id"], initial["revision"])
        state = current["state"]
        assert state["frontier"]["phase"] == phase
        assert state["scope"]["declared"] == body["scope"]
        assert state["canonical_core"] == body["canonical_core"]
        assert state["dependencies"]["declared"] == body["relationships"]["dependencies"]
        assert state["proof"]["declared"] == body["proof"]
        assert state["residual"]["continuation"] == body["continuation"]
        for field in ["assignment", "returned", "integration_pending"]:
            assert state["handoff"][field] == body["relationships"][field]
        assert plan.read_bytes() == raw
    body["canonical_core"]["hard_constraints"] = "Stop before changing the newly protected material scope"
    plan.write_text(json.dumps(body))
    with pytest.raises(AssertionError):
        call({**context, "invocation": prior_action})
    revised, _ = reconcile()
    assert revised["id"] == initial["id"]
    assert revised["revision"] != initial["revision"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_unrelated_claim_request_keeps_planning_quiet_without_chat_state(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / plan_ref
    plan.parent.mkdir(parents=True)
    plan.write_bytes((ROOT / plan_ref).read_bytes())
    selection = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "default",
                "selected_owner": {"id": "delegation-lane-sweep", "ref": plan_ref.as_posix()},
            }
        )
    )
    context = {"target": str(tmp_path), "task": "Explain the spelling in an unrelated document", "changed": ["notes.txt"]}
    initial = consume(surface, shared_core_binary, native_cli, context)
    planning_request = initial["decision_packet"]["decision_request"]["response_request"]
    planning_request["arguments"]["answer"] = "unrelated-direct"
    claim_request = initial["verification"]["requests"][0]
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    result = consume(surface, shared_core_binary, native_cli, {**context, "request": [planning_request, claim_request]})
    assert result["planning"]["current_owner"] is None
    assert result["verification"]["judgment_request"]["planning_subject"] is None
    assert result["verification"]["status"] == "unresolved"
    assert "current-task-claim-judgment-not-admitted" in result["verification"]["evidence_gaps"]
    assert before == {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_published_passed_receipt_cannot_complete_unrelated_current_task(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    fixture = json.loads((ROOT / "tests/fixtures/native_verification_publication.json").read_text())
    receipts = tmp_path / ".agentic-workspace/proof/receipts"
    receipts.mkdir(parents=True)
    (receipts / "index.json").write_text(json.dumps(fixture["index"]))
    (receipts / f"{fixture['publication_id']}.json").write_text(json.dumps(fixture["receipt"]))
    (tmp_path / "a.txt").write_text("one")
    context = {"target": str(tmp_path), "task": "Verify an unrelated document claim", "changed": ["a.txt"]}
    first = consume(surface, shared_core_binary, native_cli, context)
    request = first["verification"]["requests"][0]
    request["arguments"]["evidence_refs"] = [fixture["receipt"]["source_ref"]]
    result = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    evidence = result["verification"]["evidence"][0]
    assert evidence["publication_admission"]["status"] == "admitted"
    assert evidence["receipt_admission"]["admitted"] is True
    assert evidence["status"] == "unadmitted"
    assert "task-claim-mismatch-or-missing-identity" in evidence["gaps"]
    assert result["decision_packet"]["status"] != "terminal"
    (tmp_path / "a.txt").write_text("two")
    stale = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert "proof-semantic-input-stale-or-unavailable" in stale["verification"]["evidence"][0]["gaps"]


def pin_instructions(target: Path) -> str:
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "add", ".agentic-workspace/instructions"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(target),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Own current fixture instructions",
        ],
        check=True,
    )
    pin = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
    (target / ".agentic-workspace/config.toml").write_text(f"schema_version=1\n[assurance]\ninstruction_revision='{pin}'\n")
    return pin


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_instruction_protection_and_source_drift(surface: str, tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    source = ".agentic-workspace/instructions/workspace-operating.md"
    instruction = tmp_path / source
    instruction.parent.mkdir(parents=True)
    instruction.write_bytes((ROOT / source).read_bytes())
    pin_instructions(tmp_path)
    protected = ".agentic-workspace/local/decision-point-intent/73a213e66cd48a33.json"
    context = {"target": str(tmp_path), "task": "Preserve the current source-owned decision", "changed": [protected]}
    host_path = str(Path(shutil.which("git")).parent)
    current = consume(surface, shared_core_binary, native_cli, context, host_path=host_path)
    row = current["instructions"]["sources"][0]
    assert row["binding_admission"]["status"] == "current"
    assert row["guidance"]
    assert any(f"effect:write:{protected}" in item["affects"] for item in current["decision_packet"]["blockers"])
    assert not current["configuration"]["residuals"]
    instruction.write_bytes(instruction.read_bytes() + b"\nSource revision changed.\n")
    stale = consume(surface, shared_core_binary, native_cli, context, host_path=host_path)
    assert stale["instructions"]["sources"][0]["binding_admission"]["status"] == "stale"
    assert any("binding-unadmitted" in item["code"] for item in stale["decision_packet"]["blockers"])


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("route", ["create", "refine"])
def test_instruction_procedure_requires_current_route_not_task_words(
    surface: str, tmp_path: Path, shared_core_binary: Path, native_cli: Path, route: str
) -> None:
    name = "creation" if route == "create" else "refinement"
    source = f".agentic-workspace/instructions/github-issue-{name}.md"
    instruction = tmp_path / source
    instruction.parent.mkdir(parents=True)
    instruction.write_bytes((ROOT / source).read_bytes())
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_bytes((ROOT / "tools/skills/REGISTRY.json").read_bytes())
    for skill in ["github-issue-shaping", "github-issue-creation"]:
        procedure = tmp_path / f"tools/skills/{skill}/SKILL.md"
        procedure.parent.mkdir()
        procedure.write_bytes((ROOT / procedure.relative_to(tmp_path)).read_bytes())
    context = {"target": str(tmp_path), "task": "Explain the words GitHub issue creation and refinement"}
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert not quiet["instructions"]["sources"][0]["guidance"]
    discovery = next(item for item in quiet["semantic_routes"]["requests"] if item["request_kind"] == "semantic-routes/discover/v1")
    discovery["arguments"] = {"parent": f"github/issues/{route}"}
    detail = consume(surface, shared_core_binary, native_cli, {**context, "request": discovery})
    leaf = detail["semantic_routes"]["discovery"]["detail"]
    bindings = leaf["capability_bindings"]
    expected = {"skill:github-issue-shaping"}
    if route == "create":
        expected.add("skill:github-issue-creation")
    assert {binding["capability"] for binding in bindings} == expected
    assert all(source["procedure"]["status"] == "available" for source in leaf["sources"])
    missing = tmp_path / "tools/skills/github-issue-shaping/SKILL.md"
    missing.unlink()
    unavailable = consume(surface, shared_core_binary, native_cli, {**context, "request": discovery})
    sources = unavailable["semantic_routes"]["discovery"]["detail"]["sources"]
    assert next(source for source in sources if source["skill_id"] == "github-issue-shaping")["procedure"]["status"] == "unavailable"
    request = next(item for item in quiet["semantic_routes"]["requests"] if item["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "selected", "routes": [f"github/issues/{route}"]}
    selected = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    row = selected["instructions"]["sources"][0]
    assert row["preferred_procedures"] == (
        ["github-issue-shaping", "github-issue-creation"] if route == "create" else ["github-issue-shaping"]
    )
    assert row["binding_admission"]["status"] == "not-required"
    assert not selected["decision_packet"]["ready_actions"]
    assert not selected["decision_packet"]["blockers"]
    for projection in ("compact", "carried"):
        projected = consume(surface, shared_core_binary, native_cli, {**context, "request": request, "projection": projection})
        visible = projected["view"] if projection == "carried" else projected
        assert visible["decision_packet"]["material"]["scoped-instructions"] == [row]
    assert "material" not in quiet["decision_packet"]
    continued = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert continued["instructions"]["sources"][0]["preferred_procedures"] == row["preferred_procedures"]
    stale = consume(surface, shared_core_binary, native_cli, {**context, "task": "A different issue discussion", "request": request})
    assert stale["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    assert not stale["instructions"]["sources"][0]["guidance"]
    registry.write_bytes(registry.read_bytes() + b"\n")
    drifted = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert drifted["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    assert not drifted["instructions"]["sources"][0]["guidance"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_instruction_protection_reaches_actual_planning_writes(
    surface: str, tmp_path: Path, shared_core_binary: Path, native_cli: Path
) -> None:
    plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / plan_ref
    plan.parent.mkdir(parents=True)
    plan.write_bytes((ROOT / plan_ref).read_bytes())
    selection_ref = ".agentic-workspace/local/planning/owner-selection.json"
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{plan_ref.as_posix()}"\nstatus="active"\n'
    )
    context = {"target": str(tmp_path), "task": "Continue the selected documentation outcome", "changed": ["docs/notes.md"]}
    first = consume(surface, shared_core_binary, native_cli, context)
    request = first["decision_packet"]["decision_request"]["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    before_policy = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    action = before_policy["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.reconcile"
    instruction = tmp_path / ".agentic-workspace/instructions/custody.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text(f"---\npaths: [.agentic-workspace/**]\nprotect: [{selection_ref}]\n---\nPreserve current custody.\n")
    pin_instructions(tmp_path)
    host_path = str(Path(shutil.which("git")).parent)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in (tmp_path / ".agentic-workspace").rglob("*") if path.is_file()}
    with pytest.raises(AssertionError, match="invocation is stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "invocation": action}, host_path=host_path)
    assert before == {
        path.relative_to(tmp_path): path.read_bytes() for path in (tmp_path / ".agentic-workspace").rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("planning", [False, True])
@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_exact_published_judgment_is_recognized_without_manufacturing_evidence(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, planning: bool
) -> None:
    # Retained historical source fixture tests exact identity recognition only.
    # It acquires no publication custody and supplies no human/domain acceptance.
    from agentic_workspace.workspace_runtime_core import _proof_publication_identity

    (tmp_path / "a.txt").write_text("one")
    context = {"target": str(tmp_path), "task": "Establish the current document claim", "changed": ["a.txt"]}
    if planning:
        plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
        plan = tmp_path / plan_ref
        plan.parent.mkdir(parents=True)
        plan.write_bytes((ROOT / plan_ref).read_bytes())
        (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
            f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{plan_ref.as_posix()}"\nstatus="active"\n'
        )
        discovered = consume(surface, shared_core_binary, native_cli, context)
        continuation = discovered["decision_packet"]["decision_request"]["response_request"]
        continuation["arguments"]["answer"] = "continue-selected"
        continued = consume(surface, shared_core_binary, native_cli, {**context, "request": continuation})
        consume(surface, shared_core_binary, native_cli, {**context, "invocation": continued["decision_packet"]["primary_action"]})
    initial = consume(surface, shared_core_binary, native_cli, context)
    request = initial["verification"]["requests"][0]
    requested = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    subject = requested["verification"]["judgment_request"]
    historical = json.loads((ROOT / "tests/fixtures/native_verification_publication.json").read_text())
    receipt = historical["receipt"]
    receipt["task_claim_judgment"].update(
        work_ref=subject["work_ref"], work_revision=subject["work_revision"], task_identity=subject["task_claim_identity"]
    )
    publication_id = hashlib.sha256(
        json.dumps(_proof_publication_identity(receipt), sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()[:16]
    receipt.update(publication_id=publication_id, receipt_id=publication_id)
    reference = f"proof://receipts/{publication_id}"
    receipt["source_ref"] = reference
    old_entry = next(iter(historical["index"]["receipts"].values()))
    entry = {**old_entry, "path": f"{publication_id}.json", "source_ref": reference}
    receipts = tmp_path / ".agentic-workspace/proof/receipts"
    receipts.mkdir(parents=True)
    (receipts / f"{publication_id}.json").write_text(json.dumps(receipt))
    (receipts / "index.json").write_text(json.dumps({**historical["index"], "receipts": {publication_id: entry}}))
    request["arguments"]["evidence_refs"] = [reference]
    current = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    evidence = current["verification"]["evidence"][0]
    assert evidence["task_judgment"]["matched_judgment_count"] == 1
    assert evidence["task_judgment"]["current_judgment_count"] == 0
    assert evidence["evidence_freshness"] == "unproven"
    assert evidence["strategy_coverage"] == "unproven"
    assert current["decision_packet"]["status"] != "terminal"
    if planning:
        other_context = {**context, "task": "Establish a different requested outcome in the same plan"}
        discovered = consume(surface, shared_core_binary, native_cli, other_context)
        continuation = discovered["decision_packet"]["decision_request"]["response_request"]
        continuation["arguments"]["answer"] = "continue-selected"
        continued = consume(surface, shared_core_binary, native_cli, {**other_context, "request": continuation})
        other_request = continued["verification"]["requests"][0]
        other_request["arguments"]["evidence_refs"] = [reference]
        other = consume(surface, shared_core_binary, native_cli, {**other_context, "request": [continuation, other_request]})
        assert other["verification"]["judgment_request"]["work_ref"] == subject["work_ref"]
        assert other["verification"]["judgment_request"]["work_revision"] == subject["work_revision"]
        assert other["verification"]["evidence"][0]["task_judgment"]["matched_judgment_count"] == 0
        assert "exact-task-request-identity-mismatch" in other["verification"]["evidence"][0]["gaps"]
    index_path = tmp_path / ".agentic-workspace/proof/receipts/index.json"
    index = json.loads(index_path.read_text())
    index["receipts"][publication_id]["status"] = "superseded"
    index_path.write_text(json.dumps(index))
    stale = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert stale["verification"]["evidence"][0]["task_judgment"]["matched_judgment_count"] == 0


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_memory_note_is_selective_advisory_and_read_through_current_request(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    manifest_ref = Path(".agentic-workspace/memory/repo/manifest.toml")
    note_ref = Path(".agentic-workspace/memory/repo/domains/example-runtime-boundary.md")
    manifest = tmp_path / manifest_ref
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes((ROOT / manifest_ref).read_bytes())
    note = tmp_path / note_ref
    note.parent.mkdir(parents=True)
    original = (ROOT / note_ref).read_bytes()
    note.write_bytes(original)
    quiet = consume(
        surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Explain unrelated prose", "changed": ["notes.txt"]}
    )
    assert quiet["memory"]["selected_notes"] == []
    assert quiet["memory"]["requests"] == []
    assert quiet["decision_packet"]["status"] == "direct"
    context = {"target": str(tmp_path), "task": "Inspect the runtime boundary", "changed": ["src/agentic_workspace/native_core.py"]}
    selected = consume(surface, shared_core_binary, native_cli, context)
    assert selected["decision_packet"]["status"] == "direct"
    assert all("body" not in item for item in selected["memory"]["selected_notes"])
    request = next(item for item in selected["memory"]["requests"] if item["arguments"]["reference"] == note_ref.as_posix())
    detail = consume(surface, shared_core_binary, native_cli, {**context, "request": request})["memory"]["response"]
    assert detail["status"] == "read"
    assert detail["detail"]["body"].encode() == original
    assert detail["detail"]["authority_effect"] == "advisory-only"
    assert detail["detail"]["currentness"]["status"] == "review-required"
    assert not (tmp_path / ".agentic-workspace/local").exists()
    note.write_bytes(original + b"\nThe source changed.\n")
    with pytest.raises(AssertionError, match="Memory request is stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    other = {**context, "task": "Unrelated work", "changed": ["notes.txt"], "request": request}
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, other)


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_malformed_advisory_memory_cannot_veto_direct_work(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    manifest = tmp_path / ".agentic-workspace/memory/repo/manifest.toml"
    manifest.parent.mkdir(parents=True)
    original = b"This is not TOML ["
    manifest.write_bytes(original)
    context = {"target": str(tmp_path), "task": "Explain an unrelated detail"}
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert quiet["memory"]["selected_notes"] == []
    assert quiet["memory"]["diagnostics"] == []
    observed = consume(surface, shared_core_binary, native_cli, {**context, "changed": ["notes.txt"]})
    assert observed["memory"]["status"] == "reconciliation-required"
    assert observed["memory"]["diagnostics"]
    assert observed["decision_packet"]["status"] == "direct"
    assert not observed["decision_packet"]["blockers"]
    assert manifest.read_bytes() == original
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_reader_admission_precedes_every_domain_source(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[cli_compatibility]\nminimum_reader_epoch=2\nrequired_reader_capabilities=["future-reader"]\n')
    poisoned = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    poisoned.parent.mkdir(parents=True)
    poisoned.write_text("not JSON and never admitted")
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text("invalid route JSON")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    context = {"target": str(tmp_path), "task": "Continue current work"}
    blocked = consume(surface, shared_core_binary, native_cli, context)
    assert blocked["failed_checks"] == ["minimum_reader_epoch", "required_reader_capabilities"]
    assert blocked["managed_state_interpreted"] is False
    assert "decision_packet" not in blocked
    invoked = consume(
        surface, shared_core_binary, native_cli, {**context, "invocation": {"operation_id": "planning.reconcile"}}, allow_failure=True
    )
    assert invoked["effect_outcome"]["status"] == "rejected-before-effect"
    assert invoked["blockers"] == blocked
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_current_reader_proceeds_with_product_identity_and_retains_installed_residuals(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text(
        'schema_version=1\n[cli_compatibility]\nminimum_reader_epoch=1\nrequired_reader_capabilities=["pre-state-runtime-compatibility-v1"]\nexact_version="99.0"\n'
    )
    context = {"target": str(tmp_path), "task": "Inspect current work"}
    result = consume(surface, shared_core_binary, native_cli, context)
    assert result["runtime_compatibility"]["status"] == "admitted"
    from agentic_workspace import __version__

    assert result["runtime_compatibility"]["observed_runtime"]["version"] == __version__
    residuals = result["configuration"]["residuals"]
    assert any(r["field"] == "cli_compatibility.exact_version" for r in residuals)
    assert not any(
        r["field"] in {"cli_compatibility.minimum_reader_epoch", "cli_compatibility.required_reader_capabilities"} for r in residuals
    )


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize(
    "declaration,failed_check",
    [
        ('cli_compatibility="invalid"', "compatibility_contract_shape"),
        ('cli_compatibility=["invalid"]', "compatibility_contract_shape"),
        ('[cli_compatibility]\ncontract_schema=""', "compatibility_contract_shape"),
        ("[cli_compatibility]\nrequired_reader_capabilities=[1]", "compatibility_contract_shape"),
        ('[cli_compatibility]\ncontract_schema="agentic-workspace/future-contract/v99"', "contract_schema"),
    ],
)
def test_native_reader_rejects_invalid_or_unknown_contract_before_domain_parsing(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, declaration: str, failed_check: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("schema_version=1\n" + declaration + "\n")
    plan = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    plan.parent.mkdir(parents=True)
    plan.write_text("unreadable domain state")
    routes = tmp_path / "tools/skills/REGISTRY.json"
    routes.parent.mkdir(parents=True)
    routes.write_text("unreadable route state")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Continue current work"})
    assert result["status"] == "blocked"
    assert result["failed_checks"] == [failed_check]
    assert result["managed_state_interpreted"] is False
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_current_schema_consumption_preserves_other_residuals(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    declaration = 'schema_version=1\n[cli_compatibility]\ncontract_schema="agentic-workspace/installed-state-compatibility/v1"\n'
    config.write_text(declaration)
    context = {"target": str(tmp_path), "task": "Inspect unrelated source"}
    current = consume(surface, shared_core_binary, native_cli, context)
    assert current["runtime_compatibility"]["status"] == "admitted"
    assert current["configuration"]["residuals"] == []
    assert current["decision_packet"]["status"] == "direct"
    config.write_text(declaration + 'enforcement="advisory"\nrequired_resources=["agentic_workspace:unobserved-resource"]\n')
    residual = consume(surface, shared_core_binary, native_cli, context)
    fields = {item["field"] for item in residual["configuration"]["residuals"]}
    assert fields == {"cli_compatibility.enforcement", "cli_compatibility.required_resources"}
    assert residual["decision_packet"]["status"] == "direct"
    assert all(
        item["authority"] == "advisory" and item["satisfaction"] == "not-evidence" for item in residual["configuration"]["residuals"]
    )
    config.write_text(declaration + 'enforcement="blocking"\nrequired_resources=["agentic_workspace:unobserved-resource"]\n')
    assert consume(surface, shared_core_binary, native_cli, context)["decision_packet"]["status"] == "blocked"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize(
    ("setting", "failed_check"),
    [
        ('contract_schema="agentic-workspace/future-contract/v99"', "contract_schema"),
        ("minimum_reader_epoch=999", "minimum_reader_epoch"),
        ('required_reader_capabilities=["future-reader"]', "required_reader_capabilities"),
    ],
)
def test_native_advisory_does_not_waive_prestate_reader_contract(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, setting: str, failed_check: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[cli_compatibility]\nenforcement="advisory"\n' + setting + "\n")
    state = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    state.parent.mkdir(parents=True)
    state.write_bytes(b"unreadable source must remain untouched")
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_bytes(b"unreadable route registry")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Continue current work"})
    assert result["status"] == "blocked"
    assert result["failed_checks"] == [failed_check]
    assert result["managed_state_interpreted"] is False
    assert "decision_packet" not in result
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_explicit_empty_modules_stays_quiet_without_sources(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("schema_version=1\n[modules]\nenabled=[]\n")
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Inspect unrelated source"})
    assert result["decision_packet"]["status"] == "direct"
    assert result["configuration"]["residuals"] == []
    for owner in ("planning", "memory", "verification"):
        assert result[owner]["status"] == "disabled"
        assert result[owner]["requests"] == []
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize(
    ("owner", "reference"),
    [
        ("planning", ".agentic-workspace/local/planning/owner-selection.json"),
        ("memory", ".agentic-workspace/memory/repo/manifest.toml"),
        ("verification", ".agentic-workspace/verification/manifest.toml"),
        ("verification", ".agentic-workspace/proof/receipts/index.json"),
        ("verification", ".agentic-workspace/local/independent-review-host-results/index.json"),
    ],
)
def test_native_disabled_owner_preserves_uninterpreted_source(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, owner: str, reference: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("schema_version=1\n[modules]\nenabled=[]\n")
    source = tmp_path / reference
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"invalid state must not be decoded or adopted")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    context = {"target": str(tmp_path), "task": "Inspect unrelated source"}
    result = consume(surface, shared_core_binary, native_cli, context)
    assert result[owner]["status"] == "disabled"
    assert result[owner]["sources"][0]["status"] == "present-uninterpreted"
    assert any(b["code"].endswith("disabled-owner-source-reconciliation-required") for b in result["decision_packet"]["blockers"])
    assert result[owner]["requests"] == []
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    again = consume(surface, shared_core_binary, native_cli, context)
    assert again[owner]["source_revision"] == result[owner]["source_revision"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_disabled_verification_cannot_discard_assurance(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text(
        'schema_version=1\n[modules]\nenabled=[]\n[assurance.requirements.review]\nlevel="high"\nforce="blocking"\napplies_to_paths=["src/**"]\nblocking_claims=["claim-work-complete"]\nrequired_evidence=["domain-review"]\n'
    )
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Change source", "changed": ["src/a.py"]})
    assert result["verification"]["status"] == "disabled"
    assert any(r["field"] == "assurance.requirements" and r["affects"] == ["claim:complete"] for r in result["configuration"]["residuals"])
    assert result["decision_packet"]["blockers"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_enablement_change_stales_planning_request_and_action(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    reference = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    plan.write_bytes((ROOT / reference).read_bytes())
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{reference.as_posix()}"\nstatus="active"\n'
    )
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text('schema_version=1\n[modules]\nenabled=["planning"]\n')
    context = {"target": str(tmp_path), "task": "Continue this owner"}
    current = consume(surface, shared_core_binary, native_cli, context)
    request = current["decision_packet"]["decision_request"]["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    selected = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    action = selected["decision_packet"]["primary_action"]
    config.write_text('schema_version=1\n[modules]\nenabled=["planning","memory"]\n')
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "invocation": action})
    assert not (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").exists()
    config.write_text("schema_version=1\n[modules]\nenabled=[]\n")
    with pytest.raises(AssertionError, match="disabled"):
        consume(surface, shared_core_binary, native_cli, {**context, "invocation": action})
    assert not (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").exists()
    config.write_text('schema_version=1\n[modules]\nenabled=["planning"]\n')
    restored = consume(surface, shared_core_binary, native_cli, context)
    fresh = restored["decision_packet"]["decision_request"]["response_request"]
    fresh["arguments"]["answer"] = "continue-selected"
    current_action = consume(surface, shared_core_binary, native_cli, {**context, "request": fresh})["decision_packet"]["primary_action"]
    applied = consume(surface, shared_core_binary, native_cli, {**context, "invocation": current_action})
    assert applied["status"] == "applied"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_enablement_change_stales_proof_execution(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    from tests.test_native_proof_producer import fixture

    context = fixture(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text('schema_version=1\n[modules]\nenabled=["verification"]\n')

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    current = call(context)
    request = current["verification"]["execution_requests"][0]
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    config.write_text('schema_version=1\n[modules]\nenabled=["verification","memory"]\n')
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": action})
    config.write_text("schema_version=1\n[modules]\nenabled=[]\n")
    with pytest.raises(AssertionError, match="disabled"):
        call({**context, "invocation": action})
    assert not (tmp_path / "count.txt").exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("source_owner", ["repository", "memory"])
def test_public_read_real_repository_decision_preserves_currentness(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, source_owner: str
) -> None:
    import tomllib

    from tests.test_shared_core import _commit_native

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    reference = "docs/decisions/shared-semantic-authority.md"
    source = (ROOT / reference).read_bytes()
    if source_owner == "memory":
        reference = ".agentic-workspace/memory/repo/decisions/shared-semantic-authority.md"
    path = tmp_path / reference
    path.parent.mkdir(parents=True)
    path.write_bytes(source)
    # Real admitted rationale and its existing basis; no invented author or
    # changed decision. This fixture's commit is a host admission, not review.
    admitted = tomllib.loads((ROOT / ".agentic-workspace/config.toml").read_text())["assurance"]["decision_record_revision"]
    basis = subprocess.run(["git", "show", f"{admitted}:SYSTEM_INTENT.md"], cwd=ROOT, check=True, capture_output=True).stdout
    (tmp_path / "SYSTEM_INTENT.md").write_bytes(basis)
    record = json.loads(source.decode().split("```aw-decision\n", 1)[1].split("\n```", 1)[0])
    assert record["authority"]["basis"][0]["revision"] == "sha256:" + hashlib.sha256(basis.replace(b"\r\n", b"\n")).hexdigest()
    revision = _commit_native(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir(exist_ok=True)
    admission = (
        f'decision_record_fallback={{archive=".agentic-workspace/memory/repo/decisions",admitted_revision="{revision}"}}'
        if source_owner == "memory"
        else f'decision_record_target="docs/decisions"\ndecision_record_revision="{revision}"'
    )
    config.write_text(f'schema_version=1\n[modules]\nenabled=["memory"]\n[assurance]\n{admission}\n')
    context = {
        "target": str(tmp_path),
        "task": "Review the public semantic boundary",
        "changed": ["crates/agentic-workspace-core/src/lib.rs"],
    }

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    initial = call(context)
    request = initial["decision_sources"]["requests"][0]
    assert request["arguments"]["source"]["owner"] == source_owner
    assert initial["decision_packet"]["decision_context"]["consequences"][0]["id"] == record["id"]
    assert "response" not in initial["decision_sources"]
    selected = call({**context, "request": request})
    response = selected["decision_sources"]["response"]
    assert response["body"].replace("\r\n", "\n") == source.decode().replace("\r\n", "\n")
    assert response["decision_state"]["status"] == "current"
    assert response["authority_effect"] == "no-new-authority"
    assert selected["decision_packet"]["status"] != "terminal"
    quiet_context = {**context, "changed": ["unrelated.txt"]}
    assert call(quiet_context)["decision_sources"]["requests"] == []
    with pytest.raises(AssertionError):
        call({**quiet_context, "request": request})
    if source_owner == "memory":
        # The configured source admission, not readable bytes or actor strings,
        # owns the consequence. Disabling Memory must also disable this ingress.
        shared = config.read_text()
        config.write_text(shared.replace('enabled=["memory"]', "enabled=[]"))
        disabled = call(context)
        assert disabled["decision_sources"]["requests"] == []
        assert not disabled["decision_packet"].get("decision_context", {}).get("consequences")
        with pytest.raises(AssertionError):
            call({**context, "request": request})
        config.write_text(shared.replace(revision, "0" * 40))
        unadmitted = call(context)
        assert not unadmitted["decision_packet"].get("decision_context", {}).get("consequences")
        assert unadmitted["decision_packet"]["blockers"]
        config.write_text(shared)

        # A stronger owner must admit the exact value. A same-ID replacement or
        # a lost destination cannot discard the independently admitted fallback.
        from tests.test_shared_core import _write_native

        receiver = tmp_path / "docs/decisions/received.md"
        receiver.parent.mkdir(parents=True)
        _write_native(receiver, {**record, "consequence": "A materially different fixture decision"})

        def admit_receiver() -> None:
            current_revision = _commit_native(tmp_path)
            config.write_text(shared + f'decision_record_target="docs/decisions"\ndecision_record_revision="{current_revision}"\n')

        admit_receiver()
        pending = call(context)["decision_packet"]["decision_context"]
        assert pending["reconciliation"][0]["status"] == "pending"
        assert pending["consequences"][0]["source"]["owner"] == "memory"
        receiver.write_bytes(source)
        admit_receiver()
        promoted = call(context)["decision_packet"]["decision_context"]
        assert promoted["reconciliation"][0]["status"] == "repo-native"
        assert promoted["consequences"][0]["source"]["owner"] == "repository"
        receiver.write_bytes(b"Receiver no longer contains the admitted lesson\n")
        reopened = call(context)["decision_packet"]["decision_context"]
        assert reopened["reconciliation"][0]["status"] == "pending"
        assert reopened["consequences"][0]["source"]["owner"] == "memory"
        assert path.read_bytes() == source
        config.write_text(shared)
        request = call(context)["decision_sources"]["requests"][0]
    (tmp_path / "SYSTEM_INTENT.md").write_bytes(basis + b"\nChanged governing source\n")
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "request": request})
    stale = call(context)
    assert stale["decision_packet"]["decision_context"]["consequences"] == []
    reread = call({**context, "request": stale["decision_sources"]["requests"][0]})
    assert reread["decision_sources"]["response"]["decision_state"]["status"] == "stale"
    path.write_bytes(source + b"\nUnadmitted source edit\n")
    with pytest.raises(AssertionError, match="stale decision source"):
        call({**context, "request": request})


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_public_decision_read_supersession_keeps_rationale_without_old_consequence(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    from copy import deepcopy

    from tests.test_shared_core import _commit_native, _native_archive, _write_native

    host, record = _native_archive(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()

    def admit(revision: str) -> None:
        config.write_text(
            f'schema_version=1\n[modules]\nenabled=[]\n[assurance]\ndecision_record_target="design"\ndecision_record_revision="{revision}"\n'
        )

    admit(host["admitted_revision"])
    context = {"target": str(tmp_path), "task": "Inspect the current component boundary", "changed": ["src/core.rs"]}

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    initial = call(context)
    old_request = initial["decision_sources"]["requests"][0]
    state = initial["decision_packet"]["decision_context"]["states"][0]
    successor = deepcopy(record)
    successor["id"] = "architecture/successor"
    successor["consequence"] = "Use the current replacement consequence"
    successor["supersedes"] = [{"id": record["id"], "material_revision": state["material_revision"], "scope": record["scope"]}]
    _write_native(tmp_path / "design/successor.md", successor)
    admit(_commit_native(tmp_path))
    with pytest.raises(AssertionError):
        call({**context, "request": old_request})
    current = call(context)
    assert [r["id"] for r in current["decision_packet"]["decision_context"]["consequences"]] == [successor["id"]]
    historical_request = next(r for r in current["decision_sources"]["requests"] if r["arguments"]["id"] == record["id"])
    historical = call({**context, "request": historical_request})
    assert historical["decision_sources"]["response"]["decision_state"]["status"] == "superseded"
    assert "Rationale stays in the repository" in historical["decision_sources"]["response"]["body"]
    assert [r["id"] for r in historical["decision_packet"]["decision_context"]["consequences"]] == [successor["id"]]
