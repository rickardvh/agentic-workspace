from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from agentic_workspace.config import (
    WORKSPACE_LOCAL_CONFIG_PATH,
    WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH,
    WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH,
    DelegationTargetProfile,
    MixedAgentLocalOverride,
    WorkspaceUsageError,
    load_workspace_config,
)

CORRECTION_EVENT_RETENTION_CAP = 20
GUIDANCE_RECEIPT_INDEX_PATH = Path(".agentic-workspace/local/guidance-receipts.json")
GUIDANCE_TRANSACTION_JOURNAL_PATH = Path(".agentic-workspace/local/guidance-transaction.json")
GUIDANCE_EXTERNAL_TRANSACTION_JOURNAL_SUFFIX = ".guidance-transaction.json"
GUIDANCE_OBSERVATION_STORE_PATH = Path(".agentic-workspace/local/guidance-observations.json")
GUIDANCE_OBSERVATION_RETENTION_CAP = 200
TRUSTED_AUTHORITY_EVENT_STORE_PATH = Path(".agentic-workspace/local/trusted-authority-events")
TRUSTED_AUTHORITY_EVENT_INDEX_PATH = TRUSTED_AUTHORITY_EVENT_STORE_PATH / "index.json"
TRUSTED_AUTHORITY_EVENT_INBOX_PATH = TRUSTED_AUTHORITY_EVENT_STORE_PATH / "inbox"
TRUSTED_AUTHORITY_EVENT_AUDIENCE = "agentic-workspace.guidance-authority"
TrustedAuthorityHostEventResolver = Callable[[str], dict[str, Any]]
_RSA_SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
_TRUSTED_AUTHORITY_HOST_PUBLIC_KEYS = {
    "github-review-adapter:host-v1": {
        "algorithm": "RS256",
        "issuer": "github-review-adapter",
        "trusted_channel": "github-review-webhook",
        "n": (
            "998d17874f9e1598c0660b41e484fb8e8a16de1a523885b0c194f9468858ca108b89133eb871c8da398df7ad"
            "4e2f53e5bc474442f060655e71839cfa016922f11f26e0c07f92eeee56a8653ae8ce6c8e4e19a63622a1519685"
            "bad a671ba9655c381b4b35beda14676fd302764e5e60854c3f26b1b27a6c5ea9cf30905f2b995f5ecc6056437048"
            "cb80301f8e613920ebc5b13232f933e66e7581dee91bb7a728da54392b77736ebaf44b0cbf9bea1998d04484de"
            "87d695dec8b98936cf5d64a6ea3d91f1dc45ae91098ffb85055ff3db456a664bf3dea9f0c204f1c1c85f4d"
            "53997c2f6f8a41a7d80972ffe9dafcb939d48f35656f67f7bb0ce17c0835adf3d9"
        ).replace(" ", ""),
        "e": "010001",
        "status": "current",
    }
}
_GUIDANCE_TRANSACTION_FAULT_INJECTOR: Callable[[str, Path], None] | None = None


def _guidance_now() -> str:
    return datetime.now(UTC).isoformat()


def _trusted_authority_host_event_inbox_path(target_root: Path, host_event_ref: str) -> Path:
    fragment = host_event_ref.removeprefix("trusted-authority-event:")
    return target_root / TRUSTED_AUTHORITY_EVENT_INBOX_PATH / f"{fragment}.json"


def _load_trusted_authority_host_event_from_inbox(*, target_root: Path, host_event_ref: str) -> dict[str, Any]:
    path = _trusted_authority_host_event_inbox_path(target_root, host_event_ref)
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceUsageError("trusted authority signed host event inbox is missing or unreadable.") from exc
    if not isinstance(event, dict):
        raise WorkspaceUsageError("trusted authority signed host event inbox entry has the wrong contract.")
    return json.loads(json.dumps(event, sort_keys=True, default=str))


CORRECTION_EVENT_OPERATIONS = (
    "correction-event.submit",
    "correction-event.query",
    "correction-event.correct-dispute",
    "correction-event.withdraw-supersede",
    "correction-event.prune-compact",
)
GUIDANCE_LIFECYCLE_OPERATIONS = (
    "agent-guidance.promote",
    "agent-guidance.edit",
    "agent-guidance.merge",
    "agent-guidance.split",
    "agent-guidance.suppress",
    "agent-guidance.revalidate",
    "agent-guidance.weaken",
    "agent-guidance.supersede",
    "agent-guidance.retire",
    "agent-guidance.delete",
)
ADMITTED_CORRECTION_AUTHORITIES = {"explicit-user-correction", "pr-review", "orchestrator-review", "evaluator-finding"}
ADMITTED_ROUTE_DECISIONS = {"target-guidance", "target-suitability", "memory", "config", "issue", "no-retention"}
TRUSTED_CORRECTION_PRODUCERS = {
    "explicit-user-correction": {"human", "human-reviewer", "user"},
    "pr-review": {"human-reviewer", "review-bot", "maintainer"},
    "orchestrator-review": {"orchestrator", "maintainer"},
    "evaluator-finding": {"evaluator", "verification"},
}
_GUIDANCE_REJECTING_LIFECYCLE_STATES = {"disputed", "withdrawn", "superseded", "revoked"}
_BROAD_SCOPE_CLASSES = {"all", "*", "global", "any", "broad"}


def _stable_event_id(event: dict[str, Any]) -> str:
    identity = {
        "delivery_id": event.get("delivery_id") or event.get("idempotency_key") or event.get("source_ref"),
        "source": event.get("source"),
        "producer": event.get("producer") or event.get("authority"),
        "submitted_at": event.get("submitted_at") or event.get("recorded_at"),
        "target_identity_ref": event.get("target_identity_ref"),
    }
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
    return "correction:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _json_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _semantic_correction_identity(*, event: dict[str, Any], subject: dict[str, Any] | None, target_ref: str) -> dict[str, Any]:
    applicability = event.get("applicability")
    if not isinstance(applicability, dict):
        applicability = {}
    semantic = {
        "target_identity_ref": str(subject.get("stable_target_id") if subject is not None else target_ref),
        "target_revision": str(event.get("target_revision") or applicability.get("target_revision") or ""),
        "task_class": str(event.get("task_class") or applicability.get("task_class") or ""),
        "scope_class": str(event.get("scope_class") or applicability.get("scope_class") or event.get("task_class") or ""),
        "phase": str(event.get("phase") or applicability.get("phase") or ""),
        "subsystem": str(event.get("subsystem") or applicability.get("subsystem") or ""),
        "surface": str(event.get("surface") or applicability.get("surface") or ""),
        "repository": str(event.get("repository") or applicability.get("repository") or ""),
        "role": str(event.get("role") or applicability.get("role") or ""),
        "invariant_id": str(event.get("invariant_id") or event.get("semantic_invariant") or applicability.get("invariant_id") or ""),
        "behavior_class": str(event.get("behavior_class") or applicability.get("behavior_class") or ""),
        "applies_when": applicability.get("applies_when") or event.get("applies_when") or [],
        "consequence": str(event.get("consequence") or ""),
    }
    return semantic


def _semantic_key(identity: dict[str, Any]) -> str:
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
    return "semantic:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _correction_lifecycle_state(event: dict[str, Any]) -> str:
    return str(event.get("lifecycle_state") or event.get("evidence_state") or event.get("status") or "current")


def _correction_requires_review(event: dict[str, Any]) -> str:
    raw_applicability = event.get("applicability")
    applicability: dict[str, Any] = raw_applicability if isinstance(raw_applicability, dict) else {}
    scope_class = str(event.get("scope_class") or applicability.get("scope_class") or "").strip().lower()
    applies_when = applicability.get("applies_when") or event.get("applies_when") or []
    conflict = event.get("conflict_review") if isinstance(event.get("conflict_review"), dict) else {}
    target_revision = str(event.get("target_revision") or "")
    reviewed_revision = str(event.get("target_generation_reviewed") or event.get("target_revision_reviewed") or "")
    if _correction_lifecycle_state(event) in _GUIDANCE_REJECTING_LIFECYCLE_STATES:
        return "evidence-not-current"
    if event.get("predecessor_event_id") and str(event.get("operation") or "submit") == "submit":
        return "supersession-not-resolved"
    if _truthy(event.get("contradiction")) or event.get("contradicts_event_id"):
        return "contradiction-unresolved"
    if _truthy(event.get("safety_sensitive")) or _truthy(applicability.get("safety_sensitive")):
        return "safety-sensitive-review-required"
    if scope_class in _BROAD_SCOPE_CLASSES or applies_when == ["*"] or applies_when == "*":
        return "broad-applicability-review-required"
    if conflict and conflict.get("status") not in {"resolved-no-conflict", "not-applicable"}:
        return "conflicting-authority-review-required"
    if target_revision and reviewed_revision and reviewed_revision != target_revision:
        return "target-generation-drift"
    return ""


def _resolve_correction_authority(*, event: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    claimed_authority = str(event.get("authority") or "")
    source = str(event.get("source") or provenance.get("source") or "")
    producer_class = str(event.get("producer_class") or provenance.get("producer_class") or "")
    if claimed_authority not in ADMITTED_CORRECTION_AUTHORITIES:
        if claimed_authority == "agent-self-observation" or producer_class in {"agent", "agent-self-observation", "model"}:
            return {
                "status": "low-authority",
                "authority": "agent-self-observation",
                "claimed_authority": claimed_authority,
                "reason": "agent-origin-self-observation",
                "trusted": False,
                "source": source,
                "producer_class": producer_class,
            }
        return {
            "status": "rejected",
            "authority": claimed_authority,
            "reason": "unadmitted-authority",
            "trusted": False,
            "source": source,
            "producer_class": producer_class,
        }
    trusted_producers = TRUSTED_CORRECTION_PRODUCERS.get(claimed_authority, set())
    if producer_class not in trusted_producers:
        low_authority = "agent-self-observation" if producer_class in {"agent", "agent-self-observation", "model"} else claimed_authority
        return {
            "status": "low-authority",
            "authority": low_authority,
            "claimed_authority": claimed_authority,
            "reason": "producer-class-not-trusted-for-claimed-authority",
            "trusted": False,
            "source": source,
            "producer_class": producer_class,
        }
    return {
        "status": "trusted",
        "authority": claimed_authority,
        "reason": "trusted-channel-producer",
        "trusted": True,
        "source": source,
        "producer_class": producer_class,
    }


def _target_identity_subject(profile: DelegationTargetProfile) -> dict[str, Any]:
    return {
        "profile_name": profile.name,
        "stable_target_id": profile.target_id,
        "target_revision": profile.target_revision,
        "aliases": list(profile.aliases),
        "identity_status": profile.identity_status,
        "revision_policy": profile.revision_policy,
        "provider": profile.provider,
        "model_family": profile.model_family,
        "role_identity": profile.name,
        "continuity_rule": (
            "preserve guidance"
            if profile.revision_policy == "preserve"
            else "revalidate guidance before reuse"
            if profile.revision_policy == "revalidate"
            else "migrate guidance with explicit provenance"
            if profile.revision_policy == "migrate"
            else "retire guidance unless a newer target explicitly supersedes it"
        ),
    }


def resolve_target_identity(*, subjects: list[dict[str, Any]], value: str) -> dict[str, Any]:
    """Resolve profile name or alias inputs to one canonical stable target id."""

    token = value.strip()
    if not token:
        return {"status": "unknown", "subject": None, "matched_by": None, "recovery": "set a target id, profile name, or alias"}
    stable_matches = [subject for subject in subjects if subject.get("stable_target_id") == token]
    name_matches = [subject for subject in subjects if subject.get("profile_name") == token]
    alias_matches = [subject for subject in subjects if token in set(subject.get("aliases", []))]
    matches = stable_matches or name_matches or alias_matches
    matched_by = "target_id" if stable_matches else "profile_name" if name_matches else "alias" if alias_matches else None
    unique_ids = {subject.get("stable_target_id") for subject in matches if subject.get("stable_target_id")}
    if not matches:
        return {
            "status": "unavailable",
            "subject": None,
            "matched_by": None,
            "recovery": "configure the target or use a known stable target_id",
        }
    if len(matches) > 1 or len(unique_ids) != 1:
        return {
            "status": "ambiguous",
            "subject": None,
            "matched_by": matched_by,
            "recovery": "replace the alias with one unambiguous stable target_id",
            "candidate_target_ids": sorted(str(target_id) for target_id in unique_ids),
        }
    subject = matches[0]
    lifecycle = str(subject.get("identity_status") or "active")
    if lifecycle != "active":
        return {
            "status": lifecycle,
            "subject": subject,
            "matched_by": matched_by,
            "recovery": "revalidate or migrate target guidance before reuse",
        }
    if not subject.get("stable_target_id"):
        return {
            "status": "unknown",
            "subject": None,
            "matched_by": matched_by,
            "recovery": "set delegation_targets.<target>.target_id before using target guidance",
        }
    return {"status": "known", "subject": subject, "matched_by": matched_by, "recovery": "not-needed"}


def admit_correction_events(
    *, events: list[dict[str, Any]], subjects: list[dict[str, Any]], task_class: str | None = None, scope_class: str | None = None
) -> dict[str, Any]:
    """Admit local correction events after identity, lifecycle, revision, and context checks."""

    admitted_by_key: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []
    low_authority_events: list[dict[str, Any]] = []
    seen_delivery_ids: set[str] = set()
    recurrence_counts: dict[str, int] = {}
    recurrence_evidence_by_key: dict[str, list[dict[str, str]]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for index, raw_event in enumerate(events):
        event = dict(raw_event)
        event_id = str(event.get("event_id") or _stable_event_id(event))
        event["event_id"] = event_id
        operation = str(event.get("operation") or "submit")
        target_ref = str(event.get("target_identity_ref") or event.get("target") or "")
        resolution = resolve_target_identity(subjects=subjects, value=target_ref)
        raw_subject = resolution.get("subject")
        subject = raw_subject if isinstance(raw_subject, dict) else None
        desired = str(event.get("desired_behavior") or "")
        replaced = str(event.get("replaced_behavior") or "")
        semantic_identity = _semantic_correction_identity(event=event, subject=subject, target_ref=target_ref)
        normalized_key = _semantic_key(semantic_identity)
        event["normalized_correction_key"] = normalized_key
        event["semantic_identity"] = semantic_identity
        provenance = event.get("provenance")
        if not isinstance(provenance, dict):
            provenance = {}
        route_decisions = event.get("route_decisions")
        if not isinstance(route_decisions, list):
            route_decisions = []
        route_decisions = [str(item) for item in route_decisions if str(item).strip()]

        def reject(reason: str, recovery: str) -> None:
            rejected.append({"event_id": event_id, "index": index, "reason": reason, "recovery": recovery})

        if resolution["status"] != "known" or subject is None:
            reject(f"rejected-{resolution['status']}-target", str(resolution.get("recovery") or "resolve target identity"))
            continue
        if "sk-" in desired or "BEGIN PRIVATE KEY" in desired or "password=" in desired.lower():
            reject("rejected-secret-bearing", "Remove secrets and submit only behavioral guidance.")
            continue
        if not replaced:
            reject("rejected-missing-replaced-behavior", "Submit replaced_behavior so corrections carry the changed behavior boundary.")
            continue
        if not semantic_identity["invariant_id"] or not semantic_identity["behavior_class"]:
            reject("rejected-missing-semantic-identity", "Submit invariant_id and behavior_class so wording is not the identity.")
            continue
        if not event.get("source_ref"):
            reject("rejected-missing-source-ref", "Submit a stable source_ref for the correction evidence.")
            continue
        if not (event.get("producer_id") or event.get("producer_class") or provenance.get("producer_id")):
            reject("rejected-missing-producer", "Submit producer identity or producer class for authority resolution.")
            continue
        target_revision = str(subject.get("target_revision") or "")
        event_revision = str(event.get("target_revision") or "")
        authority_resolution = _resolve_correction_authority(event=event, provenance=provenance)
        if authority_resolution["status"] != "trusted":
            event["authority_resolution"] = authority_resolution
            if authority_resolution["status"] == "low-authority":
                event["target_identity_ref"] = subject["stable_target_id"]
                event["target_revision"] = target_revision or event_revision or None
                event["profile_name"] = subject.get("profile_name")
                event["source_ref"] = str(event.get("source_ref"))
                event["producer_class"] = str(event.get("producer_class") or provenance.get("producer_class") or "agent")
                event["producer_id"] = str(event.get("producer_id") or provenance.get("producer_id") or event["producer_class"])
                event["authority"] = str(authority_resolution["authority"])
                event["route_decisions"] = ["no-retention"]
                event["admission_state"] = "low-authority-self-observation"
                event["routing_state"] = "preserved-non-routing"
                event["rule"] = (
                    "Agent self-observation is inspectable low-authority evidence; it is not target guidance or "
                    "suitability evidence until a trusted correction channel admits it."
                )
                low_authority_events.append(event)
                by_id[event_id] = event
                continue
            reject(
                "rejected-unauthorised",
                "Submit through a trusted correction channel; self-observation remains low-authority evidence.",
            )
            continue
        if not (event.get("evidence_hash") or event.get("evidence_ref") or provenance.get("evidence_hash")):
            reject(
                "rejected-missing-evidence-hash",
                "Submit evidence_hash or evidence_ref so the event is auditable without raw transcript storage.",
            )
            continue
        if not route_decisions:
            reject(
                "rejected-missing-route-decision",
                "Submit explicit route_decisions for guidance, suitability, memory, config, issue, or no-retention.",
            )
            continue
        unknown_routes = sorted(set(route_decisions) - ADMITTED_ROUTE_DECISIONS)
        if unknown_routes:
            reject("rejected-unknown-route-decision", "Use admitted route decisions only.")
            continue
        review_required = _correction_requires_review(event)
        if review_required:
            reject(
                f"rejected-{review_required}",
                "Resolve evidence lifecycle, breadth, safety, conflict, or target-generation review before promotion.",
            )
            continue
        revision_policy = str(subject.get("revision_policy") or "preserve")
        if event_revision and target_revision and event_revision != target_revision:
            if revision_policy == "retire":
                reject("rejected-retired-revision", "Retired guidance must not route to new work.")
                continue
            revalidation = event.get("revalidation")
            revalidated = (
                isinstance(revalidation, dict) and revalidation.get("verified_by") == "aw" and revalidation.get("result") == "passed"
            )
            if revision_policy == "revalidate" and not revalidated:
                reject("rejected-stale-revision", "Revalidate the event against the current target revision.")
                continue
            if revision_policy == "migrate" and not event.get("predecessor_event_id"):
                reject("rejected-missing-migration-provenance", "Record predecessor_event_id before migrating guidance.")
                continue
            if revision_policy == "preserve":
                event["admission_state"] = "accepted-preserved-revision"
        if task_class and event.get("task_class") not in {None, "", task_class}:
            reject("rejected-task-context", "Correction applies only to its matching task class.")
            continue
        requested_scope = scope_class or task_class
        if requested_scope and event.get("scope_class") not in {None, "", requested_scope}:
            reject("rejected-scope-context", "Correction applies only to its matching scope class.")
            continue
        if operation in {"dispute", "withdraw", "supersede"}:
            predecessor_id = str(event.get("predecessor_event_id") or "")
            predecessor = by_id.get(predecessor_id)
            if predecessor is None:
                reject("rejected-unknown-predecessor", "Reference an admitted predecessor event.")
                continue
            if predecessor.get("semantic_identity", {}).get("target_identity_ref") != semantic_identity.get("target_identity_ref"):
                reject("rejected-predecessor-target-mismatch", "Predecessor transitions must stay within one resolved target identity.")
                continue
            admitted_by_key.pop(str(predecessor.get("normalized_correction_key")), None)
            if operation in {"dispute", "withdraw"}:
                event["admission_state"] = operation
                by_id[event_id] = event
                continue
        if event_id in seen_delivery_ids and operation == "submit":
            event["admission_state"] = "duplicate-replay"
            rejected.append(
                {
                    "event_id": event_id,
                    "index": index,
                    "reason": "duplicate-replay",
                    "recovery": "Use recurrence or supersede if the correction carries new evidence.",
                }
            )
            continue
        seen_delivery_ids.add(event_id)
        event["target_identity_ref"] = subject["stable_target_id"]
        event["target_revision"] = target_revision or event_revision or None
        event["profile_name"] = subject.get("profile_name")
        event["source_ref"] = str(event.get("source_ref"))
        event["producer_class"] = str(event.get("producer_class") or provenance.get("producer_class") or event.get("authority"))
        event["producer_id"] = str(event.get("producer_id") or provenance.get("producer_id") or event["producer_class"])
        event["authority_resolution"] = authority_resolution
        event["authority"] = str(authority_resolution["authority"])
        event["evidence_hash"] = str(event.get("evidence_hash") or provenance.get("evidence_hash") or "")
        event["evidence_ref"] = str(event.get("evidence_ref") or provenance.get("evidence_ref") or "")
        event["route_decisions"] = route_decisions
        recurrence_counts[normalized_key] = recurrence_counts.get(normalized_key, 0) + 1
        event["recurrence_count"] = recurrence_counts[normalized_key]
        evidence_identity = {
            "event_id": event_id,
            "delivery_id": str(event.get("delivery_id") or event.get("idempotency_key") or event.get("source_ref") or ""),
            "source_ref": str(event.get("source_ref") or ""),
            "producer_id": str(event.get("producer_id") or ""),
            "producer_class": str(event.get("producer_class") or ""),
            "evidence_hash": str(event.get("evidence_hash") or ""),
            "evidence_ref": str(event.get("evidence_ref") or ""),
            "correlation_id": str(event.get("correlation_id") or provenance.get("correlation_id") or event.get("thread_id") or ""),
        }
        recurrence_evidence = [*recurrence_evidence_by_key.get(normalized_key, []), evidence_identity]
        recurrence_evidence_by_key[normalized_key] = recurrence_evidence
        distinct_delivery = {item["delivery_id"] for item in recurrence_evidence if item["delivery_id"]}
        distinct_source = {item["source_ref"] for item in recurrence_evidence if item["source_ref"]}
        distinct_evidence = {
            item["evidence_hash"] or item["evidence_ref"] for item in recurrence_evidence if item["evidence_hash"] or item["evidence_ref"]
        }
        correlation_ids = [item["correlation_id"] for item in recurrence_evidence if item["correlation_id"]]
        event["recurrence_evidence"] = recurrence_evidence
        event["independent_recurrence"] = {
            "status": "independent"
            if recurrence_counts[normalized_key] >= 2
            and len(distinct_delivery) >= 2
            and len(distinct_source) >= 2
            and len(distinct_evidence) >= 2
            and len(correlation_ids) == len(set(correlation_ids))
            else "insufficient-independent-evidence",
            "distinct_delivery_count": len(distinct_delivery),
            "distinct_source_count": len(distinct_source),
            "distinct_evidence_count": len(distinct_evidence),
            "correlated_delivery_detected": len(correlation_ids) != len(set(correlation_ids)),
            "producer_ids": sorted({item["producer_id"] for item in recurrence_evidence if item["producer_id"]}),
        }
        base_admission_state = (
            "accepted-preserved-revision" if event.get("admission_state") == "accepted-preserved-revision" else "accepted-candidate"
        )
        event["admission_state"] = "recurrence" if recurrence_counts[normalized_key] > 1 and operation == "submit" else base_admission_state
        if operation == "submit" and recurrence_counts[normalized_key] > 1:
            prior = admitted_by_key.get(normalized_key)
            if prior is not None:
                event["contradiction_account"] = {
                    "status": "recurrence-preserved",
                    "prior_event_id": prior.get("event_id"),
                    "prior_source_ref": prior.get("source_ref"),
                    "recurrence_count": recurrence_counts[normalized_key],
                    "rule": "Recurrence preserves compact provenance rather than replacing the prior semantic correction silently.",
                }
        admitted_by_key[normalized_key] = event
        by_id[event_id] = event
    admitted = sorted(admitted_by_key.values(), key=lambda item: str(item.get("event_id")))
    retained_events = admitted[-CORRECTION_EVENT_RETENTION_CAP:]
    compacted_events = admitted[: max(0, len(admitted) - len(retained_events))]
    compacted_count = max(0, len(admitted) - len(retained_events))
    return {
        "kind": "agentic-workspace/correction-event-admission/v1",
        "status": "admitted" if retained_events else "no-admitted-events",
        "admitted_events": retained_events,
        "low_authority_events": low_authority_events[-CORRECTION_EVENT_RETENTION_CAP:],
        "rejected_events": rejected,
        "retention": {
            "mode": "bounded-local-retention",
            "cap": CORRECTION_EVENT_RETENTION_CAP,
            "compacted_count": compacted_count,
            "persisted_store_action": "rewrite-retained-plus-compact-lineage" if compacted_count else "no-rewrite-needed",
            "compacted_lineage": [
                {
                    "event_id": event.get("event_id"),
                    "normalized_correction_key": event.get("normalized_correction_key"),
                    "semantic_identity": event.get("semantic_identity"),
                    "source_ref": event.get("source_ref"),
                    "authority": event.get("authority"),
                }
                for event in compacted_events
            ],
            "lineage_inspectable": True,
            "delete_behavior": "local-only correction events may be deleted without changing checked-in repository meaning",
        },
        "store_update": {
            "kind": "agentic-workspace/correction-event-store-update/v1",
            "status": "bounded-rewrite-required" if compacted_count else "within-cap",
            "retained_event_ids": [event["event_id"] for event in retained_events],
            "compacted_event_ids": [event["event_id"] for event in compacted_events],
            "checked_in_repo_effect": "none",
            "idempotency_key": "correction-store:"
            + hashlib.sha256(json.dumps([event["event_id"] for event in retained_events], sort_keys=True).encode("utf-8")).hexdigest()[:16],
        },
        "public_operations": [
            {
                "operation_id": operation_id,
                "public": True,
                "generated_operation": True,
                "external_contract": True,
                "raw_file_write_compatibility": "compatibility-only-freshness-checked",
                "receipt": {
                    "kind": "agentic-workspace/correction-operation-receipt/v1",
                    "operation_id": operation_id,
                    "idempotency_source": "delivery_id/source_ref/semantic_identity",
                    "store_update_required": operation_id in {"correction-event.submit", "correction-event.prune-compact"},
                },
            }
            for operation_id in CORRECTION_EVENT_OPERATIONS
        ],
        "derived_routes": {
            "target_guidance": [event["event_id"] for event in retained_events if "target-guidance" in event.get("route_decisions", [])],
            "target_suitability": [
                event["event_id"] for event in retained_events if "target-suitability" in event.get("route_decisions", [])
            ],
            "memory": [event["event_id"] for event in retained_events if "memory" in event.get("route_decisions", [])],
            "no_retention": [event["event_id"] for event in retained_events if "no-retention" in event.get("route_decisions", [])],
            "low_authority": [event["event_id"] for event in low_authority_events[-CORRECTION_EVENT_RETENTION_CAP:]],
        },
        "routing_rule": "Only admitted correction events for the resolved target_id and matching task/scope context may affect target guidance.",
    }


def apply_correction_event_operation(
    *,
    target_root: Path,
    operation_id: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    """Apply a generated correction-event operation to bounded local storage."""

    operation = operation_id.removeprefix("correction-event.")
    config = load_workspace_config(target_root=target_root)
    store_path = target_root / config.local_override.correction_events_path
    store = _read_correction_event_store(store_path)
    existing_events = [item for item in store.get("events", []) if isinstance(item, dict)]
    subjects = _operation_subjects(values=values, config=config)
    task_class = str(values.get("task_class") or "") or None
    scope_class = str(values.get("scope_class") or "") or None
    mutation_applied = False
    if operation == "query":
        query_events = [
            event for event in existing_events if _correction_event_matches_query(event=event, values=values, subjects=subjects)
        ]
        admission = admit_correction_events(events=query_events, subjects=subjects, task_class=task_class, scope_class=scope_class)
        status = "queried"
    elif operation == "prune-compact":
        admission = admit_correction_events(events=existing_events, subjects=subjects, task_class=task_class, scope_class=scope_class)
        retained = [dict(event) for event in admission.get("admitted_events", []) if isinstance(event, dict)]
        retained.extend(dict(event) for event in admission.get("low_authority_events", []) if isinstance(event, dict))
        compacted_lineage = list(store.get("compacted_lineage", [])) if isinstance(store.get("compacted_lineage"), list) else []
        compacted_lineage.extend(admission.get("retention", {}).get("compacted_lineage", []))
        _write_correction_event_store(
            store_path,
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": retained[-CORRECTION_EVENT_RETENTION_CAP:],
                "compacted_lineage": compacted_lineage[-CORRECTION_EVENT_RETENTION_CAP:],
                "retention_cap": CORRECTION_EVENT_RETENTION_CAP,
                "checked_in_repo_effect": "none",
            },
        )
        mutation_applied = True
        status = "compacted"
    else:
        event = _operation_event(values=values, operation=operation, target_root=target_root)
        event_id = str(event.get("event_id") or _stable_event_id(event))
        duplicate_submit = operation == "submit" and any(
            str(candidate.get("event_id") or _stable_event_id(candidate)) == event_id for candidate in existing_events
        )
        events = existing_events if duplicate_submit else [*existing_events, event]
        admission = admit_correction_events(events=events, subjects=subjects, task_class=task_class, scope_class=scope_class)
        accepted_ids = {
            str(candidate.get("event_id"))
            for bucket in (admission.get("admitted_events", []), admission.get("low_authority_events", []))
            for candidate in bucket
            if isinstance(candidate, dict)
        }
        retained_events = [
            candidate for candidate in events if str(candidate.get("event_id") or _stable_event_id(candidate)) in accepted_ids
        ][-CORRECTION_EVENT_RETENTION_CAP:]
        if accepted_ids and not duplicate_submit:
            _write_correction_event_store(
                store_path,
                {
                    "kind": "agentic-workspace/correction-event-store/v1",
                    "events": retained_events,
                    "compacted_lineage": store.get("compacted_lineage", []) if isinstance(store.get("compacted_lineage"), list) else [],
                    "retention_cap": CORRECTION_EVENT_RETENTION_CAP,
                    "checked_in_repo_effect": "none",
                },
            )
            mutation_applied = True
        status = "stored" if accepted_ids else "blocked"
    receipt = _correction_operation_receipt(
        operation_id=operation_id,
        status=status,
        store_path=store_path,
        target_root=target_root,
        admission=admission,
        mutation_applied=mutation_applied,
    )
    receipt_path = _write_correction_receipt(target_root=target_root, receipt=receipt)
    receipt["receipt_ref"] = _repo_relative(receipt_path, root=target_root)
    return json.loads(json.dumps(receipt, sort_keys=True, default=str))


def _correction_event_matches_query(*, event: dict[str, Any], values: dict[str, Any], subjects: list[dict[str, Any]]) -> bool:
    target_ref = str(values.get("target_identity_ref") or "").strip()
    if target_ref:
        resolution = resolve_target_identity(subjects=subjects, value=target_ref)
        subject = resolution.get("subject") if resolution.get("status") == "known" else None
        expected_target = str(subject.get("stable_target_id") or "") if isinstance(subject, dict) else target_ref
        event_target_ref = str(event.get("target_identity_ref") or "")
        event_resolution = resolve_target_identity(subjects=subjects, value=event_target_ref)
        event_subject = event_resolution.get("subject") if event_resolution.get("status") == "known" else None
        actual_target = str(event_subject.get("stable_target_id") or "") if isinstance(event_subject, dict) else event_target_ref
        if actual_target != expected_target:
            return False
    for field in ("target_revision", "task_class", "scope_class", "phase", "subsystem", "surface"):
        expected = str(values.get(field) or "").strip()
        if expected and str(event.get(field) or "") != expected:
            return False
    return True


def _read_correction_event_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"kind": "agentic-workspace/correction-event-store/v1", "events": [], "compacted_lineage": []}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"kind": "agentic-workspace/correction-event-store/v1", "events": [], "compacted_lineage": [], "status": "unreadable"}
    return loaded if isinstance(loaded, dict) else {"kind": "agentic-workspace/correction-event-store/v1", "events": []}


def _write_correction_event_store(path: Path, store: dict[str, Any], *, expected_digest: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if expected_digest is not None and path.exists():
        current = _json_digest(json.loads(path.read_text(encoding="utf-8")))
        if current != expected_digest:
            raise WorkspaceUsageError("store changed before guidance lifecycle mutation could be applied; retry with fresh revision.")
    lock_path = path.with_name(f".{path.name}.lock")
    lock_fd: int | None = None
    try:
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise WorkspaceUsageError("store is locked by another guidance lifecycle mutation; retry after it completes.") from exc
        os.write(lock_fd, str(os.getpid()).encode("utf-8"))
        tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp_path.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _write_guidance_json_transaction(
    writes: list[tuple[Path, dict[str, Any], str | None]],
    *,
    stale_message: str = "store changed before guidance lifecycle mutation could be applied; retry with fresh revision.",
    journal_root: Path | None = None,
    recovery_result: dict[str, Any] | None = None,
) -> None:
    """Apply guidance writes through a prepared journal recoverable after process loss."""
    if not writes:
        return
    unique: dict[Path, tuple[dict[str, Any], str | None]] = {}
    for path, payload, expected_digest in writes:
        unique[path.resolve()] = (payload, expected_digest)
    if journal_root is None:
        common_parent = Path(os.path.commonpath([str(path.parent) for path in unique]))
        journal_root = common_parent
    journal_root = journal_root.resolve()
    journal_path = journal_root / GUIDANCE_TRANSACTION_JOURNAL_PATH
    external_store_paths = [path for path in sorted(unique) if not path.is_relative_to(journal_root)]
    journal_paths = [
        journal_path,
        *[_guidance_store_transaction_journal_path(path) for path in external_store_paths],
    ]
    for recovery_journal in journal_paths:
        recovered = _recover_guidance_json_transaction(journal_path=recovery_journal)
        if recovered.get("status") == "recovery-conflict":
            raise WorkspaceUsageError(str(recovered.get("reason") or "guidance transaction recovery requires repair."))
    transaction_identity = {
        "paths": [path.as_posix() for path in sorted(unique)],
        "desired_digests": {path.as_posix(): _json_digest(payload) for path, (payload, _) in sorted(unique.items())},
        "expected_digests": {path.as_posix(): expected for path, (_, expected) in sorted(unique.items())},
    }
    transaction_id = "guidance-tx:" + _json_digest(transaction_identity)[:24]
    lock_handles: list[tuple[Path, int]] = []
    snapshots: dict[Path, tuple[bool, bytes]] = {}
    written: list[Path] = []
    tmp_paths: list[Path] = []
    journal_prepared = False
    try:
        for path in [*journal_paths, *sorted(unique)]:
            path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = path.with_name(f".{path.name}.lock")
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as exc:
                raise WorkspaceUsageError("store is locked by another guidance lifecycle mutation; retry after it completes.") from exc
            os.write(lock_fd, transaction_id.encode("utf-8"))
            lock_handles.append((lock_path, lock_fd))
        for path, (_payload, expected_digest) in unique.items():
            existed = path.exists()
            snapshots[path] = (existed, path.read_bytes() if existed else b"")
            if expected_digest is not None and existed:
                current = _json_digest(json.loads(path.read_text(encoding="utf-8")))
                if current != expected_digest:
                    raise WorkspaceUsageError(stale_message)
            if expected_digest is not None and not existed:
                raise WorkspaceUsageError(stale_message)
        journal = {
            "kind": "agentic-workspace/guidance-transaction-journal/v1",
            "status": "prepared",
            "transaction_id": transaction_id,
            "prepared_at": _guidance_now(),
            "writer_pid": os.getpid(),
            "origin_root": journal_root.as_posix(),
            "journal_paths": [path.as_posix() for path in journal_paths],
            "entries": [
                {
                    "path": path.as_posix(),
                    "existed": snapshots[path][0],
                    "before_digest": hashlib.sha256(snapshots[path][1]).hexdigest(),
                    "expected_json_digest": expected_digest,
                    "desired": payload,
                    "desired_json_digest": _json_digest(payload),
                }
                for path, (payload, expected_digest) in sorted(unique.items())
            ],
            "recovery_result": recovery_result or {},
            "rule": "Recovery completes only entries still at their prepared before-state or already at the desired state; concurrent divergence fails closed.",
        }
        for prepared_journal_path in journal_paths:
            _write_guidance_atomic_json(prepared_journal_path, journal, transaction_id=transaction_id)
        journal_prepared = True
        for path, (payload, _expected_digest) in unique.items():
            _write_guidance_atomic_json(path, payload, transaction_id=transaction_id, tmp_paths=tmp_paths)
            written.append(path)
            if _GUIDANCE_TRANSACTION_FAULT_INJECTOR is not None:
                _GUIDANCE_TRANSACTION_FAULT_INJECTOR(f"after-write:{len(written)}", path)
        for path, (payload, _expected_digest) in unique.items():
            if not path.exists() or _json_digest(json.loads(path.read_text(encoding="utf-8"))) != _json_digest(payload):
                raise WorkspaceUsageError("guidance transaction postcondition verification failed; retry recovery.")
        for prepared_journal_path in journal_paths:
            prepared_journal_path.unlink(missing_ok=True)
        journal_prepared = False
    except Exception:
        for path in reversed(written):
            existed, content = snapshots[path]
            if existed:
                _write_guidance_atomic_bytes(path, content, transaction_id=transaction_id)
            else:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
        if journal_prepared:
            for prepared_journal_path in journal_paths:
                prepared_journal_path.unlink(missing_ok=True)
        raise
    finally:
        for tmp_path in tmp_paths:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        for lock_path, lock_fd in lock_handles:
            os.close(lock_fd)
            try:
                if lock_path.read_text(encoding="utf-8") == transaction_id:
                    lock_path.unlink()
            except FileNotFoundError:
                pass


def _write_guidance_atomic_bytes(
    path: Path,
    content: bytes,
    *,
    transaction_id: str,
    tmp_paths: list[Path] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = hashlib.sha256(f"{transaction_id}:{path.as_posix()}".encode("utf-8")).hexdigest()[:12]
    tmp_path = path.with_name(f".{path.name}.{suffix}.tmp")
    if tmp_paths is not None:
        tmp_paths.append(tmp_path)
    with tmp_path.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    tmp_path.replace(path)


def _write_guidance_atomic_json(
    path: Path,
    payload: dict[str, Any],
    *,
    transaction_id: str,
    tmp_paths: list[Path] | None = None,
) -> None:
    content = (json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")
    _write_guidance_atomic_bytes(path, content, transaction_id=transaction_id, tmp_paths=tmp_paths)


def _guidance_store_transaction_journal_path(store_path: Path) -> Path:
    return store_path.resolve().with_name(f".{store_path.name}{GUIDANCE_EXTERNAL_TRANSACTION_JOURNAL_SUFFIX}")


def _guidance_transaction_identity(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "paths": sorted(str(entry.get("path") or "") for entry in entries),
        "desired_digests": {str(entry.get("path") or ""): str(entry.get("desired_json_digest") or "") for entry in entries},
        "expected_digests": {str(entry.get("path") or ""): entry.get("expected_json_digest") for entry in entries},
    }


def _recover_guidance_json_transaction(*, journal_root: Path | None = None, journal_path: Path | None = None) -> dict[str, Any]:
    if (journal_root is None) is (journal_path is None):
        raise WorkspaceUsageError("guidance transaction recovery requires exactly one journal location.")
    if journal_path is None:
        assert journal_root is not None
        journal_path = journal_root.resolve() / GUIDANCE_TRANSACTION_JOURNAL_PATH
    else:
        journal_path = journal_path.resolve()
    if not journal_path.exists():
        return {"status": "none"}
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceUsageError("guidance transaction journal is unreadable; repair it before lifecycle mutation.") from exc
    if (
        journal.get("kind") != "agentic-workspace/guidance-transaction-journal/v1"
        or journal.get("status") != "prepared"
        or not isinstance(journal.get("entries"), list)
        or not str(journal.get("transaction_id") or "").startswith("guidance-tx:")
    ):
        raise WorkspaceUsageError("guidance transaction journal is malformed; repair it before lifecycle mutation.")
    transaction_id = str(journal["transaction_id"])
    entries = [entry for entry in journal["entries"] if isinstance(entry, dict)]
    if len(entries) != len(journal["entries"]):
        raise WorkspaceUsageError("guidance transaction journal contains malformed entries.")
    paths = [Path(str(entry.get("path") or "")).resolve() for entry in entries]
    if any(not str(entry.get("path") or "") for entry in entries) or len(set(paths)) != len(paths):
        raise WorkspaceUsageError("guidance transaction journal path inventory is invalid.")
    expected_transaction_id = "guidance-tx:" + _json_digest(_guidance_transaction_identity(entries))[:24]
    if transaction_id != expected_transaction_id:
        raise WorkspaceUsageError("guidance transaction journal identity does not match its entries.")
    origin_root_value = str(journal.get("origin_root") or "").strip()
    if origin_root_value:
        origin_root = Path(origin_root_value).resolve()
    elif journal_root is not None:
        origin_root = journal_root.resolve()
    else:
        raise WorkspaceUsageError("external guidance transaction journal is missing its origin repository identity.")
    raw_journal_paths = journal.get("journal_paths")
    journal_paths = (
        [Path(str(path)).resolve() for path in raw_journal_paths]
        if isinstance(raw_journal_paths, list) and raw_journal_paths
        else [origin_root / GUIDANCE_TRANSACTION_JOURNAL_PATH]
    )
    if len(set(journal_paths)) != len(journal_paths) or journal_path not in journal_paths:
        raise WorkspaceUsageError("guidance transaction journal mirror inventory is invalid.")
    external_paths = [path for path in paths if not path.is_relative_to(origin_root)]
    expected_external_journals = {_guidance_store_transaction_journal_path(path) for path in external_paths}
    if expected_external_journals - set(journal_paths):
        raise WorkspaceUsageError("guidance transaction journal is not discoverable from every external store.")
    if journal_path != origin_root / GUIDANCE_TRANSACTION_JOURNAL_PATH and journal_path not in expected_external_journals:
        raise WorkspaceUsageError("external guidance transaction journal is not colocated with a transaction store.")
    origin_available = origin_root.exists()
    orphaned_origin_paths = [path for path in paths if path.is_relative_to(origin_root) and not origin_available]
    recoverable_entries = [(path, entry) for path, entry in zip(paths, entries, strict=True) if path not in orphaned_origin_paths]
    recoverable_paths = [path for path, _entry in recoverable_entries]
    existing_journal_paths = [path for path in journal_paths if path.exists() or path.parent.exists()]
    lock_paths = [
        *[path.with_name(f".{path.name}.lock") for path in existing_journal_paths],
        *[path.with_name(f".{path.name}.lock") for path in recoverable_paths],
    ]
    matching_locks: list[Path] = []
    for lock_path in lock_paths:
        try:
            if lock_path.read_text(encoding="utf-8") == transaction_id:
                matching_locks.append(lock_path)
        except FileNotFoundError:
            pass
    writer_pid = journal.get("writer_pid")
    if matching_locks and isinstance(writer_pid, int) and _guidance_process_alive(writer_pid):
        raise WorkspaceUsageError("guidance transaction is still owned by a live writer; retry after it completes.")
    for lock_path in matching_locks:
        lock_path.unlink()
    lock_handles: list[tuple[Path, int]] = []
    tmp_paths: list[Path] = []
    try:
        for path in [*existing_journal_paths, *recoverable_paths]:
            path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = path.with_name(f".{path.name}.lock")
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as exc:
                raise WorkspaceUsageError("guidance transaction recovery is blocked by a concurrent writer.") from exc
            os.write(lock_fd, transaction_id.encode("utf-8"))
            lock_handles.append((lock_path, lock_fd))
        repaired_paths: list[str] = []
        for path, entry in recoverable_entries:
            desired = entry.get("desired")
            if not isinstance(desired, dict) or _json_digest(desired) != entry.get("desired_json_digest"):
                raise WorkspaceUsageError("guidance transaction journal desired payload is invalid.")
            if path.exists():
                current_bytes = path.read_bytes()
                try:
                    current_json_digest = _json_digest(json.loads(current_bytes.decode("utf-8")))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    current_json_digest = ""
                if current_json_digest == entry["desired_json_digest"]:
                    continue
                before_matches = hashlib.sha256(current_bytes).hexdigest() == entry.get("before_digest")
            else:
                before_matches = entry.get("existed") is False
            if not before_matches:
                return {
                    "status": "recovery-conflict",
                    "transaction_id": transaction_id,
                    "reason": f"guidance transaction recovery found a concurrent change at {path.as_posix()}; inspect before retry.",
                }
            _write_guidance_atomic_json(path, desired, transaction_id=transaction_id, tmp_paths=tmp_paths)
            repaired_paths.append(path.as_posix())
            if _GUIDANCE_TRANSACTION_FAULT_INJECTOR is not None:
                _GUIDANCE_TRANSACTION_FAULT_INJECTOR(f"after-recovery-write:{len(repaired_paths)}", path)
        for path, entry in recoverable_entries:
            if not path.exists() or _json_digest(json.loads(path.read_text(encoding="utf-8"))) != entry["desired_json_digest"]:
                raise WorkspaceUsageError("guidance transaction recovery could not prove all postconditions.")
        for prepared_journal_path in journal_paths:
            prepared_journal_path.unlink(missing_ok=True)
        return {
            "status": "recovered",
            "transaction_id": transaction_id,
            "repaired_paths": repaired_paths,
            "origin_root": origin_root.as_posix(),
            "orphaned_origin_paths": [path.as_posix() for path in orphaned_origin_paths],
            "repair_route": (
                {
                    "status": "origin-repository-unavailable",
                    "next_action": "continue the lifecycle operation from the current repository to rebuild its owner registry and receipt",
                    "rule": "The shared user-local store is completed and unlocked; vanished repository-local custody is never recreated outside an explicit repository operation.",
                }
                if orphaned_origin_paths
                else {"status": "not-needed"}
            ),
            "result": journal.get("recovery_result") if isinstance(journal.get("recovery_result"), dict) else {},
        }
    finally:
        for tmp_path in tmp_paths:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        for lock_path, lock_fd in lock_handles:
            os.close(lock_fd)
            try:
                if lock_path.read_text(encoding="utf-8") == transaction_id:
                    lock_path.unlink()
            except FileNotFoundError:
                pass


def _recover_guidance_transactions_for_target(*, target_root: Path) -> dict[str, Any]:
    target_root = target_root.resolve()
    candidates = [target_root / GUIDANCE_TRANSACTION_JOURNAL_PATH]
    try:
        config = load_workspace_config(target_root=target_root)
    except WorkspaceUsageError:
        config = None
    user_root_value = getattr(config.local_override, "user_guidance_root", None) if config is not None else None
    if user_root_value:
        configured_root = Path(user_root_value)
        user_root = configured_root if configured_root.is_absolute() else target_root / configured_root
        if user_root.exists():
            candidates.extend(
                path.resolve() for path in user_root.glob(f"*/.*{GUIDANCE_EXTERNAL_TRANSACTION_JOURNAL_SUFFIX}") if path.is_file()
            )
    recovered_results: list[dict[str, Any]] = []
    for candidate in dict.fromkeys(candidates):
        result = _recover_guidance_json_transaction(journal_path=candidate)
        if result.get("status") == "recovery-conflict":
            return result
        if result.get("status") == "recovered":
            recovered_results.append(result)
    if not recovered_results:
        return {"status": "none"}
    if len(recovered_results) > 1:
        raise WorkspaceUsageError("multiple independent guidance transactions require recovery; retry after inspecting each store.")
    return recovered_results[0]


def _guidance_process_alive(process_id: int) -> bool:
    if process_id <= 0:
        return False
    try:
        os.kill(process_id, 0)
    except OSError:
        return False
    return True


def _write_correction_receipt(*, target_root: Path, receipt: dict[str, Any]) -> Path:
    receipt_id = hashlib.sha256(json.dumps(receipt, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    path = target_root / ".agentic-workspace/local/correction-event-receipts" / f"{receipt_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def _guidance_receipt_index(target_root: Path) -> tuple[Path, dict[str, Any]]:
    path = target_root / GUIDANCE_RECEIPT_INDEX_PATH
    if not path.exists():
        return path, {"kind": "agentic-workspace/guidance-receipt-index/v1", "receipts": []}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceUsageError("guidance receipt index is unreadable; repair it before correction or promotion.") from exc
    if loaded.get("kind") != "agentic-workspace/guidance-receipt-index/v1" or not isinstance(loaded.get("receipts"), list):
        raise WorkspaceUsageError("guidance receipt index is malformed; repair it before correction or promotion.")
    return path, loaded


def _guidance_receipt_ref(receipt: dict[str, Any]) -> str:
    return "guidance-receipt:" + _json_digest({key: value for key, value in receipt.items() if key != "receipt_ref"})[:24]


def _guidance_receipt_write_plan(
    *,
    target_root: Path,
    receipt: dict[str, Any],
    operation_id: str,
) -> tuple[dict[str, Any], list[tuple[Path, dict[str, Any], str | None]]]:
    path, index = _guidance_receipt_index(target_root)
    receipt = {
        "kind": "agentic-workspace/guidance-receipt/v1",
        "status": "current",
        "recorded_at": _guidance_now(),
        "custody": {
            "operation_id": operation_id,
            "producer": "agentic-workspace.guidance-receipt-index",
            "trusted_channel": "producer-owned-local-operation",
            "index_ref": GUIDANCE_RECEIPT_INDEX_PATH.as_posix(),
        },
        **receipt,
    }
    receipt["receipt_ref"] = _guidance_receipt_ref(receipt)
    receipts = [item for item in index.get("receipts", []) if isinstance(item, dict)]
    existing = next((item for item in receipts if item.get("receipt_ref") == receipt["receipt_ref"]), None)
    writes: list[tuple[Path, dict[str, Any], str | None]] = []
    if existing is None:
        writes.append(
            (
                path,
                {"kind": "agentic-workspace/guidance-receipt-index/v1", "receipts": [*receipts, receipt]},
                _json_digest(index) if path.exists() else None,
            )
        )
        stored = receipt
    else:
        stored = existing
    result = {
        "kind": "agentic-workspace/guidance-receipt-operation-result/v1",
        "operation_id": operation_id,
        "status": "stored",
        "receipt_ref": str(stored.get("receipt_ref") or ""),
        "receipt": stored,
        "store": GUIDANCE_RECEIPT_INDEX_PATH.as_posix(),
        "rule": "Correction and guidance authority receipts resolve only through this producer-owned index; arbitrary JSON paths are not authority.",
    }
    return result, writes


def _store_guidance_receipt(*, target_root: Path, receipt: dict[str, Any], operation_id: str) -> dict[str, Any]:
    result, writes = _guidance_receipt_write_plan(target_root=target_root, receipt=receipt, operation_id=operation_id)
    _write_guidance_json_transaction(writes, journal_root=target_root)
    return result


def record_trusted_authority_host_event(
    *,
    target_root: Path,
    authority: str,
    producer_class: str,
    producer_id: str,
    source_ref: str,
    source: str = "",
    target_revision: str = "",
    event_id: str = "",
    trusted_channel: str = "host-trusted-authority-event",
    host_event_ref: str = "",
    host_event_resolver: TrustedAuthorityHostEventResolver | None = None,
) -> dict[str, Any]:
    ref = str(host_event_ref or "").strip()
    if not ref.startswith("trusted-authority-event:") or "/" in ref or "\\" in ref:
        raise WorkspaceUsageError("trusted authority host event imports require an opaque host_event_ref.")
    if host_event_resolver is not None:
        raise WorkspaceUsageError(
            "caller-provided trusted authority host event resolvers are rejected; import a signed host event envelope."
        )
    event = _load_trusted_authority_host_event_from_inbox(target_root=target_root, host_event_ref=ref)
    if not isinstance(event, dict):
        raise WorkspaceUsageError("trusted authority host resolver returned the wrong contract.")
    if event.get("kind") != "agentic-workspace/trusted-authority-host-event/v1" or event.get("event_ref") != ref:
        raise WorkspaceUsageError("trusted authority host resolver returned the wrong contract.")
    expected_inputs = {
        "authority": authority,
        "producer_class": producer_class,
        "producer_id": producer_id,
        "source": source or authority,
        "source_ref": source_ref,
        "target_revision": target_revision,
        "event_id": event_id,
    }
    if any(str(event.get(key) or "") != expected for key, expected in expected_inputs.items() if expected):
        raise WorkspaceUsageError("trusted authority host event inputs do not match the signed host event.")
    custody_raw = event.get("custody")
    custody: dict[str, Any] = custody_raw if isinstance(custody_raw, dict) else {}
    if trusted_channel and str(custody.get("trusted_channel") or "") != trusted_channel:
        raise WorkspaceUsageError("trusted authority host event channel does not match the requested trusted_channel.")
    if not _host_admits_trusted_authority_event(ref=ref, event=event, target_root=target_root):
        raise WorkspaceUsageError("trusted authority host event was not admitted by the host boundary.")
    path = target_root / TRUSTED_AUTHORITY_EVENT_STORE_PATH / f"{ref.removeprefix('trusted-authority-event:')}.json"
    index_path = target_root / TRUSTED_AUTHORITY_EVENT_INDEX_PATH
    try:
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceUsageError("trusted authority host event index is unreadable; repair it before importing evidence.") from exc
    if not isinstance(index, dict) or (index and index.get("kind") != "agentic-workspace/trusted-authority-host-event-index/v1"):
        raise WorkspaceUsageError("trusted authority host event index has the wrong contract.")
    events = [entry for entry in index.get("events", []) if isinstance(entry, dict)]
    event_digest = _trusted_authority_event_digest(event)
    stored = {
        **event,
        "import_custody": {
            "kind": "agentic-workspace/trusted-authority-host-event-import/v1",
            "importer": "agentic-workspace.guidance-authority-import",
            "source": "signed-host-event-inbox",
            "event_digest": event_digest,
            "signature_key_id": str(event.get("host_admission", {}).get("key_id") or "")
            if isinstance(event.get("host_admission"), dict)
            else "",
        },
        "event_path": path.relative_to(target_root).as_posix(),
        "revision": event_digest,
    }
    entries = [entry for entry in events if entry.get("event_ref") != ref]
    entries.append(
        {
            "event_ref": ref,
            "path": stored["event_path"],
            "revision": event_digest,
            "status": str(stored.get("status") or ""),
            "authority": str(stored.get("authority") or ""),
            "producer_class": str(stored.get("producer_class") or ""),
            "source_ref": str(stored.get("source_ref") or ""),
        }
    )
    _write_guidance_json_transaction(
        [
            (path, stored, _json_digest(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else None),
            (
                index_path,
                {"kind": "agentic-workspace/trusted-authority-host-event-index/v1", "events": entries},
                _json_digest(index) if index_path.exists() else None,
            ),
        ],
        journal_root=target_root,
    )
    return {
        "kind": "agentic-workspace/trusted-authority-host-event-import-result/v1",
        "status": "imported",
        "event_ref": ref,
        "event": stored,
        "event_store": TRUSTED_AUTHORITY_EVENT_STORE_PATH.as_posix(),
        "event_index": TRUSTED_AUTHORITY_EVENT_INDEX_PATH.as_posix(),
        "rule": "Repo-local guidance code imports signed producer-owned host events; local transport JSON is untrusted until a pinned host signature admits it.",
    }


def _trusted_authority_event_digest(event: dict[str, Any]) -> str:
    return _json_digest(
        {
            key: value
            for key, value in event.items()
            if key
            not in {
                "event_path",
                "host_admission",
                "host_admission_ref",
                "host_admission_verdict",
                "import_custody",
                "revision",
            }
        }
    )


def _trusted_authority_admission_signature_payload(
    *,
    ref: str,
    event: dict[str, Any],
    verdict: dict[str, Any],
    admission: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/trusted-authority-host-admission-signature-payload/v1",
        "algorithm": str(admission.get("algorithm") or ""),
        "key_id": str(admission.get("key_id") or ""),
        "event_ref": ref,
        "event_digest": _trusted_authority_event_digest(event),
        "verdict_digest": _json_digest(verdict),
        "audience": TRUSTED_AUTHORITY_EVENT_AUDIENCE,
    }


def _base64url_decode(value: str) -> bytes:
    text = value.strip()
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _verify_rs256_signature(*, key: dict[str, str], payload: dict[str, Any], signature: str) -> bool:
    try:
        n = int(str(key.get("n") or ""), 16)
        e = int(str(key.get("e") or ""), 16)
        raw_signature = _base64url_decode(signature)
    except (ValueError, TypeError):
        return False
    key_size = (n.bit_length() + 7) // 8
    if len(raw_signature) != key_size:
        return False
    message = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest_info = _RSA_SHA256_DER_PREFIX + hashlib.sha256(message).digest()
    encoded = pow(int.from_bytes(raw_signature, "big"), e, n).to_bytes(key_size, "big")
    minimum_padding = 8
    if not (encoded.startswith(b"\x00\x01") and b"\x00" in encoded[2 + minimum_padding :]):
        return False
    separator = encoded.find(b"\x00", 2)
    if separator < 2 + minimum_padding:
        return False
    padding = encoded[2:separator]
    if len(padding) < minimum_padding or any(byte != 0xFF for byte in padding):
        return False
    return hmac.compare_digest(encoded[separator + 1 :], digest_info)


def _parse_guidance_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _host_admits_trusted_authority_event(*, ref: str, event: dict[str, Any], target_root: Path) -> bool:
    """Return whether a pinned host signature admitted this event."""

    verdict_raw = event.get("host_admission_verdict")
    if not isinstance(verdict_raw, dict):
        return False
    verdict: dict[str, Any] = verdict_raw
    admission_raw = event.get("host_admission")
    if not isinstance(admission_raw, dict):
        return False
    admission: dict[str, Any] = admission_raw
    key_id = str(admission.get("key_id") or "")
    key = _TRUSTED_AUTHORITY_HOST_PUBLIC_KEYS.get(key_id)
    if not isinstance(key, dict) or key.get("status") != "current":
        return False
    if admission.get("kind") != "agentic-workspace/trusted-authority-host-admission/v1":
        return False
    if admission.get("algorithm") != "RS256" or key.get("algorithm") != "RS256":
        return False
    if verdict.get("kind") != "agentic-workspace/trusted-authority-host-event-verdict/v1":
        return False
    if verdict.get("status") != "admitted" or verdict.get("admission_authority") != "signed-host-adapter":
        return False
    if str(verdict.get("event_ref") or "") != ref or str(verdict.get("event_digest") or "") != _trusted_authority_event_digest(event):
        return False
    custody_raw = event.get("custody")
    custody: dict[str, Any] = custody_raw if isinstance(custody_raw, dict) else {}
    if str(key.get("issuer") or "") != str(custody.get("producer") or ""):
        return False
    if str(key.get("trusted_channel") or "") != str(custody.get("trusted_channel") or ""):
        return False
    if str(verdict.get("producer") or "") != str(custody.get("producer") or ""):
        return False
    if str(verdict.get("trusted_channel") or "") != str(custody.get("trusted_channel") or ""):
        return False
    if str(verdict.get("workspace_ref") or "") != f"workspace:path:{target_root.resolve()}":
        return False
    if str(verdict.get("audience") or "") != TRUSTED_AUTHORITY_EVENT_AUDIENCE:
        return False
    for verdict_field, event_field in (
        ("correction_authority", "authority"),
        ("producer_class", "producer_class"),
        ("source_ref", "source_ref"),
        ("target_revision", "target_revision"),
        ("event_id", "event_id"),
    ):
        if str(verdict.get(verdict_field) or "") != str(event.get(event_field) or ""):
            return False
    issued_at = _parse_guidance_time(verdict.get("issued_at"))
    expires_at = _parse_guidance_time(verdict.get("expires_at"))
    if issued_at is None or expires_at is None or expires_at <= issued_at or expires_at <= datetime.now(UTC):
        return False
    if not str(verdict.get("nonce") or "").strip() or not str(verdict.get("verifier_revision") or "").strip():
        return False
    if str(verdict.get("revoked_at") or "").strip() or str(verdict.get("superseded_by") or "").strip():
        return False
    payload = _trusted_authority_admission_signature_payload(ref=ref, event=event, verdict=verdict, admission=admission)
    return _verify_rs256_signature(key=key, payload=payload, signature=str(admission.get("signature") or ""))


def _trusted_authority_host_event(*, target_root: Path, event_ref: str) -> dict[str, Any]:
    ref = str(event_ref or "").strip()
    if not ref.startswith("trusted-authority-event:") or "/" in ref or "\\" in ref:
        raise WorkspaceUsageError("trusted authority receipts require a trusted host event ref.")
    path = target_root / TRUSTED_AUTHORITY_EVENT_STORE_PATH / f"{ref.removeprefix('trusted-authority-event:')}.json"
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceUsageError("trusted authority host event is missing or unreadable.") from exc
    if event.get("kind") != "agentic-workspace/trusted-authority-host-event/v1" or event.get("event_ref") != ref:
        raise WorkspaceUsageError("trusted authority host event has the wrong contract.")
    if event.get("status") != "current":
        raise WorkspaceUsageError("trusted authority host event is not current.")
    import_custody = event.get("import_custody") if isinstance(event.get("import_custody"), dict) else {}
    if (
        import_custody.get("kind") != "agentic-workspace/trusted-authority-host-event-import/v1"
        or import_custody.get("source") != "signed-host-event-inbox"
        or import_custody.get("event_digest") != _trusted_authority_event_digest(event)
    ):
        raise WorkspaceUsageError("trusted authority host event was not imported through the signed host boundary.")
    if not _host_admits_trusted_authority_event(ref=ref, event=event, target_root=target_root):
        raise WorkspaceUsageError("trusted authority host event was not admitted by the host boundary.")
    custody = event.get("custody") if isinstance(event.get("custody"), dict) else {}
    if custody.get("producer") in {"", "agentic-workspace.trusted-authority-host-event", "caller", "implementer"}:
        raise WorkspaceUsageError("trusted authority host event is not producer-owned.")
    if custody.get("trusted_channel") not in {"github-review-webhook", "human-instruction-host", "evaluation-result-adapter"}:
        raise WorkspaceUsageError("trusted authority host event does not come from an admitted host channel.")
    authority = str(event.get("authority") or "")
    producer_class = str(event.get("producer_class") or "")
    if authority not in ADMITTED_CORRECTION_AUTHORITIES or producer_class not in TRUSTED_CORRECTION_PRODUCERS.get(authority, set()):
        raise WorkspaceUsageError("trusted authority host event producer is not admitted for this authority.")
    if not str(event.get("source_ref") or ""):
        raise WorkspaceUsageError("trusted authority host event is missing source_ref.")
    return event


def record_trusted_authority_receipt(
    *,
    target_root: Path,
    authority: str,
    producer_class: str,
    producer_id: str,
    source_ref: str,
    source: str = "",
    target_revision: str = "",
    event_id: str = "",
    host_event_ref: str = "",
) -> dict[str, Any]:
    event = _trusted_authority_host_event(target_root=target_root, event_ref=host_event_ref)
    if any(
        str(event.get(key) or "") != expected
        for key, expected in {
            "authority": authority,
            "producer_class": producer_class,
            "producer_id": producer_id,
            "source_ref": source_ref,
            "source": source or authority,
            "target_revision": target_revision,
            "event_id": event_id,
        }.items()
        if expected
    ):
        raise WorkspaceUsageError("trusted authority receipt inputs do not match the host event.")
    return _store_guidance_receipt(
        target_root=target_root,
        operation_id="agent-guidance.receipt.authorize-correction",
        receipt={
            "receipt_type": "trusted-authority",
            "authority": authority,
            "producer_class": producer_class,
            "producer_id": producer_id,
            "source": source or authority,
            "source_ref": source_ref,
            "target_revision": target_revision,
            "event_id": event_id,
            "host_event_ref": host_event_ref,
        },
    )


def record_guidance_remember_receipt(
    *,
    target_root: Path,
    producer_class: str,
    producer_id: str,
    source_ref: str,
    target_revision: str = "",
    event_id: str = "",
    instruction: str = "remember",
    host_event_ref: str = "",
) -> dict[str, Any]:
    event = _trusted_authority_host_event(target_root=target_root, event_ref=host_event_ref)
    if event.get("authority") != "explicit-user-correction":
        raise WorkspaceUsageError("remember receipts require an explicit-user-correction host event.")
    if any(
        str(event.get(key) or "") != expected
        for key, expected in {
            "producer_class": producer_class,
            "producer_id": producer_id,
            "source_ref": source_ref,
            "target_revision": target_revision,
            "event_id": event_id,
        }.items()
        if expected
    ):
        raise WorkspaceUsageError("remember receipt inputs do not match the host event.")
    return _store_guidance_receipt(
        target_root=target_root,
        operation_id="agent-guidance.receipt.remember",
        receipt={
            "receipt_type": "remember",
            "authority": "explicit-user-correction",
            "producer_class": producer_class,
            "producer_id": producer_id,
            "source": "explicit-user-correction",
            "source_ref": source_ref,
            "target_revision": target_revision,
            "event_id": event_id,
            "instruction": instruction or "remember",
            "host_event_ref": host_event_ref,
        },
    )


def _guidance_receipt_by_ref(*, target_root: Path, value: Any, receipt_type: str) -> dict[str, Any] | None:
    ref = str(value or "").strip()
    if not ref or "/" in ref or "\\" in ref or not ref.startswith("guidance-receipt:"):
        return None
    try:
        _path, index = _guidance_receipt_index(target_root)
    except WorkspaceUsageError:
        return None
    receipt = next(
        (item for item in index.get("receipts", []) if isinstance(item, dict) and str(item.get("receipt_ref") or "") == ref),
        None,
    )
    if not isinstance(receipt, dict):
        return None
    if receipt.get("kind") != "agentic-workspace/guidance-receipt/v1":
        return None
    if str(receipt.get("receipt_type") or "") != receipt_type:
        return None
    if str(receipt.get("status") or "") != "current":
        return None
    custody = receipt.get("custody") if isinstance(receipt.get("custody"), dict) else {}
    if custody.get("producer") != "agentic-workspace.guidance-receipt-index":
        return None
    return receipt


def _operation_subjects(*, values: dict[str, Any], config: Any) -> list[dict[str, Any]]:
    subjects_json = values.get("subjects_json") if values.get("_fixture_allow_subjects_json") else None
    if subjects_json:
        try:
            loaded = json.loads(str(subjects_json))
        except json.JSONDecodeError:
            loaded = []
        if isinstance(loaded, list):
            return [dict(item) for item in loaded if isinstance(item, dict)]
    return [_target_identity_subject(profile) for profile in config.local_override.delegation_targets]


def _operation_event(*, values: dict[str, Any], operation: str, target_root: Path) -> dict[str, Any]:
    event_json = values.get("event_json")
    if event_json:
        try:
            loaded = json.loads(str(event_json))
        except json.JSONDecodeError:
            loaded = {}
        event = dict(loaded) if isinstance(loaded, dict) else {}
    else:
        event = {}
    operation_metadata_keys = {
        "event_json",
        "subjects_json",
        "trusted_authority_receipt_json",
        "trusted_authority_receipt_ref",
        "target",
        "target_root",
        "format",
        "dry_run",
        "verbose",
    }
    event.update({key: value for key, value in values.items() if value not in (None, "", []) and key not in operation_metadata_keys})
    event["operation"] = {
        "submit": "submit",
        "correct-dispute": "dispute",
        "withdraw-supersede": str(values.get("lifecycle_action") or "withdraw"),
    }.get(operation, operation)
    trusted_receipt = _trusted_authority_receipt(target_root=target_root, value=values.get("trusted_authority_receipt_ref"))
    if trusted_receipt:
        event["authority"] = trusted_receipt["authority"]
        event["producer_class"] = trusted_receipt["producer_class"]
        event["producer_id"] = trusted_receipt["producer_id"]
        event["source"] = trusted_receipt["source"]
        event.setdefault("source_ref", trusted_receipt["source_ref"])
        event["authority_resolution_source"] = "trusted-operation-receipt"
    else:
        event["authority"] = "agent-self-observation"
        event["producer_class"] = "agent"
        event.setdefault("producer_id", "agent-self-observation")
        event.setdefault("source", "agent-local-observation")
        event["authority_resolution_source"] = "operation-boundary-low-authority-default"
    return event


def _trusted_authority_receipt(*, target_root: Path, value: Any) -> dict[str, str] | None:
    receipt = _guidance_receipt_by_ref(target_root=target_root, value=value, receipt_type="trusted-authority")
    if receipt is None:
        return None
    authority = str(receipt.get("authority") or "")
    producer_class = str(receipt.get("producer_class") or "")
    if authority not in ADMITTED_CORRECTION_AUTHORITIES:
        return None
    if producer_class not in TRUSTED_CORRECTION_PRODUCERS.get(authority, set()):
        return None
    source_ref = str(receipt.get("source_ref") or "")
    if not source_ref:
        return None
    if str(receipt.get("status") or "current") in {"stale", "superseded", "revoked", "closed"}:
        return None
    return {
        "authority": authority,
        "producer_class": producer_class,
        "producer_id": str(receipt.get("producer_id") or producer_class),
        "source": str(receipt.get("source") or authority),
        "source_ref": source_ref,
    }


def _guidance_remember_receipt(*, target_root: Path, event: dict[str, Any]) -> dict[str, Any] | None:
    receipt_ref = str(event.get("remember_receipt_ref") or event.get("remember_instruction_ref") or "")
    if not receipt_ref:
        return None
    receipt = _guidance_receipt_by_ref(target_root=target_root, value=receipt_ref, receipt_type="remember")
    if receipt is None:
        return None
    if str(receipt.get("status") or "") != "current":
        return None
    if str(receipt.get("authority") or "") != "explicit-user-correction":
        return None
    producer_class = str(receipt.get("producer_class") or "")
    if producer_class not in TRUSTED_CORRECTION_PRODUCERS["explicit-user-correction"]:
        return None
    if str(receipt.get("producer_id") or "") != str(event.get("producer_id") or ""):
        return None
    if str(receipt.get("source_ref") or "") != str(event.get("source_ref") or ""):
        return None
    receipt_event_id = str(receipt.get("event_id") or "")
    if receipt_event_id and receipt_event_id != str(event.get("event_id") or ""):
        return None
    target_revision = str(event.get("target_revision") or "")
    receipt_target_revision = str(receipt.get("target_revision") or "")
    if receipt_target_revision and target_revision and receipt_target_revision != target_revision:
        return None
    return {
        "receipt_ref": receipt_ref,
        "receipt_digest": _json_digest(receipt),
        "receipt_store": GUIDANCE_RECEIPT_INDEX_PATH.as_posix(),
        "instruction": str(receipt.get("instruction") or "remember"),
        "producer_id": str(receipt.get("producer_id") or ""),
        "source_ref": str(receipt.get("source_ref") or ""),
    }


def _correction_operation_receipt(
    *,
    operation_id: str,
    status: str,
    store_path: Path,
    target_root: Path,
    admission: dict[str, Any],
    mutation_applied: bool,
) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/correction-event-operation-result/v1",
        "operation_id": operation_id,
        "status": status,
        "mutation_applied": mutation_applied,
        "store_ref": _repo_relative(store_path, root=target_root),
        "admission": admission,
        "admitted_event_count": len(admission.get("admitted_events", [])),
        "low_authority_event_count": len(admission.get("low_authority_events", [])),
        "rejected_event_count": len(admission.get("rejected_events", [])),
        "checked_in_repo_effect": "none",
        "rule": "Generated correction-event operations are the authoritative public boundary; raw local file writes are compatibility-only.",
    }


def _repo_relative(path: Path, *, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _guidance_destination_for_event(*, event: dict[str, Any], target_root: Path | None = None, config: Any | None = None) -> dict[str, Any]:
    routes = [str(item) for item in event.get("route_decisions", []) if str(item).strip()]
    target_id = str(event.get("target_identity_ref") or "unknown-target")
    safe_target_id = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in target_id).strip("-") or "target"
    if "no-retention" in routes:
        return {"owner": "dismissal", "store": None, "route_decision": "no-retention", "promotable": False}
    if "target-guidance" in routes:
        if config is not None and getattr(config.local_override, "user_guidance_root", None):
            store = Path(config.local_override.user_guidance_root) / safe_target_id / "guidance-lifecycle.json"
            return {
                "owner": "user-local-target-guidance",
                "owner_operation_id": "agent-guidance.promote.target-guidance",
                "store": store.as_posix(),
                "route_decision": "target-guidance",
                "promotable": True,
            }
        overlay = (
            config.local_override.target_guidance_overlay_path
            if config is not None and getattr(config.local_override, "target_guidance_overlay_path", None)
            else WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH
        )
        return {
            "owner": "repo-local-target-guidance-overlay",
            "owner_operation_id": "agent-guidance.promote.target-guidance",
            "store": Path(overlay).as_posix(),
            "route_decision": "target-guidance",
            "promotable": True,
        }
    if "memory" in routes:
        return {
            "owner": "checked-in-memory",
            "store": ".agentic-workspace/memory/guidance-lifecycle.json",
            "route_decision": "memory",
            "promotable": False,
            "owner_operation_required": "memory.guidance-promote",
            "promotion_status": "owner-operation-required",
        }
    if "config" in routes:
        return {
            "owner": "policy-config-review",
            "store": ".agentic-workspace/local/guidance-policy-review.json",
            "route_decision": "config",
            "promotable": False,
            "owner_operation_required": "config.guidance-review-intake",
            "promotion_status": "owner-operation-required",
        }
    if "issue" in routes:
        return {
            "owner": "issue-intake",
            "store": ".agentic-workspace/local/guidance-issue-intake.json",
            "route_decision": "issue",
            "promotable": False,
            "owner_operation_required": "issue.guidance-intake",
            "promotion_status": "owner-operation-required",
        }
    return {"owner": "review-required", "store": None, "route_decision": "unresolved", "promotable": False}


def _promotion_blocker_for_event(*, event: dict[str, Any]) -> str:
    review_required = _correction_requires_review(event)
    if review_required:
        return review_required
    raw_independent = event.get("independent_recurrence")
    independent: dict[str, Any] = raw_independent if isinstance(raw_independent, dict) else {}
    if independent.get("correlated_delivery_detected"):
        return "correlated-delivery"
    return ""


def guidance_promotion_decision(
    *,
    admission: dict[str, Any],
    target_root: Path | None = None,
    config: Any | None = None,
    explicit_remember: bool = False,
) -> dict[str, Any]:
    """Derive one compact, reviewable guidance candidate from admitted events.

    This is intentionally a pure projection: correction-event admission remains
    the authority for evidence, while callers own the chosen durable sink.
    """
    events = [event for event in admission.get("admitted_events", []) if isinstance(event, dict)]
    candidates: list[dict[str, Any]] = []
    for event in events:
        authority = str(event.get("authority") or "")
        recurrence = int(event.get("recurrence_count") or 1)
        remember_receipt = _guidance_remember_receipt(target_root=target_root, event=event) if target_root is not None else None
        immediate = remember_receipt is not None and authority == "explicit-user-correction"
        independent = event.get("independent_recurrence") if isinstance(event.get("independent_recurrence"), dict) else {}
        independent_recurrence = recurrence >= 2 and independent.get("status") == "independent"
        promotion_blocker = _promotion_blocker_for_event(event=event)
        destination = _guidance_destination_for_event(event=event, target_root=target_root, config=config)
        destination_blocker = str(destination.get("promotion_status") or "") if not destination.get("promotable") else ""
        promotable = (immediate or independent_recurrence) and not promotion_blocker and bool(destination.get("promotable"))
        applicability = event.get("semantic_identity") if isinstance(event.get("semantic_identity"), dict) else {}
        desired = str(event.get("desired_behavior") or "").strip()
        candidates.append(
            {
                "guidance_id": "guidance:"
                + hashlib.sha256(str(event.get("normalized_correction_key") or event.get("event_id")).encode()).hexdigest()[:20],
                "status": "active" if promotable else "candidate",
                "instruction": desired,
                "applicability": applicability,
                "authority": authority,
                "promotion_reason": "explicit-authorised-remember"
                if immediate
                else "independent-recurrence"
                if promotable
                else promotion_blocker or destination_blocker or "insufficient-independent-evidence",
                "promotion_authority": {
                    "remember_receipt": remember_receipt,
                    "independent_recurrence": independent,
                    "caller_explicit_remember_ignored": explicit_remember and remember_receipt is None,
                    "blocker": promotion_blocker or destination_blocker or None,
                },
                "evidence_refs": [str(event.get("source_ref"))],
                "source_event_refs": [str(event.get("event_id"))],
                "recurrence_count": recurrence,
                "primary_owner": destination["owner"],
                "destination": destination,
                "lifecycle": {
                    "allowed": ["edit", "merge", "split", "suppress", "revalidate", "weaken", "supersede", "retire", "delete"],
                    "provenance_retained": True,
                },
            }
        )
    low_authority = [event for event in admission.get("low_authority_events", []) if isinstance(event, dict)]
    return {
        "kind": "agentic-workspace/agent-guidance-promotion-decision/v1",
        "status": "ready"
        if any(item["status"] == "active" for item in candidates)
        else "review-required"
        if candidates or low_authority
        else "no-candidate",
        "guidance": candidates,
        "low_authority_evidence": [str(event.get("event_id")) for event in low_authority],
        "hygiene": {
            "duplicate_prevented_by": "normalized correction identity",
            "oversized_instruction_count": sum(len(item["instruction"]) > 280 for item in candidates),
            "raw_transcripts_retained": False,
        },
        "rule": "Only explicit authorised remember instructions or independently admitted repeated corrections may activate durable guidance; self-observation remains a candidate.",
    }


def guidance_promotion_from_store(
    *,
    target_root: Path,
    task_class: str | None = None,
    scope_class: str | None = None,
    explicit_remember: bool = False,
) -> dict[str, Any]:
    """Derive promotion only from the bounded correction-event authority store.

    The public store path is the custody boundary: callers cannot provide a
    recurrence count, source authority, or immediate-remember flag here.
    """
    config = load_workspace_config(target_root=target_root)
    store = _read_correction_event_store(target_root / config.local_override.correction_events_path)
    if store.get("status") == "unreadable":
        return {
            "kind": "agentic-workspace/agent-guidance-promotion-decision/v1",
            "status": "repair-required",
            "repair": "repair the canonical correction-event store before guidance promotion",
        }
    admission = admit_correction_events(
        events=[item for item in store.get("events", []) if isinstance(item, dict)],
        subjects=[_target_identity_subject(profile) for profile in config.local_override.delegation_targets],
        task_class=task_class,
        scope_class=scope_class,
    )
    decision = guidance_promotion_decision(admission=admission, target_root=target_root, config=config, explicit_remember=explicit_remember)
    decision["authority_source"] = {
        "store": _repo_relative(target_root / config.local_override.correction_events_path, root=target_root),
        "store_update": admission.get("store_update", {}),
        "admission_summary": {
            "admitted_event_ids": [
                str(event.get("event_id") or "") for event in admission.get("admitted_events", []) if isinstance(event, dict)
            ],
            "rejected_reasons": sorted(
                {str(event.get("reason") or "") for event in admission.get("rejected_events", []) if isinstance(event, dict)}
            ),
            "low_authority_event_ids": [
                str(event.get("event_id") or "") for event in admission.get("low_authority_events", []) if isinstance(event, dict)
            ],
        },
        "explicit_remember_requested": explicit_remember,
        "rule": "Promotion consumes admitted current store records and producer-owned receipts; direct caller recurrence, authority, and remember assertions are ignored.",
    }
    return decision


GUIDANCE_LIFECYCLE_STORE_PATH = Path(".agentic-workspace/local/guidance-lifecycle.json")
GUIDANCE_STORE_OWNER_REGISTRY_PATH = Path(".agentic-workspace/local/guidance-store-owners.json")
_GUIDANCE_LIFECYCLE_OPERATIONS = {"edit", "merge", "split", "suppress", "revalidate", "weaken", "supersede", "retire", "delete"}
_GUIDANCE_TERMINAL_STATUSES = {"retired", "deleted", "superseded", "merged", "split-retired"}


def _guidance_lifecycle_store(target_root: Path, store_ref: str | Path | None = None) -> tuple[Path, dict[str, Any]]:
    path = target_root / (Path(store_ref) if store_ref else GUIDANCE_LIFECYCLE_STORE_PATH)
    if not path.exists():
        payload = {"kind": "agentic-workspace/guidance-lifecycle-store/v1", "records": []}
    else:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceUsageError("guidance lifecycle store is unreadable; repair it before promotion or transition.") from exc
    if payload.get("kind") != "agentic-workspace/guidance-lifecycle-store/v1" or not isinstance(payload.get("records"), list):
        raise WorkspaceUsageError("guidance lifecycle store is malformed; repair it before promotion or transition.")
    return path, payload


def _guidance_store_owner_registry(target_root: Path) -> tuple[Path, dict[str, Any], str | None]:
    path = target_root / GUIDANCE_STORE_OWNER_REGISTRY_PATH
    if not path.exists():
        return path, {"kind": "agentic-workspace/guidance-store-owner-registry/v1", "stores": []}, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceUsageError("guidance store owner registry is unreadable; repair it before lifecycle mutation.") from exc
    if payload.get("kind") != "agentic-workspace/guidance-store-owner-registry/v1" or not isinstance(payload.get("stores"), list):
        raise WorkspaceUsageError("guidance store owner registry is malformed; repair it before lifecycle mutation.")
    return path, payload, _json_digest(payload)


def _candidate_guidance_store_refs(*, target_root: Path, config: Any | None = None) -> list[Path]:
    refs = [GUIDANCE_LIFECYCLE_STORE_PATH, WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH]
    if config is not None:
        overlay = getattr(config.local_override, "target_guidance_overlay_path", None)
        if overlay:
            refs.append(Path(overlay))
        user_root = getattr(config.local_override, "user_guidance_root", None)
        if user_root:
            configured_user_path = Path(user_root)
            user_path = configured_user_path if configured_user_path.is_absolute() else target_root / configured_user_path
            for path in user_path.glob("*/guidance-lifecycle.json"):
                if not path.is_file():
                    continue
                resolved = path.resolve()
                refs.append(resolved.relative_to(target_root.resolve()) if resolved.is_relative_to(target_root.resolve()) else resolved)
    refs.extend(
        [
            Path(".agentic-workspace/memory/guidance-lifecycle.json"),
            Path(".agentic-workspace/local/guidance-policy-review.json"),
            Path(".agentic-workspace/local/guidance-issue-intake.json"),
        ]
    )
    _, owner_registry, _ = _guidance_store_owner_registry(target_root)
    for raw_store in owner_registry["stores"]:
        if not isinstance(raw_store, dict) or raw_store.get("status") != "current":
            continue
        store_ref = str(raw_store.get("store_ref") or "")
        if store_ref:
            refs.append(Path(store_ref))
    deduped: list[Path] = []
    for ref in refs:
        if ref not in deduped:
            deduped.append(ref)
    return deduped


def _guidance_store_location_identity(*, path: Path, target_root: Path) -> dict[str, Any]:
    resolved = path.resolve()
    repo_root = target_root.resolve()
    external = not resolved.is_relative_to(repo_root)
    return {
        "kind": "agentic-workspace/guidance-store-location/v1",
        "scope": "user-local-external" if external else "repository-local",
        "store_ref": resolved.as_posix() if external else resolved.relative_to(repo_root).as_posix(),
        "absolute": external,
        "owner": "user-local-target-guidance" if external else "repo-local-target-guidance-overlay",
    }


def _matching_guidance_lifecycle_stores(
    *, target_root: Path, guidance_id: str, semantic_identity: str = ""
) -> list[tuple[Path, dict[str, Any], int]]:
    config = load_workspace_config(target_root=target_root)
    matches: list[tuple[Path, dict[str, Any], int]] = []
    for store_ref in _candidate_guidance_store_refs(target_root=target_root, config=config):
        path, store = _guidance_lifecycle_store(target_root, store_ref)
        records = [item for item in store["records"] if isinstance(item, dict)]
        for index, record in enumerate(records):
            record_identity = _json_digest(
                {
                    "instruction": str(record.get("instruction") or ""),
                    "applicability": record.get("applicability") if isinstance(record.get("applicability"), dict) else {},
                }
            )
            if record.get("guidance_id") == guidance_id or (semantic_identity and record_identity == semantic_identity):
                store["records"] = records
                matches.append((path, store, index))
    return matches


def _find_guidance_lifecycle_store(target_root: Path, guidance_id: str) -> tuple[Path, dict[str, Any], int] | None:
    matches = _matching_guidance_lifecycle_stores(target_root=target_root, guidance_id=guidance_id)
    active = [match for match in matches if str(match[1]["records"][match[2]].get("status") or "") not in _GUIDANCE_TERMINAL_STATUSES]
    if len(active) > 1:
        stores = [_guidance_store_location_identity(path=path, target_root=target_root)["store_ref"] for path, _, _ in active]
        raise WorkspaceUsageError(
            "guidance lifecycle authority is duplicated across stores; reconcile one canonical owner before transition: "
            + ", ".join(stores)
        )
    return active[0] if active else matches[0] if matches else None


def _guidance_revision(record: dict[str, Any]) -> int:
    try:
        return int(record.get("revision") or 0)
    except (TypeError, ValueError):
        return 0


def _guidance_index(records: list[dict[str, Any]], guidance_id: str) -> int | None:
    return next((index for index, item in enumerate(records) if item.get("guidance_id") == guidance_id), None)


def _require_guidance_expected_revision(record: dict[str, Any], expected_revision: int | None) -> dict[str, Any] | None:
    current_revision = _guidance_revision(record)
    if expected_revision is None:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "expected-revision-required",
            "guidance_id": record.get("guidance_id"),
            "current_revision": current_revision,
        }
    if expected_revision != current_revision:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "stale-guidance-revision",
            "guidance_id": record.get("guidance_id"),
            "expected_revision": expected_revision,
            "current_revision": current_revision,
        }
    return None


def _require_related_guidance_revision(
    *,
    records: list[dict[str, Any]],
    guidance_id: str,
    expected_record_revisions: dict[str, int] | None,
    relation: str,
) -> dict[str, Any] | None:
    index = _guidance_index(records, guidance_id)
    if index is None:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": f"missing-{relation}-guidance",
            "guidance_id": guidance_id,
        }
    record = records[index]
    if expected_record_revisions is None or guidance_id not in expected_record_revisions:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "expected-related-revisions-required",
            "guidance_id": guidance_id,
            "relation": relation,
            "current_revision": _guidance_revision(record),
        }
    expected = expected_record_revisions[guidance_id]
    current = _guidance_revision(record)
    if expected != current:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "stale-related-guidance-revision",
            "guidance_id": guidance_id,
            "relation": relation,
            "expected_revision": expected,
            "current_revision": current,
        }
    return None


def _guidance_mutation_receipt(
    *,
    operation: str,
    target_root: Path,
    store_path: Path,
    store_pre_digest: str,
    records: list[dict[str, Any]],
    affected_records: list[dict[str, Any]],
    postconditions: list[str],
    owner_admission: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "operation": operation,
        "store_ref": _repo_relative(store_path, root=target_root),
        "store_pre_digest": store_pre_digest,
        "record_ids": [str(record.get("guidance_id") or "") for record in records],
        "affected_record_ids": [str(record.get("guidance_id") or "") for record in affected_records],
        "postconditions": postconditions,
        "owner_admission": owner_admission,
    }
    return {
        "kind": "agentic-workspace/guidance-mutation-receipt/v1",
        **payload,
        "idempotency_key": "guidance-mutation:"
        + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:20],
        "store_digest": hashlib.sha256(json.dumps(records, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
        "atomic_record_count": len(affected_records),
    }


def _record_guidance_mutation_receipt(
    *,
    operation: str,
    target_root: Path,
    store_path: Path,
    store_pre_digest: str,
    records: list[dict[str, Any]],
    affected_records: list[dict[str, Any]],
    postconditions: list[str],
    owner_admission: dict[str, Any],
) -> dict[str, Any]:
    mutation, receipt_result, writes = _guidance_mutation_receipt_write_plan(
        operation=operation,
        target_root=target_root,
        store_path=store_path,
        store_pre_digest=store_pre_digest,
        records=records,
        affected_records=affected_records,
        postconditions=postconditions,
        owner_admission=owner_admission,
    )
    _ = mutation
    _write_guidance_json_transaction(writes, journal_root=target_root)
    return receipt_result


def _guidance_mutation_receipt_write_plan(
    *,
    operation: str,
    target_root: Path,
    store_path: Path,
    store_pre_digest: str,
    records: list[dict[str, Any]],
    affected_records: list[dict[str, Any]],
    postconditions: list[str],
    owner_admission: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[tuple[Path, dict[str, Any], str | None]]]:
    mutation = _guidance_mutation_receipt(
        operation=operation,
        target_root=target_root,
        store_path=store_path,
        store_pre_digest=store_pre_digest,
        records=records,
        affected_records=affected_records,
        postconditions=postconditions,
        owner_admission=owner_admission,
    )
    stored, writes = _guidance_receipt_write_plan(
        target_root=target_root,
        operation_id=f"agent-guidance.{operation}",
        receipt={
            "receipt_type": "guidance-mutation",
            "operation": operation,
            "mutation_receipt": mutation,
            "store_ref": mutation["store_ref"],
            "affected_record_ids": mutation["affected_record_ids"],
            "idempotency_key": mutation["idempotency_key"],
        },
    )
    result = {
        **mutation,
        "receipt_ref": stored["receipt_ref"],
        "receipt_store": stored["store"],
        "receipt_custody": stored["receipt"]["custody"],
        "receipt_status": stored["status"],
    }
    return mutation, result, writes


def _guidance_owner_admission(*, destination: dict[str, Any], store_digest: str, store_path: Path, target_root: Path) -> dict[str, Any]:
    owner = str(destination.get("owner") or "")
    operation_id = str(destination.get("owner_operation_id") or "")
    admitted = bool(operation_id) and owner in {"user-local-target-guidance", "repo-local-target-guidance-overlay"}
    return {
        "kind": "agentic-workspace/guidance-owner-admission/v1",
        "status": "admitted" if admitted else "owner-operation-required",
        "owner": owner,
        "operation_id": operation_id or str(destination.get("owner_operation_required") or ""),
        "store_ref": _repo_relative(store_path, root=target_root),
        "expected_store_digest": store_digest,
        "checked_in_repo_effect": False,
        "rule": "Guidance lifecycle mutations require a named destination owner operation; Memory, config, and issue routes fail closed until their owners admit the transition.",
    }


def _guidance_owner_registry_plan(
    *, target_root: Path, store_path: Path, records: list[dict[str, Any]]
) -> tuple[Path, dict[str, Any], str | None, dict[str, Any], bool]:
    registry_path, owner_registry, owner_registry_digest = _guidance_store_owner_registry(target_root)
    location = _guidance_store_location_identity(path=store_path, target_root=target_root)
    expected_revision = "sha256:" + _json_digest({"records": records})
    current_entry = next(
        (item for item in owner_registry["stores"] if isinstance(item, dict) and str(item.get("store_ref") or "") == location["store_ref"]),
        None,
    )
    current = bool(
        isinstance(current_entry, dict)
        and current_entry.get("status") == "current"
        and current_entry.get("store_revision") == expected_revision
        and current_entry.get("owner") == location["owner"]
        and current_entry.get("scope") == location["scope"]
        and bool(current_entry.get("absolute")) is bool(location["absolute"])
    )
    registered_stores = [
        item for item in owner_registry["stores"] if isinstance(item, dict) and str(item.get("store_ref") or "") != location["store_ref"]
    ]
    next_registry = {
        "kind": "agentic-workspace/guidance-store-owner-registry/v1",
        "stores": [
            *registered_stores,
            {
                "store_ref": location["store_ref"],
                "absolute": location["absolute"],
                "scope": location["scope"],
                "owner": location["owner"],
                "status": "current",
                "store_revision": expected_revision,
            },
        ],
    }
    return registry_path, next_registry, owner_registry_digest, location, current


def _guidance_promotion_receipt_current(*, target_root: Path, store_path: Path, records: list[dict[str, Any]], guidance_id: str) -> bool:
    _receipt_path, index = _guidance_receipt_index(target_root)
    expected_store_ref = _repo_relative(store_path, root=target_root)
    expected_store_digest = hashlib.sha256(json.dumps(records, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    for receipt in index["receipts"]:
        if not isinstance(receipt, dict) or receipt.get("receipt_type") != "guidance-mutation":
            continue
        mutation = receipt.get("mutation_receipt") if isinstance(receipt.get("mutation_receipt"), dict) else {}
        custody = receipt.get("custody") if isinstance(receipt.get("custody"), dict) else {}
        if (
            receipt.get("status") == "current"
            and custody.get("producer") == "agentic-workspace.guidance-receipt-index"
            and mutation.get("store_ref") == expected_store_ref
            and mutation.get("store_digest") == expected_store_digest
            and guidance_id in mutation.get("affected_record_ids", [])
            and "store-owner-registry-current" in mutation.get("postconditions", [])
        ):
            return True
    return False


def apply_guidance_promotion(
    *,
    target_root: Path,
    guidance_id: str,
    task_class: str | None = None,
    scope_class: str | None = None,
    explicit_remember: bool = False,
) -> dict[str, Any]:
    """Persist one promoted candidate with its evidence and future lifecycle custody."""
    request_identity = _json_digest(
        {
            "operation": "promote",
            "guidance_id": guidance_id,
            "task_class": task_class or "",
            "scope_class": scope_class or "",
            "explicit_remember": explicit_remember,
        }
    )
    recovery = _recover_guidance_transactions_for_target(target_root=target_root)
    if recovery.get("status") == "recovery-conflict":
        raise WorkspaceUsageError(str(recovery.get("reason") or "guidance transaction recovery requires repair."))
    raw_recovered_payload = recovery.get("result")
    recovered_payload: dict[str, Any] = raw_recovered_payload if isinstance(raw_recovered_payload, dict) else {}
    raw_recovered_result = recovered_payload.get("result")
    recovered_result: dict[str, Any] = raw_recovered_result if isinstance(raw_recovered_result, dict) else {}
    recovered_origin = str(recovery.get("origin_root") or "")
    if recovered_payload.get("request_identity") == request_identity and recovered_result:
        if Path(recovered_origin).resolve() == target_root.resolve():
            return {
                **recovered_result,
                "recovery": {
                    "status": "completed-prepared-transaction",
                    "transaction_id": recovery.get("transaction_id", ""),
                    "repaired_paths": recovery.get("repaired_paths", []),
                },
            }
        recovered_store = _find_guidance_lifecycle_store(target_root, guidance_id)
        if recovered_store is None:
            raise WorkspaceUsageError("cross-repository guidance recovery completed without a current lifecycle record.")
        recovered_path, recovered_store_payload, recovered_index = recovered_store
        recovered_records = [item for item in recovered_store_payload["records"] if isinstance(item, dict)]
        recovered_record = recovered_records[recovered_index]
        raw_destination = recovered_record.get("destination")
        recovered_destination: dict[str, Any] = raw_destination if isinstance(raw_destination, dict) else {}
        owner_admission = _guidance_owner_admission(
            destination=recovered_destination,
            store_digest=_json_digest(recovered_store_payload),
            store_path=recovered_path,
            target_root=target_root,
        )
        if owner_admission["status"] != "admitted":
            raise WorkspaceUsageError("cross-repository guidance recovery requires the current store owner operation.")
        registry_path, next_owner_registry, owner_registry_digest, location, registry_current = _guidance_owner_registry_plan(
            target_root=target_root,
            store_path=recovered_path,
            records=recovered_records,
        )
        affected_ids = {str(item.get("guidance_id") or "") for item in recovered_result.get("records", []) if isinstance(item, dict)} or {
            guidance_id
        }
        affected_records = [item for item in recovered_records if str(item.get("guidance_id") or "") in affected_ids]
        _mutation, receipt_result, receipt_writes = _guidance_mutation_receipt_write_plan(
            operation="promote-recovery",
            target_root=target_root,
            store_path=recovered_path,
            store_pre_digest=_json_digest(recovered_store_payload),
            records=recovered_records,
            affected_records=affected_records,
            postconditions=[
                "interrupted-cross-repository-promotion-recovered",
                "store-owner-registry-current",
                "shared-store-unlocked",
            ],
            owner_admission=owner_admission,
        )
        adopted_result = {
            **recovered_result,
            "record": recovered_record,
            "store_location": location,
            "mutation_receipt": receipt_result,
            "custody_verification": {
                "status": "recovered",
                "origin_root": recovered_origin,
                "orphaned_origin_paths": recovery.get("orphaned_origin_paths", []),
                "repair_route": recovery.get("repair_route", {"status": "not-needed"}),
            },
            "recovery": {
                "status": "completed-cross-repository-prepared-transaction",
                "transaction_id": recovery.get("transaction_id", ""),
                "repaired_paths": recovery.get("repaired_paths", []),
            },
        }
        registry_writes = [] if registry_current else [(registry_path, next_owner_registry, owner_registry_digest)]
        _write_guidance_json_transaction(
            [*registry_writes, *receipt_writes],
            journal_root=target_root,
            recovery_result={"request_identity": request_identity, "result": adopted_result},
        )
        return adopted_result
    decision = guidance_promotion_from_store(
        target_root=target_root,
        task_class=task_class,
        scope_class=scope_class,
        explicit_remember=explicit_remember,
    )
    candidate = next(
        (item for item in decision.get("guidance", []) if isinstance(item, dict) and item.get("guidance_id") == guidance_id), None
    )
    if decision.get("status") != "ready" or not isinstance(candidate, dict) or candidate.get("status") != "active":
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "promotion-not-authorized",
            "guidance_id": guidance_id,
            "decision": decision,
        }
    destination = candidate.get("destination") if isinstance(candidate.get("destination"), dict) else {}
    store_ref = destination.get("store")
    if not store_ref:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "promotion-destination-required",
            "guidance_id": guidance_id,
            "decision": decision,
        }
    path, store = _guidance_lifecycle_store(target_root, str(store_ref))
    store_digest = _json_digest(store)
    semantic_identity = _json_digest(
        {
            "instruction": str(candidate.get("instruction") or ""),
            "applicability": candidate.get("applicability") if isinstance(candidate.get("applicability"), dict) else {},
        }
    )
    canonical_matches = _matching_guidance_lifecycle_stores(
        target_root=target_root,
        guidance_id=guidance_id,
        semantic_identity=semantic_identity,
    )
    active_matches = [
        match for match in canonical_matches if str(match[1]["records"][match[2]].get("status") or "") not in _GUIDANCE_TERMINAL_STATUSES
    ]
    same_store_match = next((match for match in active_matches if match[0].resolve() == path.resolve()), None)
    conflicting_matches = [match for match in active_matches if match[0].resolve() != path.resolve()]
    canonical_store_scan = {
        "kind": "agentic-workspace/guidance-canonical-store-scan/v1",
        "status": "conflict" if conflicting_matches else "unique",
        "guidance_id": guidance_id,
        "semantic_identity": semantic_identity,
        "selected_store": _guidance_store_location_identity(path=path, target_root=target_root),
        "active_match_count": len(active_matches),
        "active_stores": [
            _guidance_store_location_identity(path=match_path, target_root=target_root) for match_path, _, _ in active_matches
        ],
        "rule": "Promotion may create authority only when no other authoritative target-guidance store has the same guidance or semantic identity.",
    }
    if conflicting_matches:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "promotion-owner-conflict",
            "guidance_id": guidance_id,
            "canonical_store_scan": canonical_store_scan,
            "migration": {
                "kind": "agentic-workspace/guidance-owner-migration-required/v1",
                "status": "required",
                "expected_source_revisions": [
                    {
                        "store": _guidance_store_location_identity(path=match_path, target_root=target_root),
                        "store_digest": _json_digest(match_store),
                        "record_revision": _guidance_revision(match_store["records"][index]),
                    }
                    for match_path, match_store, index in conflicting_matches
                ],
                "destination_store_digest": store_digest,
                "rule": "Move authority through an explicit revision-guarded migration; promotion never copies an active record across owners.",
            },
        }
    if same_store_match is not None:
        existing = same_store_match[1]["records"][same_store_match[2]]
        existing_records = [item for item in same_store_match[1]["records"] if isinstance(item, dict)]
        registry_path, next_owner_registry, owner_registry_digest, location, registry_current = _guidance_owner_registry_plan(
            target_root=target_root,
            store_path=path,
            records=existing_records,
        )
        receipt_current = _guidance_promotion_receipt_current(
            target_root=target_root,
            store_path=path,
            records=existing_records,
            guidance_id=guidance_id,
        )
        result = {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "already-promoted",
            "record": existing,
            "store": _repo_relative(path, root=target_root),
            "store_location": location,
            "canonical_store_scan": canonical_store_scan,
        }
        if registry_current and receipt_current:
            result["custody_verification"] = {
                "status": "current",
                "postconditions": ["lifecycle-record-current", "store-owner-registry-current", "promotion-receipt-current"],
            }
            return result
        raw_destination = existing.get("destination")
        existing_destination = raw_destination if isinstance(raw_destination, dict) else {}
        owner_admission = _guidance_owner_admission(
            destination=existing_destination,
            store_digest=_json_digest(same_store_match[1]),
            store_path=path,
            target_root=target_root,
        )
        if owner_admission["status"] != "admitted":
            return {
                **result,
                "status": "promotion-custody-repair-required",
                "owner_admission": owner_admission,
                "missing_postconditions": [
                    condition
                    for condition, current in (
                        ("store-owner-registry-current", registry_current),
                        ("promotion-receipt-current", receipt_current),
                    )
                    if not current
                ],
            }
        _mutation, receipt_result, receipt_writes = _guidance_mutation_receipt_write_plan(
            operation="promote-recovery",
            target_root=target_root,
            store_path=path,
            store_pre_digest=_json_digest(same_store_match[1]),
            records=existing_records,
            affected_records=[existing],
            postconditions=[
                "canonical-store-scan-unique",
                "store-owner-registry-current",
                "single-canonical-destination",
                "active-guidance-created",
                "promotion-authority-retained",
                "interrupted-custody-recovered",
            ],
            owner_admission=owner_admission,
        )
        repaired_result = {
            **result,
            "custody_verification": {
                "status": "recovered",
                "repaired_postconditions": [
                    condition
                    for condition, current in (
                        ("store-owner-registry-current", registry_current),
                        ("promotion-receipt-current", receipt_current),
                    )
                    if not current
                ],
            },
            "mutation_receipt": receipt_result,
        }
        registry_writes = [] if registry_current else [(registry_path, next_owner_registry, owner_registry_digest)]
        _write_guidance_json_transaction(
            [*registry_writes, *receipt_writes],
            journal_root=target_root,
            recovery_result={"request_identity": request_identity, "result": repaired_result},
        )
        return repaired_result
    owner_admission = _guidance_owner_admission(
        destination=destination,
        store_digest=store_digest,
        store_path=path,
        target_root=target_root,
    )
    if owner_admission["status"] != "admitted":
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "promotion-owner-operation-required",
            "guidance_id": guidance_id,
            "owner_admission": owner_admission,
            "decision": decision,
        }
    owner_admission["canonical_store_scan"] = canonical_store_scan
    records = [item for item in store["records"] if isinstance(item, dict)]
    record = {
        "kind": "agentic-workspace/guidance-lifecycle-record/v1",
        "guidance_id": guidance_id,
        "status": "active",
        "instruction": candidate["instruction"],
        "applicability": candidate["applicability"],
        "destination": destination,
        "provenance": {
            "source_event_refs": candidate["source_event_refs"],
            "evidence_refs": candidate["evidence_refs"],
            "promotion_reason": candidate["promotion_reason"],
            "promotion_authority": candidate.get("promotion_authority", {}),
            "authority_source": decision.get("authority_source", {}),
        },
        "transitions": [{"operation": "promote", "at": _guidance_now(), "reason": candidate["promotion_reason"]}],
        "revision": 1,
        "schema_revision": hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()[:20],
    }
    next_records = [*records, record]
    registry_path, next_owner_registry, owner_registry_digest, location, _registry_current = _guidance_owner_registry_plan(
        target_root=target_root,
        store_path=path,
        records=next_records,
    )
    mutation, receipt_result, receipt_writes = _guidance_mutation_receipt_write_plan(
        operation="promote",
        target_root=target_root,
        store_path=path,
        store_pre_digest=store_digest,
        records=next_records,
        affected_records=[record],
        postconditions=[
            "canonical-store-scan-unique",
            "store-owner-registry-current",
            "single-canonical-destination",
            "active-guidance-created",
            "promotion-authority-retained",
        ],
        owner_admission=owner_admission,
    )
    _ = mutation
    promotion_result = {
        "kind": "agentic-workspace/guidance-lifecycle-result/v1",
        "status": "promoted",
        "record": record,
        "store": _repo_relative(path, root=target_root),
        "store_location": location,
        "canonical_store_scan": canonical_store_scan,
        "mutation_receipt": receipt_result,
    }
    _write_guidance_json_transaction(
        [
            (
                path,
                {"kind": "agentic-workspace/guidance-lifecycle-store/v1", "records": next_records},
                store_digest if path.exists() else None,
            ),
            (registry_path, next_owner_registry, owner_registry_digest),
            *receipt_writes,
        ],
        journal_root=target_root,
        recovery_result={"request_identity": request_identity, "result": promotion_result},
    )
    return promotion_result


def _guidance_int_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise WorkspaceUsageError("guidance lifecycle expected revisions must be integers.") from exc


def _guidance_json_mapping(value: Any) -> dict[str, int] | None:
    if value in (None, ""):
        return None
    loaded = value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise WorkspaceUsageError("expected_record_revisions_json must be valid JSON.") from exc
    if not isinstance(loaded, dict):
        raise WorkspaceUsageError("expected_record_revisions_json must be a JSON object.")
    return {str(key): int(raw) for key, raw in loaded.items()}


def _guidance_string_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        loaded = None
    if isinstance(loaded, list):
        return [str(item).strip() for item in loaded if str(item).strip()]
    return [item.strip() for item in text.split(",") if item.strip()]


def apply_guidance_lifecycle_operation(
    *,
    target_root: Path,
    operation_id: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    """Apply a generated agent-guidance lifecycle operation through the public command boundary."""

    operation = operation_id.removeprefix("agent-guidance.")
    guidance_id = str(values.get("guidance_id") or "").strip()
    if not guidance_id:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "operation_id": operation_id,
            "status": "missing-guidance-id",
            "mutation_applied": False,
        }
    if operation == "promote":
        result = apply_guidance_promotion(
            target_root=target_root,
            guidance_id=guidance_id,
            task_class=str(values.get("task_class") or "") or None,
            scope_class=str(values.get("scope_class") or "") or None,
            explicit_remember=_truthy(values.get("explicit_remember")),
        )
    else:
        result = transition_guidance(
            target_root=target_root,
            guidance_id=guidance_id,
            operation=operation,
            reason=str(values.get("reason") or "").strip(),
            expected_revision=_guidance_int_value(values.get("expected_revision")),
            expected_record_revisions=_guidance_json_mapping(
                values.get("expected_record_revisions_json") or values.get("expected_record_revisions")
            ),
            replacement_guidance_id=str(values.get("replacement_guidance_id") or "").strip(),
            instruction=str(values.get("instruction") or "") if values.get("instruction") is not None else None,
            merge_guidance_ids=_guidance_string_list(values.get("merge_guidance_ids")),
            split_instructions=_guidance_string_list(values.get("split_instructions")),
        )
    mutation_applied = result.get("status") in {"promoted", "transitioned"}
    return json.loads(
        json.dumps(
            {
                "operation_id": operation_id,
                "mutation_applied": mutation_applied,
                **result,
            },
            sort_keys=True,
            default=str,
        )
    )


def _guidance_context_match(*, applicability: dict[str, Any], context: dict[str, str]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    unknown: list[str] = []
    for field in (
        "target_identity_ref",
        "target_revision",
        "task_class",
        "scope_class",
        "repository",
        "role",
        "phase",
        "subsystem",
        "surface",
    ):
        expected = applicability.get(field)
        expected_values = _guidance_string_list(expected)
        if not expected_values:
            continue
        observed = str(context.get(field) or "").strip()
        if not observed:
            unknown.append(field)
        elif observed not in expected_values:
            reasons.append(f"{field}-mismatch")
    applies_when = _guidance_string_list(applicability.get("applies_when"))
    for condition in applies_when:
        if ":" not in condition:
            continue
        field, expected = (part.strip() for part in condition.split(":", 1))
        if field not in context or not str(context.get(field) or "").strip():
            unknown.append(field)
        elif str(context.get(field) or "").strip() != expected:
            reasons.append(f"{field}-mismatch")
    if reasons:
        return "not-applicable", sorted(set(reasons))
    if unknown:
        return "unknown", sorted(set(unknown))
    return "applicable", []


def route_agent_guidance(
    *,
    target_root: Path,
    target_identity_ref: str,
    target_revision: str = "",
    task_class: str = "",
    scope_class: str = "",
    repository: str = "",
    role: str = "",
    phase: str = "",
    subsystem: str = "",
    surface: str = "",
) -> dict[str, Any]:
    """Select the smallest current guidance bundle for one structured decision context."""
    context = {
        "target_identity_ref": target_identity_ref.strip(),
        "target_revision": target_revision.strip(),
        "task_class": task_class.strip(),
        "scope_class": scope_class.strip(),
        "repository": repository.strip(),
        "role": role.strip(),
        "phase": phase.strip(),
        "subsystem": subsystem.strip(),
        "surface": surface.strip(),
    }
    stores = _candidate_guidance_store_refs(target_root=target_root, config=load_workspace_config(target_root=target_root))
    matched: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for store_path in stores:
        _path, store = _guidance_lifecycle_store(target_root, store_path)
        for record in store.get("records", []):
            if not isinstance(record, dict):
                continue
            status = str(record.get("status") or "")
            if status not in {"active", "revalidated"}:
                excluded.append({"guidance_id": record.get("guidance_id"), "reason": f"lifecycle-{status or 'unknown'}"})
                continue
            applicability = record.get("applicability") if isinstance(record.get("applicability"), dict) else {}
            relevance, reasons = _guidance_context_match(applicability=applicability, context=context)
            packet = {
                "guidance_id": record.get("guidance_id"),
                "instruction": record.get("instruction"),
                "authority": "target-scoped-user-local-guidance",
                "relevance": relevance,
                "relevance_basis": {"applicability": applicability, "context": context, "reasons": reasons},
                "trust": {"status": "current", "record_revision": record.get("revision"), "schema_revision": record.get("schema_revision")},
                "affected_boundary": {
                    "task_class": applicability.get("task_class", ""),
                    "scope_class": applicability.get("scope_class", ""),
                    "phase": applicability.get("phase", ""),
                    "subsystem": applicability.get("subsystem", ""),
                    "surface": applicability.get("surface", ""),
                },
                "observation_required": True,
                "precedence": "current user instruction and checked-in repo authority override target guidance",
            }
            if relevance == "applicable":
                matched.append(packet)
            elif relevance == "unknown":
                uncertain.append({"guidance_id": record.get("guidance_id"), "missing_context": reasons})
            else:
                excluded.append({"guidance_id": record.get("guidance_id"), "reason": ",".join(reasons)})
    matched.sort(key=lambda item: str(item.get("guidance_id") or ""))
    return {
        "kind": "agentic-workspace/agent-guidance-route/v1",
        "status": "routed" if matched else "probe-required" if uncertain else "no-applicable-guidance",
        "context": context,
        "guidance": matched,
        "uncertain": uncertain,
        "excluded": excluded,
        "context_overhead": {"routed_count": len(matched), "ordinary_no_match_artifact_count": 0},
        "probe": {"required_fields": sorted({field for item in uncertain for field in item["missing_context"]})} if uncertain else {},
        "rule": "Route only current target guidance with structured applicability; unknown relevance requests bounded context and never broad-dumps guidance.",
    }


_GUIDANCE_COMPLIANCE_OUTCOMES = {
    "surfaced-followed",
    "surfaced-violated",
    "inconclusive",
    "routing-missed",
    "not-applicable",
    "contradicted",
    "correct-escalation",
}
_GUIDANCE_OBSERVATION_AUTHORITY = {"agent-self-report": 0, "aw-owned-proof": 2, "review": 3, "human": 4}


_GUIDANCE_CONSEQUENCE_CONTEXT_FIELDS = (
    "target_identity_ref",
    "target_revision",
    "task_class",
    "scope_class",
    "phase",
    "subsystem",
    "surface",
)


def guidance_consequence_decision(
    *,
    observations: list[dict[str, Any]],
    guidance_id: str,
    target_identity_ref: str,
    target_revision: str,
    task_class: str,
    scope_class: str,
    phase: str,
    subsystem: str,
    surface: str,
) -> dict[str, Any]:
    context = {
        "target_identity_ref": target_identity_ref,
        "target_revision": target_revision,
        "task_class": task_class,
        "scope_class": scope_class,
        "phase": phase,
        "subsystem": subsystem,
        "surface": surface,
    }
    same_guidance = [item for item in observations if str(item.get("guidance_id") or "") == guidance_id]
    relevant = [
        item
        for item in same_guidance
        if all(str(item.get(field) or "").strip() == str(context[field] or "").strip() for field in _GUIDANCE_CONSEQUENCE_CONTEXT_FIELDS)
    ]
    attributable = [
        item
        for item in relevant
        if item.get("outcome") == "surfaced-violated"
        and item.get("cause_class") not in {"routing-failure", "guidance-defect", "higher-authority-contradiction", "infrastructure-defect"}
        and int(item.get("authority_rank") or 0) >= _GUIDANCE_OBSERVATION_AUTHORITY["aw-owned-proof"]
    ]
    recovery = [
        item
        for item in relevant
        if item.get("outcome") in {"surfaced-followed", "correct-escalation"}
        and int(item.get("authority_rank") or 0) >= _GUIDANCE_OBSERVATION_AUTHORITY["aw-owned-proof"]
    ]
    infrastructure = [item for item in relevant if item.get("cause_class") == "infrastructure-defect"]
    net = max(0, len(attributable) - (1 if len(recovery) >= 2 else 0))
    human_prohibition = any(item.get("human_authorized_prohibition") is True for item in relevant)
    level = (
        "class-prohibition"
        if net >= 3 and human_prohibition
        else "suitability-impact"
        if net >= 3
        else "review-required"
        if net >= 2
        else "advisory"
        if net == 1
        else "none"
    )
    return {
        "kind": "agentic-workspace/guidance-consequence-decision/v1",
        "status": level,
        "guidance_id": guidance_id,
        "context": context,
        "same_context_observation_count": len(relevant),
        "excluded_cross_context_observation_count": len(same_guidance) - len(relevant),
        "decisive_evidence_ids": [item.get("observation_id") for item in attributable],
        "recovery_evidence_ids": [item.get("observation_id") for item in recovery],
        "excluded_cause_counts": {
            cause: sum(item.get("cause_class") == cause for item in relevant)
            for cause in ("routing-failure", "guidance-defect", "higher-authority-contradiction", "infrastructure-defect")
        },
        "next_action": "route-product-improvement"
        if infrastructure
        else "apply-contextual-assignment-consequence"
        if level != "none"
        else "none",
        "human_authority_required": level == "class-prohibition",
        "rule": "Only admitted post-surfacing evidence can affect contextual suitability; infrastructure and guidance failures route to product repair, and prohibitions require human authority.",
    }


def observe_agent_guidance(
    *,
    target_root: Path,
    guidance_id: str,
    outcome: str,
    evidence_authority: str,
    evidence_ref: str,
    target_identity_ref: str,
    target_revision: str,
    task_class: str,
    scope_class: str,
    phase: str,
    subsystem: str,
    surface: str,
    cause_class: str = "target-behavior",
    human_authorized_prohibition: bool = False,
) -> dict[str, Any]:
    if outcome not in _GUIDANCE_COMPLIANCE_OUTCOMES:
        raise WorkspaceUsageError(f"unsupported guidance compliance outcome: {outcome}")
    if evidence_authority not in _GUIDANCE_OBSERVATION_AUTHORITY:
        raise WorkspaceUsageError(f"unsupported guidance evidence authority: {evidence_authority}")
    identity = {
        "guidance_id": guidance_id,
        "outcome": outcome,
        "evidence_ref": evidence_ref,
        "target_identity_ref": target_identity_ref,
        "target_revision": target_revision,
        "task_class": task_class,
        "scope_class": scope_class,
        "phase": phase,
        "subsystem": subsystem,
        "surface": surface,
        "cause_class": cause_class,
    }
    observation_id = "guidance-observation:" + _json_digest(identity)[:24]
    path = target_root / GUIDANCE_OBSERVATION_STORE_PATH
    if path.exists():
        try:
            store = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceUsageError("guidance observation store is unreadable") from exc
    else:
        store = {"kind": "agentic-workspace/guidance-observation-store/v1", "observations": []}
    observations = [item for item in store.get("observations", []) if isinstance(item, dict)]
    existing = next((item for item in observations if item.get("observation_id") == observation_id), None)
    if existing is None:
        observation = {
            "kind": "agentic-workspace/guidance-compliance-observation/v1",
            "observation_id": observation_id,
            **identity,
            "authority_rank": _GUIDANCE_OBSERVATION_AUTHORITY[evidence_authority],
            "evidence_authority": evidence_authority,
            "human_authorized_prohibition": human_authorized_prohibition and evidence_authority == "human",
            "observed_at": _guidance_now(),
        }
        observations = [*observations, observation][-GUIDANCE_OBSERVATION_RETENTION_CAP:]
        next_store = {"kind": "agentic-workspace/guidance-observation-store/v1", "observations": observations}
        _write_guidance_json_transaction([(path, next_store, _json_digest(store) if path.exists() else None)], journal_root=target_root)
        status = "recorded"
    else:
        observation = existing
        status = "duplicate-replay"
    return {
        "kind": "agentic-workspace/guidance-compliance-result/v1",
        "status": status,
        "observation": observation,
        "consequence": guidance_consequence_decision(
            observations=observations,
            guidance_id=guidance_id,
            target_identity_ref=target_identity_ref,
            target_revision=target_revision,
            task_class=task_class,
            scope_class=scope_class,
            phase=phase,
            subsystem=subsystem,
            surface=surface,
        ),
        "storage": {
            "path": GUIDANCE_OBSERVATION_STORE_PATH.as_posix(),
            "checked_in": False,
            "retention_cap": GUIDANCE_OBSERVATION_RETENTION_CAP,
        },
    }


def correction_capture_decision(
    *, correction_signal: str, feedback_source_available: bool, shared_repo_lesson: bool = False
) -> dict[str, Any]:
    signal = correction_signal.strip().lower()
    recognized = signal in {"explicit-user-correction", "pr-review", "orchestrator-review", "external-adapter-correction"}
    if not recognized:
        status = "dismissed" if signal in {"new-requirement", "apology", "recap", "ordinary-feedback"} else "ambiguous"
    elif not feedback_source_available:
        status = "unavailable"
    else:
        status = "routed" if shared_repo_lesson else "event-submitted"
    return {
        "kind": "agentic-workspace/correction-capture-decision/v1",
        "status": status,
        "recognized_correction": recognized,
        "owner": "checked-in-memory" if shared_repo_lesson else "correction-event.submit" if recognized else "none",
        "required_operation": "memory guidance promotion review" if shared_repo_lesson else "correction-event submit" if recognized else "",
        "limitation": "feedback source is not exposed by the current host" if status == "unavailable" else "",
        "rule": "Recognized corrections require capture or an honest unavailable/routed result; apologies, recaps, and changed requirements do not create correction events.",
    }


def transition_guidance(
    *,
    target_root: Path,
    guidance_id: str,
    operation: str,
    reason: str,
    expected_revision: int | None = None,
    expected_record_revisions: dict[str, int] | None = None,
    replacement_guidance_id: str = "",
    instruction: str | None = None,
    merge_guidance_ids: list[str] | None = None,
    split_instructions: list[str] | None = None,
) -> dict[str, Any]:
    """Apply a reversible lifecycle transition without discarding promotion evidence."""
    if operation not in _GUIDANCE_LIFECYCLE_OPERATIONS:
        raise WorkspaceUsageError(f"unsupported guidance lifecycle operation: {operation}")
    if not reason.strip():
        raise WorkspaceUsageError("guidance lifecycle transitions require a reason.")
    request_identity = _json_digest(
        {
            "operation": operation,
            "guidance_id": guidance_id,
            "reason": reason,
            "expected_revision": expected_revision,
            "expected_record_revisions": expected_record_revisions or {},
            "replacement_guidance_id": replacement_guidance_id,
            "instruction": instruction,
            "merge_guidance_ids": merge_guidance_ids or [],
            "split_instructions": split_instructions or [],
        }
    )
    recovery = _recover_guidance_transactions_for_target(target_root=target_root)
    if recovery.get("status") == "recovery-conflict":
        raise WorkspaceUsageError(str(recovery.get("reason") or "guidance transaction recovery requires repair."))
    raw_recovered_payload = recovery.get("result")
    recovered_payload: dict[str, Any] = raw_recovered_payload if isinstance(raw_recovered_payload, dict) else {}
    raw_recovered_result = recovered_payload.get("result")
    recovered_result: dict[str, Any] = raw_recovered_result if isinstance(raw_recovered_result, dict) else {}
    recovered_origin = str(recovery.get("origin_root") or "")
    if recovered_payload.get("request_identity") == request_identity and recovered_result:
        if Path(recovered_origin).resolve() == target_root.resolve():
            return {
                **recovered_result,
                "recovery": {
                    "status": "completed-prepared-transaction",
                    "transaction_id": recovery.get("transaction_id", ""),
                    "repaired_paths": recovery.get("repaired_paths", []),
                },
            }
        recovered_store = _find_guidance_lifecycle_store(target_root, guidance_id)
        if recovered_store is None:
            raise WorkspaceUsageError("cross-repository guidance transition recovery found no current lifecycle record.")
        recovered_path, recovered_store_payload, recovered_index = recovered_store
        recovered_records = [item for item in recovered_store_payload["records"] if isinstance(item, dict)]
        recovered_record = recovered_records[recovered_index]
        raw_destination = recovered_record.get("destination")
        recovered_destination: dict[str, Any] = raw_destination if isinstance(raw_destination, dict) else {}
        owner_admission = _guidance_owner_admission(
            destination=recovered_destination,
            store_digest=_json_digest(recovered_store_payload),
            store_path=recovered_path,
            target_root=target_root,
        )
        if owner_admission["status"] != "admitted":
            raise WorkspaceUsageError("cross-repository guidance transition recovery requires the current store owner operation.")
        registry_path, next_owner_registry, owner_registry_digest, location, registry_current = _guidance_owner_registry_plan(
            target_root=target_root,
            store_path=recovered_path,
            records=recovered_records,
        )
        affected_ids = {str(item.get("guidance_id") or "") for item in recovered_result.get("records", []) if isinstance(item, dict)} or {
            guidance_id
        }
        affected_records = [item for item in recovered_records if str(item.get("guidance_id") or "") in affected_ids]
        _mutation, receipt_result, receipt_writes = _guidance_mutation_receipt_write_plan(
            operation=f"{operation}-recovery",
            target_root=target_root,
            store_path=recovered_path,
            store_pre_digest=_json_digest(recovered_store_payload),
            records=recovered_records,
            affected_records=affected_records,
            postconditions=[
                "interrupted-cross-repository-transition-recovered",
                "store-owner-registry-current",
                "shared-store-unlocked",
            ],
            owner_admission=owner_admission,
        )
        adopted_result = {
            **recovered_result,
            "record": recovered_record,
            "store_location": location,
            "mutation_receipt": receipt_result,
            "custody_verification": {
                "status": "recovered",
                "origin_root": recovered_origin,
                "orphaned_origin_paths": recovery.get("orphaned_origin_paths", []),
                "repair_route": recovery.get("repair_route", {"status": "not-needed"}),
            },
            "recovery": {
                "status": "completed-cross-repository-prepared-transaction",
                "transaction_id": recovery.get("transaction_id", ""),
                "repaired_paths": recovery.get("repaired_paths", []),
            },
        }
        registry_writes = [] if registry_current else [(registry_path, next_owner_registry, owner_registry_digest)]
        _write_guidance_json_transaction(
            [*registry_writes, *receipt_writes],
            journal_root=target_root,
            recovery_result={"request_identity": request_identity, "result": adopted_result},
        )
        return adopted_result
    found = _find_guidance_lifecycle_store(target_root, guidance_id)
    if found is None:
        return {"kind": "agentic-workspace/guidance-lifecycle-result/v1", "status": "missing-guidance", "guidance_id": guidance_id}
    path, store, index = found
    store_digest = _json_digest(store)
    records = [item for item in store["records"] if isinstance(item, dict)]
    record = dict(records[index])
    stale = _require_guidance_expected_revision(record, expected_revision)
    if stale is not None:
        return stale
    if record.get("status") in _GUIDANCE_TERMINAL_STATUSES:
        return {"kind": "agentic-workspace/guidance-lifecycle-result/v1", "status": "terminal-guidance", "record": record}
    if operation == "edit":
        if instruction is None or not instruction.strip():
            raise WorkspaceUsageError("edit guidance transitions require a non-empty instruction.")
        new_instruction = instruction.strip()
        if new_instruction == str(record.get("instruction") or ""):
            return {"kind": "agentic-workspace/guidance-lifecycle-result/v1", "status": "semantic-no-op", "record": record}
        record["instruction"] = new_instruction
    elif operation == "merge":
        subjects = [item for item in (merge_guidance_ids or []) if item and item != guidance_id]
        if not subjects:
            raise WorkspaceUsageError("merge guidance transitions require at least one additional guidance id.")
        for subject_id in subjects:
            subject_revision = _require_related_guidance_revision(
                records=records,
                guidance_id=subject_id,
                expected_record_revisions=expected_record_revisions,
                relation="merge-subject",
            )
            if subject_revision is not None:
                return subject_revision
        record["merged_guidance_ids"] = sorted(set([*record.get("merged_guidance_ids", []), *subjects]))
        for subject_id in subjects:
            subject_index = _guidance_index(records, subject_id)
            if subject_index is None:
                continue
            subject = dict(records[subject_index])
            if subject.get("status") in _GUIDANCE_TERMINAL_STATUSES:
                return {
                    "kind": "agentic-workspace/guidance-lifecycle-result/v1",
                    "status": "terminal-merge-subject",
                    "guidance_id": subject_id,
                }
            subject_transition = {
                "operation": "merge-source",
                "at": _guidance_now(),
                "reason": reason,
                "replacement_guidance_id": guidance_id,
            }
            subject.update(
                status="merged",
                merged_into_guidance_id=guidance_id,
                revision=_guidance_revision(subject) + 1,
                transitions=[*subject.get("transitions", []), subject_transition],
            )
            records[subject_index] = subject
    elif operation == "split":
        parts = [item.strip() for item in (split_instructions or []) if item and item.strip()]
        if len(parts) < 2:
            raise WorkspaceUsageError("split guidance transitions require at least two replacement instructions.")
        raw_provenance = record.get("provenance")
        provenance: dict[str, Any] = raw_provenance if isinstance(raw_provenance, dict) else {}
        replacements = [
            {
                "kind": "agentic-workspace/guidance-lifecycle-record/v1",
                "guidance_id": "guidance:" + hashlib.sha256(f"{guidance_id}:split:{position}:{item}".encode()).hexdigest()[:20],
                "status": "active",
                "instruction": item,
                "applicability": record.get("applicability", {}),
                "destination": record.get("destination", {}),
                "provenance": {
                    **provenance,
                    "split_from_guidance_id": guidance_id,
                },
                "transitions": [
                    {"operation": "split-replacement", "at": _guidance_now(), "reason": reason, "source_guidance_id": guidance_id}
                ],
                "revision": 1,
                "schema_revision": hashlib.sha256(
                    json.dumps({"source": guidance_id, "position": position, "instruction": item}, sort_keys=True).encode()
                ).hexdigest()[:20],
            }
            for position, item in enumerate(parts, start=1)
        ]
        record["split_replacements"] = [
            {"guidance_id": replacement["guidance_id"], "instruction": replacement["instruction"]} for replacement in replacements
        ]
        record["split_replacement_ids"] = [replacement["guidance_id"] for replacement in replacements]
        record["status"] = "split-retired"
        records.extend(replacements)
    elif operation == "weaken":
        record["strength"] = "weakened"
        record["claim_effect"] = "advisory-only"
        record["routing_state"] = "backgrounded-until-repromoted"
    elif operation == "revalidate":
        config = load_workspace_config(target_root=target_root)
        raw_applicability = record.get("applicability")
        applicability: dict[str, Any] = raw_applicability if isinstance(raw_applicability, dict) else {}
        target_id = str(applicability.get("target_identity_ref") or "")
        subject = next(
            (
                item
                for item in [_target_identity_subject(profile) for profile in config.local_override.delegation_targets]
                if item.get("stable_target_id") == target_id
            ),
            None,
        )
        if subject is None:
            return {"kind": "agentic-workspace/guidance-lifecycle-result/v1", "status": "revalidation-target-missing", "record": record}
        record["last_revalidated_at"] = _guidance_now()
        record["authority_revalidation"] = {
            "status": "current",
            "target_identity_ref": target_id,
            "target_revision": subject.get("target_revision"),
            "owner": record.get("destination", {}).get("owner") if isinstance(record.get("destination"), dict) else None,
        }
    elif operation == "supersede":
        if not replacement_guidance_id or replacement_guidance_id == guidance_id:
            raise WorkspaceUsageError("supersede guidance transitions require a distinct replacement guidance id.")
        replacement_revision = _require_related_guidance_revision(
            records=records,
            guidance_id=replacement_guidance_id,
            expected_record_revisions=expected_record_revisions,
            relation="replacement",
        )
        if replacement_revision is not None:
            replacement_revision["replacement_guidance_id"] = replacement_guidance_id
            if replacement_revision["status"] == "missing-replacement-guidance":
                replacement_revision["status"] = "missing-replacement-guidance"
            return replacement_revision
    status = {
        "suppress": "suppressed",
        "retire": "retired",
        "delete": "deleted",
        "supersede": "superseded",
        "split": "split-retired",
    }.get(operation, str(record.get("status") or "active") if operation == "merge" else "active")
    transition = {
        "operation": operation,
        "at": _guidance_now(),
        "reason": reason,
        "replacement_guidance_id": replacement_guidance_id or None,
    }
    record.update(status=status, revision=_guidance_revision(record) + 1, transitions=[*record.get("transitions", []), transition])
    records[index] = record
    raw_destination = record.get("destination")
    destination: dict[str, Any] = raw_destination if isinstance(raw_destination, dict) else {}
    owner_admission = _guidance_owner_admission(
        destination=destination,
        store_digest=store_digest,
        store_path=path,
        target_root=target_root,
    )
    if owner_admission["status"] != "admitted":
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "transition-owner-operation-required",
            "guidance_id": guidance_id,
            "owner_admission": owner_admission,
            "record": record,
        }
    affected = [record]
    if operation == "merge":
        affected.extend(item for item in records if item.get("guidance_id") in set(merge_guidance_ids or []))
    if operation == "split":
        affected.extend(item for item in records if item.get("guidance_id") in set(record.get("split_replacement_ids", [])))
    postconditions = [
        "revision-guard-satisfied",
        "lineage-preserved",
        "store-owner-registry-current",
        "no-duplicate-active-authority"
        if operation in {"merge", "split", "supersede", "retire", "delete"}
        else "single-record-postcondition",
    ]
    mutation, receipt_result, receipt_writes = _guidance_mutation_receipt_write_plan(
        operation=operation,
        target_root=target_root,
        store_path=path,
        store_pre_digest=store_digest,
        records=records,
        affected_records=affected,
        postconditions=postconditions,
        owner_admission=owner_admission,
    )
    _ = mutation
    registry_path, next_owner_registry, owner_registry_digest, location, _registry_current = _guidance_owner_registry_plan(
        target_root=target_root,
        store_path=path,
        records=records,
    )
    transition_result = {
        "kind": "agentic-workspace/guidance-lifecycle-result/v1",
        "status": "transitioned",
        "record": record,
        "records": affected,
        "store": _repo_relative(path, root=target_root),
        "store_location": location,
        "mutation_receipt": receipt_result,
    }
    _write_guidance_json_transaction(
        [
            (path, {"kind": "agentic-workspace/guidance-lifecycle-store/v1", "records": records}, store_digest),
            (registry_path, next_owner_registry, owner_registry_digest),
            *receipt_writes,
        ],
        journal_root=target_root,
        recovery_result={"request_identity": request_identity, "result": transition_result},
    )
    return transition_result


def target_identity_posture(*, local_override: MixedAgentLocalOverride, target_root: Path | None) -> dict[str, Any]:
    subjects = [_target_identity_subject(profile) for profile in local_override.delegation_targets]
    current_name = local_override.current_target or ""
    resolution = resolve_target_identity(subjects=subjects, value=current_name)
    current_status = resolution["status"]
    recovery = str(resolution.get("recovery") or "resolve target identity")
    current_subject = resolution.get("subject") if isinstance(resolution.get("subject"), dict) else None
    user_root = local_override.user_guidance_root
    overlay_path = local_override.target_guidance_overlay_path or WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH
    correction_path = local_override.correction_events_path or WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH
    overlay_exists = (target_root / overlay_path).exists() if target_root is not None else False
    correction_exists = (target_root / correction_path).exists() if target_root is not None else False
    enabled = bool(local_override.target_guidance_enabled)
    storage_status = "disabled" if not enabled else "missing-user-root" if not user_root else "available"
    return {
        "kind": "agentic-workspace/target-identity-posture/v1",
        "status": "configured" if subjects else "no-target-profiles",
        "current_target": current_name or None,
        "current_target_identity": {
            "status": current_status,
            "subject": current_subject,
            "provenance": {
                "source": local_override.field_sources.get("delegation.current_target", "unset") if current_name else "unset",
                "binding": "delegation.current_target",
                "matched_by": resolution.get("matched_by"),
                "canonical_join_key": "stable_target_id",
                "raw_runtime_identity_stored": False,
            },
            "recovery": recovery,
            "fail_closed": current_status not in {"known"},
        },
        "subjects": subjects,
        "storage": {
            "status": storage_status,
            "layers": [
                {
                    "id": "user-local-target-guidance",
                    "owner": "user-local",
                    "enabled": enabled,
                    "path": user_root,
                    "checked_in": False,
                    "portable_by_user_backup_only": True,
                },
                {
                    "id": "repo-local-overlay",
                    "owner": "repo-local",
                    "path": overlay_path.as_posix(),
                    "exists": overlay_exists,
                    "checked_in": False,
                    "precedence": "overrides user-local guidance only for this repository",
                },
                {
                    "id": "correction-events",
                    "owner": "repo-local",
                    "path": correction_path.as_posix(),
                    "exists": correction_exists,
                    "checked_in": False,
                    "retention": "bounded-by-correction-event-store-update",
                },
            ],
            "conflict_resolution": {
                "suppression": "repo overlay may suppress user-local guidance for one stable target id without deleting user-local data",
                "rename_or_generation_change": "resolve by stable_target_id first; aliases/display names are migration hints only",
                "ambiguous_identity": "fail-closed until the caller supplies one stable target_id",
                "removal": "deleting repo-local overlay or correction events has no checked-in repository meaning",
            },
            "user_local_target_guidance": {
                "enabled": enabled,
                "root": user_root,
                "source": local_override.field_sources.get("local_memory.user_guidance_root", "unset") if user_root else "unset",
                "checked_in": False,
                "portable_by_user_backup_only": True,
            },
            "repo_local_overlay": {
                "path": overlay_path.as_posix(),
                "exists": overlay_exists,
                "checked_in": False,
                "git_ignored": True,
                "safe_to_delete": True,
            },
            "correction_events": {
                "path": correction_path.as_posix(),
                "exists": correction_exists,
                "checked_in": False,
                "bounded_local_retention": True,
                "raw_transcripts_stored": False,
            },
        },
        "precedence": [
            "explicit current user instruction",
            "checked-in repo authority, safety, proof, and policy",
            "checked-in shared Memory for agent-independent repository knowledge",
            "repo-local target overlay under .agentic-workspace/local/",
            "user-local target guidance for this stable target id",
            "agent self-observation",
        ],
        "continuity_rules": {
            "preserve": "guidance survives target revision only when profile revision_policy=preserve",
            "revalidate": "guidance is visible but must be rechecked before use",
            "migrate": "guidance may move to a replacement target with explicit provenance",
            "retire": "guidance is not routed to new work",
        },
        "rule": "Target guidance routes only through a known stable target identity; display names and aliases alone are not sufficient.",
    }


def _guidance_public_operation_entries() -> list[dict[str, Any]]:
    lifecycle_requirements = {
        "promote": "requires a current producer-owned remember receipt or independently admitted recurrence and one canonical destination owner",
        "edit": "requires expected_revision and a semantic instruction change",
        "merge": "requires expected_revision and expected_record_revisions for every active merge subject; atomically marks sources merged into the target",
        "split": "requires expected_revision and at least two replacement instructions; atomically creates replacements and retires the source",
        "suppress": "requires expected_revision and records suppression without deleting provenance",
        "revalidate": "requires expected_revision and resolves current target identity/authority before reuse",
        "weaken": "requires expected_revision and backgrounds routing/claim authority",
        "supersede": "requires expected_revision, expected_record_revisions for the replacement, and an existing distinct replacement guidance id",
        "retire": "requires expected_revision and terminates future routing",
        "delete": "requires expected_revision and leaves provenance-preserving mutation receipt",
    }
    return [
        {
            "operation": operation_id.removeprefix("agent-guidance."),
            "operation_id": operation_id,
            "public": True,
            "generated_operation": True,
            "external_contract": True,
            "generated_parity": "runtime-backed-python-typescript",
            "schema": "schemas/guidance_lifecycle_input.schema.json",
            "result_schema": "agentic-workspace/guidance-lifecycle-result/v1",
            "receipt_schema": "agentic-workspace/guidance-mutation-receipt/v1",
            "callable": "agentic_workspace.agent_guidance.apply_guidance_lifecycle_operation",
            "admission": lifecycle_requirements[operation_id.removeprefix("agent-guidance.")],
            "operation_contract": f"src/agentic_workspace/contracts/operations/{operation_id}.json",
        }
        for operation_id in GUIDANCE_LIFECYCLE_OPERATIONS
    ]


def correction_feedback_contract(*, identity_posture: dict[str, Any]) -> dict[str, Any]:
    current_identity = identity_posture.get("current_target_identity", {})
    current_known = isinstance(current_identity, dict) and current_identity.get("status") == "known"
    storage = identity_posture.get("storage", {}) if isinstance(identity_posture.get("storage"), dict) else {}
    correction_storage = storage.get("correction_events", {}) if isinstance(storage.get("correction_events"), dict) else {}
    return {
        "kind": "agentic-workspace/correction-feedback-contract/v1",
        "status": "ready" if current_known else "fail-closed",
        "target_identity_required": True,
        "failure_recovery": current_identity.get("recovery", "resolve target identity before admitting correction events")
        if isinstance(current_identity, dict)
        else "resolve target identity before admitting correction events",
        "event_schema": {
            "required": [
                "target_identity_ref",
                "desired_behavior",
                "replaced_behavior",
                "applicability",
                "invariant_id",
                "behavior_class",
                "source",
                "source_ref",
                "authority",
                "provenance",
            ],
            "source_types": [
                "explicit-user-correction",
                "remember-instruction",
                "pr-review",
                "orchestrator-review",
                "evaluator-finding",
                "agent-self-observation",
                "external-adapter",
            ],
            "admission_states": [
                "accepted-candidate",
                "accepted-preserved-revision",
                "duplicate-replay",
                "recurrence",
                "contradicted",
                "disputed",
                "superseded",
                "withdrawn",
                "rejected-ambiguous-target",
                "rejected-secret-bearing",
            ],
        },
        "routing": {
            "agent_guidance": "candidate only; promotion threshold is out of scope for raw events",
            "target_suitability": "allowed when applicability and outcome evidence are scoped",
            "shared_memory": "only for agent-independent repository knowledge",
            "no_retention": "required for malformed, secret-bearing, or unauthorised submissions",
            "identity_rule": (
                "Delivery/idempotency identity is separate from semantic correction identity; semantic identity is "
                "derived from invariant_id, behavior_class, target, task/scope, applicability, and consequence rather than wording."
            ),
        },
        "operations": [
            {
                "operation": "submit",
                "operation_id": "correction-event.submit",
                "public": True,
                "generated_operation": True,
                "external_contract": True,
                "callable": "agentic_workspace.agent_guidance.admit_correction_events",
                "admission": "resolves profile names and aliases to one stable target_id before event storage or routing",
            },
            {
                "operation": "query",
                "operation_id": "correction-event.query",
                "public": True,
                "generated_operation": True,
                "external_contract": True,
                "callable": "agentic_workspace.agent_guidance.admit_correction_events",
                "admission": "returns only admitted events matching resolved target_id plus task/scope context",
            },
            {
                "operation": "dispute",
                "operation_id": "correction-event.correct-dispute",
                "public": True,
                "generated_operation": True,
                "external_contract": True,
                "callable": "agentic_workspace.agent_guidance.admit_correction_events",
                "admission": "requires an admitted predecessor_event_id and removes that predecessor from current routing",
            },
            {
                "operation": "supersede",
                "operation_id": "correction-event.withdraw-supersede",
                "public": True,
                "generated_operation": True,
                "external_contract": True,
                "callable": "agentic_workspace.agent_guidance.admit_correction_events",
                "admission": "requires an admitted predecessor_event_id, keeps provenance, and routes only the superseding event",
            },
            {
                "operation": "withdraw",
                "operation_id": "correction-event.withdraw-supersede",
                "public": True,
                "generated_operation": True,
                "external_contract": True,
                "callable": "agentic_workspace.agent_guidance.admit_correction_events",
                "admission": "requires an admitted predecessor_event_id and excludes withdrawn guidance from routing",
            },
            {
                "operation": "migrate-or-retire",
                "operation_id": "correction-event.prune-compact",
                "public": True,
                "generated_operation": True,
                "external_contract": True,
                "callable": "agentic_workspace.agent_guidance.admit_correction_events",
                "admission": "applies the target revision policy before reuse: preserve, revalidate, migrate with predecessor, or retire",
            },
            *_guidance_public_operation_entries(),
        ],
        "decision_surfaces": [
            {
                "contract": "agentic-workspace/correction-capture-decision/v1",
                "callable": "agentic_workspace.agent_guidance.correction_capture_decision",
                "purpose": "distinguish required correction capture from apology, recap, changed requirements, shared Memory, and unavailable host feedback",
            },
            {
                "contract": "agentic-workspace/agent-guidance-route/v1",
                "callable": "agentic_workspace.agent_guidance.route_agent_guidance",
                "purpose": "select the smallest target/task/scope/repository/role/phase bundle before the affected decision",
            },
            {
                "contract": "agentic-workspace/guidance-compliance-result/v1",
                "callable": "agentic_workspace.agent_guidance.observe_agent_guidance",
                "purpose": "record authority-ranked compliance and return contextual consequence state",
            },
            {
                "contract": "agentic-workspace/guidance-consequence-decision/v1",
                "callable": "agentic_workspace.agent_guidance.guidance_consequence_decision",
                "purpose": "derive advisory, review, suitability, human-authorized prohibition, recovery, or product-improvement consequences",
            },
        ],
        "storage": {
            "path": correction_storage.get("path", WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH.as_posix()),
            "checked_in": False,
            "raw_transcripts_stored": False,
            "controlled_by": WORKSPACE_LOCAL_CONFIG_PATH.as_posix(),
            "retention_cap": CORRECTION_EVENT_RETENTION_CAP,
            "retention_operations": ["correction-event.prune-compact"],
            "delete_behavior": "local-only correction events may be deleted without changing checked-in repository meaning",
        },
        "rule": "Correction feedback is a structured local event stream, not a transcript archive and not direct workflow policy.",
    }
