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
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path, PurePosixPath
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
    if primitive == "payload.view":
        return _view_payload(values=values, arguments=arguments)
    if primitive == "payload.project":
        return _project_payload(values=values, arguments=arguments)
    if primitive == "output.emit":
        return _emit_output(values=values, arguments=arguments)
    if primitive == "transaction.plan":
        return _transaction_plan(values=values, arguments=arguments)
    if primitive == "python.function.call":
        return _call_python_function(values=values, arguments=arguments)
    if primitive == "operation.call":
        return _call_operation(values=values, arguments=arguments)
    if primitive == "operation.dispatch":
        return _dispatch_operation(values=values, arguments=arguments)
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
    if fields.get("payload_kind") == "package-resource-manifest":
        return _assemble_package_resource_manifest(values=values, fields=fields)
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


def _assemble_package_resource_manifest(
    *, values: dict[str, Any], fields: Mapping[str, Any]
) -> dict[str, Any]:
    manifest_from = str(fields.get("manifest_from", "manifest"))
    manifest = values.get(manifest_from, {})
    if not isinstance(manifest, Mapping):
        raise PrimitiveExecutionError(f"{manifest_from} must be an object")
    files_path = str(fields.get("files_path", "files"))
    bundled_skills_path = str(
        fields.get("bundled_skill_files_path", "bundled_skill_files")
    )
    files = _resolve_dotted_value(manifest, files_path)
    bundled_skill_files = _resolve_dotted_value(manifest, bundled_skills_path)
    return {
        "files": _manifest_path_list(files or [], source=f"{manifest_from}.{files_path}"),
        "default_files": _string_list(
            fields.get("default_files", []),
            source="payload.assemble fields.default_files",
        ),
        "optional_files": _string_list(
            fields.get("optional_files", []),
            source="payload.assemble fields.optional_files",
        ),
        "bundled_skill_files": _manifest_path_list(
            bundled_skill_files or [],
            source=f"{manifest_from}.{bundled_skills_path}",
        ),
        "optional_enable_commands": _string_list(
            fields.get("optional_enable_commands", []),
            source="payload.assemble fields.optional_enable_commands",
        ),
    }


def _manifest_path_list(value: Any, *, source: str) -> list[str]:
    if not isinstance(value, list):
        raise PrimitiveExecutionError(f"{source} must be a list")
    paths: list[str] = []
    for item in value:
        if isinstance(item, str):
            paths.append(item)
            continue
        if isinstance(item, Mapping):
            raw_path = item.get("relative_path", item.get("path"))
            if isinstance(raw_path, str):
                paths.append(raw_path)
                continue
        raise PrimitiveExecutionError(
            f"{source} entries must be strings or objects with path"
        )
    return paths


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
    if "$select_by_value" in template:
        spec = template["$select_by_value"]
        if not isinstance(spec, dict):
            raise PrimitiveExecutionError("template $select_by_value must be an object")
        choices = spec.get("choices", {})
        if not isinstance(choices, Mapping):
            raise PrimitiveExecutionError(
                "template $select_by_value choices must be an object"
            )
        value_name = str(spec.get("value", ""))
        selected_value = values.get(value_name)
        selected_key = (
            _template_choice_key(selected_value)
            if value_name in values and selected_value is not None
            else _template_choice_key(spec.get("default", ""))
        )
        if selected_key not in choices:
            selected_key = _template_choice_key(spec.get("default", ""))
        if selected_key not in choices:
            raise PrimitiveExecutionError(
                f"template $select_by_value cannot resolve choice for {value_name!r}"
            )
        return _resolve_template(choices[selected_key], values=values)
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


def _template_choice_key(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _emit_output(
    *, values: dict[str, Any], arguments: dict[str, Any] | None = None
) -> str:
    arguments = arguments or {}
    result = _plain_output_result(values.get("result"))
    output_format = str(values.get("format") or "text")
    if output_format == "json":
        return json.dumps(result, indent=2, sort_keys=True) + "\n"
    if isinstance(result, dict):
        declared_view = _emit_declared_text_view(result, arguments.get("text_views", []))
        if declared_view is not None:
            return declared_view
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


def _emit_declared_text_view(result: dict[str, Any], views: Any) -> str | None:
    if views is None:
        return None
    if not isinstance(views, Sequence) or isinstance(views, (str, bytes, bytearray)):
        raise PrimitiveExecutionError("output.emit text_views must be a list")
    default_view: Mapping[str, Any] | None = None
    for view in views:
        if not isinstance(view, Mapping):
            raise PrimitiveExecutionError("output.emit text_views entries must be objects")
        if bool(view.get("default")):
            default_view = view
        if _declared_text_view_matches(result, view):
            return _render_declared_text_view(result, view)
    if default_view is not None:
        return _render_declared_text_view(result, default_view)
    return None


def _declared_text_view_matches(result: dict[str, Any], view: Mapping[str, Any]) -> bool:
    match = view.get("match", {})
    if not isinstance(match, Mapping) or not match:
        return False
    for path, expected in match.items():
        found, actual = _field_by_path(result, str(path))
        if not found or actual != expected:
            return False
    return True


def _render_declared_text_view(result: dict[str, Any], view: Mapping[str, Any]) -> str:
    rendered = _render_declared_text_lines(view.get("lines", []), current=result, root=result)
    return "\n".join(rendered).rstrip() + "\n"


def _render_declared_text_lines(lines: Any, *, current: Any, root: dict[str, Any]) -> list[str]:
    if not isinstance(lines, Sequence) or isinstance(lines, (str, bytes, bytearray)):
        raise PrimitiveExecutionError("output.emit text view lines must be a list")
    rendered: list[str] = []
    for line in lines:
        rendered.extend(_render_declared_text_line(line, current=current, root=root))
    return rendered


def _render_declared_text_line(line: Any, *, current: Any, root: dict[str, Any]) -> list[str]:
    if isinstance(line, str):
        return [_render_declared_text_template(line, current=current, root=root)]
    if not isinstance(line, Mapping):
        raise PrimitiveExecutionError("output.emit text view lines must be strings or objects")
    if "when" in line:
        found, value = _declared_text_value(line["when"], current=current, root=root)
        if not found or not _declared_text_truthy(value):
            return []
        return _render_declared_text_lines(line.get("lines", []), current=current, root=root)
    if "for_each" in line:
        spec = line["for_each"]
        if not isinstance(spec, Mapping):
            raise PrimitiveExecutionError("output.emit for_each line must be an object")
        found, value = _declared_text_value(spec.get("path", ""), current=current, root=root)
        if not found or value in (None, ""):
            return []
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise PrimitiveExecutionError("output.emit for_each path must resolve to a list")
        nested_lines = spec.get("lines")
        if nested_lines is None:
            nested_lines = [str(spec.get("template", "{}"))]
        return [
            nested
            for item in value
            for nested in _render_declared_text_lines(nested_lines, current=item, root=root)
        ]
    if "json" in line:
        found, value = _declared_text_value(line["json"], current=current, root=root)
        if not found:
            value = None
        return json.dumps(_plain_output_result(value), indent=2).splitlines()
    if "template" in line:
        return [_render_declared_text_template(str(line["template"]), current=current, root=root)]
    if "literal" in line:
        return [str(line["literal"])]
    raise PrimitiveExecutionError("output.emit text view line object must declare when, for_each, json, template, or literal")


def _render_declared_text_template(template: str, *, current: Any, root: dict[str, Any]) -> str:
    rendered = template
    for token in _declared_text_template_tokens(template):
        found, value = _declared_text_placeholder_value(token, current=current, root=root)
        rendered = rendered.replace("{" + token + "}", _declared_text_format(value if found else ""))
    return rendered


def _declared_text_template_tokens(template: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    while index < len(template):
        start = template.find("{", index)
        if start == -1:
            break
        end = template.find("}", start + 1)
        if end == -1:
            break
        tokens.append(template[start + 1 : end])
        index = end + 1
    return tokens


def _declared_text_placeholder_value(token: str, *, current: Any, root: dict[str, Any]) -> tuple[bool, Any]:
    parts = token.split("|")
    found, value = _declared_text_value(parts[0], current=current, root=root)
    for raw_filter in parts[1:]:
        name, _, argument = raw_filter.partition(":")
        if name == "len":
            value = len(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else 0
            found = True
        elif name == "join":
            separator = argument
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                value = separator.join(str(item) for item in value)
            found = True
        elif name == "empty":
            if not _declared_text_truthy(value):
                value = argument
                found = True
        else:
            raise PrimitiveExecutionError(f"unsupported output.emit text view filter: {name!r}")
    return found, value


def _declared_text_value(path: Any, *, current: Any, root: dict[str, Any]) -> tuple[bool, Any]:
    path_text = str(path or "")
    if path_text in {"", "."}:
        return True, current
    if path_text.startswith("root."):
        return _field_by_path(root, path_text.removeprefix("root."))
    if isinstance(current, Mapping):
        found, value = _field_by_path(current, path_text)
        if found:
            return True, value
    return _field_by_path(root, path_text)


def _declared_text_truthy(value: Any) -> bool:
    return bool(value)


def _declared_text_format(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return ""
    return str(value)


def _view_payload(*, values: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    source_name = str(arguments.get("source") or "result")
    if source_name not in values:
        raise PrimitiveExecutionError(f"payload.view source value is missing: {source_name!r}")
    fields = _string_list(arguments.get("fields", []), source="payload.view fields")
    limits = arguments.get("limits", {})
    if not isinstance(limits, Mapping):
        raise PrimitiveExecutionError("payload.view limits must be an object")
    payload = values[source_name]
    viewed: dict[str, Any] = {
        "kind": str(arguments.get("view_kind") or "command-generation/payload-view/v1"),
        "source_command": str(arguments.get("source_command") or values.get("operation_id") or ""),
        "values": {},
    }
    missing: list[str] = []
    for field_name in fields:
        found, value = _field_by_path(payload, field_name)
        if not found:
            missing.append(field_name)
            continue
        cast(dict[str, Any], viewed["values"])[field_name] = _limited_view_value(
            _plain_output_result(value), limit=limits.get(field_name)
        )
    if missing:
        viewed["missing"] = missing
    return viewed


def _limited_view_value(value: Any, *, limit: Any) -> Any:
    if not isinstance(limit, int) or isinstance(value, (str, bytes, bytearray)):
        return value
    if isinstance(value, Sequence):
        return list(value[: max(limit, 0)])
    return value


def _transaction_plan(*, values: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    resources_from = str(arguments.get("resources_from", "resources"))
    raw_resources = values.get(resources_from, arguments.get("resources", []))
    if not isinstance(raw_resources, list):
        raise PrimitiveExecutionError("transaction.plan resources must be a list")
    actions: list[dict[str, Any]] = []
    default_action = str(arguments.get("default_action", "write"))
    default_kind = str(arguments.get("default_kind", "file"))
    for item in raw_resources:
        if isinstance(item, str):
            actions.append(
                {
                    "action": default_action,
                    "kind": default_kind,
                    "path": _validate_resource_path(item),
                }
            )
            continue
        if not isinstance(item, Mapping):
            raise PrimitiveExecutionError(
                "transaction.plan resources must be strings or objects"
            )
        raw_path = item.get("path", item.get("relative_path"))
        if not isinstance(raw_path, str) or not raw_path:
            raise PrimitiveExecutionError("transaction.plan resource path is required")
        resource_path = _validate_resource_path(raw_path)
        actions.append(
            {
                "action": str(item.get("action", default_action)),
                "kind": str(item.get("kind", default_kind)),
                "path": resource_path,
            }
        )
    target_root_value = str(arguments.get("target_root_value", "target_root"))
    plan: dict[str, Any] = {
        "kind": str(arguments.get("plan_kind", "command-generation/transaction-plan/v1")),
        "dry_run": True,
        "target_root": str(values.get(target_root_value, "")),
        "schema_ref": str(arguments.get("schema_ref", "")),
        "actions": actions,
        "mutation_safety": {
            "apply_status": "package-owned",
            "apply_primitive": str(arguments.get("apply_primitive", "")),
            "conflict_hooks": _string_list(
                arguments.get("conflict_hooks", []),
                source="transaction.plan conflict_hooks",
            ),
            "provenance_hooks": _string_list(
                arguments.get("provenance_hooks", []),
                source="transaction.plan provenance_hooks",
            ),
            "rule": "Generic transaction planning is dry-run only; mutating apply remains an explicit package-domain primitive.",
        },
    }
    return plan


def _validate_resource_path(path: str) -> str:
    resource_path = path.replace("\\", "/")
    pure_path = PurePosixPath(resource_path)
    raw_parts = resource_path.split("/")
    if (
        not resource_path
        or pure_path.is_absolute()
        or ":" in raw_parts[0]
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise PrimitiveExecutionError(
            f"transaction.plan resource path must be relative and stay inside resources: {path!r}"
        )
    return resource_path


def _project_payload(*, values: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    source_name = str(arguments.get("source") or "result")
    source_command = str(arguments.get("source_command") or values.get("operation_id") or "")
    selected_output_kind = str(arguments.get("selected_output_kind") or "command-generation/selected-output/v1")
    if source_name not in values:
        raise PrimitiveExecutionError(f"payload.project source value is missing: {source_name!r}")
    payload = values[source_name]
    selectors = _projection_selectors(values=values, arguments=arguments)
    if not selectors:
        return _plain_output_result(payload)
    selected: dict[str, Any] = {
        "kind": selected_output_kind,
        "source_command": source_command,
        "values": {},
    }
    missing: list[str] = []
    projected_values = cast(dict[str, Any], selected["values"])
    for selector in selectors:
        found, value = _field_by_path(payload, selector)
        if found:
            projected_values[selector] = _plain_output_result(value)
        else:
            missing.append(selector)
    if missing:
        selected["missing"] = missing
        selected["selector_rule"] = "Comma-separated dot paths select exact JSON fields; unknown fields are reported in missing."
        selected["available_selectors"] = _available_selectors_for_payload(payload)
    return selected


def _projection_selectors(*, values: dict[str, Any], arguments: dict[str, Any]) -> list[str]:
    raw_selectors = arguments.get("selectors")
    if raw_selectors is None:
        select_value_name = str(arguments.get("select_value") or "select")
        raw_selectors = values.get(select_value_name)
    if isinstance(raw_selectors, Sequence) and not isinstance(raw_selectors, (str, bytes, bytearray)):
        return [str(item).strip() for item in raw_selectors if str(item).strip()]
    return [token.strip() for token in str(raw_selectors or "").split(",") if token.strip()]


def _plain_output_result(result: Any) -> Any:
    if isinstance(result, Path):
        return str(result)
    to_dict = getattr(result, "to_dict", None)
    if callable(to_dict):
        return _plain_output_result(to_dict())
    if is_dataclass(result) and not isinstance(result, type):
        return _plain_output_result(asdict(result))
    if isinstance(result, Mapping):
        return {str(key): _plain_output_result(value) for key, value in result.items()}
    if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
        return [_plain_output_result(value) for value in result]
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
    return _call_operation(values=values, arguments=arguments)


def _call_operation(*, values: dict[str, Any], arguments: dict[str, Any]) -> Any:
    import_module = str(arguments.get("import_module", "")).strip()
    function_name = str(arguments.get("function", "")).strip()
    if not import_module or not function_name:
        raise PrimitiveExecutionError(
            "operation.call requires import_module and function"
        )
    try:
        function = getattr(importlib.import_module(import_module), function_name)
    except (ImportError, AttributeError) as exc:
        raise PrimitiveExecutionError(
            f"operation.call cannot resolve {import_module}.{function_name}"
        ) from exc
    positional = _resolve_call_args(values=values, raw_args=arguments.get("args", []))
    kwargs = _resolve_call_kwargs(values=values, raw_kwargs=arguments.get("kwargs", {}))
    return function(*positional, **kwargs)


def _dispatch_operation(*, values: dict[str, Any], arguments: dict[str, Any]) -> Any:
    raw_branches = arguments.get("branches", [])
    if not isinstance(raw_branches, Sequence) or isinstance(raw_branches, (str, bytes)):
        raise PrimitiveExecutionError("operation.dispatch branches must be a sequence")
    if not raw_branches:
        raise PrimitiveExecutionError("operation.dispatch requires at least one branch")
    for index, raw_branch in enumerate(raw_branches):
        if not isinstance(raw_branch, Mapping):
            raise PrimitiveExecutionError("operation.dispatch branch must be an object")
        branch = dict(raw_branch)
        if not _condition_matches(branch.get("when"), values=values):
            continue
        branch.pop("when", None)
        return _call_operation(values=values, arguments=branch)
    raise PrimitiveExecutionError("operation.dispatch no branch matched")


def _resolve_call_args(*, values: dict[str, Any], raw_args: Any) -> list[Any]:
    if not isinstance(raw_args, Sequence) or isinstance(raw_args, (str, bytes)):
        raise PrimitiveExecutionError("operation.call args must be a sequence")
    return [
        _resolve_call_argument(values=values, source=source, label=f"arg {index}")
        for index, source in enumerate(raw_args)
    ]


def _resolve_call_kwargs(*, values: dict[str, Any], raw_kwargs: Any) -> dict[str, Any]:
    if not isinstance(raw_kwargs, Mapping):
        raise PrimitiveExecutionError("operation.call kwargs must be an object")
    kwargs: dict[str, Any] = {}
    for name, source in raw_kwargs.items():
        kwargs[str(name)] = _resolve_call_argument(
            values=values, source=source, label=f"kwarg {name!r}"
        )
    return kwargs


def _resolve_call_argument(*, values: dict[str, Any], source: Any, label: str) -> Any:
    if not isinstance(source, Mapping):
        return source
    if "value" in source:
        return _require_call_value(values, str(source["value"]))
    if "literal" in source:
        return source["literal"]
    if "raw_value" in source:
        return _require_call_value(values, str(source["raw_value"]))
    if "string_value" in source or "str_value" in source:
        value_name = str(source.get("string_value", source.get("str_value", "")))
        return str(values.get(value_name) or source.get("default", ""))
    if "bool_value" in source:
        return bool(values.get(str(source["bool_value"])))
    if "not_bool_value" in source:
        return not bool(values.get(str(source["not_bool_value"])))
    raise PrimitiveExecutionError(
        f"operation.call {label} must declare value, raw_value, literal, string_value, bool_value, or not_bool_value"
    )


def _require_call_value(values: dict[str, Any], value_name: str) -> Any:
    if value_name not in values:
        raise PrimitiveExecutionError(
            f"operation.call cannot resolve value {value_name!r}"
        )
    return values[value_name]


def _resolve_dotted_value(payload: Mapping[str, Any], dotted_path: str) -> Any:
    if not dotted_path:
        return None
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _field_by_path(payload: Any, dotted_path: str) -> tuple[bool, Any]:
    if not dotted_path:
        return False, None
    current: Any = payload
    for part in dotted_path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
            continue
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            try:
                current = current[int(part)]
                continue
            except (ValueError, IndexError):
                return False, None
        return False, None
    return True, current


def _available_selectors_for_payload(payload: Any, prefix: str = "") -> list[str]:
    selectors: list[str] = []
    if isinstance(payload, Mapping):
        for key in sorted(str(item) for item in payload):
            path = f"{prefix}.{key}" if prefix else key
            selectors.append(path)
            selectors.extend(_available_selectors_for_payload(payload.get(key), path))
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for index, item in enumerate(payload[:10]):
            path = f"{prefix}.{index}" if prefix else str(index)
            selectors.append(path)
            selectors.extend(_available_selectors_for_payload(item, path))
    return selectors


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
