"""Generated target-local host primitive support module.

Source: src/agentic_workspace/contracts/command_package_ir.json
Host primitive support: src/agentic_workspace/contracts/python_primitive_support.py
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

# DO NOT EDIT DIRECTLY.
# Domain-runtime primitive behavior belongs in the configured host support source.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast


class PrimitiveExecutionError(RuntimeError):
    pass


PrimitiveContext = Any


def execute_host_primitive(
    primitive: str,
    *,
    values: dict[str, Any],
    arguments: dict[str, Any],
    context: PrimitiveContext,
) -> Any:
    if primitive == "memory.payload.status":
        return _payload_status(values=values, arguments=arguments, context=context)
    if primitive == "memory.payload.lifecycle-plan":
        return _payload_lifecycle_plan(values=values, arguments=arguments, context=context)
    if primitive == "memory.payload.current-memory":
        return _payload_current_memory(values=values, arguments=arguments, context=context)
    if primitive == "memory.payload.verify":
        return _verify_payload(values=values, arguments=arguments, context=context)
    if primitive == "workspace.output.emit":
        return _emit_output(values=values, arguments=arguments)
    if primitive == "assignment.lifecycle.apply":
        return _assignment_lifecycle_apply(values=values, arguments=arguments, context=context)
    raise PrimitiveExecutionError(f"unsupported AW host primitive: {primitive!r}")


def _verify_payload(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    policy_root = context.root(str(arguments.get("policy_root", "")))
    payload_root = context.root(str(arguments.get("payload_root", "")))
    policy_path = _resolve_inside(policy_root, str(arguments.get("policy_path", "")))
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrimitiveExecutionError(f"memory.payload.verify cannot load policy: {policy_path}") from exc
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
    for required in _string_list(policy.get("required_files", []), source="memory.payload.verify required_files"):
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
    compatibility_files = _string_list(
        policy.get("compatibility_contract_files", []), source="memory.payload.verify compatibility_contract_files"
    )
    helper_files = [
        path
        for path in _string_list(policy.get("required_files", []), source="memory.payload.verify required_files")
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
        raise PrimitiveExecutionError("memory.payload.verify current_memory must be an object")
    current_prefix = str(current_memory.get("prefix", ""))
    current_payload = {path for path in payload_paths if path.startswith(current_prefix)}
    required_current = set(_string_list(current_memory.get("required", []), source="memory.payload.verify current_memory.required"))
    optional_current = set(_string_list(current_memory.get("optional", []), source="memory.payload.verify current_memory.optional"))
    for extra in sorted(current_payload - (required_current | optional_current)):
        actions.append(_payload_action("manual review", extra, "local-only or unexpected current-memory note is in the shipped payload"))
    for missing in sorted(required_current - current_payload):
        actions.append(_payload_action("manual review", missing, "baseline current-memory note missing from shipped payload"))
    for forbidden in _string_list(policy.get("forbidden_files", []), source="memory.payload.verify forbidden_files"):
        if forbidden in payload_paths:
            actions.append(_payload_action("manual review", forbidden, "forbidden file is present in the shipped payload"))
    for payload_path in sorted(payload_paths):
        if any(
            payload_path.startswith(prefix)
            for prefix in _string_list(policy.get("forbidden_prefixes", []), source="memory.payload.verify forbidden_prefixes")
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
        raise PrimitiveExecutionError(f"memory.payload.status cannot load policy: {policy_path}") from exc
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
    for raw_entry in _list_of_objects(policy.get("status_files", []), source="memory.payload.status status_files"):
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
    for obsolete in _string_list(policy.get("obsolete_files", []), source="memory.payload.status obsolete_files"):
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
        raise PrimitiveExecutionError(f"memory.payload.lifecycle-plan cannot load policy: {policy_path}") from exc
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
    for raw_entry in _list_of_objects(policy.get("status_files", []), source="memory.payload.lifecycle-plan status_files"):
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
        raise PrimitiveExecutionError(f"memory.payload.current-memory cannot load policy: {policy_path}") from exc
    target_root = Path(str(values.get(str(arguments.get("target_root_value", "target_root")), context.cwd))).resolve()
    bootstrap_version = int(policy.get("bootstrap_version", 0))
    version_path = str(policy.get("version_path", ""))
    legacy_version_path = str(policy.get("legacy_version_path", ""))
    current_memory = policy.get("current_memory", {})
    if not isinstance(current_memory, dict):
        raise PrimitiveExecutionError("memory.payload.current-memory current_memory policy must be an object")
    note_paths = _string_list(current_memory.get("view_files", []), source="memory.payload.current-memory current_memory.view_files")
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
        note_payload = cast(Mapping[str, Any], note)
        relevance = str(note_payload.get("task_relevance", "")).strip().lower()
        if relevance == "required":
            counts["required_count"] += 1
        elif relevance == "optional":
            counts["optional_count"] += 1
        if bool(note_payload.get("routing_only", False)):
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
        raise PrimitiveExecutionError("memory.payload.verify upgrade_source must be an object")
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
    if source_type not in set(
        _string_list(upgrade_source.get("allowed_source_types", []), source="memory.payload.verify allowed_source_types")
    ):
        actions.append(_payload_action("manual review", relative, "upgrade source metadata must declare source_type as git or local"))
        return
    for required in _string_list(upgrade_source.get("required_fields", []), source="memory.payload.verify required_fields"):
        if not str(data.get(required, "")).strip():
            actions.append(_payload_action("manual review", relative, f"upgrade source metadata is missing {required}"))
            return
    for field_name, date_format in (upgrade_source.get("date_fields", {}) or {}).items():
        value = str(data.get(str(field_name), "")).strip()
        if value and str(date_format) == "YYYY-MM-DD" and not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            actions.append(_payload_action("manual review", relative, f"upgrade source metadata has invalid {field_name}; use YYYY-MM-DD"))
    for field_name in _string_list(upgrade_source.get("integer_fields", []), source="memory.payload.verify integer_fields"):
        if not isinstance(data.get(field_name, 30), int):
            actions.append(
                _payload_action("manual review", relative, f"upgrade source metadata has invalid {field_name}; use an integer day count")
            )


def _verify_guidance_fragments(*, policy: dict[str, Any], payload_root: Path, actions: list[dict[str, str]]) -> None:
    raw_fragments = policy.get("guidance_fragments", {})
    if not isinstance(raw_fragments, dict):
        raise PrimitiveExecutionError("memory.payload.verify guidance_fragments must be an object")
    for relative, fragments in raw_fragments.items():
        relative_path = str(relative)
        path = payload_root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [
            fragment for fragment in _string_list(fragments, source="memory.payload.verify guidance fragments") if fragment not in text
        ]
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
        raise PrimitiveExecutionError(f"{source} entries must be strings or objects with relative_path")
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


def _assignment_lifecycle_apply(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    del arguments
    operation_id = str(values.get("operation_id") or "")
    transition = str(values.get("assignment_command") or operation_id.rsplit(".", 1)[-1])
    supported = {"export", "import", "admit", "reject", "repair", "reassign", "integrate", "close", "cleanup", "override"}
    if transition not in supported:
        raise PrimitiveExecutionError(f"unsupported assignment lifecycle transition: {transition!r}")
    target_root = Path(str(values.get("target_root") or values.get("target") or context.cwd)).resolve()
    local_root = _resolve_inside(target_root, ".agentic-workspace/local/assignment-runs")
    dry_run = bool(values.get("dry_run", False))

    assignment_id = _optional_text(values.get("assignment_id"))
    assignment_revision = _optional_text(values.get("assignment_revision"))
    run_id = _optional_text(values.get("run_id")) or _assignment_default_run_id(
        assignment_id=assignment_id, assignment_revision=assignment_revision, transition=transition
    )
    run_dir = _resolve_inside(local_root, _safe_assignment_fragment(run_id))
    state_path = _resolve_inside(run_dir, "state.json")
    state = _read_assignment_state(state_path=state_path)
    artifact_paths: list[Path] = []
    failures: list[dict[str, str]] = []
    writes: dict[Path, Any] = {}

    def require(field: str) -> str:
        value = _optional_text(values.get(field))
        if not value:
            failures.append(
                {
                    "reason": "missing-required-input",
                    "field": field,
                    "recovery": f"Retry assignment {transition} with --{field.replace('_', '-')}.",
                }
            )
        return value

    def artifact(relative: str) -> Path:
        return _resolve_inside(run_dir, relative)

    if transition == "export":
        assignment_id = require("assignment_id")
        current_authorities = _assignment_current_authorities_from_store(
            target_root=target_root,
            assignment_id=assignment_id,
            assignment_revision=assignment_revision,
            run_id=run_id,
            state=state,
            values=values,
            failures=failures,
        )
        identity = _assignment_identity(current_authorities) if current_authorities else {}
        target_name = require("target_name") or _optional_text(identity.get("target"))
        if identity and assignment_revision and identity.get("revision") != assignment_revision:
            failures.append(
                {
                    "reason": "assignment-revision-mismatch",
                    "field": "assignment_revision",
                    "recovery": "Export from the current Planning assignment identity revision.",
                }
            )
        packet = {
            "kind": "agentic-workspace/assignment-export-packet/v1",
            "assignment_id": assignment_id,
            "assignment_revision": identity.get("revision") if identity else assignment_revision,
            "run_id": run_id,
            "target": target_name,
            "transport": _optional_text(values.get("transport")) or "manual",
            "scope": _assignment_list(identity.get("allowed_paths")) or _optional_text(values.get("scope")),
            "assignment_identity": identity,
            "authority_refs": {
                "planning_assignment": current_authorities.get("planning_assignment_ref"),
                "proof_receipt": current_authorities.get("proof_receipt_ref"),
                "mutation_baseline": "host-resolved:git-or-aw-baseline",
            },
            "return_contract": "assignment import places results in received/awaiting-admission before admission or integration",
        }
        packet_path = artifact("export/packet.json")
        prompt_path = artifact("export/prompt.md")
        manifest_path = artifact("export/manifest.json")
        prompt = _assignment_export_prompt(packet)
        manifest = {
            "kind": "agentic-workspace/assignment-export-manifest/v1",
            "assignment_id": assignment_id,
            "assignment_revision": assignment_revision,
            "run_id": run_id,
            "packet_ref": _assignment_relative(packet_path, root=target_root),
            "prompt_ref": _assignment_relative(prompt_path, root=target_root),
            "integrity": _assignment_digest(packet),
        }
        artifact_paths.extend([packet_path, prompt_path, manifest_path])
        state.update(
            {
                "assignment": packet,
                "planning_assignment_ref": current_authorities.get("planning_assignment_ref"),
                "proof_receipt_ref": current_authorities.get("proof_receipt_ref"),
                "current_state": "handoff-prepared",
                "run_id": run_id,
            }
        )
        writes = {packet_path: packet, prompt_path: prompt, manifest_path: manifest}
    elif transition == "import":
        require("run_id")
        returned = _assignment_json_value(require("return_json"), field="return_json")
        return_id = _optional_text(values.get("return_id")) or _assignment_digest(returned).removeprefix("sha256:")[:16]
        assignment = state.get("assignment") if isinstance(state.get("assignment"), dict) else {}
        if assignment:
            expected_revision = _optional_text(assignment.get("assignment_revision"))
            returned_revision = _optional_text(returned.get("assignment_revision")) if isinstance(returned, dict) else ""
            if expected_revision and returned_revision != expected_revision:
                failures.append(
                    {
                        "reason": "assignment-revision-mismatch",
                        "field": "return_json.assignment_revision",
                        "recovery": "Return work generated from the current exported assignment packet.",
                    }
                )
        return_path = artifact(f"received/awaiting-admission/{_safe_assignment_fragment(return_id)}.json")
        receipt_path = artifact(f"received/import-{_safe_assignment_fragment(return_id)}.json")
        receipt = {
            "kind": "agentic-workspace/assignment-return-import-receipt/v1",
            "run_id": run_id,
            "return_id": return_id,
            "state": "received/awaiting-admission",
            "return_artifact_ref": _assignment_relative(return_path, root=target_root),
            "integrity": _assignment_digest(returned),
            "rule": "Import records returned work only; AW-owned review, proof, admission, and integration remain pending.",
        }
        artifact_paths.extend([return_path, receipt_path])
        raw_returns = state.get("returns")
        returns = cast(dict[str, Any], raw_returns) if isinstance(raw_returns, dict) else {}
        returns[return_id] = {
            "artifact_ref": _assignment_relative(return_path, root=target_root),
            "integrity": _assignment_digest(returned),
            "state": "received/awaiting-admission",
        }
        state.update({"current_state": "awaiting-admission", "last_return_id": return_id, "returns": returns})
        writes = {return_path: returned, receipt_path: receipt}
    elif transition in {"admit", "reject", "repair"}:
        require("run_id")
        if transition in {"reject", "repair"}:
            require("reason")
        return_id = _optional_text(values.get("return_id")) or str(state.get("last_return_id") or "unidentified-return")
        returned = _assignment_return_for_state(state=state, target_root=target_root, run_dir=run_dir, return_id=return_id)
        current_authorities = _assignment_current_authorities_from_store(
            target_root=target_root,
            assignment_id=assignment_id or _optional_text(state.get("assignment_id")),
            assignment_revision=assignment_revision,
            run_id=run_id,
            state=state,
            values=values,
            failures=failures,
        )
        admission = (
            _assignment_admit_with_current_authority(current_authorities=current_authorities, returned_work=returned)
            if transition == "admit"
            else {"admitted": False, "status": {"reject": "rejected", "repair": "repair-requested"}[transition], "failures": []}
        )
        if transition == "admit" and not admission.get("admitted"):
            failures.extend(_assignment_failures_from_admission(admission))
        admission_status = (
            (_optional_text(values.get("admission_status")) or ("admitted" if admission.get("admitted") else "blocked"))
            if transition == "admit"
            else {"reject": "rejected", "repair": "repair-requested"}[transition]
        )
        receipt_path = artifact(f"admission/{_safe_assignment_fragment(return_id)}.{transition}.json")
        receipt = {
            "kind": "agentic-workspace/assignment-admission-receipt/v1",
            "run_id": run_id,
            "return_id": return_id,
            "status": admission_status,
            "admission": admission,
            "current_authority_ref": _optional_text(admission.get("assignment_revision")),
            "live_mutation_baseline": _optional_text(
                (admission.get("current_authority") or {}).get("mutation_baseline")
                if isinstance(admission.get("current_authority"), dict)
                else ""
            ),
            "reason": _optional_text(values.get("reason")),
            "worker_reported_proof_trusted": False,
            "worker_reported_baseline_trusted": False,
            "rule": "Admission receipts are valid only after the host primitive re-resolves current Planning, proof, run, and mutation baseline authorities and strict return admission succeeds.",
        }
        artifact_paths.append(receipt_path)
        state.update(
            {
                "current_state": admission_status,
                "last_admission_status": admission_status,
                "last_admission": admission,
                "last_return_id": return_id,
            }
        )
        writes = {receipt_path: receipt}
    elif transition == "integrate":
        require("run_id")
        return_id = _optional_text(values.get("return_id")) or str(state.get("last_return_id") or "unidentified-return")
        returned = _assignment_return_for_state(state=state, target_root=target_root, run_dir=run_dir, return_id=return_id)
        current_authorities = _assignment_current_authorities_from_store(
            target_root=target_root,
            assignment_id=assignment_id or _optional_text(state.get("assignment_id")),
            assignment_revision=assignment_revision,
            run_id=run_id,
            state=state,
            values=values,
            failures=failures,
        )
        admission = _assignment_admit_with_current_authority(current_authorities=current_authorities, returned_work=returned)
        admitted = state.get("last_admission_status") == "admitted" and bool(admission.get("admitted"))
        if not admitted:
            if not admission.get("admitted"):
                failures.extend(_assignment_failures_from_admission(admission))
            if state.get("last_admission_status") != "admitted":
                failures.append(
                    {
                        "reason": "return-not-admitted",
                        "field": "state.last_admission_status",
                        "recovery": "Run assignment admit after importing returned work and resolving current authority.",
                    }
                )
        receipt_path = artifact("integration/integration.json")
        receipt = {
            "kind": "agentic-workspace/assignment-integration-receipt/v1",
            "run_id": run_id,
            "status": "integrated" if admitted and not failures else "blocked",
            "admission": admission,
        }
        artifact_paths.append(receipt_path)
        state.update({"current_state": receipt["status"]})
        writes = {receipt_path: receipt}
    elif transition == "reassign":
        require("run_id")
        target_name = require("target_name")
        reason = require("reason")
        receipt_path = artifact("reassignment/reassign.json")
        receipt = {
            "kind": "agentic-workspace/assignment-reassignment-receipt/v1",
            "run_id": run_id,
            "status": "superseded",
            "new_target": target_name,
            "reason": reason,
        }
        artifact_paths.append(receipt_path)
        state.update({"current_state": "superseded", "reassigned_to": target_name})
        writes = {receipt_path: receipt}
    elif transition == "override":
        assignment_id = require("assignment_id")
        reason = require("reason")
        scope = require("scope")
        expires_at = require("expires_at")
        receipt_path = artifact("override/override.json")
        receipt = {
            "kind": "agentic-workspace/assignment-human-override-receipt/v1",
            "assignment_id": assignment_id,
            "run_id": run_id,
            "status": "override-recorded",
            "scope": scope,
            "reason": reason,
            "expires_at": expires_at,
            "revalidation_required": True,
            "claim_effect": "downgrade-until-revalidated",
            "proof_effect": "explicit override receipt required in proof boundary",
        }
        artifact_paths.append(receipt_path)
        state.update({"current_state": "override-recorded", "override": receipt})
        writes = {receipt_path: receipt}
    else:
        require("run_id")
        receipt_path = artifact(f"closeout/{transition}.json")
        receipt = {
            "kind": "agentic-workspace/assignment-closeout-receipt/v1",
            "run_id": run_id,
            "status": "closed" if transition == "close" else "archived",
            "cleanup_deletes_files": False,
            "reason": _optional_text(values.get("reason")),
        }
        artifact_paths.append(receipt_path)
        state.update({"current_state": receipt["status"]})
        writes = {receipt_path: receipt}

    transition_receipt = {
        "transition": transition,
        "operation_id": operation_id,
        "status": "blocked" if failures else str(state.get("current_state") or transition),
        "artifacts": [_assignment_relative(path, root=target_root) for path in artifact_paths],
        "dry_run": dry_run,
    }
    transitions = state.get("transitions")
    if not isinstance(transitions, list):
        transitions = []
    transitions.append(transition_receipt)
    state["transitions"] = transitions
    state["run_id"] = run_id
    if assignment_id:
        state["assignment_id"] = assignment_id
    state["schema_version"] = "agentic-workspace/assignment-run-state/v1"
    state["locality"] = "local-disposable"

    if failures:
        outcome = "blocked"
        status = "blocked"
    elif dry_run:
        outcome = "noop"
        status = str(state.get("current_state") or transition)
    else:
        outcome = "applied"
        status = str(state.get("current_state") or transition)
        for path, payload in writes.items():
            _write_assignment_artifact(path=path, payload=payload)
        _write_assignment_artifact(path=state_path, payload=state)
        artifact_paths.append(state_path)

    artifact_refs = [_assignment_relative(path, root=target_root) for path in artifact_paths]
    return {
        "kind": "agentic-workspace/assignment-lifecycle-result/v1",
        "operation_id": operation_id,
        "transition": transition,
        "status": status,
        "outcome": outcome,
        "mutation_applied": outcome == "applied",
        "target_root": target_root.as_posix(),
        "run_id": run_id,
        "artifact_refs": artifact_refs,
        "state": state,
        "failures": failures,
        "reason_code": failures[0]["reason"] if failures else None,
        "recovery_command": failures[0]["recovery"] if failures else None,
        "message": f"assignment {transition}: {status}",
        "actions": [{"kind": "write", "path": ref} for ref in artifact_refs],
    }


def _assignment_current_authorities_from_store(
    *,
    target_root: Path,
    assignment_id: str,
    assignment_revision: str,
    run_id: str,
    state: Mapping[str, Any],
    values: Mapping[str, Any],
    failures: list[dict[str, str]],
) -> dict[str, Any]:
    if not assignment_id:
        failures.append(
            {
                "reason": "missing-current-authority",
                "field": "assignment_id",
                "recovery": "Retry with the stable assignment id so AW can resolve Planning authority.",
            }
        )
        return {}
    planning_assignment_ref = _assignment_planning_ref(values=values, assignment_id=assignment_id)
    planning_assignment = _read_assignment_json_ref(
        target_root=target_root,
        ref=planning_assignment_ref,
        field="planning_assignment_ref",
        failures=failures,
    )
    if not planning_assignment:
        return {}
    if planning_assignment.get("kind") != "agentic-workspace/planning-assignment/v1":
        failures.append(
            {
                "reason": "invalid-current-authority",
                "field": "planning_assignment_ref.kind",
                "recovery": "Regenerate the checked-in Planning assignment record.",
            }
        )
    if _optional_text(planning_assignment.get("assignment_id")) != assignment_id:
        failures.append(
            {
                "reason": "assignment-id-mismatch",
                "field": "planning_assignment_ref.assignment_id",
                "recovery": "Retry with the assignment id owned by the Planning assignment record.",
            }
        )
    assignment_gate = _assignment_mapping(planning_assignment.get("assignment_gate"))
    assignment_policy = _assignment_mapping(planning_assignment.get("assignment_policy"))
    delegation_decision = _assignment_mapping(planning_assignment.get("delegation_decision"))
    identity = _assignment_identity(
        {
            "assignment_gate": assignment_gate,
            "assignment_policy": assignment_policy,
            "delegation_decision": delegation_decision,
        }
    )
    current_revision = _optional_text(planning_assignment.get("current_revision") or identity.get("revision"))
    if assignment_revision and assignment_revision != current_revision:
        failures.append(
            {
                "reason": "assignment-revision-mismatch",
                "field": "assignment_revision",
                "recovery": "Refresh from the current checked-in Planning assignment revision.",
            }
        )
    if _optional_text(planning_assignment.get("status") or "current") in {"superseded", "closed", "archived"}:
        failures.append(
            {
                "reason": "assignment-not-current",
                "field": "planning_assignment_ref.status",
                "recovery": "Reassign or reopen a current Planning assignment before continuing.",
            }
        )
    proof_ref = _optional_text(planning_assignment.get("aw_proof_receipt_ref") or planning_assignment.get("proof_receipt_ref"))
    proof_receipt = _read_assignment_json_ref(
        target_root=target_root,
        ref=proof_ref,
        field="planning_assignment_ref.aw_proof_receipt_ref",
        failures=failures,
    )
    live_mutation_baseline = _assignment_live_mutation_baseline(target_root=target_root)
    if not live_mutation_baseline:
        failures.append(
            {
                "reason": "missing-current-authority",
                "field": "live_mutation_baseline",
                "recovery": "Record an AW mutation baseline file or run inside a Git checkout before admission.",
            }
        )
    run_state = _assignment_current_run_state(run_id=run_id, state=state, planning_assignment=planning_assignment)
    return {
        "assignment_gate": assignment_gate,
        "assignment_policy": assignment_policy,
        "delegation_decision": delegation_decision,
        "aw_proof_receipt": proof_receipt,
        "live_mutation_baseline": live_mutation_baseline,
        "run_state": run_state,
        "planning_assignment_ref": planning_assignment_ref,
        "proof_receipt_ref": proof_ref,
    }


def _assignment_planning_ref(*, values: Mapping[str, Any], assignment_id: str) -> str:
    return _optional_text(values.get("planning_assignment_ref") or values.get("assignment_ref")) or (
        f".agentic-workspace/planning/assignments/{_safe_assignment_fragment(assignment_id)}.assignment.json"
    )


def _read_assignment_json_ref(
    *, target_root: Path, ref: str, field: str, failures: list[dict[str, str]]
) -> dict[str, Any]:
    if not ref:
        failures.append(
            {
                "reason": "missing-current-authority",
                "field": field,
                "recovery": "Resolve the current AW-owned authority ref and retry.",
            }
        )
        return {}
    path = _resolve_inside(target_root, ref)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        failures.append(
            {
                "reason": "missing-current-authority",
                "field": field,
                "recovery": f"Create or refresh {ref} before continuing.",
            }
        )
        return {}
    return payload if isinstance(payload, dict) else {}


def _assignment_live_mutation_baseline(*, target_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=target_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        result = None
    if result is not None and result.returncode == 0:
        return result.stdout.strip()
    baseline_file = target_root / ".agentic-workspace/planning/mutation-baseline.json"
    try:
        payload = json.loads(baseline_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return _optional_text(payload.get("current_baseline") or payload.get("live_mutation_baseline") or payload.get("baseline"))


def _assignment_current_run_state(
    *, run_id: str, state: Mapping[str, Any], planning_assignment: Mapping[str, Any]
) -> dict[str, Any]:
    current_attempt = _assignment_mapping(planning_assignment.get("current_attempt"))
    if current_attempt and _optional_text(current_attempt.get("run_id")) not in {"", run_id}:
        return {"status": "superseded", "run_id": run_id, "current_run_id": current_attempt.get("run_id")}
    status = _optional_text(state.get("current_state")) or _optional_text(current_attempt.get("status")) or "awaiting-admission"
    return {"status": status, "run_id": run_id, "owner": current_attempt.get("owner")}


def _assignment_identity(current_authorities: Mapping[str, Any]) -> dict[str, Any]:
    assignment_gate = _assignment_mapping(current_authorities.get("assignment_gate"))
    assignment_policy = _assignment_mapping(current_authorities.get("assignment_policy"))
    delegation_decision = _assignment_mapping(current_authorities.get("delegation_decision"))
    scope = _assignment_mapping(assignment_gate.get("scope"))
    next_step = _assignment_mapping(delegation_decision.get("delegation_next_step"))
    proof_obligation = _assignment_mapping(assignment_gate.get("proof_obligation") or next_step.get("proof_obligation"))
    manual_transport_policy = _assignment_mapping(assignment_policy.get("manual_transport_policy"))
    identity: dict[str, Any] = {
        "target": assignment_gate.get("selected_target"),
        "target_identity_ref": assignment_gate.get("target_identity_ref") or assignment_gate.get("selected_target"),
        "target_revision": assignment_gate.get("target_revision"),
        "task_class": assignment_gate.get("task_class"),
        "scope_class": assignment_gate.get("scope_class") or scope.get("scope_class"),
        "plan_ref": assignment_gate.get("plan_ref") or next_step.get("plan_ref"),
        "plan_revision": assignment_gate.get("plan_revision") or next_step.get("plan_revision"),
        "slice_id": assignment_gate.get("slice_id") or next_step.get("slice_id"),
        "slice_revision": assignment_gate.get("slice_revision") or next_step.get("slice_revision"),
        "required_next_action": assignment_gate.get("required_next_action"),
        "gate_status": assignment_gate.get("status"),
        "assignment_policy": assignment_gate.get("assignment_policy"),
        "assignment_decision_revision": assignment_gate.get("assignment_decision_revision"),
        "manual_transport_policy": str(manual_transport_policy.get("value") or "allowed"),
        "delegation_decision": delegation_decision.get("decision"),
        "handoff_run_id": next_step.get("handoff_run_id"),
        "role": next_step.get("role") or assignment_gate.get("role"),
        "allowed_effects": _assignment_list(assignment_gate.get("allowed_effects") or next_step.get("allowed_effects")),
        "allowed_paths": _assignment_list(
            assignment_gate.get("allowed_paths") or scope.get("allowed_paths") or next_step.get("allowed_paths")
        ),
        "return_schema": next_step.get("return_schema") or "delegated-return/v1",
        "proof_obligation_id": proof_obligation.get("id"),
        "proof_obligation_revision": proof_obligation.get("revision"),
        "stop_conditions": _assignment_list(assignment_gate.get("stop_conditions") or next_step.get("stop_conditions")),
        "mutation_baseline": assignment_gate.get("mutation_baseline") or next_step.get("mutation_baseline"),
        "return_admission_owner": "delegated-return.admit",
    }
    required_fields = [
        "target",
        "target_identity_ref",
        "target_revision",
        "task_class",
        "scope_class",
        "plan_ref",
        "plan_revision",
        "slice_id",
        "slice_revision",
        "assignment_decision_revision",
        "handoff_run_id",
        "role",
        "allowed_effects",
        "allowed_paths",
        "return_schema",
        "proof_obligation_id",
        "proof_obligation_revision",
        "stop_conditions",
        "mutation_baseline",
    ]
    missing = [field for field in required_fields if not _assignment_identity_field_present(identity.get(field))]
    identity["complete"] = not missing
    identity["missing_required_fields"] = missing
    identity["revision"] = _assignment_digest(identity)
    return identity


def _assignment_admit_with_current_authority(*, current_authorities: Mapping[str, Any], returned_work: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(current_authorities, Mapping) or not current_authorities:
        return {
            "admitted": False,
            "status": "blocked",
            "failures": [
                {
                    "reason": "missing-current-authority",
                    "field": "state.current_authorities",
                    "recovery": "Run assignment export from the current Planning assignment before admission.",
                }
            ],
        }
    failures: list[dict[str, str]] = []
    for field in ("assignment_gate", "assignment_policy", "delegation_decision", "aw_proof_receipt"):
        value = current_authorities.get(field)
        if not isinstance(value, Mapping) or not value:
            failures.append(
                {
                    "reason": "missing-current-authority",
                    "field": f"current_authorities.{field}",
                    "recovery": "Resolve the current assignment/run/proof/baseline authorities and retry admission.",
                }
            )
    identity = _assignment_identity(current_authorities)
    if not identity.get("complete"):
        failures.append(
            {
                "reason": "incomplete-assignment-identity",
                "field": "assignment_identity",
                "recovery": "Regenerate the assignment with all required identity fields.",
            }
        )
    mutation_baseline = _optional_text(current_authorities.get("live_mutation_baseline") or current_authorities.get("mutation_baseline"))
    if not mutation_baseline:
        failures.append(
            {
                "reason": "missing-current-authority",
                "field": "current_authorities.live_mutation_baseline",
                "recovery": "Resolve the current assignment/run/proof/baseline authorities and retry admission.",
            }
        )
    current_proof = _assignment_mapping(current_authorities.get("aw_proof_receipt") or current_authorities.get("proof_receipt"))
    if current_proof.get("result") != "passed" or current_proof.get("verified_by") != "aw":
        failures.append(
            {
                "reason": "aw-proof-missing-or-not-passed",
                "field": "current_authorities.aw_proof_receipt",
                "recovery": "Run AW-owned proof and record the current receipt before admission.",
            }
        )
    run_state = _assignment_mapping(current_authorities.get("run_state"))
    if _optional_text(run_state.get("status")) in {"duplicate", "malformed", "superseded", "closed"}:
        failures.append(
            {
                "reason": "return-run-not-awaiting-admission",
                "field": "current_authorities.run_state",
                "recovery": "Import a fresh return or route repair/reassignment.",
            }
        )
    if _optional_text(returned_work.get("assignment_revision")) != _optional_text(identity.get("revision")):
        failures.append(
            {
                "reason": "stale-assignment-revision",
                "field": "assignment_revision",
                "recovery": "Refresh the handoff and resubmit against the current assignment revision.",
            }
        )
    if _optional_text(returned_work.get("target")) and _optional_text(returned_work.get("target")) != _optional_text(
        identity.get("target")
    ):
        failures.append(
            {
                "reason": "target-mismatch",
                "field": "target",
                "recovery": "Return work from the selected assignment target only.",
            }
        )
    if mutation_baseline and mutation_baseline != _optional_text(identity.get("mutation_baseline")):
        failures.append(
            {
                "reason": "mutation-baseline-mismatch",
                "field": "live_mutation_baseline",
                "recovery": "Rebase or regenerate the returned work against the current baseline.",
            }
        )
    allowed_paths = set(_assignment_list(identity.get("allowed_paths")))
    changed_paths = _assignment_list(returned_work.get("changed_paths"))
    if not allowed_paths:
        failures.append(
            {
                "reason": "missing-canonical-scope",
                "field": "assignment_identity.allowed_paths",
                "recovery": "Refresh the assignment so AW can compare returned paths.",
            }
        )
    for changed_path in changed_paths:
        if changed_path not in allowed_paths:
            failures.append(
                {
                    "reason": "scope-escape",
                    "field": "changed_paths",
                    "recovery": "Repair returned work to stay inside the assigned scope.",
                }
            )
    admitted = not failures
    return {
        "admitted": admitted,
        "status": "admitted" if admitted else "rejected",
        "failures": failures,
        "assignment_revision": identity.get("revision"),
        "assignment_identity": identity,
        "current_authority": {
            "planning_assignment": current_authorities.get("planning_assignment_ref"),
            "proof_receipt": current_proof or None,
            "proof_source": current_authorities.get("proof_receipt_ref"),
            "mutation_baseline": mutation_baseline,
            "baseline_source": "host-resolved:git-or-aw-baseline",
        },
        "rule": "Returned delegated work is executable only after AW re-resolves current assignment/run identity, transport authority, canonical scope, AW-owned proof, stop conditions, and baseline immediately before admission.",
    }


def _assignment_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _assignment_list(value: Any) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [str(item) for item in value if str(item)]
    return []


def _assignment_identity_field_present(value: Any) -> bool:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return bool(value)
    return bool(_optional_text(value))


def _assignment_failures_from_admission(admission: Mapping[str, Any]) -> list[dict[str, str]]:
    failures = admission.get("failures") if isinstance(admission, Mapping) else []
    result: list[dict[str, str]] = []
    if isinstance(failures, Sequence) and not isinstance(failures, (str, bytes)):
        for failure in failures:
            if not isinstance(failure, Mapping):
                continue
            result.append(
                {
                    "reason": _optional_text(failure.get("reason")) or "admission-failed",
                    "field": _optional_text(failure.get("field")) or "assignment.admit",
                    "recovery": _optional_text(failure.get("recovery")) or "Repair the returned work and retry assignment admit.",
                }
            )
    if result:
        return result
    return [
        {
            "reason": "admission-failed",
            "field": "assignment.admit",
            "recovery": "Repair the returned work and retry assignment admit.",
        }
    ]


def _assignment_return_for_state(*, state: Mapping[str, Any], target_root: Path, run_dir: Path, return_id: str) -> dict[str, Any]:
    returns = state.get("returns") if isinstance(state.get("returns"), Mapping) else {}
    entry = returns.get(return_id) if isinstance(returns, Mapping) else None
    if not isinstance(entry, Mapping):
        return {}
    artifact_ref = _optional_text(entry.get("artifact_ref"))
    if not artifact_ref:
        return {}
    path = (target_root / artifact_ref).resolve()
    try:
        path.relative_to(run_dir)
    except ValueError:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _optional_text(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _safe_assignment_fragment(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip(".-")
    return text or "assignment-run"


def _assignment_default_run_id(*, assignment_id: str, assignment_revision: str, transition: str) -> str:
    seed = f"{assignment_id}:{assignment_revision}:{transition}" if assignment_id or assignment_revision else transition
    return f"run-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def _assignment_json_value(value: Any, *, field: str) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = _optional_text(value)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise PrimitiveExecutionError(f"assignment lifecycle {field} must be valid JSON") from exc


def _assignment_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _assignment_relative(path: Path, *, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise PrimitiveExecutionError(f"assignment artifact escaped target root: {path}") from exc


def _read_assignment_state(*, state_path: Path) -> dict[str, Any]:
    if not state_path.is_file():
        return {}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrimitiveExecutionError(f"assignment run state is unreadable: {state_path}") from exc
    if not isinstance(payload, dict):
        raise PrimitiveExecutionError("assignment run state must be a JSON object")
    return payload


def _write_assignment_artifact(*, path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        text = payload
    else:
        text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _assignment_export_prompt(packet: Any) -> str:
    return "\n".join(
        [
            "You are receiving an Agentic Workspace assignment packet.",
            "Use only the bounded scope and return contract in the JSON below.",
            "Return a structured result for `agentic-workspace assignment import`; do not claim AW proof or integration.",
            "",
            "```json",
            json.dumps(packet, indent=2, sort_keys=True, default=str),
            "```",
        ]
    )


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
    if isinstance(result, dict) and result.get("kind") == "planning-module-report/v1" and result.get("profile") == "tiny":
        return _emit_planning_module_report_text(result)
    if isinstance(result, dict) and result.get("kind") == "agentic-workspace/defaults-router/v1":
        return _emit_tiny_sectioned_text(result)
    if isinstance(result, dict) and result.get("kind") == "agentic-workspace/selected-output/v1":
        return _emit_selected_output_text(result)
    if isinstance(result, dict) and result.get("kind") == "agentic-workspace/delegation-outcomes/v1":
        return _emit_delegation_outcomes_text(result)
    if isinstance(result, dict) and values.get("operation_id") == "defaults.report" and values.get("verbose"):
        return _emit_defaults_verbose_text(result)
    if not isinstance(result, dict):
        return f"{result}\n"
    if isinstance(result.get("files"), list) and all(isinstance(item, str) for item in result["files"]):
        return "\n".join(result["files"]).rstrip() + "\n"
    lines = [str(result.get("message", ""))]
    for action in _list_of_objects(result.get("actions", []), source="result.actions"):
        label = action.get("path") or action.get("id") or action.get("kind")
        lines.append(f"- {label}")
    return "\n".join(lines).rstrip() + "\n"


def _plain_output_result(result: Any) -> Any:
    if isinstance(result, Path):
        return str(result)
    if isinstance(result, Mapping):
        return {str(key): _plain_output_result(value) for key, value in result.items()}
    if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
        return [_plain_output_result(value) for value in result]
    to_dict = getattr(result, "to_dict", None)
    if callable(to_dict):
        return _plain_output_result(to_dict())
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


def _emit_tiny_sectioned_text(result: dict[str, Any]) -> str:
    lines = [str(result.get("summary", ""))]
    common_sections = result.get("common_sections", [])
    if isinstance(common_sections, list) and common_sections:
        lines.append("Common sections:")
        for section in common_sections:
            lines.append(f"- {section}")
    detail_commands = result.get("detail_commands", {})
    if isinstance(detail_commands, Mapping):
        lines.append("Detail commands:")
        for key, value in detail_commands.items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines).rstrip() + "\n"


def _emit_selected_output_text(result: dict[str, Any]) -> str:
    lines = [
        f"Kind: {result.get('kind', '')}",
        f"Source command: {result.get('source_command', '')}",
        "Values:",
        json.dumps(result.get("values", {}), indent=2),
    ]
    missing = result.get("missing", [])
    if isinstance(missing, list) and missing:
        lines.append("Missing:")
        for item in missing:
            lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def _emit_delegation_outcomes_text(result: dict[str, Any]) -> str:
    recorded = result.get("recorded", {})
    lines = [
        f"Kind: {result.get('kind', '')}",
        f"Path: {result.get('path', '.agentic-workspace/delegation-outcomes.json')}",
        f"Record count: {result.get('record_count', 1)}",
        f"Rule: {result.get('rule', 'local-only delegation outcome evidence')}",
    ]
    if isinstance(recorded, Mapping) and recorded:
        lines.append("Recorded:")
        for key in (
            "recorded_at",
            "delegation_target",
            "task_class",
            "outcome",
            "handoff_sufficiency",
            "review_burden",
            "escalation_required",
        ):
            if key in recorded:
                lines.append(f"- {key}: {recorded[key]}")
    return "\n".join(lines).rstrip() + "\n"


def _emit_defaults_verbose_text(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for section, value in result.items():
        if lines:
            lines.append("")
        lines.append(f"{_display_label(section, title=True)}:")
        _append_structured_text(lines, value, indent=2)
    return "\n".join(lines).rstrip() + "\n"


def _append_structured_text(lines: list[str], value: Any, *, indent: int) -> None:
    prefix = " " * indent
    if isinstance(value, Mapping):
        for key, nested in value.items():
            label = _display_label(str(key))
            if isinstance(nested, Mapping):
                if "command" in nested and "field" in nested:
                    lines.append(f"{prefix}{label}: {nested['command']} -> {nested['field']}")
                    remaining = {item_key: item_value for item_key, item_value in nested.items() if item_key not in {"command", "field"}}
                    _append_structured_text(lines, remaining, indent=indent + 2)
                    continue
                lines.append(f"{prefix}{label}:")
                _append_structured_text(lines, nested, indent=indent + 2)
            elif isinstance(nested, list):
                lines.append(f"{prefix}{label}:")
                _append_structured_text(lines, nested, indent=indent + 2)
            else:
                lines.append(f"{prefix}{label}: {nested}")
        return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                if "mode" in item and "summary" in item:
                    lines.append(f"{prefix}- {item['mode']}: {item['summary']}")
                    remaining = {key: nested for key, nested in item.items() if key not in {"mode", "summary"}}
                    _append_structured_text(lines, remaining, indent=indent + 2)
                    continue
                lines.append(f"{prefix}-")
                _append_structured_text(lines, item, indent=indent + 2)
            elif isinstance(item, list):
                lines.append(f"{prefix}-")
                _append_structured_text(lines, item, indent=indent + 2)
            else:
                lines.append(f"{prefix}- {item}")
        return
    lines.append(f"{prefix}{value}")


def _display_label(value: str, *, title: bool = False) -> str:
    if value == "mixed_agent":
        return "Mixed-agent" if title else "mixed-agent"
    if value == "operational_follow_through":
        return "Delegated judgment follow-through"
    if value in {"confirmed_intent", "interpreted_intent"}:
        value = value.removesuffix("_intent")
    label = value.replace("_", " ")
    return label[:1].upper() + label[1:] if title else label


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
