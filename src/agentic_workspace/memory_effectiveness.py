"""Decision-bound Memory projection and sparse effectiveness feedback."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from agentic_workspace.proof_receipt_admission import proof_receipt_admission


def canonical_planning_delegation(record: dict[str, Any]) -> dict[str, Any]:
    relationships = record.get("relationships")
    delegation = relationships.get("delegation") if isinstance(relationships, dict) else None
    contracts = record.get("specialist_contracts")
    if not isinstance(delegation, dict) or not isinstance(contracts, list):
        return {}
    route = str(delegation.get("route", "") or "").strip()
    has_contract = any(
        isinstance(contract, dict)
        and contract.get("kind") == "planning-delegation/v1"
        and contract.get("target") == f"planning://delegation/{route}"
        for contract in contracts
    )
    if not has_contract:
        return {}
    return {
        "status": str(delegation.get("state", "") or "").strip(),
        "route chosen": route,
        "canonical contract": True,
        "scope": str(delegation.get("scope", "active-plan-work-unit") or "active-plan-work-unit"),
        "parent task custody": str(delegation.get("parent_task_custody", "unchanged") or "unchanged"),
        "bounded child authority": str(
            delegation.get("bounded_child_authority", "separate-binding-decision") or "separate-binding-decision"
        ),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def memory_effectiveness_operation(
    *,
    operation: str,
    target_root: Path | None = None,
    route_matches: list[dict[str, Any]] | None = None,
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expose one bounded runtime adapter for Memory-effect projections."""

    if operation == "project-use" and target_root is not None:
        return project_memory_use(target_root=target_root, route_matches=route_matches or [])
    if operation == "operating-loop-state":
        return _operating_loop_memory_state(packet or {})
    if operation == "compact-packet":
        return _compact_memory_decision_packet(packet or {})
    if operation == "canonical-planning-delegation":
        return canonical_planning_delegation(packet or {})
    if operation == "prove-stronger-owner-resolution":
        return prove_stronger_owner_resolution(packet or {})
    raise ValueError(f"unsupported Memory effectiveness operation: {operation}")


def prove_stronger_owner_resolution(packet: dict[str, Any]) -> dict[str, Any]:
    """Bind one durable fact to an admitted stronger-owner decision and proof receipt."""

    contribution = _as_dict(packet.get("contribution"))
    owner_surface = _as_dict(packet.get("owner_surface"))
    receipt = _as_dict(packet.get("proof_receipt"))
    selected_identity = _as_dict(owner_surface.get("selected_owner_identity"))
    owner_ref = str(owner_surface.get("selected_owner") or selected_identity.get("ref") or "")
    owner_revision = str(selected_identity.get("revision") or "")
    expected_plan_id = Path(owner_ref).name.removesuffix(".plan.json") if owner_ref else ""
    admission = proof_receipt_admission(receipt)
    affected_decision = "planning-route" if owner_surface.get("kind") == "agentic-planning/route-decision/v1" else ""
    checks = {
        "owner_surface_current": owner_surface.get("task_relation") == "continues-selected-owner"
        and owner_surface.get("owner_posture") == "current"
        and owner_surface.get("required_transition") == "none",
        "owner_revision_bound": bool(owner_revision) and receipt.get("subject_revision") == owner_revision,
        "owner_identity_bound": bool(expected_plan_id) and receipt.get("plan_id") == expected_plan_id,
        "affected_decision_bound": affected_decision in _as_list(contribution.get("affected_decisions")),
        "proof_admitted": admission.get("proof_sufficient") is True,
    }
    status = "passed" if all(checks.values()) else "incomplete"
    identity = {
        "fact_id": str(contribution.get("fact_id") or ""),
        "fact_revision": str(contribution.get("fact_revision") or ""),
        "owner": "planning-route-decision" if affected_decision else "",
        "owner_ref": owner_ref,
        "owner_revision": owner_revision,
        "affected_decision": affected_decision,
        "proof_command": str(receipt.get("command") or ""),
    }
    return {
        "kind": "agentic-memory/stronger-owner-resolution/v1",
        "status": status,
        **identity,
        "resolution_id": f"memory-resolution:{_digest(identity)[:16]}",
        "checks": checks,
        "proof_receipt_admission": {
            "status": admission.get("status"),
            "result_class": admission.get("result_class"),
            "reason": admission.get("reason"),
        },
        "evidence_refs": [
            owner_ref,
            *[str(path) for path in _as_list(receipt.get("changed_paths")) if str(path)],
        ],
        "rule": "Memory may change shape only when an admitted proof receipt is revision-bound to the current stronger-owner decision that absorbed the same fact.",
    }


def _fact_id_from_route(route: dict[str, Any]) -> str:
    if str(route.get("match_source") or "") != "durable-fact":
        return ""
    source = str(route.get("source") or route.get("path") or "")
    marker = "#durable_facts."
    return source.split(marker, 1)[1].strip().strip('"') if marker in source else ""


def project_memory_use(*, target_root: Path, route_matches: list[dict[str, Any]]) -> dict[str, Any]:
    """Project exact durable-fact route matches without widening into note prose."""

    manifest_path = target_root / ".agentic-workspace/memory/repo/manifest.toml"
    relevant_routes = [route for route in route_matches if str(route.get("match_source") or "") != "routing-baseline"]
    if not relevant_routes:
        return _memory_use("no-match", relevant_routes=[])
    if not manifest_path.is_file():
        return _memory_use("unavailable", relevant_routes=relevant_routes, resolver="repair the Memory manifest")
    try:
        document = tomllib.loads(manifest_path.read_text(encoding="utf-8-sig"))
        manifest_revision = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return _memory_use("unavailable", relevant_routes=relevant_routes, resolver="repair the Memory manifest")
    facts = _as_dict(document.get("durable_facts"))
    contributions: list[dict[str, Any]] = []
    for route in relevant_routes:
        fact_id = _fact_id_from_route(route)
        fact = _as_dict(facts.get(fact_id))
        if not fact_id or not fact:
            continue
        fact_status = str(fact.get("status") or "active")
        identity = {
            "fact_id": fact_id,
            "manifest_revision": manifest_revision,
            "fact": fact,
        }
        contribution = {
            "kind": "agentic-memory/decision-contribution/v1",
            "status": "projected" if fact_status == "active" else "stale",
            "fact_id": fact_id,
            "fact_revision": "sha256:" + _digest(identity),
            "source_revision": manifest_revision,
            "freshness": "current" if fact_status == "active" else fact_status,
            "owner": str(fact.get("owner") or "memory"),
            "authority_class": str(fact.get("authority_class") or "advisory"),
            "applicability_basis": [
                f"structured-route:{str(route.get('match_source') or '')}",
                f"route-source:{str(route.get('source') or route.get('path') or '')}",
            ],
            "affected_decisions": [str(item) for item in _as_list(fact.get("affected_decisions")) if str(item)],
            "guidance": str(fact.get("summary") or ""),
            "evidence_refs": [str(item) for item in _as_list(fact.get("evidence")) if str(item)],
            "drill_down_ref": str(fact.get("note_ref") or route.get("source") or route.get("path") or ""),
            "lifecycle": {
                key: str(fact.get(key) or "")
                for key in (
                    "promotion_target",
                    "promotion_trigger",
                    "preferred_remediation",
                    "elimination_target",
                    "retention_after_promotion",
                    "promotion",
                    "demotion_or_expiry",
                )
                if str(fact.get(key) or "")
            },
            "authority_boundary": "Memory contributes advisory knowledge; the affected specialist still owns the decision and enforcement.",
        }
        contributions.append(contribution)
    if contributions:
        status = "stale" if all(item["status"] == "stale" for item in contributions) else "projected"
        return _memory_use(status, relevant_routes=relevant_routes, contributions=contributions)
    if relevant_routes:
        return _memory_use(
            "candidate-only",
            relevant_routes=relevant_routes,
            resolver="run the displayed bounded Memory route to resolve semantic applicability",
        )
    return _memory_use("no-match", relevant_routes=[])


def _memory_use(
    status: str,
    *,
    relevant_routes: list[dict[str, Any]],
    contributions: list[dict[str, Any]] | None = None,
    resolver: str = "",
) -> dict[str, Any]:
    contributions = contributions or []
    revision_input = {"status": status, "contributions": contributions, "routes": relevant_routes}
    return {
        "kind": "agentic-workspace/memory-use/v1",
        "status": status,
        "use_revision": "sha256:" + _digest(revision_input),
        "contributions": contributions,
        "candidate_count": len(relevant_routes),
        "projected_count": len([item for item in contributions if item.get("status") == "projected"]),
        "resolver": resolver,
        "agent_decision_required": status == "candidate-only",
        "rule": "Candidate discovery is not consultation or application; only embedded decision contributions count as projected use.",
    }


def _first_ref(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("ref", "path", "source", "command", "run", "id"):
            if str(value.get(key) or "").strip():
                return str(value[key]).strip()
    for item in _as_list(value):
        if ref := _first_ref(item):
            return ref
    return None


def _operating_loop_memory_state(packet: dict[str, Any]) -> dict[str, Any]:
    pull = _as_dict(packet.get("pull"))
    use = _as_dict(packet.get("use"))
    capture = _as_dict(packet.get("capture"))
    pull_status = str(pull.get("status") or "")
    use_status = str(use.get("status") or "")
    if use_status == "projected":
        state, reason = "projected", "decision_contribution_projected"
    elif use_status == "candidate-only" or pull_status == "relevant_notes_found":
        state, reason = "candidate", "candidate_only"
    elif use_status == "stale" or pull_status == "stale":
        state, reason = "stale", "stale_contribution"
    elif pull_status in {"checked_none", "baseline_only"}:
        state, reason = "dismissed", "no_relevant_route"
    elif pull_status == "unavailable" or use_status == "unavailable":
        state, reason = "unavailable", "unavailable"
    elif pull_status == "dismissed":
        state, reason = "dismissed", "explicitly_dismissed"
    else:
        state, reason = "not_applicable", "not_requested"
    capture_status = str(capture.get("status") or "")
    capture_state = (
        "required" if capture_status == "follow_up_required" else "recommended" if capture_status == "capture_candidate" else "none"
    )
    return {
        "state": state,
        "reason_code": reason,
        "route_ref": _first_ref(pull.get("candidate_routes")),
        "contribution_ids": [str(item.get("fact_id")) for item in _as_list(use.get("contributions")) if isinstance(item, dict)],
        "use_revision": str(use.get("use_revision") or ""),
        "capture": capture_state,
    }


def _compact_memory_decision_packet(packet: dict[str, Any]) -> dict[str, Any]:
    pull = _as_dict(packet.get("pull"))
    capture = _as_dict(packet.get("capture"))
    use = _as_dict(packet.get("use"))
    routes = _as_list(pull.get("candidate_routes"))
    relevant = [item for item in routes if isinstance(item, dict) and item.get("match_source") != "routing-baseline"]
    compact_pull = {
        "status": pull.get("status"),
        "recommended_command": pull.get("recommended_command"),
        "route_count": len(routes),
        "relevant_route_count": len(relevant),
        "read_budget": pull.get("read_budget"),
        "agent_decision_required": pull.get("agent_decision_required"),
    }
    if relevant:
        compact_pull["candidate_routes"] = relevant
    use_status = str(use.get("status") or "")
    compact_use: dict[str, Any] = {"status": use_status}
    if use_status in {"projected", "stale", "candidate-only"}:
        compact_use.update(
            {
                key: use[key]
                for key in (
                    "use_revision",
                    "contributions",
                    "candidate_count",
                    "projected_count",
                    "resolver",
                    "agent_decision_required",
                )
                if key in use
            }
        )
    return {
        "kind": packet.get("kind"),
        "label": "knowledge",
        "provenance": "memory",
        "stage": packet.get("stage"),
        "force": packet.get("force"),
        "why_visible": "Agent-owned Memory decision.",
        "pull": {key: value for key, value in compact_pull.items() if value is not None},
        "use": compact_use,
        "capture": {
            "status": capture.get("status"),
            "outcome_count": len(_as_list(capture.get("allowed_outcomes"))),
            "recommended_commands": capture.get("recommended_commands", []),
            "candidate_owner_surface_count": len(_as_list(capture.get("candidate_owner_surfaces"))),
            "agent_decision_required": capture.get("agent_decision_required"),
        },
        "detail_visibility": "details stay behind verbose implement context",
    }


def compile_memory_effectiveness(*, contributions: list[dict[str, Any]], outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify only material outcome evidence; successful ordinary use stays quiet."""

    by_id = {str(item.get("fact_id") or ""): item for item in contributions if str(item.get("fact_id") or "")}
    evaluations: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    lifecycle_reviews: list[dict[str, Any]] = []
    for raw in outcomes:
        outcome = _as_dict(raw)
        fact_id = str(outcome.get("fact_id") or "")
        contribution = _as_dict(by_id.get(fact_id))
        classification, reason = _classify_outcome(contribution=contribution, outcome=outcome)
        identity = {
            "fact_id": fact_id,
            "fact_revision": str(outcome.get("fact_revision") or contribution.get("fact_revision") or ""),
            "decision_id": str(outcome.get("decision_id") or ""),
            "failure_identity": str(outcome.get("failure_identity") or outcome.get("evidence_revision") or ""),
            "classification": classification,
        }
        evaluation = {
            "kind": "agentic-memory/effectiveness-evaluation/v1",
            **identity,
            "evaluation_id": f"memory-effect:{_digest(identity)[:16]}",
            "reason": reason,
            "evidence_authority": str(outcome.get("evidence_authority") or "unavailable"),
        }
        evaluations.append(evaluation)
        finding = _effectiveness_finding(evaluation=evaluation, contribution=contribution, outcome=outcome)
        if finding:
            findings.append(finding)
        review = _lifecycle_review(evaluation=evaluation, contribution=contribution, outcome=outcome)
        if review:
            lifecycle_reviews.append(review)
    input_revision = "sha256:" + _digest({"contributions": contributions, "outcomes": outcomes})
    return {
        "kind": "agentic-memory/effectiveness-feedback/v1",
        "status": "attention" if findings else "quiet",
        "input_revision": input_revision,
        "projected_contributions": contributions,
        "evaluations": evaluations,
        "findings": findings,
        "lifecycle_reviews": lifecycle_reviews,
        "storage_posture": "sparse-existing-surfaces-only",
        "rule": "No per-use ledger is created; material recurrence reuses canonical decision, consequence, and Memory lifecycle owners.",
    }


def _classify_outcome(*, contribution: dict[str, Any], outcome: dict[str, Any]) -> tuple[str, str]:
    if not contribution:
        return "routing_projection_miss", "the durable fact did not reach the affected decision"
    if outcome.get("fact_revision") and outcome.get("fact_revision") != contribution.get("fact_revision"):
        return "stale_or_superseded", "outcome evidence references a different fact revision"
    if str(outcome.get("current_authority_status") or "") in {"stale", "superseded", "contradicted"}:
        return "stale_or_superseded", "current authority invalidates or replaces this Memory fact"
    authority = str(outcome.get("evidence_authority") or "")
    if authority in {"", "agent-self-report", "unavailable", "generic-test-pass"}:
        return "outcome_inconclusive", "authoritative outcome evidence is unavailable; agent self-report is insufficient"
    reported = str(outcome.get("outcome") or "")
    known = {
        "contradicted": "apparently_ignored_or_violated",
        "insufficient": "insufficient_or_incorrect_memory",
        "incorrect": "insufficient_or_incorrect_memory",
        "product-defect": "product_or_infrastructure_defect",
        "infrastructure-defect": "product_or_infrastructure_defect",
        "resolved-by-stronger-owner": "resolved_by_stronger_owner",
        "no-material-follow-up": "no_material_follow_up",
        "aligned": "no_material_follow_up",
    }
    classification = known.get(reported, "outcome_inconclusive")
    return classification, f"authoritative outcome classified as {classification}"


def _effectiveness_finding(*, evaluation: dict[str, Any], contribution: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    classification = str(evaluation.get("classification") or "")
    if classification in {"outcome_inconclusive", "no_material_follow_up", "resolved_by_stronger_owner"}:
        return {}
    lifecycle = _as_dict(contribution.get("lifecycle"))
    owner = str(
        outcome.get("product_owner")
        or outcome.get("owner")
        or lifecycle.get("promotion_target")
        or contribution.get("owner")
        or "memory-routing"
    )
    return {
        "kind": "agentic-memory/effectiveness-finding/v1",
        "id": str(evaluation["evaluation_id"]),
        "finding_class": "memory-effectiveness",
        "effectiveness_class": classification,
        "severity": "medium",
        "lifecycle": "unresolved",
        "owner": owner,
        "next_route": str(lifecycle.get("preferred_remediation") or f"route {classification} to {owner}"),
        "trigger": str(lifecycle.get("promotion_trigger") or outcome.get("failure_identity") or "material recurrence"),
        "task_relevant": True,
        "evidence_refs": [str(item) for item in _as_list(outcome.get("evidence_refs")) if str(item)],
        "dedupe_identity": str(evaluation["evaluation_id"]),
    }


def _lifecycle_review(*, evaluation: dict[str, Any], contribution: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    lifecycle = _as_dict(contribution.get("lifecycle"))
    if not lifecycle or evaluation.get("classification") not in {
        "product_or_infrastructure_defect",
        "resolved_by_stronger_owner",
    }:
        return {}
    resolution = _as_dict(outcome.get("stronger_owner_resolution"))
    resolution_identity = {
        key: resolution.get(key)
        for key in ("fact_id", "fact_revision", "owner", "owner_ref", "owner_revision", "affected_decision", "proof_command")
    }
    resolution_checks = _as_dict(resolution.get("checks"))
    resolution_admission = _as_dict(resolution.get("proof_receipt_admission"))
    owner = str(resolution.get("owner") or "")
    promotion_target = str(lifecycle.get("promotion_target") or outcome.get("product_owner") or "")
    proof_passed = (
        resolution.get("kind") == "agentic-memory/stronger-owner-resolution/v1"
        and resolution.get("status") == "passed"
        and bool(resolution_checks)
        and all(value is True for value in resolution_checks.values())
        and resolution_admission.get("status") == "admitted"
        and resolution_admission.get("result_class") == "passed"
        and resolution.get("resolution_id") == f"memory-resolution:{_digest(resolution_identity)[:16]}"
        and resolution.get("fact_id") == contribution.get("fact_id")
        and resolution.get("fact_revision") == contribution.get("fact_revision")
        and resolution.get("affected_decision") in _as_list(contribution.get("affected_decisions"))
        and bool(owner)
        and (owner == contribution.get("owner") or owner in promotion_target)
        and bool(_as_list(resolution.get("evidence_refs")))
    )
    requested = str(lifecycle.get("retention_after_promotion") or "retain")
    disposition = requested if evaluation.get("classification") == "resolved_by_stronger_owner" and proof_passed else "retain"
    return {
        "kind": "agentic-memory/lifecycle-review/v1",
        "fact_id": str(contribution.get("fact_id") or ""),
        "fact_revision": str(contribution.get("fact_revision") or ""),
        "promotion_target": promotion_target,
        "promotion_proof_status": "passed" if proof_passed else "required",
        "stronger_owner_resolution_id": str(resolution.get("resolution_id") or ""),
        "disposition": disposition,
        "requested_post_promotion_shape": requested,
        "retention_basis": "declared-durable-after-remediation" if requested == "retain" else "stronger-owner-proof-required",
        "status": "ready" if proof_passed else "pending-stronger-owner-proof",
        "rule": "A stronger owner changes Memory shape only after an admitted, revision-bound resolution proves it absorbed this exact fact; declared durable rationale remains retained.",
    }
