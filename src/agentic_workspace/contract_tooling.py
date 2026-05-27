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
        repo_root / "packages" / "verification" / "src" / "repo_verification_bootstrap" / "contracts",
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


def _markdown_list(items: list[Any]) -> str:
    return "\n".join(f"- {str(item)}" for item in items)


def _generated_behavior_fixture_lines(manifest: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for fixture in manifest.get("generated_target_behavior_fixtures", []):
        if not isinstance(fixture, dict):
            continue
        fixture_id = str(fixture.get("id", ""))
        task_shape = str(fixture.get("task_shape", ""))
        required_skill = str(fixture.get("required_skill", ""))
        preserve = "; ".join(str(item) for item in fixture.get("must_preserve", []) if str(item).strip())
        lines.append(f"`{fixture_id}` ({task_shape}, skill `{required_skill}`): {preserve}")
    return lines


def render_skillspec_target_skill(manifest: dict[str, Any], skill_id: str) -> str:
    specs = {str(spec.get("id")): spec for spec in manifest.get("specs", []) if isinstance(spec, dict)}
    if skill_id not in specs:
        raise KeyError(f"unknown SkillSpec id: {skill_id}")
    spec = specs[skill_id]
    commands = spec.get("preferred_cli_commands", [])
    primary_command = commands[0] if commands and isinstance(commands[0], dict) else {}
    generated_requirements = spec.get("generated_target_requirements", {})
    must_preserve = generated_requirements.get("must_preserve", []) if isinstance(generated_requirements, dict) else []

    sections = [
        "---",
        f"name: generated-{skill_id}",
        "description: Generated SkillSpec target projection for Agentic Workspace startup routing. Use as a compact adapter target, not as the source of product behavior.",
        "---",
        "",
        f"# Generated {spec.get('title', skill_id)}",
        "",
        "Generated from `src/agentic_workspace/contracts/skill_specs.json`. Do not hand-edit generated output.",
        "",
        "## Applies When",
        _markdown_list(list(spec.get("applies_when", []))),
        "",
        "## Preferred CLI",
        f"- `{primary_command.get('preferred_invocation', '')}`",
        f"- Purpose: {primary_command.get('purpose', '')}",
        f"- Mutates state: {str(primary_command.get('mutates_state', False)).lower()}",
        "",
        "## Interpret These Fields",
        _markdown_list(
            [
                f"`{field.get('path', '')}`: {field.get('decision', '')}"
                for field in spec.get("interpreted_output_fields", [])
                if isinstance(field, dict)
            ]
        ),
        "",
        "## Allowed Actions",
        _markdown_list(list(spec.get("allowed_actions", []))),
        "",
        "## Forbidden Actions",
        _markdown_list(list(spec.get("forbidden_actions", []))),
        "",
        "## No-CLI Fallback",
        _markdown_list(list(spec.get("fallback_when_cli_unavailable", []))),
        "",
        "## Proof And Closeout",
        _markdown_list([*list(spec.get("proof_obligations", [])), *list(spec.get("closeout_obligations", []))]),
        "",
        "## Generated Target Contract",
        _markdown_list(list(must_preserve)),
        "",
        "## Behavior Fixture",
        "- Direct task: continue without durable artifacts only when compact routing permits it and proof is obvious.",
        "- Lane or epic task: block implementation until compact routing, planning ownership, and proof expectations are present.",
        "- Fallback task: when the CLI is unavailable, read the workflow fallback and preserve forbidden actions.",
        "",
        "## Generated Target Behavior Fixtures",
        _markdown_list(_generated_behavior_fixture_lines(manifest)),
        "",
    ]
    return "\n".join(sections)


def _generated_plugin_targets(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(target.get("id")): target for target in manifest.get("generated_plugin_targets", []) if isinstance(target, dict)}


def render_skillspec_plugin_target(manifest: dict[str, Any], target_id: str) -> str:
    targets = _generated_plugin_targets(manifest)
    if target_id not in targets:
        raise KeyError(f"unknown SkillSpec plugin target id: {target_id}")
    target = targets[target_id]

    payload = {
        "name": target["plugin_name"],
        "version": "0.1.0",
        "description": "Generated Codex plugin projection for Agentic Workspace startup routing.",
        "author": {
            "name": "Agentic Workspace",
            "url": "https://github.com/rickardvh/agentic-workspace",
        },
        "repository": "https://github.com/rickardvh/agentic-workspace",
        "license": "MIT",
        "keywords": [
            "agentic-workspace",
            "skillspec",
            "workspace-routing",
        ],
        "skills": "./skills/",
        "interface": {
            "displayName": "Agentic Workspace",
            "shortDescription": "Generated AW routing plugin projection.",
            "longDescription": (
                "Framework-native metadata generated from SkillSpec. The plugin prefers the configured AW CLI "
                "when available and preserves conservative no-CLI fallback behavior."
            ),
            "developerName": "Agentic Workspace",
            "category": "Productivity",
            "capabilities": [
                "Read",
                "Workflow",
            ],
            "defaultPrompt": [
                "Start AW routing for this repo.",
                "Check whether completion is claimable.",
                "Show the next safe AW action.",
            ],
        },
        "agenticWorkspace": {
            "generated": True,
            "source": "src/agentic_workspace/contracts/skill_specs.json",
            "schema": "src/agentic_workspace/contracts/schemas/skill_spec.schema.json",
            "targetId": target["id"],
            "framework": target["framework"],
            "status": target["status"],
            "sourceSkillSpecs": target["source_skill_ids"],
            "generatedSkills": target["generated_skill_paths"],
            "preferredCli": target["preferred_cli_commands"],
            "cliDependency": target["cli_dependency"],
            "interpretedFields": target["interpreted_fields"],
            "forbiddenActions": target["forbidden_actions"],
            "fallbackWhenCliUnavailable": target["fallback_when_cli_unavailable"],
            "mustPreserve": target["must_preserve"],
            "nextSafeActionSemantics": target["next_safe_action_semantics"],
            "behaviorFixtures": manifest["generated_target_behavior_fixtures"],
            "whereToEdit": "src/agentic_workspace/contracts/skill_specs.json",
            "doNotHandEditGeneratedOutput": True,
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


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


def operational_affordance_roles_manifest() -> dict[str, Any]:
    return load_validated_contract_json("operational_affordance_roles.json", "operational_affordance_roles.schema.json")


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
