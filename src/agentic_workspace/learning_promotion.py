"""Evidence- and authority-bounded promotion into existing repo owners."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

_DETERMINISTIC = {"test-check", "scaffold-generator", "command-operation", "config-contract", "code-boundary"}
_PROCEDURAL = {"skill", "runbook", "command", "helper"}
_HUMAN_OWNED = {"canonical-docs", "policy", "architecture", "public-contract", "security"}
_MATERIAL_EFFECTIVENESS = {
    "product-repo-interface-defect",
    "successful-evidenced-reuse",
    "insufficient-or-incorrect-learning",
}
_TERMINAL = {"already-absorbed", "completed", "dismissed", "retired", "superseded"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _texts(value: Any) -> list[str]:
    return list(dict.fromkeys(str(item).strip() for item in _as_list(value) if str(item).strip()))


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _status(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _proof_complete(candidate: dict[str, Any], operation: dict[str, Any]) -> bool:
    result = _as_dict(candidate.get("operation_result"))
    proof = _as_dict(candidate.get("promotion_proof"))
    owner_revision = str(result.get("owner_revision") or "")
    return bool(
        operation
        and operation.get("operation_id")
        and operation.get("expected_input_revision")
        and result.get("status") == "succeeded"
        and result.get("operation_id") == operation.get("operation_id")
        and result.get("expected_input_revision") == operation.get("expected_input_revision")
        and owner_revision
        and proof.get("status") == "passed"
        and proof.get("operation_id") == operation.get("operation_id")
        and proof.get("owner_revision") == owner_revision
        and bool(_texts(proof.get("evidence_refs")))
    )


def _subtraction(candidate: dict[str, Any], *, completed: bool) -> dict[str, Any]:
    if not completed:
        return {"status": "not-ready", "disposition": "retain", "remove_duplicate_refs": []}
    if candidate.get("durable_anti_rediscovery_value") is True:
        disposition = "retain"
    elif candidate.get("discovery_stub_required") is True:
        disposition = "stub"
    elif candidate.get("partial_advisory_value_remains") is True:
        disposition = "shrink"
    else:
        disposition = "delete"
    return {
        "status": "ready",
        "disposition": disposition,
        "remove_duplicate_refs": _texts(candidate.get("duplicate_owner_refs")),
        "canonical_owner_ref": str(candidate.get("target_owner_ref") or ""),
        "rule": "One owner retains substantive truth; provisional residue remains only when it still reduces future decision or discovery cost.",
    }


def _decision(candidate: dict[str, Any], *, improvement_latitude: str) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or candidate.get("id") or "")
    target_class = _status(candidate.get("target_class"))
    lifecycle = _status(candidate.get("lifecycle") or "active")
    effectiveness = _status(candidate.get("effectiveness_class"))
    evidence_count = int(candidate.get("material_evidence_count") or 0)
    authority = _status(candidate.get("evidence_authority"))
    operations = _as_dict(candidate.get("owner_operations"))
    operation = _as_dict(operations.get(target_class))
    stronger_owner = _as_dict(candidate.get("stronger_owner"))

    disposition = "retain-provisional"
    reason = "material promotion evidence is not yet sufficient"
    owner = str(candidate.get("provisional_owner") or "future-learning-owner")
    next_route = "retain the provisional owner and collect authoritative later evidence"
    requires_review = False

    if lifecycle in _TERMINAL:
        disposition = lifecycle
        reason = "terminal promotion pressure is quiet"
        next_route = ""
    elif stronger_owner.get("status") == "current" and stronger_owner.get("implements_behavior") is True:
        disposition = "already-absorbed"
        reason = "the current stronger owner already implements the learned behavior"
        owner = str(stronger_owner.get("owner") or owner)
        next_route = "subtract duplicate provisional residue"
    elif _status(candidate.get("scope_class")) == "target-specific":
        disposition = "keep-target-specific"
        reason = "the evidence describes one target rather than shared repository truth"
        owner = str(candidate.get("target_owner") or owner)
        next_route = "retain through existing target guidance or suitability ownership"
    elif candidate.get("durable_anti_rediscovery_value") is True and not target_class:
        disposition = "retain-provisional"
        reason = "no stronger owner removes the advisory lesson's anti-rediscovery value"
        next_route = "retain the bounded advisory in Memory or its existing owner"
    elif (
        effectiveness not in _MATERIAL_EFFECTIVENESS
        or evidence_count < 2
        or authority
        in {
            "",
            "agent-self-report",
            "candidate",
            "unavailable",
        }
    ):
        disposition = "refine-revalidate" if effectiveness else "retain-provisional"
        reason = "recurrence count, one success, or low-authority evidence cannot authorize canonical mutation"
        next_route = "refine or revalidate through the provisional source owner"
    elif candidate.get("increases_total_future_cost") is True or candidate.get("weakens_proof_or_security") is True:
        disposition = "reject-or-human-review"
        reason = "the proposed owner would widen risk, weaken proof/security, or increase total future cost"
        owner = str(candidate.get("authority_owner") or "human-domain-owner")
        next_route = "obtain explicit owner review or reject the promotion"
        requires_review = True
    elif target_class in _HUMAN_OWNED and _as_dict(candidate.get("authority_admission")).get("status") != "admitted":
        disposition = "human-admission-required"
        reason = "human/domain-owned semantic change lacks explicit current admission"
        owner = str(candidate.get("authority_owner") or "human-domain-owner")
        next_route = "obtain explicit admission before using the existing canonical owner operation"
        requires_review = True
    elif target_class in _DETERMINISTIC | _PROCEDURAL | _HUMAN_OWNED:
        owner = str(candidate.get("target_owner") or target_class)
        if improvement_latitude not in {"proactive", "delegated"} and target_class not in _HUMAN_OWNED:
            disposition = "route-repo-improvement"
            reason = "a valid stronger-owner opportunity exceeds configured repo-directed initiative latitude"
            owner = "repo-improvement"
            next_route = "preserve awareness through existing repo-improvement pressure"
        elif not operation.get("operation_id") or not operation.get("expected_input_revision"):
            disposition = "route-repo-improvement"
            reason = "the selected owner has no revision-bound existing mutation operation"
            owner = "repo-improvement"
            next_route = "route through the existing improvement owner until a typed owner operation exists"
        elif _proof_complete(candidate, operation):
            disposition = "promoted-complete"
            reason = "the existing owner operation and revision-bound proof implement the learned behavior"
            next_route = "apply the explicit provisional subtraction disposition"
        else:
            disposition = "promotion-ready"
            reason = "material evidence and authority select an existing revision-bound owner operation"
            next_route = f"invoke existing {target_class} owner operation and prove the resulting owner revision"
    else:
        disposition = "route-repo-improvement"
        reason = "the broader structural owner is not yet safe or specific enough to mutate"
        owner = "repo-improvement"
        next_route = "retain existing improvement pressure without premature canonical mutation"

    completed = disposition in {"promoted-complete", "already-absorbed"}
    identity = {
        "candidate_id": candidate_id,
        "provisional_identity": _as_dict(candidate.get("provisional_identity")),
        "target_class": target_class,
        "target_owner_ref": str(candidate.get("target_owner_ref") or ""),
        "source_owner_revision": str(candidate.get("source_owner_revision") or ""),
        "disposition": disposition,
    }
    return {
        "kind": "agentic-workspace/learning-promotion-decision/v1",
        "decision_id": f"learning-promotion:{_digest(identity)[:16]}",
        **identity,
        "reason": reason,
        "owner": owner,
        "next_route": next_route,
        "requires_human_review": requires_review,
        "operation_invocation": operation if disposition in {"promotion-ready", "promoted-complete"} else {},
        "subtraction": _subtraction(candidate, completed=completed),
        "terminal": lifecycle in _TERMINAL or disposition in {"promoted-complete", "already-absorbed"},
    }


def compile_learning_promotion(
    candidates: Iterable[dict[str, Any]] | None,
    *,
    improvement_latitude: str = "conservative",
) -> dict[str, Any]:
    """Select stronger existing owners without creating a promotion mutation API."""

    source = [dict(item) for item in (candidates or []) if isinstance(item, dict)]
    decisions = [_decision(item, improvement_latitude=_status(improvement_latitude)) for item in source]
    active = [item for item in decisions if not item["terminal"]]
    findings = []
    for item in active:
        disposition = str(item["disposition"])
        if disposition in {"retain-provisional", "keep-target-specific"}:
            continue
        finding_class = "architecture-conflict" if item["requires_human_review"] else "learning-promotion"
        finding: dict[str, Any] = {
            "kind": "agentic-workspace/learning-promotion-finding/v1",
            "id": str(item["decision_id"]),
            "finding_class": finding_class,
            "promotion_disposition": disposition,
            "severity": "medium",
            "lifecycle": "unresolved",
            "owner": str(item["owner"]),
            "next_route": str(item["next_route"]),
            "task_relevant": True,
            "dedupe_identity": str(item["decision_id"]),
        }
        operation = _as_dict(item.get("operation_invocation"))
        if disposition == "promotion-ready" and operation:
            finding["safe_repair"] = operation
        findings.append(finding)
    return {
        "kind": "agentic-workspace/learning-promotion-set/v1",
        "status": "attention" if findings else "quiet",
        "input_revision": "sha256:" + _digest({"candidates": source, "latitude": improvement_latitude}) if source else "",
        "candidate_count": len(source),
        "decisions": decisions,
        "findings": findings,
        "canonical_store_created": False,
        "generic_mutation_operation_created": False,
        "rule": "Promotion selects an existing owner operation; evidence, authority, latitude, currentness, proof, and post-promotion subtraction remain explicit.",
    }
