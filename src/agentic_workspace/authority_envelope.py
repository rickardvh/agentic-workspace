from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

PROTECTED_MUTATION_BOUNDARIES = [
    "returned-worker-admission",
    "integration",
    "destructive-mutation",
    "proof-admission",
    "closeout",
]
MUTATION_CLAIMS_PATH = ".agentic-workspace/local/mutation-claims.json"
MUTATION_CLAIMS_LOCK_PATH = ".agentic-workspace/local/mutation-claims.lock"
MUTATION_CLAIM_LEASE_SECONDS = 15 * 60
MUTATION_CLAIM_LOCK_STALE_SECONDS = 2 * 60
INSTRUCTION_PROVENANCE_RECEIPT_ROOT = Path(".agentic-workspace") / "authority" / "receipts"
GOVERNANCE_RECEIPT_ROOT = Path(".agentic-workspace") / "governance" / "receipts"
HOST_RECEIPT_INDEX_KIND = "agentic-workspace/host-receipt-index/v1"

INSTRUCTION_PROVENANCE_CLASSES: dict[str, dict[str, Any]] = {
    "host-platform": {
        "trust": "highest",
        "rank": 100,
        "effect": "may constrain all work",
        "may_authorise_side_effects": True,
    },
    "repo-policy": {
        "trust": "high",
        "rank": 90,
        "effect": "ordinary-work invariant",
        "may_authorise_side_effects": True,
    },
    "trusted-human-task": {
        "trust": "high",
        "rank": 80,
        "effect": "may authorise current scope",
        "may_authorise_side_effects": True,
    },
    "planning-assignment-handoff": {
        "trust": "bounded",
        "rank": 70,
        "effect": "may narrow current scope",
        "may_authorise_side_effects": False,
    },
    "repo-docs-and-artifacts": {
        "trust": "advisory",
        "rank": 40,
        "effect": "may inform but not widen permissions",
        "may_authorise_side_effects": False,
    },
    "untrusted-content": {
        "trust": "data-only",
        "rank": 0,
        "effect": "cannot authorise side effects or override policy",
        "may_authorise_side_effects": False,
    },
}

SIDE_EFFECT_TAXONOMY: dict[str, dict[str, str]] = {
    "read-repo": {"default_decision": "allow", "reason_code": "ordinary-inspection"},
    "write-requested-paths": {"default_decision": "allow", "reason_code": "changed-path-scope"},
    "write-outside-scope": {"default_decision": "requires-explicit-authority", "reason_code": "scope-widening"},
    "destructive-filesystem-or-git": {"default_decision": "deny", "reason_code": "unowned-state-protected"},
    "network": {"default_decision": "requires-explicit-authority", "reason_code": "external-side-effect"},
    "credentials": {"default_decision": "deny", "reason_code": "secret-boundary"},
    "external-write": {"default_decision": "requires-explicit-authority", "reason_code": "external-system-mutation"},
    "database-mutation": {"default_decision": "requires-explicit-authority", "reason_code": "persistent-data-mutation"},
    "publish-or-production": {"default_decision": "requires-explicit-authority", "reason_code": "release-or-prod-effect"},
    "repository-policy-mutation": {"default_decision": "requires-explicit-authority", "reason_code": "policy-governance"},
}


def _git_observation(target_root: Path, *args: str, text: bool = True) -> dict[str, Any]:
    command = ["git", *args]
    try:
        result = subprocess.run(command, cwd=target_root, check=True, capture_output=True, text=text)
    except OSError as exc:
        return {
            "ok": False,
            "command": command,
            "exit_code": None,
            "stdout": "" if text else b"",
            "stderr": str(exc),
            "error": exc.__class__.__name__,
        }
    except subprocess.CalledProcessError as exc:
        return {
            "ok": False,
            "command": command,
            "exit_code": exc.returncode,
            "stdout": exc.stdout if exc.stdout is not None else "" if text else b"",
            "stderr": exc.stderr if exc.stderr is not None else "",
            "error": exc.__class__.__name__,
        }
    return {
        "ok": True,
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr if result.stderr is not None else "",
        "error": None,
    }


def _git_lines(target_root: Path, *args: str) -> dict[str, Any]:
    result = _git_observation(target_root, *args, text=True)
    result["lines"] = [line for line in str(result.get("stdout") or "").splitlines() if line.strip()]
    return result


def _git_bytes(target_root: Path, *args: str) -> dict[str, Any]:
    result = _git_observation(target_root, *args, text=False)
    stdout = result.get("stdout")
    result["stdout_bytes"] = stdout if isinstance(stdout, bytes) else b""
    return result


def _git_value(target_root: Path, *args: str) -> dict[str, Any]:
    result = _git_lines(target_root, *args)
    lines = result.get("lines") if isinstance(result.get("lines"), list) else []
    result["value"] = str(lines[0]).strip() if lines else ""
    return result


def _list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict_payload(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _host_receipt_path(*, target_root: Path, store_root: Path, receipt_ref: str) -> Path:
    receipt_text = receipt_ref.strip()
    if not receipt_text:
        raise ValueError("receipt ref is required")
    root = (target_root / store_root).resolve()
    if "://" in receipt_text:
        receipt_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", receipt_text.rsplit("/", 1)[-1]).strip("-")
        if not receipt_id:
            raise ValueError("receipt ref has no stable id")
        return root / f"{receipt_id}.json"
    candidate = Path(receipt_text)
    if candidate.is_absolute():
        raise ValueError("receipt ref must be repo-relative")
    resolved = (target_root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("receipt ref must resolve inside the owning receipt store")
    if resolved.suffix != ".json":
        raise ValueError("receipt ref must point to a JSON receipt")
    return resolved


def _load_indexed_host_receipt(*, target_root: Path, store_root: Path, receipt_ref: str) -> dict[str, Any]:
    path = _host_receipt_path(target_root=target_root, store_root=store_root, receipt_ref=receipt_ref)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("receipt must be a JSON object")
    receipt_id = str(payload.get("receipt_id") or payload.get("id") or path.stem).strip()
    index_path = (target_root / store_root / "index.json").resolve()
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(index_payload, dict) or index_payload.get("kind") != HOST_RECEIPT_INDEX_KIND:
        raise ValueError("receipt store index has an invalid kind")
    entry = _dict_payload(_dict_payload(index_payload.get("receipts")).get(receipt_id))
    if not entry:
        raise ValueError("receipt is not registered in its owning index")
    indexed_path = ((target_root / store_root).resolve() / str(entry.get("path") or "")).resolve()
    if indexed_path != path.resolve():
        raise ValueError("receipt index path does not match receipt")
    if str(entry.get("status") or payload.get("status") or "current").strip() not in {"current", "fresh", "accepted"}:
        raise ValueError("receipt is not current")
    if entry.get("superseded_by") or payload.get("superseded_by") or payload.get("revoked_at"):
        raise ValueError("receipt is superseded or revoked")
    indexed_revision = str(entry.get("revision") or "").strip()
    receipt_revision = str(payload.get("revision") or "").strip()
    if indexed_revision and receipt_revision and indexed_revision != receipt_revision:
        raise ValueError("receipt revision does not match index")
    return payload


def _write_indexed_host_receipt(*, target_root: Path, store_root: Path, receipt_id: str, receipt: dict[str, Any]) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", receipt_id.strip()).strip("-")
    if not safe_id:
        raise ValueError("receipt id is required")
    root = target_root / store_root
    root.mkdir(parents=True, exist_ok=True)
    revision = str(receipt.get("revision") or time.time()).strip()
    payload = {
        **receipt,
        "receipt_id": str(receipt.get("receipt_id") or safe_id).strip(),
        "status": str(receipt.get("status") or "current").strip(),
        "revision": revision,
    }
    path = root / f"{safe_id}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_path = root / "index.json"
    index_payload = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {}
    receipts = _dict_payload(index_payload.get("receipts"))
    receipts[payload["receipt_id"]] = {
        "path": f"{safe_id}.json",
        "status": payload["status"],
        "revision": revision,
    }
    index_path.write_text(
        json.dumps({"kind": HOST_RECEIPT_INDEX_KIND, "receipts": receipts}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return f"aw://{store_root.as_posix()}/{safe_id}"


def _claim_store_path(target_root: Path) -> Path:
    return target_root / MUTATION_CLAIMS_PATH


def _claim_lock_path(target_root: Path) -> Path:
    return target_root / MUTATION_CLAIMS_LOCK_PATH


@contextmanager
def _mutation_claim_store_lock(target_root: Path, *, owner_id: str):
    path = _claim_lock_path(target_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    acquired = False
    deadline = time.time() + 1.0
    while not acquired:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                stale = time.time() - path.stat().st_mtime > MUTATION_CLAIM_LOCK_STALE_SECONDS
            except OSError:
                stale = False
            if stale:
                try:
                    path.unlink()
                    continue
                except OSError:
                    pass
            if time.time() >= deadline:
                raise TimeoutError("mutation claim store lock is held by another process")
            time.sleep(0.02)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "kind": "agentic-workspace/mutation-claim-lock/v1",
                        "owner_id": owner_id,
                        "acquired_at": time.time(),
                    },
                    sort_keys=True,
                )
            )
        acquired = True
    try:
        yield
    finally:
        if acquired:
            try:
                path.unlink()
            except OSError:
                pass


def _read_mutation_claims(target_root: Path) -> list[dict[str, Any]]:
    path = _claim_store_path(target_root)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [
            {
                "claim_id": "unreadable-claim-store",
                "owner_id": "unknown",
                "allowed_paths": ["."],
                "status": "unreadable",
            }
        ]
    claims = payload.get("claims", []) if isinstance(payload, dict) else []
    return [claim for claim in claims if isinstance(claim, dict)]


def _write_mutation_claims(target_root: Path, claims: list[dict[str, Any]]) -> None:
    path = _claim_store_path(target_root)
    if not claims:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/mutation-claims/v1",
                "claims": claims,
                "checked_in_repo_effect": "none",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _path_overlaps(left: str, right: str) -> bool:
    left_norm = left.replace("\\", "/").strip("/") or "."
    right_norm = right.replace("\\", "/").strip("/") or "."
    return (
        left_norm == "."
        or right_norm == "."
        or left_norm == right_norm
        or left_norm.startswith(f"{right_norm}/")
        or right_norm.startswith(f"{left_norm}/")
    )


def _claim_is_live(claim: dict[str, Any], now: float) -> bool:
    if str(claim.get("status") or "active") != "active":
        return False
    acquired_at = claim.get("acquired_at_epoch")
    if acquired_at is None:
        return True
    try:
        acquired_epoch = float(acquired_at)
    except (TypeError, ValueError):
        return True
    lease_seconds = claim.get("lease_seconds")
    if lease_seconds is None:
        lease = MUTATION_CLAIM_LEASE_SECONDS
    else:
        try:
            lease = float(lease_seconds)
        except (TypeError, ValueError):
            lease = MUTATION_CLAIM_LEASE_SECONDS
    return now - acquired_epoch <= lease


def _mutation_claim_lifecycle(
    *,
    target_root: Path,
    boundary_id: str,
    owner_id: str,
    allowed_paths: list[str],
    allowed_effects: list[str],
    baseline_id: str | None,
    claim_action: str,
) -> dict[str, Any]:
    action = claim_action if claim_action in {"inspect", "acquire", "release", "acquire-and-release", "cleanup"} else "inspect"
    claim_id = hashlib.sha256(
        json.dumps(
            {
                "owner_id": owner_id,
                "allowed_paths": allowed_paths,
                "allowed_effects": allowed_effects,
                "baseline_id": baseline_id,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    if action == "acquire-and-release":
        return {
            "kind": "agentic-workspace/mutation-claim-lifecycle/v1",
            "status": "rejected-unsupported-pre-release",
            "claim_action": action,
            "claim_id": claim_id,
            "owner_id": owner_id,
            "store_ref": MUTATION_CLAIMS_PATH,
            "lock_ref": MUTATION_CLAIMS_LOCK_PATH,
            "persistent_residue": False,
            "rule": "Protected mutation claims must remain held across the protected operation and be released in a separate finally/closeout step.",
        }
    try:
        with _mutation_claim_store_lock(target_root, owner_id=owner_id):
            now = time.time()
            claims = _read_mutation_claims(target_root)
            live_claims = [claim for claim in claims if _claim_is_live(claim, now)]
            stale_claims = [claim for claim in claims if not _claim_is_live(claim, now)]
            overlap_claims = [
                claim
                for claim in live_claims
                if str(claim.get("owner_id") or "") != owner_id
                and any(
                    _path_overlaps(path, claimed)
                    for path in allowed_paths or ["."]
                    for claimed in _list_payload(claim.get("allowed_paths"))
                )
            ]
            if overlap_claims:
                return {
                    "kind": "agentic-workspace/mutation-claim-lifecycle/v1",
                    "status": "rejected-overlap",
                    "claim_action": action,
                    "claim_id": claim_id,
                    "owner_id": owner_id,
                    "overlap_claims": [
                        {
                            "claim_id": claim.get("claim_id"),
                            "owner_id": claim.get("owner_id"),
                            "allowed_paths": claim.get("allowed_paths"),
                            "baseline_id": claim.get("baseline_id"),
                            "lease_seconds": claim.get("lease_seconds"),
                            "acquired_at_epoch": claim.get("acquired_at_epoch"),
                        }
                        for claim in overlap_claims
                    ],
                    "store_ref": MUTATION_CLAIMS_PATH,
                    "lock_ref": MUTATION_CLAIMS_LOCK_PATH,
                    "stale_recovered_count": len(stale_claims),
                    "rule": "Overlapping live mutation claims from other owners reject before protected mutation admission.",
                }
            if action in {"release", "cleanup"}:
                remaining = [claim for claim in live_claims if not (claim.get("claim_id") == claim_id or claim.get("owner_id") == owner_id)]
                _write_mutation_claims(target_root, remaining)
                return {
                    "kind": "agentic-workspace/mutation-claim-lifecycle/v1",
                    "status": "released",
                    "claim_action": action,
                    "claim_id": claim_id,
                    "owner_id": owner_id,
                    "store_ref": MUTATION_CLAIMS_PATH,
                    "lock_ref": MUTATION_CLAIMS_LOCK_PATH,
                    "persistent_residue": bool(remaining),
                    "stale_recovered_count": len(stale_claims),
                }
            if action == "acquire":
                claim = {
                    "claim_id": claim_id,
                    "owner_id": owner_id,
                    "boundary_id": boundary_id,
                    "allowed_paths": allowed_paths,
                    "allowed_effects": allowed_effects,
                    "baseline_id": baseline_id,
                    "status": "active",
                    "acquired_at_epoch": now,
                    "updated_at_epoch": now,
                    "lease_seconds": MUTATION_CLAIM_LEASE_SECONDS,
                }
                merged = [existing for existing in live_claims if existing.get("claim_id") != claim_id]
                merged.append(claim)
                _write_mutation_claims(target_root, merged)
                return {
                    "kind": "agentic-workspace/mutation-claim-lifecycle/v1",
                    "status": "acquired",
                    "claim_action": action,
                    "claim_id": claim_id,
                    "owner_id": owner_id,
                    "store_ref": MUTATION_CLAIMS_PATH,
                    "lock_ref": MUTATION_CLAIMS_LOCK_PATH,
                    "persistent_residue": True,
                    "stale_recovered_count": len(stale_claims),
                    "lease_seconds": MUTATION_CLAIM_LEASE_SECONDS,
                }
            if stale_claims:
                _write_mutation_claims(target_root, live_claims)
    except TimeoutError:
        return {
            "kind": "agentic-workspace/mutation-claim-lifecycle/v1",
            "status": "rejected-lock-unavailable",
            "claim_action": action,
            "claim_id": claim_id,
            "owner_id": owner_id,
            "store_ref": MUTATION_CLAIMS_PATH,
            "lock_ref": MUTATION_CLAIMS_LOCK_PATH,
            "persistent_residue": False,
            "rule": "Mutation claim read/check/write must occur under the local claim-store lock.",
        }
    return {
        "kind": "agentic-workspace/mutation-claim-lifecycle/v1",
        "status": "inspected-no-overlap",
        "claim_action": action,
        "claim_id": claim_id,
        "owner_id": owner_id,
        "store_ref": MUTATION_CLAIMS_PATH,
        "lock_ref": MUTATION_CLAIMS_LOCK_PATH,
        "persistent_residue": False,
        "rule": "Default protected-boundary inspection rejects existing overlap but does not leave a local claim residue.",
    }


def _status_entry(status: str, path: str, original_path: str | None = None) -> dict[str, Any]:
    normalized_path = path.replace("\\", "/")
    normalized_original = original_path.replace("\\", "/") if original_path else None
    paths = [normalized_path] + ([normalized_original] if normalized_original else [])
    return {
        "path": normalized_path,
        "original_path": normalized_original,
        "paths": paths,
        "index_status": status[0],
        "worktree_status": status[1],
        "untracked": status == "??",
        "managed_local_state": any(item.startswith(".agentic-workspace/local/") for item in paths),
        "rename_or_copy": status[0] in {"R", "C"} or status[1] in {"R", "C"},
        "classification": "untracked" if status == "??" else "staged" if status[0] != " " else "unstaged" if status[1] != " " else "clean",
    }


def _path_identity(target_root: Path, path: str) -> dict[str, Any]:
    normalized = path.replace("\\", "/")
    head_result = _git_value(target_root, "rev-parse", f"HEAD:{normalized}")
    worktree_path = target_root / normalized
    worktree_result = (
        _git_value(target_root, "hash-object", "--", normalized)
        if worktree_path.is_file()
        else {"ok": False, "value": "", "error": "path-not-file", "command": ["git", "hash-object", "--", normalized]}
    )
    return {
        "path": normalized,
        "head_object": str(head_result.get("value") or "") or None,
        "worktree_object": str(worktree_result.get("value") or "") or None,
        "head_observed": bool(head_result.get("ok")),
        "worktree_observed": bool(worktree_result.get("ok")),
    }


def _attach_entry_identities(target_root: Path, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for entry in entries:
        entry_paths = entry.get("paths")
        paths: list[Any]
        if isinstance(entry_paths, list):
            paths = entry_paths
        else:
            paths = [entry.get("path")]
        enriched.append(
            {
                **entry,
                "object_identities": [_path_identity(target_root, str(path)) for path in paths if path],
            }
        )
    return enriched


def _enforcement_fingerprint(*, head: str, scope: list[str], entries: list[dict[str, Any]], assignment: dict[str, Any]) -> str:
    payload = {
        "head": head,
        "scope": scope,
        "entry_count": len(entries),
        "entries": entries,
        "assignment": assignment,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _status_entries_z(target_root: Path, status_args: list[str]) -> dict[str, Any]:
    raw_result = _git_bytes(target_root, *status_args)
    raw = raw_result.get("stdout_bytes") if isinstance(raw_result.get("stdout_bytes"), bytes) else b""
    if not raw:
        return {**raw_result, "entries": []}
    parts = [item.decode("utf-8", errors="surrogateescape") for item in raw.split(b"\0") if item]
    entries: list[dict[str, Any]] = []
    index = 0
    while index < len(parts):
        item = parts[index]
        status = item[:2]
        path = item[3:] if len(item) > 3 else ""
        original_path = None
        if ("R" in status or "C" in status) and index + 1 < len(parts):
            original_path = parts[index + 1]
            index += 1
        entries.append(_status_entry(status=status, path=path, original_path=original_path))
        index += 1
    return {**raw_result, "entries": _attach_entry_identities(target_root, entries)}


def mutation_baseline_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    assignment_target_identity_ref: str | None = None,
    assignment_revision: str | None = None,
) -> dict[str, Any]:
    normalized_paths = [path for path in changed_paths if path]
    head_observation = _git_value(target_root, "rev-parse", "HEAD")
    head = str(head_observation.get("value") or "")
    status_args = ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    if normalized_paths:
        status_args.extend(["--", *normalized_paths])
    status_observation = _status_entries_z(target_root, status_args)
    entries = [entry for entry in status_observation.get("entries", []) if isinstance(entry, dict)]
    observation_errors = (
        [
            {
                "reason": "git-head-observation-failed",
                "command": head_observation.get("command"),
                "exit_code": head_observation.get("exit_code"),
                "diagnostic": str(head_observation.get("stderr") or head_observation.get("error") or ""),
            }
        ]
        if not head_observation.get("ok") or not head
        else []
    )
    if not status_observation.get("ok"):
        observation_errors.append(
            {
                "reason": "git-status-observation-failed",
                "command": status_observation.get("command"),
                "exit_code": status_observation.get("exit_code"),
                "diagnostic": str(status_observation.get("stderr") or status_observation.get("error") or ""),
            }
        )
    assignment = {
        "target_identity_ref": assignment_target_identity_ref,
        "assignment_revision": assignment_revision,
        "comparison": "stable-target-and-assignment-context",
    }
    enforcement_fingerprint = (
        ""
        if observation_errors
        else _enforcement_fingerprint(
            head=head,
            scope=normalized_paths,
            entries=entries,
            assignment=assignment,
        )
    )
    digest_input = {
        "head": head,
        "paths": normalized_paths,
        "status_fingerprint": enforcement_fingerprint,
        "assignment": assignment,
        "observation_errors": observation_errors,
    }
    digest = hashlib.sha256(json.dumps(digest_input, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    dirty = bool(entries)
    revalidation_command = "git status --porcelain=v1 --untracked-files=all -- <changed-paths>"
    comparison_fields = [
        "baseline_id",
        "head",
        "scope.allowed_paths",
        "observed_state.enforcement_fingerprint",
        "observed_state.entry_count",
        "assignment.target_identity_ref",
        "assignment.assignment_revision",
    ]
    fail_closed_reasons = [
        "baseline-observation-failed",
        "baseline-head-changed",
        "unexpected-path-overlap",
        "scoped-state-fingerprint-changed",
        "untracked-managed-state",
        "dirty-scope-not-accounted",
        "renamed-managed-path",
        "assignment-target-mismatch",
        "assignment-revision-mismatch",
        "scope-expanded",
    ]
    return {
        "kind": "agentic-workspace/mutation-baseline/v1",
        "status": "baseline-observation-failed" if observation_errors else "dirty-scope-advisory-baseline" if dirty else "clean-scope",
        "baseline_id": digest,
        "head": head or None,
        "observation": {
            "ok": not observation_errors,
            "head": {
                "ok": bool(head_observation.get("ok")) and bool(head),
                "command": head_observation.get("command"),
                "diagnostic": str(head_observation.get("stderr") or head_observation.get("error") or ""),
            },
            "status": {
                "ok": bool(status_observation.get("ok")),
                "command": status_observation.get("command"),
                "diagnostic": str(status_observation.get("stderr") or status_observation.get("error") or ""),
            },
            "errors": observation_errors,
        },
        "scope": {
            "allowed_paths": normalized_paths,
            "path_count": len(normalized_paths),
            "comparison": "changed-path-scope" if normalized_paths else "whole-worktree-status",
        },
        "assignment": assignment,
        "observed_state": {
            "entry_count": len(entries),
            "entries": entries[:20],
            "enforcement_fingerprint": enforcement_fingerprint or None,
            "enforcement_entry_count": len(entries),
            "enforcement_scope": "full-scoped-status",
            "omitted_entry_count": max(0, len(entries) - 20),
            "untracked_managed_count": len([entry for entry in entries if entry["untracked"] and entry["managed_local_state"]]),
        },
        "ownership": {
            "owner": "current-agent-session",
            "integration_conflict_owner": "current-agent-session-or-human-review",
            "claim": "advisory-observed-baseline",
            "claim_boundary": "This is a point-in-time git baseline for the requested changed-path scope; it is not a lock and cannot prove when dirty state was created.",
        },
        "stale_revalidation": {
            "status": "required",
            "admission": "fail-closed",
            "comparison_fields": comparison_fields,
            "required_before": [
                "destructive action",
                "returned-worker admission",
                "integration",
                "proof admission",
                "completion claim when dirty scope is material",
            ],
            "stop_reasons": fail_closed_reasons,
            "inspect_route": revalidation_command,
            "repair_routes": {
                "baseline-head-changed": "rerun implement after rebasing or refreshing the branch head",
                "unexpected-path-overlap": "inspect overlapping edits and assign ownership before writing",
                "untracked-managed-state": "admit, move, or remove managed local state before claiming closure",
                "renamed-managed-path": "treat rename as scope expansion unless the changed-path owner includes both sides",
                "assignment-target-mismatch": "recompute assignment and handoff for the current target identity",
                "assignment-revision-mismatch": "recompute assignment and handoff for the current assignment revision",
                "scope-expanded": "rerun implement with the widened changed-path scope or ask for authority",
            },
        },
        "boundary_enforcement": {
            "kind": "agentic-workspace/mutation-boundary-enforcement/v1",
            "status": "fail-closed-contract",
            "baseline_id": digest,
            "boundaries": [
                {
                    "id": boundary_id,
                    "read_before": ("git rev-parse HEAD && " if boundary_id == "destructive-mutation" else "") + revalidation_command,
                    "resolver": "admit_live_mutation_boundary",
                    "reject_on": fail_closed_reasons,
                }
                for boundary_id in PROTECTED_MUTATION_BOUNDARIES
            ],
            "clean_noop_rule": "If head, scoped status, allowed paths, target identity, and managed-state checks still match, revalidation does not require a new baseline.",
        },
        "host_enforcement": "fail-closed-at-aw-boundaries",
    }


def compare_mutation_baseline(
    *,
    expected: dict[str, Any],
    current: dict[str, Any],
    assignment_target_identity_ref: str | None = None,
    allowed_paths: list[str] | None = None,
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []

    def reject(reason: str, field: str, repair: str) -> None:
        failures.append({"reason": reason, "field": field, "repair": repair})

    def path_in_scope(path: str, scope: set[str]) -> bool:
        normalized = path.replace("\\", "/").strip("/")
        for item in scope:
            allowed = item.replace("\\", "/").strip("/")
            if allowed in {"", "."}:
                return True
            if normalized == allowed or normalized.startswith(f"{allowed}/"):
                return True
        return False

    expected_observation = expected.get("observation", {}) if isinstance(expected.get("observation"), dict) else {}
    current_observation = current.get("observation", {}) if isinstance(current.get("observation"), dict) else {}
    if expected.get("status") == "baseline-observation-failed" or expected_observation.get("ok") is False:
        reject(
            "baseline-observation-failed",
            "expected.observation",
            "Refresh the expected baseline only after Git head and scoped status are observable.",
        )
    if current.get("status") == "baseline-observation-failed" or current_observation.get("ok") is False:
        reject(
            "baseline-observation-failed",
            "current.observation",
            "Stop this protected boundary until Git head and scoped status are observable.",
        )
    if expected.get("head") != current.get("head"):
        reject("baseline-head-changed", "head", "Refresh the mutation baseline after rebasing or branch movement.")
    expected_scope = set(_as_path for _as_path in expected.get("scope", {}).get("allowed_paths", []) if isinstance(_as_path, str))
    current_scope = set(_as_path for _as_path in current.get("scope", {}).get("allowed_paths", []) if isinstance(_as_path, str))
    if allowed_paths is not None:
        requested_scope = {path for path in allowed_paths if path}
        if not requested_scope.issubset(expected_scope):
            reject("scope-expanded", "scope.allowed_paths", "Rerun implement with the widened changed-path scope.")
        if current_scope and not all(path_in_scope(path, expected_scope) for path in current_scope):
            reject("scope-expanded", "scope.allowed_paths", "Rerun implement with the widened changed-path scope.")
    elif current_scope != expected_scope:
        reject("scope-expanded", "scope.allowed_paths", "Rerun implement with the changed path scope.")
    expected_entries = expected.get("observed_state", {}).get("entries", [])
    current_entries = current.get("observed_state", {}).get("entries", [])
    expected_state = expected.get("observed_state", {}) if isinstance(expected.get("observed_state"), dict) else {}
    current_state = current.get("observed_state", {}) if isinstance(current.get("observed_state"), dict) else {}
    if expected_state.get("entry_count") != current_state.get("entry_count"):
        reject(
            "scoped-state-fingerprint-changed",
            "observed_state.entry_count",
            "Refresh the mutation baseline after scoped Git state changes.",
        )
    expected_fingerprint = expected_state.get("enforcement_fingerprint")
    current_fingerprint = current_state.get("enforcement_fingerprint")
    if expected_fingerprint and current_fingerprint and expected_fingerprint != current_fingerprint:
        reject(
            "scoped-state-fingerprint-changed",
            "observed_state.enforcement_fingerprint",
            "Refresh the mutation baseline after scoped Git state changes, including same-path content changes.",
        )
    expected_paths = {
        str(path)
        for entry in expected_entries
        if isinstance(entry, dict)
        for path in (entry.get("paths") if isinstance(entry.get("paths"), list) else [entry.get("path")])
        if path
    }
    current_paths = {
        str(path)
        for entry in current_entries
        if isinstance(entry, dict)
        for path in (entry.get("paths") if isinstance(entry.get("paths"), list) else [entry.get("path")])
        if path
    }
    if current_paths - expected_paths:
        reject("unexpected-path-overlap", "observed_state.entries", "Inspect overlapping edits and assign ownership before writing.")
    if any(isinstance(entry, dict) and entry.get("managed_local_state") and entry.get("untracked") for entry in current_entries):
        reject("untracked-managed-state", "observed_state.entries", "Admit, move, or remove managed local state before claiming closure.")
    for entry in current_entries:
        if not isinstance(entry, dict) or not entry.get("rename_or_copy"):
            continue
        entry_paths = entry.get("paths") if isinstance(entry.get("paths"), list) else [entry.get("path")]
        if not all(path and path_in_scope(str(path), expected_scope) for path in entry_paths):
            reject(
                "renamed-managed-path",
                "observed_state.entries",
                "Treat rename/copy paths as scope expansion unless both sides are owned.",
            )
    expected_assignment = expected.get("assignment", {}) if isinstance(expected.get("assignment"), dict) else {}
    current_assignment = current.get("assignment", {}) if isinstance(current.get("assignment"), dict) else {}
    expected_target = assignment_target_identity_ref or expected_assignment.get("target_identity_ref")
    current_target = current_assignment.get("target_identity_ref")
    expected_assignment_revision = expected_assignment.get("assignment_revision")
    current_assignment_revision = current_assignment.get("assignment_revision")
    if expected_target and current_target and expected_target != current_target:
        reject(
            "assignment-target-mismatch",
            "assignment.target_identity_ref",
            "Recompute assignment and handoff for the current target identity.",
        )
    if expected_assignment_revision and current_assignment_revision and expected_assignment_revision != current_assignment_revision:
        reject(
            "assignment-revision-mismatch",
            "assignment.assignment_revision",
            "Recompute assignment and handoff for the current assignment revision.",
        )
    admitted = not failures
    return {
        "kind": "agentic-workspace/mutation-baseline-revalidation/v1",
        "status": "admitted" if admitted else "rejected",
        "admitted": admitted,
        "baseline_id": expected.get("baseline_id"),
        "current_baseline_id": current.get("baseline_id"),
        "failures": failures,
        "repair": "none" if admitted else failures[0]["repair"],
        "clean_noop": admitted and expected.get("baseline_id") == current.get("baseline_id"),
        "rule": "Mutation baselines are re-read and compared at admission, integration, destructive mutation, and closeout boundaries before trusting returned work or claims.",
    }


def admit_mutation_boundary(
    *,
    boundary_id: str,
    expected: dict[str, Any] | None,
    current: dict[str, Any] | None,
    assignment_target_identity_ref: str | None = None,
    allowed_paths: list[str] | None = None,
) -> dict[str, Any]:
    boundary = boundary_id.strip() or "unknown"
    if not isinstance(expected, dict) or not isinstance(current, dict) or not expected or not current:
        missing = []
        if not isinstance(expected, dict) or not expected:
            missing.append("expected_mutation_baseline")
        if not isinstance(current, dict) or not current:
            missing.append("current_mutation_baseline")
        return {
            "kind": "agentic-workspace/mutation-boundary-admission/v1",
            "boundary_id": boundary,
            "status": "rejected",
            "admitted": False,
            "reason": "mutation baseline pair was not supplied to this boundary",
            "failures": [
                {
                    "reason": "mutation-baseline-missing",
                    "field": ",".join(missing) or "mutation_baseline",
                    "repair": "Re-read the live repository baseline and compare it to the stored expected baseline before this boundary.",
                }
            ],
            "repair": "Re-read the live repository baseline and compare it to the stored expected baseline before this boundary.",
            "required_for": [
                *PROTECTED_MUTATION_BOUNDARIES,
            ],
            "rule": "Mutation boundaries fail closed: missing expected or current baselines are typed rejections at return, integration, destructive mutation, proof, and closeout boundaries.",
        }
    revalidation = compare_mutation_baseline(
        expected=expected,
        current=current,
        assignment_target_identity_ref=assignment_target_identity_ref,
        allowed_paths=allowed_paths,
    )
    return {
        "kind": "agentic-workspace/mutation-boundary-admission/v1",
        "boundary_id": boundary,
        "status": "admitted" if revalidation["admitted"] else "rejected",
        "admitted": revalidation["admitted"],
        "revalidation": revalidation,
        "failures": revalidation["failures"],
        "repair": revalidation["repair"],
        "rule": (
            "The boundary revalidates the canonical mutation baseline immediately before admitting the operation; "
            "rejection blocks returned work, integration, destructive mutation, and closeout claims."
        ),
    }


def admit_live_mutation_boundary(
    *,
    boundary_id: str,
    target_root: Path | None,
    expected: dict[str, Any] | None,
    assignment_target_identity_ref: str | None = None,
    assignment_revision: str | None = None,
    allowed_paths: list[str] | None = None,
    allowed_effects: list[str] | None = None,
    owner_id: str | None = None,
    claim_action: str = "inspect",
) -> dict[str, Any]:
    """Resolve the current baseline at the protected boundary.

    This is the ordinary protected-front-door helper.  It intentionally accepts
    no caller-provided current baseline; the live state is acquired from Git
    immediately before admission.
    """

    boundary = boundary_id.strip() or "unknown"
    if not isinstance(target_root, Path):
        admission = admit_mutation_boundary(
            boundary_id=boundary,
            expected=expected,
            current=None,
            assignment_target_identity_ref=assignment_target_identity_ref,
            allowed_paths=allowed_paths,
        )
        admission["live_resolution"] = {
            "kind": "agentic-workspace/live-mutation-baseline-resolution/v1",
            "status": "missing-target-root",
            "trusted_supplied_current_baseline": False,
            "source": "boundary.live-snapshot-unavailable",
            "rule": "Protected mutation boundaries must snapshot live Git state themselves; caller-supplied current baselines are not authority.",
        }
        return admission
    expected_assignment = (
        expected.get("assignment", {}) if isinstance(expected, dict) and isinstance(expected.get("assignment"), dict) else {}
    )
    scope = allowed_paths
    if scope is None and isinstance(expected, dict):
        expected_scope = expected.get("scope", {}) if isinstance(expected.get("scope"), dict) else {}
        scope = [str(path) for path in expected_scope.get("allowed_paths", []) if isinstance(path, str)]
    owner = owner_id or "current-agent-session"
    current = mutation_baseline_payload(
        target_root=target_root,
        changed_paths=scope or [],
        assignment_target_identity_ref=assignment_target_identity_ref or expected_assignment.get("target_identity_ref"),
        assignment_revision=assignment_revision or expected_assignment.get("assignment_revision"),
    )
    admission = admit_mutation_boundary(
        boundary_id=boundary,
        expected=expected,
        current=current,
        assignment_target_identity_ref=assignment_target_identity_ref,
        allowed_paths=scope,
    )
    claim_lifecycle = _mutation_claim_lifecycle(
        target_root=target_root,
        boundary_id=boundary,
        owner_id=owner,
        allowed_paths=scope or ["."],
        allowed_effects=[str(effect) for effect in allowed_effects or ["repo-write"]],
        baseline_id=str(current.get("baseline_id") or ""),
        claim_action=claim_action,
    )
    if str(claim_lifecycle["status"]).startswith("rejected"):
        admission["status"] = "rejected"
        admission["admitted"] = False
        admission.setdefault("failures", []).append(
            {
                "reason": "overlapping-mutation-claim"
                if claim_lifecycle["status"] == "rejected-overlap"
                else str(claim_lifecycle["status"]),
                "field": "mutation_claims",
                "repair": "Wait for, supersede, or explicitly clean up the overlapping owner claim before mutating shared paths."
                if claim_lifecycle["status"] == "rejected-overlap"
                else "Acquire the mutation claim under the store lock and release it only after the protected operation finishes.",
            }
        )
        admission["repair"] = (
            "Wait for, supersede, or explicitly clean up the overlapping owner claim before mutating shared paths."
            if claim_lifecycle["status"] == "rejected-overlap"
            else "Acquire the mutation claim under the store lock and release it only after the protected operation finishes."
        )
    admission["current_baseline"] = current
    admission["claim_lifecycle"] = claim_lifecycle
    admission["live_resolution"] = {
        "kind": "agentic-workspace/live-mutation-baseline-resolution/v1",
        "status": "baseline-observation-failed" if current.get("status") == "baseline-observation-failed" else "snapshotted",
        "source": "boundary.live-git-snapshot",
        "boundary_id": boundary,
        "trusted_supplied_current_baseline": False,
        "snapshot_fields": [
            "head",
            "scope.allowed_paths",
            "observed_state.enforcement_fingerprint",
            "observed_state.entry_count",
            "assignment",
            "claim_lifecycle",
        ],
        "rule": "The protected boundary owns live-state acquisition immediately before admission or mutation.",
    }
    return admission


def revalidate_mutation_baseline(
    *,
    target_root: Path,
    expected: dict[str, Any],
    assignment_target_identity_ref: str | None = None,
    allowed_paths: list[str] | None = None,
) -> dict[str, Any]:
    current = mutation_baseline_payload(
        target_root=target_root,
        changed_paths=allowed_paths or list(expected.get("scope", {}).get("allowed_paths", [])),
        assignment_target_identity_ref=assignment_target_identity_ref
        or (expected.get("assignment", {}) if isinstance(expected.get("assignment"), dict) else {}).get("target_identity_ref"),
        assignment_revision=(expected.get("assignment", {}) if isinstance(expected.get("assignment"), dict) else {}).get(
            "assignment_revision"
        ),
    )
    return compare_mutation_baseline(
        expected=expected,
        current=current,
        assignment_target_identity_ref=assignment_target_identity_ref,
        allowed_paths=allowed_paths,
    )


def _normalise_instruction_sources(
    *, target_root: Path, task_text: str | None, instruction_sources: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    sources = [
        {"class": "host-platform", "source": "runtime-host", "trusted_identity": True, "_host_resolved": True},
        {"class": "repo-policy", "source": "repository-config", "trusted_identity": True, "_host_resolved": True},
        {
            "class": "trusted-human-task",
            "source": "task-text",
            "present": bool(task_text),
            "trusted_identity": True,
            "_host_resolved": True,
        },
        {"class": "planning-assignment-handoff", "source": "planning-state", "trusted_identity": True, "_host_resolved": True},
        {"class": "repo-docs-and-artifacts", "source": "repo-material", "trusted_identity": True, "_host_resolved": True},
        {"class": "untrusted-content", "source": "external-content", "trusted_identity": False, "_host_resolved": True},
    ]
    if instruction_sources:
        sources.extend(instruction_sources)
    resolved: list[dict[str, Any]] = []
    for source in sources:
        claimed_class = str(source.get("class") or "untrusted-content").strip()
        receipt: dict[str, Any] = {}
        receipt_ref = str(source.get("trusted_provenance_ref") or source.get("host_provenance_ref") or "").strip()
        if receipt_ref:
            try:
                receipt = _load_indexed_host_receipt(
                    target_root=target_root,
                    store_root=INSTRUCTION_PROVENANCE_RECEIPT_ROOT,
                    receipt_ref=receipt_ref,
                )
            except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                receipt = {}
        receipt_class = str(receipt.get("class") or receipt.get("authority_class") or "").strip()
        host_resolved = bool(source.get("_host_resolved")) or bool(receipt)
        trusted_identity = bool(host_resolved and (source.get("trusted_identity") or receipt))
        source_class = claimed_class
        authority_resolution_status = "trusted-host-boundary" if trusted_identity else "caller-supplied-data"
        if receipt_class in INSTRUCTION_PROVENANCE_CLASSES:
            source_class = receipt_class
            authority_resolution_status = "host-receipt-resolved"
        elif not trusted_identity and claimed_class in {"host-platform", "repo-policy", "trusted-human-task"}:
            source_class = "untrusted-content"
            authority_resolution_status = "blocked-self-asserted-provenance"
        rule = INSTRUCTION_PROVENANCE_CLASSES.get(source_class, INSTRUCTION_PROVENANCE_CLASSES["untrusted-content"])
        resolved.append(
            {
                **source,
                "class": source_class if source_class in INSTRUCTION_PROVENANCE_CLASSES else "untrusted-content",
                "claimed_class": claimed_class,
                "trusted_identity": trusted_identity,
                "trusted_provenance_ref": receipt_ref or None,
                "trusted_provenance_receipt_id": receipt.get("receipt_id"),
                "authority_resolution_status": authority_resolution_status,
                "trust": rule["trust"],
                "rank": rule["rank"],
                "effect": rule["effect"],
                "may_authorise_side_effects": rule["may_authorise_side_effects"],
            }
        )
    return resolved


def _trusted_governance_receipt(*, target_root: Path, policy_mutation: dict[str, Any] | None) -> dict[str, Any] | None:
    receipt_ref = str((policy_mutation or {}).get("trusted_governance_receipt_ref") or "").strip()
    if not receipt_ref:
        return None
    try:
        receipt = _load_indexed_host_receipt(target_root=target_root, store_root=GOVERNANCE_RECEIPT_ROOT, receipt_ref=receipt_ref)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if str(receipt.get("kind") or "") != "agentic-workspace/governance-receipt/v1":
        return None
    authority_class = str(receipt.get("authority_class") or "")
    operation_id = str(receipt.get("operation_id") or "")
    authoriser = str(receipt.get("authoriser") or receipt.get("authorizer") or "")
    policy_revision = str(receipt.get("policy_revision") or "")
    if operation_id != "repository-policy-mutation.authorise":
        return None
    if authority_class not in {"host-platform", "repo-policy", "trusted-human-task"}:
        return None
    if not authoriser or not policy_revision:
        return None
    return {
        "operation_id": operation_id,
        "authority_class": authority_class,
        "authoriser": authoriser,
        "policy_revision": policy_revision,
        "receipt_ref": receipt_ref,
        "receipt_id": receipt.get("receipt_id"),
        "scope": receipt.get("scope") or [],
        "compatibility": receipt.get("compatibility") or "not-recorded",
    }


def _effect_decision(effect_class: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    effect = effect_class.strip() or "unknown"
    rule = SIDE_EFFECT_TAXONOMY.get(effect, {"default_decision": "requires-explicit-authority", "reason_code": "unknown-effect"})
    authorising_sources = [
        source
        for source in sources
        if effect in set(source.get("authorises_effects", []))
        and bool(source.get("may_authorise_side_effects"))
        and bool(source.get("present", True))
    ]
    hostile_wideners = [
        source
        for source in sources
        if effect in set(source.get("requested_effects", []))
        and str(source.get("class")) == "untrusted-content"
        and effect not in {"read-repo"}
    ]
    decision = rule["default_decision"]
    reason_code = rule["reason_code"]
    if hostile_wideners:
        decision = "deny"
        reason_code = "untrusted-content-cannot-widen-authority"
    elif authorising_sources and decision == "requires-explicit-authority":
        decision = "allow"
        reason_code = "explicit-authority-resolved"
    return {
        "class": effect,
        "decision": decision,
        "reason_code": reason_code,
        "authorised_by": [str(source.get("source") or source.get("class")) for source in authorising_sources],
        "hostile_widening_source_count": len(hostile_wideners),
    }


def resolve_authority_effect_envelope(
    *,
    target_root: Path,
    changed_paths: list[str],
    task_text: str | None,
    instruction_sources: list[dict[str, Any]] | None = None,
    requested_effects: list[str] | None = None,
    delegated_authority: dict[str, Any] | None = None,
    policy_mutation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sources = _normalise_instruction_sources(target_root=target_root, task_text=task_text, instruction_sources=instruction_sources)
    effect_classes = list(SIDE_EFFECT_TAXONOMY)
    for effect in requested_effects or []:
        if effect not in effect_classes:
            effect_classes.append(effect)
    decisions = [_effect_decision(effect, sources) for effect in effect_classes]
    allowed_effects = [item["class"] for item in decisions if item["decision"] == "allow"]
    parent_allowed = [str(effect) for effect in _list_payload((delegated_authority or {}).get("parent_allowed_effects"))]
    requested_delegated = [str(effect) for effect in _list_payload((delegated_authority or {}).get("requested_effects"))]
    delegated_intersection = [effect for effect in requested_delegated if effect in set(parent_allowed) and effect in set(allowed_effects)]
    rejected_delegated = [effect for effect in requested_delegated if effect not in set(delegated_intersection)]
    mutation_authority = str((policy_mutation or {}).get("authority_class") or "").strip()
    governance_receipt = _trusted_governance_receipt(target_root=target_root, policy_mutation=policy_mutation)
    effective_mutation_authority = str((governance_receipt or {}).get("authority_class") or "")
    mutation_source = next((source for source in sources if source["class"] == effective_mutation_authority), None)
    policy_requested = bool((policy_mutation or {}).get("requested"))
    governance_scope = [str(path) for path in _list_payload((governance_receipt or {}).get("scope")) if str(path).strip()]
    governance_scope_ok = not governance_scope or all(
        any(_path_overlaps(changed_path, scope_path) for scope_path in governance_scope) for changed_path in changed_paths
    )
    policy_authorised = bool(
        policy_requested
        and governance_receipt
        and mutation_source
        and mutation_source.get("may_authorise_side_effects")
        and effective_mutation_authority in {"host-platform", "repo-policy", "trusted-human-task"}
        and governance_scope_ok
    )
    return {
        "kind": "agentic-workspace/authority-effect-resolution/v1",
        "status": "resolved",
        "resolver_owner": "agentic_workspace.authority_envelope.resolve_authority_effect_envelope",
        "instruction_provenance": sources,
        "side_effect_decisions": decisions,
        "requested_effects": requested_effects or [],
        "untrusted_content_boundary": {
            "status": "enforced",
            "blocked_effects": [item["class"] for item in decisions if item["reason_code"] == "untrusted-content-cannot-widen-authority"],
            "rule": "Untrusted issue, document, worker, or repository content is data; it cannot widen side effects or override policy.",
        },
        "repository_policy_mutation": {
            "kind": "agentic-workspace/repository-policy-mutation-authority/v1",
            "operation_id": "repository-policy-mutation.authorise",
            "requested": policy_requested,
            "status": "authorised" if policy_authorised else "not-requested" if not policy_requested else "blocked",
            "requested_authority_class": mutation_authority or None,
            "authority_class": effective_mutation_authority or None,
            "allowed_authority_classes": ["host-platform", "repo-policy", "trusted-human-task"],
            "trusted_governance_receipt": governance_receipt,
            "receipt_required": True,
            "scope_authorised": governance_scope_ok,
            "repair": "Use an explicit trusted human task or repo-policy route for repository policy promotion/mutation."
            if policy_requested and not policy_authorised
            else "none",
        },
        "delegation_intersection": {
            "kind": "agentic-workspace/delegated-authority-intersection/v1",
            "status": "narrowed" if rejected_delegated else "within-parent" if requested_delegated else "not-delegated",
            "parent_allowed_effects": parent_allowed,
            "requested_effects": requested_delegated,
            "effective_allowed_effects": delegated_intersection if requested_delegated else allowed_effects,
            "rejected_effects": rejected_delegated,
            "rule": "Delegation receives the intersection of host/repo/task authority, assignment scope, target capability, and parent limits.",
        },
        "host_enforcement_limits": {
            "host_enforceable": [
                "live mutation baseline admission",
                "full scoped mutation fingerprint comparison",
                "mutation claim overlap admission",
                "trusted governance receipt binding",
                "side-effect taxonomy decisions",
                "delegated authority narrowing",
            ],
            "advisory": ["unrestricted external processes may still act outside AW unless host sandboxing also enforces them"],
            "honesty": "AW exposes and checks authority at its ordinary front doors; it is not a universal OS sandbox.",
        },
        "mutation_baseline": mutation_baseline_payload(target_root=target_root, changed_paths=changed_paths),
    }


def authority_envelope_payload(*, target_root: Path, changed_paths: list[str], task_text: str | None) -> dict[str, Any]:
    resolution = resolve_authority_effect_envelope(target_root=target_root, changed_paths=changed_paths, task_text=task_text)
    baseline = resolution["mutation_baseline"]
    return {
        "kind": "agentic-workspace/authority-envelope/v1",
        "status": "resolved",
        "authority_resolution": resolution,
        "instruction_provenance": resolution["instruction_provenance"],
        "side_effect_decisions": resolution["side_effect_decisions"],
        "mutation_baseline": baseline,
        "delegation_rule": "Delegated or manual workers receive the intersection of this envelope, assignment scope, target capability, and host limits; they may only narrow it.",
        "enforcement": {
            "host_enforceable": resolution["host_enforcement_limits"]["host_enforceable"],
            "aw_boundary_checks": ["implement context", "handoff packet", "returned-result admission", "proof/closeout"],
            "honesty": resolution["host_enforcement_limits"]["honesty"],
        },
        "detail_route": "agentic-workspace implement --target . --changed <paths> --verbose --format json",
    }
