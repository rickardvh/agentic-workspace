from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_config_command_reports_effective_defaults_without_repo_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    _assert_cli_compatibility(payload, status="no-expectation")
    assert payload["exists"] is False
    assert payload["edit_reference"]["reference_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["edit_reference"]["generated_reference_doc"] == "docs/reference/workspace-config.md"
    assert payload["edit_reference"]["source_schema"] == "src/agentic_workspace/contracts/schemas/workspace_config.schema.json"
    assert "# Agentic Workspace managed config." in payload["edit_reference"]["managed_header"]
    assert payload["edit_reference"]["check_command"] == "agentic-workspace config --target . --profile tiny --format json"
    assert payload["workspace"]["default_preset"] == "full"
    assert payload["workspace"]["agent_instructions_file"] == "AGENTS.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "product-default"
    assert payload["workspace"]["workflow_artifact_profile"] == "repo-owned"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "product-default"
    assert payload["workspace"]["improvement_latitude"] == "conservative"
    assert payload["workspace"]["improvement_latitude_source"] == "product-default"
    assert payload["workspace"]["optimization_bias"] == "balanced"
    assert payload["workspace"]["optimization_bias_source"] == "product-default"
    assert payload["workspace"]["advanced_features"] == []
    assert payload["workspace"]["advanced_features_source"] == "product-default"
    assert payload["workspace"]["supported_advanced_features"] == ["review_artifacts", "external_adapters"]
    assert payload["workspace"]["workflow_artifact_adapter"]["canonical_surfaces"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/",
    ]
    assert payload["workspace"]["agent_configuration_substrate"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["workspace"]["agent_configuration_substrate"]["owner_surface"] == ".agentic-workspace/config.toml"
    assert payload["workspace"]["workflow_obligations"] == []
    assert payload["config_enforcement"]["field_count_by_class"]["hard"] >= 1
    assert any(field["field"] == "workspace.improvement_latitude" for field in payload["config_enforcement"]["fields"])
    assert payload["config_effect_audit"]["status"] == "present"
    assert payload["config_effect_audit"]["field_count_by_effect"]["operational"] >= 1
    assert payload["config_effect_audit"]["field_count_by_effect"]["unused"] == 0
    assert payload["config_effect_audit"]["detail_command"].endswith(
        "agentic-workspace report --target ./repo --section config_effect_audit --format json"
    )
    assert payload["update"]["wrapper_rule"] == "normal update execution stays behind agentic-workspace"
    assert {item["module"] for item in payload["update"]["modules"]} == {"planning", "memory"}
    assert {item["freshness"]["status"] for item in payload["update"]["modules"]} == {"unknown"}
    assert payload["assurance"]["default_level"] == "low"
    assert payload["assurance"]["default_level_source"] == "product-default"
    assert payload["assurance"]["onboarding"]["status"] == "absent"
    assert payload["assurance"]["onboarding"]["configured_profile_count"] == 0
    assert payload["mixed_agent"]["status"] == "reporting-only"
    assert payload["mixed_agent"]["repo_policy"]["source"] == "product-defaults"
    assert payload["mixed_agent"]["repo_policy"]["path"] == ".agentic-workspace/config.toml"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is False
    assert payload["mixed_agent"]["local_override"]["path"] == ".agentic-workspace/config.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["exists"] is False
    assert payload["mixed_agent"]["local_override"]["applied"] is False
    assert payload["mixed_agent"]["local_integration_area"] == {
        "root": ".agentic-workspace/local/integrations",
        "subfolder_convention": "<vendor-or-runtime>/",
        "example_subfolder": ".agentic-workspace/local/integrations/codex",
        "scratch": {
            "root": ".agentic-workspace/local/scratch",
            "status": "ready-local-only",
            "exists": False,
            "git_ignored": True,
            "authoritative": False,
            "safe_to_delete": True,
            "sign": "Go ahead and use this for whatever temporary working files you need.",
        },
        "status": "available-local-only",
        "exists": False,
        "authoritative": False,
        "git_ignored": True,
        "canonical_doc": ".agentic-workspace/docs/local-integration-area.md",
        "runtime_artifact_shim_pattern": {
            "kind": "agentic-workspace/local-runtime-artifact-shim/v1",
            "root": ".agentic-workspace/local/integrations",
            "status": "local-only-pattern",
            "authoritative": False,
            "git_ignored": True,
            "use_for": [
                "internal agent plans that need compact checked-in planning updates",
                "runtime check bundles that need compact pass/fail plus inspectable logs",
                "handoff or resume state that needs a bounded workspace continuation record",
                "runtime-native planning systems that the agent is already optimized or hardwired to use",
            ],
            "bridge_rule": (
                "Use runtime-native plans as private working memory when they help, but bridge decisions, scope, proof, "
                "and continuation into checked-in Agentic Workspace Planning before implementation handoff or closeout."
            ),
            "preferred_bridge_steps": [
                "capture the runtime-native plan or todo list under the local integration area when it is useful evidence",
                "summarize only durable intent, scope, proof, and next action into checked-in planning state",
                "run agentic-workspace summary --format json after the bridge and resolve warnings before implementation",
            ],
            "artifact_classes": ["internal-plan", "check-bundle", "handoff-state", "runtime-export"],
            "metadata_required": [
                "kind",
                "source_runtime",
                "artifact_class",
                "input_owner",
                "output_target",
                "authority",
                "promotion_target",
                "proof_command",
                "created_at",
            ],
            "compact_output": "short agent-facing status, next action, and proof pointer",
            "full_evidence": "inspectable local artifact, manifest, command log, or exported source file",
            "promotion_boundary": [
                "local shims never become shared authority by existing locally",
                "promote only through checked-in planning, memory, agent-aid, docs, or repo-native review surfaces",
                "record proof before treating shim output as repo-shared state",
                "a runtime-native plan or todo list does not satisfy required Agentic Workspace Planning until bridged",
            ],
            "discovery": [
                "agentic-workspace defaults --section agent_aid_storage --format json",
                "agentic-workspace config --target ./repo --profile tiny --format json",
                "agentic-workspace report --target ./repo --section agent_aids --format json",
            ],
        },
        "allowed_aid_kinds": [
            "prompt helpers",
            "export/import shims",
            "local wrappers",
            "native-workflow adapters",
            "resumable handoff helpers",
            "runtime scratch files",
        ],
        "boundary_rules": [
            "local-only and ignored by git",
            "optional for ordinary workspace commands",
            "non-authoritative for planning, memory, startup, review, and workflow state",
            "safe to delete without changing repo-owned shared behavior",
            "not a plugin registry or shared compatibility framework",
        ],
        "rule": "local-only vendor/runtime aids; may reduce local operating cost, but must not become shared workflow authority",
    }
    assert payload["mixed_agent"]["local_scratch"] == {
        "root": ".agentic-workspace/local/scratch",
        "status": "ready-local-only",
        "exists": False,
        "git_ignored": True,
        "authoritative": False,
        "safe_to_delete": True,
        "sign": "Go ahead and use this for whatever temporary working files you need.",
    }
    agent_aids = payload["mixed_agent"]["agent_aid_storage"]
    assert agent_aids["canonical_doc"] == ".agentic-workspace/docs/agent-aids-storage.md"
    assert agent_aids["candidate_root"] == ".agentic-workspace/agent-aids"
    assert agent_aids["candidate_subdirs"] == [
        "scripts",
        "skills",
        "runbooks",
        "prompts",
        "checks",
        "templates",
        "module-components",
    ]
    assert [entry["class"] for entry in agent_aids["storage_classes"][:3]] == [
        "local-only",
        "checked-in-candidate",
        "promoted-repo-native",
    ]
    assert payload["mixed_agent"]["local_memory"]["status"] == "disabled"
    assert payload["mixed_agent"]["local_memory"]["path"] == ".agentic-workspace/local/memory.toml"
    assert payload["mixed_agent"]["local_memory"]["authoritative"] is False
    assert payload["mixed_agent"]["runtime_inference"]["tool_owned"] is True
    assert payload["mixed_agent"]["runtime_inference"]["reported_here"] is False
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {"value": None, "source": "unset"}
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {"value": None, "source": "unset"}
    assert payload["mixed_agent"]["delegated_run_guardrail"]["status"] == "present"
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["lower_trust_profiles"] == []
    assert payload["mixed_agent"]["success_measures"] == [
        "lower long-run token cost",
        "lower restart and handoff cost",
        "cheap switching across agents and subscriptions",
        "persisted shared knowledge beats rediscovery",
    ]


def test_config_command_reports_compact_profile_for_agent_startup(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workspace]
improvement_latitude = "proactive"
optimization_bias = "agent-efficiency"

[workflow_obligations.closeout_proof]
summary = "Run closeout proof before reporting done."
stage = "closeout"
scope_tags = ["closeout"]
commands = ["make check"]
""".strip(),
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[delegation]
mode = "suggest"

[clarification]
mode = "ask-first"

[safety]
safe_to_auto_run_commands = false
""".strip(),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--profile", "compact", "--format", "json"]) == 0

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["kind"] == "agentic-workspace/config-compact/v1"
    assert payload["profile"] == "compact"
    assert payload["warnings"] == []
    assert payload["target"] == "."
    assert payload["config_path"] == ".agentic-workspace/config.toml"
    assert "mixed_agent" not in payload
    assert payload["workspace"]["improvement_latitude"] == "proactive"
    assert payload["workspace"]["optimization_bias"] == "agent-efficiency"
    assert payload["workspace"]["workflow_obligations"][0]["id"] == "closeout_proof"
    assert payload["reporting_posture"]["repo_policy"]["improvement_latitude"] == "proactive"
    assert payload["reporting_posture"]["citation_rule"].startswith("Final answers should cite repo-relative")
    assert payload["local_runtime"]["delegation_mode"] == {"value": "suggest", "source": "local-override"}
    assert payload["local_runtime"]["clarification_mode"] == {"value": "ask-first", "source": "local-override"}
    assert payload["local_runtime"]["safe_to_auto_run_commands"] == {"value": False, "source": "local-override"}
    assert payload["edit_reference"]["check_command"] == "agentic-workspace config --target . --profile tiny --format json"
    assert payload["full_profile_command"] == "agentic-workspace config --target . --profile full --format json"
    assert len(output) < 10000


def test_config_command_reports_tiny_profile_for_config_posture(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workspace]
improvement_latitude = "reporting"
optimization_bias = "agent-efficiency"
cli_invoke = "uv run agentic-workspace"

[workflow_obligations.closeout_proof]
summary = "Run closeout proof before reporting done."
stage = "closeout"
scope_tags = ["closeout"]
commands = ["make check"]
""".strip(),
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[delegation]
mode = "suggest"

[clarification]
mode = "ask-first"

[safety]
safe_to_auto_run_commands = false
requires_human_verification_on_pr = true
""".strip(),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--profile", "tiny", "--format", "json"]) == 0

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["kind"] == "agentic-workspace/config-tiny/v1"
    assert payload["profile"] == "tiny"
    assert not any("clarification" in warning for warning in payload["warnings"])
    assert payload["workspace"]["agent_instructions_file"] == "AGENTS.md"
    assert payload["workspace"]["improvement_latitude"] == "reporting"
    assert payload["workspace"]["optimization_bias"] == "agent-efficiency"
    assert payload["workspace"]["workflow_obligation_ids"] == ["closeout_proof"]
    assert payload["local_runtime"]["delegation_mode"] == {"value": "suggest", "source": "local-override"}
    assert payload["local_runtime"]["clarification_mode"] == {"value": "ask-first", "source": "local-override"}
    assert payload["local_runtime"]["safe_to_auto_run_commands"] == {"value": False, "source": "local-override"}
    assert payload["local_runtime"]["requires_human_verification_on_pr"] == {"value": True, "source": "local-override"}
    assert payload["next_detail"]["compact"].endswith("agentic-workspace config --target . --profile compact --format json")
    assert "config_effect_audit" not in payload
    assert len(output) < 3000


def test_config_command_accepts_reporting_improvement_latitude_mode(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "reporting"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["improvement_latitude"] == "reporting"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"


def test_config_command_accepts_agent_efficiency_optimization_bias(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\noptimization_bias = "agent-efficiency"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["optimization_bias"] == "agent-efficiency"
    assert payload["workspace"]["optimization_bias_source"] == "repo-config"


def test_config_command_reports_assurance_onboarding_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
""",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    partial = json.loads(capsys.readouterr().out)
    assert partial["assurance"]["onboarding"]["status"] == "partial"
    assert partial["assurance"]["onboarding"]["configured_profile_count"] == 0

    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
decision_record_target = "docs/decisions/"

[assurance.proof_profiles.security]
required_commands = ["uv run pytest tests/security -q"]
optional_commands = []
review_aids = []
""",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    usable = json.loads(capsys.readouterr().out)
    assert usable["assurance"]["onboarding"]["status"] == "usable"
    assert usable["assurance"]["onboarding"]["configured_profile_count"] == 1
    assert usable["assurance"]["onboarding"]["host_ref_count"] == 1


def test_config_command_reports_enabled_advanced_features(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nadvanced_features = ["review_artifacts", "external_adapters"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["advanced_features"] == ["review_artifacts", "external_adapters"]
    assert payload["workspace"]["advanced_features_source"] == "repo-config"


def test_config_command_reports_workflow_obligations_from_repo_config(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workflow_obligations.adapter_surface_refresh]\n"
        'summary = "Refresh adapter surfaces."\n'
        'stage = "before-claiming-completion"\n'
        'scope_tags = ["workspace", "adapter-surfaces"]\n'
        'commands = ["make maintainer-surfaces"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["workflow_obligations"][0]["id"] == "adapter_surface_refresh"
    assert payload["workspace"]["workflow_obligations"][0]["stage"] == "before-claiming-completion"
    assert payload["workspace"]["workflow_obligations"][0]["force"] == "required-before-closeout"
    assert payload["workspace"]["workflow_obligations"][0]["commands"] == ["make maintainer-surfaces"]


def test_config_command_accepts_explicit_workflow_obligation_force(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n"
        "[workflow_obligations.inspect_before_review]\n"
        'summary = "Inspect config effect before review."\n'
        'stage = "review"\n'
        'force = "blocking"\n'
        'scope_tags = ["workspace"]\n'
        'commands = ["agentic-workspace report --target . --section config_effect_audit --format json"]\n',
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    obligation = payload["workspace"]["workflow_obligations"][0]
    assert obligation["id"] == "inspect_before_review"
    assert obligation["force"] == "blocking"


def test_config_command_reports_system_intent_source_declaration(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[system_intent]\n"
        'sources = ["SYSTEM_INTENT.md", "docs/product-direction.md"]\n'
        'preferred_source = "docs/product-direction.md"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["system_intent"]["sources"] == ["SYSTEM_INTENT.md", "docs/product-direction.md"]
    assert payload["workspace"]["system_intent"]["preferred_source"] == "docs/product-direction.md"
    assert payload["workspace"]["system_intent"]["mirror_path"] == ".agentic-workspace/system-intent/intent.toml"


def test_config_command_warns_about_unsupported_top_level_repo_config_fields(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\nunsupported_top_level = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["warnings"] == [".agentic-workspace/config.toml contains unsupported top-level field(s): unsupported_top_level."]


def test_config_command_autodetects_conservative_system_intent_sources_when_no_explicit_source_declared(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# README\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Repo Instructions\n", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("Repo direction hint\n", encoding="utf-8")

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["system_intent"]["sources"] == ["README.md", "AGENTS.md", "llms.txt"]
    assert payload["workspace"]["system_intent"]["sources_source"] == "autodetected-existing"
    assert payload["workspace"]["system_intent"]["preferred_source"] == "README.md"


def test_config_command_autodetects_existing_supported_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "GEMINI.md").write_text("# Gemini\n")

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["GEMINI.md"]


def test_config_command_autodetects_claude_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "CLAUDE.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["CLAUDE.md"]


def test_config_command_autodetects_legacy_cursor_rules_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".cursorrules").write_text("Use repo conventions.\n", encoding="utf-8")

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == ".cursorrules"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == [".cursorrules"]


def test_config_command_accepts_custom_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        'schema_version = 1\n\n[workspace]\nagent_instructions_file = "docs/agent-instructions.md"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "docs/agent-instructions.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "repo-config"


def test_config_command_discovers_workspace_root_from_subdirectory(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "balanced"\n',
        encoding="utf-8",
    )
    nested = tmp_path / "src" / "agentic_workspace"
    nested.mkdir(parents=True)
    previous_cwd = Path.cwd()
    monkeypatch.chdir(nested)
    try:
        assert cli.main(["config", "--profile", "full", "--format", "json"]) == 0
    finally:
        monkeypatch.chdir(previous_cwd)

    payload = json.loads(capsys.readouterr().out)
    assert payload["target"] == tmp_path.as_posix()
    assert payload["config_path"] == (tmp_path / ".agentic-workspace/config.toml").as_posix()
    assert payload["workspace"]["improvement_latitude"] == "balanced"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"


def test_config_command_surfaces_unknown_local_override_fields_as_warnings(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                "",
                "[runtime]",
                "supports_internal_delegation = true",
                "mystery_flag = true",
                "",
                "[delegation_targets.gpt_5_4_mini]",
                'strength = "weak"',
                'location = "either"',
                'execution_methods = ["internal"]',
                'unexpected = "note"',
            )
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["exists"] is True
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["warnings"] == [
        ".agentic-workspace/config.local.toml [runtime] contains unsupported field(s): mystery_flag.",
        ".agentic-workspace/config.local.toml delegation_targets.gpt_5_4_mini contains unsupported field(s): unexpected.",
    ]


def test_config_command_reports_repo_owned_overrides(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'default_preset = "planning"\n'
        'agent_instructions_file = "GEMINI.md"\n'
        'workflow_artifact_profile = "gemini"\n'
        'improvement_latitude = "balanced"\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is True
    assert payload["workspace"]["default_preset"] == "planning"
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "repo-config"
    assert payload["workspace"]["workflow_artifact_profile"] == "gemini"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "repo-config"
    assert payload["workspace"]["improvement_latitude"] == "balanced"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"
    assert payload["workspace"]["workflow_artifact_adapter"]["native_artifacts"] == [
        "implementation_plan.md",
        "task.md",
        "walkthrough.md",
    ]
    planning_policy = next(item for item in payload["update"]["modules"] if item["module"] == "planning")
    assert planning_policy["source"] == "repo-config"
    assert planning_policy["source_ref"] == "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"
    assert planning_policy["source_label"] == "planning feature ref"
    assert planning_policy["recommended_upgrade_after_days"] == 14
    assert payload["mixed_agent"]["repo_policy"]["source"] == "repo-config"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is True


def test_config_command_reports_reserved_local_override_presence_without_applying_it(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n[runtime]\nsupports_internal_delegation = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["exists"] is True
    assert payload["mixed_agent"]["local_override"]["applied"] is True
    assert payload["mixed_agent"]["local_override"]["status"] == "applied"
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {
        "value": True,
        "source": "local-override",
    }


def test_config_command_reports_local_only_memory_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[local_memory]\nenabled = true\npath = ".agentic-workspace/local/memory.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    local_memory = payload["mixed_agent"]["local_memory"]
    assert local_memory["status"] == "enabled"
    assert local_memory["enabled"] is True
    assert local_memory["configured"] is True
    assert local_memory["path"] == ".agentic-workspace/local/memory.toml"
    assert local_memory["controlled_by"] == ".agentic-workspace/config.local.toml"
    assert local_memory["authoritative"] is False
    assert local_memory["advisory_only"] is True
    assert "not a secret store" in local_memory["boundary_rules"]


def test_config_command_reports_narrow_local_override_fields_with_source_attribution(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[runtime]\n"
        "supports_internal_delegation = true\n"
        "strong_planner_available = true\n"
        "cheap_bounded_executor_available = true\n\n"
        "[handoff]\n"
        "prefer_internal_delegation_when_available = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["cheap_bounded_executor_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["prefer_internal_delegation_when_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["derived_mode"]["planner_executor_pattern"] == "strong-planner-cheap-executor-available"
    assert payload["mixed_agent"]["derived_mode"]["handoff_preference"] == "prefer-internal-when-safe"


def test_config_command_reports_local_delegation_target_profiles(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[delegation_targets.fast_docs]\n"
        'strength = "weak"\n'
        'location = "external"\n'
        "confidence = 0.58\n"
        'task_fit = ["bounded-docs", "narrow-tests"]\n'
        'capability_classes = ["mechanical-follow-through"]\n'
        'execution_methods = ["cli"]\n\n'
        "[delegation_targets.primary_planner]\n"
        'strength = "strong"\n'
        'location = "local"\n'
        "confidence = 0.92\n"
        'model_family = "gpt-5.5"\n'
        'provider = "openai"\n'
        'context_capacity = "large"\n'
        'reasoning_profile = "strong"\n'
        'cost_class = "premium"\n'
        'latency_class = "slow"\n'
        'capability_classes = ["boundary-shaping", "reasoning-heavy"]\n'
        'safe_task_classes = ["boundary-shaping", "reasoning-heavy"]\n'
        'forbidden_task_classes = ["mechanical-follow-through"]\n'
        'escalation_target = "human"\n'
        'confidence_source = "local-evaluation"\n'
        'last_evaluation = "2026-05-04"\n'
        'human_control_modes = ["manual", "suggest"]\n'
        'execution_methods = ["internal", "api"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]
    assert targets["status"] == "configured"
    fast_docs = next(item for item in targets["profiles"] if item["name"] == "fast_docs")
    assert fast_docs["strength"] == "weak"
    assert fast_docs["location"] == "external"
    assert fast_docs["confidence"] == 0.58
    assert fast_docs["task_fit"] == ["bounded-docs", "narrow-tests"]
    assert fast_docs["capability_classes"] == ["mechanical-follow-through"]
    assert fast_docs["execution_methods"] == ["cli"]
    assert fast_docs["advisory"] == {
        "handoff_detail": "high",
        "review_burden": "high",
    }
    assert fast_docs["closeout_gate"]["trust"] == "lower-trust"
    assert "target strength is weak" in fast_docs["closeout_gate"]["reasons"]
    planner = next(item for item in targets["profiles"] if item["name"] == "primary_planner")
    assert planner["location"] == "local"
    assert planner["model_family"] == "gpt-5.5"
    assert planner["provider"] == "openai"
    assert planner["context_capacity"] == "large"
    assert planner["reasoning_profile"] == "strong"
    assert planner["cost_class"] == "premium"
    assert planner["latency_class"] == "slow"
    assert planner["capability_classes"] == ["boundary-shaping", "reasoning-heavy"]
    assert planner["safe_task_classes"] == ["boundary-shaping", "reasoning-heavy"]
    assert planner["forbidden_task_classes"] == ["mechanical-follow-through"]
    assert planner["escalation_target"] == "human"
    assert planner["confidence_source"] == "local-evaluation"
    assert planner["last_evaluation"] == "2026-05-04"
    assert planner["human_control_modes"] == ["manual", "suggest"]
    assert planner["execution_methods"] == ["internal", "api"]
    assert planner["advisory"] == {
        "handoff_detail": "compact",
        "review_burden": "light",
    }
    assert planner["closeout_gate"]["trust"] == "normal"
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["lower_trust_profiles"] == ["fast_docs"]
    posture_effect = payload["mixed_agent"]["delegated_run_guardrail"]["local_posture_effect"]
    assert posture_effect["status"] == "configured"
    assert posture_effect["configured_profiles"] == ["fast_docs", "primary_planner"]
    assert posture_effect["proof_burden"].startswith("lower-trust profiles require")


def test_config_command_rejects_invalid_local_target_reasoning_profile(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.worker]",
                'strength = "weak"',
                'execution_methods = ["cli"]',
                'reasoning_profile = "omniscient"',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"])
    assert "reasoning_profile must be one of" in capsys.readouterr().err


def test_config_command_reports_local_delegation_control_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[safety]",
                "safe_to_auto_run_commands = false",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[delegation_targets.local_worker]",
                'strength = "medium"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    control = payload["mixed_agent"]["delegation_control"]
    assert control["configured_mode"] == "auto"
    assert control["effective_mode"] == "suggest"
    assert control["execution_permitted"] is False
    assert control["disabled_reason"] == "delegation.mode is auto, but safety.safe_to_auto_run_commands is not true"
    assert payload["mixed_agent"]["effective_posture"]["delegation_mode"] == {
        "value": "auto",
        "source": "local-override",
    }


def test_config_command_rejects_invalid_local_delegation_control_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation]\nmode = "delegate-everything"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"])
    assert "delegation.mode must be one of" in capsys.readouterr().err


def test_config_command_reports_runtime_resolution_for_no_posture(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    rr = payload["mixed_agent"]["runtime_resolution"]
    assert rr["recommendation"] in ("stay-local", "stronger-reasoning", "external-delegation", "manual-handoff")
    assert rr["posture_source"] == "none"
    assert rr["confidence"] in ("high", "medium", "low")
    assert "guidance" in rr
    assert rr["resolution_categories"] == [
        "stay-local",
        "stronger-reasoning",
        "external-delegation",
        "manual-handoff",
    ]


def test_config_command_runtime_resolution_recommends_external_delegation_when_strong_external_preferred(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                "confidence = 0.9",
                'capability_classes = ["boundary-shaping", "reasoning-heavy"]',
                'execution_methods = ["cli"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    # Without posture the default resolution is generated; just confirm structure is valid
    rr = payload["mixed_agent"]["runtime_resolution"]
    assert rr["recommendation"] in ("stay-local", "stronger-reasoning", "external-delegation", "manual-handoff")
    assert rr["profile_recommendations"][0]["name"] == "chatgpt"
    assert rr["profile_recommendations"][0]["recommendation"] in ("recommended", "acceptable", "poor-fit")
    assert "strong_handoff_packet" in payload["mixed_agent"]


def test_config_command_runtime_resolution_recommends_stronger_reasoning_for_boundary_shaping_with_strong_planner(
    tmp_path: Path, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[runtime]",
                "strong_planner_available = true",
                "cheap_bounded_executor_available = true",
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "boundary-shaping", "recommended strength": "strong"},
    )
    assert rr["recommendation"] == "stronger-reasoning"
    assert rr["confidence"] == "high"
    assert any("boundary-shaping" in r for r in rr["reasons"])
    assert rr["posture_source"] == "provided"


def test_config_command_runtime_resolution_recommends_stay_local_for_mechanical_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )
    assert rr["recommendation"] == "stay-local"
    assert rr["confidence"] == "high"
    assert any("mechanical-follow-through" in r for r in rr["reasons"])
    assert rr["weak_target_guardrail"]["status"] == "inactive"
    assert rr["downrouting_guardrail"]["status"] == "inactive"


def test_runtime_resolution_marks_weak_target_escalation_for_boundary_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "suggest"',
                "",
                "[delegation_targets.haiku]",
                'strength = "weak"',
                'location = "external"',
                "confidence = 0.7",
                'task_fit = ["bounded docs edits"]',
                'capability_classes = ["mechanical-follow-through"]',
                'execution_methods = ["cli"]',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "boundary-shaping", "recommended strength": "strong"},
    )

    haiku = rr["profile_recommendations"][0]
    assert haiku["name"] == "haiku"
    assert haiku["recommendation"] == "poor-fit"
    assert haiku["capability_mismatch"] is True
    assert haiku["required_action"] == "escalate-before-execution"
    assert rr["weak_target_guardrail"]["status"] == "active"
    assert rr["weak_target_guardrail"]["effective_mode"] == "suggest"
    assert "do not execute the weak target automatically" in rr["weak_target_guardrail"]["mode_action"]
    assert rr["weak_target_guardrail"]["mismatched_targets"][0]["name"] == "haiku"
    assert rr["self_assessment"]["authority"] == "advisory-only"
    assert "capability_mismatch" in rr["self_assessment"]["cannot_override"]


def test_runtime_resolution_marks_strong_target_downrouting_for_mechanical_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "suggest"',
                "",
                "[delegation_targets.haiku]",
                'strength = "weak"',
                'location = "external"',
                "confidence = 0.7",
                'task_fit = ["bounded docs edits"]',
                'capability_classes = ["mechanical-follow-through"]',
                'execution_methods = ["cli"]',
                "",
                "[delegation_targets.strong_planner]",
                'strength = "strong"',
                'location = "local"',
                "confidence = 0.9",
                'task_fit = ["architecture", "review"]',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mechanical-follow-through"]',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )

    strong = next(item for item in rr["profile_recommendations"] if item["name"] == "strong_planner")
    assert strong["required_action"] == "delegate-down-when-safe"
    assert strong["overqualified_for_task"] is True
    assert rr["downrouting_guardrail"]["status"] == "active"
    assert rr["downrouting_guardrail"]["cheaper_fit_targets"][0]["name"] == "haiku"
    assert "cheaper bounded executor" in rr["downrouting_guardrail"]["mode_action"]


def test_runtime_resolution_respects_forbidden_task_classes(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.fast_worker]",
                'strength = "strong"',
                'execution_methods = ["cli"]',
                'capability_classes = ["mechanical-follow-through"]',
                'forbidden_task_classes = ["mechanical-follow-through"]',
                'reasoning_profile = "strong"',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )

    worker = rr["profile_recommendations"][0]
    assert worker["recommendation"] == "poor-fit"
    assert worker["capability_mismatch"] is True
    assert worker["required_action"] == "escalate-before-execution"
    assert "target forbids this execution class" in worker["reasons"]


def test_config_command_runtime_resolution_recommends_manual_handoff_when_strong_external_preferred_and_no_external_targets(
    tmp_path: Path, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"strong external reasoning": "preferred"},
    )
    assert rr["recommendation"] == "manual-handoff"
    assert rr["confidence"] == "high"
    assert any("no automated external path" in r for r in rr["reasons"])


def test_config_command_accepts_manual_external_delegation_target(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "AGENTS.md").write_text("repo instructions\n", encoding="utf-8")
    (target / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                "confidence = 0.88",
                'task_fit = ["general-purpose-planning", "cross-cutting-review"]',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed"]',
                'execution_methods = ["manual"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]["profiles"]
    chatgpt = next(profile for profile in targets if profile["name"] == "chatgpt")
    assert chatgpt["strength"] == "strong"
    assert chatgpt["location"] == "external"
    assert chatgpt["capability_classes"] == ["boundary-shaping", "reasoning-heavy", "mixed"]
    assert chatgpt["execution_methods"] == ["manual"]
    assert chatgpt["advisory"] == {
        "handoff_detail": "compact",
        "review_burden": "light",
    }


def test_config_command_rejects_invalid_local_delegation_target_strength(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.bad_target]\nstrength = "expert"\nexecution_methods = ["cli"]\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"])
    assert "strength must be one of" in capsys.readouterr().err


def test_config_command_accepts_utf8_bom_local_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_docs]\nstrength = "weak"\nexecution_methods = ["cli"]\n',
        encoding="utf-8-sig",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["delegation_targets"]["profiles"][0]["name"] == "fast_docs"


def test_note_delegation_outcome_command_writes_local_artifact(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert (
        cli.main(
            [
                "note-delegation-outcome",
                "--target",
                str(target),
                "--delegation-target",
                "gpt_5_4_mini",
                "--task-class",
                "bounded-docs",
                "--outcome",
                "success",
                "--handoff-sufficiency",
                "sufficient",
                "--review-burden",
                "light",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == ".agentic-workspace/delegation-outcomes.json"
    assert payload["record_count"] == 1
    artifact = json.loads((target / ".agentic-workspace/delegation-outcomes.json").read_text(encoding="utf-8"))
    assert artifact["kind"] == "agentic-workspace/delegation-outcomes/v1"
    assert artifact["records"][0]["delegation_target"] == "gpt_5_4_mini"


def test_config_command_reports_delegation_outcome_suggestions(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[delegation_targets.gpt_5_4_mini]\n"
        'strength = "weak"\n'
        'location = "external"\n'
        "confidence = 0.62\n"
        'task_fit = ["bounded-docs"]\n'
        'capability_classes = ["mechanical-follow-through"]\n'
        'execution_methods = ["cli"]\n',
        encoding="utf-8",
    )
    (target / ".agentic-workspace/delegation-outcomes.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/delegation-outcomes/v1",
                "records": [
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "bounded-docs",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "light",
                        "escalation_required": False,
                    },
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "narrow-tests",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "normal",
                        "escalation_required": False,
                    },
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "narrow-tests",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "light",
                        "escalation_required": False,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]
    assert targets["outcome_artifact"] == {
        "path": ".agentic-workspace/delegation-outcomes.json",
        "status": "configured",
        "record_count": 3,
    }
    mini = targets["profiles"][0]
    assert mini["location"] == "external"
    assert mini["capability_classes"] == ["mechanical-follow-through"]
    assert mini["outcome_evidence"]["record_count"] == 3
    assert mini["outcome_evidence"]["confidence"]["action"] == "raise"
    assert mini["outcome_evidence"]["task_fit"]["suggest_add"] == ["narrow-tests"]


def test_repo_config_cli_invoke_is_ignored_as_machine_local_policy(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["cli_invoke"] == "agentic-workspace"
    assert payload["workspace"]["cli_invoke_source"] == "product-default"
    assert payload["warnings"] == [".agentic-workspace/config.toml [workspace] contains unsupported field(s): cli_invoke."]


def test_config_reports_satisfied_repo_owned_cli_compatibility_expectation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n"
        "[cli_compatibility]\n"
        'enforcement = "blocking"\n'
        'minimum_version = "0.0.0"\n'
        'source_classes = ["source-checkout"]\n'
        'target_relations = ["outside-target"]\n'
        'command = "uv run agentic-workspace"\n',
    )

    assert cli.main(["config", "--profile", "full", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    compatibility = _assert_cli_compatibility(payload, status="satisfied")
    assert compatibility["configured"] is True
    assert compatibility["enforcement"] == "blocking"
    assert compatibility["expected_command"] == "uv run agentic-workspace"
    assert compatibility["failed_checks"] == []
    checks = {check["name"]: check for check in compatibility["checks"]}
    assert checks["minimum_version"]["satisfied"] is True
    assert checks["source_class"]["satisfied"] is True
    assert checks["target_relation"]["satisfied"] is True
