from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from collections.abc import Callable, Mapping
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from .durability import atomic_create_json, atomic_write_json
from .generated_semantics import operation_contract, semantic_digest
from .modules import Module
from .operations import Operation

STATE_ROOT = ".agentic-workspace"
PLANNING_STATE = f"{STATE_ROOT}/planning.json"
MEMORY_STATE = f"{STATE_ROOT}/memory.json"
VERIFICATION_STATE = f"{STATE_ROOT}/verification.json"
VERIFICATION_POLICY = f"{STATE_ROOT}/verification.toml"
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
    *,
    accepted_handoffs: tuple[str, ...] = (),
) -> Operation:
    contract = operation_contract(operation_id)
    return Operation(
        operation_id,
        contract["input"],
        tuple(contract["effects"]),
        handler,
        recover,
        accepted_handoffs,
    )


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


def _planning_subjects(state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    stored = state.get("subjects")
    if isinstance(stored, dict):
        return {str(key): dict(value) for key, value in stored.items() if isinstance(value, dict)}
    legacy = state.get("subject") if isinstance(state.get("subject"), dict) else state.get("active")
    if isinstance(legacy, dict) and legacy.get("id"):
        return {str(legacy["id"]): dict(legacy)}
    return {}


def _refresh_planning_subjects(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    subjects = _planning_subjects(state)
    memo: dict[str, str] = {}

    def revision(item: str, stack: frozenset[str] = frozenset()) -> str:
        if item in memo:
            return memo[item]
        subject = subjects[item]
        dependencies: dict[str, str] = {}
        for dependency in subject.get("dependencies", []):
            dependency_id = str(dependency)
            if dependency_id not in subjects:
                dependencies[dependency_id] = "missing"
            elif dependency_id in stack or dependency_id == item:
                dependencies[dependency_id] = "cycle"
            else:
                dependency_subject = subjects[dependency_id]
                dependencies[dependency_id] = semantic_digest(
                    {
                        "revision": revision(dependency_id, stack | {item}),
                        "status": dependency_subject.get("status"),
                        "outcome": dependency_subject.get("outcome", ""),
                    }
                )
        subject["dependency_revisions"] = dependencies
        subject["semantic_revision"] = _planning_semantic_revision(subject)
        memo[item] = str(subject["semantic_revision"])
        return memo[item]

    for item in sorted(subjects):
        revision(item)
    state["subjects"] = subjects
    return subjects


def _planning_frontier(state: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], dict[str, list[str]]]:
    subjects = _refresh_planning_subjects(state)
    ready: list[str] = []
    blocked: dict[str, list[str]] = {}
    for item, subject in sorted(subjects.items()):
        if subject.get("status") == "complete":
            subject["readiness"] = "complete"
            continue
        unsatisfied = [
            str(dependency)
            for dependency in subject.get("dependencies", [])
            if str(dependency) not in subjects or subjects[str(dependency)].get("status") != "complete"
        ]
        if unsatisfied:
            subject["readiness"] = "blocked"
            blocked[item] = unsatisfied
        else:
            subject["readiness"] = "ready"
            ready.append(item)
    preferred = [item for item in ready if subjects[item].get("status") in {"returned", "integration-pending"}]
    current_id = (preferred or ready or sorted(blocked) or [None])[0]
    return (subjects.get(current_id) if current_id is not None else None, ready, blocked)


def _planning_contribution(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    path = root / PLANNING_STATE
    state = _json(path)
    requested = context.get("planning")
    if isinstance(requested, Mapping) and requested.get("operation") == "record-attempt":
        existing_attempts = state.get("attempts", [])
        already_recorded = isinstance(existing_attempts, list) and any(
            isinstance(item, dict)
            and item.get("id") == requested.get("attempt_id")
            and item.get("status") == requested.get("status")
            for item in existing_attempts
        )
        if not already_recorded:
            return {
                "revision": _state_revision(root, PLANNING_STATE),
                "actions": [
                    {
                        "operation_id": "planning.record-attempt",
                        "arguments": {
                            "target": str(root),
                            "item": str(requested.get("item") or ""),
                            "expected_subject_revision": str(requested.get("expected_subject_revision") or ""),
                            "attempt_id": str(requested.get("attempt_id") or ""),
                            "target_id": str(requested.get("target_id") or ""),
                            "status": str(requested.get("status") or ""),
                            "result_revision": str(requested.get("result_revision") or ""),
                        },
                        "effects": ["planning-state"],
                        "priority": 60,
                    }
                ],
            }
    existing_attempts = state.get("attempts", [])
    recorded_ids = {
        str(item.get("id")) for item in existing_attempts if isinstance(item, dict) and item.get("status") == "returned"
    }
    subjects = _planning_subjects(state)
    delegated = _json(root / ".agentic-workspace/local/delegation-attempts.json").get("attempts", [])
    integrated = next(
        (
            item
            for item in reversed(delegated if isinstance(delegated, list) else [])
            if isinstance(item, dict)
            and item.get("status") == "integrated"
            and item.get("id") not in recorded_ids
            and any(subject.get("semantic_revision") == item.get("subject_revision") for subject in subjects.values())
        ),
        None,
    )
    if integrated is not None:
        subject = next(
            item for item in subjects.values() if item.get("semantic_revision") == integrated.get("subject_revision")
        )
        return {
            "revision": _state_revision(root, PLANNING_STATE),
            "actions": [
                {
                    "operation_id": "planning.record-attempt",
                    "arguments": {
                        "target": str(root),
                        "item": str(subject["id"]),
                        "expected_subject_revision": str(subject["semantic_revision"]),
                        "attempt_id": str(integrated["id"]),
                        "target_id": str(integrated.get("target_id") or ""),
                        "status": "returned",
                        "result_revision": semantic_digest(integrated.get("result", {})),
                    },
                    "effects": ["planning-state"],
                    "priority": 70,
                }
            ],
        }
    if isinstance(requested, Mapping) and requested.get("operation") == "set":
        item = str(requested.get("item") or "")
        status = str(requested.get("status") or "")
        current = _planning_subjects(state).get(item)
        requested_subject = {
            "id": item,
            "status": status,
            "outcome": str(requested.get("outcome") or ""),
            "scope": list(requested.get("scope", [])),
            "constraints": list(requested.get("constraints", [])),
            "dependencies": list(requested.get("dependencies", [])),
            "stops": list(requested.get("stops", [])),
            "proof_claims": list(requested.get("proof_claims", ["complete"])),
        }
        if not isinstance(current, dict) or any(current.get(key) != value for key, value in requested_subject.items()):
            return {
                "revision": _state_revision(root, PLANNING_STATE),
                "actions": [
                    {
                        "operation_id": "planning.set",
                        "arguments": {
                            "target": str(root),
                            "item": item,
                            "status": status,
                            "outcome": requested_subject["outcome"],
                            "scope": requested_subject["scope"],
                            "constraints": requested_subject["constraints"],
                            "dependencies": requested_subject["dependencies"],
                            "stops": requested_subject["stops"],
                            "proof_claims": requested_subject["proof_claims"],
                        },
                        "effects": ["planning-state"],
                        "priority": 50,
                    }
                ],
            }
    if not state:
        return None
    active, frontier, blocked_dependencies = _planning_frontier(state)
    if not isinstance(active, dict):
        return {"revision": _state_revision(root, PLANNING_STATE), "terminal": True}
    status = active.get("status")
    actions = []
    decisions = []
    if status == "ready-to-complete":
        actions = [
            {
                "operation_id": "planning.complete",
                "arguments": {"target": str(root), "item": str(active.get("id") or "")},
                "effects": ["planning-state"],
                "priority": 50,
            }
        ]
    elif status in {"returned", "integration-pending"}:
        decisions = [
            {
                "id": f"reconcile:{active.get('id')}",
                "question": "How should the returned work change the current Planning subject?",
                "authority": "planning-owner",
                "response_operation_id": "planning.reconcile",
                "effects": ["planning-state"],
                "choices": [
                    {"id": "integrated", "label": "Integrated"},
                    {"id": "revise-scope", "label": "Revise scope"},
                    {"id": "residual", "label": "Residual work"},
                ],
            }
        ]
    return {
        "revision": _state_revision(root, PLANNING_STATE),
        "facts": {
            "active": active,
            "frontier": frontier,
            "blocked_dependencies": blocked_dependencies,
            "current_attempts": state.get("attempts", []),
        },
        "actions": actions,
        "decisions": decisions,
        "claims": {"allowed": ["progress"], "blocked": [] if status == "complete" else ["complete"]},
        "terminal": status == "complete",
    }


def _planning_semantic_revision(subject: Mapping[str, Any]) -> str:
    return semantic_digest(
        {
            "id": subject.get("id"),
            "outcome": subject.get("outcome", ""),
            "scope": subject.get("scope", []),
            "constraints": subject.get("constraints", []),
            "dependencies": subject.get("dependencies", []),
            "dependency_revisions": subject.get("dependency_revisions", {}),
            "stops": subject.get("stops", []),
            "proof_claims": subject.get("proof_claims", ["complete"]),
        }
    )


def _planning_set(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    path = root / PLANNING_STATE
    expected_revision = str(arguments.get("expected_state_revision") or "")
    if expected_revision and _state_revision(root, PLANNING_STATE) != expected_revision:
        return {"status": "rejected", "effects": [], "value": {"reason": "stale-planning-state"}}
    state = _json(path) or {"schema_version": 1, "revision": 0}
    subjects = _planning_subjects(state)
    current = subjects.get(arguments["item"], {})
    subject = {
        "id": arguments["item"],
        "status": arguments["status"],
        "outcome": arguments.get("outcome", current.get("outcome", "")),
        "scope": list(arguments.get("scope", current.get("scope", []))),
        "constraints": list(arguments.get("constraints", current.get("constraints", []))),
        "dependencies": list(arguments.get("dependencies", current.get("dependencies", []))),
        "stops": list(arguments.get("stops", current.get("stops", []))),
        "proof_claims": list(arguments.get("proof_claims", current.get("proof_claims", ["complete"]))),
    }
    subjects[subject["id"]] = subject
    state["subjects"] = subjects
    subjects = _refresh_planning_subjects(state)
    subject = subjects[subject["id"]]
    attempts = state.get("attempts", [])
    if isinstance(attempts, list):
        state["attempts"] = [
            attempt
            for attempt in attempts
            if not isinstance(attempt, dict)
            or attempt.get("item") not in subjects
            or attempt.get("subject_revision") == subjects[str(attempt["item"])].get("semantic_revision")
        ]
    state["revision"] = int(state.get("revision", 0)) + 1
    active, _, _ = _planning_frontier(state)
    state["subject"] = active or subject
    state["active"] = {"id": state["subject"]["id"], "status": state["subject"]["status"]}
    _write_owned_json(
        root,
        PLANNING_STATE,
        "planning",
        "durable-module-state",
        state,
        recognizes_existing=lambda item: item.get("schema_version") == 1 and isinstance(item.get("revision"), int),
    )
    return {"status": "applied", "effects": ["planning-state"], "value": subject}


def _planning_complete(arguments: dict[str, Any]) -> dict[str, Any]:
    return _planning_set({**arguments, "status": "complete"})


def _recover_planning(arguments: dict[str, Any]) -> dict[str, Any] | None:
    state = _json(_root(arguments) / PLANNING_STATE)
    subject = state.get("subject") if isinstance(state.get("subject"), dict) else state.get("active")
    expected = {"id": arguments["item"], "status": arguments["status"]}
    if isinstance(subject, dict) and all(subject.get(key) == value for key, value in expected.items()):
        if not _repair_owned_record(_root(arguments), PLANNING_STATE, "planning", "durable-module-state"):
            return None
        return {"status": "applied", "effects": ["planning-state"], "value": subject}
    return None


def _correction_revision(correction: Mapping[str, Any]) -> str:
    return semantic_digest(
        {
            "correction_id": correction.get("correction_id"),
            "statement": correction.get("statement"),
            "subject": dict(correction.get("subject", {})),
            "applicability": dict(correction.get("applicability", {})),
            "provenance": dict(correction.get("provenance", {})),
            "future_usefulness": correction.get("future_usefulness"),
            "existing_owner": dict(correction.get("existing_owner", {})),
            "deterministic_owner_failure": dict(correction.get("deterministic_owner_failure", {})),
        }
    )


def _planning_accept_correction_failure(arguments: dict[str, Any]) -> dict[str, Any]:
    from .repository_controls import repository_rule_revision

    root = _root(arguments)
    correction = arguments["correction"]
    failure = correction.get("deterministic_owner_failure", {}) if isinstance(correction, Mapping) else {}
    subject = correction.get("subject", {}) if isinstance(correction, Mapping) else {}
    failed_owner = str(failure.get("owner") or "") if isinstance(failure, Mapping) else ""
    owner_ref = arguments["owner_ref"]
    owner_revision = arguments["owner_revision"]
    owner_current = False
    if failed_owner == "repository":
        owner_current = (
            subject.get("kind") == "repository-rule"
            and subject.get("id") == owner_ref
            and repository_rule_revision(root, owner_ref) == owner_revision
        )
    elif failed_owner == "verification":
        policy_path = root / VERIFICATION_POLICY
        try:
            policy = tomllib.loads(policy_path.read_text(encoding="utf-8")) if policy_path.is_file() else {}
        except (OSError, tomllib.TOMLDecodeError):
            policy = {}
        routes = policy.get("routes", []) if isinstance(policy, Mapping) else []
        owner_current = (
            subject.get("kind") == "verification-route"
            and subject.get("id") == owner_ref
            and _revision(policy_path) == owner_revision
            and any(isinstance(route, Mapping) and route.get("id") == owner_ref for route in routes)
        )
    elif failed_owner == "assignment":
        from .orchestration import assignment_evidence_current

        owner_current = assignment_evidence_current(root, owner_ref, owner_revision, subject)
    valid = (
        isinstance(failure, Mapping)
        and isinstance(subject, Mapping)
        and _correction_revision(correction) == arguments["correction_revision"]
        and correction.get("provenance", {}).get("authority") == "human"
        and failure.get("ref") == arguments["owner_ref"]
        and failure.get("revision") == arguments["owner_revision"]
        and owner_current
        and _state_revision(root, PLANNING_STATE) == arguments["expected_state_revision"]
    )
    if not valid:
        return {"status": "rejected", "effects": [], "value": {"reason": "owner-failure-not-established"}}
    outcome = _planning_set(
        {
            "target": str(root),
            "item": f"correction-repair:{correction['correction_id']}",
            "status": "in-progress",
            "outcome": f"Repair deterministic {failed_owner} owner failure: {correction['statement']}",
            "scope": [arguments["owner_ref"]],
            "constraints": [
                f"correction_revision={arguments['correction_revision']}",
                f"failed_owner_revision={arguments['owner_revision']}",
            ],
            "dependencies": [],
            "stops": ["do not create compensating Memory guidance"],
            "proof_claims": ["complete"],
            "expected_state_revision": arguments["expected_state_revision"],
        }
    )
    if outcome["status"] == "applied":
        outcome["value"] = {**outcome["value"], "correction_revision": arguments["correction_revision"]}
    return outcome


def _recover_planning_correction(arguments: dict[str, Any]) -> dict[str, Any] | None:
    root = _root(arguments)
    item = f"correction-repair:{arguments['correction']['correction_id']}"
    subject = _json(root / PLANNING_STATE).get("subjects", {}).get(item)
    if (
        not isinstance(subject, Mapping)
        or f"correction_revision={arguments['correction_revision']}" not in subject.get("constraints", [])
        or not _repair_owned_record(root, PLANNING_STATE, "planning", "durable-module-state")
    ):
        return None
    return {
        "status": "applied",
        "effects": ["planning-state"],
        "value": {**subject, "correction_revision": arguments["correction_revision"]},
    }


def _recover_planning_complete(arguments: dict[str, Any]) -> dict[str, Any] | None:
    return _recover_planning({**arguments, "status": "complete"})


def _planning_reconcile(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    state = _json(root / PLANNING_STATE)
    subject = state.get("subject")
    if not isinstance(subject, dict) or subject.get("semantic_revision") != arguments["expected_subject_revision"]:
        return {"status": "rejected", "effects": [], "value": {"reason": "stale-planning-subject"}}
    disposition = arguments["disposition"]
    next_status = {"integrated": "ready-to-complete", "revise-scope": "in-progress", "residual": "residual"}[
        disposition
    ]
    return _planning_set({"target": str(root), "item": arguments["item"], "status": next_status})


def _recover_planning_reconcile(arguments: dict[str, Any]) -> dict[str, Any] | None:
    expected_status = {
        "integrated": "ready-to-complete",
        "revise-scope": "in-progress",
        "residual": "residual",
    }[arguments["disposition"]]
    return _recover_planning({"target": arguments["target"], "item": arguments["item"], "status": expected_status})


def _planning_record_attempt(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    state = _json(root / PLANNING_STATE)
    subjects = _refresh_planning_subjects(state)
    subject = subjects.get(arguments["item"])
    if (
        not isinstance(subject, dict)
        or subject.get("id") != arguments["item"]
        or subject.get("semantic_revision") != arguments["expected_subject_revision"]
    ):
        return {"status": "rejected", "effects": [], "value": {"reason": "stale-planning-subject"}}
    attempts = state.get("attempts", [])
    if not isinstance(attempts, list):
        return {"status": "rejected", "effects": [], "value": {"reason": "invalid-attempt-state"}}
    attempt = {
        "id": arguments["attempt_id"],
        "item": arguments["item"],
        "subject_revision": arguments["expected_subject_revision"],
        "target_id": arguments["target_id"],
        "status": arguments["status"],
        "result_revision": arguments.get("result_revision") or "",
    }
    attempts = [item for item in attempts if not isinstance(item, dict) or item.get("id") != attempt["id"]]
    attempts.append(attempt)
    state["attempts"] = attempts[-20:]
    if attempt["status"] == "returned":
        subject["status"] = "integration-pending"
        subjects[subject["id"]] = subject
        state["subjects"] = subjects
        active, _, _ = _planning_frontier(state)
        state["subject"] = active or subject
        state["active"] = {"id": state["subject"]["id"], "status": state["subject"]["status"]}
    state["revision"] = int(state.get("revision", 0)) + 1
    _write_owned_json(
        root,
        PLANNING_STATE,
        "planning",
        "durable-module-state",
        state,
        recognizes_existing=lambda item: item.get("schema_version") == 1 and isinstance(item.get("revision"), int),
    )
    return {"status": "applied", "effects": ["planning-state"], "value": attempt}


def _recover_planning_attempt(arguments: dict[str, Any]) -> dict[str, Any] | None:
    root = _root(arguments)
    state = _json(root / PLANNING_STATE)
    attempt = next(
        (
            item
            for item in state.get("attempts", [])
            if isinstance(item, dict)
            and item.get("id") == arguments["attempt_id"]
            and item.get("status") == arguments["status"]
        ),
        None,
    )
    if attempt is None or not _repair_owned_record(root, PLANNING_STATE, "planning", "durable-module-state"):
        return None
    return {"status": "applied", "effects": ["planning-state"], "value": attempt}


def planning_module() -> Module:
    return Module(
        name="planning",
        owns=("planning-state",),
        claims=("progress",),
        contribute=_planning_contribution,
        operations=(
            _operation("planning.set", _planning_set, _recover_planning, accepted_handoffs=("correction",)),
            _operation(
                "planning.accept-correction-failure",
                _planning_accept_correction_failure,
                _recover_planning_correction,
                accepted_handoffs=("correction",),
            ),
            _operation("planning.complete", _planning_complete, _recover_planning_complete),
            _operation("planning.reconcile", _planning_reconcile, _recover_planning_reconcile),
            _operation("planning.record-attempt", _planning_record_attempt, _recover_planning_attempt),
        ),
        currentness=lambda context: (
            semantic_digest(
                {
                    "state": _revision(Path(str(context["target"])).resolve() / PLANNING_STATE),
                    "ownership": _revision(Path(str(context["target"])).resolve() / MANIFEST_STATE),
                    "delegation": _revision(
                        Path(str(context["target"])).resolve() / ".agentic-workspace/local/delegation-attempts.json"
                    ),
                    "request": context.get("planning"),
                }
            )
            if (Path(str(context["target"])).resolve() / PLANNING_STATE).is_file()
            or (Path(str(context["target"])).resolve() / ".agentic-workspace/local/delegation-attempts.json").is_file()
            or context.get("planning") is not None
            else None
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
        if isinstance(records, list) and any(
            isinstance(item, dict) and item.get("key") == record["key"] and item.get("value") == record["value"]
            for item in records
        ):
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
                        "summary": str(requested.get("summary") or requested["value"]),
                        "provenance": str(requested.get("provenance") or "explicit-human-or-repo-source"),
                        "task_terms": list(requested.get("task_terms", [])),
                        "paths": list(requested.get("paths", [])),
                        "dependency_revision": str(requested.get("dependency_revision") or ""),
                        "kind": str(requested.get("kind") or "advisory"),
                    },
                    "effects": ["memory-state"],
                    "priority": 50,
                }
            ],
        }
    if isinstance(requested, Mapping) and requested.get("operation") == "disposition":
        return {
            "revision": _state_revision(root, MEMORY_STATE),
            "actions": [
                {
                    "operation_id": "memory.disposition",
                    "arguments": {
                        "target": str(root),
                        "key": str(requested.get("key") or ""),
                        "disposition": str(requested.get("disposition") or ""),
                        "stronger_owner": str(requested.get("stronger_owner") or ""),
                    },
                    "effects": ["memory-state"],
                    "priority": 50,
                }
            ],
        }
    if not state:
        return None
    task = str(context.get("task") or "").lower()
    changed_paths = [str(path) for path in context.get("changed_paths", [])]
    source_revisions = context.get("source_revisions", {})
    selected = []
    records = state.get("records", [])
    if isinstance(records, list):
        for item in records:
            if not isinstance(item, dict) or item.get("disposition", "active") != "active":
                continue
            terms = item.get("task_terms", [])
            paths = item.get("paths", [])
            dependency_revision = str(item.get("dependency_revision") or "")
            current_dependency = (
                source_revisions.get(item.get("key")) if isinstance(source_revisions, Mapping) else None
            )
            current = not dependency_revision or current_dependency == dependency_revision
            applicable = (terms and any(str(term).lower() in task for term in terms)) or (
                paths and any(fnmatch(path, str(pattern)) for path in changed_paths for pattern in paths)
            )
            if current and applicable:
                selected.append(
                    {
                        "id": item.get("key"),
                        "summary": item.get("summary"),
                        "provenance": item.get("provenance"),
                        "kind": item.get("kind", "advisory"),
                    }
                )
    if not selected:
        return None
    return {
        "revision": _state_revision(root, MEMORY_STATE),
        "facts": {"memory_candidates_selected": selected, "use_status": "selected-not-yet-used"},
        "terminal": True,
    }


def _memory_record(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    path = root / MEMORY_STATE
    expected_revision = str(arguments.get("expected_state_revision") or "")
    if expected_revision and _state_revision(root, MEMORY_STATE) != expected_revision:
        return {"status": "rejected", "effects": [], "value": {"reason": "stale-memory-state"}}
    state = _json(path) or {"schema_version": 1, "revision": 0, "records": []}
    records = state.get("records", [])
    if not isinstance(records, list):
        return {"status": "rejected", "effects": [], "value": {"reason": "invalid-memory-state"}}
    record = {
        "key": arguments["key"],
        "value": arguments["value"],
        "summary": arguments.get("summary") or str(arguments["value"]),
        "provenance": arguments.get("provenance") or "explicit-human-or-repo-source",
        "task_terms": list(arguments.get("task_terms", [])),
        "paths": list(arguments.get("paths", [])),
        "dependency_revision": arguments.get("dependency_revision") or "",
        "kind": arguments.get("kind") or "advisory",
        "disposition": "active",
    }
    if arguments.get("correction_revision"):
        record["correction_revision"] = arguments["correction_revision"]
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
    if any(
        isinstance(item, dict) and item.get("key") == record["key"] and item.get("value") == record["value"]
        for item in state.get("records", [])
    ):
        if not _repair_owned_record(_root(arguments), MEMORY_STATE, "memory", "durable-module-state"):
            return None
        return {"status": "applied", "effects": ["memory-state"], "value": record}
    return None


def _memory_accept_correction(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    correction = arguments["correction"]
    applicability = correction.get("applicability", {}) if isinstance(correction, Mapping) else {}
    valid = (
        isinstance(applicability, Mapping)
        and _correction_revision(correction) == arguments["correction_revision"]
        and correction.get("provenance", {}).get("authority") == "human"
        and not correction.get("existing_owner")
        and not correction.get("deterministic_owner_failure")
        and correction.get("future_usefulness") != "do-not-retain"
        and (
            correction.get("future_usefulness") == "retain"
            or bool(applicability.get("task_terms"))
            or bool(applicability.get("paths"))
            or bool(applicability.get("dependency_revision"))
        )
        and _state_revision(root, MEMORY_STATE) == arguments["expected_state_revision"]
    )
    if not valid:
        return {"status": "rejected", "effects": [], "value": {"reason": "correction-not-retainable"}}
    outcome = _memory_record(
        {
            "target": str(root),
            "key": f"human-correction:{correction['correction_id']}",
            "value": correction["statement"],
            "summary": correction["statement"],
            "provenance": "trusted-human-correction:" + arguments["correction_revision"],
            "task_terms": list(applicability.get("task_terms", [])),
            "paths": list(applicability.get("paths", [])),
            "dependency_revision": str(applicability.get("dependency_revision") or ""),
            "kind": "advisory",
            "expected_state_revision": arguments["expected_state_revision"],
            "correction_revision": arguments["correction_revision"],
        }
    )
    if outcome["status"] == "applied":
        outcome["value"] = {**outcome["value"], "correction_revision": arguments["correction_revision"]}
    return outcome


def _recover_memory_correction(arguments: dict[str, Any]) -> dict[str, Any] | None:
    correction = arguments["correction"]
    record = next(
        (
            item
            for item in _json(_root(arguments) / MEMORY_STATE).get("records", [])
            if isinstance(item, Mapping)
            and item.get("key") == f"human-correction:{correction['correction_id']}"
            and item.get("correction_revision") == arguments["correction_revision"]
        ),
        None,
    )
    if record is None or not _repair_owned_record(_root(arguments), MEMORY_STATE, "memory", "durable-module-state"):
        return None
    return {
        "status": "applied",
        "effects": ["memory-state"],
        "value": {**record, "correction_revision": arguments["correction_revision"]},
    }


def _memory_disposition(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    state = _json(root / MEMORY_STATE)
    records = state.get("records", [])
    if not isinstance(records, list):
        return {"status": "rejected", "effects": [], "value": {"reason": "invalid-memory-state"}}
    changed = False
    for item in records:
        if isinstance(item, dict) and item.get("key") == arguments["key"]:
            item["disposition"] = arguments["disposition"]
            if arguments.get("stronger_owner"):
                item["stronger_owner"] = arguments["stronger_owner"]
            changed = True
    if not changed:
        return {"status": "rejected", "effects": [], "value": {"reason": "unknown-memory"}}
    state["revision"] = int(state.get("revision", 0)) + 1
    _write_owned_json(
        root,
        MEMORY_STATE,
        "memory",
        "durable-module-state",
        state,
        recognizes_existing=lambda item: item.get("schema_version") == 1 and isinstance(item.get("records"), list),
    )
    return {
        "status": "applied",
        "effects": ["memory-state"],
        "value": {"key": arguments["key"], "disposition": arguments["disposition"]},
    }


def _recover_memory_disposition(arguments: dict[str, Any]) -> dict[str, Any] | None:
    root = _root(arguments)
    records = _json(root / MEMORY_STATE).get("records", [])
    current = next(
        (
            item
            for item in records
            if isinstance(item, dict)
            and item.get("key") == arguments["key"]
            and item.get("disposition") == arguments["disposition"]
        ),
        None,
    )
    if current is None or not _repair_owned_record(root, MEMORY_STATE, "memory", "durable-module-state"):
        return None
    return {
        "status": "applied",
        "effects": ["memory-state"],
        "value": {"key": arguments["key"], "disposition": arguments["disposition"]},
    }


def memory_module() -> Module:
    return Module(
        name="memory",
        owns=("memory-state",),
        contribute=_memory_contribution,
        operations=(
            _operation("memory.read", _memory_read),
            _operation("memory.record", _memory_record, _recover_memory_record, accepted_handoffs=("correction",)),
            _operation(
                "memory.accept-correction",
                _memory_accept_correction,
                _recover_memory_correction,
                accepted_handoffs=("correction",),
            ),
            _operation("memory.disposition", _memory_disposition, _recover_memory_disposition),
        ),
        currentness=lambda context: (
            semantic_digest(
                {
                    "state": _revision(Path(str(context["target"])).resolve() / MEMORY_STATE),
                    "ownership": _revision(Path(str(context["target"])).resolve() / MANIFEST_STATE),
                    "request": context.get("memory"),
                    "task": context.get("task"),
                    "changed_paths": context.get("changed_paths", []),
                    "source_revisions": context.get("source_revisions", {}),
                }
            )
            if (Path(str(context["target"])).resolve() / MEMORY_STATE).is_file() or context.get("memory") is not None
            else None
        ),
    )


def _verification_contribution(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    planning = _json(root / PLANNING_STATE)
    raw_active = planning.get("subject") if isinstance(planning.get("subject"), dict) else planning.get("active")
    active = raw_active if isinstance(raw_active, dict) else {}
    needs_proof = active.get("status") == "ready-to-complete"
    path = root / VERIFICATION_STATE
    state = _json(path)
    if not needs_proof and not state:
        return None
    policy_path = root / VERIFICATION_POLICY
    strategy_revision = _revision(policy_path)
    subject_revision = str(
        active.get("semantic_revision") or (_planning_semantic_revision(active) if active else "absent")
    )
    if not needs_proof:
        passed = (
            state.get("status") == "passed"
            and state.get("subject_revision") == subject_revision
            and state.get("strategy_revision") == strategy_revision
        )
        return {
            "revision": _state_revision(root, VERIFICATION_STATE),
            "facts": {"proof": state},
            "claims": {"allowed": ["complete"] if passed else [], "blocked": [] if passed else ["complete"]},
            "terminal": True,
        }
    current_subject = subject_revision
    try:
        policy = tomllib.loads(policy_path.read_text(encoding="utf-8")) if policy_path.is_file() else {}
    except (OSError, tomllib.TOMLDecodeError):
        policy = {}
    strategy_revision = _revision(policy_path)
    current = bool(
        state
        and state.get("subject_revision") == current_subject
        and state.get("strategy_revision") == strategy_revision
        and state.get("status") == "passed"
    )
    actions = []
    if needs_proof and not current:
        routes = policy.get("routes", [])
        required_claims = set(active.get("proof_claims", ["complete"]))
        if not isinstance(routes, list):
            routes = []
        candidates = []
        task = str(context.get("task") or "").lower()
        changed_paths = [str(path) for path in context.get("changed_paths", [])]
        for route in routes:
            if not isinstance(route, dict):
                continue
            route_claims = route.get("claims", [])
            terms = route.get("task_terms", [])
            patterns = route.get("paths", [])
            applicable = (
                (not terms and not patterns)
                or any(str(term).lower() in task for term in terms)
                or any(fnmatch(path, str(pattern)) for path in changed_paths for pattern in patterns)
            )
            if applicable and isinstance(route_claims, list) and required_claims.issubset(set(route_claims)):
                candidates.append(route)
        candidates.sort(key=lambda route: (int(route.get("breadth", 1000)), str(route.get("id") or "")))
        if not candidates:
            return {
                "revision": _state_revision(root, VERIFICATION_STATE),
                "blockers": [
                    {
                        "code": "missing-proof-strategy",
                        "message": "Verification has no current applicable route sufficient for the required claims",
                        "owner": "verification",
                        "recovery": VERIFICATION_POLICY,
                    }
                ],
                "claims": {"blocked": ["complete"]},
            }
        route = candidates[0]
        commands = route.get("commands", [])
        if not isinstance(commands, list) or any(
            not isinstance(command, list) or any(not isinstance(part, str) for part in command) for command in commands
        ):
            return {
                "revision": _state_revision(root, VERIFICATION_STATE),
                "blockers": [
                    {
                        "code": "non-executable-proof-route",
                        "message": "Verification's selected route has no executable typed producer binding",
                        "owner": "verification",
                        "recovery": f"{VERIFICATION_POLICY}#{route.get('id')}",
                    }
                ],
                "claims": {"blocked": ["complete"]},
            }
        actions = [
            {
                "operation_id": "verification.run",
                "arguments": {
                    "target": str(root),
                    "subject_revision": current_subject,
                    "strategy_revision": strategy_revision,
                    "route_id": str(route.get("id") or ""),
                    "commands": commands,
                },
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
        "strategy_revision": arguments["strategy_revision"],
        "route_id": arguments["route_id"],
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
    if (
        state.get("subject_revision") != arguments["subject_revision"]
        or state.get("strategy_revision") != arguments["strategy_revision"]
        or state.get("route_id") != arguments["route_id"]
        or state.get("status")
        not in {
            "passed",
            "failed",
        }
    ):
        return None
    if not _repair_owned_record(root, VERIFICATION_STATE, "verification", "package-residue"):
        return None
    passed = state["status"] == "passed"
    return {
        "status": "applied" if passed else "rejected",
        "effects": ["verification-state", "process"],
        "value": state,
    }


def _verification_accept_correction(arguments: dict[str, Any]) -> dict[str, Any]:
    root = _root(arguments)
    correction = arguments["correction"]
    evidence = correction.get("existing_owner", {}) if isinstance(correction, Mapping) else {}
    subject = correction.get("subject", {}) if isinstance(correction, Mapping) else {}
    policy_path = root / VERIFICATION_POLICY
    try:
        policy = tomllib.loads(policy_path.read_text(encoding="utf-8")) if policy_path.is_file() else {}
    except (OSError, tomllib.TOMLDecodeError):
        policy = {}
    routes = policy.get("routes", []) if isinstance(policy, Mapping) else []
    valid = (
        isinstance(evidence, Mapping)
        and isinstance(subject, Mapping)
        and _correction_revision(correction) == arguments["correction_revision"]
        and correction.get("provenance", {}).get("authority") == "human"
        and evidence.get("owner") == "verification"
        and evidence.get("ref") == arguments["owner_ref"]
        and evidence.get("revision") == arguments["owner_revision"]
        and _revision(policy_path) == arguments["owner_revision"]
        and subject.get("kind") == "verification-route"
        and subject.get("id") == arguments["owner_ref"]
        and any(isinstance(route, Mapping) and route.get("id") == arguments["owner_ref"] for route in routes)
    )
    if not valid:
        return {"status": "rejected", "effects": [], "value": {"reason": "correction-not-enforced-by-owner"}}
    return {
        "status": "unchanged",
        "effects": [],
        "value": {
            "correction_revision": arguments["correction_revision"],
            "owner": "verification",
            "owner_ref": arguments["owner_ref"],
            "owner_revision": arguments["owner_revision"],
            "disposition": "already-owned",
            "justification": "the exact Verification route already enforces this correction",
        },
    }


def verification_module() -> Module:
    return Module(
        name="verification",
        owns=("verification-state", "completion-claim"),
        claims=("complete",),
        contribute=_verification_contribution,
        operations=(
            _operation("verification.run", _verification_run, _recover_verification),
            _operation(
                "verification.accept-correction",
                _verification_accept_correction,
                _verification_accept_correction,
                accepted_handoffs=("correction",),
            ),
        ),
        currentness=lambda context: (
            semantic_digest(
                {
                    "planning": _revision(Path(str(context["target"])).resolve() / PLANNING_STATE),
                    "policy": _revision(Path(str(context["target"])).resolve() / VERIFICATION_POLICY),
                    "evidence": _revision(Path(str(context["target"])).resolve() / VERIFICATION_STATE),
                    "ownership": _revision(Path(str(context["target"])).resolve() / MANIFEST_STATE),
                    "task": context.get("task"),
                    "changed_paths": context.get("changed_paths", []),
                    "claims": context.get("claims", []),
                }
            )
            if any(
                (Path(str(context["target"])).resolve() / relative).is_file()
                for relative in (PLANNING_STATE, VERIFICATION_POLICY, VERIFICATION_STATE)
            )
            else None
        ),
    )
