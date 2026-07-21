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


def _git_value(target_root: Path, *args: str) -> str:
    lines = _git_lines(target_root, *args)
    return lines[0].strip() if lines else ""


def _status_entry(line: str) -> dict[str, Any]:
    status = line[:2]
    path = line[3:] if len(line) > 3 else ""
    return {
        "path": path.replace("\\", "/"),
        "index_status": status[0],
        "worktree_status": status[1],
        "untracked": status == "??",
        "managed_local_state": path.replace("\\", "/").startswith(".agentic-workspace/local/"),
        "classification": "untracked" if status == "??" else "staged" if status[0] != " " else "unstaged" if status[1] != " " else "clean",
    }


def mutation_baseline_payload(*, target_root: Path, changed_paths: list[str]) -> dict[str, Any]:
    normalized_paths = [path for path in changed_paths if path]
    head = _git_value(target_root, "rev-parse", "HEAD")
    status_args = ["status", "--porcelain=v1", "--untracked-files=all"]
    if normalized_paths:
        status_args.extend(["--", *normalized_paths])
    status_lines = _git_lines(target_root, *status_args)
    entries = [_status_entry(line) for line in status_lines]
    digest_input = {"head": head, "paths": normalized_paths, "status": entries}
    digest = hashlib.sha256(json.dumps(digest_input, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    dirty = bool(entries)
    revalidation_command = "git status --porcelain=v1 --untracked-files=all -- <changed-paths>"
    comparison_fields = [
        "baseline_id",
        "head",
        "scope.allowed_paths",
        "observed_state.entries",
        "assignment.target_identity_ref",
    ]
    fail_closed_reasons = [
        "baseline-head-changed",
        "unexpected-path-overlap",
        "untracked-managed-state",
        "dirty-scope-not-accounted",
        "renamed-managed-path",
        "assignment-target-mismatch",
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
                    "id": "closeout",
                    "read_before": revalidation_command,
                    "reject_on": fail_closed_reasons,
                },
            ],
            "clean_noop_rule": "If head, scoped status, allowed paths, target identity, and managed-state checks still match, revalidation does not require a new baseline.",
        },
        "host_enforcement": "fail-closed-at-aw-boundaries",
    }


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
