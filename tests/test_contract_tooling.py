from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from agentic_workspace import contract_tooling


def test_contract_tooling_check_passes() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main([]) == 0


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
    assert migration["memory"]["status"] == "planned-next-package-surface"


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


def test_generated_command_adapter_module_routes_direct_edits_to_authoritative_sources() -> None:
    generated_path = Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "generated_command_adapters.py"
    generated_text = generated_path.read_text(encoding="utf-8")

    assert "DO NOT EDIT DIRECTLY." in generated_text
    assert "src/agentic_workspace/contracts/command_adapter_generation.json" in generated_text
    assert "hand-written operation/primitive implementation code" in generated_text
    assert "uv run python scripts/generate/generate_command_adapters.py" in generated_text


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
