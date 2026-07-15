"""Dependency-scoped identity and compatibility for proof receipts.

The proof subject deliberately describes only the inputs which can affect a
claim.  It is therefore safe to retain evidence across unrelated repository
edits without pretending that a commit timestamp proves freshness.
"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any

PROOF_SUBJECT_KIND = "agentic-workspace/proof-subject/v1"
_MANUAL_CLAIMS = {"manual-review", "documentation-review"}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def build_proof_subject(
    *,
    target_root: Path,
    changed_paths: list[str],
    command: str,
    claim_classes: list[str] | None = None,
    effect_scope: list[str] | None = None,
) -> dict[str, Any]:
    """Build a stable, privacy-preserving subject for one proof claim."""

    claims = sorted({str(value).strip() for value in (claim_classes or ["executable-validation"]) if str(value).strip()})
    paths = sorted({str(value).replace("\\", "/").strip() for value in changed_paths if str(value).strip()})
    sources = []
    unavailable = []
    for relative in paths:
        digest = _file_digest(target_root / relative)
        if digest:
            sources.append({"path": relative, "sha256": digest})
        else:
            unavailable.append(relative)
    manual_only = bool(claims) and set(claims).issubset(_MANUAL_CLAIMS)
    identity_complete = bool(sources) and not unavailable
    if not paths and manual_only and effect_scope:
        identity_complete = True
    canonical = {
        "claim_classes": claims,
        "effect_scope": sorted({str(value).strip() for value in (effect_scope or paths) if str(value).strip()}),
        "source_inputs": sources,
        "command_sha256": hashlib.sha256(str(command).strip().encode("utf-8")).hexdigest(),
        "runtime": {"implementation": platform.python_implementation(), "version": platform.python_version()},
        "identity_complete": identity_complete,
        "unavailable_inputs": unavailable,
    }
    return {
        "kind": PROOF_SUBJECT_KIND,
        "id": f"proof-subject:{_digest(canonical)[:20]}",
        "fingerprint": _digest(canonical),
        **canonical,
        "dependency_scope": "declared-path-and-command",
        "fallback": "whole-state-required" if not identity_complete else "not-required",
        "rule": "Only declared comparison-relevant inputs participate in proof reuse; omitted inputs make reuse conservative.",
    }


def classify_proof_subject(*, target_root: Path, receipt: dict[str, Any], changed_paths: list[str], command: str) -> dict[str, Any]:
    """Classify a stored receipt against the current dependency-scoped subject."""

    stored = receipt.get("proof_subject")
    if not isinstance(stored, dict) or stored.get("kind") != PROOF_SUBJECT_KIND:
        return {
            "status": "unverifiable",
            "reasons": ["legacy-receipt-without-proof-subject"],
            "minimum_rerun_command": command,
            "rule": "Legacy receipts remain visible for migration but cannot demonstrate dependency-scoped equivalence.",
        }
    current = build_proof_subject(
        target_root=target_root,
        changed_paths=changed_paths,
        command=command,
        claim_classes=stored.get("claim_classes") if isinstance(stored.get("claim_classes"), list) else None,
        effect_scope=stored.get("effect_scope") if isinstance(stored.get("effect_scope"), list) else None,
    )
    if not bool(stored.get("identity_complete")) or not bool(current.get("identity_complete")):
        return {"status": "unverifiable", "reasons": ["incomplete-subject-identity"], "minimum_rerun_command": command}
    if stored.get("claim_classes") != current.get("claim_classes"):
        return {"status": "incompatible", "reasons": ["claim-class-changed"], "minimum_rerun_command": command}
    if stored.get("fingerprint") == current.get("fingerprint"):
        return {"status": "reusable", "reasons": ["subject-fingerprint-match"], "minimum_rerun_command": ""}
    stored_paths = {item.get("path") for item in stored.get("source_inputs", []) if isinstance(item, dict)}
    current_paths = {item.get("path") for item in current.get("source_inputs", []) if isinstance(item, dict)}
    if stored_paths.isdisjoint(current_paths):
        return {"status": "partially-reusable", "reasons": ["independent-subject-scope"], "minimum_rerun_command": command}
    return {"status": "stale", "reasons": ["dependency-input-changed"], "minimum_rerun_command": command}
