"""Generated target-local primitive executor implementation.

Source: src/agentic_workspace/contracts/command_package_ir.json
Host primitive support: src/agentic_workspace/contracts/python_primitive_support.py
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

# DO NOT EDIT DIRECTLY.
# Portable primitive dispatch and executor structure belong to command-generation.
# Host primitive behavior belongs in the configured support module.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from __future__ import annotations

import importlib
import json
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from .operation_composition import expand_operation_steps, operation_fragments


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


def execute_host_primitive(
    primitive: str,
    *,
    values: dict[str, Any],
    arguments: dict[str, Any],
    context: PrimitiveContext,
) -> Any:
    raise PrimitiveExecutionError(f"unsupported host primitive: {primitive!r}")


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
    fragments = operation_fragments(operation, error_type=PrimitiveExecutionError)
    for raw_step in expand_operation_steps(
        steps, fragments=fragments, error_type=PrimitiveExecutionError
    ):
        primitive = str(raw_step.get("uses", ""))
        arguments = raw_step.get("arguments", {})
        if not isinstance(arguments, dict):
            raise PrimitiveExecutionError(
                f"step {raw_step.get('id', primitive)!r} arguments must be an object"
            )
        if not _condition_matches(raw_step.get("when"), values=values):
            continue
        handler = custom_handlers.get(primitive)
        result = (
            handler(values, arguments, context)
            if handler is not None
            else execute_primitive(
                primitive, values=values, arguments=arguments, context=context
            )
        )
        _store_step_result(
            values=values, outputs=raw_step.get("outputs", []), result=result
        )
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
        return _resolve_target_root(values=values, arguments=arguments, context=context)
    if primitive == "filesystem.exists":
        return _exists(arguments=arguments, context=context, values=values)
    if primitive == "filesystem.read":
        return _read_text(arguments=arguments, context=context)
    if primitive == "filesystem.glob":
        return _glob(arguments=arguments, context=context, values=values)
    if primitive == "json.parse":
        return _parse_json(values=values, arguments=arguments)
    if primitive == "toml.table.counts":
        return _toml_table_counts(values=values, arguments=arguments, context=context)
    if primitive == "payload.assemble":
        return _assemble_payload(values=values, arguments=arguments)
    if primitive == "output.emit":
        return _emit_output(values=values, arguments=arguments)
    if primitive == "python.function.call":
        return _call_python_function(values=values, arguments=arguments)
    return execute_host_primitive(
        primitive, values=values, arguments=arguments, context=context
    )


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
            raise PrimitiveExecutionError(
                f"primitive result missing declared output: {output_name!r}"
            )
        values[output_name] = result[output_name]


def _condition_matches(condition: Any, *, values: dict[str, Any]) -> bool:
    if condition in (None, {}, []):
        return True
    if not isinstance(condition, dict):
        raise PrimitiveExecutionError("step when condition must be an object")
    keys = set(condition)
    if keys == {"all"}:
        items = condition["all"]
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            raise PrimitiveExecutionError("step when all condition must be a sequence")
        return all(_condition_matches(item, values=values) for item in items)
    if keys == {"any"}:
        items = condition["any"]
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            raise PrimitiveExecutionError("step when any condition must be a sequence")
        return any(_condition_matches(item, values=values) for item in items)
    if keys == {"not"}:
        return not _condition_matches(condition["not"], values=values)
    if keys not in ({"value", "equals"}, {"value", "present"}):
        raise PrimitiveExecutionError(
            "step when condition must use exactly one of all, any, not, equals, or present"
        )
    value_name = str(condition.get("value", ""))
    if not value_name:
        raise PrimitiveExecutionError("step when condition must declare a value name")
    actual = values.get(value_name)
    if "equals" in condition:
        return actual == condition["equals"]
    return (actual is not None) == bool(condition["present"])


def _resolve_target_root(
    *, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext
) -> str:
    target = values.get("target") or "."
    target_root = (context.cwd / str(target)).resolve()
    if bool(arguments.get("must_exist", False)) and not target_root.exists():
        raise PrimitiveExecutionError(f"target root does not exist: {target_root}")
    if bool(arguments.get("must_be_dir", False)) and not target_root.is_dir():
        raise PrimitiveExecutionError(f"target root is not a directory: {target_root}")
    return str(target_root)


def _read_text(*, arguments: dict[str, Any], context: PrimitiveContext) -> str:
    root = context.root(str(arguments.get("root", "")))
    path = _resolve_inside(root, str(arguments.get("path", "")))
    if not path.is_file():
        raise PrimitiveExecutionError(f"filesystem.read path is not a file: {path}")
    return path.read_text(encoding="utf-8")


def _glob(
    *, arguments: dict[str, Any], context: PrimitiveContext, values: dict[str, Any]
) -> list[dict[str, str]]:
    root = _primitive_root(arguments=arguments, context=context, values=values)
    pattern = str(arguments.get("pattern", ""))
    if not pattern or Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        raise PrimitiveExecutionError(
            f"unsupported filesystem.glob pattern: {pattern!r}"
        )
    matches = []
    for path in root.glob(pattern):
        resolved = path.resolve()
        _ensure_inside(root, resolved)
        if resolved.is_file():
            matches.append({"relative_path": resolved.relative_to(root).as_posix()})
    return sorted(matches, key=lambda item: item["relative_path"])


def _exists(
    *, arguments: dict[str, Any], context: PrimitiveContext, values: dict[str, Any]
) -> bool:
    root = _primitive_root(arguments=arguments, context=context, values=values)
    path = _resolve_inside(root, str(arguments.get("path", "")))
    if str(arguments.get("kind", "any")) == "file":
        return path.is_file()
    if str(arguments.get("kind", "any")) == "directory":
        return path.is_dir()
    return path.exists()


def _parse_json(*, values: dict[str, Any], arguments: dict[str, Any]) -> Any:
    source_name = str(arguments.get("source") or "registry_text")
    try:
        text = values[source_name]
    except KeyError as exc:
        raise PrimitiveExecutionError(
            f"json.parse missing source value: {source_name!r}"
        ) from exc
    return json.loads(str(text))


def _toml_table_counts(
    *, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext
) -> dict[str, Any]:
    root = _primitive_root(arguments=arguments, context=context, values=values)
    relative_path = str(arguments.get("path", ""))
    path = _resolve_inside(root, relative_path)
    table_name = str(arguments.get("table", ""))
    relevance_field = str(arguments.get("relevance_field", ""))
    required_value = str(arguments.get("required_value", "required")).strip().lower()
    optional_value = str(arguments.get("optional_value", "optional")).strip().lower()
    routing_only_field = str(arguments.get("routing_only_field", "routing_only"))
    counts = {
        "status": "missing",
        "note_count": 0,
        "required_count": 0,
        "optional_count": 0,
        "routing_only_count": 0,
        "path": relative_path,
    }
    if not path.exists():
        return {
            "table_counts": counts,
            "table_present": False,
            "table_status": counts["status"],
        }
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        counts["status"] = "invalid"
        return {
            "table_counts": counts,
            "table_present": False,
            "table_status": counts["status"],
        }
    records = payload.get(table_name, {}) if isinstance(payload, dict) else {}
    record_values = list(records.values()) if isinstance(records, dict) else []
    counts["status"] = "present"
    counts["note_count"] = len(record_values)
    for record in record_values:
        if not isinstance(record, dict):
            continue
        record_payload = cast(Mapping[str, Any], record)
        relevance = str(record_payload.get(relevance_field, "")).strip().lower()
        if relevance == required_value:
            counts["required_count"] += 1
        elif relevance == optional_value:
            counts["optional_count"] += 1
        if bool(record_payload.get(routing_only_field, False)):
            counts["routing_only_count"] += 1
    return {
        "table_counts": counts,
        "table_present": True,
        "table_status": counts["status"],
    }


def _assemble_payload(
    *, values: dict[str, Any], arguments: dict[str, Any]
) -> dict[str, Any]:
    fields = arguments.get("fields", {})
    if not isinstance(fields, dict):
        raise PrimitiveExecutionError("payload.assemble fields must be an object")
    if "template" in fields:
        return _resolve_template(fields["template"], values=values)
    if fields.get("payload_kind") == "package-file-list":
        return _assemble_package_file_list(values=values, fields=fields)
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
            raise PrimitiveExecutionError(
                "registry.skills payload source must be an object"
            )
        payload["mode"] = str(fields.get("mode", "skills"))
        payload["bootstrap_version"] = _resolve_dotted_value(
            registry, str(fields.get("bootstrap_version_from", ""))
        )
        payload["actions"] = []
        for item in _list_of_objects(
            registry.get("skills", []), source="registry.skills"
        ):
            skill_id = str(item.get("id", "")).strip()
            path = str(item.get("path", "")).strip()
            if not skill_id or not path:
                continue
            payload["actions"].append(
                {
                    "kind": "bundled skill",
                    "path": str(Path(path).parent).replace("\\", "/"),
                    "detail": "registered packaged product skill",
                    "role": "skill",
                    "safety": "safe",
                    "source": skill_id,
                    "category": "safe-update",
                    "remediation_kind": "",
                    "remediation_target": "",
                    "remediation_reason": "",
                    "remediation_confidence": "",
                    "memory_action": "",
                    "match_source": "",
                }
            )
        return payload
    raise PrimitiveExecutionError(
        f"unsupported payload.assemble actions_from: {actions_from!r}"
    )


def _assemble_package_file_list(
    *, values: dict[str, Any], fields: Mapping[str, Any]
) -> dict[str, Any]:
    files_from = str(fields.get("files_from", "files"))
    bundled_skills_from = str(
        fields.get("bundled_skill_files_from", "bundled_skill_files")
    )
    return {
        "files": _relative_path_list(values.get(files_from, []), source=files_from),
        "default_files": _string_list(
            fields.get("default_files", []),
            source="payload.assemble fields.default_files",
        ),
        "optional_files": _string_list(
            fields.get("optional_files", []),
            source="payload.assemble fields.optional_files",
        ),
        "bundled_skill_files": _relative_path_list(
            values.get(bundled_skills_from, []), source=bundled_skills_from
        ),
        "optional_enable_commands": _string_list(
            fields.get("optional_enable_commands", []),
            source="payload.assemble fields.optional_enable_commands",
        ),
    }


def _string_list(value: Any, *, source: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PrimitiveExecutionError(f"{source} must be a list of strings")
    return value


def _relative_path_list(value: Any, *, source: str) -> list[str]:
    if not isinstance(value, list):
        raise PrimitiveExecutionError(f"{source} must be a list")
    paths: list[str] = []
    for item in value:
        if isinstance(item, str):
            paths.append(item)
            continue
        if isinstance(item, Mapping):
            relative_path = item.get("relative_path")
            if isinstance(relative_path, str):
                paths.append(relative_path)
                continue
        raise PrimitiveExecutionError(
            f"{source} entries must be strings or objects with relative_path"
        )
    return paths


def _resolve_template(template: Any, *, values: dict[str, Any]) -> Any:
    if isinstance(template, list):
        return [_resolve_template(item, values=values) for item in template]
    if not isinstance(template, dict):
        return template
    if set(template) == {"$value"}:
        return values.get(str(template["$value"]))
    if "$field" in template:
        spec = template["$field"]
        if not isinstance(spec, dict):
            raise PrimitiveExecutionError("template $field must be an object")
        value_name = str(spec.get("value", ""))
        path = spec.get("path", [])
        if isinstance(path, str):
            path_parts = [part for part in path.split(".") if part]
        elif isinstance(path, Sequence) and not isinstance(path, (str, bytes)):
            path_parts = [str(part) for part in path]
        else:
            raise PrimitiveExecutionError(
                "template $field path must be a string or sequence"
            )
        value: Any = values.get(value_name)
        for part in path_parts:
            if not isinstance(value, Mapping) or part not in value:
                raise PrimitiveExecutionError(
                    f"template $field cannot resolve {value_name!r}.{'.'.join(path_parts)}"
                )
            value = value[part]
        return value
    if set(template) == {"$count"}:
        counted = values.get(str(template["$count"]), [])
        if not isinstance(counted, Sequence) or isinstance(counted, (str, bytes)):
            raise PrimitiveExecutionError(
                f"template count source must be a sequence: {template['$count']!r}"
            )
        return len(counted)
    if "$exists_status" in template:
        spec = template["$exists_status"]
        if not isinstance(spec, dict):
            raise PrimitiveExecutionError("template $exists_status must be an object")
        value = bool(values.get(str(spec.get("value", ""))))
        return (
            spec.get("present", "present") if value else spec.get("missing", "missing")
        )
    if "$count_status" in template:
        spec = template["$count_status"]
        if not isinstance(spec, dict):
            raise PrimitiveExecutionError("template $count_status must be an object")
        counted = values.get(str(spec.get("value", "")), [])
        if not isinstance(counted, Sequence) or isinstance(counted, (str, bytes)):
            raise PrimitiveExecutionError(
                f"template count source must be a sequence: {spec.get('value')!r}"
            )
        return (
            spec.get("present", "present")
            if len(counted)
            else spec.get("missing", "missing")
        )
    if "$join_path" in template:
        spec = template["$join_path"]
        if not isinstance(spec, dict):
            raise PrimitiveExecutionError("template $join_path must be an object")
        base = Path(str(values.get(str(spec.get("base", "")), "")))
        return (base / str(spec.get("path", ""))).as_posix()
    return {
        str(key): _resolve_template(value, values=values)
        for key, value in template.items()
    }


def _emit_output(
    *, values: dict[str, Any], arguments: dict[str, Any] | None = None
) -> str:
    arguments = arguments or {}
    result = _plain_output_result(values.get("result"))
    output_format = str(values.get("format") or "text")
    if output_format == "json":
        return json.dumps(result, indent=2, sort_keys=True) + "\n"
    if str(arguments.get("text_style", "")) == "current-memory" and isinstance(
        result, dict
    ):
        return _emit_current_memory_text(result)
    if str(arguments.get("text_style", "")) == "install-result" and isinstance(
        result, dict
    ):
        return _emit_install_result_text(result)
    if isinstance(result, dict) and isinstance(
        result.get("route_report_summary"), dict
    ):
        return _emit_route_report_text(result)
    if isinstance(result, dict) and result.get("kind") == "memory-module-report/v1":
        return _emit_memory_report_text(result)
    if (
        isinstance(result, dict)
        and result.get("kind") == "planning-module-report/v1"
        and result.get("profile") == "tiny"
    ):
        return _emit_planning_module_report_text(result)
    if not isinstance(result, dict):
        return f"{result}\n"
    if isinstance(result.get("files"), list) and all(
        isinstance(item, str) for item in result["files"]
    ):
        return "\n".join(result["files"]).rstrip() + "\n"
    lines = [str(result.get("message", ""))]
    for action in _list_of_objects(result.get("actions", []), source="result.actions"):
        label = action.get("path") or action.get("id") or action.get("kind")
        lines.append(f"- {label}")
    return "\n".join(lines).rstrip() + "\n"


def _plain_output_result(result: Any) -> Any:
    if isinstance(result, Mapping):
        return dict(result)
    to_dict = getattr(result, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return result


def _emit_install_result_text(result: dict[str, Any]) -> str:
    target_root = Path(str(result.get("target_root", ""))).resolve()
    lines = [
        f"Target: {target_root}",
        str(result.get("message", "")),
        f"Detected version: {result.get('detected_version') or 'none'} (payload version {result.get('bootstrap_version')})",
    ]
    for action in _list_of_objects(result.get("actions", []), source="result.actions"):
        raw_path = str(action.get("path", ""))
        action_path = Path(raw_path)
        try:
            label = action_path.relative_to(target_root)
        except ValueError:
            label = action_path
        details = []
        for key, label_name in (
            ("detail", ""),
            ("role", "role"),
            ("safety", "safety"),
            ("category", "category"),
            ("remediation_kind", "remediation"),
            ("remediation_target", "target"),
            ("remediation_confidence", "confidence"),
            ("memory_action", "memory_action"),
            ("match_source", "match_source"),
        ):
            value = action.get(key)
            if value:
                details.append(
                    str(value) if not label_name else f"{label_name}={value}"
                )
        detail = f" ({'; '.join(details)})" if details else ""
        lines.append(f"- {action.get('kind')}: {label}{detail}")
    return "\n".join(lines).rstrip() + "\n"


def _emit_current_memory_text(result: dict[str, Any]) -> str:
    lines = [f"Target: {Path(str(result.get('target_root', ''))).resolve()}"]
    detected_version = result.get("detected_version")
    lines.append(
        f"Detected version: {detected_version if detected_version is not None else 'none'} (payload version {result.get('bootstrap_version')})"
    )
    for note in _list_of_objects(result.get("notes", []), source="result.notes"):
        lines.append("")
        lines.append(f"[{note.get('path', '')}]")
        if not bool(note.get("exists", False)):
            lines.append("(missing)")
            continue
        lines.append(str(note.get("content", "")).rstrip())
    return "\n".join(lines).rstrip() + "\n"


def _emit_route_report_text(result: dict[str, Any]) -> str:
    summary = result.get("route_report_summary", {})
    if not isinstance(summary, Mapping):
        return f"{result.get('message', 'Routing report')}\n"
    feedback = summary.get("feedback", {})
    fixtures = summary.get("fixtures", {})
    lines = [str(result.get("message", "Routing report"))]
    if isinstance(feedback, Mapping):
        lines.append(
            f"Feedback: {feedback.get('status', 'unknown')} ({feedback.get('path', '')})"
        )
    if isinstance(fixtures, Mapping):
        lines.append(
            f"Fixtures: {fixtures.get('status', 'unknown')} ({fixtures.get('fixture_count', 0)})"
        )
    detail = summary.get("detail") or result.get("detail_command")
    if detail:
        lines.append(str(detail))
    return "\n".join(lines).rstrip() + "\n"


def _emit_memory_report_text(result: dict[str, Any]) -> str:
    status = result.get("status", {})
    active = result.get("active", {})
    habitual_pull = result.get("habitual_pull", {})
    next_action = result.get("next_action", {})
    lines = [
        "Memory report",
        f"Target: {result.get('target_root', '')}",
        f"Health: {result.get('health', 'unknown')}",
    ]
    if isinstance(status, Mapping):
        lines.append(
            f"Notes: {status.get('note_count', 0)} ({status.get('manifest_status', 'unknown')})"
        )
    if isinstance(active, Mapping):
        lines.append(
            "Active: "
            f"required={active.get('required_count', 0)}, "
            f"optional={active.get('optional_count', 0)}, "
            f"routing-only={active.get('routing_only_count', 0)}"
        )
    if isinstance(habitual_pull, Mapping):
        lines.append(f"Habitual pull: {habitual_pull.get('status', 'unknown')}")
    if isinstance(next_action, Mapping):
        lines.append(f"Next: {next_action.get('summary', '')}")
    detail_commands = result.get("detail_commands", {})
    if isinstance(detail_commands, Mapping) and detail_commands.get("full"):
        lines.append(str(detail_commands["full"]))
    return "\n".join(lines).rstrip() + "\n"


def _emit_planning_module_report_text(result: dict[str, Any]) -> str:
    status = result.get("status", {})
    next_action = result.get("next_action", {})
    lines = [
        f"Target: {result.get('target_root')}",
        f"Command: {result.get('module', 'planning')}",
        f"Health: {result.get('health')}",
    ]
    if isinstance(status, Mapping):
        lines.append(
            "Status: "
            f"{status.get('active_todo_count', 0)} active TODO / "
            f"{status.get('queued_todo_count', 0)} queued TODO / "
            f"{status.get('active_execplan_count', 0)} active execplans / "
            f"{status.get('roadmap_lane_count', 0)} roadmap lanes / "
            f"{status.get('roadmap_candidate_count', 0)} roadmap candidates"
        )
    if isinstance(next_action, Mapping):
        lines.append(f"Next action: {next_action.get('summary', '')}")
    return "\n".join(lines).rstrip() + "\n"


def _call_python_function(*, values: dict[str, Any], arguments: dict[str, Any]) -> Any:
    import_module = str(arguments.get("import_module", "")).strip()
    function_name = str(arguments.get("function", "")).strip()
    if not import_module or not function_name:
        raise PrimitiveExecutionError(
            "python.function.call requires import_module and function"
        )
    try:
        function = getattr(importlib.import_module(import_module), function_name)
    except (ImportError, AttributeError) as exc:
        raise PrimitiveExecutionError(
            f"python.function.call cannot resolve {import_module}.{function_name}"
        ) from exc
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
                raise PrimitiveExecutionError(
                    f"python.function.call cannot resolve value {value_name!r}"
                )
            kwargs[str(name)] = values[value_name]
        elif "literal" in source:
            kwargs[str(name)] = source["literal"]
        else:
            raise PrimitiveExecutionError(
                f"python.function.call kwarg {name!r} must declare value or literal"
            )
    return kwargs


def _resolve_dotted_value(payload: Mapping[str, Any], dotted_path: str) -> Any:
    if not dotted_path:
        return None
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _resolve_inside(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    _ensure_inside(root, candidate)
    return candidate


def _primitive_root(
    *, arguments: dict[str, Any], context: PrimitiveContext, values: dict[str, Any]
) -> Path:
    if "base_value" in arguments:
        value_name = str(arguments["base_value"])
        if value_name not in values:
            raise PrimitiveExecutionError(
                f"unknown primitive base value: {value_name!r}"
            )
        return Path(str(values[value_name])).resolve()
    return context.root(str(arguments.get("root", "")))


def _ensure_inside(root: Path, candidate: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PrimitiveExecutionError(
            f"path escapes primitive root: {candidate}"
        ) from exc


def _list_of_objects(value: Any, *, source: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise PrimitiveExecutionError(f"{source} must be a list of objects")
    return value


from .host_primitive_support import execute_host_primitive as _execute_configured_host_primitive

execute_host_primitive = _execute_configured_host_primitive
