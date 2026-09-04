from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

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
