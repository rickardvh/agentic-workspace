from __future__ import annotations

import importlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class PrimitiveExecutionError(RuntimeError):
    pass


PrimitiveHandler = Callable[[dict[str, Any], dict[str, Any], "PrimitiveContext"], Any]


@dataclass(frozen=True)
class PrimitiveContext:
    cwd: Path
    roots: dict[str, Path] = field(default_factory=dict)

    def root(self, name: str) -> Path:
        try:
            return self.roots[name].resolve()
        except KeyError as exc:
            raise PrimitiveExecutionError(f"unknown primitive root: {name!r}") from exc


def run_operation_steps(
    operation: dict[str, Any],
    *,
    initial_values: dict[str, Any],
    context: PrimitiveContext,
    handlers: Mapping[str, PrimitiveHandler] | None = None,
) -> dict[str, Any]:
    """Execute an operation ir_plan with codegen-owned primitive dataflow."""
    values = dict(initial_values)
    custom_handlers = dict(handlers or {})
    steps = operation.get("ir_plan", {}).get("steps", [])
    if not isinstance(steps, list):
        raise PrimitiveExecutionError("operation ir_plan.steps must be a list")
    for raw_step in steps:
        if not isinstance(raw_step, dict):
            raise PrimitiveExecutionError("operation ir_plan step must be an object")
        primitive = str(raw_step.get("uses", ""))
        arguments = raw_step.get("arguments", {})
        if not isinstance(arguments, dict):
            raise PrimitiveExecutionError(f"step {raw_step.get('id', primitive)!r} arguments must be an object")
        handler = custom_handlers.get(primitive)
        result = (
            handler(values, arguments, context)
            if handler is not None
            else execute_primitive(primitive, values=values, arguments=arguments, context=context)
        )
        _store_step_result(values=values, outputs=raw_step.get("outputs", []), result=result)
    return values


def execute_primitive(
    primitive: str,
    *,
    values: dict[str, Any],
    arguments: dict[str, Any] | None = None,
    context: PrimitiveContext,
) -> Any:
    arguments = arguments or {}
    if primitive == "path.target_root.resolve":
        return _resolve_target_root(values=values, context=context)
    if primitive == "filesystem.read":
        return _read_text(arguments=arguments, context=context)
    if primitive == "filesystem.glob":
        return _glob(arguments=arguments, context=context)
    if primitive == "json.parse":
        return _parse_json(values=values, arguments=arguments)
    if primitive == "payload.assemble":
        return _assemble_payload(values=values, arguments=arguments)
    if primitive == "output.emit":
        return _emit_output(values=values)
    if primitive == "python.function.call":
        return _call_python_function(values=values, arguments=arguments)
    raise PrimitiveExecutionError(f"unsupported portable primitive: {primitive!r}")


def _store_step_result(*, values: dict[str, Any], outputs: Any, result: Any) -> None:
    if result is None:
        return
    if isinstance(outputs, Sequence) and not isinstance(outputs, (str, bytes)):
        output_names = [str(output) for output in outputs if str(output)]
    else:
        output_names = []
    if not output_names:
        values["_last"] = result
        return
    if len(output_names) == 1:
        values[output_names[0]] = result
        return
    if not isinstance(result, Mapping):
        raise PrimitiveExecutionError("multi-output primitive results must be mappings")
    for output_name in output_names:
        if output_name not in result:
            raise PrimitiveExecutionError(f"primitive result missing declared output: {output_name!r}")
        values[output_name] = result[output_name]


def _resolve_target_root(*, values: dict[str, Any], context: PrimitiveContext) -> str:
    target = values.get("target") or "."
    return str((context.cwd / str(target)).resolve())


def _read_text(*, arguments: dict[str, Any], context: PrimitiveContext) -> str:
    root = context.root(str(arguments.get("root", "")))
    path = _resolve_inside(root, str(arguments.get("path", "")))
    if not path.is_file():
        raise PrimitiveExecutionError(f"filesystem.read path is not a file: {path}")
    return path.read_text(encoding="utf-8")


def _glob(*, arguments: dict[str, Any], context: PrimitiveContext) -> list[dict[str, str]]:
    root = context.root(str(arguments.get("root", "")))
    pattern = str(arguments.get("pattern", ""))
    if not pattern or Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        raise PrimitiveExecutionError(f"unsupported filesystem.glob pattern: {pattern!r}")
    matches = []
    for path in root.glob(pattern):
        resolved = path.resolve()
        _ensure_inside(root, resolved)
        if resolved.is_file():
            matches.append({"relative_path": resolved.relative_to(root).as_posix()})
    return sorted(matches, key=lambda item: item["relative_path"])


def _parse_json(*, values: dict[str, Any], arguments: dict[str, Any]) -> Any:
    source_name = str(arguments.get("source") or "registry_text")
    try:
        text = values[source_name]
    except KeyError as exc:
        raise PrimitiveExecutionError(f"json.parse missing source value: {source_name!r}") from exc
    return json.loads(str(text))


def _assemble_payload(*, values: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    fields = arguments.get("fields", {})
    if not isinstance(fields, dict):
        raise PrimitiveExecutionError("payload.assemble fields must be an object")
    actions_from = str(fields.get("actions_from", ""))
    payload: dict[str, Any] = {
        "dry_run": bool(fields.get("dry_run", True)),
        "message": str(fields.get("message", "")),
    }
    target_root = values.get("target_root")
    if target_root is not None:
        payload["target_root"] = str(target_root)
    if actions_from == "files":
        payload["actions"] = [
            {"kind": "file", "path": str(item.get("relative_path", ""))}
            for item in _list_of_objects(values.get("files", []), source="files")
        ]
        return payload
    if actions_from == "registry.skills":
        registry = values.get("registry", {})
        if not isinstance(registry, dict):
            raise PrimitiveExecutionError("registry.skills payload source must be an object")
        payload["mode"] = str(fields.get("mode", "skills"))
        payload["actions"] = [
            {"kind": "skill", "id": str(item.get("id", "")), "path": str(item.get("path", ""))}
            for item in _list_of_objects(registry.get("skills", []), source="registry.skills")
        ]
        return payload
    raise PrimitiveExecutionError(f"unsupported payload.assemble actions_from: {actions_from!r}")


def _emit_output(*, values: dict[str, Any]) -> str:
    result = values.get("result")
    output_format = str(values.get("format") or "text")
    if output_format == "json":
        return json.dumps(result, indent=2, sort_keys=True) + "\n"
    if not isinstance(result, dict):
        return f"{result}\n"
    lines = [str(result.get("message", ""))]
    for action in _list_of_objects(result.get("actions", []), source="result.actions"):
        label = action.get("path") or action.get("id") or action.get("kind")
        lines.append(f"- {label}")
    return "\n".join(lines).rstrip() + "\n"


def _call_python_function(*, values: dict[str, Any], arguments: dict[str, Any]) -> Any:
    import_module = str(arguments.get("import_module", "")).strip()
    function_name = str(arguments.get("function", "")).strip()
    if not import_module or not function_name:
        raise PrimitiveExecutionError("python.function.call requires import_module and function")
    try:
        function = getattr(importlib.import_module(import_module), function_name)
    except (ImportError, AttributeError) as exc:
        raise PrimitiveExecutionError(f"python.function.call cannot resolve {import_module}.{function_name}") from exc
    kwargs = _resolve_call_kwargs(values=values, raw_kwargs=arguments.get("kwargs", {}))
    return function(**kwargs)


def _resolve_call_kwargs(*, values: dict[str, Any], raw_kwargs: Any) -> dict[str, Any]:
    if not isinstance(raw_kwargs, dict):
        raise PrimitiveExecutionError("python.function.call kwargs must be an object")
    kwargs: dict[str, Any] = {}
    for name, source in raw_kwargs.items():
        if not isinstance(source, dict):
            kwargs[str(name)] = source
            continue
        if "value" in source:
            value_name = str(source["value"])
            if value_name not in values:
                raise PrimitiveExecutionError(f"python.function.call cannot resolve value {value_name!r}")
            kwargs[str(name)] = values[value_name]
        elif "literal" in source:
            kwargs[str(name)] = source["literal"]
        else:
            raise PrimitiveExecutionError(f"python.function.call kwarg {name!r} must declare value or literal")
    return kwargs


def _resolve_inside(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    _ensure_inside(root, candidate)
    return candidate


def _ensure_inside(root: Path, candidate: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PrimitiveExecutionError(f"path escapes primitive root: {candidate}") from exc


def _list_of_objects(value: Any, *, source: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise PrimitiveExecutionError(f"{source} must be a list of objects")
    return value
