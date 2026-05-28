from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *


def test_doctor_ignores_nested_repositories_inside_uv_caches(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / ".uv-cache" / "sdists-v9" / "pkg" / ".git").mkdir(parents=True)
    (target / "vendor" / "nested" / ".git").mkdir(parents=True)

    result = installer.doctor_bootstrap(target=target)

    nested_warnings = [
        action.path.relative_to(target).as_posix()
        for action in result.actions
        if action.detail == "nested repository detected under target; installer will not recurse into repo roots automatically"
    ]
    assert ".uv-cache/sdists-v9/pkg" not in nested_warnings
    assert nested_warnings == ["vendor/nested"]


def test_doctor_does_not_warn_about_parent_repo_for_explicit_git_root(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    target = parent / "repo"
    (parent / ".git").mkdir(parents=True)
    (target / ".git").mkdir(parents=True)

    result = installer.doctor_bootstrap(target=target)

    assert not any(action.detail.startswith("target is inside parent repository") for action in result.actions)


def test_doctor_warns_about_parent_repo_when_target_has_no_git_boundary(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    target = parent / "repo"
    (parent / ".git").mkdir(parents=True)
    target.mkdir(parents=True)

    result = installer.doctor_bootstrap(target=target)

    assert any(action.detail.startswith("target is inside parent repository") for action in result.actions)


def test_doctor_flags_agents_that_embed_current_shared_workflow_sections(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text(
        "# Agent Instructions\n\n"
        f"{installer.WORKFLOW_POINTER_BLOCK}\n\n"
        "## Overview file\n"
        "- copied shared rule\n\n"
        "## Task-context file\n"
        "- copied shared rule\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 8\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "AGENTS.md" and action.kind == "manual review" and "embeds shared workflow rules" in action.detail
        for action in result.actions
    )


def test_doctor_reports_customised_seed_notes_as_expected_customisation(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
    note_path.write_text("# Project State\n\nlocalised\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(action.path == note_path and action.role == "current-memory-migration" for action in result.actions)


def test_doctor_overlap_audit_ignores_generic_ownership_terms(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    domain_path = target / ".agentic-workspace" / "memory" / "repo" / "domains" / "ownership-domain.md"
    decision_path = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "ownership-decision.md"
    domain_path.write_text(
        (
            "# Ownership Domain\n\n"
            "ownership boundaries install installed root package packages workflow managed explicit contract "
            "consolidation lifecycle files read durable memory-only adapter\n"
        ),
        encoding="utf-8",
    )
    decision_path.write_text(
        (
            "# Ownership Decision\n\n"
            "ownership boundaries install installed root package packages workflow managed explicit contract "
            "consolidation lifecycle files read durable decision-specific ledger\n"
        ),
        encoding="utf-8",
    )

    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text += (
        '\n[notes.".agentic-workspace/memory/repo/domains/ownership-domain.md"]\n'
        'note_type = "domain"\n'
        'canonical_home = ".agentic-workspace/memory/repo/domains/ownership-domain.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["ownership"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["AGENTS.md"]\n'
        'stale_when = ["AGENTS.md"]\n'
        '\n[notes.".agentic-workspace/memory/repo/decisions/ownership-decision.md"]\n'
        'note_type = "decision"\n'
        'canonical_home = ".agentic-workspace/memory/repo/decisions/ownership-decision.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["ownership"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["AGENTS.md"]\n'
        'stale_when = ["AGENTS.md"]\n'
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit" and action.path in {domain_path, decision_path} and "ownership-decision.md" in action.detail
        for action in result.actions
    )


def test_doctor_overlap_audit_skips_explicit_primary_home_references(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    domain_path = target / ".agentic-workspace" / "memory" / "repo" / "domains" / "package-context.md"
    decision_path = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "package-context-decision.md"
    domain_path.write_text(
        (
            "# Package Context\n\n"
            "Package boundary context lives here.\n\n"
            "For the owning rationale, load `.agentic-workspace/memory/repo/decisions/package-context-decision.md` instead of expanding this note.\n"
        ),
        encoding="utf-8",
    )
    decision_path.write_text(
        ("# Package Context Decision\n\nThis note keeps the durable decision about the package boundary.\n"),
        encoding="utf-8",
    )

    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text += (
        '\n[notes.".agentic-workspace/memory/repo/domains/package-context.md"]\n'
        'note_type = "domain"\n'
        'canonical_home = ".agentic-workspace/memory/repo/domains/package-context.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["packages"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["packages/**"]\n'
        'stale_when = ["packages/**"]\n'
        '\n[notes.".agentic-workspace/memory/repo/decisions/package-context-decision.md"]\n'
        'note_type = "decision"\n'
        'canonical_home = ".agentic-workspace/memory/repo/decisions/package-context-decision.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["packages"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["packages/**"]\n'
        'stale_when = ["packages/**"]\n'
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path in {domain_path, decision_path}
        and "package-context-decision.md" in action.detail
        for action in result.actions
    )


def test_doctor_overlap_audit_requires_shared_title_terms_for_decision_family_pairs(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    installed_path = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "installed-system.md"
    foundation_path = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "foundation-stability.md"
    shared_text = (
        "operational orchestration planning root-owned installs validation lifecycle boundaries adopted packages "
        "managed workspace authority consolidation checks\n"
    )
    installed_path.write_text("# Root-Owned Installed Systems\n\n" + shared_text, encoding="utf-8")
    foundation_path.write_text("# Repository Foundation Stability\n\n" + shared_text, encoding="utf-8")

    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text += (
        '\n[notes.".agentic-workspace/memory/repo/decisions/installed-system.md"]\n'
        'note_type = "decision"\n'
        'canonical_home = ".agentic-workspace/memory/repo/decisions/installed-system.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["orchestration"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["AGENTS.md"]\n'
        'stale_when = ["AGENTS.md"]\n'
        '\n[notes.".agentic-workspace/memory/repo/decisions/foundation-stability.md"]\n'
        'note_type = "decision"\n'
        'canonical_home = ".agentic-workspace/memory/repo/decisions/foundation-stability.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["orchestration"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["AGENTS.md"]\n'
        'stale_when = ["AGENTS.md"]\n'
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path in {installed_path, foundation_path}
        and "foundation-stability.md" in action.detail
        for action in result.actions
    )


def test_doctor_overlap_audit_skips_distinct_package_context_notes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "memory-package-context.md").write_text(
        "# Memory Package Context\n\nMemory package authority lives in packages/memory/src and packages/memory/tests.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "planning-package-context.md").write_text(
        "# Planning Package Context\n\nPlanning package authority lives in packages/planning/src and packages/planning/tests.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/memory-package-context.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/memory-package-context.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["architecture"]
routes_from = ["packages/memory/**"]

[notes.".agentic-workspace/memory/repo/domains/planning-package-context.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/planning-package-context.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["architecture"]
routes_from = ["packages/planning/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "memory-package-context.md"
        and "planning-package-context.md" in action.detail
        for action in result.actions
    )


def test_doctor_overlap_audit_skips_package_context_companion_runbook(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "memory-package-context.md").write_text(
        "# Memory Package Context\n\nUse the companion skill for the checklist.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "package-context-inspection.md").write_text(
        "# Package Context Inspection\n\nUse the skill for execution.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/memory-package-context.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/memory-package-context.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["architecture"]
routes_from = ["packages/memory/**"]

[notes.".agentic-workspace/memory/repo/runbooks/package-context-inspection.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/package-context-inspection.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["runtime"]
routes_from = ["packages/memory/**", "packages/planning/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "memory-package-context.md"
        and "package-context-inspection.md" in action.detail
        for action in result.actions
    )


def test_doctor_reports_stale_upgrade_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").write_text(
        (
            'source_type = "git"\n'
            f'source_ref = "{MEMORY_GIT_SOURCE_REF}"\n'
            'source_label = "agentic-memory main"\n'
            'recorded_at = "2025-01-01"\n'
            "recommended_upgrade_after_days = 30\n"
        ),
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "warning"
        and "consider refreshing `.agentic-workspace/memory/UPGRADE-SOURCE.toml`" in action.detail
        for action in result.actions
    )


def test_doctor_reports_contract_surface_shortlists(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
        and action.kind == "current"
        and action.role == "payload-contract"
        and "compatibility contract files:" in action.detail
        and ".agentic-workspace/memory/repo/runbooks/README.md" in action.detail
        and ".agentic-workspace/memory/repo/decisions/README.md" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and action.role == "payload-contract"
        and "lower-stability helper files:" in action.detail
        and ".agentic-workspace/memory/skills/README.md" in action.detail
        and ".agentic-workspace/memory/UPGRADE-SOURCE.toml" in action.detail
        for action in result.actions
    )


def test_doctor_reports_placeholder_review_category(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 8\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").write_text("old workflow\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(action.category == "placeholder-review" for action in result.actions)


def test_doctor_agents_guidance_mentions_apply_local_entrypoint(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 10\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(action.path == target / "AGENTS.md" and "--apply-local-entrypoint" in action.detail for action in result.actions)


def test_doctor_accepts_local_only_agents_indirection(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("Follow instructions in `AGENTS.local.md` if present.\n", encoding="utf-8")
    (target / "AGENTS.local.md").write_text(
        "# Local Agent Instructions\n\n"
        "<!-- agentic-workspace:workflow:start -->\n"
        'Run `agentic-workspace start --task "<task>" --format json` and read `.agentic-workspace/WORKFLOW.md` '
        "only as fallback after `immediate_next_allowed_action`.\n"
        "<!-- agentic-workspace:workflow:end -->\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "LOCAL-ONLY.toml").write_text(
        'schema_version = 1\nmode = "local-only"\nrepo_hook = ".git/info/exclude"\n',
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 10\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "AGENTS.md"
        and action.kind == "current"
        and "local startup indirection points to AGENTS.local.md" in action.detail
        for action in result.actions
    )
    assert not any(action.path == target / "AGENTS.md" and "--apply-local-entrypoint" in action.detail for action in result.actions)


def test_doctor_flags_legacy_bootstrap_agents_prose_outside_managed_block(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        f"{installer.WORKFLOW_POINTER_BLOCK}\n\n"
        "Check `.agentic-workspace/memory/repo/skills/README.md` and the skill directories under `.agentic-workspace/memory/repo/skills/` "
        "for a checked-in memory skill whose name or description matches the task.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace/memory" / "VERSION.md").write_text("Version: 39\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "AGENTS.md"
        and action.kind == "manual review"
        and "older bootstrap prose outside the managed workflow pointer block" in action.detail
        for action in result.actions
    )


def test_doctor_flags_incomplete_durable_fact_records(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8")
        + """

[durable_facts."too-vague"]
summary = ""
owner = ""
authority_class = "policy"
status = "active"
""",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(action.role == "memory-manifest" and "durable_facts.too-vague" in action.detail for action in result.actions)


def test_doctor_emits_improvement_pressure_suggestions_from_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 32\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring failures\n\n- This keeps happening.\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "test"
improvement_candidate = true
elimination_target = "shrink"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md"
        and action.kind == "consider"
        and "regression test" in action.detail
        and action.remediation_kind == "test"
        and action.remediation_target == "tests/test_recurring-failures.py"
        and action.memory_action == "shrink"
        for action in result.actions
    )


def test_doctor_flags_legacy_upgrade_runbook_for_removal(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    legacy = target / ".agentic-workspace" / "memory" / "UPGRADE.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("# legacy\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == legacy and action.kind == "would remove" and action.category == "obsolete-managed-file" for action in result.actions
    )


def test_doctor_audits_routing_feedback_hygiene(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    _write_repo_file(target, ".agentic-workspace/memory/repo/index.md", _memory_index_text())
    filler = "\n".join("- filler" for _ in range(110))
    feedback_text = (
        "# Routing Feedback\n\n"
        "## Status\n\n"
        "Active\n\n"
        "## Scope\n\n"
        "- Oversized routing feedback test.\n\n"
        "## Load when\n\n"
        "- Reviewing calibration cases.\n\n"
        "## Review when\n\n"
        "- Compressing stale cases.\n\n"
        "## Missed-note entries\n\n"
        "### Case: incomplete-a\n"
        "Status\n"
        "- tuned\n\n"
        "### Case: resolved-b\n"
        "Task surface summary\n"
        "- Resolved case.\n"
        "Expected missing note\n"
        "- .agentic-workspace/memory/repo/domains/a.md\n"
        "Status\n"
        "- tuned\n\n"
        "### Case: resolved-c\n"
        "Task surface summary\n"
        "- Resolved case.\n"
        "Expected missing note\n"
        "- .agentic-workspace/memory/repo/domains/b.md\n"
        "Status\n"
        "- rejected\n\n"
        "### Case: resolved-d\n"
        "Task surface summary\n"
        "- Resolved case.\n"
        "Expected missing note\n"
        "- .agentic-workspace/memory/repo/domains/c.md\n"
        "Status\n"
        "- rejected\n\n"
        "## Over-routing entries\n\n"
        "## Synthesis\n\n"
        f"{filler}\n"
    )
    _write_repo_file(target, ".agentic-workspace/memory/repo/current/routing-feedback.md", feedback_text)

    result = installer.doctor_bootstrap(target=target)
    details = [
        action.detail for action in result.actions if action.path == target / ".agentic-workspace/memory/repo/current/routing-feedback.md"
    ]

    assert any("missing Last confirmed" in detail for detail in details)
    assert any("routing-feedback note is oversized" in detail for detail in details)
    assert any("too many resolved entries" in detail for detail in details)
    assert any("missing task surface summary" in detail for detail in details)
    assert any("missing expected missing/unexpected note entries" in detail for detail in details)


def test_doctor_audit_flags_core_docs_that_depend_on_memory_when_policy_enabled(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
forbid_core_docs_depend_on_memory = true
core_doc_globs = ["README.md", "docs/**/*.md"]
core_doc_exclude_globs = [".agentic-workspace/memory/repo/**/*.md", "AGENTS.md"]

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        "See `.agentic-workspace/memory/repo/runbooks/deploy.md` for the stable deployment procedure.\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "README.md" and action.kind == "manual review" and "core doc depends on memory" in action.detail
        for action in result.actions
    )


def test_doctor_strict_doc_ownership_forces_audit_without_manifest_opt_in(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
core_doc_globs = ["README.md"]
core_doc_exclude_globs = [".agentic-workspace/memory/repo/**/*.md", "AGENTS.md"]
forbid_core_docs_depend_on_memory = false

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text("See .agentic-workspace/memory/repo/runbooks/deploy.md for deployment steps.\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target, strict_doc_ownership=True)

    assert any(action.path == target / "README.md" and "core doc depends on memory" in action.detail for action in result.actions)


def test_doctor_validates_manifest_canonicality_values(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "wrong"
task_relevance = "sometimes"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and "manifest canonicality must be one of" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and "manifest task_relevance must be required or optional" in action.detail
        for action in result.actions
    )


def test_doctor_validates_optional_improvement_manifest_values(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 33\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "weird"
symptom_of = "bad"
preferred_remediation = "robot"
elimination_target = "gone"
retention_after_promotion = "forever"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("manifest memory_role must be durable_truth or improvement_signal" in action.detail for action in result.actions)
    assert any("manifest symptom_of must be one of" in action.detail for action in result.actions)
    assert any("manifest preferred_remediation must be one of" in action.detail for action in result.actions)
    assert any("manifest elimination_target must be one of" in action.detail for action in result.actions)
    assert any("manifest retention_after_promotion must be one of" in action.detail for action in result.actions)


def test_doctor_reports_invalid_manifest_toml(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1
[notes.".agentic-workspace/memory/repo/domains/api.md"
note_type = "domain"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(action.role == "memory-manifest" and "manifest TOML parse error" in action.detail for action in result.actions)


def test_doctor_reports_manifest_shape_drift(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text("# API\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = "1"

[rules]
routing_only = ".agentic-workspace/memory/repo/index.md"
forbid_core_docs_depend_on_memory = "yes"

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
routes_from = "README.md"
use_when = "touching API code"
evidence = "README.md"
retention_after_promotion = ""
improvement_candidate = "true"

[notes.".agentic-workspace/memory/repo/domains/missing-fields.md"]
routes_from = ["README.md"]

[durable_facts."memory-owner-boundary"]
summary = "Memory owns durable facts."
owner = "memory"
authority_class = "canonical"
route_keys = "memory"
evidence = "README.md"
promotion = "Promote if useful."
demotion_or_expiry = "Demote if stale."
status = "active"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)
    details = [action.detail for action in result.actions if action.role == "memory-manifest"]

    assert "manifest version must be an integer" in details
    assert "manifest rules.routing_only must be an array of strings" in details
    assert "manifest rules.forbid_core_docs_depend_on_memory must be a boolean" in details
    assert any("routes_from must be an array of strings" in detail for detail in details)
    assert any("use_when must be an array of strings" in detail for detail in details)
    assert any("evidence must be an array of strings" in detail for detail in details)
    assert any("retention_after_promotion must be a non-empty string when present" in detail for detail in details)
    assert any("improvement_candidate must be a boolean" in detail for detail in details)
    assert any("missing-fields.md.note_type must be a non-empty string" in detail for detail in details)
    assert any("missing-fields.md.authority must be a non-empty string" in detail for detail in details)
    assert any("durable_facts.memory-owner-boundary.route_keys must be an array of strings" in detail for detail in details)
    assert any("durable_facts.memory-owner-boundary.evidence must be an array of strings" in detail for detail in details)


def test_doctor_flags_incomplete_improvement_signal_lifecycle(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("preferred_remediation plus improvement_note, or retention_justification" in action.detail for action in result.actions)
    assert any("missing elimination_target" in action.detail for action in result.actions)
    assert any("should declare config_treatment" in action.detail for action in result.actions)
    assert any("should pair config_treatment with config_note" in action.detail for action in result.actions)


def test_doctor_accepts_retention_justification_for_improvement_signal(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
retention_justification = "The repo still lacks an executable replacement for this recurring operator trap."
elimination_target = "shrink"
config_treatment = "retain"
config_note = "Current config does not change the need to keep this trap visible until an executable replacement exists."
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any("retention_justification" in action.detail for action in result.actions)
    assert not any("config_treatment" in action.detail for action in result.actions)


def test_doctor_flags_invalid_config_treatment_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md").write_text(
        "# Recurring Friction Ledger\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "validation"
improvement_note = "Promote repeated friction into stronger remediation."
elimination_target = "promote"
config_treatment = "escalate"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("manifest config_treatment must be one of" in action.detail for action in result.actions)
    assert any("should pair config_treatment with config_note" in action.detail for action in result.actions)


def test_doctor_emits_recurring_friction_promotion_pressure_for_repeated_entry(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 32\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md").write_text(
        """
# Recurring Friction Ledger

## Status

Active

## Scope

- Lightweight recurring friction evidence.

## Load when

- The same friction shows up again.

## Review when

- A friction class is promoted elsewhere.

## Failure signals

- The same friction keeps recurring.

## When to use this

- The signal is real but still below issue threshold.

## Rules

- Keep one entry per friction class.

## Entry format

### Friction: missing-memory-capture

Observed recurrences
- 2026-04-20: Post-task friction was noticed but not captured.
- 2026-04-22: Another task required the same manual rescue.

Keep now
- Two recurrences are enough to preserve, but the exact fix still needs shaping.

Promote when
- The same friction recurs again or a clear package change presents itself.

Most likely remediation
- validation

Config treatment
- promote because current repo posture prefers escalating repeated workflow drift instead of letting it stay note-only evidence.

Last seen
2026-04-22 during issue #263 first slice

## Verification

- Repeated friction can be preserved without opening an issue immediately.

## Boundary reminder

- This note is pre-backlog evidence.

## Last confirmed

2026-04-22 during issue #263 first slice
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "validation"
improvement_candidate = true
improvement_note = "Promote repeated friction into stronger remediation."
elimination_target = "promote"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md"
        and action.role == "recurring-friction-audit"
        and action.kind == "consider"
        and "has 2 observed recurrences" in action.detail
        for action in result.actions
    )


def test_doctor_flags_missing_config_treatment_in_recurring_friction_entry(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 32\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md").write_text(
        """
# Recurring Friction Ledger

## Status

Active

## Scope

- Lightweight recurring friction evidence.

## Load when

- The same friction shows up again.

## Review when

- A friction class is promoted elsewhere.

## Failure signals

- The same friction keeps recurring.

## When to use this

- The signal is real but still below issue threshold.

## Rules

- Keep one entry per friction class.

## Entry format

### Friction: missing-memory-capture

Observed recurrences
- 2026-04-20: Post-task friction was noticed but not captured.

Keep now
- One recurrence is enough to preserve while the exact remediation is still forming.

Promote when
- The same friction recurs again or a clear package change presents itself.

Most likely remediation
- validation

Last seen
2026-04-22 during issue #263 second slice

## Verification

- Repeated friction can be preserved without opening an issue immediately.

## Boundary reminder

- This note is pre-backlog evidence.

## Last confirmed

2026-04-22 during issue #263 second slice
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "validation"
improvement_candidate = true
improvement_note = "Promote repeated friction into stronger remediation."
elimination_target = "promote"
config_treatment = "promote"
config_note = "Current repo posture prefers escalating repeated workflow drift."
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("missing Config treatment" in action.detail for action in result.actions)


def test_doctor_flags_manifest_routing_drift_for_small_default_surface(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
routing_only = [".agentic-workspace/memory/repo/index.md", ".agentic-workspace/memory/WORKFLOW.md"]
high_level = [".agentic-workspace/memory/repo/index.md", ".agentic-workspace/memory/repo/current/task-context.md"]

[notes.".agentic-workspace/memory/WORKFLOW.md"]
note_type = "workflow-policy"
canonical_home = ".agentic-workspace/memory/WORKFLOW.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"

[notes.".agentic-workspace/memory/repo/current/task-context.md"]
note_type = "current-context"
canonical_home = ".agentic-workspace/memory/repo/current/task-context.md"
authority = "canonical"
audience = "agent"
canonicality = "agent_only"
task_relevance = "required"
surfaces = ["api"]
routes_from = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)
    details = [action.detail for action in result.actions]

    assert any("rules.routing_only should contain only .agentic-workspace/memory/repo/index.md" in detail for detail in details)
    assert any("rules.high_level should not include .agentic-workspace/memory/repo/current/task-context.md" in detail for detail in details)
    assert any("WORKFLOW.md should remain reference policy" in detail for detail in details)
    assert any("task-context should stay optional continuation compression" in detail for detail in details)
    assert any("task-context should not advertise broad routing metadata" in detail for detail in details)


def test_doctor_flags_task_board_dependence_outside_current_notes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text("# API\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
task_board_globs = ["TODO.md"]

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
routes_from = ["TODO.md"]
stale_when = ["TODO.md"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("task-board globs should not drive durable memory routing" in action.detail for action in result.actions)


def test_doctor_flags_canonical_dir_and_note_type_drift(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "misc").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "misc" / "api.md").write_text("# API\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "wrong.md").write_text("# Wrong\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
canonical_dirs = [".agentic-workspace/memory/repo/domains", ".agentic-workspace/memory/repo/invariants", ".agentic-workspace/memory/repo/runbooks", ".agentic-workspace/memory/repo/mistakes", ".agentic-workspace/memory/repo/decisions"]

[notes.".agentic-workspace/memory/repo/domains/wrong.md"]
note_type = "invariant"
canonical_home = ".agentic-workspace/memory/repo/domains/wrong.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"

[notes."memory/misc/api.md"]
note_type = "invariant"
canonical_home = "memory/misc/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("durable memory notes should live under rules.canonical_dirs" in action.detail for action in result.actions)
    assert any(
        "notes under .agentic-workspace/memory/repo/domains/ should keep note_type = domain" in action.detail for action in result.actions
    )


def test_doctor_enforces_routing_feedback_as_calibration_only(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md").write_text(
        """# Routing Feedback

## Status

Active

## Scope

- Calibration only.

## Load when

- Reviewing routing.

## Review when

- Routes change.

## Missed-note entries

## Over-routing entries

## Synthesis

- Keep this compact.

## Last confirmed

2026-04-05
""",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/current/routing-feedback.md"]
note_type = "routing-feedback"
canonical_home = "docs/routing.md"
authority = "canonical"
audience = "agent"
canonicality = "candidate_for_promotion"
task_relevance = "required"
memory_role = "durable_truth"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)
    details = [
        action.detail for action in result.actions if action.path == target / ".agentic-workspace/memory/repo/current/routing-feedback.md"
    ]

    assert any("routing-feedback should stay optional calibration context" in detail for detail in details)
    assert any("routing-feedback should stay agent_only calibration context" in detail for detail in details)
    assert any("routing-feedback should stay calibration-only" in detail for detail in details)
    assert any("should not advertise broad routing or freshness metadata" in detail for detail in details)


def test_doctor_flags_current_note_authority_and_memory_role_drift(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text(
        """
# Project State

## Status

Active

## Scope

- Overview only.

## Applies to

- README.md

## Load when

- Starting work.

## Review when

- Focus changes.

## Current focus

- Short summary.

## Recent meaningful progress

- None yet.

## Blockers

- None.

## High-level notes

- Keep brief.

## Failure signals

- Drift.

## Verify

- Check current state.

## Verified against

- README.md

## Last confirmed

2026-04-06
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/current/project-state.md"]
note_type = "current-overview"
canonical_home = ".agentic-workspace/memory/repo/current/project-state.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "durable_truth"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)
    details = [
        action.detail for action in result.actions if action.path == target / ".agentic-workspace/memory/repo/current/project-state.md"
    ]

    assert any("weak-authority context" in detail for detail in details)
    assert any("should not declare durable-truth or improvement-signal memory roles" in detail for detail in details)


def test_doctor_emits_note_type_specific_size_warning(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "invariants").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "invariants" / "api.md").write_text(
        ("# API invariant\n\n" + "detail\n") * 90, encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/invariants/api.md"]
note_type = "invariant"
canonical_home = ".agentic-workspace/memory/repo/invariants/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.role == "memory-size-audit" and "invariant note is oversized" in action.detail and "expected <= 80" in action.detail
        for action in result.actions
    )


def test_doctor_emits_note_lifecycle_pressure_for_promotion_candidate(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(
        "# API\n\n" + ("Stable guidance.\n" * 45), encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = "docs/api.md"
authority = "advisory"
audience = "human+agent"
canonicality = "candidate_for_promotion"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.role == "memory-lifecycle"
        and action.path == target / ".agentic-workspace/memory/repo/domains/api.md"
        and "move canonical guidance into docs/api.md" in action.detail
        and "short stub" in action.detail
        for action in result.actions
    )


def test_doctor_emits_multi_home_pressure_for_procedural_domain_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(
        "# API\n\n" + "\n".join(f"{idx}. Run `cmd {idx}` and verify output." for idx in range(1, 8)),
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.role == "memory-multi-home"
        and action.path == target / ".agentic-workspace/memory/repo/domains/api.md"
        and ".agentic-workspace/memory/repo/skills/api/SKILL.md" in action.detail
        for action in result.actions
    )


def test_doctor_ignores_standard_metadata_sections_when_counting_domain_procedure(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(
        """# API

## Purpose

Durable package boundary.

## Durable boundaries

- API package authority lives in `packages/api/src/`.
- Tests live in `packages/api/tests/`.

## Companion skill

Use `.agentic-workspace/memory/repo/skills/api/SKILL.md`.

## Verify

- `packages/api/src/`
- `packages/api/tests/`
""",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-multi-home" and action.path == target / ".agentic-workspace/memory/repo/domains/api.md"
        for action in result.actions
    )


def test_doctor_emits_multi_home_pressure_for_invariant_heavy_runbook(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "release.md").write_text(
        "# Release\n\n" + "\n".join("The service must remain compatible and must never skip validation." for _ in range(8)),
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/release.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/release.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.role == "memory-multi-home"
        and action.path == target / ".agentic-workspace/memory/repo/runbooks/release.md"
        and ".agentic-workspace/memory/repo/invariants/release.md" in action.detail
        for action in result.actions
    )


def test_doctor_rejects_canonical_elsewhere_targets_inside_memory(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/invariants/api.md"
authority = "advisory"
audience = "human+agent"
canonicality = "canonical_elsewhere"
task_relevance = "optional"
surfaces = ["api"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    doctor = installer.doctor_bootstrap(target=target)
    routed = installer.route_memory(target=target, surfaces=["api"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and "canonical_elsewhere notes must point canonical_home" in action.detail
        for action in doctor.actions
    )
    assert not any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "invariants" / "api.md" and action.kind == "required"
        for action in routed.actions
    )


def test_doctor_emits_advisory_note_overlap_warning(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "invariants").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    shared_text = (
        "service contract boundary request validation response schema compatibility migration rollback observability operator safety\n"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(shared_text, encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "invariants" / "api.md").write_text(shared_text, encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["api"]
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/invariants/api.md"]
note_type = "invariant"
canonical_home = ".agentic-workspace/memory/repo/invariants/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["api"]
routes_from = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.role == "memory-overlap-audit" and "possible note overlap" in action.detail and "recommend" in action.detail
        for action in result.actions
    )


def test_doctor_does_not_flag_wishlist_style_note_overlap_from_template_language(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "decisions").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "wishlist.md").write_text(
        """# Wishlist

## Status

Active

## Scope

- Product wishlist note.

## Applies to

- `AGENTS.md`

## Review when

- Changes are implemented.

## Failure signals

- Product feedback is not captured.

## Rule or lesson

- Keep this note focused on improvements and verified lessons.

## Last confirmed

2026-04-05
""",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        """# Recurring Failures

## Status

Active

## Scope

- Mistakes note.

## Applies to

- `AGENTS.md`

## Review when

- Behaviour changes.

## Failure signals

- Check current failure modes.

## Rule or lesson

- Keep this note focused on repeated failures and verified fixes.

## Last confirmed

2026-04-05
""",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/decisions/wishlist.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/wishlist.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["memory-system"]

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["memory-system"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path == target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "wishlist.md"
        for action in result.actions
    )


def test_doctor_shadow_doc_detection_flags_overlap(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    shared_text = (
        "deployment rollback procedure staging production release verification service health incident operator checklist observability\n"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md").write_text(shared_text, encoding="utf-8")
    (target / "docs" / "deploy.md").write_text(shared_text, encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
forbid_core_docs_depend_on_memory = true
core_doc_globs = ["docs/**/*.md"]
core_doc_exclude_globs = [".agentic-workspace/memory/repo/**/*.md", "AGENTS.md"]

[notes.".agentic-workspace/memory/repo/domains/deploy.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/deploy.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md"
        and action.role == "shadow-doc-audit"
        and "shadow-doc overlap" in action.detail
        for action in result.actions
    )
