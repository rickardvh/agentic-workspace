"""Sparse effectiveness and retirement for repository-improvement outcomes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agentic_workspace.evaluation import register_evaluation


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _contains_raw_context(value: Any) -> bool:
    forbidden = {"prompt", "raw_prompt", "transcript", "raw_transcript", "messages", "conversation"}
    if isinstance(value, dict):
        return any(str(key).lower() in forbidden or _contains_raw_context(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_raw_context(item) for item in value)
    return False


def _compact_observation(value: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "observation_id",
        "candidate_id",
        "task_shape",
        "comparable",
        "friction_recurred",
        "benefit_effect",
        "shifted_cost",
        "misclassified",
        "evidence_refs",
        "owner",
    )
    return {key: value[key] for key in allowed if value.get(key) not in (None, "", [], {})}


def _evaluation_definition(*, candidate_id: str, claim: dict[str, Any], owner: str, evidence_refs: list[str]) -> dict[str, Any]:
    evaluation_id = f"repo-improvement-{_digest({'candidate_id': candidate_id, 'claim': claim})[:16]}"
    task_shape = str(claim.get("comparable_task_shape") or "equivalent owner and proof route")
    minimum = max(2, int(claim.get("minimum_comparable_observations") or 2))
    return {
        "id": evaluation_id,
        "question": f"Did {candidate_id} reduce repository operability cost without shifting a larger burden elsewhere?",
        "subject": {
            "type": "repo-improvement-outcome",
            "candidate_id": candidate_id,
            "comparable_task_shape": task_shape,
            "expected_benefit": str(claim.get("expected_benefit") or ""),
            "regression_dimension": str(claim.get("regression_dimension") or ""),
        },
        "criteria": [
            {
                "id": "recurrence",
                "type": "qualitative",
                "question": "Did the original friction recur under comparable later work?",
                "success_condition": "Comparable observations do not reproduce the original material friction.",
                "required": True,
            },
            {
                "id": "operability-benefit",
                "type": "qualitative",
                "question": "Did later work become materially cheaper, clearer, or safer?",
                "success_condition": str(claim.get("expected_benefit") or "Expected operability benefit is observed."),
                "required": True,
            },
            {
                "id": "shifted-cost",
                "type": "qualitative",
                "question": "Did abstraction, coupling, proof, migration, or maintenance cost increase elsewhere?",
                "success_condition": f"No material worsening in {claim.get('regression_dimension') or 'the named regression dimension'}.",
                "required": True,
            },
        ],
        "decision_owner": {"id": owner, "class": "source-owner"},
        "evidence_sources": [{"id": ref, "class": "improvement-evidence"} for ref in evidence_refs]
        or [{"id": candidate_id, "class": "improvement-signal"}],
        "report_sinks": [{"id": str(claim.get("report_sink") or owner), "class": "owner-route"}],
        "selectors": {"candidate_ids": [candidate_id], "task_shapes": [task_shape]},
        "collection_policy": {
            "mode": "local-first",
            "minimum_observations": minimum,
            "comparable_task_shape": task_shape,
            "privacy_safe_context_required": True,
            "retention": "current-comparable-results-only",
        },
        "conclusion_policy": {
            "rule": "source owner concludes only from current comparable observations and checks shifted cost",
            "terminal_states": ["concluded", "abandoned", "superseded"],
        },
        "action_policy": {
            "material_negative_finding": "route-to-originating-source-owner-with-candidate-identity",
            "resolved": "retire-active-improvement-pressure",
        },
    }


def register_repo_improvement_evaluation(*, target_root: Path, effectiveness: dict[str, Any]) -> dict[str, Any]:
    """Register the compiled definition through Evaluation's existing owner."""

    definition = _mapping(effectiveness.get("evaluation_definition"))
    if not definition:
        return {"kind": "agentic-workspace/repo-improvement-evaluation-registration/v1", "status": "not-required"}
    return register_evaluation(
        target_root=target_root,
        evaluation_id=str(definition["id"]),
        question=str(definition["question"]),
        subject=_mapping(definition.get("subject")),
        criteria=[dict(item) for item in _items(definition.get("criteria")) if isinstance(item, dict)],
        decision_owner=_mapping(definition.get("decision_owner")),
        evidence_sources=[dict(item) for item in _items(definition.get("evidence_sources")) if isinstance(item, dict)],
        report_sinks=[dict(item) for item in _items(definition.get("report_sinks")) if isinstance(item, dict)],
        selectors=_mapping(definition.get("selectors")),
        collection_policy=_mapping(definition.get("collection_policy")),
        conclusion_policy=_mapping(definition.get("conclusion_policy")),
        action_policy=_mapping(definition.get("action_policy")),
    )


def compile_repo_improvement_effectiveness(*, candidate: dict[str, Any] | None) -> dict[str, Any]:
    """Classify recurrence and retire or route the originating pressure."""

    candidate = _mapping(candidate)
    claim = _mapping(candidate.get("improvement_claim"))
    implementation_proof = _mapping(candidate.get("implementation_proof"))
    if not candidate or not claim:
        return {}
    candidate_id = str(candidate.get("id") or candidate.get("evidence_fingerprint") or "improvement")
    action_id = str(claim.get("action_id") or candidate.get("action_id") or "")
    execution_id = str(claim.get("execution_id") or candidate.get("execution_id") or "")
    owner = str(claim.get("source_owner") or candidate.get("resulting_owner") or candidate.get("suspected_owner") or "unknown")
    expected_benefit = str(claim.get("expected_benefit") or candidate.get("expected_benefit") or "")
    regression_dimension = str(claim.get("regression_dimension") or "")
    proof_complete = implementation_proof.get("status") == "passed" and bool(implementation_proof.get("evidence_refs"))
    longitudinal_required = bool(claim.get("requires_later_observation"))
    evidence_refs = [
        str(item)
        for source in (candidate.get("evidence_refs"), implementation_proof.get("evidence_refs"))
        for item in _items(source)
        if str(item).strip()
    ]
    rejected_observations = [
        item for item in _items(candidate.get("later_observations")) if isinstance(item, dict) and _contains_raw_context(item)
    ]
    observations = [
        _compact_observation(item)
        for item in _items(candidate.get("later_observations"))
        if isinstance(item, dict) and not _contains_raw_context(item)
    ]
    comparable_shape = str(claim.get("comparable_task_shape") or "")
    comparable = [
        item for item in observations if item.get("comparable") is True or (comparable_shape and item.get("task_shape") == comparable_shape)
    ]
    minimum = max(2, int(claim.get("minimum_comparable_observations") or 2))
    stronger_owner = _mapping(candidate.get("stronger_owner"))
    misclassified = any(item.get("misclassified") is True for item in comparable)
    shifted_regression = any(str(item.get("shifted_cost") or "") in {"material", "worse"} for item in comparable)
    recurred = any(item.get("friction_recurred") is True for item in comparable)
    reduced = any(str(item.get("benefit_effect") or "") in {"reduced", "resolved"} for item in comparable)
    all_resolved = len(comparable) >= minimum and all(
        item.get("friction_recurred") is False and str(item.get("benefit_effect") or "") in {"reduced", "resolved"} for item in comparable
    )

    classification = "awaiting-later-observation"
    disposition = "retain-active-pressure"
    next_action = "collect a later comparable owner-bound observation"
    human_visibility = "background-owner-route"
    signal_state = "active"
    if not expected_benefit or not regression_dimension:
        classification = "claim-incomplete"
        next_action = "state expected benefit and the main plausible shifted-cost dimension before claiming improvement"
        human_visibility = "compact-owner-visible"
    elif not proof_complete:
        classification = "implementation-proof-required"
        next_action = "complete present-tense implementation proof before using later Evaluation"
        human_visibility = "compact-owner-visible"
    elif stronger_owner.get("status") == "absorbed" and stronger_owner.get("owner_ref"):
        classification = "obsolete-stronger-owner"
        disposition = "retire-obsolete-pressure"
        next_action = "retire the original signal and point durable rationale at the stronger owner"
        signal_state = "obsolete"
    elif misclassified:
        classification = "misclassified"
        disposition = "dismiss-or-reroute"
        next_action = "dismiss or reroute the original candidate through its source owner"
        signal_state = "obsolete"
        human_visibility = "compact-owner-visible"
    elif shifted_regression:
        classification = "local-improvement-global-regression"
        disposition = "refine-promote-or-revert"
        next_action = "route the shifted cost to the originating source owner with the same candidate identity"
        human_visibility = "compact-owner-visible"
    elif recurred and not reduced:
        classification = "recurrence-failed-improvement"
        disposition = "refine-promote-or-revert"
        next_action = "route recurrence evidence to the originating source owner with the same candidate identity"
        human_visibility = "compact-owner-visible"
    elif recurred or (comparable and reduced and len(comparable) < minimum):
        classification = "partial-improvement" if recurred and reduced else "inconclusive-comparison"
        disposition = "refine-or-continue-bounded-evaluation"
        next_action = "refine through the source owner or collect enough comparable evidence"
        human_visibility = "compact-owner-visible" if recurred else "background-owner-route"
    elif all_resolved:
        classification = "resolved"
        disposition = "retire-resolved-pressure"
        next_action = "retire active signal, Planning, review, and Memory pressure"
        signal_state = "mitigated"
    elif not longitudinal_required and implementation_proof.get("fully_establishes_claim") is True:
        classification = "resolved-deterministically"
        disposition = "retire-resolved-pressure"
        next_action = "retire active improvement pressure; no longitudinal Evaluation is needed"
        signal_state = "mitigated"
    elif comparable:
        classification = "inconclusive-comparison"
        disposition = "retain-until-comparable"
        next_action = "collect additional comparable evidence without inferring causality from one non-recurrence"

    terminal = classification in {"resolved", "resolved-deterministically", "obsolete-stronger-owner", "misclassified"}
    evaluation_definition = (
        _evaluation_definition(candidate_id=candidate_id, claim=claim, owner=owner, evidence_refs=evidence_refs)
        if longitudinal_required and not terminal and proof_complete and expected_benefit and regression_dimension
        else {}
    )
    rationale = str(candidate.get("counterexample_rationale") or "")
    residue = {
        "signal": "retire" if terminal else "retain",
        "planning": "close-or-shrink" if terminal else "retain-owner",
        "review": "resolve" if terminal else "retain-owner-route",
        "memory": "retire" if terminal else "retain-only-if-future-useful",
        "durable_rationale": rationale if rationale and bool(candidate.get("expensive_to_rediscover")) else "",
    }
    observation_evidence_refs = list(
        dict.fromkeys(str(ref) for item in comparable for ref in _items(item.get("evidence_refs")) if str(ref).strip())
    )
    identity = {
        "candidate_id": candidate_id,
        "action_id": action_id,
        "execution_id": execution_id,
        "implementation_proof_refs": [str(item) for item in _items(implementation_proof.get("evidence_refs")) if str(item)],
        "later_observation_refs": observation_evidence_refs,
    }
    revision_inputs = {
        "identity": identity,
        "claim": claim,
        "implementation_proof": implementation_proof,
        "observations": comparable,
        "stronger_owner": stronger_owner,
        "classification": classification,
        "disposition": disposition,
    }
    revision = "sha256:" + _digest(revision_inputs)
    return {
        "kind": "agentic-workspace/repo-improvement-effectiveness/v1",
        "effectiveness_id": f"repo-improvement-effectiveness:{_digest({'revision': revision})[:16]}",
        "input_revision": revision,
        "identity": identity,
        "claim": {
            "expected_benefit": expected_benefit,
            "regression_dimension": regression_dimension,
            "comparable_task_shape": comparable_shape,
            "requires_later_observation": longitudinal_required,
        },
        "implementation_proof": implementation_proof,
        "classification": classification,
        "signal_state": signal_state,
        "disposition": disposition,
        "owner": owner,
        "next_action": next_action,
        "human_visibility": human_visibility,
        "comparable_observation_count": len(comparable),
        "rejected_raw_context_observation_count": len(rejected_observations),
        "evaluation_definition": evaluation_definition,
        "residue": residue,
        "recurring_context_required": not terminal,
        "ordinary_projection": {} if terminal else {"classification": classification, "owner": owner, "next_action": next_action},
        "rule": "Present proof owns implementation truth; owner-bound Evaluation is used only for later operability claims, and mature residue retires.",
    }
