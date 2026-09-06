from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
import time
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from agentic_workspace.assignment_lifecycle import (
    assignment_task_proof_binding,
    delegated_return_owner_packet,
    load_indexed_assignment_task_proof,
)
from agentic_workspace.proof_receipt_admission import proof_receipt_admission


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
    if primitive == "independent-review.admission.apply":
        return _independent_review_admission_apply(values=values, arguments=arguments, context=context)
    if primitive == "correction.event.apply":
        return _correction_event_apply(values=values, arguments=arguments, context=context)
    if primitive == "guidance.lifecycle.apply":
        return _guidance_lifecycle_apply(values=values, arguments=arguments, context=context)
    if primitive == "instructions.execute":
        return _instructions_execute(values=values, arguments=arguments, context=context)
    if primitive == "config.policy.apply":
        from agentic_workspace.workspace_runtime_core import _apply_workspace_config_policy

        return _apply_workspace_config_policy(values, arguments, context)
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


def _assignment_lifecycle_decision_state(state: Mapping[str, Any]) -> dict[str, Any]:
    current_attempt = _assignment_mapping(state.get("current_attempt"))
    projection: dict[str, Any] = {
        "schema_version": "agentic-workspace/assignment-lifecycle-decision-state/v1",
        "current_state": _optional_text(state.get("current_state")) or "unknown",
    }
    for field in ("assignment_id", "run_id", "last_return_id", "last_admission_status"):
        value = _optional_text(state.get(field))
        if value:
            projection[field] = value
    if current_attempt:
        projection["current_attempt"] = {
            field: current_attempt[field] for field in ("run_id", "target", "status") if _optional_text(current_attempt.get(field))
        }
    return projection


def _assignment_lifecycle_apply(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    del arguments
    operation_id = str(values.get("operation_id") or "")
    transition = str(values.get("assignment_command") or operation_id.rsplit(".", 1)[-1])
    supported = {
        "dispatch",
        "export",
        "import",
        "admit",
        "reject",
        "repair",
        "reassign",
        "integrate",
        "status",
        "close",
        "cleanup",
        "override",
    }
    if transition not in supported:
        raise PrimitiveExecutionError(f"unsupported assignment lifecycle transition: {transition!r}")
    target_root = Path(str(values.get("target_root") or values.get("target") or context.cwd)).resolve()
    local_root = _resolve_inside(target_root, ".agentic-workspace/local/assignment-runs")
    dry_run = bool(values.get("dry_run", False))

    assignment_id = _optional_text(values.get("assignment_id"))
    assignment_revision = _optional_text(values.get("assignment_revision"))
    if transition in {"dispatch", "export"} and not assignment_id:
        from agentic_workspace import config as config_lib
        from agentic_workspace.workspace_runtime_core import _execution_posture_payload

        raw_changed = values.get("changed_paths", values.get("changed", []))
        changed_paths = _assignment_list(raw_changed) if not isinstance(raw_changed, str) else [raw_changed]
        posture = _execution_posture_payload(
            config=config_lib.load_workspace_config(target_root=target_root),
            changed_paths=changed_paths,
            task_text=_optional_text(values.get("task")),
            target_root=target_root,
            materialize_assignment=True,
        )
        materialization = _assignment_mapping(posture.get("assignment_materialization"))
        assignment_id = _optional_text(materialization.get("assignment_id"))
        assignment_revision = _optional_text(materialization.get("assignment_revision"))
        if assignment_id:
            values = {
                **values,
                "assignment_id": assignment_id,
                "assignment_revision": assignment_revision,
                "run_id": materialization.get("run_id"),
                "target_name": _assignment_mapping(posture.get("assignment_gate")).get("selected_target"),
            }
    supplied_run_id = _optional_text(values.get("run_id"))
    if not supplied_run_id and assignment_id:
        planning_ref = _assignment_planning_ref(values=values, assignment_id=assignment_id)
        try:
            planning_assignment = json.loads(_resolve_inside(target_root, planning_ref).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            planning_assignment = {}
        if isinstance(planning_assignment, dict):
            supplied_run_id = _optional_text(_assignment_mapping(planning_assignment.get("current_attempt")).get("run_id"))
    run_id = supplied_run_id or _assignment_default_run_id(
        assignment_id=assignment_id, assignment_revision=assignment_revision, transition=transition
    )
    run_dir = _resolve_inside(local_root, _safe_assignment_fragment(run_id))
    state_path = _resolve_inside(run_dir, "state.json")
    state = _read_assignment_state(state_path=state_path)
    artifact_paths: list[Path] = []
    failures: list[dict[str, str]] = []
    writes: dict[Path, Any] = {}

    if transition == "status":
        resolved_assignment_id = assignment_id or _optional_text(state.get("assignment_id"))
        planning_assignment: dict[str, Any] = {}
        planning_ref = ""
        if resolved_assignment_id:
            planning_ref = _assignment_planning_ref(values=values, assignment_id=resolved_assignment_id)
            try:
                loaded_assignment = json.loads(_resolve_inside(target_root, planning_ref).read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                loaded_assignment = {}
            planning_assignment = _assignment_mapping(loaded_assignment)
        current_attempt = _assignment_mapping(planning_assignment.get("current_attempt"))
        current_run_id = _optional_text(current_attempt.get("run_id"))
        state_exists = state_path.is_file()
        if not state_exists and not planning_assignment:
            failures.append(
                {
                    "reason": "assignment-run-not-found",
                    "field": "assignment_id|run_id",
                    "recovery": "Re-resolve the current assignment decision, or retry with its exact assignment id and run id.",
                }
            )
        currentness = (
            "current"
            if current_run_id == run_id
            else "stale"
            if current_run_id
            else "historical-detail-not-retained"
            if planning_assignment and not state_exists
            else "unknown"
        )
        lifecycle_state = _optional_text(state.get("current_state")) or _optional_text(current_attempt.get("status")) or "unknown"
        integration_path = _resolve_inside(run_dir, "integration/integration.json")
        try:
            integration_receipt = _assignment_mapping(json.loads(integration_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            integration_receipt = {}
        admission_status = _optional_text(state.get("last_admission_status")) or (
            "admitted" if lifecycle_state in {"admitted", "integrated", "closed", "archived"} else "pending"
        )
        integration_status = _optional_text(integration_receipt.get("status")) or (
            "integrated" if lifecycle_state in {"integrated", "closed", "archived"} else "pending"
        )
        effective_revision = (
            assignment_revision
            or _optional_text(planning_assignment.get("current_revision"))
            or _optional_text(_assignment_mapping(_assignment_mapping(state.get("assignment")).get("assignment_identity")).get("revision"))
        )
        result = {
            "kind": "agentic-workspace/assignment-lifecycle-result/v1",
            "operation_id": operation_id,
            "transition": transition,
            "status": "blocked" if failures else lifecycle_state,
            "outcome": "blocked" if failures else "noop",
            "mutation_applied": False,
            "target_root": target_root.as_posix(),
            "run_id": run_id,
            "assignment_id": resolved_assignment_id or None,
            "assignment_revision": effective_revision or None,
            "return_id": _optional_text(state.get("last_return_id")) or None,
            "artifact_refs": [
                ref
                for ref in (
                    _assignment_relative(state_path, root=target_root) if state_exists else "",
                    planning_ref if planning_assignment else "",
                    _assignment_relative(integration_path, root=target_root) if integration_receipt else "",
                )
                if ref
            ],
            "state_ref": _assignment_relative(state_path, root=target_root) if state_exists else None,
            "state": _assignment_lifecycle_decision_state(
                {
                    **state,
                    "current_state": lifecycle_state,
                    "assignment_id": resolved_assignment_id,
                    "run_id": run_id,
                    "current_attempt": current_attempt,
                }
            ),
            "inspection": {
                "currentness": currentness,
                "retention": "retained" if state_exists else "historical-detail-not-retained",
                "admission": admission_status,
                "integration": integration_status,
                "proof": "required"
                if integration_status == "integrated" and lifecycle_state not in {"closed", "archived"}
                else "not-pending",
                "completion_permission": lifecycle_state in {"closed", "archived"},
            },
            "stale": currentness == "stale",
            "currentness_owner": planning_ref or "assignment-lifecycle",
            "replacement_action": "query-current-assignment-run" if currentness == "stale" else None,
            "failures": failures,
            "reason_code": failures[0]["reason"] if failures else None,
            "recovery_command": failures[0]["recovery"] if failures else None,
            "message": f"assignment status: {'blocked' if failures else lifecycle_state}",
            "actions": [],
        }
        from agentic_workspace.orchestration import reconcile_action_result

        result["next_current_continuation"] = reconcile_action_result(result=result)
        return result

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

    if transition == "admit" and (values.get("review_result_json") or values.get("review_result") or values.get("review_result_ref")):
        admission = _independent_review_admission_apply(values=values, arguments={}, context=context)
        admitted = bool(admission.get("admitted"))
        admission_failures = admission.get("failures") or []
        return {
            "kind": "agentic-workspace/assignment-lifecycle-result/v1",
            "operation_id": "assignment.admit",
            "transition": "admit",
            "status": str(admission.get("status") or ""),
            "outcome": "applied" if admitted else "blocked",
            "mutation_applied": admitted,
            "run_id": run_id,
            "artifact_refs": [str(admission.get("store") or "")] if admission.get("store") else [],
            "state": {
                "schema_version": "agentic-workspace/assignment-lifecycle-decision-state/v1",
                "current_state": str(admission.get("status") or "blocked"),
                "run_id": run_id,
            },
            "state_ref": str(admission.get("store") or "") or None,
            "failures": admission_failures,
            "reason_code": ""
            if admitted
            else str((admission_failures or [{"reason": "independent-review-admission-rejected"}])[0].get("reason")),
            "recovery_command": "assignment admit --review-result-json <json> --changed <path> --format json"
            if not admission.get("admitted")
            else None,
        }

    if transition in {"dispatch", "export"}:
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
        target_name = _optional_text(values.get("target_name")) or _optional_text(identity.get("target"))
        if not target_name:
            require("target_name")
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
                "structural_proof_receipt": current_authorities.get("proof_receipt_ref"),
                "mutation_baseline": "host-resolved:git-or-aw-baseline",
            },
            "dispatch_contract": {
                "transport": _optional_text(values.get("transport")) or "manual",
                "adapter_authority": "execution-only",
                "semantic_authority": "assignment_identity",
                "dispatch_input": "this exact packet",
                "silent_local_fallback_allowed": False,
            },
            "return_contract": {
                "kind": "agentic-workspace/delegated-return/v1",
                "required_fields": [
                    "assignment_revision",
                    "run_id",
                    "target",
                    "changed_paths",
                    "summary",
                    "stop_conditions_hit",
                ]
                + (["patch"] if identity.get("role") == "implementer" else []),
                "admission_operation": "assignment.import then assignment.admit",
                "result_delivery": {
                    "field": "result_delivery",
                    "modes": ["unapplied-patch", "already-materialized"],
                    "default": "unapplied-patch",
                    "already_materialized_requires": ["mutation_baseline"],
                },
                "worker_proof_authority": False,
                "worker_completion_authority": False,
                "rule": "Import records evidence in received/awaiting-admission; AW-owned admission, integration, proof, and closeout remain pending.",
            },
        }
        canonical_packet = current_authorities.get("replacement_packet")
        if canonical_packet:
            from agentic_workspace.assignment_source import source_facts
            from agentic_workspace.decision import admit_assignment_packet

            try:
                admission, execution = source_facts(target_root)
                current = admit_assignment_packet(
                    {
                        "packet": canonical_packet,
                        "canonical": canonical_packet,
                        "source": admission["source"],
                        "execution": execution,
                        "work": {"id": identity["slice_id"], "revision": identity["plan_revision"]},
                    }
                )
                if current["status"] != "current":
                    raise ValueError(current["reason_code"])
                if (
                    target_name != canonical_packet["target"]
                    or packet["transport"] != canonical_packet["transport"]
                    or run_id != canonical_packet["run_id"]
                ):
                    raise ValueError("assignment-replacement-intention-mismatch")
                packet = canonical_packet
            except (ValueError, OSError) as error:
                failures.append(
                    {
                        "reason": str(error),
                        "field": "assignment.replacement",
                        "recovery": "Reconcile the current replacement source; do not use the previous target or local execution.",
                    }
                )
        else:
            packet["worker_context"] = _assignment_worker_context(packet)
        transport = _optional_text(values.get("transport")) or "manual"
        dispatch_configuration = _assignment_dispatch_configuration(identity=identity, transport=transport)
        if not canonical_packet and dispatch_configuration["kind"] == "host-native" and not dispatch_configuration["command"]:
            packet = _assignment_seal_host_native_packet(packet)
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
            "integrity": _optional_text(packet.get("packet_integrity")) or _assignment_digest(packet),
            "worker_context_integrity": _assignment_digest(packet.get("worker_context") or _assignment_worker_context(packet)),
        }
        artifact_paths.extend([packet_path, prompt_path, manifest_path])
        if not canonical_packet and transition == "dispatch" and transport == "manual":
            failures.append(
                {
                    "reason": "automatic-transport-required",
                    "field": "transport",
                    "recovery": "Use assignment export for manual handoff or retry dispatch with an authorized automatic transport.",
                }
            )
        state.update(
            {
                "assignment": packet,
                "planning_assignment_ref": current_authorities.get("planning_assignment_ref"),
                "structural_proof_receipt_ref": current_authorities.get("proof_receipt_ref"),
                "current_state": "handoff-prepared",
                "run_id": run_id,
                "assignment_id": assignment_id,
            }
        )
        writes = {packet_path: packet, prompt_path: prompt, manifest_path: manifest}
        if transition == "dispatch" and transport != "manual" and not failures:
            dispatch = _dispatch_assignment_packet(
                packet=packet,
                prompt=prompt,
                target_root=target_root,
                transport=transport,
            )
            dispatch_path = artifact("dispatch/receipt.json")
            artifact_paths.append(dispatch_path)
            writes[dispatch_path] = dispatch
            returned = dispatch.get("returned_work") if isinstance(dispatch.get("returned_work"), dict) else {}
            if dispatch.get("status") == "host-execution-required":
                state.update(
                    {
                        "current_state": "awaiting-host-execution",
                        "host_execution": dispatch.get("execution_contract"),
                    }
                )
            elif dispatch.get("status") != "returned" or not returned:
                failures.append(
                    {
                        "reason": str(dispatch.get("reason") or "automatic-dispatch-failed"),
                        "field": "transport",
                        "recovery": "Repair the configured target adapter or export the same packet through an admitted manual transport.",
                        "detail": _optional_text(dispatch.get("stderr")) or _optional_text(dispatch.get("stdout_tail")),
                    }
                )
            else:
                required_return_fields = (
                    "assignment_revision",
                    "run_id",
                    "target",
                    "changed_paths",
                    "summary",
                    "stop_conditions_hit",
                ) + (("patch",) if identity.get("role") == "implementer" else ())
                missing_return_fields = [field for field in required_return_fields if field not in returned]
                if missing_return_fields:
                    failures.append(
                        {
                            "reason": "malformed-return",
                            "field": "returned_work." + ",".join(missing_return_fields),
                            "recovery": "Repair the configured target adapter so it returns every required contract field.",
                        }
                    )
                returned_changed_paths = returned.get("changed_paths")
                patch_text = str(returned.get("patch") or "")
                if identity.get("role") == "implementer" and bool(returned_changed_paths) and not patch_text.strip():
                    failures.append(
                        {
                            "reason": "malformed-return",
                            "field": "returned_work.patch",
                            "recovery": "Repair the configured target adapter so implementer returns include a non-empty unified diff.",
                        }
                    )
                elif identity.get("role") == "implementer" and patch_text.strip():
                    if not _assignment_patch_paths(patch_text):
                        failures.append(
                            {
                                "reason": "malformed-return",
                                "field": "returned_work.patch",
                                "recovery": "Repair the configured target adapter so the patch is a complete git-compatible unified diff.",
                            }
                        )
                    else:
                        patch_check = subprocess.run(
                            ["git", "apply", "--check", "-"],
                            cwd=target_root,
                            input=patch_text,
                            text=True,
                            capture_output=True,
                            check=False,
                        )
                        if patch_check.returncode != 0:
                            failures.append(
                                {
                                    "reason": "malformed-return",
                                    "field": "returned_work.patch",
                                    "recovery": "Repair the configured target adapter so the patch applies cleanly to the current checkout.",
                                    "detail": _optional_text(patch_check.stderr),
                                }
                            )
                if returned.get("assignment_revision") != assignment_revision:
                    failures.append(
                        {
                            "reason": "return-revision-mismatch",
                            "field": "returned_work.assignment_revision",
                            "recovery": "Return work for the exported assignment revision only.",
                        }
                    )
                if returned.get("run_id") != run_id or returned.get("target") != target_name:
                    failures.append(
                        {
                            "reason": "return-identity-mismatch",
                            "field": "returned_work.run_id|target",
                            "recovery": "Return work for the exported run and selected target only.",
                        }
                    )
                if failures:
                    returned = {}
            if returned:
                return_id = _assignment_digest(returned).removeprefix("sha256:")[:16]
                return_path = artifact(f"received/awaiting-admission/{return_id}.json")
                artifact_paths.append(return_path)
                writes[return_path] = returned
                state.update(
                    {
                        "current_state": "awaiting-admission",
                        "last_return_id": return_id,
                        "returns": {
                            return_id: {
                                "artifact_ref": _assignment_relative(return_path, root=target_root),
                                "integrity": _assignment_digest(returned),
                                "state": "received/awaiting-admission",
                            }
                        },
                    }
                )
    elif transition == "import":
        require("run_id")
        returned = _assignment_import_return_value(values=values, target_root=target_root, failures=failures)
        if not isinstance(returned, dict):
            failures.append(
                {
                    "reason": "malformed-return",
                    "field": "return_json",
                    "recovery": "Return one JSON object matching the exported return contract.",
                }
            )
            returned = {}
        assignment = _assignment_mapping(state.get("assignment"))
        assignment_identity = _assignment_mapping(assignment.get("assignment_identity"))
        required_return_fields = (
            "assignment_revision",
            "run_id",
            "target",
            "changed_paths",
            "summary",
            "stop_conditions_hit",
        ) + (("patch",) if assignment_identity.get("role") == "implementer" else ())
        if assignment.get("replacement") or _assignment_mapping(state.get("host_execution")).get("result_delivery_required"):
            required_return_fields += ("assignment_id", "packet_integrity", "result_delivery")
        missing_return_fields = [field for field in required_return_fields if field not in returned]
        if missing_return_fields:
            failures.append(
                {
                    "reason": "malformed-return",
                    "field": "return_json." + ",".join(missing_return_fields),
                    "recovery": "Return every required field from the exported return contract.",
                }
            )
        if (
            assignment_identity.get("role") == "implementer"
            and bool(returned.get("changed_paths"))
            and not str(returned.get("patch") or "").strip()
        ):
            failures.append(
                {
                    "reason": "malformed-return",
                    "field": "return_json.patch",
                    "recovery": "Return a non-empty unified diff for an implementer assignment.",
                }
            )
        if returned.get("run_id") != run_id:
            failures.append(
                {
                    "reason": "return-run-mismatch",
                    "field": "return_json.run_id",
                    "recovery": "Return work for the exported assignment run only.",
                }
            )
        if not isinstance(returned.get("changed_paths"), list) or not isinstance(returned.get("stop_conditions_hit"), list):
            failures.append(
                {
                    "reason": "malformed-return",
                    "field": "return_json.changed_paths|stop_conditions_hit",
                    "recovery": "Return changed_paths and stop_conditions_hit as JSON arrays.",
                }
            )
        return_id = _optional_text(values.get("return_id")) or _assignment_digest(returned).removeprefix("sha256:")[:16]
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
        owner_packet = delegated_return_owner_packet(admission=admission)
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
            "owner_packet": owner_packet,
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
                "last_owner_packet": owner_packet,
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
        patch_text = str(returned.get("patch") or "")
        result_delivery = _assignment_mapping(returned.get("result_delivery"))
        delivery_mode = _optional_text(result_delivery.get("mode")) or "unapplied-patch"
        changed_paths = _assignment_list(returned.get("changed_paths"))
        mutation_baseline = _optional_text(result_delivery.get("mutation_baseline")) or _optional_text(
            _assignment_mapping(admission.get("current_authority")).get("mutation_baseline")
        )
        integration_receipt_path = artifact("integration/integration.json")
        return_integrity = _assignment_digest(returned)
        prior_integration: dict[str, Any] = {}
        if integration_receipt_path.is_file():
            try:
                loaded_prior_integration = json.loads(integration_receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded_prior_integration = {}
            prior_integration = _assignment_mapping(loaded_prior_integration)
        replayed = bool(
            prior_integration.get("status") == "integrated"
            and prior_integration.get("run_id") == run_id
            and prior_integration.get("return_id") == return_id
            and prior_integration.get("return_integrity") == return_integrity
        )
        if prior_integration.get("status") == "integrated" and not replayed:
            failures.append(
                {
                    "reason": "assignment-integration-replay-mismatch",
                    "field": "integration.receipt",
                    "recovery": "Reconcile or supersede the prior integrated return before integrating different work.",
                }
            )
        materialized_verified = False
        if admitted and patch_text and not dry_run and not failures:
            integration_patch_path = artifact("integration/returned.patch")
            integration_patch_path.parent.mkdir(parents=True, exist_ok=True)
            integration_patch_path.write_bytes(_normalize_assignment_patch_transport(patch_text).encode("utf-8"))
            artifact_paths.append(integration_patch_path)
            already_materialized = delivery_mode == "already-materialized"
            apply_patch: subprocess.CompletedProcess[bytes] | None = None
            if not already_materialized and not replayed:
                try:
                    apply_patch = subprocess.run(
                        ["git", "apply", "--recount", str(integration_patch_path)],
                        cwd=target_root,
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                except (OSError, subprocess.SubprocessError):
                    apply_patch = None
            if not already_materialized and not replayed and (apply_patch is None or apply_patch.returncode != 0):
                failures.append(
                    {
                        "reason": "assignment-patch-apply-failed",
                        "field": "returned_work.patch",
                        "recovery": "Repair the returned unified diff against the current mutation baseline and retry integration.",
                        "detail": _optional_text(apply_patch.stderr.decode("utf-8", errors="replace") if apply_patch is not None else "")[
                            -2000:
                        ],
                    }
                )
            if not failures and (already_materialized or replayed):
                materialized_verified, verification_detail = _verify_materialized_assignment_delta(
                    target_root=target_root,
                    mutation_baseline=mutation_baseline,
                    patch_path=integration_patch_path,
                    changed_paths=changed_paths,
                )
                if not materialized_verified:
                    failures.append(
                        {
                            "reason": "assignment-materialized-delta-mismatch",
                            "field": "returned_work.patch|changed_paths|result_delivery.mutation_baseline",
                            "recovery": "Restore the exact bounded baseline-plus-patch bytes before integrating or replaying this return.",
                            "detail": verification_detail,
                        }
                    )
        receipt_path = integration_receipt_path
        receipt = {
            "kind": "agentic-workspace/assignment-integration-receipt/v1",
            "run_id": run_id,
            "return_id": return_id,
            "status": "integrated" if admitted and not failures else "blocked",
            "admission": admission,
            "integration_disposition": (
                "blocked"
                if failures
                else (
                    "already-integrated"
                    if replayed
                    else (
                        "verified-already-materialized"
                        if _optional_text(_assignment_mapping(returned.get("result_delivery")).get("mode")) == "already-materialized"
                        else "applied-returned-patch"
                    )
                )
            ),
            "result_delivery_mode": _optional_text(_assignment_mapping(returned.get("result_delivery")).get("mode")) or "unapplied-patch",
            "changed_paths": changed_paths,
            "mutation_baseline": mutation_baseline,
            "materialized_delta_verified": materialized_verified,
            "return_integrity": return_integrity,
            "patch_integrity": _assignment_digest({"patch": patch_text}),
            "replayed": replayed,
        }
        artifact_paths.append(receipt_path)
        state.update({"current_state": receipt["status"]})
        writes = {receipt_path: receipt}
    elif transition == "reassign":
        from agentic_workspace.assignment_source import replace_from_source, source_facts

        try:
            source_facts(target_root)
        except (ValueError, OSError) as error:
            failures.append(
                {
                    "reason": "assignment-override-authority-unavailable",
                    "field": "host.assignment_override_admission",
                    "recovery": str(error),
                }
            )

        assignment_id = assignment_id or _optional_text(state.get("assignment_id"))
        authorities = _assignment_current_authorities_from_store(
            target_root=target_root,
            assignment_id=assignment_id,
            assignment_revision=assignment_revision,
            run_id=run_id,
            state=state,
            values=values,
            failures=failures,
            replacing=True,
        )
        prior = _assignment_mapping(state.get("assignment"))
        if prior.get("assignment_identity") != _assignment_identity(authorities):
            failures.append(
                {
                    "reason": "assignment-revision-mismatch",
                    "field": "assignment_revision",
                    "recovery": "Resolve the exact current assignment packet before replacement.",
                }
            )
        if not failures:
            try:
                result = replace_from_source(
                    target_root,
                    prior,
                    {"id": prior["assignment_identity"]["slice_id"], "revision": prior["assignment_identity"]["plan_revision"]},
                    {"assignment_revision": assignment_revision, "target": values.get("target_name"), "transport": values.get("transport")},
                )
            except (ValueError, OSError, KeyError) as error:
                result = {"status": "blocked", "reason_code": str(error)}
            if result["status"] != "replaced":
                failures.append(
                    {
                        "reason": result["reason_code"],
                        "field": "host.assignment_override_admission",
                        "recovery": "Resolve the current local-config owner replacement answer; command fields cannot supply authority.",
                    }
                )
            else:
                packet = _assignment_mapping(result.get("packet"))
                from agentic_workspace.assignment_source import current_replacement

                try:
                    current_replacement(target_root, packet, packet["replacement"]["work"])
                except (ValueError, OSError) as error:
                    failures.append(
                        {
                            "reason": str(error),
                            "field": "host.assignment_override_admission",
                            "recovery": "Refresh the source-owner answer before replacement.",
                        }
                    )
                canonical_path = _resolve_inside(target_root, authorities["planning_assignment_ref"])
                canonical = json.loads(canonical_path.read_text(encoding="utf-8-sig"))
                if canonical.get("current_revision") != prior["assignment_revision"]:
                    failures.append(
                        {
                            "reason": "assignment-revision-mismatch",
                            "field": "assignment_revision",
                            "recovery": "Resolve the new current assignment before replacing it.",
                        }
                    )
                canonical["replacement_packet"] = packet
                canonical["current_revision"] = packet["assignment_revision"]
                canonical["target_name"] = packet["target"]
                canonical["assignment_gate"] = {
                    **canonical["assignment_gate"],
                    "selected_target": packet["target"],
                    "target_identity_ref": packet["assignment_identity"]["target_identity_ref"],
                    "target_revision": packet["assignment_identity"]["target_revision"],
                    "assignment_decision_revision": packet["assignment_revision"],
                    "dispatch_adapter": packet["assignment_identity"]["dispatch_adapter"],
                    "status": packet["assignment_identity"]["gate_status"],
                    "required_next_action": packet["assignment_identity"]["required_next_action"],
                    "implementation_allowed": result["implementation_allowed"],
                    "executor_disposition": {"transport": packet["transport"]},
                }
                obligation = canonical["assignment_gate"].get("proof_obligation", {})
                canonical["assignment_gate"]["proof_obligation"] = {
                    **obligation,
                    "revision": packet["assignment_identity"]["proof_obligation_revision"],
                    "subject": {**obligation.get("subject", {}), "run_id": packet["run_id"]},
                }
                canonical["current_attempt"] = {"run_id": packet["run_id"], "owner": packet["target"], "status": "selected"}
                proof_path = _resolve_inside(target_root, authorities["proof_receipt_ref"])
                proof = dict(authorities["structural_proof_receipt"])
                proof["assignment_revision"] = packet["assignment_revision"]
                # Existing owner paths only. The old packet and run stay intact.
                writes = {proof_path: proof, canonical_path: canonical}
                artifact_paths.extend(writes)
                state = {**state, "current_state": "superseded"}
    elif transition == "override":
        failures.append(
            {
                "reason": "assignment-override-authority-unavailable",
                "field": "host.assignment_override_admission",
                "recovery": "Only exact source-owner replacement is constructible; caller fields cannot grant override authority.",
            }
        )
    else:
        require("run_id")
        prior_state = _optional_text(state.get("current_state"))
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
        if transition == "close":
            close_assignment_id = assignment_id or _optional_text(state.get("assignment_id"))
            planning_ref = _assignment_planning_ref(values=values, assignment_id=close_assignment_id)
            planning_assignment = _read_assignment_json_ref(
                target_root=target_root,
                ref=planning_ref,
                field="planning_assignment_ref",
                failures=failures,
            )
            current_attempt = _assignment_mapping(planning_assignment.get("current_attempt"))
            if prior_state != "integrated":
                failures.append(
                    {
                        "reason": "assignment-run-not-integrated",
                        "field": "state.current_state",
                        "recovery": "Admit and integrate the current return before closing the assignment.",
                    }
                )
            if current_attempt and _optional_text(current_attempt.get("run_id")) not in {"", run_id}:
                failures.append(
                    {
                        "reason": "return-run-mismatch",
                        "field": "planning_assignment_ref.current_attempt.run_id",
                        "recovery": "Close only the current assignment run.",
                    }
                )
            task_proof_ref = require("task_proof_receipt_ref")
            task_proof = load_indexed_assignment_task_proof(target_root=target_root, receipt_ref=task_proof_ref)
            if not task_proof:
                failures.append(
                    {
                        "reason": "assignment-task-proof-not-producer-owned",
                        "field": "task_proof_receipt_ref",
                        "recovery": "Supply the current proof:// receipt resolved through the AW proof producer index.",
                    }
                )
            task_proof_admission = proof_receipt_admission(task_proof) if task_proof else {"admitted": False}
            expected_obligation = _assignment_mapping(
                _assignment_mapping(planning_assignment.get("assignment_gate")).get("proof_obligation")
            )
            observed_obligation = _assignment_mapping(task_proof.get("assignment_proof_obligation"))
            if not task_proof_admission.get("admitted") or not task_proof_admission.get("proof_sufficient"):
                failures.append(
                    {
                        "reason": "assignment-task-proof-not-admitted",
                        "field": "task_proof_receipt_ref",
                        "recovery": "Run AW proof for the integrated assignment and supply its admitted passed receipt.",
                    }
                )
            if not expected_obligation or observed_obligation != expected_obligation:
                failures.append(
                    {
                        "reason": "assignment-proof-obligation-mismatch",
                        "field": "task_proof_receipt_ref.assignment_proof_obligation",
                        "recovery": "Supply the passed AW proof receipt sealed for this exact assignment obligation.",
                    }
                )
            if task_proof.get("assignment_proof_binding") != assignment_task_proof_binding(task_proof):
                failures.append(
                    {
                        "reason": "assignment-proof-binding-mismatch",
                        "field": "task_proof_receipt_ref.assignment_proof_binding",
                        "recovery": "Record proof through AW for this exact integrated assignment and retry close.",
                    }
                )
            expected_paths = set(_assignment_list(_assignment_mapping(planning_assignment.get("assignment_gate")).get("allowed_paths")))
            proved_paths = set(_assignment_list(task_proof.get("changed_paths")))
            proof_subject = _assignment_mapping(task_proof.get("proof_subject"))
            try:
                integration_receipt = _assignment_mapping(json.loads(artifact("integration/integration.json").read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                integration_receipt = {}
            integrated_paths = set(_assignment_list(integration_receipt.get("changed_paths")))
            integration_current = (
                integration_receipt.get("kind") == "agentic-workspace/assignment-integration-receipt/v1"
                and integration_receipt.get("status") == "integrated"
                and _optional_text(integration_receipt.get("run_id")) == run_id
            )
            if (
                not expected_paths
                or not proved_paths
                or not integration_current
                or proof_subject.get("identity_complete") is not True
                or any(not _assignment_path_allowed(path, expected_paths) for path in proved_paths)
                or not integrated_paths.issubset(proved_paths)
            ):
                failures.append(
                    {
                        "reason": "assignment-proof-scope-mismatch",
                        "field": "task_proof_receipt_ref.changed_paths",
                        "recovery": "Record complete proof for every concrete integrated path within the assignment's allowed scope.",
                    }
                )
            if planning_assignment and not failures:
                planning_path = _resolve_inside(target_root, planning_ref)
                planning_assignment["status"] = "closed"
                planning_assignment["current_attempt"] = {**current_attempt, "status": "closed"}
                planning_assignment["closeout"] = {
                    "run_id": run_id,
                    "receipt_ref": _assignment_relative(receipt_path, root=target_root),
                    "task_proof_receipt_ref": task_proof_ref,
                    "claim_authority": "orchestrator-after-current-proof-and-closeout",
                }
                writes[planning_path] = planning_assignment
                artifact_paths.append(planning_path)
            elif failures:
                state["current_state"] = prior_state
                receipt["status"] = "blocked"

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
    state_ref = _assignment_relative(state_path, root=target_root) if state_path.is_file() or outcome == "applied" else None
    effective_assignment_revision = assignment_revision or _optional_text(
        _assignment_mapping(_assignment_mapping(state.get("assignment")).get("assignment_identity")).get("revision")
    )
    result = {
        "kind": "agentic-workspace/assignment-lifecycle-result/v1",
        "operation_id": operation_id,
        "transition": transition,
        "status": status,
        "outcome": outcome,
        "mutation_applied": outcome == "applied",
        "target_root": target_root.as_posix(),
        "run_id": run_id,
        "assignment_id": assignment_id or _optional_text(state.get("assignment_id")) or None,
        "assignment_revision": effective_assignment_revision or None,
        "return_id": _optional_text(state.get("last_return_id")) or None,
        "artifact_refs": artifact_refs,
        "state_ref": state_ref,
        "state": _assignment_lifecycle_decision_state(state),
        "failures": failures,
        "reason_code": failures[0]["reason"] if failures else None,
        "recovery_command": failures[0]["recovery"] if failures else None,
        "message": f"assignment {transition}: {status}",
        "actions": [{"kind": "write", "path": ref} for ref in artifact_refs],
    }
    from agentic_workspace.orchestration import reconcile_action_result

    result["next_current_continuation"] = reconcile_action_result(result=result)
    if transition == "reassign" and failures and prior:
        from agentic_workspace.assignment_source import replacement_offer

        try:
            result["required_source_answer"] = replacement_offer(
                target_root, prior, str(values.get("target_name") or ""), str(values.get("transport") or "")
            )
        except (ValueError, OSError, KeyError):
            pass
    if transition == "reassign" and not failures:
        result["status"] = "replaced"
        result["replacement_packet"] = packet
        result["next_current_continuation"] = {
            "status": "actionable",
            "owner": "assignment-lifecycle",
            "action": "export-current-replacement",
            "operation_invocation": {
                "operation_id": "assignment.export",
                "arguments": {
                    "assignment_id": packet["assignment_id"],
                    "assignment_revision": packet["assignment_revision"],
                    "run_id": packet["run_id"],
                    "target_name": packet["target"],
                    "transport": packet["transport"],
                },
            },
            "implementation_allowed": False,
            "silent_local_fallback_allowed": False,
        }
    return result


def _assignment_current_authorities_from_store(
    *,
    target_root: Path,
    assignment_id: str,
    assignment_revision: str,
    run_id: str,
    state: Mapping[str, Any],
    values: Mapping[str, Any],
    failures: list[dict[str, str]],
    replacing: bool = False,
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
    if "replacement_packet" in planning_assignment:
        identity = dict(planning_assignment["replacement_packet"]["assignment_identity"])
        from agentic_workspace.assignment_source import current_replacement

        try:
            if not replacing:
                current_replacement(
                    target_root,
                    planning_assignment["replacement_packet"],
                    {"id": assignment_gate.get("slice_id"), "revision": assignment_gate.get("plan_revision")},
                )
        except (ValueError, OSError) as error:
            failures.append(
                {
                    "reason": str(error),
                    "field": "assignment.replacement",
                    "recovery": "Reconcile current source-owner admission before continuation; no previous-target fallback.",
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
    proof_ref = _optional_text(planning_assignment.get("structural_proof_receipt_ref"))
    structural_proof_receipt = _read_assignment_json_ref(
        target_root=target_root,
        ref=proof_ref,
        field="planning_assignment_ref.structural_proof_receipt_ref",
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
        **({"replacement_packet": planning_assignment["replacement_packet"]} if "replacement_packet" in planning_assignment else {}),
        "assignment_gate": assignment_gate,
        "assignment_policy": assignment_policy,
        "delegation_decision": delegation_decision,
        "structural_proof_receipt": structural_proof_receipt,
        "live_mutation_baseline": live_mutation_baseline,
        "run_state": run_state,
        "planning_assignment_ref": planning_assignment_ref,
        "proof_receipt_ref": proof_ref,
    }


def _assignment_planning_ref(*, values: Mapping[str, Any], assignment_id: str) -> str:
    return _optional_text(values.get("planning_assignment_ref") or values.get("assignment_ref")) or (
        f".agentic-workspace/planning/assignments/{_safe_assignment_fragment(assignment_id)}.assignment.json"
    )


def _read_assignment_json_ref(*, target_root: Path, ref: str, field: str, failures: list[dict[str, str]]) -> dict[str, Any]:
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
            encoding="utf-8",
            errors="replace",
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


def _assignment_current_run_state(*, run_id: str, state: Mapping[str, Any], planning_assignment: Mapping[str, Any]) -> dict[str, Any]:
    current_attempt = _assignment_mapping(planning_assignment.get("current_attempt"))
    if current_attempt and _optional_text(current_attempt.get("run_id")) not in {"", run_id}:
        return {"status": "superseded", "run_id": run_id, "current_run_id": current_attempt.get("run_id")}
    status = _optional_text(state.get("current_state")) or _optional_text(current_attempt.get("status")) or "awaiting-admission"
    host_execution = _assignment_mapping(state.get("host_execution"))
    replacement = _assignment_mapping(planning_assignment.get("replacement_packet"))
    return {
        "status": status,
        "run_id": run_id,
        "owner": current_attempt.get("owner"),
        "result_delivery_required": bool(replacement or host_execution.get("result_delivery_required")),
        "assignment_id": replacement.get("assignment_id", host_execution.get("assignment_id")),
        "packet_integrity": replacement.get("packet_integrity", host_execution.get("packet_integrity")),
    }


def _verify_materialized_assignment_delta(
    *, target_root: Path, mutation_baseline: str, patch_path: Path, changed_paths: Sequence[str]
) -> tuple[bool, str]:
    """Verify that bounded worktree bytes equal applying patch_path to mutation_baseline."""

    baseline_check = subprocess.run(
        ["git", "rev-parse", "--verify", f"{mutation_baseline}^{{commit}}"],
        cwd=target_root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if baseline_check.returncode != 0:
        return False, baseline_check.stderr.decode("utf-8", errors="replace")[-2000:]
    try:
        with tempfile.TemporaryDirectory(prefix="aw-assignment-baseline-") as temporary_directory:
            expected_root = Path(temporary_directory)
            for changed_path in changed_paths:
                expected_path = _resolve_inside(expected_root, changed_path)
                baseline_file = subprocess.run(
                    ["git", "show", f"{mutation_baseline}:{changed_path}"],
                    cwd=target_root,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                if baseline_file.returncode == 0:
                    expected_path.parent.mkdir(parents=True, exist_ok=True)
                    baseline_entry = subprocess.run(
                        ["git", "ls-tree", mutation_baseline, "--", changed_path],
                        cwd=target_root,
                        capture_output=True,
                        check=False,
                        text=True,
                        timeout=30,
                    )
                    baseline_mode = baseline_entry.stdout.split(" ", 1)[0]
                    if baseline_mode == "120000":
                        os.symlink(baseline_file.stdout.decode("utf-8", errors="surrogateescape"), expected_path)
                    elif baseline_mode in {"100644", "100755"}:
                        expected_path.write_bytes(baseline_file.stdout)
                        if baseline_mode == "100755":
                            expected_path.chmod(expected_path.stat().st_mode | 0o111)
                    else:
                        return False, f"unsupported baseline object mode for {changed_path}: {baseline_mode}"
            apply_check = subprocess.run(
                ["git", "apply", "--check", "--recount", str(patch_path)],
                cwd=expected_root,
                capture_output=True,
                check=False,
                timeout=60,
            )
            if apply_check.returncode != 0:
                return False, apply_check.stderr.decode("utf-8", errors="replace")[-2000:]
            apply_patch = subprocess.run(
                ["git", "apply", "--recount", str(patch_path)],
                cwd=expected_root,
                capture_output=True,
                check=False,
                timeout=60,
            )
            if apply_patch.returncode != 0:
                return False, apply_patch.stderr.decode("utf-8", errors="replace")[-2000:]
            for changed_path in changed_paths:
                expected_path = _resolve_inside(expected_root, changed_path)
                observed_path = _resolve_inside(target_root, changed_path)
                expected_type = "symlink" if expected_path.is_symlink() else "file" if expected_path.is_file() else "missing"
                observed_type = "symlink" if observed_path.is_symlink() else "file" if observed_path.is_file() else "missing"
                if expected_type != observed_type:
                    return False, f"materialized path type differs from baseline-plus-patch: {changed_path}"
                if expected_type == "symlink" and os.readlink(expected_path) != os.readlink(observed_path):
                    return False, f"materialized symlink target differs from baseline-plus-patch: {changed_path}"
                if expected_type == "file" and bool(expected_path.stat().st_mode & 0o111) != bool(observed_path.stat().st_mode & 0o111):
                    return False, f"materialized path executable mode differs from baseline-plus-patch: {changed_path}"
                if expected_path.is_file():
                    expected_hash = subprocess.run(
                        ["git", "hash-object", f"--path={changed_path}", str(expected_path)],
                        cwd=target_root,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    observed_hash = subprocess.run(
                        ["git", "hash-object", f"--path={changed_path}", str(observed_path)],
                        cwd=target_root,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    if expected_hash.returncode != 0 or observed_hash.returncode != 0 or expected_hash.stdout != observed_hash.stdout:
                        return False, f"materialized path content differs from baseline-plus-patch: {changed_path}"
    except (OSError, subprocess.SubprocessError, PrimitiveExecutionError) as exc:
        return False, str(exc)[-2000:]
    return True, ""


def _assignment_identity(current_authorities: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(current_authorities.get("replacement_packet"), Mapping):
        return dict(current_authorities["replacement_packet"]["assignment_identity"])
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
        "human_intent": assignment_gate.get("human_intent")
        or next_step.get("human_intent")
        or assignment_gate.get("task")
        or assignment_gate.get("task_class"),
        "required_inputs": _assignment_list(assignment_gate.get("required_inputs") or next_step.get("required_inputs")),
        "read_first": _assignment_list(assignment_gate.get("read_first") or next_step.get("read_first")),
        "prohibited_effects": _assignment_list(assignment_gate.get("prohibited_effects") or next_step.get("prohibited_effects"))
        or ["scope-widening", "merge", "closeout", "proof-authority", "human-authority"],
        "dispatch_adapter": _assignment_mapping(assignment_gate.get("dispatch_adapter")),
        "claim_authority": {
            "worker_result": "evidence-only",
            "proof": "orchestrator-owned",
            "integration": "orchestrator-owned",
            "completion": "orchestrator-owned",
        },
    }
    required_fields = [
        "target",
        "target_identity_ref",
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
    for field in ("assignment_gate", "assignment_policy", "delegation_decision", "structural_proof_receipt"):
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
    structural_proof = _assignment_mapping(current_authorities.get("structural_proof_receipt"))
    if (
        structural_proof.get("kind") != "agentic-workspace/assignment-structural-proof-receipt/v1"
        or structural_proof.get("result") != "passed"
        or structural_proof.get("verified_by") != "aw"
        or _optional_text(structural_proof.get("assignment_revision")) != _optional_text(identity.get("revision"))
    ):
        failures.append(
            {
                "reason": "assignment-structural-proof-missing-or-stale",
                "field": "current_authorities.structural_proof_receipt",
                "recovery": "Prepare the current assignment again so AW can seal its structural identity.",
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
    if _optional_text(returned_work.get("target")) != _optional_text(identity.get("target")):
        failures.append(
            {
                "reason": "target-mismatch",
                "field": "target",
                "recovery": "Return work from the selected assignment target only.",
            }
        )
    if _optional_text(returned_work.get("run_id")) != _optional_text(run_state.get("run_id")):
        failures.append(
            {
                "reason": "return-run-mismatch",
                "field": "run_id",
                "recovery": "Return work for the current assignment run only.",
            }
        )
    if run_state.get("result_delivery_required"):
        if _optional_text(returned_work.get("assignment_id")) != _optional_text(run_state.get("assignment_id")):
            failures.append(
                {
                    "reason": "host-execution-contract-mismatch",
                    "field": "assignment_id",
                    "recovery": "Return the assignment id from the sealed host execution contract.",
                }
            )
        if _optional_text(returned_work.get("packet_integrity")) != _optional_text(run_state.get("packet_integrity")):
            failures.append(
                {
                    "reason": "host-execution-contract-mismatch",
                    "field": "packet_integrity",
                    "recovery": "Return the packet integrity from the sealed host execution contract.",
                }
            )
    stop_conditions_hit = _assignment_list(returned_work.get("stop_conditions_hit"))
    if stop_conditions_hit:
        failures.append(
            {
                "reason": "stop-condition-hit",
                "field": "stop_conditions_hit",
                "recovery": "Route the reported stop condition before integration.",
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
    patch_text = str(returned_work.get("patch") or "")
    changed_paths = _assignment_list(returned_work.get("changed_paths"))
    result_delivery = _assignment_mapping(returned_work.get("result_delivery"))
    delivery_mode = _optional_text(result_delivery.get("mode")) or "unapplied-patch"
    if run_state.get("result_delivery_required") and not result_delivery:
        failures.append(
            {
                "reason": "missing-result-delivery",
                "field": "result_delivery",
                "recovery": "Declare whether the host result is an unapplied patch or already materialized in the shared worktree.",
            }
        )
    if delivery_mode not in {"unapplied-patch", "already-materialized"}:
        failures.append(
            {
                "reason": "unsupported-result-delivery",
                "field": "result_delivery.mode",
                "recovery": "Return either an unapplied patch or an explicitly baseline-bound already-materialized result.",
            }
        )
    if delivery_mode == "already-materialized" and _optional_text(result_delivery.get("mutation_baseline")) != _optional_text(
        identity.get("mutation_baseline")
    ):
        failures.append(
            {
                "reason": "result-delivery-baseline-mismatch",
                "field": "result_delivery.mutation_baseline",
                "recovery": "Return the exact pre-dispatch mutation baseline sealed by the current assignment.",
            }
        )
    if identity.get("role") == "implementer" and changed_paths and not patch_text.strip():
        failures.append(
            {
                "reason": "missing-implementation-patch",
                "field": "patch",
                "recovery": "Return the proposed unified diff required by the implementer assignment contract.",
            }
        )
    patch_paths = _assignment_patch_paths(patch_text) if patch_text else []
    if delivery_mode == "already-materialized" and set(patch_paths) != set(changed_paths):
        failures.append(
            {
                "reason": "result-delivery-scope-mismatch",
                "field": "result_delivery|changed_paths|patch",
                "recovery": "Return the exact bounded changed-path set represented by the already-materialized patch.",
            }
        )
    allowed_paths = set(_assignment_list(identity.get("allowed_paths")))
    if patch_paths and any(not _assignment_path_allowed(path, allowed_paths) for path in patch_paths):
        failures.append(
            {
                "reason": "returned-patch-outside-assignment-scope",
                "field": "patch",
                "recovery": "Return a unified diff touching only the assignment's allowed paths.",
            }
        )
    allowed_paths = set(_assignment_list(identity.get("allowed_paths")))
    if not allowed_paths:
        failures.append(
            {
                "reason": "missing-canonical-scope",
                "field": "assignment_identity.allowed_paths",
                "recovery": "Refresh the assignment so AW can compare returned paths.",
            }
        )
    for changed_path in changed_paths:
        if not _assignment_path_allowed(changed_path, allowed_paths):
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
            "structural_proof_receipt": structural_proof or None,
            "proof_source": current_authorities.get("proof_receipt_ref"),
            "mutation_baseline": mutation_baseline,
            "baseline_source": "host-resolved:git-or-aw-baseline",
        },
        "rule": "Returned delegated work is executable only after AW re-resolves current assignment/run identity, transport authority, canonical scope, AW-owned proof, stop conditions, and baseline immediately before admission.",
    }


def _assignment_path_allowed(path: str, allowed_paths: set[str]) -> bool:
    normalized = _assignment_canonical_relative_path(path)
    if not normalized:
        return False
    for raw_pattern in allowed_paths:
        pattern = _assignment_canonical_relative_path(raw_pattern)
        if not pattern:
            continue
        if normalized == pattern:
            return True
        expression: list[str] = []
        offset = 0
        while offset < len(pattern):
            character = pattern[offset]
            if character == "*" and offset + 1 < len(pattern) and pattern[offset + 1] == "*":
                expression.append(".*")
                offset += 2
                continue
            expression.append("[^/]*" if character == "*" else "[^/]" if character == "?" else re.escape(character))
            offset += 1
        if re.fullmatch("".join(expression), normalized):
            return True
    return False


def _assignment_canonical_relative_path(value: object) -> str:
    normalized = str(value or "").replace("\\", "/")
    if (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
        or "\x00" in normalized
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
    ):
        return ""
    return normalized


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


def _assignment_import_return_value(*, values: Mapping[str, Any], target_root: Path, failures: list[dict[str, Any]]) -> Any:
    inline_return = _optional_text(values.get("return_json"))
    return_file = _optional_text(values.get("return_file"))
    if bool(inline_return) == bool(return_file):
        failures.append(
            {
                "reason": "return-input-required",
                "field": "return_json|return_file",
                "recovery": "Provide exactly one inline return_json or repo-contained return_file.",
            }
        )
        return {}
    if inline_return:
        return _assignment_json_value(inline_return, field="return_json")
    try:
        path = (target_root / return_file).resolve()
        path.relative_to(target_root.resolve())
        payload = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise PrimitiveExecutionError("assignment lifecycle return_file must be a readable repo-contained UTF-8 file") from exc
    return _assignment_json_value(payload, field="return_file")


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
    # Preserve a complete current owner record if local replacement is interrupted.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(text.rstrip() + "\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _assignment_export_prompt(packet: Any) -> str:
    packet_mapping = _assignment_mapping(packet)
    worker_context = _assignment_mapping(packet_mapping.get("worker_context")) or _assignment_worker_context(packet_mapping)
    delivery_mode = (
        _optional_text(
            _assignment_mapping(_assignment_mapping(worker_context.get("return_contract")).get("result_delivery")).get("default")
        )
        or "unapplied-patch"
    )
    delivery_instruction = (
        "The selected result delivery mode is `already-materialized`: edit only the assigned shared worktree paths, and return the exact baseline-relative unified diff plus its sealed mutation baseline."
        if delivery_mode == "already-materialized"
        else "The selected result delivery mode is `unapplied-patch`: do not edit the target checkout; return the proposed unified diff in a `patch` field."
    )
    required_identity = _assignment_mapping(_assignment_mapping(worker_context.get("return_contract")).get("required_identity"))
    identity_instruction = (
        "Copy every value in `return_contract.required_identity` exactly and include the selected `result_delivery` mode."
        if required_identity
        else "Return every field named by `return_contract.required_fields` and include the selected `result_delivery` mode."
    )
    return "\n".join(
        [
            "You are receiving a bounded Agentic Workspace worker context.",
            "Use only the intent, scope, effects, inputs, proof burden, stop conditions, authority limits, and return contract below.",
            "Acquire deeper repository context only through the listed read-first references; omitted parent conversation and broad workspace state are not part of this assignment.",
            "Return a structured result for `agentic-workspace assignment import`; do not claim AW proof or integration.",
            delivery_instruction,
            identity_instruction,
            "The patch must be a complete git-compatible unified diff beginning with `diff --git`; generate or verify it with diff tooling so hunk counts are exact, and never use apply_patch markers, ellipses, placeholder `@@` markers, or omitted context.",
            "",
            "```json",
            json.dumps(worker_context, indent=2, sort_keys=True, default=str),
            "```",
        ]
    )


def _assignment_worker_context(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Project only worker-required semantics from canonical assignment authority."""

    identity = _assignment_mapping(packet.get("assignment_identity"))
    return_contract = _assignment_mapping(packet.get("return_contract"))
    return {
        "kind": "agentic-workspace/assignment-worker-context/v1",
        "assignment": {
            "id": _optional_text(packet.get("assignment_id")),
            "revision": _optional_text(packet.get("assignment_revision")) or _optional_text(identity.get("revision")),
            "run_id": _optional_text(packet.get("run_id")),
            "target": _optional_text(packet.get("target")) or _optional_text(identity.get("target")),
        },
        "intent": {
            "outcome": _optional_text(identity.get("human_intent")),
            "task_class": _optional_text(identity.get("task_class")),
            "role": _optional_text(identity.get("role")),
        },
        "scope": {
            "class": _optional_text(identity.get("scope_class")),
            "allowed_paths": _assignment_list(identity.get("allowed_paths")),
        },
        "effects": {
            "allowed": _assignment_list(identity.get("allowed_effects")),
            "prohibited": _assignment_list(identity.get("prohibited_effects")),
        },
        "inputs": {
            "required": _assignment_list(identity.get("required_inputs")),
            "read_first": _assignment_list(identity.get("read_first")),
            "lazy_expansion_rule": "Read only these exact references first; request or resolve deeper context only when the assignment requires it.",
        },
        "proof": {
            "obligation_id": _optional_text(identity.get("proof_obligation_id")),
            "obligation_revision": _optional_text(identity.get("proof_obligation_revision")),
            "worker_authority": False,
        },
        "stop_conditions": _assignment_list(identity.get("stop_conditions")),
        "authority": {
            "semantic_source": "canonical-assignment-identity",
            "claim_authority": _assignment_mapping(identity.get("claim_authority")),
            "scope_widening_allowed": False,
        },
        "return_contract": return_contract,
    }


def _assignment_dispatch_configuration(*, identity: Mapping[str, Any], transport: str) -> dict[str, Any]:
    adapter = _assignment_mapping(identity.get("dispatch_adapter"))
    variants = [item for item in adapter.get("transports", []) if isinstance(item, Mapping)]
    selected = next((item for item in variants if _optional_text(item.get("method")) == transport), None)
    selected_mapping = _assignment_mapping(selected)
    variant_kind = _optional_text(selected_mapping.get("kind"))
    kind = (
        "process"
        if variant_kind in {"process", "api"}
        else "host-native"
        if variant_kind == "internal"
        else _optional_text(adapter.get("kind"))
    )
    return {
        "admitted": transport in set(_assignment_list(adapter.get("execution_methods"))),
        "kind": kind,
        "command": (
            _assignment_list(selected_mapping.get("command")) if selected is not None else _assignment_list(adapter.get("command"))
        ),
        "output_mode": _optional_text(selected_mapping.get("output_mode")) or _optional_text(adapter.get("output_mode")) or "stdout",
        "timeout_seconds": selected_mapping.get("timeout_seconds", adapter.get("timeout_seconds", 1800)),
        "adapter": adapter,
    }


def _assignment_packet_integrity(packet: Mapping[str, Any]) -> str:
    subject = json.loads(json.dumps(packet, default=str))
    subject["packet_integrity"] = ""
    for contract in (
        _assignment_mapping(subject.get("return_contract")),
        _assignment_mapping(_assignment_mapping(subject.get("worker_context")).get("return_contract")),
    ):
        if isinstance(contract.get("required_identity"), dict):
            contract["required_identity"]["packet_integrity"] = ""
    return _assignment_digest(subject)


def _assignment_seal_host_native_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    sealed = json.loads(json.dumps(packet, default=str))
    return_contract = _assignment_mapping(sealed.get("return_contract"))
    return_contract["required_fields"] = list(
        dict.fromkeys([*_assignment_list(return_contract.get("required_fields")), "assignment_id", "packet_integrity", "result_delivery"])
    )
    return_contract["required_identity"] = {
        "assignment_id": sealed.get("assignment_id"),
        "assignment_revision": sealed.get("assignment_revision"),
        "run_id": sealed.get("run_id"),
        "target": sealed.get("target"),
        "packet_integrity": "",
    }
    sealed["return_contract"] = return_contract
    sealed["worker_context"] = _assignment_worker_context(sealed)
    integrity = _assignment_packet_integrity(sealed)
    sealed["packet_integrity"] = integrity
    sealed["return_contract"]["required_identity"]["packet_integrity"] = integrity
    sealed["worker_context"] = _assignment_worker_context(sealed)
    if _assignment_packet_integrity(sealed) != integrity:
        raise PrimitiveExecutionError("host-native assignment packet integrity did not stabilize")
    return sealed


def _dispatch_assignment_packet(*, packet: Mapping[str, Any], prompt: str, target_root: Path, transport: str) -> dict[str, Any]:
    """Execute a sealed packet through its configured adapter command.

    Adapters own transport only.  The packet remains semantic authority and
    the returned JSON remains untrusted until assignment admission.
    """

    identity = _assignment_mapping(packet.get("assignment_identity"))
    configuration = _assignment_dispatch_configuration(identity=identity, transport=transport)
    adapter = _assignment_mapping(configuration.get("adapter"))
    adapter_kind = _optional_text(configuration.get("kind"))
    command_template = _assignment_list(configuration.get("command"))
    output_mode = _optional_text(configuration.get("output_mode"))
    timeout_seconds = configuration.get("timeout_seconds", 1800)
    if not configuration.get("admitted"):
        return {
            "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
            "status": "blocked",
            "reason": "transport-not-admitted-by-target",
            "transport": transport,
            "adapter_kind": adapter_kind or None,
        }
    if adapter_kind == "host-native" and not command_template:
        host_return_contract = dict(_assignment_mapping(packet.get("return_contract")))
        packet_integrity = _optional_text(packet.get("packet_integrity"))
        required_identity = _assignment_mapping(host_return_contract.get("required_identity"))
        if (
            not packet_integrity
            or packet_integrity != _assignment_packet_integrity(packet)
            or required_identity.get("packet_integrity") != packet_integrity
        ):
            return {
                "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
                "status": "blocked",
                "reason": "host-native-packet-unsealed",
                "transport": transport,
                "adapter_kind": adapter_kind,
            }
        return {
            "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
            "status": "host-execution-required",
            "reason": "execute-canonical-assignment-with-host-native-transport",
            "transport": transport,
            "adapter_kind": adapter_kind,
            "execution_contract": {
                "kind": "agentic-workspace/host-native-assignment-execution/v1",
                "assignment_id": packet.get("assignment_id"),
                "assignment_revision": packet.get("assignment_revision") or identity.get("revision"),
                "run_id": packet.get("run_id"),
                "target": packet.get("target") or identity.get("target"),
                "packet_integrity": packet_integrity,
                "worker_context": packet.get("worker_context") or _assignment_worker_context(packet),
                "return_contract": host_return_contract,
                "reentry_operation": "assignment.import",
                "result_delivery_required": True,
            },
            "claim_boundary": "transport-only; host result still requires AW import, admission, integration, proof, and closeout",
        }
    if adapter_kind not in {"process", "host-native"} or not command_template:
        return {
            "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
            "status": "blocked",
            "reason": "configured-dispatch-adapter-unavailable",
            "transport": transport,
            "adapter_kind": adapter_kind or None,
        }
    if output_mode not in {"stdout", "json-file"}:
        return {
            "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
            "status": "blocked",
            "reason": "configured-dispatch-output-mode-unsupported",
            "transport": transport,
            "adapter_kind": adapter_kind,
        }
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
        return {
            "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
            "status": "blocked",
            "reason": "configured-dispatch-timeout-invalid",
            "transport": transport,
            "adapter_kind": adapter_kind,
        }
    role = _optional_text(identity.get("role"))
    model = _optional_text(adapter.get("model"))
    adapter_revision = _assignment_digest(
        {
            "kind": adapter_kind,
            "command": command_template,
            "output_mode": output_mode,
            "timeout_seconds": timeout_seconds,
        }
    )
    completed: subprocess.CompletedProcess[str]
    output = ""
    observed_metrics: dict[str, Any] = {}
    started_at = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="aw-assignment-dispatch-") as temporary_directory:
            last_message_path = Path(temporary_directory) / "last-message.json"
            output_schema_path = Path(temporary_directory) / "delegated-return.schema.json"
            metrics_path = Path(temporary_directory) / "transport-metrics.json"
            required_fields = [
                "assignment_revision",
                "run_id",
                "target",
                "changed_paths",
                "summary",
                "stop_conditions_hit",
            ]
            if role == "implementer":
                required_fields.append("patch")
            return_properties = {
                "assignment_revision": {"type": "string"},
                "run_id": {"type": "string"},
                "target": {"type": "string"},
                "changed_paths": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
                "stop_conditions_hit": {"type": "array", "items": {"type": "string"}},
                "result_delivery": {
                    "type": "object",
                    "properties": {
                        "mode": {"enum": ["unapplied-patch", "already-materialized"]},
                        "mutation_baseline": {"type": "string"},
                    },
                    "required": ["mode"],
                    "additionalProperties": False,
                },
            }
            if role == "implementer":
                return_properties["patch"] = {"type": "string"}
            for field in ("assignment_id", "packet_integrity"):
                if field in _assignment_mapping(packet.get("return_contract")).get("required_fields", []):
                    return_properties[field] = {"type": "string"}
                    required_fields.append(field)
            output_schema_path.write_text(
                json.dumps(
                    {
                        "type": "object",
                        "properties": return_properties,
                        "required": required_fields,
                        "additionalProperties": False,
                    }
                ),
                encoding="utf-8",
            )
            placeholders = {
                "{target_root}": str(target_root),
                "{output_schema}": str(output_schema_path),
                "{output_file}": str(last_message_path),
                "{metrics_file}": str(metrics_path),
                "{model}": model,
            }
            dispatch_command = []
            for template_part in command_template:
                rendered_part = template_part
                for placeholder, value in placeholders.items():
                    rendered_part = rendered_part.replace(placeholder, value)
                if rendered_part:
                    dispatch_command.append(rendered_part)
            completed = subprocess.run(
                dispatch_command,
                input=prompt,
                cwd=target_root,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
            output = (
                last_message_path.read_text(encoding="utf-8", errors="replace").strip()
                if output_mode == "json-file" and last_message_path.is_file()
                else completed.stdout.strip()
            )
            if metrics_path.is_file():
                try:
                    loaded_metrics = json.loads(metrics_path.read_text(encoding="utf-8", errors="replace"))
                except json.JSONDecodeError:
                    loaded_metrics = {}
                observed_metrics = _assignment_mapping(loaded_metrics)
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
            "status": "blocked",
            "reason": "target-adapter-execution-failed",
            "transport": transport,
            "adapter_kind": adapter_kind,
            "detail": str(exc),
            "context_cost": _assignment_context_cost(
                packet=packet,
                prompt=prompt,
                transport=transport,
                adapter_revision=adapter_revision,
                elapsed_ms=round((time.perf_counter() - started_at) * 1000),
            ),
        }
    if output.startswith("```json") and output.endswith("```"):
        output = output[7:-3].strip()
    try:
        returned = json.loads(output)
    except json.JSONDecodeError:
        returned = {}
    if completed.returncode != 0 or not isinstance(returned, dict):
        returned = {}
    if role == "implementer":
        reported_paths = _assignment_list(returned.get("changed_paths"))
        if reported_paths and not _optional_text(returned.get("patch")):
            returned = {}
    return {
        "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
        "status": "returned" if returned else "blocked",
        "reason": "worker-returned-untrusted-evidence" if returned else "target-adapter-return-invalid",
        "transport": transport,
        "adapter_kind": adapter_kind,
        "adapter_revision": adapter_revision,
        "model": model or None,
        "exit_code": completed.returncode,
        "returned_work": returned,
        "stdout_tail": completed.stdout[-4000:] if completed.stdout else "",
        "stderr": completed.stderr[-4000:] if completed.stderr else "",
        "context_cost": _assignment_context_cost(
            packet=packet,
            prompt=prompt,
            transport=transport,
            adapter_revision=adapter_revision,
            elapsed_ms=round((time.perf_counter() - started_at) * 1000),
            observed=observed_metrics,
        ),
        "claim_boundary": "transport-only; return still requires AW admission, integration, proof, and closeout",
    }


_ASSIGNMENT_CONTEXT_COST_METRICS = (
    "effective_input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "orientation_command_count",
    "retry_count",
    "repair_loop_count",
)


def _assignment_context_cost(
    *,
    packet: Mapping[str, Any],
    prompt: str,
    transport: str,
    adapter_revision: str,
    elapsed_ms: int,
    observed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    observed_mapping = _assignment_mapping(observed)
    if observed_mapping.get("kind") != "agentic-workspace/assignment-transport-metrics/v1":
        observed_mapping = {}
    metrics: dict[str, int | None] = {}
    for field in _ASSIGNMENT_CONTEXT_COST_METRICS:
        value = observed_mapping.get(field)
        metrics[field] = value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
    packet_text = json.dumps(packet, indent=2, sort_keys=True, default=str).rstrip() + "\n"
    return {
        "kind": "agentic-workspace/assignment-context-cost/v1",
        "transport": transport,
        "adapter_revision": adapter_revision,
        "assignment_packet_bytes": len(packet_text.encode("utf-8")),
        "rendered_prompt_bytes": len(prompt.encode("utf-8")),
        **metrics,
        "elapsed_ms": max(0, elapsed_ms),
        "unknown_fields": [field for field, value in metrics.items() if value is None],
        "observation_authority": "adapter-sidecar-or-host-measurement",
        "raw_transcript_stored": False,
    }


def _assignment_patch_paths(patch_text: str) -> list[str]:
    paths: set[str] = set()

    def add_path(raw_value: str) -> None:
        value = raw_value.split("\t", 1)[0].strip()
        if not value or value == "/dev/null":
            return
        try:
            parsed = shlex.split(value, posix=True)
        except ValueError:
            parsed = []
        if len(parsed) == 1:
            value = parsed[0]
        if value.startswith(("a/", "b/")):
            value = value[2:]
        if value:
            paths.add(value)

    for line in patch_text.splitlines():
        if line.startswith(("+++ ", "--- ")):
            add_path(line[4:])
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            add_path(line.split(" ", 2)[2])
        elif line.startswith("diff --git "):
            try:
                header = shlex.split(line, posix=True)
            except ValueError:
                header = []
            if len(header) == 4:
                add_path(header[2])
                add_path(header[3])
    return sorted(paths)


def _normalize_assignment_patch_transport(patch_text: str) -> str:
    """Normalize CRLF unified-diff transport only at the Git application boundary.

    Return identity, scope admission, and receipt integrity continue to use the
    original worker payload.  Git still validates every normalized hunk.
    """
    return patch_text.replace("\r\n", "\n")


def _correction_event_apply(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    target_root = Path(str(values.get("target_root") or values.get("target") or ".")).resolve()
    operation_id = str(values.get("operation_id") or arguments.get("operation_id") or "")
    try:
        from agentic_workspace.agent_guidance import apply_correction_event_operation

        return apply_correction_event_operation(target_root=target_root, operation_id=operation_id, values=values)
    except Exception as exc:  # pragma: no cover - surfaced as structured operation failure.
        return {
            "kind": "agentic-workspace/correction-event-operation-result/v1",
            "operation_id": operation_id or "correction-event.unknown",
            "status": "blocked",
            "mutation_applied": False,
            "failures": [
                {
                    "reason": "correction-event-operation-error",
                    "field": "correction-event",
                    "recovery": f"Repair correction event input or local store before retrying: {exc}",
                }
            ],
        }


def _guidance_lifecycle_apply(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    target_root = Path(str(values.get("target_root") or values.get("target") or ".")).resolve()
    operation_id = str(values.get("operation_id") or arguments.get("operation_id") or "")
    try:
        from agentic_workspace.agent_guidance import apply_guidance_lifecycle_operation

        return apply_guidance_lifecycle_operation(target_root=target_root, operation_id=operation_id, values=values)
    except Exception as exc:  # pragma: no cover - surfaced as structured operation failure.
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "operation_id": operation_id or "agent-guidance.unknown",
            "status": "blocked",
            "mutation_applied": False,
            "failures": [
                {
                    "reason": "guidance-lifecycle-operation-error",
                    "field": "agent-guidance",
                    "recovery": f"Repair guidance lifecycle input or local store before retrying: {exc}",
                }
            ],
        }


def _instructions_execute(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    del context
    target_root = Path(str(values.get("target_root") or values.get("target") or ".")).resolve()
    operation_id = str(values.get("operation_id") or arguments.get("operation_id") or "")
    from agentic_workspace.scoped_instructions import apply_instruction_operation

    return apply_instruction_operation(target_root=target_root, operation_id=operation_id, values=values)


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


def _independent_review_admission_apply(*, values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> dict[str, Any]:
    del arguments
    target_root = Path(str(values.get("target_root") or values.get("target") or context.cwd)).resolve()
    from agentic_workspace.workspace_runtime_proof import admit_independent_review_result_operation

    return admit_independent_review_result_operation(target_root=target_root, values=values)


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
