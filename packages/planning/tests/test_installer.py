from __future__ import annotations

from pathlib import Path

import repo_planning_bootstrap.installer as installer_mod
from repo_planning_bootstrap._ownership import module_root as planning_module_root
from repo_planning_bootstrap.installer import (
    PLANNING_COMPATIBILITY_CONTRACT_FILES,
    PLANNING_LOWER_STABILITY_HELPER_FILES,
    REQUIRED_PAYLOAD_FILES,
    adopt_bootstrap,
    archive_execplan,
    collect_status,
    doctor_bootstrap,
    install_bootstrap,
    planning_summary,
    promote_todo_item_to_execplan,
    uninstall_bootstrap,
    upgrade_bootstrap,
    verify_payload,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _minimal_execplan(status: str = "in-progress") -> str:
    return f"""
# Plan Alpha

## Goal

- Keep scope clear.

## Non-Goals

- No runtime changes.

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

## Drift Log

- 2026-04-04: Initial plan created.
"""


def test_install_bootstrap_copies_required_files(tmp_path: Path) -> None:
    result = install_bootstrap(target=tmp_path)
    skill_readme_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "README.md"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"
    intake_skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-intake-upstream-task" / "SKILL.md"
    review_readme_path = tmp_path / "docs" / "reviews" / "README.md"
    review_template_path = tmp_path / "docs" / "reviews" / "TEMPLATE.md"
    intake_doc_path = tmp_path / "docs" / "upstream-task-intake.md"

    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "TODO.md").exists()
    assert (tmp_path / "ROADMAP.md").exists()
    assert review_readme_path.exists()
    assert review_template_path.exists()
    assert intake_doc_path.exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "scripts" / "render_agent_docs.py").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_planning_surfaces.py").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_maintainer_surfaces.py").exists()
    assert skill_readme_path.exists()
    assert skill_path.exists()
    assert intake_skill_path.exists()
    assert (tmp_path / "tools" / "AGENT_QUICKSTART.md").exists()
    assert (tmp_path / "tools" / "AGENT_ROUTING.md").exists()
    assert (tmp_path / "scripts" / "check" / "check_maintainer_surfaces.py").exists()
    assert any(action.kind in {"copied", "created", "updated"} for action in result.actions)


def test_ownership_module_root_matches_workspace_ledger() -> None:
    assert planning_module_root("planning") == Path(".agentic-workspace/planning")


def test_planning_contract_file_shortlist_is_explicit() -> None:
    assert Path("AGENTS.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path("TODO.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path("docs/execplans/README.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path("docs/reviews/README.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path("docs/upstream-task-intake.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path("tools/AGENT_QUICKSTART.md") in PLANNING_LOWER_STABILITY_HELPER_FILES
    assert Path("scripts/render_agent_docs.py") in PLANNING_LOWER_STABILITY_HELPER_FILES
    assert set(PLANNING_COMPATIBILITY_CONTRACT_FILES).isdisjoint(PLANNING_LOWER_STABILITY_HELPER_FILES)
    assert set(PLANNING_COMPATIBILITY_CONTRACT_FILES) | set(PLANNING_LOWER_STABILITY_HELPER_FILES) == set(REQUIRED_PAYLOAD_FILES)


def test_adopt_bootstrap_preserves_existing_agents(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    result = adopt_bootstrap(target=tmp_path)
    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)


def test_adopt_bootstrap_docs_heavy_repo_preserves_root_surfaces_and_installs_helpers(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    todo_path = tmp_path / "TODO.md"
    roadmap_path = tmp_path / "ROADMAP.md"
    execplan_readme_path = tmp_path / "docs" / "execplans" / "README.md"
    contributor_playbook_path = tmp_path / "docs" / "contributor-playbook.md"
    maintainer_commands_path = tmp_path / "docs" / "maintainer-commands.md"

    _write(agents_path, "# Existing agents\n")
    _write(todo_path, "# Existing TODO\n")
    _write(roadmap_path, "# Existing Roadmap\n")
    _write(execplan_readme_path, "# Existing execution docs\n")
    _write(contributor_playbook_path, "# Existing contributor playbook\n")
    _write(maintainer_commands_path, "# Existing commands\n")

    result = adopt_bootstrap(target=tmp_path)

    assert agents_path.read_text(encoding="utf-8") == "# Existing agents\n"
    assert todo_path.read_text(encoding="utf-8") == "# Existing TODO\n"
    assert roadmap_path.read_text(encoding="utf-8") == "# Existing Roadmap\n"
    assert execplan_readme_path.read_text(encoding="utf-8") == "# Existing execution docs\n"
    assert contributor_playbook_path.read_text(encoding="utf-8") == "# Existing contributor playbook\n"
    assert maintainer_commands_path.read_text(encoding="utf-8") == "# Existing commands\n"
    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md").exists()
    assert (tmp_path / "tools" / "AGENT_QUICKSTART.md").exists()
    assert (tmp_path / "tools" / "AGENT_ROUTING.md").exists()
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "skipped" and action.path == execplan_readme_path for action in result.actions)
    assert any(
        action.kind in {"copied", "created", "updated"}
        and action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        for action in result.actions
    )
    assert any(
        action.kind in {"copied", "created", "updated"}
        and action.path == tmp_path / "tools" / "AGENT_QUICKSTART.md"
        for action in result.actions
    )


def test_adopt_bootstrap_preserves_existing_manifest_in_partial_managed_state(tmp_path: Path) -> None:
    manifest_path = tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
    manifest_text = '{"bootstrap": {"first_reads": ["AGENTS.md", "TODO.md"]}}\n'
    _write(manifest_path, manifest_text)

    result = adopt_bootstrap(target=tmp_path)

    assert manifest_path.read_text(encoding="utf-8") == manifest_text
    assert (tmp_path / "tools" / "agent-manifest.json").exists()
    assert (tmp_path / "tools" / "AGENT_QUICKSTART.md").exists()
    assert any(action.kind == "skipped" and action.path == manifest_path for action in result.actions)
    assert any(
        action.kind in {"created", "updated"}
        and action.path == tmp_path / "tools" / "agent-manifest.json"
        for action in result.actions
    )


def test_adopt_bootstrap_leaves_memory_owned_surfaces_untouched(tmp_path: Path) -> None:
    memory_index_path = tmp_path / "memory" / "index.md"
    _write(memory_index_path, "# Existing memory index\n")

    result = adopt_bootstrap(target=tmp_path)

    assert memory_index_path.read_text(encoding="utf-8") == "# Existing memory index\n"
    assert not any(action.path == memory_index_path for action in result.actions)
    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()


def test_status_reports_missing_and_present_files(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    result = collect_status(target=tmp_path)
    assert any(action.kind == "present" for action in result.actions)


def test_payload_filters_generated_artifacts(tmp_path: Path, monkeypatch) -> None:
    payload_root = tmp_path / "payload"
    _write(payload_root / "AGENTS.md", "agents\n")
    _write(
        payload_root / "scripts" / "render_agent_docs.py",
        (
            "import json\n\n"
            "from pathlib import Path\n\n"
            "def load_manifest():\n"
            "    manifest_path = Path(__file__).resolve().parents[1] / '.agentic-workspace' / 'planning' / 'agent-manifest.json'\n"
            "    return json.loads(manifest_path.read_text(encoding='utf-8'))\n\n"
            "def render_quickstart(_manifest):\n"
            "    return 'generated file\\n'\n\n"
            "def render_routing(_manifest):\n"
            "    return 'generated file\\n'\n"
        ),
    )
    _write(payload_root / "scripts" / "__pycache__" / "render_agent_docs.cpython-314.pyc", "junk\n")

    monkeypatch.setattr(installer_mod, "payload_root", lambda: payload_root)

    files = installer_mod.list_payload_files()
    assert "scripts/__pycache__/render_agent_docs.cpython-314.pyc" not in files

    result = install_bootstrap(target=tmp_path / "target")
    assert not (tmp_path / "target" / "scripts" / "__pycache__").exists()
    assert any(action.path == tmp_path / "target" / "AGENTS.md" for action in result.actions)


def test_verify_payload_generated_docs_match_manifest() -> None:
    result = verify_payload()
    manifest_actions = [action for action in result.actions if action.path.name == "agent-manifest.json"]
    quickstart_actions = [action for action in result.actions if action.path.name == "AGENT_QUICKSTART.md"]
    routing_actions = [action for action in result.actions if action.path.name == "AGENT_ROUTING.md"]
    assert manifest_actions
    assert quickstart_actions
    assert routing_actions
    assert any(action.kind == "current" for action in manifest_actions)
    assert any(action.kind == "current" for action in quickstart_actions)
    assert any(action.kind == "current" for action in routing_actions)


def test_verify_payload_reports_contract_surface_shortlists() -> None:
    result = verify_payload()

    assert any(
        action.path.name == "agent-manifest.json"
        and action.kind == "current"
        and "compatibility contract files:" in action.detail
        and "AGENTS.md" in action.detail
        and ".agentic-workspace/planning/agent-manifest.json" in action.detail
        for action in result.actions
    )
    assert any(
        action.path.name == "render_agent_docs.py"
        and action.kind == "current"
        and "lower-stability helper files:" in action.detail
        and "scripts/render_agent_docs.py" in action.detail
        and "tools/AGENT_QUICKSTART.md" in action.detail
        for action in result.actions
    )


def test_doctor_reports_contract_surface_shortlists(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert any(
        action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        and action.kind == "current"
        and "compatibility contract files:" in action.detail
        and "AGENTS.md" in action.detail
        and "docs/execplans/TEMPLATE.md" in action.detail
        and "docs/upstream-task-intake.md" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == tmp_path / ".agentic-workspace" / "planning" / "scripts" / "render_agent_docs.py"
        and action.kind == "current"
        and "lower-stability helper files:" in action.detail
        and "scripts/check/check_planning_surfaces.py" in action.detail
        and "tools/AGENT_ROUTING.md" in action.detail
        for action in result.actions
    )


def test_verify_payload_flags_missing_collaboration_safe_template_guidance(tmp_path: Path, monkeypatch) -> None:
    payload_root = tmp_path / "payload"
    _write(payload_root / "AGENTS.md", "# Agent Instructions\n")
    _write(payload_root / "TODO.md", "# TODO\n")
    _write(payload_root / "ROADMAP.md", "# Roadmap\n")
    _write(payload_root / "docs" / "execplans" / "README.md", "# Execution Plans\n")
    _write(payload_root / "docs" / "execplans" / "TEMPLATE.md", "# Plan Title\n")
    _write(payload_root / "docs" / "execplans" / "archive" / "README.md", "# Archive\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml", "source_type = \"git\"\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}\n")
    _write(
        payload_root / ".agentic-workspace" / "planning" / "scripts" / "render_agent_docs.py",
        (
            "def render_quickstart(_manifest):\n"
            "    return \"generated file\\n\"\n\n"
            "def render_routing(_manifest):\n"
            "    return \"generated file\\n\"\n"
        ),
    )
    _write(payload_root / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_planning_surfaces.py", "print('ok')\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_maintainer_surfaces.py", "print('ok')\n")
    _write(
        payload_root / "scripts" / "render_agent_docs.py",
        (
            "import json\n\n"
            "from pathlib import Path\n\n"
            "def load_manifest():\n"
            "    manifest_path = Path(__file__).resolve().parents[1] / '.agentic-workspace' / 'planning' / 'agent-manifest.json'\n"
            "    return json.loads(manifest_path.read_text(encoding='utf-8'))\n\n"
            "def render_quickstart(_manifest):\n"
            "    return 'generated file\\n'\n\n"
            "def render_routing(_manifest):\n"
            "    return 'generated file\\n'\n"
        ),
    )
    _write(payload_root / "scripts" / "check" / "check_planning_surfaces.py", "print('ok')\n")
    _write(payload_root / "scripts" / "check" / "check_maintainer_surfaces.py", "print('ok')\n")
    _write(payload_root / "tools" / "agent-manifest.json", "{}\n")
    _write(payload_root / "tools" / "AGENT_QUICKSTART.md", "generated file\n")
    _write(payload_root / "tools" / "AGENT_ROUTING.md", "generated file\n")

    monkeypatch.setattr(installer_mod, "payload_root", lambda: payload_root)

    result = verify_payload()

    assert any(
        action.path == payload_root / "docs" / "execplans" / "TEMPLATE.md"
        and action.kind == "manual review"
        and "collaboration-safe template wording" in action.detail
        for action in result.actions
    )


def test_upgrade_bootstrap_overwrites_managed_files_but_preserves_root_surfaces(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    checker_path = tmp_path / "scripts" / "check" / "check_planning_surfaces.py"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    checker_path.write_text("stale checker\n", encoding="utf-8")
    skill_path.write_text("stale skill\n", encoding="utf-8")

    result = upgrade_bootstrap(target=tmp_path)

    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert "stale checker" not in checker_path.read_text(encoding="utf-8")
    assert "stale skill" not in skill_path.read_text(encoding="utf-8")
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "overwritten" and action.path == checker_path for action in result.actions)
    assert any(action.kind == "overwritten" and action.path == skill_path for action in result.actions)


def test_upgrade_bootstrap_legacy_standalone_install_adds_managed_helpers_without_overwriting_root_surfaces(tmp_path: Path) -> None:
    _write(tmp_path / "AGENTS.md", "legacy repo-owned agents\n")
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / "docs" / "execplans" / "README.md", "# Execution Plans\n")
    _write(tmp_path / "docs" / "execplans" / "TEMPLATE.md", "# Plan Title\n")
    _write(tmp_path / "docs" / "execplans" / "archive" / "README.md", "# Archive\n")
    _write(tmp_path / "docs" / "reviews" / "README.md", "# Reviews\n")
    _write(tmp_path / "docs" / "reviews" / "TEMPLATE.md", "# Review Template\n")
    _write(tmp_path / "docs" / "upstream-task-intake.md", "# Upstream Task Intake\n")

    result = upgrade_bootstrap(target=tmp_path)

    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (tmp_path / "tools" / "AGENT_QUICKSTART.md").exists()
    assert (tmp_path / "tools" / "AGENT_ROUTING.md").exists()
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "legacy repo-owned agents\n"
    assert any(action.kind == "skipped" and action.path == tmp_path / "AGENTS.md" for action in result.actions)
    assert any(
        action.kind == "copied" and action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        for action in result.actions
    )


def test_upgrade_bootstrap_recovers_partial_managed_state_without_overwriting_root_surfaces(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    manifest_path = tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
    routing_path = tmp_path / "tools" / "AGENT_ROUTING.md"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    manifest_path.unlink()
    routing_path.unlink()

    result = upgrade_bootstrap(target=tmp_path)

    assert manifest_path.exists()
    assert routing_path.exists()
    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert any(action.kind == "copied" and action.path == manifest_path for action in result.actions)
    assert any(action.kind == "created" and action.path == routing_path for action in result.actions)
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)


def test_doctor_reports_stale_generated_routing_residue_for_partial_managed_state(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    routing_path = tmp_path / "tools" / "AGENT_ROUTING.md"
    routing_path.write_text("stale generated routing\n", encoding="utf-8")

    result = doctor_bootstrap(target=tmp_path)

    assert any(
        action.kind == "manual review"
        and action.path == routing_path
        and "out of sync with .agentic-workspace/planning/agent-manifest.json" in action.detail
        for action in result.actions
    )


def test_uninstall_bootstrap_removes_pristine_files_and_keeps_modified_surfaces(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    checker_path = tmp_path / "scripts" / "check" / "check_planning_surfaces.py"
    quickstart_path = tmp_path / "tools" / "AGENT_QUICKSTART.md"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")

    result = uninstall_bootstrap(target=tmp_path)

    assert agents_path.exists()
    assert not checker_path.exists()
    assert not quickstart_path.exists()
    assert not skill_path.exists()
    assert any(action.kind == "manual review" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "removed" and action.path == checker_path for action in result.actions)
    assert any(action.kind == "removed" and action.path == skill_path for action in result.actions)


def test_promote_todo_item_to_execplan_scaffolds_plan_and_updates_todo(tmp_path: Path) -> None:
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: direct-item
  Status: in-progress
  Surface: direct
  Why now: this thread needs a bounded execution contract.
  Next Action: sketch the first implementation step.
  Done When: the bounded change is implemented and validated.
""",
    )

    result = promote_todo_item_to_execplan("direct-item", target=tmp_path)
    plan_path = tmp_path / "docs" / "execplans" / "direct-item.md"

    assert plan_path.exists()
    todo_text = (tmp_path / "TODO.md").read_text(encoding="utf-8")
    assert "Surface: docs/execplans/direct-item.md" in todo_text
    assert "Next Action:" not in todo_text
    assert "Done When:" not in todo_text
    assert any(action.kind == "created" and action.path == plan_path for action in result.actions)


def test_promote_todo_item_to_execplan_refuses_existing_execplan_surface(tmp_path: Path) -> None:
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: docs/execplans/plan-alpha.md
  Why now: this item is already routed through an execplan.
""",
    )
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())

    result = promote_todo_item_to_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "manual review" and "already points at" in action.detail for action in result.actions)


def test_archive_execplan_moves_completed_plan(tmp_path: Path) -> None:
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / "docs" / "execplans" / "plan-alpha.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("plan-alpha", target=tmp_path)
    archived_path = tmp_path / "docs" / "execplans" / "archive" / "plan-alpha.md"

    assert archived_path.exists()
    assert not plan_path.exists()
    assert any(action.kind == "moved" and action.path == archived_path for action in result.actions)


def test_archive_execplan_apply_cleanup_updates_completed_todo_and_roadmap(tmp_path: Path) -> None:
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: plan-alpha
  Status: completed
  Surface: docs/execplans/plan-alpha.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Plan alpha is the current active package pass.

## Next Candidate Queue

- Candidate beta: promote when a report signals follow-on work.
""",
    )
    plan_path = tmp_path / "docs" / "execplans" / "plan-alpha.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("plan-alpha", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / "TODO.md").read_text(encoding="utf-8")
    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "plan-alpha" not in todo_text
    assert "- No active work right now." in todo_text
    assert "- No active handoff right now." in roadmap_text
    assert any(action.kind == "updated" and action.path == tmp_path / "TODO.md" for action in result.actions)
    assert any(action.kind == "updated" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)


def test_archive_execplan_apply_cleanup_removes_matching_candidate_queue_entry(tmp_path: Path) -> None:
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: workspace-result-contract
  Status: completed
  Surface: docs/execplans/workspace-result-contract-2026-04-05.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Workspace result contract docs are complete.

## Next Candidate Queue

- Workspace result contract: define a shared adapter or result protocol for
    orchestrated module actions and warnings when more module families land.
- Shared tooling extraction: evaluate a common checker core when repeated maintenance friction appears.
""",
    )
    plan_path = tmp_path / "docs" / "execplans" / "workspace-result-contract-2026-04-05.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("workspace-result-contract-2026-04-05", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Workspace result contract:" not in roadmap_text
    assert "Shared tooling extraction:" in roadmap_text
    assert any(
        action.kind == "updated" and action.path == tmp_path / "ROADMAP.md" and "Next Candidate Queue" in action.detail
        for action in result.actions
    )


def test_archive_execplan_without_cleanup_only_suggests_roadmap_followup(tmp_path: Path) -> None:
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Plan alpha is the current active package pass.
""",
    )
    plan_path = tmp_path / "docs" / "execplans" / "plan-alpha.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "suggested fix" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)
    assert any(warning["warning_class"] == "roadmap_archive_followup" for warning in result.warnings)


def test_archive_execplan_ignores_generic_roadmap_language(tmp_path: Path) -> None:
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- The initial package pass is complete.

## Promotion Rules

- Promote an epic only when it is ready for active execution.
""",
    )
    plan_path = tmp_path / "docs" / "execplans" / "promotion-linkage-tuning-2026-04-05.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("promotion-linkage-tuning-2026-04-05", target=tmp_path)

    assert not any(action.kind == "suggested fix" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)
    assert not any(warning["warning_class"] == "roadmap_archive_followup" for warning in result.warnings)


def test_planning_summary_reports_active_items_and_warnings(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: docs/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Candidate alpha: promote when maintained report signal appears.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)

    assert summary["todo"]["active_count"] == 1
    assert summary["execplans"]["active_count"] == 1
    assert summary["roadmap"]["candidate_count"] == 1
    assert summary["warning_count"] == 0
