from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentic_workspace import builtin_modules
from agentic_workspace.builtin_modules import memory_module, planning_module, verification_module, workspace_module
from agentic_workspace.workspace import Workspace


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_direct_work_has_no_module_or_durable_state(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, modules=[workspace_module(), planning_module(), verification_module()])
    decision = workspace.start(task="rename a local variable")
    assert decision["status"] == "direct"
    assert decision["relevant_owners"] == []
    assert not (tmp_path / ".agentic-workspace").exists()


def test_planning_proof_and_completion_are_source_owned_transitions(tmp_path: Path) -> None:
    planning = {
        "schema_version": 1,
        "revision": 1,
        "active": {"id": "ship", "status": "ready-to-complete"},
        "validation": [[sys.executable, "-c", "raise SystemExit(0)"]],
    }
    _write(tmp_path / ".agentic-workspace" / "planning.json", planning)
    workspace = Workspace(tmp_path, modules=[planning_module(), verification_module()])

    proof_decision = workspace.start(task="ship", claims=["complete"])
    assert proof_decision["primary_action"]["operation_id"] == "verification.run"
    proof_result = workspace.invoke(proof_decision["primary_action"])
    completion_decision = proof_result["next_decision"]
    assert completion_decision["primary_action"]["operation_id"] == "planning.complete"

    completion_result = workspace.invoke(completion_decision["primary_action"])
    assert completion_result["next_decision"]["status"] == "terminal"
    assert "complete" in completion_result["next_decision"]["claim_boundary"]["allowed"]


def test_pre_v1_removal_is_bounded_and_preserves_unknown_content(tmp_path: Path) -> None:
    legacy = tmp_path / ".agentic-workspace"
    legacy.mkdir()
    (legacy / "WORKFLOW.md").write_text("managed alpha guidance", encoding="utf-8")
    (legacy / "repo-owned-note.md").write_text("keep me", encoding="utf-8")
    workspace = Workspace(tmp_path, modules=[workspace_module()])

    decision = workspace.start(task="continue")
    assert decision["primary_action"]["operation_id"] == "workspace.remove-legacy"
    result = workspace.invoke(decision["primary_action"])
    assert result["next_decision"]["status"] == "direct"
    assert not (legacy / "WORKFLOW.md").exists()
    assert (legacy / "repo-owned-note.md").read_text(encoding="utf-8") == "keep me"


def test_first_party_operations_are_selected_from_structured_intent(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, modules=[workspace_module(), planning_module(), memory_module()])

    planning = workspace.start(intent={"planning": {"operation": "set", "item": "one", "status": "in-progress"}})
    assert planning["primary_action"]["operation_id"] == "planning.set"
    workspace.invoke(planning["primary_action"])

    memory = workspace.start(intent={"memory": {"key": "choice", "value": "small"}})
    assert memory["primary_action"]["operation_id"] == "memory.record"
    memory_result = workspace.invoke(memory["primary_action"])
    assert workspace.invoke(memory["primary_action"]) == memory_result
    assert memory_result["next_decision"]["status"] == "direct"
    assert memory_result["next_decision"]["primary_action"] is None
    assert memory_result["next_decision"]["relevant_owners"] == ["memory", "planning"]

    read = workspace.start(intent={"memory": {"operation": "read", "key": "choice"}})
    assert read["primary_action"]["operation_id"] == "memory.read"
    assert workspace.invoke(read["primary_action"])["value"] == {"key": "choice", "value": "small"}

    assert (tmp_path / ".agentic-workspace" / "planning.json").is_file()
    assert (tmp_path / ".agentic-workspace" / "memory.json").is_file()

    unknown = tmp_path / ".agentic-workspace" / "repo-owned.md"
    unknown.write_text("preserve", encoding="utf-8")
    removal = workspace.start(intent={"workspace": "remove"})
    assert removal["primary_action"]["operation_id"] == "workspace.remove"
    removed = workspace.invoke(removal["primary_action"])
    assert removed["next_decision"]["status"] == "direct"
    assert unknown.read_text(encoding="utf-8") == "preserve"


def test_cli_and_python_use_the_same_decision_authority(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from agentic_workspace.cli import main

    workspace = Workspace(tmp_path, modules=[])
    expected = workspace.start(task="tiny")
    assert main(["start", "--target", str(tmp_path), "--task", "tiny"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected


def test_unknown_state_collision_is_byte_preserved_until_explicit_transfer(tmp_path: Path) -> None:
    state_path = tmp_path / ".agentic-workspace" / "memory.json"
    state_path.parent.mkdir()
    state_path.write_bytes(b'{"private":"keep"}')
    before = state_path.read_bytes()
    workspace = Workspace(tmp_path, modules=[workspace_module(), memory_module()])
    decision = workspace.start(intent={"memory": {"key": "choice", "value": "small"}})

    with pytest.raises(ValueError, match="unknown content collision"):
        workspace.invoke(decision["primary_action"])
    assert state_path.read_bytes() == before

    digest = "sha256:" + hashlib.sha256(before).hexdigest()
    transfer = workspace.start(
        intent={
            "workspace": {
                "operation": "transfer-ownership",
                "path": ".agentic-workspace/memory.json",
                "from_owner": "unowned",
                "to_owner": "memory",
                "expected_sha256": digest,
                "classification": "durable-module-state",
            }
        }
    )
    workspace.invoke(transfer["primary_action"])
    current = workspace.start(intent={"memory": {"key": "choice", "value": "small"}})
    workspace.invoke(current["primary_action"])
    assert json.loads(state_path.read_text(encoding="utf-8"))["records"] == [{"key": "choice", "value": "small"}]


def test_manipulated_manifest_cannot_authorize_removal(tmp_path: Path) -> None:
    unknown = tmp_path / ".agentic-workspace" / "unknown.txt"
    unknown.parent.mkdir()
    unknown.write_text("preserve", encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(unknown.read_bytes()).hexdigest()
    _write(
        tmp_path / ".agentic-workspace" / "managed.json",
        {
            "schema_version": 2,
            "records": [
                {
                    "path": ".agentic-workspace/unknown.txt",
                    "owner": "workspace",
                    "classification": "package-residue",
                    "sha256": digest,
                }
            ],
        },
    )
    workspace = Workspace(tmp_path, modules=[workspace_module()])
    decision = workspace.start(intent={"workspace": "remove"})
    result = workspace.invoke(decision["primary_action"])
    assert result["status"] == "rejected"
    assert unknown.read_text(encoding="utf-8") == "preserve"


def test_two_processes_commit_one_idempotent_effect(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, modules=[memory_module()])
    invocation = workspace.start(intent={"memory": {"key": "race", "value": "once"}})["primary_action"]
    command = [
        sys.executable,
        "-m",
        "agentic_workspace.cli",
        "invoke",
        "--target",
        str(tmp_path),
        "--invocation",
        json.dumps(invocation),
    ]
    processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    completed = [process.communicate(timeout=20) + (process.returncode,) for process in processes]
    assert [returncode for _, _, returncode in completed] == [0, 0], completed
    state = json.loads((tmp_path / ".agentic-workspace" / "memory.json").read_text(encoding="utf-8"))
    assert state["revision"] == 1
    assert state["records"] == [{"key": "race", "value": "once"}]


def test_fresh_process_reconstructs_interrupted_multi_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = Workspace(tmp_path, modules=[planning_module()])
    invocation = workspace.start(intent={"planning": {"operation": "set", "item": "ship", "status": "in-progress"}})[
        "primary_action"
    ]
    original = builtin_modules._write_json
    failed = False

    def interrupt_manifest(path: Path, value: dict[str, object]) -> None:
        nonlocal failed
        if path.name == "managed.json" and not failed:
            failed = True
            raise OSError("fault between custody and manifest")
        original(path, value)

    monkeypatch.setattr(builtin_modules, "_write_json", interrupt_manifest)
    with pytest.raises(OSError, match="fault between custody and manifest"):
        workspace.invoke(invocation)
    monkeypatch.setattr(builtin_modules, "_write_json", original)

    recovered = Workspace(tmp_path, modules=[planning_module()]).invoke(invocation)
    assert recovered["next_decision"]["status"] == "direct"
    manifest = json.loads((tmp_path / ".agentic-workspace" / "managed.json").read_text(encoding="utf-8"))
    custody = json.loads((tmp_path / ".agentic-workspace" / "local" / "ownership.json").read_text(encoding="utf-8"))
    assert manifest["records"] == custody["records"]


@pytest.mark.parametrize("managed_path", [".agentic-workspace/../outside.txt", "C:/outside.txt"])
def test_ownership_transfer_rejects_noncanonical_or_escaping_paths(tmp_path: Path, managed_path: str) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("preserve", encoding="utf-8")
    workspace = Workspace(tmp_path, modules=[workspace_module()])
    decision = workspace.start(
        intent={
            "workspace": {
                "operation": "transfer-ownership",
                "path": managed_path,
                "from_owner": "unowned",
                "to_owner": "workspace",
                "expected_sha256": "sha256:" + hashlib.sha256(outside.read_bytes()).hexdigest(),
                "classification": "package-residue",
            }
        }
    )
    with pytest.raises(ValueError, match="not canonical|outside"):
        workspace.invoke(decision["primary_action"])
    assert outside.read_text(encoding="utf-8") == "preserve"


def test_ownership_transfer_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "victim.txt"
    victim.write_text("preserve", encoding="utf-8")
    state = tmp_path / ".agentic-workspace"
    state.mkdir()
    link = state / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are not available")
    workspace = Workspace(tmp_path, modules=[workspace_module()])
    decision = workspace.start(
        intent={
            "workspace": {
                "operation": "transfer-ownership",
                "path": ".agentic-workspace/link/victim.txt",
                "from_owner": "unowned",
                "to_owner": "workspace",
                "expected_sha256": "sha256:" + hashlib.sha256(victim.read_bytes()).hexdigest(),
                "classification": "package-residue",
            }
        }
    )
    with pytest.raises(ValueError, match="escapes target"):
        workspace.invoke(decision["primary_action"])
    assert victim.read_text(encoding="utf-8") == "preserve"


def test_legitimately_acquired_package_residue_is_removable(tmp_path: Path) -> None:
    residue = tmp_path / ".agentic-workspace" / "generated.txt"
    residue.parent.mkdir()
    residue.write_text("managed", encoding="utf-8")
    workspace = Workspace(tmp_path, modules=[workspace_module()])
    transfer = workspace.start(
        intent={
            "workspace": {
                "operation": "transfer-ownership",
                "path": ".agentic-workspace/generated.txt",
                "from_owner": "unowned",
                "to_owner": "workspace",
                "expected_sha256": "sha256:" + hashlib.sha256(residue.read_bytes()).hexdigest(),
                "classification": "package-residue",
            }
        }
    )
    workspace.invoke(transfer["primary_action"])
    removal = workspace.start(intent={"workspace": "remove"})
    result = workspace.invoke(removal["primary_action"])
    assert result["status"] == "applied"
    assert not residue.exists()
