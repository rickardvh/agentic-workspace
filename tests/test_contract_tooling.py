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

    assert defaults_adapter["command"]["name"] == "defaults"
    assert defaults_adapter["operation_ref"]["id"] == "defaults.report"
    assert defaults_adapter["runtime_binding"]["kind"] == "operation-primitive-sequence"
    assert defaults_adapter["effect_hints"]["read_only"] is True
    assert defaults_adapter["effect_hints"]["writes_repo_state"] is False
    assert "defaults.report.process" in defaults_adapter["conformance_refs"]
    assert "primitive implementation" in defaults_adapter["generation_boundary"]["runtime_owns"]


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
