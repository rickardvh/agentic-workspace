from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

_QUIET_DISPOSITIONS = {"fixed", "superseded", "dismissed", "not-applicable", "obsolete"}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalized(value: Any) -> str:
    text = re.sub(r"https?://\S+", "<url>", str(value or "").strip().lower())
    text = re.sub(r"#[0-9]+", "#<issue>", text)
    text = re.sub(r"\b[0-9a-f]{8,}\b", "<identity>", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "<n>", text)
    return " ".join(text.split())


def _candidate_id(*, source_owner: str, owner_class: str, symptom: str, proposed_delta: str) -> str:
    basis = {
        "source_owner": source_owner,
        "owner_class": owner_class,
        "symptom": _normalized(symptom),
        "proposed_delta": _normalized(proposed_delta),
    }
    return "adapt-" + hashlib.sha256(json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]


def simulate_adaptation(candidate: dict[str, Any]) -> dict[str, Any]:
    simulation = _dict(candidate.get("simulation"))
    required = {str(item) for item in _list(simulation.get("required_behaviors")) if str(item)}
    preserved = {str(item) for item in _list(simulation.get("preserved_behaviors")) if str(item)}
    reasons: list[str] = []
    missing_behaviors = sorted(required - preserved)
    if missing_behaviors:
        reasons.append("required-behavior-removed")
    if str(simulation.get("authority_delta") or "none") != "none":
        reasons.append("authority-widened")
    allowed_paths = {str(item) for item in _list(simulation.get("allowed_owner_paths")) if str(item)}
    if allowed_paths and str(candidate.get("source_owner") or "") not in allowed_paths:
        reasons.append("source-owner-outside-admitted-scope")
    before_cost = simulation.get("before_cost")
    after_cost = simulation.get("after_cost")
    if isinstance(before_cost, (int, float)) and isinstance(after_cost, (int, float)) and after_cost > before_cost:
        reasons.append("cost-boundary-worsened")
    before_precision = simulation.get("before_precision")
    after_precision = simulation.get("after_precision")
    if isinstance(before_precision, (int, float)) and isinstance(after_precision, (int, float)) and after_precision < before_precision:
        reasons.append("precision-boundary-worsened")
    complete = bool(required) and before_cost is not None and after_cost is not None
    return {
        "kind": "agentic-workspace/adaptation-simulation/v1",
        "status": "rejected" if reasons else "passed" if complete else "evidence-required",
        "reason_codes": reasons,
        "missing_required_behaviors": missing_behaviors,
        "cost_delta": after_cost - before_cost if isinstance(before_cost, (int, float)) and isinstance(after_cost, (int, float)) else None,
        "precision_delta": (
            after_precision - before_precision
            if isinstance(before_precision, (int, float)) and isinstance(after_precision, (int, float))
            else None
        ),
        "replay_route": candidate.get("validation_route"),
        "rule": "Promotion fails closed when replay removes required behavior, widens authority, or worsens the declared cost/precision boundary.",
    }


def bounded_adaptation_projection(signals: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        adaptation = _dict(signal.get("adaptation"))
        required = (
            "owner_class",
            "source_owner",
            "proposed_delta",
            "authority_requirement",
            "expected_effect",
            "validation_route",
            "rollback",
        )
        if not adaptation or any(adaptation.get(field) in (None, "", [], {}) for field in required):
            continue
        candidate = copy.deepcopy(adaptation)
        candidate["symptom"] = str(signal.get("symptom") or "")
        candidate["evidence"] = {
            "fingerprint": str(signal.get("evidence_fingerprint") or ""),
            "source": str(signal.get("source") or ""),
            "observed_during": str(signal.get("observed_during") or ""),
            "cost": str(signal.get("cost") or ""),
            "recurrence": str(signal.get("recurrence") or ""),
        }
        candidate_id = _candidate_id(
            source_owner=str(candidate["source_owner"]),
            owner_class=str(candidate["owner_class"]),
            symptom=candidate["symptom"],
            proposed_delta=str(candidate["proposed_delta"]),
        )
        grouped.setdefault(candidate_id, []).append(candidate)

    candidates: list[dict[str, Any]] = []
    for candidate_id, equivalents in sorted(grouped.items()):
        candidate = equivalents[0]
        authority = _dict(candidate.get("authority_requirement"))
        disposition = str(candidate.get("disposition") or "active")
        simulation = simulate_adaptation(candidate)
        revision_matched = bool(authority.get("expected_owner_revision")) and authority.get("expected_owner_revision") == authority.get(
            "current_owner_revision"
        )
        auto_eligible = (
            candidate.get("risk_class") == "low"
            and authority.get("mode") == "existing-typed-operation"
            and bool(authority.get("operation_id"))
            and revision_matched
            and simulation["status"] == "passed"
        )
        quiet = disposition in _QUIET_DISPOSITIONS
        candidate.update(
            {
                "kind": "agentic-workspace/bounded-adaptation-candidate/v1",
                "id": candidate_id,
                "status": "quiet"
                if quiet
                else "promotion-ready"
                if auto_eligible
                else "rejected"
                if simulation["status"] == "rejected"
                else "owner-review-required",
                "disposition": disposition,
                "equivalent_signal_count": len(equivalents),
                "evidence": [item["evidence"] for item in equivalents[:3]],
                "simulation_result": simulation,
                "promotion": {
                    "status": "existing-operation-ready"
                    if auto_eligible
                    else "not-authorized"
                    if simulation["status"] == "rejected"
                    else "owner-admission-required",
                    "operation_id": authority.get("operation_id"),
                    "revision_guard": "matched" if revision_matched else "missing-or-stale",
                    "canonical_source_only": True,
                    "learned_override_created": False,
                },
                "retire_when": candidate.get("retire_when")
                or "the canonical owner revision changes and later equivalent evidence no longer contains the original friction",
            }
        )
        candidates.append(candidate)
    active = [candidate for candidate in candidates if candidate["status"] != "quiet"]
    return {
        "kind": "agentic-workspace/bounded-adaptation-projection/v1",
        "status": "attention" if active else "quiet",
        "candidate_count": len(candidates),
        "active_candidate_count": len(active),
        "candidates": candidates,
        "first_line_cost": "none" if not active else "selector-only",
        "rule": "Adaptations are derived from existing improvement evidence, mutate only canonical source owners through existing operations, and never form a learned override layer.",
    }
