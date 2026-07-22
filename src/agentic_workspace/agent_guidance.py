from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agentic_workspace.config import (
    WORKSPACE_LOCAL_CONFIG_PATH,
    WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH,
    WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH,
    DelegationTargetProfile,
    MixedAgentLocalOverride,
    load_workspace_config,
)

CORRECTION_EVENT_RETENTION_CAP = 20
CORRECTION_EVENT_OPERATIONS = (
    "correction-event.submit",
    "correction-event.query",
    "correction-event.correct-dispute",
    "correction-event.withdraw-supersede",
    "correction-event.prune-compact",
)
ADMITTED_CORRECTION_AUTHORITIES = {"explicit-user-correction", "pr-review", "orchestrator-review", "evaluator-finding"}
ADMITTED_ROUTE_DECISIONS = {"target-guidance", "target-suitability", "memory", "config", "issue", "no-retention"}
TRUSTED_CORRECTION_PRODUCERS = {
    "explicit-user-correction": {"human", "human-reviewer", "user"},
    "pr-review": {"human-reviewer", "review-bot", "maintainer"},
    "orchestrator-review": {"orchestrator", "maintainer"},
    "evaluator-finding": {"evaluator", "verification"},
}


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


def _write_correction_event_store(path: Path, store: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_correction_receipt(*, target_root: Path, receipt: dict[str, Any]) -> Path:
    receipt_id = hashlib.sha256(json.dumps(receipt, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    path = target_root / ".agentic-workspace/local/correction-event-receipts" / f"{receipt_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


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
    if not value:
        return None
    try:
        receipt_path = (target_root / str(value)).resolve()
        receipt_path.relative_to(target_root.resolve())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(receipt, dict):
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
