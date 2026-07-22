from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

PROTECTED_MUTATION_BOUNDARIES = [
    "returned-worker-admission",
    "integration",
    "destructive-mutation",
    "proof-admission",
    "closeout",
]

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


def _list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _dirty_content_fingerprint(target_root: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, str]] = []
    for entry in entries:
        entry_paths = entry.get("paths")
        paths = entry_paths if isinstance(entry_paths, list) else [entry.get("path")]
        for raw_path in paths:
            path = str(raw_path or "").replace("\\", "/")
            if not path:
                continue
            absolute = target_root / path
            if absolute.is_file():
                digest = hashlib.sha256(absolute.read_bytes()).hexdigest()
                state = "file"
            elif absolute.exists():
                digest = "directory"
                state = "directory"
            else:
                digest = "missing"
                state = "missing"
            items.append({"path": path, "state": state, "sha256": digest})
    items = sorted(items, key=lambda item: (item["path"], item["state"], item["sha256"]))
    return {
        "fingerprint_count": len(items),
        "fingerprints": items[:20],
        "omitted_fingerprint_count": max(0, len(items) - 20),
        "dirty_content_digest": hashlib.sha256(json.dumps(items, sort_keys=True).encode("utf-8")).hexdigest(),
    }


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
    content_fingerprint = _dirty_content_fingerprint(target_root, entries)
    full_status_digest = hashlib.sha256(json.dumps(entries, sort_keys=True).encode("utf-8")).hexdigest()
    digest_input = {
        "head": head,
        "paths": normalized_paths,
        "status": entries,
        "full_status_digest": full_status_digest,
        "dirty_content_digest": content_fingerprint["dirty_content_digest"],
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
        "dirty-scope-changed",
        "live-git-unavailable",
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
            "git_status": "observed" if head else "unavailable",
            "entry_count": len(entries),
            "full_status_digest": full_status_digest,
            "dirty_content_digest": content_fingerprint["dirty_content_digest"],
            "entries": entries[:20],
            "omitted_entry_count": max(0, len(entries) - 20),
            "fingerprints": content_fingerprint["fingerprints"],
            "fingerprint_count": content_fingerprint["fingerprint_count"],
            "omitted_fingerprint_count": content_fingerprint["omitted_fingerprint_count"],
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

    if expected.get("head") != current.get("head"):
        reject("baseline-head-changed", "head", "Refresh the mutation baseline after rebasing or branch movement.")
    expected_observed = expected.get("observed_state", {}) if isinstance(expected.get("observed_state"), dict) else {}
    current_observed = current.get("observed_state", {}) if isinstance(current.get("observed_state"), dict) else {}
    if current_observed.get("git_status") == "unavailable" or not current.get("head"):
        reject("live-git-unavailable", "observed_state.git_status", "Resolve Git status/HEAD before admitting this boundary.")
    if expected_observed.get("full_status_digest") and current_observed.get("full_status_digest"):
        if expected_observed.get("full_status_digest") != current_observed.get("full_status_digest"):
            reject(
                "dirty-scope-not-accounted",
                "observed_state.full_status_digest",
                "Refresh the mutation baseline for the changed scoped status.",
            )
    if expected_observed.get("dirty_content_digest") and current_observed.get("dirty_content_digest"):
        if expected_observed.get("dirty_content_digest") != current_observed.get("dirty_content_digest"):
            reject(
                "dirty-scope-changed",
                "observed_state.dirty_content_digest",
                "Refresh the mutation baseline after same-path dirty content changed.",
            )
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
    expected_entries = expected_observed.get("entries", [])
    current_entries = current_observed.get("entries", [])
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
    admission["current_baseline"] = current
    admission["live_resolution"] = {
        "kind": "agentic-workspace/live-mutation-baseline-resolution/v1",
        "status": "snapshotted",
        "source": "boundary.live-git-snapshot",
        "boundary_id": boundary,
        "trusted_supplied_current_baseline": False,
        "snapshot_fields": ["head", "scope.allowed_paths", "observed_state.entries", "assignment"],
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


def _normalise_instruction_sources(*, task_text: str | None, instruction_sources: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    sources = [
        {"class": "host-platform", "source": "runtime-host"},
        {"class": "repo-policy", "source": "repository-config"},
        {"class": "trusted-human-task", "source": "task-text", "present": bool(task_text)},
        {"class": "planning-assignment-handoff", "source": "planning-state"},
        {"class": "repo-docs-and-artifacts", "source": "repo-material"},
        {"class": "untrusted-content", "source": "external-content"},
    ]
    if instruction_sources:
        sources.extend(instruction_sources)
    resolved: list[dict[str, Any]] = []
    for source in sources:
        source_class = str(source.get("class") or "untrusted-content").strip()
        rule = INSTRUCTION_PROVENANCE_CLASSES.get(source_class, INSTRUCTION_PROVENANCE_CLASSES["untrusted-content"])
        resolved.append(
            {
                **source,
                "class": source_class if source_class in INSTRUCTION_PROVENANCE_CLASSES else "untrusted-content",
                "trust": rule["trust"],
                "rank": rule["rank"],
                "effect": rule["effect"],
                "may_authorise_side_effects": rule["may_authorise_side_effects"],
            }
        )
    return resolved


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
    sources = _normalise_instruction_sources(task_text=task_text, instruction_sources=instruction_sources)
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
    mutation_source = next((source for source in sources if source["class"] == mutation_authority), None)
    policy_requested = bool((policy_mutation or {}).get("requested"))
    policy_authorised = bool(
        policy_requested
        and mutation_source
        and mutation_source.get("may_authorise_side_effects")
        and mutation_authority in {"host-platform", "repo-policy", "trusted-human-task"}
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
            "authority_class": mutation_authority or None,
            "allowed_authority_classes": ["host-platform", "repo-policy", "trusted-human-task"],
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
            "host_enforceable": ["live mutation baseline admission", "side-effect taxonomy decisions", "delegated authority narrowing"],
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
