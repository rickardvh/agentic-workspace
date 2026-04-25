from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class ContractValidationError(ValueError):
    """Raised when a checked-in contract does not satisfy its declared schema."""


def contracts_root() -> Path:
    return Path(__file__).resolve().parent / "contracts"


@lru_cache(maxsize=None)
def load_contract_json(relative_path: str) -> dict[str, Any]:
    path = contracts_root() / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_validated_contract_json(relative_path: str, schema_relative_path: str) -> dict[str, Any]:
    payload = load_contract_json(relative_path)
    schema = contract_schema(schema_relative_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ContractValidationError(
            f"{relative_path} failed validation against schemas/{schema_relative_path} at {location}: {first.message}"
        )
    return payload


def compact_contract_manifest() -> dict[str, Any]:
    return load_contract_json("compact_contract_profile.json")


def proof_routes_manifest() -> dict[str, Any]:
    return load_contract_json("proof_routes.json")


def proof_selection_rules_manifest() -> dict[str, Any]:
    return load_validated_contract_json("proof_selection_rules.json", "proof_selection_rules.schema.json")


def report_contract_manifest() -> dict[str, Any]:
    return load_contract_json("report_contract.json")


def contract_inventory_manifest() -> dict[str, Any]:
    return load_contract_json("contract_inventory.json")


def workspace_surfaces_manifest() -> dict[str, Any]:
    return load_contract_json("workspace_surfaces.json")


def setup_findings_policy_manifest() -> dict[str, Any]:
    return load_contract_json("setup_findings_policy.json")


def workflow_artifact_profiles_manifest() -> dict[str, Any]:
    return load_contract_json("workflow_artifact_profiles.json")


def workflow_definition_format_manifest() -> dict[str, Any]:
    return load_validated_contract_json("workflow_definition_format.json", "workflow_definition_format.schema.json")


def improvement_latitude_policy_manifest() -> dict[str, Any]:
    return load_contract_json("improvement_latitude_policy.json")


def optimization_bias_policy_manifest() -> dict[str, Any]:
    return load_contract_json("optimization_bias_policy.json")


def repo_friction_policy_manifest() -> dict[str, Any]:
    return load_contract_json("repo_friction_policy.json")


def preflight_policy_manifest() -> dict[str, Any]:
    return load_contract_json("preflight_policy.json")


def module_registry_manifest() -> dict[str, Any]:
    return load_contract_json("module_registry.json")


def cli_commands_manifest() -> dict[str, Any]:
    return load_contract_json("cli_commands.json")


def cli_option_groups_manifest() -> dict[str, Any]:
    return load_contract_json("cli_option_groups.json")


def operation_contracts_manifest() -> dict[str, Any]:
    return load_contract_json("operation_contracts.json")


def conformance_contracts_manifest() -> dict[str, Any]:
    return load_contract_json("conformance_contracts.json")


def conformance_contract_manifest(relative_path: str) -> dict[str, Any]:
    return load_validated_contract_json(relative_path, "conformance.schema.json")


def operation_primitives_manifest() -> dict[str, Any]:
    return load_contract_json("operation_primitives.json")


def operation_manifest(relative_path: str) -> dict[str, Any]:
    return load_contract_json(relative_path)


def python_extraction_map_manifest() -> dict[str, Any]:
    return load_contract_json("python_extraction_map.json")


def python_contract_consumption_manifest() -> dict[str, Any]:
    return load_validated_contract_json("python_contract_consumption.json", "python_contract_consumption.schema.json")


def context_templates_manifest() -> dict[str, Any]:
    return load_validated_contract_json("context_templates.json", "context_templates.schema.json")


def python_runtime_boundary_manifest() -> dict[str, Any]:
    return load_validated_contract_json("python_runtime_boundary.json", "python_runtime_boundary.schema.json")


def contract_schema(relative_path: str) -> dict[str, Any]:
    return load_contract_json(f"schemas/{relative_path}")
