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
    execution_summary = (
        "- Outcome delivered: Added one bounded planning improvement.\n"
        "- Validation confirmed: uv run pytest tests/test_check_planning_surfaces.py\n"
        "- Follow-on routed to: none; slice complete\n"
        "- Resume from: no further action in this plan\n"
        if status in {"completed", "done", "closed"}
        else "- Outcome delivered: not completed yet\n"
        "- Validation confirmed: pending\n"
        "- Follow-on routed to: none yet\n"
        "- Resume from: current milestone\n"
    )
    proof_report = (
        "\n## Proof Report\n\n"
        "- Validation proof: uv run pytest tests/test_check_planning_surfaces.py\n"
        '- Proof achieved now: validation and closure checks passed for the bounded slice.\n'
        '- Evidence for "Proof achieved" state: archive gate and planning checks were satisfied.\n'
        if status in {"completed", "done", "closed"}
        else ""
    )
    intent_satisfaction = (
        "\n## Intent Satisfaction\n\n"
        "- Original intent: Keep scope clear.\n"
        "- Was original intent fully satisfied?: yes\n"
        "- Evidence of intent satisfaction: the bounded slice landed and the lane-level evidence was recorded.\n"
        "- Unsolved intent passed to: none\n"
        if status in {"completed", "done", "closed"}
        else ""
    )
    return """
# Plan Alpha

## Goal

- Keep scope clear.

## Non-Goals

- No runtime changes.

## Intent Continuity

- Larger intended outcome: Land plan alpha end to end.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: Added one bounded planning improvement.
- Intentionally deferred: none
- Discovered implications: none yet
- Proof achieved now: validation remains pending until the current milestone closes.
- Validation still needed: run the bounded planning checker test before archive.
- Next likely slice: finish the current milestone and archive if no larger follow-on remains.

## Delegated Judgment

- Requested outcome: Land plan alpha end to end.
- Hard constraints: Keep scope clear and local.
- Agent may decide locally: Bounded decomposition and validation tightening.
- Escalate when: The requested outcome, owned surface, or time horizon would change.

## Active Milestone

- ID: plan-alpha
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

## Execution Summary

{execution_summary}

{proof_report}
{intent_satisfaction}

## Drift Log

- 2026-04-04: Initial plan created.
""".format(status=status, execution_summary=execution_summary, proof_report=proof_report, intent_satisfaction=intent_satisfaction)


def _rename_like_execplan(*, with_reference_sweep: bool = False) -> str:
    plan = _minimal_execplan(status="completed").replace("- Keep scope clear.", "- Rename the stale planning surface cleanly.")
    if with_reference_sweep:
        plan = plan.replace(
            "- uv run pytest tests/test_check_planning_surfaces.py",
            "- uv run pytest tests/test_check_planning_surfaces.py\n- rg old-planning-surface docs scripts",
            1,
        )
        plan = plan.replace(
            "- Validation confirmed: uv run pytest tests/test_check_planning_surfaces.py",
            "- Validation confirmed: uv run pytest tests/test_check_planning_surfaces.py; rg old-planning-surface docs scripts",
        )
    return plan


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
            "first_queries": [
                "Use `agentic-workspace defaults --section startup --format json` when startup or first-contact routing is the question.",
            ],
            "surface_roles": [
                "`docs/agent-installation.md` is only the external install/adopt handoff surface.",
                "`llms.txt` is the agent entrypoint router.",
            ],
            "conditional_reads": [
                "Read `ROADMAP.md` only when promoting work.",
                "Treat `docs/agent-installation.md` as the external install/adopt handoff only; after bootstrap, return to the configured startup entrypoint for normal repo work.",
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
When the question is active planning recovery rather than startup order, prefer `agentic-workspace summary --format json` and `agentic-workspace defaults --section startup --format json` before reopening broader planning prose.
"""


def _baseline_llms() -> str:
    return """
# Agent Entrypoint Router

- If you are here to DEVELOP this repository: Read `AGENTS.md`
- If you are here to INSTALL Agentic Workspace: Read `docs/agent-installation.md`
"""


def _baseline_install() -> str:
    return """
# Agentic Workspace External Install Or Adopt Handoff

This file is only the external install/adopt handoff.
Do not treat it as the normal repo startup surface after bootstrap or adoption.

- After install or adopt, inspect `agentic-workspace config --target ./repo --format json`.
- When the question is active planning recovery rather than bootstrap, prefer `agentic-workspace summary --format json`.
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
- Use `agentic-workspace summary --format json` when the question is active planning state.
- Use `agentic-workspace report --target ./repo --format json` when the question is combined workspace state.
- Open the active execplan only when the compact surfaces are insufficient.
- Read package-local `AGENTS.md` only for the package being edited.
"""


def _baseline_default_path_contract() -> str:
    return """
# Default Path Contract

## Inspection Order

1. report or summary
2. narrow selector
3. raw file or richer prose only when the compact surface is insufficient

- use `agentic-workspace summary --format json` before opening `TODO.md` or execplan prose
- use `agentic-workspace report --target ./repo --format json` before reading raw module files

## Routine Planning Recovery

Use `agentic-workspace summary --format json` first when the question is active planning recovery.

The minimum questions are:

- What is active right now? -> `planning_record`
- What should I do next? -> `resumable_contract`
- What larger chunk or queue owns follow-on? -> `hierarchy_contract`
- What residue remains if this slice stops? -> `follow_through_contract`
- When do I fall back to prose? -> only when the compact summary leaves the answer ambiguous

Use [`docs/execplans/README.md`](execplans/README.md) for the meaning boundary behind those answers.

The compact rule is:

- machine-readable state keeps restart-critical meanings
- compact prose keeps stable route guidance and framing
- raw execplan detail keeps slice-local narrative and change-log residue

Example: "What should I do next?" belongs in `resumable_contract`; the route that gets you there belongs in compact prose; the line-by-line change log belongs in raw execplan detail.
"""


def _baseline_intent_contract() -> str:
    return """
# Intent Contract

- Treat `planning_record` as the canonical active planning state whenever it is available.
- Treat raw planning prose as a thin human maintenance view and semantic fallback, not the default inspection path.
"""


def _baseline_resumable_contract() -> str:
    return """
# Resumable Execution Contract

- Treat `planning_record` as the canonical active planning state when it is available.
- Treat raw planning prose as the semantic fallback and maintenance layer rather than the default restart-inspection path.
"""


def _baseline_execplans_readme() -> str:
    return """
# Execution Plans

Use `agentic-workspace summary --format json` first when the question is active planning state.
Use raw `TODO.md` and execplan prose after that only when the compact summary is insufficient.
`agentic-workspace summary --format json` exposes a typed payload and `planning_record` is the canonical active planning record.

## Meaning Boundary

Use one compact rule when deciding where a planning meaning belongs:

- machine-readable state keeps the restart-critical meanings that must be recovered cheaply and unambiguously, including active work, next action, follow-on owner, proof state, and escalation boundaries
- compact prose keeps stable route guidance and framing when a queryable field would not reduce recovery cost enough to justify a second owner
- raw execplan detail keeps slice-specific narrative, implementation notes, drift-log residue, and other maintenance detail that should not be the default recovery path

Example: "What should I do next?" belongs in `resumable_contract`; the route that gets you there belongs in compact prose; the line-by-line change log belongs in raw execplan detail.
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
    _write(tmp_path / "llms.txt", _baseline_llms())
    _write(tmp_path / "docs" / "agent-installation.md", _baseline_install())
    _write(tmp_path / "README.md", readme or _baseline_readme())
    _write(
        tmp_path / "docs" / "contributor-playbook.md",
        contributor_playbook or _baseline_contributor_playbook(),
    )
    _write_generated_agent_surfaces(tmp_path, manifest)


def _write_hierarchy_docs(tmp_path: Path) -> None:
    _write(tmp_path / "docs" / "default-path-contract.md", _baseline_default_path_contract())
    _write(tmp_path / "docs" / "intent-contract.md", _baseline_intent_contract())
    _write(tmp_path / "docs" / "resumable-execution-contract.md", _baseline_resumable_contract())
    _write(tmp_path / "docs" / "execplans" / "README.md", _baseline_execplans_readme())


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


def test_default_path_contract_without_meaning_boundary_warns(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_default_path_recovery")
    _write(
        tmp_path / "TODO.md",
        _baseline_todo(),
    )
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(
        tmp_path / "docs" / "default-path-contract.md",
        """
# Default Path Contract

## Inspection Order

1. report or summary
2. narrow selector
3. raw file or richer prose only when the compact surface is insufficient

- use `agentic-workspace summary --format json` before opening `TODO.md` or execplan prose
- use `agentic-workspace report --target ./repo --format json` before reading raw module files

## Routine Planning Recovery

Use `agentic-workspace summary --format json` first when the question is active planning recovery.

The minimum questions are:

- What is active right now? -> `planning_record`
- What should I do next? -> `resumable_contract`
- What larger chunk or queue owns follow-on? -> `hierarchy_contract`
- What residue remains if this slice stops? -> `follow_through_contract`
- When do I fall back to prose? -> only when the compact summary leaves the answer ambiguous
""",
    )
    _write(tmp_path / "docs" / "intent-contract.md", _baseline_intent_contract())
    _write(tmp_path / "docs" / "resumable-execution-contract.md", _baseline_resumable_contract())
    _write(tmp_path / "docs" / "execplans" / "README.md", _baseline_execplans_readme())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    assert any(warning.warning_class == "docs_surface_role_drift" for warning in warnings)


def test_default_path_contract_with_meaning_boundary_passes(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_default_path_boundary")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "default-path-contract.md", _baseline_default_path_contract())
    _write(tmp_path / "docs" / "intent-contract.md", _baseline_intent_contract())
    _write(tmp_path / "docs" / "resumable-execution-contract.md", _baseline_resumable_contract())
    _write(tmp_path / "docs" / "execplans" / "README.md", _baseline_execplans_readme())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    assert not [warning for warning in warnings if warning.warning_class == "docs_surface_role_drift"]


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

## Intent Continuity

- Larger intended outcome:
- This slice completes the larger intended outcome: no
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

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


def test_execplan_intent_continuity_requires_continuation_surface_when_parent_intent_is_unfinished(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_intent_continuity")
    plan = (
        _minimal_execplan()
        .replace(
            "- Continuation surface: none",
            "- Continuation surface: none",
        )
        .replace(
            "- This slice completes the larger intended outcome: yes",
            "- This slice completes the larger intended outcome: no",
        )
    )
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", plan)

    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "execplan_under_specified" in classes


def test_execplan_requires_structured_required_follow_on_when_parent_intent_is_unfinished(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_required_follow_on")
    plan = (
        _minimal_execplan()
        .replace(
            "- This slice completes the larger intended outcome: yes",
            "- This slice completes the larger intended outcome: no",
        )
        .replace(
            "- Continuation surface: none",
            "- Continuation surface: ROADMAP.md candidate next-slice",
        )
    )
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", plan)

    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "execplan_under_specified" in classes


def test_execplan_requires_delegated_judgment_when_active(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_delegated_judgment")
    plan = _minimal_execplan().replace(
        "## Delegated Judgment\n\n"
        "- Requested outcome: Land plan alpha end to end.\n"
        "- Hard constraints: Keep scope clear and local.\n"
        "- Agent may decide locally: Bounded decomposition and validation tightening.\n"
        "- Escalate when: The requested outcome, owned surface, or time horizon would change.\n\n",
        "",
    )
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", plan)

    messages = [warning.message for warning in mod.gather_planning_warnings(repo_root=tmp_path)]
    assert any("Requested outcome" in message for message in messages)
    assert any("Hard constraints" in message for message in messages)
    assert any("Agent may decide locally" in message for message in messages)
    assert any("Escalate when" in message for message in messages)


def test_completed_execplan_left_active_warns_archive_drift(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_completed_active")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan(status="completed"))

    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "archive_accumulation_drift" in classes


def test_completed_execplan_without_execution_summary_warns_under_specified(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_completed_summary")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(
        tmp_path / "docs" / "execplans" / "plan-alpha.md",
        _minimal_execplan(status="completed").replace(
            "- Outcome delivered: Added one bounded planning improvement.",
            "- Outcome delivered: not completed yet",
        ),
    )

    classes = {warning.warning_class for warning in mod.gather_planning_warnings(repo_root=tmp_path)}
    assert "execplan_under_specified" in classes


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


def test_contract_shaping_execplan_without_decision_sections_warns_under_specified(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_contract_shaping_missing_sections")
    plan = (
        _minimal_execplan()
        .replace(
            "- Keep scope clear.",
            "- Freeze the contract decisions for a provenance-aware update policy.",
        )
        .replace(
            "- Scope: maintain planning discipline.",
            "- Scope: close the schema, precedence, and policy decisions before implementation.",
        )
    )
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", plan)

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    matching = [warning for warning in warnings if warning.warning_class == "execplan_under_specified"]
    assert any("Contract Decisions To Freeze" in warning.message for warning in matching)
    assert any("Open Questions To Close" in warning.message for warning in matching)


def test_contract_shaping_execplan_with_decision_sections_passes(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_contract_shaping_complete")
    plan = (
        _minimal_execplan()
        .replace(
            "- Keep scope clear.",
            "- Freeze the contract decisions for a provenance-aware update policy.",
        )
        .replace(
            "- Scope: maintain planning discipline.",
            "- Scope: close the schema, precedence, and policy decisions before implementation.",
        )
        .replace(
            "## Validation Commands",
            "## Contract Decisions To Freeze\n\n- Canonical config lives at repo root.\n\n"
            "## Open Questions To Close\n\n- What wins when workspace and module pins disagree?\n\n"
            "## Validation Commands",
        )
    )
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", plan)

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    assert not [warning for warning in warnings if warning.warning_class == "execplan_under_specified"]


def test_completed_rename_like_execplan_without_reference_sweep_warns(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_closure_drift")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _rename_like_execplan())

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    assert any(warning.warning_class == "execplan_closure_drift" for warning in warnings)


def test_completed_rename_like_execplan_with_reference_sweep_passes(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_closure_clean")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _rename_like_execplan(with_reference_sweep=True))

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    assert not [warning for warning in warnings if warning.warning_class == "execplan_closure_drift"]


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


def test_startup_policy_ignores_generic_readme_but_warns_for_contributor_drift(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_startup_policy")
    _write_startup_surfaces(
        tmp_path,
        readme="# Agentic Workspace\n\nBrief overview only.\n",
        contributor_playbook="# Contributor Playbook\n\nGeneral notes only.\n",
    )

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    startup_warnings = [warning for warning in warnings if warning.warning_class == "startup_policy_drift"]

    assert not _has_warning_path_suffix(startup_warnings, "README.md")
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


def test_active_execplan_space_warns_for_review_artifact(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_active_surface_hygiene")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write_startup_surfaces(tmp_path)
    _write_hierarchy_docs(tmp_path)
    _write(tmp_path / "docs" / "execplans" / "review-alpha.md", "# Review\n\nCompleted audit notes.\n")

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    docs_warnings = [warning for warning in warnings if warning.warning_class == "docs_surface_role_drift"]
    assert _has_warning_path_suffix(docs_warnings, "docs/execplans/review-alpha.md")


def test_docs_surface_role_drift_warns_when_summary_first_hierarchy_is_missing(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "planning_docs_surface_roles")
    _write(tmp_path / "TODO.md", _baseline_todo())
    _write(tmp_path / "ROADMAP.md", _baseline_roadmap())
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())
    _write_startup_surfaces(tmp_path)
    _write_hierarchy_docs(tmp_path)
    _write(
        tmp_path / "docs" / "contributor-playbook.md",
        """
# Contributor Playbook

- Read `AGENTS.md`.
- Read `TODO.md`.
- Open the active execplan.
""",
    )

    warnings = mod.gather_planning_warnings(repo_root=tmp_path)
    docs_warnings = [warning for warning in warnings if warning.warning_class == "docs_surface_role_drift"]
    assert _has_warning_path_suffix(docs_warnings, "docs/contributor-playbook.md")
