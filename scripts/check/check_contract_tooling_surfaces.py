from __future__ import annotations

import argparse
import importlib.util
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace import cli
from agentic_workspace.contract_tooling import (
    authority_markers_manifest,
    cli_commands_manifest,
    cli_option_groups_manifest,
    command_adapter_generation_manifest,
    compact_contract_manifest,
    conformance_contract_manifest,
    conformance_contracts_manifest,
    context_templates_manifest,
    contract_inventory_manifest,
    contract_schema,
    improvement_latitude_policy_manifest,
    module_registry_manifest,
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
    repo_friction_policy_manifest,
    report_contract_manifest,
    setup_findings_policy_manifest,
    workflow_artifact_profiles_manifest,
    workflow_definition_format_manifest,
    workspace_surfaces_manifest,
)
from agentic_workspace.generated_command_adapters import GENERATED_COMMAND_ADAPTERS_BY_COMMAND

REPO_ROOT = Path(__file__).resolve().parents[2]


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
            "default_preset": "full",
            "agent_instructions_file": "AGENTS.md",
            "workflow_artifact_profile": "repo-owned",
            "improvement_latitude": "balanced",
            "optimization_bias": "agent-efficiency",
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
                "path": "src/agentic_workspace/cli.py",
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
        "include_in_full_preset": descriptor.include_in_full_preset,
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
            changed_paths=["src/agentic_workspace/cli.py"],
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
                "src/agentic_workspace/cli.py",
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
    primitives = payload.get("primitives")
    if not isinstance(primitives, list) or not primitives:
        errors.append("operation_primitives.json must contain at least one primitive")
        return errors
    seen_ids: set[str] = set()
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
        if command_manifest.get("program") != command.get("program"):
            errors.append(f"command adapter {adapter_id} program drifted from cli_commands.json")
        if command_name not in known_commands:
            errors.append(f"command adapter {adapter_id} references unknown command {command_name}")
        operation_id = str(operation_ref.get("id", ""))
        operation_registry_ref = operation_refs.get(operation_id)
        if operation_registry_ref is None:
            errors.append(f"command adapter {adapter_id} references unknown operation {operation_id}")
            continue
        if operation_ref.get("path") != operation_registry_ref.get("path"):
            errors.append(f"command adapter {adapter_id} operation path drifted from operation registry")
        operation = operation_manifest(str(operation_ref.get("path", "")))
        operation_command = operation.get("command_surface", {}).get("command")
        if operation_command != command_name:
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
                errors.append(f"command adapter {adapter_id} conformance ref {conformance_ref} targets a different operation")
    return errors


def _validate_generated_command_adapter_output() -> list[str]:
    errors: list[str] = []
    repo_root = Path(__file__).resolve().parents[2]
    generator_path = repo_root / "scripts" / "generate" / "generate_command_adapters.py"
    generated_path = repo_root / "src" / "agentic_workspace" / "generated_command_adapters.py"
    spec = importlib.util.spec_from_file_location("generate_command_adapters", generator_path)
    if spec is None or spec.loader is None:
        return [f"generator layer: cannot load {generator_path.relative_to(repo_root).as_posix()}"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = module._render_generated_module(command_adapter_generation_manifest())
    current = generated_path.read_text(encoding="utf-8") if generated_path.exists() else ""
    if current != expected:
        errors.append(
            "generated adapter layer: src/agentic_workspace/generated_command_adapters.py is stale; "
            "run uv run python scripts/generate/generate_command_adapters.py"
        )

    expected_by_command = {
        str(adapter["command"]["name"]): {
            "id": adapter["id"],
            "status": adapter["status"],
            "operation_id": adapter["operation_ref"]["id"],
            "runtime_binding": adapter["runtime_binding"],
            "effect_hints": adapter["effect_hints"],
            "schemas": adapter["schemas"],
            "conformance_refs": adapter["conformance_refs"],
        }
        for adapter in command_adapter_generation_manifest()["adapters"]
    }
    for command_name, expected_adapter in expected_by_command.items():
        actual_adapter = GENERATED_COMMAND_ADAPTERS_BY_COMMAND.get(command_name)
        if actual_adapter is None:
            errors.append(f"generated adapter layer: missing generated adapter for command {command_name}")
            continue
        for key, expected_value in expected_adapter.items():
            if actual_adapter.get(key) != expected_value:
                errors.append(f"generated adapter layer: {command_name} {key} drifted from command_adapter_generation.json")
    for command_name in set(GENERATED_COMMAND_ADAPTERS_BY_COMMAND) - set(expected_by_command):
        errors.append(f"generated adapter layer: unexpected generated adapter for command {command_name}")
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
            for subcommand_spec in subcommands:
                surfaces.add((command_name, str(subcommand_spec["name"])))
            continue
        surfaces.add((command_name, None))
    return surfaces


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
            _validate_operation_registry(operation_contracts_manifest()),
        ),
        (
            "conformance contracts registry",
            _validate_conformance_registry(conformance_contracts_manifest()),
        ),
        (
            "command adapter generation manifest",
            _validate(command_adapter_generation_manifest(), "command_adapter_generation.schema.json")
            + _validate_command_adapter_generation(command_adapter_generation_manifest()),
        ),
        (
            "generated command adapter output",
            _validate_generated_command_adapter_output(),
        ),
        (
            "operation primitives registry",
            _validate_operation_primitives(operation_primitives_manifest()),
        ),
        (
            "python extraction map",
            _validate(python_extraction_map_manifest(), "python_extraction_map.schema.json"),
        ),
        (
            "python contract consumption policy",
            _validate(python_contract_consumption_manifest(), "python_contract_consumption.schema.json"),
        ),
        (
            "python runtime boundary",
            _validate(python_runtime_boundary_manifest(), "python_runtime_boundary.schema.json"),
        ),
        (
            "authority marker parity",
            _validate_authority_marker_parity(authority_markers_manifest()),
        ),
    ]

    operation_contracts = operation_contracts_manifest()
    operation_primitives = operation_primitives_manifest()
    known_commands = {command["name"] for command in cli_commands_manifest()["commands"]}
    known_primitives = {primitive["id"] for primitive in operation_primitives["primitives"]}
    operation_surfaces: list[tuple[str, str | None]] = []
    for operation_ref in operation_contracts["operations"]:
        operation = operation_manifest(operation_ref["path"])
        command_surface = operation["command_surface"]
        operation_surfaces.append((str(command_surface["command"]), command_surface.get("subcommand")))
        checks.append(
            (
                f"operation contract {operation_ref['id']}",
                _validate(operation, "operation.schema.json"),
            )
        )
        if operation_ref["command"] not in known_commands:
            checks.append(("operation command parity", [f"unknown command for operation {operation_ref['id']}"]))
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
    consumption_policy = python_contract_consumption_manifest()
    validation_lane_ids = {lane["id"] for lane in defaults_payload["validation"]["lanes"]}
    proof_rule_lanes = {rule["lane"] for rule in proof_rules["rules"]} | {proof_rules["fallback_lane"]}
    unknown_rule_lanes = sorted(proof_rule_lanes - validation_lane_ids)
    if unknown_rule_lanes:
        checks.append(("proof selection rules parity", [f"unknown validation lane(s): {', '.join(unknown_rule_lanes)}"]))
    expected_validated_contracts = {
        ("proof_selection_rules.json", "proof_selection_rules.schema.json", "agentic_workspace.cli:_proof_selection_for_changed_paths"),
        ("authority_markers.json", "authority_markers.schema.json", "agentic_workspace.cli:_authority_marker_for_path"),
        ("context_templates.json", "context_templates.schema.json", "agentic_workspace.cli:_start_payload"),
        ("context_templates.json", "context_templates.schema.json", "agentic_workspace.cli:_implement_payload"),
        (
            "command_adapter_generation.json",
            "command_adapter_generation.schema.json",
            "scripts/check/check_contract_tooling_surfaces.py",
        ),
    }
    actual_validated_contracts = {
        (entry["contract"], entry["schema"], entry["consumer"]) for entry in consumption_policy["validated_at_consumption"]
    }
    if expected_validated_contracts - actual_validated_contracts:
        missing_consumers = sorted(consumer for _, _, consumer in expected_validated_contracts - actual_validated_contracts)
        checks.append(
            (
                "python contract consumption parity",
                [f"validated contract consumers are not recorded: {', '.join(missing_consumers)}"],
            )
        )
    if cli._reporting_schema_payload() != report_contract_manifest():  # type: ignore[attr-defined]
        checks.append(("report contract parity", ["reporting schema payload drifted from report_contract.json"]))
    workspace_surfaces = workspace_surfaces_manifest()
    if [path.as_posix() for path in cli.WORKSPACE_PAYLOAD_FILES] != workspace_surfaces["payload_files"]:
        checks.append(("workspace surfaces parity", ["workspace payload files drifted from workspace_surfaces.json"]))
    if cli.SYSTEM_INTENT_MIRROR_KIND != workspace_surfaces["system_intent_mirror_kind"]:
        checks.append(("workspace surfaces parity", ["system intent mirror kind drifted from workspace_surfaces.json"]))
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
            "include_in_full_preset": descriptors[entry.name].include_in_full_preset,
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
    parser_snapshot = _parser_snapshot(cli.build_parser())
    expected_parser_snapshot = [_resolved_command_manifest(spec) for spec in parser_manifest["commands"]]
    if parser_snapshot != expected_parser_snapshot:
        checks.append(("cli command manifest parity", ["argparse command/options/defaults drifted from cli_commands.json or cli_option_groups.json"]))
    if [item["name"] for item in parser_manifest["commands"]] != [item["name"] for item in expected_parser_snapshot]:
        checks.append(("cli command manifest parity", ["resolved command ordering drifted from cli_commands.json"]))
    if "modules" not in cli._command_suggestions("moduls"):  # type: ignore[attr-defined]
        checks.append(("cli command manifest parity", ["command suggestions no longer derive the expected known commands"]))
    workspace_config_schema = contract_schema("workspace_config.schema.json")
    local_override_schema = contract_schema("workspace_local_override.schema.json")
    if workspace_config_schema["properties"]["workspace"]["properties"]["agent_instructions_file"]["enum"] != list(
        cli.SUPPORTED_AGENT_INSTRUCTIONS_FILES
    ):
        checks.append(("workspace config schema parity", ["agent_instructions_file enum drifted from cli supported files"]))
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
        "include_in_full_preset",
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
        print("Contract tooling health report")
        print("- No contract-tooling drift warnings detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
