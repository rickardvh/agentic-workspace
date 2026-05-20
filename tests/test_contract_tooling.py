from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace import contract_tooling
from command_generation.generated_package_loader import load_generated_command_package_for_entrypoint


def _command_operation_ids(command: dict[str, object]) -> set[str]:
    operation_ref = command.get("operation_ref", {})
    operation_ids = {str(operation_ref["id"])} if isinstance(operation_ref, dict) and "id" in operation_ref else set()

    def collect_interface(interface: object) -> None:
        if not isinstance(interface, dict):
            return
        nested_operation_ref = interface.get("operation_ref", {})
        if isinstance(nested_operation_ref, dict) and "id" in nested_operation_ref:
            operation_ids.add(str(nested_operation_ref["id"]))
        subcommands = interface.get("subcommands", [])
        if isinstance(subcommands, list):
            for subcommand in subcommands:
                collect_interface(subcommand)

    collect_interface(command.get("interface"))
    return operation_ids


def test_contract_tooling_check_passes() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main([]) == 0


def test_command_contracts_do_not_expose_profile_flags() -> None:
    def walk_options(value: object) -> list[dict[str, object]]:
        if isinstance(value, dict):
            found: list[dict[str, object]] = []
            options = value.get("options")
            if isinstance(options, list):
                found.extend(option for option in options if isinstance(option, dict))
            for nested in value.values():
                found.extend(walk_options(nested))
            return found
        if isinstance(value, list):
            found: list[dict[str, object]] = []
            for nested in value:
                found.extend(walk_options(nested))
            return found
        return []

    manifests = [
        contract_tooling.cli_commands_manifest(),
        contract_tooling.command_package_ir_manifest(),
    ]

    assert not [
        option
        for manifest in manifests
        for option in walk_options(manifest)
        if option.get("name") == "profile" or "--profile" in option.get("flags", [])
    ]


def test_current_agent_facing_surfaces_do_not_teach_profile_flags() -> None:
    root = Path(__file__).resolve().parents[1]
    skill_roots = [
        root / "packages" / "planning" / "skills",
        root / ".agentic-workspace" / "planning" / "skills",
        root / "tools" / "model-cli-harness" / "fixtures",
    ]

    offenders = [
        path.relative_to(root).as_posix()
        for skill_root in skill_roots
        for path in skill_root.rglob("*")
        if path.is_file() and path.suffix in {".md", ".toml", ".json"}
        if "--profile" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_contract_inventory_declares_owner_choice_model() -> None:
    manifest = contract_tooling.contract_inventory_manifest()
    concern_classes = {entry["id"]: entry for entry in manifest["owner_choice_model"]["concern_classes"]}

    assert {
        "config_policy",
        "contract_schema_authority",
        "planning_active_state",
        "memory_durable_understanding",
        "review_evidence",
        "generated_adapter_output",
        "package_payload",
        "runtime_primitive_implementation",
    } <= concern_classes.keys()
    assert concern_classes["contract_schema_authority"]["owner_surface"] == "src/agentic_workspace/contracts/"
    assert concern_classes["review_evidence"]["authority_class"] == "historical-evidence"


def test_skill_specs_contract_models_startup_and_planning_behavior() -> None:
    manifest = contract_tooling.skill_specs_manifest()
    schema = contract_tooling.contract_schema("skill_spec.schema.json")
    cli_manifest = contract_tooling.cli_commands_manifest()

    assert list(Draft202012Validator(schema).iter_errors(manifest)) == []
    assert manifest["rule"].startswith("Skills steer agent behavior")

    specs = {entry["id"]: entry for entry in manifest["specs"]}
    assert {"startup-router", "planning-autopilot"} <= specs.keys()
    transition_gates = {entry["id"]: entry for entry in manifest["transition_gates"]}
    module_slots = {entry["id"]: entry for entry in manifest["module_slots"]}
    assert {
        "startup-to-work",
        "work-to-planning",
        "work-to-proof",
        "work-to-memory-residue",
        "proof-to-closeout",
    } == transition_gates.keys()
    assert {"workspace", "planning", "planning.closeout", "workspace.proof", "memory"} == module_slots.keys()
    behavior_fixtures = {entry["id"]: entry for entry in manifest["generated_target_behavior_fixtures"]}
    assert {
        "direct-task-cheap-path",
        "lane-task-planning-gate",
        "no-cli-conservative-fallback",
    } == behavior_fixtures.keys()

    required_gate_fields = {
        "trigger",
        "preferred_cli_or_report",
        "interpreted_fields",
        "allowed_actions",
        "forbidden_actions",
        "proof_obligations",
        "closeout_obligations",
        "fallback_when_cli_unavailable",
        "generated_target_requirements",
    }
    for gate in transition_gates.values():
        assert required_gate_fields <= gate.keys()
        assert gate["preferred_cli_or_report"]
        assert gate["fallback_when_cli_unavailable"]
        assert gate["allowed_actions"]
        assert gate["forbidden_actions"]
        assert gate["interpreted_fields"]
        assert gate["generated_target_requirements"]["must_preserve"]

    required_slot_fields = {"owns", *(required_gate_fields - {"trigger"})}
    for slot in module_slots.values():
        assert required_slot_fields <= slot.keys()
        assert slot["preferred_cli_or_report"]
        assert slot["fallback_when_cli_unavailable"]
        assert slot["allowed_actions"]
        assert slot["forbidden_actions"]
        assert slot["interpreted_fields"]
        assert slot["generated_target_requirements"]["must_preserve"]

    assert "next_safe_action" in " ".join(module_slots["workspace"]["interpreted_fields"])
    assert "state.toml" in " ".join(module_slots["planning"]["forbidden_actions"])
    assert "completion_claim_allowed" in transition_gates["proof-to-closeout"]["interpreted_fields"]
    assert "durable_residue_decision" in transition_gates["work-to-memory-residue"]["interpreted_fields"]
    assert behavior_fixtures["direct-task-cheap-path"]["implementation_allowed"] is True
    assert behavior_fixtures["lane-task-planning-gate"]["implementation_allowed"] is False
    assert behavior_fixtures["lane-task-planning-gate"]["required_skill"] == "planning-autopilot"
    assert behavior_fixtures["no-cli-conservative-fallback"]["proof_required"] is True
    assert any("forbidden actions" in item for item in behavior_fixtures["no-cli-conservative-fallback"]["must_preserve"])

    startup = specs["startup-router"]
    startup_command = startup["preferred_cli_commands"][0]
    assert startup["proportionality"]["no_artifact_by_default"] is True
    assert startup_command["command"] == "start"
    assert startup_command["mutates_state"] is False
    assert "skill_routing.preferred_routes" in startup_command["key_output_fields"]
    assert any("Create planning" in action or "planning" in action for action in startup["forbidden_actions"])
    assert startup["generated_target_requirements"]["status"] == "ready-for-renderer"

    planning = specs["planning-autopilot"]
    planning_commands = {command["id"]: command for command in planning["preferred_cli_commands"]}
    assert planning["proportionality"]["ordinary_work_rule"].startswith("Use planning only when the router requires it")
    assert planning_commands["planning-promote-to-plan"]["mutates_state"] is True
    assert planning_commands["planning-delegation-decision"]["mutates_state"] is True
    assert any("Hand-edit planning state" in action for action in planning["forbidden_actions"])
    assert planning["generated_target_requirements"]["status"] == "contract-only"

    def _command_registry() -> dict[str, dict[str, object]]:
        registry: dict[str, dict[str, object]] = {}

        def visit(command: dict[str, object], prefix: str = "") -> None:
            name = str(command["name"])
            ref = f"{prefix}.{name}" if prefix else name
            registry[ref] = command
            for subcommand in command.get("subcommands", []):
                if isinstance(subcommand, dict):
                    visit(subcommand, ref)

        for command in cli_manifest["commands"]:
            visit(command)
        return registry

    commands_by_ref = _command_registry()
    for command_ref, command in commands_by_ref.items():
        assert "mutates_state" in command, command_ref
    for mutating_command_ref in {
        "planning.archive-plan",
        "planning.close-item",
    }:
        assert commands_by_ref[mutating_command_ref]["mutates_state"] is True
    for spec in manifest["specs"]:
        for affordance in spec["preferred_cli_commands"]:
            command_ref = affordance["command_ref"]
            assert command_ref in commands_by_ref
            assert affordance["command"].replace(" ", ".") == command_ref
            assert affordance["mutates_state"] is commands_by_ref[command_ref]["mutates_state"]


def test_skillspec_generated_startup_target_preserves_behavior_contract() -> None:
    manifest = contract_tooling.skill_specs_manifest()
    rendered = contract_tooling.render_skillspec_target_skill(manifest, "startup-router")
    checked_in = Path("generated/workspace/skills/startup-router/SKILL.md").read_text(encoding="utf-8")

    assert checked_in == rendered
    assert "uv run agentic-workspace start --task" in checked_in
    assert "`immediate_next_allowed_action`" in checked_in
    assert "`next_safe_action.implementation_allowed`" in checked_in
    assert "Open raw planning or memory state before compact startup routing points there." in checked_in
    assert "Read `.agentic-workspace/WORKFLOW.md` before other workspace files." in checked_in
    assert "Direct task: continue without durable artifacts" in checked_in
    assert "Lane or epic task: block implementation" in checked_in
    assert "Fallback task: when the CLI is unavailable" in checked_in
    assert "`direct-task-cheap-path`" in checked_in
    assert "`lane-task-planning-gate`" in checked_in
    assert "`no-cli-conservative-fallback`" in checked_in
    assert "Generated targets surface required skill visibility." in checked_in


def test_skillspec_generated_codex_plugin_preserves_framework_native_contract() -> None:
    manifest = contract_tooling.skill_specs_manifest()
    rendered = contract_tooling.render_skillspec_plugin_target(manifest, "codex-plugin")
    checked_in = Path("generated/workspace/plugins/codex/.codex-plugin/plugin.json").read_text(encoding="utf-8")
    payload = json.loads(checked_in)
    metadata = payload["agenticWorkspace"]

    assert checked_in == rendered
    assert payload["name"] == "agentic-workspace"
    assert payload["skills"] == "./skills/"
    assert metadata["generated"] is True
    assert metadata["source"] == "src/agentic_workspace/contracts/skill_specs.json"
    assert metadata["whereToEdit"] == "src/agentic_workspace/contracts/skill_specs.json"
    assert metadata["framework"] == "codex"
    assert metadata["sourceSkillSpecs"] == ["startup-router"]
    assert metadata["generatedSkills"] == ["generated/workspace/skills/startup-router/SKILL.md"]
    assert metadata["cliDependency"] == "preferred-when-available"
    assert 'uv run agentic-workspace start --task "<task>" --format json' in metadata["preferredCli"]
    assert "next_safe_action.completion_claim_allowed" in metadata["interpretedFields"]
    assert metadata["nextSafeActionSemantics"] is True
    fixture_ids = {fixture["id"] for fixture in metadata["behaviorFixtures"]}
    assert fixture_ids == {"direct-task-cheap-path", "lane-task-planning-gate", "no-cli-conservative-fallback"}
    lane_fixture = next(fixture for fixture in metadata["behaviorFixtures"] if fixture["id"] == "lane-task-planning-gate")
    assert lane_fixture["required_skill"] == "planning-autopilot"
    assert lane_fixture["implementation_allowed"] is False
    assert lane_fixture["proof_required"] is True
    assert "next_safe_action.proof_required" in lane_fixture["expected_fields"]
    assert any("Open raw planning or memory state" in action for action in metadata["forbiddenActions"])
    assert any("WORKFLOW.md" in fallback for fallback in metadata["fallbackWhenCliUnavailable"])
    assert any("Generated skill linkage" in requirement for requirement in metadata["mustPreserve"])


def test_operational_affordance_roles_classify_first_contact_and_diagnostics() -> None:
    manifest = contract_tooling.operational_affordance_roles_manifest()
    schema = contract_tooling.contract_schema("operational_affordance_roles.schema.json")
    assert list(Draft202012Validator(schema).iter_errors(manifest)) == []

    command_roles = {entry["command"]: entry for entry in manifest["command_roles"]}
    assert command_roles["start"]["role"] == "ordinary_first_contact"
    assert command_roles["start"]["first_line"] is True
    assert command_roles["implement --changed"]["role"] == "changed_path_first_contact"
    assert command_roles["preflight"]["role"] == "recovery_takeover"
    assert command_roles["preflight"]["first_line"] is False
    assert command_roles["summary"]["role"] == "active_planning_state"
    assert command_roles["WORKFLOW.md"]["role"] == "no_cli_fallback_projection"

    warning_roles = {entry["warning_class"]: entry for entry in manifest["warning_roles"]}
    checker_text = Path("packages/planning/scripts/check/check_planning_surfaces.py").read_text(encoding="utf-8")
    checker_warning_classes = set(re.findall(r'WARNING_[A-Z0-9_]+ = "([^"]+)"', checker_text))
    assert checker_warning_classes <= warning_roles.keys()
    assert warning_roles["archive_missing_execution_summary"]["role"] == "diagnostic"
    assert "planning closeout evidence options" in warning_roles["archive_missing_execution_summary"]["preferred_remedy"]
    assert warning_roles["planning_artifact_freehand"]["role"] == "external_manual_drift"
    assert "intake-artifact" in warning_roles["planning_artifact_freehand"]["preferred_remedy"]

    source_boundary_review = manifest["source_boundary_review"]
    assert source_boundary_review["review_issue"] == "#1032"
    assert source_boundary_review["status"] == "ready-to-close"
    assert "archive_missing_execution_summary" in source_boundary_review["demoted_warning_classes"]
    assert "planning_artifact_freehand" in source_boundary_review["demoted_warning_classes"]
    assert any(item["issue"] == "#1033" for item in source_boundary_review["routed_followups"])

    report_roles = {entry["section"]: entry for entry in manifest["report_section_roles"]}
    assert report_roles["next_action"]["default_visibility"] == "first_line"
    assert report_roles["report_profile.feature_tier"]["role"] == "inventory"
    assert report_roles["report_profile.feature_tier"]["default_visibility"] == "selector_or_verbose"
    assert report_roles["planning archives"]["role"] == "historical"
    assert manifest["closeout_writer_direction"]["source_issue"] == "#1029"


def test_agent_feedback_schema_validates_normalized_feedback_artifact() -> None:
    schema = contract_tooling.contract_schema("agent_feedback.schema.json")
    metadata = schema["x-agentic-workspace"]
    assert metadata["surface_role"] == "optional-review-artifact-schema"
    assert metadata["required_operating_surface"] is False
    assert metadata["emitted_by_command"] is False

    sample = {
        "kind": "agent-feedback-review/v1",
        "schema_version": "agentic-workspace/agent-feedback/v1",
        "evaluated_at": "2026-04-26",
        "prompt_ref": "agent-feedback-prompt.txt",
        "context": {
            "target": ".",
            "work_window": "current self-improvement branch",
            "package_surfaces_used": [
                "agentic-workspace report --target . --format json",
                "agentic-workspace summary --format json",
            ],
        },
        "impact": {
            "outcome": "better recovery and proof routing",
            "quality": "higher closeout confidence",
            "efficiency": "lower total reconstruction work",
            "cognitive_load": "lower when compact routes answer the task",
        },
        "findings": [
            {
                "id": "ordinary-agent-path",
                "summary": "The ordinary path should be one compact answer.",
                "classification": "product-general",
                "evidence": ["agent-feedback-prompt.txt evaluation"],
                "severity": "medium",
            }
        ],
        "suggestions": [
            {
                "finding_id": "ordinary-agent-path",
                "summary": "Expose entry, state, proof, and escalation guidance together.",
                "expected_effect": "new agents can start with less reconstruction",
            }
        ],
        "follow_up_routing": {
            "issues": ["#388"],
            "deferred": [],
        },
    }

    errors = list(Draft202012Validator(schema).iter_errors(sample))
    assert errors == []


def test_workspace_config_schema_accepts_supported_system_intent_declaration() -> None:
    schema = contract_tooling.contract_schema("workspace_config.schema.json")
    sample = {
        "schema_version": 1,
        "system_intent": {
            "sources": ["SYSTEM_INTENT.md", "README.md"],
            "preferred_source": "SYSTEM_INTENT.md",
        },
    }

    errors = list(Draft202012Validator(schema).iter_errors(sample))
    assert errors == []


def test_subsystem_intent_schema_accepts_provenance_and_revision_fields() -> None:
    schema = contract_tooling.contract_schema("subsystem_intent.schema.json")
    sample = {
        "schema_version": 1,
        "kind": "agentic-workspace/subsystem-intent-set/v1",
        "rule": "Subsystem intent is decision pressure.",
        "subsystems": [
            {
                "id": "access-log",
                "scope": "audit log storage and reporting",
                "status": "needs-review",
                "summary": "Access logs must remain auditable for compliance review.",
                "governing_intents": ["Keep audit evidence queryable."],
                "anti_intents": ["Do not replace audit evidence with transient chat context."],
                "decision_tests": ["Does this change preserve auditability?"],
                "source_records": [
                    {
                        "source_type": "issue",
                        "ref": "#746",
                        "summary": "Durable intent needs provenance.",
                        "observed_at": "2026-05-05",
                    }
                ],
                "confidence": "medium",
                "needs_review": True,
                "supersedes": ["old-audit-intent"],
                "superseded_by": [],
                "last_reviewed_at": "2026-05-05",
                "open_questions": ["Which retention rule applies?"],
                "interpretation_notes": "Inferred from issue discussion.",
            }
        ],
    }

    errors = list(Draft202012Validator(schema).iter_errors(sample))
    assert errors == []


def test_workspace_config_schema_accepts_custom_agent_instructions_file() -> None:
    schema = contract_tooling.contract_schema("workspace_config.schema.json")
    sample = {
        "schema_version": 1,
        "workspace": {
            "agent_instructions_file": "docs/agent-instructions.md",
        },
    }

    errors = list(Draft202012Validator(schema).iter_errors(sample))
    assert errors == []


def test_command_adapter_generation_contract_identifies_defaults_candidate() -> None:
    manifest = contract_tooling.command_adapter_generation_manifest()
    adapters = {adapter["id"]: adapter for adapter in manifest["adapters"]}

    defaults_adapter = adapters["defaults.report.cli"]

    assert defaults_adapter["status"] == "generated"
    assert defaults_adapter["command"]["name"] == "defaults"
    assert defaults_adapter["operation_ref"]["id"] == "defaults.report"
    assert defaults_adapter["runtime_binding"]["kind"] == "operation-primitive-sequence"
    assert defaults_adapter["effect_hints"]["read_only"] is True
    assert defaults_adapter["effect_hints"]["writes_repo_state"] is False
    assert "defaults.report.process" in defaults_adapter["conformance_refs"]
    assert "primitive implementation" in defaults_adapter["generation_boundary"]["runtime_owns"]


def test_command_adapter_generation_contract_records_package_migration_path() -> None:
    manifest = contract_tooling.command_adapter_generation_manifest()
    migration = manifest["package_surface_migration"]
    adapters = {adapter["id"]: adapter for adapter in manifest["adapters"]}

    assert migration["planning"]["program"] == "agentic-planning"
    assert migration["planning"]["status"] == "first-read-only-generated"
    assert adapters["planning.status.cli"]["command"]["program"] == migration["planning"]["program"]
    assert adapters["planning.status.cli"]["command"]["name"] == migration["planning"]["first_read_only_candidate"]
    assert migration["memory"]["program"] == "agentic-memory"
    assert migration["memory"]["status"] == "first-read-only-generated"
    assert adapters["memory.status.cli"]["command"]["program"] == migration["memory"]["program"]
    assert adapters["memory.status.cli"]["command"]["name"] == migration["memory"]["first_read_only_candidate"]


def test_command_adapter_generation_contract_records_multi_target_requirements() -> None:
    manifest = contract_tooling.command_adapter_generation_manifest()
    requirements = manifest["projection_requirements"]
    target_kinds = {target["kind"]: target for target in requirements["future_target_kinds"]}

    assert "operation id and registry path" in requirements["universal_command_truth"]
    assert "runtime primitive sequence" in requirements["universal_command_truth"]
    assert "help text layout" in requirements["adapter_specific_rendering"]
    assert "target-specific installation metadata" in requirements["adapter_specific_rendering"]
    assert "Python module paths" not in " ".join(requirements["universal_command_truth"])

    for kind in ("process-cli", "npm-cli", "posix-shell", "powershell", "binary", "local-mcp-tool", "generated-skill"):
        assert kind in target_kinds
        assert target_kinds[kind]["requirements"]

    assert target_kinds["process-cli"]["status"] == "supported-now"
    assert target_kinds["local-mcp-tool"]["status"] == "requirements-baseline"


def test_command_package_ir_declares_python_and_typescript_targets() -> None:
    manifest = contract_tooling.command_package_ir_manifest()
    packages = {package["id"]: package for package in manifest["packages"]}

    assert (
        manifest["generation_policy"]["ordinary_development_environment"] == "Python development remains sufficient for ordinary repo work."
    )
    assert manifest["generation_policy"]["test_environment"] == "Generated non-Python package tests run in Docker-selected proof lanes."
    maturity = {level["id"]: level for level in manifest["generation_policy"]["generated_package_maturity"]["levels"]}
    python_completion = manifest["generation_policy"]["python_cli_completion"]
    runtime_binding = manifest["generation_policy"]["non_python_runtime_binding"]
    assert {
        "metadata-proof-fixture",
        "parser-help-proof",
        "runnable-read-only-adapter",
        "runtime-backed-read-only-adapter",
        "weak-agent-safe-adapter",
        "mutation-capable-adapter",
        "deferred",
    } <= maturity.keys()
    assert "Weak agents may use only generated targets" in manifest["generation_policy"]["generated_package_maturity"]["routing_rule"]
    assert maturity["metadata-proof-fixture"]["runnable"] is False
    assert maturity["metadata-proof-fixture"]["weak_agent_routing"] == "forbidden"
    assert maturity["runnable-read-only-adapter"]["runnable"] is True
    assert "black-box conformance" in " ".join(maturity["runnable-read-only-adapter"]["promotion_requires"])
    assert maturity["weak-agent-safe-adapter"]["weak_agent_routing"] == "allowed-read-only"
    assert "unsupported command errors" in " ".join(maturity["weak-agent-safe-adapter"]["promotion_requires"])
    assert "runtime handoff failures" in " ".join(maturity["weak-agent-safe-adapter"]["promotion_requires"])
    assert "implementation-independent contracts or IR" in python_completion["finish_line"]
    assert "codegen-owned primitive executors" in python_completion["finish_line"]
    assert python_completion["current_state"] == "product-runtime-source-generation-incomplete"
    assert python_completion["completion_gate"]["state"] == "pending"
    assert python_completion["completion_gate"]["scope"] == "python-only"
    completion_evidence = {item["id"] for item in python_completion["completion_gate"]["satisfied_by"]}
    assert "python-docker-conformance" in completion_evidence
    assert "runtime-handlers-thin" in completion_evidence
    assert "representative-operation-ir-runtime-consumed" in completion_evidence
    assert "operation-execution-inventory-exhaustive" in completion_evidence
    assert "root-console-generated-command-smoke" in completion_evidence
    assert "product-specific-runtime-generated-output-owned" in completion_evidence
    assert any(
        "package-specific runtime primitive implementation" in item for item in python_completion["allowed_hand_owned_cli_responsibilities"]
    )
    assert "command parser shape" in python_completion["must_move_behind_contracts_or_generation"]
    assert "option and help interface semantics" in python_completion["must_move_behind_contracts_or_generation"]
    assert any("generic file" in item and "Markdown" in item for item in python_completion["must_move_behind_contracts_or_generation"])
    assert any(
        "product-specific executable runtime modules" in item for item in python_completion["must_move_behind_contracts_or_generation"]
    )
    assert any("weak-agent-safe-adapter" in item for item in python_completion["proof_requirements"])
    assert any("generic deterministic operations" in item for item in python_completion["proof_requirements"])
    assert any("generated/python target output" in item for item in python_completion["proof_requirements"])
    assert any("compact Python completion blocker report" in item for item in python_completion["proof_requirements"])
    assert runtime_binding["selected_model"] == "generated parser/help with process handoff to canonical Python CLI"
    assert "operation primitive implementation" in runtime_binding["runtime_owns"]
    assert "argv spelling and help rendering" in runtime_binding["target_projection_owns"]
    assert "adapter failures" in " ".join(runtime_binding["error_mapping"])
    assert "must not own runtime primitive behavior" in manifest["generation_policy"]["shell_adapter_policy"]
    assert "direct cli.py edits" in manifest["generation_policy"]["direct_cli_edit_policy"]
    assert "instead of package-local executable cli.py files" in manifest["generation_policy"]["direct_cli_edit_policy"]

    root_package = packages["root-workspace"]
    targets = {target["kind"]: target for target in root_package["targets"]}

    assert root_package["program"] == "agentic-workspace"
    assert targets["python"]["test_environment"] == "python-dev"
    assert targets["python"]["maturity_level_ref"] == "mutation-capable-adapter"
    assert targets["python"]["generation_status"] == "mutation-capable-adapter"
    assert targets["typescript"]["test_environment"] == "docker"
    assert targets["typescript"]["maturity_level_ref"] == "mutation-capable-adapter"
    assert targets["typescript"]["generation_status"] == "mutation-capable-adapter"
    assert targets["bash"]["generation_status"] == "deferred"
    assert targets["bash"]["maturity_level_ref"] == "deferred"
    assert targets["powershell"]["generation_status"] == "deferred"

    planning_targets = {target["kind"]: target for target in packages["planning-bootstrap"]["targets"]}
    assert planning_targets["typescript"]["test_environment"] == "docker"
    assert planning_targets["typescript"]["maturity_level_ref"] == "mutation-capable-adapter"
    assert planning_targets["typescript"]["generation_status"] == "mutation-capable-adapter"

    memory_targets = {target["kind"]: target for target in packages["memory-bootstrap"]["targets"]}
    assert memory_targets["typescript"]["test_environment"] == "docker"
    assert memory_targets["typescript"]["maturity_level_ref"] == "mutation-capable-adapter"
    assert memory_targets["typescript"]["generation_status"] == "mutation-capable-adapter"


def test_command_package_ir_reuses_generated_adapter_truth() -> None:
    package_ir = contract_tooling.command_package_ir_manifest()
    adapter_manifest = contract_tooling.command_adapter_generation_manifest()
    adapters = {adapter["id"]: adapter for adapter in adapter_manifest["adapters"]}
    commands = {command["adapter_id"]: command for package in package_ir["packages"] for command in package["commands"]}

    assert set(commands) == {
        "defaults.report.cli",
        "config.report.cli",
        "modules.report.cli",
        "start.context.cli",
        "summary.report.cli",
        "implement.context.cli",
        "preflight.report.cli",
        "proof.report.cli",
        "ownership.report.cli",
        "system-intent.sync.cli",
        "delegation-outcome.append.cli",
        "skills.report.cli",
        "planning.front-door.cli",
        "memory.front-door.cli",
        "external-intent.refresh-github.cli",
        "install.lifecycle.cli",
        "init.lifecycle.cli",
        "prompt.lifecycle.cli",
        "upgrade.lifecycle.cli",
        "uninstall.lifecycle.cli",
        "report.combined.cli",
        "reconcile.report.cli",
        "setup.guidance.cli",
        "status.report.cli",
        "doctor.report.cli",
        "planning.adopt.cli",
        "planning.archive-plan.cli",
        "planning.closeout.cli",
        "planning.close-item.cli",
        "planning.create-review.cli",
        "planning.delegation-decision.cli",
        "planning.status.cli",
        "planning.doctor.cli",
        "planning.handoff.cli",
        "planning.init.cli",
        "planning.install.cli",
        "planning.list-files.cli",
        "planning.intake-artifact.cli",
        "planning.new-plan.cli",
        "planning.promote-to-plan.cli",
        "planning.prompt.cli",
        "planning.summary.cli",
        "planning.uninstall.cli",
        "planning.upgrade.cli",
        "planning.verify-payload.cli",
        "planning.report.cli",
        "planning.reconcile.cli",
        "memory.status.cli",
        "memory.doctor.cli",
        "memory.install.cli",
        "memory.init.cli",
        "memory.adopt.cli",
        "memory.upgrade.cli",
        "memory.migrate-layout.cli",
        "memory.uninstall.cli",
        "memory.bootstrap-cleanup.cli",
        "memory.capture-note.cli",
        "memory.create-note.cli",
        "memory.current.cli",
        "memory.prompt.cli",
        "memory.report.cli",
        "memory.route.cli",
        "memory.route-report.cli",
        "memory.route-review.cli",
        "memory.search.cli",
        "memory.verify-payload.cli",
        "memory.sync-memory.cli",
        "memory.promotion-report.cli",
        "memory.list-files.cli",
        "memory.list-skills.cli",
    }
    defaults_command = commands["defaults.report.cli"]
    defaults_adapter = adapters["defaults.report.cli"]

    assert defaults_command["operation_ref"] == {
        "id": defaults_adapter["operation_ref"]["id"],
        "path": defaults_adapter["operation_ref"]["path"],
    }
    assert defaults_command["runtime_binding"] == defaults_adapter["runtime_binding"]
    assert defaults_command["effect_hints"] == defaults_adapter["effect_hints"]
    assert defaults_command["conformance_refs"] == defaults_adapter["conformance_refs"]
    assert "parser library" in defaults_command["projection_boundary"]["target_specific"]


def test_command_package_ir_rejects_generated_direct_function_call_handlers() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = copy.deepcopy(contract_tooling.command_package_ir_manifest())
    handlers = manifest["packages"][0]["python_runtime_binding"]["operation_executor"]["handlers"]
    handlers.append(
        {
            "primitive": "example.direct.load",
            "handler": "function_call",
            "import_module": "example",
            "function": "load",
            "kwargs": {},
        }
    )

    errors = module._validate_command_package_ir(manifest)

    assert any("declare python.function.call in operation IR instead" in error for error in errors)


def test_python_contract_consumption_declares_validated_loader_bindings() -> None:
    manifest = contract_tooling.python_contract_consumption_manifest()
    entries = manifest["validated_at_consumption"]

    assert all(entry["loader"].endswith("_manifest") for entry in entries)
    assert manifest["dynamic_validated_loader_boundary"] == [
        {
            "loader": "conformance_contract_manifest",
            "schema": "conformance.schema.json",
            "reason": "The contract path is selected from conformance_contracts.json at runtime, so only the schema side is static.",
        }
    ]
    assert {
        (entry["contract"], entry["schema"], entry["loader"]) for entry in entries if entry["contract"] == "command_adapter_generation.json"
    } == {
        (
            "command_adapter_generation.json",
            "command_adapter_generation.schema.json",
            "command_adapter_generation_manifest",
        )
    }
    assert any(entry["loader"] == "command_package_ir_manifest" for entry in entries)
    assert any(entry["loader"] == "lifecycle_generation_readiness_manifest" for entry in entries)


def test_lifecycle_generation_readiness_records_phase_risk_and_fixture_plan() -> None:
    manifest = contract_tooling.lifecycle_generation_readiness_manifest()
    commands = {(entry["surface"], entry["command"]): entry for entry in manifest["commands"]}

    assert manifest["phase_model"] == [
        "resolve context",
        "resolve selection",
        "plan changes",
        "validate plan",
        "apply changes",
        "verify result",
        "emit output/proof",
    ]
    assert commands[("root", "doctor")]["generation_eligibility"] == "eligible-read-only"
    assert commands[("root", "uninstall")]["generation_eligibility"] == "deferred-destructive"
    assert commands[("root", "uninstall")]["refusal_generation_eligibility"] == "eligible-refusal-only"
    assert commands[("root", "upgrade")]["generation_eligibility"] == "eligible-dry-run-refusal"
    assert commands[("root", "uninstall")]["effects"]["destructive_potential"] is True
    assert commands[("root", "install")]["capability_maturity"]["dry_run_plan"] == "proved"
    assert commands[("root", "install")]["capability_maturity"]["apply_mutation"] == "deferred"
    assert commands[("root", "uninstall")]["capability_maturity"]["destructive_refusal"] == "proved"
    assert "uninstall.lifecycle.destructive-refusal.process" in commands[("root", "uninstall")]["conformance_refs"]
    assert "upgrade.lifecycle.strict-preflight-refusal.process" in commands[("root", "upgrade")]["conformance_refs"]
    assert commands[("root", "upgrade")]["capability_maturity"]["strict_preflight_refusal"] == "proved"
    assert commands[("root", "upgrade")]["mutation_promotion_blockers"]
    assert commands[("planning-package", "status")]["generation_eligibility"] == "eligible-read-only"
    assert commands[("memory-package", "status")]["generation_eligibility"] == "eligible-read-only"
    assert commands[("memory-package", "status")]["capability_maturity"]["verify"] == "proved"
    assert any("strict preflight" in fixture for fixture in manifest["conformance_fixture_plan"])
    assert any("Dry-run lifecycle conformance" in decision for decision in manifest["dry_run_conformance_decision"])


def test_contract_tooling_check_derives_validated_consumption_from_policy() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    text = script_path.read_text(encoding="utf-8")

    assert "expected_validated_contracts" not in text
    assert "_validate_python_contract_consumption_policy" in text
    assert "validated_loader_calls" in text


def test_generated_command_adapter_module_is_current() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate" / "generate_command_adapters.py"
    spec = importlib.util.spec_from_file_location("generate_command_adapters", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main(["--check"]) == 0


def test_generated_command_package_files_are_current() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate" / "generate_command_packages.py"
    spec = importlib.util.spec_from_file_location("generate_command_packages", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main(["--check"]) == 0


def test_generated_command_package_check_surface_is_current() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_generated_command_packages.py"
    spec = importlib.util.spec_from_file_location("check_generated_command_packages", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main([]) == 0


def test_generated_command_package_adapter_conformance_check_passes() -> None:
    if os.environ.get("PYTEST_XDIST_WORKER"):
        pytest.skip("run generated adapter conformance as an explicit proof command outside the broad xdist suite")
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_generated_command_packages.py"
    spec = importlib.util.spec_from_file_location("check_generated_command_packages", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main(["--conformance"]) == 0


def test_generated_command_package_docker_flags_compose(monkeypatch) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_generated_command_packages.py"
    spec = importlib.util.spec_from_file_location("check_generated_command_packages", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calls: list[tuple[str, str, str]] = []

    def fake_run(command: list[str]) -> int:
        return 0

    def fake_run_docker(tag: str, *, dockerfile: str, proof_label: str, require_docker: bool) -> int:
        calls.append((tag, dockerfile, proof_label))
        assert require_docker is True
        return 0

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "_run_docker", fake_run_docker)

    assert module.main(["--python-docker-conformance", "--docker", "--docker-conformance", "--require-docker"]) == 0
    assert calls == [
        (
            "agentic-workspace-generated-python-cli-test-conformance",
            "generated/python/Dockerfile.conformance",
            "generated Python package Docker conformance proof",
        ),
        (
            "agentic-workspace-generated-typescript-cli-test",
            "generated/typescript/Dockerfile",
            "generated TypeScript package Docker proof",
        ),
        (
            "agentic-workspace-generated-typescript-cli-test-conformance",
            "generated/typescript/Dockerfile.conformance",
            "generated TypeScript package Docker conformance proof",
        ),
    ]


def test_generated_command_package_docker_skip_message_uses_proof_label(monkeypatch, capsys) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_generated_command_packages.py"
    spec = importlib.util.spec_from_file_location("check_generated_command_packages", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)

    status = module._run_docker(
        "proof-image",
        dockerfile="generated/python/Dockerfile.conformance",
        proof_label="generated Python package Docker conformance proof",
        require_docker=False,
    )

    assert status == 0
    output = capsys.readouterr().out
    assert "classification=proof-environment/setup-failure" in output
    assert "proof_surface=generated Python package Docker conformance proof" in output
    assert "phase=docker-cli" in output
    assert "stderr_tail='docker is not available'" in output


def test_generated_command_package_docker_conformance_surface_exists() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    python_dockerfile = repo_root / "generated" / "python" / "Dockerfile.conformance"
    python_text = python_dockerfile.read_text(encoding="utf-8")
    dockerfile = repo_root / "generated" / "typescript" / "Dockerfile.conformance"
    text = dockerfile.read_text(encoding="utf-8")

    assert "scripts/check/check_generated_command_packages.py" in python_text
    assert "--python-conformance" in python_text
    assert "COPY src ./src" in python_text
    assert "COPY generated ./generated" in python_text
    assert "scripts/check/check_generated_command_packages.py" in text
    assert "--conformance" in text
    assert "--require-node" in text
    assert "COPY src ./src" in text
    assert "COPY generated ./generated" in text


def test_command_generation_schema_boundary_is_checked() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._validate_command_generation_schema_boundary() == []
    workspace_schema = (
        Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "contracts" / "schemas" / "command_package_ir.schema.json"
    )
    package_schema = Path(__file__).resolve().parents[1] / "packages" / "command-generation" / "schemas" / "command_package_ir.schema.json"
    assert workspace_schema.read_text(encoding="utf-8") == package_schema.read_text(encoding="utf-8")


def test_command_generation_loader_uses_explicit_ir_and_schema_paths() -> None:
    from command_generation import load_command_package_ir

    repo_root = Path(__file__).resolve().parents[1]
    ir_path = repo_root / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json"
    schema_path = repo_root / "packages" / "command-generation" / "schemas" / "command_package_ir.schema.json"

    manifest = load_command_package_ir(ir_path, schema_path)

    assert manifest["schema_version"] == "agentic-workspace/command-package-ir/v1"
    assert {package["program"] for package in manifest["packages"]} >= {
        "agentic-workspace",
        "agentic-planning",
        "agentic-memory",
    }


def test_operation_command_parity_uses_package_program_namespace() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    root_commands = module._known_command_names_for_program("agentic-workspace")
    memory_commands = module._known_command_names_for_program("agentic-memory")

    assert "route-report" not in root_commands
    assert {"route-report", "promotion-report", "list-files", "list-skills"}.issubset(memory_commands)
    assert module._validate_operation_registry(module.operation_contracts_manifest()) == []


def test_operation_ir_has_complete_portable_memory_list_files_command() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    primitive_errors = module._validate_operation_primitives(module.operation_primitives_manifest())
    ir_errors = module._validate_operation_ir_plans()
    primitive_registry = module.operation_primitives_manifest()
    operation = contract_tooling.operation_manifest("operations/memory.list-files.report.json")
    used = [step["uses"] for step in operation["ir_plan"]["steps"]]
    support_matrix = {entry["target"]: entry for entry in primitive_registry["primitive_extension_boundary"]["target_support_matrix"]}

    assert primitive_errors == []
    assert ir_errors == []
    assert primitive_registry["module_ir_ownership"]["namespaces"]
    assert primitive_registry["primitive_extension_boundary"]["target_support_rule"]
    assert support_matrix["python"]["status"] == "implemented"
    assert "path.target_root.resolve" in support_matrix["python"]["implemented_shared_primitives"]
    assert support_matrix["typescript"]["status"] == "unsupported-reported"
    assert "runtime handoff" in support_matrix["typescript"]["unsupported_behavior"]
    assert operation["ir_plan"]["status"] == "complete"
    assert used == [
        "path.target_root.resolve",
        "filesystem.glob",
        "payload.assemble",
        "output.emit",
    ]
    assert operation["migration_status"] == "runtime-consumed"


def test_operation_ir_requires_declared_module_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    registry = copy.deepcopy(module.operation_primitives_manifest())
    registry["module_ir_ownership"]["namespaces"] = [
        {
            "id": "planning",
            "operation_id_prefix": "planning.",
            "contract_owner": "packages/planning",
            "current_contract_root": "src/agentic_workspace/contracts/operations",
            "future_contract_root": "packages/planning/contracts",
        }
    ]
    monkeypatch.setattr(module, "operation_primitives_manifest", lambda: registry)

    errors = module._validate_operation_ir_plans()

    assert any("memory.list-files.report" in error and "module_ir_ownership" in error for error in errors)


def test_module_operation_contracts_are_not_owned_by_root_operations() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    root_operations = Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "contracts" / "operations"

    assert module._validate_module_operation_contract_locations() == []
    assert not list(root_operations.glob("planning.*.json"))
    assert not list(root_operations.glob("memory.*.json"))


def test_operation_primitives_require_target_support_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    registry = copy.deepcopy(module.operation_primitives_manifest())
    registry["primitive_extension_boundary"]["target_support_matrix"] = [
        {
            "target": "typescript",
            "status": "unsupported-reported",
            "implemented_shared_primitives": [],
            "domain_runtime_extension_behavior": "reported through runtime handoff",
            "conformance_ref": "scripts/check/check_generated_command_packages.py --docker-conformance --require-docker",
            "unsupported_behavior": "primitive execution is not implemented",
        }
    ]

    errors = module._validate_operation_primitives(registry)

    assert any("missing target python" in error for error in errors)
    assert any("schema-backed primitives missing implemented target support" in error for error in errors)


def test_operation_primitives_classify_operation_step_tiers(monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    registry = copy.deepcopy(module.operation_primitives_manifest())
    by_id = {primitive["id"]: primitive for primitive in registry["primitives"]}

    assert module._validate_operation_primitives(registry) == []
    assert by_id["filesystem.glob"]["taxonomy_tier"] == "tier-1-portable-codegen"
    assert by_id["workspace.root.resolve"]["taxonomy_tier"] == "tier-2-package-domain"
    assert by_id["python.function.call"]["portability"] == "external-adapter"
    assert by_id["python.function.call"]["taxonomy_tier"] == "tier-2-package-domain"
    assert by_id["workspace.root.resolve"]["tier_owner"]
    assert by_id["workspace.root.resolve"]["generic_behavior_audit"]

    by_id["python.function.call"]["taxonomy_tier"] = "tier-1-portable-codegen"
    monkeypatch.setattr(module, "operation_primitives_manifest", lambda: registry)

    errors = module._validate_operation_primitives(registry)

    assert any("non-portable primitive python.function.call must not be classified tier-1-portable-codegen" in error for error in errors)

    by_id["python.function.call"]["taxonomy_tier"] = "tier-2-package-domain"
    by_id["workspace.root.resolve"].pop("generic_behavior_audit")
    errors = module._validate_operation_primitives(registry)

    assert any("tier-2 primitive workspace.root.resolve missing audit field" in error for error in errors)


def test_python_operation_execution_inventory_tracks_direct_generated_memory_commands() -> None:
    inventory = contract_tooling.load_contract_json("python_operation_execution_inventory.json")
    entries = {entry["operation_id"]: entry for entry in inventory["entries"]}

    list_files = entries["memory.list-files.report"]

    assert list_files["status"] == "portable-codegen-primitive-executed"
    assert list_files["primitive_executor"] == "generated/memory/python/commands/memory_list_files_report.py"
    assert entries["memory.list-skills.report"]["status"] == "portable-codegen-primitive-executed"
    assert entries["memory.list-skills.report"]["primitive_executor"] == "generated/memory/python/commands/memory_list_skills_report.py"
    assert entries["memory.report.report"]["status"] == "domain-runtime-primitive-via-ir"
    assert "compatibility-runtime-handler" not in {entry["status"] for entry in entries.values()}
    assert "accepted-hand-owned-runtime-primitive" in {entry["status"] for entry in entries.values()}
    audited_runtime = [
        entry
        for entry in entries.values()
        if entry["status"] in {"domain-runtime-primitive-via-ir", "accepted-hand-owned-runtime-primitive"}
    ]
    assert all(entry.get("runtime_boundary_class") for entry in audited_runtime)
    assert all(entry.get("runtime_boundary_reason") for entry in audited_runtime)
    assert all(entry.get("what_would_make_portable_later") for entry in audited_runtime)
    assert all(entry.get("generic_behavior_audit") for entry in audited_runtime)
    assert "generic-deterministic-runtime-debt" not in {entry["runtime_boundary_class"] for entry in audited_runtime}
    generated_operations = {
        operation_id
        for package in contract_tooling.command_package_ir_manifest()["packages"]
        for command in package["commands"]
        for operation_id in _command_operation_ids(command)
    }
    assert set(entries) == generated_operations


def test_workspace_command_generation_integration_owns_repo_paths() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "generate" / "workspace_command_generation.py"
    spec = importlib.util.spec_from_file_location("workspace_command_generation", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.SOURCE_PATH == "src/agentic_workspace/contracts/command_package_ir.json"
    assert module.SCHEMA_PATH == "packages/command-generation/schemas/command_package_ir.schema.json"
    manifest = module.load_workspace_command_package_ir()
    assert manifest["schema_version"] == "agentic-workspace/command-package-ir/v1"


def test_generate_command_packages_wrapper_uses_workspace_consumer_integration() -> None:
    wrapper = Path(__file__).resolve().parents[1] / "scripts" / "generate" / "generate_command_packages.py"
    text = wrapper.read_text(encoding="utf-8")

    assert "workspace_command_generation" in text
    assert "load_command_package_ir" not in text
    assert "agentic_workspace.contract_tooling" not in text


def test_command_package_generator_normalizes_line_endings() -> None:
    generator = Path(__file__).resolve().parents[1] / "packages" / "command-generation" / "src" / "command_generation" / "generator.py"
    wrapper = Path(__file__).resolve().parents[1] / "scripts" / "generate" / "generate_command_packages.py"

    assert 'newline="\\n"' in generator.read_text(encoding="utf-8")
    assert "line-ending drift" in wrapper.read_text(encoding="utf-8")


def test_command_package_generator_renders_planning_runtime_module_from_binding() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    generator_path = repo_root / "packages" / "command-generation" / "src" / "command_generation" / "generator.py"
    spec = importlib.util.spec_from_file_location("command_generation_generator_render_outputs", generator_path)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = generator
    spec.loader.exec_module(generator)

    outputs = generator.render_outputs(
        contract_tooling.command_package_ir_manifest(),
        repo_root=repo_root,
        source_path="src/agentic_workspace/contracts/command_package_ir.json",
        regenerate_command="uv run python scripts/generate/generate_command_packages.py",
    )
    rendered = {str(output.path.relative_to(repo_root)).replace("\\", "/"): output.content for output in outputs}

    assert "generated/planning/python/cli.py" in rendered
    assert "generated/planning/python/commands/planning_status_report.py" in rendered
    planning_command = rendered["generated/planning/python/commands/planning_status_report.py"]
    assert "Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json" in planning_command
    assert "run_operation_ir(generated_operation_contract('planning.status.report'), args)" in planning_command
    assert "generated/workspace/python/cli.py" in rendered
    assert "generated/workspace/python/commands/status_report.py" in rendered
    workspace_command = rendered["generated/workspace/python/commands/status_report.py"]
    assert "Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json" in workspace_command
    assert "from ..primitives.workspace_runtime import" in workspace_command
    assert "return _run_" in workspace_command
    assert "generated/workspace/python/primitives/workspace_runtime.py" in rendered
    workspace_runtime = rendered["generated/workspace/python/primitives/workspace_runtime.py"]
    assert "from agentic_workspace.workspace_runtime_primitives import" in workspace_runtime
    assert "generated/memory/python/cli.py" in rendered
    assert "generated/memory/python/commands/memory_status_report.py" in rendered
    memory_command = rendered["generated/memory/python/commands/memory_status_report.py"]
    assert "Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json" in memory_command
    assert "run_operation_ir(generated_operation_contract('memory.status.report'), args)" in memory_command


def test_generated_python_module_collects_nested_operation_refs(tmp_path: Path) -> None:
    generator_path = Path(__file__).resolve().parents[1] / "packages" / "command-generation" / "src" / "command_generation" / "generator.py"
    spec = importlib.util.spec_from_file_location("command_generation_generator", generator_path)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = generator
    spec.loader.exec_module(generator)
    package = {
        "program": "example",
        "summary": "Example generated package",
        "commands": [
            {
                "adapter_id": "prompt.lifecycle.cli",
                "operation_ref": {"id": "prompt.init", "path": "operations/prompt.init.json"},
                "status": "generated",
                "interface": {
                    "name": "prompt",
                    "help": "Prompt lifecycle",
                    "subcommand_dest": "prompt_command",
                    "subcommands": [
                        {
                            "name": "upgrade",
                            "help": "Upgrade prompt",
                            "operation_ref": {"id": "prompt.upgrade", "path": "operations/prompt.upgrade.json"},
                        },
                        {
                            "name": "uninstall",
                            "help": "Uninstall prompt",
                            "operation_ref": {"id": "prompt.uninstall", "path": "operations/prompt.uninstall.json"},
                        },
                    ],
                },
            },
        ],
    }
    target = {"maturity_level_ref": "weak-agent-safe-adapter", "kind": "python"}
    package_dir = tmp_path / "nested_generated_cli_package"
    package_dir.mkdir()
    (package_dir / "command_package.json").write_text(json.dumps(package), encoding="utf-8")
    (package_dir / "adapter_commands.json").write_text(
        json.dumps(
            [
                {
                    "adapter_id": "prompt.lifecycle.cli",
                    "operation_id": "prompt.init",
                    "operation_path": "operations/prompt.init.json",
                    "interface": package["commands"][0]["interface"],
                }
            ]
        ),
        encoding="utf-8",
    )
    module_text = generator._python_runtime_adapter_module(
        package,
        target,
        {
            "weak-agent-safe-adapter": {
                "weak_agent_routing": "allowed-read-only",
            },
        },
        source_path="src/agentic_workspace/contracts/command_package_ir.json",
        regenerate_command="uv run python scripts/generate/generate_command_packages.py",
    )
    (package_dir / "__init__.py").write_text(module_text, encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        generated = __import__("nested_generated_cli_package")
    finally:
        sys.path.remove(str(tmp_path))

    assert generated.generated_operation_ids() == ("prompt.init", "prompt.uninstall", "prompt.upgrade")
    parser = generated.build_generated_parser()
    assert parser.parse_args(["prompt", "upgrade"])._generated_operation_id == "prompt.upgrade"
    assert parser.parse_args(["prompt", "uninstall"])._generated_operation_id == "prompt.uninstall"


def test_generic_command_generation_package_has_no_workspace_imports() -> None:
    package_root = Path(__file__).resolve().parents[1] / "packages" / "command-generation" / "src" / "command_generation"
    for path in package_root.rglob("*.py"):
        if path.name.endswith(("_generated_cli_package.py", "_operation_ir_executor.py", "_runtime_cli.py")):
            continue
        text = path.read_text(encoding="utf-8")
        assert "from agentic_workspace" not in text
        assert "import agentic_workspace" not in text


def test_command_generation_readme_defines_lift_out_criteria() -> None:
    readme = Path(__file__).resolve().parents[1] / "packages" / "command-generation" / "README.md"
    text = readme.read_text(encoding="utf-8")

    assert "## Lift-Out Readiness" in text
    assert "Technical criteria:" in text
    assert "Ownership criteria:" in text
    assert "Migration criteria:" in text
    assert "Stability criteria:" in text
    for required in (
        "no imports from `agentic_workspace`",
        "Agentic Workspace command truth remains in workspace-owned contracts",
        "Runtime primitives",
        "Replace local path injection with normal package imports",
        "schema versioning rules",
    ):
        assert required in text


def test_generated_python_command_package_metadata_is_current() -> None:
    generated = load_generated_command_package_for_entrypoint("agentic-workspace")
    GENERATED_COMMAND_PACKAGE = generated.GENERATED_COMMAND_PACKAGE
    generated_command_names = generated.generated_command_names
    generated_maturity = generated.generated_maturity
    generated_operation_ids = generated.generated_operation_ids
    generated_weak_agent_routing = generated.generated_weak_agent_routing
    supports_generated_command = generated.supports_generated_command

    assert GENERATED_COMMAND_PACKAGE["program"] == "agentic-workspace"
    assert {command["adapter_id"] for command in GENERATED_COMMAND_PACKAGE["commands"]} == {
        "defaults.report.cli",
        "config.report.cli",
        "modules.report.cli",
        "start.context.cli",
        "summary.report.cli",
        "implement.context.cli",
        "preflight.report.cli",
        "proof.report.cli",
        "ownership.report.cli",
        "system-intent.sync.cli",
        "delegation-outcome.append.cli",
        "skills.report.cli",
        "planning.front-door.cli",
        "memory.front-door.cli",
        "external-intent.refresh-github.cli",
        "install.lifecycle.cli",
        "init.lifecycle.cli",
        "prompt.lifecycle.cli",
        "upgrade.lifecycle.cli",
        "uninstall.lifecycle.cli",
        "report.combined.cli",
        "reconcile.report.cli",
        "setup.guidance.cli",
        "status.report.cli",
        "doctor.report.cli",
    }
    target_kinds = {target["kind"] for target in GENERATED_COMMAND_PACKAGE["targets"]}
    assert {"python", "typescript", "bash", "powershell"} <= target_kinds
    python_target = next(target for target in GENERATED_COMMAND_PACKAGE["targets"] if target["kind"] == "python")
    assert python_target["generated_root"] == "generated/workspace/python"
    assert python_target["maturity_level_ref"] == "mutation-capable-adapter"
    assert python_target["generation_status"] == "mutation-capable-adapter"
    assert generated_maturity() == {
        "id": "mutation-capable-adapter",
        "runnable": True,
        "weak_agent_routing": "allowed-mutation-with-review",
    }
    assert generated_weak_agent_routing() == "allowed-mutation-with-review"
    assert generated_command_names() == (
        "config",
        "defaults",
        "doctor",
        "external-intent",
        "implement",
        "init",
        "install",
        "memory",
        "modules",
        "note-delegation-outcome",
        "ownership",
        "planning",
        "preflight",
        "prompt",
        "proof",
        "reconcile",
        "report",
        "setup",
        "skills",
        "start",
        "status",
        "summary",
        "system-intent",
        "uninstall",
        "upgrade",
    )
    assert generated_operation_ids() == (
        "config.report",
        "defaults.report",
        "delegation-outcome.append",
        "doctor.report",
        "external-intent.refresh-github",
        "implement.context",
        "init.lifecycle",
        "install.lifecycle",
        "memory.front-door",
        "modules.report",
        "ownership.report",
        "planning.front-door",
        "preflight.report",
        "prompt.init",
        "prompt.uninstall",
        "prompt.upgrade",
        "proof.report",
        "reconcile.report",
        "report.combined",
        "setup.guidance",
        "skills.report",
        "start.context",
        "status.report",
        "summary.report",
        "system-intent.sync",
        "uninstall.lifecycle",
        "upgrade.lifecycle",
    )
    assert supports_generated_command(["defaults", "--format", "json"]) is True
    assert supports_generated_command(["config", "--format", "json"]) is True
    assert supports_generated_command(["modules", "--format", "json"]) is True
    assert supports_generated_command(["start", "--format", "json"]) is True
    assert supports_generated_command(["summary", "--format", "json"]) is True
    assert supports_generated_command(["implement", "--format", "json"]) is True
    assert supports_generated_command(["init", "--format", "json"]) is True
    assert supports_generated_command(["install", "--format", "json"]) is True
    assert supports_generated_command(["preflight", "--format", "json"]) is True
    assert supports_generated_command(["proof", "--format", "json"]) is True
    assert supports_generated_command(["ownership", "--format", "json"]) is True
    assert supports_generated_command(["system-intent", "--format", "json"]) is True
    assert supports_generated_command(["note-delegation-outcome", "--help"]) is True
    assert supports_generated_command(["skills", "--format", "json"]) is True
    assert supports_generated_command(["planning", "--format", "json"]) is True
    assert supports_generated_command(["memory", "--format", "json"]) is True
    assert supports_generated_command(["external-intent", "refresh-github", "--help"]) is True
    assert supports_generated_command(["prompt", "init", "--help"]) is True
    assert supports_generated_command(["report", "--format", "json"]) is True
    assert supports_generated_command(["reconcile", "--format", "json"]) is True
    assert supports_generated_command(["setup", "--format", "json"]) is True
    assert supports_generated_command(["status", "--format", "json"]) is True
    assert supports_generated_command(["doctor", "--format", "json"]) is True
    assert supports_generated_command(["uninstall", "--format", "json"]) is True
    assert supports_generated_command(["upgrade", "--format", "json"]) is True


def test_generated_python_command_package_parses_and_dispatches_runtime_operations() -> None:
    generated = load_generated_command_package_for_entrypoint("agentic-workspace")
    build_generated_parser = generated.build_generated_parser
    run_generated_command = generated.run_generated_command

    calls: list[tuple[str, str | None, str, str | None]] = []

    def runtime_handler(operation_id: str, args: argparse.Namespace) -> int:
        calls.append((operation_id, getattr(args, "target", None), args.format, getattr(args, "section", None)))
        return 0

    help_text = build_generated_parser().format_help()
    assert "Weak-agent routing: allowed-mutation-with-review" in help_text
    assert "Recovery: use one of the supported generated commands" in help_text
    assert run_generated_command(["defaults", "--section", "startup", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["config", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["modules", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["start", "--target", ".", "--changed", "README.md", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["summary", "--target", ".", "--verbose", "--format", "json"], runtime_handler) == 0
    assert (
        run_generated_command(
            ["implement", "--target", ".", "--changed", "README.md", "--task", "generated-adapter-proof", "--format", "json"],
            runtime_handler,
        )
        == 0
    )
    assert (
        run_generated_command(["install", "--target", ".", "--modules", "planning", "--dry-run", "--format", "json"], runtime_handler) == 0
    )
    assert run_generated_command(["init", "--target", ".", "--modules", "planning", "--dry-run", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["preflight", "--target", ".", "--active-only", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["proof", "--target", ".", "--changed", "README.md", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["ownership", "--target", ".", "--concern", "startup", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["skills", "--target", ".", "--task", "proof", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["planning", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["planning", "--target", ".", "--format", "json", "report"], runtime_handler) == 0
    assert run_generated_command(["memory", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["memory", "--target", ".", "--format", "json", "report"], runtime_handler) == 0
    assert run_generated_command(["report", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["reconcile", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["setup", "--target", ".", "--modules", "planning", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["status", "--target", ".", "--modules", "planning", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["doctor", "--target", ".", "--modules", "planning", "--format", "json"], runtime_handler) == 0
    assert (
        run_generated_command(["uninstall", "--target", ".", "--modules", "planning", "--dry-run", "--format", "json"], runtime_handler)
        == 0
    )
    assert (
        run_generated_command(["upgrade", "--target", ".", "--modules", "planning", "--dry-run", "--format", "json"], runtime_handler) == 0
    )
    assert calls == [
        ("defaults.report", None, "json", "startup"),
        ("config.report", ".", "json", None),
        ("modules.report", ".", "json", None),
        ("start.context", ".", "json", None),
        ("summary.report", ".", "json", None),
        ("implement.context", ".", "json", None),
        ("install.lifecycle", ".", "json", None),
        ("init.lifecycle", ".", "json", None),
        ("preflight.report", ".", "json", None),
        ("proof.report", ".", "json", None),
        ("ownership.report", ".", "json", None),
        ("skills.report", ".", "json", None),
        ("planning.front-door", ".", "json", None),
        ("planning.front-door", ".", "json", None),
        ("memory.front-door", ".", "json", None),
        ("memory.front-door", ".", "json", None),
        ("report.combined", ".", "json", None),
        ("reconcile.report", ".", "json", None),
        ("setup.guidance", ".", "json", None),
        ("status.report", ".", "json", None),
        ("doctor.report", ".", "json", None),
        ("uninstall.lifecycle", ".", "json", None),
        ("upgrade.lifecycle", ".", "json", None),
    ]


def test_generated_python_command_package_parses_doctor_select() -> None:
    run_generated_command = load_generated_command_package_for_entrypoint("agentic-workspace").run_generated_command

    calls: list[tuple[str, str | None]] = []

    def runtime_handler(operation_id: str, args: argparse.Namespace) -> int:
        calls.append((operation_id, getattr(args, "select", None)))
        return 0

    assert run_generated_command(["doctor", "--target", ".", "--format", "json", "--select", "health,next_action"], runtime_handler) == 0
    assert calls == [("doctor.report", "health,next_action")]


def test_package_generated_python_command_packages_parse_status_runtime_operations() -> None:
    memory_generated = load_generated_command_package_for_entrypoint("agentic-memory")
    planning_generated = load_generated_command_package_for_entrypoint("agentic-planning")
    memory_generated_maturity = memory_generated.generated_maturity
    run_memory_generated_command = memory_generated.run_generated_command
    planning_generated_maturity = planning_generated.generated_maturity
    run_planning_generated_command = planning_generated.run_generated_command

    calls: list[tuple[str, str | None, str]] = []

    def runtime_handler(operation_id: str, args: argparse.Namespace) -> int:
        calls.append((operation_id, getattr(args, "target", None), args.format))
        return 0

    assert run_planning_generated_command(["status", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_planning_generated_command(["doctor", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_planning_generated_command(["summary", "--target", ".", "--verbose", "--format", "json"], runtime_handler) == 0
    assert run_planning_generated_command(["report", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_planning_generated_command(["reconcile", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_memory_generated_command(["status", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_memory_generated_command(["doctor", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_memory_generated_command(["report", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert planning_generated_maturity()["weak_agent_routing"] == "allowed-mutation-with-review"
    assert memory_generated_maturity()["weak_agent_routing"] == "allowed-mutation-with-review"
    assert calls == [
        ("planning.status.report", ".", "json"),
        ("planning.doctor.report", ".", "json"),
        ("planning.summary.report", ".", "json"),
        ("planning.report.report", ".", "json"),
        ("planning.reconcile.report", ".", "json"),
        ("memory.status.report", ".", "json"),
        ("memory.doctor.report", ".", "json"),
        ("memory.report.report", ".", "json"),
    ]


def test_generated_typescript_command_package_fixture_is_current() -> None:
    package_root = Path(__file__).resolve().parents[1] / "generated" / "typescript" / "workspace-cli"
    package_json = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
    source_text = (package_root / "src" / "commandPackage.ts").read_text(encoding="utf-8")
    cli_text = (package_root / "src" / "cli.mjs").read_text(encoding="utf-8")
    test_text = (package_root / "test" / "command-package.test.mjs").read_text(encoding="utf-8")

    assert package_json["name"] == "@agentic-workspace/workspace-cli"
    assert package_json["bin"] == {"agentic-workspace": "./src/cli.mjs"}
    assert package_json["agenticWorkspace"]["generated"] is True
    assert package_json["agenticWorkspace"]["fixtureOnly"] is False
    assert package_json["agenticWorkspace"]["generationStatus"] == "mutation-capable-adapter"
    assert package_json["agenticWorkspace"]["maturity"]["id"] == "mutation-capable-adapter"
    assert package_json["agenticWorkspace"]["maturity"]["weak_agent_routing"] == "allowed-mutation-with-review"
    assert package_json["agenticWorkspace"]["maturity"]["runnable"] is True
    assert package_json["agenticWorkspace"]["maturity"]["promotion_requires"]
    assert (
        package_json["agenticWorkspace"]["runtimeBinding"]["selected_model"]
        == "generated parser/help with process handoff to canonical Python CLI"
    )
    assert package_json["agenticWorkspace"]["declaredEntrypoints"] == ["agentic-workspace"]
    assert "defaults.report.cli" in source_text
    assert "config.report.cli" in source_text
    assert "modules.report.cli" in source_text
    assert "start.context.cli" in source_text
    assert "summary.report.cli" in source_text
    assert "implement.context.cli" in source_text
    assert "preflight.report.cli" in source_text
    assert "proof.report.cli" in source_text
    assert "ownership.report.cli" in source_text
    assert "skills.report.cli" in source_text
    assert "report.combined.cli" in source_text
    assert "reconcile.report.cli" in source_text
    assert "setup.guidance.cli" in source_text
    assert "status.report.cli" in source_text
    assert "doctor.report.cli" in source_text
    assert "DO NOT EDIT DIRECTLY" in source_text
    assert "maxBuffer: 16 * 1024 * 1024" in cli_text
    assert "function splitRuntimeCommand(commandLine)" in cli_text
    assert "spawnSync(runtimeExecutable, [...runtimeArgs, ...argv]" in cli_text
    assert "shell: true" not in cli_text
    assert "writeSync(1, result.stdout)" in cli_text
    assert "writeSync(2, result.stderr)" in cli_text
    assert "Weak-agent routing: allowed-mutation-with-review" in cli_text
    assert "Unsupported generated command" in cli_text
    assert "Adapter runtime handoff failed" in cli_text
    assert "generated package metadata exposes expected commands" in test_text
    assert "generated runnable adapter delegates supported command to runtime process" in test_text
    assert "generated runnable adapter exposes routing status and recovery guidance" in test_text
    assert "generated runnable adapter maps runtime handoff failure with recovery guidance" in test_text


def test_generated_typescript_package_adapters_are_runnable() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    packages = {
        "planning-cli": (
            "@agentic-workspace/planning-cli",
            "agentic-planning",
            "agentic-planning",
            "mutation-capable-adapter",
            "allowed-mutation-with-review",
        ),
        "memory-cli": (
            "@agentic-workspace/memory-cli",
            "agentic-memory",
            "agentic-memory",
            "mutation-capable-adapter",
            "allowed-mutation-with-review",
        ),
    }
    for package, (package_name, entrypoint, runtime_command, maturity, weak_agent_routing) in packages.items():
        package_root = repo_root / "generated" / "typescript" / package
        package_json = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
        cli_text = (package_root / "src" / "cli.mjs").read_text(encoding="utf-8")
        test_text = (package_root / "test" / "command-package.test.mjs").read_text(encoding="utf-8")

        assert package_json["name"] == package_name
        assert package_json["bin"] == {entrypoint: "./src/cli.mjs"}
        metadata = package_json["agenticWorkspace"]
        assert metadata["fixtureOnly"] is False
        assert metadata["generationStatus"] == maturity
        assert runtime_command in metadata["effectiveRuntimeCommand"]
        assert metadata["maturity"]["id"] == maturity
        assert metadata["maturity"]["runnable"] is True
        assert metadata["maturity"]["weak_agent_routing"] == weak_agent_routing
        assert metadata["maturity"]["promotion_requires"]
        assert runtime_command in cli_text
        assert "function splitRuntimeCommand(commandLine)" in cli_text
        assert "spawnSync(runtimeExecutable, [...runtimeArgs, ...argv]" in cli_text
        assert "shell: true" not in cli_text
        assert f"Weak-agent routing: {weak_agent_routing}" in cli_text
        assert "generated runnable adapter delegates supported command to runtime process" in test_text
        assert "generated runnable adapter preserves spaced argv values during runtime handoff" in test_text


def test_generated_command_adapter_metadata_routes_direct_edits_to_authoritative_sources() -> None:
    generated_path = Path(__file__).resolve().parents[1] / "generated" / "workspace" / "python" / "generated_command_adapters.json"
    generated_text = generated_path.read_text(encoding="utf-8")
    generated_payload = json.loads(generated_text)

    assert generated_payload["source"] == "src/agentic_workspace/contracts/command_adapter_generation.json"
    assert generated_payload["program"] == "agentic-workspace"
    assert generated_payload["regenerate_with"] == "uv run python scripts/generate/generate_command_adapters.py"
    assert "adapters_by_command" in generated_payload


def test_python_runtime_boundary_declares_root_cli_authority_audit() -> None:
    manifest = contract_tooling.python_runtime_boundary_manifest()
    audit = manifest["root_cli_authority_audit"]

    assert audit["command"] == "agentic-workspace defaults --section root_cli_authority --format json"
    classes = {item["id"]: item for item in audit["responsibility_classes"]}
    assert classes["runtime-primitives"]["authority_class"] == "allowed-root-runtime"
    assert classes["remaining-interface-authority"]["authority_class"] == "remaining-interface-authority"
    boundaries = {item["id"]: item for item in manifest["boundaries"]}
    assert boundaries["report-router-rendering"]["owner_modules"] == [
        "agentic_workspace.reporting_support",
        "generated/workspace/python/cli.py",
    ]
    assert boundaries["report-router-rendering"]["classification"] == "operation-contract-covered"
    statuses = {item["status"] for item in audit["current_audit"]}
    assert "legitimate-runtime-ownership" in statuses
    assert "extract-or-guard-candidate" in statuses
    candidates = audit["next_extraction_or_guard_candidates"]
    assert {candidate["candidate_type"] for candidate in candidates} >= {
        "extract-interface-authority",
        "add-guard-check",
    }
    assert not any(candidate.get("tracking_issue") == "#410" for candidate in candidates)
    assert any(
        candidate["provenance_issue"] == "#410" and candidate["tracking_role"] == "historical-provenance" for candidate in candidates
    )
    assert all(candidate["tracking_role"] != "live-owner" or candidate["tracking_status"] != "closed" for candidate in candidates)
    assert audit["direct_cli_edit_routing"]["route_to_contract_when"]
    assert audit["direct_cli_edit_routing"]["review_requires"]


def test_python_runtime_projection_inventory_tracks_generated_output_debt() -> None:
    manifest = contract_tooling.python_runtime_projection_inventory_manifest()
    entries = {entry["path"]: entry for entry in manifest["entries"]}

    assert set(entries) == {
        "generated/workspace/python/cli.py",
        "generated/workspace/python/primitives/operation_executor.py",
        "generated/planning/python/cli.py",
        "generated/planning/python/primitives/operation_executor.py",
        "generated/memory/python/cli.py",
        "generated/memory/python/primitives/operation_executor.py",
    }
    assert entries["generated/workspace/python/primitives/operation_executor.py"]["provenance_status"] == "rendered-by-command-generation"
    assert entries["generated/workspace/python/primitives/operation_executor.py"]["blocking_full_completion"] is False
    assert entries["generated/planning/python/primitives/operation_executor.py"]["provenance_status"] == "rendered-by-command-generation"
    assert entries["generated/planning/python/primitives/operation_executor.py"]["blocking_full_completion"] is False
    assert entries["generated/memory/python/primitives/operation_executor.py"]["provenance_status"] == "rendered-by-command-generation"
    assert entries["generated/memory/python/primitives/operation_executor.py"]["blocking_full_completion"] is False
    rendered_entries = {
        "generated/workspace/python/cli.py",
        "generated/workspace/python/primitives/operation_executor.py",
        "generated/planning/python/cli.py",
        "generated/planning/python/primitives/operation_executor.py",
        "generated/memory/python/cli.py",
        "generated/memory/python/primitives/operation_executor.py",
    }
    transitional_entries = [entry for entry in entries.values() if entry["path"] not in rendered_entries]
    assert transitional_entries == []


def test_contract_tooling_check_enforces_root_cli_authority_audit() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._validate_python_runtime_boundary_authority(contract_tooling.python_runtime_boundary_manifest()) == []

    manifest = copy.deepcopy(contract_tooling.python_runtime_boundary_manifest())
    manifest["root_cli_authority_audit"]["next_extraction_or_guard_candidates"][0]["tracking_role"] = "live-owner"
    manifest["root_cli_authority_audit"]["next_extraction_or_guard_candidates"][0]["tracking_status"] = "closed"
    manifest["root_cli_authority_audit"]["next_extraction_or_guard_candidates"][0]["tracking_issue"] = "#410"
    assert any(
        "cannot use closed tracking as live ownership" in error for error in module._validate_python_runtime_boundary_authority(manifest)
    )

    manifest = copy.deepcopy(contract_tooling.python_runtime_boundary_manifest())
    manifest["root_cli_authority_audit"]["next_extraction_or_guard_candidates"][0]["tracking_issue"] = "#410"
    assert any(
        "must not use tracking_issue for historical provenance" in error
        for error in module._validate_python_runtime_boundary_authority(manifest)
    )


def test_contract_tooling_check_reports_generated_adapter_status() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    statuses, errors = module._generated_command_adapter_statuses()

    assert errors == []
    assert {status["program"] for status in statuses} == {
        "agentic-workspace",
        "agentic-planning",
        "agentic-memory",
    }
    assert all(status["status"] == "current" for status in statuses)
    assert all(status["direct_edit_detected"] is False for status in statuses)
    assert all(status["source_contract"] == "src/agentic_workspace/contracts/command_adapter_generation.json" for status in statuses)
    assert all(
        status["where_to_edit"]["command_interface"] == "src/agentic_workspace/contracts/command_adapter_generation.json"
        for status in statuses
    )
    assert all(status["where_to_edit"]["runtime_behavior"] == "hand-written operation/primitive implementation code" for status in statuses)
    commands_by_program = {status["program"]: status["command_surfaces"] for status in statuses}
    assert commands_by_program["agentic-workspace"] == [
        "config",
        "defaults",
        "note-delegation-outcome",
        "doctor",
        "external-intent",
        "implement",
        "init",
        "install",
        "memory",
        "modules",
        "ownership",
        "planning",
        "preflight",
        "prompt",
        "proof",
        "reconcile",
        "report",
        "setup",
        "skills",
        "start",
        "status",
        "summary",
        "system-intent",
        "uninstall",
        "upgrade",
    ]
    assert commands_by_program["agentic-planning"] == [
        "adopt",
        "archive-plan",
        "closeout",
        "close-item",
        "create-review",
        "delegation-decision",
        "doctor",
        "handoff",
        "init",
        "install",
        "list-files",
        "new-plan",
        "intake-artifact",
        "promote-to-plan",
        "prompt",
        "reconcile",
        "report",
        "status",
        "summary",
        "uninstall",
        "upgrade",
        "verify-payload",
    ]
    assert commands_by_program["agentic-memory"] == [
        "doctor",
        "install",
        "init",
        "adopt",
        "upgrade",
        "migrate-layout",
        "uninstall",
        "bootstrap-cleanup",
        "capture-note",
        "create-note",
        "current",
        "prompt",
        "list-files",
        "list-skills",
        "promotion-report",
        "report",
        "route-report",
        "route",
        "route-review",
        "search",
        "verify-payload",
        "sync-memory",
        "status",
    ]


def test_generated_adapter_contracts_match_live_cli_surfaces() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._validate_generated_adapter_live_cli_parity(contract_tooling.command_adapter_generation_manifest()) == []


def test_generated_adapter_live_cli_parity_defers_generated_command_options_to_package_ir(monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    memory_adapter = next(
        adapter for adapter in contract_tooling.command_adapter_generation_manifest()["adapters"] if adapter["id"] == "memory.status.cli"
    )

    def fake_operation_manifest(_path: str) -> dict[str, object]:
        return {
            "command_surface": {"program": "agentic-memory", "command": "status", "format_option": "format"},
            "inputs": [{"name": "format", "source": "cli-option", "required": False}],
        }

    monkeypatch.setattr(module, "operation_manifest", fake_operation_manifest)

    errors = module._validate_generated_adapter_live_cli_parity({"adapters": [memory_adapter]})

    assert errors == []


def test_validated_contract_loader_reports_contract_and_schema(monkeypatch, tmp_path: Path) -> None:
    contracts_root = tmp_path / "contracts"
    schemas_root = contracts_root / "schemas"
    schemas_root.mkdir(parents=True)
    (contracts_root / "sample.json").write_text(json.dumps({"kind": "wrong"}) + "\n", encoding="utf-8")
    (schemas_root / "sample.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {"kind": {"const": "right"}},
                "required": ["kind"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(contract_tooling, "contracts_root", lambda: contracts_root)
    contract_tooling.load_contract_json.cache_clear()
    contract_tooling.load_validated_contract_json.cache_clear()

    with pytest.raises(contract_tooling.ContractValidationError) as excinfo:
        contract_tooling.load_validated_contract_json("sample.json", "sample.schema.json")

    message = str(excinfo.value)
    assert "sample.json failed validation against schemas/sample.schema.json" in message
    assert "kind" in message
