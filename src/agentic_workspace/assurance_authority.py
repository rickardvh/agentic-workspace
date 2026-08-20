"""Bounded repository assurance classification and evidence admission.

This module does not certify compliance. It admits repository-owned policy
decisions and candidate proof evidence without letting the producer, transport,
or caller widen their own authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from agentic_workspace.proof_subject import compare_proof_subjects

APPLICATION_KIND = "agentic-workspace/assurance-application/v1"
DECISION_KIND = "agentic-workspace/repository-assurance-decision/v1"
EVIDENCE_KIND = "agentic-workspace/external-evidence-candidate/v1"
AUTHORITY_KIND = "agentic-workspace/evidence-authority/v1"


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def build_assurance_application(
    *,
    requirement_id: str,
    classification_owner: str,
    source_revision: str,
    applicability_input: dict[str, Any],
    current_work_id: str = "",
) -> dict[str, Any]:
    """Issue identity for why a requirement applies, separate from proof identity."""

    identity_input = {
        "requirement_id": str(requirement_id).strip(),
        "classification_owner": str(classification_owner).strip(),
        "source_revision": str(source_revision).strip(),
        "applicability_input": applicability_input,
        "current_work_id": str(current_work_id).strip(),
    }
    missing = [key for key in ("requirement_id", "classification_owner", "source_revision") if not identity_input[key]]
    status = "current" if not missing else "unverifiable"
    fingerprint = _digest(identity_input)
    return {
        "kind": APPLICATION_KIND,
        "status": status,
        "application_id": f"assurance-application:{fingerprint[:20]}" if status == "current" else "",
        "fingerprint": fingerprint,
        **identity_input,
        "missing_identity_fields": missing,
        "rule": "Application identity binds only classification-relevant repository policy and current-work inputs; proof has a separate subject.",
    }


def admit_repository_assurance_decision(
    *,
    candidate: dict[str, Any] | None,
    configured_owner: str,
    expected_source_revision: str,
    expected_input_revision: str,
) -> dict[str, Any]:
    """Fail closed while admitting a config-native or repository-produced decision."""

    value = _as_dict(candidate)
    reasons: list[str] = []
    if not value:
        reasons.append("decision-unavailable")
    elif value.get("kind") != DECISION_KIND:
        reasons.append("decision-kind-incompatible")
    if value and str(value.get("classification_owner") or "") != str(configured_owner):
        reasons.append("classification-owner-conflict")
    if value and str(value.get("source_revision") or "") != str(expected_source_revision):
        reasons.append("decision-source-stale")
    if value and str(value.get("input_revision") or "") != str(expected_input_revision):
        reasons.append("decision-input-stale")
    if value and value.get("complete") is not True:
        reasons.append("decision-incomplete")
    if value and not isinstance(value.get("requirements"), list):
        reasons.append("decision-malformed")
    forbidden = _strings(value.get("authority_effects"))
    if forbidden:
        reasons.append("authority-widening-denied")
    applications: list[dict[str, Any]] = []
    if not reasons:
        for requirement in value["requirements"]:
            item = _as_dict(requirement)
            if not item.get("id") or not isinstance(item.get("applicability_input"), dict):
                reasons.append("requirement-ambiguous")
                continue
            applications.append(
                build_assurance_application(
                    requirement_id=str(item["id"]),
                    classification_owner=str(configured_owner),
                    source_revision=str(expected_source_revision),
                    applicability_input=item["applicability_input"],
                    current_work_id=str(item.get("current_work_id") or ""),
                )
            )
    status = "admitted" if not reasons else "blocked"
    return {
        "kind": "agentic-workspace/assurance-decision-admission/v1",
        "status": status,
        "reason_codes": sorted(set(reasons)),
        "classification_owner": configured_owner,
        "source_revision": expected_source_revision,
        "input_revision": expected_input_revision,
        "requirements": value.get("requirements", []) if status == "admitted" else [],
        "applications": applications if status == "admitted" else [],
        "next_action": {
            "id": "none" if status == "admitted" else "refresh-repository-assurance-decision",
            "owner": configured_owner or "repository",
            "why": "The repository classification owner must issue a complete decision bound to current source and input revisions."
            if status != "admitted"
            else "The repository-owned assurance decision is current and admitted.",
        },
        "authority_boundary": "The decision may add repository-policy obligations; it cannot grant mutation, claim, waiver, or proof authority.",
    }


def evaluate_assurance_disposition(
    *,
    disposition: dict[str, Any] | None,
    application: dict[str, Any],
    proof_subject: dict[str, Any] | None = None,
    strict_policy: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate waiver/dismissal applicability and reactivate on any mismatch."""

    value = _as_dict(disposition)
    if not value:
        return {"status": "none", "requirement_active": True, "reason_codes": []}
    applicability = _as_dict(value.get("applicability"))
    if not applicability:
        if strict_policy:
            return {"status": "migration-required", "requirement_active": True, "reason_codes": ["legacy-unbounded-disposition"]}
        return {"status": "active-legacy", "requirement_active": False, "reason_codes": []}
    reasons: list[str] = []
    expected_application = str(applicability.get("application_id") or "")
    if expected_application and expected_application != str(application.get("application_id") or ""):
        reasons.append("application-changed")
    expected_source = str(applicability.get("source_revision") or "")
    if expected_source and expected_source != str(application.get("source_revision") or ""):
        reasons.append("classification-source-changed")
    expected_work = str(applicability.get("current_work_id") or "")
    if expected_work and expected_work != str(application.get("current_work_id") or ""):
        reasons.append("current-work-changed")
    expected_subject = str(applicability.get("proof_subject_fingerprint") or "")
    if expected_subject and expected_subject != str(_as_dict(proof_subject).get("fingerprint") or ""):
        reasons.append("proof-subject-changed")
    current = now or datetime.now(timezone.utc)
    for field, reason in (("expires_at", "disposition-expired"), ("review_after", "disposition-review-required")):
        raw = str(applicability.get(field) or "")
        if raw:
            try:
                bound = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if current >= bound:
                    reasons.append(reason)
            except ValueError:
                reasons.append(f"{field.replace('_', '-')}-malformed")
    return {
        "status": "active" if not reasons else "inactive",
        "requirement_active": bool(reasons),
        "reason_codes": sorted(set(reasons)),
        "application_id": application.get("application_id", ""),
        "rule": "An inactive disposition re-exposes the original assurance requirement and its claim block.",
    }


def admit_external_evidence(
    *,
    candidate: dict[str, Any] | None,
    authorities: list[dict[str, Any]],
    current_proof_subject: dict[str, Any],
    application_id: str = "",
) -> dict[str, Any]:
    """Admit an external reference only when repository proof policy authorizes its producer."""

    value = _as_dict(candidate)
    reasons: list[str] = []
    if not value:
        reasons.append("candidate-unavailable")
    elif value.get("kind") != EVIDENCE_KIND:
        reasons.append("candidate-kind-incompatible")
    required = ("producer_id", "proof_route", "evidence_class", "result_contract", "result", "evidence_ref", "proof_subject")
    if value and any(not value.get(field) for field in required):
        reasons.append("candidate-incomplete")
    if value and str(value.get("producer_id") or "") == str(value.get("transport_id") or "") and value.get("transport_id"):
        reasons.append("transport-self-authorization-denied")
    matching = []
    for authority in authorities:
        authority = _as_dict(authority)
        if authority.get("kind") != AUTHORITY_KIND:
            continue
        if all(
            str(authority.get(field) or "") == str(value.get(field) or "")
            for field in ("producer_id", "proof_route", "evidence_class", "result_contract")
        ):
            matching.append(authority)
    if value and not matching:
        reasons.append("producer-unauthorized")
    if len(matching) > 1:
        reasons.append("evidence-authority-ambiguous")
    authority = matching[0] if len(matching) == 1 else {}
    allowed_results = _strings(authority.get("allowed_results"))
    if authority and allowed_results and str(value.get("result") or "") not in allowed_results:
        reasons.append("result-contract-violated")
    required_application = str(authority.get("application_id") or "")
    if required_application and required_application != str(application_id):
        reasons.append("application-binding-mismatch")
    subject = compare_proof_subjects(stored=_as_dict(value.get("proof_subject")), current=current_proof_subject)
    if subject["status"] in {"stale", "incompatible", "unverifiable"}:
        reasons.append(f"proof-subject-{subject['status']}")
    status = "admitted" if not reasons else "rejected"
    identity = {
        "producer_id": value.get("producer_id"),
        "proof_route": value.get("proof_route"),
        "evidence_class": value.get("evidence_class"),
        "result_contract": value.get("result_contract"),
        "result": value.get("result"),
        "evidence_ref": value.get("evidence_ref"),
        "proof_subject_fingerprint": _as_dict(value.get("proof_subject")).get("fingerprint"),
    }
    return {
        "kind": "agentic-workspace/external-evidence-admission/v1",
        "status": status,
        "admission_id": f"external-evidence:{_digest(identity)[:20]}",
        "reason_codes": sorted(set(reasons)),
        "proof_subject_status": subject,
        "producer_result": value.get("result"),
        "evidence_ref": value.get("evidence_ref", "") if status == "admitted" else "",
        "authority_id": authority.get("id", "") if status == "admitted" else "",
        "claim_authority": "none",
        "transport_id": value.get("transport_id", ""),
        "rule": "External evidence remains a bounded reference; transport is not producer authority and admission does not certify the claim.",
    }
