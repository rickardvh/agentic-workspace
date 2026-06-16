from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_status_detects_installed_modules_by_default(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, calls)
    (tmp_path / "planning").mkdir()
    _write((tmp_path / "TODO.md"), "# TODO\n")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"), "{}\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: descriptors)

    assert cli.main(["status", "--verbose", "--target", str(tmp_path)]) == 0

    assert calls == [
        ("planning", "status", {"target": str(tmp_path)}),
        ("memory", "status", {"target": str(tmp_path)}),
    ]


def test_doctor_emits_affordance_shaped_repair_and_manual_review_actions(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "WORKFLOW.md").unlink()
    agents_path = target / "AGENTS.md"
    agents_path.write_text(agents_path.read_text(encoding="utf-8").replace(cli.WORKSPACE_POINTER_BLOCK, ""), encoding="utf-8")

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    safe_action = workspace_report["repair_actions"][0]
    assert safe_action["id"] == "restore-missing-workspace-surface"
    assert safe_action["invariant"] == "workspace.required_surface_present"
    assert safe_action["safe_to_apply"] is True
    assert safe_action["command"].startswith("agentic-workspace upgrade --target ")
    assert "--dry-run" in safe_action["dry_run"]
    assert safe_action["proof_after"][0].startswith("agentic-workspace doctor --target ")
    assert safe_action["do_not"]
    assert safe_action["improvement_signal_candidate"]["kind"] == "repair_recurrence"

    manual_action = workspace_report["manual_review_actions"][0]
    assert manual_action["id"] == "restore-workspace-pointer-manually"
    assert manual_action["invariant"] == "workspace.startup_pointer_present"
    assert manual_action["safe_to_apply"] is False
    assert manual_action["command"] is None
    assert manual_action["proof_after"][0].startswith("agentic-workspace doctor --target ")

    repair_plan = workspace_report["repair_plan"]
    assert repair_plan["status"] == "safe-action-available"
    assert repair_plan["primary_next_action"]["id"] == "restore-missing-workspace-surface"
    assert repair_plan["repair_action_count"] == 1
    assert repair_plan["manual_review_action_count"] == 1
    assert payload["repair_plan"]["primary_next_action"]["id"] == "restore-missing-workspace-surface"
    assert payload["repair_actions"][0]["id"] == "restore-missing-workspace-surface"
    assert payload["manual_review_actions"][0]["id"] == "restore-workspace-pointer-manually"


def test_doctor_repair_actions_use_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    (target / ".agentic-workspace" / "WORKFLOW.md").unlink()

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    action = workspace_report["repair_actions"][0]
    assert action["id"] == "restore-missing-workspace-surface"
    assert action["action"] == "run-workspace-upgrade"
    assert action.get("requires_dry_run_review") is not True
    assert action["command"].startswith("uv run agentic-workspace upgrade ")
    assert "--dry-run" not in action["command"]
    assert action["dry_run"].startswith("uv run agentic-workspace upgrade ")
    assert "--dry-run" in action["dry_run"]
    assert action.get("apply_after_review") in {None, action["command"]}
    assert action["proof_after"][0].startswith("uv run agentic-workspace doctor ")


def test_doctor_accepts_local_only_startup_indirection(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["install", "--modules", "planning", "--target", str(target), "--local-only", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    startup_action = next(action for action in workspace_report["actions"] if action["path"] == "AGENTS.md")
    assert startup_action["kind"] == "current"
    assert startup_action["detail"] == "local startup indirection points to AGENTS.local.md workspace workflow block"
    assert not any("workspace workflow pointer block missing" in warning for warning in payload["warnings"])
    assert not any(action["id"] == "restore-workspace-pointer-manually" for action in payload["manual_review_actions"])


def test_doctor_requires_local_only_state_for_local_startup_indirection(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / "AGENTS.md", "Follow instructions in `AGENTS.local.md` if present.\n")
    _write(target / "AGENTS.local.md", cli.workspace_pointer_block(cli_invoke=REPO_LOCAL_CLI_INVOKE) + "\n")
    _write(target / ".agentic-workspace" / "WORKFLOW.md", "# Workflow\n")
    _write(target / ".agentic-workspace" / "OWNERSHIP.toml", "schema_version = 1\n")
    _write(target / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}\n")

    assert cli.main(["doctor", "--modules", "planning", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    startup_action = next(action for action in workspace_report["actions"] if action["path"] == "AGENTS.md")
    assert startup_action["kind"] == "warning"
    assert startup_action["detail"] == "workspace workflow pointer block missing"


def test_doctor_does_not_enforce_source_repo_absolute_path_policy_in_target_repo(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    _write(target / "Dockerfile", "RUN rm -rf /var/lib/apt/lists/*\n")
    _write(target / "src" / "app" / "admin" / "CreateUser.tsx", "export const Role = () => <option>Admin</option>;\n")

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert not any("absolute path found" in warning for warning in payload["warnings"])
    assert not any(action["id"] == "remove-or-localize-absolute-paths" for action in payload["manual_review_actions"])


def test_doctor_routes_workspace_merge_conflict_markers_to_manual_review(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        "<<<<<<< ours\nschema_version = 1\n=======\nschema_version = 1\n>>>>>>> theirs\n",
    )
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        '<<<<<<< ours\nkind = "agentic-planning-state"\n=======\nkind = "agentic-planning-state"\n>>>>>>> theirs\n',
    )

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    manual_actions = payload["manual_review_actions"]
    ids = {action["id"] for action in manual_actions}
    assert "resolve-workspace-policy-merge-conflict" in ids
    assert "resolve-planning-live-state-merge-conflict" in ids
    config_action = next(action for action in manual_actions if action["id"] == "resolve-workspace-policy-merge-conflict")
    assert config_action["invariant"] == "workspace.policy_conflict_reviewed"
    assert "blind regeneration" in " ".join(config_action["do_not"])


def test_doctor_ignores_local_scratch_merge_conflict_markers(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        target
        / ".agentic-workspace"
        / "local"
        / "scratch"
        / "model-cli-harness"
        / "run"
        / "repo"
        / ".venv"
        / "Lib"
        / "site-packages"
        / "distlib-0.4.0.dist-info"
        / "LICENSE.txt",
        "<<<<<<< local scratch\nignored\n=======\nignored\n>>>>>>> local scratch\n",
    )

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    assert payload["health"] == "healthy"
    assert "distlib-0.4.0.dist-info/LICENSE.txt" not in encoded
    assert "resolve-workspace-policy-merge-conflict" not in {action["id"] for action in payload["manual_review_actions"]}


def test_workspace_report_buckets_scratch_nested_repo_warnings(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    scratch_repo = ".agentic-workspace/local/scratch/run/repo"
    ordinary_repo = "vendor/nested"

    payload = cli._workspace_report(
        target_root=tmp_path,
        message="Upgrade report",
        dry_run=True,
        actions=[],
        warnings=[
            {
                "kind": "manual review",
                "path": scratch_repo,
                "detail": "nested repository detected under target; installer will not recurse into repo roots automatically",
            },
            {
                "kind": "manual review",
                "path": ordinary_repo,
                "detail": "nested repository detected under target; installer will not recurse into repo roots automatically",
            },
        ],
    )

    assert [item["path"] for item in payload["local_scratch_notices"]] == [scratch_repo]
    assert payload["local_scratch_notices"][0]["classification"] == "local-scratch-residue"
    assert [item["path"] for item in payload["warnings"]] == [ordinary_repo]


def test_doctor_promotes_safe_module_lifecycle_repairs_for_missing_memory_templates(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    template_paths = [
        target / ".agentic-workspace" / "memory" / "repo" / "templates" / "invariant.template.md",
        target / ".agentic-workspace" / "memory" / "repo" / "templates" / "memory-note.template.md",
        target / ".agentic-workspace" / "memory" / "repo" / "templates" / "runbook.template.md",
    ]
    for path in template_paths:
        if path.exists():
            path.unlink()

    assert cli.main(["setup", "--target", str(target), "--non-interactive", "--format", "json"]) == 0
    setup_payload = json.loads(capsys.readouterr().out)
    assert setup_payload["health"] == "attention-needed"

    assert cli.main(["status", "--verbose", "--target", str(target), "--format", "json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["health"] == "attention-needed"
    assert any("memory-note.template.md" in item for item in status_payload["needs_review"])

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["health"] == "attention-needed"
    repair = next(action for action in doctor_payload["repair_actions"] if action["id"] == "apply-safe-memory-lifecycle-repair")
    assert repair["safe_to_apply"] is True
    assert "--module memory" in repair["command"]
    assert "payload sync" in repair["current_fault_summary"]
    assert "not a Python package upgrade" in repair["current_fault_summary"]
    assert "source-checkout" in " ".join(repair["do_not"])
    assert any(surface.endswith("memory/repo/templates/memory-note.template.md") for surface in repair["affected_surfaces"])
    assert doctor_payload["repair_plan"]["status"] == "safe-action-available"


def test_setup_surfaces_assurance_verification_onboarding_without_optional_module_residue(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    _write(
        target / ".agentic-workspace" / "verification" / "manifest.toml",
        'schema_version = "agentic-workspace/verification-manifest/v1"\n',
    )
    capsys.readouterr()

    assert cli.main(["setup", "--target", str(target), "--non-interactive", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    routes = payload["onboarding_routes"]
    assert routes["assurance"]["status"] == "absent"
    assert routes["assurance"]["command"] == "agentic-workspace defaults --section assurance_onboarding --format json"
    assert routes["assurance"]["report_command"] == (
        "agentic-workspace report --target ./repo --section assurance_requirements --format json"
    )
    assert routes["verification"]["status"] == "configured"
    assert routes["verification"]["command"] == "agentic-workspace defaults --section verification_onboarding --format json"
    assert routes["verification"]["report_command"] == "agentic-workspace report --target ./repo --section verification --format json"
    assert payload["current"]["installed_modules"]
    assert not any("installed module 'verification' is not enabled" in warning for warning in payload["current"]["warnings"])
    assert payload["current"]["optional_module_notices"] == [
        "Verification is installed and available as an optional module; it is not part of the default enabled module set."
    ]
    assert "agentic-workspace defaults --section assurance_onboarding --format json" in payload["next_action"]["commands"]
    assert "agentic-workspace defaults --section verification_onboarding --format json" in payload["next_action"]["commands"]


def test_doctor_module_filter_does_not_require_llms_adapter(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--modules", "planning", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert not any("llms.txt" in warning for warning in payload["warnings"])
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    assert not any(action["path"] == "llms.txt" for action in workspace_report["actions"])


def test_doctor_module_filter_does_not_warn_about_omitted_installed_modules(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    _write(
        target / ".agentic-workspace" / "verification" / "manifest.toml",
        'schema_version = "agentic-workspace/verification-manifest/v1"\n',
    )
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--modules", "planning", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["planning"]
    assert payload["residue_modules"] == []
    assert not any("installed module 'memory' is not enabled" in warning for warning in payload["warnings"])
    assert not any("installed module 'verification' is not enabled" in warning for warning in payload["warnings"])

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    unscoped_payload = json.loads(capsys.readouterr().out)
    assert unscoped_payload["residue_modules"] == ["verification"]
    assert any("installed module 'verification' is not enabled" in warning for warning in unscoped_payload["warnings"])


def test_status_flags_missing_workspace_shared_layer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    (target / ".agentic-workspace" / "WORKFLOW.md").unlink()
    capsys.readouterr()

    assert cli.main(["status", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/WORKFLOW.md" in warning for warning in payload["warnings"])


def test_doctor_flags_missing_workspace_shared_layer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    (target / ".agentic-workspace" / "OWNERSHIP.toml").unlink()
    capsys.readouterr()

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/OWNERSHIP.toml" in warning for warning in payload["warnings"])


def test_doctor_json_exposes_standardised_summary_fields(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "WORKFLOW.md"), "# Workflow\n")
    _write((tmp_path / ".agentic-workspace" / "OWNERSHIP.toml"), "schema_version = 1\n")
    _write((tmp_path / ".agentic-workspace" / "docs" / "jumpstart-contract.md"), "# Jumpstart Contract\n")
    _write((tmp_path / ".agentic-workspace" / "docs" / "module-map.md"), "# Installed Module Map\n")
    _write((tmp_path / ".agentic-workspace" / "docs" / "setup-findings-contract.md"), "# Setup Findings Contract\n")
    _write(
        (tmp_path / ".agentic-workspace" / "skills" / "REGISTRY.json"),
        '{"schema_version":"skill-registry.v1","owner":"agentic-workspace","source_kind":"installed-workspace-skills","skills":[]}\n',
    )
    _write((tmp_path / ".agentic-workspace" / "skills" / "workspace-startup" / "SKILL.md"), "# Workspace Startup\n")
    _write(
        (tmp_path / ".agentic-workspace" / "skills" / "workspace-intent-discovery" / "SKILL.md"),
        "# Workspace Intent Discovery\n",
    )
    _write((tmp_path / ".agentic-workspace" / "skills" / "workspace-work-shape" / "SKILL.md"), "# Workspace Work Shape\n")
    _write(
        (tmp_path / ".agentic-workspace" / "skills" / "workspace-proof-selection" / "SKILL.md"),
        "# Workspace Proof Selection\n",
    )
    _write(
        (tmp_path / ".agentic-workspace" / "skills" / "workspace-transition-gates" / "SKILL.md"),
        "# Workspace Transition Gates\n",
    )
    _write(
        (tmp_path / ".agentic-workspace" / "skills" / "workspace-operating-loop" / "SKILL.md"),
        "# Workspace Operating Loop\n",
    )
    _write(
        (tmp_path / ".agentic-workspace" / "skills" / "workspace-setup-jumpstart" / "SKILL.md"),
        "# Workspace Setup Jumpstart\n",
    )
    _write((tmp_path / ".agentic-workspace" / "system-intent" / "WORKFLOW.md"), "# System Intent Workflow\n")
    _write(
        (tmp_path / "AGENTS.md"),
        f"# Agent Instructions\n\n{cli.WORKSPACE_POINTER_BLOCK}\n\nLocal repo instructions.\n",
        encoding="utf-8",
    )
    _write(
        (tmp_path / ".agentic-workspace" / "AGENTS.md"),
        cli._workspace_managed_agent_instructions_text(config=cli.config_lib.load_workspace_config(target_root=tmp_path)),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["doctor", "--verbose", "--modules", "planning,memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "doctor"
    assert payload["created"] == ["planning", "memory"]
    assert payload["updated_managed"] == []
    assert payload["preserved_existing"] == []
    assert payload["needs_review"] == []
    assert payload["generated_artifacts"] == []
    assert payload["registry"][0]["name"] == "planning"


def test_status_warns_when_redundant_memory_pointer_block_remains(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    agents_path = target / "AGENTS.md"
    _write(
        agents_path,
        agents_path.read_text(encoding="utf-8").replace(
            "<!-- agentic-workspace:workflow:end -->\n",
            "<!-- agentic-workspace:workflow:end -->\n\n"
            "<!-- agentic-memory:workflow:start -->\n"
            "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n"
            "<!-- agentic-memory:workflow:end -->\n",
        ),
        encoding="utf-8",
    )
    capsys.readouterr()

    assert cli.main(["status", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any("redundant top-level memory workflow pointer block still present" in warning for warning in payload["warnings"])


def test_doctor_real_init_preserves_package_contract_shortlists_in_reports(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    planning_report = next(report for report in payload["reports"] if report["module"] == "planning")
    memory_report = next(report for report in payload["reports"] if report["module"] == "memory")

    assert any(
        action["path"] == ".agentic-workspace/planning/agent-manifest.json"
        and "compatibility contract files:" in action["detail"]
        and "AGENTS.md" in action["detail"]
        for action in planning_report["actions"]
    )
    assert any(
        action["path"] == ".agentic-workspace/memory/UPGRADE-SOURCE.toml"
        and "lower-stability helper files:" in action["detail"]
        and ".agentic-workspace/memory/UPGRADE-SOURCE.toml" in action["detail"]
        for action in memory_report["actions"]
    )
    assert not any(action["path"] == "AGENTS.md" and "--apply-local-entrypoint" in action["detail"] for action in memory_report["actions"])


def test_doctor_text_output_shows_package_contract_shortlists(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--verbose", "--target", str(target)]) == 0

    output = capsys.readouterr().out
    assert "[planning] Doctor report" in output
    assert "[memory] Doctor report" in output
    assert "compatibility contract files:" in output
    assert "lower-stability helper files:" in output


def test_doctor_real_init_reports_stale_planning_generated_residue(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    (target / "tools" / "AGENT_ROUTING.md").write_text("stale generated routing\n")
    capsys.readouterr()

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "healthy"
    assert not any(".agentic-workspace/planning/agent-manifest.json" in item for item in payload["needs_review"])


def test_status_reports_advisory_cli_compatibility_drift(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "advisory"\nexact_version = "999.0.0"\n',
    )

    assert cli.main(["status", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    compatibility = _assert_cli_compatibility(payload, status="advisory-drift")
    assert compatibility["enforcement"] == "advisory"
    assert compatibility["failed_checks"] == ["exact_version"]
    assert payload["health"] == "attention-needed"
    assert payload["executable_drift_warnings"][0].startswith("executable compatibility advisory-drift")
    assert compatibility["drift_findings"][0]["class"] == "executable-version-drift"
    assert compatibility["remediation"]["payload_drift_separate"] is True


def test_status_and_doctor_compact_outputs_include_machine_next_action(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "advisory"\nexact_version = "999.0.0"\n',
    )

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["next_action"]["action"] == "inspect-health-with-doctor"
    assert status_payload["next_action"]["command"] == "agentic-workspace doctor --target ./repo --format json"
    assert status_payload["next_action"]["run"] == status_payload["next_action"]["command"]

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["next_action"]["action"] == "inspect-repair-or-full-detail"
    assert doctor_payload["next_action"]["command"] == "agentic-workspace doctor --target ./repo --verbose --format json"
    assert doctor_payload["next_action"]["run"] == doctor_payload["next_action"]["command"]


def test_doctor_select_returns_requested_fields(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json", "--select", "health,warnings_count,next_action"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "doctor"
    assert payload["values"]["health"] == "healthy"
    assert payload["values"]["warnings_count"] == 0
    assert payload["values"]["next_action"]["action"] == "no-immediate-action"
    assert "available_selectors" not in payload


def test_doctor_select_reports_available_fields_for_missing_selector(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json", "--select", "missing.field"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["missing"] == ["missing.field"]
    assert payload["selector_rule"].startswith("Comma-separated dot paths")
    assert "health" in payload["available_selectors"]
    assert "warnings_count" in payload["available_selectors"]
    assert "next_action" in payload["available_selectors"]


def test_status_select_returns_requested_fields(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "status",
                "--target",
                str(target),
                "--format",
                "json",
                "--select",
                "health,installed_modules,warnings",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "status"
    assert payload["values"]["health"] == "healthy"
    assert payload["values"]["installed_modules"]
    assert payload["values"]["warnings"] == []
    assert "available_selectors" not in payload


def test_status_select_reports_available_fields_for_missing_selector(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json", "--select", "missing.field"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "status"
    assert payload["missing"] == ["missing.field"]
    assert payload["selector_rule"].startswith("Comma-separated dot paths")
    assert "health" in payload["available_selectors"]
    assert "installed_modules" in payload["available_selectors"]
    assert "warnings" in payload["available_selectors"]


def test_doctor_reports_cli_executable_drift_with_concrete_next_action(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "blocking"\nexact_version = "999.0.0"\n',
    )

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    compatibility = _assert_cli_compatibility(payload, status="blocking-drift")
    assert payload["health"] == "attention-needed"
    assert compatibility["failed_checks"] == ["exact_version"]
    assert compatibility["remediation"]["action"] == "upgrade-or-select-cli"
    action = payload["manual_review_actions"][0]
    assert action["id"] == "resolve-cli-executable-drift"
    assert action["severity"] == "error"
    assert action["cli_compatibility"]["payload_drift_separate"] is True
    assert "wrong CLI" in action["current_fault_summary"] or action["run"] == "agentic-workspace"


def test_doctor_json_does_not_report_dry_run_actions_as_mutations(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["doctor", "--verbose", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] == []
    assert payload["updated_managed"] == []
    assert payload["reports"][0]["actions"][0]["kind"] == "would update"


def test_status_warns_when_module_update_source_metadata_drifts_from_repo_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--modules", "planning", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'enabled = ["planning"]\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["status", "--verbose", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/planning/UPGRADE-SOURCE.toml" in warning for warning in payload["warnings"])
