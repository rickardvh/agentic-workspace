from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def _checker_script_path() -> Path:
    root_checker = WORKSPACE_ROOT / "scripts" / "check" / "check_planning_surfaces.py"
    if root_checker.exists():
        return root_checker
    return PACKAGE_ROOT / "scripts" / "check" / "check_planning_surfaces.py"


def _render_script_path() -> Path:
    root_render = WORKSPACE_ROOT / "scripts" / "render_agent_docs.py"
    if root_render.exists():
        return root_render
    return PACKAGE_ROOT / "scripts" / "render_agent_docs.py"


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


def _minimal_execplan(*, status: str = "in-progress") -> str:
    return """
# Plan Alpha

## Goal

- Keep scope clear.

## Non-Goals

- No runtime changes.

## Active Milestone

- Status: {status}
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
""".format(status=status)


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


def _baseline_manifest() -> dict[str, object]:
    return {
        "bootstrap": {
            "first_reads": ["AGENTS.md", "TODO.md"],
            "conditional_reads": [
                "Read `ROADMAP.md` only when promoting work.",
                "Do not bulk-read all planning surfaces.",
            ],
            "task_source_of_truth": "TODO.md",
            "active_plan_dir": "docs/execplans/",
            "archived_plan_dir": "docs/execplans/archive/",
            "roadmap_source_of_truth": "ROADMAP.md",
        },
        "routing": {
            "planning-surfaces": {
                "when": "Changing TODO, ROADMAP, or execplans.",
                "touches": ["TODO.md", "ROADMAP.md", "docs/execplans/"],
                "commands": ["uv run pytest packages/planning/tests/test_check_planning_surfaces.py"],
            }
        },
        "skills": {
            "repo_dev_source_dir": "tools/skills",
            "memory_source_dir": ".agentic-workspace/memory/skills",
        },
        "invariants": ["Planning surfaces remain separate."],
    }


def _baseline_agents() -> str:
    return """
# Agent Instructions

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. Read the active feature plan in `docs/execplans/` when the TODO surface points there.
4. Read `ROADMAP.md` only when promoting work.

Do not bulk-read all planning surfaces.
"""


def _baseline_readme() -> str:
    return """
# Agentic Workspace

For agent maintainers, the primary operating path is `AGENTS.md`, `TODO.md`, the active execplan, and `docs/contributor-playbook.md`.
"""


def _baseline_contributor_playbook() -> str:
    return """
# Contributor Playbook

The default startup path for an agent maintainer is:

- Read `AGENTS.md`.
- Read `TODO.md`.
- Open the active execplan.
- Read package-local `AGENTS.md` only for the package being edited.
"""


def _write_generated_agent_surfaces(tmp_path: Path, manifest: dict[str, object] | None = None) -> None:
    manifest_payload = manifest or _baseline_manifest()
    render_module = _load_module(_render_script_path(), "planning_render")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json",
        json.dumps(manifest_payload, ensure_ascii=False, indent=2),
    )
    _write(
        tmp_path / "tools" / "agent-manifest.json",
        json.dumps(manifest_payload, ensure_ascii=False, indent=2),
    )
    _write(tmp_path / "tools" / "AGENT_QUICKSTART.md", render_module.render_quickstart(manifest_payload))
    _write(tmp_path / "tools" / "AGENT_ROUTING.md", render_module.render_routing(manifest_payload))


def _write_startup_surfaces(
    tmp_path: Path,
    *,
    readme: str | None = None,
    contributor_playbook: str | None = None,
    manifest: dict[str, object] | None = None,
) -> None:
    _write(tmp_path / "AGENTS.md", _baseline_agents())
    _write(tmp_path / "README.md", readme or _baseline_readme())
    _write(
        tmp_path / "docs" / "contributor-playbook.md",
        contributor_playbook or _baseline_contributor_playbook(),
    )
    _write_generated_agent_surfaces(tmp_path, manifest)


def _has_warning_path_suffix(warnings, suffix: str) -> bool:
    normalized_suffix = suffix.replace("\\", "/")
    return any(str(warning.path).replace("\\", "/").endswith(normalized_suffix) for warning in warnings)


def test_valid_compact_planning_shape_passes(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_valid")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())
    assert mod.gather_planning_warnings(repo_root=tmp_path) == []


def test_todo_shape_drift_for_checklist_and_missing_execplan(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_todo_shape")
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


def test_todo_shape_drift_for_finished_work_section(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_todo_finished_work")
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Now

- ID: plan-alpha
    Status: in-progress
    Surface: docs/execplans/plan-alpha.md
    Why now: promote when maintained report signal appears for this bounded next step.

## Added In This Pass

- Completed prior tranche details live here.
""",
    )
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())

    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "todo_shape_drift" in classes


def test_execplan_readiness_missing_warning(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_readiness")
    plan = _minimal_execplan().replace("- Ready: ready\n", "")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", plan)
    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "execplan_readiness_drift" in classes


def test_direct_task_can_trigger_plan_required_hint(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_plan_required")
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: direct-item
  Status: in-progress
  Surface: direct
  Why now: this step now carries milestone and validation detail that no longer fits a tiny direct task.
  Next action: check blocker sequencing and validation scope before coding.
  Done when: milestone-level validation and blocker handling are recorded.
""",
    )
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "todo_plan_required_hint" in classes


def test_direct_task_handoff_and_recovery_language_triggers_plan_hint(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_plan_required_recovery")
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: direct-item
    Status: in-progress
    Surface: direct
    Why now: this needs a clean handoff if the current session stops midway.
    Next action: resume from the last checkpoint and recover the partial failure path.
    Done when: concurrent branch work can land without extra restart notes.
""",
    )
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "todo_plan_required_hint" in classes


def test_execplan_under_specified_and_notebook_warnings(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_execplan_shape")
    under_specified_plan = """
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

Long narrative status update line one.
Long narrative status update line two.
Long narrative status update line three.
Long narrative status update line four.
Long narrative status update line five.
Long narrative status update line six.
Long narrative status update line seven.
Long narrative status update line eight.
Long narrative status update line nine.
Long narrative status update line ten.
Long narrative status update line eleven.

## Touched Paths

## Invariants

## Validation Commands

## Completion Criteria

- 

## Drift Log

- 2026-04-01: Decision one.
- 2026-04-02: Decision two.
- 2026-04-03: Decision three.
- 2026-04-04: Decision four.
- 2026-04-05: Decision five.
- 2026-04-06: Decision six.
"""
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", under_specified_plan)
    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "execplan_under_specified" in classes
    assert "execplan_notebook_drift" in classes


def test_completed_execplan_left_active_warns_archive_drift(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_completed_active")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan(status="completed"))

    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "archive_accumulation_drift" in classes


def test_active_execplan_set_pressure_warns(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_active_set")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    for name in ("plan-alpha", "plan-beta", "plan-gamma", "plan-delta"):
        _write(tmp_path / "docs" / "execplans" / f"{name}.md", _minimal_execplan())

    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "execplan_active_set_pressure" in classes


def test_promotion_linkage_accepts_clear_causal_why_now(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_promotion_reason")
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: promotion-linkage-tuning
  Status: in-progress
  Surface: docs/execplans/promotion-linkage-tuning-2026-04-05.md
  Why now: repeated self-hosted dogfooding exposed a false-positive case that should be tuned.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Add upgrade and uninstall flows when repeated dogfooding shows the safe lifecycle boundaries clearly.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / "docs" / "execplans" / "promotion-linkage-tuning-2026-04-05.md", _minimal_execplan())
    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "promotion_linkage_drift" not in classes


def test_promotion_linkage_still_warns_for_vague_activation(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_promotion_vague")
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: vague-thread
  Status: in-progress
  Surface: docs/execplans/vague-thread-2026-04-05.md
  Why now: work on this next.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Add upgrade and uninstall flows when repeated dogfooding shows the safe lifecycle boundaries clearly.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / "docs" / "execplans" / "vague-thread-2026-04-05.md", _minimal_execplan())
    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "promotion_linkage_drift" in classes


def test_main_json_format_outputs_payload(tmp_path: Path, capsys) -> None:
    mod = _load_module(_checker_script_path(), "planning_json")
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
    assert payload["todo"]["active_count"] == 1
    assert payload["execplans"]["active_count"] == 1


def test_startup_policy_warns_for_readme_and_contributor_drift(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_startup_policy")
    _write_startup_surfaces(
        tmp_path,
        readme="# Agentic Workspace\n\nBrief overview only.\n",
        contributor_playbook="# Contributor Playbook\n\nGeneral notes only.\n",
    )

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    startup_warnings = [warning for warning in warnings if warning.warning_class == "startup_policy_drift"]

    assert _has_warning_path_suffix(startup_warnings, "README.md")
    assert _has_warning_path_suffix(startup_warnings, "docs/contributor-playbook.md")


def test_generated_docs_warn_for_drift_and_missing_marker(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_generated_docs")
    _write_startup_surfaces(tmp_path)
    _write(tmp_path / "tools" / "agent-manifest.json", '{"stale": true}')
    _write(tmp_path / "tools" / "AGENT_QUICKSTART.md", "# Agent Quickstart\n\nmanual edit\n")
    _write(tmp_path / "tools" / "AGENT_ROUTING.md", "# Agent Routing\n\nmanual edit\n")

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    generated_warnings = [warning for warning in warnings if warning.warning_class == "generated_docs_drift"]

    assert _has_warning_path_suffix(generated_warnings, "tools/agent-manifest.json")
    assert _has_warning_path_suffix(generated_warnings, "tools/AGENT_QUICKSTART.md")
    assert _has_warning_path_suffix(generated_warnings, "tools/AGENT_ROUTING.md")
