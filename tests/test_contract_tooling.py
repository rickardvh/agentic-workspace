from __future__ import annotations

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
    assert targets["typescript"]["test_environment"] == "docker"
    assert targets["typescript"]["maturity_level_ref"] == "metadata-proof-fixture"
    assert targets["bash"]["generation_status"] == "deferred"
    assert targets["bash"]["maturity_level_ref"] == "deferred"
    assert targets["powershell"]["generation_status"] == "deferred"


def test_command_package_ir_reuses_generated_adapter_truth() -> None:
    package_ir = contract_tooling.command_package_ir_manifest()
    adapter_manifest = contract_tooling.command_adapter_generation_manifest()
    adapters = {adapter["id"]: adapter for adapter in adapter_manifest["adapters"]}
    commands = {command["adapter_id"]: command for package in package_ir["packages"] for command in package["commands"]}

    assert set(commands) == {"defaults.report.cli", "planning.status.cli", "memory.status.cli"}
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
    assert commands[("planning-package", "status")]["generation_eligibility"] == "eligible-read-only"
    assert commands[("memory-package", "status")]["generation_eligibility"] == "eligible-read-only"
    assert any("strict preflight" in fixture for fixture in manifest["conformance_fixture_plan"])


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


def test_generated_python_command_package_metadata_is_current() -> None:
    from agentic_workspace.generated_cli_package import GENERATED_COMMAND_PACKAGE

    assert GENERATED_COMMAND_PACKAGE["program"] == "agentic-workspace"
    assert {command["adapter_id"] for command in GENERATED_COMMAND_PACKAGE["commands"]} == {"defaults.report.cli"}
    target_kinds = {target["kind"] for target in GENERATED_COMMAND_PACKAGE["targets"]}
    assert {"python", "typescript", "bash", "powershell"} <= target_kinds


def test_generated_typescript_command_package_fixture_is_current() -> None:
    package_root = Path(__file__).resolve().parents[1] / "generated" / "typescript" / "workspace-cli"
    package_json = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
    source_text = (package_root / "src" / "commandPackage.ts").read_text(encoding="utf-8")
    test_text = (package_root / "test" / "command-package.test.mjs").read_text(encoding="utf-8")

    assert package_json["name"] == "@agentic-workspace/workspace-cli"
    assert "bin" not in package_json
    assert package_json["agenticWorkspace"]["generated"] is True
    assert package_json["agenticWorkspace"]["fixtureOnly"] is True
    assert package_json["agenticWorkspace"]["generationStatus"] == "proof-fixture"
    assert package_json["agenticWorkspace"]["maturity"]["id"] == "metadata-proof-fixture"
    assert package_json["agenticWorkspace"]["maturity"]["weak_agent_routing"] == "forbidden"
    assert package_json["agenticWorkspace"]["maturity"]["runnable"] is False
    assert (
        package_json["agenticWorkspace"]["runtimeBinding"]["selected_model"]
        == "generated parser/help with process handoff to canonical Python CLI"
    )
    assert package_json["agenticWorkspace"]["declaredEntrypoints"] == ["agentic-workspace"]
    assert "defaults.report.cli" in source_text
    assert "DO NOT EDIT DIRECTLY" in source_text
    assert "generated package metadata exposes expected commands" in test_text


def test_generated_command_adapter_module_routes_direct_edits_to_authoritative_sources() -> None:
    generated_path = Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "generated_command_adapters.py"
    generated_text = generated_path.read_text(encoding="utf-8")

    assert "DO NOT EDIT DIRECTLY." in generated_text
    assert "src/agentic_workspace/contracts/command_adapter_generation.json" in generated_text
    assert "hand-written operation/primitive implementation code" in generated_text
    assert "uv run python scripts/generate/generate_command_adapters.py" in generated_text


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
    assert commands_by_program["agentic-workspace"] == ["defaults"]
    assert commands_by_program["agentic-planning-bootstrap"] == ["status"]
    assert commands_by_program["agentic-memory-bootstrap"] == ["status"]


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
