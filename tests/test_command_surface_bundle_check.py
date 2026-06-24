from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_checker():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_command_surface_bundle.py"
    spec = importlib.util.spec_from_file_location("check_command_surface_bundle", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_command_surface_bundle_check_passes_for_checkpoint_write() -> None:
    checker = _load_checker()

    report = checker.command_surface_bundle_report("checkpoint.write")

    assert report["status"] == "ok"
    assert report["missing"] == []
    assert "checkpoint.write.cli" in report["details"]["package_refs"]
    assert report["details"]["python_operation_execution_inventory"]
    assert report["details"]["python_runtime_projection_inventory"]


def test_command_surface_bundle_check_reports_all_missing_layers(tmp_path: Path) -> None:
    checker = _load_checker()
    contract_root = tmp_path / "src/agentic_workspace/contracts"
    generated_root = tmp_path / "generated/workspace/python"
    (contract_root / "operations").mkdir(parents=True)
    (contract_root / "conformance").mkdir(parents=True)
    generated_root.mkdir(parents=True)
    (contract_root / "operations/example.write.json").write_text(
        json.dumps(
            {
                "id": "example.write",
                "steps": [{"uses": "workspace.example.write"}],
                "output": {"schema_ref": "schemas/example_write_result.schema.json"},
            }
        ),
        encoding="utf-8",
    )
    for relative, payload in {
        "operation_contracts.json": {"operations": []},
        "operation_primitives.json": {"primitives": []},
        "conformance_contracts.json": {"contracts": []},
        "command_adapter_generation.json": {"adapters": []},
        "command_package_ir.json": {"packages": []},
        "python_operation_execution_inventory.json": {"entries": []},
        "python_runtime_projection_inventory.json": {"accepted_runtime_boundaries": {"entries": []}},
    }.items():
        (contract_root / relative).write_text(json.dumps(payload), encoding="utf-8")
    (generated_root / "command_package.json").write_text(json.dumps({"commands": []}), encoding="utf-8")

    report = checker.command_surface_bundle_report("example.write", repo_root=tmp_path)

    assert report["status"] == "missing-companion-surfaces"
    assert {
        "operation_contract_registry",
        "operation_primitives",
        "conformance_file",
        "conformance_registry",
        "command_adapter_generation",
        "command_package_ir",
        "generated_python_command_package",
        "python_operation_execution_inventory",
        "python_runtime_projection_inventory",
        "output_schema_refs",
        "conformance_refs",
    } <= set(report["missing"])
