from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_config_command_reports_effective_defaults_without_repo_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    _assert_cli_compatibility(payload, status="no-expectation")
    assert payload["exists"] is False
    assert payload["edit_reference"]["reference_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["edit_reference"]["generated_reference_doc"] == "docs/reference/workspace-config.md"
    assert payload["edit_reference"]["source_schema"] == "src/agentic_workspace/contracts/schemas/workspace_config.schema.json"
    assert "# Agentic Workspace managed config." in payload["edit_reference"]["managed_header"]
    assert payload["edit_reference"]["check_command"] == "agentic-workspace config --target . --format json"
    assert payload["workspace"]["enabled"] is True
    assert payload["workspace"]["enabled_source"] == "product-default"
    assert payload["workspace"]["enabled_modules"] == ["planning", "memory"]
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
    assert payload["workspace"]["maintainer_mode"] is False
    assert payload["workspace"]["maintainer_mode_source"] == "product-default"
    assert payload["workspace"]["maintainer_mode_detail"]["status"] == "disabled"
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
    projection = payload["configuration_projection"]
    assert projection["kind"] == "agentic-workspace/configuration-projection/v1"
    assert projection["projection_status_counts"]["active"] >= 1
    assert projection["projection_status_counts"]["latent"] >= 1
    assert projection["projection_status_counts"]["unprojected"] == 0
    assert projection["unprojected_fields"] == []
    projection_sources = {field["id"] for field in projection["facts"]}
    assert {
        "ownership:authority-ledger",
        "system-intent:durable-intent",
        "verification:manifest",
        "memory:routing-metadata",
        "planning:active-state-obligations",
    } <= projection_sources
    obligation_projection = next(field for field in projection["facts"] if field["field"] == "workflow_obligations.<name>.*")
    assert obligation_projection["projection_status"] == "active"
    assert obligation_projection["source_surface"] == ".agentic-workspace/config.toml"
    assert obligation_projection["ordinary_path_routes"]
    assert obligation_projection["trigger"]
    assert "scope_tags" in obligation_projection["applicability_signal"]
    assert "hide obligation detail" in obligation_projection["suppression_rule"]
    assert obligation_projection["owner_boundary"] == "human-owned"
    local_projection = next(field for field in projection["facts"] if field["field"] == "runtime|handoff|safety|delegation_targets")
    assert local_projection["owner_boundary"] == "local-human-owned"
    assert "cannot create shared repo obligations" in local_projection["authority_exception"]
    assert projection["verification"]["positive_surfacing"][0]["id"] == "startup-config-task-routes-to-config"
    assert projection["verification"]["non_applicable_suppression"][0]["id"] == "ordinary-report-keeps-detail-sectioned"
    assert projection["detail_command"].endswith(
        "agentic-workspace report --target ./repo --section configuration_projection --format json"
    )
    surfacing_eval = projection["selective_surfacing_evaluation"]
    assert surfacing_eval["status"] == "pass"
    assert {check["id"]: check["result"] for check in surfacing_eval["checks"]} == {
        "required-guidance-present": "pass",
        "positive-and-suppression-scenarios-present": "pass",
        "irrelevant-guidance-suppressed-from-compact-output": "pass",
        "compact-output-size-bounded": "pass",
        "typed-relevance-basis-present": "pass",
    }
    assert surfacing_eval["metrics"]["projection_row_count"] == len(projection["facts"])
    relevance = {item["id"]: item for item in surfacing_eval["relevance_scenarios"]}
    assert {
        "changed-path-ownership",
        "active-planning-task-switch",
        "configured-proof-closeout",
    } <= set(relevance)
    assert {item["basis_source_type"] for item in relevance.values()} == {"explicit-state-and-contract"}
    assert relevance["changed-path-ownership"]["shown_because"] == ["state.changed_paths=present", "contract.owner_boundary"]
    assert relevance["active-planning-task-switch"]["not_based_on"] == "broad planning vocabulary"
    assert relevance["configured-proof-closeout"]["not_based_on"] == "bug/fix/test keyword matching"
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
    assert "workspace.maintainer_mode" in payload["mixed_agent"]["repo_policy"]["supported_fields"]
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
            "retention": {
                "status": "bounded",
                "run_root": ".agentic-workspace/local/scratch/runs",
                "manifest_name": ".aw-scratch.toml",
                "report_section": "local_footprint",
            },
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
                "agentic-workspace config --target ./repo --format json",
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
        "retention": {
            "status": "bounded",
            "run_root": ".agentic-workspace/local/scratch/runs",
            "manifest_name": ".aw-scratch.toml",
            "report_section": "local_footprint",
        },
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


def test_configuration_projection_reports_selector_backed_and_stale_sources(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[modules]
enabled = ["planning", "memory", "verification"]
""".strip(),
    )
    verification_manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    if verification_manifest.exists():
        verification_manifest.unlink()

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    projection = payload["configuration_projection"]
    facts = {field["id"]: field for field in projection["facts"]}
    assert facts["ownership:authority-ledger"]["projection_status"] == "selector-backed"
    assert facts["memory:routing-metadata"]["projection_status"] == "selector-backed"
    assert facts["verification:manifest"]["projection_status"] == "stale"
    assert projection["projection_status_counts"]["selector-backed"] >= 2
    assert projection["projection_status_counts"]["stale"] >= 1
    assert facts["verification:manifest"]["ordinary_path_routes"]
    assert "missing enabled manifest" in facts["verification:manifest"]["suppression_rule"]
    scenarios = {scenario["id"]: scenario["covered"] for scenario in projection["selective_surfacing_evaluation"]["scenarios"]}
    assert scenarios["selector-backed-owner-memory-intent"] is True
    assert scenarios["stale-or-unprojected-gap"] is True


def test_config_command_reports_selected_fields_for_agent_startup(tmp_path: Path, capsys) -> None:
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

    assert (
        cli.main(
            [
                "config",
                "--target",
                str(tmp_path),
                "--select",
                "workspace.improvement_latitude,workspace.optimization_bias,workspace.workflow_obligations,warnings,target,config_path",
                "--format",
                "json",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    values = payload["values"]
    assert values["warnings"] == []
    assert Path(values["target"]).name == tmp_path.name
    assert Path(values["config_path"]).as_posix().endswith(".agentic-workspace/config.toml")
    assert values["workspace.improvement_latitude"] == "proactive"
    assert values["workspace.optimization_bias"] == "agent-efficiency"
    assert values["workspace.workflow_obligations"][0]["id"] == "closeout_proof"


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

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

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
    assert payload["next_detail"]["select"].endswith("agentic-workspace config --target . --select <field.path> --format json")
    assert payload["next_detail"]["verbose"].endswith("agentic-workspace config --target . --verbose --format json")
    assert "config_effect_audit" not in payload
    assert "configuration_projection" not in payload
    assert len(output) < 3000


def test_config_command_compact_reports_projection_summary_without_fact_detail(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    full_payload = cli._config_payload(config=cli._load_workspace_config(target_root=tmp_path))
    payload = cli._compact_config_payload(full_payload)
    projection = payload["configuration_projection"]
    assert projection["status"] == "present"
    assert projection["projection_status_counts"]["active"] >= 1
    assert projection["unprojected_field_count"] == 0
    assert projection["detail_command"].endswith(
        "agentic-workspace report --target ./repo --section configuration_projection --format json"
    )
    assert "facts" not in projection


def test_config_command_accepts_reporting_improvement_latitude_mode(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "reporting"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["improvement_latitude"] == "reporting"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"


def test_config_command_accepts_agent_efficiency_optimization_bias(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\noptimization_bias = "agent-efficiency"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["optimization_bias"] == "agent-efficiency"
    assert payload["workspace"]["optimization_bias_source"] == "repo-config"


def test_config_local_maintainer_mode_overrides_host_repo_policy(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[workspace]
maintainer_mode = true
""".strip(),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace = payload["workspace"]
    assert workspace["maintainer_mode"] is True
    assert workspace["maintainer_mode_source"] == "local-override"
    assert workspace["maintainer_mode_detail"]["status"] == "enabled"
    assert workspace["maintainer_mode_detail"]["dogfooding_reports"][0]["section"] == "improvement_intake"
    assert payload["mixed_agent"]["local_override"]["maintainer_mode"] == {
        "value": True,
        "source": "local-override",
    }


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

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    partial = json.loads(capsys.readouterr().out)
    assert partial["assurance"]["onboarding"]["status"] == "absent"
    assert partial["assurance"]["onboarding"]["configured_profile_count"] == 0
    assert partial["assurance"]["onboarding"]["configured_subsystem_profile_count"] == 0

    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"

[assurance.proof_profiles.security]
required_commands = ["uv run pytest tests/security -q"]
optional_commands = []
review_aids = []

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
requirement_refs = ["docs/requirements.md#auditability"]
required_evidence = ["requirement_grounding"]
force = "required-before-closeout"
""",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    usable = json.loads(capsys.readouterr().out)
    assert usable["assurance"]["onboarding"]["status"] == "usable"
    assert usable["assurance"]["onboarding"]["configured_profile_count"] == 1
    assert usable["assurance"]["onboarding"]["configured_subsystem_profile_count"] == 1
    assert usable["assurance"]["onboarding"]["host_ref_count"] == 1
    assert ".agentic-workspace/config.toml [assurance.subsystem_profiles]" in usable["assurance"]["onboarding"]["candidate_seed_surfaces"]


def test_config_command_reports_assurance_requirements(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["db/migrations/**"]
applies_to_task_markers = ["privacy"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted", "risk_assessment"]
proof_profile = "privacy"
workflow_obligation_refs = ["privacy_review"]
review_owner = "privacy-review"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]

[assurance.requirements.privacy_data.waiver]
reason = "Covered by existing privacy review for this migration class."
owner = "privacy-review"
""",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    requirement = payload["assurance"]["requirements"][0]
    assert requirement["id"] == "privacy_data"
    assert requirement["level"] == "high"
    assert requirement["applies_to_paths"] == ["db/migrations/**"]
    assert requirement["required_evidence"] == ["authority_consulted", "risk_assessment"]
    assert requirement["force"] == "required-before-closeout"
    assert requirement["blocking_claims"] == ["claim-work-complete", "close-parent-lane"]
    assert requirement["waiver"]["status"] == "recorded"
    assert requirement["waiver"]["owner"] == "privacy-review"


def test_config_command_rejects_assurance_requirement_without_activation_signal(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.no_signal]
level = "high"
force = "required-before-closeout"
required_evidence = ["authority_consulted"]
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "requires at least one activation signal" in capsys.readouterr().err


def test_config_command_requires_assurance_requirement_level_and_force(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.missing_level]
applies_to_paths = ["docs/**"]
force = "required-before-closeout"

[assurance.requirements.missing_force]
level = "high"
applies_to_paths = ["src/**"]
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "missing_force force is required" in capsys.readouterr().err

    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.missing_level]
applies_to_paths = ["docs/**"]
force = "required-before-closeout"
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "missing_level level is required" in capsys.readouterr().err


def test_config_command_rejects_invalid_assurance_requirement_claim(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.bad_claim]
level = "high"
applies_to_paths = ["docs/**"]
force = "required-before-closeout"
blocking_claims = ["certify-compliant"]
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "blocking_claims entries must be one of" in capsys.readouterr().err


def test_config_command_reports_enabled_advanced_features(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nadvanced_features = ["review_artifacts", "external_adapters"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["warnings"] == [".agentic-workspace/config.toml contains unsupported top-level field(s): unsupported_top_level."]


def test_config_command_autodetects_conservative_system_intent_sources_when_no_explicit_source_declared(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# README\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Repo Instructions\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "product-direction.md").write_text("Repo direction hint\n", encoding="utf-8")

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["system_intent"]["sources"] == ["README.md", "AGENTS.md", "docs/product-direction.md"]
    assert payload["workspace"]["system_intent"]["sources_source"] == "autodetected-existing"
    assert payload["workspace"]["system_intent"]["preferred_source"] == "README.md"


def test_config_command_autodetects_existing_supported_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "GEMINI.md").write_text("# Gemini\n")

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["GEMINI.md"]


def test_config_command_autodetects_claude_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "CLAUDE.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["CLAUDE.md"]


def test_config_command_autodetects_legacy_cursor_rules_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".cursorrules").write_text("Use repo conventions.\n", encoding="utf-8")

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

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
        assert cli.main(["config", "--verbose", "--format", "json"]) == 0
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

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

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
        'agent_instructions_file = "GEMINI.md"\n'
        'workflow_artifact_profile = "gemini"\n'
        'improvement_latitude = "balanced"\n\n'
        "[modules]\n"
        'enabled = ["planning"]\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is True
    assert payload["workspace"]["enabled_modules"] == ["planning"]
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

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["exists"] is True
    assert payload["mixed_agent"]["local_override"]["applied"] is True
    assert payload["mixed_agent"]["local_override"]["status"] == "applied"
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {
        "value": True,
        "source": "local-override",
    }


def test_config_command_layers_shared_local_config_below_repo_local_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    shared = tmp_path / "agentic-workspace.local.toml"
    shared.write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'cli_invoke = "python -c \\"import sys; from agentic_workspace.cli import main; '
        'raise SystemExit(main(sys.argv[1:]))\\""\n\n'
        "[runtime]\n"
        "strong_planner_available = true\n"
        "cheap_bounded_executor_available = false\n\n"
        "[delegation]\n"
        'mode = "manual"\n\n'
        "[local_memory]\n"
        "enabled = true\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        f'shared_config_path = "{shared.as_posix()}"\n\n'
        "[runtime]\n"
        "cheap_bounded_executor_available = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["cli_invoke"] == (
        'python -c "import sys; from agentic_workspace.cli import main; raise SystemExit(main(sys.argv[1:]))"'
    )
    assert payload["workspace"]["cli_invoke_source"] == "shared-local-config"
    local_override = payload["mixed_agent"]["local_override"]
    assert local_override["shared_config"] == {
        "path": shared.as_posix(),
        "exists": True,
        "applied": True,
        "status": "applied",
    }
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {
        "value": True,
        "source": "shared-local-config",
    }
    assert payload["mixed_agent"]["effective_posture"]["cheap_bounded_executor_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["delegation_mode"] == {
        "value": "manual",
        "source": "shared-local-config",
    }
    assert payload["mixed_agent"]["local_memory"]["source"] == "shared-local-config"
    assert payload["warnings"] == []


def test_config_command_warns_when_shared_local_config_is_missing(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[workspace]\nshared_config_path = "../missing.local.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["shared_config"]["status"] == "missing"
    assert payload["warnings"] == [
        f".agentic-workspace/config.local.toml workspace.shared_config_path points to missing file: {(tmp_path / 'missing.local.toml').as_posix()}."
    ]


def test_config_command_resolves_relative_shared_local_config_from_repo_root(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    shared = tmp_path / "aw.config.shared.toml"
    shared.write_text('schema_version = 1\n\n[delegation]\nmode = "manual"\n', encoding="utf-8")
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[workspace]\nshared_config_path = "../aw.config.shared.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["shared_config"] == {
        "path": shared.as_posix(),
        "exists": True,
        "applied": True,
        "status": "applied",
    }
    assert payload["mixed_agent"]["effective_posture"]["delegation_mode"] == {
        "value": "manual",
        "source": "shared-local-config",
    }
    assert payload["warnings"] == []


def test_config_command_reports_local_only_memory_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[local_memory]\nenabled = true\npath = ".agentic-workspace/local/memory.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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
        cli.main(["config", "--verbose", "--target", str(target), "--format", "json"])
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

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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


def test_config_command_reports_assignment_policy_separate_from_delegation_mode(tmp_path: Path, capsys) -> None:
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
                'execution_role = "orchestrator"',
                'assignment_policy = "required-best-fit"',
                'selection_objective = "minimize successful completion cost after quality and proof"',
                'current_target = "codex_current"',
                'underfit_behavior = "require-delegation"',
                'down_routing_behavior = "bounded-mechanical-work"',
                'human_override_policy = "allowed-with-recorded-reason"',
                'manual_transport_policy = "required-when-no-automatic-method"',
                "",
                "[delegation_targets.codex_current]",
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    policy = payload["local_runtime"]["assignment_policy"]
    assert policy["status"] == "configured"
    assert policy["execution_role"] == {"value": "orchestrator", "source": "local-override"}
    assert policy["assignment_policy"] == {"value": "required-best-fit", "source": "local-override"}
    assert policy["current_target"] == {"value": "codex_current", "source": "local-override"}
    assert policy["current_target_status"] == "known-profile"
    assert policy["binding"] == {
        "required_best_fit_requested": True,
        "enforceable": True,
        "claim_boundary": "assignment policy resolved",
    }


def test_config_command_blocks_required_best_fit_when_current_target_is_unknown(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'execution_role = "orchestrator"',
                'assignment_policy = "required-best-fit"',
                'current_target = "missing_profile"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    policy = payload["local_runtime"]["assignment_policy"]
    assert policy["status"] == "blocked-unknown-current-target"
    assert policy["current_target_status"] == "unknown"
    assert policy["binding"]["enforceable"] is False
    assert "cannot be claimed" in policy["binding"]["claim_boundary"]


def test_config_command_layers_assignment_policy_from_shared_local_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    shared = tmp_path / "aw.config.shared.toml"
    shared.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'execution_role = "orchestrator"',
                'assignment_policy = "best-fit-advisory"',
                'current_target = "shared_current"',
                'underfit_behavior = "prepare-manual-escalation"',
                "",
                "[delegation_targets.shared_current]",
                'strength = "strong"',
                'execution_methods = ["manual"]',
            ]
        ),
        encoding="utf-8",
    )
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[workspace]",
                f'shared_config_path = "{shared.as_posix()}"',
                "",
                "[delegation]",
                'assignment_policy = "required-best-fit"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    policy = payload["mixed_agent"]["assignment_policy"]
    assert policy["execution_role"] == {"value": "orchestrator", "source": "shared-local-config"}
    assert policy["assignment_policy"] == {"value": "required-best-fit", "source": "local-override"}
    assert policy["current_target"] == {"value": "shared_current", "source": "shared-local-config"}
    assert policy["underfit_behavior"] == {"value": "prepare-manual-escalation", "source": "shared-local-config"}
    assert policy["binding"]["enforceable"] is True


def test_config_command_rejects_invalid_local_delegation_control_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation]\nmode = "delegate-everything"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(target), "--format", "json"])
    assert "delegation.mode must be one of" in capsys.readouterr().err


def test_config_command_rejects_invalid_assignment_policy_value(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation]\nassignment_policy = "self-confidence"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(target), "--format", "json"])
    assert "assignment_policy must be one of" in capsys.readouterr().err


def test_config_command_reports_runtime_resolution_for_no_posture(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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
        cli.main(["config", "--verbose", "--target", str(target), "--format", "json"])
    assert "strength must be one of" in capsys.readouterr().err


def test_config_command_accepts_utf8_bom_local_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_docs]\nstrength = "weak"\nexecution_methods = ["cli"]\n',
        encoding="utf-8-sig",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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
    evidence = payload["mixed_agent"]["target_evidence"]
    assert evidence["status"] == "present"
    assert evidence["storage"] == {
        "path": ".agentic-workspace/delegation-outcomes.json",
        "location": "local-only",
        "checked_in": False,
        "exists": True,
        "safe_to_remove": True,
        "raw_transcripts_stored": False,
    }
    assert evidence["record_count"] == 3
    assert evidence["normalized_records"][0]["target"] == "gpt_5_4_mini"
    assert evidence["normalized_records"][0]["admission_state"] == "accepted-normalized"
    assert evidence["normalized_records"][0]["routing_relevance"] == "task-class-bound"
    assert evidence["suitability"] == [
        {
            "target": "gpt_5_4_mini",
            "profile_status": "configured",
            "record_count": 3,
            "average_signal": 1.42,
            "route_effect": "preferred-for-matching-task-class",
            "uncertainty": "low",
            "supported_task_classes": ["bounded-docs", "narrow-tests"],
            "irrelevance_rule": "Only records for matching task/scope classes may affect assignment for that class.",
            "raw_history_retention": "bounded-local-ledger",
        }
    ]
    decision = payload["mixed_agent"]["assignment_decision"]
    assert decision["kind"] == "agentic-workspace/assignment-decision/v1"
    assert decision["assignment_policy"] == "local-preferred"
    assert decision["decision"] == "keep-local"
    assert decision["record_count"] == 3


def test_repo_config_cli_invoke_sets_repo_owned_invocation_policy(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["cli_invoke"] == "uv run agentic-workspace"
    assert payload["workspace"]["cli_invoke_source"] == "repo-config"
    assert payload["warnings"] == []


def test_local_config_cli_invoke_overrides_repo_owned_invocation_policy(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "python -c \\"import sys; '
        "from agentic_workspace.cli import main; "
        'raise SystemExit(main(sys.argv[1:]))\\""\n',
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["cli_invoke"] == (
        'python -c "import sys; from agentic_workspace.cli import main; raise SystemExit(main(sys.argv[1:]))"'
    )
    assert payload["workspace"]["cli_invoke_source"] == "local-override"
    assert payload["warnings"] == []


def test_local_config_can_disable_workspace_operation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace" / "config.toml", "schema_version = 1\n")
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[workspace]\nenabled = false\n",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["enabled"] is False
    assert payload["workspace"]["enabled_source"] == "local-override"
    assert payload["warnings"] == []


def test_local_config_can_reenable_repo_disabled_workspace_operation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace" / "config.toml", "schema_version = 1\n\n[workspace]\nenabled = false\n")
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[workspace]\nenabled = true\n",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["enabled"] is True
    assert payload["workspace"]["enabled_source"] == "local-override"
    assert payload["warnings"] == []


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

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

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
