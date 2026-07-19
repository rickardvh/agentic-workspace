from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from planning_test_support import *
from repo_planning_bootstrap._source import UPGRADE_SOURCE_PATH, current_recorded_at, resolve_upgrade_source


def test_install_bootstrap_copies_required_files(tmp_path: Path) -> None:
    result = install_bootstrap(target=tmp_path)
    capability_fit_doc_path = tmp_path / ".agentic-workspace" / "docs" / "capability-aware-execution.md"
    routing_doc_path = tmp_path / ".agentic-workspace" / "docs" / "routing-contract.md"
    execution_flow_doc_path = tmp_path / ".agentic-workspace" / "docs" / "execution-flow-contract.md"
    lifecycle_doc_path = tmp_path / ".agentic-workspace" / "docs" / "lifecycle-and-config-contract.md"
    extraction_doc_path = tmp_path / ".agentic-workspace" / "docs" / "extraction-and-discovery-contract.md"
    skill_readme_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "README.md"
    skill_registry_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "REGISTRY.json"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"
    intake_skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-intake-upstream-task" / "SKILL.md"
    review_readme_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "README.md"
    review_template_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.md"
    review_record_template_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.review.json"
    intake_doc_path = tmp_path / ".agentic-workspace" / "planning" / "upstream-task-intake.md"
    refinement_doc_path = tmp_path / ".agentic-workspace" / "planning" / "pre-ingestion-refinement.md"
    execplan_schema_path = tmp_path / ".agentic-workspace" / "planning" / "schemas" / "planning-execplan.schema.json"
    review_schema_path = tmp_path / ".agentic-workspace" / "planning" / "schemas" / "planning-review.schema.json"
    external_evidence_schema_path = (
        tmp_path / ".agentic-workspace" / "planning" / "schemas" / "planning-external-intent-evidence.schema.json"
    )
    finished_evidence_schema_path = tmp_path / ".agentic-workspace" / "planning" / "schemas" / "planning-finished-work-evidence.schema.json"
    closeout_evidence_schema_path = tmp_path / ".agentic-workspace" / "planning" / "schemas" / "planning-closeout-evidence.schema.json"

    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    assert not (tmp_path / ".agentic-workspace/planning/TODO.md").exists()
    assert not (tmp_path / ".agentic-workspace/planning/ROADMAP.md").exists()
    assert not (tmp_path / "TODO.md").exists()
    assert not (tmp_path / "ROADMAP.md").exists()
    assert not capability_fit_doc_path.exists()
    assert routing_doc_path.exists()
    assert execution_flow_doc_path.exists()
    assert lifecycle_doc_path.exists()
    assert not extraction_doc_path.exists()
    assert not review_readme_path.exists()
    assert review_record_template_path.exists()
    assert not review_template_path.exists()
    assert not intake_doc_path.exists()
    assert not refinement_doc_path.exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "execplans" / "TEMPLATE.plan.json").exists()
    assert execplan_schema_path.exists()
    assert review_schema_path.exists()
    assert external_evidence_schema_path.exists()
    assert finished_evidence_schema_path.exists()
    assert closeout_evidence_schema_path.exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert not (tmp_path / ".agentic-workspace" / "planning" / "scripts").exists()
    assert skill_readme_path.exists()
    assert skill_registry_path.exists()
    assert skill_path.exists()
    assert intake_skill_path.exists()
    assert not (tmp_path / "tools").exists()
    assert not (tmp_path / "scripts").exists()
    assert any(action.kind in {"copied", "created", "updated"} for action in result.actions)


def test_install_bootstrap_writes_fresh_upgrade_source_record(tmp_path: Path) -> None:
    result = install_bootstrap(target=tmp_path)

    source_path = tmp_path / UPGRADE_SOURCE_PATH
    text = source_path.read_text(encoding="utf-8")
    resolved = resolve_upgrade_source(tmp_path)

    assert 'source_type = "git"' in text
    assert 'source_label = "agentic-planning monorepo master"' in text
    assert f'recorded_at = "{current_recorded_at()}"' in text
    assert resolved.age_days() == 0
    assert any(
        action.kind == "copied" and action.path == source_path and "current install date" in action.detail for action in result.actions
    )


def test_upgrade_bootstrap_preserves_existing_upgrade_source_metadata(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    source_path = tmp_path / UPGRADE_SOURCE_PATH
    source_path.write_text(
        'source_type = "local"\nsource_ref = "./vendor/agentic-planning"\nrecorded_at = "2026-01-15"\n',
        encoding="utf-8",
    )

    result = upgrade_bootstrap(target=tmp_path)

    assert source_path.read_text(encoding="utf-8").startswith('source_type = "local"\n')
    assert any(
        action.kind == "current" and action.path == source_path and "preserving repo-local source selection" in action.detail
        for action in result.actions
    )


def test_direct_planning_install_warns_without_workspace_orchestrator(tmp_path: Path) -> None:
    result = install_bootstrap(target=tmp_path)

    assert any(
        action.kind == "warning"
        and action.path == tmp_path / ".agentic-workspace" / "WORKFLOW.md"
        and "agentic-workspace init --modules planning" in action.detail
        and "module-level maintenance/debugging" in action.detail
        for action in result.actions
    )


def test_planning_status_warns_without_workspace_orchestrator(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    (tmp_path / ".agentic-workspace" / "WORKFLOW.md").unlink(missing_ok=True)

    result = collect_status(target=tmp_path)

    assert any(
        action.kind == "warning"
        and action.path == tmp_path / ".agentic-workspace" / "WORKFLOW.md"
        and "agentic-workspace init --modules planning" in action.detail
        for action in result.actions
    )


def test_direct_planning_install_skips_orchestrator_warning_when_workspace_present(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace" / "WORKFLOW.md").parent.mkdir(parents=True)
    (tmp_path / ".agentic-workspace" / "WORKFLOW.md").write_text("Workspace workflow\n", encoding="utf-8")

    result = install_bootstrap(target=tmp_path)

    assert not any(action.kind == "warning" and action.path == tmp_path / ".agentic-workspace" / "WORKFLOW.md" for action in result.actions)


def test_install_bootstrap_state_toml_includes_managed_state_header(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert state_text.startswith("# Agentic Workspace managed state.\n")
    assert "# Do not edit by hand when the CLI is available." in state_text
    assert "# Inspect: uv run agentic-workspace summary --format json" in state_text
    assert "# Mutate through the package command named by that output." in state_text
    assert 'kind = "agentic-planning-state"' in state_text


def test_install_bootstrap_include_optional_copies_optional_payload(tmp_path: Path) -> None:
    result = install_bootstrap(target=tmp_path, include_optional=True)

    assert (tmp_path / ".agentic-workspace" / "docs" / "capability-contract.json").exists()
    assert not (tmp_path / ".agentic-workspace" / "docs" / "capability-aware-execution.md").exists()
    assert not (tmp_path / ".agentic-workspace" / "docs" / "extraction-and-discovery-contract.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "reviews" / "README.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.review.json").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "upstream-task-intake.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "pre-ingestion-refinement.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "skills" / "REGISTRY.json").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md").exists()
    assert any(
        action.kind == "copied" and action.path == tmp_path / ".agentic-workspace" / "planning" / "reviews" / "README.md"
        for action in result.actions
    )


def test_install_dry_run_json_includes_compact_lifecycle_plan(tmp_path: Path, capsys) -> None:
    result = planning_cli.main(["install", "--target", str(tmp_path), "--dry-run", "--format", "json"])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    plan = payload["lifecycle_plan"]
    assert plan["schema_version"] == "planning-lifecycle-plan/v1"
    assert plan["operation"] == "install"
    assert plan["selected_modules"] == ["planning"]
    assert plan["summary"]["create_count"] > 0
    assert plan["summary"]["review_required_count"] >= 0
    assert plan["files"]["create"]
    assert ".agentic-workspace/planning/skills/planning-autopilot/SKILL.md" in plan["files"]["create"]
    assert ".agentic-workspace/planning/skills/planning-intake-upstream-task/SKILL.md" in plan["files"]["create"]
    assert plan["local_only_state"]["status"] == "not-authoritative"
    assert plan["next_safe_command"].startswith("agentic-planning install --target ")


def test_install_include_optional_dry_run_json_includes_optional_payload(tmp_path: Path, capsys) -> None:
    result = planning_cli.main(["install", "--target", str(tmp_path), "--include-optional", "--dry-run", "--format", "json"])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    actions = payload["actions"]
    assert any(
        action["kind"] == "would copy" and action["path"].replace("\\", "/").endswith(".agentic-workspace/planning/reviews/README.md")
        for action in actions
    )
    assert any(
        action["kind"] == "would copy"
        and action["path"].replace("\\", "/").endswith(".agentic-workspace/planning/skills/planning-autopilot/SKILL.md")
        for action in actions
    )
    assert ".agentic-workspace/planning/reviews/README.md" in payload["lifecycle_plan"]["files"]["create"]
    assert ".agentic-workspace/planning/skills/planning-autopilot/SKILL.md" in payload["lifecycle_plan"]["files"]["create"]


def test_ownership_module_root_matches_workspace_ledger() -> None:
    assert planning_module_root("planning") == Path(".agentic-workspace/planning")


def test_planning_contract_file_shortlist_is_explicit() -> None:
    assert Path("AGENTS.template.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/docs/capability-contract.json") in OPTIONAL_PAYLOAD_FILES
    assert Path(".agentic-workspace/docs/capability-aware-execution.md") not in OPTIONAL_PAYLOAD_FILES
    assert Path(".agentic-workspace/docs/orchestrator-workflow-contract.md") not in OPTIONAL_PAYLOAD_FILES
    assert Path(".agentic-workspace/docs/minimum-operating-model.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/execplans/README.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/reviews/README.md") in OPTIONAL_PAYLOAD_FILES
    assert Path(".agentic-workspace/planning/reviews/TEMPLATE.review.json") in REQUIRED_PAYLOAD_FILES
    assert Path(".agentic-workspace/planning/reviews/TEMPLATE.review.json") not in OPTIONAL_PAYLOAD_FILES
    assert Path(".agentic-workspace/planning/upstream-task-intake.md") in OPTIONAL_PAYLOAD_FILES
    assert Path(".agentic-workspace/planning/pre-ingestion-refinement.md") in OPTIONAL_PAYLOAD_FILES
    assert Path(".agentic-workspace/docs/routing-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/UPGRADE-SOURCE.toml") in PLANNING_LOWER_STABILITY_HELPER_FILES
    assert Path("tools/AGENT_QUICKSTART.md") not in REQUIRED_PAYLOAD_FILES
    assert Path("scripts/render_agent_docs.py") not in REQUIRED_PAYLOAD_FILES
    assert Path(".agentic-workspace/planning/scripts/render_agent_docs.py") not in REQUIRED_PAYLOAD_FILES
    assert set(PLANNING_COMPATIBILITY_CONTRACT_FILES).isdisjoint(PLANNING_LOWER_STABILITY_HELPER_FILES)
    assert set(PLANNING_COMPATIBILITY_CONTRACT_FILES) | set(PLANNING_LOWER_STABILITY_HELPER_FILES) == set(REQUIRED_PAYLOAD_FILES)
    assert set(REQUIRED_PAYLOAD_FILES).isdisjoint(OPTIONAL_PAYLOAD_FILES)


def test_bootstrap_upgrade_skill_uses_root_lifecycle_without_unshipped_helper_scripts() -> None:
    package_skill = installer_mod.skills_root() / "bootstrap-upgrade" / "SKILL.md"
    repo_skill = Path(__file__).resolve().parents[3] / ".agentic-workspace" / "planning" / "skills" / "bootstrap-upgrade" / "SKILL.md"
    for skill_path in (package_skill, repo_skill):
        text = skill_path.read_text(encoding="utf-8")
        assert "agentic-workspace upgrade --target <repo> --dry-run --format json" in text
        assert "agentic-workspace upgrade --target <repo> --format json" in text
        assert "agentic-workspace doctor --target <repo> --format json" in text
        assert "agentic-workspace upgrade --target <repo>" in text
        assert "agentic-planning upgrade --target <repo>" not in text
        assert "package-local debugging" in text
        assert "scripts/render_agent_docs.py" not in text
        assert "scripts/check/check_maintainer_surfaces.py" not in text


def test_adopt_bootstrap_preserves_existing_agents(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    result = adopt_bootstrap(target=tmp_path)
    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)


def test_adopt_bootstrap_docs_heavy_repo_preserves_root_surfaces_and_installs_helpers(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    todo_path = tmp_path / ".agentic-workspace/planning/state.toml"
    roadmap_path = tmp_path / "ROADMAP.md"
    execplan_readme_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "README.md"
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
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "skipped" and action.path == execplan_readme_path for action in result.actions)
    assert any(
        action.kind in {"copied", "created", "updated"}
        and action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        for action in result.actions
    )
    assert not (tmp_path / "tools").exists()


def test_adopt_bootstrap_include_optional_preserves_existing_optional_surfaces(tmp_path: Path) -> None:
    review_readme_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "README.md"
    _write(review_readme_path, "# Existing review workflow\n")

    result = adopt_bootstrap(target=tmp_path, include_optional=True)

    assert review_readme_path.read_text(encoding="utf-8") == "# Existing review workflow\n"
    assert (tmp_path / ".agentic-workspace" / "planning" / "upstream-task-intake.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-intake-upstream-task" / "SKILL.md").exists()
    assert any(action.kind == "skipped" and action.path == review_readme_path for action in result.actions)


def test_render_wrapper_install_does_not_ship_root_script_entrypoint(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    assert not (tmp_path / "scripts" / "render_agent_docs.py").exists()


def test_adopt_bootstrap_preserves_existing_manifest_in_partial_managed_state(tmp_path: Path) -> None:
    manifest_path = tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
    manifest_text = '{"bootstrap": {"first_reads": ["AGENTS.md", ".agentic-workspace/planning/state.toml"]}}\n'
    _write(manifest_path, manifest_text)

    result = adopt_bootstrap(target=tmp_path)

    assert manifest_path.read_text(encoding="utf-8") == manifest_text
    assert any(action.kind == "skipped" and action.path == manifest_path for action in result.actions)
    assert not (tmp_path / "tools").exists()


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


def test_status_command_routes_through_generated_adapter(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_status_handler(args) -> int:
        calls.append((args.command, args.format, args.target))
        print('{"ok": true}')
        return 0

    monkeypatch.setitem(planning_cli._GENERATED_RUNTIME_HANDLERS, "planning.status.report", fake_status_handler)

    assert planning_cli.main(["status", "--target", str(tmp_path), "--format", "json"]) == 0

    assert json.loads(capsys.readouterr().out) == {"ok": True}
    assert calls == [("status", "json", str(tmp_path))]


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
    assert manifest_actions
    assert any(action.kind == "current" for action in manifest_actions)


def test_verify_payload_reports_contract_surface_shortlists() -> None:
    result = verify_payload()

    assert any(
        action.path.name == "agent-manifest.json"
        and action.kind == "current"
        and "default compatibility contract files:" in action.detail
        and "AGENTS.md" in action.detail
        and ".agentic-workspace/planning/agent-manifest.json" in action.detail
        for action in result.actions
    )
    assert any(
        action.path.name == "agent-manifest.json"
        and action.kind == "current"
        and "default lower-stability helper files:" in action.detail
        and ".agentic-workspace/planning/UPGRADE-SOURCE.toml" in action.detail
        for action in result.actions
    )
    assert any(
        action.path.name == "agent-manifest.json"
        and action.kind == "current"
        and "optional packaged payload files:" in action.detail
        and ".agentic-workspace/docs/capability-contract.json" in action.detail
        and ".agentic-workspace/planning/upstream-task-intake.md" in action.detail
        for action in result.actions
    )


def test_list_files_json_separates_default_optional_and_skill_payloads(capsys) -> None:
    result = planning_cli.main(["list-files", "--format", "json"])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert ".agentic-workspace/docs/execution-flow-contract.md" in payload["default_files"]
    assert ".agentic-workspace/docs/capability-contract.json" in payload["optional_files"]
    assert "planning-autopilot/SKILL.md" in payload["bundled_skill_files"]
    assert ".agentic-workspace/docs/capability-contract.json" in payload["files"]
    assert "skills/planning-autopilot/SKILL.md" not in payload["files"]
    assert "agentic-planning install --include-optional" in payload["optional_enable_commands"]


def test_bootstrap_review_readme_includes_canonical_review_portfolio() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "reviews" / "README.md").read_text(encoding="utf-8")

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
    assert "## Constrained Prose" in text
    assert "Finding`, `Evidence`, `Impact`, `Recommendation`, `Owner`, `Status" in text


def test_bootstrap_review_template_includes_mode_and_cap_fields() -> None:
    record = json.loads(
        (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.review.json").read_text(encoding="utf-8")
    )

    assert record["kind"] == "planning-review/v1"
    assert "review_mode" in record
    assert "findings" in record
    assert record["prose_templates"]["review_finding"]["sections"] == [
        "Finding",
        "Evidence",
        "Impact",
        "Recommendation",
        "Owner",
        "Status",
    ]
    assert record["prose_templates"]["handoff_or_closeout"]["sections"] == [
        "Intent",
        "What changed",
        "Proof",
        "Remaining risk",
        "Durable residue",
        "Next owner",
    ]


def test_bootstrap_delegated_judgment_doc_is_part_of_contract() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")

    assert "# Execution and Milestone Flow Contract" in text
    assert "## Delegated Judgment" in text
    assert "Agents have bounded initiative to" in text
    assert "Escalation is required" in text
    assert "The path is blocked" in text
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_bootstrap_environment_recovery_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")

    assert "agentic-workspace report" in text
    assert "summary" in text
    assert "recover current context" in text
    assert "### Resumable Execution" in text
    assert "Environment and State Recovery" in text
    assert "agentic-workspace report" in text
    assert "agentic-workspace doctor --target ./repo" in text
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_bootstrap_execplan_readme_includes_memory_synergy_guidance() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "execplans" / "README.md").read_text(encoding="utf-8")

    assert "prefer borrowing durable context from the smallest relevant memory note or canonical doc" in text
    assert "Repeated background prose in plans is a missing-synergy signal" in text
    assert "promote it into memory or canonical docs" in text
    assert "must not silently widen the requested outcome" in text
    assert "Continuation surface" in text
    assert "larger intended outcome" in text
    assert "Required follow-on for the larger intended outcome" in text
    assert "Activation trigger" in text
    assert "## Iterative Follow-Through" in text
    assert "What this slice enabled" in text
    assert "## Delegated Judgment" in text
    assert "Requested outcome" in text
    assert "Agent may decide locally" in text
    assert "required tools" in text
    assert "Native runtime artifacts such as `implementation_plan.md`" in text
    assert "## Execution Summary" in text
    assert "Outcome delivered" in text


def test_bootstrap_execution_summary_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert "Execution Summary" in text
    assert "Execution Summary" in text
    assert "Captured Outcome" in text
    assert "Unfinished Detail" in text
    assert "Stable References" in text


def test_bootstrap_iterative_follow_through_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")

    assert "## Iterative Follow-Through" in text
    assert "Follow-Through Section" in text
    assert "residue" in text
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_bootstrap_resumable_execution_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert "Resumable Execution" in text
    assert "agentic-workspace report" in text
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_doctor_reports_contract_surface_shortlists(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert any(
        action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        and action.kind == "current"
        and "default compatibility contract files:" in action.detail
        and "AGENTS.md" in action.detail
        and ".agentic-workspace/planning/execplans/TEMPLATE.plan.json" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        and action.kind == "current"
        and "default lower-stability helper files:" in action.detail
        and ".agentic-workspace/planning/UPGRADE-SOURCE.toml" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        and action.kind == "current"
        and "optional packaged payload files:" in action.detail
        and ".agentic-workspace/docs/capability-contract.json" in action.detail
        and ".agentic-workspace/planning/upstream-task-intake.md" in action.detail
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

    assert not any(action.path == tmp_path / "README.md" and "agent-startup guidance" in action.detail for action in result.actions)


def test_doctor_does_not_flag_starter_todo_for_milestone_word_in_hygiene_rules(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert not any(
        action.path == tmp_path / ".agentic-workspace/planning/state.toml" and "milestone-level narrative" in action.detail
        for action in result.actions
    )


def test_doctor_guides_older_execplans_toward_current_contract_sections(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: the active plan still needs migration hints for the newer contract shape.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Candidate alpha; promote when maintained report signal appears.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        """
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
""",
    )

    result = doctor_bootstrap(target=tmp_path)

    assert any(warning["warning_class"] == "execplan_structure_drift" for warning in result.warnings)
    assert any(
        action.kind == "suggested fix"
        and action.path == plan_path
        and ".agentic-workspace/docs/execution-flow-contract.md" in action.detail
        and ".agentic-workspace/planning/execplans/README.md" in action.detail
        for action in result.actions
    )


def test_verify_payload_flags_missing_collaboration_safe_template_guidance(tmp_path: Path, monkeypatch) -> None:
    payload_root = tmp_path / "payload"
    _write(payload_root / "AGENTS.md", "# Agent Instructions\n")
    _write(payload_root / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(payload_root / "ROADMAP.md", "# Roadmap\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "execplans" / "README.md", "# Execution Plans\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "execplans" / "TEMPLATE.md", "# Plan Title\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "execplans" / "archive" / "README.md", "# Archive\n")
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
        action.path == payload_root / ".agentic-workspace" / "planning" / "execplans" / "TEMPLATE.md"
        and action.kind == "manual review"
        and "collaboration-safe template wording" in action.detail
        for action in result.actions
    )


def test_upgrade_bootstrap_overwrites_managed_files_but_preserves_root_surfaces(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    checker_path = tmp_path / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    checker_path.write_text("stale checker\n", encoding="utf-8")
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("stale skill\n", encoding="utf-8")

    result = upgrade_bootstrap(target=tmp_path)

    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert "stale checker" not in checker_path.read_text(encoding="utf-8")
    assert "stale skill" not in skill_path.read_text(encoding="utf-8")
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "overwritten" and action.path == checker_path for action in result.actions)
    assert any(action.kind == "overwritten" and action.path == skill_path for action in result.actions)


def test_upgrade_bootstrap_include_optional_refreshes_optional_payload_and_keeps_skills_current(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path, include_optional=True)
    review_readme_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "README.md"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"

    review_readme_path.write_text("stale optional review surface\n", encoding="utf-8")
    skill_path.write_text("stale optional skill\n", encoding="utf-8")

    result = upgrade_bootstrap(target=tmp_path, include_optional=True)

    assert "stale optional review surface" not in review_readme_path.read_text(encoding="utf-8")
    assert "stale optional skill" not in skill_path.read_text(encoding="utf-8")
    assert any(action.kind == "overwritten" and action.path == review_readme_path for action in result.actions)
    assert any(action.kind == "overwritten" and action.path == skill_path for action in result.actions)


def test_upgrade_bootstrap_legacy_standalone_install_adds_managed_helpers_without_overwriting_root_surfaces(tmp_path: Path) -> None:
    _write(tmp_path / "AGENTS.md", "legacy repo-owned agents\n")
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Candidate alpha

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "README.md", "# Execution Plans\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "TEMPLATE.md", "# Plan Title\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "README.md", "# Archive\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "reviews" / "README.md", "# Reviews\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.md", "# Review Template\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "upstream-task-intake.md", "# Upstream Task Intake\n")

    result = upgrade_bootstrap(target=tmp_path)

    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert not (tmp_path / "tools").exists()
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
    routing_path = tmp_path / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    manifest_path.unlink()
    routing_path.unlink()

    result = upgrade_bootstrap(target=tmp_path)

    assert manifest_path.exists()
    assert routing_path.exists()
    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert any(action.kind == "copied" and action.path == manifest_path for action in result.actions)
    assert any(action.kind == "copied" and action.path == routing_path for action in result.actions)
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)


def test_upgrade_bootstrap_preserves_unowned_root_todo_and_roadmap_files(tmp_path: Path) -> None:
    todo_path = tmp_path / "TODO.md"
    roadmap_path = tmp_path / "ROADMAP.md"
    todo_text = "# TODO\n\n## Personal Notes\n\n- Keep this user-owned file.\n"
    roadmap_text = "# ROADMAP\n\n## My Product Plan\n\n- Keep this user-owned file.\n"

    _write(todo_path, todo_text)
    _write(roadmap_path, roadmap_text)

    upgrade_bootstrap(target=tmp_path)

    assert todo_path.exists()
    assert roadmap_path.exists()
    assert todo_path.read_text(encoding="utf-8") == todo_text
    assert roadmap_path.read_text(encoding="utf-8") == roadmap_text
    assert (tmp_path / ".agentic-workspace/planning/state.toml").exists()


def test_upgrade_bootstrap_flags_managed_compatibility_views_for_manual_review(tmp_path: Path) -> None:
    todo_path = tmp_path / "TODO.md"
    roadmap_path = tmp_path / "ROADMAP.md"
    compat_notice = installer_mod._COMPATIBILITY_VIEW_NOTICE

    _write(todo_path, f"{compat_notice}\n# TODO\n")
    _write(roadmap_path, f"{compat_notice}\n# ROADMAP\n")

    result = upgrade_bootstrap(target=tmp_path)

    assert todo_path.exists()
    assert roadmap_path.exists()
    assert (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    assert not (tmp_path / "docs" / "planning-process.md").exists()
    assert any(
        action.kind == "manual review" and action.path == todo_path and "unsupported legacy compatibility view" in action.detail
        for action in result.actions
    )
    assert any(
        action.kind == "manual review" and action.path == roadmap_path and "unsupported legacy compatibility view" in action.detail
        for action in result.actions
    )


def test_doctor_reports_stale_generated_routing_residue_for_partial_managed_state(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    routing_path = tmp_path / "tools" / "AGENT_ROUTING.md"
    routing_path.parent.mkdir(parents=True, exist_ok=True)
    routing_path.write_text("stale generated routing\n", encoding="utf-8")

    result = doctor_bootstrap(target=tmp_path)

    assert not any(action.path == routing_path for action in result.actions)


def test_uninstall_bootstrap_removes_pristine_files_and_keeps_modified_surfaces(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    checker_path = tmp_path / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml"
    quickstart_path = tmp_path / "tools" / "AGENT_QUICKSTART.md"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    skill_source = installer_mod.skills_root() / "planning-autopilot" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_bytes(skill_source.read_bytes())

    result = uninstall_bootstrap(target=tmp_path)

    assert agents_path.exists()
    assert not checker_path.exists()
    assert not quickstart_path.exists()
    assert not skill_path.exists()
    assert any(action.kind == "manual review" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "removed" and action.path == checker_path for action in result.actions)
    assert any(action.kind == "removed" and action.path == skill_path for action in result.actions)
