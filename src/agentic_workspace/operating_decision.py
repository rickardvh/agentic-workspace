"""Compose current AW authorities into one internal operating decision."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from agentic_workspace.actionability import invocation_decision_input_revision

BLOCKER_PRECEDENCE = [
    "missing-authority",
    "stale-revision",
    "conflicting-input",
    "denied-effect",
    "stale-mutation-baseline",
    "stale-proof",
    "context-coverage-gap",
    "missing-capability",
]

ORDINARY_DECISION_CONSUMERS = [
    "autopilot",
    "closeout",
    "implement",
    "next",
    "proof",
    "start",
    "status",
    "summary",
]

ORDINARY_DECISION_CONSUMER_REQUIREMENTS = {
    "autopilot": ["planning", "assignment", "mutation-baseline", "proof", "evaluation", "autopilot-executor"],
    "closeout": ["planning", "assignment", "mutation-baseline", "proof", "evaluation", "terminal-outcome"],
    "implement": ["planning", "assignment", "mutation-baseline", "proof", "evaluation", "skills", "target-guidance"],
    "next": ["planning", "assignment", "skills", "target-guidance"],
    "proof": ["planning", "proof", "mutation-baseline", "evaluation"],
    "start": ["system-intent", "planning", "memory", "skills", "target-guidance"],
    "status": ["planning", "assignment", "proof", "evaluation", "terminal-outcome"],
    "summary": ["planning", "memory", "terminal-outcome"],
}

CONTEXT_AUTHORITY_REGISTRY = [
    {
        "surface": "system-intent",
        "owner": "workspace-system-intent",
        "authority_class": "canonical",
        "consumers": ["start", "startup", "implement", "proof", "report", "status", "closeout"],
        "activation": "durable shaping input, not active task state",
        "editable_by": "system-intent sync and explicit repo edits",
        "stale_when": "mirror revision differs from source declaration",
        "proof_route": "system-intent sync and contract tooling checks",
        "disposition": "retain as durable shaping authority",
        "revision_fields": ["system_intent_revision", "mirror_revision"],
    },
    {
        "surface": "planning",
        "owner": "planning package",
        "authority_class": "canonical",
        "consumers": ["start", "summary", "next", "implement", "proof", "autopilot", "status", "closeout"],
        "activation": "active TODO item, selected owner, or current lane slice",
        "editable_by": "planning operations",
        "stale_when": "planning revision or selected owner revision changes",
        "proof_route": "planning package tests and lane health checks",
        "disposition": "retain as current-work authority",
        "revision_fields": ["owner_ref", "owner_revision", "slice_revision"],
    },
    {
        "surface": "memory",
        "owner": "memory package",
        "authority_class": "historical/evidence",
        "consumers": ["start", "summary", "implement", "proof", "report"],
        "activation": "route-selected by task/path/stage",
        "editable_by": "memory operations",
        "stale_when": "manifest route no longer selects or finding is superseded",
        "proof_route": "memory doctor and freshness checks",
        "disposition": "retain as routed evidence, not current-task authority",
        "revision_fields": ["memory_route_revision", "finding_revision"],
    },
    {
        "surface": "assignment",
        "owner": "workspace assignment gate",
        "authority_class": "hard-gate",
        "consumers": ["implement", "next", "autopilot", "closeout", "status"],
        "activation": "selected target, context, allowed effects, and transport policy",
        "editable_by": "target evidence and assignment policy operations",
        "stale_when": "target identity, assignment revision, or transport policy changes",
        "proof_route": "implementation assignment-gate and delegated-return tests",
        "disposition": "retain as execution authority",
        "revision_fields": ["target_identity_ref", "assignment_revision", "manual_transport_policy"],
    },
    {
        "surface": "evaluation",
        "owner": "evaluation runtime",
        "authority_class": "canonical",
        "consumers": ["status", "proof", "implement", "autopilot", "operating-decision", "closeout"],
        "activation": "fresh bound result for the current definition revision",
        "editable_by": "evaluation operations",
        "stale_when": "definition revision or bound result identity changes",
        "proof_route": "evaluation lifecycle tests",
        "disposition": "retain as longitudinal authority when registered",
        "revision_fields": ["evaluation_id", "definition_revision", "current_result_identity"],
    },
    {
        "surface": "proof",
        "owner": "verification and proof runtime",
        "authority_class": "canonical",
        "consumers": ["proof", "implement", "status", "autopilot", "closeout", "operating-decision"],
        "activation": "selected proof subject for current changed paths",
        "editable_by": "proof receipt admission and verification operations",
        "stale_when": "proof subject, selected command, or changed-path fingerprint changes",
        "proof_route": "proof report and receipt reconciliation tests",
        "disposition": "retain as claim authority",
        "revision_fields": ["proof_obligation_id", "proof_subject_fingerprint", "receipt_revision"],
    },
    {
        "surface": "mutation-baseline",
        "owner": "authority envelope",
        "authority_class": "hard-gate",
        "consumers": ["implement", "autopilot", "proof", "closeout"],
        "activation": "current head/scope/target baseline before mutation or admission",
        "editable_by": "authority envelope resolution",
        "stale_when": "head, scope, target, or managed state changes",
        "proof_route": "mutation baseline admission tests",
        "disposition": "retain as mutation authority",
        "revision_fields": ["baseline_id", "head", "scope", "assignment"],
    },
    {
        "surface": "autopilot-executor",
        "owner": "autopilot runtime",
        "authority_class": "hard-gate",
        "consumers": ["autopilot", "final-response", "operating-decision"],
        "activation": "valid executor binding for current owner/target/assignment/proof state",
        "editable_by": "autopilot binding resolver",
        "stale_when": "executor binding fingerprint changes",
        "proof_route": "autopilot executor-binding tests",
        "disposition": "retain as executor authority",
        "revision_fields": ["binding_fingerprint", "availability", "validity"],
    },
    {
        "surface": "skills",
        "owner": "workspace skill registry",
        "authority_class": "canonical",
        "consumers": ["start", "next", "implement"],
        "activation": "task-routed skill viability and dependency checks",
        "editable_by": "skill registry and installed skill metadata",
        "stale_when": "skill registry, dependency status, or routed task shape changes",
        "proof_route": "skill registry and workspace startup tests",
        "disposition": "retain as routed operating guidance",
        "revision_fields": ["skill_id", "registry_revision", "dependency_status"],
    },
    {
        "surface": "target-guidance",
        "owner": "target guidance runtime",
        "authority_class": "canonical",
        "consumers": ["start", "next", "implement"],
        "activation": "target identity, guidance overlay, and execution posture selection",
        "editable_by": "target evidence and guidance identity operations",
        "stale_when": "target identity, guidance overlay, or execution posture changes",
        "proof_route": "target guidance identity and assignment tests",
        "disposition": "retain as target-specific operating context",
        "revision_fields": ["target_identity_ref", "guidance_revision", "execution_posture_revision"],
    },
    {
        "surface": "terminal-outcome",
        "owner": "final-response admission runtime",
        "authority_class": "canonical",
        "consumers": ["summary", "status", "closeout"],
        "activation": "terminal outcome contract, custody, and final-response admission state",
        "editable_by": "final-response admission and continuation operations",
        "stale_when": "terminal outcome, custody, or continuation state changes",
        "proof_route": "final-response and autopilot continuation tests",
        "disposition": "retain as final-claim and continuation authority",
        "revision_fields": ["terminal_state", "custody_owner", "continuation_revision"],
    },
    {
        "surface": "generated-references",
        "owner": "command-generation and contract tooling",
        "authority_class": "generated",
        "consumers": ["cli", "python-adapter", "typescript-adapter", "contract-checks"],
        "activation": "generated freshness and operation registry selection",
        "editable_by": "generators only",
        "stale_when": "source contract revision differs from generated projection",
        "proof_route": "generated command package checks",
        "disposition": "regenerate rather than hand edit",
        "revision_fields": ["command_package_fingerprint", "adapter_fingerprint"],
    },
]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def context_authority_declarations() -> list[dict[str, Any]]:
    schema_keys = {
        "surface",
        "owner",
        "authority_class",
        "consumer",
        "activation",
        "editable_by",
        "stale_when",
        "proof_route",
        "disposition",
    }
    return [
        {key: value for key, value in {**item, "consumer": ", ".join(item["consumers"])}.items() if key in schema_keys}
        for item in CONTEXT_AUTHORITY_REGISTRY
    ]


def _context_authority_registry_items(declarations: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if declarations is None:
        return [dict(item) for item in CONTEXT_AUTHORITY_REGISTRY]
    return [dict(item) for item in declarations if isinstance(item, dict)]


def _registry_consumers(item: dict[str, Any]) -> list[str]:
    consumers = item.get("consumers")
    if isinstance(consumers, list):
        return [str(consumer).strip() for consumer in consumers if str(consumer).strip()]
    consumer = str(item.get("consumer") or "").strip()
    return [part.strip() for part in consumer.split(",") if part.strip()]


def context_authority_coverage(
    *,
    declarations: list[dict[str, Any]] | None = None,
    observed_consumers: list[str] | None = None,
    consumer_requirements: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    registry = _context_authority_registry_items(declarations)
    expected_consumers = sorted({str(item).strip() for item in (observed_consumers or ORDINARY_DECISION_CONSUMERS) if str(item).strip()})
    requirements = {
        str(consumer): [str(surface) for surface in surfaces]
        for consumer, surfaces in (consumer_requirements or ORDINARY_DECISION_CONSUMER_REQUIREMENTS).items()
        if str(consumer).strip()
    }
    consumer_to_surfaces: dict[str, list[str]] = {consumer: [] for consumer in expected_consumers}
    missing_owner_surfaces: list[str] = []
    duplicate_surfaces: list[str] = []
    seen_surfaces: set[str] = set()
    duplicate_canonical_owners: list[str] = []
    owner_to_canonical_surfaces: dict[str, list[str]] = {}
    surfaces: list[str] = []
    for item in registry:
        surface = str(item.get("surface") or "").strip()
        if not surface:
            continue
        if surface in seen_surfaces:
            duplicate_surfaces.append(surface)
        seen_surfaces.add(surface)
        surfaces.append(surface)
        owner = str(item.get("owner") or "").strip()
        if not owner:
            missing_owner_surfaces.append(surface)
        if str(item.get("authority_class") or "") == "canonical":
            owner_to_canonical_surfaces.setdefault(owner, []).append(surface)
        for consumer in _registry_consumers(item):
            if consumer in consumer_to_surfaces:
                consumer_to_surfaces[consumer].append(surface)
    duplicate_canonical_owners = sorted(
        owner for owner, owner_surfaces in owner_to_canonical_surfaces.items() if owner and len(owner_surfaces) > 1
    )
    uncovered_consumers = sorted(consumer for consumer, consumer_surfaces in consumer_to_surfaces.items() if not consumer_surfaces)
    missing_required_sources = {
        consumer: sorted(set(requirements.get(consumer, [])) - set(consumer_to_surfaces.get(consumer, [])))
        for consumer in expected_consumers
        if set(requirements.get(consumer, [])) - set(consumer_to_surfaces.get(consumer, []))
    }
    duplicate_consumer_authorities = sorted(
        consumer
        for consumer, consumer_surfaces in consumer_to_surfaces.items()
        if len(
            [
                surface
                for surface in consumer_surfaces
                if str(next((item.get("authority_class") for item in registry if item.get("surface") == surface), "")) == "canonical"
            ]
        )
        > 4
    )
    status = "measured"
    if uncovered_consumers or missing_required_sources or missing_owner_surfaces or duplicate_surfaces or duplicate_canonical_owners:
        status = "coverage-gap"
    return {
        "kind": "agentic-workspace/context-authority-coverage/v1",
        "status": status,
        "surface_count": len(surfaces),
        "consumer_count": len(expected_consumers),
        "surfaces": surfaces,
        "ordinary_consumers": expected_consumers,
        "consumer_to_surfaces": consumer_to_surfaces,
        "consumer_requirements": {consumer: requirements.get(consumer, []) for consumer in expected_consumers},
        "missing_required_sources": missing_required_sources,
        "uncovered_consumers": uncovered_consumers,
        "missing_owner_surfaces": missing_owner_surfaces,
        "duplicate_surfaces": sorted(set(duplicate_surfaces)),
        "duplicate_canonical_owners": duplicate_canonical_owners,
        "duplicate_consumer_authorities": duplicate_consumer_authorities,
        "rule": "Operating decisions measure declared authority coverage against ordinary consumers and fail closed on missing owners, duplicate surfaces, or uncovered consumers.",
    }


def _surface_gap_class(surface: dict[str, Any]) -> str:
    requirement_status = str(surface.get("requirement_status") or "").strip()
    population_status = str(surface.get("population_status") or "").strip()
    routing_status = str(surface.get("routing_status") or "").strip()
    coverage_status = str(surface.get("coverage_status") or "").strip()
    freshness_status = str(surface.get("freshness_status") or "").strip()
    finding_status = str(surface.get("finding_status") or "").strip()
    source_status = str(surface.get("source_status") or "").strip()
    if source_status == "undeclared":
        return "consumer-without-source"
    if requirement_status == "required" and population_status == "missing":
        return "configured-but-missing"
    if requirement_status == "required" and population_status == "below-minimum":
        return "configured-but-unpopulated"
    if population_status == "present" and routing_status == "unreachable":
        return "declared-but-unroutable"
    if coverage_status == "gap":
        return "coverage-gap"
    if freshness_status == "inference-fallback":
        return "inference-fallback"
    if finding_status == "unresolved":
        return "unresolved-populated-finding"
    return ""


def derive_context_gaps(*, declarations: list[dict[str, Any]], selected_surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    declared = {str(item.get("surface") or ""): item for item in declarations if isinstance(item, dict)}
    gaps: list[dict[str, Any]] = []
    for surface in selected_surfaces:
        if not isinstance(surface, dict):
            continue
        surface_id = str(surface.get("surface") or "").strip()
        admitted_state = _as_dict(surface.get("admitted_state")) or surface
        if surface_id not in declared:
            admitted_state = {**admitted_state, "source_status": "undeclared"}
        gap_class = _surface_gap_class(admitted_state)
        if not gap_class:
            continue
        owner = str(_as_dict(declared.get(surface_id)).get("owner") or surface.get("owner") or "workspace-maintainer")
        severity = str(
            admitted_state.get("severity")
            or surface.get("severity")
            or ("blocking" if admitted_state.get("requirement_status") == "required" else "advisory")
        )
        gaps.append(
            {
                "kind": "agentic-workspace/context-gap/v1",
                "id": f"{gap_class}:{surface_id or 'unknown'}",
                "gap_class": gap_class,
                "surface": surface_id,
                "affected_capability": str(surface.get("affected_capability") or "ordinary-operating-decision"),
                "affected_decisions": _as_list(surface.get("affected_decisions")) or ["routing", "claim-boundary"],
                "evidence_refs": _as_list(surface.get("evidence_refs")),
                "confidence": str(surface.get("confidence") or "high"),
                "severity": severity,
                "current_task_effect": str(surface.get("current_task_effect") or "weakens current AW decision input"),
                "owner": owner,
                "next_route": str(surface.get("next_route") or f"repair or declare lifecycle for {surface_id}"),
            }
        )
    return gaps


def _specialist_blocker(authority: dict[str, Any], *, default_owner: str, default_repair: str = "") -> dict[str, str] | None:
    blocker = _as_dict(authority.get("operating_blocker") or authority.get("blocker"))
    reason_code = str(blocker.get("reason_code") or authority.get("reason_code") or "").strip()
    if not reason_code:
        return None
    return {
        "reason_code": reason_code,
        "owner": str(blocker.get("owner") or authority.get("owner") or default_owner),
        "repair": str(blocker.get("repair") or authority.get("repair") or default_repair or "refresh owning authority"),
    }


def derive_operating_blockers_from_authorities(*, authorities: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    target = _as_dict(authorities.get("target"))
    assignment = _as_dict(authorities.get("assignment_gate") or authorities.get("assignment"))
    transport = _as_dict(authorities.get("manual_transport"))
    mutation = _as_dict(authorities.get("mutation_baseline"))
    evaluation = _as_dict(authorities.get("evaluation"))
    planning = _as_dict(authorities.get("planning_owner") or authorities.get("planning"))
    proof = _as_dict(authorities.get("proof") or authorities.get("proof_obligation"))
    executor = _as_dict(authorities.get("executor") or authorities.get("autopilot_executor"))

    for authority, owner in [
        (target, "assignment target"),
        (assignment, "assignment gate"),
        (transport, "manual transport"),
        (mutation, "mutation authority"),
        (evaluation, "evaluation"),
        (planning, "planning owner"),
        (proof, "proof receipt"),
        (executor, "autopilot executor"),
    ]:
        specialist = _specialist_blocker(authority, default_owner=owner)
        if specialist:
            blockers.append(specialist)

    if str(target.get("status") or "") in {"unknown", "missing", "no-safe-target"}:
        blockers.append({"reason_code": "missing-capability", "owner": "assignment target", "repair": "select a safe target"})
    handoff_admission = str(
        assignment.get("handoff_admission_status")
        or _as_dict(assignment.get("handoff_admission")).get("status")
        or transport.get("handoff_admission_status")
        or _as_dict(transport.get("handoff_admission")).get("status")
        or ""
    )
    assignment_status = str(assignment.get("status") or "")
    transport_status = str(transport.get("status") or "")
    handoff_is_admitted = assignment_status == "handoff-required" and handoff_admission in {
        "admitted",
        "admitted-handoff",
        "manual-required",
    }
    if (transport_status in {"blocked", "disabled"} or assignment_status == "handoff-required") and not handoff_is_admitted:
        blockers.append({"reason_code": "denied-effect", "owner": "manual transport", "repair": "prepare handoff"})
    if str(mutation.get("revalidation_status") or mutation.get("status") or "") in {"stale", "rejected", "failed"}:
        blockers.append({"reason_code": "stale-mutation-baseline", "owner": "mutation authority", "repair": "refresh baseline"})
    evaluation_status = str(evaluation.get("freshness_status") or evaluation.get("status") or "")
    evaluation_required = evaluation.get("required") is True or str(evaluation.get("applicability") or "") == "required"
    if evaluation_status in {"missing", "not-registered"} and evaluation_required:
        blockers.append({"reason_code": "context-coverage-gap", "owner": "evaluation", "repair": "register evaluation"})
    if evaluation_status in {"stale", "superseded", "stale-bound"}:
        blockers.append({"reason_code": "stale-revision", "owner": "evaluation", "repair": "rerun evaluation"})
    if str(planning.get("freshness_status") or planning.get("status") or "") in {"stale", "superseded", "malformed"}:
        blockers.append({"reason_code": "stale-revision", "owner": "planning owner", "repair": "reselect owner"})
    if str(proof.get("receipt_status") or proof.get("status") or "") in {"invalid", "stale", "rejected", "missing"}:
        blockers.append({"reason_code": "stale-proof", "owner": "proof receipt", "repair": "rerun proof"})
    if str(executor.get("availability_status") or _as_dict(executor.get("availability")).get("status") or executor.get("status") or "") in {
        "unavailable",
        "stale-binding",
        "no-valid-executor",
    }:
        blockers.append({"reason_code": "missing-capability", "owner": "autopilot executor", "repair": "rebind executor"})
    return blockers


def _authority_revision(authority: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    revision: dict[str, Any] = {}
    for key in keys:
        if key in authority:
            revision[key] = authority.get(key)
    identity = authority.get("identity")
    if isinstance(identity, dict):
        revision["identity"] = identity
    admission = authority.get("fresh_result_admission") or authority.get("admission")
    if isinstance(admission, dict):
        revision["admission"] = admission
    blocker = authority.get("operating_blocker") or authority.get("blocker")
    if isinstance(blocker, dict):
        revision["blocker"] = blocker
    status = authority.get("status") or authority.get("freshness_status") or authority.get("revalidation_status")
    if status:
        revision["status"] = status
    return revision


def _live_authority_revision_fields(*, authorities: dict[str, Any]) -> dict[str, Any]:
    target = _as_dict(authorities.get("target"))
    assignment = _as_dict(authorities.get("assignment_gate") or authorities.get("assignment"))
    transport = _as_dict(authorities.get("manual_transport"))
    mutation = _as_dict(authorities.get("mutation_baseline"))
    evaluation = _as_dict(authorities.get("evaluation"))
    planning = _as_dict(authorities.get("planning_owner") or authorities.get("planning"))
    proof = _as_dict(authorities.get("proof") or authorities.get("proof_obligation"))
    executor = _as_dict(authorities.get("executor") or authorities.get("autopilot_executor"))
    owner_context_revision = {
        **_authority_revision(planning, ["owner_id", "owner_ref", "owner_revision", "selected_plan_id", "current_work_id"]),
        "target": _authority_revision(target, ["target_identity_ref", "selected_target", "revision"]),
        "assignment": _authority_revision(
            assignment,
            ["assignment_revision", "context_key", "target_identity_ref", "status", "handoff_admission_status"],
        ),
        "transport": _authority_revision(transport, ["status", "policy_revision", "handoff_admission_status"]),
    }
    return {
        "owner_context_revision": owner_context_revision,
        "mutation_boundary": _authority_revision(
            mutation,
            ["baseline_id", "head", "scope", "assignment", "revalidation_status", "mutation_revision"],
        ),
        "proof_requirements": [
            _authority_revision(
                proof,
                ["proof_obligation_id", "proof_subject_fingerprint", "receipt_revision", "receipt_status", "status"],
            )
        ]
        if proof
        else [],
        "evaluation_revision": _authority_revision(
            evaluation,
            ["evaluation_id", "definition_revision", "current_result_identity", "freshness_status", "status", "required"],
        ),
        "executor_revision": _authority_revision(
            executor,
            ["binding_fingerprint", "availability_status", "invocation_revision", "status"],
        ),
    }


def live_decision_input_revision(*, invocation: dict[str, Any], authorities: dict[str, Any]) -> str:
    live_fields = _live_authority_revision_fields(authorities=authorities)
    return invocation_decision_input_revision(
        {
            **invocation,
            **live_fields,
        }
    )


def bind_operation_invocation_to_authorities(*, invocation: dict[str, Any], authorities: dict[str, Any]) -> dict[str, Any]:
    bound = {**invocation, **_live_authority_revision_fields(authorities=authorities)}
    bound["expected_input_revision"] = invocation_decision_input_revision(bound)
    bound["stale_action_rejection"] = {
        **_as_dict(bound.get("stale_action_rejection")),
        "revision_source": "live-authority-resolver",
        "comparison_fields": [
            "expected_input_revision",
            "owner_context_revision",
            "mutation_boundary",
            "proof_requirements",
            "evaluation_revision",
            "executor_revision",
        ],
    }
    return bound


def compile_operating_decision(*, inputs: dict[str, Any]) -> dict[str, Any]:
    """Return one primary typed action or one typed external blocker."""

    revisions = _as_dict(inputs.get("revisions"))
    authorities = _as_dict(inputs.get("authorities"))
    actionability = _as_dict(inputs.get("actionability"))
    action = _as_dict(actionability.get("next_action") or inputs.get("primary_action"))
    progress_check = _as_dict(actionability.get("progress_check"))
    invocation = _as_dict(action.get("operation_invocation"))
    invocation_expected_revision = str(invocation.get("expected_input_revision") or "").strip()
    embedded_invocation_revision = invocation_decision_input_revision(invocation) if invocation else ""
    invocation_current_revision = (
        live_decision_input_revision(invocation=invocation, authorities=authorities)
        if invocation and authorities
        else embedded_invocation_revision
    )
    blockers = [item for item in _as_list(inputs.get("blockers")) if isinstance(item, dict)]
    authority_blockers = derive_operating_blockers_from_authorities(authorities=authorities)
    blockers.extend(authority_blockers)
    for gap in _as_list(inputs.get("context_gaps")):
        if isinstance(gap, dict) and str(gap.get("severity") or "") == "blocking":
            blockers.append({"reason_code": "context-coverage-gap", "owner": gap.get("owner", ""), "repair": gap.get("next_route", "")})
    if (
        not invocation
        and action
        and str(action.get("action") or "") not in {"no-immediate-action", ""}
        and progress_check.get("result") != "rejected-stale-action"
    ):
        blockers.append(
            {
                "reason_code": "missing-authority",
                "owner": "operation-invocation",
                "repair": "attach a typed operation_invocation before treating this action as executable",
            }
        )
    if progress_check.get("result") == "rejected-stale-action" and not authority_blockers:
        blockers.append(
            {
                "reason_code": "stale-revision",
                "owner": "operation-invocation",
                "repair": "refresh the operating decision and rebuild the typed action from current owner/context/proof state",
            }
        )
    elif (
        invocation
        and not authority_blockers
        and (not invocation_expected_revision or invocation_expected_revision != invocation_current_revision)
    ):
        blockers.append(
            {
                "reason_code": "stale-revision",
                "owner": "operation-invocation",
                "repair": "refresh the operating decision and rebuild the typed action from current canonical decision inputs",
            }
        )
    if inputs.get("stale_revision"):
        blockers.append({"reason_code": "stale-revision", "owner": "input-revision", "repair": "refresh authoritative input projection"})
    if inputs.get("conflict"):
        blockers.append(
            {"reason_code": "conflicting-input", "owner": "conflicting authorities", "repair": "resolve specialist input conflict"}
        )
    if inputs.get("denied_effect"):
        blockers.append(
            {"reason_code": "denied-effect", "owner": "effect authority", "repair": "select an allowed effect or request authority"}
        )
    if inputs.get("stale_mutation_baseline"):
        blockers.append({"reason_code": "stale-mutation-baseline", "owner": "mutation authority", "repair": "refresh mutation baseline"})
    if inputs.get("stale_proof"):
        blockers.append({"reason_code": "stale-proof", "owner": "proof authority", "repair": "rerun or re-record selected proof"})
    blockers.sort(
        key=lambda item: (
            BLOCKER_PRECEDENCE.index(str(item.get("reason_code"))) if str(item.get("reason_code")) in BLOCKER_PRECEDENCE else 99
        )
    )
    blocker = blockers[0] if blockers else {}
    if blocker:
        status = "blocked"
        primary_action: dict[str, Any] = {}
        external_blocker = {
            "kind": "agentic-workspace/operating-decision-blocker/v1",
            "reason_code": str(blocker.get("reason_code") or "blocked"),
            "owner": str(blocker.get("owner") or "workspace-maintainer"),
            "repair": str(blocker.get("repair") or "refresh or resolve the owning authority"),
        }
    else:
        status = "actionable" if invocation else "terminal"
        primary_action = action if invocation else {}
        external_blocker = {}
    identity_input = {
        "revisions": revisions,
        "action": invocation,
        "blocker": external_blocker,
        "terminal_state": inputs.get("terminal_state", ""),
        "live_decision_input_revision": invocation_current_revision,
    }
    coverage = context_authority_coverage()
    input_revisions = {
        **revisions,
        **(
            {
                "embedded_action_revision": embedded_invocation_revision,
                "live_authority_revision": invocation_current_revision,
            }
            if invocation
            else {}
        ),
    }
    return {
        "kind": "agentic-workspace/operating-decision/v1",
        "decision_id": f"operating-decision:{_digest(identity_input)[:16]}",
        "status": status,
        "input_revisions": input_revisions,
        "canonical_decision_input_revision": invocation_current_revision,
        "context_authority_coverage": coverage,
        "current_work": _as_dict(inputs.get("current_work")),
        "selected_owner": _as_dict(inputs.get("selected_owner")),
        "terminal_state": str(inputs.get("terminal_state") or "CONTINUE"),
        "primary_action": primary_action,
        "external_blocker": external_blocker,
        "blocked_claim_classes": _as_list(inputs.get("blocked_claim_classes")),
        "provenance": _as_dict(inputs.get("provenance")),
        "replacement_map": {
            "next_action.command": "display rendering only; operation_invocation owns executable identity",
            "actionability.progress_check.proposed_operation": "derived from operation_invocation.operation_id",
            "startup/implement/proof claim gates": "consume operating decision status and blocker reason codes",
        },
        "rule": "This compiler composes admitted specialist outputs and preserves their ownership; it does not infer authority from rendered text.",
    }
