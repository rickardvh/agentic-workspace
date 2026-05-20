from __future__ import annotations

import importlib
import json
import re
import tomllib
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
        if not _condition_matches(raw_step.get("when"), values=values):
            continue
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
    if primitive == "payload.status":
        return _payload_status(values=values, arguments=arguments, context=context)
    if primitive == "payload.lifecycle-plan":
        return _payload_lifecycle_plan(values=values, arguments=arguments, context=context)
    if primitive == "payload.current-memory":
        return _payload_current_memory(values=values, arguments=arguments, context=context)
    if primitive == "payload.verify":
        return _verify_payload(values=values, arguments=arguments, context=context)
    if primitive == "output.emit":
        return _emit_output(values=values, arguments=arguments)
    if primitive == "output.emit.install-result":
        return _emit_output(values=values, arguments={"text_style": "install-result"})
    if primitive == "output.emit.current-memory":
        return _emit_output(values=values, arguments={"text_style": "current-memory"})
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


def _condition_matches(condition: Any, *, values: dict[str, Any]) -> bool:
    if condition in (None, {}, []):
        return True
    if not isinstance(condition, dict):
        raise PrimitiveExecutionError("step when condition must be an object")
    if "all" in condition:
        items = condition["all"]
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            raise PrimitiveExecutionError("step when all condition must be a sequence")
        return all(_condition_matches(item, values=values) for item in items)
    if "any" in condition:
        items = condition["any"]
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            raise PrimitiveExecutionError("step when any condition must be a sequence")
        return any(_condition_matches(item, values=values) for item in items)
    if "not" in condition:
        return not _condition_matches(condition["not"], values=values)
    value_name = str(condition.get("value", ""))
    if not value_name:
        raise PrimitiveExecutionError("step when condition must declare value, all, any, or not")
    actual = values.get(value_name)
    if "equals" in condition:
        return actual == condition["equals"]
    if "present" in condition:
        return (actual is not None) == bool(condition["present"])
    raise PrimitiveExecutionError("step when value condition must declare equals or present")


def _resolve_target_root(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> str:
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


def _glob(*, arguments: dict[str, Any], context: PrimitiveContext, values: dict[str, Any]) -> list[dict[str, str]]:
    root = _primitive_root(arguments=arguments, context=context, values=values)
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


def _exists(*, arguments: dict[str, Any], context: PrimitiveContext, values: dict[str, Any]) -> bool:
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
        raise PrimitiveExecutionError(f"json.parse missing source value: {source_name!r}") from exc
    return json.loads(str(text))


def _toml_table_counts(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
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
        return {"table_counts": counts, "table_present": False, "table_status": counts["status"]}
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        counts["status"] = "invalid"
        return {"table_counts": counts, "table_present": False, "table_status": counts["status"]}
    records = payload.get(table_name, {}) if isinstance(payload, dict) else {}
    record_values = list(records.values()) if isinstance(records, dict) else []
    counts["status"] = "present"
    counts["note_count"] = len(record_values)
    for record in record_values:
        if not isinstance(record, dict):
            continue
        relevance = str(record.get(relevance_field, "")).strip().lower()
        if relevance == required_value:
            counts["required_count"] += 1
        elif relevance == optional_value:
            counts["optional_count"] += 1
        if bool(record.get(routing_only_field, False)):
            counts["routing_only_count"] += 1
    return {"table_counts": counts, "table_present": True, "table_status": counts["status"]}


def _assemble_payload(*, values: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    fields = arguments.get("fields", {})
    if not isinstance(fields, dict):
        raise PrimitiveExecutionError("payload.assemble fields must be an object")
    if "template" in fields:
        return _resolve_template(fields["template"], values=values)
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


def _verify_payload(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    policy_root = context.root(str(arguments.get("policy_root", "")))
    payload_root = context.root(str(arguments.get("payload_root", "")))
    policy_path = _resolve_inside(policy_root, str(arguments.get("policy_path", "")))
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrimitiveExecutionError(f"payload.verify cannot load policy: {policy_path}") from exc
    target_root = Path(str(values.get(str(arguments.get("target_root_value", "target_root")), context.cwd))).resolve()
    bootstrap_version = int(policy.get("bootstrap_version", 0))
    version_path = str(policy.get("version_path", ""))
    manifest_path = str(policy.get("manifest_path", ""))
    payload_paths = _payload_file_set(payload_root=payload_root, policy=policy)
    legacy_version_path = str(policy.get("legacy_version_path", ""))
    detected_version = _read_first_version(target_root, [version_path, legacy_version_path])
    payload_version = _read_version(payload_root / version_path)
    actions: list[dict[str, str]] = []
    if payload_version is None:
        actions.append(_payload_action("manual review", version_path, "payload version marker is missing or invalid"))
    elif payload_version != bootstrap_version:
        actions.append(
            _payload_action(
                "manual review",
                version_path,
                f"payload version marker ({payload_version}) does not match installer bootstrap version ({bootstrap_version})",
            )
        )
    _verify_upgrade_source(policy=policy, payload_root=payload_root, actions=actions)
    for required in _string_list(policy.get("required_files", []), source="payload.verify required_files"):
        present = required in payload_paths
        actions.append(
            _payload_action(
                "current" if present else "manual review",
                required,
                "required payload file present" if present else "required payload file missing",
                safety="safe" if present else "manual",
                category="safe-update" if present else "contract-drift",
            )
        )
    compatibility_files = _string_list(policy.get("compatibility_contract_files", []), source="payload.verify compatibility_contract_files")
    helper_files = [
        path
        for path in _string_list(policy.get("required_files", []), source="payload.verify required_files")
        if path not in set(compatibility_files)
    ]
    actions.append(
        _payload_action(
            "current",
            manifest_path,
            "compatibility contract files: " + ", ".join(compatibility_files),
            safety="safe",
            category="safe-update",
        )
    )
    upgrade_path = str(policy.get("upgrade_source", {}).get("path", ""))
    actions.append(
        _payload_action(
            "current",
            upgrade_path,
            "lower-stability helper files: " + ", ".join(helper_files),
            safety="safe",
            category="safe-update",
        )
    )
    current_memory = policy.get("current_memory", {})
    if not isinstance(current_memory, dict):
        raise PrimitiveExecutionError("payload.verify current_memory must be an object")
    current_prefix = str(current_memory.get("prefix", ".agentic-workspace/memory/repo/current/"))
    current_payload = {path for path in payload_paths if path.startswith(current_prefix)}
    required_current = set(_string_list(current_memory.get("required", []), source="payload.verify current_memory.required"))
    optional_current = set(_string_list(current_memory.get("optional", []), source="payload.verify current_memory.optional"))
    for extra in sorted(current_payload - (required_current | optional_current)):
        actions.append(_payload_action("manual review", extra, "local-only or unexpected current-memory note is in the shipped payload"))
    for missing in sorted(required_current - current_payload):
        actions.append(_payload_action("manual review", missing, "baseline current-memory note missing from shipped payload"))
    for forbidden in _string_list(policy.get("forbidden_files", []), source="payload.verify forbidden_files"):
        if forbidden in payload_paths:
            actions.append(_payload_action("manual review", forbidden, "forbidden file is present in the shipped payload"))
    for payload_path in sorted(payload_paths):
        if any(
            payload_path.startswith(prefix)
            for prefix in _string_list(policy.get("forbidden_prefixes", []), source="payload.verify forbidden_prefixes")
        ):
            actions.append(_payload_action("manual review", payload_path, "forbidden path prefix is present in the shipped payload"))
    if not _toml_file_valid(payload_root / manifest_path):
        actions.append(_payload_action("manual review", manifest_path, "payload manifest is missing or invalid"))
    _verify_guidance_fragments(policy=policy, payload_root=payload_root, actions=actions)
    return {
        "target_root": str(target_root),
        "dry_run": True,
        "mode": "full",
        "message": "Payload verification",
        "detected_version": detected_version,
        "bootstrap_version": bootstrap_version,
        "actions": actions,
        "route_summary": {},
        "missing_note_hint": "",
        "review_summary": {},
        "review_cases": [],
        "sync_summary": {},
        "route_report_summary": {},
        "route_report_feedback_cases": [],
        "route_report_fixture_results": [],
    }


def _payload_status(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    policy_root = context.root(str(arguments.get("policy_root", "")))
    policy_path = _resolve_inside(policy_root, str(arguments.get("policy_path", "")))
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrimitiveExecutionError(f"payload.status cannot load policy: {policy_path}") from exc
    target_root = Path(str(values.get(str(arguments.get("target_root_value", "target_root")), context.cwd))).resolve()
    bootstrap_version = int(policy.get("bootstrap_version", 0))
    version_path = str(policy.get("version_path", ""))
    legacy_version_path = str(policy.get("legacy_version_path", ""))
    manifest_path = str(policy.get("manifest_path", ""))
    detected_version = _read_first_version(target_root, [version_path, legacy_version_path])
    active = _memory_manifest_counts(target_root=target_root, manifest_path=manifest_path)
    actions: list[dict[str, Any]] = []
    workspace_notice = policy.get("workspace_orchestrator_notice", {})
    if isinstance(workspace_notice, dict):
        marker = str(workspace_notice.get("marker", "")).strip()
        if marker and not (target_root / marker).exists():
            actions.append(
                _status_action(
                    "warning",
                    marker,
                    str(workspace_notice.get("detail", "")),
                    role=str(workspace_notice.get("role", "workspace-orchestration")),
                    safety=str(workspace_notice.get("safety", "safe")),
                    source=marker,
                    category=str(workspace_notice.get("category", "safe-update")),
                )
            )
    for raw_entry in _list_of_objects(policy.get("status_files", []), source="payload.status status_files"):
        relative_path = str(raw_entry.get("path", ""))
        present = (target_root / relative_path).exists()
        role = str(raw_entry.get("role", ""))
        safety = str(raw_entry.get("safety", "safe"))
        kind = "present" if present else "missing"
        detail = "file exists" if present else "file missing"
        actions.append(
            _status_action(
                kind,
                relative_path,
                detail,
                role=role,
                safety=safety,
                source=relative_path,
                category=str(raw_entry.get("present_category" if present else "missing_category", ""))
                or _infer_status_category(kind=kind, path=relative_path, detail=detail, role=role, safety=safety),
            )
        )
    for obsolete in _string_list(policy.get("obsolete_files", []), source="payload.status obsolete_files"):
        if (target_root / obsolete).exists():
            actions.append(
                _status_action(
                    "obsolete",
                    obsolete,
                    "legacy shared file should be removed on upgrade",
                    role="shared-replaceable",
                    safety="safe",
                    source=obsolete,
                    category="obsolete-managed-file",
                )
            )
    return {
        "target_root": str(target_root),
        "dry_run": bool(arguments.get("dry_run", False)),
        "mode": "",
        "message": str(arguments.get("message", "Status report")),
        "health": "healthy" if active["status"] == "present" else "attention-needed",
        "detected_version": detected_version,
        "bootstrap_version": bootstrap_version,
        "action_count": len(actions),
        "actions": actions,
        "active": active,
        "detail_command": str(arguments.get("detail_command", "")),
    }


def _payload_lifecycle_plan(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    policy_root = context.root(str(arguments.get("policy_root", "")))
    policy_path = _resolve_inside(policy_root, str(arguments.get("policy_path", "")))
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrimitiveExecutionError(f"payload.lifecycle-plan cannot load policy: {policy_path}") from exc
    target_root = Path(str(values.get(str(arguments.get("target_root_value", "target_root")), context.cwd))).resolve()
    bootstrap_version = int(policy.get("bootstrap_version", 0))
    version_path = str(policy.get("version_path", ""))
    legacy_version_path = str(policy.get("legacy_version_path", ""))
    detected_version = _read_first_version(target_root, [version_path, legacy_version_path])
    actions: list[dict[str, Any]] = []
    workspace_notice = policy.get("workspace_orchestrator_notice", {})
    if isinstance(workspace_notice, dict):
        marker = str(workspace_notice.get("marker", "")).strip()
        if marker and not (target_root / marker).exists():
            actions.append(
                _status_action(
                    "warning",
                    marker,
                    str(workspace_notice.get("detail", "")),
                    role=str(workspace_notice.get("role", "workspace-orchestration")),
                    safety=str(workspace_notice.get("safety", "safe")),
                    source=marker,
                    category=str(workspace_notice.get("category", "safe-update")),
                )
            )
    for raw_entry in _list_of_objects(policy.get("status_files", []), source="payload.lifecycle-plan status_files"):
        relative_path = str(raw_entry.get("path", ""))
        if not relative_path:
            continue
        exists = (target_root / relative_path).exists()
        actions.append(
            _status_action(
                "preserve" if exists else str(arguments.get("missing_kind", "would copy")),
                relative_path,
                "already exists" if exists else str(arguments.get("missing_detail", "planned change")),
                role=str(raw_entry.get("role", "")),
                safety=str(raw_entry.get("safety", "safe")),
                source=str(raw_entry.get("source", relative_path)),
                category=str(raw_entry.get("category", "")) or "safe-update",
            )
        )
    return {
        "target_root": str(target_root),
        "dry_run": bool(arguments.get("dry_run", True)),
        "mode": str(arguments.get("mode", "")),
        "message": str(arguments.get("message", "Install plan")),
        "detected_version": detected_version,
        "bootstrap_version": bootstrap_version,
        "actions": actions,
    }


def _payload_current_memory(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    policy_root = context.root(str(arguments.get("policy_root", "")))
    policy_path = _resolve_inside(policy_root, str(arguments.get("policy_path", "")))
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrimitiveExecutionError(f"payload.current-memory cannot load policy: {policy_path}") from exc
    target_root = Path(str(values.get(str(arguments.get("target_root_value", "target_root")), context.cwd))).resolve()
    bootstrap_version = int(policy.get("bootstrap_version", 0))
    version_path = str(policy.get("version_path", ""))
    legacy_version_path = str(policy.get("legacy_version_path", ""))
    current_memory = policy.get("current_memory", {})
    if not isinstance(current_memory, dict):
        raise PrimitiveExecutionError("payload.current-memory current_memory policy must be an object")
    note_paths = _string_list(current_memory.get("view_files", []), source="payload.current-memory current_memory.view_files")
    notes: list[dict[str, Any]] = []
    for relative_path in note_paths:
        note_path = target_root / relative_path
        exists = note_path.exists()
        notes.append(
            {
                "path": relative_path,
                "exists": exists,
                "content": note_path.read_text(encoding="utf-8") if exists else "",
            }
        )
    return {
        "target_root": str(target_root),
        "detected_version": _read_first_version(target_root, [version_path, legacy_version_path]),
        "bootstrap_version": bootstrap_version,
        "notes": notes,
    }


def _memory_manifest_counts(*, target_root: Path, manifest_path: str) -> dict[str, Any]:
    counts = {
        "status": "missing",
        "note_count": 0,
        "required_count": 0,
        "optional_count": 0,
        "routing_only_count": 0,
        "path": manifest_path,
    }
    path = target_root / manifest_path
    if not path.exists():
        return counts
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        counts["status"] = "invalid"
        return counts
    notes = payload.get("notes", {}) if isinstance(payload, dict) else {}
    note_values = list(notes.values()) if isinstance(notes, dict) else []
    counts["status"] = "present"
    counts["note_count"] = len(note_values)
    for note in note_values:
        if not isinstance(note, dict):
            continue
        relevance = str(note.get("task_relevance", "")).strip().lower()
        if relevance == "required":
            counts["required_count"] += 1
        elif relevance == "optional":
            counts["optional_count"] += 1
        if bool(note.get("routing_only", False)):
            counts["routing_only_count"] += 1
    return counts


def _status_action(
    kind: str,
    path: str,
    detail: str,
    *,
    role: str,
    safety: str,
    source: str,
    category: str,
) -> dict[str, str]:
    return {
        "kind": kind,
        "path": path,
        "detail": detail,
        "role": role,
        "safety": safety,
        "source": source,
        "category": category,
        "remediation_kind": "",
        "remediation_target": "",
        "remediation_reason": "",
        "remediation_confidence": "",
        "memory_action": "",
        "match_source": "",
    }


def _infer_status_category(*, kind: str, path: str, detail: str, role: str, safety: str) -> str:
    detail_lower = detail.lower()
    if "placeholder" in detail_lower:
        return "placeholder-review"
    if role in {"payload-contract", "local-entrypoint"} or role.startswith("shared-"):
        if kind in {"manual review", "missing"}:
            return "contract-drift"
    if kind in {"current", "present", "optional", "required", "warning"}:
        return "safe-update"
    if kind in {"manual review", "consider"}:
        return "manual-review"
    if safety == "safe":
        return "safe-update"
    return ""


def _payload_file_set(*, payload_root: Path, policy: dict[str, Any]) -> set[str]:
    aliases = {
        str(item["source"]): str(item["target"])
        for item in policy.get("payload_path_aliases", [])
        if isinstance(item, dict) and isinstance(item.get("source"), str) and isinstance(item.get("target"), str)
    }
    payload_paths: set[str] = set()
    for path in payload_root.rglob("*"):
        if path.is_file():
            relative = path.relative_to(payload_root).as_posix()
            payload_paths.add(aliases.get(relative, relative))
    return payload_paths


def _payload_action(kind: str, path: str, detail: str, *, safety: str = "manual", category: str = "contract-drift") -> dict[str, str]:
    return {
        "kind": kind,
        "path": path,
        "detail": detail,
        "role": "payload-contract",
        "safety": safety,
        "source": path,
        "category": category,
        "remediation_kind": "",
        "remediation_target": "",
        "remediation_reason": "",
        "remediation_confidence": "",
        "memory_action": "",
        "match_source": "",
    }


def _verify_upgrade_source(*, policy: dict[str, Any], payload_root: Path, actions: list[dict[str, str]]) -> None:
    upgrade_source = policy.get("upgrade_source", {})
    if not isinstance(upgrade_source, dict):
        raise PrimitiveExecutionError("payload.verify upgrade_source must be an object")
    relative = str(upgrade_source.get("path", ""))
    legacy_relative = str(upgrade_source.get("legacy_path", ""))
    path = payload_root / relative
    if not path.exists():
        path = payload_root / legacy_relative
    if not path.exists():
        actions.append(_payload_action("manual review", relative, "upgrade source metadata is missing from the payload"))
        return
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        actions.append(_payload_action("manual review", relative, "upgrade source metadata is not valid TOML"))
        return
    source_type = str(data.get("source_type", "")).strip()
    if source_type not in set(_string_list(upgrade_source.get("allowed_source_types", []), source="payload.verify allowed_source_types")):
        actions.append(_payload_action("manual review", relative, "upgrade source metadata must declare source_type as git or local"))
        return
    for required in _string_list(upgrade_source.get("required_fields", []), source="payload.verify required_fields"):
        if not str(data.get(required, "")).strip():
            actions.append(_payload_action("manual review", relative, f"upgrade source metadata is missing {required}"))
            return
    for field_name, date_format in (upgrade_source.get("date_fields", {}) or {}).items():
        value = str(data.get(str(field_name), "")).strip()
        if value and str(date_format) == "YYYY-MM-DD" and not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            actions.append(_payload_action("manual review", relative, f"upgrade source metadata has invalid {field_name}; use YYYY-MM-DD"))
    for field_name in _string_list(upgrade_source.get("integer_fields", []), source="payload.verify integer_fields"):
        if not isinstance(data.get(field_name, 30), int):
            actions.append(
                _payload_action("manual review", relative, f"upgrade source metadata has invalid {field_name}; use an integer day count")
            )


def _verify_guidance_fragments(*, policy: dict[str, Any], payload_root: Path, actions: list[dict[str, str]]) -> None:
    raw_fragments = policy.get("guidance_fragments", {})
    if not isinstance(raw_fragments, dict):
        raise PrimitiveExecutionError("payload.verify guidance_fragments must be an object")
    for relative, fragments in raw_fragments.items():
        relative_path = str(relative)
        path = payload_root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [fragment for fragment in _string_list(fragments, source="payload.verify guidance fragments") if fragment not in text]
        actions.append(
            _payload_action(
                "current" if not missing else "manual review",
                relative_path,
                "collaboration-safe current-note guidance present"
                if not missing
                else "current-note payload guidance is missing collaboration-safe wording",
                safety="safe" if not missing else "manual",
                category="safe-update" if not missing else "contract-drift",
            )
        )


def _toml_file_valid(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return True


def _read_version(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^\s*Version:\s*(\d+)\s*$", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def _read_first_version(root: Path, relative_paths: Sequence[str]) -> int | None:
    for relative_path in relative_paths:
        if not relative_path:
            continue
        version = _read_version(root / relative_path)
        if version is not None:
            return version
    return None


def _string_list(value: Any, *, source: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PrimitiveExecutionError(f"{source} must be a list of strings")
    return value


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
            raise PrimitiveExecutionError("template $field path must be a string or sequence")
        value: Any = values.get(value_name)
        for part in path_parts:
            if not isinstance(value, Mapping) or part not in value:
                raise PrimitiveExecutionError(f"template $field cannot resolve {value_name!r}.{'.'.join(path_parts)}")
            value = value[part]
        return value
    if set(template) == {"$count"}:
        counted = values.get(str(template["$count"]), [])
        if not isinstance(counted, Sequence) or isinstance(counted, (str, bytes)):
            raise PrimitiveExecutionError(f"template count source must be a sequence: {template['$count']!r}")
        return len(counted)
    if "$exists_status" in template:
        spec = template["$exists_status"]
        if not isinstance(spec, dict):
            raise PrimitiveExecutionError("template $exists_status must be an object")
        value = bool(values.get(str(spec.get("value", ""))))
        return spec.get("present", "present") if value else spec.get("missing", "missing")
    if "$count_status" in template:
        spec = template["$count_status"]
        if not isinstance(spec, dict):
            raise PrimitiveExecutionError("template $count_status must be an object")
        counted = values.get(str(spec.get("value", "")), [])
        if not isinstance(counted, Sequence) or isinstance(counted, (str, bytes)):
            raise PrimitiveExecutionError(f"template count source must be a sequence: {spec.get('value')!r}")
        return spec.get("present", "present") if len(counted) else spec.get("missing", "missing")
    if "$join_path" in template:
        spec = template["$join_path"]
        if not isinstance(spec, dict):
            raise PrimitiveExecutionError("template $join_path must be an object")
        base = Path(str(values.get(str(spec.get("base", "")), "")))
        return (base / str(spec.get("path", ""))).as_posix()
    return {str(key): _resolve_template(value, values=values) for key, value in template.items()}


def _emit_output(*, values: dict[str, Any], arguments: dict[str, Any] | None = None) -> str:
    arguments = arguments or {}
    result = _plain_output_result(values.get("result"))
    output_format = str(values.get("format") or "text")
    if output_format == "json":
        return json.dumps(result, indent=2, sort_keys=True) + "\n"
    if str(arguments.get("text_style", "")) == "current-memory" and isinstance(result, dict):
        return _emit_current_memory_text(result)
    if str(arguments.get("text_style", "")) == "install-result" and isinstance(result, dict):
        return _emit_install_result_text(result)
    if isinstance(result, dict) and isinstance(result.get("route_report_summary"), dict):
        return _emit_route_report_text(result)
    if isinstance(result, dict) and result.get("kind") == "memory-module-report/v1":
        return _emit_memory_report_text(result)
    if not isinstance(result, dict):
        return f"{result}\n"
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
                details.append(str(value) if not label_name else f"{label_name}={value}")
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
        lines.append(f"Feedback: {feedback.get('status', 'unknown')} ({feedback.get('path', '')})")
    if isinstance(fixtures, Mapping):
        lines.append(f"Fixtures: {fixtures.get('status', 'unknown')} ({fixtures.get('fixture_count', 0)})")
    detail = summary.get("detail") or result.get("detail_command")
    if detail:
        lines.append(str(detail))
    return "\n".join(lines).rstrip() + "\n"


def _emit_memory_report_text(result: dict[str, Any]) -> str:
    status = result.get("status", {})
    active = result.get("active", {})
    habitual_pull = result.get("habitual_pull", {})
    next_action = result.get("next_action", {})
    lines = ["Memory report", f"Target: {result.get('target_root', '')}", f"Health: {result.get('health', 'unknown')}"]
    if isinstance(status, Mapping):
        lines.append(f"Notes: {status.get('note_count', 0)} ({status.get('manifest_status', 'unknown')})")
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


def _primitive_root(*, arguments: dict[str, Any], context: PrimitiveContext, values: dict[str, Any]) -> Path:
    if "base_value" in arguments:
        value_name = str(arguments["base_value"])
        if value_name not in values:
            raise PrimitiveExecutionError(f"unknown primitive base value: {value_name!r}")
        return Path(str(values[value_name])).resolve()
    return context.root(str(arguments.get("root", "")))


def _ensure_inside(root: Path, candidate: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PrimitiveExecutionError(f"path escapes primitive root: {candidate}") from exc


def _list_of_objects(value: Any, *, source: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise PrimitiveExecutionError(f"{source} must be a list of objects")
    return value
