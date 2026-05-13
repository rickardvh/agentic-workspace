from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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

    values: dict[str, Any] = {"target": getattr(args, "target", None), "format": getattr(args, "format", "text")}
    for step in operation.get("ir_plan", {}).get("steps", []):
        primitive = step.get("uses")
        if primitive == "path.target_root.resolve":
            values["target_root"] = resolve_target_root(values["target"])
        elif primitive == "filesystem.read":
            values["registry_text"] = _read_memory_package_file(step.get("arguments", {}))
        elif primitive == "json.parse":
            values["registry"] = json.loads(str(values["registry_text"]))
        elif primitive == "filesystem.glob":
            values["files"] = _list_memory_payload_entries(step.get("arguments", {}))
        elif primitive == "payload.assemble":
            values["result"] = _assemble_payload(operation_id=str(operation["id"]), values=values, arguments=step.get("arguments", {}))
        elif primitive == "output.emit":
            _emit_operation_output(values["result"], output_format=str(values["format"]))
        else:
            raise OperationIrExecutionError(f"unsupported primitive in operation IR: {primitive!r}")
    return 0


def _read_memory_package_file(arguments: dict[str, Any]) -> str:
    if arguments.get("root") != "memory.package-skills":
        raise OperationIrExecutionError(f"unsupported filesystem.read root: {arguments.get('root')!r}")
    relative_path = Path(str(arguments.get("path", "")))
    if relative_path.as_posix() != "REGISTRY.json":
        raise OperationIrExecutionError(f"unsupported filesystem.read path: {relative_path.as_posix()!r}")
    return (skills_root() / relative_path).read_text(encoding="utf-8")


def _list_memory_payload_entries(arguments: dict[str, Any]) -> list[dict[str, str]]:
    if arguments.get("root") != "memory.package-payload":
        raise OperationIrExecutionError(f"unsupported filesystem.glob root: {arguments.get('root')!r}")
    if arguments.get("pattern") != "**/*":
        raise OperationIrExecutionError(f"unsupported filesystem.glob pattern: {arguments.get('pattern')!r}")

    entries = [
        {
            "relative_path": entry.relative_path.as_posix(),
            "role": entry.role,
            "strategy": entry.strategy,
            "kind": "managed file",
            "source": entry.relative_path.as_posix(),
        }
        for entry in _payload_entries(payload_root(), target_layout="managed-root")
    ]
    entries.extend(
        {
            "relative_path": target_file.as_posix(),
            "role": "append-target",
            "strategy": f"optional fragment {fragment_path}",
            "kind": "append target",
            "source": fragment_path.as_posix(),
        }
        for target_file, fragment_path in OPTIONAL_APPEND_TARGETS.items()
    )
    return sorted(entries, key=lambda item: (item["kind"], item["relative_path"], item["source"]))


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
    for file_entry in files:
        result.add(
            file_entry["kind"],
            target_root / file_entry["relative_path"],
            file_entry["strategy"],
            role=file_entry["role"],
            safety="safe",
            source=file_entry["source"],
        )
    return result


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
