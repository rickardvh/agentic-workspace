from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agentic_command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, run_operation_steps

from repo_memory_bootstrap._installer_output import _new_result, format_actions, format_result_json
from repo_memory_bootstrap._installer_paths import _record_repo_context_warnings, payload_root, resolve_target_root, skills_root
from repo_memory_bootstrap._installer_payload import _payload_entries
from repo_memory_bootstrap._installer_shared import OPTIONAL_APPEND_TARGETS, InstallResult


class OperationIrExecutionError(RuntimeError):
    pass


def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:
    if operation.get("id") not in {"memory.list-files.report", "memory.list-skills.report"}:
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
            initial_values={"target": getattr(args, "target", None), "format": getattr(args, "format", "text")},
            context=context,
            handlers={
                "path.target_root.resolve": _resolve_memory_target_root,
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
