from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
TRUSTED_AUTHORITY_EVENT_STORE_PATH = Path(".agentic-workspace/local/trusted-authority-events")


def _guidance_now() -> str:
    return datetime.now(UTC).isoformat()


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
        "task_class": str(event.get("task_class") or applicability.get("task_class") or ""),
        "scope_class": str(event.get("scope_class") or applicability.get("scope_class") or event.get("task_class") or ""),
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
        admission = admit_correction_events(events=existing_events, subjects=subjects, task_class=task_class, scope_class=scope_class)
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
        events = [*existing_events, event]
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
        if accepted_ids:
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


def _store_guidance_receipt(*, target_root: Path, receipt: dict[str, Any], operation_id: str) -> dict[str, Any]:
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
    if existing is None:
        _write_correction_event_store(
            path,
            {"kind": "agentic-workspace/guidance-receipt-index/v1", "receipts": [*receipts, receipt]},
            expected_digest=_json_digest(index) if path.exists() else None,
        )
        stored = receipt
    else:
        stored = existing
    return {
        "kind": "agentic-workspace/guidance-receipt-operation-result/v1",
        "operation_id": operation_id,
        "status": "stored",
        "receipt_ref": str(stored.get("receipt_ref") or ""),
        "receipt": stored,
        "store": GUIDANCE_RECEIPT_INDEX_PATH.as_posix(),
        "rule": "Correction and guidance authority receipts resolve only through this producer-owned index; arbitrary JSON paths are not authority.",
    }


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
) -> dict[str, Any]:
    raise WorkspaceUsageError(
        "trusted authority host events are adapter-owned evidence and cannot be minted by repo-local guidance code; "
        "import a current host event into .agentic-workspace/local/trusted-authority-events and pass its host_event_ref."
    )


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


def _candidate_guidance_store_refs(*, target_root: Path, config: Any | None = None) -> list[Path]:
    refs = [GUIDANCE_LIFECYCLE_STORE_PATH, WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH]
    if config is not None:
        overlay = getattr(config.local_override, "target_guidance_overlay_path", None)
        if overlay:
            refs.append(Path(overlay))
        user_root = getattr(config.local_override, "user_guidance_root", None)
        if user_root:
            user_path = target_root / Path(user_root)
            refs.extend(path.relative_to(target_root) for path in user_path.glob("*/guidance-lifecycle.json") if path.is_file())
    refs.extend(
        [
            Path(".agentic-workspace/memory/guidance-lifecycle.json"),
            Path(".agentic-workspace/local/guidance-policy-review.json"),
            Path(".agentic-workspace/local/guidance-issue-intake.json"),
        ]
    )
    deduped: list[Path] = []
    for ref in refs:
        if ref not in deduped:
            deduped.append(ref)
    return deduped


def _find_guidance_lifecycle_store(target_root: Path, guidance_id: str) -> tuple[Path, dict[str, Any], int] | None:
    config = load_workspace_config(target_root=target_root)
    for store_ref in _candidate_guidance_store_refs(target_root=target_root, config=config):
        path, store = _guidance_lifecycle_store(target_root, store_ref)
        records = [item for item in store["records"] if isinstance(item, dict)]
        index = _guidance_index(records, guidance_id)
        if index is not None:
            store["records"] = records
            return path, store, index
    return None


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
    stored = _store_guidance_receipt(
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
    return {
        **mutation,
        "receipt_ref": stored["receipt_ref"],
        "receipt_store": stored["store"],
        "receipt_custody": stored["receipt"]["custody"],
        "receipt_status": stored["status"],
    }


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


def apply_guidance_promotion(
    *,
    target_root: Path,
    guidance_id: str,
    task_class: str | None = None,
    scope_class: str | None = None,
    explicit_remember: bool = False,
) -> dict[str, Any]:
    """Persist one promoted candidate with its evidence and future lifecycle custody."""
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
    records = [item for item in store["records"] if isinstance(item, dict)]
    existing = next((item for item in records if item.get("guidance_id") == guidance_id), None)
    if isinstance(existing, dict):
        return {
            "kind": "agentic-workspace/guidance-lifecycle-result/v1",
            "status": "already-promoted",
            "record": existing,
            "store": _repo_relative(path, root=target_root),
        }
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
    _write_correction_event_store(
        path,
        {"kind": "agentic-workspace/guidance-lifecycle-store/v1", "records": next_records},
        expected_digest=store_digest if path.exists() else None,
    )
    return {
        "kind": "agentic-workspace/guidance-lifecycle-result/v1",
        "status": "promoted",
        "record": record,
        "store": _repo_relative(path, root=target_root),
        "mutation_receipt": _record_guidance_mutation_receipt(
            operation="promote",
            target_root=target_root,
            store_path=path,
            store_pre_digest=store_digest,
            records=next_records,
            affected_records=[record],
            postconditions=["single-canonical-destination", "active-guidance-created", "promotion-authority-retained"],
            owner_admission=owner_admission,
        ),
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
    _write_correction_event_store(
        path,
        {"kind": "agentic-workspace/guidance-lifecycle-store/v1", "records": records},
        expected_digest=store_digest,
    )
    affected = [record]
    if operation == "merge":
        affected.extend(item for item in records if item.get("guidance_id") in set(merge_guidance_ids or []))
    if operation == "split":
        affected.extend(item for item in records if item.get("guidance_id") in set(record.get("split_replacement_ids", [])))
    return {
        "kind": "agentic-workspace/guidance-lifecycle-result/v1",
        "status": "transitioned",
        "record": record,
        "records": affected,
        "store": _repo_relative(path, root=target_root),
        "mutation_receipt": _record_guidance_mutation_receipt(
            operation=operation,
            target_root=target_root,
            store_path=path,
            store_pre_digest=store_digest,
            records=records,
            affected_records=affected,
            postconditions=[
                "revision-guard-satisfied",
                "lineage-preserved",
                "no-duplicate-active-authority"
                if operation in {"merge", "split", "supersede", "retire", "delete"}
                else "single-record-postcondition",
            ],
            owner_admission=owner_admission,
        ),
    }


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
            "schema": "agentic-workspace/guidance-lifecycle-record/v1",
            "result_schema": "agentic-workspace/guidance-lifecycle-result/v1",
            "receipt_schema": "agentic-workspace/guidance-mutation-receipt/v1",
            "callable": "agentic_workspace.agent_guidance.apply_guidance_promotion"
            if operation_id == "agent-guidance.promote"
            else "agentic_workspace.agent_guidance.transition_guidance",
            "admission": lifecycle_requirements[operation_id.removeprefix("agent-guidance.")],
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
