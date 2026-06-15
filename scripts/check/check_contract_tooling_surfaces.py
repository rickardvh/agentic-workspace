from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace import workspace_runtime_primitives as cli
from agentic_workspace.contract_tooling import (
    authority_markers_manifest,
    cli_commands_manifest,
    cli_option_groups_manifest,
    command_adapter_generation_manifest,
    command_package_ir_manifest,
    compact_contract_manifest,
    conformance_contract_manifest,
    conformance_contracts_manifest,
    context_templates_manifest,
    contract_inventory_manifest,
    contract_schema,
    generated_behavior_stratification_manifest,
    improvement_latitude_policy_manifest,
    improvement_signal_contract_manifest,
    lifecycle_generation_readiness_manifest,
    module_registry_manifest,
    operation_artifact_registry_manifest,
    operation_conformance_test_ir_manifest,
    operation_contracts_manifest,
    operation_manifest,
    operation_primitives_manifest,
    optimization_bias_policy_manifest,
    preflight_policy_manifest,
    proof_routes_manifest,
    proof_selection_rules_manifest,
    python_contract_consumption_manifest,
    python_extraction_map_manifest,
    python_runtime_boundary_manifest,
    python_runtime_projection_inventory_manifest,
    repo_friction_policy_manifest,
    report_contract_manifest,
    setup_findings_policy_manifest,
    target_support_manifest,
    workflow_artifact_profiles_manifest,
    workflow_definition_format_manifest,
    workspace_surfaces_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

from command_generation import (  # noqa: E402
    TargetExtensionContractError,
    command_package_schema_path,
    target_support_matrix_entries,
    validate_target_extension_contract,
)
from command_generation.generated_package_loader import (  # noqa: E402
    load_generated_command_module_for_entrypoint,
    load_generated_command_package_for_entrypoint,
)

generated_workspace_cli = load_generated_command_module_for_entrypoint("agentic-workspace", "cli.py")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate contract-tooling schemas, samples, and parity surfaces.")
    parser.add_argument(
        "--quiet-success",
        action="store_true",
        help="Emit a compact one-line success message when no drift warnings are present.",
    )
    return parser.parse_args(argv)


def _validator(schema_name: str) -> Draft202012Validator:
    schema = contract_schema(schema_name)
    return Draft202012Validator(schema)


def _validate(instance: object, schema_name: str) -> list[str]:
    validator = _validator(schema_name)
    return [error.message for error in validator.iter_errors(instance)]


def _validate_command_generation_schema_boundary() -> list[str]:
    workspace_schema = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "schemas" / "command_package_ir.schema.json"
    package_schema = command_package_schema_path()
    errors: list[str] = []
    if not package_schema.is_file():
        return ["command-generation packaged command_package_ir.schema.json is missing"]
    if workspace_schema.read_text(encoding="utf-8") != package_schema.read_text(encoding="utf-8"):
        errors.append("command-generation packaged command_package_ir.schema.json drifted from workspace validation schema")
    return errors


def _sample_compact_answer() -> dict[str, object]:
    return cli._compact_contract_answer(  # type: ignore[attr-defined]
        surface="defaults",
        selector={"section": "proof_selection"},
        answer={"id": "workspace_proof"},
        refs=[".agentic-workspace/docs/compact-contract-profile.md", "agentic-workspace defaults --format json"],
    )


def _sample_report_payload() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "repo"
        target.mkdir()
        (target / ".git").mkdir(exist_ok=True)
        descriptors = cli._module_operations()  # type: ignore[attr-defined]
        config = cli._load_workspace_config(target_root=target, descriptors=descriptors)  # type: ignore[attr-defined]
        selected_modules, resolved_preset = cli._selected_modules(  # type: ignore[attr-defined]
            command_name="report",
            preset_name=None,
            module_arg=None,
            target_root=target,
            descriptors=descriptors,
            config=config,
        )
        return cli._run_report_command(  # type: ignore[attr-defined]
            target_root=target,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            config=config,
        )


def _sample_workspace_config_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "workspace": {
            "agent_instructions_file": "AGENTS.md",
            "workflow_artifact_profile": "repo-owned",
            "improvement_latitude": "balanced",
            "optimization_bias": "agent-efficiency",
        },
        "modules": {
            "enabled": ["planning", "memory"],
        },
        "update": {
            "modules": {
                "planning": {
                    "source_type": "git",
                    "source_ref": "git+https://example.invalid/planning",
                    "source_label": "planning source",
                    "recommended_upgrade_after_days": 30,
                },
                "memory": {
                    "source_type": "local",
                    "source_ref": "../packages/memory",
                    "source_label": "local memory source",
                    "recommended_upgrade_after_days": 7,
                },
            }
        },
        "workflow_obligations": {
            "adapter_surface_refresh": {
                "summary": "Refresh adapter surfaces when structured routing changes.",
                "stage": "before-claiming-completion",
                "scope_tags": ["workspace", "adapter-surfaces"],
                "commands": ["make maintainer-surfaces"],
                "review_hint": "Use when startup routing, llms, or generated agent docs changed.",
            }
        },
        "system_intent": {
            "sources": ["SYSTEM_INTENT.md", "README.md"],
            "preferred_source": "SYSTEM_INTENT.md",
        },
    }


def _sample_workspace_local_override_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "runtime": {
            "supports_internal_delegation": True,
            "strong_planner_available": True,
            "cheap_bounded_executor_available": True,
        },
        "handoff": {
            "prefer_internal_delegation_when_available": False,
        },
        "safety": {
            "safe_to_auto_run_commands": False,
            "requires_human_verification_on_pr": True,
        },
        "delegation_targets": {
            "mini_impl": {
                "strength": "weak",
                "confidence": 0.62,
                "task_fit": ["bounded-docs", "narrow-tests"],
                "execution_methods": ["cli"],
            }
        },
    }


def _sample_delegation_outcomes_payload() -> dict[str, object]:
    return {
        "kind": "agentic-workspace/delegation-outcomes/v1",
        "records": [
            {
                "recorded_at": "2026-04-17",
                "delegation_target": "mini_impl",
                "task_class": "bounded-docs",
                "outcome": "success",
                "handoff_sufficiency": "sufficient",
                "review_burden": "light",
                "escalation_required": False,
            }
        ],
    }


def _sample_setup_findings_payload() -> dict[str, object]:
    return {
        "kind": "workspace-setup-findings/v1",
        "findings": [
            {
                "class": "repo_friction_evidence",
                "summary": "Large shared workspace CLI surface is still a hotspot.",
                "confidence": 0.91,
                "path": "generated/workspace/python/cli.py",
                "refs": [".agentic-workspace/docs/reporting-contract.md"],
                "why": "Would reduce rediscovery during later repo work.",
            },
            {
                "class": "planning_candidate",
                "summary": "One module-reporting follow-on still needs promotion.",
                "confidence": 0.82,
                "next_action": "Promote the next bounded reporting slice into TODO.md when current setup work finishes.",
            },
        ],
    }


def _sample_module_capability_payload() -> dict[str, object]:
    descriptor = cli._module_operations()["planning"]  # type: ignore[attr-defined]
    return {
        "name": descriptor.name,
        "description": descriptor.description,
        "selection_rank": descriptor.selection_rank,
        "kind": descriptor.kind,
        "default_enabled": descriptor.default_enabled,
        "capabilities": list(descriptor.capabilities),
        "commands": list(descriptor.commands),
        "command_args": {name: list(args) for name, args in descriptor.command_args.items()},
        "install_signals": [path.as_posix() for path in descriptor.install_signals],
        "workflow_surfaces": [path.as_posix() for path in descriptor.workflow_surfaces],
        "generated_artifacts": [path.as_posix() for path in descriptor.generated_artifacts],
        "dependencies": list(descriptor.dependencies),
        "conflicts": list(descriptor.conflicts),
        "startup_steps": list(descriptor.startup_steps),
        "sources_of_truth": list(descriptor.sources_of_truth),
        "result_contract": {
            "schema_version": descriptor.result_contract.schema_version,
            "guaranteed_fields": list(descriptor.result_contract.guaranteed_fields),
            "action_fields": list(descriptor.result_contract.action_fields),
            "warning_fields": list(descriptor.result_contract.warning_fields),
        },
    }


def _sample_startup_context_payload() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "repo"
        target.mkdir()
        (target / ".git").mkdir(exist_ok=True)
        return cli._start_payload(  # type: ignore[attr-defined]
            target_root=target,
            changed_paths=["generated/workspace/python/cli.py"],
        )


def _sample_implementer_context_payload() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "repo"
        target.mkdir()
        (target / ".git").mkdir(exist_ok=True)
        return cli._implement_payload(  # type: ignore[attr-defined]
            target_root=target,
            changed_paths=[
                "packages/planning/bootstrap/repo_planning_bootstrap/installer.py",
                "generated/workspace/python/cli.py",
            ],
        )


def _validate_operation_registry(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "agentic-workspace/operation-contracts/v1":
        errors.append("operation_contracts.json has unexpected schema_version")
    operations = payload.get("operations")
    if not isinstance(operations, list) or not operations:
        errors.append("operation_contracts.json must contain at least one operation")
        return errors
    seen_ids: set[str] = set()
    for index, operation_ref in enumerate(operations):
        if not isinstance(operation_ref, dict):
            errors.append(f"operation registry entry {index} must be an object")
            continue
        for field in ("id", "path", "command", "migration_status"):
            if not isinstance(operation_ref.get(field), str) or not str(operation_ref.get(field)).strip():
                errors.append(f"operation registry entry {index} missing string field {field}")
        operation_id = str(operation_ref.get("id", ""))
        if operation_id in seen_ids:
            errors.append(f"duplicate operation id {operation_id}")
        seen_ids.add(operation_id)
    return errors


def _validate_operation_primitives(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "agentic-workspace/operation-primitives/v1":
        errors.append("operation_primitives.json has unexpected schema_version")
    ir_model = payload.get("ir_model")
    if not isinstance(ir_model, dict):
        errors.append("operation_primitives.json must declare ir_model")
    else:
        boundary_rules = ir_model.get("boundary_rules")
        if not isinstance(boundary_rules, list) or not boundary_rules:
            errors.append("operation_primitives.json ir_model must declare boundary_rules")
        if "general-purpose" not in " ".join(str(rule) for rule in boundary_rules).lower():
            errors.append("operation_primitives.json ir_model must explicitly guard against becoming a general-purpose language")
    ownership = payload.get("module_ir_ownership")
    if not isinstance(ownership, dict):
        errors.append("operation_primitives.json must declare module_ir_ownership")
        namespace_prefixes: dict[str, str] = {}
    else:
        namespaces = ownership.get("namespaces")
        if not isinstance(namespaces, list) or not namespaces:
            errors.append("operation_primitives.json module_ir_ownership must declare namespaces")
            namespace_prefixes = {}
        else:
            namespace_prefixes = {}
            for namespace in namespaces:
                if not isinstance(namespace, dict):
                    errors.append("operation_primitives.json module_ir_ownership namespaces must be objects")
                    continue
                namespace_id = str(namespace.get("id", ""))
                prefix = str(namespace.get("operation_id_prefix", ""))
                owner = str(namespace.get("contract_owner", ""))
                if not namespace_id or not prefix or not owner:
                    errors.append("operation_primitives.json module_ir_ownership namespace missing id, operation_id_prefix, or contract_owner")
                    continue
                namespace_prefixes[namespace_id] = prefix
            prefixes = list(namespace_prefixes.values())
            if len(prefixes) != len(set(prefixes)):
                errors.append("operation_primitives.json module_ir_ownership contains duplicate operation_id_prefix values")
            for prefix in prefixes:
                overlapping = sorted(other for other in prefixes if other != prefix and other.startswith(prefix))
                if overlapping:
                    errors.append(
                        "operation_primitives.json module_ir_ownership contains overlapping prefix "
                        f"{prefix!r}: "
                        + ", ".join(overlapping)
                    )
    extension_boundary = payload.get("primitive_extension_boundary")
    if not isinstance(extension_boundary, dict):
        errors.append("operation_primitives.json must declare primitive_extension_boundary")
    else:
        for field in ("portable_support_rule", "module_extension_rule", "target_support_rule"):
            if not isinstance(extension_boundary.get(field), str) or not str(extension_boundary.get(field)).strip():
                errors.append(f"operation_primitives.json primitive_extension_boundary missing {field}")
        support_matrix = extension_boundary.get("target_support_matrix")
        if not isinstance(support_matrix, list) or not support_matrix:
            errors.append("operation_primitives.json primitive_extension_boundary must declare target_support_matrix")
        else:
            support_targets: dict[str, dict[str, object]] = {}
            for entry in support_matrix:
                if not isinstance(entry, dict):
                    errors.append("operation_primitives.json target_support_matrix entries must be objects")
                    continue
                target = str(entry.get("target", ""))
                status = str(entry.get("status", ""))
                conformance_ref = str(entry.get("conformance_ref", ""))
                unsupported_behavior = str(entry.get("unsupported_behavior", ""))
                if not target or not status or not conformance_ref or not unsupported_behavior:
                    errors.append("operation_primitives.json target_support_matrix entries need target, status, conformance_ref, and unsupported_behavior")
                    continue
                support_targets[target] = entry
                implemented = entry.get("implemented_shared_primitives", [])
                if status == "implemented" and (not isinstance(implemented, list) or not implemented):
                    errors.append(f"operation_primitives.json target {target} must list implemented_shared_primitives")
                if status in {"unsupported-reported", "deferred"} and not unsupported_behavior:
                    errors.append(f"operation_primitives.json target {target} must describe unsupported_behavior")
            for required_target in ("python", "typescript", "bash", "powershell"):
                if required_target not in support_targets:
                    errors.append(f"operation_primitives.json target_support_matrix missing target {required_target}")
    taxonomy = payload.get("primitive_taxonomy")
    tier_2_required_fields = {
        "tier_owner",
        "tier_reason",
        "conformance_ref",
        "migration_path",
        "generic_behavior_audit",
    }
    if not isinstance(taxonomy, dict):
        errors.append("operation_primitives.json must declare primitive_taxonomy")
    else:
        definitions = taxonomy.get("tier_definitions")
        if not isinstance(definitions, list):
            errors.append("operation_primitives.json primitive_taxonomy must declare tier_definitions")
        else:
            defined_tiers = {str(item.get("id")) for item in definitions if isinstance(item, dict)}
            missing_tiers = {
                "tier-1-portable-codegen",
                "tier-2-package-domain",
                "tier-3-deferred-or-out-of-scope",
            } - defined_tiers
            if missing_tiers:
                errors.append("operation_primitives.json primitive_taxonomy missing tier(s): " + ", ".join(sorted(missing_tiers)))
        required_fields = taxonomy.get("tier_2_required_audit_fields")
        if set(required_fields or []) != tier_2_required_fields:
            errors.append(
                "operation_primitives.json primitive_taxonomy tier_2_required_audit_fields must be: "
                + ", ".join(sorted(tier_2_required_fields))
            )
    primitives = payload.get("primitives")
    if not isinstance(primitives, list) or not primitives:
        errors.append("operation_primitives.json must contain at least one primitive")
        return errors
    seen_ids: set[str] = set()
    target_executor_kinds: set[str] = set()
    for index, primitive in enumerate(primitives):
        if not isinstance(primitive, dict):
            errors.append(f"primitive entry {index} must be an object")
            continue
        primitive_id = primitive.get("id")
        if not isinstance(primitive_id, str) or not primitive_id.strip():
            errors.append(f"primitive entry {index} missing id")
            continue
        if primitive_id in seen_ids:
            errors.append(f"duplicate primitive id {primitive_id}")
        seen_ids.add(primitive_id)
        if not isinstance(primitive.get("summary"), str) or not str(primitive.get("summary")).strip():
            errors.append(f"primitive {primitive_id} missing summary")
        if primitive.get("portability") == "target-executor":
            kind = primitive.get("kind")
            if isinstance(kind, str):
                target_executor_kinds.add(kind)
            if not isinstance(primitive.get("semantics"), str) or not str(primitive.get("semantics")).strip():
                errors.append(f"target-executor primitive {primitive_id} must declare semantics")
        taxonomy_tier = primitive.get("taxonomy_tier")
        if taxonomy_tier not in {
            "tier-1-portable-codegen",
            "tier-2-package-domain",
            "tier-3-deferred-or-out-of-scope",
        }:
            errors.append(f"primitive {primitive_id} missing valid taxonomy_tier")
        if primitive.get("portability") == "target-executor" and taxonomy_tier != "tier-1-portable-codegen":
            errors.append(f"target-executor primitive {primitive_id} must be classified tier-1-portable-codegen")
        if primitive.get("portability") in {"domain-runtime", "external-adapter"} and taxonomy_tier == "tier-1-portable-codegen":
            errors.append(f"non-portable primitive {primitive_id} must not be classified tier-1-portable-codegen")
        if taxonomy_tier == "tier-2-package-domain":
            missing_audit = sorted(field for field in tier_2_required_fields if not str(primitive.get(field, "")).strip())
            if missing_audit:
                errors.append(f"tier-2 primitive {primitive_id} missing audit field(s): " + ", ".join(missing_audit))
    required_target_executor_kinds = {
        "filesystem",
        "structured-data",
        "record",
        "validation",
        "rendering",
        "output",
        "check",
    }
    missing_kinds = sorted(required_target_executor_kinds - target_executor_kinds)
    if missing_kinds:
        errors.append("operation_primitives.json target-executor coverage missing kind(s): " + ", ".join(missing_kinds))
    if isinstance(extension_boundary, dict):
        support_matrix = extension_boundary.get("target_support_matrix")
        if isinstance(support_matrix, list):
            implemented_target_primitives = {
                str(primitive_id)
                for entry in support_matrix
                if isinstance(entry, dict) and entry.get("status") == "implemented"
                for primitive_id in entry.get("implemented_shared_primitives", [])
                if isinstance(primitive_id, str)
            }
            schema_backed_primitives = {
                str(primitive["id"])
                for primitive in primitives
                if isinstance(primitive, dict)
                and primitive.get("portability") == "target-executor"
                and isinstance(primitive.get("input_schema_ref"), str)
                and isinstance(primitive.get("output_schema_ref"), str)
            }
            missing_support = sorted(schema_backed_primitives - implemented_target_primitives)
            if missing_support:
                errors.append("operation_primitives.json schema-backed primitives missing implemented target support: " + ", ".join(missing_support))
    operation_step_primitives: set[str] = set()
    for operation_ref in operation_contracts_manifest()["operations"]:
        try:
            operation = operation_manifest(str(operation_ref.get("path", "")))
        except Exception as exc:  # pragma: no cover - checker reports the loaded path
            errors.append(f"operation {operation_ref.get('id')} failed primitive taxonomy load: {exc}")
            continue
        for step in operation.get("steps", []):
            if isinstance(step, dict) and isinstance(step.get("uses"), str):
                operation_step_primitives.add(step["uses"])
        ir_plan = operation.get("ir_plan", {})
        if isinstance(ir_plan, dict):
            fragment_errors: list[str] = []
            for step in _expanded_ir_primitive_steps(ir_plan, operation_id=str(operation_ref.get("id", "")), errors=fragment_errors):
                if isinstance(step, dict) and isinstance(step.get("uses"), str):
                    operation_step_primitives.add(step["uses"])
            errors.extend(fragment_errors)
    missing_classification = sorted(primitive for primitive in operation_step_primitives if primitive not in seen_ids)
    if missing_classification:
        errors.append("operation steps reference primitives missing from operation_primitives.json: " + ", ".join(missing_classification))
    tiered_primitives = {
        str(primitive["id"]): str(primitive.get("taxonomy_tier"))
        for primitive in primitives
        if isinstance(primitive, dict) and isinstance(primitive.get("id"), str)
    }
    unclassified_steps = sorted(
        primitive
        for primitive in operation_step_primitives
        if tiered_primitives.get(primitive)
        not in {"tier-1-portable-codegen", "tier-2-package-domain", "tier-3-deferred-or-out-of-scope"}
    )
    if unclassified_steps:
        errors.append("operation step primitives missing valid taxonomy_tier: " + ", ".join(unclassified_steps))
    return errors


def _module_ir_namespace_prefixes() -> list[str]:
    ownership = operation_primitives_manifest().get("module_ir_ownership", {})
    if not isinstance(ownership, dict):
        return []
    namespaces = ownership.get("namespaces", [])
    if not isinstance(namespaces, list):
        return []
    prefixes: list[str] = []
    for namespace in namespaces:
        if isinstance(namespace, dict) and isinstance(namespace.get("operation_id_prefix"), str):
            prefixes.append(str(namespace["operation_id_prefix"]))
    return prefixes


def _ir_plan_fragments(ir_plan: dict[str, object], *, operation_id: str, errors: list[str]) -> dict[str, list[object]]:
    raw_fragments = ir_plan.get("fragments", [])
    if raw_fragments in (None, []):
        return {}
    if not isinstance(raw_fragments, list):
        errors.append(f"operation {operation_id} ir_plan.fragments must be a list")
        return {}
    fragments: dict[str, list[object]] = {}
    for raw_fragment in raw_fragments:
        if not isinstance(raw_fragment, dict):
            errors.append(f"operation {operation_id} ir_plan fragment must be an object")
            continue
        fragment_id = str(raw_fragment.get("id", "")).strip()
        if not fragment_id:
            errors.append(f"operation {operation_id} ir_plan fragment id is required")
            continue
        if fragment_id in fragments:
            errors.append(f"operation {operation_id} has duplicate ir_plan fragment {fragment_id}")
            continue
        fragment_steps = raw_fragment.get("steps", [])
        if not isinstance(fragment_steps, list) or not fragment_steps:
            errors.append(f"operation {operation_id} ir_plan fragment {fragment_id} must declare steps")
            continue
        fragments[fragment_id] = fragment_steps
    return fragments


def _expand_ir_steps(
    steps: list[object],
    *,
    fragments: dict[str, list[object]],
    operation_id: str,
    errors: list[str],
    stack: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    expanded: list[dict[str, object]] = []
    for step in steps:
        if not isinstance(step, dict):
            errors.append(f"operation {operation_id} ir_plan step must be an object")
            continue
        primitive_id = str(step.get("uses", "")).strip()
        fragment_id = str(step.get("uses_fragment", "")).strip()
        if primitive_id and fragment_id:
            errors.append(f"operation {operation_id} ir_plan step {step.get('id', primitive_id)} cannot declare both uses and uses_fragment")
            continue
        if fragment_id:
            if step.get("arguments") not in (None, {}):
                errors.append(f"operation {operation_id} ir_plan fragment call {step.get('id', fragment_id)} cannot declare arguments")
            if step.get("outputs") not in (None, []):
                errors.append(f"operation {operation_id} ir_plan fragment call {step.get('id', fragment_id)} cannot declare outputs")
            if fragment_id in stack:
                errors.append(f"operation {operation_id} ir_plan fragment cycle: {' -> '.join((*stack, fragment_id))}")
                continue
            fragment_steps = fragments.get(fragment_id)
            if fragment_steps is None:
                errors.append(f"operation {operation_id} ir_plan uses unknown fragment {fragment_id}")
                continue
            expanded.extend(_expand_ir_steps(fragment_steps, fragments=fragments, operation_id=operation_id, errors=errors, stack=(*stack, fragment_id)))
            continue
        if not primitive_id:
            errors.append(f"operation {operation_id} ir_plan step {step.get('id', '<unknown>')} must declare uses or uses_fragment")
            continue
        expanded.append(step)
    return expanded


def _expanded_ir_primitive_steps(ir_plan: dict[str, object], *, operation_id: str, errors: list[str]) -> list[dict[str, object]]:
    steps = ir_plan.get("steps")
    if not isinstance(steps, list):
        return []
    fragments = _ir_plan_fragments(ir_plan, operation_id=operation_id, errors=errors)
    return _expand_ir_steps(steps, fragments=fragments, operation_id=operation_id, errors=errors)


def _interface_operation_refs(interface: dict[str, object], inherited_operation_ref: dict[str, object]) -> list[dict[str, object]]:
    operation_ref = interface.get("operation_ref", inherited_operation_ref)
    refs = [operation_ref] if isinstance(operation_ref, dict) else [inherited_operation_ref]
    subcommands = interface.get("subcommands", [])
    if isinstance(subcommands, list):
        for subcommand in subcommands:
            if isinstance(subcommand, dict):
                refs.extend(_interface_operation_refs(subcommand, refs[-1]))
    return refs


def _command_operation_refs(command: dict[str, object]) -> list[dict[str, object]]:
    operation_ref = command.get("operation_ref", {})
    interface = command.get("interface", {})
    if not isinstance(operation_ref, dict):
        return []
    if not isinstance(interface, dict):
        return [operation_ref]
    return _interface_operation_refs(interface, operation_ref)


def _validate_operation_ir_plans() -> list[str]:
    errors: list[str] = []
    operation_refs = operation_contracts_manifest()["operations"]
    primitive_map = {primitive["id"]: primitive for primitive in operation_primitives_manifest()["primitives"]}
    primitive_refs = set(primitive_map)
    module_prefixes = _module_ir_namespace_prefixes()
    conformance_operation_ids = {contract["operation_id"] for contract in conformance_contracts_manifest()["contracts"]}
    representative_ids: set[str] = set()
    for operation_ref in operation_refs:
        operation = operation_manifest(str(operation_ref.get("path", "")))
        ir_plan = operation.get("ir_plan")
        if ir_plan is None:
            continue
        if not isinstance(ir_plan, dict):
            errors.append(f"operation {operation_ref['id']} ir_plan must be an object")
            continue
        status = ir_plan.get("status")
        operation_id = str(operation.get("id", operation_ref.get("id", "")))
        if status in {"representative", "complete"}:
            representative_ids.add(operation_id)
            if module_prefixes and not any(operation_id.startswith(prefix) for prefix in module_prefixes):
                errors.append(f"operation {operation_id} has {status} IR without declared module_ir_ownership namespace")
            if operation_id not in conformance_operation_ids:
                errors.append(f"operation {operation_id} has representative IR without process conformance")
        steps = ir_plan.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"operation {operation_id} ir_plan must declare steps")
            continue
        for step in _expanded_ir_primitive_steps(ir_plan, operation_id=operation_id, errors=errors):
            primitive_id = step.get("uses")
            if primitive_id not in primitive_refs:
                errors.append(f"operation {operation_id} ir_plan uses unknown primitive {primitive_id}")
                continue
            primitive = primitive_map[primitive_id]
            if status in {"representative", "complete"} and primitive.get("portability") == "target-executor":
                for field in ("input_schema_ref", "output_schema_ref"):
                    schema_ref = primitive.get(field)
                    if not isinstance(schema_ref, str) or not schema_ref.strip():
                        errors.append(f"representative primitive {primitive_id} must declare {field}")
                        continue
                    schema_path = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / schema_ref
                    if not schema_path.is_file():
                        errors.append(f"representative primitive {primitive_id} references missing {field} {schema_ref}")
    if "memory.list-files.report" not in representative_ids:
        errors.append("memory.list-files.report must remain the #930 representative operation IR proof")
    else:
        operation = operation_manifest("operations/memory.list-files.report.json")
        plan_steps = operation.get("ir_plan", {}).get("steps", [])
        used = {step.get("uses") for step in plan_steps if isinstance(step, dict)}
        required = {"path.target_root.resolve", "filesystem.glob", "payload.assemble", "output.emit"}
        missing = sorted(required - used)
        if missing:
            errors.append("memory.list-files.report representative IR missing primitive(s): " + ", ".join(missing))
    return errors


def _validate_module_operation_contract_locations() -> list[str]:
    errors: list[str] = []
    root_operations = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "operations"
    misplaced = sorted(path.name for prefix in ("planning.", "memory.", "verification.") for path in root_operations.glob(f"{prefix}*.json"))
    if misplaced:
        errors.append("module-owned operation contracts must not live under root workspace operations: " + ", ".join(misplaced))

    module_roots = {
        "planning.": REPO_ROOT / "packages" / "planning" / "src" / "repo_planning_bootstrap" / "contracts" / "operations",
        "memory.": REPO_ROOT / "packages" / "memory" / "src" / "repo_memory_bootstrap" / "contracts" / "operations",
        "verification.": REPO_ROOT
        / "packages"
        / "verification"
        / "src"
        / "repo_verification_bootstrap"
        / "contracts"
        / "operations",
    }
    for operation_ref in operation_contracts_manifest()["operations"]:
        operation_id = str(operation_ref.get("id", ""))
        operation_file = Path(str(operation_ref.get("path", ""))).name
        for prefix, module_root in module_roots.items():
            if operation_id.startswith(prefix) and not (module_root / operation_file).is_file():
                relative_root = module_root.relative_to(REPO_ROOT).as_posix()
                errors.append(f"module-owned operation {operation_id} must live under {relative_root}")
    return errors


def _validate_conformance_registry(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "agentic-workspace/conformance-contracts/v1":
        errors.append("conformance_contracts.json has unexpected schema_version")
    contracts = payload.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        errors.append("conformance_contracts.json must contain at least one contract")
        return errors
    operation_ids = {operation_ref["id"] for operation_ref in operation_contracts_manifest()["operations"]}
    seen_ids: set[str] = set()
    for index, contract_ref in enumerate(contracts):
        if not isinstance(contract_ref, dict):
            errors.append(f"conformance registry entry {index} must be an object")
            continue
        for field in ("id", "operation_id", "path", "adapter_kind"):
            if not isinstance(contract_ref.get(field), str) or not str(contract_ref.get(field)).strip():
                errors.append(f"conformance registry entry {index} missing string field {field}")
        contract_id = str(contract_ref.get("id", ""))
        if contract_id in seen_ids:
            errors.append(f"duplicate conformance contract id {contract_id}")
        seen_ids.add(contract_id)
        if contract_ref.get("operation_id") not in operation_ids:
            errors.append(f"conformance contract {contract_id} references unknown operation {contract_ref.get('operation_id')}")
        if contract_ref.get("adapter_kind") != "process":
            errors.append(f"conformance contract {contract_id} has unsupported adapter kind {contract_ref.get('adapter_kind')}")
        path = str(contract_ref.get("path", ""))
        try:
            contract = conformance_contract_manifest(path)
        except Exception as exc:  # pragma: no cover - error text is surfaced by the checker
            errors.append(f"conformance contract {contract_id} failed schema validation: {exc}")
            continue
        if contract.get("id") != contract_id:
            errors.append(f"conformance contract {contract_id} path payload id drifted")
        if contract.get("operation_id") != contract_ref.get("operation_id"):
            errors.append(f"conformance contract {contract_id} operation_id drifted from registry")
        if contract.get("adapter", {}).get("kind") != contract_ref.get("adapter_kind"):
            errors.append(f"conformance contract {contract_id} adapter kind drifted from registry")
    return errors


def _validate_command_adapter_generation(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "agentic-workspace/command-adapter-generation/v1":
        errors.append("command_adapter_generation.json has unexpected schema_version")
        return errors
    command_manifest = cli_commands_manifest()
    known_commands = {command["name"]: command for command in command_manifest["commands"]}
    operation_refs = {operation_ref["id"]: operation_ref for operation_ref in operation_contracts_manifest()["operations"]}
    primitives = {primitive["id"] for primitive in operation_primitives_manifest()["primitives"]}
    conformance_refs = {contract_ref["id"]: contract_ref for contract_ref in conformance_contracts_manifest()["contracts"]}
    seen_ids: set[str] = set()
    adapters = payload.get("adapters", [])
    if not isinstance(adapters, list):
        return ["command_adapter_generation.json adapters must be a list"]
    projection_requirements = payload.get("projection_requirements", {})
    if not isinstance(projection_requirements, dict):
        errors.append("command_adapter_generation.json projection_requirements must be an object")
    else:
        universal_truth = projection_requirements.get("universal_command_truth", [])
        adapter_rendering = projection_requirements.get("adapter_specific_rendering", [])
        target_kinds = projection_requirements.get("future_target_kinds", [])
        if not isinstance(universal_truth, list) or not isinstance(adapter_rendering, list) or not isinstance(target_kinds, list):
            errors.append("command_adapter_generation.json projection_requirements fields must be lists")
        else:
            universal_text = " ".join(str(item).lower() for item in universal_truth)
            adapter_text = " ".join(str(item).lower() for item in adapter_rendering)
            required_universal = {
                "operation id and registry path",
                "runtime primitive sequence",
                "input and output schema refs",
                "read/write/destructive/idempotence effects",
                "conformance refs",
            }
            missing_universal = sorted(required_universal - {str(item) for item in universal_truth})
            if missing_universal:
                errors.append(
                    "command_adapter_generation.json projection_requirements missing universal truth: "
                    + ", ".join(missing_universal)
                )
            if "python" in universal_text or "argparse" in universal_text:
                errors.append("command_adapter_generation.json universal command truth contains target-specific implementation detail")
            if "help text layout" not in {str(item) for item in adapter_rendering}:
                errors.append("command_adapter_generation.json adapter rendering requirements must include help text layout")
            if "argparse" in adapter_text:
                errors.append("command_adapter_generation.json adapter rendering requirements should not name Python argparse")
            seen_target_kinds = {str(target.get("kind", "")) for target in target_kinds if isinstance(target, dict)}
            expected_target_kinds = {
                "process-cli",
                "npm-cli",
                "posix-shell",
                "powershell",
                "binary",
                "local-mcp-tool",
                "generated-skill",
            }
            missing_target_kinds = sorted(expected_target_kinds - seen_target_kinds)
            if missing_target_kinds:
                errors.append(
                    "command_adapter_generation.json projection_requirements missing target kind(s): "
                    + ", ".join(missing_target_kinds)
                )
    for index, raw_adapter in enumerate(adapters):
        if not isinstance(raw_adapter, dict):
            errors.append(f"adapter entry {index} must be an object")
            continue
        adapter_id = str(raw_adapter.get("id", ""))
        if adapter_id in seen_ids:
            errors.append(f"duplicate command adapter id {adapter_id}")
        seen_ids.add(adapter_id)
        command = raw_adapter.get("command", {})
        operation_ref = raw_adapter.get("operation_ref", {})
        runtime_binding = raw_adapter.get("runtime_binding", {})
        if not isinstance(command, dict) or not isinstance(operation_ref, dict) or not isinstance(runtime_binding, dict):
            errors.append(f"command adapter {adapter_id} has malformed command, operation_ref, or runtime_binding")
            continue
        command_name = str(command.get("name", ""))
        command_program = str(command.get("program", ""))
        if command_program == command_manifest.get("program") and command.get("command_manifest") != "cli_commands.json":
            errors.append(f"command adapter {adapter_id} root command must use cli_commands.json")
        if command_program == command_manifest.get("program") and command_manifest.get("program") != command.get("program"):
            errors.append(f"command adapter {adapter_id} program drifted from cli_commands.json")
        if command_program == command_manifest.get("program") and command_name not in known_commands:
            errors.append(f"command adapter {adapter_id} references unknown command {command_name}")
        if command_program != command_manifest.get("program") and not str(command.get("command_manifest", "")).startswith("package:"):
            errors.append(f"command adapter {adapter_id} package command must use a package command manifest marker")
        operation_id = str(operation_ref.get("id", ""))
        operation_registry_ref = operation_refs.get(operation_id)
        if operation_registry_ref is None:
            errors.append(f"command adapter {adapter_id} references unknown operation {operation_id}")
            continue
        if operation_ref.get("path") != operation_registry_ref.get("path"):
            errors.append(f"command adapter {adapter_id} operation path drifted from operation registry")
        operation = operation_manifest(str(operation_ref.get("path", "")))
        operation_surface = operation.get("command_surface", {})
        if not isinstance(operation_surface, dict) or not (_adapter_command_surfaces(command) & _operation_command_surfaces(operation_surface)):
            errors.append(f"command adapter {adapter_id} command does not match operation command_surface")
        if raw_adapter.get("effect_hints") != operation.get("effects"):
            errors.append(f"command adapter {adapter_id} effect_hints drifted from operation effects")
        operation_primitives = [step["uses"] for step in operation.get("steps", [])]
        adapter_primitives = list(runtime_binding.get("primitive_refs", []))
        if adapter_primitives != operation_primitives:
            errors.append(f"command adapter {adapter_id} primitive sequence drifted from operation steps")
        missing_primitives = [primitive for primitive in adapter_primitives if primitive not in primitives]
        if missing_primitives:
            errors.append(f"command adapter {adapter_id} references unknown primitive(s): {', '.join(missing_primitives)}")
        for schema_ref in raw_adapter.get("schemas", {}).get("input", []) + raw_adapter.get("schemas", {}).get("output", []):
            try:
                contract_schema(str(schema_ref))
            except FileNotFoundError:
                errors.append(f"command adapter {adapter_id} references unknown schema {schema_ref}")
        for conformance_ref in raw_adapter.get("conformance_refs", []):
            conformance = conformance_refs.get(str(conformance_ref))
            if conformance is None:
                errors.append(f"command adapter {adapter_id} references unknown conformance contract {conformance_ref}")
                continue
            if conformance.get("operation_id") != operation_id:
                conformance_operation_ref = operation_refs.get(str(conformance.get("operation_id", "")))
                conformance_operation = (
                    operation_manifest(str(conformance_operation_ref.get("path", ""))) if isinstance(conformance_operation_ref, dict) else {}
                )
                conformance_surface = conformance_operation.get("command_surface", {}) if isinstance(conformance_operation, dict) else {}
                if isinstance(conformance_surface, dict) and _adapter_command_surfaces(command) & _operation_command_surfaces(conformance_surface):
                    continue
                errors.append(f"command adapter {adapter_id} conformance ref {conformance_ref} targets a different operation")
    return errors


def _validate_command_package_ir(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "agentic-workspace/command-package-ir/v1":
        return ["command_package_ir.json has unexpected schema_version"]
    adapters = {adapter["id"]: adapter for adapter in command_adapter_generation_manifest()["adapters"]}
    operations = {operation["id"]: operation for operation in operation_contracts_manifest()["operations"]}
    conformance_refs = {contract["id"] for contract in conformance_contracts_manifest()["contracts"]}
    primitive_entries = {
        str(primitive["id"]): primitive
        for primitive in operation_primitives_manifest()["primitives"]
        if isinstance(primitive, dict) and primitive.get("id")
    }
    primitive_refs = set(primitive_entries)
    packages = payload.get("packages", [])
    if not isinstance(packages, list):
        return ["command_package_ir.json packages must be a list"]
    seen_adapter_ids: set[str] = set()
    for package_index, package in enumerate(packages):
        if not isinstance(package, dict):
            errors.append(f"command_package_ir package {package_index} must be an object")
            continue
        program = str(package.get("program", ""))
        targets = package.get("targets", [])
        commands = package.get("commands", [])
        if not isinstance(targets, list) or not isinstance(commands, list):
            errors.append(f"command_package_ir package {program} targets and commands must be lists")
            continue
        target_kinds = {str(target.get("kind", "")) for target in targets if isinstance(target, dict)}
        if "python" not in target_kinds:
            errors.append(f"command_package_ir package {program} must declare a python target")
        if "typescript" not in target_kinds:
            errors.append(f"command_package_ir package {program} must declare a typescript target")
        python_binding = package.get("python_runtime_binding", {})
        if isinstance(python_binding, dict):
            operation_executor = python_binding.get("operation_executor", {})
            if isinstance(operation_executor, dict):
                handlers = operation_executor.get("handlers", [])
                if isinstance(handlers, list):
                    package_runtime_primitives = {
                        str(ref)
                        for command in commands
                        if isinstance(command, dict) and isinstance(command.get("runtime_binding"), dict)
                        for ref in command["runtime_binding"].get("primitive_refs", [])
                    }
                    for handler in handlers:
                        if not isinstance(handler, dict):
                            continue
                        if handler.get("handler") == "function_call":
                            primitive = str(handler.get("primitive", ""))
                            primitive_entry = primitive_entries.get(primitive, {})
                            if primitive not in primitive_entries:
                                errors.append(
                                    f"command_package_ir package {program} primitive {primitive} uses function_call without "
                                    "a declared domain-runtime primitive"
                                )
                            if primitive == "python.function.call" or primitive_entry.get("portability") == "target-executor":
                                errors.append(
                                    f"command_package_ir package {program} primitive {primitive} uses direct function_call; "
                                    "declare a named domain-runtime primitive in operation IR instead"
                                )
                            if primitive not in package_runtime_primitives:
                                errors.append(
                                    f"command_package_ir package {program} primitive {primitive} has a function_call handler "
                                    "but no generated command references that primitive"
                                )
                            if primitive_entry.get("taxonomy_tier") == "tier-1-portable-codegen":
                                errors.append(
                                    f"command_package_ir package {program} primitive {primitive} cannot use function_call for "
                                    "tier-1 portable codegen behavior"
                                )
        for command in commands:
            if not isinstance(command, dict):
                errors.append(f"command_package_ir package {program} command entry must be an object")
                continue
            adapter_id = str(command.get("adapter_id", ""))
            seen_adapter_ids.add(adapter_id)
            adapter = adapters.get(adapter_id)
            if adapter is None:
                errors.append(f"command_package_ir command {adapter_id} does not reference a known generated adapter")
                continue
            if adapter["command"]["program"] != program:
                errors.append(f"command_package_ir command {adapter_id} program drifted from command_adapter_generation.json")
            runtime_binding = command.get("runtime_binding", {})
            if not isinstance(runtime_binding, dict):
                errors.append(f"command_package_ir command {adapter_id} has malformed operation or runtime binding")
                continue
            for operation_ref in _command_operation_refs(command):
                operation_id = str(operation_ref.get("id", ""))
                operation = operations.get(operation_id)
                if operation is None:
                    errors.append(f"command_package_ir command {adapter_id} references unknown operation {operation_id}")
                elif operation.get("path") != operation_ref.get("path"):
                    errors.append(f"command_package_ir command {adapter_id} operation path drifted from registry")
            expected_operation_ref = {"id": adapter["operation_ref"]["id"], "path": adapter["operation_ref"]["path"]}
            top_level_operation_ref = command.get("operation_ref", {})
            if top_level_operation_ref != expected_operation_ref:
                errors.append(f"command_package_ir command {adapter_id} operation ref drifted from command_adapter_generation.json")
            if runtime_binding != adapter["runtime_binding"]:
                errors.append(f"command_package_ir command {adapter_id} runtime binding drifted from command_adapter_generation.json")
            unknown_primitives = sorted(set(runtime_binding.get("primitive_refs", [])) - primitive_refs)
            if unknown_primitives:
                errors.append(
                    f"command_package_ir command {adapter_id} references unknown primitive(s): "
                    + ", ".join(str(item) for item in unknown_primitives)
                )
            if command.get("effect_hints") != adapter["effect_hints"]:
                errors.append(f"command_package_ir command {adapter_id} effect hints drifted from command_adapter_generation.json")
            if command.get("schemas") != adapter["schemas"]:
                errors.append(f"command_package_ir command {adapter_id} schema refs drifted from command_adapter_generation.json")
            command_conformance_refs = command.get("conformance_refs", [])
            if command_conformance_refs != adapter["conformance_refs"]:
                errors.append(f"command_package_ir command {adapter_id} conformance refs drifted from command_adapter_generation.json")
            unknown_conformance = sorted(set(command_conformance_refs) - conformance_refs) if isinstance(command_conformance_refs, list) else []
            if unknown_conformance:
                errors.append(
                    f"command_package_ir command {adapter_id} references unknown conformance ref(s): "
                    + ", ".join(str(item) for item in unknown_conformance)
                )
    generated_adapter_ids = {adapter["id"] for adapter in adapters.values() if adapter.get("status") == "generated"}
    missing_generated = sorted(generated_adapter_ids - seen_adapter_ids)
    if missing_generated:
        errors.append("command_package_ir.json missing generated adapter(s): " + ", ".join(missing_generated))
    return errors


def _validate_operation_conformance_test_ir(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "agentic-workspace/operation-conformance-test-ir/v1":
        return ["operation_conformance_test_ir.json has unexpected schema_version"]
    package_ir = command_package_ir_manifest()
    packages = {str(package.get("id", "")): package for package in package_ir.get("packages", []) if isinstance(package, dict)}
    conformance_refs = {str(contract["id"]): contract for contract in conformance_contracts_manifest()["contracts"]}
    target_matrix = {
        str(target.get("kind", "")): str(target.get("status", ""))
        for target in payload.get("target_matrix", [])
        if isinstance(target, dict)
    }
    required_classes = {"success", "error", "cross-target-parity"}
    seen_classes = {
        str(case.get("behavioral_class", ""))
        for case in payload.get("initial_cases", [])
        if isinstance(case, dict)
    }
    missing_classes = sorted(required_classes - seen_classes)
    if missing_classes:
        errors.append("operation_conformance_test_ir.json missing behavioral class(es): " + ", ".join(missing_classes))
    source_role = payload.get("source_role", {})
    if not isinstance(source_role, dict) or source_role.get("ordinary_startup_visibility") != "not-startup-workflow":
        errors.append("operation_conformance_test_ir.json must stay out of ordinary startup workflow visibility")
    migration_policy = payload.get("migration_policy", {})
    if not isinstance(migration_policy, dict):
        errors.append("operation_conformance_test_ir.json migration_policy must be an object")
    else:
        do_not_preserve = " ".join(str(item).lower() for item in migration_policy.get("do_not_preserve", []))
        composition_rule = str(migration_policy.get("composition_rule", "")).lower()
        if "one-for-one" not in do_not_preserve or "regression-test bulk" not in do_not_preserve:
            errors.append("operation_conformance_test_ir.json must reject one-for-one regression-test bulk preservation")
        if "primitive behavior is tested once" not in composition_rule or "composite operation cases assume" not in composition_rule:
            errors.append("operation_conformance_test_ir.json must record compositional primitive reuse for composite cases")
    adapter_model = payload.get("adapter_model", {})
    if not isinstance(adapter_model, dict):
        errors.append("operation_conformance_test_ir.json adapter_model must be an object")
    else:
        adapter_kinds = {
            str(adapter.get("id", "")): adapter
            for adapter in adapter_model.get("adapter_kinds", [])
            if isinstance(adapter, dict)
        }
        for required_adapter in ("python.function", "typescript.function", "cli.process"):
            if required_adapter not in adapter_kinds:
                errors.append(f"operation_conformance_test_ir.json missing adapter kind {required_adapter}")
        cli_adapter = adapter_kinds.get("cli.process", {})
        if isinstance(cli_adapter, dict) and cli_adapter.get("default_for_semantic_proof") is not False:
            errors.append("operation_conformance_test_ir.json cli.process must not be the default semantic proof adapter")
    proof_output = payload.get("proof_output", {})
    if not isinstance(proof_output, dict):
        errors.append("operation_conformance_test_ir.json proof_output must be an object")
    else:
        states = set(proof_output.get("states", []))
        if {"pass", "fail", "stale", "unavailable", "skipped"} - states:
            errors.append("operation_conformance_test_ir.json proof_output must include pass/fail/stale/unavailable/skipped states")
    seen_case_ids: set[str] = set()
    for case in payload.get("initial_cases", []):
        if not isinstance(case, dict):
            errors.append("operation_conformance_test_ir.json initial_cases entries must be objects")
            continue
        case_id = str(case.get("id", ""))
        if case_id in seen_case_ids:
            errors.append(f"operation_conformance_test_ir.json duplicate case id {case_id}")
        seen_case_ids.add(case_id)
        operation_ref = case.get("operation_ref", {})
        if not isinstance(operation_ref, dict):
            errors.append(f"operation_conformance_test_ir.json case {case_id} has malformed operation_ref")
            continue
        package_id = str(operation_ref.get("package_id", ""))
        operation_id = str(operation_ref.get("operation_id", ""))
        package = packages.get(package_id)
        if package is None:
            errors.append(f"operation_conformance_test_ir.json case {case_id} references unknown package {package_id}")
            continue
        commands = {str(command.get("adapter_id", "")): command for command in package.get("commands", []) if isinstance(command, dict)}
        matching_commands = [
            command
            for command in commands.values()
            if isinstance(command.get("operation_ref"), dict) and command["operation_ref"].get("id") == operation_id
        ]
        if not matching_commands:
            errors.append(f"operation_conformance_test_ir.json case {case_id} references unknown operation {operation_id}")
        if operation_ref.get("operation_path"):
            matching_paths = {
                str(command.get("operation_ref", {}).get("path", ""))
                for command in matching_commands
                if isinstance(command.get("operation_ref"), dict)
            }
            if str(operation_ref.get("operation_path")) not in matching_paths:
                errors.append(f"operation_conformance_test_ir.json case {case_id} operation_path drifted from command_package_ir.json")
        conformance_ref = operation_ref.get("conformance_ref")
        if conformance_ref is not None:
            conformance = conformance_refs.get(str(conformance_ref))
            if conformance is None:
                errors.append(f"operation_conformance_test_ir.json case {case_id} references unknown conformance {conformance_ref}")
            elif conformance.get("operation_id") != operation_id:
                errors.append(f"operation_conformance_test_ir.json case {case_id} conformance operation drifted from operation_ref")
        artifacts = case.get("artifacts", [])
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"operation_conformance_test_ir.json case {case_id} must declare artifact refs")
            artifacts = []
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                errors.append(f"operation_conformance_test_ir.json case {case_id} has malformed artifact ref")
                continue
            adapter_id = str(artifact.get("adapter_id", ""))
            if adapter_id == "cli.process" and artifact.get("proof_role") != "wrapper-smoke":
                errors.append(f"operation_conformance_test_ir.json case {case_id} cli.process artifacts must declare wrapper-smoke proof_role")
            wrapper_refs = {str(ref) for ref in artifact.get("wrapper_refs", [])}
            unknown_wrappers = sorted(wrapper_refs - set(commands))
            if unknown_wrappers:
                errors.append(f"operation_conformance_test_ir.json case {case_id} references unknown wrapper(s): {', '.join(unknown_wrappers)}")
        case_targets = {str(target.get("kind", "")) for target in case.get("targets", []) if isinstance(target, dict)}
        unknown_targets = sorted(case_targets - set(target_matrix))
        if unknown_targets:
            errors.append(f"operation_conformance_test_ir.json case {case_id} references unknown target(s): {', '.join(unknown_targets)}")
        required_targets = {kind for kind, status in target_matrix.items() if status == "required"}
        if case.get("behavioral_class") == "cross-target-parity" and not required_targets <= case_targets:
            errors.append(f"operation_conformance_test_ir.json parity case {case_id} must cover all required targets")
        expected = case.get("expected", {})
        if case.get("behavioral_class") == "error" and isinstance(expected, dict) and int(expected.get("exit_code", 0)) == 0:
            errors.append(f"operation_conformance_test_ir.json error case {case_id} must expect a non-zero exit")
        if case.get("behavioral_class") == "cross-target-parity" and isinstance(expected, dict) and "parity" not in expected:
            errors.append(f"operation_conformance_test_ir.json parity case {case_id} must declare parity comparison")
        composition = case.get("composition", {})
        if isinstance(composition, dict) and case.get("behavioral_class") == "cross-target-parity":
            if not composition.get("assumes_primitives"):
                errors.append(f"operation_conformance_test_ir.json parity case {case_id} must declare assumed primitives")
        migration = case.get("migration", {})
        if not isinstance(migration, dict) or not migration.get("rationale"):
            errors.append(f"operation_conformance_test_ir.json case {case_id} must declare migration rationale")
    return errors


def _validate_operation_artifact_registry(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "agentic-workspace/operation-artifact-registry/v1":
        return ["operation_artifact_registry.json has unexpected schema_version"]
    conformance_ir = operation_conformance_test_ir_manifest()
    case_by_id = {
        str(case.get("id", "")): case
        for case in conformance_ir.get("initial_cases", [])
        if isinstance(case, dict)
    }
    package_ir = command_package_ir_manifest()
    packages = {str(package.get("id", "")): package for package in package_ir.get("packages", []) if isinstance(package, dict)}
    seen_artifacts: set[str] = set()
    artifacts_by_case: dict[str, set[str]] = {}
    for artifact in payload.get("artifacts", []):
        if not isinstance(artifact, dict):
            errors.append("operation_artifact_registry.json artifacts entries must be objects")
            continue
        artifact_id = str(artifact.get("artifact_id", ""))
        if artifact_id in seen_artifacts:
            errors.append(f"operation_artifact_registry.json duplicate artifact id {artifact_id}")
        seen_artifacts.add(artifact_id)
        package_id = str(artifact.get("package_id", ""))
        operation_id = str(artifact.get("operation_id", ""))
        adapter_id = str(artifact.get("adapter_id", ""))
        proof_role = str(artifact.get("proof_role", ""))
        package = packages.get(package_id)
        if package is None:
            errors.append(f"operation_artifact_registry.json artifact {artifact_id} references unknown package {package_id}")
            continue
        commands = {str(command.get("adapter_id", "")): command for command in package.get("commands", []) if isinstance(command, dict)}
        matching_commands = [
            command
            for command in commands.values()
            if isinstance(command.get("operation_ref"), dict) and command["operation_ref"].get("id") == operation_id
        ]
        if not matching_commands:
            errors.append(f"operation_artifact_registry.json artifact {artifact_id} references unknown operation {operation_id}")
        wrapper_refs = {str(ref) for ref in artifact.get("wrapper_refs", [])}
        unknown_wrappers = sorted(wrapper_refs - set(commands))
        if unknown_wrappers:
            errors.append(f"operation_artifact_registry.json artifact {artifact_id} references unknown wrapper(s): {', '.join(unknown_wrappers)}")
        if adapter_id == "cli.process" and proof_role != "wrapper-smoke":
            errors.append(f"operation_artifact_registry.json artifact {artifact_id} cli.process must be wrapper-smoke")
        if adapter_id.endswith(".function") and proof_role != "operation-conformance":
            errors.append(f"operation_artifact_registry.json artifact {artifact_id} direct function adapters must be operation-conformance")
        if adapter_id.endswith(".function") and not artifact.get("symbol"):
            errors.append(f"operation_artifact_registry.json artifact {artifact_id} direct function adapters must declare symbol")
        for case_id in artifact.get("case_ids", []):
            case_id = str(case_id)
            case = case_by_id.get(case_id)
            if case is None:
                errors.append(f"operation_artifact_registry.json artifact {artifact_id} references unknown case {case_id}")
                continue
            operation_ref = case.get("operation_ref", {})
            if isinstance(operation_ref, dict) and operation_ref.get("operation_id") != operation_id:
                errors.append(f"operation_artifact_registry.json artifact {artifact_id} operation drifted from case {case_id}")
            artifacts_by_case.setdefault(case_id, set()).add(artifact_id)
    for case_id, case in case_by_id.items():
        declared_artifacts = {
            str(artifact.get("artifact_id", ""))
            for artifact in case.get("artifacts", [])
            if isinstance(artifact, dict)
        }
        missing_from_registry = sorted(declared_artifacts - seen_artifacts)
        if missing_from_registry:
            errors.append(f"operation_artifact_registry.json missing artifact(s) declared by case {case_id}: {', '.join(missing_from_registry)}")
        if not artifacts_by_case.get(case_id):
            errors.append(f"operation_artifact_registry.json no artifacts route to case {case_id}")
    proof_routing = payload.get("proof_routing", {})
    if not isinstance(proof_routing, dict):
        errors.append("operation_artifact_registry.json proof_routing must be an object")
    else:
        changed_surfaces = {
            str(route.get("changed_surface", ""))
            for route in proof_routing.get("routes", [])
            if isinstance(route, dict)
        }
        required_surfaces = {"operation-contract", "implementation-artifact", "implementation-adapter", "cli-wrapper", "schema", "generated-artifact-freshness"}
        missing_surfaces = sorted(required_surfaces - changed_surfaces)
        if missing_surfaces:
            errors.append("operation_artifact_registry.json proof_routing missing surface(s): " + ", ".join(missing_surfaces))
        rule = str(proof_routing.get("rule", "")).lower()
        if "do not use wrapper execution as the default" not in rule:
            errors.append("operation_artifact_registry.json proof_routing must reject wrapper-default semantic proof")
    return errors


def _validate_generated_behavior_stratification(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "agentic-workspace/generated-behavior-stratification/v1":
        return ["generated_behavior_stratification.json has unexpected schema_version"]
    expected_layers = [
        "primitive",
        "operation-ir",
        "generated-implementation",
        "target-extension",
        "wrapper-adapter",
        "conformance-case",
        "ordinary-test-boundary",
    ]
    layers = payload.get("layers", [])
    layer_ids = [str(layer.get("id", "")) for layer in layers if isinstance(layer, dict)]
    if layer_ids != expected_layers:
        errors.append("generated_behavior_stratification.json layer order drifted from #1476 closure model")
    layers_by_id = {str(layer.get("id", "")): layer for layer in layers if isinstance(layer, dict)}
    generated_layer = layers_by_id.get("generated-implementation", {})
    if "do not hand-edit generated" not in str(generated_layer.get("direct_edit_policy", "")).lower():
        errors.append("generated_behavior_stratification.json generated layer must reject direct generated behavior edits")
    wrapper_layer = layers_by_id.get("wrapper-adapter", {})
    if "default semantic proof" not in str(wrapper_layer.get("direct_edit_policy", "")).lower():
        errors.append("generated_behavior_stratification.json wrapper layer must reject wrapper-default semantic proof")
    ordinary_layer = layers_by_id.get("ordinary-test-boundary", {})
    if "owner" not in str(ordinary_layer.get("allowed_handwritten_tests", "")).lower():
        errors.append("generated_behavior_stratification.json ordinary-test layer must require owner-bearing retained tests")
    retained = payload.get("retained_hand_owned_boundaries", [])
    required_boundary_fields = {
        "owner_surface",
        "proof_route",
        "keep_reason",
        "conversion_or_retirement_condition",
        "accepted_direct_edit_reasons",
        "stale_when",
    }
    for boundary in retained:
        if not isinstance(boundary, dict):
            errors.append("generated_behavior_stratification.json retained boundaries must be objects")
            continue
        missing = sorted(field for field in required_boundary_fields if not boundary.get(field))
        if missing:
            errors.append(
                f"generated_behavior_stratification.json retained boundary {boundary.get('id', '<unknown>')} missing: "
                + ", ".join(missing)
            )
    boundary_ids = {str(boundary.get("id", "")) for boundary in retained if isinstance(boundary, dict)}
    if not {"package-domain-runtime-primitives", "wrapper-boundary-tests", "aw-proof-routing-and-integration-tests"} <= boundary_ids:
        errors.append("generated_behavior_stratification.json missing required retained boundary records")
    retained_groups = payload.get("retained_ordinary_test_groups", [])
    required_group_fields = {
        "test_surface",
        "owner",
        "retained_boundary_ref",
        "proof_route",
        "keep_reason",
        "future_conversion_condition",
        "durable_boundary_rationale",
    }
    required_group_ids = {
        "generated-command-package-proof-runner",
        "contract-tooling-source-of-truth",
        "workspace-proof-generated-packages-cli",
        "generated-tool-conformance",
        "command-generation-dependency-integration",
        "installed-product-generated-surface-routing",
    }
    group_ids: set[str] = set()
    for group in retained_groups:
        if not isinstance(group, dict):
            errors.append("generated_behavior_stratification.json retained ordinary test groups must be objects")
            continue
        group_id = str(group.get("id", ""))
        group_ids.add(group_id)
        missing = sorted(field for field in required_group_fields if not group.get(field))
        if missing:
            errors.append(
                f"generated_behavior_stratification.json retained ordinary test group {group.get('id', '<unknown>')} missing: "
                + ", ".join(missing)
            )
        boundary_ref = str(group.get("retained_boundary_ref", ""))
        if boundary_ref not in boundary_ids:
            errors.append(
                f"generated_behavior_stratification.json retained ordinary test group {group_id} references unknown retained boundary {boundary_ref}"
            )
        combined_rationale = " ".join(
            str(group.get(field, ""))
            for field in ("keep_reason", "future_conversion_condition", "durable_boundary_rationale")
        ).lower()
        if "command-generation" not in combined_rationale and "operation conformance" not in combined_rationale:
            errors.append(
                f"generated_behavior_stratification.json retained ordinary test group {group_id} must name conversion ownership"
            )
    missing_groups = sorted(required_group_ids - group_ids)
    if missing_groups:
        errors.append("generated_behavior_stratification.json missing retained ordinary test group(s): " + ", ".join(missing_groups))
    closure_inventory = payload.get("parent_closure_inventory", {})
    if not isinstance(closure_inventory, dict):
        errors.append("generated_behavior_stratification.json parent_closure_inventory must be an object")
        return errors
    required_requirement_ids = {
        "checked-stratification-contract",
        "generated-direct-operation-callables",
        "target-extension-consumed",
        "ir-backed-conformance-cases",
        "wrapper-demotion",
        "ordinary-test-boundary-inventory",
        "generated-code-and-test-bypass-guardrails",
    }
    requirements = closure_inventory.get("final_state_requirements", [])
    requirement_ids: set[str] = set()
    for requirement in requirements:
        if not isinstance(requirement, dict):
            errors.append("generated_behavior_stratification.json final_state_requirements must contain objects")
            continue
        requirement_id = str(requirement.get("id", ""))
        requirement_ids.add(requirement_id)
        if requirement.get("status") not in {"satisfied", "owner-approved-rejected"}:
            errors.append(f"generated_behavior_stratification.json final requirement {requirement_id} is not closure-ready")
        for field in ("intent_served", "proof_route"):
            if not requirement.get(field):
                errors.append(f"generated_behavior_stratification.json final requirement {requirement_id} missing {field}")
        if not requirement.get("evidence_refs"):
            errors.append(f"generated_behavior_stratification.json final requirement {requirement_id} missing evidence_refs")
    missing_requirements = sorted(required_requirement_ids - requirement_ids)
    if missing_requirements:
        errors.append("generated_behavior_stratification.json missing final requirement(s): " + ", ".join(missing_requirements))
    required_guardrail_ids = {
        "direct-generated-edit-bypass",
        "ordinary-regression-bypass",
        "target-product-semantics-bypass",
        "representative-slice-parent-closure-bypass",
    }
    guardrails = closure_inventory.get("bypass_guardrails", [])
    guardrail_ids: set[str] = set()
    for guardrail in guardrails:
        if not isinstance(guardrail, dict):
            errors.append("generated_behavior_stratification.json bypass_guardrails must contain objects")
            continue
        guardrail_id = str(guardrail.get("id", ""))
        guardrail_ids.add(guardrail_id)
        for field in ("prevents", "check_surface", "proof_route"):
            if not guardrail.get(field):
                errors.append(f"generated_behavior_stratification.json bypass guardrail {guardrail_id} missing {field}")
        if not guardrail.get("fails_when"):
            errors.append(f"generated_behavior_stratification.json bypass guardrail {guardrail_id} missing fails_when")
    missing_guardrails = sorted(required_guardrail_ids - guardrail_ids)
    if missing_guardrails:
        errors.append("generated_behavior_stratification.json missing bypass guardrail(s): " + ", ".join(missing_guardrails))
    status = closure_inventory.get("status")
    unresolved = closure_inventory.get("unresolved", [])
    if status == "ready-to-close-parent" and unresolved:
        errors.append("generated_behavior_stratification.json cannot be ready-to-close-parent with unresolved parent gaps")
    if status != "ready-to-close-parent":
        errors.append("generated_behavior_stratification.json parent closure inventory is not ready-to-close-parent")
    if not closure_inventory.get("closure_statement"):
        errors.append("generated_behavior_stratification.json parent closure inventory must include closure_statement")
    return errors


def _validate_target_support(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    contracts = payload.get("contracts", [])
    if not isinstance(contracts, list):
        return ["target_support.json contracts must be a list"]
    for contract in contracts:
        if not isinstance(contract, dict):
            errors.append("target_support.json contracts must be objects")
            continue
        try:
            validate_target_extension_contract(contract)
        except TargetExtensionContractError as exc:
            errors.append(f"target_support.json contract {contract.get('target_id', '<unknown>')} invalid: {exc}")
    if errors:
        return errors
    target_ids = {str(contract.get("target_id", "")) for contract in contracts if isinstance(contract, dict)}
    if not {"python", "typescript"} <= target_ids:
        errors.append("target_support.json must declare python and typescript target support posture")
    matrix_entries = target_support_matrix_entries(
        [contract for contract in contracts if isinstance(contract, dict)],
        operation_id="defaults.report",
        case_id="defaults.selected-output.success",
    )
    matrix_by_target = {entry["target_id"]: entry for entry in matrix_entries}
    if matrix_by_target.get("python", {}).get("adapter_id") != "python.function":
        errors.append("target_support.json implemented python target must project python.function into the semantic matrix")
    if matrix_by_target.get("typescript", {}).get("adapter_id") != "typescript.function":
        errors.append("target_support.json implemented typescript target must project typescript.function into the semantic matrix")
    rule = str(payload.get("rule", "")).lower()
    if "must not own product operation semantics" not in rule or "per-operation feature maintenance" not in rule:
        errors.append("target_support.json rule must reject product semantics and per-operation feature maintenance in targets")
    return errors


def _generated_command_adapter_statuses() -> tuple[list[dict[str, object]], list[str]]:
    statuses: list[dict[str, object]] = []
    errors: list[str] = []
    repo_root = Path(__file__).resolve().parents[2]
    generator_path = repo_root / "scripts" / "generate" / "generate_command_adapters.py"
    spec = importlib.util.spec_from_file_location("generate_command_adapters", generator_path)
    if spec is None or spec.loader is None:
        return statuses, [f"generator layer: cannot load {generator_path.relative_to(repo_root).as_posix()}"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = command_adapter_generation_manifest()
    for output_spec in manifest["generated_outputs"]:
        program = str(output_spec["program"])
        generated_path = repo_root / str(output_spec["path"])
        output_adapters = [
            adapter for adapter in manifest["adapters"] if adapter.get("command", {}).get("program") == program
        ]
        expected = module._render_generated_json(manifest, program=program)
        current = generated_path.read_text(encoding="utf-8") if generated_path.exists() else ""
        is_current = current == expected
        statuses.append(
            {
                "program": program,
                "path": generated_path.relative_to(repo_root).as_posix(),
                "status": "current" if is_current else "stale",
                "direct_edit_detected": not is_current,
                "source_contract": "src/agentic_workspace/contracts/command_adapter_generation.json",
                "regenerate": "uv run python scripts/generate/generate_command_adapters.py",
                "command_surfaces": [
                    str(adapter.get("command", {}).get("name", "")) for adapter in output_adapters
                ],
                "where_to_edit": {
                    "command_interface": "src/agentic_workspace/contracts/command_adapter_generation.json",
                    "runtime_behavior": "hand-written operation/primitive implementation code",
                },
            }
        )
        if not is_current:
            errors.append(
                f"generated adapter layer: {generated_path.relative_to(repo_root).as_posix()} is stale; "
                "run uv run python scripts/generate/generate_command_adapters.py"
            )

        expected_by_command = {
            str(adapter["command"]["name"]): {
                "id": adapter["id"],
                "status": adapter["status"],
                "command": adapter["command"],
                "operation_id": adapter["operation_ref"]["id"],
                "runtime_binding": adapter["runtime_binding"],
                "effect_hints": adapter["effect_hints"],
                "schemas": adapter["schemas"],
                "conformance_refs": adapter["conformance_refs"],
            }
            for adapter in manifest["adapters"]
            if adapter["command"]["program"] == program
        }
        try:
            payload = json.loads(current) if current else {}
        except json.JSONDecodeError as exc:
            errors.append(f"generated adapter layer: {generated_path.relative_to(repo_root).as_posix()} is not valid JSON: {exc}")
            continue
        actual_by_command = payload.get("adapters_by_command", {}) if isinstance(payload, dict) else {}
        if not isinstance(actual_by_command, dict):
            errors.append(f"generated adapter layer: {generated_path.relative_to(repo_root).as_posix()} missing adapters_by_command object")
            continue
        for command_name, expected_adapter in expected_by_command.items():
            actual_adapter = actual_by_command.get(command_name)
            if actual_adapter is None:
                errors.append(f"generated adapter layer: missing generated adapter for {program} command {command_name}")
                continue
            if not isinstance(actual_adapter, dict):
                errors.append(f"generated adapter layer: {program} command {command_name} adapter is not an object")
                continue
            for key, expected_value in expected_adapter.items():
                if actual_adapter.get(key) != expected_value:
                    errors.append(f"generated adapter layer: {program} command {command_name} {key} drifted from command_adapter_generation.json")
        for command_name in set(actual_by_command) - set(expected_by_command):
            errors.append(f"generated adapter layer: unexpected generated adapter for {program} command {command_name}")
    return statuses, errors


def _validate_generated_command_adapter_output() -> list[str]:
    return _generated_command_adapter_statuses()[1]


def _validate_generated_command_package_output() -> list[str]:
    repo_root = Path(__file__).resolve().parents[2]
    generator_path = repo_root / "scripts" / "generate" / "generate_command_packages.py"
    spec = importlib.util.spec_from_file_location("generate_command_packages", generator_path)
    if spec is None or spec.loader is None:
        return [f"generated package layer: cannot load {generator_path.relative_to(repo_root).as_posix()}"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stale_outputs: list[str] = []
    for output_path, rendered in module._render_outputs(command_package_ir_manifest()):
        current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        if current != rendered:
            stale_outputs.append(output_path.relative_to(repo_root).as_posix())
    return [f"generated package layer: {output} is stale; run uv run python scripts/generate/generate_command_packages.py" for output in stale_outputs]


def _validate_python_contract_consumption_policy(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    entries = payload.get("validated_at_consumption", [])
    if not isinstance(entries, list):
        return ["python_contract_consumption.json validated_at_consumption must be a list"]
    dynamic_entries = payload.get("dynamic_validated_loader_boundary", [])
    if not isinstance(dynamic_entries, list):
        return ["python_contract_consumption.json dynamic_validated_loader_boundary must be a list"]
    dynamic_loaders = {str(entry.get("loader", "")) for entry in dynamic_entries if isinstance(entry, dict)}
    implemented_dynamic_loaders: set[str] = set()

    contract_tooling_path = REPO_ROOT / "src" / "agentic_workspace" / "contract_tooling.py"
    tree = ast.parse(contract_tooling_path.read_text(encoding="utf-8"))
    validated_loader_calls: dict[str, tuple[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            if not isinstance(child.func, ast.Name) or child.func.id != "load_validated_contract_json":
                continue
            if len(child.args) < 2:
                errors.append(f"validated loader {node.name} calls load_validated_contract_json without contract and schema")
                continue
            contract_arg, schema_arg = child.args[:2]
            if not isinstance(contract_arg, ast.Constant) or not isinstance(schema_arg, ast.Constant):
                if node.name not in dynamic_loaders:
                    errors.append(f"validated loader {node.name} must use literal contract and schema refs or be declared dynamic")
                else:
                    implemented_dynamic_loaders.add(node.name)
                continue
            if not isinstance(contract_arg.value, str) or not isinstance(schema_arg.value, str):
                errors.append(f"validated loader {node.name} must use string contract and schema refs")
                continue
            validated_loader_calls[node.name] = (contract_arg.value, schema_arg.value)

    declared_loaders: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"validated_at_consumption entry {index} must be an object")
            continue
        loader = str(entry.get("loader", ""))
        contract = str(entry.get("contract", ""))
        schema = str(entry.get("schema", ""))
        consumer = str(entry.get("consumer", ""))
        if not loader or not contract or not schema or not consumer:
            errors.append(f"validated_at_consumption entry {index} is missing loader, contract, schema, or consumer")
            continue
        declared_loaders.add(loader)
        actual_refs = validated_loader_calls.get(loader)
        if actual_refs is None:
            errors.append(f"validated contract consumer {consumer} declares unknown loader {loader}")
            continue
        if actual_refs != (contract, schema):
            errors.append(
                f"validated contract consumer {consumer} declares {contract} with {schema}, "
                f"but loader {loader} validates {actual_refs[0]} with {actual_refs[1]}"
            )

    unrecorded_loaders = sorted(set(validated_loader_calls) - declared_loaders - dynamic_loaders - {"python_contract_consumption_manifest"})
    if unrecorded_loaders:
        errors.append(
            "validated contract loaders are not recorded in python_contract_consumption.json: "
            + ", ".join(unrecorded_loaders)
        )
    missing_dynamic_loaders = sorted(dynamic_loaders - implemented_dynamic_loaders)
    if missing_dynamic_loaders:
        errors.append(
            "dynamic validated loaders are declared but not implemented in contract_tooling.py: "
            + ", ".join(missing_dynamic_loaders)
        )
    return errors


def _validate_lifecycle_generation_readiness(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    phase_model = payload.get("phase_model", [])
    commands = payload.get("commands", [])
    if not isinstance(phase_model, list) or not isinstance(commands, list):
        return ["lifecycle_generation_readiness.json phase_model and commands must be lists"]
    phase_set = {str(phase) for phase in phase_model}
    expected_commands = {
        ("root", "install"),
        ("root", "init"),
        ("root", "adopt"),
        ("root", "upgrade"),
        ("root", "uninstall"),
        ("root", "doctor"),
        ("root", "status"),
        ("planning-package", "status"),
        ("memory-package", "status"),
    }
    actual_commands: set[tuple[str, str]] = set()
    for command in commands:
        if not isinstance(command, dict):
            errors.append("lifecycle_generation_readiness.json command entries must be objects")
            continue
        surface_command = (str(command.get("surface", "")), str(command.get("command", "")))
        actual_commands.add(surface_command)
        for phase_field in ("phases", "adapter_owned_phases", "runtime_owned_phases"):
            unknown = sorted(str(phase) for phase in command.get(phase_field, []) if str(phase) not in phase_set)
            if unknown:
                errors.append(f"lifecycle {surface_command} references unknown {phase_field}: {', '.join(unknown)}")
        effects = command.get("effects", {})
        if not isinstance(effects, dict):
            errors.append(f"lifecycle {surface_command} effects must be an object")
            continue
        eligibility = str(command.get("generation_eligibility", ""))
        if effects.get("destructive_potential") and eligibility != "deferred-destructive":
            errors.append(f"lifecycle {surface_command} destructive command must be deferred-destructive")
        if effects.get("writes_repo_state") and eligibility == "eligible-read-only":
            errors.append(f"lifecycle {surface_command} mutating command cannot be eligible-read-only")
        capability_maturity = command.get("capability_maturity", {})
        if not isinstance(capability_maturity, dict):
            errors.append(f"lifecycle {surface_command} capability_maturity must be an object")
            continue
        required_capabilities = {
            "dry_run_plan",
            "strict_preflight_refusal",
            "destructive_refusal",
            "apply_mutation",
            "verify",
        }
        missing_capabilities = sorted(required_capabilities - set(capability_maturity))
        if missing_capabilities:
            errors.append(f"lifecycle {surface_command} missing capability maturity: {', '.join(missing_capabilities)}")
        if effects.get("writes_repo_state") and capability_maturity.get("apply_mutation") == "proved":
            errors.append(f"lifecycle {surface_command} apply mutation cannot be proved while generation remains deferred")
        if not effects.get("writes_repo_state") and capability_maturity.get("apply_mutation") != "not-applicable":
            errors.append(f"lifecycle {surface_command} read-only command apply mutation must be not-applicable")
        if eligibility == "eligible-dry-run-refusal":
            dry_run_proved = capability_maturity.get("dry_run_plan") == "proved"
            refusal_proved = (
                capability_maturity.get("strict_preflight_refusal") == "proved"
                or capability_maturity.get("destructive_refusal") == "proved"
            )
            if not dry_run_proved and not refusal_proved:
                errors.append(f"lifecycle {surface_command} eligible-dry-run-refusal requires proved dry-run or refusal conformance")
            if capability_maturity.get("apply_mutation") == "proved":
                errors.append(f"lifecycle {surface_command} eligible-dry-run-refusal must not prove apply mutation")
            if not command.get("conformance_refs"):
                errors.append(f"lifecycle {surface_command} eligible-dry-run-refusal requires conformance_refs")
    missing = sorted(expected_commands - actual_commands)
    if missing:
        errors.append(f"lifecycle_generation_readiness.json missing command classifications: {missing}")
    mutation_criteria = payload.get("mutation_promotion_criteria", [])
    if not isinstance(mutation_criteria, list) or len(mutation_criteria) < 5:
        errors.append("lifecycle_generation_readiness.json mutation_promotion_criteria must list explicit safety gates")
    return errors


def _validate_python_runtime_boundary_authority(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    audit = payload.get("root_cli_authority_audit")
    if not isinstance(audit, dict):
        return ["python_runtime_boundary.json missing root_cli_authority_audit"]
    classes = {
        str(item.get("id", ""))
        for item in audit.get("responsibility_classes", [])
        if isinstance(item, dict)
    }
    required_classes = {
        "runtime-primitives",
        "derived-renderers",
        "generated-dispatch-bridges",
        "remaining-interface-authority",
    }
    missing_classes = sorted(required_classes - classes)
    if missing_classes:
        errors.append("python_runtime_boundary.json root CLI audit missing responsibility class(es): " + ", ".join(missing_classes))
    candidates = [item for item in audit.get("next_extraction_or_guard_candidates", []) if isinstance(item, dict)]
    candidate_types = {str(item.get("candidate_type", "")) for item in candidates}
    if not {"extract-interface-authority", "add-guard-check"} <= candidate_types:
        errors.append("python_runtime_boundary.json root CLI audit must name extraction and guard candidates")
    for item in candidates:
        role = str(item.get("tracking_role", "")).strip()
        status = str(item.get("tracking_status", "")).strip()
        if role not in {"live-owner", "historical-provenance"} or not status:
            errors.append("python_runtime_boundary.json root CLI audit candidates must classify tracking as live-owner or historical-provenance")
            continue
        tracking_issue = str(item.get("tracking_issue", "")).strip()
        provenance_issue = str(item.get("provenance_issue", "")).strip()
        if role == "live-owner" and status == "closed":
            errors.append(
                f"python_runtime_boundary.json root CLI audit candidate {item.get('id', '<unknown>')} cannot use closed tracking as live ownership"
            )
        if role == "live-owner" and (not tracking_issue.startswith("#") or not str(item.get("current_owner", "")).strip()):
            errors.append(
                f"python_runtime_boundary.json root CLI audit candidate {item.get('id', '<unknown>')} must name tracking_issue and current_owner for live ownership"
            )
        if role == "historical-provenance" and (
            not provenance_issue.startswith("#") or not str(item.get("provenance", "")).strip()
        ):
            errors.append(
                f"python_runtime_boundary.json root CLI audit candidate {item.get('id', '<unknown>')} must name provenance_issue and explain historical provenance"
            )
        if role == "historical-provenance" and tracking_issue:
            errors.append(
                f"python_runtime_boundary.json root CLI audit candidate {item.get('id', '<unknown>')} must not use tracking_issue for historical provenance"
            )
    routing = audit.get("direct_cli_edit_routing", {})
    if not isinstance(routing, dict):
        errors.append("python_runtime_boundary.json root CLI audit missing direct_cli_edit_routing")
    elif not routing.get("route_to_contract_when") or not routing.get("review_requires"):
        errors.append("python_runtime_boundary.json root CLI audit must route contract edits and review requirements")
    return errors


def _parser_snapshot(parser) -> list[dict[str, object]]:
    subparsers_action = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    return [_command_parser_snapshot(subparsers_action.choices[name]) for name in subparsers_action.choices]


def _command_parser_snapshot(parser) -> dict[str, object]:
    snapshot: dict[str, object] = {"name": parser.prog.split()[-1], "help": parser.description}
    options: list[dict[str, object]] = []
    for action in parser._actions:
        if not action.option_strings:
            continue
        if action.dest == "help":
            continue
        option: dict[str, object] = {"flags": list(action.option_strings)}
        if action.help is not None:
            option["help"] = action.help
        if action.required:
            option["required"] = True
        if action.choices is not None:
            option["choices"] = list(action.choices)
        if action.default is not None and action.default != argparse.SUPPRESS:
            option["default"] = action.default
        if action.type is int:
            option["type"] = "integer"
        if type(action).__name__ == "_StoreTrueAction":
            option["action"] = "store_true"
        options.append(option)
    if options:
        snapshot["options"] = options
    subparsers_action = next((action for action in parser._actions if isinstance(action, argparse._SubParsersAction)), None)
    if subparsers_action is not None:
        snapshot["subcommands"] = [_command_parser_snapshot(subparsers_action.choices[name]) for name in subparsers_action.choices]
    return snapshot


def _resolved_manifest_option(option_spec: dict[str, object]) -> dict[str, object]:
    resolved: dict[str, object] = {"flags": list(option_spec["flags"])}
    help_text = cli._resolved_option_help(option_spec)  # type: ignore[attr-defined]
    if help_text is not None:
        resolved["help"] = help_text
    if option_spec.get("required") is True:
        resolved["required"] = True
    choices = cli._resolve_option_choices(option_spec)  # type: ignore[attr-defined]
    if choices is not None:
        resolved["choices"] = list(choices)
    if "default" in option_spec or "default_ref" in option_spec:
        resolved["default"] = cli._resolve_option_default(option_spec)  # type: ignore[attr-defined]
    option_type = cli._resolve_option_type(option_spec)  # type: ignore[attr-defined]
    if option_type is int:
        resolved["type"] = "integer"
    action = option_spec.get("action")
    if isinstance(action, str):
        resolved["action"] = action
        if action == "store_true" and "default" not in resolved:
            resolved["default"] = False
    return resolved


def _resolved_group_options(group_name: str) -> list[dict[str, object]]:
    group_spec = cli_option_groups_manifest()["option_groups"][group_name]
    resolved: list[dict[str, object]] = []
    for parent_group in group_spec.get("uses", []):
        resolved.extend(_resolved_group_options(parent_group))
    for option_spec in group_spec.get("options", []):
        resolved.append(_resolved_manifest_option(option_spec))
    return resolved


def _resolved_command_manifest(command_spec: dict[str, object]) -> dict[str, object]:
    resolved: dict[str, object] = {
        "name": str(command_spec["name"]),
        "help": str(command_spec["help"]),
    }
    options: list[dict[str, object]] = []
    for group_name in command_spec.get("uses_option_groups", []):
        options.extend(_resolved_group_options(str(group_name)))
    for option_spec in command_spec.get("options", []):
        options.append(_resolved_manifest_option(option_spec))
    if options:
        resolved["options"] = options
    subcommands = command_spec.get("subcommands", [])
    if isinstance(subcommands, list) and subcommands:
        resolved["subcommands"] = [_resolved_command_manifest(spec) for spec in subcommands]
    return resolved


def _executable_command_surfaces(command_specs: list[dict[str, object]]) -> set[tuple[str, str | None]]:
    surfaces: set[tuple[str, str | None]] = set()
    for command_spec in command_specs:
        command_name = str(command_spec["name"])
        subcommands = command_spec.get("subcommands", [])
        if isinstance(subcommands, list) and subcommands:
            if command_spec.get("subcommands_required") is False:
                surfaces.add((command_name, None))
            for subcommand_spec in subcommands:
                surfaces.add((command_name, str(subcommand_spec["name"])))
            continue
        surfaces.add((command_name, None))
    return surfaces


def _operation_command_surfaces(command_surface: dict[str, object]) -> set[tuple[str, str | None]]:
    command_name = str(command_surface["command"])
    surfaces = {(command_name, command_surface.get("subcommand") if isinstance(command_surface.get("subcommand"), str) else None)}
    subcommands = command_surface.get("subcommands", [])
    if isinstance(subcommands, list):
        for subcommand in subcommands:
            if isinstance(subcommand, str):
                surfaces.add((command_name, subcommand))
            elif isinstance(subcommand, dict) and isinstance(subcommand.get("name"), str):
                surfaces.add((command_name, str(subcommand["name"])))
    return surfaces


def _adapter_command_surfaces(command: dict[str, object]) -> set[tuple[str, str | None]]:
    command_name = str(command["name"])
    subcommands = command.get("subcommands", [])
    if isinstance(subcommands, list) and subcommands:
        return {(command_name, str(subcommand)) for subcommand in subcommands}
    subcommand = command.get("subcommand")
    return {(command_name, str(subcommand) if isinstance(subcommand, str) else None)}


def _known_command_names_for_program(program: str) -> set[str]:
    if program == cli_commands_manifest()["program"]:
        return {command["name"] for command in cli_commands_manifest()["commands"]}
    generated_parser = _program_generated_parser(program)
    generated_subparsers = _subparser_action(generated_parser) if generated_parser is not None else None
    generated_names = set(generated_subparsers.choices) if generated_subparsers is not None else set()
    parser = _program_parser(program)
    subparsers = _subparser_action(parser) if parser is not None else None
    if subparsers is None:
        return {str(command_name) for command_name in generated_names}
    return {str(command_name) for command_name in set(subparsers.choices) | generated_names}


def _program_generated_parser(program: str) -> argparse.ArgumentParser | None:
    if program in {"agentic-workspace", "agentic-planning", "agentic-memory", "agentic-verification"}:
        return load_generated_command_package_for_entrypoint(program).build_generated_parser()
    return None


def _program_generated_command_names(program: str) -> set[str]:
    if program in {"agentic-workspace", "agentic-planning", "agentic-memory", "agentic-verification"}:
        return set(load_generated_command_package_for_entrypoint(program).generated_command_names())
    return set()


def _program_parser(program: str) -> argparse.ArgumentParser | None:
    if program == "agentic-workspace":
        return generated_workspace_cli.build_parser()
    if program == "agentic-planning":
        return load_generated_command_module_for_entrypoint("agentic-planning", "cli.py").build_parser()
    if program == "agentic-memory":
        return load_generated_command_module_for_entrypoint("agentic-memory", "cli.py").build_parser()
    if program == "agentic-verification":
        return load_generated_command_module_for_entrypoint("agentic-verification", "cli.py").build_parser()
    return None


def _subparser_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    return next((action for action in parser._actions if isinstance(action, argparse._SubParsersAction)), None)


def _command_parser(
    parser: argparse.ArgumentParser,
    *,
    command_name: str,
    subcommand_name: str | None = None,
) -> argparse.ArgumentParser | None:
    subparsers_action = _subparser_action(parser)
    if subparsers_action is None:
        return None
    command_parser = subparsers_action.choices.get(command_name)
    if command_parser is None or subcommand_name is None:
        return command_parser
    command_subparsers = _subparser_action(command_parser)
    if command_subparsers is None:
        return None
    return command_subparsers.choices.get(subcommand_name)


def _command_option_actions(parser: argparse.ArgumentParser) -> dict[str, argparse.Action]:
    return {
        str(action.dest): action
        for action in parser._actions
        if action.option_strings and action.dest != "help"
    }


def _validate_generated_adapter_live_cli_parity(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    adapters = payload.get("adapters", [])
    if not isinstance(adapters, list):
        return ["generated adapter live CLI parity cannot inspect malformed adapters list"]
    for raw_adapter in adapters:
        if not isinstance(raw_adapter, dict) or raw_adapter.get("status") != "generated":
            continue
        adapter_id = str(raw_adapter.get("id", ""))
        command = raw_adapter.get("command", {})
        operation_ref = raw_adapter.get("operation_ref", {})
        if not isinstance(command, dict) or not isinstance(operation_ref, dict):
            continue
        program = str(command.get("program", ""))
        command_name = str(command.get("name", ""))
        if isinstance(command.get("subcommands"), list):
            subcommand_names: list[str | None] = [
                str(subcommand) for subcommand in command["subcommands"] if isinstance(subcommand, str)
            ]
        else:
            subcommand_names = [str(command["subcommand"]) if isinstance(command.get("subcommand"), str) else None]
        parser = _program_parser(program)
        if command_name in _program_generated_command_names(program):
            parser = _program_generated_parser(program)
        if parser is None:
            errors.append(f"generated adapter {adapter_id} references unknown live CLI program {program}")
            continue
        live_command_parser = None
        for subcommand_name in subcommand_names:
            live_command_parser = _command_parser(parser, command_name=command_name, subcommand_name=subcommand_name)
            if live_command_parser is None:
                surface = f"{command_name} {subcommand_name}" if subcommand_name else command_name
                errors.append(f"generated adapter {adapter_id} command surface {program} {surface} is missing from the live CLI")
                continue
        operation = operation_manifest(str(operation_ref.get("path", "")))
        operation_surface = operation.get("command_surface", {})
        if not isinstance(operation_surface, dict):
            errors.append(f"generated adapter {adapter_id} operation command_surface is malformed")
            continue
        if operation_surface.get("program", "agentic-workspace") != program:
            errors.append(f"generated adapter {adapter_id} program drifted from operation command_surface")
        operation_surfaces = _operation_command_surfaces(operation_surface)
        if len(subcommand_names) == 1 and (command_name, subcommand_names[0]) not in operation_surfaces:
            errors.append(f"generated adapter {adapter_id} command drifted from operation command_surface")
        if len(subcommand_names) > 1 and command_name != operation_surface.get("command"):
            errors.append(f"generated adapter {adapter_id} command drifted from operation command_surface")
        if command_name in _program_generated_command_names(program):
            continue
        expected_cli_inputs = {
            str(input_spec["name"]): bool(input_spec.get("required", False))
            for input_spec in operation.get("inputs", [])
            if isinstance(input_spec, dict) and input_spec.get("source") == "cli-option"
        }
        live_options = _command_option_actions(live_command_parser)
        live_option_names = set(live_options)
        expected_option_names = set(expected_cli_inputs)
        missing_options = sorted(expected_option_names - live_option_names)
        extra_options = sorted(live_option_names - expected_option_names)
        if missing_options:
            errors.append(
                f"generated adapter {adapter_id} contract declares CLI option(s) missing from live parser: "
                + ", ".join(missing_options)
            )
        if extra_options:
            errors.append(
                f"generated adapter {adapter_id} live parser has CLI option(s) missing from operation contract: "
                + ", ".join(extra_options)
            )
        for option_name, expected_required in expected_cli_inputs.items():
            action = live_options.get(option_name)
            if action is None:
                continue
            if bool(action.required) != expected_required:
                errors.append(f"generated adapter {adapter_id} option {option_name} required flag drifted from operation contract")
    return errors


def _expected_authority_marker(marker: dict[str, object], path: str) -> dict[str, object]:
    canonical_source = marker["canonical_source"]
    if not isinstance(canonical_source, dict):
        return {}
    kind = canonical_source["kind"]
    if kind == "fixed":
        source = canonical_source["value"]
    elif kind == "path":
        source = path
    elif kind == "package-root-source":
        package_root = "/".join(path.split("/")[:2]) if path.startswith("packages/") else "package"
        source = f"{package_root}/src/"
    else:
        source = ""
    return {
        "path": path,
        "authority": marker["authority"],
        "canonical_source": source,
        "safe_to_edit": marker["safe_to_edit"],
        "refresh_command": marker["refresh_command"],
    }


def _validate_authority_marker_parity(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    markers = payload.get("markers", [])
    if not isinstance(markers, list):
        return ["authority marker manifest must contain marker list"]
    for marker in markers:
        if not isinstance(marker, dict):
            errors.append("authority marker entry must be an object")
            continue
        marker_id = str(marker.get("id", ""))
        if marker_id in seen_ids:
            errors.append(f"duplicate authority marker id {marker_id}")
        seen_ids.add(marker_id)
        representative_paths = marker.get("representative_paths", [])
        if not isinstance(representative_paths, list):
            errors.append(f"authority marker {marker_id} representative_paths must be a list")
            continue
        for path in representative_paths:
            if not isinstance(path, str):
                errors.append(f"authority marker {marker_id} representative path must be a string")
                continue
            expected = _expected_authority_marker(marker, path)
            actual = cli._authority_marker_for_path(path)  # type: ignore[attr-defined]
            if actual != expected:
                errors.append(f"authority marker {marker_id} representative path {path} drifted: expected {expected}, got {actual}")
    return errors


def _validate_contract_inventory_owner_choice() -> list[str]:
    errors: list[str] = []
    manifest = contract_inventory_manifest()
    areas = manifest.get("areas", [])
    if isinstance(areas, list):
        seen_areas: set[str] = set()
        for entry in areas:
            if not isinstance(entry, dict):
                continue
            area = entry.get("area")
            if not isinstance(area, str):
                continue
            if area in seen_areas:
                errors.append(f"contract_inventory.json declares duplicate area {area}")
            seen_areas.add(area)

    model = manifest.get("owner_choice_model", {})
    concern_classes = model.get("concern_classes", []) if isinstance(model, dict) else []
    declared = {
        concern.get("id")
        for concern in concern_classes
        if isinstance(concern, dict) and isinstance(concern.get("id"), str)
    }
    required = {
        "config_policy",
        "contract_schema_authority",
        "planning_active_state",
        "memory_durable_understanding",
        "review_evidence",
        "generated_adapter_output",
        "package_payload",
        "runtime_primitive_implementation",
    }
    missing = sorted(required - declared)
    if missing:
        errors.append("contract_inventory.json owner_choice_model is missing concern class(es): " + ", ".join(missing))
    if len(declared) != len(concern_classes):
        errors.append("contract_inventory.json owner_choice_model concern class ids must be unique strings")
    return errors


def _find_review_references(value: object, *, path: str = "<root>") -> list[str]:
    references: list[str] = []
    review_markers = ("docs/reviews/", ".agentic-workspace/planning/reviews/")
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if any(marker in normalized for marker in review_markers):
            references.append(f"{path}: {value}")
    elif isinstance(value, dict):
        for key, nested in value.items():
            references.extend(_find_review_references(nested, path=f"{path}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            references.extend(_find_review_references(nested, path=f"{path}[{index}]"))
    return references


def _validate_review_artifacts_not_startup_inputs() -> list[str]:
    startup_surfaces = {
        "defaults.startup": cli._defaults_payload()["startup"],  # type: ignore[attr-defined]
        "context_templates.startup_context": context_templates_manifest()["startup_context"],
        "start_payload": _sample_startup_context_payload(),
    }
    errors: list[str] = []
    for name, payload in startup_surfaces.items():
        references = _find_review_references(payload, path=name)
        if references:
            errors.append(
                f"{name} routes ordinary startup to historical review artifact(s): " + "; ".join(references)
            )
    return errors


def _validate_product_managed_enclave() -> list[str]:
    descriptors = cli._module_operations()  # type: ignore[attr-defined]
    ownership = cli._ownership_payload(target_root=REPO_ROOT, descriptors=descriptors)  # type: ignore[attr-defined]
    payload = cli._product_managed_enclave_payload(  # type: ignore[attr-defined]
        target_root=REPO_ROOT,
        ownership_payload=ownership,
    )
    errors: list[str] = []
    if payload.get("managed_root") != ".agentic-workspace/":
        errors.append("product-managed enclave managed_root drifted from .agentic-workspace/")
    if payload.get("boundary_leaks"):
        errors.append(f"product-managed enclave reports boundary leaks: {payload['boundary_leaks']}")
    local_only = payload.get("local_only_state", {})
    if not isinstance(local_only, dict) or local_only.get("status") != "non-authoritative":
        errors.append("product-managed enclave local-only state must stay non-authoritative")
    startup_quietness = payload.get("startup_quietness", {})
    if not isinstance(startup_quietness, dict) or startup_quietness.get("status") != "compact":
        errors.append("product-managed enclave startup quietness must stay compact")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    checks: list[tuple[str, list[str]]] = [
        ("compact_contract_profile.json", _validate(compact_contract_manifest(), "selector_contracts_manifest.schema.json")),
        ("proof_routes.json", _validate(proof_routes_manifest(), "proof_routes_manifest.schema.json")),
        ("proof_selection_rules.json", _validate(proof_selection_rules_manifest(), "proof_selection_rules.schema.json")),
        ("authority_markers.json", _validate(authority_markers_manifest(), "authority_markers.schema.json")),
        ("context_templates.json", _validate(context_templates_manifest(), "context_templates.schema.json")),
        ("report_contract.json", _validate(report_contract_manifest(), "report_contract_manifest.schema.json")),
        ("contract_inventory.json", _validate(contract_inventory_manifest(), "contract_inventory.schema.json")),
        ("contract_inventory owner choice", _validate_contract_inventory_owner_choice()),
        ("review artifacts startup hygiene", _validate_review_artifacts_not_startup_inputs()),
        ("product-managed enclave", _validate_product_managed_enclave()),
        ("compact answer sample", _validate(_sample_compact_answer(), "compact_contract_answer.schema.json")),
        ("workspace report sample", _validate(_sample_report_payload(), "workspace_report.schema.json")),
        ("workspace config sample", _validate(_sample_workspace_config_payload(), "workspace_config.schema.json")),
        (
            "workspace local override sample",
            _validate(_sample_workspace_local_override_payload(), "workspace_local_override.schema.json"),
        ),
        (
            "delegation outcomes sample",
            _validate(_sample_delegation_outcomes_payload(), "delegation_outcomes.schema.json"),
        ),
        (
            "setup findings sample",
            _validate(_sample_setup_findings_payload(), "setup_findings.schema.json"),
        ),
        (
            "module capability sample",
            _validate(_sample_module_capability_payload(), "module_capability.schema.json"),
        ),
        (
            "startup context sample",
            _validate(_sample_startup_context_payload(), "startup_context.schema.json"),
        ),
        (
            "implementer context sample",
            _validate(_sample_implementer_context_payload(), "implementer_context.schema.json"),
        ),
        (
            "workspace surfaces manifest",
            _validate(workspace_surfaces_manifest(), "workspace_surfaces_manifest.schema.json"),
        ),
        (
            "setup findings policy manifest",
            _validate(setup_findings_policy_manifest(), "setup_findings_policy.schema.json"),
        ),
        (
            "workflow artifact profiles manifest",
            _validate(workflow_artifact_profiles_manifest(), "workflow_artifact_profiles.schema.json"),
        ),
        (
            "workflow definition format manifest",
            _validate(workflow_definition_format_manifest(), "workflow_definition_format.schema.json"),
        ),
        (
            "improvement latitude policy manifest",
            _validate(improvement_latitude_policy_manifest(), "improvement_latitude_policy.schema.json"),
        ),
        (
            "optimization bias policy manifest",
            _validate(optimization_bias_policy_manifest(), "optimization_bias_policy.schema.json"),
        ),
        (
            "repo friction policy manifest",
            _validate(repo_friction_policy_manifest(), "repo_friction_policy.schema.json"),
        ),
        (
            "preflight policy manifest",
            _validate(preflight_policy_manifest(), "preflight_policy.schema.json"),
        ),
        (
            "module registry manifest",
            _validate(module_registry_manifest(), "module_registry.schema.json"),
        ),
        (
            "cli commands manifest",
            _validate(cli_commands_manifest(), "cli_commands.schema.json"),
        ),
        (
            "cli option groups manifest",
            _validate(cli_option_groups_manifest(), "cli_option_groups.schema.json"),
        ),
        (
            "operation contracts registry",
            _validate(operation_contracts_manifest(), "operation_contracts.schema.json")
            + _validate_operation_registry(operation_contracts_manifest()),
        ),
        (
            "module operation contract locations",
            _validate_module_operation_contract_locations(),
        ),
        (
            "conformance contracts registry",
            _validate(conformance_contracts_manifest(), "conformance_contracts.schema.json")
            + _validate_conformance_registry(conformance_contracts_manifest()),
        ),
        (
            "command adapter generation manifest",
            _validate(command_adapter_generation_manifest(), "command_adapter_generation.schema.json")
            + _validate_command_adapter_generation(command_adapter_generation_manifest())
            + _validate_generated_adapter_live_cli_parity(command_adapter_generation_manifest()),
        ),
        (
            "command package IR",
            _validate(command_package_ir_manifest(), "command_package_ir.schema.json")
            + _validate_command_package_ir(command_package_ir_manifest()),
        ),
        (
            "Operation Conformance Test IR",
            _validate(operation_conformance_test_ir_manifest(), "operation_conformance_test_ir.schema.json")
            + _validate_operation_conformance_test_ir(operation_conformance_test_ir_manifest()),
        ),
        (
            "operation artifact registry",
            _validate(operation_artifact_registry_manifest(), "operation_artifact_registry.schema.json")
            + _validate_operation_artifact_registry(operation_artifact_registry_manifest()),
        ),
        (
            "generated behavior stratification",
            _validate(generated_behavior_stratification_manifest(), "generated_behavior_stratification.schema.json")
            + _validate_generated_behavior_stratification(generated_behavior_stratification_manifest()),
        ),
        (
            "target support",
            _validate(target_support_manifest(), "target_support.schema.json") + _validate_target_support(target_support_manifest()),
        ),
        (
            "command-generation schema boundary",
            _validate_command_generation_schema_boundary(),
        ),
        (
            "generated command adapter output",
            _validate_generated_command_adapter_output(),
        ),
        (
            "generated command package output",
            _validate_generated_command_package_output(),
        ),
        (
            "operation primitives registry",
            _validate(operation_primitives_manifest(), "operation_primitives.schema.json")
            + _validate_operation_primitives(operation_primitives_manifest()),
        ),
        (
            "operation IR representative plans",
            _validate_operation_ir_plans(),
        ),
        (
            "improvement signal contract",
            _validate(improvement_signal_contract_manifest(), "improvement_signal_contract.schema.json"),
        ),
        (
            "python extraction map",
            _validate(python_extraction_map_manifest(), "python_extraction_map.schema.json"),
        ),
        (
            "python contract consumption policy",
            _validate(python_contract_consumption_manifest(), "python_contract_consumption.schema.json")
            + _validate_python_contract_consumption_policy(python_contract_consumption_manifest()),
        ),
        (
            "python runtime boundary",
            _validate(python_runtime_boundary_manifest(), "python_runtime_boundary.schema.json")
            + _validate_python_runtime_boundary_authority(python_runtime_boundary_manifest()),
        ),
        (
            "python runtime projection inventory",
            _validate(python_runtime_projection_inventory_manifest(), "python_runtime_projection_inventory.schema.json"),
        ),
        (
            "lifecycle generation readiness",
            _validate(lifecycle_generation_readiness_manifest(), "lifecycle_generation_readiness.schema.json")
            + _validate_lifecycle_generation_readiness(lifecycle_generation_readiness_manifest()),
        ),
        (
            "authority marker parity",
            _validate_authority_marker_parity(authority_markers_manifest()),
        ),
    ]

    operation_contracts = operation_contracts_manifest()
    operation_primitives = operation_primitives_manifest()
    known_primitives = {primitive["id"] for primitive in operation_primitives["primitives"]}
    operation_surfaces: list[tuple[str, str | None]] = []
    for operation_ref in operation_contracts["operations"]:
        operation = operation_manifest(operation_ref["path"])
        command_surface = operation["command_surface"]
        if command_surface.get("program", "agentic-workspace") == cli_commands_manifest()["program"]:
            operation_surfaces.extend(_operation_command_surfaces(command_surface))
        checks.append(
            (
                f"operation contract {operation_ref['id']}",
                _validate(operation, "operation.schema.json"),
            )
        )
        surface_program = str(command_surface.get("program", cli_commands_manifest()["program"]))
        known_commands = _known_command_names_for_program(surface_program)
        if operation_ref["command"] not in known_commands:
            checks.append(
                (
                    "operation command parity",
                    [f"unknown command for operation {operation_ref['id']} on program {surface_program}"],
                )
            )
        registry_errors: list[str] = []
        if operation["id"] != operation_ref["id"]:
            registry_errors.append(f"operation id mismatch for {operation_ref['path']}")
        if operation["command_surface"]["command"] != operation_ref["command"]:
            registry_errors.append(f"operation command mismatch for {operation_ref['id']}")
        if operation.get("migration_status") != operation_ref["migration_status"]:
            registry_errors.append(f"operation migration status mismatch for {operation_ref['id']}")
        if registry_errors:
            checks.append(("operation registry parity", registry_errors))
        missing_primitives = [step["uses"] for step in operation["steps"] if step["uses"] not in known_primitives]
        if missing_primitives:
            checks.append(
                (
                    "operation primitive parity",
                    [f"{operation_ref['id']} uses unknown primitive(s): {', '.join(missing_primitives)}"],
                )
            )
    expected_operation_surfaces = _executable_command_surfaces(cli_commands_manifest()["commands"])
    actual_operation_surfaces = set(operation_surfaces)
    missing_operation_surfaces = sorted(expected_operation_surfaces - actual_operation_surfaces)
    extra_operation_surfaces = sorted(actual_operation_surfaces - expected_operation_surfaces)
    duplicate_operation_surfaces = sorted(
        surface for surface in actual_operation_surfaces if operation_surfaces.count(surface) > 1
    )
    operation_surface_errors: list[str] = []
    if missing_operation_surfaces:
        operation_surface_errors.append(f"missing operation contracts: {missing_operation_surfaces}")
    if extra_operation_surfaces:
        operation_surface_errors.append(f"operation contracts reference non-executable surfaces: {extra_operation_surfaces}")
    if duplicate_operation_surfaces:
        operation_surface_errors.append(f"duplicate operation contracts: {duplicate_operation_surfaces}")
    if operation_surface_errors:
        checks.append(("operation command-surface parity", operation_surface_errors))

    defaults_payload = cli._defaults_payload()  # type: ignore[attr-defined]
    if defaults_payload["compact_contract_profile"]["answer_shape"] != compact_contract_manifest()["answer_shape"]:
        checks.append(("defaults compact profile parity", ["defaults payload answer_shape drifted from compact_contract_profile.json"]))
    if defaults_payload["proof_surfaces"]["default_routes"] != proof_routes_manifest()["default_routes"]:
        checks.append(("proof routes parity", ["defaults payload proof routes drifted from proof_routes.json"]))
    proof_rules = proof_selection_rules_manifest()
    validation_lane_ids = {lane["id"] for lane in defaults_payload["validation"]["lanes"]}
    proof_rule_lanes = {rule["lane"] for rule in proof_rules["rules"]} | {proof_rules["fallback_lane"]}
    unknown_rule_lanes = sorted(proof_rule_lanes - validation_lane_ids)
    if unknown_rule_lanes:
        checks.append(("proof selection rules parity", [f"unknown validation lane(s): {', '.join(unknown_rule_lanes)}"]))
    if cli._reporting_schema_payload() != report_contract_manifest():  # type: ignore[attr-defined]
        checks.append(("report contract parity", ["reporting schema payload drifted from report_contract.json"]))
    workspace_surfaces = workspace_surfaces_manifest()
    if [path.as_posix() for path in cli.WORKSPACE_PAYLOAD_FILES] != workspace_surfaces["payload_files"]:
        checks.append(("workspace surfaces parity", ["workspace payload files drifted from workspace_surfaces.json"]))
    if cli.SYSTEM_INTENT_MIRROR_KIND != workspace_surfaces["system_intent_mirror_kind"]:
        checks.append(("workspace surfaces parity", ["system intent mirror kind drifted from workspace_surfaces.json"]))
    if cli.SUBSYSTEM_INTENT_KIND != workspace_surfaces["subsystem_intent_kind"]:
        checks.append(("workspace surfaces parity", ["subsystem intent kind drifted from workspace_surfaces.json"]))
    if cli.WORKSPACE_AGENTS_PATH.as_posix() != workspace_surfaces["default_agents_path"]:
        checks.append(("workspace surfaces parity", ["workspace agents path drifted from workspace_surfaces.json"]))
    if [path.as_posix() for path in cli.WORKSPACE_HANDOFF_SURFACES] != workspace_surfaces["handoff_surfaces"]:
        checks.append(("workspace surfaces parity", ["workspace handoff surfaces drifted from workspace_surfaces.json"]))
    if {key: value.as_posix() for key, value in cli.MODULE_UPGRADE_SOURCE_PATHS.items()} != workspace_surfaces["module_upgrade_source_paths"]:
        checks.append(("workspace surfaces parity", ["module upgrade source paths drifted from workspace_surfaces.json"]))
    if cli.SETUP_FINDINGS_PATH.as_posix() != workspace_surfaces["setup_findings_path"]:
        checks.append(("workspace surfaces parity", ["setup findings path drifted from workspace_surfaces.json"]))
    if list(cli.MIXED_AGENT_LOCAL_OVERRIDE_FIELDS) != workspace_surfaces["mixed_agent_local_override_fields"]:
        checks.append(("workspace surfaces parity", ["mixed-agent local override fields drifted from workspace_surfaces.json"]))
    setup_policy = setup_findings_policy_manifest()
    if setup_policy["artifact_path"] != cli.SETUP_FINDINGS_PATH.as_posix():
        checks.append(("setup findings policy parity", ["setup findings artifact path drifted from setup_findings_policy.json"]))
    if setup_policy["accepted_kind"] != cli.SETUP_FINDINGS_KIND:
        checks.append(("setup findings policy parity", ["setup findings kind drifted from setup_findings_policy.json"]))
    if setup_policy["promotion_confidence_threshold"] != cli.SETUP_FINDING_PROMOTION_THRESHOLD:
        checks.append(("setup findings policy parity", ["setup findings promotion threshold drifted from setup_findings_policy.json"]))
    if [item["class"] for item in setup_policy["accepted_classes"]] != list(cli.SUPPORTED_SETUP_FINDING_CLASSES):
        checks.append(("setup findings policy parity", ["setup findings classes drifted from setup_findings_policy.json"]))
    if setup_policy["accepted_classes"] != [cli._setup_finding_class_payload(name) for name in cli.SUPPORTED_SETUP_FINDING_CLASSES]:  # type: ignore[attr-defined]
        checks.append(("setup findings policy parity", ["setup finding class payloads drifted from setup_findings_policy.json"]))
    workflow_profiles = workflow_artifact_profiles_manifest()
    if workflow_profiles["default_profile"] != cli.DEFAULT_WORKFLOW_ARTIFACT_PROFILE:
        checks.append(("workflow artifact profiles parity", ["default workflow artifact profile drifted from workflow_artifact_profiles.json"]))
    if [item["profile"] for item in workflow_profiles["profiles"]] != list(cli.SUPPORTED_WORKFLOW_ARTIFACT_PROFILES):
        checks.append(("workflow artifact profiles parity", ["workflow artifact profiles drifted from workflow_artifact_profiles.json"]))
    if workflow_profiles["profiles"] != [cli._workflow_artifact_profile_payload(name) for name in cli.SUPPORTED_WORKFLOW_ARTIFACT_PROFILES]:  # type: ignore[attr-defined]
        checks.append(("workflow artifact profiles parity", ["workflow artifact payloads drifted from workflow_artifact_profiles.json"]))
    improvement_policy = improvement_latitude_policy_manifest()
    if improvement_policy["default_mode"] != cli.DEFAULT_IMPROVEMENT_LATITUDE:
        checks.append(("improvement latitude policy parity", ["default improvement latitude drifted from improvement_latitude_policy.json"]))
    if [item["mode"] for item in improvement_policy["modes"]] != list(cli.SUPPORTED_IMPROVEMENT_LATITUDES):
        checks.append(("improvement latitude policy parity", ["supported improvement latitude modes drifted from improvement_latitude_policy.json"]))
    if improvement_policy["modes"] != [cli._improvement_latitude_payload(name) for name in cli.SUPPORTED_IMPROVEMENT_LATITUDES]:  # type: ignore[attr-defined]
        checks.append(("improvement latitude policy parity", ["improvement latitude payloads drifted from improvement_latitude_policy.json"]))
    improvement_defaults = defaults_payload["improvement_latitude"]
    if improvement_defaults["default_mode"] != improvement_policy["default_mode"]:
        checks.append(("improvement latitude policy parity", ["defaults payload default_mode drifted from improvement_latitude_policy.json"]))
    if improvement_defaults["supported_modes"] != improvement_policy["modes"]:
        checks.append(("improvement latitude policy parity", ["defaults payload supported_modes drifted from improvement_latitude_policy.json"]))
    if improvement_defaults["mode_interpretation"] != improvement_policy["mode_interpretation"]:
        checks.append(("improvement latitude policy parity", ["defaults payload mode_interpretation drifted from improvement_latitude_policy.json"]))
    if improvement_defaults["examples"] != improvement_policy["examples"]:
        checks.append(("improvement latitude policy parity", ["defaults payload examples drifted from improvement_latitude_policy.json"]))
    if improvement_defaults["evidence_source"] != improvement_policy["evidence_source"]:
        checks.append(("improvement latitude policy parity", ["defaults payload evidence_source drifted from improvement_latitude_policy.json"]))
    if improvement_defaults["evidence_classes"] != improvement_policy["evidence_classes"]:
        checks.append(("improvement latitude policy parity", ["defaults payload evidence_classes drifted from improvement_latitude_policy.json"]))
    optimization_policy = optimization_bias_policy_manifest()
    if optimization_policy["default_mode"] != cli.DEFAULT_OPTIMIZATION_BIAS:
        checks.append(("optimization bias policy parity", ["default optimization bias drifted from optimization_bias_policy.json"]))
    if [item["mode"] for item in optimization_policy["modes"]] != list(cli.SUPPORTED_OPTIMIZATION_BIASES):
        checks.append(("optimization bias policy parity", ["supported optimization bias modes drifted from optimization_bias_policy.json"]))
    if optimization_policy["modes"] != [cli._optimization_bias_payload(name) for name in cli.SUPPORTED_OPTIMIZATION_BIASES]:  # type: ignore[attr-defined]
        checks.append(("optimization bias policy parity", ["optimization bias payloads drifted from optimization_bias_policy.json"]))
    optimization_defaults = defaults_payload["optimization_bias"]
    if optimization_defaults["default_mode"] != optimization_policy["default_mode"]:
        checks.append(("optimization bias policy parity", ["defaults payload default_mode drifted from optimization_bias_policy.json"]))
    if optimization_defaults["supported_modes"] != optimization_policy["modes"]:
        checks.append(("optimization bias policy parity", ["defaults payload supported_modes drifted from optimization_bias_policy.json"]))
    if optimization_defaults["surface_boundary"] != optimization_policy["surface_boundary"]:
        checks.append(("optimization bias policy parity", ["defaults payload surface_boundary drifted from optimization_bias_policy.json"]))
    if optimization_defaults["must_not_change"] != optimization_policy["must_not_change"]:
        checks.append(("optimization bias policy parity", ["defaults payload must_not_change drifted from optimization_bias_policy.json"]))
    repo_friction_policy = repo_friction_policy_manifest()
    if cli._workspace_self_adaptation_payload() != repo_friction_policy["workspace_self_adaptation"]:  # type: ignore[attr-defined]
        checks.append(("repo friction policy parity", ["workspace self adaptation payload drifted from repo_friction_policy.json"]))
    if cli._friction_response_order_payload() != repo_friction_policy["friction_response_order"]:  # type: ignore[attr-defined]
        checks.append(("repo friction policy parity", ["friction response order drifted from repo_friction_policy.json"]))
    if cli._workspace_self_adaptation_guardrail_payload() != repo_friction_policy["workspace_self_adaptation_guardrail"]:  # type: ignore[attr-defined]
        checks.append(("repo friction policy parity", ["workspace self adaptation guardrail drifted from repo_friction_policy.json"]))
    if cli._repo_directed_improvement_evidence_threshold_payload() != repo_friction_policy["repo_directed_improvement_threshold"]:  # type: ignore[attr-defined]
        checks.append(("repo friction policy parity", ["repo-directed improvement threshold drifted from repo_friction_policy.json"]))
    if cli._validation_friction_payload() != repo_friction_policy["validation_friction"]:  # type: ignore[attr-defined]
        checks.append(("repo friction policy parity", ["validation friction payload drifted from repo_friction_policy.json"]))
    if cli._improvement_boundary_test_payload() != repo_friction_policy["improvement_boundary_test"]:  # type: ignore[attr-defined]
        checks.append(("repo friction policy parity", ["improvement boundary test drifted from repo_friction_policy.json"]))
    if improvement_defaults["workspace_self_adaptation"] != repo_friction_policy["workspace_self_adaptation"]:
        checks.append(("repo friction policy parity", ["defaults payload workspace_self_adaptation drifted from repo_friction_policy.json"]))
    if improvement_defaults["friction_response_order"] != repo_friction_policy["friction_response_order"]:
        checks.append(("repo friction policy parity", ["defaults payload friction_response_order drifted from repo_friction_policy.json"]))
    if improvement_defaults["guardrail_test"] != repo_friction_policy["workspace_self_adaptation_guardrail"]:
        checks.append(("repo friction policy parity", ["defaults payload guardrail_test drifted from repo_friction_policy.json"]))
    if improvement_defaults["repo_directed_improvement_threshold"] != repo_friction_policy["repo_directed_improvement_threshold"]:
        checks.append(("repo friction policy parity", ["defaults payload repo_directed_improvement_threshold drifted from repo_friction_policy.json"]))
    if improvement_defaults["validation_friction"] != repo_friction_policy["validation_friction"]:
        checks.append(("repo friction policy parity", ["defaults payload validation_friction drifted from repo_friction_policy.json"]))
    if improvement_defaults["decision_test"] != repo_friction_policy["improvement_boundary_test"]:
        checks.append(("repo friction policy parity", ["defaults payload decision_test drifted from repo_friction_policy.json"]))
    preflight_policy = preflight_policy_manifest()
    if sorted(cli.HIGH_RISK_COMMANDS) != sorted(preflight_policy["high_risk_commands"]):
        checks.append(("preflight policy parity", ["high-risk command set drifted from preflight_policy.json"]))
    if cli.PREFLIGHT_TOKEN_PREFIX != preflight_policy["token"]["prefix"]:
        checks.append(("preflight policy parity", ["preflight token prefix drifted from preflight_policy.json"]))
    if cli.DEFAULT_PREFLIGHT_MAX_AGE_SECONDS != preflight_policy["default_max_age_seconds"]:
        checks.append(("preflight policy parity", ["default preflight max age drifted from preflight_policy.json"]))
    if cli._PREFLIGHT_STRICT_GATE_POLICY != preflight_policy["strict_gate"]:  # type: ignore[attr-defined]
        checks.append(("preflight policy parity", ["strict-gate policy drifted from preflight_policy.json"]))
    module_registry = module_registry_manifest()
    if {name: list(args) for name, args in cli.MODULE_COMMAND_ARGS.items()} != module_registry["module_command_args"]:
        checks.append(("module registry parity", ["module command args drifted from module_registry.json"]))
    descriptors = cli._module_operations()  # type: ignore[attr-defined]
    expected_module_names = [item["name"] for item in module_registry["modules"]]
    if cli._ordered_module_names(descriptors) != expected_module_names:  # type: ignore[attr-defined]
        checks.append(("module registry parity", ["ordered module names drifted from module_registry.json"]))
    live_registry = cli._module_registry(descriptors=descriptors, target_root=None)  # type: ignore[attr-defined]
    live_registry_payload = [
        {
            "name": entry.name,
            "description": entry.description,
            "selection_rank": descriptors[entry.name].selection_rank,
            "kind": entry.kind,
            "default_enabled": entry.default_enabled,
            "install_signals": [path.as_posix() for path in entry.install_signals],
            "workflow_surfaces": [path.as_posix() for path in entry.workflow_surfaces],
            "generated_artifacts": [path.as_posix() for path in entry.generated_artifacts],
            "startup_steps": list(descriptors[entry.name].startup_steps),
            "sources_of_truth": list(descriptors[entry.name].sources_of_truth),
            "root_agents_cleanup_blocks": [
                {
                    "block": block.block,
                    "start_marker": block.start_marker,
                    "end_marker": block.end_marker,
                    "label": block.label,
                }
                for block in descriptors[entry.name].root_agents_cleanup_blocks
            ],
            "capabilities": list(entry.capabilities),
            "dependencies": list(entry.dependencies),
            "conflicts": list(entry.conflicts),
            "participation": entry.participation,
            "components": cli._MODULE_REGISTRY_ENTRIES[entry.name]["components"],  # type: ignore[attr-defined]
            "result_contract": {
                "schema_version": entry.result_contract.schema_version,
                "guaranteed_fields": list(entry.result_contract.guaranteed_fields),
                "action_fields": list(entry.result_contract.action_fields),
                "warning_fields": list(entry.result_contract.warning_fields),
            },
        }
        for entry in live_registry
    ]
    if live_registry_payload != module_registry["modules"]:
        checks.append(("module registry parity", ["live module registry drifted from module_registry.json"]))
    parser_manifest = cli_commands_manifest()
    parser_snapshot = _parser_snapshot(generated_workspace_cli.build_parser())
    generated_root_commands = set(generated_workspace_cli.generated_command_names())  # type: ignore[attr-defined]
    manifest_command_names = {str(spec["name"]) for spec in parser_manifest["commands"]}
    if not generated_root_commands >= manifest_command_names:
        expected_parser_snapshot = [
            _resolved_command_manifest(spec) for spec in parser_manifest["commands"] if str(spec["name"]) not in generated_root_commands
        ]
        if parser_snapshot != expected_parser_snapshot:
            checks.append(
                ("cli command manifest parity", ["argparse command/options/defaults drifted from cli_commands.json or cli_option_groups.json"])
            )
        if [item["name"] for item in parser_snapshot] != [item["name"] for item in expected_parser_snapshot]:
            checks.append(("cli command manifest parity", ["resolved handwritten command ordering drifted from cli_commands.json"]))
    if "modules" not in cli._command_suggestions("moduls"):  # type: ignore[attr-defined]
        checks.append(("cli command manifest parity", ["command suggestions no longer derive the expected known commands"]))
    workspace_config_schema = contract_schema("workspace_config.schema.json")
    local_override_schema = contract_schema("workspace_local_override.schema.json")
    agent_instructions_schema = workspace_config_schema["properties"]["workspace"]["properties"]["agent_instructions_file"]
    if agent_instructions_schema.get("type") != "string" or agent_instructions_schema.get("minLength") != 1:
        checks.append(("workspace config schema parity", ["agent_instructions_file must accept any non-empty string path"]))
    if workspace_config_schema["properties"]["workspace"]["properties"]["workflow_artifact_profile"]["enum"] != list(
        cli.SUPPORTED_WORKFLOW_ARTIFACT_PROFILES
    ):
        checks.append(("workspace config schema parity", ["workflow_artifact_profile enum drifted from cli supported profiles"]))
    if workspace_config_schema["properties"]["workspace"]["properties"]["improvement_latitude"]["enum"] != list(
        cli.SUPPORTED_IMPROVEMENT_LATITUDES
    ):
        checks.append(("workspace config schema parity", ["improvement_latitude enum drifted from cli supported modes"]))
    if workspace_config_schema["properties"]["workspace"]["properties"]["optimization_bias"]["enum"] != list(
        cli.SUPPORTED_OPTIMIZATION_BIASES
    ):
        checks.append(("workspace config schema parity", ["optimization_bias enum drifted from cli supported modes"]))
    workflow_obligation_schema = workspace_config_schema["$defs"][
        workspace_config_schema["properties"]["workflow_obligations"]["patternProperties"]["^.+$"]["$ref"].split("/")[-1]
    ]
    if workflow_obligation_schema["properties"]["stage"]["enum"] != list(cli.SUPPORTED_WORKFLOW_OBLIGATION_STAGES):
        checks.append(("workspace config schema parity", ["workflow obligation stages drifted from cli supported values"]))
    local_runtime_properties = local_override_schema["properties"]["runtime"]["properties"]
    expected_runtime = {
        "supports_internal_delegation",
        "strong_planner_available",
        "cheap_bounded_executor_available",
    }
    if set(local_runtime_properties) != expected_runtime:
        checks.append(("workspace local override schema parity", ["runtime properties drifted from supported local override fields"]))
    if set(local_override_schema["properties"]["handoff"]["properties"]) != {"prefer_internal_delegation_when_available"}:
        checks.append(("workspace local override schema parity", ["handoff properties drifted from supported local override fields"]))
    if set(local_override_schema["properties"]["safety"]["properties"]) != {
        "safe_to_auto_run_commands",
        "requires_human_verification_on_pr",
    }:
        checks.append(("workspace local override schema parity", ["safety properties drifted from supported local override fields"]))
    delegation_target_schema = local_override_schema["properties"]["delegation_targets"]["patternProperties"]["^.+$"]
    if delegation_target_schema["properties"]["strength"]["enum"] != list(cli.SUPPORTED_DELEGATION_TARGET_STRENGTHS):
        checks.append(
            ("workspace local override schema parity", ["delegation target strengths drifted from supported local override fields"])
        )
    if delegation_target_schema["properties"]["execution_methods"]["items"]["enum"] != list(
        cli.SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS
    ):
        checks.append(
            ("workspace local override schema parity", ["delegation target execution methods drifted from supported local override fields"])
        )
    delegation_outcome_schema = contract_schema("delegation_outcomes.schema.json")
    record_schema = delegation_outcome_schema["properties"]["records"]["items"]
    if record_schema["properties"]["outcome"]["enum"] != list(cli.SUPPORTED_DELEGATION_OUTCOMES):
        checks.append(("delegation outcomes schema parity", ["delegation outcome enums drifted from cli supported values"]))
    if record_schema["properties"]["handoff_sufficiency"]["enum"] != list(cli.SUPPORTED_HANDOFF_SUFFICIENCY):
        checks.append(("delegation outcomes schema parity", ["handoff sufficiency enums drifted from cli supported values"]))
    if record_schema["properties"]["review_burden"]["enum"] != list(cli.SUPPORTED_REVIEW_BURDENS):
        checks.append(("delegation outcomes schema parity", ["review burden enums drifted from cli supported values"]))
    setup_findings_schema = contract_schema("setup_findings.schema.json")
    if setup_findings_schema["properties"]["kind"]["const"] != cli.SETUP_FINDINGS_KIND:
        checks.append(("setup findings schema parity", ["setup findings kind drifted from cli supported value"]))
    finding_schema = setup_findings_schema["properties"]["findings"]["items"]
    if finding_schema["properties"]["class"]["enum"] != list(cli.SUPPORTED_SETUP_FINDING_CLASSES):
        checks.append(("setup findings schema parity", ["setup findings classes drifted from cli supported values"]))
    module_capability_schema = contract_schema("module_capability.schema.json")
    module_capability_properties = module_capability_schema["properties"]
    descriptor = cli._module_operations()["planning"]  # type: ignore[attr-defined]
    expected_module_capability_properties = {
        "name",
        "description",
        "selection_rank",
        "kind",
        "default_enabled",
        "capabilities",
        "commands",
        "command_args",
        "install_signals",
        "workflow_surfaces",
        "generated_artifacts",
        "dependencies",
        "conflicts",
        "startup_steps",
        "sources_of_truth",
        "result_contract",
    }
    if set(module_capability_properties) != expected_module_capability_properties:
        checks.append(("module capability schema parity", ["module capability properties drifted from supported descriptor fields"]))
    if set(module_capability_schema["required"]) != {
        "name",
        "description",
        "capabilities",
        "commands",
        "install_signals",
        "workflow_surfaces",
        "result_contract",
    }:
        checks.append(("module capability schema parity", ["required module capability fields drifted from the supported contract"]))
    if set(module_capability_properties["command_args"]["patternProperties"]["^.+$"]["items"]["enum"]) != {
        "target",
        "dry_run",
        "force",
    }:
        checks.append(("module capability schema parity", ["command arg names drifted from supported module invocation args"]))
    if set(_sample_module_capability_payload()) != expected_module_capability_properties:
        checks.append(("module capability schema parity", ["sample module capability payload drifted from the supported descriptor fields"]))
    if set(_sample_module_capability_payload()["commands"]) != set(descriptor.commands):
        checks.append(("module capability schema parity", ["sample module capability commands drifted from the live module descriptor"]))

    failures = [(name, errors) for name, errors in checks if errors]
    if failures:
        print("Contract tooling health report")
        for name, errors in failures:
            for error in errors:
                print(f"- [{name}] {error}")
        return 1
    if args.quiet_success:
        print("[ok] contract tooling")
    else:
        generated_adapter_statuses, _ = _generated_command_adapter_statuses()
        print("Contract tooling health report")
        print("- No contract-tooling drift warnings detected.")
        print("- Command-generation schema boundary: packaged command_package_ir.schema.json mirrors workspace validation schema.")
        print("- Generated command adapter status:")
        for status in generated_adapter_statuses:
            commands = ", ".join(str(command) for command in status["command_surfaces"])
            print(
                "  - "
                f"{status['program']} -> {status['path']}: {status['status']}; "
                f"commands: {commands}; "
                f"source: {status['source_contract']}; "
                f"direct_edit_detected: {str(status['direct_edit_detected']).lower()}; "
                f"edit command interface in {status['where_to_edit']['command_interface']}; "
                f"edit runtime behavior in {status['where_to_edit']['runtime_behavior']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
