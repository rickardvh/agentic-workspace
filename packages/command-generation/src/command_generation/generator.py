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
    entrypoint = str(package.get("python_runtime_binding", {}).get("entrypoint") or package.get("program") or "")
    if entrypoint:
        snippet = (
            "import sys; "
            "from command_generation.console import main_for_entrypoint; "
            f"raise SystemExit(main_for_entrypoint({entrypoint!r}, sys.argv[1:]))"
        )
        return "python -c " + json.dumps(snippet)
    return str(runtime_binding["default_runtime_command"])


def _runtime_module_file_for_package(package: dict[str, Any]) -> str:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return ""
    configured = str(binding.get("runtime_module_file") or "")
    return configured.removesuffix(".py")


def _operation_executor_binding(package: dict[str, Any]) -> dict[str, Any]:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return {}
    operation_executor = binding.get("operation_executor", {})
    return operation_executor if isinstance(operation_executor, dict) else {}


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
    operation_executor = _operation_executor_binding(package)
    direct_handlers = {
        str(handler["operation_id"]): handler for handler in binding.get("runtime_module_handlers", []) if isinstance(handler, dict)
    }
    if operation_id in direct_handlers:
        handler = direct_handlers[operation_id]
        import_module = str(handler["import_module"])
        imported_function = str(handler.get("function") or _runtime_adapter_function_name(operation_id))
        run_body = f"    from {import_module} import {imported_function}\n\n    return {imported_function}(args)\n"
    else:
        run_body = f"    return run_operation_ir(generated_operation_contract({operation_id!r}), args)\n"
    executor_module = str(operation_executor.get("module_file", "operation_executor"))
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
        "from ..cli import generated_operation_contract\n"
        f"from ..{executor_module} import run_operation_ir\n\n\n"
        "def run(args: argparse.Namespace) -> int:\n" + run_body
    )


def _is_memory_list_skills_direct_projection(package: dict[str, Any], operation_id: str) -> bool:
    return package.get("id") == "memory-bootstrap" and operation_id == "memory.list-skills.report"


def _python_memory_list_skills_command_module(
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
        "import argparse\n"
        "import json\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command behavior changes belong in {source_path} and the referenced operation contract.\n"
        f"# Regenerate with: {regenerate_command}\n\n\n"
        "def _skills_root() -> Path:\n"
        "    for parent in Path(__file__).resolve().parents:\n"
        "        for candidate in (parent / '_skills', parent / 'packages' / 'memory' / 'skills'):\n"
        "            if (candidate / 'REGISTRY.json').is_file():\n"
        "                return candidate\n"
        "    raise FileNotFoundError('Bundled memory skill registry is not available.')\n\n\n"
        "def _read_json_resource(root: Path, relative_path: str) -> dict[str, Any]:\n"
        "    payload = json.loads((root / relative_path).read_text(encoding='utf-8'))\n"
        "    if not isinstance(payload, dict):\n"
        "        raise RuntimeError(f'{relative_path} must parse to an object')\n"
        "    return payload\n\n\n"
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
        "    skills_root = _skills_root()\n"
        "    registry = _read_json_resource(skills_root, 'REGISTRY.json')\n"
        "    payload = _assemble_payload(registry, skills_root)\n"
        "    _emit_output(payload, str(getattr(args, 'format', 'text') or 'text'))\n"
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
        "# Primitive implementations belong to command_generation. This module makes the target-local boundary explicit.\n"
        f"# Regenerate with: {regenerate_command}\n\n"
        "from command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps\n\n"
        "__all__ = [\n"
        '    "PrimitiveContext",\n'
        '    "PrimitiveExecutionError",\n'
        '    "execute_primitive",\n'
        '    "run_operation_steps",\n'
        "]\n"
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


def _render_function_call_handler(function_name: str, handler: dict[str, Any]) -> str:
    imported_name = str(handler["function"])
    kwargs = _render_value_kwargs(handler.get("kwargs", {}))
    return (
        f"def {function_name}(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:\n"
        f"    from {handler['import_module']} import {imported_name}\n\n"
        f"    return {imported_name}({kwargs})\n"
    )


def _render_conditional_function_call_handler(function_name: str, handler: dict[str, Any]) -> str:
    condition_value = str(handler["condition_value"])
    true_handler = handler["if_true"]
    false_handler = handler["if_false"]
    true_name = str(true_handler["function"])
    false_name = str(false_handler["function"])
    true_kwargs = _render_value_kwargs(true_handler.get("kwargs", {}))
    false_kwargs = _render_value_kwargs(false_handler.get("kwargs", {}))
    return (
        f"def {function_name}(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:\n"
        f"    if values.get({condition_value!r}):\n"
        f"        from {true_handler['import_module']} import {true_name}\n\n"
        f"        return {true_name}({true_kwargs})\n"
        f"    from {false_handler['import_module']} import {false_name}\n\n"
        f"    return {false_name}({false_kwargs})\n"
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


def _render_runtime_handler(function_name: str, handler: dict[str, Any], *, runtime_module_file: str) -> str:
    runtime_function = str(handler["function"])
    import_module = str(handler.get("import_module") or "")
    if import_module:
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


def _render_context_root_function(root: dict[str, Any]) -> str:
    function_name = _handler_function_name(f"context.root.{root['name']}")
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
            handlers.append(_render_runtime_handler(function_name, handler, runtime_module_file=runtime_module_file))
        elif handler_kind == "function_call":
            handlers.append(_render_function_call_handler(function_name, handler))
        elif handler_kind == "conditional_function_call":
            handlers.append(_render_conditional_function_call_handler(function_name, handler))
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
        "from command_generation.primitive_executor import (\n"
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
        "        run_operation_steps(\n"
        "            operation,\n"
        "            initial_values={\n"
        '                "operation_id": operation.get("id"),\n' + "\n".join(initial_values) + "\n"
        "            },\n"
        f"            context=PrimitiveContext(cwd=Path.cwd(), roots={{{roots_block}}}),\n"
        "            handlers={\n" + "\n".join(handler_items) + "\n"
        "            },\n"
        "        )\n"
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
        "class GeneratedArgumentParser(argparse.ArgumentParser):\n"
        "    def error(self, message: str) -> None:\n"
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
        "def build_generated_parser() -> argparse.ArgumentParser:\n"
        "    epilog = (\n"
        '        f"Weak-agent routing: {_GENERATED_WEAK_AGENT_ROUTING}\\n"\n'
        '        "Recovery: use one of the supported generated commands or route back to the canonical Python CLI."\n'
        "    )\n"
        f"    parser = GeneratedArgumentParser(prog={json.dumps(package['program'])}, description={json.dumps(package.get('summary', ''))}, epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)\n"
        f"    parser.add_argument('--version', action='version', version='%(prog)s 0.0.0-generated')\n"
        '    subparsers = parser.add_subparsers(dest="command", required=True)\n'
        "    for command in _GENERATED_ADAPTER_COMMANDS:\n"
        '        interface = command["interface"]\n'
        '        _add_interface_command(subparsers, interface, str(command["operation_id"]))\n'
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
    runtime_command = _runtime_command_for_package(package, runtime_binding)
    payload = {
        "name": target["package_name"],
        "version": "0.0.0-generated",
        "private": True,
        "type": "module",
        "bin": {entrypoint: "./src/cli.mjs" for entrypoint in target["entrypoints"]} if _is_runnable_typescript_target(target) else {},
        "scripts": {"test": "node --test test/command-package.test.mjs"},
        "agenticWorkspace": {
            "generated": True,
            "fixtureOnly": not _is_runnable_typescript_target(target),
            "generationStatus": target["generation_status"],
            "maturity": maturity,
            "runtimeBinding": runtime_binding,
            "effectiveRuntimeCommand": runtime_command,
            "source": source_path,
            "program": package["program"],
            "declaredEntrypoints": target["entrypoints"],
        },
    }
    if not payload["bin"]:
        del payload["bin"]
    return _json_block(payload) + "\n"


def _typescript_module(package: dict[str, Any], *, source_path: str, regenerate_command: str) -> str:
    rendered = _json_block(package)
    return (
        "// Generated command package metadata.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        f"export const generatedCommandPackage = {rendered} as const;\n"
        "\n"
        "export type GeneratedCommandPackage = typeof generatedCommandPackage;\n"
    )


def _typescript_cli_module(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity_levels: dict[str, dict[str, Any]],
    runtime_binding: dict[str, Any],
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    command_names = sorted(command["command"]["name"] for command in package["commands"])
    rendered_commands = json.dumps(command_names)
    default_runtime_command = json.dumps(_runtime_command_for_package(package, runtime_binding))
    weak_agent_status = _weak_agent_routing_for_target(target, maturity_levels)
    recovery_command = f"{target['entrypoints'][0]} --help"
    return (
        "#!/usr/bin/env node\n"
        "// Generated runnable adapter.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        "import { spawnSync } from 'node:child_process';\n"
        "import { writeSync } from 'node:fs';\n\n"
        f"const supportedCommands = new Set({rendered_commands});\n"
        "const argv = process.argv.slice(2);\n"
        "const command = argv[0];\n\n"
        "if (!command || command === '--help' || command === '-h') {\n"
        f"  console.log(`Usage: {target['entrypoints'][0]} <command> [options]`);\n"
        "  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);\n"
        f"  console.log('Weak-agent routing: {weak_agent_status}');\n"
        "  console.log('Recovery: use a supported generated command or route back to the canonical Python CLI.');\n"
        "  process.exit(0);\n"
        "}\n\n"
        "if (!supportedCommands.has(command)) {\n"
        "  console.error(`Unsupported generated command: ${command}`);\n"
        f"  console.error('Recovery: run {recovery_command} and choose one of the supported generated commands.');\n"
        "  process.exit(2);\n"
        "}\n\n"
        f"const runtimeCommand = process.env.AGENTIC_WORKSPACE_RUNTIME ?? {default_runtime_command};\n"
        "\n"
        "function splitRuntimeCommand(commandLine) {\n"
        "  const parts = [];\n"
        "  let current = '';\n"
        "  let quote = null;\n"
        "  for (const char of commandLine.trim()) {\n"
        "    if (quote) {\n"
        "      if (char === quote) quote = null;\n"
        "      else current += char;\n"
        "    } else if (char === '\"' || char === \"'\") {\n"
        "      quote = char;\n"
        "    } else if (/\\s/.test(char)) {\n"
        "      if (current) {\n"
        "        parts.push(current);\n"
        "        current = '';\n"
        "      }\n"
        "    } else {\n"
        "      current += char;\n"
        "    }\n"
        "  }\n"
        "  if (quote) throw new Error('runtime command has an unterminated quote');\n"
        "  if (current) parts.push(current);\n"
        "  if (parts.length === 0) throw new Error('runtime command is empty');\n"
        "  return parts;\n"
        "}\n"
        "\n"
        "let result;\n"
        "try {\n"
        "  const [runtimeExecutable, ...runtimeArgs] = splitRuntimeCommand(runtimeCommand);\n"
        "  result = spawnSync(runtimeExecutable, [...runtimeArgs, ...argv], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });\n"
        "} catch (error) {\n"
        "  console.error(`Adapter runtime handoff failed: ${error.message}`);\n"
        "  console.error('Recovery: verify AGENTIC_WORKSPACE_RUNTIME or run the canonical Python CLI directly.');\n"
        "  process.exit(1);\n"
        "}\n"
        "if (result.error) {\n"
        "  console.error(`Adapter runtime handoff failed: ${result.error.message}`);\n"
        "  console.error('Recovery: verify AGENTIC_WORKSPACE_RUNTIME or run the canonical Python CLI directly.');\n"
        "  process.exit(1);\n"
        "}\n"
        "if (result.stdout) writeSync(1, result.stdout);\n"
        "if (result.stderr) writeSync(2, result.stderr);\n"
        "process.exit(result.status ?? 1);\n"
    )


def _typescript_mock_runtime() -> str:
    return "const payload = {\n  command: process.argv[2],\n  args: process.argv.slice(2),\n};\nconsole.log(JSON.stringify(payload));\n"


def _typescript_test(package: dict[str, Any], target: dict[str, Any]) -> str:
    expected_commands = sorted(command["command"]["name"] for command in package["commands"])
    rendered_expected = json.dumps(expected_commands)
    sample_command = expected_commands[0]
    runnable = _is_runnable_typescript_target(target)
    expected_maturity = target["maturity_level_ref"]
    expected_generation_status = target["generation_status"]
    if target.get("maturity_level_ref") == "weak-agent-safe-adapter":
        expected_weak_agent_routing = "allowed-read-only"
    elif target.get("maturity_level_ref") == "mutation-capable-adapter":
        expected_weak_agent_routing = "allowed-mutation-with-review"
    else:
        expected_weak_agent_routing = "review-required"
    imports = "import assert from 'node:assert/strict';\nimport test from 'node:test';\n"
    if runnable:
        imports += "import { spawnSync } from 'node:child_process';\nimport { fileURLToPath } from 'node:url';\n"
    imports += "import { readFileSync } from 'node:fs';\n"
    body = imports + (
        "\n"
        "const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');\n"
        "const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));\n"
        "\n"
        "test('generated package metadata exposes expected commands', () => {\n"
        f"  const expected = {rendered_expected};\n"
        "  for (const command of expected) {\n"
        '    assert.match(source, new RegExp(`\\"name\\": \\\\"${command}\\\\"`));\n'
        "  }\n"
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
            "test('generated runnable adapter delegates supported command to runtime process', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const mockRuntime = fileURLToPath(new URL('./mock-runtime.mjs', import.meta.url));\n"
            '  const runtime = `"${process.execPath}" "${mockRuntime}"`;\n'
            f"  const result = spawnSync(process.execPath, [cli, {sample_command!r}, '--format', 'json'], {{\n"
            "    encoding: 'utf8',\n"
            "    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: runtime },\n"
            "  });\n"
            "  assert.equal(result.status, 0);\n"
            "  const payload = JSON.parse(result.stdout);\n"
            f"  assert.equal(payload.command, {sample_command!r});\n"
            f"  assert.deepEqual(payload.args, [{sample_command!r}, '--format', 'json']);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter preserves spaced argv values during runtime handoff', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const mockRuntime = fileURLToPath(new URL('./mock-runtime.mjs', import.meta.url));\n"
            '  const runtime = `"${process.execPath}" "${mockRuntime}"`;\n'
            f"  const result = spawnSync(process.execPath, [cli, {sample_command!r}, '--task', 'value with spaces'], {{\n"
            "    encoding: 'utf8',\n"
            "    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: runtime },\n"
            "  });\n"
            "  assert.equal(result.status, 0);\n"
            "  const payload = JSON.parse(result.stdout);\n"
            f"  assert.deepEqual(payload.args, [{sample_command!r}, '--task', 'value with spaces']);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter exposes routing status and recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const result = spawnSync(process.execPath, [cli, '--help'], { encoding: 'utf8' });\n"
            "  assert.equal(result.status, 0);\n"
            "  assert.match(result.stdout, /Supported generated commands:/);\n"
            f"  assert.match(result.stdout, /Weak-agent routing: {expected_weak_agent_routing}/);\n"
            "  assert.match(result.stdout, /Recovery:/);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter rejects unsupported commands with recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const result = spawnSync(process.execPath, [cli, '__unsupported__'], { encoding: 'utf8' });\n"
            "  assert.equal(result.status, 2);\n"
            "  assert.equal(result.stdout, '');\n"
            "  assert.match(result.stderr, /Unsupported generated command: __unsupported__/);\n"
            "  assert.match(result.stderr, /Recovery:/);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter maps runtime handoff failure with recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            f"  const result = spawnSync(process.execPath, [cli, {sample_command!r}], {{\n"
            "    encoding: 'utf8',\n"
            "    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: '' },\n"
            "  });\n"
            "  assert.equal(result.status, 1);\n"
            "  assert.match(result.stderr, /Adapter runtime handoff failed:/);\n"
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
                outputs.append(GeneratedOutput(root / "test" / "command-package.test.mjs", _typescript_test(package, target)))
                if _is_runnable_typescript_target(target):
                    outputs.append(
                        GeneratedOutput(
                            root / "src" / "cli.mjs",
                            _typescript_cli_module(
                                package,
                                target,
                                maturity_levels,
                                runtime_binding,
                                source_path=source_path,
                                regenerate_command=regenerate_command,
                            ),
                        )
                    )
                    outputs.append(GeneratedOutput(root / "test" / "mock-runtime.mjs", _typescript_mock_runtime()))
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
