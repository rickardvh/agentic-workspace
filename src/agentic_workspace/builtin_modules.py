from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .durability import atomic_create_json, atomic_write_json
from .generated_semantics import operation_contract
from .modules import Module
from .operations import Operation

STATE_ROOT = ".agentic-workspace"
PLANNING_STATE = f"{STATE_ROOT}/planning.json"
MEMORY_STATE = f"{STATE_ROOT}/memory.json"
VERIFICATION_STATE = f"{STATE_ROOT}/verification.json"
CONFIG_STATE = f"{STATE_ROOT}/config.toml"
MANIFEST_STATE = f"{STATE_ROOT}/managed.json"
CUSTODY_STATE = f"{STATE_ROOT}/local/ownership.json"
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
    atomic_write_json(path, value)


def _digest_path(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _managed_path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(f"managed path is not canonical and relative: {relative}")
    if candidate.as_posix() != relative or candidate.parts[0] != STATE_ROOT:
        raise ValueError(f"managed path is outside {STATE_ROOT}: {relative}")
    path = root.joinpath(*candidate.parts)
    root_resolved = (root / STATE_ROOT).resolve()
    parent_resolved = path.parent.resolve()
    if root_resolved != parent_resolved and root_resolved not in parent_resolved.parents:
        raise ValueError(f"managed path escapes target through indirection: {relative}")
    return path


def _ownership(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest = _json(root / MANIFEST_STATE) or {"schema_version": 2, "records": []}
    custody = _json(root / CUSTODY_STATE) or {"schema_version": 1, "records": []}
    if manifest.get("schema_version") != 2 or custody.get("schema_version") != 1:
        raise ValueError("ownership records use an unsupported schema")
    manifest_records = manifest.get("records", [])
    custody_records = custody.get("records", [])
    if not isinstance(manifest_records, list) or not isinstance(custody_records, list):
        raise ValueError("ownership records must be lists")
    if any(not isinstance(item, dict) or not isinstance(item.get("path"), str) for item in manifest_records):
        raise ValueError("managed ownership manifest contains malformed records")
    if any(not isinstance(item, dict) or not isinstance(item.get("path"), str) for item in custody_records):
        raise ValueError("local ownership custody contains malformed records")
    manifest_by_path = {str(item["path"]): dict(item) for item in manifest_records}
    custody_by_path = {str(item["path"]): dict(item) for item in custody_records}
    if manifest_by_path != custody_by_path:
        raise ValueError("managed ownership manifest does not match local custody proof")
    return manifest_by_path, custody_by_path


def _state_revision(root: Path, relative: str) -> str:
    state_revision = _revision(root / relative)
    try:
        records, _ = _ownership(root)
    except ValueError:
        return state_revision + ":ownership-conflict"
    record = records.get(relative)
    if record is None:
        return state_revision + ":unowned"
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return state_revision + ":ownership-" + hashlib.sha256(encoded).hexdigest()


def _write_ownership(root: Path, records: Mapping[str, Mapping[str, Any]]) -> None:
    ordered = [dict(records[path]) for path in sorted(records)]
    _write_json(root / CUSTODY_STATE, {"schema_version": 1, "records": ordered})
    _write_json(root / MANIFEST_STATE, {"schema_version": 2, "records": ordered})


def _raw_ownership_records(path: Path) -> dict[str, dict[str, Any]]:
    payload = _json(path)
    records = payload.get("records", []) if payload else []
    if not isinstance(records, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("path"), str) for item in records
    ):
        return {}
    return {str(item["path"]): dict(item) for item in records}


def _repair_owned_record(root: Path, relative: str, owner: str, classification: str) -> bool:
    """Finish an interrupted owner multi-write only when no competing owner exists."""

    path = _managed_path(root, relative)
    if not path.is_file() or path.is_symlink():
        return False
    manifest = _raw_ownership_records(root / MANIFEST_STATE)
    custody = _raw_ownership_records(root / CUSTODY_STATE)
    candidates = [record for record in (manifest.get(relative), custody.get(relative)) if record is not None]
    if any(record.get("owner") != owner for record in candidates):
        return False
    records = {**custody, **manifest}
    records[relative] = {
        "path": relative,
        "owner": owner,
        "classification": classification,
        "sha256": _digest_path(path),
    }
    _write_ownership(root, records)
    return True


def _write_owned_json(
    root: Path,
    relative: str,
    owner: str,
    classification: str,
    value: dict[str, Any],
    *,
    recognizes_existing: Callable[[dict[str, Any]], bool],
) -> None:
    path = _managed_path(root, relative)
    manifest, custody = _ownership(root)
    record = manifest.get(relative)
    if record != custody.get(relative):
        raise ValueError(f"ownership proof mismatch for {relative}; reconcile through workspace.transfer-ownership")
    existed = path.exists()
    if existed:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"owned state path is not a regular file: {relative}")
        current_digest = _digest_path(path)
        if record is None:
            existing = _json(path)
            if not recognizes_existing(existing):
                raise ValueError(f"unknown content collision at {relative}; use workspace.transfer-ownership")
        elif record.get("owner") != owner or record.get("sha256") != current_digest:
            raise ValueError(f"current ownership/content proof failed for {relative}")
    if existed:
        _write_json(path, value)
    else:
        try:
            atomic_create_json(path, value)
        except FileExistsError as exc:
            raise ValueError(f"unknown content collision at {relative}; use workspace.transfer-ownership") from exc
    manifest[relative] = {
        "path": relative,
        "owner": owner,
        "classification": classification,
        "sha256": _digest_path(path),
    }
    _write_ownership(root, manifest)


def _operation(
    operation_id: str,
    handler: Callable[[dict[str, Any]], dict[str, Any]],
    recover: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
) -> Operation:
    contract = operation_contract(operation_id)
    return Operation(operation_id, contract["input"], tuple(contract["effects"]), handler, recover)


def _workspace_contribution(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    requested = context.get("workspace")
    if isinstance(requested, Mapping) and requested.get("operation") == "transfer-ownership":
        path = str(requested.get("path") or "")
        return {
            "revision": _revision(root / MANIFEST_STATE),
            "actions": [
                {
                    "operation_id": "workspace.transfer-ownership",
                    "arguments": {
                        "target": str(root),
                        "path": path,
                        "from_owner": str(requested.get("from_owner") or "unowned"),
                        "to_owner": str(requested.get("to_owner") or ""),
                        "expected_sha256": str(requested.get("expected_sha256") or ""),
                        "classification": str(requested.get("classification") or "durable-module-state"),
                    },
                    "effects": ["workspace-ownership"],
                    "priority": 1000,
                }
            ],
        }
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
    try:
        manifest, custody = _ownership(root)
    except ValueError as exc:
        return {"status": "rejected", "effects": [], "value": {"reason": str(exc)}}
    removed: list[str] = []
    preserved: list[str] = []
    for relative, record in manifest.items():
        if record != custody.get(relative) or record.get("classification") != "package-residue":
            preserved.append(relative)
            continue
        try:
            path = _managed_path(root, relative)
        except ValueError:
            preserved.append(relative)
            continue
        if path.is_file() and not path.is_symlink() and record.get("sha256") == _digest_path(path):
            path.unlink()
            removed.append(relative)
    if manifest_path.is_file():
        manifest_path.unlink()
        removed.append(MANIFEST_STATE)
    custody_path = root / CUSTODY_STATE
    if custody_path.is_file():
        custody_path.unlink()
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


def _transfer_ownership(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    relative = arguments["path"]
    path = _managed_path(root, relative)
    if not path.is_file() or path.is_symlink() or _digest_path(path) != arguments["expected_sha256"]:
        return {"status": "rejected", "effects": [], "value": {"reason": "path-currentness-mismatch"}}
    manifest, custody = _ownership(root)
    current = manifest.get(relative)
    if current != custody.get(relative):
        return {"status": "rejected", "effects": [], "value": {"reason": "ownership-proof-mismatch"}}
    current_owner = str(current.get("owner")) if current else "unowned"
    if current_owner != arguments["from_owner"]:
        return {"status": "rejected", "effects": [], "value": {"reason": "from-owner-mismatch"}}
    manifest[relative] = {
        "path": relative,
        "owner": arguments["to_owner"],
        "classification": arguments["classification"],
        "sha256": arguments["expected_sha256"],
    }
    _write_ownership(root, manifest)
    return {"status": "applied", "effects": ["workspace-ownership"], "value": manifest[relative]}


def _recover_transfer(arguments: dict[str, Any]) -> dict[str, Any] | None:
    root = _root(arguments)
    manifest, custody = _ownership(root)
    record = manifest.get(arguments["path"])
    if record == custody.get(arguments["path"]) and record and record.get("owner") == arguments["to_owner"]:
        return {"status": "applied", "effects": ["workspace-ownership"], "value": record}
    return None


def _recover_remove(arguments: dict[str, Any]) -> dict[str, Any] | None:
    root = _root(arguments)
    if not (root / MANIFEST_STATE).exists():
        return {
            "status": "applied",
            "effects": ["workspace-managed-files"],
            "value": {"removed": [], "preserved": [], "recovered": True},
        }
    return None


def workspace_module() -> Module:
    return Module(
        name="workspace",
        owns=("workspace-managed-state",),
        contribute=_workspace_contribution,
        operations=(
            _operation("workspace.transfer-ownership", _transfer_ownership, _recover_transfer),
            _operation("workspace.remove-legacy", _remove_legacy, _recover_remove),
            _operation("workspace.remove", _remove, _recover_remove),
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
        if state.get("active") != {"id": item, "status": status}:
            return {
                "revision": _state_revision(root, PLANNING_STATE),
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
        return {"revision": _state_revision(root, PLANNING_STATE), "terminal": True}
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
        "revision": _state_revision(root, PLANNING_STATE),
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
    _write_owned_json(
        root,
        PLANNING_STATE,
        "planning",
        "durable-module-state",
        state,
        recognizes_existing=lambda item: item.get("schema_version") == 1 and isinstance(item.get("revision"), int),
    )
    return {"status": "applied", "effects": ["planning-state"], "value": state["active"]}


def _planning_complete(arguments: dict[str, Any]) -> dict[str, Any]:
    return _planning_set({**arguments, "status": "complete"})


def _recover_planning(arguments: dict[str, Any]) -> dict[str, Any] | None:
    state = _json(_root(arguments) / PLANNING_STATE)
    expected = {"id": arguments["item"], "status": arguments["status"]}
    if state.get("active") == expected:
        if not _repair_owned_record(_root(arguments), PLANNING_STATE, "planning", "durable-module-state"):
            return None
        return {"status": "applied", "effects": ["planning-state"], "value": expected}
    return None


def _recover_planning_complete(arguments: dict[str, Any]) -> dict[str, Any] | None:
    return _recover_planning({**arguments, "status": "complete"})


def planning_module() -> Module:
    return Module(
        name="planning",
        owns=("planning-state",),
        claims=("progress",),
        contribute=_planning_contribution,
        operations=(
            _operation("planning.set", _planning_set, _recover_planning),
            _operation("planning.complete", _planning_complete, _recover_planning_complete),
        ),
    )


def _memory_contribution(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    path = root / MEMORY_STATE
    state = _json(path)
    requested = context.get("memory")
    if isinstance(requested, Mapping) and requested.get("operation") == "read":
        return {
            "revision": _state_revision(root, MEMORY_STATE),
            "actions": [
                {
                    "operation_id": "memory.read",
                    "arguments": {"target": str(root), "key": str(requested.get("key") or "")},
                    "effects": [],
                    "priority": 50,
                }
            ],
        }
    if isinstance(requested, Mapping) and "key" in requested and "value" in requested:
        record = {"key": str(requested["key"]), "value": requested["value"]}
        records = state.get("records", [])
        if isinstance(records, list) and record in records:
            return {"revision": _state_revision(root, MEMORY_STATE), "facts": {"record": record}, "terminal": True}
        return {
            "revision": _state_revision(root, MEMORY_STATE),
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
    return {
        "revision": _state_revision(root, MEMORY_STATE),
        "facts": {"records": state.get("records", [])},
        "terminal": True,
    }


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
    state.setdefault("schema_version", 1)
    state.update(revision=int(state.get("revision", 0)) + 1, records=records)
    _write_owned_json(
        root,
        MEMORY_STATE,
        "memory",
        "durable-module-state",
        state,
        recognizes_existing=lambda item: item.get("schema_version") == 1 and isinstance(item.get("records"), list),
    )
    return {"status": "applied", "effects": ["memory-state"], "value": record}


def _memory_read(arguments: dict[str, Any]) -> dict[str, Any]:
    state = _json(_root(arguments) / MEMORY_STATE)
    records = state.get("records", [])
    if not isinstance(records, list):
        return {"status": "rejected", "effects": [], "value": {"reason": "invalid-memory-state"}}
    value = next(
        (item.get("value") for item in records if isinstance(item, dict) and item.get("key") == arguments["key"]),
        None,
    )
    return {"status": "unchanged", "effects": [], "value": {"key": arguments["key"], "value": value}}


def _recover_memory_record(arguments: dict[str, Any]) -> dict[str, Any] | None:
    record = {"key": arguments["key"], "value": arguments["value"]}
    state = _json(_root(arguments) / MEMORY_STATE)
    if record in state.get("records", []):
        if not _repair_owned_record(_root(arguments), MEMORY_STATE, "memory", "durable-module-state"):
            return None
        return {"status": "applied", "effects": ["memory-state"], "value": record}
    return None


def memory_module() -> Module:
    return Module(
        name="memory",
        owns=("memory-state",),
        contribute=_memory_contribution,
        operations=(
            _operation("memory.read", _memory_read),
            _operation("memory.record", _memory_record, _recover_memory_record),
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
            "revision": _state_revision(root, VERIFICATION_STATE),
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
                "revision": _state_revision(root, VERIFICATION_STATE),
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
        "revision": _state_revision(root, VERIFICATION_STATE),
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
    _write_owned_json(
        root,
        VERIFICATION_STATE,
        "verification",
        "package-residue",
        state,
        recognizes_existing=lambda item: item.get("schema_version") == 1 and item.get("status") in {"passed", "failed"},
    )
    return {
        "status": "applied" if passed else "rejected",
        "effects": ["verification-state", "process"],
        "value": state,
    }


def _recover_verification(arguments: dict[str, Any]) -> dict[str, Any] | None:
    root = _root(arguments)
    state = _json(root / VERIFICATION_STATE)
    if state.get("subject_revision") != arguments["subject_revision"] or state.get("status") not in {
        "passed",
        "failed",
    }:
        return None
    if not _repair_owned_record(root, VERIFICATION_STATE, "verification", "package-residue"):
        return None
    passed = state["status"] == "passed"
    return {
        "status": "applied" if passed else "rejected",
        "effects": ["verification-state", "process"],
        "value": state,
    }


def verification_module() -> Module:
    return Module(
        name="verification",
        owns=("verification-state", "completion-claim"),
        claims=("complete",),
        contribute=_verification_contribution,
        operations=(_operation("verification.run", _verification_run, _recover_verification),),
    )
