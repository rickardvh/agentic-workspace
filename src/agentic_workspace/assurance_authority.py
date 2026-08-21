"""Bounded repository assurance classification and evidence admission.

This module does not certify compliance. It admits repository-owned policy
decisions and candidate proof evidence without letting the producer, transport,
or caller widen their own authority.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any

from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.proof_subject import compare_proof_subjects

APPLICATION_KIND = "agentic-workspace/assurance-application/v1"
DECISION_KIND = "agentic-workspace/repository-assurance-decision/v1"
EVIDENCE_KIND = "agentic-workspace/external-evidence-candidate/v1"
RESOLVED_PRODUCER_KIND = "agentic-workspace/resolved-evidence-producer/v1"
AUTHORITY_KIND = "agentic-workspace/evidence-authority/v1"
EXTERNAL_EVIDENCE_HOST_RESULT_KIND = "agentic-workspace/external-evidence-host-result/v1"
EXTERNAL_EVIDENCE_OPERATION_RESULT_KIND = "agentic-workspace/external-evidence-operation-result/v1"
EXTERNAL_EVIDENCE_HOST_RESULT_DIR = Path(".agentic-workspace/local/proof/external-evidence-host-results/inbox")
EXTERNAL_EVIDENCE_AUDIENCE = "agentic-workspace.external-evidence"
_RSA_SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
_PINNED_EXTERNAL_EVIDENCE_HOST_KEYS = MappingProxyType(
    {
        # The private key is not present in the repository. Rotation is a package
        # release, never an operation argument or repository-local trust update.
        "external-evidence-host:fixture-v1": MappingProxyType(
            {
                "algorithm": "RS256",
                "issuer_id": "synthetic-evidence-host",
                "n": (
                    "6aa122d5c14f291551b39a7070739b43748b8d5b22911eadc6677544a9698cfe9af057eda390500fd5742ed5d2fcc0d"
                    "23fc93e0f575b16c4a9337008690b625a41e11cb65611eda17a694b3dc96acb43f8b549e706ab8a34d826d7818f519"
                    "1d8458335e7fc718db615fa30a394062680c65751486ee3b2ff20813de0e565ad45"
                ),
                "e": "010001",
                "status": "current",
                "key_revision": "fixture-v1",
            }
        )
    }
)


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
    resolved_producer: dict[str, Any] | None,
    authorities: list[dict[str, Any]],
    current_proof_subject: dict[str, Any],
    application_id: str = "",
) -> dict[str, Any]:
    """Admit evidence only from host-resolved producer custody authorized by repository policy."""

    value = _as_dict(candidate)
    resolved = _as_dict(resolved_producer)
    reasons: list[str] = []
    if not value:
        reasons.append("candidate-unavailable")
    elif value.get("kind") != EVIDENCE_KIND:
        reasons.append("candidate-kind-incompatible")
    required = ("proof_route", "evidence_class", "proof_subject")
    if value and any(not value.get(field) for field in required):
        reasons.append("candidate-incomplete")
    resolved_required = ("producer_id", "issuer_id", "result_contract", "result", "evidence_ref")
    if resolved.get("kind") != RESOLVED_PRODUCER_KIND or resolved.get("authenticated") is not True:
        reasons.append("producer-custody-unresolved")
    elif any(not resolved.get(field) for field in resolved_required):
        reasons.append("resolved-producer-incomplete")
    if value.get("producer_id") and str(value.get("producer_id")) != str(resolved.get("producer_id") or ""):
        reasons.append("candidate-producer-mismatch")
    for field in ("result_contract", "result", "evidence_ref"):
        if value.get(field) and str(value.get(field)) != str(resolved.get(field) or ""):
            reasons.append(f"candidate-{field.replace('_', '-')}-mismatch")
    matching = []
    for authority in authorities:
        authority = _as_dict(authority)
        if authority.get("kind") != AUTHORITY_KIND:
            continue
        identity_matches = (
            str(authority.get("producer_id") or "") == str(resolved.get("producer_id") or "")
            and str(authority.get("proof_route") or "") == str(value.get("proof_route") or "")
            and str(authority.get("evidence_class") or "") == str(value.get("evidence_class") or "")
            and str(authority.get("result_contract") or "") == str(resolved.get("result_contract") or "")
        )
        issuer_matches = not authority.get("issuer_id") or str(authority.get("issuer_id")) == str(resolved.get("issuer_id") or "")
        if identity_matches and issuer_matches:
            matching.append(authority)
    if value and not matching:
        reasons.append("producer-unauthorized")
    if len(matching) > 1:
        reasons.append("evidence-authority-ambiguous")
    authority = matching[0] if len(matching) == 1 else {}
    allowed_results = _strings(authority.get("allowed_results"))
    if authority and allowed_results and str(resolved.get("result") or "") not in allowed_results:
        reasons.append("result-contract-violated")
    required_application = str(authority.get("application_id") or "")
    if required_application and required_application != str(application_id):
        reasons.append("application-binding-mismatch")
    subject = compare_proof_subjects(stored=_as_dict(value.get("proof_subject")), current=current_proof_subject)
    if subject["status"] in {"stale", "incompatible", "unverifiable"}:
        reasons.append(f"proof-subject-{subject['status']}")
    status = "admitted" if not reasons else "rejected"
    identity = {
        "producer_id": resolved.get("producer_id"),
        "issuer_id": resolved.get("issuer_id"),
        "proof_route": value.get("proof_route"),
        "evidence_class": value.get("evidence_class"),
        "result_contract": resolved.get("result_contract"),
        "result": resolved.get("result"),
        "evidence_ref": resolved.get("evidence_ref"),
        "proof_subject_fingerprint": _as_dict(value.get("proof_subject")).get("fingerprint"),
    }
    return {
        "kind": "agentic-workspace/external-evidence-admission/v1",
        "status": status,
        "admission_id": f"external-evidence:{_digest(identity)[:20]}",
        "reason_codes": sorted(set(reasons)),
        "proof_subject_status": subject,
        "producer_result": resolved.get("result"),
        "evidence_ref": resolved.get("evidence_ref", "") if status == "admitted" else "",
        "authority_id": authority.get("id", "") if status == "admitted" else "",
        "claim_authority": "none",
        "transport_id": resolved.get("transport_id", ""),
        "producer_custody": "host-authenticated" if resolved.get("authenticated") is True else "unresolved",
        "rule": "External evidence remains a bounded reference; host-resolved producer custody is distinct from candidate and transport assertions, and admission does not certify the claim.",
    }


def _base64url_decode(value: str) -> bytes:
    text = value.strip()
    return base64.urlsafe_b64decode((text + ("=" * (-len(text) % 4))).encode("ascii"))


def _verify_rs256_signature(*, key: dict[str, Any], payload: dict[str, Any], signature: str) -> bool:
    try:
        modulus = int(str(key.get("n") or ""), 16)
        exponent = int(str(key.get("e") or ""), 16)
        raw_signature = _base64url_decode(signature)
    except (ValueError, TypeError):
        return False
    key_size = (modulus.bit_length() + 7) // 8
    if len(raw_signature) != key_size:
        return False
    message = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest_info = _RSA_SHA256_DER_PREFIX + hashlib.sha256(message).digest()
    encoded = pow(int.from_bytes(raw_signature, "big"), exponent, modulus).to_bytes(key_size, "big")
    separator = encoded.find(b"\x00", 2)
    if not encoded.startswith(b"\x00\x01") or separator < 10:
        return False
    padding = encoded[2:separator]
    if len(padding) < 8 or any(byte != 0xFF for byte in padding):
        return False
    return hmac.compare_digest(encoded[separator + 1 :], digest_info)


def _host_signature_payload(host_result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in host_result.items() if key != "host_admission"}


def _load_external_evidence_host_result(*, target_root: Path, host_result_ref: str) -> dict[str, Any]:
    """Resolve and verify producer custody from an opaque package-trusted host record."""

    ref = str(host_result_ref or "").strip()
    if not ref.startswith("external-evidence-host-result:") or "/" in ref or "\\" in ref:
        raise WorkspaceUsageError("host_result_ref must be an opaque external-evidence-host-result reference.")
    result_id = ref.removeprefix("external-evidence-host-result:")
    path = target_root / EXTERNAL_EVIDENCE_HOST_RESULT_DIR / f"{result_id}.json"
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceUsageError("external evidence host result is missing or unreadable.") from exc
    if not isinstance(result, dict) or result.get("kind") != EXTERNAL_EVIDENCE_HOST_RESULT_KIND:
        raise WorkspaceUsageError("external evidence host result has the wrong contract.")
    if result.get("status") != "current" or result.get("result_id") != result_id or result.get("result_ref") != ref:
        raise WorkspaceUsageError("external evidence host result identity or currentness is invalid.")
    if result.get("audience") != EXTERNAL_EVIDENCE_AUDIENCE or not str(result.get("nonce") or "").strip():
        raise WorkspaceUsageError("external evidence host result has invalid audience or replay identity.")
    issued_at = _parse_host_time(result.get("issued_at"))
    expires_at = _parse_host_time(result.get("expires_at"))
    if issued_at is None or expires_at is None or expires_at <= issued_at or expires_at <= datetime.now(timezone.utc):
        raise WorkspaceUsageError("external evidence host result is expired or has an invalid validity interval.")
    if result.get("revoked_at") or result.get("superseded_by"):
        raise WorkspaceUsageError("external evidence host result is revoked or superseded.")
    admission = _as_dict(result.get("host_admission"))
    key = _PINNED_EXTERNAL_EVIDENCE_HOST_KEYS.get(str(admission.get("key_id") or ""))
    if key is None:
        raise WorkspaceUsageError("external evidence host key is not package-trusted.")
    if (
        admission.get("kind") != "agentic-workspace/external-evidence-host-admission/v1"
        or admission.get("algorithm") != "RS256"
        or key.get("algorithm") != "RS256"
        or key.get("status") != "current"
        or key.get("revoked_at")
        or key.get("superseded_by")
        or str(key.get("issuer_id") or "") != str(result.get("issuer_id") or "")
        or not str(key.get("key_revision") or "").strip()
        or not _verify_rs256_signature(
            key=dict(key), payload=_host_signature_payload(result), signature=str(admission.get("signature") or "")
        )
    ):
        raise WorkspaceUsageError("external evidence host result was not admitted by the package-trusted host boundary.")
    return result


def _parse_host_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _current_subject_from_candidate(*, target_root: Path, stored: dict[str, Any]) -> dict[str, Any]:
    """Revalidate a producer-bound proof subject against current repo files."""

    if stored.get("kind") != "agentic-workspace/proof-subject/v1" or not isinstance(stored.get("source_inputs"), list):
        return {"kind": "", "identity_complete": False}
    current = dict(stored)
    current_sources: list[dict[str, str]] = []
    unavailable: list[str] = []
    changed = False
    root = target_root.resolve()
    for raw in stored.get("source_inputs", []):
        item = _as_dict(raw)
        relative = str(item.get("path") or "").replace("\\", "/").strip()
        candidate = (root / relative).resolve()
        if not relative or Path(relative).is_absolute() or not candidate.is_relative_to(root):
            unavailable.append(relative)
            continue
        try:
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError:
            unavailable.append(relative)
            continue
        current_sources.append({"path": relative, "sha256": digest})
        changed = changed or digest != str(item.get("sha256") or "")
    current["source_inputs"] = current_sources
    current["unavailable_inputs"] = unavailable
    current["identity_complete"] = bool(current_sources) and not unavailable
    runtime = _as_dict(stored.get("runtime"))
    if runtime and (
        str(runtime.get("implementation") or "") != platform.python_implementation()
        or str(runtime.get("version") or "") != platform.python_version()
    ):
        current["claim_classes"] = [*list(stored.get("claim_classes", [])), "runtime-incompatible"]
    if changed or unavailable or current.get("claim_classes") != stored.get("claim_classes"):
        current["fingerprint"] = _digest(
            {
                "claim_classes": current.get("claim_classes", []),
                "source_inputs": current_sources,
                "unavailable_inputs": unavailable,
                "runtime": current.get("runtime", {}),
            }
        )
    return current


def _repository_evidence_authorities(target_root: Path) -> list[dict[str, Any]]:
    from repo_verification_bootstrap.runtime_primitives import verification_report_payload

    report = verification_report_payload(target_root=target_root)
    values = report.get("evidence_authorities", [])
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def _evaluate_external_evidence_operation(
    *, target_root: Path, candidate: dict[str, Any], host_result_ref: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    host_result = _load_external_evidence_host_result(target_root=target_root, host_result_ref=host_result_ref)
    stored_subject = _as_dict(candidate.get("proof_subject"))
    reasons: list[str] = []
    if "authenticated" in candidate or "resolved_producer" in candidate or "producer_custody" in candidate:
        reasons.append("candidate-custody-assertion-denied")
    bound_fields = ("proof_route", "evidence_class")
    for field in bound_fields:
        if str(host_result.get(field) or "") != str(candidate.get(field) or ""):
            reasons.append(f"host-{field.replace('_', '-')}-mismatch")
    if str(host_result.get("proof_subject_digest") or "") != _digest(stored_subject):
        reasons.append("host-proof-subject-mismatch")
    resolved = {
        "kind": RESOLVED_PRODUCER_KIND,
        "authenticated": True,
        "producer_id": host_result.get("producer_id"),
        "issuer_id": host_result.get("issuer_id"),
        "transport_id": host_result.get("transport_id"),
        "result_contract": host_result.get("result_contract"),
        "result": host_result.get("result"),
        "evidence_ref": host_result.get("evidence_ref"),
    }
    admission = admit_external_evidence(
        candidate=candidate,
        resolved_producer=resolved,
        authorities=_repository_evidence_authorities(target_root),
        current_proof_subject=_current_subject_from_candidate(target_root=target_root, stored=stored_subject),
        application_id=str(candidate.get("application_id") or ""),
    )
    if reasons:
        admission["status"] = "rejected"
        admission["reason_codes"] = sorted(set([*admission.get("reason_codes", []), *reasons]))
        admission["evidence_ref"] = ""
        admission["authority_id"] = ""
    admission["producer_custody"] = "package-trusted-host-result"
    admission["host_result_ref"] = host_result_ref
    return admission, host_result


def submit_external_evidence_operation(*, target_root: Path, candidate_json: str, host_result_ref: str) -> dict[str, Any]:
    """Submit evidence through the public operation without accepting caller custody facts."""

    try:
        candidate = json.loads(candidate_json)
    except json.JSONDecodeError as exc:
        raise WorkspaceUsageError("candidate_json must contain one external evidence candidate object.") from exc
    if not isinstance(candidate, dict):
        raise WorkspaceUsageError("candidate_json must contain one external evidence candidate object.")
    admission, _host_result = _evaluate_external_evidence_operation(
        target_root=target_root, candidate=candidate, host_result_ref=host_result_ref
    )
    return {
        "kind": EXTERNAL_EVIDENCE_OPERATION_RESULT_KIND,
        "operation": "submit",
        "status": admission.get("status"),
        "admission": admission,
        "stored": False,
    }


def query_external_evidence_operation(*, target_root: Path, candidate_json: str, host_result_ref: str) -> dict[str, Any]:
    try:
        candidate = json.loads(candidate_json)
    except json.JSONDecodeError as exc:
        raise WorkspaceUsageError("candidate_json must contain one external evidence candidate object.") from exc
    if not isinstance(candidate, dict):
        raise WorkspaceUsageError("candidate_json must contain one external evidence candidate object.")
    admission, _host_result = _evaluate_external_evidence_operation(
        target_root=target_root,
        candidate=candidate,
        host_result_ref=host_result_ref,
    )
    return {
        "kind": EXTERNAL_EVIDENCE_OPERATION_RESULT_KIND,
        "operation": "query",
        "status": admission.get("status"),
        "admission": admission,
        "stored": False,
    }


def _run_external_evidence_adapter(args: Any) -> int:
    target_root = Path(str(getattr(args, "target", ".") or ".")).resolve()
    command = str(getattr(args, "command", "") or "")
    try:
        if command == "external-evidence-submit":
            payload = submit_external_evidence_operation(
                target_root=target_root,
                candidate_json=str(getattr(args, "candidate_json", "") or ""),
                host_result_ref=str(getattr(args, "host_result_ref", "") or ""),
            )
        elif command == "external-evidence-query":
            payload = query_external_evidence_operation(
                target_root=target_root,
                candidate_json=str(getattr(args, "candidate_json", "") or ""),
                host_result_ref=str(getattr(args, "host_result_ref", "") or ""),
            )
        else:
            raise WorkspaceUsageError(f"unsupported external evidence operation: {command}")
    except WorkspaceUsageError as exc:
        print(
            json.dumps(
                {
                    "kind": "agentic-workspace/external-evidence-operation-error/v1",
                    "status": "rejected",
                    "message": str(exc),
                    "command": command,
                    "exit_status": 2,
                },
                indent=2,
            )
        )
        return 2
    print(json.dumps(payload, indent=2))
    return 0
