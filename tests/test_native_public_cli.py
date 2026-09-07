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


@pytest.fixture(scope="module")
def native_cli(shared_core_binary: Path) -> Path:
    subprocess.run(["cargo", "build", "--locked", "-p", "agentic-workspace-cli"], cwd=ROOT, check=True)
    return shared_core_binary.with_name("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace")


def consume(surface: str, binary: Path, native: Path, context: dict, *, host_path: str = "") -> dict:
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
    environment = {**os.environ, "PATH": host_path} if surface == "native" else None
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
def test_instruction_procedure_requires_current_route_not_task_words(
    surface: str, tmp_path: Path, shared_core_binary: Path, native_cli: Path
) -> None:
    source = ".agentic-workspace/instructions/github-issue-creation.md"
    instruction = tmp_path / source
    instruction.parent.mkdir(parents=True)
    instruction.write_bytes((ROOT / source).read_bytes())
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "issue", "semantic_routes": ["github/issues/create"]}]}))
    context = {"target": str(tmp_path), "task": "Explain the words GitHub issue creation"}
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert not quiet["instructions"]["sources"][0]["guidance"]
    request = next(item for item in quiet["semantic_routes"]["requests"] if item["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "selected", "routes": ["github/issues/create"]}
    selected = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    row = selected["instructions"]["sources"][0]
    assert row["preferred_procedures"] == ["github-issue-shaping", "github-issue-creation"]
    assert row["binding_admission"]["status"] == "not-required"
    assert not selected["decision_packet"]["ready_actions"]
    assert not selected["decision_packet"]["blockers"]


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
    # Deterministic producer fixture, not human/domain acceptance evidence.
    from agentic_workspace.workspace_runtime_core import _proof_publication_identity, _write_trusted_producer_receipt

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
    receipt = json.loads((ROOT / "tests/fixtures/native_verification_publication.json").read_text())["receipt"]
    receipt["task_claim_judgment"].update(
        work_ref=subject["work_ref"], work_revision=subject["work_revision"], task_identity=subject["task_claim_identity"]
    )
    publication_id = hashlib.sha256(
        json.dumps(_proof_publication_identity(receipt), sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()[:16]
    receipt.update(publication_id=publication_id, receipt_id=publication_id)
    reference = f"proof://receipts/{publication_id}"
    _write_trusted_producer_receipt(
        target_root=tmp_path, producer_class="aw-proof", receipt_id=publication_id, receipt=receipt, source_ref=reference
    )
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
