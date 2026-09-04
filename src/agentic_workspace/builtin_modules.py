from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .modules import Module
from .operations import Operation

STATE_ROOT = ".agentic-workspace"
PLANNING_STATE = f"{STATE_ROOT}/planning.json"
MEMORY_STATE = f"{STATE_ROOT}/memory.json"
VERIFICATION_STATE = f"{STATE_ROOT}/verification.json"
CONFIG_STATE = f"{STATE_ROOT}/config.toml"
MANIFEST_STATE = f"{STATE_ROOT}/managed.json"
LEGACY_MANAGED_FILES = (
    f"{STATE_ROOT}/WORKFLOW.md",
    f"{STATE_ROOT}/OWNERSHIP.toml",
    f"{STATE_ROOT}/payload-provenance.json",
    f"{STATE_ROOT}/fallback/no-cli-policy.json",
    f"{STATE_ROOT}/fallback/no_cli_startup.py",
)


def _root(arguments: dict[str, Any]) -> Path:
    target = arguments.get("target", ".")
    if not isinstance(target, str) or not target:
        raise ValueError("target must be a non-empty path")
    return Path(target).resolve()


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _revision(path: Path, *, absent: str = "absent") -> str:
    if not path.is_file():
        return absent
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _record_managed(root: Path, relative: str) -> None:
    path = root / MANIFEST_STATE
    payload = _json(path) or {"schema_version": 1, "files": []}
    files = payload.get("files", [])
    if not isinstance(files, list):
        raise ValueError("managed.json files must be a list")
    if relative not in files:
        files.append(relative)
    payload["files"] = sorted(str(item) for item in files)
    _write_json(path, payload)


def _operation_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def _workspace_contribution(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    requested = context.get("workspace")
    legacy = [relative for relative in LEGACY_MANAGED_FILES if (root / relative).is_file()]
    config_path = root / CONFIG_STATE
    config: dict[str, Any] = {}
    if config_path.is_file():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            legacy.append(CONFIG_STATE)
    if config and config.get("schema_version") != 1:
        legacy.append(CONFIG_STATE)
    if legacy:
        return {
            "revision": "sha256:" + hashlib.sha256("\n".join(sorted(set(legacy))).encode()).hexdigest(),
            "actions": [
                {
                    "operation_id": "workspace.remove-legacy",
                    "arguments": {"target": str(root), "confirm": "remove-managed-v0"},
                    "effects": ["workspace-managed-files"],
                    "priority": 1000,
                }
            ],
            "claims": {"blocked": ["complete"]},
        }
    if requested == "remove" and any(
        (root / relative).exists() for relative in (MANIFEST_STATE, *LEGACY_MANAGED_FILES)
    ):
        return {
            "revision": _revision(root / MANIFEST_STATE),
            "actions": [
                {
                    "operation_id": "workspace.remove",
                    "arguments": {"target": str(root)},
                    "effects": ["workspace-managed-files"],
                    "priority": 1000,
                }
            ],
        }
    if not config:
        return None
    return {"revision": _revision(config_path), "facts": {"schema_version": 1}, "terminal": True}


def _remove_legacy(arguments: dict[str, Any]) -> dict[str, Any]:
    if arguments["confirm"] != "remove-managed-v0":
        return {"status": "rejected", "effects": [], "value": {"reason": "confirmation-mismatch"}}
    root = _root(arguments)
    removed: list[str] = []
    for relative in LEGACY_MANAGED_FILES:
        path = root / relative
        if path.is_file():
            path.unlink()
            removed.append(relative)
    config_path = root / CONFIG_STATE
    if config_path.is_file():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            config = {}
        if config.get("schema_version") != 1:
            config_path.unlink()
            removed.append(CONFIG_STATE)
    return {
        "status": "applied" if removed else "unchanged",
        "effects": ["workspace-managed-files"] if removed else [],
        "value": {"removed": removed},
    }


def _remove(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    manifest_path = root / MANIFEST_STATE
    manifest = _json(manifest_path)
    files = manifest.get("files", []) if manifest else []
    if not isinstance(files, list):
        return {"status": "rejected", "effects": [], "value": {"reason": "invalid-managed-manifest"}}
    removed: list[str] = []
    preserved: list[str] = []
    for relative in files:
        if not isinstance(relative, str) or not relative.startswith(f"{STATE_ROOT}/"):
            preserved.append(str(relative))
            continue
        path = root / relative
        if path.is_file():
            path.unlink()
            removed.append(relative)
    if manifest_path.is_file():
        manifest_path.unlink()
        removed.append(MANIFEST_STATE)
    receipt_root = root / STATE_ROOT / "receipts"
    if receipt_root.is_dir():
        for receipt in receipt_root.glob("*.json"):
            receipt.unlink()
            removed.append(receipt.relative_to(root).as_posix())
        receipt_root.rmdir()
    return {
        "status": "applied" if removed else "unchanged",
        "effects": ["workspace-managed-files"] if removed else [],
        "value": {"removed": removed, "preserved": preserved},
    }


def workspace_module() -> Module:
    target = {"target": {"type": "string", "minLength": 1}}
    return Module(
        name="workspace",
        contribute=_workspace_contribution,
        operations=(
            Operation(
                "workspace.remove-legacy",
                _operation_schema({**target, "confirm": {"const": "remove-managed-v0"}}, ["target", "confirm"]),
                ("workspace-managed-files",),
                _remove_legacy,
            ),
            Operation(
                "workspace.remove",
                _operation_schema(target, ["target"]),
                ("workspace-managed-files",),
                _remove,
            ),
        ),
    )


def _planning_contribution(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    path = root / PLANNING_STATE
    state = _json(path)
    requested = context.get("planning")
    if isinstance(requested, Mapping) and requested.get("operation") == "set":
        item = str(requested.get("item") or "")
        status = str(requested.get("status") or "")
        return {
            "revision": _revision(path),
            "actions": [
                {
                    "operation_id": "planning.set",
                    "arguments": {"target": str(root), "item": item, "status": status},
                    "effects": ["planning-state"],
                    "priority": 50,
                }
            ],
        }
    if not state:
        return None
    active = state.get("active")
    if not isinstance(active, dict):
        return {"revision": _revision(path), "terminal": True}
    status = active.get("status")
    actions = []
    if status == "ready-to-complete":
        actions = [
            {
                "operation_id": "planning.complete",
                "arguments": {"target": str(root), "item": str(active.get("id") or "")},
                "effects": ["planning-state"],
                "priority": 50,
            }
        ]
    return {
        "revision": _revision(path),
        "facts": {"active": active},
        "actions": actions,
        "claims": {"allowed": ["progress"], "blocked": [] if status == "complete" else ["complete"]},
        "terminal": status == "complete",
    }


def _planning_set(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    path = root / PLANNING_STATE
    state = _json(path) or {"schema_version": 1, "revision": 0}
    state["revision"] = int(state.get("revision", 0)) + 1
    state["active"] = {"id": arguments["item"], "status": arguments["status"]}
    _write_json(path, state)
    _record_managed(root, PLANNING_STATE)
    return {"status": "applied", "effects": ["planning-state"], "value": state["active"]}


def _planning_complete(arguments: dict[str, Any]) -> dict[str, Any]:
    return _planning_set({**arguments, "status": "complete"})


def planning_module() -> Module:
    target = {"type": "string", "minLength": 1}
    item = {"type": "string", "minLength": 1}
    return Module(
        name="planning",
        contribute=_planning_contribution,
        operations=(
            Operation(
                "planning.set",
                _operation_schema(
                    {
                        "target": target,
                        "item": item,
                        "status": {"enum": ["in-progress", "ready-to-complete", "complete"]},
                    },
                    ["target", "item", "status"],
                ),
                ("planning-state",),
                _planning_set,
            ),
            Operation(
                "planning.complete",
                _operation_schema({"target": target, "item": item}, ["target", "item"]),
                ("planning-state",),
                _planning_complete,
            ),
        ),
    )


def _memory_contribution(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    path = root / MEMORY_STATE
    state = _json(path)
    requested = context.get("memory")
    if isinstance(requested, Mapping) and "key" in requested and "value" in requested:
        return {
            "revision": _revision(path),
            "actions": [
                {
                    "operation_id": "memory.record",
                    "arguments": {
                        "target": str(root),
                        "key": str(requested["key"]),
                        "value": requested["value"],
                    },
                    "effects": ["memory-state"],
                    "priority": 50,
                }
            ],
        }
    if not state:
        return None
    return {"revision": _revision(path), "facts": {"records": state.get("records", [])}, "terminal": True}


def _memory_record(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    path = root / MEMORY_STATE
    state = _json(path) or {"schema_version": 1, "revision": 0, "records": []}
    records = state.get("records", [])
    if not isinstance(records, list):
        return {"status": "rejected", "effects": [], "value": {"reason": "invalid-memory-state"}}
    record = {"key": arguments["key"], "value": arguments["value"]}
    records = [item for item in records if not isinstance(item, dict) or item.get("key") != arguments["key"]]
    records.append(record)
    state.update(revision=int(state.get("revision", 0)) + 1, records=records)
    _write_json(path, state)
    _record_managed(root, MEMORY_STATE)
    return {"status": "applied", "effects": ["memory-state"], "value": record}


def memory_module() -> Module:
    return Module(
        name="memory",
        contribute=_memory_contribution,
        operations=(
            Operation(
                "memory.record",
                _operation_schema(
                    {
                        "target": {"type": "string", "minLength": 1},
                        "key": {"type": "string", "minLength": 1},
                        "value": {},
                    },
                    ["target", "key", "value"],
                ),
                ("memory-state",),
                _memory_record,
            ),
        ),
    )


def _verification_contribution(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    planning = _json(root / PLANNING_STATE)
    raw_active = planning.get("active")
    active = raw_active if isinstance(raw_active, dict) else {}
    needs_proof = active.get("status") == "ready-to-complete"
    path = root / VERIFICATION_STATE
    state = _json(path)
    if not needs_proof and not state:
        return None
    if not needs_proof:
        passed = state.get("status") == "passed"
        return {
            "revision": _revision(path),
            "facts": {"proof": state},
            "claims": {"allowed": ["complete"] if passed else [], "blocked": [] if passed else ["complete"]},
            "terminal": True,
        }
    current_subject = _revision(root / PLANNING_STATE)
    current = bool(state and state.get("subject_revision") == current_subject and state.get("status") == "passed")
    actions = []
    if needs_proof and not current:
        commands = planning.get("validation", [])
        if not isinstance(commands, list) or any(
            not isinstance(command, list) or any(not isinstance(part, str) for part in command) for command in commands
        ):
            return {
                "revision": _revision(path),
                "blockers": [
                    {"code": "missing-proof-route", "message": "Planning did not declare typed validation argv"}
                ],
                "claims": {"blocked": ["complete"]},
            }
        actions = [
            {
                "operation_id": "verification.run",
                "arguments": {"target": str(root), "subject_revision": current_subject, "commands": commands},
                "effects": ["verification-state", "process"],
                "priority": 100,
            }
        ]
    return {
        "revision": _revision(path),
        "facts": {"proof": state if current else None},
        "actions": actions,
        "claims": {"allowed": ["complete"] if current else [], "blocked": [] if current else ["complete"]},
        "terminal": current,
    }


def _verification_run(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    commands = arguments["commands"]
    results: list[dict[str, Any]] = []
    passed = True
    for command in commands:
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        results.append({"argv": command, "returncode": completed.returncode})
        if completed.returncode != 0:
            passed = False
            break
    state = {
        "schema_version": 1,
        "subject_revision": arguments["subject_revision"],
        "status": "passed" if passed else "failed",
        "results": results,
    }
    path = root / VERIFICATION_STATE
    _write_json(path, state)
    _record_managed(root, VERIFICATION_STATE)
    return {
        "status": "applied" if passed else "rejected",
        "effects": ["verification-state", "process"],
        "value": state,
    }


def verification_module() -> Module:
    command_schema = {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}
    return Module(
        name="verification",
        contribute=_verification_contribution,
        operations=(
            Operation(
                "verification.run",
                _operation_schema(
                    {
                        "target": {"type": "string", "minLength": 1},
                        "subject_revision": {"type": "string", "minLength": 1},
                        "commands": {"type": "array", "items": command_schema},
                    },
                    ["target", "subject_revision", "commands"],
                ),
                ("verification-state", "process"),
                _verification_run,
            ),
        ),
    )
