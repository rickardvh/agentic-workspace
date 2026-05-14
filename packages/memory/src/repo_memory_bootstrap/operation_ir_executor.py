from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any, cast

from agentic_command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, run_operation_steps

from repo_memory_bootstrap._installer_output import _new_result, format_actions, format_result_json
from repo_memory_bootstrap._installer_paths import _record_repo_context_warnings, payload_root, resolve_target_root, skills_root
from repo_memory_bootstrap._installer_payload import _payload_entries
from repo_memory_bootstrap._installer_shared import OPTIONAL_APPEND_TARGETS, InstallResult
from repo_memory_bootstrap.installer import MANIFEST_PATH, collect_status


class OperationIrExecutionError(RuntimeError):
    pass


def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:
    if operation.get("id") not in {"memory.list-files.report", "memory.list-skills.report", "memory.status.report"}:
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    context = PrimitiveContext(
        cwd=Path.cwd(),
        roots={
            "memory.package-payload": payload_root(),
            "memory.package-skills": skills_root(),
        },
    )
    try:
        run_operation_steps(
            operation,
            initial_values={
                "target": getattr(args, "target", None),
                "format": getattr(args, "format", "text"),
                "verbose": getattr(args, "verbose", False),
            },
            context=context,
            handlers={
                "path.target_root.resolve": _resolve_memory_target_root,
                "memory.bootstrap.status.load": _load_memory_bootstrap_status,
                "payload.assemble": lambda values, arguments, _context: _assemble_payload(
                    operation_id=str(operation["id"]), values=values, arguments=arguments
                ),
                "output.emit": _emit_memory_operation_output,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _resolve_memory_target_root(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Path:
    return resolve_target_root(values.get("target"))


def _load_memory_bootstrap_status(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    if values.get("format") == "json" and not values.get("verbose"):
        return _tiny_memory_lifecycle_payload(target=values.get("target"), command="status")
    return collect_status(target=values.get("target"))


def _assemble_payload(*, operation_id: str, values: dict[str, Any], arguments: dict[str, Any]):
    if operation_id == "memory.list-files.report":
        return _assemble_memory_list_files_payload(
            target_root=values["target_root"],
            files=values["files"],
            arguments=arguments,
        )
    if operation_id == "memory.list-skills.report":
        return _assemble_memory_list_skills_payload(registry=values["registry"], arguments=arguments)
    raise OperationIrExecutionError(f"unsupported payload assembly operation: {operation_id!r}")


def _assemble_memory_list_files_payload(*, target_root: Path, files: list[dict[str, str]], arguments: dict[str, Any]):
    fields = arguments.get("fields", {})
    if not isinstance(fields, dict) or fields.get("actions_from") != "files":
        raise OperationIrExecutionError("payload.assemble must declare actions_from='files'")

    result = _new_result(
        target_root,
        dry_run=bool(fields.get("dry_run", True)),
        message=str(fields.get("message", "Packaged bootstrap file preview")),
    )
    _record_repo_context_warnings(target_root, result)
    payload_entries = _memory_payload_entries_by_relative()
    for file_entry in _enriched_memory_payload_files(files=files, payload_entries=payload_entries):
        result.add(
            file_entry["kind"],
            target_root / file_entry["relative_path"],
            file_entry["strategy"],
            role=file_entry["role"],
            safety="safe",
            source=file_entry["source"],
        )
    return result


def _memory_payload_entries_by_relative() -> dict[str, dict[str, str]]:
    entries = {
        entry.source_path.relative_to(payload_root()).as_posix(): {
            "relative_path": entry.relative_path.as_posix(),
            "role": entry.role,
            "strategy": entry.strategy,
            "kind": "managed file",
            "source": entry.relative_path.as_posix(),
        }
        for entry in _payload_entries(payload_root(), target_layout="managed-root")
    }
    entries.update(
        {
            f"__append_target__/{target_file.as_posix()}": {
                "relative_path": target_file.as_posix(),
                "role": "append-target",
                "strategy": f"optional fragment {fragment_path}",
                "kind": "append target",
                "source": fragment_path.as_posix(),
            }
            for target_file, fragment_path in OPTIONAL_APPEND_TARGETS.items()
        }
    )
    return entries


def _enriched_memory_payload_files(*, files: list[dict[str, str]], payload_entries: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    entries = []
    for file_entry in files:
        relative_path = str(file_entry.get("relative_path", ""))
        payload_entry = payload_entries.get(relative_path)
        if payload_entry is not None:
            entries.append(payload_entry)
    entries.extend(payload_entry for key, payload_entry in payload_entries.items() if key.startswith("__append_target__/"))
    return sorted(entries, key=lambda item: (item["kind"], item["relative_path"], item["source"]))


def _assemble_memory_list_skills_payload(*, registry: Any, arguments: dict[str, Any]) -> InstallResult:
    fields = arguments.get("fields", {})
    if not isinstance(fields, dict) or fields.get("actions_from") != "registry.skills":
        raise OperationIrExecutionError("payload.assemble must declare actions_from='registry.skills'")
    if not isinstance(registry, dict):
        raise OperationIrExecutionError("memory skill registry must parse to an object")

    skills_dir = skills_root()
    result = InstallResult(target_root=skills_dir, dry_run=bool(fields.get("dry_run", True)), message=str(fields["message"]))
    result.mode = str(fields.get("mode", "skills"))
    result.detected_version = None
    for skill in registry.get("skills", []):
        if not isinstance(skill, dict):
            continue
        skill_id = str(skill.get("id", "")).strip()
        relative = Path(str(skill.get("path", "")).strip())
        if not skill_id or not relative.as_posix():
            continue
        result.add(
            "bundled skill",
            skills_dir / relative.parent,
            "registered packaged product skill",
            role="skill",
            safety="safe",
            source=skill_id,
        )
    return result


def _emit_operation_output(result, *, output_format: str) -> None:
    if output_format == "json":
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
            return
        print(format_result_json(result))
        return

    print(f"Target: {result.target_root}")
    print(result.message)
    if result.detected_version is None:
        print(f"Detected version: none (payload version {result.bootstrap_version})")
    else:
        print(f"Detected version: {result.detected_version} (payload version {result.bootstrap_version})")
    for line in format_actions(result.actions, result.target_root):
        print(f"- {line}")


def _emit_memory_operation_output(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> None:
    _emit_operation_output(values["result"], output_format=str(values.get("format") or "text"))


def _tiny_memory_manifest_counts(*, target_root: Path) -> dict[str, object]:
    manifest_path = target_root / MANIFEST_PATH
    if not manifest_path.exists():
        return {
            "status": "missing",
            "note_count": 0,
            "required_count": 0,
            "optional_count": 0,
            "routing_only_count": 0,
            "path": MANIFEST_PATH.as_posix(),
        }
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {
            "status": "invalid",
            "note_count": 0,
            "required_count": 0,
            "optional_count": 0,
            "routing_only_count": 0,
            "path": MANIFEST_PATH.as_posix(),
        }
    notes = payload.get("notes", {}) if isinstance(payload, dict) else {}
    note_values = list(notes.values()) if isinstance(notes, dict) else []
    required_count = 0
    optional_count = 0
    routing_only_count = 0
    for note in note_values:
        if not isinstance(note, dict):
            continue
        note_map = cast(dict[str, object], note)
        relevance = str(note_map.get("task_relevance", "")).strip().lower()
        if relevance == "required":
            required_count += 1
        elif relevance == "optional":
            optional_count += 1
        if bool(note_map.get("routing_only", False)):
            routing_only_count += 1
    return {
        "status": "present",
        "note_count": len(note_values),
        "required_count": required_count,
        "optional_count": optional_count,
        "routing_only_count": routing_only_count,
        "path": MANIFEST_PATH.as_posix(),
    }


def _tiny_memory_lifecycle_payload(*, target: str | Path | None, command: str) -> dict[str, object]:
    target_root = resolve_target_root(target)
    counts = _tiny_memory_manifest_counts(target_root=target_root)
    health = "healthy" if counts["status"] == "present" else "attention-needed"
    return {
        "target_root": str(target_root),
        "dry_run": command == "doctor",
        "mode": "",
        "message": "Status report" if command == "status" else "Doctor report",
        "health": health,
        "detected_version": None,
        "bootstrap_version": None,
        "action_count": 0 if health == "healthy" else 1,
        "actions": []
        if health == "healthy"
        else [
            {
                "kind": counts["status"],
                "path": counts["path"],
                "detail": "memory manifest is not readable; run full doctor for remediation detail",
            }
        ],
        "active": counts,
        "detail_command": f"agentic-memory {command} --target . --verbose --format json",
    }
