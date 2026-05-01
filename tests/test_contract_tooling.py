from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace import contract_tooling


def test_contract_tooling_check_passes() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main([]) == 0


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

    assert migration["planning"]["program"] == "agentic-planning-bootstrap"
    assert migration["planning"]["status"] == "first-read-only-generated"
    assert adapters["planning.status.cli"]["command"]["program"] == migration["planning"]["program"]
    assert adapters["planning.status.cli"]["command"]["name"] == migration["planning"]["first_read_only_candidate"]
    assert migration["memory"]["program"] == "agentic-memory-bootstrap"
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
    assert runtime_binding["selected_model"] == "generated parser/help with process handoff to canonical Python CLI"
    assert "operation primitive implementation" in runtime_binding["runtime_owns"]
    assert "argv spelling and help rendering" in runtime_binding["target_projection_owns"]
    assert "adapter failures" in " ".join(runtime_binding["error_mapping"])
    assert "must not own runtime primitive behavior" in manifest["generation_policy"]["shell_adapter_policy"]
    assert "direct cli.py edits" in manifest["generation_policy"]["direct_cli_edit_policy"]

    root_package = packages["root-workspace"]
    targets = {target["kind"]: target for target in root_package["targets"]}

    assert root_package["program"] == "agentic-workspace"
    assert targets["python"]["test_environment"] == "python-dev"
    assert targets["python"]["maturity_level_ref"] == "runtime-backed-read-only-adapter"
    assert targets["python"]["generation_status"] == "runtime-backed-read-only-adapter"
    assert targets["typescript"]["test_environment"] == "docker"
    assert targets["typescript"]["maturity_level_ref"] == "runnable-read-only-adapter"
    assert targets["typescript"]["generation_status"] == "runnable-read-only-adapter"
    assert targets["bash"]["generation_status"] == "deferred"
    assert targets["bash"]["maturity_level_ref"] == "deferred"
    assert targets["powershell"]["generation_status"] == "deferred"


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
        "skills.report.cli",
        "report.combined.cli",
        "reconcile.report.cli",
        "setup.guidance.cli",
        "status.report.cli",
        "doctor.report.cli",
        "planning.status.cli",
        "planning.doctor.cli",
        "planning.summary.cli",
        "planning.report.cli",
        "planning.reconcile.cli",
        "memory.status.cli",
        "memory.doctor.cli",
        "memory.report.cli",
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

    calls: list[tuple[str, str]] = []

    def fake_run(command: list[str]) -> int:
        return 0

    def fake_run_docker(tag: str, *, dockerfile: str, require_docker: bool) -> int:
        calls.append((tag, dockerfile))
        assert require_docker is True
        return 0

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "_run_docker", fake_run_docker)

    assert module.main(["--docker", "--docker-conformance", "--require-docker"]) == 0
    assert calls == [
        ("agentic-workspace-generated-typescript-cli-test", "generated/typescript/Dockerfile"),
        ("agentic-workspace-generated-typescript-cli-test-conformance", "generated/typescript/Dockerfile.conformance"),
    ]


def test_generated_command_package_docker_conformance_surface_exists() -> None:
    dockerfile = Path(__file__).resolve().parents[1] / "generated" / "typescript" / "Dockerfile.conformance"
    text = dockerfile.read_text(encoding="utf-8")

    assert "scripts/check/check_generated_command_packages.py" in text
    assert "--conformance" in text
    assert "--require-node" in text
    assert "COPY src ./src" in text
    assert "COPY generated/typescript ./generated/typescript" in text


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
    from agentic_command_generation import load_command_package_ir

    repo_root = Path(__file__).resolve().parents[1]
    ir_path = repo_root / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json"
    schema_path = repo_root / "packages" / "command-generation" / "schemas" / "command_package_ir.schema.json"

    manifest = load_command_package_ir(ir_path, schema_path)

    assert manifest["schema_version"] == "agentic-workspace/command-package-ir/v1"
    assert {package["program"] for package in manifest["packages"]} >= {
        "agentic-workspace",
        "agentic-planning-bootstrap",
        "agentic-memory-bootstrap",
    }


def test_operation_command_parity_uses_package_program_namespace() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    root_commands = module._known_command_names_for_program("agentic-workspace")
    memory_commands = module._known_command_names_for_program("agentic-memory-bootstrap")

    assert "route-report" not in root_commands
    assert {"route-report", "promotion-report", "list-files", "list-skills"}.issubset(memory_commands)
    assert module._validate_operation_registry(module.operation_contracts_manifest()) == []


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
    generator = (
        Path(__file__).resolve().parents[1] / "packages" / "command-generation" / "src" / "agentic_command_generation" / "generator.py"
    )
    wrapper = Path(__file__).resolve().parents[1] / "scripts" / "generate" / "generate_command_packages.py"

    assert 'newline="\\n"' in generator.read_text(encoding="utf-8")
    assert "line-ending drift" in wrapper.read_text(encoding="utf-8")


def test_generic_command_generation_package_has_no_workspace_imports() -> None:
    package_root = Path(__file__).resolve().parents[1] / "packages" / "command-generation" / "src" / "agentic_command_generation"
    for path in package_root.rglob("*.py"):
        assert "agentic_workspace" not in path.read_text(encoding="utf-8")


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
    from agentic_workspace.generated_cli_package import GENERATED_COMMAND_PACKAGE, generated_command_names, supports_generated_command

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
        "skills.report.cli",
        "report.combined.cli",
        "reconcile.report.cli",
        "setup.guidance.cli",
        "status.report.cli",
        "doctor.report.cli",
    }
    target_kinds = {target["kind"] for target in GENERATED_COMMAND_PACKAGE["targets"]}
    assert {"python", "typescript", "bash", "powershell"} <= target_kinds
    assert generated_command_names() == (
        "config",
        "defaults",
        "doctor",
        "implement",
        "modules",
        "ownership",
        "preflight",
        "proof",
        "reconcile",
        "report",
        "setup",
        "skills",
        "start",
        "status",
        "summary",
    )
    assert supports_generated_command(["defaults", "--format", "json"]) is True
    assert supports_generated_command(["config", "--format", "json"]) is True
    assert supports_generated_command(["modules", "--format", "json"]) is True
    assert supports_generated_command(["start", "--format", "json"]) is True
    assert supports_generated_command(["summary", "--format", "json"]) is True
    assert supports_generated_command(["implement", "--format", "json"]) is True
    assert supports_generated_command(["preflight", "--format", "json"]) is True
    assert supports_generated_command(["proof", "--format", "json"]) is True
    assert supports_generated_command(["ownership", "--format", "json"]) is True
    assert supports_generated_command(["skills", "--format", "json"]) is True
    assert supports_generated_command(["report", "--format", "json"]) is True
    assert supports_generated_command(["reconcile", "--format", "json"]) is True
    assert supports_generated_command(["setup", "--format", "json"]) is True
    assert supports_generated_command(["status", "--format", "json"]) is True
    assert supports_generated_command(["doctor", "--format", "json"]) is True


def test_generated_python_command_package_parses_and_dispatches_runtime_operations() -> None:
    from agentic_workspace.generated_cli_package import run_generated_command

    calls: list[tuple[str, str | None, str, str | None]] = []

    def runtime_handler(operation_id: str, args: argparse.Namespace) -> int:
        calls.append((operation_id, getattr(args, "target", None), args.format, getattr(args, "section", None)))
        return 0

    assert run_generated_command(["defaults", "--section", "startup", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["config", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["modules", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["start", "--target", ".", "--changed", "README.md", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["summary", "--target", ".", "--profile", "compact", "--format", "json"], runtime_handler) == 0
    assert (
        run_generated_command(
            ["implement", "--target", ".", "--changed", "README.md", "--task", "generated-adapter-proof", "--format", "json"],
            runtime_handler,
        )
        == 0
    )
    assert run_generated_command(["preflight", "--target", ".", "--active-only", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["proof", "--target", ".", "--changed", "README.md", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["ownership", "--target", ".", "--concern", "startup", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["skills", "--target", ".", "--task", "proof", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["report", "--target", ".", "--profile", "router", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["reconcile", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["setup", "--target", ".", "--modules", "planning", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["status", "--target", ".", "--modules", "planning", "--format", "json"], runtime_handler) == 0
    assert run_generated_command(["doctor", "--target", ".", "--modules", "planning", "--format", "json"], runtime_handler) == 0
    assert calls == [
        ("defaults.report", None, "json", "startup"),
        ("config.report", ".", "json", None),
        ("modules.report", ".", "json", None),
        ("start.context", ".", "json", None),
        ("summary.report", ".", "json", None),
        ("implement.context", ".", "json", None),
        ("preflight.report", ".", "json", None),
        ("proof.report", ".", "json", None),
        ("ownership.report", ".", "json", None),
        ("skills.report", ".", "json", None),
        ("report.combined", ".", "json", None),
        ("reconcile.report", ".", "json", None),
        ("setup.guidance", ".", "json", None),
        ("status.report", ".", "json", None),
        ("doctor.report", ".", "json", None),
    ]


def test_package_generated_python_command_packages_parse_status_runtime_operations() -> None:
    from repo_memory_bootstrap.generated_cli_package import run_generated_command as run_memory_generated_command
    from repo_planning_bootstrap.generated_cli_package import run_generated_command as run_planning_generated_command

    calls: list[tuple[str, str | None, str]] = []

    def runtime_handler(operation_id: str, args: argparse.Namespace) -> int:
        calls.append((operation_id, getattr(args, "target", None), args.format))
        return 0

    assert run_planning_generated_command(["status", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_planning_generated_command(["doctor", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_planning_generated_command(["summary", "--target", ".", "--profile", "compact", "--format", "json"], runtime_handler) == 0
    assert run_planning_generated_command(["report", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_planning_generated_command(["reconcile", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_memory_generated_command(["status", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_memory_generated_command(["doctor", "--target", ".", "--format", "json"], runtime_handler) == 0
    assert run_memory_generated_command(["report", "--target", ".", "--format", "json"], runtime_handler) == 0
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
    test_text = (package_root / "test" / "command-package.test.mjs").read_text(encoding="utf-8")

    assert package_json["name"] == "@agentic-workspace/workspace-cli"
    assert package_json["bin"] == {"agentic-workspace": "./src/cli.mjs"}
    assert package_json["agenticWorkspace"]["generated"] is True
    assert package_json["agenticWorkspace"]["fixtureOnly"] is False
    assert package_json["agenticWorkspace"]["generationStatus"] == "runnable-read-only-adapter"
    assert package_json["agenticWorkspace"]["maturity"]["id"] == "runnable-read-only-adapter"
    assert package_json["agenticWorkspace"]["maturity"]["weak_agent_routing"] == "review-required"
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
    assert "generated package metadata exposes expected commands" in test_text
    assert "generated runnable adapter delegates supported command to runtime process" in test_text


def test_generated_typescript_proof_fixture_declares_non_runnable_maturity() -> None:
    package_root = Path(__file__).resolve().parents[1] / "generated" / "typescript" / "memory-cli"
    package_json = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
    test_text = (package_root / "test" / "command-package.test.mjs").read_text(encoding="utf-8")

    assert package_json["name"] == "@agentic-workspace/memory-cli"
    assert "bin" not in package_json
    metadata = package_json["agenticWorkspace"]
    assert metadata["fixtureOnly"] is True
    assert metadata["generationStatus"] == "proof-fixture"
    assert metadata["maturity"]["id"] == "metadata-proof-fixture"
    assert metadata["maturity"]["runnable"] is False
    assert metadata["maturity"]["weak_agent_routing"] == "forbidden"
    assert metadata["maturity"]["promotion_requires"]
    assert "generated package metadata exposes maturity and weak-agent routing status" in test_text


def test_generated_command_adapter_module_routes_direct_edits_to_authoritative_sources() -> None:
    generated_path = Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "generated_command_adapters.py"
    generated_text = generated_path.read_text(encoding="utf-8")

    assert "DO NOT EDIT DIRECTLY." in generated_text
    assert "src/agentic_workspace/contracts/command_adapter_generation.json" in generated_text
    assert "hand-written operation/primitive implementation code" in generated_text
    assert "uv run python scripts/generate/generate_command_adapters.py" in generated_text


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
        "agentic_workspace.cli",
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
        "agentic-planning-bootstrap",
        "agentic-memory-bootstrap",
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
        "defaults",
        "config",
        "modules",
        "start",
        "summary",
        "implement",
        "preflight",
        "proof",
        "ownership",
        "skills",
        "report",
        "reconcile",
        "setup",
        "status",
        "doctor",
    ]
    assert commands_by_program["agentic-planning-bootstrap"] == ["status", "doctor", "summary", "report", "reconcile"]
    assert commands_by_program["agentic-memory-bootstrap"] == ["doctor", "report", "status"]


def test_generated_adapter_contracts_match_live_cli_surfaces() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._validate_generated_adapter_live_cli_parity(contract_tooling.command_adapter_generation_manifest()) == []


def test_generated_adapter_live_cli_parity_catches_missing_contract_option(monkeypatch: pytest.MonkeyPatch) -> None:
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
            "command_surface": {"program": "agentic-memory-bootstrap", "command": "status", "format_option": "format"},
            "inputs": [{"name": "format", "source": "cli-option", "required": False}],
        }

    monkeypatch.setattr(module, "operation_manifest", fake_operation_manifest)

    errors = module._validate_generated_adapter_live_cli_parity({"adapters": [memory_adapter]})

    assert errors == ["generated adapter memory.status.cli live parser has CLI option(s) missing from operation contract: target"]


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
