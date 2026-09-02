"""Dependency-bound reuse for source-owned resolved orchestration conclusions.

This module deliberately stores nothing. It only decides whether an existing
source-owned conclusion is still current for the exact dependencies that owner
declared. Stale conclusions route back to their owner instead of being copied
or reinterpreted by consumers.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _revision(subject: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(subject), sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _proof_policy_identity(proof_policy: Mapping[str, Any]) -> dict[str, Any]:
    policy = dict(proof_policy)
    revision = _text(policy.get("revision"))
    if revision:
        return {"id": policy.get("id"), "revision": revision}
    return {"id": policy.get("id"), "digest": _revision(policy)}


def verification_semantic_dependencies(
    *, semantic_slice: Mapping[str, Any], proof_policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Return only the source identities that can stale semantic Verification work."""

    return {
        "planning_slice": {
            "slice_id": semantic_slice.get("slice_id"),
            "semantic_revision": semantic_slice.get("semantic_revision"),
        },
        "proof_policy": _proof_policy_identity(proof_policy),
    }


def _previous_verification_semantic_dependencies(previous_partition: Mapping[str, Any]) -> dict[str, Any]:
    previous = _mapping(previous_partition)
    semantic = _mapping(previous.get("semantic"))
    return verification_semantic_dependencies(
        semantic_slice=semantic,
        proof_policy=_mapping(semantic.get("proof_policy")),
    )


def reuse_verification_semantic_contribution(
    *,
    previous_partition: Mapping[str, Any],
    semantic_slice: Mapping[str, Any],
    proof_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Reuse a current Verification conclusion or route exact owner re-resolution.

    Assignment target, transport, run, and return identity are intentionally not
    inputs: #2971 partitions those as attempt-specific facts. A retry therefore
    cannot invalidate semantic proof/review reasoning unless its Planning slice
    or proof-policy dependency changed.
    """

    previous = _mapping(previous_partition)
    current_dependencies = verification_semantic_dependencies(
        semantic_slice=semantic_slice,
        proof_policy=proof_policy,
    )
    previous_dependencies = _previous_verification_semantic_dependencies(previous)
    current_revision = _revision(current_dependencies)
    previous_revision = _revision(previous_dependencies)
    previous_semantic = _mapping(previous.get("semantic"))
    decision_revision = _text(previous.get("semantic_contribution_revision"))
    reusable = (
        previous.get("kind") == "agentic-workspace/verification-contribution-partition/v1"
        and bool(previous_semantic)
        and bool(decision_revision)
        and previous_revision == current_revision
    )
    if reusable:
        return {
            "kind": "agentic-workspace/verification-semantic-conclusion-reuse/v1",
            "status": "reused",
            "owner": "verification",
            "decision_revision": decision_revision,
            "dependency_revision": current_revision,
            "dependencies": current_dependencies,
            "semantic": previous_semantic,
            "invalidated_dependencies": [],
            "re_resolution": None,
            "attempt_identity_used": False,
            "target_selection_authority": False,
        }

    changed_dependencies = [
        name
        for name in ("planning_slice", "proof_policy")
        if previous_dependencies.get(name) != current_dependencies.get(name)
    ]
    return {
        "kind": "agentic-workspace/verification-semantic-conclusion-reuse/v1",
        "status": "resolution-required",
        "owner": "verification",
        "decision_revision": decision_revision or None,
        "dependency_revision": current_revision,
        "dependencies": current_dependencies,
        "semantic": None,
        "invalidated_dependencies": changed_dependencies or ["previous-conclusion"],
        "re_resolution": {
            "owner": "verification",
            "action": "resolve-semantic-verification-contribution",
            "reason_code": "resolved-decision-dependency-changed",
        },
        "attempt_identity_used": False,
        "target_selection_authority": False,
    }
