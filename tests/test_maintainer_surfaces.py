from __future__ import annotations

import importlib.util
import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _checker_script_path() -> Path:
    return WORKSPACE_ROOT / "scripts" / "check" / "check_maintainer_surfaces.py"


def _render_script_path() -> Path:
    return WORKSPACE_ROOT / "scripts" / "render_agent_docs.py"


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


def _baseline_manifest() -> dict[str, object]:
    return {
        "bootstrap": {
            "first_reads": ["AGENTS.md"],
            "first_queries": [
                'Use `agentic-workspace start --task "<task>" --format json` before non-trivial work.',
                'Use `agentic-workspace implement --changed <paths> --task "<task>" --format json` when changed paths are already known.',
            ],
            "tiny_safe_model": [
                "Start from `AGENTS.md`.",
                "Ask the Startup Router first.",
                "Open deeper surfaces only when the small model stops being sufficient.",
            ],
            "surface_roles": [
                "`.agentic-workspace/docs/routing-contract.md` is the authoritative routing home.",
                "`AGENTS.md` is the agent entrypoint router.",
            ],
            "boundary_triggered_escalation": [
                {
                    "boundary": "workspace",
                    "cue": "routing question",
                    "load_next": ["agentic-workspace defaults --section startup --format json"],
                    "why": "workspace owns routing",
                },
                {
                    "boundary": "planning",
                    "cue": "sequencing question",
                    "load_next": ["agentic-workspace summary --format json"],
                    "why": "planning owns active work",
                },
                {
                    "boundary": "memory",
                    "cue": "durable context question",
                    "load_next": [".agentic-workspace/memory/repo/"],
                    "why": "memory owns durable knowledge",
                },
            ],
            "top_level_capabilities": [
                {
                    "module": "workspace",
                    "owns": "routing",
                    "escalate_when": "routing boundary",
                    "capability_unlocked": "defaults",
                    "first_surface": "agentic-workspace defaults --section startup --format json",
                },
                {
                    "module": "planning",
                    "owns": "active work",
                    "escalate_when": "planning boundary",
                    "capability_unlocked": "summary",
                    "first_surface": "agentic-workspace summary --format json",
                },
                {
                    "module": "memory",
                    "owns": "durable context",
                    "escalate_when": "memory boundary",
                    "capability_unlocked": "memory",
                    "first_surface": ".agentic-workspace/memory/repo/",
                },
            ],
            "conditional_reads": [
                "Read the roadmap in `state.toml` (authoritative) only when promoting work.",
                "Read `agentic-workspace summary --format json` when the Startup Router or explicit task asks for planning recovery.",
                "Read `.agentic-workspace/docs/routing-contract.md` when execution hits an edge case, ambiguity, or requires deep context.",
                "Do not bulk-read all planning surfaces.",
            ],
        }
    }


def _write_generated_agent_surfaces(tmp_path: Path) -> None:
    render_module = _load_module(_render_script_path(), "maintainer_render")
    manifest = _baseline_manifest()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )
    _write(tmp_path / "tools" / "agent-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    _write(tmp_path / "tools" / "AGENT_QUICKSTART.md", render_module.render_quickstart(manifest))
    _write(tmp_path / "tools" / "AGENT_ROUTING.md", render_module.render_routing(manifest))


def test_workspace_workflow_is_projection_not_primary_authority() -> None:
    for path in (
        WORKSPACE_ROOT / ".agentic-workspace" / "WORKFLOW.md",
        WORKSPACE_ROOT / "src" / "agentic_workspace" / "_payload" / ".agentic-workspace" / "WORKFLOW.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Conservative fallback/projection workflow" in text
        assert "do not treat it as an independent workflow authority" in text
        assert "| Current next safe action | `next_safe_action`" in text
        assert "| Workflow transition data | `transition_gates`" in text
        assert "| Command surface facts | `src/agentic_workspace/contracts/cli_commands.json`" in text
        assert "Ordinary first contact is one routed decision" in text
        assert "## Active Work Boundary" in text
        assert "Active work is Work Shaping plus Planning Autopilot" in text
        assert "`start` owns ordinary first-contact routing" in text
        assert "`summary` owns active continuation" in text
        assert "`implement --changed` owns known changed-path work context" in text
        assert "`planning` owns routed state mutation" in text
        assert "## Fallback Work Shape" in text
        assert "## Work Routing Gate" not in text
        assert (
            "Treat `preflight`, `summary`, `config`, `defaults`, `planning`, `skills`, `modules`, `ownership`, and `report` as routed drill-down"
            in text
        )
        assert "## First Route" not in text
        assert "Mandatory CLI-first startup router" not in text


def _write_planning_surfaces(tmp_path: Path) -> None:
    _write(
        tmp_path / "AGENTS.md",
        """
# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Ordinary route:
1. Use `agentic-workspace start --task "<task>" --format json` before non-trivial answers, edits, read-only workflow, config, delegation, or action-safety decisions.
2. Use `agentic-workspace implement --changed <paths> --task "<task>" --format json` when changed paths are already known.
3. Follow `next_safe_action`, `action_signals`, and `skills` before opening raw `.agentic-workspace` files or running drill-down commands.

Boundaries:
- The effective invocation comes from `.agentic-workspace/config.toml` `[workspace].cli_invoke`; `.agentic-workspace/config.local.toml` may override it.
- Known dedicated Agentic Workspace commands are allowed only when the request maps directly to that command and no takeover, recovery, active-planning, or ambiguous safety decision is needed first.
- Do not try a bare `agentic-workspace` command first when the effective invocation names a repo-local or dev-dependency command; PATH may resolve a stale installed selector.
- Treat `preflight`, `config`, `defaults`, `skills`, `modules`, `ownership`, and `report` as routed drill-down or recovery surfaces, not the ordinary startup loop.
- Report repo-relative paths, not local absolute paths.
- If the effective CLI is unavailable after trying it, immediately read `.agentic-workspace/WORKFLOW.md` before any other files.
<!-- agentic-workspace:workflow:end -->
""",
    )
    _write(
        tmp_path / "docs" / "routing-contract.md",
        """
# Routing and Entry Contract (Authoritative Routing Home)

This contract defines how to enter the repository, orient quickly, and pick the right execution lane.

## 1. Startup and First Contact

Use the following order for a fresh entry:
1. [Cold-Start Protocol](cold-start-protocol.md)
2. AGENTS.md
3. .agentic-workspace/planning/state.toml
4. Compact queries:
   - agentic-workspace summary --format json
   - agentic-workspace report --target ./repo --format json

### Tiny Safe Model

- start from AGENTS.md
- use compact queries before broader prose
""",
    )
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Now

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears for this bounded next step.
""",
    )
    _write(
        tmp_path / ".agentic-workspace/planning/process.md",
        """
# Roadmap

## Next Candidate Queue

- Candidate alpha: promote when maintained report signal appears.

## Reopen Conditions

- Reopen only when a queue or report signals new work.
""",
    )
    _write(
        tmp_path / "docs" / "execplans" / "plan-alpha.md",
        """
# Plan Alpha

## Goal

- Keep scope clear.

## Non-Goals

- No runtime changes.

## Machine-Readable Contract

```yaml
intent:
  outcome: "Keep scope clear."
```

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

- 2026-04-06: Initial plan created.
""",
    )


def _write_docs_surfaces(tmp_path: Path, *, drift_readme: bool = False) -> None:
    readme = """
# agentic-workspace

## Docs Map

For maintainers:

- `docs/maintainer/contributor-playbook.md` - choose the right ownership surface and validation lane before editing.
- `docs/maintainer/maintainer-commands.md` - canonical command index for routine maintenance.
- `docs/collaboration-safety.md` - concurrent-edit and git hygiene rules.
- `docs/maintainer/installed-contract-design-checklist.md` - review bar for new or changed shipped surfaces.
- `docs/maintainer/dogfooding-feedback.md` - classify internal friction before routing it onward.
- `.agentic-workspace/memory/repo/runbooks/dogfooding-feedback-routing.md` - classify internal friction before routing it onward.
- `docs/workflow-contract-changes.md` - compact record of recent workflow-surface changes.

for agent maintainers, the primary operating path is `agents.md`, active execplan, and `docs/maintainer/contributor-playbook.md`.
"""
    if drift_readme:
        readme = "# agentic-workspace\n\n## Docs Map\n\nFor maintainers:\n\n- `docs/maintainer/contributor-playbook.md`\n"
    _write(tmp_path / "README.md", readme)
    _write(
        tmp_path / "docs" / "contributor-playbook.md",
        """
# Contributor Playbook

Use this playbook to choose the right package, planning surface, and validation lane before making changes in `agentic-workspace`.

Use `docs/maintainer/maintainer-commands.md` when you need the literal command to run; use this playbook when you need routing,
ownership, or validation guidance.

## Agent Maintainer Path

Default startup path for an agent maintainer:

1. Read `agents.md`.
2. Read `.agentic-workspace/planning/state.toml` via `agentic-workspace summary --format json`.
3. If the question is startup order or first-contact routing, ask `agentic-workspace defaults --section startup --format json` before broader prose.
4. Read one active execplan only when the planning state surface points to it.
6. Read package-local `agents.md` only for the package you will edit.
""",
    )
    _write(
        tmp_path / "docs" / "maintainer-commands.md",
        """
# Maintainer Commands

This page is the single-source command index for routine repo maintenance.

Use this page when you need the canonical command to run, not the broader routing, ownership, or workflow-history context.
""",
    )
    _write(
        tmp_path / "docs" / "collaboration-safety.md",
        """
# Collaboration Safety

Use these rules when multiple agents or contributors are working through git.

Use `docs/maintainer/maintainer-commands.md` for command lookup and `docs/workflow-contract-changes.md` for compact workflow
history; this page is only for concurrent-edit and merge-safety rules.
""",
    )
    _write(
        tmp_path / "docs" / "installed-contract-design-checklist.md",
        """
# Installed-Contract Design Checklist

Use this checklist when adding or materially changing a shipped installed surface in a package payload.

Use `docs/maintainer/maintainer-commands.md` for commands and `docs/maintainer/contributor-playbook.md` for routing; this page is only the
review bar for collaboration-sensitive installed surfaces.
""",
    )
    _write(
        tmp_path / "memory" / "runbooks" / "dogfooding-feedback-routing.md",
        """
# Dogfooding Feedback Routing

Use this convention when internal use reveals friction.

Use planning surfaces when the signal changes active execution; this page is only for classifying and routing the
signal, not for keeping a backlog.
""",
    )
    _write(
        tmp_path / "docs" / "workflow-contract-changes.md",
        """
# Workflow Contract Changes

Use this page as a compact maintainer-facing record of recent workflow-surface changes.

Keep this page short and decision-shaped; it is not the full changelog, release notes, or command index.
""",
    )


def test_self_improvement_skill_requires_anti_overfitting_closeout_review() -> None:
    skill_text = (WORKSPACE_ROOT / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md").read_text(
        encoding="utf-8",
    )

    assert "Required Anti-Overfitting Review" in skill_text
    assert "`user_agent_value`" in skill_text
    assert "`surface_pressure`" in skill_text
    assert "`portability_boundary`" in skill_text
    assert "`human_intent_preserved`" in skill_text
    assert "Route to a planning review instead of closing" in skill_text
    assert "only package-internal neatness" in skill_text


def test_self_improvement_skill_requires_total_operating_cost_assessment() -> None:
    skill_text = (WORKSPACE_ROOT / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md").read_text(
        encoding="utf-8",
    )

    assert "Required Cost Assessment" in skill_text
    assert "`workflow_cost_found`" in skill_text
    assert "`architecture_cost_found`" in skill_text
    assert "`correct_by_design_assessment`" in skill_text
    assert "`validation_role`" in skill_text
    assert "`signals_consumed`" in skill_text
    assert "`signals_still_accumulating`" in skill_text
    assert "`net_cost_direction`" in skill_text
    assert "Validation success and issue closure are evidence, but they are not sufficient by themselves." in skill_text
    assert "agentic-workspace report --target . --section improvement_intake --format json" in skill_text
    assert "repeated validation repair loops as package/interface defects" in skill_text


def test_self_improvement_skill_requires_durable_residue_routing_before_closeout() -> None:
    skill_text = (WORKSPACE_ROOT / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md").read_text(
        encoding="utf-8",
    )

    assert "Required Durable-Residue Routing" in skill_text
    assert "`validation_passed`" in skill_text
    assert "`issue_completed`" in skill_text
    assert "`intent_satisfied`" in skill_text
    assert "`operating_cost_reduced`" in skill_text
    assert "`durable_residue_routed`" in skill_text
    assert "`durable_residue_owner`" in skill_text
    assert "`post_promotion_shape`" in skill_text
    assert "future-relevant motivation or lessons exist only in an archived execplan" in skill_text
    assert "Memory note template's closeout-derived residue fields" in skill_text


def test_dogfooding_routing_runbook_covers_routed_dismissed_and_no_signal_cases() -> None:
    text = (WORKSPACE_ROOT / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "dogfooding-feedback-routing.md").read_text(
        encoding="utf-8"
    )

    assert "Routine Routing Examples" in text
    assert "Routed issue signal" in text
    assert "Memory-or-docs candidate" in text
    assert "Dismissed signal" in text
    assert "No-signal-found case" in text
    assert "`no_signal_found`" in text
    assert "`not_checked`" in text


def test_dogfooding_feedback_doc_distinguishes_not_checked_from_no_signal_found() -> None:
    text = (WORKSPACE_ROOT / "docs" / "maintainer" / "dogfooding-feedback.md").read_text(encoding="utf-8")

    assert "`not_checked`" in text
    assert "`no_signal_found`" in text
    assert "issue follow-up, Memory, Planning, docs/checks/contracts, direct fix, or dismissed-with-reason" in text


def test_self_improvement_skill_uses_constrained_prose_shape() -> None:
    skill_text = (WORKSPACE_ROOT / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md").read_text(
        encoding="utf-8",
    )

    assert "Constrained Prose Shape" in skill_text
    assert "planning review `prose_templates`" in skill_text
    assert "`Intent`" in skill_text
    assert "`What changed`" in skill_text
    assert "`Proof`" in skill_text
    assert "`Remaining risk`" in skill_text
    assert "`Durable residue`" in skill_text
    assert "`Next owner`" in skill_text


def test_self_improvement_skill_requires_operational_affordance_review() -> None:
    skill_text = (WORKSPACE_ROOT / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md").read_text(
        encoding="utf-8",
    )

    assert "Required Operational-Affordance Review" in skill_text
    assert "docs/maintainer/operational-affordance-design.md" in skill_text
    assert "`primary_next_action`" in skill_text
    assert "`irrelevant_actions_demoted`" in skill_text
    assert "`resolved_invocation`" in skill_text
    assert "`weak_agent_path`" in skill_text
    assert "`context_burden_change`" in skill_text
    assert "raw planning, Memory, review, contract, or issue-thread detail" in skill_text


def test_contributor_playbook_requires_operational_affordance_review() -> None:
    text = (WORKSPACE_ROOT / "docs" / "maintainer" / "contributor-playbook.md").read_text(encoding="utf-8")

    assert "docs/maintainer/operational-affordance-design.md" in text
    assert "operational-affordance review" in text
    assert "one primary next action" in text
    assert "resolved config/local invocation" in text
    assert "weak agents can proceed without learning package internals" in text


def test_testing_strategy_guides_against_one_off_regression_sprawl() -> None:
    playbook = (WORKSPACE_ROOT / "docs" / "maintainer" / "contributor-playbook.md").read_text(encoding="utf-8")
    strategy = (WORKSPACE_ROOT / "docs" / "maintainer" / "testing-strategy.md").read_text(encoding="utf-8")
    replacement_plan = (WORKSPACE_ROOT / "docs" / "maintainer" / "contract-test-replacement-plan.md").read_text(encoding="utf-8")
    aw_inventory = (WORKSPACE_ROOT / "docs" / "maintainer" / "aw-contract-test-replacement-inventory.md").read_text(encoding="utf-8")

    assert "docs/maintainer/testing-strategy.md" in playbook
    assert "Primitive conformance" in strategy
    assert "Fragment or subflow behavior" in strategy
    assert "Operation composition" in strategy
    assert "Representative command black-box behavior" in strategy
    assert "Contract-Owned Cases" in strategy
    assert "Prune only when stronger or equivalent coverage remains" in strategy
    assert "#1373 owns the plan" in strategy
    assert "contract-test-replacement-plan.md" in strategy
    assert "#1374 owns replacing AW generated-command behavior tests" in strategy
    assert "rickardvh/command-generation#9" in strategy
    assert "aw-contract-test-replacement-inventory.md" in strategy
    assert "Do not preserve the current test layout" in replacement_plan
    assert "Delete Or Merge Only With Equivalent Coverage" in replacement_plan
    assert "old test name" in replacement_plan
    assert "replacement contract id and case id" in replacement_plan
    assert "rickardvh/command-generation#9" in replacement_plan
    assert "#1374 is complete for the AW repository" in aw_inventory
    assert "This inventory does not close `rickardvh/command-generation#9`" in aw_inventory
    assert "test_blackbox_root_generated_command_executes_through_console_script" in aw_inventory
    assert "test_blackbox_root_generated_command_executes_primitive_ir_through_console_script" in aw_inventory
    assert "test_defaults_tiny_text_uses_generated_output" in aw_inventory
    assert "test_defaults_selected_section_text_uses_generated_output" in aw_inventory
    assert "test_config_selected_text_uses_generated_output" in aw_inventory
    assert "test_note_delegation_outcome_text_uses_generated_output" in aw_inventory
    assert "modules.report.process" in aw_inventory
    assert "defaults.root-cli-authority.process" in aw_inventory
    assert "defaults.tiny-text.process" in aw_inventory
    assert "defaults.selected-text.process" in aw_inventory
    assert "config.selected-text.process" in aw_inventory
    assert "delegation-outcome.append-text.process" in aw_inventory
    assert "stdout.contains" in aw_inventory
    assert "rickardvh/command-generation#10" in aw_inventory
    assert "Deleted Ordinary Regressions" in aw_inventory
    assert "tests/test_generated_command_package_proof_runner.py" in aw_inventory
    assert "tests/test_workspace_proof_generated_packages_cli.py" in aw_inventory
    assert "tests/test_command_generation_primitive_executor.py" in aw_inventory
    assert "tests/test_workspace_cli.py" in aw_inventory
    assert "tests/test_workspace_config_cli.py" in aw_inventory
    assert "tests/test_workspace_defaults_cli.py" in aw_inventory
    assert "tests/test_workspace_implement_cli.py" in aw_inventory
    assert "tests/test_workspace_proof_cli.py" in aw_inventory
    assert "tests/test_workspace_report_cli.py" in aw_inventory
    assert "tests/test_workspace_start_preflight_cli.py" in aw_inventory
    assert "adapter error classification and recovery-message surfaces" in aw_inventory
    assert "proof/checker orchestration" in aw_inventory
    assert "high-risk workflow semantics" in aw_inventory


def test_maintainer_surface_role_guidance_passes_when_docs_are_scoped(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "maintainer_surfaces_valid")
    _write_planning_surfaces(tmp_path)
    _write_generated_agent_surfaces(tmp_path)
    _write_docs_surfaces(tmp_path)

    warnings = mod.gather_maintainer_warnings(repo_root=tmp_path)

    assert not any(warning.warning_class == "startup_policy_drift" for warning in warnings)


def test_contributor_playbook_routes_first_contact_through_compact_queries() -> None:
    text = (WORKSPACE_ROOT / "docs" / "maintainer" / "contributor-playbook.md").read_text(encoding="utf-8")
    startup_section = text.split("## Start Here", 1)[1].split("##", 1)[0].lower()

    assert 'agentic-workspace start --task "<task>" --format json' in startup_section
    assert "agentic-workspace summary --format json" in startup_section
    assert startup_section.index('agentic-workspace start --task "<task>" --format json') < startup_section.index(
        ".agentic-workspace/planning/state.toml"
    )
    assert "only when compact output points there" in startup_section


def test_maintainer_surface_role_guidance_warns_when_readme_docs_map_drifts(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "maintainer_surfaces_drift")
    _write_planning_surfaces(tmp_path)
    _write_generated_agent_surfaces(tmp_path)
    _write_docs_surfaces(tmp_path, drift_readme=True)

    warnings = mod.gather_maintainer_warnings(repo_root=tmp_path)

    assert any(warning.warning_class == "startup_policy_drift" and str(warning.path).endswith("README.md") for warning in warnings)


def test_maintainer_surface_checker_includes_boundary_warnings(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "maintainer_surfaces_boundary")
    _write_planning_surfaces(tmp_path)
    _write_generated_agent_surfaces(tmp_path)
    _write_docs_surfaces(tmp_path)
    _write(tmp_path / "packages" / "planning" / ".agentic-workspace" / "planning" / "state.toml", "# cloned planning state")

    warnings = mod.gather_maintainer_warnings(repo_root=tmp_path)

    assert any(warning.warning_class == "package_local_install_drift" for warning in warnings)


def test_render_wrapper_keeps_backward_compatible_entrypoint_alias() -> None:
    mod = _load_module(_render_script_path(), "maintainer_render_alias")

    assert mod.REPO_ROOT == WORKSPACE_ROOT
    assert mod.render_readme_entrypoints is mod.render_quickstart


def test_rendered_routing_adapter_stays_secondary_and_compact() -> None:
    mod = _load_module(_render_script_path(), "maintainer_render_compact")
    text = mod.render_routing(_baseline_manifest())

    assert "Secondary generated adapter" in text
    assert "Prefer `AGENTS.md`, then `tools/AGENT_QUICKSTART.md`." in text
    assert 'uv run agentic-workspace start --task "<task>" --format json' in text
    assert "uv run agentic-workspace summary --format json" in text
    assert "uv run agentic-workspace preflight --format json" not in text
    assert "uv run agentic-workspace report --target . --format json" not in text
    assert len(text.splitlines()) <= 20
