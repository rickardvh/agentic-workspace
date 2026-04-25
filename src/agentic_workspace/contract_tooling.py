from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def contracts_root() -> Path:
    return Path(__file__).resolve().parent / "contracts"


@lru_cache(maxsize=None)
def load_contract_json(relative_path: str) -> dict[str, Any]:
    path = contracts_root() / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def compact_contract_manifest() -> dict[str, Any]:
    return load_contract_json("compact_contract_profile.json")


def proof_routes_manifest() -> dict[str, Any]:
    return load_contract_json("proof_routes.json")


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


def operation_primitives_manifest() -> dict[str, Any]:
    return load_contract_json("operation_primitives.json")


def operation_manifest(relative_path: str) -> dict[str, Any]:
    return load_contract_json(relative_path)


def python_extraction_map_manifest() -> dict[str, Any]:
    return load_contract_json("python_extraction_map.json")


def contract_schema(relative_path: str) -> dict[str, Any]:
    return load_contract_json(f"schemas/{relative_path}")
