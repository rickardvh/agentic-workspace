from __future__ import annotations

import json
from pathlib import Path

import repo_planning_bootstrap._render as render_module
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
    return f"""
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

## Delegated Judgment

- Requested outcome: Keep scope clear.
- Hard constraints: Keep scope bounded to the promoted TODO item and its touched paths.
- Agent may decide locally: Bounded decomposition, validation tightening, and plan-local residue routing.
- Escalate when: The requested outcome, owned surface, time horizon, or meaningful validation story would change.

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

## Drift Log

- 2026-04-04: Initial plan created.
"""


def test_install_bootstrap_copies_required_files(tmp_path: Path) -> None:
    result = install_bootstrap(target=tmp_path)
    capability_fit_doc_path = tmp_path / "docs" / "capability-aware-execution.md"
    environment_recovery_doc_path = tmp_path / "docs" / "environment-recovery-contract.md"
    execution_summary_doc_path = tmp_path / "docs" / "execution-summary-contract.md"
    intent_contract_doc_path = tmp_path / "docs" / "intent-contract.md"
    skill_readme_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "README.md"
    skill_registry_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "REGISTRY.json"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"
    intake_skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-intake-upstream-task" / "SKILL.md"
    review_readme_path = tmp_path / "docs" / "reviews" / "README.md"
    review_template_path = tmp_path / "docs" / "reviews" / "TEMPLATE.md"
    intake_doc_path = tmp_path / "docs" / "upstream-task-intake.md"

    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "TODO.md").exists()
    assert (tmp_path / "ROADMAP.md").exists()
    assert capability_fit_doc_path.exists()
    assert environment_recovery_doc_path.exists()
    assert execution_summary_doc_path.exists()
    assert intent_contract_doc_path.exists()
    assert review_readme_path.exists()
    assert review_template_path.exists()
    assert intake_doc_path.exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "scripts" / "render_agent_docs.py").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_planning_surfaces.py").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_maintainer_surfaces.py").exists()
    assert skill_readme_path.exists()
    assert skill_registry_path.exists()
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
    assert Path("docs/capability-aware-execution.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path("docs/environment-recovery-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
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
        action.kind in {"copied", "created", "updated"} and action.path == tmp_path / "tools" / "AGENT_QUICKSTART.md"
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
        action.kind in {"created", "updated"} and action.path == tmp_path / "tools" / "agent-manifest.json" for action in result.actions
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


def test_bootstrap_review_readme_includes_canonical_review_portfolio() -> None:
    text = (installer_mod.payload_root() / "docs" / "reviews" / "README.md").read_text(encoding="utf-8")

    assert "## Canonical Review Portfolio" in text
    assert "`contract-integrity`" in text
    assert "future contributors would reasonably trust" in text
    assert "promise-vs-enforcement gaps" in text
    assert "`maintainer-workflow`" in text
    assert "`source-payload-install`" in text
    assert "`doctrine-refresh`" in text
    assert "`review-promotion`" in text
    assert "Use one primary review mode per artifact." in text
    assert "default finding cap" in text
    assert "long-horizon doctrine still matches current dogfooding reality" in text
    assert "## Improvement-targeting workflow" in text
    assert "record the intended post-remediation note shape" in text
    assert "Repeated findings that work needed stronger execution capability than expected" in text
    assert "make future work cheaper to execute" in text
    assert "Last doctrinal review" in text


def test_bootstrap_review_template_includes_mode_and_cap_fields() -> None:
    text = (installer_mod.payload_root() / "docs" / "reviews" / "TEMPLATE.md").read_text(encoding="utf-8")

    assert "## Review Mode" in text
    assert "- Mode:" in text
    assert "- Review question:" in text
    assert "- Default finding cap:" in text
    assert "- Inputs inspected first:" in text
    assert "- Post-remediation note shape:" in text


def test_bootstrap_capability_aware_execution_doc_defines_categories() -> None:
    text = (installer_mod.payload_root() / "docs" / "capability-aware-execution.md").read_text(encoding="utf-8")

    assert "# Capability-Aware Execution" in text
    assert "## Operating Stance" in text
    assert "## Task-Shape Dimensions" in text
    assert "### Cheap Direct Execution" in text
    assert "### Stronger Planning First" in text
    assert "### Autopilot-Suitable" in text
    assert "### Delegation-Friendly" in text
    assert "### Stop And Escalate" in text
    assert "## Silent Shaping And Non-Interference" in text
    assert "## Bounded Initiative And Scope Expansion" in text
    assert "## Complexity-Reduction Feedback" in text
    assert "automatic capability selection" in text
    assert "Prefer changing the work shape over interrupting execution with capability advice." in text
    assert "make more future tasks safe for cheaper execution paths" in text
    assert "task-shape based" in text
    assert "Intent is sticky" in text
    assert "do not silently replace the requested outcome" in text
    assert "improve means locally" in text
    assert "do not rewrite ends locally" in text
    assert "present it as a promotion or escalation decision" in text


def test_bootstrap_delegated_judgment_doc_is_part_of_contract() -> None:
    text = (installer_mod.payload_root() / "docs" / "delegated-judgment-contract.md").read_text(encoding="utf-8")

    assert "# Delegated Judgment Contract" in text
    assert "## What The Human Sets" in text
    assert "## What The Agent May Decide Locally" in text
    assert "## What Requires Promotion Or Escalation" in text
    assert "## Scope-Expansion Rule" in text
    assert "Improve means locally" in text
    assert "The agent must not silently widen" in text
    assert "active execplans should carry a compact delegated-judgment section" in text
    assert Path("docs/delegated-judgment-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_bootstrap_environment_recovery_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / "docs" / "environment-recovery-contract.md").read_text(encoding="utf-8")

    assert "# Environment And Recovery Contract" in text
    assert "## Canonical Shape" in text
    assert "Immediate Next Action" in text
    assert "Validation Commands" in text
    assert "Do not add a new dedicated recovery section to every execplan." in text
    assert "Do not stretch TODO rows into shadow execplans." in text
    assert "## Ordered Recovery Path" in text
    assert "agentic-workspace status --target ./repo" in text
    assert "agentic-workspace doctor --target ./repo" in text
    assert "uv run agentic-planning-bootstrap upgrade --target ." in text
    assert ".agentic-workspace/bootstrap-handoff.md" in text
    assert Path("docs/environment-recovery-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_planning_readme_and_bootstrap_agents_describe_required_follow_on_routing() -> None:
    readme_text = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    bootstrap_agents_text = (installer_mod.payload_root() / "AGENTS.md").read_text(encoding="utf-8")
    execplans_readme_text = (installer_mod.payload_root() / "docs" / "execplans" / "README.md").read_text(encoding="utf-8")
    manifest_payload = json.loads(
        (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "agent-manifest.json").read_text(encoding="utf-8")
    )
    quickstart_text = render_module.render_quickstart(manifest_payload)

    assert "Execplans now treat three fields as first-class" in readme_text
    assert "clear the matched queue residue in the same pass" in readme_text
    assert "`Required Continuation`" in readme_text
    assert "`Execution Summary`" in readme_text
    assert "Required continuation for an unfinished larger intended outcome" in readme_text
    assert "the execplan must record both `Intent Continuity` and `Required Continuation` before archive" in bootstrap_agents_text
    assert "remove or archive the matched planning residue in the same pass" in bootstrap_agents_text
    assert "record the required next owner and activation trigger explicitly before archive" in bootstrap_agents_text
    assert "remove or archive the matched queue residue in the same pass" in execplans_readme_text
    assert any(
        "prefer `agentic-workspace defaults --format json`, then use `llms.txt` or `AGENTS.md` when those surfaces are present" in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any("clear the matched queue residue in the same pass" in item for item in manifest_payload["bootstrap"]["completion_reminders"])
    assert "agentic-workspace defaults --format json" in quickstart_text
    assert "clear the matched queue residue in the same pass" in quickstart_text


def test_bootstrap_execplan_readme_includes_memory_synergy_guidance() -> None:
    text = (installer_mod.payload_root() / "docs" / "execplans" / "README.md").read_text(encoding="utf-8")

    assert "prefer borrowing durable context from the smallest relevant memory note or canonical doc" in text
    assert "Repeated background prose in plans is a missing-synergy signal" in text
    assert "promote it into memory or canonical docs" in text
    assert "must not silently widen the requested outcome" in text
    assert "Continuation surface" in text
    assert "larger intended outcome" in text
    assert "Required follow-on for the larger intended outcome" in text
    assert "Activation trigger" in text
    assert "## Delegated Judgment" in text
    assert "Requested outcome" in text
    assert "Agent may decide locally" in text
    assert "## Execution Summary" in text
    assert "Outcome delivered" in text


def test_bootstrap_execution_summary_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / "docs" / "execution-summary-contract.md").read_text(encoding="utf-8")

    assert "# Execution Summary Contract" in text
    assert "## Canonical Shape" in text
    assert "Outcome delivered" in text
    assert "Validation confirmed" in text
    assert "Follow-on routed to" in text
    assert "Resume from" in text
    assert Path("docs/execution-summary-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_bootstrap_intent_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / "docs" / "intent-contract.md").read_text(encoding="utf-8")

    assert "active_contract" in text
    assert "agentic-planning-bootstrap summary --format json" in text
    assert Path("docs/intent-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_doctor_reports_contract_surface_shortlists(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert any(
        action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        and action.kind == "current"
        and "compatibility contract files:" in action.detail
        and "AGENTS.md" in action.detail
        and "docs/capability-aware-execution.md" in action.detail
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


def test_doctor_ignores_generic_repo_readme_without_startup_claims(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("planning proof repo\n", encoding="utf-8")
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert not any(action.path == tmp_path / "README.md" and "agent-startup guidance" in action.detail for action in result.actions)


def test_doctor_flags_partial_readme_startup_guidance(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    (tmp_path / "README.md").write_text(
        "# Repo\n\nFor agent maintainers, the primary operating path is `AGENTS.md`.\n",
        encoding="utf-8",
    )

    result = doctor_bootstrap(target=tmp_path)

    assert any(action.path == tmp_path / "README.md" and "agent-startup guidance" in action.detail for action in result.actions)


def test_doctor_does_not_flag_starter_todo_for_milestone_word_in_hygiene_rules(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert not any(action.path == tmp_path / "TODO.md" and "milestone-level narrative" in action.detail for action in result.actions)


def test_verify_payload_flags_missing_collaboration_safe_template_guidance(tmp_path: Path, monkeypatch) -> None:
    payload_root = tmp_path / "payload"
    _write(payload_root / "AGENTS.md", "# Agent Instructions\n")
    _write(payload_root / "TODO.md", "# TODO\n")
    _write(payload_root / "ROADMAP.md", "# Roadmap\n")
    _write(payload_root / "docs" / "execplans" / "README.md", "# Execution Plans\n")
    _write(payload_root / "docs" / "execplans" / "TEMPLATE.md", "# Plan Title\n")
    _write(payload_root / "docs" / "execplans" / "archive" / "README.md", "# Archive\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml", 'source_type = "git"\n')
    _write(payload_root / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}\n")
    _write(
        payload_root / ".agentic-workspace" / "planning" / "scripts" / "render_agent_docs.py",
        (
            "def render_quickstart(_manifest):\n"
            '    return "generated file\\n"\n\n'
            "def render_routing(_manifest):\n"
            '    return "generated file\\n"\n'
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
    plan_text = plan_path.read_text(encoding="utf-8")
    todo_text = (tmp_path / "TODO.md").read_text(encoding="utf-8")
    assert "## Intent Continuity" in plan_text
    assert "## Required Continuation" in plan_text
    assert "## Delegated Judgment" in plan_text
    assert "- This slice completes the larger intended outcome: yes" in plan_text
    assert "- Continuation surface: none" in plan_text
    assert "- Required follow-on for the larger intended outcome: no" in plan_text
    assert "- Requested outcome: this thread needs a bounded execution contract." in plan_text
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


def test_archive_execplan_blocks_unfinished_larger_intent_without_continuation_surface(tmp_path: Path) -> None:
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / "docs" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "- This slice completes the larger intended outcome: yes", "- This slice completes the larger intended outcome: no"
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_intent_continuity" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Continuation surface" in action.detail for action in result.actions
    )


def test_archive_execplan_blocks_missing_required_follow_on_when_parent_intent_is_unfinished(tmp_path: Path) -> None:
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / "docs" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- This slice completes the larger intended outcome: yes", "- This slice completes the larger intended outcome: no")
        .replace("- Continuation surface: none", "- Continuation surface: `ROADMAP.md` candidate `next-slice`"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_required_follow_on" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Required Continuation" in action.detail
        for action in result.actions
    )


def test_archive_execplan_blocks_missing_execution_summary(tmp_path: Path) -> None:
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / "docs" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "- Outcome delivered: Added one bounded planning improvement.",
            "- Outcome delivered: not completed yet",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_execution_summary" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Execution Summary" in action.detail for action in result.actions
    )


def test_archive_execplan_blocks_missing_delegated_judgment(tmp_path: Path) -> None:
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / "docs" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "## Delegated Judgment\n\n"
            "- Requested outcome: Keep scope clear.\n"
            "- Hard constraints: Keep scope bounded to the promoted TODO item and its touched paths.\n"
            "- Agent may decide locally: Bounded decomposition, validation tightening, and plan-local residue routing.\n"
            "- Escalate when: The requested outcome, owned surface, time horizon, or meaningful validation story would change.\n\n",
            "",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_delegated_judgment" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Delegated Judgment" in action.detail for action in result.actions
    )


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


def test_archive_execplan_apply_cleanup_removes_active_todo_pointer_to_same_plan(tmp_path: Path) -> None:
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Now

- ID: bounded-delegated-judgment-contract
  Status: in-progress
  Surface: docs/execplans/bounded-delegated-judgment-contract-2026-04-09.md
  Why now: finish the bounded contract update.

## Action

- Complete `bounded-delegated-judgment-contract`, then archive it and return the active queue to empty.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / "docs" / "execplans" / "bounded-delegated-judgment-contract-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "bounded-delegated-judgment-contract"))

    result = archive_execplan("bounded-delegated-judgment-contract-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / "TODO.md").read_text(encoding="utf-8")
    assert "Surface: docs/execplans/bounded-delegated-judgment-contract-2026-04-09.md" not in todo_text
    assert "- No active work right now." in todo_text
    assert (
        "Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation."
        in todo_text
    )
    assert any(
        action.kind == "updated"
        and action.path == tmp_path / "TODO.md"
        and "remove TODO item 'bounded-delegated-judgment-contract'" in action.detail
        for action in result.actions
    )
    assert (tmp_path / "docs" / "execplans" / "archive" / "bounded-delegated-judgment-contract-2026-04-09.md").exists()


def test_archive_execplan_apply_cleanup_handles_active_todo_without_blank_before_action_heading(tmp_path: Path) -> None:
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Now

- ID: intent-continuity-across-slices
  Status: in-progress
  Surface: docs/execplans/intent-continuity-across-slices-2026-04-09.md
  Why now: keep larger intent alive across bounded slices.
## Action

- Complete `intent-continuity-across-slices`, then archive it and return the active queue to empty.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / "docs" / "execplans" / "intent-continuity-across-slices-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "intent-continuity-across-slices"))

    archive_execplan("intent-continuity-across-slices-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / "TODO.md").read_text(encoding="utf-8")
    assert "## Action" in todo_text
    assert "- No active work right now." in todo_text
    assert "Complete `intent-continuity-across-slices`" not in todo_text


def test_archive_execplan_apply_cleanup_updates_compact_now_todo_shape(tmp_path: Path) -> None:
    _write(
        tmp_path / "TODO.md",
        """
# TODO

## Purpose

Active queue for repository work.

## Now
- front-door-defaults-tranche: Active - compress front-door docs and land the defaults contract.

## Action
- Execute `docs/execplans/front-door-defaults-tranche-2026-04-09.md` and archive it once validation is complete.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / "docs" / "execplans" / "front-door-defaults-tranche-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "front-door-defaults-tranche"))

    result = archive_execplan("front-door-defaults-tranche-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / "TODO.md").read_text(encoding="utf-8")
    assert "front-door-defaults-tranche: Active" not in todo_text
    assert "docs/execplans/front-door-defaults-tranche-2026-04-09.md" not in todo_text
    assert "- No active work right now." in todo_text
    assert (
        "Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation."
        in todo_text
    )
    assert any(action.kind == "updated" and action.path == tmp_path / "TODO.md" for action in result.actions)


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


def test_archive_execplan_preserves_explicit_roadmap_continuation_candidate(tmp_path: Path) -> None:
    _write(tmp_path / "TODO.md", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Intent continuity follow-through: promote when another larger user outcome
    needs multiple bounded slices so Planning can preserve unfinished parent
    intent across archival without re-explaining the purpose in chat.
""",
    )
    plan_path = tmp_path / "docs" / "execplans" / "intent-continuity-across-slices-2026-04-09.md"
    plan_text = (
        _minimal_execplan(status="completed")
        .replace("plan-alpha", "intent-continuity-across-slices")
        .replace(
            "- Continuation surface: none",
            "- Continuation surface: `ROADMAP.md` candidate `Intent continuity follow-through`",
        )
        .replace(
            "- This slice completes the larger intended outcome: yes",
            "- This slice completes the larger intended outcome: no",
        )
    )
    _write(plan_path, plan_text)

    archive_execplan("intent-continuity-across-slices-2026-04-09", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Intent continuity follow-through:" in roadmap_text


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
    assert summary["active_contract"]["status"] == "present"
    assert summary["active_contract"]["todo_item"]["id"] == "plan-alpha"
    assert summary["active_contract"]["intent"]["requested_outcome"] == "Keep scope clear."
    assert summary["active_contract"]["proof_expectations"] == ["uv run pytest tests/test_check_planning_surfaces.py"]
    assert summary["active_contract"]["touched_scope"] == ["scripts/check/check_planning_surfaces.py"]
    assert summary["active_contract"]["minimal_refs"] == ["TODO.md", "docs/execplans/plan-alpha.md"]
    assert summary["roadmap"]["candidate_count"] == 1
    assert summary["warning_count"] == 0


def test_planning_summary_can_expose_active_contract_from_execplan_without_todo_row(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / "TODO.md", "# TODO\n\n## Now\n\n- Active execplan: docs/execplans/plan-alpha.md\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / "docs" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)

    assert summary["todo"]["active_count"] == 0
    assert summary["execplans"]["active_count"] == 1
    assert summary["active_contract"]["status"] == "present"
    assert summary["active_contract"]["todo_item"]["id"] == ""
    assert summary["active_contract"]["minimal_refs"] == ["TODO.md", "docs/execplans/plan-alpha.md"]
