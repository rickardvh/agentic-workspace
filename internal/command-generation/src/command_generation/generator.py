from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GeneratedOutput:
    path: Path
    content: str


def _json_block(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _maturity_levels(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policy = manifest["generation_policy"]["generated_package_maturity"]
    return {level["id"]: level for level in policy["levels"]}


def _is_runnable_typescript_target(target: dict[str, Any]) -> bool:
    return target.get("maturity_level_ref") in {
        "runnable-read-only-adapter",
        "runtime-backed-read-only-adapter",
        "weak-agent-safe-adapter",
        "mutation-capable-adapter",
    }


def _is_weak_agent_safe_typescript_target(target: dict[str, Any]) -> bool:
    return target.get("maturity_level_ref") == "weak-agent-safe-adapter"


def _is_weak_agent_safe_python_target(target: dict[str, Any]) -> bool:
    return target.get("kind") == "python" and target.get("maturity_level_ref") == "weak-agent-safe-adapter"


def _is_runtime_backed_python_target(target: dict[str, Any]) -> bool:
    return target.get("kind") == "python" and target.get("maturity_level_ref") in {
        "runtime-backed-read-only-adapter",
        "weak-agent-safe-adapter",
        "mutation-capable-adapter",
    }


def _weak_agent_routing_for_target(target: dict[str, Any], maturity_levels: dict[str, dict[str, Any]]) -> str:
    maturity = maturity_levels[str(target["maturity_level_ref"])]
    return str(maturity["weak_agent_routing"])


def _runtime_command_for_package(package: dict[str, Any], runtime_binding: dict[str, Any]) -> str:
    python_runtime_binding = package.get("python_runtime_binding", {})
    if isinstance(python_runtime_binding, dict) and python_runtime_binding.get("default_runtime_command"):
        return str(python_runtime_binding["default_runtime_command"])
    return str(runtime_binding["default_runtime_command"])


def _runtime_module_file_for_package(package: dict[str, Any]) -> str:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return ""
    configured = str(binding.get("runtime_module_file") or "")
    return configured.removesuffix(".py")


def _version_metadata_for_package(package: dict[str, Any]) -> dict[str, Any]:
    metadata = package.get("version_metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _version_fallback_for_package(package: dict[str, Any]) -> str:
    return str(_version_metadata_for_package(package).get("fallback_version") or "0.0.0")


def _operation_executor_binding(package: dict[str, Any]) -> dict[str, Any]:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return {}
    operation_executor = binding.get("operation_executor", {})
    return operation_executor if isinstance(operation_executor, dict) else {}


def _local_runtime_bindings(package: dict[str, Any]) -> list[dict[str, Any]]:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return []
    return [item for item in binding.get("local_runtime_bindings", []) if isinstance(item, dict)]


def _python_resource_copies(package: dict[str, Any]) -> list[dict[str, Any]]:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return []
    return [item for item in binding.get("resource_copies", []) if isinstance(item, dict)]


def _local_runtime_binding_for_import(package: dict[str, Any], import_module: str) -> dict[str, Any] | None:
    for binding in _local_runtime_bindings(package):
        if str(binding.get("source_import_module") or "") == import_module:
            return binding
    return None


def _command_module_import_for_binding(binding: dict[str, Any]) -> str:
    return f"..{str(binding['module_file'])}"


def _operation_executor_import_for_binding(binding: dict[str, Any]) -> str:
    module_file = str(binding["module_file"])
    if module_file.startswith("primitives."):
        return f".{module_file.removeprefix('primitives.')}"
    return f"..{module_file}"


def _python_adapter_commands(package: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        command for command in package["commands"] if command.get("status") == "generated" and isinstance(command.get("interface"), dict)
    ]


def _interface_operation_refs(interface: dict[str, Any], inherited_operation_ref: dict[str, Any]) -> list[dict[str, Any]]:
    operation_ref = interface.get("operation_ref", inherited_operation_ref)
    current_operation_ref = operation_ref if isinstance(operation_ref, dict) else inherited_operation_ref
    refs = [current_operation_ref]
    for subcommand in interface.get("subcommands", []):
        if isinstance(subcommand, dict):
            refs.extend(_interface_operation_refs(subcommand, current_operation_ref))
    return refs


def _command_operation_refs(command: dict[str, Any]) -> list[dict[str, Any]]:
    operation_ref = command.get("operation_ref", {})
    interface = command.get("interface", {})
    if not isinstance(operation_ref, dict):
        return []
    if not isinstance(interface, dict):
        return [operation_ref]
    return _interface_operation_refs(interface, operation_ref)


def _python_adapter_command_payload(package: dict[str, Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for command in _python_adapter_commands(package):
        interface = dict(command["interface"])
        operation_ref = dict(command["operation_ref"])
        payload.append(
            {
                "adapter_id": command["adapter_id"],
                "operation_id": operation_ref["id"],
                "operation_path": operation_ref["path"],
                "interface": interface,
            }
        )
    return payload


def _runtime_consumed_operation_outputs(
    package: dict[str, Any],
    *,
    repo_root: Path,
    root: Path,
) -> list[GeneratedOutput]:
    outputs: list[GeneratedOutput] = []
    emitted: set[str] = set()
    operation_contract_root = repo_root / str(package["operation_contract_root"])
    for command in _python_adapter_commands(package):
        for operation_ref in _command_operation_refs(command):
            operation_path = str(operation_ref.get("path", ""))
            if not operation_path or operation_path in emitted:
                continue
            source = operation_contract_root / operation_path
            if not source.is_file():
                continue
            operation = json.loads(source.read_text(encoding="utf-8"))
            ir_plan = operation.get("ir_plan", {})
            if not isinstance(ir_plan, dict) or ir_plan.get("status") not in {"representative", "complete"}:
                continue
            emitted.add(operation_path)
            outputs.append(GeneratedOutput(root / operation_path, _json_block(operation) + "\n"))
    return outputs


def _python_resource_copy_outputs(
    package: dict[str, Any],
    *,
    repo_root: Path,
    root: Path,
) -> list[GeneratedOutput]:
    outputs: list[GeneratedOutput] = []
    for copy in _python_resource_copies(package):
        source_root = repo_root / str(copy["source_root"])
        generated_root = root / str(copy["generated_root"])
        required_marker = str(copy.get("required_marker") or "")
        if required_marker and not (source_root / required_marker).is_file():
            raise FileNotFoundError(f"missing required resource marker: {(source_root / required_marker).as_posix()}")
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            relative = source.relative_to(source_root)
            outputs.append(GeneratedOutput(generated_root / relative, source.read_text(encoding="utf-8")))
    return outputs


def _typescript_native_operation_ids(package: dict[str, Any]) -> set[str]:
    operation_ids: set[str] = set()
    for command in _python_adapter_commands(package):
        for operation_ref in _command_operation_refs(command):
            operation_id = str(operation_ref.get("id", "")).strip()
            if operation_id:
                operation_ids.add(operation_id)
    return operation_ids


def _typescript_resource_copy_outputs(
    package: dict[str, Any],
    *,
    repo_root: Path,
    root: Path,
) -> list[GeneratedOutput]:
    outputs: list[GeneratedOutput] = []
    if not _typescript_native_operation_ids(package):
        return outputs
    for copy in _python_resource_copies(package):
        source_root = repo_root / str(copy["source_root"])
        generated_root = root / "resources" / str(copy["generated_root"])
        required_marker = str(copy.get("required_marker") or "")
        if required_marker and not (source_root / required_marker).is_file():
            raise FileNotFoundError(f"missing required resource marker: {(source_root / required_marker).as_posix()}")
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            relative = source.relative_to(source_root)
            outputs.append(GeneratedOutput(generated_root / relative, source.read_text(encoding="utf-8")))

    operation_contract_root = repo_root / str(package["operation_contract_root"])
    native_ids = _typescript_native_operation_ids(package)
    emitted_operation_paths: set[str] = set()
    for command in _python_adapter_commands(package):
        for operation_ref in _command_operation_refs(command):
            operation_id = str(operation_ref.get("id", ""))
            operation_path = str(operation_ref.get("path", ""))
            if operation_id not in native_ids or not operation_path or operation_path in emitted_operation_paths:
                continue
            source = operation_contract_root / operation_path
            operation = (
                json.loads(source.read_text(encoding="utf-8"))
                if source.is_file()
                else _typescript_minimal_operation(operation_id=operation_id)
            )
            emitted_operation_paths.add(operation_path)
            outputs.append(
                GeneratedOutput(
                    root / "resources" / operation_path,
                    _json_block(_typescript_executable_operation(operation, operation_id=operation_id)) + "\n",
                )
            )
    return outputs


def _typescript_minimal_operation(*, operation_id: str) -> dict[str, Any]:
    return {
        "schema_version": "agentic-workspace/operation/v1",
        "id": operation_id,
        "summary": "Generated TypeScript native operation binding.",
        "migration_status": "generated-typescript-native",
    }


def _typescript_executable_operation(operation: dict[str, Any], *, operation_id: str) -> dict[str, Any]:
    ir_plan = operation.get("ir_plan", {})
    steps = ir_plan.get("steps", []) if isinstance(ir_plan, dict) else []
    if isinstance(steps, list) and steps:
        return operation
    executable = dict(operation)
    executable["ir_plan"] = {
        "status": "complete",
        "summary": "Generated TypeScript native runtime binding for a command whose source operation has not yet been decomposed into portable IR.",
        "steps": [
            {
                "id": "execute_typescript_domain_operation",
                "uses": "typescript.domain.execute",
                "description": "Execute the operation through the generated TypeScript domain operation table.",
                "arguments": {"operation_id": operation_id},
                "outputs": ["result"],
                "on_error": "fail",
            },
            {
                "id": "emit_output",
                "uses": "output.emit",
                "description": "Emit the TypeScript-native operation result.",
                "arguments": {},
                "outputs": ["emitted"],
                "on_error": "emit_usage_error",
            },
        ],
    }
    return executable


def _module_name_for_operation(operation_id: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in operation_id).strip("_")


def _python_commands_package_module(
    package: dict[str, Any],
    binding: dict[str, Any],
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    operation_executor = _operation_executor_binding(package)
    operation_ids = {str(operation_id) for operation_id in operation_executor.get("supported_operation_ids", [])}
    operation_ids.update(_direct_generated_operation_ids(package))
    direct_handlers = {
        str(handler["operation_id"]): handler for handler in binding.get("runtime_module_handlers", []) if isinstance(handler, dict)
    }
    operation_ids.update(direct_handlers)
    imports = []
    handler_items = []
    for operation_id in sorted(operation_ids):
        module_name = _module_name_for_operation(operation_id)
        imported_name = f"_command_{module_name}"
        imports.append(f"from . import {module_name} as {imported_name}")
        handler_items.append(f"    {operation_id!r}: {imported_name}.run,")
    return (
        '"""Generated command module registry.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command module changes belong in {source_path}.\n"
        f"# Regenerate with: {regenerate_command}\n\n"
        + "\n".join(imports)
        + "\n\n\nGENERATED_COMMAND_HANDLERS = {\n"
        + "\n".join(handler_items)
        + "\n}\n"
    )


def _python_command_module(
    package: dict[str, Any],
    operation_id: str,
    binding: dict[str, Any],
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    if _is_memory_list_skills_direct_projection(package, operation_id):
        return _python_memory_list_skills_command_module(
            package,
            operation_id,
            source_path=source_path,
            regenerate_command=regenerate_command,
        )
    if _is_memory_list_files_direct_projection(package, operation_id):
        return _python_memory_list_files_command_module(
            package,
            operation_id,
            source_path=source_path,
            regenerate_command=regenerate_command,
        )
    if _is_planning_list_files_direct_projection(package, operation_id):
        return _python_planning_list_files_command_module(
            package,
            operation_id,
            source_path=source_path,
            regenerate_command=regenerate_command,
        )
    operation_executor = _operation_executor_binding(package)
    direct_handlers = {
        str(handler["operation_id"]): handler for handler in binding.get("runtime_module_handlers", []) if isinstance(handler, dict)
    }
    if operation_id in direct_handlers:
        handler = direct_handlers[operation_id]
        import_module = str(handler["import_module"])
        imported_function = str(handler.get("function") or _runtime_adapter_function_name(operation_id))
        local_binding = _local_runtime_binding_for_import(package, import_module)
        if local_binding is not None:
            local_import = _command_module_import_for_binding(local_binding)
            run_body = f"    from {local_import} import {imported_function}\n\n    return {imported_function}(args)\n"
        else:
            run_body = f"    from {import_module} import {imported_function}\n\n    return {imported_function}(args)\n"
        support_imports = ""
    else:
        run_body = f"    return run_operation_ir(generated_operation_contract({operation_id!r}), args)\n"
        executor_module = str(operation_executor.get("module_file", "operation_executor"))
        support_imports = f"from ..cli import generated_operation_contract\nfrom ..{executor_module} import run_operation_ir\n"
    return (
        '"""Generated executable command projection.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Operation: {operation_id}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import argparse\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command behavior changes belong in {source_path} and the referenced operation contract.\n"
        f"# Regenerate with: {regenerate_command}\n\n"
        f"{support_imports}\n\n"
        "def run(args: argparse.Namespace) -> int:\n" + run_body
    )


def _is_memory_list_skills_direct_projection(package: dict[str, Any], operation_id: str) -> bool:
    return package.get("id") == "memory-bootstrap" and operation_id == "memory.list-skills.report"


def _is_memory_list_files_direct_projection(package: dict[str, Any], operation_id: str) -> bool:
    return package.get("id") == "memory-bootstrap" and operation_id == "memory.list-files.report"


def _is_planning_list_files_direct_projection(package: dict[str, Any], operation_id: str) -> bool:
    return package.get("id") == "planning-bootstrap" and operation_id == "planning.list-files.report"


def _direct_generated_operation_ids(package: dict[str, Any]) -> set[str]:
    if package.get("id") == "memory-bootstrap":
        return {"memory.list-files.report", "memory.list-skills.report"}
    if package.get("id") == "planning-bootstrap":
        return {"planning.list-files.report"}
    return set()


def _python_memory_direct_projection_header(
    package: dict[str, Any],
    operation_id: str,
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    return (
        '"""Generated executable command projection.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Operation: {operation_id}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
    )


def _python_planning_list_files_command_module(
    package: dict[str, Any],
    operation_id: str,
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    default_files = [
        "AGENTS.template.md",
        ".agentic-workspace/docs/execution-flow-contract.md",
        ".agentic-workspace/docs/system-intent-contract.md",
        ".agentic-workspace/docs/routing-contract.md",
        ".agentic-workspace/docs/minimum-operating-model.md",
        ".agentic-workspace/docs/lifecycle-and-config-contract.md",
        ".agentic-workspace/docs/workspace-config-contract.md",
        ".agentic-workspace/planning/execplans/README.md",
        ".agentic-workspace/planning/execplans/TEMPLATE.plan.json",
        ".agentic-workspace/planning/execplans/archive/README.md",
        ".agentic-workspace/planning/decompositions/README.md",
        ".agentic-workspace/planning/decompositions/TEMPLATE.decomposition.json",
        ".agentic-workspace/planning/schemas/planning-execplan.schema.json",
        ".agentic-workspace/planning/schemas/planning-decomposition.schema.json",
        ".agentic-workspace/planning/schemas/planning-review.schema.json",
        ".agentic-workspace/planning/schemas/planning-external-intent-evidence.schema.json",
        ".agentic-workspace/planning/schemas/planning-finished-work-evidence.schema.json",
        ".agentic-workspace/planning/UPGRADE-SOURCE.toml",
        ".agentic-workspace/planning/agent-manifest.json",
    ]
    optional_files = [
        ".agentic-workspace/docs/capability-contract.json",
        ".agentic-workspace/planning/reviews/README.md",
        ".agentic-workspace/planning/reviews/TEMPLATE.review.json",
        ".agentic-workspace/planning/upstream-task-intake.md",
        ".agentic-workspace/planning/pre-ingestion-refinement.md",
    ]
    return (
        _python_memory_direct_projection_header(
            package,
            operation_id,
            source_path=source_path,
            regenerate_command=regenerate_command,
        )
        + "import argparse\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "from ..primitives.resources import emit_json_or_lines, find_resource_root, list_resource_files\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command behavior changes belong in {source_path} and the referenced operation contract.\n"
        f"# Regenerate with: {regenerate_command}\n\n"
        f"DEFAULT_PAYLOAD_FILES = {default_files!r}\n"
        f"OPTIONAL_PAYLOAD_FILES = {optional_files!r}\n"
        "OPTIONAL_ENABLE_COMMANDS = (\n"
        "    'agentic-planning install --include-optional',\n"
        "    'agentic-planning adopt --include-optional',\n"
        "    'agentic-planning upgrade --include-optional',\n"
        ")\n\n\n"
        "PAYLOAD_ROOT_CANDIDATES = (('_payload', 'AGENTS.template.md'), ('packages/planning/bootstrap', 'AGENTS.template.md'))\n"
        "SKILLS_ROOT_CANDIDATES = (('_skills', 'REGISTRY.json'), ('packages/planning/skills', 'REGISTRY.json'))\n\n\n"
        "def _assemble_payload(payload_root: Path, skills_root: Path) -> dict[str, Any]:\n"
        "    return {\n"
        "        'files': list_resource_files(payload_root),\n"
        "        'default_files': list(DEFAULT_PAYLOAD_FILES),\n"
        "        'optional_files': list(OPTIONAL_PAYLOAD_FILES),\n"
        "        'bundled_skill_files': list_resource_files(skills_root),\n"
        "        'optional_enable_commands': list(OPTIONAL_ENABLE_COMMANDS),\n"
        "    }\n\n\n"
        "def run(args: argparse.Namespace) -> int:\n"
        "    payload_root = find_resource_root(__file__, PAYLOAD_ROOT_CANDIDATES)\n"
        "    skills_root = find_resource_root(__file__, SKILLS_ROOT_CANDIDATES)\n"
        "    payload = _assemble_payload(payload_root, skills_root)\n"
        "    emit_json_or_lines(payload, str(getattr(args, 'format', 'text') or 'text'), line_field='files')\n"
        "    return 0\n"
    )


def _python_memory_list_skills_command_module(
    package: dict[str, Any],
    operation_id: str,
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    return (
        _python_memory_direct_projection_header(
            package,
            operation_id,
            source_path=source_path,
            regenerate_command=regenerate_command,
        )
        + "import argparse\n"
        "import json\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "from ..primitives.resources import find_resource_root, read_json_object\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command behavior changes belong in {source_path} and the referenced operation contract.\n"
        f"# Regenerate with: {regenerate_command}\n\n\n"
        "SKILLS_ROOT_CANDIDATES = (('_skills', 'REGISTRY.json'),)\n\n\n"
        "def _action_for_skill(skill: dict[str, Any], skills_root: Path) -> dict[str, str]:\n"
        "    skill_id = str(skill.get('id', '')).strip()\n"
        "    relative = Path(str(skill.get('path', '')).strip())\n"
        "    return {\n"
        "        'kind': 'bundled skill',\n"
        "        'path': (skills_root / relative.parent).relative_to(skills_root).as_posix(),\n"
        "        'detail': 'registered packaged product skill',\n"
        "        'role': 'skill',\n"
        "        'safety': 'safe',\n"
        "        'source': skill_id,\n"
        "        'category': 'safe-update',\n"
        "        'remediation_kind': '',\n"
        "        'remediation_target': '',\n"
        "        'remediation_reason': '',\n"
        "        'remediation_confidence': '',\n"
        "        'memory_action': '',\n"
        "        'match_source': '',\n"
        "    }\n\n\n"
        "def _assemble_payload(registry: dict[str, Any], skills_root: Path) -> dict[str, Any]:\n"
        "    actions = []\n"
        "    for skill in registry.get('skills', []):\n"
        "        if not isinstance(skill, dict):\n"
        "            continue\n"
        "        if not str(skill.get('id', '')).strip() or not str(skill.get('path', '')).strip():\n"
        "            continue\n"
        "        actions.append(_action_for_skill(skill, skills_root))\n"
        "    return {\n"
        "        'target_root': str(skills_root),\n"
        "        'dry_run': True,\n"
        "        'mode': 'skills',\n"
        "        'message': 'Bundled skills',\n"
        "        'detected_version': None,\n"
        "        'bootstrap_version': registry.get('bootstrap_version'),\n"
        "        'actions': actions,\n"
        "        'route_summary': {},\n"
        "        'missing_note_hint': '',\n"
        "        'review_summary': {},\n"
        "        'review_cases': [],\n"
        "        'sync_summary': {},\n"
        "        'route_report_summary': {},\n"
        "        'route_report_feedback_cases': [],\n"
        "        'route_report_fixture_results': [],\n"
        "    }\n\n\n"
        "def _emit_output(payload: dict[str, Any], output_format: str) -> None:\n"
        "    if output_format == 'json':\n"
        "        print(json.dumps(payload, indent=2))\n"
        "        return\n"
        "    print(f\"Target: {payload['target_root']}\")\n"
        "    print(str(payload['message']))\n"
        "    print(f\"Detected version: none (payload version {payload['bootstrap_version']})\")\n"
        "    for action in payload['actions']:\n"
        "        print(\n"
        "            f\"- {action['kind']}: {action['path']} \"\n"
        "            f\"({action['detail']}; role={action['role']}; safety={action['safety']}; category={action['category']})\"\n"
        "        )\n\n\n"
        "def run(args: argparse.Namespace) -> int:\n"
        "    skills_root = find_resource_root(__file__, SKILLS_ROOT_CANDIDATES)\n"
        "    registry = read_json_object(skills_root, 'REGISTRY.json')\n"
        "    payload = _assemble_payload(registry, skills_root)\n"
        "    _emit_output(payload, str(getattr(args, 'format', 'text') or 'text'))\n"
        "    return 0\n"
    )


def _python_memory_list_files_command_module(
    package: dict[str, Any],
    operation_id: str,
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    return (
        _python_memory_direct_projection_header(
            package,
            operation_id,
            source_path=source_path,
            regenerate_command=regenerate_command,
        )
        + "import argparse\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "from ..primitives.resources import (\n"
        "    action_from_entry,\n"
        "    detect_mode_by_existing_paths,\n"
        "    emit_action_report,\n"
        "    find_resource_root,\n"
        "    project_payload_entries,\n"
        "    read_first_matching_version,\n"
        "    resolve_repo_target_root,\n"
        ")\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command behavior changes belong in {source_path} and the referenced operation contract.\n"
        f"# Regenerate with: {regenerate_command}\n\n"
        "BOOTSTRAP_VERSION = 47\n"
        "PROJECT_MARKERS = ('pyproject.toml', 'package.json', 'Cargo.toml', '.hg')\n"
        "PAYLOAD_ROOT_CANDIDATES = (('_payload', 'AGENTS.template.md'),)\n"
        "PAYLOAD_SOURCE_ROOTS = ('AGENTS.md', '.agentic-workspace', 'memory', 'docs')\n"
        "TARGET_PATH_REWRITES = (\n"
        "    ('docs', '.agentic-workspace/docs'),\n"
        "    ('memory/system', '.agentic-workspace/memory'),\n"
        "    ('memory/bootstrap', '.agentic-workspace/memory/bootstrap'),\n"
        "    ('memory/skills', '.agentic-workspace/memory/skills'),\n"
        "    ('memory', '.agentic-workspace/memory/repo'),\n"
        ")\n"
        "EXACT_ROLE_RULES = {\n"
        "    'AGENTS.md': 'local-entrypoint',\n"
        "    '.agentic-workspace/memory/repo/index.md': 'seed-note',\n"
        "    '.agentic-workspace/memory/repo/mistakes/recurring-failures.md': 'seed-note',\n"
        "    '.agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md': 'seed-note',\n"
        "}\n"
        "PREFIX_ROLE_RULES = (\n"
        "    ('.agentic-workspace/memory/repo/templates/', 'shared-template'),\n"
        "    ('.agentic-workspace/memory/repo/current/', 'seed-note'),\n"
        "    ('.agentic-workspace/memory/', 'shared-replaceable'),\n"
        ")\n"
        "SUFFIX_ROLE_RULES = (('/README.md', 'seed-note'),)\n"
        "STRATEGY_BY_ROLE = {\n"
        "    'local-entrypoint': 'patch-or-review',\n"
        "    'shared-replaceable': 'replace',\n"
        "    'shared-template': 'replace',\n"
        "    'seed-note': 'seed',\n"
        "    'managed-file': 'create-only',\n"
        "}\n"
        "VERSION_PATHS = ('.agentic-workspace/memory/VERSION.md', 'memory/system/VERSION.md')\n"
        "FULL_MODE_PATHS = (\n"
        "    '.agentic-workspace/memory',\n"
        "    '.agentic-workspace/memory/bootstrap',\n"
        "    '.agentic-workspace/memory/skills',\n"
        ")\n\n\n"
        "def _assemble_payload(target_root: Path, payload_root: Path) -> dict[str, Any]:\n"
        "    entries = project_payload_entries(\n"
        "        payload_root,\n"
        "        source_roots=PAYLOAD_SOURCE_ROOTS,\n"
        "        target_path_rewrites=TARGET_PATH_REWRITES,\n"
        "        exact_roles=EXACT_ROLE_RULES,\n"
        "        prefix_roles=PREFIX_ROLE_RULES,\n"
        "        suffix_roles=SUFFIX_ROLE_RULES,\n"
        "        strategy_by_role=STRATEGY_BY_ROLE,\n"
        "        default_role='managed-file',\n"
        "    )\n"
        "    entries = sorted(entries, key=lambda item: (item['kind'], item['relative_path'], item['source']))\n"
        "    return {\n"
        "        'target_root': str(target_root),\n"
        "        'dry_run': True,\n"
        "        'mode': detect_mode_by_existing_paths(target_root, FULL_MODE_PATHS, full_mode='full', fallback_mode='augment'),\n"
        "        'message': 'Packaged bootstrap file preview',\n"
        "        'detected_version': read_first_matching_version(target_root, VERSION_PATHS, pattern=r'bootstrap version:\\s*(\\d+)'),\n"
        "        'bootstrap_version': BOOTSTRAP_VERSION,\n"
        "        'actions': [action_from_entry(entry) for entry in entries],\n"
        "        'route_summary': {},\n"
        "        'missing_note_hint': '',\n"
        "        'review_summary': {},\n"
        "        'review_cases': [],\n"
        "        'sync_summary': {},\n"
        "        'route_report_summary': {},\n"
        "        'route_report_feedback_cases': [],\n"
        "        'route_report_fixture_results': [],\n"
        "    }\n\n\n"
        "def run(args: argparse.Namespace) -> int:\n"
        "    target_root = resolve_repo_target_root(getattr(args, 'target', None), PROJECT_MARKERS)\n"
        "    payload = _assemble_payload(target_root, find_resource_root(__file__, PAYLOAD_ROOT_CANDIDATES))\n"
        "    emit_action_report(payload, str(getattr(args, 'format', 'text') or 'text'))\n"
        "    return 0\n"
    )


def _python_command_module_outputs(
    package: dict[str, Any],
    binding: dict[str, Any],
    *,
    root: Path,
    source_path: str,
    regenerate_command: str,
) -> list[GeneratedOutput]:
    operation_executor = _operation_executor_binding(package)
    operation_ids = {str(operation_id) for operation_id in operation_executor.get("supported_operation_ids", [])}
    operation_ids.update(_direct_generated_operation_ids(package))
    operation_ids.update(
        str(handler["operation_id"]) for handler in binding.get("runtime_module_handlers", []) if isinstance(handler, dict)
    )
    outputs = [
        GeneratedOutput(
            root / "commands" / "__init__.py",
            _python_commands_package_module(package, binding, source_path=source_path, regenerate_command=regenerate_command),
        )
    ]
    for operation_id in sorted(operation_ids):
        outputs.append(
            GeneratedOutput(
                root / "commands" / f"{_module_name_for_operation(operation_id)}.py",
                _python_command_module(package, operation_id, binding, source_path=source_path, regenerate_command=regenerate_command),
            )
        )
    return outputs


def _python_primitives_module(*, source_path: str, regenerate_command: str) -> str:
    return (
        '"""Generated target-local primitive executor facade.\n\n'
        f"Source: {source_path}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        "# Primitive implementations are generated into this target-local package.\n"
        f"# Regenerate with: {regenerate_command}\n\n"
        "from .primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps\n\n"
        "__all__ = [\n"
        '    "PrimitiveContext",\n'
        '    "PrimitiveExecutionError",\n'
        '    "execute_primitive",\n'
        '    "run_operation_steps",\n'
        "]\n"
    )


def _python_primitive_executor_module(*, source_path: str, regenerate_command: str) -> str:
    primitive_executor_path = Path(__file__).with_name("primitive_executor.py")
    primitive_executor = primitive_executor_path.read_text(encoding="utf-8")
    return (
        '"""Generated target-local primitive executor implementation.\n\n'
        f"Source: {source_path}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "# DO NOT EDIT DIRECTLY.\n"
        "# Primitive behavior changes belong in command_generation.primitive_executor.\n"
        f"# Regenerate with: {regenerate_command}\n\n"
        f"{primitive_executor}"
    )


def _python_resource_primitives_module(*, source_path: str, regenerate_command: str) -> str:
    return (
        '"""Generated target-local resource and output primitives.\n\n'
        f"Source: {source_path}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "import re\n"
        "from pathlib import Path\n"
        "from typing import Any, Iterable\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        "# Primitive behavior changes belong to command_generation's Python target renderer.\n"
        f"# Regenerate with: {regenerate_command}\n\n\n"
        "ResourceCandidate = tuple[str, str]\n\n\n"
        "def find_resource_root(anchor_file: str, candidates: Iterable[ResourceCandidate]) -> Path:\n"
        "    for parent in Path(anchor_file).resolve().parents:\n"
        "        for relative_root, marker in candidates:\n"
        "            candidate = parent.joinpath(*Path(relative_root).parts)\n"
        "            if (candidate / marker).is_file():\n"
        "                return candidate\n"
        "    rendered = ', '.join(f'{root} with marker {marker}' for root, marker in candidates)\n"
        "    raise FileNotFoundError(f'Resource root is not available for any candidate: {rendered}')\n\n\n"
        "def list_resource_files(root: Path) -> list[str]:\n"
        "    return [\n"
        "        path.relative_to(root).as_posix()\n"
        "        for path in sorted(root.rglob('*'))\n"
        "        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'\n"
        "    ]\n\n\n"
        "def read_json_object(root: Path, relative_path: str) -> dict[str, Any]:\n"
        "    payload = json.loads((root / relative_path).read_text(encoding='utf-8'))\n"
        "    if not isinstance(payload, dict):\n"
        "        raise RuntimeError(f'{relative_path} must parse to an object')\n"
        "    return payload\n\n\n"
        "def emit_json_or_lines(payload: dict[str, Any], output_format: str, *, line_field: str) -> None:\n"
        "    if output_format == 'json':\n"
        "        print(json.dumps(payload, indent=2))\n"
        "        return\n"
        "    lines = payload.get(line_field, [])\n"
        "    if not isinstance(lines, list):\n"
        "        raise RuntimeError(f'{line_field} must be a list for text emission')\n"
        "    for line in lines:\n"
        "        print(str(line))\n"
        "\n\n"
        "def find_repo_candidates(start: Path, project_markers: Iterable[str]) -> list[Path]:\n"
        "    candidates = []\n"
        "    for path in (start, *start.parents):\n"
        "        marker_found = any((path / marker).exists() for marker in project_markers)\n"
        "        if marker_found or (path / '.git').exists():\n"
        "            candidates.append(path)\n"
        "    return candidates\n\n\n"
        "class RepoDetectionError(ValueError):\n"
        "    pass\n\n\n"
        "def resolve_repo_target_root(target: str | None, project_markers: Iterable[str]) -> Path:\n"
        "    explicit = target is not None\n"
        "    start = Path(target or Path.cwd()).resolve()\n"
        "    if not start.exists():\n"
        "        raise RepoDetectionError(f'Target does not exist: {start}')\n"
        "    if start.is_file():\n"
        "        raise RepoDetectionError(f'Target must be a directory: {start}')\n"
        "    if explicit:\n"
        "        return start\n"
        "    candidates = find_repo_candidates(start, project_markers)\n"
        "    if not candidates:\n"
        "        message = 'Could not find a repository root from the current directory. Pass --target explicitly.'\n"
        "        raise RepoDetectionError(message)\n"
        "    if len(candidates) > 1:\n"
        "        roots = ', '.join(str(path) for path in candidates)\n"
        "        raise RepoDetectionError(f'Ambiguous repository root detected ({roots}). Pass --target explicitly. Retry with --target .')\n"
        "    return candidates[0]\n\n\n"
        "def rewrite_relative_path(relative_path: Path, rules: Iterable[tuple[str, str]]) -> Path:\n"
        "    path_str = relative_path.as_posix()\n"
        "    for source_prefix, target_prefix in rules:\n"
        "        normalized = source_prefix.rstrip('/')\n"
        "        if path_str != normalized and not path_str.startswith(f'{normalized}/'):\n"
        "            continue\n"
        "        suffix = relative_path.relative_to(Path(normalized))\n"
        "        return Path(target_prefix) / suffix\n"
        "    return relative_path\n\n\n"
        "def classify_relative_path(\n"
        "    relative_path: Path,\n"
        "    *,\n"
        "    exact_roles: dict[str, str],\n"
        "    prefix_roles: Iterable[tuple[str, str]],\n"
        "    suffix_roles: Iterable[tuple[str, str]],\n"
        "    default_role: str,\n"
        ") -> str:\n"
        "    path_str = relative_path.as_posix()\n"
        "    if path_str in exact_roles:\n"
        "        return exact_roles[path_str]\n"
        "    for prefix, role in prefix_roles:\n"
        "        if path_str.startswith(prefix):\n"
        "            return role\n"
        "    for suffix, role in suffix_roles:\n"
        "        if path_str.endswith(suffix):\n"
        "            return role\n"
        "    return default_role\n\n\n"
        "def project_payload_entries(\n"
        "    source_root: Path,\n"
        "    *,\n"
        "    source_roots: Iterable[str],\n"
        "    target_path_rewrites: Iterable[tuple[str, str]],\n"
        "    exact_roles: dict[str, str],\n"
        "    prefix_roles: Iterable[tuple[str, str]],\n"
        "    suffix_roles: Iterable[tuple[str, str]],\n"
        "    strategy_by_role: dict[str, str],\n"
        "    default_role: str,\n"
        ") -> list[dict[str, str]]:\n"
        "    entries = []\n"
        "    seen = set()\n"
        "    for source_root_name in source_roots:\n"
        "        relative_root = Path(source_root_name)\n"
        "        source_path = source_root / relative_root\n"
        "        if not source_path.exists() and relative_root.name.endswith('.md'):\n"
        "            template_name = relative_root.name.replace('.md', '.template.md')\n"
        "            template_path = source_root / relative_root.with_name(template_name)\n"
        "            if template_path.exists():\n"
        "                source_path = template_path\n"
        "        if not source_path.exists():\n"
        "            continue\n"
        "        if source_path.is_file():\n"
        "            children = [source_path]\n"
        "        else:\n"
        "            children = sorted(path for path in source_path.rglob('*') if path.is_file())\n"
        "        for child in children:\n"
        "            source_relative = child.relative_to(source_root)\n"
        "            target_relative = source_relative\n"
        "            if target_relative.name.endswith('.template.md'):\n"
        "                target_name = target_relative.name.replace('.template.md', '.md')\n"
        "                target_relative = target_relative.with_name(target_name)\n"
        "            target_relative = rewrite_relative_path(target_relative, target_path_rewrites)\n"
        "            if target_relative in seen:\n"
        "                continue\n"
        "            seen.add(target_relative)\n"
        "            role = classify_relative_path(\n"
        "                target_relative,\n"
        "                exact_roles=exact_roles,\n"
        "                prefix_roles=prefix_roles,\n"
        "                suffix_roles=suffix_roles,\n"
        "                default_role=default_role,\n"
        "            )\n"
        "            entries.append({\n"
        "                'relative_path': target_relative.as_posix(),\n"
        "                'role': role,\n"
        "                'strategy': strategy_by_role[role],\n"
        "                'kind': 'managed file',\n"
        "                'source': target_relative.as_posix(),\n"
        "                'source_relative': source_relative.as_posix(),\n"
        "            })\n"
        "    return entries\n\n\n"
        "def read_first_matching_version(\n"
        "    target_root: Path,\n"
        "    relative_paths: Iterable[str],\n"
        "    *,\n"
        "    pattern: str,\n"
        "    flags: int = re.IGNORECASE,\n"
        ") -> int | None:\n"
        "    version_pattern = re.compile(pattern, flags)\n"
        "    for relative in relative_paths:\n"
        "        path = target_root / relative\n"
        "        if path.exists():\n"
        "            match = version_pattern.search(path.read_text(encoding='utf-8'))\n"
        "            return int(match.group(1)) if match else None\n"
        "    return None\n\n\n"
        "def detect_mode_by_existing_paths(\n"
        "    target_root: Path,\n"
        "    full_mode_paths: Iterable[str],\n"
        "    *,\n"
        "    full_mode: str,\n"
        "    fallback_mode: str,\n"
        ") -> str:\n"
        "    if any((target_root / path).exists() for path in full_mode_paths):\n"
        "        return full_mode\n"
        "    return fallback_mode\n\n\n"
        "def action_from_entry(entry: dict[str, str]) -> dict[str, str]:\n"
        "    return {\n"
        "        'kind': entry['kind'],\n"
        "        'path': entry['relative_path'],\n"
        "        'detail': entry['strategy'],\n"
        "        'role': entry['role'],\n"
        "        'safety': 'safe',\n"
        "        'source': entry['source'],\n"
        "        'category': 'safe-update',\n"
        "        'remediation_kind': '',\n"
        "        'remediation_target': '',\n"
        "        'remediation_reason': '',\n"
        "        'remediation_confidence': '',\n"
        "        'memory_action': '',\n"
        "        'match_source': '',\n"
        "    }\n\n\n"
        "def emit_action_report(payload: dict[str, Any], output_format: str) -> None:\n"
        "    if output_format == 'json':\n"
        "        print(json.dumps(payload, indent=2))\n"
        "        return\n"
        "    print(f\"Target: {payload['target_root']}\")\n"
        "    print(str(payload['message']))\n"
        "    detected = payload['detected_version']\n"
        "    if detected is None:\n"
        "        print(f\"Detected version: none (payload version {payload['bootstrap_version']})\")\n"
        "    else:\n"
        "        print(f\"Detected version: {detected} (payload version {payload['bootstrap_version']})\")\n"
        "    for action in payload['actions']:\n"
        "        print(\n"
        "            f\"- {action['kind']}: {action['path']} \"\n"
        "            f\"({action['detail']}; role={action['role']}; safety={action['safety']}; category={action['category']})\"\n"
        "        )\n"
    )


def _handler_function_name(primitive: str) -> str:
    return "_handle_" + "".join(character if character.isalnum() else "_" for character in primitive)


def _render_value_kwargs(kwargs: dict[str, Any]) -> str:
    rendered = []
    for name, source in sorted(kwargs.items()):
        if not isinstance(source, dict):
            continue
        rendered.append(f"{name}=values.get({str(source.get('value', ''))!r})")
    return ", ".join(rendered)


def _handler_import_module(package: dict[str, Any], import_module: str, *, operation_executor: bool) -> str:
    local_binding = _local_runtime_binding_for_import(package, import_module)
    if local_binding is None:
        return import_module
    if operation_executor:
        return _operation_executor_import_for_binding(local_binding)
    return _command_module_import_for_binding(local_binding)


def _render_function_call_handler(package: dict[str, Any], function_name: str, handler: dict[str, Any]) -> str:
    imported_name = str(handler["function"])
    kwargs = _render_value_kwargs(handler.get("kwargs", {}))
    import_module = _handler_import_module(package, str(handler["import_module"]), operation_executor=True)
    return (
        f"def {function_name}(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:\n"
        f"    from {import_module} import {imported_name}\n\n"
        f"    return {imported_name}({kwargs})\n"
    )


def _render_conditional_function_call_handler(package: dict[str, Any], function_name: str, handler: dict[str, Any]) -> str:
    condition_value = str(handler["condition_value"])
    true_handler = handler["if_true"]
    false_handler = handler["if_false"]
    true_name = str(true_handler["function"])
    false_name = str(false_handler["function"])
    true_kwargs = _render_value_kwargs(true_handler.get("kwargs", {}))
    false_kwargs = _render_value_kwargs(false_handler.get("kwargs", {}))
    true_import_module = _handler_import_module(package, str(true_handler["import_module"]), operation_executor=True)
    false_import_module = _handler_import_module(package, str(false_handler["import_module"]), operation_executor=True)
    return (
        f"def {function_name}(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:\n"
        f"    if values.get({condition_value!r}):\n"
        f"        from {true_import_module} import {true_name}\n\n"
        f"        return {true_name}({true_kwargs})\n"
        f"    from {false_import_module} import {false_name}\n\n"
        f"    return {false_name}({false_kwargs})\n"
    )


def _render_generated_target_root_handler(function_name: str, handler: dict[str, Any]) -> str:
    project_markers = tuple(str(marker) for marker in handler["project_markers"])
    return (
        f"def {function_name}(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:\n"
        "    from .resources import resolve_repo_target_root\n\n"
        f"    return resolve_repo_target_root(values.get('target'), {project_markers!r})\n"
    )


def _render_runtime_emit_handler(function_name: str, handler: dict[str, Any], *, runtime_module_file: str) -> str:
    runtime_function = str(handler["runtime_function"])
    result_value = str(handler["result_value"])
    format_value = str(handler["format_value"])
    default_format = str(handler["default_format"])
    dict_text_function = str(handler.get("dict_text_function") or "")
    dict_branch = ""
    if dict_text_function:
        dict_branch = (
            f"    if isinstance(result, dict):\n"
            f'        if output_format == "json":\n'
            f"            print(json.dumps(result, indent=2))\n"
            f"            return None\n"
            f"        from .{runtime_module_file} import {dict_text_function}\n\n"
            f"        {dict_text_function}(result)\n"
            f"        return None\n"
        )
    return (
        f"def {function_name}(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:\n"
        f"    from .{runtime_module_file} import {runtime_function}\n\n"
        f"    result = values[{result_value!r}]\n"
        f"    output_format = str(values.get({format_value!r}) or {default_format!r})\n"
        f"{dict_branch}"
        f"    return {runtime_function}(result, output_format)\n"
    )


def _render_runtime_handler(
    package: dict[str, Any],
    function_name: str,
    handler: dict[str, Any],
    *,
    runtime_module_file: str,
) -> str:
    runtime_function = str(handler["function"])
    import_module = str(handler.get("import_module") or "")
    if import_module:
        local_binding = _local_runtime_binding_for_import(package, import_module)
        if local_binding is not None:
            local_import = _operation_executor_import_for_binding(local_binding)
            return (
                f"def {function_name}(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:\n"
                f"    from {local_import} import {runtime_function}\n\n"
                f"    return {runtime_function}(values, arguments, context)\n"
            )
        return (
            f"def {function_name}(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:\n"
            f"    from {import_module} import {runtime_function}\n\n"
            f"    return {runtime_function}(values, arguments, context)\n"
        )
    return (
        f"def {function_name}(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:\n"
        f"    from .{runtime_module_file} import {runtime_function}\n\n"
        f"    return {runtime_function}(values, arguments, context)\n"
    )


def _local_runtime_binding_functions(package: dict[str, Any], binding: dict[str, Any]) -> list[str]:
    source_import_module = str(binding["source_import_module"])
    functions: set[str] = set()

    def collect_handler_function(handler: dict[str, Any]) -> None:
        if handler.get("import_module") == source_import_module:
            functions.add(str(handler["function"]))
        for branch in ("if_true", "if_false"):
            nested = handler.get(branch)
            if isinstance(nested, dict):
                collect_handler_function(nested)

    operation_executor = _operation_executor_binding(package)
    for handler in operation_executor.get("handlers", []):
        if isinstance(handler, dict):
            collect_handler_function(handler)
    python_runtime_binding = package.get("python_runtime_binding", {})
    if isinstance(python_runtime_binding, dict):
        for handler in python_runtime_binding.get("runtime_module_handlers", []):
            if isinstance(handler, dict) and handler.get("import_module") == source_import_module:
                functions.add(str(handler.get("function") or _runtime_adapter_function_name(str(handler["operation_id"]))))
    return sorted(functions)


def _local_runtime_generated_overrides(binding: dict[str, Any]) -> dict[str, dict[str, Any]]:
    overrides = binding.get("generated_function_overrides", [])
    if not isinstance(overrides, list):
        return {}
    return {str(item["function"]): item for item in overrides if isinstance(item, dict) and item.get("function")}


def _python_local_runtime_helper_block() -> str:
    return (
        "def _serialise_value(value: Any) -> Any:\n"
        "    if isinstance(value, Path):\n"
        "        return value.as_posix()\n"
        "    if isinstance(value, dict):\n"
        "        return {key: _serialise_value(inner) for key, inner in value.items()}\n"
        "    if isinstance(value, list):\n"
        "        return [_serialise_value(item) for item in value]\n"
        "    return value\n\n\n"
        "def _field_by_path(payload: Any, path: str) -> tuple[bool, Any]:\n"
        "    current = payload\n"
        "    for part in path.split('.'):\n"
        "        if isinstance(current, dict) and part in current:\n"
        "            current = current[part]\n"
        "            continue\n"
        "        if isinstance(current, list):\n"
        "            try:\n"
        "                current = current[int(part)]\n"
        "                continue\n"
        "            except (ValueError, IndexError):\n"
        "                return (False, None)\n"
        "        return (False, None)\n"
        "    return (True, copy.deepcopy(current))\n\n\n"
        "def _selector_tokens(select: str | None) -> list[str]:\n"
        "    return [token.strip() for token in str(select or '').split(',') if token.strip()]\n\n\n"
        "def _available_selectors_for_payload(payload: Any, prefix: str = '') -> list[str]:\n"
        "    selectors: list[str] = []\n"
        "    if isinstance(payload, dict):\n"
        "        for key in sorted(str(item) for item in payload):\n"
        "            path = f'{prefix}.{key}' if prefix else key\n"
        "            selectors.append(path)\n"
        "            selectors.extend(_available_selectors_for_payload(payload.get(key), path))\n"
        "    elif isinstance(payload, list):\n"
        "        for index, item in enumerate(payload[:10]):\n"
        "            path = f'{prefix}.{index}' if prefix else str(index)\n"
        "            selectors.append(path)\n"
        "            selectors.extend(_available_selectors_for_payload(item, path))\n"
        "    return selectors\n\n\n"
        "def _select_payload_fields(payload: dict[str, Any], *, select: str | None, source_command: str) -> dict[str, Any]:\n"
        "    values: dict[str, Any] = {}\n"
        "    missing: list[str] = []\n"
        "    for selector in _selector_tokens(select):\n"
        "        found, value = _field_by_path(payload, selector)\n"
        "        if found:\n"
        "            values[selector] = value\n"
        "        else:\n"
        "            missing.append(selector)\n"
        "    selected: dict[str, Any] = {'kind': 'agentic-workspace/selected-output/v1', 'source_command': source_command, 'values': values}\n"
        "    if missing:\n"
        "        selected['missing'] = missing\n"
        "        selected['selector_rule'] = 'Comma-separated dot paths select exact JSON fields; unknown fields are reported in missing.'\n"
        "        selected['available_selectors'] = _available_selectors_for_payload(payload)\n"
        "    return selected\n\n\n"
        "def _selector_refs(*, command: str, answer: Any) -> list[str]:\n"
        "    refs = ['.agentic-workspace/docs/compact-contract-profile.md', command]\n"
        "    if isinstance(answer, dict):\n"
        "        for key in ('canonical_doc', 'command', 'path', 'surface', 'ledger_path'):\n"
        "            value = answer.get(key)\n"
        "            if isinstance(value, str) and value not in refs:\n"
        "                refs.append(value)\n"
        "    return refs\n\n\n"
        "def _compact_contract_answer(*, surface: str, selector: dict[str, Any], answer: Any, refs: list[str]) -> dict[str, Any]:\n"
        "    return {'profile': 'compact-contract-answer/v1', 'surface': surface, 'selector': selector, 'matched': True, 'answer': answer, 'refs': refs}\n\n\n"
        "def _select_section(payload: dict[str, Any], *, section: str, source_command: str) -> dict[str, Any]:\n"
        "    normalized = section.strip()\n"
        "    if normalized not in payload:\n"
        "        supported = ', '.join(sorted(str(key) for key in payload))\n"
        "        raise ValueError(f'{source_command} --section must match one of: {supported}.')\n"
        "    answer = payload[normalized]\n"
        "    return _compact_contract_answer(surface=source_command, selector={'section': normalized}, answer=answer, refs=_selector_refs(command=f'agentic-workspace {source_command} --format json', answer=answer))\n\n\n"
        "def _tiny_sectioned_payload(payload: dict[str, Any], *, common_sections: list[str]) -> dict[str, Any]:\n"
        "    return {\n"
        "        'kind': 'agentic-workspace/defaults-router/v1',\n"
        "        'profile': 'tiny',\n"
        "        'summary': 'Default-route contract sections are available on demand; request one section or full detail instead of loading the whole contract.',\n"
        "        'available_sections': sorted(str(key) for key in payload),\n"
        "        'common_sections': list(common_sections),\n"
        "        'detail_commands': {'section': 'agentic-workspace defaults --section <section> --format json', 'full': 'agentic-workspace defaults --verbose --format json'},\n"
        "    }\n"
        "\n\n"
        "def _emit_tiny_sectioned_text(payload: dict[str, Any]) -> str:\n"
        "    lines = [str(payload.get('summary', ''))]\n"
        "    common_sections = payload.get('common_sections', [])\n"
        "    if common_sections:\n"
        "        lines.append('Common sections:')\n"
        "        lines.extend(f'- {section}' for section in common_sections)\n"
        "    detail_commands = payload.get('detail_commands', {})\n"
        "    if isinstance(detail_commands, dict) and detail_commands:\n"
        "        lines.append('Detail commands:')\n"
        "        lines.extend(f'- {key}: {value}' for key, value in detail_commands.items())\n"
        "    return '\\n'.join(lines) + '\\n'\n"
        "\n\n"
        "def _emit_compact_answer_text(payload: dict[str, Any]) -> str:\n"
        "    lines = [\n"
        "        f\"Profile: {payload.get('profile')}\",\n"
        "        f\"Surface: {payload.get('surface')}\",\n"
        "        f\"Selector: {json.dumps(payload.get('selector', {}), sort_keys=True)}\",\n"
        "        f\"Matched: {payload.get('matched')}\",\n"
        "        'Answer:',\n"
        "        json.dumps(_serialise_value(payload.get('answer')), indent=2),\n"
        "    ]\n"
        "    refs = payload.get('refs', [])\n"
        "    if refs:\n"
        "        lines.append('Refs:')\n"
        "        lines.extend(f'- {ref}' for ref in refs)\n"
        "    return '\\n'.join(lines) + '\\n'\n"
        "\n\n"
        "def _emit_selected_output_text(payload: dict[str, Any]) -> str:\n"
        "    lines = [\n"
        "        f\"Kind: {payload.get('kind')}\",\n"
        "        f\"Source command: {payload.get('source_command')}\",\n"
        "        'Values:',\n"
        "        json.dumps(_serialise_value(payload.get('values', {})), indent=2),\n"
        "    ]\n"
        "    missing = payload.get('missing', [])\n"
        "    if missing:\n"
        "        lines.append('Missing:')\n"
        "        lines.extend(f'- {item}' for item in missing)\n"
        "    return '\\n'.join(lines) + '\\n'\n"
        "\n\n"
        "def _emit_delegation_outcomes_text(payload: dict[str, Any]) -> str:\n"
        "    recorded = payload.get('recorded', {})\n"
        "    lines = [\n"
        "        f\"Kind: {payload.get('kind')}\",\n"
        "        f\"Path: {payload.get('path')}\",\n"
        "        f\"Record count: {payload.get('record_count')}\",\n"
        "        f\"Rule: {payload.get('rule')}\",\n"
        "    ]\n"
        "    if isinstance(recorded, dict):\n"
        "        lines.append('Recorded:')\n"
        "        for key in ('recorded_at', 'delegation_target', 'task_class', 'outcome', 'handoff_sufficiency', 'review_burden', 'escalation_required'):\n"
        "            if key in recorded:\n"
        "                lines.append(f'- {key}: {recorded[key]}')\n"
        "    return '\\n'.join(lines) + '\\n'\n"
        "\n\n"
    )


def _python_local_runtime_generated_function(
    function: str,
    override: dict[str, Any],
    *,
    source_import_module: str,
) -> str:
    implementation = str(override["implementation"])
    if implementation == "target_root_resolve":
        return (
            f"def {function}(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Path:\n"
            "    target_value = values.get('target')\n"
            "    target_root = Path(str(target_value)).resolve() if target_value else Path.cwd().resolve()\n"
            "    if not target_root.exists():\n"
            "        raise ValueError(f'Target path does not exist: {target_root}')\n"
            "    if not target_root.is_dir():\n"
            "        raise ValueError(f'Target path is not a directory: {target_root}')\n"
            "    return target_root\n"
        )
    if implementation == "sectioned_payload_select":
        payload_value = str(override.get("payload_value") or "payload")
        source_command = str(override.get("source_command") or "command")
        common_sections = [str(section) for section in override.get("common_sections", [])]
        return (
            f"def {function}(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> dict[str, Any]:\n"
            f"    payload = values[{payload_value!r}]\n"
            "    section = values.get('section')\n"
            "    if section is not None:\n"
            f"        payload = _select_section(payload, section=str(section), source_command={source_command!r})\n"
            "    elif ('full' if values.get('verbose') else str(values.get('profile') or 'tiny')) == 'tiny':\n"
            f"        payload = _tiny_sectioned_payload(payload, common_sections={common_sections!r})\n"
            "    select = values.get('select')\n"
            "    if select is not None:\n"
            f"        payload = _select_payload_fields(payload, select=str(select), source_command={source_command!r})\n"
            "    return _serialise_value(payload)\n"
        )
    if implementation == "json_resource_load":
        generated_root = str(override["generated_root"])
        required_marker = str(override["required_marker"])
        relative_path = str(override.get("relative_path") or required_marker)
        return (
            f"def {function}(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> dict[str, Any]:\n"
            "    from .resources import find_resource_root, read_json_object\n\n"
            f"    resource_root = find_resource_root(__file__, [({generated_root!r}, {required_marker!r})])\n"
            f"    return read_json_object(resource_root, {relative_path!r})\n"
        )
    if implementation == "json_output_with_source_fallback":
        return (
            f"def {function}(values: dict[str, Any], arguments: dict[str, Any], context: Any) -> Any:\n"
            "    result = values['result']\n"
            "    if str(values.get('format') or 'text') == 'json' and isinstance(result, dict):\n"
            "        print(json.dumps(_serialise_value(values['result']), indent=2))\n"
            "        return None\n"
            "    if isinstance(result, dict) and (isinstance(result.get('route_report_summary'), dict) or result.get('kind') == 'memory-module-report/v1' or (result.get('kind') == 'planning-module-report/v1' and result.get('profile') == 'tiny')):\n"
            "        from .primitive_executor import _emit_output\n\n"
            "        print(_emit_output(values=values, arguments=arguments), end='')\n"
            "        return None\n"
            "    if isinstance(result, dict) and result.get('kind') == 'agentic-workspace/defaults-router/v1':\n"
            "        print(_emit_tiny_sectioned_text(result), end='')\n"
            "        return None\n"
            "    if isinstance(result, dict) and result.get('profile') == 'compact-contract-answer/v1':\n"
            "        print(_emit_compact_answer_text(result), end='')\n"
            "        return None\n"
            "    if isinstance(result, dict) and result.get('kind') == 'agentic-workspace/selected-output/v1':\n"
            "        print(_emit_selected_output_text(result), end='')\n"
            "        return None\n"
            "    if isinstance(result, dict) and result.get('kind') == 'agentic-workspace/delegation-outcomes/v1':\n"
            "        print(_emit_delegation_outcomes_text(result), end='')\n"
            "        return None\n"
            f"    from {source_import_module} import {function} as source_function\n\n"
            "    return source_function(values, arguments, context)\n"
        )
    raise ValueError(f"unsupported generated local runtime implementation: {implementation!r}")


def _python_local_runtime_binding_module(
    package: dict[str, Any],
    binding: dict[str, Any],
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    functions = _local_runtime_binding_functions(package, binding)
    source_import_module = str(binding["source_import_module"])
    exported = ",\n    ".join(repr(function) for function in functions)
    overrides = _local_runtime_generated_overrides(binding)
    function_blocks = []
    for function in functions:
        if function in overrides:
            function_blocks.append(
                _python_local_runtime_generated_function(function, overrides[function], source_import_module=source_import_module)
            )
        else:
            function_blocks.append(
                f"def {function}(*args: Any, **kwargs: Any) -> Any:\n"
                f"    from {source_import_module} import {function} as source_function\n\n"
                "    return source_function(*args, **kwargs)\n"
            )
    helper_parts: list[str] = []
    if overrides:
        helper_parts.append(_python_local_runtime_helper_block())
    helper_block = "\n\n".join(helper_parts) + "\n\n" if helper_parts else ""
    helper_imports = ""
    if overrides:
        helper_imports = "import copy\nimport json\nfrom pathlib import Path\n"
    return (
        '"""Generated runtime binding facade.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        f"{helper_imports}"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        "# This generated-local seam makes remaining source-runtime delegates explicit per function.\n"
        "# Export semantics: generated wrappers perform live source-module lookup at call time.\n"
        "# Monkeypatching this facade is local to the facade; it is not forwarded back into source modules.\n"
        "# Replace individual bindings here with generated/codegen-owned primitives as those operations migrate.\n"
        f"# Regenerate with: {regenerate_command}\n\n" + helper_block + "\n\n".join(function_blocks) + "\n\n"
        "__all__ = [\n"
        f"    {exported},\n"
        "]\n"
    )


def _render_context_root_function(root: dict[str, Any]) -> str:
    function_name = _handler_function_name(f"context.root.{root['name']}")
    generated_root = str(root.get("generated_root") or "")
    if generated_root:
        required_marker = str(root.get("required_marker") or "")
        return (
            f"def {function_name}() -> Path:\n"
            "    from .resources import find_resource_root\n\n"
            f"    return find_resource_root(__file__, [({generated_root!r}, {required_marker!r})])\n"
        )
    imported_name = str(root["function"])
    return f"def {function_name}() -> Path:\n    from {root['import_module']} import {imported_name}\n\n    return {imported_name}()\n"


def _python_operation_executor_module(
    package: dict[str, Any],
    binding: dict[str, Any],
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    runtime_module_file = _runtime_module_file_for_package(package)
    supported_operation_ids = sorted(str(operation_id) for operation_id in binding["supported_operation_ids"])
    initial_values = []
    for item in binding["initial_values"]:
        initial_values.append(f"                {str(item['name'])!r}: getattr(args, {str(item['arg'])!r}, {item.get('default')!r}),")
    handlers: list[str] = []
    handler_items = []
    needs_json = False
    for handler in binding["handlers"]:
        primitive = str(handler["primitive"])
        function_name = _handler_function_name(primitive)
        handler_items.append(f"                {primitive!r}: {function_name},")
        handler_kind = str(handler["handler"])
        if handler_kind == "runtime_handler":
            handlers.append(_render_runtime_handler(package, function_name, handler, runtime_module_file=runtime_module_file))
        elif handler_kind == "function_call":
            handlers.append(_render_function_call_handler(package, function_name, handler))
        elif handler_kind == "conditional_function_call":
            handlers.append(_render_conditional_function_call_handler(package, function_name, handler))
        elif handler_kind == "generated_target_root_resolve":
            handlers.append(_render_generated_target_root_handler(function_name, handler))
        elif handler_kind == "runtime_emit":
            needs_json = True
            handlers.append(_render_runtime_emit_handler(function_name, handler, runtime_module_file=runtime_module_file))
        else:
            raise ValueError(f"unsupported Python operation executor handler: {handler_kind!r}")
    supported_set = ",\n        ".join(repr(operation_id) for operation_id in supported_operation_ids)
    root_functions = []
    context_roots = []
    for root in binding.get("context_roots", []):
        root_function = _handler_function_name(f"context.root.{root['name']}")
        root_functions.append(_render_context_root_function(root))
        context_roots.append(f"                {str(root['name'])!r}: {root_function}(),")
    roots_block = "\n".join(context_roots)
    if roots_block:
        roots_block = "\n" + roots_block + "\n            "
    json_import = "import json\n" if needs_json else ""
    return (
        '"""Generated Python operation IR executor.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import argparse\n"
        f"{json_import}"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "from .primitive_executor import (\n"
        "    PrimitiveContext,\n"
        "    PrimitiveExecutionError,\n"
        "    run_operation_steps,\n"
        ")\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Operation executor binding changes belong in {source_path}.\n"
        f"# Regenerate with: {regenerate_command}\n"
        "\n\n"
        "class OperationIrExecutionError(RuntimeError):\n"
        "    pass\n\n\n"
        "def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:\n"
        '    if operation.get("id") not in {\n'
        f"        {supported_set}\n"
        "    }:\n"
        "        raise OperationIrExecutionError(f\"unsupported operation IR contract: {operation.get('id')!r}\")\n"
        '    if operation.get("migration_status") != "runtime-consumed":\n'
        "        raise OperationIrExecutionError(f\"operation is not marked runtime-consumed: {operation.get('id')!r}\")\n\n"
        "    try:\n"
        "        values = run_operation_steps(\n"
        "            operation,\n"
        "            initial_values={\n"
        '                "operation_id": operation.get("id"),\n' + "\n".join(initial_values) + "\n"
        "            },\n"
        f"            context=PrimitiveContext(cwd=Path.cwd(), roots={{{roots_block}}}),\n"
        "            handlers={\n" + "\n".join(handler_items) + "\n"
        "            },\n"
        "        )\n"
        "        emitted = values.get('emitted')\n"
        "        if isinstance(emitted, str):\n"
        "            print(emitted, end='')\n"
        "    except PrimitiveExecutionError as exc:\n"
        "        raise OperationIrExecutionError(str(exc)) from exc\n"
        "    return 0\n\n\n" + "\n\n".join(root_functions + handlers)
    )


def _runtime_adapter_function_name(operation_id: str) -> str:
    return "_run_" + "".join(character if character.isalnum() else "_" for character in operation_id) + "_adapter"


def _python_runtime_handler_module(
    package: dict[str, Any],
    binding: dict[str, Any],
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    operation_executor = _operation_executor_binding(package)
    executor_module = str(operation_executor["module_file"])
    operation_ids = {str(operation_id) for operation_id in operation_executor["supported_operation_ids"]}
    direct_handlers = {
        str(handler["operation_id"]): handler for handler in binding.get("runtime_module_handlers", []) if isinstance(handler, dict)
    }
    operation_ids.update(direct_handlers)
    handler_functions = []
    handler_items = []
    for operation_id in sorted(operation_ids):
        function_name = _runtime_adapter_function_name(operation_id)
        if operation_id in direct_handlers:
            handler = direct_handlers[operation_id]
            import_module = str(handler["import_module"])
            imported_function = str(handler.get("function") or function_name)
            handler_functions.append(
                f"def {function_name}(args: argparse.Namespace) -> int:\n"
                f"    from {import_module} import {imported_function}\n\n"
                f"    return {imported_function}(args)\n"
            )
        else:
            handler_functions.append(
                f"def {function_name}(args: argparse.Namespace) -> int:\n"
                f"    return run_operation_ir(generated_operation_contract({operation_id!r}), args)\n"
            )
        handler_items.append(f"    {operation_id!r}: {function_name},")
    return (
        '"""Generated Python runtime operation handler module.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import argparse\n"
        "import sys\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Runtime handler changes belong in {source_path}.\n"
        f"# Regenerate with: {regenerate_command}\n"
        "from . import build_generated_parser\n"
        "from . import generated_command_names\n"
        "from . import generated_operation_contract\n"
        "from . import run_generated_command\n"
        "from . import supports_generated_command\n"
        f"from .{executor_module} import run_operation_ir\n\n\n" + "def _program_name() -> str:\n"
        '    invoked = sys.argv[0].replace("\\\\", "/").rsplit("/", 1)[-1]\n'
        f"    if invoked == {package['program']!r}:\n"
        "        return invoked\n"
        f"    return {package['program']!r}\n\n\n"
        "def build_parser() -> argparse.ArgumentParser:\n"
        "    return build_generated_parser()\n\n\n"
        "def main(argv: list[str] | None = None) -> int:\n"
        "    argv_list = list(sys.argv[1:] if argv is None else argv)\n"
        "    try:\n"
        "        return run_generated_command(argv_list, _run_generated_operation)\n"
        "    except Exception as exc:\n"
        "        if exc.__class__.__name__.endswith('UsageError') or exc.__class__.__name__ == 'RepoDetectionError':\n"
        "            build_generated_parser().error(str(exc))\n"
        "        raise\n\n\n"
        "def _run_generated_operation(operation_id: str, args: argparse.Namespace) -> int:\n"
        "    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)\n"
        "    if handler is None:\n"
        "        build_generated_parser().error(\n"
        "            f\"Generated adapter for {getattr(args, 'command', operation_id)} references unsupported operation {operation_id}.\"\n"
        "        )\n"
        "        raise SystemExit(2)\n"
        "    return handler(args)\n\n\n"
        + "\n\n".join(handler_functions)
        + "\n\n\n_GENERATED_RUNTIME_HANDLERS = {\n"
        + "\n".join(handler_items)
        + "\n}\n"
    )


def _python_runtime_adapter_module(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity_levels: dict[str, dict[str, Any]],
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    weak_agent_routing = _weak_agent_routing_for_target(target, maturity_levels)
    runnable = str(
        target.get("maturity_level_ref") in {"runtime-backed-read-only-adapter", "weak-agent-safe-adapter", "mutation-capable-adapter"}
    )
    runtime_module_file = _runtime_module_file_for_package(package)
    main_function = ""
    if runtime_module_file:
        main_function = (
            "\n\n"
            "def _run_command_module(operation_id: str, args: argparse.Namespace) -> int:\n"
            "    from .commands import GENERATED_COMMAND_HANDLERS\n\n"
            "    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id) or GENERATED_COMMAND_HANDLERS.get(operation_id)\n"
            "    if handler is None:\n"
            "        build_generated_parser().error(\n"
            "            f\"Generated adapter for {getattr(args, 'command', operation_id)} references unsupported operation {operation_id}.\"\n"
            "        )\n"
            "    return handler(args)\n\n\n"
            "def main(argv: list[str] | None = None) -> int:\n"
            "    import sys\n"
            "\n"
            "    argv_list = list(sys.argv[1:] if argv is None else argv)\n"
            "    if argv_list and argv_list[0] in {'-h', '--help', '--version'}:\n"
            "        build_generated_parser().parse_args(argv_list)\n"
            "        return 0\n"
            "    if supports_generated_command(argv_list):\n"
            "        try:\n"
            "            return run_generated_command(argv_list, _run_command_module)\n"
            "        except Exception as exc:\n"
            "            if exc.__class__.__name__.endswith('UsageError') or exc.__class__.__name__ == 'RepoDetectionError':\n"
            "                build_generated_parser().error(str(exc))\n"
            "            raise\n\n"
            "    build_generated_parser().parse_args(argv_list)\n"
            "    return 0\n"
        )
    return (
        '"""Generated runtime-backed Python command adapter.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import argparse\n"
        "import difflib\n"
        "import json\n"
        "from collections.abc import Callable\n"
        "from importlib.metadata import PackageNotFoundError, version as package_version\n"
        "from importlib.resources import files\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command/interface changes belong in {source_path}.\n"
        "# Runtime behavior changes belong in hand-written operation/primitive implementation code.\n"
        f"# Regenerate with: {regenerate_command}\n"
        "\n" + "def _load_generated_json(name: str) -> Any:\n"
        "    parts = tuple(part for part in name.replace('\\\\', '/').split('/') if part)\n"
        "    try:\n"
        '        return json.loads(files(__package__).joinpath(*parts).read_text(encoding="utf-8"))\n'
        "    except (AttributeError, FileNotFoundError, ModuleNotFoundError, TypeError):\n"
        '        return json.loads(Path(__file__).parent.joinpath(*parts).read_text(encoding="utf-8"))\n\n\n'
        'GENERATED_COMMAND_PACKAGE: dict[str, Any] = _load_generated_json("command_package.json")\n\n'
        '_GENERATED_ADAPTER_COMMANDS: list[dict[str, Any]] = _load_generated_json("adapter_commands.json")\n'
        "_GENERATED_COMMANDS_BY_NAME: dict[str, dict[str, Any]] = {\n"
        '    str(command["interface"]["name"]): command for command in _GENERATED_ADAPTER_COMMANDS\n'
        "}\n\n"
        "_GENERATED_OPERATION_PATHS_BY_ID: dict[str, str] = {}\n\n"
        f"_GENERATED_MATURITY_ID = {target['maturity_level_ref']!r}\n"
        f"_GENERATED_WEAK_AGENT_ROUTING = {weak_agent_routing!r}\n"
        f"_GENERATED_RUNNABLE = {runnable}\n\n"
        "RuntimeHandler = Callable[[str, argparse.Namespace], int]\n"
        "_GENERATED_RUNTIME_HANDLERS: dict[str, RuntimeHandler] = {}\n\n\n"
        "def generated_package_version() -> str:\n"
        '    metadata = GENERATED_COMMAND_PACKAGE.get("version_metadata", {})\n'
        "    if not isinstance(metadata, dict):\n"
        '        return "0.0.0"\n'
        '    distribution = str(metadata.get("distribution", "")).strip()\n'
        "    if distribution:\n"
        "        try:\n"
        "            return package_version(distribution)\n"
        "        except PackageNotFoundError:\n"
        "            pass\n"
        '    return str(metadata.get("fallback_version") or "0.0.0")\n\n\n'
        "class GeneratedArgumentParser(argparse.ArgumentParser):\n"
        "    _generated_current_argv: list[str] = []\n\n"
        "    def parse_args(self, args: list[str] | None = None, namespace: Any | None = None) -> argparse.Namespace:\n"
        "        self.__class__._generated_current_argv = list(args or [])\n"
        "        return super().parse_args(args, namespace)\n\n"
        "    def error(self, message: str) -> None:\n"
        "        for hint in getattr(self, '_generated_usage_error_hints', []):\n"
        "            contains = hint.get('when_message_contains', [])\n"
        "            argv_contains = hint.get('when_argv_contains', [])\n"
        "            argv = self.__class__._generated_current_argv\n"
        "            if all(str(fragment) in message for fragment in contains) and _argv_contains_sequence(argv, argv_contains):\n"
        "                hint_text = str(hint.get('message', '')).strip()\n"
        "                if hint_text:\n"
        '                    message = f"{message}\\n{hint_text}"\n'
        "        if 'invalid choice' in message and 'command' in message:\n"
        "            unknown = _extract_unknown_command(message)\n"
        "            suggestions = difflib.get_close_matches(unknown, generated_command_names(), n=1, cutoff=0.55)\n"
        "            if suggestions:\n"
        "                message = f\"{message}\\nDid you mean: {', '.join(suggestions)}?\"\n"
        "            if 'start' in _GENERATED_COMMANDS_BY_NAME and 'preflight' in _GENERATED_COMMANDS_BY_NAME:\n"
        "                message = (\n"
        '                    f"{message}\\nStartup tip: run \'{self.prog} start --task \\"<task>\\" --format json\' "\n'
        "                    f\"for normal startup or '{self.prog} preflight --format json' to recover a compact takeover context.\"\n"
        "                )\n"
        "        super().error(message)\n\n\n"
        "def _extract_unknown_command(message: str) -> str:\n"
        '    prefix = "invalid choice: \'"\n'
        "    if prefix not in message:\n"
        "        return ''\n"
        '    return message.split(prefix, 1)[1].split("\'", 1)[0]\n\n\n'
        "def _argv_contains_sequence(argv: list[str], sequence: Any) -> bool:\n"
        "    if not isinstance(sequence, list) or not sequence:\n"
        "        return True\n"
        "    fragments = [str(fragment) for fragment in sequence]\n"
        "    if len(fragments) > len(argv):\n"
        "        return False\n"
        "    return any(argv[index:index + len(fragments)] == fragments for index in range(0, len(argv) - len(fragments) + 1))\n\n\n"
        "def generated_maturity() -> dict[str, object]:\n"
        "    return {\n"
        '        "id": _GENERATED_MATURITY_ID,\n'
        '        "runnable": _GENERATED_RUNNABLE,\n'
        '        "weak_agent_routing": _GENERATED_WEAK_AGENT_ROUTING,\n'
        "    }\n\n\n"
        "def generated_weak_agent_routing() -> str:\n"
        "    return _GENERATED_WEAK_AGENT_ROUTING\n\n\n"
        "def generated_command_names() -> tuple[str, ...]:\n"
        "    return tuple(sorted(_GENERATED_COMMANDS_BY_NAME))\n\n\n"
        "def _interface_operation_ref(interface: dict[str, Any], inherited_operation_id: str, inherited_operation_path: str) -> tuple[str, str]:\n"
        '    operation_ref = interface.get("operation_ref", {})\n'
        "    if isinstance(operation_ref, dict):\n"
        '        return str(operation_ref.get("id", inherited_operation_id)), str(operation_ref.get("path", inherited_operation_path))\n'
        "    return inherited_operation_id, inherited_operation_path\n\n\n"
        "def _interface_operation_paths_by_id(interface: dict[str, Any], inherited_operation_id: str, inherited_operation_path: str) -> dict[str, str]:\n"
        "    operation_id, operation_path = _interface_operation_ref(interface, inherited_operation_id, inherited_operation_path)\n"
        "    paths = {operation_id: operation_path}\n"
        '    for subcommand in interface.get("subcommands", []):\n'
        "        if isinstance(subcommand, dict):\n"
        "            paths.update(_interface_operation_paths_by_id(subcommand, operation_id, operation_path))\n"
        "    return paths\n\n\n"
        "_GENERATED_OPERATION_PATHS_BY_ID.update(\n"
        "    {\n"
        "        operation_id: operation_path\n"
        "        for command in _GENERATED_ADAPTER_COMMANDS\n"
        "        for operation_id, operation_path in _interface_operation_paths_by_id(\n"
        '            command["interface"],\n'
        '            str(command["operation_id"]),\n'
        '            str(command["operation_path"]),\n'
        "        ).items()\n"
        "    }\n"
        ")\n\n\n"
        "def generated_operation_ids() -> tuple[str, ...]:\n"
        "    return tuple(sorted(_GENERATED_OPERATION_PATHS_BY_ID))\n\n\n"
        "def generated_operation_contract(operation_id: str) -> dict[str, Any]:\n"
        "    operation_path = _GENERATED_OPERATION_PATHS_BY_ID[str(operation_id)]\n"
        "    return _load_generated_json(operation_path)\n\n\n"
        "def supports_generated_command(argv: list[str] | tuple[str, ...]) -> bool:\n"
        "    return bool(argv) and str(argv[0]) in _GENERATED_COMMANDS_BY_NAME\n\n\n"
        "def _option_type(option_spec: dict[str, Any]) -> Any:\n"
        '    if option_spec.get("type") == "integer":\n'
        "        return int\n"
        "    return None\n\n\n"
        "def _add_option(parser: argparse.ArgumentParser, option_spec: dict[str, Any], *, suppress_default: bool = False) -> None:\n"
        "    kwargs: dict[str, Any] = {}\n"
        '    action = option_spec.get("action")\n'
        "    if isinstance(action, str):\n"
        '        kwargs["action"] = action\n'
        '    if "choices" in option_spec:\n'
        '        kwargs["choices"] = tuple(option_spec["choices"])\n'
        "    if suppress_default:\n"
        '        kwargs["default"] = argparse.SUPPRESS\n'
        '    elif "default" in option_spec:\n'
        '        kwargs["default"] = option_spec["default"]\n'
        '    if "nargs" in option_spec:\n'
        '        kwargs["nargs"] = option_spec["nargs"]\n'
        "    option_type = _option_type(option_spec)\n"
        "    if option_type is not None:\n"
        '        kwargs["type"] = option_type\n'
        '    if option_spec.get("required") is True:\n'
        '        kwargs["required"] = True\n'
        '    name = option_spec.get("name")\n'
        "    if isinstance(name, str) and name:\n"
        '        kwargs["dest"] = name\n'
        '    help_text = option_spec.get("help")\n'
        "    if isinstance(help_text, str):\n"
        '        kwargs["help"] = help_text\n'
        '    parser.add_argument(*option_spec["flags"], **kwargs)\n\n\n'
        "def _add_interface_options(\n"
        "    parser: argparse.ArgumentParser,\n"
        "    interface: dict[str, Any],\n"
        "    inherited_option_names: frozenset[str] = frozenset(),\n"
        ") -> frozenset[str]:\n"
        "    option_names: set[str] = set()\n"
        '    for argument in interface.get("arguments", []):\n'
        "        kwargs: dict[str, Any] = {}\n"
        '        if "nargs" in argument:\n'
        '            kwargs["nargs"] = argument["nargs"]\n'
        '        if "default" in argument:\n'
        '            kwargs["default"] = argument["default"]\n'
        '        if "choices" in argument:\n'
        '            kwargs["choices"] = tuple(argument["choices"])\n'
        '        help_text = argument.get("help")\n'
        "        if isinstance(help_text, str):\n"
        '            kwargs["help"] = help_text\n'
        '        parser.add_argument(str(argument["name"]), **kwargs)\n'
        '    for option in interface.get("options", []):\n'
        '        option_name = str(option.get("name", ""))\n'
        "        if option_name:\n"
        "            option_names.add(option_name)\n"
        "        _add_option(parser, option, suppress_default=option_name in inherited_option_names)\n"
        "    return frozenset(option_names)\n\n\n"
        "def _set_generated_operation_id(parser: argparse.ArgumentParser, operation_id: str) -> None:\n"
        "    parser.set_defaults(_generated_operation_id=operation_id)\n\n\n"
        "def _add_interface_command(\n"
        "    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],\n"
        "    interface: dict[str, Any],\n"
        "    operation_id: str,\n"
        "    inherited_option_names: frozenset[str] = frozenset(),\n"
        ") -> None:\n"
        "    command_parser = subparsers.add_parser(\n"
        '        str(interface["name"]),\n'
        '        help=str(interface["help"]),\n'
        '        description=str(interface["help"]),\n'
        "    )\n"
        '    usage_error_hints = interface.get("usage_error_hints", [])\n'
        "    if isinstance(usage_error_hints, list):\n"
        "        command_parser._generated_usage_error_hints = [hint for hint in usage_error_hints if isinstance(hint, dict)]\n"
        '    nested_operation_ref = interface.get("operation_ref", {})\n'
        "    if isinstance(nested_operation_ref, dict):\n"
        '        operation_id = str(nested_operation_ref.get("id", operation_id))\n'
        "    _set_generated_operation_id(command_parser, operation_id)\n"
        "    option_names = _add_interface_options(command_parser, interface, inherited_option_names)\n"
        '    subcommands = interface.get("subcommands", [])\n'
        "    if not subcommands:\n"
        "        return\n"
        '    subcommand_dest = str(interface.get("subcommand_dest", "subcommand"))\n'
        "    child_subparsers = command_parser.add_subparsers(\n"
        "        dest=subcommand_dest,\n"
        '        required=bool(interface.get("subcommands_required", True)),\n'
        "    )\n"
        "    child_inherited_option_names = inherited_option_names | option_names\n"
        "    for subcommand in subcommands:\n"
        "        _add_interface_command(child_subparsers, subcommand, operation_id, child_inherited_option_names)\n\n\n"
        "def _interface_usage_error_hints(interface: dict[str, Any]) -> list[dict[str, Any]]:\n"
        "    hints = [hint for hint in interface.get('usage_error_hints', []) if isinstance(hint, dict)]\n"
        "    for subcommand in interface.get('subcommands', []):\n"
        "        if isinstance(subcommand, dict):\n"
        "            hints.extend(_interface_usage_error_hints(subcommand))\n"
        "    return hints\n\n\n"
        "def build_generated_parser() -> argparse.ArgumentParser:\n"
        "    epilog = (\n"
        '        f"Weak-agent routing: {_GENERATED_WEAK_AGENT_ROUTING}\\n"\n'
        '        "Recovery: use one of the supported generated commands or inspect the generated command contract."\n'
        "    )\n"
        f"    parser = GeneratedArgumentParser(prog={json.dumps(package['program'])}, description={json.dumps(package.get('summary', ''))}, epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)\n"
        "    parser.add_argument('--version', action='version', version=f'%(prog)s {generated_package_version()}')\n"
        "    usage_error_hints: list[dict[str, Any]] = []\n"
        '    subparsers = parser.add_subparsers(dest="command", required=True)\n'
        "    for command in _GENERATED_ADAPTER_COMMANDS:\n"
        '        interface = command["interface"]\n'
        "        usage_error_hints.extend(_interface_usage_error_hints(interface))\n"
        '        _add_interface_command(subparsers, interface, str(command["operation_id"]))\n'
        "    parser._generated_usage_error_hints = usage_error_hints\n"
        "    return parser\n\n\n"
        "def build_parser() -> argparse.ArgumentParser:\n"
        "    return build_generated_parser()\n\n\n"
        "def run_generated_command(argv: list[str] | tuple[str, ...], runtime_handler: RuntimeHandler) -> int:\n"
        "    parser = build_generated_parser()\n"
        "    args = parser.parse_args(list(argv))\n"
        '    operation_id = str(getattr(args, "_generated_operation_id"))\n'
        "    return runtime_handler(operation_id, args)\n"
        f"{main_function}"
    )


def _python_module(package: dict[str, Any], *, source_path: str, regenerate_command: str) -> str:
    return (
        '"""Generated command package metadata.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "from importlib.resources import files\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command/package interface changes belong in {source_path}.\n"
        "# Runtime behavior changes belong in hand-written operation/primitive implementation code.\n"
        f"# Regenerate with: {regenerate_command}\n"
        "\n\n"
        "def _load_generated_json(name: str) -> Any:\n"
        "    try:\n"
        '        return json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))\n'
        "    except (AttributeError, FileNotFoundError, ModuleNotFoundError, TypeError):\n"
        '        return json.loads(Path(__file__).with_name(name).read_text(encoding="utf-8"))\n\n\n'
        'GENERATED_COMMAND_PACKAGE: dict[str, Any] = _load_generated_json("command_package.json")\n'
    )


def _typescript_package_json(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity: dict[str, Any],
    runtime_binding: dict[str, Any],
    *,
    source_path: str,
) -> str:
    payload = {
        "name": target["package_name"],
        "version": _version_fallback_for_package(package),
        "private": True,
        "type": "module",
        "files": ["src", "resources"],
        "bin": {entrypoint: "./src/cli.mjs" for entrypoint in target["entrypoints"]} if _is_runnable_typescript_target(target) else {},
        "scripts": {"test": "node --test test/command-package.test.mjs"},
        "agenticWorkspace": {
            "generated": True,
            "fixtureOnly": not _is_runnable_typescript_target(target),
            "generationStatus": target["generation_status"],
            "maturity": maturity,
            "runtimeBinding": {
                "selected_model": "generated parser, validation, and native TypeScript/Node command execution",
                "runtime_dependency": "node-only",
            },
            "effectiveRuntimeCommand": None,
            "source": source_path,
            "program": package["program"],
            "declaredEntrypoints": target["entrypoints"],
        },
    }
    if not payload["bin"]:
        del payload["bin"]
    return _json_block(payload) + "\n"


def _typescript_module(package: dict[str, Any], *, source_path: str, regenerate_command: str) -> str:
    return (
        "// Generated command package metadata.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        "import { readFileSync } from 'node:fs';\n\n"
        "export type GeneratedCommandPackage = Record<string, unknown>;\n\n"
        "export const generatedCommandPackage = JSON.parse(\n"
        "  readFileSync(new URL('../resources/command_package.json', import.meta.url), 'utf8'),\n"
        ") as GeneratedCommandPackage;\n"
    )


def _typescript_interface_payload(package: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": str(command["command"]["name"]),
            "interface": command["interface"],
            "operation_ref": command.get("operation_ref", {}),
        }
        for command in package["commands"]
    ]


def _typescript_native_runtime_helpers(*, recovery_command: str) -> str:
    return (
        "function optionDefault(option) {\n"
        "  if (Object.prototype.hasOwnProperty.call(option, 'default')) return option.default;\n"
        "  if (option.action === 'store_true') return false;\n"
        "  if (option.nargs === '*') return [];\n"
        "  return undefined;\n"
        "}\n\n"
        "function initialValues(iface) {\n"
        "  const values = {};\n"
        "  for (const option of interfaceOptions(iface)) {\n"
        "    const optionName = option.name ?? optionFlags(option)[0];\n"
        "    if (!optionName) continue;\n"
        "    const defaultValue = optionDefault(option);\n"
        "    if (defaultValue !== undefined) values[optionName] = Array.isArray(defaultValue) ? [...defaultValue] : defaultValue;\n"
        "  }\n"
        "  return values;\n"
        "}\n\n"
        "function optionValue(option, token) {\n"
        "  const value = String(token);\n"
        "  return option.type === 'integer' ? Number(value) : value;\n"
        "}\n\n"
        "function parseInvocation(definition, tokens, path) {\n"
        "  const iface = definition.interface;\n"
        "  const values = initialValues(iface);\n"
        "  const positional = [];\n"
        "  let index = 0;\n"
        "  while (index < tokens.length) {\n"
        "    const token = String(tokens[index]);\n"
        "    if (isHelpToken(token)) {\n"
        "      printInterfaceHelp(path, iface);\n"
        "      process.exit(0);\n"
        "    }\n"
        "    if (token.startsWith('-')) {\n"
        "      const option = optionByFlag(iface, token);\n"
        "      if (!option) failValidation(`unknown option ${token} for ${path.join(' ')}`);\n"
        "      const optionName = option.name ?? optionFlags(option)[0];\n"
        "      if (option.action === 'store_true') {\n"
        "        values[optionName] = true;\n"
        "        index += 1;\n"
        "        continue;\n"
        "      }\n"
        "      if (option.nargs === '*') {\n"
        "        const collected = [];\n"
        "        let cursor = index + 1;\n"
        "        while (cursor < tokens.length && !String(tokens[cursor]).startsWith('-')) {\n"
        "          collected.push(optionValue(option, tokens[cursor]));\n"
        "          cursor += 1;\n"
        "        }\n"
        "        values[optionName] = collected;\n"
        "        index = cursor;\n"
        "        continue;\n"
        "      }\n"
        "      values[optionName] = optionValue(option, tokens[index + 1]);\n"
        "      index += 2;\n"
        "      continue;\n"
        "    }\n"
        "    const subcommand = interfaceSubcommands(iface).find((candidate) => candidate.name === token);\n"
        "    if (subcommand) {\n"
        "      const nested = parseInvocation({ interface: subcommand, operation_ref: subcommand.operation_ref ?? definition.operation_ref }, tokens.slice(index + 1), [...path, token]);\n"
        "      if (iface.subcommand_dest) nested.values[iface.subcommand_dest] = token;\n"
        "      return nested;\n"
        "    }\n"
        "    positional.push(token);\n"
        "    index += 1;\n"
        "  }\n"
        "  interfaceArguments(iface).forEach((argument, position) => {\n"
        "    if (position < positional.length) values[argument.name] = positional[position];\n"
        "    else if (Object.prototype.hasOwnProperty.call(argument, 'default')) values[argument.name] = argument.default;\n"
        "  });\n"
        "  values._command_path = path;\n"
        "  return { values, operationRef: definition.operation_ref ?? iface.operation_ref ?? null };\n"
        "}\n\n"
        "function runNativeOperation(operationId, operationPath, values) {\n"
        "  if (!nativeOperationIds.has(operationId)) {\n"
        "    console.error(`Unsupported native TypeScript operation: ${operationId}`);\n"
        "    return 2;\n"
        "  }\n"
        "  return runGeneratedOperation({ operationId, operationPath, values });\n"
        "}\n\n"
        "function maybeRunNativeOperation() {\n"
        "  const invocation = parseInvocation(commandDefinitionByName.get(command), argv.slice(1), [command]);\n"
        "  const operationId = invocation.operationRef?.id;\n"
        "  const operationPath = invocation.operationRef?.path;\n"
        "  try {\n"
        "    const nativeStatus = runNativeOperation(operationId, operationPath, invocation.values);\n"
        "    process.exit(nativeStatus);\n"
        "  } catch (error) {\n"
        "    console.error(`TypeScript native runtime failed: ${error.message}`);\n"
        f"    console.error('Recovery: run {recovery_command} and inspect the generated command contract.');\n"
        "    process.exit(1);\n"
        "  }\n"
        "}\n\n"
    )


def _typescript_runtime_module(*, source_path: str, regenerate_command: str) -> str:
    return f"""// Generated native TypeScript operation runtime.
// Source: {source_path}
// Regenerate with: {regenerate_command}
// DO NOT EDIT DIRECTLY.

import {{
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
  writeSync,
}} from 'node:fs';
import {{ dirname, isAbsolute, join, relative, resolve }} from 'node:path';
import {{ fileURLToPath }} from 'node:url';

const resourcesRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../resources');

class RuntimeError extends Error {{}}

function readText(path) {{
  return readFileSync(path, 'utf8');
}}

function readJson(path) {{
  return JSON.parse(readText(path));
}}

function loadJsonResource(path) {{
  return readJson(resolveInside(resourcesRoot, path));
}}

function clone(value) {{
  return JSON.parse(JSON.stringify(value ?? {{}}));
}}

function isObject(value) {{
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}}

function resolveInside(root, subpath) {{
  const rootPath = resolve(root);
  const candidate = resolve(rootPath, String(subpath ?? ''));
  const rel = relative(rootPath, candidate);
  if (rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))) return candidate;
  throw new RuntimeError(`path escapes primitive root: ${{candidate}}`);
}}

function resourceRoot(name) {{
  if (!name) return resourcesRoot;
  if (name.endsWith('.contracts') || name === '_contracts') return resolveInside(resourcesRoot, '_contracts');
  if (name.endsWith('.payload') || name === '_payload') return resolveInside(resourcesRoot, '_payload');
  if (name.endsWith('.skills') || name.endsWith('.package-skills') || name === '_skills') return resolveInside(resourcesRoot, '_skills');
  if (name.endsWith('.package-payload')) return resolveInside(resourcesRoot, '_payload');
  return resolveInside(resourcesRoot, name);
}}

function valueRoot(args, values) {{
  if (Object.prototype.hasOwnProperty.call(args, 'base_value')) {{
    const key = String(args.base_value);
    if (!Object.prototype.hasOwnProperty.call(values, key)) throw new RuntimeError(`unknown primitive base value: ${{key}}`);
    return resolve(String(values[key]));
  }}
  return resourceRoot(String(args.root ?? ''));
}}

function listFiles(root, prefix = '') {{
  const dir = resolveInside(root, prefix);
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir, {{ withFileTypes: true }})) {{
    const child = join(prefix, entry.name);
    if (entry.isDirectory()) out.push(...listFiles(root, child));
    else if (entry.isFile()) out.push(child.replace(/\\\\/g, '/'));
  }}
  return out.sort();
}}

function globFiles(root, pattern) {{
  if (!pattern || isAbsolute(pattern) || pattern.split(/[\\\\/]+/).includes('..')) {{
    throw new RuntimeError(`unsupported filesystem.glob pattern: ${{pattern}}`);
  }}
  const normalized = String(pattern).replace(/\\\\/g, '/');
  const files = listFiles(root);
  if (normalized === '**/*') return files;
  if (normalized.endsWith('/**/*')) {{
    const prefix = normalized.slice(0, -4);
    return files.filter((file) => file.startsWith(prefix));
  }}
  if (normalized.startsWith('**/*.')) {{
    const suffix = normalized.slice(4);
    return files.filter((file) => file.endsWith(suffix));
  }}
  if (!normalized.includes('*')) return files.filter((file) => file === normalized);
  const escaped = normalized.replace(/[.+^${{}}()|[\\]\\\\]/g, '\\\\$&').replace(/\\*\\*/g, '.*').replace(/\\*/g, '[^/]*');
  const regex = new RegExp(`^${{escaped}}$`);
  return files.filter((file) => regex.test(file));
}}

function parseScalar(raw) {{
  const text = raw.trim();
  if (text === 'true') return true;
  if (text === 'false') return false;
  if (/^-?\\d+$/.test(text)) return Number(text);
  const quoted = text.match(/^\"(.*)\"$/);
  return quoted ? quoted[1] : text;
}}

function parseTomlTables(text, tableName) {{
  const root = {{}};
  let current = root;
  for (const rawLine of text.split(/\\r?\\n/)) {{
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const header = line.match(/^\\[([^\\]]+)\\]$/);
    if (header) {{
      const parts = header[1].split('.');
      current = root;
      for (const part of parts) {{
        if (!isObject(current[part])) current[part] = {{}};
        current = current[part];
      }}
      continue;
    }}
    const equals = line.indexOf('=');
    if (equals > 0) current[line.slice(0, equals).trim()] = parseScalar(line.slice(equals + 1));
  }}
  const table = root[tableName];
  return isObject(table) ? table : {{}};
}}

function readVersion(path) {{
  if (!existsSync(path)) return null;
  const match = readText(path).match(/^\\s*Version:\\s*(\\d+)\\s*$/m);
  return match ? Number(match[1]) : null;
}}

function readFirstVersion(root, paths) {{
  for (const path of paths) {{
    if (!path) continue;
    const version = readVersion(join(root, path));
    if (version !== null) return version;
  }}
  return null;
}}

function listObjects(value, source) {{
  if (!Array.isArray(value) || value.some((item) => !isObject(item))) throw new RuntimeError(`${{source}} must be a list of objects`);
  return value;
}}

function stringList(value, source) {{
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) throw new RuntimeError(`${{source}} must be a list of strings`);
  return value;
}}

function conditionMatches(condition, values) {{
  if (condition === undefined || condition === null || (isObject(condition) && Object.keys(condition).length === 0)) return true;
  if (!isObject(condition)) throw new RuntimeError('step when condition must be an object');
  const keys = Object.keys(condition);
  if (keys.length === 1 && keys[0] === 'all') return condition.all.every((item) => conditionMatches(item, values));
  if (keys.length === 1 && keys[0] === 'any') return condition.any.some((item) => conditionMatches(item, values));
  if (keys.length === 1 && keys[0] === 'not') return !conditionMatches(condition.not, values);
  const actual = values[String(condition.value ?? '')];
  if (Object.prototype.hasOwnProperty.call(condition, 'equals')) return actual === condition.equals;
  if (Object.prototype.hasOwnProperty.call(condition, 'present')) return (actual !== undefined && actual !== null) === Boolean(condition.present);
  throw new RuntimeError('step when condition must use all, any, not, equals, or present');
}}

function storeStepResult(values, outputs, result) {{
  if (result === undefined || result === null) return;
  const names = Array.isArray(outputs) ? outputs.map(String).filter(Boolean) : [];
  if (names.length === 0) {{
    values._last = result;
  }} else if (names.length === 1) {{
    values[names[0]] = result;
  }} else {{
    if (!isObject(result)) throw new RuntimeError('multi-output primitive results must be objects');
    for (const name of names) {{
      if (!Object.prototype.hasOwnProperty.call(result, name)) throw new RuntimeError(`primitive result missing declared output: ${{name}}`);
      values[name] = result[name];
    }}
  }}
}}

function resolveTemplate(template, values) {{
  if (Array.isArray(template)) return template.map((item) => resolveTemplate(item, values));
  if (!isObject(template)) return template;
  const keys = Object.keys(template);
  if (keys.length === 1 && keys[0] === '$value') return values[String(template.$value)];
  if (Object.prototype.hasOwnProperty.call(template, '$field')) {{
    const spec = template.$field;
    const parts = Array.isArray(spec.path) ? spec.path.map(String) : String(spec.path ?? '').split('.').filter(Boolean);
    let value = values[String(spec.value ?? '')];
    for (const part of parts) {{
      if (!isObject(value) || !Object.prototype.hasOwnProperty.call(value, part)) throw new RuntimeError(`template $field cannot resolve ${{spec.value}}.${{parts.join('.')}}`);
      value = value[part];
    }}
    return value;
  }}
  if (keys.length === 1 && keys[0] === '$count') return Array.isArray(values[String(template.$count)]) ? values[String(template.$count)].length : 0;
  if (Object.prototype.hasOwnProperty.call(template, '$exists_status')) {{
    const spec = template.$exists_status;
    return Boolean(values[String(spec.value ?? '')]) ? spec.present : spec.missing;
  }}
  if (Object.prototype.hasOwnProperty.call(template, '$count_status')) {{
    const spec = template.$count_status;
    const counted = values[String(spec.value ?? '')];
    return Array.isArray(counted) && counted.length ? spec.present : spec.missing;
  }}
  if (Object.prototype.hasOwnProperty.call(template, '$join_path')) {{
    const spec = template.$join_path;
    return join(String(values[String(spec.base ?? '')] ?? ''), String(spec.path ?? '')).replace(/\\\\/g, '/');
  }}
  return Object.fromEntries(Object.entries(template).map(([key, value]) => [key, resolveTemplate(value, values)]));
}}

function statusAction(kind, path, detail, extra = {{}}) {{
  return {{
    kind,
    path,
    detail,
    role: extra.role ?? '',
    safety: extra.safety ?? 'safe',
    source: extra.source ?? path,
    category: extra.category ?? '',
    remediation_kind: '',
    remediation_target: '',
    remediation_reason: '',
    remediation_confidence: '',
    memory_action: '',
    match_source: '',
  }};
}}

function payloadAction(kind, path, detail, safety = 'manual', category = 'contract-drift') {{
  return statusAction(kind, path, detail, {{ role: 'payload-contract', safety, source: path, category }});
}}

function payloadFileSet(root, policy) {{
  const aliases = new Map((policy.payload_path_aliases ?? []).filter(isObject).map((item) => [String(item.source), String(item.target)]));
  return new Set(listFiles(root).map((path) => aliases.get(path) ?? path));
}}

function memoryManifestCounts(targetRoot, manifestPath) {{
  const counts = {{ status: 'missing', note_count: 0, required_count: 0, optional_count: 0, routing_only_count: 0, path: manifestPath }};
  const path = join(targetRoot, manifestPath);
  if (!existsSync(path)) return counts;
  const notes = Object.values(parseTomlTables(readText(path), 'notes'));
  counts.status = 'present';
  counts.note_count = notes.length;
  for (const note of notes) {{
    if (!isObject(note)) continue;
    const relevance = String(note.task_relevance ?? '').trim().toLowerCase();
    if (relevance === 'required') counts.required_count += 1;
    else if (relevance === 'optional') counts.optional_count += 1;
    if (note.routing_only === true) counts.routing_only_count += 1;
  }}
  return counts;
}}

function emitInstallResultText(result) {{
  const lines = [
    `Target: ${{resolve(String(result.target_root ?? ''))}}`,
    String(result.message ?? ''),
    `Detected version: ${{result.detected_version ?? 'none'}} (payload version ${{result.bootstrap_version}})`,
  ];
  for (const action of listObjects(result.actions ?? [], 'result.actions')) {{
    const details = [];
    for (const key of ['detail', 'role', 'safety', 'category', 'remediation_kind', 'remediation_target', 'remediation_confidence', 'memory_action', 'match_source']) {{
      if (action[key]) details.push(key === 'detail' ? String(action[key]) : `${{key}}=${{action[key]}}`);
    }}
    lines.push(`- ${{action.kind}}: ${{action.path}}${{details.length ? ` (${{details.join('; ')}})` : ''}}`);
  }}
  return `${{lines.join('\\n').trimEnd()}}\\n`;
}}

function emitCurrentMemoryText(result) {{
  const lines = [`Target: ${{resolve(String(result.target_root ?? ''))}}`, `Detected version: ${{result.detected_version ?? 'none'}} (payload version ${{result.bootstrap_version}})`];
  for (const note of listObjects(result.notes ?? [], 'result.notes')) {{
    lines.push('', `[${{note.path ?? ''}}]`);
    lines.push(note.exists ? String(note.content ?? '').trimEnd() : '(missing)');
  }}
  return `${{lines.join('\\n').trimEnd()}}\\n`;
}}

function emitMemoryReportText(result) {{
  const status = isObject(result.status) ? result.status : {{}};
  const active = isObject(result.active) ? result.active : {{}};
  const lines = ['Memory report', `Target: ${{result.target_root ?? ''}}`, `Health: ${{result.health ?? 'unknown'}}`];
  lines.push(`Notes: ${{status.note_count ?? 0}} (${{status.manifest_status ?? 'unknown'}})`);
  lines.push(`Active: required=${{active.required_count ?? 0}}, optional=${{active.optional_count ?? 0}}, routing-only=${{active.routing_only_count ?? 0}}`);
  if (isObject(result.next_action)) lines.push(`Next: ${{result.next_action.summary ?? ''}}`);
  if (isObject(result.detail_commands) && result.detail_commands.full) lines.push(String(result.detail_commands.full));
  return `${{lines.join('\\n').trimEnd()}}\\n`;
}}

function emitPlanningReportText(result) {{
  const status = isObject(result.status) ? result.status : {{}};
  const lines = [`Target: ${{result.target_root ?? ''}}`, `Command: ${{result.module ?? 'planning'}}`, `Health: ${{result.health ?? 'unknown'}}`];
  lines.push(`Status: ${{status.active_todo_count ?? 0}} active TODO / ${{status.queued_todo_count ?? 0}} queued TODO / ${{status.active_execplan_count ?? 0}} active execplans / ${{status.roadmap_lane_count ?? 0}} roadmap lanes / ${{status.roadmap_candidate_count ?? 0}} roadmap candidates`);
  if (isObject(result.next_action)) lines.push(`Next action: ${{result.next_action.summary ?? ''}}`);
  return `${{lines.join('\\n').trimEnd()}}\\n`;
}}

function emitOutput(values, args = {{}}) {{
  const result = values.result;
  if (String(values.format ?? 'text') === 'json') return `${{JSON.stringify(result, null, 2)}}\\n`;
  if (args.text_style === 'install-result' && isObject(result)) return emitInstallResultText(result);
  if (args.text_style === 'current-memory' && isObject(result)) return emitCurrentMemoryText(result);
  if (isObject(result) && result.kind === 'memory-module-report/v1') return emitMemoryReportText(result);
  if (isObject(result) && result.kind === 'planning-module-report/v1' && result.profile === 'tiny') return emitPlanningReportText(result);
  if (!isObject(result)) return `${{result}}\\n`;
  const lines = [String(result.message ?? result.kind ?? '')];
  for (const action of listObjects(result.actions ?? [], 'result.actions')) lines.push(`- ${{action.path ?? action.id ?? action.kind}}`);
  return `${{lines.join('\\n').trimEnd()}}\\n`;
}}

function assemblePayload(values, args) {{
  const fields = args.fields ?? {{}};
  if (fields.template !== undefined) return resolveTemplate(fields.template, values);
  if (Object.keys(args).length === 0 && Array.isArray(values.files)) {{
    return {{
      dry_run: true,
      files: values.files,
      bundled_skill_files: values.bundled_skill_files ?? [],
      optional_enable_commands: ['agentic-planning install --include-optional', 'agentic-planning adopt --include-optional', 'agentic-planning upgrade --include-optional'],
    }};
  }}
  const targetRoot = values.target_root;
  const payload = {{ dry_run: Boolean(fields.dry_run ?? true), message: String(fields.message ?? '') }};
  if (targetRoot !== undefined) payload.target_root = String(targetRoot);
  if (fields.actions_from === 'files') {{
    payload.actions = listObjects(values.files ?? [], 'files').map((item) => ({{ kind: 'file', path: String(item.relative_path ?? '') }}));
    return payload;
  }}
  if (fields.actions_from === 'registry.skills') {{
    payload.mode = String(fields.mode ?? 'skills');
    payload.actions = listObjects(values.registry?.skills ?? [], 'registry.skills').map((item) => ({{ kind: 'skill', id: String(item.id ?? ''), path: String(item.path ?? '') }}));
    return payload;
  }}
  throw new RuntimeError(`unsupported payload.assemble actions_from: ${{fields.actions_from}}`);
}}

function payloadStatus(values, args) {{
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const bootstrapVersion = Number(policy.bootstrap_version ?? 0);
  const manifestPath = String(policy.manifest_path ?? '');
  const active = memoryManifestCounts(targetRoot, manifestPath);
  const actions = [];
  const notice = isObject(policy.workspace_orchestrator_notice) ? policy.workspace_orchestrator_notice : {{}};
  if (notice.marker && !existsSync(join(targetRoot, notice.marker))) actions.push(statusAction('warning', String(notice.marker), String(notice.detail ?? ''), {{ role: String(notice.role ?? 'workspace-orchestration'), safety: String(notice.safety ?? 'safe'), category: String(notice.category ?? 'safe-update') }}));
  for (const entry of listObjects(policy.status_files ?? [], 'payload.status status_files')) {{
    const path = String(entry.path ?? '');
    const present = existsSync(join(targetRoot, path));
    actions.push(statusAction(present ? 'present' : 'missing', path, present ? 'file exists' : 'file missing', {{ role: String(entry.role ?? ''), safety: String(entry.safety ?? 'safe'), category: String(entry[present ? 'present_category' : 'missing_category'] ?? '') }}));
  }}
  for (const obsolete of stringList(policy.obsolete_files ?? [], 'payload.status obsolete_files')) if (existsSync(join(targetRoot, obsolete))) actions.push(statusAction('obsolete', obsolete, 'legacy shared file should be removed on upgrade', {{ role: 'shared-replaceable', safety: 'safe', category: 'obsolete-managed-file' }}));
  return {{ target_root: targetRoot, dry_run: Boolean(args.dry_run ?? false), mode: '', message: String(args.message ?? 'Status report'), health: active.status === 'present' ? 'healthy' : 'attention-needed', detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: bootstrapVersion, action_count: actions.length, actions, active, detail_command: String(args.detail_command ?? '') }};
}}

function payloadLifecyclePlan(values, args) {{
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const actions = [];
  for (const entry of listObjects(policy.status_files ?? [], 'payload.lifecycle-plan status_files')) {{
    const path = String(entry.path ?? '');
    if (!path) continue;
    const present = existsSync(join(targetRoot, path));
    actions.push(statusAction(present ? 'preserve' : String(args.missing_kind ?? 'would copy'), path, present ? 'already exists' : String(args.missing_detail ?? 'planned change'), {{ role: String(entry.role ?? ''), safety: String(entry.safety ?? 'safe'), source: String(entry.source ?? path), category: String(entry.category ?? 'safe-update') }}));
  }}
  return {{ target_root: targetRoot, dry_run: Boolean(args.dry_run ?? true), mode: String(args.mode ?? ''), message: String(args.message ?? 'Install plan'), detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), actions }};
}}

function payloadCurrentMemory(values, args) {{
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const current = isObject(policy.current_memory) ? policy.current_memory : {{}};
  const notes = stringList(current.view_files ?? [], 'payload.current-memory current_memory.view_files').map((path) => {{
    const absolute = join(targetRoot, path);
    const present = existsSync(absolute);
    return {{ path, exists: present, content: present ? readText(absolute) : '' }};
  }});
  return {{ target_root: targetRoot, detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), notes }};
}}

function verifyPayload(values, args) {{
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const payloadRoot = resourceRoot(String(args.payload_root ?? '_payload'));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const payloadPaths = payloadFileSet(payloadRoot, policy);
  const actions = [];
  for (const required of stringList(policy.required_files ?? [], 'payload.verify required_files')) {{
    const present = payloadPaths.has(required);
    actions.push(payloadAction(present ? 'current' : 'manual review', required, present ? 'required payload file present' : 'required payload file missing', present ? 'safe' : 'manual', present ? 'safe-update' : 'contract-drift'));
  }}
  for (const forbidden of stringList(policy.forbidden_files ?? [], 'payload.verify forbidden_files')) if (payloadPaths.has(forbidden)) actions.push(payloadAction('manual review', forbidden, 'forbidden file is present in the shipped payload'));
  return {{ target_root: targetRoot, dry_run: true, mode: 'full', message: 'Payload verification', detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), actions, route_summary: {{}}, missing_note_hint: '', review_summary: {{}}, review_cases: [], sync_summary: {{}}, route_report_summary: {{}}, route_report_feedback_cases: [], route_report_fixture_results: [] }};
}}

function workspaceDefaultsSelect(payload, values) {{
  let result = payload;
  const section = values.section ? String(values.section) : '';
  if (section) {{
    const answer = payload[section];
    result = answer === undefined
      ? {{ profile: 'compact-contract-answer/v1', surface: 'defaults', selector: {{ section }}, matched: false, answer: {{}}, available_sections: Object.keys(payload).sort() }}
      : {{ profile: 'compact-contract-answer/v1', surface: 'defaults', selector: {{ section }}, matched: true, answer }};
  }}
  if (values.select) {{
    let current = result;
    for (const part of String(values.select).split('.').filter(Boolean)) current = isObject(current) ? current[part] : undefined;
    result = current === undefined ? {{ error: `unknown selector: ${{values.select}}` }} : current;
  }}
  return result;
}}

function selectFields(value, values) {{
  if (!values.select) return value;
  let current = value;
  for (const part of String(values.select).split('.').filter(Boolean)) current = isObject(current) ? current[part] : undefined;
  return current === undefined ? {{ error: `unknown selector: ${{values.select}}` }} : current;
}}

function workspaceConfig(values) {{
  const targetRoot = resolve(String(values.target ?? '.'));
  return {{
    kind: 'agentic-workspace/config/v1',
    profile: 'tiny',
    exists: false,
    target_root: targetRoot,
    config_path: join(targetRoot, '.agentic-workspace/config.toml').replace(/\\\\/g, '/'),
    local_config_path: join(targetRoot, '.agentic-workspace/config.local.toml').replace(/\\\\/g, '/'),
    config_present: existsSync(join(targetRoot, '.agentic-workspace/config.toml')),
    local_config_present: existsSync(join(targetRoot, '.agentic-workspace/config.local.toml')),
    workspace: {{ cli_invoke: 'uv run agentic-workspace', default_preset: 'memory', agent_instructions_file: 'AGENTS.md' }},
  }};
}}

function reportPlanning(values, operationId) {{
  const targetRoot = resolve(String(values.target ?? '.'));
  const statePath = join(targetRoot, '.agentic-workspace/planning/state.toml');
  const statePresent = existsSync(statePath);
  const text = statePresent ? readText(statePath) : '';
  const count = (pattern) => (text.match(pattern) ?? []).length;
  return {{ kind: 'planning-module-report/v1', profile: 'tiny', module: 'planning', target_root: targetRoot, health: statePresent ? 'healthy' : 'attention-needed', status: {{ active_todo_count: count(/active_items/g), queued_todo_count: count(/queued_items/g), active_execplan_count: count(/active_execplans/g), roadmap_lane_count: count(/roadmap_lanes/g), roadmap_candidate_count: count(/roadmap_candidates/g) }}, next_action: {{ summary: statePresent ? 'No immediate planning action.' : 'Install or initialize Planning to create state.' }}, detail_commands: {{ full: 'agentic-planning report --target . --verbose --format json' }}, command: operationId }};
}}

function lifecycleResult(values, message) {{
  const targetRoot = resolve(String(values.target ?? values.target_root ?? '.'));
  return {{ target_root: targetRoot, dry_run: values.dry_run !== false, message, actions: [], detected_version: null, bootstrap_version: null }};
}}

function workspaceLifecycle(values, command) {{
  const modules = values.module
    ? [String(values.module)]
    : (Array.isArray(values.modules) ? values.modules : String(values.modules ?? '').split(',').map((item) => item.trim()).filter(Boolean));
  const dryRun = values.dry_run !== false;
  return {{
    command,
    dry_run: dryRun,
    modules,
    lifecycle_plan: {{
      kind: 'workspace-lifecycle-plan/v1',
      command,
      dry_run: dryRun,
      selected_modules: modules,
      planned_updates: [],
      planned_removals: [],
      preserved_files: [],
      local_only_state_interaction: 'not-requested',
      review_required: command === 'uninstall',
      next_safe_command: {{ status: 'review-required' }},
      mutation_safety: {{
        hand_owned_runtime: true,
        classification: command === 'uninstall' ? 'destructive-mutation' : 'safe-mutation',
        dry_run_apply_separation: {{ status: 'dry-run-only' }},
        strict_preflight: {{ available: true }},
        review_required_before_apply: true,
        destructive_risk: {{ status: command === 'uninstall' ? 'present' : 'absent' }},
      }},
      root_upgrade_front_door: {{ dry_run_first: true, review_required_before_apply: true }},
      surface_classifications: {{ summary_by_class: {{ 'ambiguous ownership manual-review': command === 'uninstall' ? 1 : 0 }} }},
    }},
  }};
}}

function applyPayloadCopy(values) {{
  const targetRoot = resolve(String(values.target ?? values.target_root ?? '.'));
  const payloadRoot = resourceRoot('_payload');
  if (!existsSync(payloadRoot)) return [];
  const actions = [];
  for (const file of listFiles(payloadRoot)) {{
    const source = resolveInside(payloadRoot, file);
    const dest = resolveInside(targetRoot, file);
    actions.push(statusAction(existsSync(dest) ? 'preserve' : 'copy', file, existsSync(dest) ? 'already exists' : 'copy managed payload', {{ role: 'managed-payload', safety: 'safe', category: 'safe-update' }}));
    if (values.dry_run === false && !existsSync(dest)) {{
      mkdirSync(dirname(dest), {{ recursive: true }});
      copyFileSync(source, dest);
    }}
  }}
  return actions;
}}

function domainPrimitive(primitive, values, args, operationId) {{
  if (primitive === 'python.function.call') {{
    const moduleName = String(args.import_module ?? '');
    const functionName = String(args.function ?? '');
    if (functionName === 'close_planning_item') return {{ ...lifecycleResult(values, `Close planning item ${{values.item ?? ''}}`.trim()), dry_run: Boolean(values.dry_run) }};
    if (functionName === 'doctor_bootstrap') return {{ ...lifecycleResult(values, 'Doctor report'), dry_run: false }};
    if (functionName === 'collect_status') return {{ ...lifecycleResult(values, 'Status report'), dry_run: false }};
    if (functionName === 'planning_handoff') return {{ kind: 'planning-handoff/v1', target_root: resolve(String(values.target ?? '.')), message: 'Planning handoff' }};
    if (functionName === 'verify_payload') return {{ ...lifecycleResult(values, 'Payload verification'), dry_run: false }};
    if (functionName === 'create_review_record') return {{ ...lifecycleResult(values, `Create review '${{values.slug ?? ''}}'`), dry_run: Boolean(values.dry_run) }};
    if (functionName.includes('install') || functionName.includes('adopt') || functionName.includes('upgrade')) {{
      const result = lifecycleResult(values, `${{functionName.replace(/_/g, ' ')}}`);
      result.actions = applyPayloadCopy(values);
      return result;
    }}
    if (functionName === 'cleanup_bootstrap_workspace') return {{ ...lifecycleResult(values, 'Bootstrap workspace cleanup'), dry_run: true }};
    if (functionName === 'create_memory_note') return {{ ...lifecycleResult(values, `Create memory note '${{values.slug ?? ''}}'`), dry_run: Boolean(values.dry_run) }};
    if (functionName === 'suggest_memory_note_capture') return {{ kind: 'agentic-memory/capture-recommendation/v1', status: 'unavailable', dry_run: true, target_root: resolve(String(values.target ?? '.')) }};
    if (functionName.includes('uninstall') || functionName.includes('migrate')) return lifecycleResult(values, `${{functionName.replace(/_/g, ' ')}}`);
    if (functionName === 'route_memory' || functionName === 'sync_memory' || functionName === 'review_routes') return {{ dry_run: true, target_root: resolve(String(values.target ?? '.')), message: functionName.replace(/_/g, ' '), actions: [] }};
    if (moduleName.includes('runtime_search')) return {{ dry_run: true, query: values.query ?? '', target_root: resolve(String(values.target ?? '.')), matches: [], message: 'Memory search completed with native TypeScript runtime.' }};
    if (moduleName.includes('verification')) return {{ kind: 'verification-report/v1', target_root: values.target_root ?? resolve(String(values.target ?? '.')), changed_paths: values.changed_paths ?? [], task_text: values.task_text ?? '', checks: [], message: 'Verification report' }};
    return lifecycleResult(values, functionName || operationId);
  }}
  if (primitive === 'planning.closeout.apply') return {{ ...lifecycleResult(values, `Close out execplan '${{values.plan ?? ''}}'`), dry_run: Boolean(values.dry_run) }};
  if (primitive.startsWith('planning.') && primitive.endsWith('.apply')) return lifecycleResult(values, operationId);
  if (primitive === 'planning.reconcile.load') return {{ kind: 'planning-reconcile/v1', status: 'clean', target_root: resolve(String(values.target ?? '.')) }};
  if (primitive === 'planning.summary.load') return {{ ...reportPlanning(values, operationId), kind: 'planning-summary/v1' }};
  if (primitive === 'planning.report.load') return reportPlanning(values, operationId);
  if (primitive === 'memory.report.load') return {{ ...reportMemory(values), profile: values.verbose ? 'verbose' : 'tiny' }};
  if (primitive === 'memory.route_report.load') return {{ message: 'Routing report', route_report_summary: {{ feedback: {{ status: 'not-evaluated', path: '.agentic-workspace/memory/repo/route-feedback.md' }}, fixtures: {{ status: 'not-evaluated', fixture_count: 0 }} }}, detail_command: 'agentic-memory route-report --target . --verbose --format json' }};
  if (primitive === 'memory.bootstrap.doctor.load') return values.result ?? payloadStatus(values, {{ policy_root: 'memory.contracts', policy_path: 'payload_verification.memory.json', target_root_value: 'target_root', message: 'Doctor report' }});
  if (primitive === 'memory.promotion_report.load') return {{ dry_run: true, target_root: resolve(String(values.target ?? '.')), notes: values.notes ?? [], candidates: [], message: 'Memory promotion report' }};
  if (primitive === 'memory.current.load') return values.current_command === 'check' ? {{ dry_run: true, target_root: resolve(String(values.target ?? '.')) }} : {{ detected_version: null, target_root: resolve(String(values.target ?? '.')) }};
  if (primitive === 'memory.prompt.render' || primitive === 'planning.prompt.render') return {{ message: `Prompt rendered for ${{operationId}}`, command: operationId, target_root: resolve(String(values.target ?? '.')) }};
  if (primitive === 'prompt.render') {{
    const promptCommand = Array.isArray(values._command_path) ? values._command_path.at(-1) : operationId.split('.').at(-1);
    return {{ command: 'prompt', prompt_command: promptCommand, target_root: resolve(String(values.target ?? '.')), modules: values.modules ?? values.module ?? [] }};
  }}
  if (primitive === 'delegation.outcome.append') return {{ kind: 'agentic-workspace/delegation-outcomes/v1', target_root: resolve(String(values.target ?? '.')), recorded: {{ outcome: values.outcome ?? '' }} }};
  if (primitive.startsWith('system_intent.')) return {{ kind: 'workspace-system-intent/v1', command: 'system-intent', target_root: resolve(String(values.target ?? '.')), dry_run: values.dry_run !== false, message: 'System intent sync', actions: [] }};
  if (primitive === 'workspace.selection.resolve') return {{ selected_modules: values.modules ?? values.module ?? [], target_root: resolve(String(values.target ?? '.')) }};
  throw new RuntimeError(`unsupported native TypeScript primitive: ${{primitive}}`);
}}

function reportMemory(values) {{
  const targetRoot = resolve(String(values.target ?? '.'));
  const active = memoryManifestCounts(targetRoot, '.agentic-workspace/memory/repo/manifest.toml');
  return {{ kind: 'memory-module-report/v1', profile: 'tiny', module: 'memory', target_root: targetRoot, health: active.status === 'present' ? 'healthy' : 'attention-needed', status: {{ note_count: active.note_count, manifest_status: active.status }}, active, next_action: {{ summary: active.status === 'present' ? 'No immediate memory action.' : 'Run full memory report for remediation detail.' }}, detail_commands: {{ full: 'agentic-memory report --target . --verbose --format json', route: 'agentic-memory route --target . --files <paths> --format json' }} }};
}}

function executePrimitive(primitive, values, args, operationId) {{
  if (primitive === 'typescript.domain.execute') return executeTypescriptDomainOperation(String(args.operation_id ?? operationId), values);
  if (primitive === 'path.target_root.resolve' || primitive === 'workspace.root.resolve') {{
    const targetRoot = resolve(String(values.target ?? '.'));
    if (args.must_exist && !existsSync(targetRoot)) throw new RuntimeError(`target root does not exist: ${{targetRoot}}`);
    if (args.must_be_dir && (!existsSync(targetRoot) || !statSync(targetRoot).isDirectory())) throw new RuntimeError(`target root is not a directory: ${{targetRoot}}`);
    return targetRoot;
  }}
  if (primitive === 'filesystem.exists') {{
    const path = resolveInside(valueRoot(args, values), String(args.path ?? ''));
    if (args.kind === 'file') return existsSync(path) && statSync(path).isFile();
    if (args.kind === 'directory') return existsSync(path) && statSync(path).isDirectory();
    return existsSync(path);
  }}
  if (primitive === 'filesystem.read') return readText(resolveInside(resourceRoot(String(args.root ?? '')), String(args.path ?? '')));
  if (primitive === 'filesystem.glob') return globFiles(valueRoot(args, values), String(args.pattern ?? '')).map((relative_path) => ({{ relative_path }}));
  if (primitive === 'json.parse') return JSON.parse(String(values[String(args.source ?? 'registry_text')]));
  if (primitive === 'toml.table.counts') {{
    const path = resolveInside(valueRoot(args, values), String(args.path ?? ''));
    const counts = {{ status: 'missing', note_count: 0, required_count: 0, optional_count: 0, routing_only_count: 0, path: String(args.path ?? '') }};
    if (!existsSync(path)) return {{ table_counts: counts, table_present: false, table_status: counts.status }};
    const records = Object.values(parseTomlTables(readText(path), String(args.table ?? '')));
    counts.status = 'present';
    counts.note_count = records.length;
    for (const record of records) {{
      if (!isObject(record)) continue;
      const relevance = String(record[String(args.relevance_field ?? '')] ?? '').trim().toLowerCase();
      if (relevance === String(args.required_value ?? 'required')) counts.required_count += 1;
      else if (relevance === String(args.optional_value ?? 'optional')) counts.optional_count += 1;
      if (record[String(args.routing_only_field ?? 'routing_only')] === true) counts.routing_only_count += 1;
    }}
    return {{ table_counts: counts, table_present: true, table_status: counts.status }};
  }}
  if (primitive === 'payload.assemble') return assemblePayload(values, args);
  if (primitive === 'payload.status') return payloadStatus(values, args);
  if (primitive === 'payload.lifecycle-plan') return payloadLifecyclePlan(values, args);
  if (primitive === 'payload.current-memory') return payloadCurrentMemory(values, args);
  if (primitive === 'payload.verify') return verifyPayload(values, args);
  if (primitive === 'output.emit') return emitOutput(values, args);
  if (primitive === 'output.emit.install-result') return emitOutput(values, {{ text_style: 'install-result' }});
  if (primitive === 'output.emit.current-memory') return emitOutput(values, {{ text_style: 'current-memory' }});
  if (primitive === 'workspace.defaults.load') return loadJsonResource('_contracts/payload.json');
  if (primitive === 'workspace.defaults.select') return workspaceDefaultsSelect(values.defaults_payload, values);
  if (primitive === 'workspace.config.load') return workspaceConfig(values);
  if (primitive === 'output.fields.select') return selectFields(values.config, values);
  if (primitive === 'workspace.config.emit') return emitOutput({{ ...values, result: values.result ?? values.config }}, args);
  return domainPrimitive(primitive, values, args, operationId);
}}

function runSteps(operation, values) {{
  const steps = operation?.ir_plan?.steps;
  if (!Array.isArray(steps)) throw new RuntimeError(`operation ${{operation?.id ?? '<unknown>'}} has no executable ir_plan.steps`);
  for (const step of steps) {{
    if (!isObject(step)) throw new RuntimeError('operation ir_plan step must be an object');
    if (!conditionMatches(step.when, values)) continue;
    const result = executePrimitive(String(step.uses ?? ''), values, isObject(step.arguments) ? step.arguments : {{}}, String(operation.id ?? ''));
    storeStepResult(values, step.outputs ?? [], result);
  }}
  return values;
}}

function executeTypescriptDomainOperation(operationId, values) {{
  const target = resolve(String(values.target ?? '.'));
  if (operationId === 'planning.front-door') return {{ kind: 'agentic-workspace/planning-help/v1', command: values._command_path?.join(' ') ?? operationId, target }};
  if (operationId === 'memory.front-door') return {{ kind: 'agentic-workspace/memory-help/v1', command: values._command_path?.join(' ') ?? operationId, target }};
  if (operationId === 'modules.report') return {{ kind: 'agentic-workspace/modules-router/v1', profile: 'tiny', target_root: target, detail_commands: {{ full: 'agentic-workspace modules --target . --verbose --format json' }} }};
  if (operationId === 'summary.report') return {{ kind: 'planning-summary/v1', profile: values.verbose ? 'full' : 'tiny', machine_first_planning: {{ status: 'no-active-execplan' }}, target_root: target }};
  if (operationId === 'start.context') return {{ kind: 'startup-context/v1', target_root: target, drill_down: {{ rule: 'Use --select <field[,field...]> for exact fields; use --verbose only for broad diagnostics.' }}, context: {{ proof: {{ kind: 'proof-selection/v1' }} }} }};
  if (operationId === 'implement.context') return {{ kind: 'implementer-context-tiny/v1', target_root: target, proof: {{ kind: 'proof-selection/v1' }} }};
  if (operationId === 'proof.report') return {{ kind: 'proof-next-decision/v1', next: {{ action: 'run-validation-command' }}, detail_command: 'agentic-workspace proof --verbose --changed <paths> --format json' }};
  if (operationId === 'setup.guidance') return {{ kind: 'workspace-setup/v1', command: 'setup', target_root: target }};
  if (operationId === 'ownership.report') return {{ profile: 'compact-contract-answer/v1', surface: 'ownership', matched: false, target_root: target }};
  if (operationId === 'skills.report') return {{ task: values.task ?? '', target_root: target, skills: [] }};
  if (operationId === 'report.combined') return {{ kind: 'workspace-report-router/v1', command: 'report', target_root: target }};
  if (operationId === 'reconcile.report') return {{ kind: 'planning-reconcile/v1', status: 'clean', target_root: target }};
  if (operationId === 'preflight.report') return {{ kind: 'preflight-response/v1', mode: values.active_only ? 'active-state-only' : 'full', target_root: target }};
  if (['install.lifecycle', 'init.lifecycle', 'upgrade.lifecycle', 'uninstall.lifecycle'].includes(operationId)) return workspaceLifecycle(values, operationId.split('.')[0]);
  if (operationId === 'status.report') return {{ command: 'status', health: 'attention-needed', target_root: target }};
  if (operationId === 'doctor.report') return {{ command: 'doctor', health: 'attention-needed', repair_plan: {{ kind: 'workspace-repair-plan/v1' }}, target_root: target }};
  return {{ command: values._command_path?.join(' ') ?? operationId, target_root: target, dry_run: Boolean(values.dry_run), message: operationId }};
}}

export function runGeneratedOperation({{ operationId, operationPath, values }}) {{
  if (!operationId) throw new RuntimeError('generated command has no operation id');
  if (values.strict_preflight === true && !values.preflight_token) {{
    writeSync(2, 'Strict preflight gate is enabled. Provide --preflight-token to continue.\\n');
    return 2;
  }}
  let output;
  if (!operationPath) throw new RuntimeError(`operation ${{operationId}} has no operation resource path`);
  const resourcePath = resolveInside(resourcesRoot, operationPath);
  if (!existsSync(resourcePath)) throw new RuntimeError(`operation resource is missing: ${{operationPath}}`);
  const operation = loadJsonResource(operationPath);
  const steps = operation?.ir_plan?.steps;
  if (!Array.isArray(steps) || steps.length === 0) throw new RuntimeError(`operation ${{operationId}} has no executable ir_plan.steps`);
  const finalValues = runSteps(operation, {{ ...values }});
  output = finalValues.emitted ?? emitOutput({{ ...finalValues, result: finalValues.result }});
  if (typeof output !== 'string') output = `${{JSON.stringify(output, null, 2)}}\\n`;
  writeSync(1, output);
  return 0;
}}
"""


def _typescript_cli_module(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity_levels: dict[str, dict[str, Any]],
    runtime_binding: dict[str, Any],
    *,
    repo_root: Path,
    source_path: str,
    regenerate_command: str,
) -> str:
    command_names = sorted(command["command"]["name"] for command in package["commands"])
    rendered_commands = json.dumps(command_names)
    rendered_interfaces = json.dumps(_typescript_interface_payload(package), indent=2, sort_keys=True)
    native_operation_ids = sorted(_typescript_native_operation_ids(package))
    rendered_native_operation_ids = json.dumps(native_operation_ids)
    weak_agent_status = _weak_agent_routing_for_target(target, maturity_levels)
    recovery_command = f"{target['entrypoints'][0]} --help"
    boundary_summary = "TypeScript CLI boundary: generated parser, validation, and command execution are Node/TypeScript only."
    native_helpers = _typescript_native_runtime_helpers(recovery_command=recovery_command)
    return (
        "#!/usr/bin/env node\n"
        "// Generated runnable adapter.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        "import { writeSync } from 'node:fs';\n"
        "import { runGeneratedOperation } from './runtime.mjs';\n\n"
        f"const supportedCommands = new Set({rendered_commands});\n"
        f"const nativeOperationIds = new Set({rendered_native_operation_ids});\n"
        f"const commandDefinitions = {rendered_interfaces};\n"
        "const commandByName = new Map(commandDefinitions.map((definition) => [definition.name, definition.interface]));\n"
        "const commandDefinitionByName = new Map(commandDefinitions.map((definition) => [definition.name, definition]));\n"
        "const argv = process.argv.slice(2);\n"
        "const command = argv[0];\n\n"
        "function optionFlags(option) {\n"
        "  return Array.isArray(option.flags) ? option.flags : [];\n"
        "}\n\n"
        "function interfaceOptions(iface) {\n"
        "  return Array.isArray(iface.options) ? iface.options : [];\n"
        "}\n\n"
        "function interfaceArguments(iface) {\n"
        "  return Array.isArray(iface.arguments) ? iface.arguments : [];\n"
        "}\n\n"
        "function interfaceSubcommands(iface) {\n"
        "  return Array.isArray(iface.subcommands) ? iface.subcommands : [];\n"
        "}\n\n"
        "function isHelpToken(token) {\n"
        "  return token === '--help' || token === '-h';\n"
        "}\n\n"
        "function printRootHelp() {\n"
        f"  console.log(`Usage: {target['entrypoints'][0]} <command> [options]`);\n"
        "  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);\n"
        f"  console.log('Weak-agent routing: {weak_agent_status}');\n"
        f"  console.log({boundary_summary!r});\n"
        "  console.log('Recovery: use a supported generated command or inspect the generated command contract.');\n"
        "}\n\n"
        "function printInterfaceHelp(path, iface) {\n"
        "  const argumentNames = interfaceArguments(iface).map((argument) => argument.nargs === '?' ? `[${argument.name}]` : `<${argument.name}>`);\n"
        "  const hasSubcommands = interfaceSubcommands(iface).length > 0;\n"
        "  const subcommandSuffix = hasSubcommands ? ' <subcommand>' : '';\n"
        "  const argumentSuffix = argumentNames.length ? ` ${argumentNames.join(' ')}` : '';\n"
        "  console.log(`Usage: ${path.join(' ')}${subcommandSuffix} [options]${argumentSuffix}`);\n"
        "  if (iface.help) console.log(String(iface.help));\n"
        "  const options = interfaceOptions(iface);\n"
        "  if (options.length) {\n"
        "    console.log('Options:');\n"
        "    for (const option of options) {\n"
        "      const choices = Array.isArray(option.choices) ? ` choices=${option.choices.join('|')}` : '';\n"
        "      const required = option.required === true ? ' required' : '';\n"
        "      console.log(`  ${optionFlags(option).join(', ')}${required}${choices}  ${option.help ?? ''}`);\n"
        "    }\n"
        "  }\n"
        "  const subcommands = interfaceSubcommands(iface);\n"
        "  if (subcommands.length) {\n"
        "    console.log('Subcommands:');\n"
        "    for (const subcommand of subcommands) {\n"
        "      console.log(`  ${subcommand.name}  ${subcommand.help ?? ''}`);\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        "function failValidation(message) {\n"
        "  console.error(`TypeScript CLI validation failed: ${message}`);\n"
        f"  console.error('Recovery: run {recovery_command} and choose a supported generated command or valid option.');\n"
        "  process.exit(2);\n"
        "}\n\n"
        "function validateChoice(spec, value, label) {\n"
        "  if (Array.isArray(spec.choices) && !spec.choices.includes(value)) {\n"
        "    failValidation(`${label} must be one of: ${spec.choices.join(', ')}`);\n"
        "  }\n"
        "  if (spec.type === 'integer' && !/^-?\\d+$/.test(value)) {\n"
        "    failValidation(`${label} must be an integer`);\n"
        "  }\n"
        "}\n\n"
        "function optionByFlag(iface, flag) {\n"
        "  return interfaceOptions(iface).find((option) => optionFlags(option).includes(flag));\n"
        "}\n\n"
        "function consumeOption(iface, option, tokens, index, seenOptions) {\n"
        "  const optionName = option.name ?? optionFlags(option)[0];\n"
        "  if (optionName) seenOptions.add(optionName);\n"
        "  if (option.action === 'store_true') return index + 1;\n"
        "  if (option.nargs === '*') {\n"
        "    let cursor = index + 1;\n"
        "    while (cursor < tokens.length && !String(tokens[cursor]).startsWith('-')) {\n"
        "      validateChoice(option, String(tokens[cursor]), optionFlags(option)[0]);\n"
        "      cursor += 1;\n"
        "    }\n"
        "    return cursor;\n"
        "  }\n"
        "  if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) {\n"
        "    failValidation(`${optionFlags(option)[0]} requires a value`);\n"
        "  }\n"
        "  const value = String(tokens[index + 1]);\n"
        "  validateChoice(option, value, optionFlags(option)[0]);\n"
        "  return index + 2;\n"
        "}\n\n"
        "function validateInterface(iface, tokens, path) {\n"
        "  const seenOptions = new Set();\n"
        "  const positional = [];\n"
        "  let index = 0;\n"
        "  while (index < tokens.length) {\n"
        "    const token = String(tokens[index]);\n"
        "    if (isHelpToken(token)) {\n"
        "      printInterfaceHelp(path, iface);\n"
        "      process.exit(0);\n"
        "    }\n"
        "    if (token.startsWith('-')) {\n"
        "      const option = optionByFlag(iface, token);\n"
        "      if (!option) failValidation(`unknown option ${token} for ${path.join(' ')}`);\n"
        "      index = consumeOption(iface, option, tokens, index, seenOptions);\n"
        "      continue;\n"
        "    }\n"
        "    const subcommand = interfaceSubcommands(iface).find((candidate) => candidate.name === token);\n"
        "    if (subcommand) {\n"
        "      validateInterface(subcommand, tokens.slice(index + 1), [...path, token]);\n"
        "      return;\n"
        "    }\n"
        "    positional.push(token);\n"
        "    index += 1;\n"
        "  }\n"
        "  for (const option of interfaceOptions(iface)) {\n"
        "    const optionName = option.name ?? optionFlags(option)[0];\n"
        "    if (option.required === true && optionName && !seenOptions.has(optionName)) {\n"
        "      failValidation(`missing required option ${optionFlags(option)[0]} for ${path.join(' ')}`);\n"
        "    }\n"
        "  }\n"
        "  const positionalSpecs = interfaceArguments(iface);\n"
        "  const requiredPositionals = positionalSpecs.filter((argument) => argument.nargs !== '?' && argument.default === undefined);\n"
        "  if (positional.length < requiredPositionals.length) {\n"
        "    failValidation(`missing required argument for ${path.join(' ')}`);\n"
        "  }\n"
        "  if (positional.length > positionalSpecs.length) {\n"
        "    failValidation(`unexpected argument ${positional[positionalSpecs.length]} for ${path.join(' ')}`);\n"
        "  }\n"
        "  positional.forEach((value, position) => validateChoice(positionalSpecs[position] ?? {}, value, positionalSpecs[position]?.name ?? 'argument'));\n"
        "  if (interfaceSubcommands(iface).length && iface.subcommands_required !== false && positional.length === 0) {\n"
        "    failValidation(`missing subcommand for ${path.join(' ')}`);\n"
        "  }\n"
        "}\n\n"
        f"{native_helpers}"
        "if (!command || command === '--help' || command === '-h') {\n"
        "  printRootHelp();\n"
        "  process.exit(0);\n"
        "}\n\n"
        "if (!supportedCommands.has(command)) {\n"
        "  console.error(`Unsupported generated command: ${command}`);\n"
        f"  console.error('Recovery: run {recovery_command} and choose one of the supported generated commands.');\n"
        "  process.exit(2);\n"
        "}\n\n"
        "validateInterface(commandByName.get(command), argv.slice(1), [command]);\n\n"
        "maybeRunNativeOperation();\n"
    )


def _typescript_mock_runtime() -> str:
    return "const payload = {\n  command: process.argv[2],\n  args: process.argv.slice(2),\n};\nconsole.log(JSON.stringify(payload));\n"


def _typescript_required_option_case(package: dict[str, Any]) -> dict[str, Any] | None:
    def find_required(interface: dict[str, Any], path: list[str]) -> dict[str, Any] | None:
        for option in interface.get("options", []):
            if isinstance(option, dict) and option.get("required") is True:
                flags = option.get("flags", [])
                if isinstance(flags, list) and flags:
                    return {"path": path, "flag": str(flags[0])}
        for subcommand in interface.get("subcommands", []):
            if isinstance(subcommand, dict) and subcommand.get("name"):
                found = find_required(subcommand, [*path, str(subcommand["name"])])
                if found is not None:
                    return found
        return None

    for command in package["commands"]:
        found = find_required(command["interface"], [str(command["command"]["name"])])
        if found is not None:
            return found
    return None


def _typescript_test(package: dict[str, Any], target: dict[str, Any]) -> str:
    expected_commands = sorted(command["command"]["name"] for command in package["commands"])
    rendered_expected = json.dumps(expected_commands)
    sample_command = expected_commands[0]
    sample_command_record = next(command for command in package["commands"] if command["command"]["name"] == sample_command)
    sample_options = sample_command_record.get("interface", {}).get("options", [])
    sample_supports_dry_run = any(isinstance(option, dict) and option.get("name") == "dry_run" for option in sample_options)
    sample_json_args = [sample_command, "--format", "json"]
    sample_spaced_args = [sample_command, "--target", "__SPACED_TARGET__"]
    if sample_supports_dry_run:
        sample_json_args.insert(1, "--dry-run")
        sample_spaced_args.insert(1, "--dry-run")
    native_operation_ids = _typescript_native_operation_ids(package)
    native_command = next(
        (
            str(command["command"]["name"])
            for command in package["commands"]
            if str(command.get("operation_ref", {}).get("id", "")) in native_operation_ids
        ),
        None,
    )
    required_case = _typescript_required_option_case(package)
    runnable = _is_runnable_typescript_target(target)
    expected_maturity = target["maturity_level_ref"]
    expected_generation_status = target["generation_status"]
    if target.get("maturity_level_ref") == "weak-agent-safe-adapter":
        expected_weak_agent_routing = "allowed-read-only"
    elif target.get("maturity_level_ref") == "mutation-capable-adapter":
        expected_weak_agent_routing = "allowed-mutation-with-review"
    else:
        expected_weak_agent_routing = "review-required"
    boundary_help_assertions = (
        "  assert.match(result.stdout, /Node\\/TypeScript only/);\n"
        "  assert.doesNotMatch(result.stdout, /Python runtime handoff/);\n"
    )
    imports = "import assert from 'node:assert/strict';\nimport test from 'node:test';\n"
    if runnable:
        imports += "import { spawnSync } from 'node:child_process';\nimport { fileURLToPath } from 'node:url';\n"
    imports += "import { mkdirSync, readFileSync, rmSync } from 'node:fs';\n"
    body = imports + (
        "\n"
        "const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');\n"
        "const commandPackage = JSON.parse(readFileSync(new URL('../resources/command_package.json', import.meta.url), 'utf8'));\n"
        "const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));\n"
        "\n"
        "test('generated package resource exposes expected commands', () => {\n"
        f"  const expected = {rendered_expected};\n"
        "  assert.deepEqual(commandPackage.commands.map((command) => command.command.name).sort(), expected);\n"
        "  assert.match(source, /resources\\/command_package\\.json/);\n"
        "  assert.doesNotMatch(source, /adapter_id/);\n"
        "  assert.deepEqual(packageJson.files, ['src', 'resources']);\n"
        "});\n"
        "\n"
        "test('generated package metadata exposes maturity and weak-agent routing status', () => {\n"
        "  const metadata = packageJson.agenticWorkspace;\n"
        f"  assert.equal(metadata.generationStatus, {expected_generation_status!r});\n"
        f"  assert.equal(metadata.maturity.id, {expected_maturity!r});\n"
        "  assert.equal(typeof metadata.maturity.summary, 'string');\n"
        "  assert.ok(metadata.maturity.summary.length > 0);\n"
        "  assert.ok(Array.isArray(metadata.maturity.promotion_requires));\n"
        "  assert.ok(metadata.maturity.promotion_requires.length > 0);\n"
    )
    if runnable:
        body += (
            "  assert.equal(metadata.fixtureOnly, false);\n"
            "  assert.equal(metadata.maturity.runnable, true);\n"
            f"  assert.equal(metadata.maturity.weak_agent_routing, {expected_weak_agent_routing!r});\n"
            "  assert.ok(packageJson.bin);\n"
        )
    else:
        body += (
            "  assert.equal(metadata.fixtureOnly, true);\n"
            "  assert.equal(metadata.maturity.runnable, false);\n"
            "  assert.equal(metadata.maturity.weak_agent_routing, 'forbidden');\n"
            "  assert.equal(packageJson.bin, undefined);\n"
        )
    body += "});\n"
    if runnable:
        body += (
            "\n"
            "test('generated runnable adapter executes supported command without Python runtime', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            f"  const result = spawnSync(process.execPath, [cli, ...{json.dumps(sample_json_args)}], {{ encoding: 'utf8' }});\n"
            "  assert.equal(result.status, 0);\n"
            "  const payload = JSON.parse(result.stdout);\n"
            "  assert.equal(typeof payload, 'object');\n"
            "  assert.equal(result.stderr, '');\n"
            "});\n"
            "\n"
            "test('generated runnable adapter preserves spaced argv values during native execution', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const spacedTarget = fileURLToPath(new URL('../tmp target with spaces', import.meta.url));\n"
            "  mkdirSync(spacedTarget, { recursive: true });\n"
            "  try {\n"
            f"    const args = {json.dumps(sample_spaced_args)}.map((token) => token === '__SPACED_TARGET__' ? spacedTarget : token);\n"
            "    const result = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8' });\n"
            "    assert.equal(result.status, 0);\n"
            "    assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
            "  } finally {\n"
            "    rmSync(spacedTarget, { recursive: true, force: true });\n"
            "  }\n"
            "});\n"
            "\n"
            "test('generated runnable adapter exposes routing status and recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const result = spawnSync(process.execPath, [cli, '--help'], { encoding: 'utf8' });\n"
            "  assert.equal(result.status, 0);\n"
            "  assert.match(result.stdout, /Supported generated commands:/);\n"
            f"  assert.match(result.stdout, /Weak-agent routing: {expected_weak_agent_routing}/);\n"
            f"{boundary_help_assertions}"
            "  assert.match(result.stdout, /Recovery:/);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter renders command help without executing runtime', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            f"  const result = spawnSync(process.execPath, [cli, {sample_command!r}, '--help'], {{\n"
            "    encoding: 'utf8',\n"
            "  });\n"
            "  assert.equal(result.status, 0);\n"
            "  assert.match(result.stdout, /Usage:/);\n"
            "  assert.match(result.stdout, /Options:/);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter validates choices before command execution', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            f"  const result = spawnSync(process.execPath, [cli, {sample_command!r}, '--format', '__invalid__'], {{\n"
            "    encoding: 'utf8',\n"
            "  });\n"
            "  assert.equal(result.status, 2);\n"
            "  assert.equal(result.stdout, '');\n"
            "  assert.match(result.stderr, /TypeScript CLI validation failed:/);\n"
            "  assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
            "});\n"
        )
        if required_case is not None:
            body += (
                "\n"
                "test('generated runnable adapter validates required options before command execution', () => {\n"
                "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
                f"  const result = spawnSync(process.execPath, [cli, ...{json.dumps(required_case['path'])}], {{\n"
                "    encoding: 'utf8',\n"
                "  });\n"
                "  assert.equal(result.status, 2);\n"
                "  assert.equal(result.stdout, '');\n"
                f"  assert.match(result.stderr, /missing required option {required_case['flag']}/);\n"
                "  assert.doesNotMatch(result.stderr, /runtime handoff/i);\n"
                "});\n"
            )
        body += (
            "\n"
            "test('generated runnable adapter rejects unsupported commands with recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const result = spawnSync(process.execPath, [cli, '__unsupported__'], { encoding: 'utf8' });\n"
            "  assert.equal(result.status, 2);\n"
            "  assert.equal(result.stdout, '');\n"
            "  assert.match(result.stderr, /Unsupported generated command: __unsupported__/);\n"
            "  assert.match(result.stderr, /Recovery:/);\n"
            "});\n"
        )
    return body


def render_outputs(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    source_path: str,
    regenerate_command: str,
) -> list[GeneratedOutput]:
    outputs: list[GeneratedOutput] = []
    maturity_levels = _maturity_levels(manifest)
    runtime_binding = manifest["generation_policy"]["non_python_runtime_binding"]
    for package in manifest["packages"]:
        for target in package["targets"]:
            root = repo_root / str(target["generated_root"])
            if target["kind"] == "python":
                module_path = root / "cli.py"
                outputs.append(GeneratedOutput(root / "__init__.py", "from .cli import *  # noqa: F403\n"))
                outputs.append(GeneratedOutput(root / "command_package.json", _json_block(package) + "\n"))
                if _is_runtime_backed_python_target(target):
                    outputs.extend(_runtime_consumed_operation_outputs(package, repo_root=repo_root, root=root))
                    outputs.extend(_python_resource_copy_outputs(package, repo_root=repo_root, root=root))
                    operation_executor = _operation_executor_binding(package)
                    if operation_executor:
                        executor_module_path = Path(str(operation_executor.get("module_file", "operation_executor")).replace(".", "/"))
                        outputs.append(
                            GeneratedOutput(
                                root / executor_module_path.with_suffix(".py"),
                                _python_operation_executor_module(
                                    package,
                                    operation_executor,
                                    source_path=source_path,
                                    regenerate_command=regenerate_command,
                                ),
                            )
                        )
                    python_runtime_binding = package.get("python_runtime_binding", {})
                    if python_runtime_binding.get("render_runtime_module") is True and operation_executor:
                        outputs.extend(
                            _python_command_module_outputs(
                                package,
                                python_runtime_binding,
                                root=root,
                                source_path=source_path,
                                regenerate_command=regenerate_command,
                            )
                        )
                        outputs.append(
                            GeneratedOutput(
                                root / "primitives" / "__init__.py",
                                _python_primitives_module(source_path=source_path, regenerate_command=regenerate_command),
                            )
                        )
                        outputs.append(
                            GeneratedOutput(
                                root / "primitives" / "primitive_executor.py",
                                _python_primitive_executor_module(source_path=source_path, regenerate_command=regenerate_command),
                            )
                        )
                        outputs.append(
                            GeneratedOutput(
                                root / "primitives" / "resources.py",
                                _python_resource_primitives_module(
                                    source_path=source_path,
                                    regenerate_command=regenerate_command,
                                ),
                            )
                        )
                        for local_runtime_binding in _local_runtime_bindings(package):
                            if not _local_runtime_binding_functions(package, local_runtime_binding):
                                continue
                            local_runtime_module_path = Path(str(local_runtime_binding["module_file"]).replace(".", "/"))
                            outputs.append(
                                GeneratedOutput(
                                    root / local_runtime_module_path.with_suffix(".py"),
                                    _python_local_runtime_binding_module(
                                        package,
                                        local_runtime_binding,
                                        source_path=source_path,
                                        regenerate_command=regenerate_command,
                                    ),
                                )
                            )
                    outputs.append(
                        GeneratedOutput(
                            root / "adapter_commands.json",
                            _json_block(_python_adapter_command_payload(package)) + "\n",
                        )
                    )
                    outputs.append(
                        GeneratedOutput(
                            module_path,
                            _python_runtime_adapter_module(
                                package,
                                target,
                                maturity_levels,
                                source_path=source_path,
                                regenerate_command=regenerate_command,
                            ),
                        )
                    )
                    continue
                outputs.append(
                    GeneratedOutput(module_path, _python_module(package, source_path=source_path, regenerate_command=regenerate_command))
                )
            elif target["kind"] == "typescript":
                outputs.append(
                    GeneratedOutput(
                        root / "package.json",
                        _typescript_package_json(
                            package, target, maturity_levels[target["maturity_level_ref"]], runtime_binding, source_path=source_path
                        ),
                    )
                )
                outputs.append(
                    GeneratedOutput(
                        root / "src" / "commandPackage.ts",
                        _typescript_module(package, source_path=source_path, regenerate_command=regenerate_command),
                    )
                )
                outputs.append(GeneratedOutput(root / "resources" / "command_package.json", _json_block(package) + "\n"))
                outputs.extend(_typescript_resource_copy_outputs(package, repo_root=repo_root, root=root))
                outputs.append(GeneratedOutput(root / "test" / "command-package.test.mjs", _typescript_test(package, target)))
                if _is_runnable_typescript_target(target):
                    outputs.append(
                        GeneratedOutput(
                            root / "src" / "runtime.mjs",
                            _typescript_runtime_module(source_path=source_path, regenerate_command=regenerate_command),
                        )
                    )
                    outputs.append(
                        GeneratedOutput(
                            root / "src" / "cli.mjs",
                            _typescript_cli_module(
                                package,
                                target,
                                maturity_levels,
                                runtime_binding,
                                repo_root=repo_root,
                                source_path=source_path,
                                regenerate_command=regenerate_command,
                            ),
                        )
                    )
    return outputs


def generate_command_packages(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    source_path: str,
    regenerate_command: str,
    check: bool,
) -> list[str]:
    stale_outputs: list[str] = []
    for output in render_outputs(manifest, repo_root=repo_root, source_path=source_path, regenerate_command=regenerate_command):
        if check:
            current = _read_generated_text(output.path) if output.path.exists() else ""
            if current != output.content:
                stale_outputs.append(output.path.relative_to(repo_root).as_posix())
        else:
            output.path.parent.mkdir(parents=True, exist_ok=True)
            output.path.write_text(output.content, encoding="utf-8", newline="\n")
            print(f"[ok] wrote {output.path.relative_to(repo_root).as_posix()}")
    return stale_outputs


def _read_generated_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()
