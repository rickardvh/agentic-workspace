from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_setup_command_reports_no_new_seed_surfaces_for_mature_repo(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    (target / "memory").mkdir(exist_ok=True)
    (target / "memory" / "index.md").write_text("# Memory index\n")

    assert cli.main(["setup", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-setup/v1"
    assert payload["command"] == "setup"
    assert payload["orientation"]["mode"] == "bounded-orientation-needed"
    assert payload["orientation"]["summary"].lower().startswith("review the strongest current surface candidates")
    assert payload["findings_promotion"]["artifact_path"] == "tools/setup-findings.json"
    assert payload["findings_promotion"]["schema_path"] == "src/agentic_workspace/contracts/schemas/setup_findings.schema.json"
    assert payload["analysis_input"]["status"] == "not-found"
    assert payload["next_action"]["summary"] == "Review the compact report surfaces"
    assert "agentic-workspace report --target ./repo --format json" in payload["next_action"]["commands"]


def test_setup_command_loads_promotable_findings_artifact(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    (target / "memory").mkdir(exist_ok=True)
    _write((target / "memory" / "index.md"), "# Memory index\n")
    (target / "tools").mkdir(exist_ok=True)
    _write(
        (target / "tools" / "setup-findings.json"),
        json.dumps(
            {
                "kind": "workspace-setup-findings/v1",
                "findings": [
                    {
                        "class": "repo_friction_evidence",
                        "summary": "Workspace CLI remains a large shared hotspot.",
                        "confidence": 0.91,
                        "path": "src/agentic_workspace/cli.py",
                        "refs": [".agentic-workspace/docs/reporting-contract.md"],
                    },
                    {
                        "class": "planning_candidate",
                        "summary": "Promote one bounded module-reporting follow-on.",
                        "confidence": 0.83,
                        "next_action": "Promote the next module-reporting slice into .agentic-workspace/planning/state.toml after setup review.",
                    },
                    {
                        "class": "planning_candidate",
                        "summary": "Generic thought with no bounded action.",
                        "confidence": 0.82,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8-sig",
    )

    assert cli.main(["setup", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["analysis_input"]["status"] == "loaded"
    assert payload["analysis_input"]["loaded_count"] == 3
    assert payload["analysis_input"]["promotable"]["repo_friction_evidence"][0]["path"] == "src/agentic_workspace/cli.py"
    assert payload["analysis_input"]["promotable"]["planning_candidate"][0]["next_action"].startswith("Promote the next")
    assert payload["analysis_input"]["transient"][0]["promotion_reason"] == "planning candidate needs a bounded next_action"
    assert payload["next_action"]["summary"] == "Review promotable setup findings before seeding or promoting anything durable"
    assert payload["next_action"]["commands"] == [
        "agentic-workspace setup --target ./repo --format json",
        "agentic-workspace report --target ./repo --format json",
    ]


def test_init_dispatches_to_full_preset_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["preset"] == "full"
    assert payload["modules"] == ["planning", "memory"]
    assert payload["mode"] == "install"
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_init_seeds_schema_valid_workspace_config(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--preset", "planning", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_text = config_path.read_text(encoding="utf-8")
    assert config_text.startswith("# Agentic Workspace managed config.\n")
    assert "# Edit this file directly only when changing repo-owned policy." in config_text
    assert "# Reference: .agentic-workspace/docs/workspace-config-contract.md" in config_text
    assert "# Check resolved config: agentic-workspace config --target . --format json" in config_text
    assert 'default_preset = "planning"' in config_text
    assert payload["config"]["exists"] is True
    assert payload["config"]["edit_reference"]["reference_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert ".agentic-workspace/config.toml" in payload["created"]


def test_init_dry_run_reports_workspace_config_seed_without_writing(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--preset", "planning", "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert not (tmp_path / ".agentic-workspace" / "config.toml").exists()
    assert payload["config"]["exists"] is False
    assert ".agentic-workspace/config.toml" in payload["created"]


def test_init_preserves_existing_workspace_config(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    existing_config = 'schema_version = 1\n\n[workspace]\noptimization_bias = "human-legibility"\n'
    _write(config_path, existing_config, encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--preset", "planning", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert config_path.read_text(encoding="utf-8") == existing_config
    workspace_report = next(report for report in payload["module_reports"] if report["module"] == "workspace")
    config_action = next(action for action in workspace_report["actions"] if action["path"] == ".agentic-workspace/config.toml")
    assert config_action["kind"] == "current"
    assert "preserved repo-owned policy" in config_action["detail"]


def test_init_uses_default_preset_from_repo_config(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\ndefault_preset = "planning"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["preset"] == "planning"
    assert payload["modules"] == ["planning"]
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_init_uses_explicit_modules_csv(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--modules", "memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["memory"]
    assert calls == [("memory", "install", {"target": str(tmp_path), "dry_run": False, "force": False})]


def test_install_local_only_uses_normal_layout_with_local_startup_indirection(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "install"
    assert payload["target"] == repo_root.as_posix()
    assert (repo_root / "AGENTS.md").read_text(encoding="utf-8") == "Follow instructions in `AGENTS.local.md` if present.\n"
    local_agents_text = (repo_root / "AGENTS.local.md").read_text(encoding="utf-8")
    assert "<!-- agentic-workspace:workflow:start -->" in local_agents_text
    assert 'start --task "<task>"' in local_agents_text
    assert (repo_root / ".agentic-workspace" / "planning" / "state.toml").exists()
    assert (repo_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (repo_root / ".agentic-workspace" / "local" / "scratch").is_dir()
    assert (
        (repo_root / ".agentic-workspace" / "LOCAL-ONLY.toml")
        .read_text(encoding="utf-8")
        .startswith('schema_version = 1\nmode = "local-only"')
    )
    assert not (repo_root / "llms.txt").exists()
    git_exclude_text = (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".agentic-workspace/" in git_exclude_text
    assert "AGENTS.local.md" in git_exclude_text
    assert not (repo_root / ".gitignore").exists()
    lifecycle_plan = payload["lifecycle_plan"]
    assert "--local-only" in lifecycle_plan["next_safe_command"]["command"]
    assert lifecycle_plan["mutation_safety"]["local_only_preservation"]["status"] == "explicit-local-only-target"


def test_install_local_only_migrates_legacy_gitignore_residue(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)
    (repo_root / ".gitignore").write_text("# Agentic Workspace local-only storage\n.agentic-workspace/\n")

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "install"
    assert payload["target"] == repo_root.as_posix()
    assert not (repo_root / ".gitignore").exists()
    assert (repo_root / ".agentic-workspace" / "LOCAL-ONLY.toml").exists()
    git_exclude_text = (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".agentic-workspace/" in git_exclude_text
    assert "AGENTS.local.md" in git_exclude_text


def test_uninstall_local_only_removes_workspace_tree_local_startup_and_git_exclude(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "uninstall"
    assert payload["target"] == repo_root.as_posix()
    assert not (repo_root / ".agentic-workspace").exists()
    assert not (repo_root / "AGENTS.local.md").exists()
    assert "Follow instructions in `AGENTS.local.md` if present." not in (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    git_exclude_text = (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".agentic-workspace/" not in git_exclude_text
    assert "AGENTS.local.md" not in git_exclude_text
    lifecycle_plan = payload["lifecycle_plan"]
    assert "--local-only" in lifecycle_plan["next_safe_command"]["command"]
    assert lifecycle_plan["mutation_safety"]["classification"] == "destructive-mutation"


def test_init_reports_required_prompt_for_high_ambiguity_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    _write((tmp_path / "TODO.md"), "# Existing TODO\n")
    _write((tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md"), "# Memory\n")
    (tmp_path / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == [
        ".agentic-workspace/memory",
        ".agentic-workspace/memory/repo/index.md",
        ".agentic-workspace/planning",
        ".agentic-workspace/planning/execplans",
        "AGENTS.md",
        "TODO.md",
    ]
    assert payload["agent_instructions_file"] == "AGENTS.md"
    assert payload["handoff_prompt_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.md").as_posix()
    assert payload["handoff_record_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").as_posix()
    assert "handoff_prompt" in payload
    assert payload["handoff_record"]["kind"] == "workspace-bootstrap-handoff/v1"
    assert payload["handoff_record"]["intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert payload["handoff_record"]["intent"]["confirmed_intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert payload["handoff_record"]["intent"]["interpreted_intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert "must_not_change" in payload["handoff_record"]
    assert "escalate_when" in payload["handoff_record"]
    assert "Intent:" in payload["handoff_prompt"]
    assert "confirmed:" in payload["handoff_prompt"]
    assert "interpreted:" in payload["handoff_prompt"]
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.md").exists()
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").exists()
    assert not (tmp_path / "llms.txt").exists()
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_can_write_prompt_file(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    prompt_path = tmp_path / ".agentic-workspace" / "bootstrap-handoff.md"
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--write-prompt", str(prompt_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["handoff_prompt_path"] == prompt_path.as_posix()
    assert payload["handoff_record_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").as_posix()
    assert prompt_path.exists()
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").exists()
    assert "Finish the Agentic Workspace bootstrap" in prompt_path.read_text(encoding="utf-8")


def test_selection_commands_accept_non_interactive_flag() -> None:
    parser = cli.build_parser()

    install_args = parser.parse_args(["install", "--target", ".", "--local-only", "--non-interactive"])
    init_args = parser.parse_args(["init", "--target", ".", "--non-interactive"])
    uninstall_args = parser.parse_args(["uninstall", "--target", ".", "--local-only", "--non-interactive"])
    status_args = parser.parse_args(["status", "--target", ".", "--non-interactive"])
    prompt_args = parser.parse_args(["prompt", "upgrade", "--modules", "planning", "--target", ".", "--non-interactive"])

    assert install_args.local_only is True
    assert init_args.non_interactive is True
    assert uninstall_args.local_only is True
    assert status_args.non_interactive is True
    assert prompt_args.non_interactive is True


def test_prompt_init_uses_dry_run_workspace_bootstrap(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "prompt"
    assert payload["prompt_command"] == "init"
    assert payload["dry_run"] is True
    assert "handoff_prompt" in payload
    assert "Finish the Agentic Workspace bootstrap" in payload["handoff_prompt"]
    assert "handoff_record" not in payload
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_prompt_init_non_interactive_marks_prompt_free_handoff(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--non-interactive", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["non_interactive"] is True
    assert "do not assume a human can answer prompts or unblock a PTY" in payload["handoff_prompt"]


def test_prompt_init_returns_structured_handoff_record_for_high_ambiguity_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["prompt_requirement"] != "none"
    assert payload["handoff_record"]["kind"] == "workspace-bootstrap-handoff/v1"
    assert payload["handoff_record"]["next"]["immediate_brief"] == ".agentic-workspace/bootstrap-handoff.md"


def test_prompt_upgrade_builds_workspace_handoff_prompt(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["prompt", "upgrade", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "prompt"
    assert payload["prompt_command"] == "upgrade"
    assert payload["dry_run"] is True
    assert "Use the workspace CLI as the lifecycle entrypoint" in payload["handoff_prompt"]
    assert "README.md: inspect manually" in payload["handoff_prompt"]


def test_prompt_upgrade_non_interactive_mentions_prompt_free_execution(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["prompt", "upgrade", "--modules", "planning", "--target", str(tmp_path), "--non-interactive", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["non_interactive"] is True
    assert "Run this flow with `--non-interactive`" in payload["handoff_prompt"]


def test_init_uses_recommended_prompt_for_single_existing_surface(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["inferred_policy"] == "preserve_existing_and_adopt"
    assert payload["mode"] == "adopt"
    assert payload["prompt_requirement"] == "recommended"
    assert payload["detected_surfaces"] == ["AGENTS.md"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_autodetects_existing_gemini_file_as_startup_entrypoint(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "GEMINI.md"), "# Existing Gemini\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_instructions_file"] == "GEMINI.md"
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["detected_surfaces"] == ["GEMINI.md"]
    assert not (tmp_path / "llms.txt").exists()


def test_init_treats_multiple_supported_startup_files_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    _write((tmp_path / "GEMINI.md"), "# Existing Gemini\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert sorted(payload["detected_surfaces"]) == ["AGENTS.md", "GEMINI.md"]


def test_init_can_create_gemini_startup_file_for_blank_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert (
        cli.main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--agent-instructions-file",
                "GEMINI.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_instructions_file"] == "GEMINI.md"
    assert (tmp_path / "GEMINI.md").exists()
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "llms.txt").exists()


def test_init_dry_run_rewrites_module_startup_actions_for_custom_agent_file(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert (
        cli.main(
            [
                "init",
                "--modules",
                "planning",
                "--target",
                str(tmp_path),
                "--agent-instructions-file",
                "GEMINI.md",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "GEMINI.md" in payload["preserved_existing"]
    assert "AGENTS.md" not in payload["preserved_existing"]


def test_init_treats_existing_llms_file_as_existing_workspace_surface(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / ".agentic-workspace" / "bootstrap-handoff.md"), "# Bootstrap handoff\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["inferred_policy"] == "preserve_existing_and_adopt"
    assert payload["mode"] == "adopt"
    assert payload["prompt_requirement"] == "recommended"
    assert payload["detected_surfaces"] == [".agentic-workspace/bootstrap-handoff.md"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_reports_docs_heavy_repo_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    _write((tmp_path / "TODO.md"), "# Existing TODO\n")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "planning" / "state.toml"), "# Existing Roadmap\n")
    (tmp_path / "docs" / "maintainer" / "contributor-playbook.md").parent.mkdir(parents=True)
    _write((tmp_path / "docs" / "maintainer" / "contributor-playbook.md"), "# Contributor Playbook\n")
    _write((tmp_path / "docs" / "maintainer" / "maintainer-commands.md"), "# Maintainer Commands\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == [
        ".agentic-workspace/planning",
        ".agentic-workspace/planning/state.toml",
        "AGENTS.md",
        "TODO.md",
        "docs/maintainer/contributor-playbook.md",
    ]
    assert "AGENTS.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert "docs/maintainer/contributor-playbook.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_reports_existing_handoff_plus_workflow_surface_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    _write((tmp_path / ".agentic-workspace" / "bootstrap-handoff.md"), "# Bootstrap handoff\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "docs_heavy_existing_repo"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == [".agentic-workspace/bootstrap-handoff.md", "AGENTS.md"]
    assert "AGENTS.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert ".agentic-workspace/bootstrap-handoff.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_marks_partial_module_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md"), "# Memory\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        ".agentic-workspace/memory/repo/index.md: partial module state detected",
        ".agentic-workspace/memory: partial module state detected",
        ".agentic-workspace/memory/repo/index.md: reconcile existing workflow surface ownership",
        ".agentic-workspace/memory: reconcile existing workflow surface ownership",
    ]


def test_init_marks_partial_planning_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "TODO.md"), "# Existing TODO\n")
    (tmp_path / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "TODO.md: partial module state detected",
        ".agentic-workspace/planning/execplans: partial module state detected",
        ".agentic-workspace/planning: partial module state detected",
        "TODO.md: reconcile existing workflow surface ownership",
        ".agentic-workspace/planning/execplans: reconcile existing workflow surface ownership",
        ".agentic-workspace/planning: reconcile existing workflow surface ownership",
    ]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_marks_mixed_module_partial_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "TODO.md"), "# Existing TODO\n")
    (tmp_path / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md"), "# Existing memory index\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "TODO.md: partial module state detected",
        ".agentic-workspace/planning/execplans: partial module state detected",
        ".agentic-workspace/planning: partial module state detected",
        ".agentic-workspace/memory/repo/index.md: partial module state detected",
        ".agentic-workspace/memory: partial module state detected",
        "TODO.md: reconcile existing workflow surface ownership",
        ".agentic-workspace/planning/execplans: reconcile existing workflow surface ownership",
        ".agentic-workspace/planning: reconcile existing workflow surface ownership",
        ".agentic-workspace/memory/repo/index.md: reconcile existing workflow surface ownership",
        ".agentic-workspace/memory: reconcile existing workflow surface ownership",
    ]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_requires_git_repo(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["init", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_install_real_init_creates_combined_memory_and_planning_surfaces(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0

    assert (target / ".agentic-workspace" / "WORKFLOW.md").exists()
    assert (target / ".agentic-workspace" / "OWNERSHIP.toml").exists()
    assert (target / ".agentic-workspace" / "memory" / "repo" / "index.md").exists()
    assert (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").exists()
    assert (target / ".agentic-workspace" / "planning" / "state.toml").exists()
    assert (target / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    workflow_text = (target / ".agentic-workspace" / "WORKFLOW.md").read_text(encoding="utf-8")
    assert "not task state" in workflow_text
    assert "Do not edit this file to record task-specific" in workflow_text
    assert "startup-only, orientation-only" in workflow_text
    assert "Do not create planning files" in workflow_text
    agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- agentic-workspace:workflow:start -->" in agents_text
    assert 'start --task "<task>"' in agents_text
    assert not (target / "AGENTS.local.md").exists()
    assert "Run `agentic-workspace start --format json`" not in agents_text
    assert "Do not substitute a bare `agentic-workspace` command" in agents_text
    assert "agentic-workspace preflight --format json" not in agents_text
    assert (
        "Read `.agentic-workspace/memory/WORKFLOW.md` only when changing memory behavior or the memory workflow itself." not in agents_text
    )
    assert "Open module, planning, memory, or deeper routing files only when the compact answers point there." not in agents_text
    assert "## Module Notes" not in agents_text
    assert "<!-- agentic-memory:workflow:start -->" not in agents_text
    assert "<PROJECT_NAME>" not in agents_text


def test_install_real_init_can_use_gemini_as_root_startup_entrypoint(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--agent-instructions-file", "GEMINI.md"]) == 0

    assert (target / "GEMINI.md").exists()
    assert not (target / "AGENTS.md").exists()
    gemini_text = (target / "GEMINI.md").read_text(encoding="utf-8")
    assert 'start --task "<task>"' in gemini_text
    assert "Open module, planning, memory, or deeper routing files only when the compact answers point there." not in gemini_text
    assert not (target / "llms.txt").exists()


def test_install_real_init_does_not_generate_llms_adapter(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0

    assert not (target / "llms.txt").exists()


def test_upgrade_removes_retired_generated_llms_adapter(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / "llms.txt",
        """
# Agent Entrypoint Router

Authority marker:

- canonical_source: `src/agentic_workspace/cli.py:_external_agent_handoff_text`

Generated compatibility adapter.
""",
    )

    assert cli.main(["init", "--target", str(target)]) == 0

    assert not (target / "llms.txt").exists()


def test_upgrade_preserves_custom_llms_for_manual_review(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / "llms.txt", "# Custom local instructions\n")

    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert (target / "llms.txt").exists()
    assert "llms.txt: legacy llms.txt exists but is not recognized as the retired generated adapter" in payload["needs_review"]


def test_status_real_init_reports_workspace_shared_layer_surfaces(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    _assert_cli_compatibility(payload, status="no-expectation")
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    assert any(action["path"] == ".agentic-workspace/WORKFLOW.md" and action["kind"] == "current" for action in workspace_report["actions"])
    assert any(
        action["path"] == ".agentic-workspace/OWNERSHIP.toml" and action["kind"] == "current" for action in workspace_report["actions"]
    )


def test_status_real_init_reports_workspace_health(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "status"
    assert payload["modules"] == ["planning", "memory"]
    assert "health" in payload
    assert payload["registry"][0]["name"] == "planning"
    assert payload["registry"][1]["installed"] is True
    assert not any(".agentic-workspace/WORKFLOW.md" in warning for warning in payload["warnings"])
    assert not any(".agentic-workspace/OWNERSHIP.toml" in warning for warning in payload["warnings"])


def test_upgrade_strict_preflight_requires_token(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "upgrade",
                "--target",
                str(tmp_path),
                "--strict-preflight",
                "--dry-run",
            ]
        )

    assert excinfo.value.code == 2
    assert "Strict preflight gate is enabled" in capsys.readouterr().err


def test_upgrade_strict_preflight_rejects_stale_token(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "upgrade",
                "--target",
                str(tmp_path),
                "--strict-preflight",
                "--preflight-token",
                "preflight-v1:1",
                "--preflight-max-age-seconds",
                "60",
                "--dry-run",
            ]
        )

    assert excinfo.value.code == 2
    assert "Stale preflight token" in capsys.readouterr().err


def test_upgrade_json_collects_summary_categories(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "upgrade"
    assert payload["updated_managed"] == [".agentic-workspace/planning/agent-manifest.json"]
    assert payload["preserved_existing"] == ["AGENTS.md"]
    assert payload["generated_artifacts"] == [".agentic-workspace/planning/agent-manifest.json"]
    assert payload["needs_review"] == ["README.md: inspect manually"]
    assert payload["warnings"] == []
    assert payload["stale_generated_surfaces"] == [".agentic-workspace/planning/agent-manifest.json"]
    safety = payload["lifecycle_plan"]["mutation_safety"]
    assert safety["classification"] == "lifecycle-mutation"
    assert safety["dry_run_apply_separation"]["status"] == "dry-run-only"
    assert safety["review_required_before_apply"] is True
    assert safety["strict_preflight"]["available"] is True
    scenarios = {entry["scenario"]: entry for entry in safety["fixture_coverage"]}
    assert scenarios["upgrade dry-run on installed repo"]["status"] == "covered"


def test_init_flags_preserved_agentic_workspace_absence_instructions(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "AGENTS.md",
        "# Agent Instructions\n\nThis repository does not use Agentic Workspace. Work from ordinary files.\n",
    )

    assert cli.main(["init", "--target", str(tmp_path), "--preset", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert any(
        item.startswith("AGENTS.md: preserved repo-owned instructions claim Agentic Workspace is absent")
        for item in payload["needs_review"]
    )


@pytest.mark.parametrize(
    ("args", "expected_modules"),
    [
        (["--modules", "memory"], ["memory"]),
        (["--modules", "planning"], ["planning"]),
        (["--preset", "full"], ["planning", "memory"]),
    ],
)
def test_upgrade_lifecycle_plan_advertises_root_front_door_for_module_selections(
    monkeypatch, tmp_path: Path, capsys, args: list[str], expected_modules: list[str]
) -> None:
    _init_git_repo(tmp_path)
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["upgrade", "--target", str(tmp_path), *args, "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    front_door = payload["lifecycle_plan"]["root_upgrade_front_door"]
    assert front_door["status"] == "authoritative-host-repo-path"
    assert front_door["selected_modules"] == expected_modules
    assert front_door["dry_run_first"] is True
    assert front_door["package_specific_upgrade_role"] == "fallback-debug-only"
    assert front_door["ordinary_sequence"][0]["step"] == "inspect"
    assert front_door["ordinary_sequence"][0]["safe"] is True
    assert "--dry-run" in front_door["ordinary_sequence"][0]["command"]
    assert "selected modules" in front_door["ordinary_sequence"][0]["reason"]
    assert front_door["ordinary_sequence"][1]["step"] == "apply"
    assert "--dry-run" not in front_door["ordinary_sequence"][1]["command"]
    assert front_door["ordinary_sequence"][2]["command"].startswith("agentic-workspace doctor --target ")
    assert [(module_name, command_name) for module_name, command_name, _kwargs in calls] == [
        (module_name, "upgrade") for module_name in expected_modules
    ]


def test_lifecycle_plan_uses_resolved_cli_invoke_for_next_actions(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["upgrade", "--target", str(tmp_path), "--modules", "planning", "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    lifecycle_plan = payload["lifecycle_plan"]
    assert lifecycle_plan["next_safe_command"]["command"].startswith("uv run agentic-workspace upgrade ")
    primary_action = lifecycle_plan["primary_next_action"]
    assert primary_action["action"] == "apply-lifecycle-plan"
    assert primary_action["command"].startswith("uv run agentic-workspace upgrade ")
    assert primary_action["run"] == primary_action["command"]
    assert primary_action["risk"] == "may mutate repo-managed workspace surfaces"
    assert primary_action["required_inputs"] == ["target repo", "selected modules", "dry-run plan"]
    assert primary_action["next_proof"] == "run doctor after apply and inspect surface classifications"
    freshness = lifecycle_plan["module_update_freshness"][0]["freshness"]
    assert freshness["status"] in {"fresh", "unknown"}
    assert freshness["next_action"] is None or freshness["next_action"]["command"].startswith("uv run agentic-workspace upgrade ")
    front_door = lifecycle_plan["root_upgrade_front_door"]
    assert front_door["ordinary_sequence"][0]["command"].startswith("uv run agentic-workspace upgrade ")
    assert front_door["ordinary_sequence"][1]["command"].startswith("uv run agentic-workspace upgrade ")
    assert front_door["ordinary_sequence"][2]["command"].startswith("uv run agentic-workspace doctor ")
    assert payload["next_steps"][0].startswith("Run uv run agentic-workspace doctor ")


@pytest.mark.parametrize("dry_run_arg", [["--dry-run"], []])
def test_upgrade_lifecycle_surface_classifications_cover_reason_classes(
    monkeypatch, tmp_path: Path, capsys, dry_run_arg: list[str]
) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))
    _write(tmp_path / ".agentic-workspace" / "local" / "memory.toml", 'kind = "local-memory"\n')
    _write(
        tmp_path / "ROADMAP.md",
        "<!-- GENERATED COMPATIBILITY VIEW: authoritative source is .agentic-workspace/planning/state.toml -->\n# ROADMAP\n",
    )

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(tmp_path), *dry_run_arg, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    classifications = payload["lifecycle_plan"]["surface_classifications"]
    entries = classifications["entries"]
    by_path = {entry["path"]: entry for entry in entries}
    reason_classes = {entry["reason_class"] for entry in entries}
    assert classifications["kind"] == "workspace-lifecycle-surface-classifications/v1"
    assert by_path[".agentic-workspace/planning/agent-manifest.json"]["reason_class"] == "core refreshed"
    assert by_path["AGENTS.md"]["reason_class"] == "repo-owned preserved"
    assert by_path["README.md"]["reason_class"] == "ambiguous ownership manual-review"
    assert by_path[".agentic-workspace/local/memory.toml"]["reason_class"] == "local-only preserved"
    assert "legacy unsupported; migration/refusal required" in reason_classes
    assert classifications["summary_by_class"]["core refreshed"] >= 1


def test_uninstall_lifecycle_surface_classifications_include_refused_destructive_action(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    workflow_path = target / ".agentic-workspace" / "WORKFLOW.md"
    workflow_path.write_text(workflow_path.read_text(encoding="utf-8") + "\nLocal owner edit.\n", encoding="utf-8")

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    classifications = payload["lifecycle_plan"]["surface_classifications"]
    assert classifications["summary_by_class"]["refused destructive action"] >= 1
    assert any(
        entry["reason_class"] == "ambiguous ownership manual-review" and entry["review_required"] is True
        for entry in classifications["entries"]
    )


def test_upgrade_text_output_keeps_surface_classification_detail_in_json(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(tmp_path), "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "Surface classifications:" in output
    assert "lifecycle_plan.surface_classifications.entries" in output
    assert "[planning] upgrade planning" not in output
    assert "README.md: inspect manually" in output


def test_uninstall_dry_run_requires_review_for_ambiguous_workspace_payload(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    workflow_path = target / ".agentic-workspace" / "WORKFLOW.md"
    workflow_path.write_text(workflow_path.read_text(encoding="utf-8") + "\nLocal owner edit.\n", encoding="utf-8")

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert (
        ".agentic-workspace/WORKFLOW.md: local workspace shared-layer file differs from managed payload; remove manually if intended"
        in payload["needs_review"]
    )
    lifecycle_plan = payload["lifecycle_plan"]
    assert lifecycle_plan["review_required"] is True
    assert lifecycle_plan["next_safe_command"]["status"] == "review-required"
    primary_action = lifecycle_plan["primary_next_action"]
    assert primary_action["action"] == "resolve-lifecycle-review"
    assert primary_action["command"].startswith("agentic-workspace uninstall ")
    assert "--dry-run" in primary_action["command"]
    assert primary_action["run"] == primary_action["command"]
    assert primary_action["risk"] == "blocked until review items are resolved"
    assert primary_action["required_inputs"] == ["target repo", "selected modules", "review items"]
    assert primary_action["next_proof"] == "rerun the lifecycle dry-run after resolving review items"
    safety = lifecycle_plan["mutation_safety"]
    assert safety["classification"] == "destructive-mutation"
    assert ".agentic-workspace/WORKFLOW.md" not in safety["destructive_risk"]["planned_removals"]
    assert safety["review_required_before_apply"] is True
    scenarios = {entry["scenario"]: entry for entry in safety["fixture_coverage"]}
    assert scenarios["ambiguous ownership uninstall refuses deletion"]["status"] == "covered"


def test_uninstall_apply_refuses_workspace_payload_removal_when_ambiguous(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    workflow_path = target / ".agentic-workspace" / "WORKFLOW.md"
    ownership_path = target / ".agentic-workspace" / "OWNERSHIP.toml"
    workflow_path.write_text(workflow_path.read_text(encoding="utf-8") + "\nLocal owner edit.\n", encoding="utf-8")

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert workflow_path.exists()
    assert ownership_path.exists()
    assert (
        ".agentic-workspace/WORKFLOW.md: local workspace shared-layer file differs from managed payload; remove manually if intended"
        in payload["needs_review"]
    )
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    actions_by_path = {action["path"]: action for action in workspace_report["actions"]}
    assert actions_by_path[".agentic-workspace/OWNERSHIP.toml"]["kind"] == "skipped"
    assert "blocked by ambiguous workspace shared-layer ownership" in actions_by_path[".agentic-workspace/OWNERSHIP.toml"]["detail"]
    assert payload["lifecycle_plan"]["next_safe_command"]["status"] == "review-required"


def test_uninstall_dry_run_and_apply_agree_for_safe_managed_payloads(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    local_memory = target / ".agentic-workspace" / "local" / "memory.toml"
    local_memory.parent.mkdir(parents=True, exist_ok=True)
    local_memory.write_text('kind = "local-memory"\n', encoding="utf-8")
    agents_path = target / "AGENTS.md"
    agents_text = agents_path.read_text(encoding="utf-8")

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0
    dry_run_payload = json.loads(capsys.readouterr().out)
    dry_run_removals = set(dry_run_payload["lifecycle_plan"]["mutation_safety"]["destructive_risk"]["planned_removals"])

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    apply_payload = json.loads(capsys.readouterr().out)
    apply_removals = set(apply_payload["lifecycle_plan"]["mutation_safety"]["destructive_risk"]["planned_removals"])
    assert dry_run_removals == apply_removals
    assert ".agentic-workspace/WORKFLOW.md" in apply_removals
    assert ".agentic-workspace/OWNERSHIP.toml" in apply_removals
    assert agents_path.read_text(encoding="utf-8") == agents_text
    assert local_memory.read_text(encoding="utf-8") == 'kind = "local-memory"\n'
    assert not (target / ".agentic-workspace" / "WORKFLOW.md").exists()
    assert not (target / ".agentic-workspace" / "OWNERSHIP.toml").exists()


def test_uninstall_invokes_selected_module_uninstall(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [(module_name, command_name) for module_name, command_name, _kwargs in calls] == [("planning", "uninstall")]
    assert payload["modules"] == ["planning"]
    assert payload["reports"][0]["module"] == "planning"


def test_upgrade_apply_preserves_local_only_memory_and_integration_state(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    local_memory = target / ".agentic-workspace" / "local" / "memory.toml"
    local_integration = target / ".agentic-workspace" / "local" / "integrations" / "tool" / "state.txt"
    local_memory.parent.mkdir(parents=True, exist_ok=True)
    local_integration.parent.mkdir(parents=True)
    local_memory.write_text('kind = "local-memory"\n', encoding="utf-8")
    local_integration.write_text("private state\n", encoding="utf-8")

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert local_memory.read_text(encoding="utf-8") == 'kind = "local-memory"\n'
    assert local_integration.read_text(encoding="utf-8") == "private state\n"
    safety = payload["lifecycle_plan"]["mutation_safety"]
    assert safety["local_only_preservation"]["status"] == "preserve-by-default"
    scenarios = {entry["scenario"]: entry for entry in safety["fixture_coverage"]}
    assert scenarios["local-only memory/integration preservation"]["status"] == "covered"


@pytest.mark.parametrize(
    ("modules", "expected_modules"),
    [
        ("memory", ["memory"]),
        ("planning", ["planning"]),
        (None, ["planning", "memory"]),
    ],
)
def test_root_lifecycle_fixture_matrix_covers_upgrade_shapes(
    tmp_path: Path, capsys, modules: str | None, expected_modules: list[str]
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    init_args = ["init", "--target", str(target), "--format", "json"]
    if modules is not None:
        init_args.extend(["--modules", modules])

    assert cli.main(init_args) == 0
    capsys.readouterr()

    assert cli.main(["upgrade", "--target", str(target), "--dry-run", "--format", "json"]) == 0
    upgrade_payload = json.loads(capsys.readouterr().out)
    assert upgrade_payload["modules"] == expected_modules
    assert upgrade_payload["lifecycle_plan"]["root_upgrade_front_door"]["selected_modules"] == expected_modules

    assert cli.main(["status", "--verbose", "--target", str(target), "--format", "json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["modules"] == expected_modules

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["modules"] == expected_modules


def test_root_lifecycle_fixture_matrix_classifies_entry_states(monkeypatch, tmp_path: Path, capsys) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    _init_git_repo(empty)
    assert cli.main(["init", "--target", str(empty), "--dry-run", "--format", "json"]) == 0
    empty_payload = json.loads(capsys.readouterr().out)
    assert empty_payload["repo_state"] == "blank_or_unmanaged_repo"
    assert empty_payload["mode"] == "install"

    routing_only = tmp_path / "routing-only"
    routing_only.mkdir()
    _init_git_repo(routing_only)
    _write(routing_only / "AGENTS.md", "# Local agent instructions\n")
    _write(routing_only / ".agentic-workspace" / "bootstrap-handoff.md", "# Bootstrap handoff\n")
    assert cli.main(["init", "--target", str(routing_only), "--dry-run", "--format", "json"]) == 0
    routing_payload = json.loads(capsys.readouterr().out)
    assert routing_payload["repo_state"] == "docs_heavy_existing_repo"
    assert routing_payload["inferred_policy"] == "require_explicit_handoff"
    assert sorted(routing_payload["detected_surfaces"]) == [".agentic-workspace/bootstrap-handoff.md", "AGENTS.md"]

    partial = tmp_path / "partial"
    partial.mkdir()
    _init_git_repo(partial)
    _write(partial / "TODO.md", "# Existing TODO\n")
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(partial, calls))
    assert cli.main(["init", "--target", str(partial), "--dry-run", "--format", "json"]) == 0
    partial_payload = json.loads(capsys.readouterr().out)
    assert partial_payload["repo_state"] == "partial_or_placeholder_state"
    assert partial_payload["prompt_requirement"] == "required"
    assert "TODO.md: partial module state detected" in partial_payload["needs_review"]


def test_root_lifecycle_fixture_matrix_classifies_legacy_residue(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md",
        "# Task Context\n\n<CURRENT_FOCUS>\n",
    )
    compat_notice = "<!-- GENERATED COMPATIBILITY VIEW: authoritative source is .agentic-workspace/planning/state.toml -->"
    _write(target / "TODO.md", f"{compat_notice}\n# TODO\n")
    _write(target / "ROADMAP.md", f"{compat_notice}\n# ROADMAP\n")

    assert cli.main(["doctor", "--verbose", "--target", str(target), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    flattened_actions = [
        action
        for report in payload["reports"]
        for action in report.get("actions", [])
        if isinstance(report, dict) and isinstance(action, dict)
    ]
    assert any(
        action.get("role") == "current-memory-migration" and action.get("path") == ".agentic-workspace/memory/repo/current/task-context.md"
        for action in flattened_actions
    )
    assert any(
        action.get("kind") in {"warning", "suggested fix"}
        and action.get("path") == "ROADMAP.md"
        and "ROADMAP" in str(action.get("detail", ""))
        for action in flattened_actions
    )


def test_lifecycle_safety_payload_advertises_root_fixture_matrix(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["upgrade", "--target", str(target), "--dry-run", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    matrix = payload["lifecycle_plan"]["mutation_safety"]["fixture_matrix"]
    states = {entry["state"]: entry for entry in matrix}
    assert set(states) == {
        "empty repo",
        "routing-only installed",
        "memory-only installed",
        "planning-only installed",
        "full installed",
        "old current-memory residue",
        "old optional planning surfaces",
        "custom AGENTS.md",
        "partial managed state",
        "local-only state",
        "ambiguous ownership state",
    }
    advertised_commands = {command for entry in matrix for command in entry["commands"]}
    assert advertised_commands >= {"init", "install", "adopt", "upgrade", "uninstall", "status", "doctor"}
    assert states["old optional planning surfaces"]["expected_result"] == (
        "classified as unsupported legacy surfaces with migration/refusal guidance"
    )


def test_upgrade_preserves_repo_owned_agents_content_outside_workspace_fence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    agents_path = target / "AGENTS.md"
    original = agents_path.read_text(encoding="utf-8")
    agents_path.write_text(
        f"# Repo Instructions\n\nKeep this repo-specific guidance.\n\n{original}\nMore local instructions.\n",
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    updated = agents_path.read_text(encoding="utf-8")
    assert payload["health"] == "healthy"
    assert "# Repo Instructions" in updated
    assert "Keep this repo-specific guidance." in updated
    assert "More local instructions." in updated
    assert "<!-- agentic-workspace:workflow:start -->" in updated
    assert 'start --task "<task>"' in updated


def test_upgrade_dry_run_syncs_module_update_source_metadata_from_repo_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--modules", "planning", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'default_preset = "planning"\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert ".agentic-workspace/planning/UPGRADE-SOURCE.toml" in payload["updated_managed"]
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    assert any(
        action["path"] == ".agentic-workspace/planning/UPGRADE-SOURCE.toml" and action["kind"] == "would update"
        for action in workspace_report["actions"]
    )
