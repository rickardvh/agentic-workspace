from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _minimal_execplan() -> str:
    return """
# Plan Alpha

## Goal

- Keep scope clear.

## Non-Goals

- No runtime changes.

## Active Milestone

- Status: in-progress
- Scope: maintain planning discipline.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Add one checker.

## Blockers

- None.

## Touched Paths

- scripts/check/check_planning_surfaces.py

## Invariants

- Planning surfaces remain separate.

## Validation Commands

- uv run pytest tests/test_check_planning_surfaces.py

## Completion Criteria

- Warning classes are emitted for known drift.

## Drift Log

- 2026-04-04: Initial plan created.
"""


def _baseline_todo(surface: str = "docs/execplans/plan-alpha.md") -> str:
    return f"""
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: {surface}
  Why now: promote when maintained report signal appears for this bounded next step.
"""


def _baseline_roadmap() -> str:
    return """
# Roadmap

## Next Candidate Queue

- Candidate alpha: promote when maintained report signal appears.

## Reopen Conditions

- Reopen only when a queue or report signals new work.
"""


def test_valid_compact_planning_shape_passes(tmp_path: Path) -> None:
    mod = _load_module(REPO_ROOT / "scripts" / "check" / "check_planning_surfaces.py", "planning_valid")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())
    assert mod.gather_planning_warnings(repo_root=tmp_path) == []


def test_todo_shape_drift_for_checklist_and_missing_execplan(tmp_path: Path) -> None:
    mod = _load_module(REPO_ROOT / "scripts" / "check" / "check_planning_surfaces.py", "planning_todo_shape")
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: direct-item
  Status: in-progress
  Surface: docs/runbooks/direct-task.md
  Why now: this item depends on blocker history and validation sequencing over multiple stages.

- [ ] checkpoint one
""",
    )
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())
    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "todo_shape_drift" in classes
    assert "todo_missing_execplan_linkage" in classes


def test_execplan_readiness_missing_warning(tmp_path: Path) -> None:
    mod = _load_module(REPO_ROOT / "scripts" / "check" / "check_planning_surfaces.py", "planning_readiness")
    plan = _minimal_execplan().replace("- Ready: ready\n", "")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", plan)
    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "execplan_readiness_drift" in classes


def test_main_json_format_outputs_payload(tmp_path: Path, capsys) -> None:
    mod = _load_module(REPO_ROOT / "scripts" / "check" / "check_planning_surfaces.py", "planning_json")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())

    original_root = mod.REPO_ROOT
    try:
        mod.REPO_ROOT = tmp_path
        exit_code = mod.main(["--format", "json"])
        captured = capsys.readouterr()
    finally:
        mod.REPO_ROOT = original_root

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["warning_count"] == 0
    assert payload["warnings"] == []
