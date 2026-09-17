from __future__ import annotations

import importlib.util
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


def _write_generated_agent_surfaces(tmp_path: Path) -> None:
    render_module = _load_module(_render_script_path(), "maintainer_render")
    _write(tmp_path / "tools" / "AGENT_QUICKSTART.md", render_module.render_quickstart())
    _write(tmp_path / "tools" / "AGENT_ROUTING.md", render_module.render_routing())


def _write_planning_surfaces(tmp_path: Path) -> None:
    _write(
        tmp_path / "AGENTS.md",
        """
# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Use `.agentic-workspace/skills/workspace-startup/SKILL.md` for repository procedure;
if native skill discovery is unavailable, read it directly.
<!-- agentic-workspace:workflow:end -->
""",
    )
    # Optional Planning state is absent in the clean current baseline.
    # Individual tests introduce only the owner drift they exercise.


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
2. Follow `.agentic-workspace/skills/workspace-startup/SKILL.md`.
3. Use current native owner requests for the task and open only selected owner detail.
4. Read the relevant Planning record only when current owner routing selects it.
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


def test_readme_docs_map_is_not_a_startup_authority(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "maintainer_surfaces_drift")
    _write_planning_surfaces(tmp_path)
    _write_generated_agent_surfaces(tmp_path)
    _write_docs_surfaces(tmp_path, drift_readme=True)

    warnings = mod.gather_maintainer_warnings(repo_root=tmp_path)

    assert not any(warning.warning_class == "startup_policy_drift" for warning in warnings)


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
    text = mod.render_routing()
    assert "Use `AGENTS.md` and the canonical workspace startup skill" in text
    assert "current native Planning relation/posture" in text
    assert "No helper supplies mutation or completion authority" in text
    assert "agent-manifest" not in text
    assert len(text.splitlines()) <= 22


def test_issue_and_review_skills_audit_architectural_assumptions() -> None:
    issue_skill = (WORKSPACE_ROOT / "tools" / "skills" / "github-issue-shaping" / "SKILL.md").read_text(encoding="utf-8")
    creation_skill = (WORKSPACE_ROOT / "tools" / "skills" / "github-issue-creation" / "SKILL.md").read_text(encoding="utf-8")
    review_skill = (WORKSPACE_ROOT / "tools" / "skills" / "pr-review-recheck" / "SKILL.md").read_text(encoding="utf-8")

    assert "directly observed evidence" in issue_skill
    assert "framework, registry, durable-state, or event-ledger growth" in issue_skill
    assert "repo/provider/dogfooding evidence" in issue_skill
    assert "one-off static comparison" in issue_skill
    assert "use `github-issue-shaping` first" in creation_skill.lower()
    assert "PR violates a sound issue requirement" in review_skill
    assert "issue requirement is wrong or too strong" in review_skill
    assert "every selector to be cheaper" in review_skill
    assert "independent of the implementation lineage that produced it" in review_skill
    assert "Delegation does not create independence." in review_skill
    assert "Never use this skill as permission for an implementation agent" in review_skill


def test_rendered_quickstart_routes_to_current_procedure_without_copying_doctrine() -> None:
    mod = _load_module(_render_script_path(), "maintainer_render_issue_review_routes")
    text = mod.render_quickstart()
    assert "skills/workspace-startup/SKILL.md" in text
    assert "Follow selected owner requests and skills" in text
    assert "Verification owns proof and claims" in text
    assert "agent-manifest" not in text
    assert len(text.splitlines()) <= 28


def test_optional_friction_ledger_still_rejects_malformed_present_evidence(tmp_path: Path) -> None:
    checker = _load_module(WORKSPACE_ROOT / "scripts/check/check_recurring_friction_ledger.py", "friction_checker")
    assert checker.gather_ledger_warnings(repo_root=tmp_path) == []
    ledger = tmp_path / ".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"
    _write(ledger, "# Recurring friction\n\n## Unattributed repeated failure\n")
    warnings = checker.gather_ledger_warnings(repo_root=tmp_path)
    assert any(w.warning_class == "recurring_friction_structure" for w in warnings)
