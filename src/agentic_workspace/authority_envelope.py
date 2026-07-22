from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def _git_lines(target_root: Path, *args: str) -> list[str]:
    try:
        result = subprocess.run(["git", *args], cwd=target_root, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _git_bytes(target_root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(["git", *args], cwd=target_root, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return b""
    return result.stdout


def _git_value(target_root: Path, *args: str) -> str:
    lines = _git_lines(target_root, *args)
    return lines[0].strip() if lines else ""


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


def _status_entries_z(target_root: Path, status_args: list[str]) -> list[dict[str, Any]]:
    raw = _git_bytes(target_root, *status_args)
    if not raw:
        return []
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
    return entries


def mutation_baseline_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    assignment_target_identity_ref: str | None = None,
    assignment_revision: str | None = None,
) -> dict[str, Any]:
    normalized_paths = [path for path in changed_paths if path]
    head = _git_value(target_root, "rev-parse", "HEAD")
    status_args = ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    if normalized_paths:
        status_args.extend(["--", *normalized_paths])
    entries = _status_entries_z(target_root, status_args)
    digest_input = {
        "head": head,
        "paths": normalized_paths,
        "status": entries,
        "assignment_target_identity_ref": assignment_target_identity_ref,
        "assignment_revision": assignment_revision,
    }
    digest = hashlib.sha256(json.dumps(digest_input, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    dirty = bool(entries)
    revalidation_command = "git status --porcelain=v1 --untracked-files=all -- <changed-paths>"
    comparison_fields = [
        "baseline_id",
        "head",
        "scope.allowed_paths",
        "observed_state.entries",
        "assignment.target_identity_ref",
        "assignment.assignment_revision",
    ]
    fail_closed_reasons = [
        "baseline-head-changed",
        "unexpected-path-overlap",
        "untracked-managed-state",
        "dirty-scope-not-accounted",
        "renamed-managed-path",
        "assignment-target-mismatch",
        "assignment-revision-mismatch",
        "scope-expanded",
    ]
    return {
        "kind": "agentic-workspace/mutation-baseline/v1",
        "status": "dirty-scope-advisory-baseline" if dirty else "clean-scope",
        "baseline_id": digest,
        "head": head or None,
        "scope": {
            "allowed_paths": normalized_paths,
            "path_count": len(normalized_paths),
            "comparison": "changed-path-scope" if normalized_paths else "whole-worktree-status",
        },
        "assignment": {
            "target_identity_ref": assignment_target_identity_ref,
            "assignment_revision": assignment_revision,
            "comparison": "stable-target-and-assignment-context",
        },
        "observed_state": {
            "entry_count": len(entries),
            "entries": entries[:20],
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
                    "id": "returned-worker-admission",
                    "read_before": revalidation_command,
                    "reject_on": fail_closed_reasons,
                },
                {
                    "id": "integration",
                    "read_before": revalidation_command,
                    "reject_on": fail_closed_reasons,
                },
                {
                    "id": "destructive-mutation",
                    "read_before": "git rev-parse HEAD && " + revalidation_command,
                    "reject_on": fail_closed_reasons,
                },
                {
                    "id": "proof-admission",
                    "read_before": revalidation_command,
                    "reject_on": fail_closed_reasons,
                },
                {
                    "id": "closeout",
                    "read_before": revalidation_command,
                    "reject_on": fail_closed_reasons,
                },
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
                "returned-worker-admission",
                "integration",
                "destructive-mutation",
                "proof-admission",
                "closeout",
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


def authority_envelope_payload(*, target_root: Path, changed_paths: list[str], task_text: str | None) -> dict[str, Any]:
    baseline = mutation_baseline_payload(target_root=target_root, changed_paths=changed_paths)
    return {
        "kind": "agentic-workspace/authority-envelope/v1",
        "status": "resolved",
        "instruction_provenance": [
            {"class": "host-platform", "trust": "highest", "effect": "may constrain all work"},
            {"class": "repo-policy", "trust": "high", "effect": "ordinary-work invariant"},
            {"class": "trusted-human-task", "trust": "high", "effect": "may authorise current scope", "present": bool(task_text)},
            {"class": "planning-assignment-handoff", "trust": "bounded", "effect": "may narrow current scope"},
            {"class": "repo-docs-and-artifacts", "trust": "advisory", "effect": "may inform but not widen permissions"},
            {"class": "untrusted-content", "trust": "data-only", "effect": "cannot authorise side effects or override policy"},
        ],
        "side_effect_decisions": [
            {"class": "read-repo", "decision": "allow", "reason_code": "ordinary-inspection"},
            {"class": "write-requested-paths", "decision": "allow", "reason_code": "changed-path-scope"},
            {"class": "write-outside-scope", "decision": "requires-explicit-authority", "reason_code": "scope-widening"},
            {"class": "destructive-filesystem-or-git", "decision": "deny", "reason_code": "unowned-state-protected"},
            {"class": "network", "decision": "requires-explicit-authority", "reason_code": "external-side-effect"},
            {"class": "credentials", "decision": "deny", "reason_code": "secret-boundary"},
            {"class": "external-write", "decision": "requires-explicit-authority", "reason_code": "external-system-mutation"},
            {"class": "database-mutation", "decision": "requires-explicit-authority", "reason_code": "persistent-data-mutation"},
            {"class": "publish-or-production", "decision": "requires-explicit-authority", "reason_code": "release-or-prod-effect"},
        ],
        "mutation_baseline": baseline,
        "delegation_rule": "Delegated or manual workers receive the intersection of this envelope, assignment scope, target capability, and host limits; they may only narrow it.",
        "enforcement": {
            "host_enforceable": ["mutation baseline revalidation fails closed at AW admission/integration/closeout boundaries"],
            "aw_boundary_checks": ["implement context", "handoff packet", "returned-result admission", "proof/closeout"],
            "honesty": "This packet guides and rechecks; it is not a sandbox for unrestricted processes.",
        },
        "detail_route": "agentic-workspace implement --target . --changed <paths> --verbose --format json",
    }
