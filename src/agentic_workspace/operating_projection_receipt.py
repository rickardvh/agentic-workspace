"""Task-scoped composition of canonical operating projections.

The receipt is a derived index only.  Route, Verification, selected-proof,
closeout, and runtime-mirror owners remain authoritative for their fields.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping, cast

from agentic_workspace.projection_reuse import (
    build_standard_projection_constituent_identities,
    compare_projection_constituent_sets,
)

_RECEIPT_KIND = "agentic-workspace/operating-projection-receipt/v1"
_INDEX_KIND = "agentic-workspace/operating-projection-result-cache/v3"
_GIT_TIMEOUT_SECONDS = 0.75

ProjectionSource = Mapping[str, Any] | Callable[[], Mapping[str, Any]]
_OWNER_INPUT_PATTERNS = {
    "route_sources": (
        ".agentic-workspace/config.toml",
        ".agentic-workspace/config.local.toml",
        "src/agentic_workspace/config.py",
        "src/agentic_workspace/workspace_runtime_core.py",
        "src/agentic_workspace/workspace_runtime_planning.py",
        "packages/planning/src/repo_planning_bootstrap/installer.py",
    ),
    "verification_sources": (
        ".agentic-workspace/config.toml",
        ".agentic-workspace/config.local.toml",
        ".agentic-workspace/verification/manifest.toml",
        ".agentic-workspace/verification/assurance-evidence-records.json",
        ".agentic-workspace/local/validation-results/history.jsonl",
        "src/agentic_workspace/config.py",
        "src/agentic_workspace/workspace_runtime_core.py",
        "src/agentic_workspace/workspace_runtime_proof.py",
        "packages/verification/src/repo_verification_bootstrap/runtime_primitives.py",
    ),
    "proof_sources": (
        ".agentic-workspace/config.toml",
        ".agentic-workspace/config.local.toml",
        ".agentic-workspace/verification/manifest.toml",
        "src/agentic_workspace/config.py",
        "src/agentic_workspace/contracts/proof_routes.json",
        "src/agentic_workspace/contracts/proof_selection_rules.json",
        "src/agentic_workspace/workspace_runtime_core.py",
        "src/agentic_workspace/workspace_runtime_proof.py",
    ),
    "closeout_sources": (
        ".agentic-workspace/config.toml",
        ".agentic-workspace/config.local.toml",
        ".agentic-workspace/verification/manifest.toml",
        ".agentic-workspace/verification/assurance-evidence-records.json",
        ".agentic-workspace/local/validation-results/history.jsonl",
        ".agentic-workspace/planning/integration-proposals/*.integration-proposal.json",
        ".agentic-workspace/planning/closeout-evidence/*.json",
        "src/agentic_workspace/config.py",
        "src/agentic_workspace/workspace_runtime_core.py",
        "src/agentic_workspace/workspace_runtime_planning.py",
        "src/agentic_workspace/workspace_runtime_proof.py",
        "packages/planning/src/repo_planning_bootstrap/installer.py",
        "packages/verification/src/repo_verification_bootstrap/runtime_primitives.py",
    ),
    "runtime_mirror_sources": (
        ".agentic-workspace/config.toml",
        ".agentic-workspace/config.local.toml",
        "src/agentic_workspace/config.py",
        "src/agentic_workspace/workspace_runtime_core.py",
        "src/agentic_workspace/workspace_runtime_primitives.py",
    ),
    "proof_evidence": (
        ".agentic-workspace/local/proof-receipts/last.json",
        ".agentic-workspace/local/proof-receipts/history.jsonl",
    ),
    "closeout_evidence": (".agentic-workspace/planning/archive/index.json",),
}


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


def _has_glob(pattern: str) -> bool:
    return any(character in pattern for character in "*?[")


def _owner_input_revisions(
    *, target_root: Path, previous_files: Mapping[str, Mapping[str, Any]]
) -> tuple[dict[str, str], dict[str, dict[str, Any]], dict[str, Any]]:
    """Hash actual owner source/config inputs; metadata is evidence, never a content shortcut."""

    group_paths: dict[str, list[tuple[str, str]]] = {}
    unique_paths: dict[str, Path] = {}
    directory_scans = 0
    for group, patterns in _OWNER_INPUT_PATTERNS.items():
        entries: list[tuple[str, str]] = []
        for pattern in patterns:
            if _has_glob(pattern):
                directory_scans += 1
                matches = sorted(path for path in target_root.glob(pattern) if path.is_file())
                if not matches:
                    entries.append((pattern, "<no-matches>"))
                for path in matches:
                    relative = path.relative_to(target_root).as_posix()
                    entries.append((pattern, relative))
                    unique_paths[relative] = path
            else:
                entries.append((pattern, pattern))
                unique_paths[pattern] = target_root / pattern
        group_paths[group] = entries

    current_files: dict[str, dict[str, Any]] = {}
    content_read_paths: list[str] = []
    metadata_match_paths: list[str] = []
    missing_paths: list[str] = []
    stat_count = 0
    for relative, path in sorted(unique_paths.items()):
        try:
            stat = path.stat()
            stat_count += 1
            signature = ":".join(
                str(value)
                for value in (
                    stat.st_size,
                    stat.st_mtime_ns,
                    getattr(stat, "st_ctime_ns", 0),
                    getattr(stat, "st_dev", 0),
                    getattr(stat, "st_ino", 0),
                )
            )
        except OSError:
            signature = "missing"
        previous = previous_files.get(relative, {})
        if signature != "missing" and previous.get("signature") == signature:
            metadata_match_paths.append(relative)
        if signature == "missing":
            digest = "missing"
            missing_paths.append(relative)
        else:
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                content_read_paths.append(relative)
            except OSError:
                digest = "unavailable"
                missing_paths.append(relative)
        current_files[relative] = {"signature": signature, "sha256": digest}

    revisions: dict[str, str] = {}
    for group, entries in group_paths.items():
        identity = [
            {"pattern": pattern, "path": relative, "sha256": current_files.get(relative, {}).get("sha256", relative)}
            for pattern, relative in entries
        ]
        revisions[group] = _digest(identity)
    measurement = {
        "managed_state_content_read_count": len(content_read_paths),
        "managed_state_content_read_paths": content_read_paths,
        "managed_state_metadata_match_count": len(metadata_match_paths),
        "managed_state_metadata_match_paths": metadata_match_paths,
        "managed_state_digest_reuse_count": 0,
        "managed_state_stat_count": stat_count,
        "managed_state_directory_scan_count": directory_scans,
        "managed_state_missing_paths": missing_paths,
    }
    return revisions, current_files, measurement


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


def _load_previous_cache(
    path: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, int]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, {}, {}, {"cache_content_read_count": 0}
    identities = payload.get("constituent_identities", {}) if payload.get("kind") == _INDEX_KIND else {}
    results = payload.get("owner_results", {}) if payload.get("kind") == _INDEX_KIND else {}
    input_files = payload.get("owner_input_files", {}) if payload.get("kind") == _INDEX_KIND else {}
    return (
        identities if isinstance(identities, dict) else {},
        {key: value for key, value in results.items() if isinstance(value, dict)} if isinstance(results, dict) else {},
        {key: value for key, value in input_files.items() if isinstance(value, dict)} if isinstance(input_files, dict) else {},
        {"cache_content_read_count": 1},
    )


def _record_cache(
    path: Path,
    *,
    task_revision: str,
    identities: Mapping[str, Any],
    owner_results: Mapping[str, Mapping[str, Any]],
    owner_input_files: Mapping[str, Mapping[str, Any]],
) -> None:
    record = {
        "kind": _INDEX_KIND,
        "authority": "derived owner-result cache only; canonical owners and proof receipts remain authoritative",
        "task_revision": task_revision,
        "constituent_identities": identities,
        "owner_results": owner_results,
        "owner_input_files": owner_input_files,
        "stores_proof_evidence": False,
    }
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)


def _semantic_input_revisions(*, admitted_revisions: Mapping[str, Any], stack_context: Mapping[str, Any]) -> dict[str, Any]:
    revisions = dict(admitted_revisions)
    revisions["selected_owner"] = revisions.get("selected_owner") or "none"
    revisions.update({key: stack_context.get(key, "unavailable") for key in ("branch", "head", "base")})
    dependency_groups = {
        "route_inputs": ("task", "selected_owner", "planning", "changed_paths", "route_sources"),
        "verification_inputs": ("task", "planning", "changed_paths", "verification_sources"),
        "proof_inputs": ("task", "changed_paths", "proof_subject", "proof_evidence", "proof_sources"),
        "closeout_inputs": (
            "task",
            "selected_owner",
            "planning",
            "changed_paths",
            "proof_subject",
            "proof_evidence",
            "closeout_evidence",
            "branch",
            "closeout_sources",
        ),
        "runtime_mirror_inputs": ("runtime_compatibility", "runtime_mirror_sources"),
    }
    for result_field, fields in dependency_groups.items():
        values = {field: revisions.get(field, "unavailable") for field in fields}
        unavailable = any(str(value or "").strip().lower() in {"", "unknown", "unavailable", "truncated"} for value in values.values())
        revisions[result_field] = "unavailable" if unavailable else _digest(values)
    return revisions


def _build_owner_result(constituent_id: str, source: ProjectionSource) -> dict[str, Any]:
    value: Mapping[str, Any]
    if callable(source):
        value = cast(Callable[[], Mapping[str, Any]], source)()
    else:
        value = cast(Mapping[str, Any], source)
    if constituent_id == "selected_proof":
        return _selected_proof_projection(value)
    fields = {
        "route": (
            "kind",
            "status",
            "task_relation",
            "owner_posture",
            "required_transition",
            "selected_owner",
            "implementation_allowed",
            "blocked_claims",
        ),
        "verification": ("kind", "status", "configured", "summary", "protocols", "evidence_bundles", "known_gaps"),
        "closeout_trust": ("kind", "status", "trust", "completion_gate", "claim_boundary", "required_actions", "next_action"),
        "runtime_mirror": ("kind", "status", "health", "summary", "findings", "next_action"),
    }
    return _owner_projection(value, fields[constituent_id])


def build_operating_projection_receipt(
    *,
    target_root: Path,
    task_text: str,
    changed_paths: list[str],
    admitted_revisions: Mapping[str, Any],
    stack_context: Mapping[str, Any],
    route: ProjectionSource,
    verification: ProjectionSource,
    proof_selection: ProjectionSource,
    closeout_trust: ProjectionSource,
    runtime_mirror: ProjectionSource,
    persist_identity: bool = True,
) -> dict[str, Any]:
    """Compose owner results and a conservative constituent-level freshness delta."""

    started_ns = time.perf_counter_ns()
    index_path = _index_path(target_root, task_text)
    previous_identities, cached_results, previous_input_files, cache_measurement = _load_previous_cache(index_path)
    owner_input_revisions, owner_input_files, owner_input_measurement = _owner_input_revisions(
        target_root=target_root,
        previous_files=previous_input_files,
    )
    input_revisions = _semantic_input_revisions(
        admitted_revisions={**admitted_revisions, **owner_input_revisions},
        stack_context=stack_context,
    )
    identities = build_standard_projection_constituent_identities(input_revisions=input_revisions)
    delta = compare_projection_constituent_sets(previous=previous_identities, current=identities)
    sources = {
        "route": route,
        "verification": verification,
        "selected_proof": proof_selection,
        "closeout_trust": closeout_trust,
        "runtime_mirror": runtime_mirror,
    }
    owner_results: dict[str, dict[str, Any]] = {}
    result_reuse: list[str] = []
    result_constructions: list[str] = []
    for constituent_id, source in sources.items():
        comparison = delta["constituents"].get(constituent_id, {})
        cached = cached_results.get(constituent_id)
        if comparison.get("status") == "reused" and isinstance(cached, dict):
            owner_results[constituent_id] = cached
            result_reuse.append(constituent_id)
        else:
            owner_results[constituent_id] = _build_owner_result(constituent_id, source)
            result_constructions.append(constituent_id)
    if persist_identity:
        _record_cache(
            index_path,
            task_revision=str(input_revisions.get("task") or ""),
            identities=identities,
            owner_results=owner_results,
            owner_input_files=owner_input_files,
        )
    selected_proof = owner_results["selected_proof"]
    proof_attention = selected_proof["freshness"] != "current"
    owner_attention = any(
        str(result.get("status") or "").lower() in {"attention", "blocked", "failed", "unavailable"} for result in owner_results.values()
    ) or bool(delta["unknown_constituents"])
    receipt_build_elapsed_ms = round((time.perf_counter_ns() - started_ns) / 1_000_000, 3)
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
            "owner_source_revisions": {
                field: input_revisions[field]
                for field in (
                    "route_sources",
                    "verification_sources",
                    "proof_sources",
                    "closeout_sources",
                    "runtime_mirror_sources",
                    "proof_evidence",
                    "closeout_evidence",
                )
            },
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
            "owner_result_revisions": {key: _digest(value) for key, value in owner_results.items()},
            "observed_stack_context": dict(stack_context),
            "constituents": identities,
        },
        "freshness_delta": delta,
        "owner_results": owner_results,
        "rerun_guidance": {
            "focused_commands": selected_proof["focused_rerun_commands"],
            "focused_rebuild_constituents": delta["focused_rebuild_constituents"],
            "identity_attention_constituents": delta["unknown_constituents"],
            "broad_required": bool(selected_proof["broad_escalation"]),
            "broad_escalation": selected_proof["broad_escalation"],
            "rule": "Broad proof is shown only when the existing proof-route strategy records an explicit broad escalation; otherwise rerun only focused stale or unknown proof.",
        },
        "reuse_index": {
            "status": "recorded" if persist_identity else "not-recorded",
            "path": str(index_path.relative_to(target_root)).replace("\\", "/"),
            "stores_proof": False,
            "stores_owner_results": True,
            "rule": "The local cache stores admitted derived owner-result projections, never canonical proof evidence. Proof authority remains solely in canonical proof receipts.",
        },
        "construction_profile": {
            **cache_measurement,
            **owner_input_measurement,
            "owner_result_construction_count": len(result_constructions),
            "owner_result_reuse_count": len(result_reuse),
            "constructed_constituents": result_constructions,
            "reused_constituents": result_reuse,
            "duplicate_reconstruction_eliminated": not result_constructions and len(result_reuse) == len(sources),
            "receipt_build_elapsed_ms": receipt_build_elapsed_ms,
            "rule": "Counters and elapsed time are measured in this receipt build. Every semantic dependency is content-hashed; warm unchanged calls reuse admitted owner results without invoking owner builders.",
        },
    }
