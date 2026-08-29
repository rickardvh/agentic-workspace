"""Bounded future-decision-value candidates from source-owned outcomes.

This module composes evidence that a host or domain owner already exposes.  It
does not observe commands, parse transcripts, or persist a learning-event log.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

_MATERIAL = {"material", "candidate", "retain"}
_NO_RETENTION = {"no-retention", "one-off", "irrelevant", "low-value", "dismiss"}
_ABSORBED = {"already-absorbed", "absorbed"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text_list(value: Any) -> list[str]:
    return list(dict.fromkeys(str(item).strip() for item in _as_list(value) if str(item).strip()))


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _status(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _candidate_authority(*, source_authority: str, semantic_judgment: bool) -> str:
    if semantic_judgment:
        return "agent-proposed"
    return source_authority or "candidate"


def _existing_identity(signal: dict[str, Any]) -> set[str]:
    return {
        value
        for value in (
            str(signal.get("signal_id") or "").strip(),
            str(signal.get("related_identity") or "").strip(),
            *_text_list(signal.get("related_identities")),
        )
        if value
    }


def _signal_from_evidence(evidence: dict[str, Any]) -> dict[str, Any] | None:
    assessment = _as_dict(evidence.get("assessment"))
    assessment_status = _status(assessment.get("status"))
    known_potential = evidence.get("potential_future_value") is True
    if not assessment_status and not known_potential:
        return None

    evidence_id = str(evidence.get("evidence_id") or evidence.get("id") or "").strip()
    source_owner = str(evidence.get("source_owner") or evidence.get("owner") or "").strip()
    source_class = str(evidence.get("source_class") or "outcome-evidence").strip()
    source_authority = str(evidence.get("authority_state") or "candidate").strip()
    source_revision = str(evidence.get("source_revision") or evidence.get("revision") or "").strip()
    evidence_refs = _text_list(evidence.get("evidence_refs"))
    source_ref = str(evidence.get("source_ref") or "").strip()
    if source_ref and source_ref not in evidence_refs:
        evidence_refs.append(source_ref)
    related_identity = str(assessment.get("related_identity") or evidence.get("related_identity") or "").strip()
    future_decision = str(assessment.get("future_decision") or assessment.get("decision_effect") or "").strip()
    semantic_judgment = bool(assessment.get("semantic_judgment_required") or assessment.get("semantic_judgment"))
    rationale = str(assessment.get("rationale") or "").strip()
    owner_candidates = _text_list(assessment.get("owner_candidates"))
    selected_owner = str(assessment.get("owner") or (owner_candidates[0] if owner_candidates else source_owner)).strip()
    confidence = str(assessment.get("confidence") or "unknown").strip()
    applicability = _as_dict(evidence.get("applicability"))
    direction = _status(evidence.get("direction")) or "unknown"

    identity_seed = {
        "evidence_id": evidence_id,
        "source_owner": source_owner,
        "related_identity": related_identity,
        "future_decision": future_decision,
        "applicability": applicability,
    }
    signal_id = related_identity or f"future-learning:{_digest(identity_seed)[:20]}"
    candidate_authority = _candidate_authority(
        source_authority=source_authority,
        semantic_judgment=semantic_judgment,
    )

    if assessment_status in _NO_RETENTION:
        disposition = {
            "outcome": "dismiss",
            "owner": "none",
            "rationale": rationale or "The source owner assessed this outcome as one-off or without material future decision value.",
        }
    elif assessment_status in _ABSORBED:
        disposition = {
            "outcome": "already-absorbed",
            "owner": selected_owner or "existing-stronger-owner",
            "rationale": rationale or "The current stronger owner already contains the future decision value.",
        }
    else:
        declared_disposition = _as_dict(assessment.get("disposition"))
        disposition = declared_disposition or {
            "outcome": "unresolved",
            "owner": selected_owner or "future-context source owner",
            "next_action": str(
                assessment.get("next_action") or "admit, route to a stronger existing owner, mark already absorbed, or dismiss"
            ),
        }

    decision_contribution = _as_dict(assessment.get("decision_contribution") or evidence.get("decision_contribution"))
    return {
        "kind": "agentic-workspace/future-context-signal/v1",
        "signal_id": signal_id,
        "source_class": source_class,
        "source_owner": source_owner or "unknown-source-owner",
        "source_revision": source_revision,
        "evidence_refs": evidence_refs,
        "evidence_authority_state": source_authority,
        "authority_state": candidate_authority,
        "direction": direction,
        "future_decision": future_decision,
        "confidence": confidence,
        "semantic_judgment": "required" if semantic_judgment else "not-required",
        "applicability": applicability,
        "related_identity": related_identity,
        "owner_candidates": owner_candidates,
        "assessment_status": assessment_status or "not-evaluated",
        "rationale": rationale,
        "relevant": True,
        "status": "unresolved" if disposition.get("outcome") == "unresolved" else "assessed",
        "disposition": disposition,
        **({"decision_contribution": decision_contribution} if decision_contribution else {}),
        "authority_rule": "Candidate authority never exceeds source authority; semantic generalization remains agent-proposed until a destination owner admits it.",
    }


def compile_future_learning(
    evidence: Iterable[dict[str, Any]] | None,
    *,
    existing_signals: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compile ephemeral candidates and attach duplicates to existing owners."""

    source_evidence = [dict(item) for item in (evidence or []) if isinstance(item, dict)]
    signals = [dict(item) for item in (existing_signals or []) if isinstance(item, dict)]
    assessed_count = 0
    dismissed_count = 0
    absorbed_count = 0
    produced_count = 0
    attached_count = 0
    unassessed_count = 0

    for item in source_evidence:
        signal = _signal_from_evidence(item)
        if signal is None:
            unassessed_count += 1
            continue
        assessed_count += 1
        unassessed_count += signal.get("assessment_status") == "not-evaluated"
        outcome = str(_as_dict(signal.get("disposition")).get("outcome") or "")
        dismissed_count += outcome == "dismiss"
        absorbed_count += outcome == "already-absorbed"
        identities = _existing_identity(signal)
        existing_index = next(
            (index for index, current in enumerate(signals) if identities & _existing_identity(current)),
            None,
        )
        if existing_index is not None:
            current = dict(signals[existing_index])
            attached_refs = _text_list(current.get("attached_evidence_refs"))
            for ref in _text_list(signal.get("evidence_refs")):
                if ref not in attached_refs:
                    attached_refs.append(ref)
            current["attached_evidence_refs"] = attached_refs
            current["deduplication"] = {
                "status": "attached-existing-owner",
                "related_identity": str(signal.get("related_identity") or signal.get("signal_id") or ""),
            }
            signals[existing_index] = current
            attached_count += 1
            continue
        signals.append(signal)
        produced_count += 1

    if not source_evidence:
        status = "quiet"
    elif assessed_count == 0:
        status = "not-evaluated"
    elif produced_count or attached_count:
        status = "candidates-produced"
    else:
        status = "assessed-no-candidate"
    return {
        "kind": "agentic-workspace/future-learning-candidate-set/v1",
        "status": status,
        "evidence_count": len(source_evidence),
        "assessed_count": assessed_count,
        "produced_count": produced_count,
        "attached_count": attached_count,
        "dismissed_count": dismissed_count,
        "absorbed_count": absorbed_count,
        "unassessed_count": unassessed_count,
        "signals": signals,
        "none_found_allowed": not source_evidence or (assessed_count == len(source_evidence) and unassessed_count == 0),
        "persistent_store_created": False,
        "rule": "Preserve future decision value through existing source and reconciliation owners; this packet is an ephemeral composition result, not a learning ledger.",
    }
