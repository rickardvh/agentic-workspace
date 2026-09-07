"""Public native ingress consumed independently; no installed-platform claim."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def native_cli(shared_core_binary: Path) -> Path:
    subprocess.run(["cargo", "build", "--locked", "-p", "agentic-workspace-cli"], cwd=ROOT, check=True)
    return shared_core_binary.with_name("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace")


def consume(surface: str, binary: Path, native: Path, context: dict) -> dict:
    encoded = json.dumps(context)
    verb = "invoke" if "invocation" in context else "start"
    if surface == "native":
        command = [str(native), verb, "--target", context["target"], "--task", context["task"], "--format", "json"]
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
            f"import json,sys; from agentic_workspace.decision import {verb}; print(json.dumps({verb}(json.loads(sys.argv[1]))))",
            encoded,
        ]
        stdin = None
    else:
        module = (ROOT / "bindings/node/semantic-decision.mjs").as_uri()
        command = [
            "node",
            "--input-type=module",
            "-e",
            f"import {{{verb}}} from {json.dumps(module)}; console.log(JSON.stringify({verb}(JSON.parse(process.argv[1]))));",
            encoded,
        ]
        stdin = None
    environment = {**os.environ, "PATH": ""} if surface == "native" else None
    result = subprocess.run(command, input=stdin, text=True, capture_output=True, cwd=ROOT, check=False, env=environment)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


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
    request = next(item for item in initial["semantic_routes"]["requests"] if item["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "selected", "routes": ["repository/inspect"]}
    selected = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert selected["semantic_routes"]["status"] == "current"
    assert selected["decision_packet"]["semantic_task_routes"]["routes"] == ["repository/inspect"]
    registry.write_text(registry.read_text() + "\n")
    stale = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert stale["semantic_routes"]["status"] == "stale"
    assert stale["decision_packet"]["semantic_task_routes"]["status"] != "current"
    assert not (tmp_path / ".agentic-workspace").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_former_planning_native_invocation_and_fresh_continuation(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / plan_ref
    plan.parent.mkdir(parents=True)
    original = (ROOT / plan_ref).read_bytes()
    plan.write_bytes(original)
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
    context = {"target": str(tmp_path), "task": "Preserve the current reconstruction scope and returned work"}
    initial = consume(surface, shared_core_binary, native_cli, context)
    question = initial["decision_packet"]["decision_request"]
    request = question["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    continued = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
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
    assert "task-subject-mismatch-or-legacy-identity-compatibility-unproven" in evidence["gaps"]
    assert result["decision_packet"]["status"] != "terminal"
    (tmp_path / "a.txt").write_text("two")
    stale = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert "proof-semantic-input-stale-or-unavailable" in stale["verification"]["evidence"][0]["gaps"]
