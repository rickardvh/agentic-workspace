"""Revision-bound system-intent expectation and drift composition."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def intent_expectation_from_principle(*, principle: dict[str, Any], intent_revision: str, applicability: dict[str, Any]) -> dict[str, Any]:
    """Build one compact expectation from explicit intent and structured applicability."""

    principle_id = str(principle.get("id") or "").strip()
    structured_basis = [str(item) for item in _as_list(applicability.get("structured_basis")) if str(item).strip()]
    affected = [str(item) for item in _as_list(principle.get("affected_decisions")) if str(item).strip()]
    applicable = bool(principle_id and intent_revision and structured_basis and affected)
    preservation_condition = str(
        principle.get("preservation_condition")
        or principle.get("proof_expectation")
        or principle.get("summary")
        or "Preserve the explicit principle for every affected decision."
    ).strip()
    evidence_route = [
        str(item) for item in _as_list(principle.get("guardrail_refs") or principle.get("evidence_route")) if str(item).strip()
    ]
    enforcement_class = str(principle.get("enforcement_class") or "evidence-and-review-backed")
    identity = {
        "intent_id": principle_id,
        "intent_revision": intent_revision,
        "applicability": structured_basis,
        "affected_decisions": affected,
        "preservation_condition": preservation_condition,
        "enforcement_class": enforcement_class,
    }
    expectation_revision = "sha256:" + _digest(identity)
    return {
        "kind": "agentic-workspace/intent-expectation/v1",
        "status": "applicable" if applicable else "non-applicable",
        "expectation_id": f"intent-expectation:{_digest(identity)[:16]}",
        "expectation_revision": expectation_revision,
        "intent_id": principle_id,
        "intent_revision": intent_revision,
        "intent_authority": str(principle.get("authority") or "repo-system-intent"),
        "intent_owner": str(principle.get("owner") or "human/domain owner"),
        "applicability_basis": structured_basis,
        "affected_decisions": affected,
        "preservation_condition": preservation_condition,
        "evidence_route": evidence_route,
        "enforcement_class": enforcement_class,
        "consumer_refs": [str(item) for item in _as_list(principle.get("consumer_refs")) if str(item).strip()],
        "source_ref": str(principle.get("source") or ".agentic-workspace/system-intent/intent.toml"),
        "rule": "Applicability comes from explicit structured scope or authority evidence; arbitrary task prose is not an authority source.",
    }


def _intent_expectations_from_architecture_principles(*, principles: list[dict[str, Any]], intent_revision: str) -> list[dict[str, Any]]:
    expectations: list[dict[str, Any]] = []
    for principle in principles:
        if not isinstance(principle, dict):
            continue
        matched_paths = [str(item.get("path") or "") for item in _as_list(principle.get("matched_paths")) if isinstance(item, dict)]
        basis = [f"changed-path:{path}" for path in matched_paths if path]
        matcher = _as_dict(principle.get("matcher"))
        if matcher.get("kind"):
            basis.append(f"declared-matcher:{matcher['kind']}")
        expectations.append(
            intent_expectation_from_principle(
                principle={
                    **principle,
                    "consumer_refs": principle.get("consumer_refs")
                    or ["implement", "proof", "closeout", *[str(item) for item in _as_list(principle.get("guardrail_refs"))]],
                },
                intent_revision=intent_revision,
                applicability={"structured_basis": basis},
            )
        )
    return expectations


def architecture_principles_intent_context(
    *,
    principles: list[dict[str, Any]] | None = None,
    intent_revision: str = "",
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Expose one bounded adapter for architecture-principle intent state."""

    configured = False
    if source_path is not None and source_path.is_file():
        try:
            document = tomllib.loads(source_path.read_text(encoding="utf-8-sig"))
        except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
            document = {}
        configured = any(
            isinstance(principle, dict) and str(principle.get("id") or "").strip()
            for principle in _as_list(document.get("architecture_principles"))
        )
    expectations = _intent_expectations_from_architecture_principles(
        principles=principles or [],
        intent_revision=intent_revision,
    )
    return {
        "configured": configured,
        "expectations": expectations,
    }


def evaluate_intent_expectation(
    *, expectation: dict[str, Any], evidence: dict[str, Any] | None = None, resolution: dict[str, Any] | None = None
) -> dict[str, Any]:
    evidence = _as_dict(evidence)
    resolution = _as_dict(resolution)
    expectation_revision = str(expectation.get("expectation_revision") or "")
    evaluation_base = {
        "expectation_id": str(expectation.get("expectation_id") or ""),
        "expectation_revision": expectation_revision,
        "intent_id": str(expectation.get("intent_id") or ""),
        "intent_revision": str(expectation.get("intent_revision") or ""),
        "affected_decisions": [str(item) for item in _as_list(expectation.get("affected_decisions"))],
    }
    if expectation.get("status") != "applicable":
        posture, reason = "non-applicable", "structured applicability did not admit this expectation"
    elif (
        resolution.get("status") in {"explicitly-rescoped", "waived", "superseded", "accepted-tradeoff"}
        and resolution.get("expectation_revision") == expectation_revision
        and resolution.get("authorized_by")
    ):
        posture, reason = "explicitly-rescoped", "the intent owner recorded an expectation-revision-bound disposition"
    elif not evidence or evidence.get("expectation_revision") != expectation_revision:
        posture, reason = "unknown", "no evidence addresses this exact expectation revision"
    else:
        authority = str(evidence.get("authority_class") or "unknown")
        addresses = {str(item) for item in _as_list(evidence.get("addresses"))}
        affected = set(evaluation_base["affected_decisions"])
        evidence_addresses = bool(affected & addresses)
        outcome = str(evidence.get("outcome") or "unknown")
        enforcement = str(expectation.get("enforcement_class") or "evidence-and-review-backed")
        authority_sufficient = authority not in {"unknown", "agent-self-report"}
        preservation_sufficient = authority_sufficient and (
            enforcement == "mechanically-checkable" or authority in {"human-owner", "domain-owner", "independent-review"}
        )
        if outcome == "contradicted" and evidence_addresses and authority_sufficient:
            posture, reason = "drift", "authoritative evidence contradicts an affected decision/property"
        elif outcome == "preserved" and evidence_addresses and preservation_sufficient:
            posture, reason = "preserved", "evidence addresses the affected decision/property at the required judgment class"
        else:
            posture, reason = "unknown", "evidence is missing, low-authority, or does not address the intent expectation"
    result = {
        "kind": "agentic-workspace/intent-expectation-evaluation/v1",
        **evaluation_base,
        "posture": posture,
        "reason": reason,
        "evidence_refs": [str(item) for item in _as_list(evidence.get("evidence_refs")) if str(item).strip()],
        "resolution": resolution if posture == "explicitly-rescoped" else {},
    }
    result["evaluation_id"] = f"intent-evaluation:{_digest(result)[:16]}"
    return result


def _intent_finding(expectation: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    finding_identity = {
        "expectation_id": expectation.get("expectation_id"),
        "expectation_revision": expectation.get("expectation_revision"),
        "affected_decisions": expectation.get("affected_decisions", []),
    }
    return {
        "kind": "agentic-workspace/system-intent-finding/v1",
        "id": f"system-intent-drift:{_digest(finding_identity)[:16]}",
        "finding_class": "intent-conflict",
        "gap_class": "intent-conflict",
        "drift_class": "system-intent-drift",
        "lifecycle": "unresolved",
        "severity": "blocking" if expectation.get("enforcement_class") == "mechanically-checkable" else "medium",
        "task_relevant": True,
        "intent_ref": str(expectation.get("intent_id") or ""),
        "intent_revision": str(expectation.get("intent_revision") or ""),
        "expectation_id": str(expectation.get("expectation_id") or ""),
        "expectation_revision": str(expectation.get("expectation_revision") or ""),
        "affected_decisions": list(expectation.get("affected_decisions", [])),
        "evidence_refs": list(evaluation.get("evidence_refs", [])),
        "confidence": "high" if evaluation.get("evidence_refs") else "medium",
        "owner": str(expectation.get("intent_owner") or "human/domain owner"),
        "current_task_effect": "requires intent-owner review before the affected claim or decision may be treated as preserved",
        "next_route": "record an evidence-backed correction, authorized rescope, waiver, supersession, or accepted tradeoff",
    }


def _coverage_gap(expectation: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/context-gap/v1",
        "id": f"unembodied-intent:{_digest({'expectation': expectation.get('expectation_revision')})[:16]}",
        "finding_class": "context-coverage-gap",
        "gap_class": "unembodied-intent",
        "lifecycle": "unresolved",
        "severity": "medium",
        "task_relevant": True,
        "intent_ref": str(expectation.get("intent_id") or ""),
        "intent_revision": str(expectation.get("intent_revision") or ""),
        "affected_decisions": list(expectation.get("affected_decisions", [])),
        "owner": str(expectation.get("intent_owner") or "workspace-system-intent"),
        "current_task_effect": "the explicit intent has no effective consumer, check, proof route, or review hook",
        "next_route": "route the coverage gap through the existing context-authority or improvement owner",
    }


def compile_intent_feedback(
    *, expectations: list[dict[str, Any]], evidence: list[dict[str, Any]] | None = None, resolutions: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    evidence_by_revision = {str(item.get("expectation_revision") or ""): item for item in evidence or [] if isinstance(item, dict)}
    resolution_by_revision = {str(item.get("expectation_revision") or ""): item for item in resolutions or [] if isinstance(item, dict)}
    evaluations: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    applicable = [item for item in expectations if isinstance(item, dict) and item.get("status") == "applicable"]
    for expectation in expectations:
        if not isinstance(expectation, dict):
            continue
        revision = str(expectation.get("expectation_revision") or "")
        evaluation = evaluate_intent_expectation(
            expectation=expectation,
            evidence=evidence_by_revision.get(revision),
            resolution=resolution_by_revision.get(revision),
        )
        evaluations.append(evaluation)
        if evaluation["posture"] == "drift":
            findings.append(_intent_finding(expectation, evaluation))
        if expectation.get("status") == "applicable" and not expectation.get("consumer_refs"):
            findings.append(_coverage_gap(expectation))
    postures = {str(item["posture"]) for item in evaluations}
    status = "drift" if "drift" in postures else "unknown" if "unknown" in postures else "preserved" if "preserved" in postures else "quiet"
    identity = {
        "expectation_revisions": [str(item.get("expectation_revision") or "") for item in applicable],
        "evaluation_ids": [str(item.get("evaluation_id") or "") for item in evaluations],
        "finding_ids": [str(item.get("id") or "") for item in findings],
    }
    return {
        "kind": "agentic-workspace/intent-feedback/v1",
        "status": status,
        "input_revision": "sha256:" + _digest(identity),
        "applicable_expectations": applicable,
        "evaluations": evaluations,
        "findings": findings,
        "highest_impact_finding": findings[0] if findings else {},
        "rule": "Explicit intent is evaluated against the same expectation revision and material drift reuses context consequence ownership.",
    }


def _observed_payload(payload: dict[str, Any], key: str) -> dict[str, Any]:
    direct = _as_dict(payload.get(key))
    if direct:
        return direct
    return _as_dict(_as_dict(payload.get("context")).get(key))


def _observed_evidence(
    *,
    expectation: dict[str, Any],
    outcome: str,
    addresses: list[str],
    evidence_refs: list[str],
    source_kind: str,
) -> dict[str, Any]:
    identity = {
        "expectation_revision": str(expectation.get("expectation_revision") or ""),
        "outcome": outcome,
        "addresses": addresses,
        "evidence_refs": evidence_refs,
        "source_kind": source_kind,
    }
    return {
        "kind": "agentic-workspace/observed-intent-evidence/v1",
        **identity,
        "authority_class": "typed-runtime-observation",
        "observation_revision": "sha256:" + _digest(identity),
        "rule": "The outcome is derived from typed ordinary-product output and is bound to the expectation that shaped the decision.",
    }


def _planning_route_intent_evidence(expectation: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    gate = _observed_payload(payload, "planning_safety_gate")
    route = _as_dict(gate.get("route_decision")) or _observed_payload(payload, "planning_route_decision")
    if not route:
        return {}
    relation = str(route.get("task_relation") or "")
    owner_posture = str(route.get("owner_posture") or "")
    transition = str(route.get("required_transition") or "")
    implementation_allowed = route.get("implementation_allowed")
    contradicted = (
        relation == "independent-pending-scope"
        and owner_posture == "current"
        and transition == "inspect-current-task-scope"
        and implementation_allowed is False
    )
    preserved = relation == "bounded-independent" and transition == "none" and implementation_allowed is True
    if not contradicted and not preserved:
        return {}
    identity = _as_dict(route.get("action_identity"))
    evidence_ref = str(
        identity.get("idempotency_key") or route.get("decision_id") or route.get("input_revision") or "planning-route-decision"
    )
    return _observed_evidence(
        expectation=expectation,
        outcome="contradicted" if contradicted else "preserved",
        addresses=["routing"],
        evidence_refs=[evidence_ref],
        source_kind="agentic-planning/route-decision/v1",
    )


def _completion_cost_intent_evidence(expectation: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    completion_cost = _observed_payload(payload, "successful_completion_cost")
    validation = _as_dict(_as_dict(completion_cost.get("evidence")).get("validation_execution"))
    repeated_unchanged = []
    for item in _as_list(validation.get("runs")):
        run = _as_dict(item)
        subject = _as_dict(run.get("subject"))
        route_id = str(run.get("constituent_id") or run.get("proof_operation_id") or "").replace("-", "_")
        unchanged = bool(subject.get("pre_subject_revision")) and (
            subject.get("pre_subject_revision") == subject.get("post_subject_revision")
        )
        try:
            duration_seconds = float(run.get("duration_seconds") or 0.0)
        except (TypeError, ValueError):
            duration_seconds = 0.0
        if "closeout_trust" in route_id and run.get("rerun") is True and unchanged and duration_seconds >= 60.0:
            repeated_unchanged.append(run)
    if len(repeated_unchanged) < 2:
        return {}
    refs = [str(item.get("evidence_ref") or item.get("run_id") or "completion-cost-run") for item in repeated_unchanged]
    return _observed_evidence(
        expectation=expectation,
        outcome="contradicted",
        addresses=["operating-cost"],
        evidence_refs=refs,
        source_kind=str(validation.get("kind") or "agentic-workspace/validation-completion-cost-observations/v1"),
    )


def _skill_routing_intent_evidence(expectation: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    skill_routing = _observed_payload(payload, "skill_routing")
    if not skill_routing and isinstance(payload.get("recommendations"), list):
        skill_routing = payload
    recommendations = [_as_dict(item) for item in _as_list(skill_routing.get("recommendations"))]
    lexical = [item for item in recommendations if item.get("activation_evidence_class") == "lexical-candidate"]
    if not lexical:
        return {}
    admitted = [item for item in lexical if item.get("recommendation_authority") in {"admitted", "authoritative", "selected", "required"}]
    refs = [
        f"skill-routing:{str(item.get('id') or 'unknown')}:{str(item.get('activation_evidence_class') or 'unknown')}"
        for item in (admitted or lexical)
    ]
    return _observed_evidence(
        expectation=expectation,
        outcome="contradicted" if admitted else "preserved",
        addresses=["skill-selection"],
        evidence_refs=refs,
        source_kind="agentic-workspace/skill-recommendation/v1",
    )


def intent_evidence_from_observed_behavior(*, expectations: list[dict[str, Any]], payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive revision-bound evidence from typed ordinary-product outputs."""

    evidence: list[dict[str, Any]] = []
    for expectation in expectations:
        if not isinstance(expectation, dict) or expectation.get("status") != "applicable":
            continue
        affected = {str(item) for item in _as_list(expectation.get("affected_decisions"))}
        observed: dict[str, Any] = {}
        if "skill-selection" in affected:
            observed = _skill_routing_intent_evidence(expectation, payload)
        if not observed and "operating-cost" in affected:
            observed = _completion_cost_intent_evidence(expectation, payload)
        if not observed and "routing" in affected:
            observed = _planning_route_intent_evidence(expectation, payload)
        if observed:
            evidence.append(observed)
    return evidence


def intent_recurrence_evidence(*, finding: dict[str, Any], observations: list[dict[str, Any]], deterministic: bool) -> dict[str, Any]:
    """Bind repeated observations to one exact drift finding."""

    finding_id = str(finding.get("id") or "")
    admitted = [
        item
        for item in observations
        if isinstance(item, dict) and item.get("finding_id") == finding_id and str(item.get("observation_ref") or "").strip()
    ]
    identity = {
        "finding_id": finding_id,
        "observation_refs": sorted({str(item["observation_ref"]) for item in admitted}),
        "deterministic": deterministic,
    }
    return {
        "kind": "agentic-workspace/intent-drift-recurrence/v1",
        "status": "admitted" if finding_id and len(identity["observation_refs"]) >= 2 else "insufficient",
        **identity,
        "occurrence_count": len(identity["observation_refs"]),
        "recurrence_revision": "sha256:" + _digest(identity),
        "rule": "Recurrence is derived from distinct observations bound to the exact finding; caller counters are not proof.",
    }


def stronger_owner_correction_resolution(
    *,
    finding: dict[str, Any],
    promotion: dict[str, Any],
    owner_proof: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    """Bind a real stronger-owner proof and same-class replay to the promoted finding."""

    owner = str(_as_dict(promotion.get("stronger_owner")).get("owner") or "")
    proof_ready = owner_proof.get("status") in {"ready", "passed", "admitted"}
    replay_status = str(replay.get("status") or "")
    replay_control = str(replay.get("control") or "")
    replay_effective = replay_status in {"prevented", "detected-earlier"} or (replay_status == "blocked" and bool(replay_control))
    valid = (
        promotion.get("status") == "promote-to-stronger-owner"
        and promotion.get("finding_id") == finding.get("id")
        and owner
        and str(owner_proof.get("owner") or "") == owner
        and proof_ready
        and replay_effective
    )
    identity = {
        "finding_id": str(finding.get("id") or ""),
        "promotion_revision": str(promotion.get("promotion_revision") or ""),
        "owner": owner,
        "owner_proof_revision": str(owner_proof.get("proof_revision") or owner_proof.get("revision") or ""),
        "replay_status": replay_status,
        "replay_control": replay_control,
    }
    return {
        "kind": "agentic-workspace/stronger-owner-correction/v1",
        "status": "proven" if valid else "unproven",
        **identity,
        "resolution_revision": "sha256:" + _digest(identity),
        "rule": "Resolution requires the promoted existing owner to pass its proof and prevent or detect the same class earlier.",
    }


def recurrence_promotion(
    *,
    finding: dict[str, Any],
    recurrence: dict[str, Any] | None = None,
    promotion_target: dict[str, Any] | None = None,
    correction_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = _as_dict(promotion_target)
    recurrence = _as_dict(recurrence)
    resolution = _as_dict(correction_resolution)
    eligible = finding.get("lifecycle", "unresolved") not in {"fixed", "dismissed", "resolved", "superseded"}
    recurrence_admitted = (
        recurrence.get("kind") == "agentic-workspace/intent-drift-recurrence/v1"
        and recurrence.get("status") == "admitted"
        and recurrence.get("finding_id") == finding.get("id")
        and recurrence.get("deterministic") is True
        and int(recurrence.get("occurrence_count") or 0) >= 2
    )
    promote = eligible and recurrence_admitted and bool(target.get("owner") and target.get("proof_route"))
    promoted = {
        "kind": "agentic-workspace/intent-drift-promotion/v1",
        "status": "promote-to-stronger-owner" if promote else "retain-existing-disposition",
        "finding_id": str(finding.get("id") or ""),
        "recurrence_revision": str(recurrence.get("recurrence_revision") or ""),
        "recurrence_count": int(recurrence.get("occurrence_count") or 0),
        "deterministic": recurrence.get("deterministic") is True,
        "stronger_owner": target if promote else {},
        "required_proof": str(target.get("proof_route") or "") if promote else "",
        "memory_or_issue_spam_allowed": False,
        "rule": "Repeated deterministic drift strengthens an existing enforceable owner; it does not create a parallel drift ledger.",
    }
    promoted["promotion_revision"] = "sha256:" + _digest(promoted)
    if (
        resolution.get("kind") == "agentic-workspace/stronger-owner-correction/v1"
        and resolution.get("status") == "proven"
        and resolution.get("finding_id") == finding.get("id")
        and resolution.get("promotion_revision") == promoted["promotion_revision"]
        and resolution.get("owner") == _as_dict(promoted.get("stronger_owner")).get("owner")
    ):
        promoted["status"] = "resolved-by-stronger-owner"
        promoted["correction_resolution"] = resolution
    return promoted
