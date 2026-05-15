from __future__ import annotations

import json
import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from planning_test_support import *


def test_close_item_removes_completed_active_todo_from_state(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "done-item", title = "Done item", status = "completed" },
]
queued_items = [
  { id = "next-item", title = "Next item", status = "next" },
]
""",
    )

    result = close_planning_item("done-item", target=tmp_path, reason="completed in PR", issue="#953")
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))

    assert result.warnings == []
    assert state["todo"]["active_items"] == []
    assert state["todo"]["queued_items"][0]["id"] == "next-item"
    assert any(action.kind == "updated" and "issue: #953" in action.detail for action in result.actions)
    assert (tmp_path / ".agentic-workspace/planning/mutation-provenance.json").exists()


def test_close_item_dry_run_does_not_mutate_state(tmp_path: Path) -> None:
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    _write(
        state_path,
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "done-item", title = "Done item", status = "completed" },
]
""",
    )
    before = state_path.read_text(encoding="utf-8")

    result = close_planning_item("done-item", target=tmp_path, dry_run=True)

    assert state_path.read_text(encoding="utf-8") == before
    assert any(action.kind == "would update" for action in result.actions)


def test_close_item_refuses_ambiguous_prefix_matches(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "item-alpha", title = "Alpha", status = "completed" },
  { id = "item-beta", title = "Beta", status = "completed" },
]
""",
    )

    result = close_planning_item("item", target=tmp_path)

    assert any(warning["warning_class"] == "close_item_ambiguous" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and "item-alpha" in action.detail and "item-beta" in action.detail for action in result.actions
    )


def test_close_item_routes_execplan_id_through_archive_flow(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "plan-alpha", title = "Plan alpha", status = "completed", path = ".agentic-workspace/planning/execplans/plan-alpha.plan.json" },
]
""",
    )
    _write_execplan_record(tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.plan.json", status="completed")

    result = close_planning_item("plan-alpha", target=tmp_path)
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))

    assert result.warnings == []
    assert not (tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.plan.json").exists()
    assert (tmp_path / ".agentic-workspace/planning/execplans/archive/plan-alpha.plan.json").exists()
    assert state["todo"]["active_items"] == []
    assert any(action.kind == "archived" for action in result.actions)


def test_close_item_preserves_execplan_when_retained_archive_path_is_stale(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "plan-alpha", title = "Plan alpha", status = "completed", path = ".agentic-workspace/planning/execplans/plan-alpha.plan.json" },
]
""",
    )
    live_path = tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.plan.json"
    stale_archive_path = tmp_path / ".agentic-workspace/planning/execplans/archive/plan-alpha.plan.json"
    _write_execplan_record(live_path, status="completed")
    _write_execplan_record(stale_archive_path, status="completed")
    live = json.loads(live_path.read_text(encoding="utf-8"))
    live["proof_report"]["validation proof"] = "fresh close-item proof"
    installer_mod._write_execplan_record(record_path=live_path, record=live)
    stale = json.loads(stale_archive_path.read_text(encoding="utf-8"))
    stale["proof_report"]["validation proof"] = "stale close-item proof"
    installer_mod._write_execplan_record(record_path=stale_archive_path, record=stale)

    result = close_planning_item("plan-alpha", target=tmp_path)
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    unique_archive_path = tmp_path / ".agentic-workspace/planning/execplans/archive/plan-alpha-2.plan.json"

    assert result.warnings == []
    assert not live_path.exists()
    assert stale_archive_path.exists()
    assert unique_archive_path.exists()
    assert json.loads(stale_archive_path.read_text(encoding="utf-8"))["proof_report"]["validation proof"] == "stale close-item proof"
    assert json.loads(unique_archive_path.read_text(encoding="utf-8"))["proof_report"]["validation proof"] == "fresh close-item proof"
    assert state["todo"]["active_items"] == []
    assert any(action.kind == "retention" and "unique retained archive path" in action.detail for action in result.actions)
    assert any(action.kind == "archived" and action.path == unique_archive_path for action in result.actions)


def test_close_item_runtime_cli_outputs_json(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
queued_items = [
  { id = "done-item", title = "Done item", status = "closed" },
]
""",
    )

    assert planning_cli.main(["close-item", "done-item", "--target", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["message"] == "Close planning item done-item"
    assert any(action["kind"] == "updated" for action in payload["actions"])
