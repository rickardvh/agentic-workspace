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


def contract_roots() -> tuple[Path, ...]:
    repo_root = contracts_root().parents[2]
    return (
        contracts_root(),
        repo_root / "packages" / "planning" / "src" / "repo_planning_bootstrap" / "contracts",
        repo_root / "packages" / "memory" / "src" / "repo_memory_bootstrap" / "contracts",
    )


def contract_path(relative_path: str) -> Path:
    for root in contract_roots():
        candidate = root / relative_path
        if candidate.is_file():
            return candidate
    return contracts_root() / relative_path


@lru_cache(maxsize=None)
def load_contract_json(relative_path: str) -> dict[str, Any]:
    path = contract_path(relative_path)
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
    return load_validated_contract_json("proof_routes.json", "proof_routes_manifest.schema.json")


def proof_selection_rules_manifest() -> dict[str, Any]:
    return load_validated_contract_json("proof_selection_rules.json", "proof_selection_rules.schema.json")


def authority_markers_manifest() -> dict[str, Any]:
    return load_validated_contract_json("authority_markers.json", "authority_markers.schema.json")


def report_contract_manifest() -> dict[str, Any]:
    return load_validated_contract_json("report_contract.json", "report_contract_manifest.schema.json")


def contract_inventory_manifest() -> dict[str, Any]:
    return load_validated_contract_json("contract_inventory.json", "contract_inventory.schema.json")


def workspace_surfaces_manifest() -> dict[str, Any]:
    return load_validated_contract_json("workspace_surfaces.json", "workspace_surfaces_manifest.schema.json")


def setup_findings_policy_manifest() -> dict[str, Any]:
    return load_validated_contract_json("setup_findings_policy.json", "setup_findings_policy.schema.json")


def workflow_artifact_profiles_manifest() -> dict[str, Any]:
    return load_validated_contract_json("workflow_artifact_profiles.json", "workflow_artifact_profiles.schema.json")


def workflow_definition_format_manifest() -> dict[str, Any]:
    return load_validated_contract_json("workflow_definition_format.json", "workflow_definition_format.schema.json")


def skill_specs_manifest() -> dict[str, Any]:
    return load_validated_contract_json("skill_specs.json", "skill_spec.schema.json")


def improvement_latitude_policy_manifest() -> dict[str, Any]:
    return load_validated_contract_json("improvement_latitude_policy.json", "improvement_latitude_policy.schema.json")


def improvement_signal_contract_manifest() -> dict[str, Any]:
    return load_validated_contract_json("improvement_signal_contract.json", "improvement_signal_contract.schema.json")


def optimization_bias_policy_manifest() -> dict[str, Any]:
    return load_validated_contract_json("optimization_bias_policy.json", "optimization_bias_policy.schema.json")


def repo_friction_policy_manifest() -> dict[str, Any]:
    return load_validated_contract_json("repo_friction_policy.json", "repo_friction_policy.schema.json")


def preflight_policy_manifest() -> dict[str, Any]:
    return load_validated_contract_json("preflight_policy.json", "preflight_policy.schema.json")


def module_registry_manifest() -> dict[str, Any]:
    return load_validated_contract_json("module_registry.json", "module_registry.schema.json")


def cli_commands_manifest() -> dict[str, Any]:
    return load_validated_contract_json("cli_commands.json", "cli_commands.schema.json")


def cli_option_groups_manifest() -> dict[str, Any]:
    return load_validated_contract_json("cli_option_groups.json", "cli_option_groups.schema.json")


def operation_contracts_manifest() -> dict[str, Any]:
    return load_validated_contract_json("operation_contracts.json", "operation_contracts.schema.json")


def conformance_contracts_manifest() -> dict[str, Any]:
    return load_validated_contract_json("conformance_contracts.json", "conformance_contracts.schema.json")


def command_adapter_generation_manifest() -> dict[str, Any]:
    return load_validated_contract_json("command_adapter_generation.json", "command_adapter_generation.schema.json")


def command_package_ir_manifest() -> dict[str, Any]:
    return load_validated_contract_json("command_package_ir.json", "command_package_ir.schema.json")


def lifecycle_generation_readiness_manifest() -> dict[str, Any]:
    return load_validated_contract_json("lifecycle_generation_readiness.json", "lifecycle_generation_readiness.schema.json")


def conformance_contract_manifest(relative_path: str) -> dict[str, Any]:
    return load_validated_contract_json(relative_path, "conformance.schema.json")


def operation_primitives_manifest() -> dict[str, Any]:
    return load_validated_contract_json("operation_primitives.json", "operation_primitives.schema.json")


def operation_manifest(relative_path: str) -> dict[str, Any]:
    return load_contract_json(relative_path)


def python_extraction_map_manifest() -> dict[str, Any]:
    return load_validated_contract_json("python_extraction_map.json", "python_extraction_map.schema.json")


def python_contract_consumption_manifest() -> dict[str, Any]:
    return load_validated_contract_json("python_contract_consumption.json", "python_contract_consumption.schema.json")


def context_templates_manifest() -> dict[str, Any]:
    return load_validated_contract_json("context_templates.json", "context_templates.schema.json")


def python_runtime_boundary_manifest() -> dict[str, Any]:
    return load_validated_contract_json("python_runtime_boundary.json", "python_runtime_boundary.schema.json")


def python_runtime_projection_inventory_manifest() -> dict[str, Any]:
    return load_validated_contract_json("python_runtime_projection_inventory.json", "python_runtime_projection_inventory.schema.json")


def contract_schema(relative_path: str) -> dict[str, Any]:
    return load_contract_json(f"schemas/{relative_path}")
