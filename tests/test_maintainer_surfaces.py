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


def _write_planning_surfaces(tmp_path: Path) -> None:
    _write(
        tmp_path / "AGENTS.md",
        """
# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Use the main Agentic Workspace operating skill: `.agentic-workspace/skills/workspace-startup/SKILL.md`.

Invocation rule:
1. Use `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present.
2. Otherwise use `.agentic-workspace/config.toml` `[workspace].cli_invoke`.
3. Otherwise use the package default `agentic-workspace`.
4. If no CLI invocation works, read `.agentic-workspace/skills/workspace-startup/SKILL.md` before other workspace files.

Ordinary route:
1. Run `<configured AW invocation> start --target . --task "<task>" --format json` before non-trivial answers, edits, read-only workflow, config, delegation, or action-safety decisions.
2. Run `<configured AW invocation> implement --target . --changed <paths> --task "<task>" --format json` when changed paths are already known.
3. Follow the authoritative `decision_packet` action, effects, claim boundary, and routed detail before opening raw `.agentic-workspace` files or running drill-down commands.
4. Use the returned `communication_contract` for decision-first, evidence-backed, compact output; expand only for its safety/proof/detail triggers.
5. When implementing an issue, satisfy the intended end state in the ordinary path; ask for clarification instead of closing with a partial path when the full outcome appears larger than the issue safely permits.

Boundaries:
- Known dedicated Agentic Workspace commands are allowed only when the request maps directly to that command and no takeover, recovery, active-planning, or ambiguous safety decision is needed first.
- Do not bake machine-local AW invocation paths into checked-in generic guidance; concrete commands come from the configured invocation or live router output.
- Treat checked-in `.agentic-workspace/skills` and module skill trees as required operating surfaces, not optional payload mirror content.
- Treat `.agentic-workspace/skills/workspace-startup/SKILL.md` as the shared startup fallback reached through this adapter.
- Treat `preflight`, `config`, `defaults`, `skills`, `modules`, `ownership`, and `report` as routed drill-down or recovery surfaces, not the ordinary startup loop.
- Report repo-relative paths, not local absolute paths.
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


def test_maintainer_surface_role_guidance_passes_when_docs_are_scoped(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "maintainer_surfaces_valid")
    _write_planning_surfaces(tmp_path)
    _write_generated_agent_surfaces(tmp_path)
    _write_docs_surfaces(tmp_path)

    warnings = mod.gather_maintainer_warnings(repo_root=tmp_path)

    assert not any(warning.warning_class == "startup_policy_drift" for warning in warnings)


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


def test_runtime_source_routing_checker_accepts_current_repo() -> None:
    mod = _load_module(_checker_script_path(), "maintainer_surfaces_runtime_current")

    warnings = mod.gather_maintainer_warnings(repo_root=WORKSPACE_ROOT)

    assert not any(warning.warning_class.startswith("RUNTIME_") for warning in warnings)


def test_runtime_source_routing_checker_reports_drift(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "maintainer_surfaces_runtime_drift")
    _write_planning_surfaces(tmp_path)
    _write_generated_agent_surfaces(tmp_path)
    _write_docs_surfaces(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "workspace-cli-runtime"
paths = ["generated/workspace/python/**"]
owns = ["workspace command routing"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
kind = "agentic-workspace/system-intent/v1"

[[architecture_principles]]
id = "host-agnostic-agent-judgment"
path_globs = ["src/agentic_workspace/workspace_runtime_primitives.py"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "manifest.toml",
        """
[protocols.closeout_intent_satisfaction]
authority_refs = ["src/agentic_workspace/workspace_runtime_primitives.py"]
applies_to_paths = ["src/agentic_workspace/workspace_runtime_primitives.py"]
stale_when = ["src/agentic_workspace/workspace_runtime_primitives.py"]

[protocols.requirement_grounding_delegation]
authority_refs = ["src/agentic_workspace/workspace_runtime_primitives.py"]
applies_to_paths = ["src/agentic_workspace/workspace_runtime_primitives.py"]
stale_when = ["src/agentic_workspace/workspace_runtime_primitives.py"]
""",
    )

    warning_classes = {warning.warning_class for warning in mod.gather_maintainer_warnings(repo_root=tmp_path)}

    assert "RUNTIME_SOURCE_OWNERSHIP_DRIFT" in warning_classes
    assert "RUNTIME_ARCHITECTURE_ROUTING_DRIFT" in warning_classes
    assert "RUNTIME_VERIFICATION_ROUTING_DRIFT" in warning_classes


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
    assert "tools/skills/github-issue-shaping/SKILL.md" in text
    assert "tools/skills/pr-review-recheck/SKILL.md" in text
    assert len(text.splitlines()) <= 22


def test_issue_and_review_skills_audit_architectural_assumptions() -> None:
    issue_skill = (WORKSPACE_ROOT / "tools" / "skills" / "github-issue-shaping" / "SKILL.md").read_text(encoding="utf-8")
    creation_skill = (WORKSPACE_ROOT / "tools" / "skills" / "github-issue-creation" / "SKILL.md").read_text(encoding="utf-8")
    review_skill = (WORKSPACE_ROOT / "tools" / "skills" / "pr-review-recheck" / "SKILL.md").read_text(encoding="utf-8")

    assert "directly observed evidence" in issue_skill
    assert "framework, registry, durable-state, or event-ledger growth" in issue_skill
    assert "repo/provider/dogfooding evidence" in issue_skill
    assert "one-off static comparison" in issue_skill
    assert "use `github-issue-shaping` first" in creation_skill
    assert "PR violates a sound issue requirement" in review_skill
    assert "issue requirement is wrong or too strong" in review_skill
    assert "every selector to be cheaper" in review_skill


def test_rendered_quickstart_routes_issue_and_review_work_without_copying_doctrine() -> None:
    mod = _load_module(_render_script_path(), "maintainer_render_issue_review_routes")
    text = mod.render_quickstart(_baseline_manifest())

    assert "tools/skills/github-issue-shaping/SKILL.md" in text
    assert "tools/skills/github-issue-creation/SKILL.md" in text
    assert "tools/skills/pr-review-recheck/SKILL.md" in text
    assert "directly observed evidence" not in text
    assert len(text.splitlines()) <= 28
