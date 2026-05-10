from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_report_surfaces_config_ownership_drift_diagnostic(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "planning"]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\ndefault_preset = "planning"\ncurrent_task = "handoff detail"\n',
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--section", "ownership_diagnostics", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    findings = {finding["id"]: finding for finding in payload["answer"]["findings"]}
    assert findings["config-active-state"]["concern"] == "active execution state"
    assert findings["config-active-state"]["suspected_drift_surface"] == ".agentic-workspace/config.toml"


def test_report_real_init_summarizes_combined_workspace_state(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    _assert_cli_compatibility(payload, status="no-expectation")
    _assert_cli_compatibility_schema(payload, schema_name="workspace_report.schema.json")
    assert payload["kind"] == "workspace-report/v1"
    assert payload["command"] == "report"
    assert payload["schema"]["schema_version"] == "workspace-reporting-schema/v1"
    assert payload["schema"]["command"] == "agentic-workspace report --target ./repo --format json"
    assert "discovery" in payload["schema"]["shared_fields"]
    assert "standing_intent" in payload["schema"]["shared_fields"]
    assert "repo_friction" in payload["schema"]["shared_fields"]
    assert "output_contract" in payload["schema"]["shared_fields"]
    assert "operating_posture" in payload["schema"]["shared_fields"]
    assert "config_enforcement" in payload["schema"]["shared_fields"]
    assert "agent_configuration_queries" in payload["schema"]["shared_fields"]
    assert "system_intent_mirror" in payload["schema"]["shared_fields"]
    assert "workflow_obligations" in payload["schema"]["shared_fields"]
    assert "execution_shape" in payload["schema"]["shared_fields"]
    assert "external_work_delta" in payload["schema"]["shared_fields"]
    assert "successful_completion_cost" in payload["schema"]["shared_fields"]
    assert "module_reports" in payload["schema"]["shared_fields"]
    assert payload["selected_modules"] == ["planning", "memory"]
    assert payload["installed_modules"] == ["planning", "memory"]
    assert payload["feature_tier"]["active"]["id"] == "full"
    assert payload["feature_tier"]["active"]["modules"] == ["planning", "memory"]
    assert payload["feature_tier"]["active"]["source"] == "installed_modules"
    assert payload["feature_tier"]["default_rule"].startswith("Use the smallest module profile")
    assert payload["feature_tier"]["compatibility_status"] == "deprecated-alias-for-module-profiles"
    assert "maintainer-dogfooding" not in {tier["id"] for tier in payload["feature_tier"]["available_tiers"]}
    assert payload["health"] == "healthy"
    assert payload["output_contract"]["optimization_bias"] == "balanced"
    assert payload["output_contract"]["optimization_bias_source"] == "product-default"
    assert payload["output_contract"]["surface"] == "report"
    assert payload["output_contract"]["rendered_view_style"] == "brief-explanatory"
    assert payload["output_contract"]["verbosity_budget"]["default_detail"] == "router-with-brief-context"
    assert payload["output_contract"]["surface_boundary"]["honors_bias"][1] == "rendered human-facing views"
    assert "ownership semantics" in payload["output_contract"]["surface_boundary"]["stays_invariant"]
    operating_posture = payload["operating_posture"]
    assert operating_posture["kind"] == "agentic-workspace/operating-posture/v1"
    assert operating_posture["improvement_latitude"]["mode"] == "conservative"
    assert operating_posture["optimization_bias"]["mode"] == "balanced"
    assert "report useful incidental findings compactly even when not acting" in operating_posture["required_behaviors"]
    assert operating_posture["closeout_nudge"]["field"] == "improvement_signal_review"
    assert payload["config_enforcement"]["status"] == "present"
    assert any(route["field"] == "workspace.optimization_bias" for route in payload["config_enforcement"]["weak_field_routes"])
    assert "config_effect_audit" in payload["schema"]["shared_fields"]
    assert payload["config_effect_audit"]["kind"] == "workspace-config-effect-audit/v1"
    assert payload["config_effect_audit"]["field_count_by_effect"]["advisory-operational"] >= 3
    assert payload["config_effect_audit"]["claimed_vs_actual_warnings"] == []
    assert payload["agent_configuration_system"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["agent_configuration_system"]["startup_entrypoint"] == "AGENTS.md"
    assert payload["agent_configuration_system"]["workflow_artifact_profile"] == "repo-owned"
    assert payload["agent_configuration_system"]["module_attachment_status"][0]["module"] == "planning"
    assert payload["agent_configuration_queries"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["agent_configuration_queries"]["current_work_status"] == "no-active-direction"
    assert payload["agent_configuration_queries"]["current_queries"][0]["id"] == "startup_path"
    assert payload["system_intent_mirror"]["mirror_surface"] == ".agentic-workspace/system-intent/intent.toml"
    assert payload["system_intent_mirror"]["mirror"]["status"] in {"missing", "present"}
    assert payload["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert "durable_intent" in payload["schema"]["shared_fields"]
    assert payload["workflow_obligations"]["configured_count"] == 0
    assert payload["workflow_obligations"]["match_evidence"]["match_count"] == 0
    assert payload["workflow_obligations"]["relevant_to_current_work"] == []
    assert "product_managed_enclave" in payload["schema"]["shared_fields"]
    enclave = payload["product_managed_enclave"]
    assert enclave["managed_root"] == ".agentic-workspace/"
    assert enclave["startup_quietness"]["status"] == "compact"
    assert enclave["local_only_state"]["status"] == "non-authoritative"
    assert enclave["boundary_leaks"] == []
    assert "AGENTS.md managed workflow pointer fence only" in enclave["removability"]["would_affect"]
    assert payload["execution_shape"]["status"] == "present"
    assert payload["execution_shape"]["task_shape"]["id"] == "direct-or-no-active-plan"
    assert payload["execution_shape"]["narrow_work_fast_path"]["status"] == "blessed"
    assert payload["execution_shape"]["recommendation"]["id"] == "stay-direct"
    assert payload["execution_shape"]["recommendation"]["consult"] == ["agentic-workspace config --target ./repo --format json"]
    assert payload["next_action"]["summary"] == "No immediate action"
    assert not any(
        item["surface"] == ".agentic-workspace/docs/capability-aware-execution.md" for item in payload["discovery"]["memory_candidates"]
    )
    assert any(item["surface"] == ".agentic-workspace/planning/state.toml" for item in payload["discovery"]["planning_candidates"])
    assert payload["discovery"]["ambiguous"] == []
    assert payload["standing_intent"]["canonical_doc"] == ".agentic-workspace/docs/standing-intent-contract.md"
    assert payload["standing_intent"]["precedence_order"][0]["source"] == "explicit_current_human_instruction"
    assert payload["standing_intent"]["precedence_order"][1]["source"] == "active_directional_intent"
    assert payload["standing_intent"]["precedence_order"][2]["source"] == "config_policy"
    assert payload["standing_intent"]["supersession_rules"][0]["rule"] == "newer_same_owner_replaces_older"
    stronger_home = payload["standing_intent"]["stronger_home_model"]
    assert stronger_home["candidate_classes"][0]["class"] == "repo_doctrine"
    assert stronger_home["decision_test"]["promote_to_config_when"][0].startswith("the standing guidance should be machine-readable")
    assert all("current_owner" in example for example in stronger_home["examples"])
    assert "checked-in policy" in payload["standing_intent"]["effective_view"]["conflict_rule"]
    assert payload["standing_intent"]["effective_view"]["in_force_count"] == 3
    standing_classes = {item["class"]: item for item in payload["standing_intent"]["effective_view"]["items"]}
    assert standing_classes["config_policy"]["status"] == "present"
    assert standing_classes["repo_doctrine"]["status"] == "present"
    assert standing_classes["durable_understanding"]["status"] == "present"
    assert standing_classes["active_directional_intent"]["status"] == "absent"
    assert standing_classes["enforceable_workflow"]["status"] == "absent"
    assert payload["repo_friction"]["policy_mode"] == "conservative"
    assert payload["repo_friction"]["owner_surface"] == "workspace"
    assert payload["repo_friction"]["policy_target"] == "repo-directed-improvement"
    assert payload["repo_friction"]["workspace_self_adaptation"]["status"] == "allowed-with-bounds"
    assert payload["repo_friction"]["friction_response_order"][0]["action"] == "adapt-inside-workspace-first"
    assert "validation friction" in payload["repo_friction"]["guardrail_test"]["surface_repo_friction_when"][0]
    threshold = payload["repo_friction"]["repo_directed_improvement_threshold"]
    assert threshold["status"] == "explicit-contract"
    assert "two independent friction confirmations" in threshold["minimum_threshold"][0]
    assert threshold["not_enough"][1] == "one contributor or one model preferring a different repo shape"
    assert payload["repo_friction"]["initiative_posture"] == "local-touched-scope-only"
    assert payload["repo_friction"]["reporting_destinations"] == [
        "agentic-workspace report --target ./repo --format json",
        ".agentic-workspace/planning/state.toml or the active execplan when repeated friction deserves promotion",
    ]
    assert payload["repo_friction"]["evidence_classes"] == [
        "large_file_hotspots",
        "concept_surface_hotspots",
        "planning_friction",
        "validation_friction",
    ]
    assert payload["repo_friction"]["large_file_hotspots"]["threshold_lines"] == 400
    assert payload["repo_friction"]["concept_surface_hotspots"]["threshold_lines"] == 200
    assert payload["repo_friction"]["planning_friction"]["status"] == "explicit-contract"
    assert "unclear_seam" in payload["repo_friction"]["planning_friction"]["subtypes"]
    assert payload["repo_friction"]["validation_friction"]["status"] == "explicit-contract"
    assert "weak_seam" in payload["repo_friction"]["validation_friction"]["subtypes"]
    assert "ordinary bug-fixing" in payload["repo_friction"]["validation_friction"]["distinguish_from"][0]
    failure_classes = {item["class"]: item for item in payload["repo_friction"]["validation_friction"]["failure_classification"]}
    assert failure_classes["user_or_content_error"]["interface_design_signal"] is False
    assert failure_classes["interface_design_error"]["interface_design_signal"] is True
    assert payload["repo_friction"]["validation_friction"]["correct_by_design_remedy_order"][:3] == [
        "scaffold",
        "writer_helper",
        "alias",
    ]
    assert payload["repo_friction"]["external_evidence"] == []
    assert payload["repo_friction"]["capture_shortcut"]["status"] == "available"
    assert "observed friction" in payload["repo_friction"]["capture_shortcut"]["minimum_record"]
    assert "surface_value_guardrail" in payload["schema"]["shared_fields"]
    assert payload["surface_value_guardrail"]["preference_order"][0] == "remove an unnecessary surface"
    assert payload["surface_value_guardrail"]["first_contact_budget"]["status"] == "active"
    assert payload["surface_value_guardrail"]["review_result"]["accept_when"][1] == "ownership and authority class are explicit"
    assert "effective_authority" in payload["schema"]["shared_fields"]
    assert "operational_compression" in payload["schema"]["shared_fields"]
    effective_authority = payload["effective_authority"]
    assert effective_authority["status"] == "ready"
    authority_by_concern = {entry["concern"]: entry for entry in effective_authority["authority_map"]}
    assert authority_by_concern["active plan and continuation"]["status"] == "absent"
    assert authority_by_concern["durable repo knowledge"]["status"] == "present"
    assert effective_authority["unresolved_gaps"] == []
    assert effective_authority["idle_context"][0]["id"] == "no-active-planning-record"
    assert effective_authority["system_intent_embodiment"]["anti_framework_pressure"][0] == "remove an unnecessary surface"
    assert payload["reports"][0]["module"] == "planning"
    assert {report["module"] for report in payload["module_reports"]} == {"planning", "memory"}
    planning_report = next(report for report in payload["module_reports"] if report["module"] == "planning")
    memory_report = next(report for report in payload["module_reports"] if report["module"] == "memory")
    assert planning_report["schema"]["command"] == "agentic-planning report --format json"
    assert memory_report["schema"]["command"] == "agentic-memory report --target ./repo --format json"
    assert payload["config"]["mixed_agent"]["status"] == "reporting-only"
    operational_compression = payload["operational_compression"]
    assert operational_compression["kind"] == "workspace-operational-compression/v1"
    assert operational_compression["advisory_only"] is True
    measures = operational_compression["measures"]
    assert measures["default_report_size_or_warning_count"]["warning_count"] == len(payload["findings"])
    assert measures["routed_memory_pull_size"]["sources"] == [
        "memory.habitual_pull.evidence",
        "memory.durable_facts.routing_measure",
    ]
    assert measures["unresolved_external_work_routing"]["provider_rule"].startswith(
        "Core planning only consumes provider-agnostic external work evidence"
    )


def test_report_default_profile_returns_router_before_deep_detail(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-report-router/v1"
    assert payload["schema"]["full_profile_command"] == "agentic-workspace report --target ./repo --profile full --format json"
    assert payload["schema"]["section_command"] == "agentic-workspace report --target ./repo --section <section> --format json"
    assert payload["report_profile"]["default_profile"] == "router"
    assert payload["report_profile"]["full_profile"] == "full"
    assert payload["report_profile"]["full_profile_cost"]["classification"] == "deep-audit"
    assert payload["report_profile"]["full_profile_cost"]["expected_cost"] == "high"
    assert payload["report_profile"]["context_router"]["first_view"] == "start"
    assert payload["report_profile"]["config_enforcement"]["detail_section"] == "config_enforcement"
    assert payload["report_profile"]["config_effect_audit"]["detail_section"] == "config_effect_audit"
    assert payload["report_profile"]["config_effect_audit"]["warning_count"] == 0
    assert payload["report_profile"]["decision_grade_fields"][0] == "health"
    ordinary_path = payload["report_profile"]["ordinary_agent_path"]
    assert ordinary_path["entry_command"] == "agentic-workspace start --target ./repo --format json"
    assert ordinary_path["current_work_command"] == "agentic-workspace summary --format json"
    assert ordinary_path["proof_command"] == "agentic-workspace proof --target ./repo --changed <paths> --format json"
    recovery = ordinary_path["off_happy_path_recovery"]
    assert recovery["kind"] == "workspace-off-happy-path-recovery/v1"
    assert set(recovery["scenario_ids"]) >= {
        "opened-report-before-start",
        "opened-deep-review-artifact",
        "invalid-near-miss-command",
        "direct-generated-adapter-edit",
        "hand-authored-durable-artifact",
    }
    assert recovery["recover_by_default"] == "agentic-workspace start --target ./repo --format json"
    assert "report_profile.ordinary_agent_path" in payload["report_profile"]["decision_grade_fields"]
    guard = payload["report_profile"]["router_shape_guard"]
    assert guard["status"] == "active"
    assert len(payload) <= guard["max_top_level_fields"]
    assert payload["report_profile"]["feature_tier"]["active"]["id"] == "full"
    assert "available_tiers" not in payload["report_profile"]["feature_tier"]

    assert "report_profile.feature_tier" in payload["report_profile"]["decision_grade_fields"]
    assert len(payload["warning_summary"]["sample"]) <= guard["warning_sample_limit"]
    for section in guard["high_volume_sections_excluded"]:
        assert section not in payload
    assert payload["health"] == "healthy"
    assert "module_reports" not in payload
    assert "reports" not in payload
    assert "maintenance_pressure" not in payload
    assert payload["report_profile"]["feature_tier"]["advanced_policy"]["enabled_features"] == []
    assert "operational_compression" not in payload
    assert "closeout_trust" not in payload
    assert "external_work_delta" not in payload
    assert payload["operating_posture"]["surface"] == "report"
    assert payload["operating_posture"]["closeout_nudge"]["field"] == "improvement_signal_review"
    assert payload["execution_shape"]["task_shape_recommender"]["status"] == "available"
    assert payload["execution_shape"]["narrow_work_fast_path"]["status"] == "blessed"
    intake = payload["improvement_intake"]
    assert intake["kind"] == "workspace-improvement-intake/v1"
    assert intake["role"] == "router-not-backlog"
    assert intake["detail_section"] == "improvement_intake"
    assert isinstance(intake["candidate_count"], int)
    assert len(intake["candidate_sample"]) <= 3
    assert intake["subtypes"] == [
        "setup_finding",
        "review_finding",
        "validation_friction",
        "memory_improvement_signal",
        "repair_recurrence",
    ]
    assert "dogfooding_friction" not in json.dumps(intake, sort_keys=True)
    assert "improvement_intake" in payload["report_profile"]["decision_grade_fields"]
    reconciliation = payload["external_work_reconciliation"]
    assert reconciliation["kind"] == "planning-external-work-reconciliation/v1"
    assert "external_work_reconciliation" in payload["report_profile"]["decision_grade_fields"]
    assert payload["surface_value_guardrail"]["first_contact_budget"]["status"] == "active"
    assert payload["deeper_detail"]["high_volume_sections"][0]["section"] == "module_reports"
    section_hints = {item["section"]: item for item in payload["section_hints"]}
    assert section_hints["module_reports"]["volume"] == "high"
    assert "compact router field" in section_hints["module_reports"]["why_now"]
    assert "maintenance_pressure" not in section_hints
    assert section_hints["improvement_intake"]["volume"] == "normal"
    assert "improvement signal" in section_hints["improvement_intake"]["why_now"]
    assert section_hints["external_work_reconciliation"]["volume"] == "normal"
    assert "external-work" in section_hints["external_work_reconciliation"]["purpose_summary"]
    assert "operational_compression" not in section_hints
    assert "external_work_delta" not in section_hints
    assert section_hints["operating_posture"]["volume"] == "normal"
    assert "improvement posture" in section_hints["operating_posture"]["why_now"]
    assert "idle context" in section_hints["effective_authority"]["purpose_summary"]
    assert "idle state" in section_hints["effective_authority"]["why_now"]
    assert section_hints["effective_authority"]["command"] == (
        "agentic-workspace report --target ./repo --section effective_authority --format json"
    )
    assert len(json.dumps(payload, sort_keys=True)) < 30000

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]) == 0
    closeout_payload = json.loads(capsys.readouterr().out)
    closeout_answer = closeout_payload["answer"]
    assert "historical_review_artifacts" not in closeout_answer
    assert closeout_answer["strict_closeout_gate"]["status"] == "disabled"
    assert closeout_answer["terminal_action"]["blocking"] is False
    assert "what changes closure" not in json.dumps(closeout_answer).lower()
    assert closeout_answer["checks"]["package_workflow_evidence"]["status"] == "not-applicable"
    assert closeout_answer["checks"]["intent_satisfaction"]["reason"] == "no active planning record"
    historical_reviews = closeout_answer["evidence_summary"]["historical_review_artifacts"]
    assert historical_reviews["status"] == "evidence-only"
    assert "not ordinary operating input" in historical_reviews["role"]
    assert "retention_policy_status" in historical_reviews
    assert historical_reviews["detail"].endswith("report --target ./repo --profile full --format json")

    assert cli.main(["report", "--target", str(target), "--section", "operating_posture", "--format", "json"]) == 0
    posture_payload = json.loads(capsys.readouterr().out)
    posture = posture_payload["answer"]
    assert posture["kind"] == "agentic-workspace/operating-posture/v1"
    assert posture["closeout_nudge"]["field"] == "improvement_signal_review"
    assert posture["boundaries"]["not_blanket_refactor_permission"] is True


def test_report_tiny_profile_alias_returns_router(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--profile", "tiny", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-report-router/v1"
    assert payload["report_profile"]["default_profile"] == "router"
    assert "module_reports" not in payload


def test_report_section_returns_config_effect_audit(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[runtime]",
                "strong_planner_available = true",
                "cheap_bounded_executor_available = true",
            ]
        ),
    )

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "config_effect_audit", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"section": "config_effect_audit"}
    assert answer["kind"] == "workspace-config-effect-audit/v1"
    assert answer["field_count_by_effect"]["local-advisory"] >= 1
    assert any(effect["field"] == "runtime|handoff|safety|delegation_targets" for effect in answer["agent_dependent_fields"])
    assert answer["claimed_vs_actual_warnings"] == []


def test_report_router_uses_resolved_cli_invoke_for_copyable_commands(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"]["full_profile_command"] == "uv run agentic-workspace report --target ./repo --profile full --format json"
    assert payload["report_profile"]["default_command"] == "uv run agentic-workspace report --target ./repo --format json"
    ordinary_path = payload["report_profile"]["ordinary_agent_path"]
    assert ordinary_path["entry_command"] == "uv run agentic-workspace start --target ./repo --format json"
    assert ordinary_path["state_command"] == "uv run agentic-workspace report --target ./repo --format json"
    assert ordinary_path["current_work_command"] == "uv run agentic-workspace summary --format json"
    assert ordinary_path["proof_command"] == "uv run agentic-workspace proof --target ./repo --changed <paths> --format json"
    recovery = ordinary_path["off_happy_path_recovery"]
    assert recovery["recover_by_default"] == "uv run agentic-workspace start --target ./repo --format json"
    assert payload["section_hints"][0]["command"].startswith("uv run agentic-workspace report ")
    if "maintenance_pressure" in payload:
        assert payload["maintenance_pressure"]["subcategories"][0]["section_command"].startswith("uv run agentic-workspace report ")


def test_report_section_agent_aids_discovers_checked_in_and_local_aids(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    aid_root = target / ".agentic-workspace" / "agent-aids" / "scripts"
    candidate_manifest = {
        "kind": "agentic-workspace/agent-aid/v1",
        "id": "workspace-validation-wrapper",
        "type": "script",
        "status": "candidate",
        "scope": "repo-shared",
        "portability": "cross-platform",
        "proof_role": "candidate-aid",
        "owner": "workspace",
        "created_because": "Agents repeatedly need a bounded validation wrapper.",
        "use_when": ["validating workspace CLI and contract changes"],
        "entrypoint": ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py",
        "safety": {
            "read_only": True,
            "writes_repo": False,
            "destructive": False,
            "network": False,
            "hidden_required_workflow": False,
            "requires_review": False,
        },
        "validation": {"commands": ["uv run python .agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"]},
        "promotion": {
            "target_kind": "check",
            "target": "scripts/check/check_workspace_validation.py",
            "discovery_route": "repo-check",
            "trigger": "used successfully across multiple closeouts",
            "retention_after_promotion": "delete",
        },
        "retirement": {"trigger": "obsolete", "retention_after_retirement": "delete"},
    }
    retired_manifest = {**candidate_manifest, "id": "old-helper", "status": "retired"}
    (aid_root / "workspace-validation" / "manifest.json").write_text(json.dumps(candidate_manifest), encoding="utf-8")
    (aid_root / "old-helper" / "manifest.json").write_text(json.dumps(retired_manifest), encoding="utf-8")
    (target / ".agentic-workspace" / "local" / "integrations" / "codex" / "README.md").write_text(
        "# Local aids\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--section", "agent_aids", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert answer["kind"] == "workspace-agent-aids-discovery/v1"
    assert "storage" not in answer
    assert answer["storage_summary"]["candidate_root"] == ".agentic-workspace/agent-aids"
    assert answer["storage_summary"]["manifest_check"] == "python scripts/check/check_agent_aids.py"
    assert answer["summary"]["checked_in_count"] == 2
    assert answer["summary"]["visible_checked_in_count"] == 1
    assert answer["summary"]["retired_count"] == 1
    assert answer["summary"]["local_only_container_count"] == 1
    assert answer["creation_affordance"]["agent_may_create"] is True
    assert answer["creation_affordance"]["first_pattern"]["makefile_variable"] == "COMPACT_RUN"
    assert answer["creation_affordance"]["first_pattern"]["timeout_option"] == "--timeout-seconds <seconds>"
    candidate = next(entry for entry in answer["checked_in_aids"] if entry["id"] == "workspace-validation-wrapper")
    assert candidate["type"] == "script"
    assert candidate["status"] == "candidate"
    assert candidate["scope"] == "repo-shared"
    assert candidate["portability"] == "cross-platform"
    assert candidate["entrypoint"].endswith("workspace_validation.py")
    assert candidate["safety_summary"]["read_only"] is True
    assert candidate["canonical_proof_route"] is False
    assert candidate["promotion_summary"]["target_kind"] == "check"
    assert candidate["promotion_summary"]["discovery_route"] == "repo-check"
    assert candidate["promotion_summary"]["retention_after_promotion"] == "delete"
    assert [entry["id"] for entry in answer["recommended_actions"]] == ["workspace-validation-wrapper"]
    recommended = answer["recommended_actions"][0]
    assert recommended["risk"] == "candidate or advisory aid; inspect safety and portability before use"
    assert recommended["command"] == 'agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert recommended["run"] == recommended["command"]
    assert recommended["required_inputs"] == ["current task", "aid safety summary", "proof role"]
    assert "declared validation" in recommended["next_proof"]
    assert answer["recommended_action_omitted_count"] == 0
    primary_action = answer["primary_next_action"]
    assert primary_action["action"] == "use-agent-aid"
    assert primary_action["id"] == "workspace-validation-wrapper"
    assert primary_action["command"] == recommended["command"]
    assert primary_action["required_inputs"] == ["current task", "aid safety summary", "proof role"]
    assert answer["local_only"]["entries"][0]["id"] == "codex"
    assert answer["local_only"]["entries"][0]["authority"] == "none"


def test_report_section_agent_aids_routes_empty_discovery_to_repeat_friction_review(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "agent_aids", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "storage" not in payload["answer"]
    assert payload["answer"]["storage_summary"]["canonical_doc"] == ".agentic-workspace/docs/agent-aids-storage.md"
    action = payload["answer"]["primary_next_action"]
    assert action["action"] == "create-bounded-aid-when-it-reduces-friction"
    assert action["command"] == 'agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert action["run"] == action["command"]
    assert action["required_inputs"] == ["current task", "friction evidence", "authority boundary"]
    assert "ordinary compact routes" in action["summary"]
    assert "handoff cost" in action["summary"]
    assert "checked in" in action["next_proof"]


def test_report_improvement_intake_keeps_dogfooding_source_checkout_only(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / "pyproject.toml", '[project]\nname = "agentic-workspace"\n')
    (target / "src" / "agentic_workspace").mkdir(parents=True)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    intake = payload["improvement_intake"]
    assert intake["audience_boundary"]["status"] == "source-checkout"
    assert intake["subtypes"] == [
        "setup_finding",
        "dogfooding_friction",
        "review_finding",
        "validation_friction",
        "memory_improvement_signal",
        "repair_recurrence",
    ]


def test_report_surfaces_review_retention_cleanup_pressure(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    review_dir = target / ".agentic-workspace" / "planning" / "reviews"
    docs_review_dir = target / "docs" / "reviews"
    docs_review_dir.mkdir(parents=True)
    _write_json(review_dir / "missing.review.json", {"kind": "planning-review/v1", "title": "Missing Retention"})
    _write_json(
        review_dir / "resolved.review.json",
        {
            "kind": "planning-review/v1",
            "title": "Resolved Review",
            "issue_classifications": [
                {
                    "id": "#1",
                    "classification": "evidence-present",
                    "live_state": "closed",
                    "resolution": "implemented",
                }
            ],
            "retention": {
                "closeout shape": "shrink after findings are routed",
                "trigger": "after issue closeout",
                "proof surface": "report closeout_trust",
            },
            "padding": [f"line {index}" for index in range(90)],
        },
    )
    _write(docs_review_dir / "historical.md", "# Historical Review\n\nImplemented and superseded.\n")

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]) == 0

    closeout_payload = json.loads(capsys.readouterr().out)
    historical_summary = closeout_payload["answer"]["evidence_summary"]["historical_review_artifacts"]
    assert historical_summary["retention_policy_status"] == "attention"
    assert historical_summary["retention_candidate_count"] >= 2
    assert "historical_review_artifacts" not in closeout_payload["answer"]

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    full_payload = json.loads(capsys.readouterr().out)
    retention = full_payload["closeout_trust"]["historical_review_artifacts"]["retention_policy"]
    assert retention["status"] == "attention"
    assert retention["artifact_count"] >= 3
    assert retention["missing_retention_metadata_count"] >= 2
    signals = {candidate["signal"]: candidate for candidate in retention["candidates"]}
    assert signals["missing-retention-metadata"]["recommended_outcome"] == "add-retention-metadata"
    assert signals["retention-shape-shrink"]["recommended_outcome"] == "shrink"
    assert retention["default_outcome"] == "retain"
    assert "never deletes" in retention["rule"]

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0
    operational_payload = json.loads(capsys.readouterr().out)
    measures = operational_payload["answer"]["measures"]
    assert measures["review_retention_policy"]["candidate_count"] >= 2
    assert any(signal["measure"] == "review_retention_policy" for signal in operational_payload["answer"]["signals"])

    assert cli.main(["report", "--target", str(target), "--section", "maintenance_pressure", "--format", "json"]) == 0
    maintenance_payload = json.loads(capsys.readouterr().out)
    categories = {entry["id"]: entry for entry in maintenance_payload["answer"]["subcategories"]}
    assert categories["review_retention"]["status"] == "attention"
    assert "cleanup candidates" in categories["review_retention"]["summary"]


def test_report_section_selector_returns_compact_section_answer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "effective_authority", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "report"
    assert payload["selector"] == {"section": "effective_authority"}
    assert payload["matched"] is True
    assert payload["answer"]["defaults_command"] == "agentic-workspace defaults --section effective_authority --format json"
    assert payload["answer"]["status"] == "ready"
    assert payload["answer"]["idle_context"][0]["id"] == "no-active-planning-record"
    assert payload["refs"][0] == ".agentic-workspace/docs/reporting-contract.md"


def test_report_section_selector_returns_operational_compression_measures(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / ".agentic-workspace" / "planning" / "execplans" / "archive" / "compressed-lane.plan.json",
        {
            "kind": "planning-execplan/v1",
            "active_milestone": {"status": "completed"},
            "closeout_distillation": {
                "buckets": {
                    "continuation": [{"summary": "Parent remains open.", "owner": "planning", "source": "test"}],
                    "discard": [],
                    "memory": [],
                    "config_check": [],
                    "docs": [],
                    "issue_follow_up": [],
                }
            },
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "report"
    assert payload["selector"] == {"section": "operational_compression"}
    assert payload["matched"] is True
    assert captured.err == ""
    answer = payload["answer"]
    assert answer["kind"] == "workspace-operational-compression/v1"
    assert answer["advisory_only"] is True
    assert answer["hard_failures"] == []
    assert "dashboard" in answer["rule"]
    measures = answer["measures"]
    assert measures["first_line_startup_read_surface_count"]["count"] >= 1
    assert measures["default_report_size_or_warning_count"]["decision_grade_field_count"] >= 1
    assert measures["additive_surface_replacement_pressure"]["status"] == "available-advisory-gate"
    assert measures["additive_surface_replacement_pressure"]["review_gate"]["rule"].startswith("Durable-surface changes")
    assert measures["durable_surface_metadata"]["required_metadata"] == ["owner", "authority", "summary"]
    assert measures["archived_plan_distillation"]["archived_plan_count"] == 1
    assert measures["archived_plan_distillation"]["with_distillation_count"] == 1
    assert measures["archived_plan_distillation"]["missing_distillation_count"] == 0
    assert measures["archived_plan_distillation"]["post_contract_missing_distillation_count"] == 0
    archive_retention = measures["archive_retention_policy"]
    assert archive_retention["kind"] == "workspace-archive-retention-policy/v1"
    assert archive_retention["advisory_only"] is True
    assert archive_retention["outcomes"] == [
        "retain",
        "shrink",
        "stub",
        "delete",
        "promote-summary-elsewhere",
    ]
    assert archive_retention["default_outcome"] == "retain"
    assert archive_retention["candidate_count"] == 0
    assert "never deletes" in archive_retention["rule"]
    review_retention = measures["review_retention_policy"]
    assert review_retention["kind"] == "workspace-review-retention-policy/v1"
    assert review_retention["advisory_only"] is True
    assert review_retention["default_outcome"] == "retain"
    generated_footprint = measures["generated_output_footprint"]
    assert generated_footprint["kind"] == "workspace-generated-output-footprint/v1"
    assert generated_footprint["advisory_only"] is True
    assert generated_footprint["freshness"]["ordinary_report_runs_checks"] is False
    assert "Generated outputs are reproducible derived artifacts" in generated_footprint["guardrails"][0]
    footprint = measures["artifact_footprint_by_class"]
    assert footprint["rule"].startswith("Footprint classes are advisory")
    classes = {entry["id"]: entry for entry in footprint["classes"]}
    assert set(classes) >= {
        "active_execplans",
        "archived_execplans",
        "review_artifacts",
        "current_memory_notes",
        "durable_memory_notes",
        "generated_outputs",
        "local_only_state",
        "large_docs_or_package_surfaces",
    }
    assert classes["archived_execplans"]["role"] == "historical evidence"
    assert classes["durable_memory_notes"]["role"] == "durable knowledge"
    assert classes["generated_outputs"]["role"] == "derived reproducible artifact"


def test_report_section_selector_returns_successful_completion_cost_summary(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / "scratch" / "model-cli-harness" / "20260508T220836Z-suite-codex-summary.json",
        {
            "adapter": "codex",
            "model": "gpt-5.3-codex-spark",
            "result_count": 2,
            "usage_summary": {
                "status": "present",
                "input_tokens": 1000,
                "uncached_input_tokens": 300,
                "cached_input_tokens": 700,
                "output_tokens": 120,
                "reasoning_output_tokens": 80,
                "total_billable_proxy_tokens": 500,
            },
            "package_read_surface_summary": {
                "status": "present",
                "command_count": 3,
                "output_bytes": 1200,
                "output_lines": 42,
                "largest_command_output_bytes": 800,
                "mixed_command_count": 0,
                "precision": "direct",
            },
            "finding_classification": {"finding_count": 1},
            "capability_routing_evaluation": {"ignored_or_misread_count": 1},
            "completion_followthrough": {
                "kind": "agentic-workspace/model-cli-completion-followthrough/v1",
                "status": "pushed-to-completion",
            },
            "results": [
                {"warnings": [], "returncode": 0, "mutation_summary": {"status": "clean"}},
                {"warnings": [{"message": "rework"}], "returncode": 0, "mutation_summary": {"status": "modified"}},
            ],
        },
    )
    _write_json(
        target / "tools" / "model-cli-harness" / "model-task-weakness-ledger.json",
        {
            "schema": "agentic-workspace/model-cli-harness-weakness-ledger/v1",
            "entries": [
                {"id": "capability-routing-decision-followthrough", "status": "active-monitoring", "priority": "high"},
                {"id": "memory-context-skipped-or-bulk-read", "status": "fixed-monitoring", "priority": "medium"},
            ],
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "successful_completion_cost", "--format", "json"]) == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert captured.err == ""
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"section": "successful_completion_cost"}
    answer = payload["answer"]
    assert answer["kind"] == "workspace-successful-completion-cost/v1"
    assert answer["advisory_only"] is True
    assert "not a formal benchmark" in answer["rule"]
    assert answer["evidence"]["summary_count"] == 1
    assert answer["evidence"]["weakness_ledger"]["active_high_priority_count"] == 1
    totals = answer["totals"]
    assert totals["token_and_request_cost"]["total_billable_proxy_tokens"] == 500
    assert totals["package_read_overhead"]["command_count"] == 3
    assert totals["proof_and_rework_cost"]["warning_run_count"] == 1
    assert totals["proof_and_rework_cost"]["capability_ignored_or_misread_count"] == 1
    assert totals["proof_and_rework_cost"]["pushed_to_completion_count"] == 1
    assert answer["recent_runs"][0]["proof_and_rework_cost"]["first_pass_proxy"] == "rework-likely"
    assert answer["recent_runs"][0]["proof_and_rework_cost"]["pushed_to_completion_status"] == "pushed-to-completion"
    assert any(signal["id"] == "rework-pressure" for signal in answer["signals"])


def test_operational_compression_reports_artifact_footprint_pressure(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(target / ".agentic-workspace" / "memory" / "repo" / "current" / "legacy.md", "# Legacy\n")
    _write(target / ".agentic-workspace" / "planning" / "reviews" / "old.review.json", "{}\n")
    _write(target / "generated" / "adapter.json", "{}\n")
    _write(target / "docs" / "large.md", "\n".join(f"line {index}" for index in range(401)))

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    footprint = payload["answer"]["measures"]["artifact_footprint_by_class"]
    classes = {entry["id"]: entry for entry in footprint["classes"]}
    assert classes["current_memory_notes"]["pressure"] == "attention"
    assert classes["review_artifacts"]["pressure"] == "attention"
    assert classes["generated_outputs"]["count"] >= 1
    assert classes["large_docs_or_package_surfaces"]["pressure"] == "attention"
    generated_footprint = payload["answer"]["measures"]["generated_output_footprint"]
    assert generated_footprint["status"] == "attention"
    assert generated_footprint["unclassified_generated_output_count"] >= 1
    assert "generated/adapter.json" in generated_footprint["sample_unclassified_generated_outputs"]
    assert any(signal["measure"] == "generated_output_footprint" for signal in payload["answer"]["signals"])
    assert footprint["pressure_class_count"] >= 3
    assert footprint["recommended_cleanup_target"]["action"] == "review-shrink-route-or-retain"
    assert any(signal["measure"] == "artifact_footprint_by_class" for signal in payload["answer"]["signals"])


def test_operational_compression_classifies_generated_output_footprint(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json",
        {
            "packages": [
                {
                    "id": "root-workspace",
                    "program": "agentic-workspace",
                    "targets": [
                        {
                            "kind": "python",
                            "generated_root": "generated/python/workspace-cli",
                            "generation_status": "supported-now",
                            "maturity_level_ref": "metadata-proof-fixture",
                            "test_environment": "python-dev",
                        },
                        {
                            "kind": "typescript",
                            "generated_root": "generated/typescript/workspace-cli",
                            "generation_status": "weak-agent-safe-adapter",
                            "maturity_level_ref": "weak-agent-safe-adapter",
                            "test_environment": "docker",
                        },
                    ],
                }
            ]
        },
    )
    _write_json(
        target / "src" / "agentic_workspace" / "contracts" / "command_adapter_generation.json",
        {
            "generated_outputs": [
                {
                    "program": "agentic-workspace",
                    "path": "src/agentic_workspace/generated_command_adapters.py",
                }
            ]
        },
    )
    _write(target / "scripts" / "generate" / "generate_command_packages.py", "print('generate')\n")
    _write(target / "scripts" / "check" / "check_generated_command_packages.py", "print('check')\n")
    _write(target / "generated" / "python" / "workspace-cli" / "generated_cli_package" / "__init__.py", "# generated\n")
    _write(
        target / "src" / "agentic_workspace" / "generated_cli_package" / "__pycache__" / "__init__.cpython-313.pyc",
        "cache\n",
    )
    _write(target / "src" / "agentic_workspace" / "generated_command_adapters.py", "# generated\n")
    _write(target / "generated" / "typescript" / "workspace-cli" / "package.json", "{}\n")
    _write(target / "generated" / "typescript" / "workspace-cli" / "src" / "cli.mjs", "export {};\n")
    _write(target / "generated" / "typescript" / "Dockerfile", "FROM node:22\n")

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    generated = payload["answer"]["measures"]["generated_output_footprint"]
    assert generated["status"] == "measured"
    assert generated["artifact_count"] >= 5
    assert generated["proof_fixture_count"] == 1
    assert generated["runnable_adapter_count"] == 1
    assert generated["weak_agent_safe_adapter_count"] == 1
    assert generated["unclassified_generated_output_count"] == 0
    assert generated["freshness"]["status"] == "check-available"
    surfaces = {surface["id"]: surface for surface in generated["generated_surfaces"]}
    assert surfaces["root-workspace:python"]["role"] == "proof-fixture"
    assert surfaces["root-workspace:typescript"]["role"] == "weak-agent-safe-adapter"
    assert surfaces["typescript:proof-container-support"]["role"] == "proof-container-support"


def test_report_distinguishes_legacy_archive_distillation_debt(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    archive_dir = target / ".agentic-workspace" / "planning" / "execplans" / "archive"
    legacy_missing = archive_dir / "legacy-missing.plan.json"
    compressed = archive_dir / "compressed-lane.plan.json"
    current_missing = archive_dir / "current-missing.plan.json"
    _write_json(legacy_missing, {"kind": "planning-execplan/v1", "active_milestone": {"status": "completed"}})
    _write_json(
        compressed,
        {
            "kind": "planning-execplan/v1",
            "active_milestone": {"status": "completed"},
            "closeout_distillation": {
                "buckets": {
                    "continuation": [{"summary": "Parent remains open.", "owner": "planning", "source": "test"}],
                    "discard": [],
                    "memory": [],
                    "config_check": [],
                    "docs": [],
                    "issue_follow_up": [],
                }
            },
        },
    )
    _write_json(current_missing, {"kind": "planning-execplan/v1", "active_milestone": {"status": "completed"}})
    os.utime(legacy_missing, (1_000_000, 1_000_000))
    os.utime(compressed, (2_000_000, 2_000_000))
    os.utime(current_missing, (3_000_000, 3_000_000))

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    measure = payload["answer"]["measures"]["archived_plan_distillation"]
    assert measure["missing_distillation_count"] == 2
    assert measure["legacy_missing_distillation_count"] == 1
    assert measure["post_contract_missing_distillation_count"] == 1
    assert measure["distillation_contract_anchor"] == "compressed-lane.plan.json"
    signal = next(item for item in payload["answer"]["signals"] if item["measure"] == "archived_plan_distillation")
    assert signal["count"] == 1
    archive_retention = payload["answer"]["measures"]["archive_retention_policy"]
    assert archive_retention["status"] == "attention"
    assert archive_retention["before_shrink_or_delete"][0].startswith("promote durable learning")
    assert any(candidate["recommended_outcome"] == "promote-summary-elsewhere" for candidate in archive_retention["candidates"])
    assert any(candidate["recommended_outcome"] == "stub" for candidate in archive_retention["candidates"])
    retention_signal = next(item for item in payload["answer"]["signals"] if item["measure"] == "archive_retention_policy")
    assert retention_signal["count"] == archive_retention["candidate_count"]


def test_report_section_selector_returns_external_work_delta(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / ".agentic-workspace" / "planning" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "previous_items": [
                {
                    "system": "manual",
                    "id": "TASK-1",
                    "title": "Old open task",
                    "status": "open",
                    "kind": "task",
                    "parent_id": "",
                    "planning_residue_expected": "required",
                }
            ],
            "items": [
                {
                    "system": "manual",
                    "id": "TASK-1",
                    "title": "Old open task",
                    "status": "closed",
                    "kind": "task",
                    "parent_id": "",
                    "planning_residue_expected": "required",
                },
                {
                    "system": "manual",
                    "id": "TASK-2",
                    "title": "New follow-up",
                    "status": "open",
                    "kind": "task",
                    "parent_id": "",
                    "planning_residue_expected": "required",
                },
            ],
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "external_work_delta", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "report"
    assert payload["selector"] == {"section": "external_work_delta"}
    answer = payload["answer"]
    assert answer["status"] == "delta-present"
    assert answer["new_count"] == 1
    assert answer["changed_count"] == 1
    assert answer["closed_count"] == 1
    assert answer["recommended_next_lane"]["id"] == "TASK-2"


def test_report_section_selector_rejects_schema_invalid_external_work_delta(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / ".agentic-workspace" / "planning" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "items": [{"system": "manual", "id": "", "status": "open"}],
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "external_work_delta", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert answer["status"] == "invalid"
    assert "schema validation failed" in answer["reason"]
    assert any("items.0.id" in finding for finding in answer["schema_findings"])


def test_report_section_selector_returns_external_work_reconciliation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / ".agentic-workspace" / "planning" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "refreshed_at": "2026-04-27T12:00:00+00:00",
            "refresh_metadata": {"adapter": "manual-fixture", "item_count": 1, "open_count": 1, "closed_count": 0},
            "items": [
                {
                    "system": "manual",
                    "id": "TASK-1",
                    "title": "External follow-up",
                    "status": "open",
                    "kind": "task",
                    "parent_id": "",
                    "planning_residue_expected": "optional",
                }
            ],
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "external_work_reconciliation", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "report"
    assert payload["selector"] == {"section": "external_work_reconciliation"}
    answer = payload["answer"]
    assert answer["kind"] == "planning-external-work-reconciliation/v1"
    assert answer["freshness"]["fresh_enough_to_trust"] is True
    assert answer["freshness"]["refresh_metadata"]["adapter"] == "manual-fixture"
    assert answer["external_work_state"]["open_count"] == 1
    assert answer["external_work_state"]["untracked_open_count"] == 1
    promotion_action = answer["promotion_action"]
    assert promotion_action["action"] == "promote-external-work-to-planning"
    assert promotion_action["provider_neutral"] is True
    assert promotion_action["target_surfaces"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/<lane>.plan.json",
    ]
    assert "do not duplicate active state" in promotion_action["state_rule"]
    assert answer["workspace_report_view"]["delta_section"] == "external_work_delta"


def test_report_section_selector_accepts_current_work_alias(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "current_work", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"section": "current_work", "resolved_section": "effective_authority.current_work"}
    assert payload["answer"]["status"] in {"absent", "direct-or-no-active-plan"}


def test_report_section_selector_accepts_current_external_work_alias(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "current_external_work", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"section": "current_external_work", "resolved_section": "external_work_reconciliation"}
    assert payload["answer"]["kind"] == "planning-external-work-reconciliation/v1"


def test_report_section_selector_error_recommends_compact_recovery(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["report", "--target", str(target), "--section", "currnt_work", "--format", "json"])

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert "Did you mean: current_work" in stderr
    assert "agentic-workspace summary --format json" in stderr
    assert "--section next_action" in stderr
    assert "--section external_work_reconciliation" in stderr


def test_report_routes_roadmap_backed_work_to_planning_before_broad_execution(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\n"
        "active_items = []\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = [\n"
        "  { id = 'dogfooding-guardrail', title = 'Dogfooding guardrail', priority = 'first', issues = ['#322'], outcome = 'Make planned work use planning.', reason = 'A broad run bypassed active planning.', promotion_signal = 'Promote before broad work.', suggested_first_slice = 'Add readiness guardrail.' },\n"
        "]\n"
        "candidates = [\n"
        "  { priority = 'first', summary = 'Dogfooding guardrail' },\n"
        "]\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    execution_shape = payload["execution_shape"]
    assert execution_shape["task_shape"]["id"] == "roadmap-backed-no-active-plan"
    assert [shape["id"] for shape in execution_shape["task_shape_recommender"]["shapes"]] == [
        "direct",
        "light-plan",
        "checked-in-execplan",
    ]
    assert execution_shape["recommendation"]["id"] == "promote-before-broad-work"
    assert execution_shape["recommendation"]["consult"] == ["agentic-workspace summary --format json"]
    assert execution_shape["recommendation"]["allowed_execution_methods"] == [
        "single-agent fallback for narrow work",
        "planning-backed execution after promotion",
    ]
    assert "chat or issue context alone" in execution_shape["deviation_rule"]


def test_report_surfaces_default_branch_commit_risk(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _set_git_branch(target, current="master", default="master")

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "branch_workflow_posture" in payload["schema"]["shared_fields"]
    assert "local_memory" in payload["schema"]["shared_fields"]
    posture = payload["branch_workflow_posture"]
    assert posture["status"] == "present"
    assert posture["current_branch"] == "master"
    assert posture["default_branch"] == "master"
    assert posture["on_default_branch"] is True
    assert posture["risk"] == "default-branch-commit-risk"
    assert "do not switch branches unless the user decides" in posture["recommended_next_action"]
    policy = posture["branch_mutation_policy"]
    assert policy["advisory_only"] is True
    assert "switch-branch" in policy["guarded_actions"]
    assert "explicit user intent" in policy["rule"]


def test_report_branch_posture_flags_changed_workspace_shared_state(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=target, check=True)
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=target, check=True, capture_output=True)
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        'kind = "agentic-planning-state"\nschema_version = "planning-state/v1"\n',
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    risk = payload["branch_workflow_posture"]["shared_state_mutation_risk"]
    assert risk["status"] == "attention"
    assert risk["risk"] == "high"
    assert any(surface["path"] == ".agentic-workspace/planning/state.toml" for surface in risk["surfaces"])


def test_report_closeout_trust_surfaces_package_workflow_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n[assurance]\nstrict_closeout = true\n",
    )
    plan = target / ".agentic-workspace" / "planning" / "execplans" / "package-use.plan.json"
    _write_json(
        plan,
        {
            "kind": "planning-execplan/v1",
            "title": "Package Use",
            "active_milestone": {"id": "package-use", "status": "active"},
            "delegated_judgment": {
                "requested outcome": "Use package workflow.",
                "hard constraints": "Stay portable.",
                "agent may decide locally": "Exact signal shape.",
                "escalate when": "Package workflow is unavailable.",
            },
            "immediate_next_action": ["Use package workflow."],
            "completion_criteria": ["Package workflow evidence is visible."],
            "validation_commands": ["uv run agentic-workspace proof --target . --format json"],
            "intent_continuity": {
                "larger intended outcome": "Close broad package workflow lane.",
                "this slice completes the larger intended outcome": "no",
                "continuation surface": ".agentic-workspace/planning/state.toml",
            },
            "required_continuation": {
                "required follow-on for the larger intended outcome": "yes",
                "owner surface": ".agentic-workspace/planning/state.toml",
                "activation trigger": "after proof passes",
            },
            "iterative_follow_through": {
                "what this slice enabled": "package workflow evidence",
                "intentionally deferred": "broad package workflow lane closeout",
                "discovered implications": "validation proof is not intent closure",
                "proof achieved now": "yes",
                "validation still needed": "lane follow-on",
                "next likely slice": "continue broad workflow lane",
            },
            "context_budget": {
                "live working set": "report output and closeout trust",
                "recoverable later": "archived plan",
                "externalize before shift": "state.toml",
                "pre-work config pull": "uv run agentic-workspace summary --format json",
                "pre-work memory pull": "uv run agentic-workspace report --format json",
                "tiny resumability note": "validation proof is separate from lane closure",
                "context-shift triggers": "larger intent remains open",
            },
            "execution_run": {
                "run status": "active",
                "executor": "test",
                "handoff source": "uv run agentic-workspace preflight --format json",
                "what happened": "Used agentic-workspace report --target . --format json and proof-selected validation.",
                "scope touched": "test",
                "changed surfaces": "test",
                "validations run": "uv run agentic-workspace summary --format json; uv run agentic-workspace reconcile --format json",
                "result for continuation": "continue",
                "next step": "finish",
            },
            "proof_report": {
                "validation proof": "uv run agentic-workspace proof passed",
                "acceptance reconciliation": "requested package workflow evidence -> delivered closeout report evidence -> proof passed",
                "proof achieved now": "yes",
                'evidence for "proof achieved" state': "focused report test fixture",
            },
            "closure_check": {
                "slice status": "active",
                "larger-intent status": "open",
                "closure decision": "archive-but-keep-lane-open",
                "why this decision is honest": "The proof passed but the broader workflow lane still has follow-on work.",
                "evidence carried forward": ".agentic-workspace/planning/state.toml",
                "reopen trigger": "follow-on remains open",
            },
        },
    )
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\n"
        "active_items = [\n"
        "  { id = 'package-use', title = 'Package use', surface = '.agentic-workspace/planning/execplans/package-use.plan.json' },\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\nlanes = []\ncandidates = []\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["closeout_trust"]["strict_closeout_gate"]["status"] == "allowed"
    assert payload["closeout_trust"]["strict_closeout_gate"]["blocking"] is False
    evidence = payload["closeout_trust"]["package_workflow_evidence"]
    assert evidence["status"] == "present"
    assert evidence["trust"] == "normal"
    assert evidence["required_for_broad_work"] is True
    assert evidence["used_surfaces"] == ["preflight", "summary", "report", "proof", "reconcile"]
    assert evidence["missing_expected_surfaces"] == []
    intent_check = payload["closeout_trust"]["intent_satisfaction_check"]
    assert intent_check["status"] == "present"
    assert intent_check["trust"] == "follow-up-required"
    closure_scope = intent_check["closure_scope"]
    assert closure_scope["validation_proof"]["status"] == "separate-answer"
    assert closure_scope["validation_proof"]["not_sufficient_for_closure"] is True
    assert closure_scope["validation_proof"]["proof_expectation_count"] == 1
    assert closure_scope["requested_slice"]["status"] == "active"
    assert closure_scope["lane_or_system_intent"]["status"] == "follow-up-required"
    assert closure_scope["lane_or_system_intent"]["required_follow_on"] == "yes"
    assert closure_scope["larger_intent_closure"]["status"] == "open"
    assert closure_scope["larger_intent_closure"]["closure_decision"] == "archive-but-keep-lane-open"
    assert closure_scope["non_substitution_rule"] == "Validation success alone is not closure evidence."
    acceptance = payload["closeout_trust"]["acceptance_criteria_reconciliation"]
    assert acceptance["status"] == "present"
    assert acceptance["trust"] == "normal"
    assert acceptance["evidence_present"] is True
    assert acceptance["completion_criteria_count"] == 1
    residue_action = payload["closeout_trust"]["durable_residue_action"]
    assert residue_action["action"] == "route-durable-residue"
    assert residue_action["command"] == "agentic-workspace report --target ./repo --section closeout_trust --format json"
    assert residue_action["run"] == residue_action["command"]
    assert residue_action["risk"] == "read-only routing; mutations happen only through the selected owner surface"
    assert residue_action["required_inputs"] == ["validation result", "issue or lane scope", "future relevance of any learning"]
    assert "Memory" in residue_action["destinations"]
    assert "future work goes to planning" in residue_action["destination_rule"]
    assert "rerun summary/reconcile" in residue_action["next_proof"]
    terminal_action = payload["closeout_trust"]["terminal_action"]
    assert terminal_action["blocking"] is False
    assert terminal_action["next_command"] == "none"
    assert "No closeout trust blocker" in terminal_action["why"]
    assert "proof, intent satisfaction, issue state" in terminal_action["changes_closure"]


def test_report_closeout_trust_lowers_trust_when_active_plan_has_no_package_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n[assurance]\nstrict_closeout = true\n",
    )
    plan = target / ".agentic-workspace" / "planning" / "execplans" / "bypassed-workflow.plan.json"
    _write_json(
        plan,
        {
            "kind": "planning-execplan/v1",
            "title": "Bypassed Workflow",
            "active_milestone": {"id": "bypassed-workflow", "status": "active"},
            "delegated_judgment": {
                "requested outcome": "Implement broad work.",
                "hard constraints": "Keep workflow evidence visible.",
                "agent may decide locally": "Implementation details.",
                "escalate when": "Workflow unavailable.",
            },
            "immediate_next_action": ["Finish the lane."],
            "completion_criteria": ["Closeout trust can detect missing package evidence."],
            "validation_commands": ["make check"],
            "intent_continuity": {
                "larger intended outcome": "Close a broad workflow lane.",
                "this slice completes the larger intended outcome": "yes",
                "continuation surface": "none",
            },
            "required_continuation": {
                "required follow-on for the larger intended outcome": "no",
                "owner surface": "none",
                "activation trigger": "none",
            },
            "iterative_follow_through": {
                "what this slice enabled": "absence detection",
                "intentionally deferred": "external enforcement",
                "discovered implications": "none",
                "proof achieved now": "pending",
                "validation still needed": "make check",
                "next likely slice": "none",
            },
            "context_budget": {
                "live working set": "closeout trust",
                "recoverable later": "archive",
                "externalize before shift": "plan",
                "pre-work config pull": "",
                "pre-work memory pull": "",
                "tiny resumability note": "missing package evidence",
                "context-shift triggers": "closeout",
            },
            "execution_run": {
                "run status": "active",
                "executor": "test",
                "handoff source": "chat only",
                "what happened": "Implemented without recording package workflow use.",
                "scope touched": "test",
                "changed surfaces": "test",
                "validations run": "make check",
                "result for continuation": "close",
                "next step": "close",
            },
            "proof_report": {
                "validation proof": "make check",
                "proof achieved now": "pending",
                'evidence for "proof achieved" state': "none",
            },
            "closure_check": {
                "slice status": "active",
                "larger-intent status": "open",
                "closure decision": "archive-and-close",
                "why this decision is honest": "fixture",
                "evidence carried forward": "none",
                "reopen trigger": "missing evidence",
            },
        },
    )
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\n"
        "active_items = [\n"
        "  { id = 'bypassed-workflow', title = 'Bypassed workflow', surface = '.agentic-workspace/planning/execplans/bypassed-workflow.plan.json' },\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\nlanes = []\ncandidates = []\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    closeout = payload["closeout_trust"]
    assert closeout["trust"] == "lower-trust"
    assert closeout["strict_closeout_gate"]["status"] == "blocked"
    assert closeout["strict_closeout_gate"]["blocking"] is True
    assert closeout["lower_trust_closeout_count"] == 2
    assert closeout["planning_residue_lower_trust_count"] == 0
    assert closeout["package_evidence_lower_trust_count"] == 1
    assert closeout["acceptance_reconciliation_lower_trust_count"] == 1
    assert "missing preflight, summary, report, proof" in closeout["absence_signals"][0]
    acceptance = closeout["acceptance_criteria_reconciliation"]
    assert acceptance["trust"] == "lower-trust"
    assert "requested->delivered->proof->gap" in acceptance["recommended_next_action"]
    evidence = closeout["package_workflow_evidence"]
    assert evidence["trust"] == "lower-trust"
    assert evidence["missing_expected_surfaces"] == ["preflight", "summary", "report", "proof"]


def test_report_surfaces_local_only_memory_status(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[local_memory]\nenabled = true\npath = ".agentic-workspace/local/memory.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    local_memory = payload["local_memory"]
    assert local_memory["status"] == "enabled"
    assert local_memory["path"] == ".agentic-workspace/local/memory.toml"
    assert local_memory["git_ignored"] is True
    assert local_memory["safe_to_delete"] is True
    assert local_memory["scratch"]["root"] == ".agentic-workspace/local/scratch"
    assert local_memory["scratch"]["exists"] is True
    assert "checked-in Memory" in local_memory["promotion_guidance"]


def test_report_handles_modules_with_empty_findings_lists(tmp_path: Path, monkeypatch, capsys) -> None:
    from repo_memory_bootstrap import installer as memory_installer
    from repo_planning_bootstrap import installer as planning_installer

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    original_planning_report = planning_installer.planning_report
    original_memory_report = memory_installer.memory_report

    def _planning_report_without_findings(*, target=None):
        report = original_planning_report(target=target)
        report["findings"] = []
        return report

    def _memory_report_without_findings(*, target=None):
        report = original_memory_report(target=target)
        report["findings"] = []
        return report

    monkeypatch.setattr(planning_installer, "planning_report", _planning_report_without_findings)
    monkeypatch.setattr(memory_installer, "memory_report", _memory_report_without_findings)

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []


def test_report_surfaces_planning_intent_validation_findings(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "external-intent-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "EXT-quiet-open",
                        "title": "Quiet but open",
                        "status": "open",
                        "kind": "lane",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert any("Open external planning item EXT-quiet-open" in finding["message"] for finding in payload["findings"])
    planning_report = next(report for report in payload["module_reports"] if report["module"] == "planning")
    assert planning_report["intent_validation"]["counts"]["untracked_external_open_count"] == 1


def test_external_intent_refresh_github_writes_provider_agnostic_evidence(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "github",
                        "id": "#1",
                        "title": "Previous",
                        "status": "open",
                        "kind": "issue",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    class Result:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    recent_closed_at = cli.datetime.now(cli.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def fake_run(command, cwd, capture_output, text, encoding, check):
        assert command[:2] == ["gh", "issue"]
        assert command[command.index("--state") + 1] == "all"
        assert cwd == target
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        assert check is False
        return Result(
            json.dumps(
                [
                    {
                        "number": 1,
                        "title": "Open work",
                        "state": "OPEN",
                        "url": "https://github.com/acme/project/issues/1",
                        "labels": [{"name": "planning"}],
                        "createdAt": "2026-04-01T00:00:00Z",
                        "updatedAt": "2026-04-27T00:00:00Z",
                        "closedAt": None,
                        "body": "## Issue kind\n\nChild slice\n\n## Parent issue or lane\n\n#10\n\n## Closed lane(s) to revisit\n\n#8, #9\n",
                        "comments": [{"body": "closeout"}],
                    },
                    {
                        "number": 2,
                        "title": "Closed work",
                        "state": "CLOSED",
                        "url": "https://github.com/acme/project/issues/2",
                        "labels": [],
                        "createdAt": "2026-04-01T00:00:00Z",
                        "updatedAt": "2026-04-26T00:00:00Z",
                        "closedAt": recent_closed_at,
                        "body": "",
                        "comments": 0,
                    },
                ]
            )
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--state",
                "all",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "external-intent-refresh/v1"
    assert payload["written"] is True
    assert payload["repository"] == "acme/project"
    assert payload["storage"] == "cache"
    assert payload["path"] == ".agentic-workspace/local/cache/external-intent-evidence.json"
    assert payload["state"] == "all"
    assert payload["state_source"] == "explicit"
    assert payload["limit_source"] == "product_default"
    assert payload["item_count"] == 2
    refreshed = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert refreshed["kind"] == "planning-external-intent-evidence/v1"
    assert refreshed["refresh_metadata"]["adapter"] == "github-gh-cli"
    assert refreshed["refresh_metadata"]["repository"] == "acme/project"
    assert refreshed["refresh_metadata"]["state"] == "all"
    assert refreshed["refresh_metadata"]["limit"] == 1000
    assert "previous_items" not in refreshed
    assert refreshed["items"][0]["id"] == "#1"
    assert refreshed["items"][0]["kind"] == "slice"
    assert refreshed["items"][0]["parent_id"] == "#10"
    assert refreshed["items"][0]["reopens"] == ["#8", "#9"]
    assert refreshed["items"][0]["labels"] == ["planning"]
    assert refreshed["items"][1]["status"] == "closed"


def test_external_intent_refresh_github_compacts_old_unreferenced_closed_cache_items(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "reviews" / "retained.review.json").write_text(
        json.dumps({"kind": "planning-review/v1", "title": "Retain #3", "references": ["#3"]}) + "\n",
        encoding="utf-8",
    )
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    now = cli.datetime.now(cli.timezone.utc).replace(microsecond=0)
    recent = now.isoformat().replace("+00:00", "Z")
    old = (now - cli.timedelta(days=90)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    class Result:
        recent_closed_at = cli.datetime.now(cli.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        returncode = 0
        stderr = ""
        stdout = json.dumps(
            [
                {
                    "number": 1,
                    "title": "Open work",
                    "state": "OPEN",
                    "url": "https://github.com/acme/project/issues/1",
                    "labels": [],
                    "createdAt": old,
                    "updatedAt": old,
                    "closedAt": None,
                    "body": "",
                    "comments": 0,
                },
                {
                    "number": 2,
                    "title": "Recent closed work",
                    "state": "CLOSED",
                    "url": "https://github.com/acme/project/issues/2",
                    "labels": [],
                    "createdAt": old,
                    "updatedAt": recent,
                    "closedAt": recent,
                    "body": "",
                    "comments": 0,
                },
                {
                    "number": 3,
                    "title": "Referenced closed work",
                    "state": "CLOSED",
                    "url": "https://github.com/acme/project/issues/3",
                    "labels": [],
                    "createdAt": old,
                    "updatedAt": recent,
                    "closedAt": old,
                    "body": "",
                    "comments": 0,
                },
                {
                    "number": 4,
                    "title": "Old unreferenced closed work",
                    "state": "CLOSED",
                    "url": "https://github.com/acme/project/issues/4",
                    "labels": [],
                    "createdAt": old,
                    "updatedAt": recent,
                    "closedAt": old,
                    "body": "",
                    "comments": 0,
                },
            ]
        )

    monkeypatch.setattr(cli.subprocess, "run", lambda *args, **kwargs: Result())

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--state",
                "all",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    refreshed = json.loads(evidence_path.read_text(encoding="utf-8"))
    retained_ids = [item["id"] for item in refreshed["items"]]
    assert retained_ids == ["#1", "#2", "#3"]
    assert payload["fetched_item_count"] == 4
    assert payload["item_count"] == 3
    assert payload["cache_compaction"]["dropped_closed_count"] == 1
    assert payload["cache_compaction"]["retained_recent_closed_count"] == 1
    assert payload["cache_compaction"]["retained_referenced_closed_count"] == 1
    assert refreshed["refresh_metadata"]["fetched_closed_count"] == 3
    assert refreshed["refresh_metadata"]["closed_count"] == 2
    assert refreshed["refresh_metadata"]["cache_compaction"]["retained_item_count"] == 3


def test_external_intent_refresh_github_accepts_bom_and_recomputes_counts(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    previous = {
        "kind": "planning-external-intent-evidence/v1",
        "refresh_metadata": {"item_count": 1, "open_count": 1, "closed_count": 0},
        "items": [{"system": "github", "id": "#1", "status": "open"}],
    }
    evidence_path.write_bytes(("\ufeff" + json.dumps(previous, indent=2) + "\n").encode("utf-8"))
    recent_closed_at = cli.datetime.now(cli.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    class Result:
        returncode = 0
        stderr = ""
        stdout = json.dumps(
            [
                {
                    "number": 1,
                    "title": "Open work",
                    "state": "OPEN",
                    "url": "https://github.com/acme/project/issues/1",
                    "labels": [],
                    "createdAt": "2026-04-01T00:00:00Z",
                    "updatedAt": "2026-04-27T00:00:00Z",
                    "closedAt": None,
                    "body": "",
                    "comments": 0,
                },
                {
                    "number": 2,
                    "title": "Closed work",
                    "state": "CLOSED",
                    "url": "https://github.com/acme/project/issues/2",
                    "labels": [],
                    "createdAt": "2026-04-01T00:00:00Z",
                    "updatedAt": "2026-04-27T00:00:00Z",
                    "closedAt": recent_closed_at,
                    "body": "",
                    "comments": 0,
                },
            ]
        )

    monkeypatch.setattr(cli.subprocess, "run", lambda *args, **kwargs: Result())

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--state",
                "all",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    refreshed_bytes = evidence_path.read_bytes()
    refreshed = json.loads(refreshed_bytes.decode("utf-8"))
    assert payload["previous_item_count"] == 1
    assert not refreshed_bytes.startswith(b"\xef\xbb\xbf")
    assert refreshed["refresh_metadata"]["item_count"] == 2
    assert refreshed["refresh_metadata"]["open_count"] == 1
    assert refreshed["refresh_metadata"]["closed_count"] == 1


def test_external_intent_refresh_github_rejects_count_drift(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refresh_metadata": {"item_count": 2, "open_count": 2, "closed_count": 0},
                "items": [{"system": "github", "id": "#1", "status": "open"}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def fail_run(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("refresh should reject invalid existing evidence before calling gh")

    monkeypatch.setattr(cli.subprocess, "run", fail_run)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--format",
                "json",
            ]
        )

    assert excinfo.value.code == 2
    assert "refresh_metadata.item_count must equal 1 from items" in capsys.readouterr().err


def test_external_intent_refresh_github_uses_product_defaults_instead_of_previous_cache_scope(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refresh_metadata": {
                    "state": "all",
                    "limit": 600,
                },
                "items": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    observed_commands: list[list[str]] = []

    class Result:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, cwd, capture_output, text, encoding, check):
        observed_commands.append(command)
        assert cwd == target
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        assert check is False
        return Result("[]")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert observed_commands[-1][observed_commands[-1].index("--state") + 1] == "all"
    assert observed_commands[-1][observed_commands[-1].index("--limit") + 1] == "1000"
    assert payload["state"] == "all"
    assert payload["limit"] == 1000
    assert payload["state_source"] == "product_default"
    assert payload["limit_source"] == "product_default"
    refreshed = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert refreshed["refresh_metadata"]["state"] == "all"
    assert refreshed["refresh_metadata"]["limit"] == 1000
    assert refreshed["refresh_metadata"]["state_source"] == "product_default"
    assert refreshed["refresh_metadata"]["limit_source"] == "product_default"

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--state",
                "open",
                "--limit",
                "50",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert observed_commands[-1][observed_commands[-1].index("--state") + 1] == "open"
    assert observed_commands[-1][observed_commands[-1].index("--limit") + 1] == "50"
    assert payload["state_source"] == "explicit"
    assert payload["limit_source"] == "explicit"


def test_external_intent_refresh_github_missing_gh_fails_without_snapshot_write(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    def fake_run(command, cwd, capture_output, text, encoding, check):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--format",
                "json",
            ]
        )

    assert excinfo.value.code == 2
    assert not (target / ".agentic-workspace" / "planning" / "external-intent-evidence.json").exists()
    assert not (target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json").exists()


def test_report_surfaces_finished_work_inspection_findings(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    archive_dir = target / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "system-intent-and-planning-trust-2026-04-21.md").write_text(
        "# System Intent And Planning Trust\n\n"
        "## Intent Satisfaction\n\n"
        "- Was original intent fully satisfied?: yes\n\n"
        "## Closure Check\n\n"
        "- Closure decision: archive-and-close\n"
        "- Larger-intent status: closed\n\n"
        "Implemented #220.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "#260",
                        "title": "Finished-work intent inspection",
                        "status": "open",
                        "kind": "lane",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                        "reopens": ["#220"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert any("Archived closeout" in finding["message"] for finding in payload["findings"])
    planning_report = next(report for report in payload["module_reports"] if report["module"] == "planning")
    assert planning_report["finished_work_inspection"]["counts"]["likely_premature_closeout_count"] == 1


def test_report_surfaces_compact_lower_trust_closeout_summary(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "external-intent-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "#closed-without-residue",
                        "title": "Closed without planning residue",
                        "status": "closed",
                        "kind": "lane",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["closeout_trust"]["status"] == "present"
    assert payload["closeout_trust"]["trust"] == "lower-trust"
    assert payload["closeout_trust"]["lower_trust_closeout_count"] == 1
    assert any("Closed external planning item #closed-without-residue" in item for item in payload["closeout_trust"]["sample_signals"])
    action = payload["closeout_trust"]["durable_residue_action"]
    assert action["action"] == "route-durable-residue"
    assert "lower-trust closeout signals" in action["summary"]


def test_report_text_surfaces_compact_lower_trust_closeout_summary(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "external-intent-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "#closed-without-residue",
                        "title": "Closed without planning residue",
                        "status": "closed",
                        "kind": "lane",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target)]) == 0

    text = capsys.readouterr().out
    assert "Maintenance pressure:" in text
    assert "attention" in text
    assert "maintenance-pressure detail" in text


def test_report_surfaces_active_planning_in_standing_intent_view(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        (target / ".agentic-workspace" / "planning" / "state.toml"),
        "[todo]\n"
        "active_items = [\n"
        "    { id = 'standing-intent-slice', status = 'in-progress', surface = '.agentic-workspace/planning/execplans/standing-intent-slice.md', why_now = 'standing intent needs a durable owner.' }\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = []\n"
        "candidates = []\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "planning" / "execplans" / "standing-intent-slice.md").write_text(
        "# Standing Intent Slice\n\n"
        "## Goal\n\n"
        "- Give standing intent a durable owner.\n\n"
        "## Non-Goals\n\n"
        "- None.\n\n"
        "## Intent Continuity\n\n"
        "- Larger intended outcome: make durable repo guidance recoverable.\n"
        "- This slice completes the larger intended outcome: no\n"
        "- Continuation surface: state.toml candidate lane `standing-intent-durability`\n\n"
        "## Required Continuation\n\n"
        "- Required follow-on for the larger intended outcome: yes\n"
        "- Owner surface: .agentic-workspace/planning/state.toml\n"
        "- Activation trigger: precedence rules still need to land.\n\n"
        "## Iterative Follow-Through\n\n"
        "- What this slice enabled: standing intent is classifiable.\n"
        "- Intentionally deferred: precedence rules.\n"
        "- Discovered implications: reporting should surface effective standing intent.\n"
        "- Proof achieved now: pending\n"
        "- Validation still needed: pending\n"
        "- Next likely slice: precedence and supersession.\n\n"
        "## Delegated Judgment\n\n"
        "- Requested outcome: Give standing intent a durable owner.\n"
        "- Hard constraints: Keep the first slice compact.\n"
        "- Agent may decide locally: the smallest report shape.\n"
        "- Escalate when: a new source of truth would be required.\n\n"
        "## Active Milestone\n\n"
        "- Status: in-progress\n"
        "- Scope: ship standing-intent classification and reporting.\n"
        "- Ready: ready\n"
        "- Blocked: none\n"
        "- optional_deps: none\n\n"
        "## Immediate Next Action\n\n"
        "- Add the standing-intent report view.\n\n"
        "## Blockers\n\n"
        "- None.\n\n"
        "## Touched Paths\n\n"
        "- .agentic-workspace/docs/standing-intent-contract.md\n\n"
        "## Invariants\n\n"
        "- Standing intent stays subordinate to owner surfaces.\n\n"
        "## Validation Commands\n\n"
        "- uv run agentic-workspace report --target ./repo --format json\n\n"
        "## Completion Criteria\n\n"
        "- Standing intent is visible in reporting.\n\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    standing_classes = {item["class"]: item for item in payload["standing_intent"]["effective_view"]["items"]}
    active_direction = standing_classes["active_directional_intent"]
    assert active_direction["status"] == "present"
    assert active_direction["owner_surface"] == ".agentic-workspace/planning/execplans/standing-intent-slice.md"
    assert active_direction["summary"] == "Add the standing-intent report view."
    assert active_direction["requested_outcome"] == "Give standing intent a durable owner."
    assert payload["standing_intent"]["precedence_order"][1]["rule"] == (
        "Active planning direction governs the current bounded slice unless it conflicts with checked-in hard policy."
    )
    assert payload["standing_intent"]["supersession_rules"][2]["rule"] == "active_lane_direction_is_slice_scoped"
    assert payload["standing_intent"]["stronger_home_model"]["candidate_classes"][1]["class"] == "active_directional_intent"


def test_report_surfaces_combined_execution_shape_for_planning_backed_slice(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
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
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\n"
        "active_items = [\n"
        "    { id = 'execution-shape-slice', status = 'in-progress', surface = '.agentic-workspace/planning/execplans/execution-shape-slice.md', why_now = 'make default execution shape visible.' }\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = []\n"
        "candidates = []\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "planning" / "execplans" / "execution-shape-slice.md").write_text(
        "# Execution Shape Slice\n\n"
        "## Goal\n\n"
        "- Make default execution shape visible.\n\n"
        "## Non-Goals\n\n"
        "- Add scheduler behavior.\n\n"
        "## Intent Continuity\n\n"
        "- Larger intended outcome: make config-backed execution posture decisive.\n"
        "- This slice completes the larger intended outcome: yes\n"
        "- Continuation surface: none\n\n"
        "## Required Continuation\n\n"
        "- Required follow-on for the larger intended outcome: no\n"
        "- Owner surface: none\n"
        "- Activation trigger: none\n\n"
        "## Iterative Follow-Through\n\n"
        "- What this slice enabled: one compact execution-shaping answer.\n"
        "- Intentionally deferred: none\n"
        "- Discovered implications: deviations should stay visible.\n"
        "- Proof achieved now: pending\n"
        "- Validation still needed: pending\n"
        "- Next likely slice: none.\n\n"
        "## Delegated Judgment\n\n"
        "- Requested outcome: Make default execution shape visible.\n"
        "- Hard constraints: Keep it advisory and config-driven.\n"
        "- Agent may decide locally: the smallest combined report surface.\n"
        "- Escalate when: a new source of truth would be required.\n\n"
        "## Capability Posture\n\n"
        "- Execution class: boundary-shaping\n"
        "- Recommended strength: strong\n"
        "- Preferred location: either\n"
        "- Delegation friendly: yes\n"
        "- Strong external reasoning: allowed\n"
        "- Why: contract shaping needs stronger judgment before bounded follow-through.\n\n"
        "## Active Milestone\n\n"
        "- ID: execution-shape\n"
        "- Status: in-progress\n"
        "- Scope: expose one combined execution recommendation.\n"
        "- Ready: ready\n"
        "- Blocked: none\n"
        "- optional_deps: none\n\n"
        "## Immediate Next Action\n\n"
        "- Add the combined execution-shape report answer.\n\n"
        "## Blockers\n\n"
        "- None.\n\n"
        "## Touched Paths\n\n"
        "- src/agentic_workspace/cli.py\n\n"
        "## Invariants\n\n"
        "- Config remains posture rather than scheduler policy.\n\n"
        "## Validation Commands\n\n"
        "- uv run pytest tests/test_workspace_cli.py -q\n\n"
        "## Completion Criteria\n\n"
        "- One combined execution-shape answer is visible.\n\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    execution_shape = payload["execution_shape"]
    assert execution_shape["status"] == "present"
    assert execution_shape["task_shape"]["id"] == "planning-backed-broad-work"
    assert execution_shape["default_posture"]["planner_executor_pattern"] == "strong-planner-cheap-executor-available"
    assert execution_shape["default_posture"]["handoff_preference"] == "prefer-internal-when-safe"
    assert execution_shape["capability_posture"]["execution class"] == "boundary-shaping"
    assert execution_shape["recommendation"]["id"] == "planner-first-then-bounded-executor"
    assert execution_shape["recommendation"]["consult"] == ["agentic-planning handoff --format json"]
    assert execution_shape["recommendation"]["best_target_fits"] == []
    assert execution_shape["current_slice"]["task_id"] == "execution-shape-slice"
    assert execution_shape["resolved_targets"] == []
    assert "active execplan" in execution_shape["task_shape"]["summary"]


def test_report_surfaces_agent_efficiency_output_contract_from_repo_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\noptimization_bias = "agent-efficiency"\n',
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["output_contract"]["optimization_bias"] == "agent-efficiency"
    assert payload["output_contract"]["optimization_bias_source"] == "repo-config"
    assert payload["output_contract"]["report_density"] == "compact"
    assert "execution method" in payload["output_contract"]["must_not_change"]
    assert payload["operating_posture"]["optimization_bias"]["mode"] == "agent-efficiency"
    assert payload["operating_posture"]["optimization_bias"]["residue_density"] == "compact-carry-forward"


def test_report_text_mentions_agent_efficiency_bias(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\noptimization_bias = "agent-efficiency"\n',
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target)]) == 0

    text = capsys.readouterr().out
    assert "Output bias: agent-efficiency (repo-config)" in text
    assert "Rendering: keep this view terse" in text


def test_default_command_outputs_stay_router_sized(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    budgets = {
        "start": (["start", "--target", str(target), "--format", "json"], 9800),
        "summary": (["summary", "--target", str(target), "--format", "json"], 13000),
        "report": (["report", "--target", str(target), "--format", "json"], 18000),
        "proof": (
            ["proof", "--target", str(target), "--changed", ".agentic-workspace/config.toml", "--format", "json"],
            9000,
        ),
        "status": (["status", "--target", str(target), "--format", "json"], 25000),
    }
    for command_name, (args, budget) in budgets.items():
        assert cli.main(args) == 0
        payload = json.loads(capsys.readouterr().out)
        assert len(json.dumps(payload, sort_keys=True)) <= budget, command_name

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert "mixed_agent" not in status_payload["config"]
    assert status_payload["config"]["detail_command"] == "agentic-workspace config --target ./repo --format json"
    assert status_payload["deeper_detail"]["report_command"] == "agentic-workspace report --target ./repo --profile full --format json"
    assert status_payload["cost_provenance"]["classification"] == "compact-after-lifecycle"
    assert status_payload["cost_provenance"]["module_count"] >= 1


def test_report_surfaces_large_file_hotspots_as_repo_friction_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "balanced"\n',
        encoding="utf-8",
    )
    (target / "src").mkdir()
    (target / "src" / "big_module.py").write_text("\n".join(f"line_{index}" for index in range(450)) + "\n")

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["policy_mode"] == "balanced"
    assert payload["repo_friction"]["initiative_posture"] == "bounded-evidence-backed-action"
    assert payload["repo_friction"]["large_file_hotspots"]["count"] == 1
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["path"] == "src/big_module.py"
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["line_count"] == 450
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["kind"] == "code"
    hotspot = payload["repo_friction"]["large_file_hotspots"]["items"][0]
    assert hotspot["classification"] == "large-source-hotspot"
    assert hotspot["suggested_action"] == "inspect-symbols-before-refactor"
    assert "Use search and focused symbols first" in hotspot["context_strategy"]
    assert hotspot["primary_next_action"]["action"] == "inspect-symbols-before-refactor"
    assert hotspot["primary_next_action"]["run"] == hotspot["primary_next_action"]["command"]
    signal = payload["improvement_intake"]["improvement_signal_candidates"][0]
    assert signal["candidate_kind"] == "workspace-improvement-signal-candidate/v1"
    assert signal["kind"] == "architecture_cost"
    assert signal["suspected_owner"] == "src/big_module.py"
    assert signal["immediate_action"] == "route"
    assert signal["classification"] == "large-source-hotspot"
    assert signal["suggested_action"] == "inspect-symbols-before-refactor"
    assert signal["primary_next_action"]["action"] == "inspect-symbols-before-refactor"


def test_report_does_not_promote_regenerable_cache_as_large_file_friction(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    cache_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("\n".join(f"line_{index}" for index in range(950)) + "\n", encoding="utf-8")

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    large_files = payload["repo_friction"]["large_file_hotspots"]
    assert large_files["count"] == 0
    assert large_files["ignored_regenerable_cache_count"] == 1
    ignored = large_files["ignored_regenerable_caches"][0]
    assert ignored["path"] == ".agentic-workspace/local/cache/external-intent-evidence.json"
    assert ignored["surface_role"] == "regenerable-local-cache"
    assert ignored["suggested_action"] == "do-not-refactor"
    assert "local cache" in large_files["cache_rule"]
    assert payload["improvement_intake"]["improvement_signal_candidates"] == []


def test_report_surfaces_concept_hotspots_as_repo_friction_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "docs").mkdir()
    _write(
        (target / "docs" / "routing-contract.md"),
        "\n".join(f"line_{index}" for index in range(220)) + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["concept_surface_hotspots"]["count"] == 1
    assert payload["repo_friction"]["concept_surface_hotspots"]["items"][0]["path"] == "docs/routing-contract.md"
    assert payload["repo_friction"]["concept_surface_hotspots"]["items"][0]["kind"] == "docs"
    assert payload["repo_friction"]["concept_surface_hotspots"]["items"][0]["surface_role"] == "canonical-doc"


def test_report_consumes_external_codebase_map_when_present(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "tools").mkdir()
    (target / "tools" / "codebase-map.json").write_text(
        json.dumps(
            {
                "large_modules": [
                    {
                        "path": "src/generated_hotspot.py",
                        "line_count": 900,
                        "function_count": 12,
                        "class_count": 1,
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["evidence_classes"] == [
        "large_file_hotspots",
        "concept_surface_hotspots",
        "planning_friction",
        "validation_friction",
        "external_evidence",
    ]
    assert payload["repo_friction"]["external_evidence"][0]["kind"] == "codebase-map"
    assert payload["repo_friction"]["external_evidence"][0]["path"] == "tools/codebase-map.json"
    assert payload["repo_friction"]["external_evidence"][0]["status"] == "loaded"
    assert payload["repo_friction"]["external_evidence"][0]["items"][0]["path"] == "src/generated_hotspot.py"
    assert payload["repo_friction"]["external_evidence"][0]["items"][0]["line_count"] == 900


def test_report_surfaces_promotable_setup_findings_as_repo_friction_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "tools").mkdir()
    (target / "tools" / "setup-findings.json").write_text(
        json.dumps(
            {
                "kind": "workspace-setup-findings/v1",
                "findings": [
                    {
                        "class": "repo_friction_evidence",
                        "summary": "Validation repeatedly fails after agents hand-author schema shape.",
                        "confidence": 0.9,
                        "path": "src/agentic_workspace/cli.py",
                        "observed_during": "uv run pytest tests/test_workspace_cli.py",
                        "signal_kind": "validation_friction",
                        "cost": "Agents spend extra repair loops fixing shape that a writer helper could construct.",
                        "suspected_owner": "agentic-workspace create-review",
                        "likely_remediation": "scaffold",
                        "recurrence": "repeated",
                        "validation_failure_class": "interface_design_error",
                        "refs": [".agentic-workspace/docs/reporting-contract.md"],
                    },
                    {
                        "class": "repo_friction_evidence",
                        "summary": "Low-confidence note stays transient.",
                        "confidence": 0.4,
                        "path": "src/ignored.py",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["evidence_classes"] == [
        "large_file_hotspots",
        "concept_surface_hotspots",
        "planning_friction",
        "validation_friction",
        "external_evidence",
    ]
    setup_findings = next(evidence for evidence in payload["repo_friction"]["external_evidence"] if evidence["kind"] == "setup-findings")
    assert setup_findings["path"] == "tools/setup-findings.json"
    assert setup_findings["items"][0]["path"] == "src/agentic_workspace/cli.py"
    assert setup_findings["items"][0]["validation_failure_class"] == "interface_design_error"
    assert setup_findings["items"][0]["promotion_reason"] == "grounded friction evidence is worth preserving"
    signal = payload["improvement_intake"]["improvement_signal_candidates"][0]
    assert signal["kind"] == "validation_friction"
    assert signal["observed_during"] == "uv run pytest tests/test_workspace_cli.py"
    assert signal["suspected_owner"] == "agentic-workspace create-review"
    assert signal["likely_remediation"] == "scaffold"
    assert signal["recurrence"] == "repeated"
    assert signal["validation_failure_class"] == "interface_design_error"
    assert payload["improvement_intake"]["setup_findings"]["status"] == "loaded"
    assert payload["improvement_intake"]["setup_findings"]["loaded_count"] == 2
    assert payload["improvement_intake"]["setup_findings"]["promotable_counts"]["repo_friction_evidence"] == 1
    assert payload["improvement_intake"]["setup_findings"]["transient_count"] == 1


def test_report_surfaces_reporting_only_repo_friction_posture(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "reporting"\n',
        encoding="utf-8",
    )
    (target / "docs").mkdir()
    (target / "docs" / "big_note.md").write_text("\n".join(f"line_{index}" for index in range(450)) + "\n")

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["policy_mode"] == "reporting"
    assert payload["repo_friction"]["policy_target"] == "repo-directed-improvement"
    assert payload["repo_friction"]["friction_response_order"][2]["action"] == "avoid-externalizing-honestly-absorbable-friction"
    assert payload["repo_friction"]["initiative_posture"] == "reporting-only"
    assert payload["repo_friction"]["incidental_finding_policy"]["status"] == "required-reporting"
    assert "separate acted-on improvements" in payload["repo_friction"]["incidental_finding_policy"]["report_how"][1]
    assert payload["repo_friction"]["rule"] == (
        "Surface notable friction through bounded reporting or residue; do not act on it without explicit direction."
    )
    assert payload["repo_friction"]["reporting_destinations"] == [
        "agentic-workspace report --target ./repo --format json",
        "review outputs",
        ".agentic-workspace/planning/state.toml or the active execplan when the current slice already owns planning residue",
    ]
