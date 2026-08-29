"""Sparse, cross-owner effectiveness for admitted future learning.

The compiler joins existing destination identity/revision and canonical
operating-decision identity to later source-owned outcomes.  It deliberately
does not assign a universal learning id or retain ordinary projection/use
events.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

_TERMINAL = {"dismissed", "fixed", "promoted", "resolved", "retired", "superseded"}
_STRONG_AUTHORITIES = {
    "current-repo-authority",
    "evaluation-result",
    "human-correction",
    "proof-receipt",
    "reviewer-finding",
    "target-outcome-evidence",
    "test-result",
    "verification-receipt",
}


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


def _identity(projection: dict[str, Any]) -> dict[str, str]:
    identity = _as_dict(projection.get("owner_identity"))
    return {str(key): str(value) for key, value in sorted(identity.items()) if str(value).strip()}


def _join_key(destination: str, identity: dict[str, str]) -> str:
    stable_identity = {
        key: value
        for key, value in identity.items()
        if key not in {"fact_revision", "guidance_revision", "candidate_revision", "aid_revision", "revision"}
    }
    return f"{destination}:{_digest(stable_identity)[:20]}" if destination and stable_identity else ""


def _owner_revision(identity: dict[str, str]) -> str:
    for key in ("fact_revision", "guidance_revision", "candidate_revision", "aid_revision", "revision"):
        if identity.get(key):
            return identity[key]
    return ""


def _classification(*, projection: dict[str, Any], outcome: dict[str, Any]) -> tuple[str, str]:
    if not projection or outcome.get("projected") is False or outcome.get("guidance_was_surfaced") is False:
        return "routing_projection_miss", "the relevant admitted owner revision did not reach the affected decision"

    projected_identity = _identity(projection)
    outcome_identity = _identity(outcome)
    projected_revision = _owner_revision(projected_identity)
    outcome_revision = _owner_revision(outcome_identity)
    authority_status = _status(outcome.get("current_authority_status"))
    if authority_status in {"stale", "superseded", "contradicted"} or (
        projected_revision and outcome_revision and projected_revision != outcome_revision
    ):
        return "stale_or_contradicted_learning", "newer owner or repository authority invalidates the projected revision"

    authority = _status(outcome.get("evidence_authority"))
    if authority not in _STRONG_AUTHORITIES:
        return "outcome_inconclusive", "later attribution lacks independent owner, human, proof, test, or repository authority"

    reported = _status(outcome.get("outcome"))
    correct_but_costly = outcome.get("guidance_correct") is True and outcome.get("deterministic_cost_recurred") is True
    if correct_but_costly:
        return "product_repo_interface_defect", "correct projected guidance still leaves a repeated deterministic cost"
    if reported in {"resolved-by-stronger-owner", "absorbed"}:
        return "resolved_by_stronger_owner", "a proved stronger owner absorbed the lesson"
    if reported in {"no-material-follow-up", "aligned"}:
        return "no_material_follow_up", "later evidence does not justify a durable consequence"
    if reported in {"incorrect", "insufficient", "recurrence"}:
        return "insufficient_or_incorrect_learning", "authoritative recurrence shows that the retained semantics were insufficient"
    if reported in {"violated", "ignored", "contradicted"}:
        if str(projection.get("destination") or "") in {"target-guidance", "agent-guidance"}:
            return "target_noncompliance_candidate", "independent evidence shows surfaced target-specific guidance was violated"
        return "insufficient_or_incorrect_learning", "recurrence after projection requires refinement rather than presumed blame"
    if reported in {"product-defect", "repo-defect", "interface-defect"}:
        return "product_repo_interface_defect", "authoritative recurrence belongs to a stronger correct-by-design owner"
    if reported in {"successful-reuse", "shortcut-used", "aid-used"}:
        count = int(outcome.get("comparable_use_count") or 0)
        value = _status(outcome.get("material_value"))
        if outcome.get("actual_use_demonstrated") is True and value in {"avoided", "reduced", "material"} and count >= 2:
            return "successful_evidenced_reuse", "multiple later comparable uses independently demonstrate material value"
        return "outcome_inconclusive", "one success, missing use proof, or absence of failure cannot establish usefulness"
    return "outcome_inconclusive", "later evidence does not establish a supported effectiveness class"


def _route(*, classification: str, projection: dict[str, Any]) -> tuple[str, str]:
    destination = str(projection.get("destination") or "future-context-routing")
    owner = str(projection.get("owner") or destination)
    if classification == "routing_projection_miss":
        return "context-routing", "repair relevance, projection, or context routing through the existing owner"
    if classification == "target_noncompliance_candidate":
        return owner, "route independent evidence through existing target guidance, suitability, and review consequences"
    if classification == "product_repo_interface_defect":
        return "repo-improvement", "route deterministic recurring cost through the existing repo-improvement consequence path"
    if classification == "successful_evidenced_reuse":
        return owner, "route demonstrated reuse to the existing aid or adaptation promotion path"
    return owner, f"revalidate, refine, supersede, or retire the current {destination} owner revision"


def compile_learning_effectiveness(
    projections: Iterable[dict[str, Any]] | None,
    outcomes: Iterable[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Join only material later outcomes to existing learning owner identities."""

    projected = [dict(item) for item in (projections or []) if isinstance(item, dict)]
    later = [dict(item) for item in (outcomes or []) if isinstance(item, dict)]
    active = [item for item in projected if _status(item.get("lifecycle") or "active") not in _TERMINAL]
    terminal_keys = {
        _join_key(str(item.get("destination") or ""), _identity(item))
        for item in projected
        if _status(item.get("lifecycle") or "active") in _TERMINAL
    }
    by_key = {
        _join_key(str(item.get("destination") or ""), _identity(item)): item
        for item in active
        if _join_key(str(item.get("destination") or ""), _identity(item))
    }
    evaluations: list[dict[str, Any]] = []
    findings_by_key: dict[str, dict[str, Any]] = {}

    for outcome in later:
        destination = str(outcome.get("destination") or "")
        join_key = _join_key(destination, _identity(outcome))
        if join_key in terminal_keys:
            continue
        projection = _as_dict(by_key.get(join_key))
        classification, reason = _classification(projection=projection, outcome=outcome)
        decision_id = str(outcome.get("decision_id") or projection.get("decision_id") or "")
        failure_identity = str(outcome.get("failure_identity") or outcome.get("evidence_revision") or "")
        evaluation_identity = {
            "owner_join_key": join_key,
            "decision_id": decision_id,
            "failure_identity": failure_identity,
            "classification": classification,
        }
        evaluation_id = f"learning-effect:{_digest(evaluation_identity)[:16]}"
        evaluation = {
            "kind": "agentic-workspace/learning-effectiveness-evaluation/v1",
            "evaluation_id": evaluation_id,
            "destination": destination or str(projection.get("destination") or "unknown"),
            "owner_identity": _identity(outcome) or _identity(projection),
            "decision_id": decision_id,
            "failure_identity": failure_identity,
            "classification": classification,
            "reason": reason,
            "evidence_authority": str(outcome.get("evidence_authority") or "unavailable"),
        }
        evaluations.append(evaluation)
        if classification in {"outcome_inconclusive", "no_material_follow_up", "resolved_by_stronger_owner"}:
            continue
        owner, next_route = _route(classification=classification, projection=projection or outcome)
        dedupe_identity = f"{join_key}:{decision_id}:{failure_identity}:{classification}"
        evidence_refs = _texts(outcome.get("evidence_refs"))
        if dedupe_identity in findings_by_key:
            current = findings_by_key[dedupe_identity]
            current["evidence_refs"] = list(dict.fromkeys([*_texts(current.get("evidence_refs")), *evidence_refs]))
            current["duplicate_evidence_count"] = int(current.get("duplicate_evidence_count") or 1) + 1
            continue
        findings_by_key[dedupe_identity] = {
            "kind": "agentic-workspace/learning-effectiveness-finding/v1",
            "id": evaluation_id,
            "finding_class": "learning-effectiveness",
            "effectiveness_class": classification,
            "severity": "medium",
            "lifecycle": "unresolved",
            "owner": owner,
            "next_route": next_route,
            "trigger": failure_identity or "material later outcome",
            "task_relevant": True,
            "evidence_refs": evidence_refs,
            "dedupe_identity": dedupe_identity,
            "duplicate_evidence_count": 1,
        }

    findings = list(findings_by_key.values())
    return {
        "kind": "agentic-workspace/learning-effectiveness-feedback/v1",
        "status": "attention" if findings else "quiet",
        "input_revision": "sha256:" + _digest({"projections": active, "outcomes": later}) if later else "",
        "projected_owner_count": len(active),
        "later_outcome_count": len(later),
        "evaluations": evaluations,
        "findings": findings,
        "persistent_use_ledger_created": False,
        "rule": "Owner identity/revision plus canonical decision identity support sparse later attribution; ordinary use and absence of recurrence create no record.",
    }
