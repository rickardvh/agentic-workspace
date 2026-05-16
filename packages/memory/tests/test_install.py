from __future__ import annotations

import json
import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

from jsonschema import Draft202012Validator

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *


def test_ownership_module_root_matches_workspace_ledger() -> None:
    assert memory_module_root("memory") == Path(".agentic-workspace/memory")


def test_memory_contract_file_shortlist_is_explicit() -> None:
    assert Path("AGENTS.md") in MEMORY_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/memory/repo/index.md") in MEMORY_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/memory/repo/manifest.toml") in MEMORY_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/memory/UPGRADE-SOURCE.toml") in MEMORY_LOWER_STABILITY_HELPER_FILES
    assert Path(".agentic-workspace/memory/bootstrap/README.md") in MEMORY_LOWER_STABILITY_HELPER_FILES
    assert set(MEMORY_COMPATIBILITY_CONTRACT_FILES).isdisjoint(MEMORY_LOWER_STABILITY_HELPER_FILES)
    assert set(MEMORY_COMPATIBILITY_CONTRACT_FILES) | set(MEMORY_LOWER_STABILITY_HELPER_FILES) == set(PAYLOAD_REQUIRED_FILES)


def test_detect_install_mode_is_full_without_todo_file(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)

    assert installer.detect_install_mode(tmp_path) == "full"


def test_payload_entries_do_not_include_todo_stub() -> None:
    entries = installer._payload_entries(installer.payload_root())

    assert all(entry.relative_path != Path("TODO.md") for entry in entries)
    assert all(".agent-work" not in entry.relative_path.as_posix() for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/repo/current/active-decisions.md") for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/repo/current/project-state.md") for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/repo/current/task-context.md") for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/repo/current/routing-feedback.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/repo/manifest.toml") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/SKILLS.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/UPGRADE-SOURCE.toml") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/bootstrap/README.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/bootstrap/skills/install/SKILL.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/skills/memory-router/SKILL.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/skills/memory-upgrade/SKILL.md") for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/bootstrap/skills/upgrade/SKILL.md") for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/bootstrap/skills/upgrade/agents/openai.yaml") for entry in entries)


def test_payload_current_files_are_empty_by_default() -> None:
    entries = installer._payload_entries(installer.payload_root())

    current_paths = {
        entry.relative_path.as_posix()
        for entry in entries
        if entry.relative_path.as_posix().startswith(".agentic-workspace/memory/repo/current/")
    }

    assert current_paths == set()


def test_list_bundled_skills_only_includes_bootstrap_skills() -> None:
    result = installer.list_bundled_skills()

    bundled = {action.path.name for action in result.actions if action.kind == "bundled skill"}

    assert bundled == {
        "bootstrap-adoption",
        "bootstrap-upgrade",
        "bootstrap-uninstall",
    }
    assert all(action.detail == "registered packaged product skill" for action in result.actions if action.kind == "bundled skill")


def test_dev_bundled_skills_tree_only_contains_bootstrap_skill_directories() -> None:
    skills_dir = installer.skills_root()

    skill_dirs = {path.name for path in skills_dir.iterdir() if path.is_dir() and (path / "SKILL.md").exists()}

    assert skill_dirs == {
        "bootstrap-adoption",
        "bootstrap-upgrade",
        "bootstrap-uninstall",
    }


def test_extract_make_targets_ignores_assignments_and_recipes() -> None:
    text = """
    .PHONY: lint test
    PYTHON ?= python

    lint test:
    \t$(PYTHON) -m pytest

    check-memory:
    \tuv run agentic-workspace doctor --target . --format json
    \tuv run agentic-workspace report --target . --format json
    """

    assert installer._extract_make_targets(text) == {
        ".PHONY",
        "lint",
        "test",
        "check-memory",
    }


def test_equivalent_optional_fragment_detail_detects_existing_makefile_target() -> None:
    existing = """
    check-memory:
    \tuv run agentic-workspace doctor --target . --format json
    \tuv run agentic-workspace report --target . --format json
    """
    fragment = """
    check-memory:
    \tuv run agentic-workspace doctor --target . --format json
    \tuv run agentic-workspace report --target . --format json
    """

    detail = installer._equivalent_optional_fragment_detail(
        target_file=Path("Makefile"),
        existing=existing,
        fragment=fragment,
    )

    assert detail == "equivalent optional Makefile convenience target already present (check-memory)"


def test_equivalent_optional_fragment_detail_requires_matching_targets() -> None:
    detail = installer._equivalent_optional_fragment_detail(
        target_file=Path("Makefile"),
        existing="lint:\n\tpython -m ruff check .\n",
        fragment="check-memory:\n\tuv run agentic-workspace doctor --target . --format json\n\tuv run agentic-workspace report --target . --format json\n",
    )

    assert detail is None


def test_plan_optional_appends_skips_equivalent_makefile_target(tmp_path: Path) -> None:
    source_root = tmp_path / "payload"
    target_root = tmp_path / "target"
    (source_root / "optional").mkdir(parents=True, exist_ok=True)
    target_root.mkdir()

    fragment = "check-memory:\n\tuv run agentic-workspace doctor --target . --format json\n\tuv run agentic-workspace report --target . --format json\n"
    makefile = fragment

    (source_root / "optional" / "Makefile.fragment.mk").write_text(fragment, encoding="utf-8")
    (source_root / "optional" / "CONTRIBUTING.fragment.md").write_text("Contributing fragment\n", encoding="utf-8")
    (source_root / "optional" / "pull_request_template.fragment.md").write_text("PR fragment\n", encoding="utf-8")
    (target_root / "Makefile").write_text(makefile, encoding="utf-8")

    result = installer.InstallResult(target_root=target_root, dry_run=False)

    installer._plan_optional_appends(
        source_root,
        target_root,
        result,
        apply=True,
    )

    assert (target_root / "Makefile").read_text(encoding="utf-8") == makefile
    makefile_actions = [action for action in result.actions if action.path == target_root / "Makefile"]
    assert makefile_actions == []


def test_install_does_not_duplicate_existing_optional_fragment(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    makefile = target / "Makefile"
    makefile.write_text(
        "check-memory:\n\tuv run agentic-workspace doctor --target . --format json\n\tuv run agentic-workspace report --target . --format json\n",
        encoding="utf-8",
    )

    result = installer.install_bootstrap(target=target, dry_run=True)

    makefile_actions = [action for action in result.actions if action.path == makefile]

    assert makefile_actions == []


def test_direct_memory_install_warns_without_workspace_orchestrator(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.install_bootstrap(target=target)

    assert any(
        action.kind == "warning"
        and action.path == target / ".agentic-workspace" / "WORKFLOW.md"
        and "agentic-workspace init --preset memory" in action.detail
        and "module-level maintenance/debugging" in action.detail
        for action in result.actions
    )


def test_memory_status_warns_without_workspace_orchestrator(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace" / "WORKFLOW.md").unlink(missing_ok=True)

    result = installer.collect_status(target=target)

    assert any(
        action.kind == "warning"
        and action.path == target / ".agentic-workspace" / "WORKFLOW.md"
        and "agentic-workspace init --preset memory" in action.detail
        for action in result.actions
    )


def test_direct_memory_install_skips_orchestrator_warning_when_workspace_present(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "WORKFLOW.md").write_text("Workspace workflow\n", encoding="utf-8")

    result = installer.install_bootstrap(target=target)

    assert not any(action.kind == "warning" and action.path == target / ".agentic-workspace" / "WORKFLOW.md" for action in result.actions)


def test_patch_agents_workflow_block_inserts_pointer_after_heading() -> None:
    existing = "# Agent Instructions\n\nRepo-local rules live here.\n"

    patched = installer._patch_agents_workflow_block(existing)

    assert patched == (f"# Agent Instructions\n\n{installer.WORKFLOW_POINTER_BLOCK}\n\nRepo-local rules live here.\n")


def test_upgrade_replaces_shared_files_without_todo_manual_review(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 7\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").write_text("old workflow\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target)

    assert all(action.path != target / "TODO.md" for action in result.actions)
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "WORKFLOW.md"
        and action.kind == "would replace"
        and "planned change" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "UPGRADE-SOURCE.toml" and action.kind in {"current", "would create"}
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md"
        and action.role == "current-memory-migration"
        for action in result.actions
    )


def test_memory_status_does_not_flag_absent_optional_append_targets_in_clean_repo(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.collect_status(target=target)

    assert not any(action.path == target / "CONTRIBUTING.md" for action in result.actions)
    assert not any(action.path == target / "CONTRIBUTING.md" and action.kind == "missing" for action in result.actions)


def test_upgrade_reports_customised_seed_notes_as_expected_customisation(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
    note_path.write_text("# Project State\n\nlocalised\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target)

    assert any(action.path == note_path and action.role == "current-memory-migration" for action in result.actions)


def test_upgrade_preserves_customised_recurring_friction_ledger(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    ledger_path = target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md"
    ledger_path.write_text(
        """
# Recurring Friction Ledger

## Status

Active

## Scope

- Lightweight evidence for repeated friction.

## Entry format

### Friction: recurring-ledger-preservation

Observed recurrences
- 2026-04-22: Upgrade-safe evidence should not reset to the shipped placeholder.

Keep now
- One recurrence is enough to prove the local signal exists.

Promote when
- A second recurrence or a clear upstream guardrail lands.

Most likely remediation
- validation

Config treatment
- promote because current repo posture prefers keeping repeated friction visible until stronger enforcement lands.

Last seen
2026-04-22 during recurring-friction lane closeout
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.upgrade_bootstrap(target=target)

    assert ledger_path.read_text(encoding="utf-8").startswith("# Recurring Friction Ledger")
    assert "recurring-ledger-preservation" in ledger_path.read_text(encoding="utf-8")
    assert not any(action.path == ledger_path and action.kind in {"removed", "updated", "created"} for action in result.actions)


def test_list_payload_files_excludes_agent_work_templates_and_gitignore_append(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".git").mkdir()

    result = installer.list_payload_files(target=target)

    assert all(action.path != target / ".gitignore" for action in result.actions)
    assert all(".agent-work" not in action.path.as_posix() for action in result.actions)
    assert all(
        action.path != target / ".agentic-workspace" / "memory" / "repo" / "current" / "active-decisions.md" for action in result.actions
    )


def test_install_dry_run_excludes_current_memory_baseline(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.install_bootstrap(target=target, dry_run=True)

    planned_copies = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "would copy"}

    assert ".agentic-workspace/memory/repo/current/project-state.md" not in planned_copies
    assert ".agentic-workspace/memory/repo/current/routing-feedback.md" not in planned_copies
    assert ".agentic-workspace/memory/repo/current/task-context.md" not in planned_copies
    assert ".agentic-workspace/memory/bootstrap/README.md" in planned_copies
    assert ".agentic-workspace/memory/repo/current/active-decisions.md" not in planned_copies


def test_install_does_not_write_current_memory_seed_notes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    for relative in (
        ".agentic-workspace/memory/repo/current/project-state.md",
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        ".agentic-workspace/memory/repo/current/task-context.md",
    ):
        assert not (target / relative).exists()


def test_install_writes_upgrade_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    text = (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").read_text(encoding="utf-8")
    assert 'source_type = "git"' in text
    assert MEMORY_GIT_SOURCE_REF in text
    assert 'source_label = "agentic-memory monorepo master"' in text
    assert 'recorded_at = "2026-05-06"' in text


def test_adopt_writes_upgrade_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)

    installer.adopt_bootstrap(target=target)

    text = (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").read_text(encoding="utf-8")
    assert 'source_type = "git"' in text
    assert MEMORY_GIT_SOURCE_REF in text


def test_resolve_upgrade_source_defaults_to_git_when_metadata_missing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)

    resolved = installer.resolve_upgrade_source(target=target)

    assert resolved["source_type"] == "git"
    assert resolved["source_ref"] == MEMORY_GIT_SOURCE_REF
    assert resolved["source_label"] == "agentic-memory monorepo master"
    assert resolved["recorded_at"] == "2026-05-06"
    assert resolved["recommended_upgrade_after_days"] == 30


def test_upgrade_reports_resolved_source(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert any(
        action.path == target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and "upgrade source resolved to git" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and "recorded_at=2026-05-06" in action.detail
        for action in result.actions
    )


def test_upgrade_preserves_existing_local_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    source_path = target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml"
    source_path.write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert source_path.read_text(encoding="utf-8") == ('source_type = "local"\nsource_ref = "./local/agentic-memory"\n')
    assert any(
        action.path == source_path and action.kind == "current" and "preserving repo-local source selection" in action.detail
        for action in result.actions
    )


def test_upgrade_dry_run_does_not_include_bootstrap_workspace_files(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.upgrade_bootstrap(target=target, dry_run=True)
    planned = {action.path.relative_to(target).as_posix() for action in result.actions}

    assert all(not path.startswith(".agentic-workspace/memory/bootstrap/") for path in planned)


def test_verify_payload_passes_for_current_payload(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.verify_payload(target=target)

    assert not any(action.category == "contract-drift" for action in result.actions)


def test_payload_verification_policy_matches_installer_constants() -> None:
    policy = installer._load_payload_verification_policy()
    schema_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "agentic_workspace"
        / "contracts"
        / "schemas"
        / "payload_verification_policy.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(policy)) == []

    assert policy["bootstrap_version"] == installer.BOOTSTRAP_VERSION
    assert Path(policy["version_path"]) == installer.VERSION_PATH
    assert Path(policy["manifest_path"]) == installer.MANIFEST_PATH
    assert Path(policy["upgrade_source"]["path"]) == installer.UPGRADE_SOURCE_PATH
    assert Path(policy["upgrade_source"]["legacy_path"]) == installer.LEGACY_UPGRADE_SOURCE_PATH
    assert policy["upgrade_source"]["allowed_source_types"] == ["git", "local"]
    assert policy["upgrade_source"]["required_fields"] == ["source_ref"]
    assert policy["upgrade_source"]["date_fields"] == {"recorded_at": "YYYY-MM-DD"}
    assert policy["upgrade_source"]["integer_fields"] == ["recommended_upgrade_after_days"]
    assert tuple(Path(path) for path in policy["required_files"]) == installer.PAYLOAD_REQUIRED_FILES
    assert tuple(Path(path) for path in policy["compatibility_contract_files"]) == installer.MEMORY_COMPATIBILITY_CONTRACT_FILES
    assert tuple(Path(path) for path in policy["current_memory"]["required"]) == installer.CURRENT_MEMORY_BASELINE
    assert tuple(Path(path) for path in policy["current_memory"]["optional"]) == installer.OPTIONAL_CURRENT_MEMORY_FILES
    assert tuple(Path(path) for path in policy["forbidden_files"]) == installer.FORBIDDEN_PAYLOAD_FILES
    assert tuple(policy["forbidden_prefixes"]) == installer.FORBIDDEN_PAYLOAD_PREFIXES
    assert {
        Path(path): tuple(fragments) for path, fragments in policy["guidance_fragments"].items()
    } == installer.PAYLOAD_GUIDANCE_FRAGMENTS


def test_verify_payload_reports_contract_surface_shortlists(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.verify_payload(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
        and action.kind == "current"
        and action.role == "payload-contract"
        and "compatibility contract files:" in action.detail
        and ".agentic-workspace/memory/repo/index.md" in action.detail
        and ".agentic-workspace/memory/repo/current/project-state.md" not in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and action.role == "payload-contract"
        and "lower-stability helper files:" in action.detail
        and ".agentic-workspace/memory/UPGRADE-SOURCE.toml" in action.detail
        and ".agentic-workspace/memory/bootstrap/README.md" in action.detail
        for action in result.actions
    )


def test_verify_payload_flags_forbidden_current_note(monkeypatch, tmp_path: Path) -> None:
    payload = tmp_path / "payload"
    (payload / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "invariants").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "decisions").mkdir(parents=True, exist_ok=True)
    (payload / "scripts" / "check").mkdir(parents=True, exist_ok=True)
    (payload / "AGENTS.md").write_text("# Agent Instructions\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text("# Memory Index\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "WORKFLOW.md").write_text("# Workflow Rules\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text("# Project State\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text("# Task Context\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "active-decisions.md").write_text(
        "# Active Decisions\n", encoding="utf-8"
    )
    (payload / ".agentic-workspace" / "memory" / "repo" / "domains" / "README.md").write_text("# Domains\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "invariants" / "README.md").write_text("# Invariants\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "README.md").write_text("# Runbooks\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (payload / ".agentic-workspace" / "memory" / "repo" / "decisions" / "README.md").write_text("# Decisions\n", encoding="utf-8")
    (payload / "scripts" / "check" / "check_memory_freshness.py").write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr(installer, "payload_root", lambda: payload)
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.verify_payload(target=target)

    assert any(
        action.path.relative_to(target).as_posix() == ".agentic-workspace/memory/repo/current/active-decisions.md"
        and action.category == "contract-drift"
        for action in result.actions
    )


def test_upgrade_keeps_agents_current_when_workflow_pointer_is_current(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "WORKFLOW.md").write_text("# Workspace workflow\n", encoding="utf-8")
    (target / "AGENTS.md").write_text(
        f"# Agent instructions\n\n{WORKSPACE_POINTER_BLOCK}\n\nLocal repo instructions.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace/memory" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert any(action.path == target / "AGENTS.md" and action.kind == "current" for action in result.actions)
    assert not any(action.path == target / "AGENTS.md" and action.kind == "manual review" for action in result.actions)


def test_upgrade_can_remove_redundant_memory_pointer_when_workspace_pointer_is_present(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "WORKFLOW.md").write_text("# Workspace workflow\n", encoding="utf-8")
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        f"{WORKSPACE_POINTER_BLOCK}\n\n"
        "<!-- agentic-memory:workflow:start -->\n"
        "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-memory:workflow:end -->\n\n"
        "Local repo instructions.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace/memory" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target, apply_local_entrypoint=True)
    agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")

    assert "<!-- agentic-memory:workflow:start -->" not in agents_text
    assert WORKSPACE_POINTER_BLOCK in agents_text
    assert any(action.path == target / "AGENTS.md" and action.kind == "patched" for action in result.actions)


def test_upgrade_migrates_legacy_layout_by_default(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "bootstrap").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "skills" / "memory-router").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system" / "WORKFLOW.md").write_text("legacy workflow\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")
    (target / "memory" / "system" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )
    (target / "memory" / "bootstrap" / "README.md").write_text("legacy bootstrap\n", encoding="utf-8")
    (target / "memory" / "skills" / "memory-router" / "SKILL.md").write_text("legacy router\n", encoding="utf-8")
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        "<!-- agentic-memory:workflow:start -->\n"
        "Read `memory/system/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-memory:workflow:end -->\n",
        encoding="utf-8",
    )

    result = installer.upgrade_bootstrap(target=target)

    assert (target / ".agentic-workspace/memory" / "WORKFLOW.md").exists()
    assert (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").read_text(encoding="utf-8").startswith('source_type = "local"')
    assert not (target / "memory" / "system").exists()
    assert not (target / "memory" / "skills").exists()
    assert "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules." in (target / "AGENTS.md").read_text(encoding="utf-8")
    assert any(action.kind == "moved" for action in result.actions)
    assert not any(action.kind == "manual review" and "legacy managed layout detected" in action.detail for action in result.actions)


def test_upgrade_dry_run_simulates_default_migration_for_legacy_layout(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system" / "WORKFLOW.md").write_text("legacy workflow\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")
    (target / "memory" / "system" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        "<!-- agentic-memory:workflow:start -->\n"
        "Read `memory/system/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-memory:workflow:end -->\n",
        encoding="utf-8",
    )

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert not (target / ".agentic-workspace/memory" / "WORKFLOW.md").exists()
    assert any(
        action.kind == "would move" and action.path == target / ".agentic-workspace/memory" / "WORKFLOW.md" for action in result.actions
    )
    assert any(action.kind == "would patch" and action.path == target / "AGENTS.md" for action in result.actions)


def test_migrate_layout_moves_legacy_managed_files_into_agentic_memory_root(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "bootstrap").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "skills" / "memory-router").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system" / "WORKFLOW.md").write_text("workflow\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")
    (target / "memory" / "system" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )
    (target / "memory" / "bootstrap" / "README.md").write_text("bootstrap\n", encoding="utf-8")
    (target / "memory" / "skills" / "memory-router" / "SKILL.md").write_text("router\n", encoding="utf-8")
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        "<!-- agentic-memory:workflow:start -->\n"
        "Read `memory/system/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-memory:workflow:end -->\n",
        encoding="utf-8",
    )

    result = installer.migrate_layout(target=target)

    assert (target / ".agentic-workspace/memory" / "WORKFLOW.md").read_text(encoding="utf-8") == "workflow\n"
    assert (target / ".agentic-workspace/memory" / "VERSION.md").read_text(encoding="utf-8") == "Version: 38\n"
    assert (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").read_text(encoding="utf-8").startswith('source_type = "local"')
    assert (target / ".agentic-workspace/memory" / "bootstrap" / "README.md").read_text(encoding="utf-8") == "bootstrap\n"
    assert (target / ".agentic-workspace/memory" / "skills" / "memory-router" / "SKILL.md").read_text(encoding="utf-8") == "router\n"
    assert not (target / "memory" / "system" / "WORKFLOW.md").exists()
    assert "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules." in (target / "AGENTS.md").read_text(encoding="utf-8")
    assert any(action.kind == "moved" for action in result.actions)


def test_cli_parser_accepts_new_commands_and_placeholder_flags() -> None:
    generated_parser = cli.build_generated_parser()

    current_args = generated_parser.parse_args(["current", "check", "--target", "."])
    list_skills_args = generated_parser.parse_args(["list-skills", "--format", "json"])
    cleanup_args = generated_parser.parse_args(["bootstrap-cleanup", "--target", ".", "--format", "json"])
    migrate_args = generated_parser.parse_args(["migrate-layout", "--target", ".", "--dry-run", "--format", "json"])
    uninstall_args = generated_parser.parse_args(["uninstall", "--target", ".", "--dry-run", "--format", "json"])
    doctor_args = generated_parser.parse_args(["doctor", "--target", "."])
    prompt_install_args = generated_parser.parse_args(["prompt", "install", "--target", "./repo"])
    prompt_args = generated_parser.parse_args(["prompt", "adopt", "--target", "./repo"])
    prompt_populate_args = generated_parser.parse_args(["prompt", "populate", "--target", "./repo"])
    prompt_uninstall_args = generated_parser.parse_args(["prompt", "uninstall", "--target", "./repo"])
    route_args = generated_parser.parse_args(["route", "--files", "src/app.py"])
    sync_args = generated_parser.parse_args(["sync-memory", "--notes", ".agentic-workspace/memory/repo/index.md"])
    promotion_args = generated_parser.parse_args(
        ["promotion-report", "--notes", ".agentic-workspace/memory/repo/domains/api.md", "--mode", "remediation"]
    )
    report_args = generated_parser.parse_args(["report", "--target", ".", "--format", "json"])
    verify_args = generated_parser.parse_args(["verify-payload", "--format", "json"])
    install_args = generated_parser.parse_args(
        [
            "install",
            "--project-name",
            "demo",
            "--project-purpose",
            "purpose",
            "--key-repo-docs",
            "README.md",
            "--primary-build-command",
            "uv run build",
            "--policy-profile",
            "strict-doc-ownership",
        ]
    )

    assert current_args.command == "current"
    assert list_skills_args.command == "list-skills"
    assert cleanup_args.command == "bootstrap-cleanup"
    assert migrate_args.command == "migrate-layout"
    assert uninstall_args.command == "uninstall"
    assert doctor_args.command == "doctor"
    assert doctor_args.target == "."
    assert prompt_install_args.prompt_command == "install"
    assert prompt_args.command == "prompt"
    assert prompt_args.prompt_command == "adopt"
    assert prompt_populate_args.prompt_command == "populate"
    assert prompt_uninstall_args.prompt_command == "uninstall"
    assert route_args.command == "route"
    assert sync_args.command == "sync-memory"
    assert promotion_args.command == "promotion-report"
    assert promotion_args.mode == "remediation"
    assert report_args.command == "report"
    assert verify_args.command == "verify-payload"
    assert install_args.project_purpose == "purpose"
    assert install_args.policy_profile == "strict-doc-ownership"


def test_install_policy_profile_strict_doc_ownership_updates_manifest_rule(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target, policy_profile="strict-doc-ownership")

    manifest_text = (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").read_text(encoding="utf-8")
    assert "forbid_core_docs_depend_on_memory = true" in manifest_text


def test_install_policy_profile_strict_doc_ownership_reports_dry_run_update(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.install_bootstrap(target=target, dry_run=True, policy_profile="strict-doc-ownership")

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
        and action.kind == "would update"
        and "strict-doc-ownership" in action.detail
        for action in result.actions
    )


def test_cli_version_flag_prints_package_version(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])

    assert excinfo.value.code == 0
    assert "agentic-memory" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "setup_installed_repo"),
    [
        (["list-files", "--target", ".", "--format", "json"], False),
        (["list-skills", "--format", "json"], False),
        (["prompt", "upgrade", "--target", "./repo"], False),
        (["install", "--target", ".", "--dry-run", "--format", "json"], False),
        (["adopt", "--target", ".", "--dry-run", "--format", "json"], False),
        (["status", "--target", ".", "--format", "json"], False),
        (["verify-payload", "--target", ".", "--format", "json"], False),
        (["doctor", "--target", ".", "--format", "json"], True),
        (["current", "show", "--target", ".", "--format", "json"], True),
        (["current", "check", "--target", ".", "--format", "json"], True),
        (["route", "--target", ".", "--files", "src/app.py", "--format", "json"], True),
        (["sync-memory", "--target", ".", "--files", "src/app.py", "--format", "json"], True),
        (
            ["capture-note", "app-learning", "--target", ".", "--summary", "App learning.", "--files", "src/app.py", "--format", "json"],
            True,
        ),
        (
            [
                "promotion-report",
                "--target",
                ".",
                "--notes",
                ".agentic-workspace/memory/repo/index.md",
                "--mode",
                "remediation",
                "--format",
                "json",
            ],
            True,
        ),
        (["report", "--target", ".", "--format", "json"], True),
        (["upgrade", "--target", ".", "--dry-run", "--format", "json"], True),
        (["uninstall", "--target", ".", "--dry-run", "--format", "json"], True),
        (["bootstrap-cleanup", "--target", ".", "--format", "json"], True),
    ],
)
def test_cli_main_smoke_commands_return_zero(tmp_path: Path, argv: list[str], setup_installed_repo: bool) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    if setup_installed_repo:
        installer.install_bootstrap(target=target)

    completed = cli.main([arg if arg != "." else str(target) for arg in argv])

    assert completed == 0


def test_git_changed_files_times_out_with_warning(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["git", "status"], timeout=30)

    monkeypatch.setattr(installer.subprocess, "run", _raise_timeout)

    assert installer._git_changed_files(target) == []
    assert "Warning: git change detection failed" in capsys.readouterr().err


def test_verify_payload_reports_version_mismatch(tmp_path: Path, monkeypatch) -> None:
    payload = tmp_path / "payload"
    (payload / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace/memory" / "VERSION.md").write_text("Version: 21\n", encoding="utf-8")
    monkeypatch.setattr(installer, "payload_root", lambda: payload)

    result = installer.verify_payload(target=payload)

    assert any(
        action.path == payload / ".agentic-workspace/memory" / "VERSION.md"
        and action.kind == "manual review"
        and "does not match installer bootstrap version" in action.detail
        for action in result.actions
    )


def test_verify_payload_flags_missing_current_note_collaboration_guidance(tmp_path: Path, monkeypatch) -> None:
    payload = tmp_path / "payload"
    (payload / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace/memory" / "VERSION.md").write_text(f"Version: {installer.BOOTSTRAP_VERSION}\n", encoding="utf-8")
    (payload / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "git"\nsource_ref = "example"\nsource_label = "Example"\nrecorded_at = "2026-04-06"\n',
        encoding="utf-8",
    )
    (payload / "AGENTS.md").write_text("# Agent Instructions\n", encoding="utf-8")
    (payload / "scripts" / "check").mkdir(parents=True, exist_ok=True)
    (payload / "scripts" / "check" / "check_memory_freshness.py").write_text("print('ok')\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "invariants").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "decisions").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text("# Memory Index\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text("version = 1\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "domains" / "README.md").write_text("# Domains\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "invariants" / "README.md").write_text("# Invariants\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "README.md").write_text("# Runbooks\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (payload / ".agentic-workspace" / "memory" / "repo" / "decisions" / "README.md").write_text("# Decisions\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text("# Project State\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text("# Task Context\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md").write_text(
        "# Routing Feedback\n", encoding="utf-8"
    )

    monkeypatch.setattr(installer, "payload_root", lambda: payload)

    result = installer.verify_payload(target=payload)

    assert any(
        action.path == payload / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
        and action.kind == "manual review"
        and "collaboration-safe wording" in action.detail
        for action in result.actions
    )


def test_bootstrap_workflow_doc_includes_note_maintenance_and_skill_precedence_guidance() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "WORKFLOW.md").read_text(encoding="utf-8")

    assert "## Note maintenance rule" in text
    assert "Update a note when its primary home is still correct" in text
    assert "Checked-in repo-local skills should take precedence" in text
    assert "## Stale-note pressure" in text
    assert "## Canonical-doc boundary" in text
    assert "Treat memory as assistive residue by default" in text
    assert "## Interoperability contract" in text
    assert "active planning/status surface owns active intent and sequencing" in text
    assert "anti-trap memory for repeated or high-likelihood mistakes" in text
    assert "## Capture threshold" in text
    assert "## Anti-patterns" in text
    assert "Optimise for deletion and consolidation" in text
    assert "does not replace checking code, tests, or canonical docs" in text
    assert "user-specific preferences" in text
    assert "Memory is also a pressure layer" in text
    assert "## Improvement pressure" in text
    assert "## Improvement-targeting workflow" in text
    assert "record the intended post-remediation note shape before closing the signal" in text
    assert "## Remediation paths" in text
    assert "Treat `promotion-report` as the main elimination workflow" in text
    assert "Do not assume memory volume should trend downward across all repos or stages" in text
    assert "Judge memory by whether it justifies its cost and reduces rediscovery" in text
    assert "must not autonomously rewrite repo-owned docs, tests, scripts, or code outside the managed bootstrap surface" in text
    assert "prefer a clearer handoff into repo-owned work" in text
    assert "memory should help plans stay smaller by holding durable context that execplans can reference instead of repeating" in text
    assert "Repeated plan re-explanation or restart friction is a missing-synergy signal" in text
    assert "do not absorb plan history or milestone narration into memory" in text
    assert "## Closeout-derived residue" in text
    assert (
        "Do not paste plan history, milestone logs, validation transcripts, backlog state, or archived-plan narration into memory" in text
    )
    assert "`promotion_target`" in text
    assert "`retention_after_promotion`" in text
    assert "`summary`" in text
    assert "`applies_to`" in text
    assert "`use_when`" in text
    assert "`evidence`" in text
    assert "## Starter templates" in text
    assert ".agentic-workspace/memory/repo/templates/memory-note.template.md" in text
    assert "## Improvement metadata quick reference" in text
    assert "`retention_justification`" in text
    assert "`summary`, `applies_to`, `use_when`, and `evidence`" in text


def test_bootstrap_index_includes_token_efficiency_and_small_routing_examples() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "index.md").read_text(encoding="utf-8")

    assert "## Starter templates" in text
    assert "memory-note.template.md" in text
    assert "## Task routing" in text
    assert "not a task tracker, issue mirror, execution log, or broad fallback handbook" in text
    assert "Create repo-specific notes only from local evidence in the target repository." in text
    assert "## One-home reminder" in text


def test_bootstrap_readme_includes_optional_patterns_and_current_memory_migration_shape() -> None:
    text = (installer.payload_root() / "README.md").read_text(encoding="utf-8")

    assert "Optional repo pattern only" in text
    assert "legacy current-memory migration review" in text
    assert "durable facts move into primary memory notes or canonical docs" in text
    assert "Memory owns durable repo knowledge" in text
    assert "anti-trap memory for repeated or high-likelihood mistakes" in text
    assert "When to write to memory" in text
    assert "When not to write to memory" in text
    assert "## Anti-patterns" in text
    assert "## Minimal Adoption Checklist" in text
    assert "the combined install should be cheaper than either one alone" in text
    assert "Combined-install leverage" in text
    assert "archived planning history" in text
    assert "Good memory systems should help an agent read less, not more." in text
    assert "Memory is a reasoning aid" in text
    assert "mixing user-specific memory with repo-specific technical truth" in text
    assert "durable truth" in text
    assert "improvement signal" in text
    assert "symptom captured -> remediation target chosen -> follow-up routed -> remediation lands" in text
    assert "## Improvement Paths" in text
    assert "live decision review: the active planning slice plus `.agentic-workspace/memory/repo/decisions/README.md`" in text
    assert "promotion-report --mode remediation" in text
    assert "Do not assume memory volume should follow one universal trend" in text
    assert "suggest upstream repo improvements instead of treating memory as the default answer to repo complexity" in text
    assert "remain advisory outside the managed bootstrap surface" in text
    assert "prefer a clearer handoff into repo-owned work" in text
    assert "`.agentic-workspace/memory/repo/templates/` as starter note templates" in text
    assert "`retention_justification`" in text


def test_bootstrap_payload_uses_templates_not_repo_specific_starter_notes() -> None:
    payload_root = installer.payload_root()
    repo_root = payload_root / ".agentic-workspace" / "memory" / "repo"

    assert (repo_root / "templates" / "memory-note.template.md").exists()
    assert (repo_root / "templates" / "invariant.template.md").exists()
    assert (repo_root / "templates" / "runbook.template.md").exists()
    assert not (repo_root / "runbooks" / "dogfooding-usage-ledger.md").exists()
    assert not (repo_root / "domains" / "example-runtime-boundary.md").exists()
    assert not (repo_root / "skills").exists()

    manifest_text = (repo_root / "manifest.toml").read_text(encoding="utf-8")
    assert '[notes.".agentic-workspace/memory/repo/index.md"]' in manifest_text
    assert "dogfooding-usage-ledger.md" not in manifest_text


def test_bootstrap_task_context_starter_is_not_shipped() -> None:
    assert not (installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").exists()


def test_upgrade_removes_legacy_upgrade_runbook(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    legacy = target / ".agentic-workspace" / "memory" / "UPGRADE.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("# legacy\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target)

    assert not legacy.exists()
    assert any(
        action.path == legacy and action.kind == "removed" and action.category == "obsolete-managed-file" for action in result.actions
    )


def test_bootstrap_cleanup_removes_workspace(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    workspace = target / ".agentic-workspace/memory" / "bootstrap"
    assert workspace.exists()

    result = installer.cleanup_bootstrap_workspace(target=target)

    assert not workspace.exists()
    assert any(action.kind == "removed" for action in result.actions)


def test_bootstrap_cleanup_is_safe_when_workspace_absent(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.cleanup_bootstrap_workspace(target=target)

    assert any(action.kind == "skipped" for action in result.actions)


def test_uninstall_removes_safe_bootstrap_files(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    result = installer.uninstall_bootstrap(target=target)

    assert not (target / "AGENTS.md").exists()
    assert not (target / ".agentic-workspace" / "memory" / "repo" / "index.md").exists()
    assert not (target / "scripts" / "check" / "check_memory_freshness.py").exists()
    assert any(action.kind == "removed" for action in result.actions)


def test_uninstall_flags_customised_seed_notes_for_manual_review(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
    note_path.write_text("# Project State\n\ncustomised\n", encoding="utf-8")

    result = installer.uninstall_bootstrap(target=target, dry_run=True)

    assert any(action.path == note_path and action.kind == "manual review" for action in result.actions)


def test_uninstall_reports_remaining_repo_local_memory_as_safe_to_keep(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    extra_note = target / ".agentic-workspace" / "memory" / "repo" / "domains" / "local-note.md"
    extra_note.parent.mkdir(parents=True, exist_ok=True)
    extra_note.write_text("# Local Note\n", encoding="utf-8")

    result = installer.uninstall_bootstrap(target=target, dry_run=True)

    assert any(action.path == extra_note and action.kind == "skipped" and "safe to keep" in action.detail for action in result.actions)
