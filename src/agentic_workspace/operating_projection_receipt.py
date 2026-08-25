"""Task-scoped composition of canonical operating projections.

The receipt is a derived index only.  Route, Verification, selected-proof,
closeout, and runtime-mirror owners remain authoritative for their fields.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Mapping

from agentic_workspace.projection_reuse import (
    build_standard_projection_constituent_identities,
    compare_projection_constituent_sets,
)

_RECEIPT_KIND = "agentic-workspace/operating-projection-receipt/v1"
_INDEX_KIND = "agentic-workspace/operating-projection-identity-index/v1"
_GIT_TIMEOUT_SECONDS = 0.75


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _git(target_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=target_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def observed_stack_context(*, target_root: Path, branch: str = "", head: str = "") -> dict[str, Any]:
    """Return branch/HEAD/base as observational context, never proof authority."""

    branch_value = branch or _git(target_root, "symbolic-ref", "--quiet", "--short", "HEAD")
    head_value = head or _git(target_root, "rev-parse", "HEAD")
    upstream = _git(target_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if not upstream:
        upstream = _git(target_root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    base = _git(target_root, "merge-base", "HEAD", upstream) if upstream else ""
    return {
        "branch": branch_value or "unavailable",
        "head": head_value or "unavailable",
        "base": base or "unavailable",
        "base_ref": upstream or "unavailable",
        "status": "current" if branch_value and head_value and base else "unavailable",
        "rule": "Branch, HEAD, and base describe the observed stack position; they invalidate only owners that declare them as semantic dependencies.",
    }


def _selected_proof_projection(proof_selection: Mapping[str, Any]) -> dict[str, Any]:
    reconciliation = proof_selection.get("proof_receipt_reconciliation", {})
    reconciliation = reconciliation if isinstance(reconciliation, dict) else {}
    commands = reconciliation.get("commands", [])
    commands = commands if isinstance(commands, list) else []
    blocking = [item for item in commands if isinstance(item, dict) and item.get("blocking", True)]
    accepted = reconciliation.get("status") == "accepted" and all(item.get("status") == "accepted" for item in blocking)
    stale_statuses = {"stale", "subject-stale", "mismatched", "failed", "rejected", "partial"}
    observed_statuses = {str(item.get("status") or "") for item in blocking}
    if accepted:
        freshness = "current"
    elif observed_statuses & stale_statuses or str(reconciliation.get("status") or "") in stale_statuses:
        freshness = "stale"
    else:
        freshness = "unknown"
    minimum_rerun_commands = [
        str(item.get("minimum_rerun_command") or item.get("command") or "")
        for item in blocking
        if item.get("status") != "accepted" and str(item.get("minimum_rerun_command") or item.get("command") or "").strip()
    ]
    if not minimum_rerun_commands and not accepted:
        minimum_rerun_commands = [str(item) for item in proof_selection.get("required_commands", []) if str(item).strip()]
    strategy = proof_selection.get("proof_route_strategy_decision", {})
    strategy = strategy if isinstance(strategy, dict) else {}
    broad_escalation = strategy.get("broad_escalation") if strategy.get("outcome") == "broad-escalated" else None
    return {
        "kind": "agentic-workspace/selected-proof-operating-projection/v1",
        "status": "accepted" if accepted else "rerun-required",
        "freshness": freshness,
        "current": accepted,
        "selected_proof_identity": reconciliation.get("selected_proof_identity", {}),
        "reconciliation_status": reconciliation.get("status", "unavailable"),
        "command_states": [
            {
                "command": item.get("command", ""),
                "status": item.get("status", "unknown"),
                "reason": item.get("reason", ""),
                "minimum_rerun_command": item.get("minimum_rerun_command", ""),
            }
            for item in blocking
        ],
        "focused_rerun_commands": list(dict.fromkeys(minimum_rerun_commands)),
        "route_strategy": {
            "outcome": strategy.get("outcome", "unknown"),
            "reason_code": strategy.get("reason_code", ""),
            "claim_effect": strategy.get("claim_effect", ""),
        },
        "broad_escalation": broad_escalation,
        "claim_boundary": "Proof is current only when the canonical receipt reconciliation accepts every blocking selected command for the current proof subject.",
    }


def _owner_projection(value: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value[field] for field in fields if field in value}


def _index_path(target_root: Path, task_text: str) -> Path:
    task_key = hashlib.sha256(" ".join(task_text.split()).encode()).hexdigest()[:20]
    return target_root / ".agentic-workspace/local/projection-cache/operating-projection-receipts" / f"{task_key}.json"


def _load_previous_identities(path: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    identities = payload.get("constituent_identities", {}) if payload.get("kind") == _INDEX_KIND else {}
    return identities if isinstance(identities, dict) else {}


def _record_identities(path: Path, *, task_revision: str, identities: Mapping[str, Any]) -> None:
    record = {
        "kind": _INDEX_KIND,
        "authority": "derived identity index only; canonical owners and proof receipts remain authoritative",
        "task_revision": task_revision,
        "constituent_identities": identities,
    }
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)


def build_operating_projection_receipt(
    *,
    target_root: Path,
    task_text: str,
    changed_paths: list[str],
    admitted_revisions: Mapping[str, Any],
    stack_context: Mapping[str, Any],
    route: Mapping[str, Any],
    verification: Mapping[str, Any],
    proof_selection: Mapping[str, Any],
    closeout_trust: Mapping[str, Any],
    runtime_mirror: Mapping[str, Any],
    persist_identity: bool = True,
) -> dict[str, Any]:
    """Compose owner results and a conservative constituent-level freshness delta."""

    selected_proof = _selected_proof_projection(proof_selection)
    owner_results = {
        "route": _owner_projection(
            route,
            (
                "kind",
                "status",
                "task_relation",
                "owner_posture",
                "required_transition",
                "selected_owner",
                "implementation_allowed",
                "blocked_claims",
            ),
        ),
        "verification": _owner_projection(
            verification,
            ("kind", "status", "configured", "summary", "protocols", "evidence_bundles", "known_gaps"),
        ),
        "selected_proof": selected_proof,
        "closeout_trust": _owner_projection(
            closeout_trust,
            ("kind", "status", "trust", "completion_gate", "claim_boundary", "required_actions", "next_action"),
        ),
        "runtime_mirror": _owner_projection(
            runtime_mirror,
            ("kind", "status", "health", "summary", "findings", "next_action"),
        ),
    }
    input_revisions = dict(admitted_revisions)
    input_revisions["selected_owner"] = input_revisions.get("selected_owner") or "none"
    input_revisions.update({key: stack_context.get(key, "unavailable") for key in ("branch", "head", "base")})
    input_revisions.update(
        {
            "route_inputs": _digest(owner_results["route"]),
            "verification_inputs": _digest(owner_results["verification"]),
            "proof_inputs": _digest(owner_results["selected_proof"]),
            "closeout_inputs": _digest(owner_results["closeout_trust"]),
            "runtime_mirror_inputs": _digest(owner_results["runtime_mirror"]),
        }
    )
    identities = build_standard_projection_constituent_identities(input_revisions=input_revisions)
    index_path = _index_path(target_root, task_text)
    previous = _load_previous_identities(index_path)
    delta = compare_projection_constituent_sets(previous=previous, current=identities)
    if persist_identity:
        _record_identities(index_path, task_revision=str(input_revisions.get("task") or ""), identities=identities)
    proof_attention = selected_proof["freshness"] != "current"
    owner_attention = any(
        str(result.get("status") or "").lower() in {"attention", "blocked", "failed", "unavailable"} for result in owner_results.values()
    )
    return {
        "kind": _RECEIPT_KIND,
        "status": "attention" if proof_attention or owner_attention else "current",
        "authority": {
            "class": "derived-composition-only",
            "canonical_owners": {
                "route": "Planning route decision",
                "verification": "Verification report",
                "selected_proof": ".agentic-workspace/local/proof-receipts",
                "closeout_trust": "workspace closeout trust",
                "runtime_mirror": "runtime mirror consistency",
            },
            "rule": "This receipt does not authorize route transitions, accept proof, or replace any canonical owner.",
        },
        "scope": {"task": task_text, "changed_paths": changed_paths},
        "input_identity": {
            "task": input_revisions.get("task", "unavailable"),
            "selected_owner": input_revisions.get("selected_owner", "unavailable"),
            "planning": input_revisions.get("planning", "unavailable"),
            "changed_paths": input_revisions.get("changed_paths", "unavailable"),
            "proof_subject": input_revisions.get("proof_subject", "unavailable"),
            "runtime_compatibility": input_revisions.get("runtime_compatibility", "unavailable"),
            "owner_input_revisions": {
                field: input_revisions[field]
                for field in (
                    "route_inputs",
                    "verification_inputs",
                    "proof_inputs",
                    "closeout_inputs",
                    "runtime_mirror_inputs",
                )
            },
            "observed_stack_context": dict(stack_context),
            "constituents": identities,
        },
        "freshness_delta": delta,
        "owner_results": owner_results,
        "rerun_guidance": {
            "focused_commands": selected_proof["focused_rerun_commands"],
            "broad_required": bool(selected_proof["broad_escalation"]),
            "broad_escalation": selected_proof["broad_escalation"],
            "rule": "Broad proof is shown only when the existing proof-route strategy records an explicit broad escalation; otherwise rerun only focused stale or unknown proof.",
        },
        "reuse_index": {
            "status": "recorded" if persist_identity else "not-recorded",
            "path": str(index_path.relative_to(target_root)).replace("\\", "/"),
            "stores_proof": False,
            "rule": "The local index stores constituent identities only. Proof evidence remains solely in canonical proof receipts.",
        },
    }
