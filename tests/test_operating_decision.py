from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from tests.workspace_cli_support import cli

from agentic_workspace.actionability import (
    derive_actionability,
    invocation_decision_input_revision,
    operation_invocation,
    proposed_action_input_revision,
)
from agentic_workspace.operating_decision import (
    _resolve_context_authority_source,
    admit_projection_surface_decision_input,
    bind_operation_invocation_to_authorities,
    bind_projection_surface_operating_decision,
    classify_context_currentness,
    compile_context_maintenance_decision,
    compile_operating_decision,
    compile_projection_surface_operating_decision,
    compile_repo_improvement_action,
    compile_repo_improvement_execution,
    compose_claim_authority,
    context_authority_coverage,
    context_authority_declarations,
    context_authority_obligations,
    context_authority_repair_action,
    context_consequence_effects,
    context_surface_admission,
    cross_owner_enforcement_projection,
    derive_context_consequences,
    derive_context_gaps,
    derive_operating_blockers_from_authorities,
    live_decision_input_revision,
    ordinary_decision_enforcement_contract,
    ordinary_decision_enforcement_findings,
    resolve_context_authority_projection,
)


def test_claim_authority_normalizes_aliases_before_block_precedence() -> None:
    result = compose_claim_authority(
        allowed=["active-plan-progress", "claim-active-plan-complete", "bounded-task-progress"],
        blocked=["claim-active-plan-progress"],
    )

    assert result["allowed_claims"] == ["claim-active-plan-complete", "claim-bounded-task-progress"]
    assert result["blocked_claims"] == ["claim-active-plan-progress"]
    assert result["overridden_allowed_claims"] == ["claim-active-plan-progress"]


def test_claim_authority_keeps_unknown_allowed_alias_non_authoritative() -> None:
    result = compose_claim_authority(
        allowed=["unknown-progress-alias"],
        blocked=["unknown-blocking-alias"],
    )

    assert result["allowed_claims"] == []
    assert result["non_authoritative_allowed_claims"] == ["unknown-progress-alias"]
    assert result["blocked_claims"] == ["unknown-blocking-alias"]


SCHEMA_ROOT = Path("src/agentic_workspace/contracts/schemas")


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def test_ordinary_decision_enforcement_has_one_owner_per_join_identity_and_peer_ratchet() -> None:
    contract = ordinary_decision_enforcement_contract()
    assert ordinary_decision_enforcement_findings(contract) == []
    assert {item["dimension"] for item in contract["dimensions"]} == {
        "current-work",
        "current-target",
        "proof-requirement-subject",
        "mutation-permission",
        "claim-boundary",
        "future-relevant-residue",
    }
    assert [item["surface"] for item in contract["peer_surfaces"] if item["disposition"] == "canonical"] == ["operating-decision"]

    forked = copy.deepcopy(contract)
    forked["peer_surfaces"].append(
        {"surface": "new-first-line-authority", "disposition": "canonical", "decision_identity_field": "decision_id"}
    )
    assert "operating-decision must be the only canonical peer decision surface" in ordinary_decision_enforcement_findings(forked)


def test_cross_owner_enforcement_rejects_stale_or_scope_widening_peer() -> None:
    decision = {
        "decision_id": "operating-decision:0123456789abcdef",
        "admitted_input_revision": "sha256:" + "a" * 64,
        "canonical_decision_input_revision": "sha256:current",
    }
    admitted = cross_owner_enforcement_projection(
        decision=decision,
        peer_projections=[
            {"surface": "start", "disposition": "derived", "decision_id": decision["decision_id"]},
            {"surface": "proof", "disposition": "derived", "decision_id": decision["decision_id"]},
        ],
    )
    assert admitted["status"] == "admitted"

    blocked = cross_owner_enforcement_projection(
        decision=decision,
        peer_projections=[
            {
                "surface": "implement",
                "disposition": "derived",
                "decision_id": "operating-decision:fedcba9876543210",
                "widens_effects": True,
            }
        ],
    )
    assert blocked["status"] == "blocked"
    assert any("stale decision identity" in finding for finding in blocked["findings"])
    assert any("widens effects or claims" in finding for finding in blocked["findings"])


def _fixture_source_revision(path: Path) -> str:
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(child.relative_to(path).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(child.read_bytes()).hexdigest().encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _live_mutation_baseline(*, allowed_paths: list[str] | None = None) -> dict[str, object]:
    paths = allowed_paths or ["src/app.py"]
    return {
        "kind": "agentic-workspace/mutation-baseline/v1",
        "status": "clean-scope",
        "revalidation_status": "current",
        "baseline_id": "baseline-a",
        "head": "abc123",
        "scope": {"allowed_paths": paths, "path_count": len(paths), "comparison": "changed-path-scope"},
        "observation": {"ok": True},
        "observed_state": {"entry_count": 0, "enforcement_fingerprint": "fingerprint-a"},
        "boundary_enforcement": {"status": "fail-closed-contract"},
        "stale_revalidation": {"status": "required"},
        "ownership": {"owner": "current-agent-session"},
    }


def test_operating_decision_emits_one_typed_primary_action() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        effect_class="read-only-report",
        authority_class="verification-owned",
        expected_transition="proof status refreshed",
        preconditions={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        owner_context_revision={"owner_id": "owner-a", "target_identity_ref": "target-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report", "writes_repo_state": False},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json", "owner": "verification"}],
        command_rendering="agentic-workspace proof --target . --format json",
    )

    decision = compile_operating_decision(
        inputs={
            "revisions": {"current_work": "rev-a", "proof": "rev-proof"},
            "current_work": {"id": "work-a"},
            "selected_owner": {"id": "owner-a"},
            "terminal_state": "CONTINUE",
            "actionability": {"next_action": {"action": "run-proof", "operation_invocation": invocation}},
            "provenance": {"proof": "proof runtime"},
        }
    )

    Draft202012Validator(_schema("operation_invocation.schema.json")).validate(invocation)
    Draft202012Validator(_schema("operating_decision.schema.json")).validate(decision)
    assert decision["status"] == "actionable"
    assert decision["primary_action"]["operation_invocation"]["operation_id"] == "proof.report"
    assert decision["primary_action"]["operation_invocation"]["authority_class"] == "verification-owned"
    assert decision["primary_action"]["operation_invocation"]["preconditions"]["assignment_context_key"] == "ctx-a"
    assert decision["primary_action"]["operation_invocation"]["owner_context_revision"]["target_identity_ref"] == "target-a"
    assert decision["primary_action"]["operation_invocation"]["proof_requirements"][0]["owner"] == "verification"
    assert decision["canonical_decision_input_revision"] == invocation_decision_input_revision(invocation)
    assert decision["context_authority_coverage"]["status"] == "measured"
    assert "status" in decision["context_authority_coverage"]["ordinary_consumers"]
    assert decision["primary_action"]["operation_invocation"]["stale_action_rejection"]["status"] == "reject-on-input-revision-mismatch"
    assert decision["external_blocker"] == {}
    assert decision["replacement_map"]["next_action.command"].startswith("display rendering only")


def _material_improvement_candidate(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "id": "candidate-routing-reentry",
        "kind": "workflow_cost",
        "symptom": "agents repeatedly re-enter the same owner route",
        "cost": "three repeated maintenance passes",
        "confidence": "high",
        "recurrence": "repeated",
        "occurrence_count": 3,
        "evidence_classes": ["machine_observed", "review_derived"],
        "expected_benefit": "remove repeated routing and proof-selection work",
        "scope_relation": "current-scope",
        "suspected_owner": "repository-routing",
        "ownership": {"current_owner": True, "mutation_authority_admitted": True},
        "proof_boundary": {"status": "local"},
        "future_cost_effect": {"net_effect": "positive", "added_costs": []},
    }
    candidate.update(overrides)
    return candidate


@pytest.mark.parametrize(
    ("mode", "expected_class", "initiative_authorized"),
    [
        ("none", "report-only", False),
        ("reporting", "report-only", False),
        ("conservative", "improve-touched-scope", True),
        ("balanced", "bounded-current-slice", True),
        ("proactive", "bounded-current-slice", True),
    ],
)
def test_repo_improvement_action_enforces_full_latitude_matrix(mode: str, expected_class: str, initiative_authorized: bool) -> None:
    action = compile_repo_improvement_action(candidate=_material_improvement_candidate(), latitude=mode)

    assert action["action_class"] == expected_class
    assert action["initiative_authorized"] is initiative_authorized
    assert action["awareness"] == {"materiality": "material", "material": True, "mode_independent": True}
    assert action["authority_boundary"].startswith("This consequence permits initiative only")
    if not initiative_authorized:
        assert action["human_visibility"] == "compact-owner-visible"


def test_proactive_requires_strong_evidence_owner_proof_and_positive_future_value_for_standalone_work() -> None:
    permitted = compile_repo_improvement_action(
        candidate=_material_improvement_candidate(scope_relation="standalone-repo"), latitude="proactive"
    )
    weak = compile_repo_improvement_action(
        candidate=_material_improvement_candidate(
            scope_relation="standalone-repo",
            confidence="low",
            recurrence="first_seen",
            occurrence_count=1,
            evidence_classes=["agent_observed"],
        ),
        latitude="proactive",
    )
    missing_proof = compile_repo_improvement_action(
        candidate=_material_improvement_candidate(scope_relation="standalone-repo", proof_boundary={"status": "missing"}),
        latitude="proactive",
    )

    assert permitted["action_class"] == "bounded-standalone-permitted"
    assert permitted["initiative_authorized"] is True
    assert weak["action_class"] == "defer-with-owner"
    assert weak["initiative_authorized"] is False
    assert missing_proof["action_class"] == "promote-or-review"


def test_suspected_owner_does_not_infer_mutation_or_proof_authority() -> None:
    candidate = _material_improvement_candidate()
    candidate.pop("ownership")
    candidate.pop("proof_boundary")

    action = compile_repo_improvement_action(candidate=candidate, latitude="proactive")

    assert action["action_class"] == "promote-or-review"
    assert action["initiative_authorized"] is False
    assert action["proof_boundary"] == "missing"


def test_repo_improvement_action_routes_aw_owned_work_without_consuming_repo_latitude() -> None:
    action = compile_repo_improvement_action(
        candidate=_material_improvement_candidate(scope_relation="aw-internal", suspected_owner="agentic-workspace-package"),
        latitude="none",
    )

    assert action["action_class"] == "route-package-owner"
    assert action["owner"] == "#2647-or-package-owner"
    assert action["initiative_authorized"] is False


def test_repo_improvement_action_routes_explicit_package_owner_class_without_consuming_repo_latitude() -> None:
    action = compile_repo_improvement_action(
        candidate=_material_improvement_candidate(
            suspected_owner="runtime-owner",
            ownership={"owner_class": "package-owned", "current_owner": True, "mutation_authority_admitted": True},
        ),
        latitude="balanced",
    )

    assert action["action_class"] == "route-package-owner"
    assert action["owner"] == "#2647-or-package-owner"
    assert action["initiative_authorized"] is False


@pytest.mark.parametrize("repo_owner", ["packages/frontend", "workspace-tools"])
def test_repo_owner_name_cannot_infer_package_ownership(repo_owner: str) -> None:
    action = compile_repo_improvement_action(
        candidate=_material_improvement_candidate(
            suspected_owner=repo_owner,
            ownership={"owner_class": "repo-owned", "current_owner": True, "mutation_authority_admitted": True},
        ),
        latitude="balanced",
    )

    assert action["action_class"] == "bounded-current-slice"
    assert action["owner"] == repo_owner
    assert action["initiative_authorized"] is True


@pytest.mark.parametrize(
    "boundary",
    ["product-intent", "architecture-direction", "security-trust", "public-compatibility", "broader-ownership", "broader-claim"],
)
def test_repo_improvement_action_requires_human_domain_admission_for_consequential_boundaries(boundary: str) -> None:
    action = compile_repo_improvement_action(
        candidate=_material_improvement_candidate(consequential_boundaries=[boundary]), latitude="proactive"
    )

    assert action["action_class"] == "human-domain-review"
    assert action["initiative_authorized"] is False


def test_local_convenience_is_demoted_when_added_future_cost_is_not_outweighed() -> None:
    action = compile_repo_improvement_action(
        candidate=_material_improvement_candidate(
            added_costs=["new abstraction", "cross-owner coupling", "maintenance surface"],
            future_cost_effect={"net_effect": "uncertain"},
        ),
        latitude="proactive",
    )

    assert action["action_class"] == "dismiss-or-redesign"
    assert action["initiative_authorized"] is False
    assert action["cost_boundary"]["added_costs"] == ["new abstraction", "cross-owner coupling", "maintenance surface"]


def test_repo_improvement_action_is_one_canonical_operating_decision_dimension_across_projections() -> None:
    payload = {
        "task_posture_packet": {
            "operating_posture": {"initiative_posture": {"mode": "balanced"}},
            "improvement_pressure_records": [{**_material_improvement_candidate(), "state": "active"}],
        }
    }
    decisions = []
    for consumer in ("start", "implement", "reconcile", "closeout"):
        admitted = admit_projection_surface_decision_input(
            input_revisions={"current_work": "rev-a", "improvement_pressure": "rev-pressure"},
            consumer=consumer,
        )
        decisions.append(compile_projection_surface_operating_decision(payload=payload, admitted_input=admitted, consumer=consumer))

    assert {item["decision_id"] for item in decisions} == {decisions[0]["decision_id"]}
    assert {item["repo_improvement_action"]["decision_id"] for item in decisions} == {
        decisions[0]["repo_improvement_action"]["decision_id"]
    }
    assert {item["repo_improvement_action"]["initiative_authorized"] for item in decisions} == {True}
    assert {item["repo_improvement_action"]["next_action"] for item in decisions} == {
        decisions[0]["repo_improvement_action"]["next_action"]
    }
    assert all(item["repo_improvement_action"] == decisions[0]["repo_improvement_action"] for item in decisions)
    assert all(item["producer_function"] == "compile_operating_decision" for item in decisions)


def test_enforcing_workflow_requirement_narrows_completion_without_blocking_unrelated_work() -> None:
    admitted = admit_projection_surface_decision_input(input_revisions={"current_work": "rev-a"}, consumer="start")
    payload = {
        "decision_packet": {
            "effects": {"completion_claim_allowed": True, "blocked_claims": []},
            "claim_boundary": {"completion_claim": "allowed-after-proof"},
            "reasons": [],
        },
        "workflow_obligations": {
            "relevant_to_current_work": [
                {"id": "required-review", "force": "required-before-closeout"},
            ]
        },
    }

    decision = compile_projection_surface_operating_decision(
        payload=payload,
        admitted_input=admitted,
        consumer="start",
    )

    assert decision["external_blocker"].get("owner") != "workspace-config-workflow-obligations"
    assert decision["external_blocker"].get("reason_code") != "missing-capability"
    assert decision["blocked_claim_classes"] == ["claim-work-complete"]
    claim_blockers = decision["instruction_clause_projection"]["blockers"]
    assert claim_blockers == [
        {
            "reason_code": "missing-capability",
            "owner": "workspace-config-workflow-obligations",
            "repair": "satisfy human:workflow-obligation-disposition:required-review through its source owner",
            "clause_id": "adapter:bounded_controls:required-review",
            "target": "claim:claim-work-complete",
        }
    ]

    bound = bind_projection_surface_operating_decision(
        payload=payload,
        admitted_input=admitted,
        operating_decision=decision,
        consumer="start",
    )
    packet = bound["decision_packet"]
    assert packet["effects"]["completion_claim_allowed"] is False
    assert packet["effects"]["blocked_claims"] == ["claim-work-complete"]
    assert packet["claim_boundary"]["completion_claim"] == "blocked-until-proof-and-acceptance"
    assert packet["claim_blockers"] == claim_blockers
    assert packet["reasons"] == ["instruction_requirement_unsatisfied"]


def test_advisory_workflow_obligation_does_not_narrow_completion() -> None:
    admitted = admit_projection_surface_decision_input(input_revisions={"current_work": "rev-a"}, consumer="start")
    payload = {
        "decision_packet": {
            "effects": {"completion_claim_allowed": True, "blocked_claims": []},
            "claim_boundary": {"completion_claim": "allowed-after-proof"},
            "reasons": [],
        },
        "workflow_obligations": {
            "relevant_to_current_work": [
                {"id": "suggested-review", "force": "recommended"},
            ]
        },
    }

    decision = compile_projection_surface_operating_decision(
        payload=payload,
        admitted_input=admitted,
        consumer="start",
    )
    bound = bind_projection_surface_operating_decision(
        payload=payload,
        admitted_input=admitted,
        operating_decision=decision,
        consumer="start",
    )

    assert decision["instruction_clause_projection"]["blockers"] == []
    assert decision["blocked_claim_classes"] == []
    assert bound["decision_packet"]["effects"]["completion_claim_allowed"] is True


def test_selected_current_assignment_preserves_existing_implement_action() -> None:
    admitted = admit_projection_surface_decision_input(
        input_revisions={"current_work": "rev-a", "assignment": "assignment-rev-a"},
        consumer="implement",
    )
    assignment_action = {
        "status": "direct-current-target",
        "action": "continue-local",
        "assignment_decision_revision": "assignment-rev-a",
        "target_identity_ref": "target:current",
    }

    decision = compile_projection_surface_operating_decision(
        payload={
            "assignment_action": assignment_action,
            "next": {"action": "Resolve boundary warnings before editing."},
        },
        admitted_input=admitted,
        consumer="implement",
    )

    assert decision["projection_posture"]["primary_action"] == {"action": "Resolve boundary warnings before editing."}
    assert assignment_action["assignment_decision_revision"] == "assignment-rev-a"
    assert assignment_action["target_identity_ref"] == "target:current"


def test_nonlocal_assignment_action_preempts_local_implement_action() -> None:
    admitted = admit_projection_surface_decision_input(
        input_revisions={"current_work": "rev-a", "assignment": "assignment-rev-b"},
        consumer="implement",
    )
    assignment_action = {
        "status": "ready",
        "action": "dispatch-assigned-target",
        "assignment_decision_revision": "assignment-rev-b",
        "target_identity_ref": "target:worker",
        "implementation_allowed": False,
    }

    decision = compile_projection_surface_operating_decision(
        payload={
            "assignment_action": assignment_action,
            "next": {"action": "Inspect only the listed files and run the required validation commands."},
        },
        admitted_input=admitted,
        consumer="implement",
    )

    assert decision["projection_posture"]["primary_action"] == assignment_action


def test_no_improvement_candidate_keeps_direct_work_quiet() -> None:
    decision = compile_operating_decision(inputs={"revisions": {"current_work": "rev-a"}})

    assert decision["status"] == "terminal"
    assert decision["primary_action"] == {}
    assert decision["repo_improvement_action"] == {}
    assert decision["repo_improvement_execution"] == {}
    assert decision["repo_improvement_effectiveness"] == {}


def _coverage_observation(**overrides: object) -> dict[str, object]:
    observation: dict[str, object] = {
        "source_class": "agent",
        "owner_class": "scoped-instruction",
        "source_owner": ".agentic-workspace/instructions/api.md",
        "observed_addition": "API work repeatedly requires a compatibility procedure.",
        "source_refs": ["src/api/router.py"],
        "evidence_refs": ["tests/test_api_compat.py"],
        "affected_effects": ["procedure", "proof"],
        "operation_id": "instructions.create",
        "owner_revision": "owner-r1",
        "proposed_delta": {
            "action": "append_guidance",
            "heading": "API compatibility",
            "guidance": "Run API compatibility proof after boundary changes.",
            "positive_paths": ["src/api/**"],
            "negative_paths": ["docs/**"],
        },
        "validation_route": ["pytest tests/test_api_compat.py -q"],
    }
    observation.update(overrides)
    return observation


def test_material_coverage_candidate_enters_existing_closeout_gate() -> None:
    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "stage": "closeout",
            "coverage_observations": [_coverage_observation()],
        }
    )

    assert decision["bounded_adaptations"]["active_candidate_count"] == 1
    assert decision["context_effects"]["closeout_obligations"][0]["owner"] == ".agentic-workspace/instructions/api.md"
    assert {"full-intent-complete", "issue-closure"}.issubset(set(decision["blocked_claim_classes"]))
    candidate = decision["bounded_adaptations"]["candidates"][0]
    assert candidate["coverage"]["authority"] == "evidence"
    assert candidate["status"] == "owner-review-required"
    assert decision["primary_action"]["action"] == "request-context-maintenance-decision"
    assert decision["primary_action"]["decision_id"] == decision["maintenance_decision"]["decision_id"]


def test_deferrable_coverage_candidate_does_not_block_unrelated_direct_work() -> None:
    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "coverage_observations": [_coverage_observation(defer_until="next src/api/** change")],
        }
    )

    assert decision["context_effects"]["blocked_claim_classes"] == []
    assert decision["context_effects"]["durable_dispositions"][0]["status"] == "deferred-with-owner"
    assert decision["context_effects"]["durable_dispositions"][0]["reentry_trigger"] == "next src/api/** change"


def test_disposed_or_absent_coverage_is_quiet() -> None:
    no_signal = compile_operating_decision(inputs={"consumer": "unregistered-test-consumer"})
    disposed = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "coverage_observations": [_coverage_observation(disposition="dismissed")],
        }
    )

    assert no_signal["bounded_adaptations"]["status"] == "quiet"
    assert no_signal["bounded_adaptations"]["candidate_count"] == 0
    assert disposed["bounded_adaptations"]["status"] == "quiet"
    assert disposed["context_effects"]["status"] == "quiet"


def test_projection_operating_decision_consumes_proof_route_adaptation_signal() -> None:
    signal = {
        "symptom": "broad command is safely subsumed",
        "evidence_fingerprint": "proof-route-refinement-1",
        "source": "proof_route_maintenance.route_refinement_evidence",
        "observed_during": "proof-route-execution",
        "cost": "disproportionate",
        "recurrence": "observed",
        "adaptation": {
            "owner_class": "proof-route",
            "source_owner": ".agentic-workspace/config.toml",
            "proposed_delta": {"action": "upsert_domain_lane", "lane_id": "example"},
            "authority_requirement": {
                "mode": "existing-typed-operation",
                "operation_id": "proof.report",
                "expected_owner_revision": "rev-a",
                "current_owner_revision": "rev-a",
            },
            "risk_class": "low",
            "expected_effect": {"required_coverage": "preserved"},
            "validation_route": ["pytest tests/test_example.py -q"],
            "rollback": {"mode": "operation-transaction"},
            "simulation": {
                "required_behaviors": ["example-owner-claim"],
                "preserved_behaviors": ["example-owner-claim"],
                "authority_delta": "none",
                "allowed_owner_paths": [".agentic-workspace/config.toml"],
                "before_cost": 20,
                "after_cost": 10,
                "before_precision": 0.5,
                "after_precision": 1.0,
            },
        },
    }
    admitted = admit_projection_surface_decision_input(input_revisions={"current_work": "rev-a"}, consumer="proof")
    decision = compile_projection_surface_operating_decision(
        payload={"proof_route_maintenance": {"route_health": {"findings": [{"bounded_adaptation_signal": signal}]}}},
        admitted_input=admitted,
        consumer="proof",
    )

    candidate = decision["bounded_adaptations"]["candidates"][0]
    assert candidate["status"] == "promotion-ready"
    assert candidate["promotion"]["operation_id"] == "proof.report"


def test_repo_evidence_strategy_composes_hard_and_advisory_named_requirements() -> None:
    from agentic_workspace.workspace_runtime_proof import (
        _apply_repo_evidence_strategy_to_lanes,
        _repo_evidence_strategy_payload,
    )

    requirements = {
        "active": [
            {
                "id": "property_invariants",
                "requirement_class": "guideline",
                "preference_target": "surface:property-generative-evidence",
                "proof_profile": "property_evidence",
                "source_intent_ref": "docs/testing.md#properties",
                "source_intent_revision": "rev-1",
                "source_intent_current": True,
                "applies_because": ["matched behavior package"],
            },
            {
                "id": "representative_external_examples",
                "requirement_class": "invariant",
                "required_evidence": ["representative-public-example"],
                "proof_profile": "public_examples",
                "blocking_claims": ["claim-work-complete"],
                "evidence_owner": "verification:public-examples",
                "detail_route": "run the host-owned public example check",
                "source_intent_ref": "docs/testing.md#examples",
                "source_intent_revision": "rev-1",
                "source_intent_current": True,
                "applies_because": ["matched exported API"],
            },
            {
                "id": "public_api_only",
                "requirement_class": "invariant",
                "required_evidence": ["public-api-boundary-check"],
                "proof_profile": "public_api_boundary",
                "blocking_claims": ["claim-work-complete"],
                "evidence_owner": "module:host-api-classifier",
                "detail_route": "run the host-owned API-surface classifier",
                "source_intent_ref": "docs/testing.md#public-api-only",
                "source_intent_revision": "rev-1",
                "source_intent_current": True,
                "applies_because": ["host classifier matched library package"],
            },
            {
                "id": "compact_suite_budget",
                "requirement_class": "current-evidence",
                "required_evidence": ["workspace-suite-count-and-runtime"],
                "blocking_claims": ["claim-work-complete"],
                "evidence_owner": "verification:workspace-suite-budget",
                "detail_route": "refresh the repo-owned suite budget measurement",
                "source_intent_ref": "docs/maintainer/testing-strategy.md#budget",
                "source_intent_revision": "budget-r1",
                "source_intent_current": True,
                "applies_because": ["ordinary Workspace evidence changed"],
            },
        ],
        "evidence_status": [
            {"requirement_id": "representative_external_examples", "state": "satisfied"},
            {"requirement_id": "public_api_only", "state": "missing-evidence"},
            {"requirement_id": "compact_suite_budget", "state": "stale"},
        ],
    }
    selected = [
        {
            "command": "pytest tests/test_properties.py -q",
            "assurance_requirement_refs": ["property_invariants"],
        },
        {
            "command": "pytest tests/test_public_examples.py -q",
            "assurance_requirement_refs": ["representative_external_examples"],
        },
        {
            "command": "python scripts/check_public_api_tests.py",
            "assurance_requirement_refs": ["public_api_only"],
        },
    ]

    lanes = [
        {
            "id": "assurance-requirement:representative_external_examples",
            "requirement_id": "representative_external_examples",
            "proof_profile": "public_examples",
            "enough_proof": ["pytest tests/test_public_examples.py -q"],
        },
        {
            "id": "assurance-requirement:property_invariants",
            "requirement_id": "property_invariants",
            "proof_profile": "property_evidence",
            "evidence_concepts": ["property-generative-evidence"],
            "enough_proof": ["pytest tests/test_properties.py -q"],
        },
    ]
    ordered, construction = _apply_repo_evidence_strategy_to_lanes(assurance_requirements=requirements, selected_lanes=lanes)
    replay_ordered, replay_construction = _apply_repo_evidence_strategy_to_lanes(assurance_requirements=requirements, selected_lanes=lanes)
    assert ordered[0]["id"] == "assurance-requirement:property_invariants"
    assert construction == replay_construction
    assert ordered == replay_ordered
    assert {item["effect"] for item in construction["effects"]} == {
        "preferred-evidence-selected",
        "required-evidence-selected",
        "exact-owner-route-required",
    }

    strategy = _repo_evidence_strategy_payload(
        assurance_requirements=requirements,
        selected_commands=selected,
        construction=construction,
        blocked_commands=[
            {
                "command": "pytest tests/test_private_helper.py -q",
                "assurance_requirement_ref": "public_api_only",
            }
        ],
    )
    decision_schema = _schema("operating_decision.schema.json")
    strategy_schema = decision_schema["properties"]["repo_evidence_strategy"]
    strategy_validator = Draft202012Validator(strategy_schema)
    strategy_validator.validate(strategy)
    assert strategy["status"] == "blocked"
    assert {item["class"] for item in strategy["clauses"]} == {"guideline", "invariant", "current-evidence"}
    assert strategy["selected_command_count"] == 3
    assert strategy["clauses"][2]["blocked_commands"] == ["pytest tests/test_private_helper.py -q"]
    assert strategy["construction"]["status"] == "applied"
    assert strategy["hard_blockers"] == [
        {
            "reason_code": "missing-evidence",
            "owner": "module:host-api-classifier",
            "requirement_id": "public_api_only",
            "repair": "run the host-owned API-surface classifier",
            "blocked_claims": ["claim-work-complete"],
        },
        {
            "reason_code": "missing-evidence",
            "owner": "verification:workspace-suite-budget",
            "requirement_id": "compact_suite_budget",
            "repair": "refresh the repo-owned suite budget measurement",
            "blocked_claims": ["claim-work-complete"],
        },
    ]
    assert strategy["advisory_preferences"][0]["id"] == "property_invariants"
    malformed = {**strategy, "selected_command_count": "three"}
    assert list(strategy_validator.iter_errors(malformed))
    unknown = {**strategy, "peer_strategy": {}}
    assert list(strategy_validator.iter_errors(unknown))

    admitted = admit_projection_surface_decision_input(input_revisions={"current_work": "rev-a"}, consumer="proof")
    decision = compile_projection_surface_operating_decision(
        payload={
            "repo_evidence_strategy": strategy,
            "proof_decision": {"status": "accepted", "source": "agent-authored"},
            "manual_verification": {"status": "passed", "source": "agent-authored"},
        },
        admitted_input=admitted,
        consumer="proof",
    )
    assert decision["status"] == "blocked"
    assert "claim-work-complete" in decision["blocked_claim_classes"]
    assert decision["external_blocker"]["owner"] == "module:host-api-classifier"
    assert {item["requirement_id"] for item in decision["repo_evidence_strategy"]["hard_blockers"]} == {
        "public_api_only",
        "compact_suite_budget",
    }
    changed_strategy = copy.deepcopy(strategy)
    changed_strategy["clauses"][0]["authority_revision"] = "rev-2"
    direct = compile_operating_decision(inputs={"revisions": {"current_work": "rev-a"}, "repo_evidence_strategy": strategy})
    changed = compile_operating_decision(inputs={"revisions": {"current_work": "rev-a"}, "repo_evidence_strategy": changed_strategy})
    assert changed["decision_id"] != direct["decision_id"]
    assert changed["admitted_input_revision"] != direct["admitted_input_revision"]


def test_repo_evidence_strategy_has_no_default_methodology() -> None:
    from agentic_workspace.workspace_runtime_proof import _apply_repo_evidence_strategy_to_lanes, _repo_evidence_strategy_payload

    strategy = _repo_evidence_strategy_payload(assurance_requirements={}, selected_commands=[])
    Draft202012Validator(_schema("operating_decision.schema.json")["properties"]["repo_evidence_strategy"]).validate(strategy)
    assert strategy["status"] == "not-declared"
    assert strategy["clauses"] == []
    lanes = [{"id": "private_helper_test", "enough_proof": ["pytest tests/test_private_helper.py -q"]}]
    ordered, construction = _apply_repo_evidence_strategy_to_lanes(
        assurance_requirements={
            "framework_imports": ["hypothesis"],
            "filenames": ["test_private_helper.py"],
            "symbols": ["_private_helper"],
            "strategy_prose": "prefer property tests and public APIs",
        },
        selected_lanes=lanes,
    )
    assert ordered == lanes
    assert construction == {"status": "not-applicable", "effects": [], "owner_decisions": []}


def test_repo_evidence_strategy_leaves_unclassified_preference_with_domain_owner() -> None:
    from agentic_workspace.workspace_runtime_proof import _apply_repo_evidence_strategy_to_lanes

    requirements = {
        "active": [
            {
                "id": "property_preference",
                "requirement_class": "guideline",
                "preference_target": "surface:host-classified-property-owner",
                "evidence_owner": "module:host-test-classifier",
            }
        ]
    }
    lanes, construction = _apply_repo_evidence_strategy_to_lanes(
        assurance_requirements=requirements,
        selected_lanes=[{"id": "ordinary-proof", "enough_proof": ["pytest -q"]}],
    )
    assert lanes == [{"id": "ordinary-proof", "enough_proof": ["pytest -q"]}]
    assert construction["status"] == "owner-decision-required"
    assert construction["owner_decisions"] == [
        {
            "requirement_id": "property_preference",
            "preference_target": "surface:host-classified-property-owner",
            "owner": "module:host-test-classifier",
            "reason": "no explicitly classified admissible evidence owner matched the advisory preference",
        }
    ]


def test_authorized_local_code_seam_reuses_ordinary_implementation_owner_and_proportionate_proof() -> None:
    candidate = _material_improvement_candidate(
        proposed_paths=["src/router.py"],
        ownership={
            "current_owner": True,
            "mutation_authority_admitted": True,
            "source_owner": "routing-owner",
            "owner_revision": "routing-owner:rev-7",
        },
        proof_boundary={
            "status": "local",
            "requirements": [{"command": "pytest tests/test_router.py -q", "owner": "routing-owner"}],
        },
        claim_effect="bounded routing seam only",
    )
    action = compile_repo_improvement_action(candidate=candidate, latitude="conservative")
    execution = compile_repo_improvement_execution(
        action=action,
        candidate=candidate,
        current_work={"requested_outcome": "Fix current routing behavior"},
    )

    Draft202012Validator(_schema("repo_improvement_execution.schema.json")).validate(execution)
    Draft202012Validator(_schema("operation_invocation.schema.json")).validate(execution["operation_invocation"])
    assert execution["status"] == "ready-for-ordinary-implementation"
    assert execution["route"] == "ordinary-implementation"
    assert execution["source_owner"] == "routing-owner"
    assert execution["mutation_scope"]["allowed_paths"] == ["src/router.py"]
    assert execution["operation_invocation"]["operation_id"] == "implement.context"
    assert execution["proof_requirements"] == [{"command": "pytest tests/test_router.py -q", "owner": "routing-owner"}]
    assert execution["claim_effect"] == "bounded routing seam only"
    assert execution["continuation"]["durability"] == "current-task"
    assert execution["parallel_workflow_created"] is False


def test_proactive_tooling_affordance_creates_bounded_resumable_planning_owner() -> None:
    candidate = _material_improvement_candidate(
        id="candidate-proof-selector-affordance",
        symptom="proof selector reruns unrelated checks",
        scope_relation="standalone-repo",
        proposed_paths=["src/proof_selector.py", "tests/test_proof_selector.py"],
        ownership={
            "current_owner": True,
            "mutation_authority_admitted": True,
            "source_owner": "proof-owner",
            "owner_revision": "proof-owner:rev-2",
        },
        proof_boundary={
            "status": "bounded",
            "requirements": [{"command": "pytest tests/test_proof_selector.py -q", "owner": "proof-owner"}],
        },
    )
    action = compile_repo_improvement_action(candidate=candidate, latitude="proactive")
    execution = compile_repo_improvement_execution(action=action, candidate=candidate)

    Draft202012Validator(_schema("repo_improvement_execution.schema.json")).validate(execution)
    Draft202012Validator(_schema("operation_invocation.schema.json")).validate(execution["operation_invocation"])
    assert action["action_class"] == "bounded-standalone-permitted"
    assert execution["status"] == "promotion-required"
    assert execution["route"] == "planning-new-plan"
    assert execution["operation_invocation"]["operation_id"] == "planning.new-plan.lifecycle"
    planning_source = execution["operation_invocation"]["arguments"]["source"]
    assert planning_source.startswith("repo-improvement:")
    assert json.loads(planning_source.removeprefix("repo-improvement:"))["candidate_id"] == candidate["id"]
    assert execution["operation_invocation"]["arguments"]["prep_only"] is True
    assert execution["operation_invocation"]["mutation_boundary"]["repo_mutation_authorized"] is False
    assert execution["continuation"]["durability"] == "checked-in-planning-owner"
    assert execution["continuation"]["resume_ref"].endswith("candidate-proof-selector-affordance.plan.json")


@pytest.mark.parametrize("surface_class", ["generated", "managed", "human-owned", "cross-owner", "high-risk"])
def test_guarded_improvement_surfaces_route_to_normal_owner_before_mutation(surface_class: str) -> None:
    candidate = _material_improvement_candidate(
        scope_relation="standalone-repo",
        surface_class=surface_class,
        ownership={
            "current_owner": True,
            "mutation_authority_admitted": True,
            "source_owner": "declared-surface-owner",
            "owner_revision": "owner:rev-1",
        },
        proof_boundary={"status": "bounded", "requirements": [{"evidence": "owner proof"}]},
    )
    action = compile_repo_improvement_action(candidate=candidate, latitude="proactive")
    execution = compile_repo_improvement_execution(action=action, candidate=candidate)

    assert execution["status"] == "owner-review-required"
    assert execution["route"] == "normal-surface-owner"
    assert execution["operation_invocation"] == {}
    assert execution["mutation_scope"]["writes_repo_state"] is False


def test_balanced_scope_or_authority_drift_promotes_before_mutation() -> None:
    candidate = _material_improvement_candidate(
        scope_relation="adjacent-scope",
        proposed_paths=["src/adjacent.py"],
        ownership={"current_owner": False, "mutation_authority_admitted": False, "source_owner": "adjacent-owner"},
        proof_boundary={"status": "missing"},
    )
    action = compile_repo_improvement_action(candidate=candidate, latitude="balanced")
    execution = compile_repo_improvement_execution(action=action, candidate=candidate)

    assert action["action_class"] == "promote-or-review"
    assert execution["status"] == "promotion-required"
    assert execution["operation_invocation"]["operation_id"] == "planning.new-plan.lifecycle"
    assert execution["operation_invocation"]["mutation_boundary"]["repo_mutation_authorized"] is False


def test_rejected_improvement_has_one_bounded_recovery_and_preserves_original_task() -> None:
    candidate = _material_improvement_candidate(
        added_costs=["cross-owner coupling"],
        future_cost_effect={"net_effect": "negative"},
    )
    action = compile_repo_improvement_action(candidate=candidate, latitude="proactive")
    execution = compile_repo_improvement_execution(action=action, candidate=candidate)

    assert action["action_class"] == "dismiss-or-redesign"
    assert execution["status"] == "disposition-only"
    assert execution["operation_invocation"] == {}
    assert execution["failure_boundary"]["original_task"] == "semantically intact"
    assert execution["failure_boundary"]["unrelated_repo_state"] == "must remain unchanged"
    assert "one owner disposition" in execution["failure_boundary"]["recovery"]


def test_local_improvement_dispatches_registered_implement_context_without_parallel_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_path = tmp_path / "src" / "router.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("ROUTE = 'current'\n", encoding="utf-8")
    candidate = _material_improvement_candidate(
        proposed_paths=["src/router.py"],
        ownership={
            "current_owner": True,
            "mutation_authority_admitted": True,
            "source_owner": "routing-owner",
            "owner_revision": "routing-owner:rev-7",
        },
        proof_boundary={
            "status": "local",
            "requirements": [{"command": "pytest tests/test_router.py -q", "owner": "routing-owner"}],
        },
        claim_effect="bounded routing seam only",
    )
    action = compile_repo_improvement_action(candidate=candidate, latitude="conservative")
    execution = compile_repo_improvement_execution(
        action=action,
        candidate=candidate,
        current_work={"requested_outcome": "Fix current routing behavior", "owner_revision": "routing-owner:rev-7"},
    )
    arguments = execution["operation_invocation"]["arguments"]

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                *arguments["changed"],
                "--task",
                arguments["task"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["decision_packet"]["working_set"]["changed_paths"] == ["src/router.py"]
    assert execution["operation_invocation"]["owner_context_revision"] == {
        "owner_id": "routing-owner",
        "owner_revision": "routing-owner:rev-7",
    }
    assert execution["proof_requirements"] == [{"command": "pytest tests/test_router.py -q", "owner": "routing-owner"}]
    assert execution["operation_invocation"]["preconditions"]["requested_ends_unchanged"] is True
    assert source_path.read_text(encoding="utf-8") == "ROUTE = 'current'\n"
    assert not list(tmp_path.rglob("*repo-improvement*"))


def test_standalone_improvement_dispatches_planning_owner_and_resumes_exact_continuation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    candidate = _material_improvement_candidate(
        id="candidate-proof-selector-affordance",
        evidence_fingerprint="sha256:evidence-7",
        evidence_refs=["session-observation:7", "review:#2651"],
        symptom="proof selector reruns unrelated checks",
        scope_relation="standalone-repo",
        proposed_paths=["src/proof_selector.py", "tests/test_proof_selector.py"],
        ownership={
            "current_owner": True,
            "mutation_authority_admitted": True,
            "source_owner": "proof-owner",
            "owner_revision": "proof-owner:rev-2",
        },
        proof_boundary={
            "status": "bounded",
            "requirements": [{"command": "pytest tests/test_proof_selector.py -q", "owner": "proof-owner"}],
        },
        claim_effect="bounded proof-selection improvement only",
    )
    action = compile_repo_improvement_action(candidate=candidate, latitude="proactive")
    execution = compile_repo_improvement_execution(action=action, candidate=candidate)
    arguments = execution["operation_invocation"]["arguments"]

    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                arguments["id"],
                "--title",
                arguments["title"],
                "--source",
                arguments["source"],
                "--target",
                str(tmp_path),
                "--prep-only",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    plan_path = tmp_path / execution["continuation"]["resume_ref"]
    resumed_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    persisted_source = resumed_plan["references"][0]["target"]
    resumed = json.loads(persisted_source.removeprefix("repo-improvement:"))

    assert resumed == {
        "action_input_revision": action["input_revision"],
        "allowed_paths": ["src/proof_selector.py", "tests/test_proof_selector.py"],
        "candidate_id": candidate["id"],
        "claim_effect": "bounded proof-selection improvement only",
        "evidence_fingerprint": "sha256:evidence-7",
        "evidence_refs": ["session-observation:7", "review:#2651"],
        "owner_revision": "proof-owner:rev-2",
        "proof_requirements": [{"command": "pytest tests/test_proof_selector.py -q", "owner": "proof-owner"}],
        "source_owner": "proof-owner",
    }
    assert execution["continuation"]["durability"] == "checked-in-planning-owner"


def test_improvement_execution_rejects_stale_owner_and_failed_plan_without_unrelated_mutation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    unrelated = tmp_path / "README.md"
    unrelated.write_text("unchanged\n", encoding="utf-8")
    candidate = _material_improvement_candidate(
        proposed_paths=["src/router.py"],
        ownership={
            "current_owner": True,
            "mutation_authority_admitted": True,
            "source_owner": "routing-owner",
            "owner_revision": "routing-owner:stale",
        },
        proof_boundary={"status": "local", "requirements": [{"evidence": "focused proof"}]},
    )
    action = compile_repo_improvement_action(candidate=candidate, latitude="balanced")
    stale = compile_repo_improvement_execution(action=action, candidate=candidate, current_work={"owner_revision": "routing-owner:current"})

    assert stale["status"] == "owner-revision-stale"
    assert stale["route"] == "refresh-owner-decision"
    assert stale["operation_invocation"] == {}
    assert unrelated.read_text(encoding="utf-8") == "unchanged\n"

    standalone = _material_improvement_candidate(
        id="duplicate-owner",
        scope_relation="standalone-repo",
        ownership={"source_owner": "proof-owner", "owner_revision": "proof-owner:rev-1"},
        proof_boundary={"status": "bounded", "requirements": [{"evidence": "focused proof"}]},
    )
    standalone_action = compile_repo_improvement_action(candidate=standalone, latitude="proactive")
    planned = compile_repo_improvement_execution(action=standalone_action, candidate=standalone)
    arguments = planned["operation_invocation"]["arguments"]
    command = [
        "planning",
        "new-plan",
        "--id",
        arguments["id"],
        "--title",
        arguments["title"],
        "--source",
        arguments["source"],
        "--target",
        str(tmp_path),
        "--prep-only",
        "--format",
        "json",
    ]
    assert cli.main(command) == 0
    capsys.readouterr()
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert cli.main(command) == 0
    failure = json.loads(capsys.readouterr().out)
    after = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    assert failure["reason_code"] == "target-already-exists"
    assert after == before
    assert "one owner disposition" in planned["failure_boundary"]["recovery"]


def test_improvement_execution_uses_only_registered_existing_operations() -> None:
    registry = json.loads(Path("src/agentic_workspace/contracts/operation_contracts.json").read_text(encoding="utf-8"))
    registered = {str(item["id"]) for item in registry["operations"]}

    assert {"implement.context", "planning.new-plan.lifecycle"}.issubset(registered)
    source = Path("src/agentic_workspace/operating_decision.py").read_text(encoding="utf-8")
    assert "repo-improvement.execute" not in source


def test_operating_decision_fails_closed_without_typed_invocation() -> None:
    decision = compile_operating_decision(
        inputs={
            "revisions": {"current_work": "rev-a"},
            "actionability": {"next_action": {"action": "retry", "command": "agentic-workspace proof --format json"}},
        }
    )

    Draft202012Validator(_schema("operating_decision.schema.json")).validate(decision)
    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"]["reason_code"] == "missing-authority"
    assert decision["external_blocker"]["owner"] == "operation-invocation"


def test_operating_decision_blocker_precedence_is_deterministic() -> None:
    invocation = operation_invocation(operation_id="proof.report", arguments={})

    decision = compile_operating_decision(
        inputs={
            "revisions": {"current_work": "rev-a"},
            "actionability": {"next_action": {"action": "run-proof", "operation_invocation": invocation}},
            "stale_proof": True,
            "stale_mutation_baseline": True,
            "conflict": True,
        }
    )

    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"]["reason_code"] == "conflicting-input"


def test_caller_supplied_invocation_revision_is_ignored() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        effect_class="read-only-report",
        authority_class="verification-owned",
        input_revision="old-input-digest",
        expected_transition="proof status refreshed",
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )

    assert invocation["expected_input_revision"] == invocation_decision_input_revision(invocation)
    assert invocation["expected_input_revision"] != "old-input-digest"
    assert invocation["stale_action_rejection"]["caller_supplied_input_revision"] == "old-input-digest"
    assert invocation["stale_action_rejection"]["caller_revision_authority"] == "ignored"


def test_live_authority_revision_drift_is_rejected_before_execution() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        effect_class="read-only-report",
        authority_class="verification-owned",
        expected_transition="proof status refreshed",
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )
    live_authorities = {
        "planning_owner": {"owner_id": "owner-a", "owner_revision": "rev-owner-b"},
        "assignment": {"assignment_revision": "assign-b", "target_identity_ref": "target-a"},
        "mutation_baseline": {"baseline_id": "baseline-b", "revalidation_status": "fresh"},
        "proof": {"proof_subject_fingerprint": "proof-b", "receipt_status": "fresh"},
        "evaluation": {"freshness_status": "not-required", "required": False},
        "executor": {"binding_fingerprint": "executor-b", "availability_status": "available"},
    }
    proposed_next_action = {"action": "run-proof", "operation_invocation": invocation}
    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action=proposed_next_action,
        current_input_revision=live_decision_input_revision(invocation=invocation, authorities=live_authorities),
    )

    decision = compile_operating_decision(
        inputs={
            "revisions": {"current_work": "rev-a", "proof": "rev-proof"},
            "actionability": actionability,
            "authorities": live_authorities,
        }
    )

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["live_revision_checked"] is True
    assert actionability["progress_check"]["live_input_revision"] == live_decision_input_revision(
        invocation=invocation, authorities=live_authorities
    )
    assert actionability["progress_check"]["live_input_revision"] != invocation["expected_input_revision"]
    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"]["reason_code"] == "stale-revision"
    assert "refresh the operating decision" in decision["external_blocker"]["repair"]


def test_actionability_rejects_typed_action_against_live_revision_drift() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"baseline_id": "baseline-a"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )

    proposed_next_action = {
        "action": "run-proof",
        "operation_invocation": invocation,
    }
    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action=proposed_next_action,
        current_input_revision="sha256:live-authority-changed",
    )

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["live_revision_checked"] is True
    assert actionability["progress_check"]["live_input_revision"] == "sha256:live-authority-changed"
    assert actionability["next_action"]["action"] == "required-action-unavailable"


def test_actionability_rejects_typed_action_when_live_revision_is_missing() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"baseline_id": "baseline-a"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )

    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action={"action": "run-proof", "operation_invocation": invocation},
    )

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["live_revision_checked"] is False
    assert actionability["progress_check"]["live_revision_missing"] is True
    assert actionability["next_action"]["missing_precondition"] == (
        "live authority revision resolved immediately before actionability derivation"
    )


def test_missing_expected_revision_is_rejected_before_execution() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )
    invocation.pop("expected_input_revision")
    proposed_next_action = {"action": "run-proof", "operation_invocation": invocation}
    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action=proposed_next_action,
        current_input_revision=proposed_action_input_revision(proposed_next_action),
    )

    decision = compile_operating_decision(inputs={"actionability": actionability})

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["expected_input_revision"] == ""
    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "stale-revision"


def test_context_authority_declarations_and_gap_classes_validate() -> None:
    declarations = context_authority_declarations()
    coverage = context_authority_coverage()
    registry_schema = _schema("context_authority_registry.schema.json")
    registry = json.loads(Path("src/agentic_workspace/contracts/context_authority_registry.json").read_text(encoding="utf-8"))
    Draft202012Validator(registry_schema).validate(registry)
    declaration_schema = _schema("context_authority_declaration.schema.json")
    for declaration in declarations:
        Draft202012Validator(declaration_schema).validate(declaration)

    assert "implement" in coverage["ordinary_consumers"]
    assert "autopilot-executor" in coverage["surfaces"]
    assert {"architecture-principles", "scoped-instructions", "ownership"}.issubset(set(coverage["surfaces"]))
    assert coverage["registry_authority"] == "versioned-contract"
    assert coverage["registry_source"] == "src/agentic_workspace/contracts/context_authority_registry.json"
    obligations = context_authority_obligations()
    assert obligations["status"] == "declared"
    assert len(obligations["obligations"]) == len(registry["surfaces"])
    planning_obligation = next(item for item in obligations["obligations"] if item["surface"] == "planning")
    assert planning_obligation["owner"] == "planning package"
    assert planning_obligation["currentness_operation_id"] == "planning.summary.report"
    assert {"action", "authority", "claim", "continuation", "proof"}.issubset(
        set(planning_obligation["coverage_responsibility"]["effects"])
    )
    assert set(obligations["representative_owner_classes"]) == {
        "planning",
        "scoped-instructions-config",
        "proof-verification",
        "modules-capabilities",
        "generated-projections",
        "review-external-context",
    }

    assert set(coverage["ordinary_consumers"]) == set(registry["ordinary_decision_consumers"])
    assert {"contract-checks", "skills"}.issubset(set(coverage["ordinary_consumers"]))
    assert coverage["missing_required_sources"] == {}
    for consumer in coverage["ordinary_consumers"]:
        assert set(coverage["consumer_requirements"][consumer]).issubset(set(coverage["consumer_to_surfaces"][consumer]))
    assert {"architecture-principles", "scoped-instructions", "ownership"}.issubset(set(coverage["consumer_requirements"]["start"]))
    assert all("source_owner_contract" in surface for surface in registry["surfaces"])
    gaps = derive_context_gaps(
        declarations=declarations,
        selected_surfaces=[
            {
                "surface": "memory",
                "admitted_state": context_surface_admission(
                    surface="memory",
                    source_kind="memory-route",
                    source_id="memory/repo/index.md",
                    source_revision="rev-memory",
                    authority_owner="memory package",
                    requirement_status="required",
                    population_status="missing",
                ),
                "affected_decisions": ["reuse"],
            },
            {
                "surface": "system-intent",
                "admitted_state": context_surface_admission(
                    surface="system-intent",
                    source_kind="system-intent",
                    source_id="intent.toml",
                    source_revision="rev-intent",
                    authority_owner="workspace-system-intent",
                    requirement_status="required",
                    population_status="below-minimum",
                ),
            },
            {
                "surface": "undiscovered-surface",
                "admitted_state": context_surface_admission(
                    surface="undiscovered-surface",
                    source_kind="test-fixture",
                    source_id="fixture",
                    source_revision="rev-undiscovered",
                    authority_owner="fixture",
                    requirement_status="required",
                    population_status="present",
                ),
            },
            {
                "surface": "proof",
                "admitted_state": context_surface_admission(
                    surface="proof",
                    source_kind="proof-resolver",
                    source_id="proof.report",
                    source_revision="rev-proof",
                    authority_owner="verification and proof runtime",
                    freshness_status="inference-fallback",
                ),
            },
        ],
    )

    gap_schema = _schema("context_gap.schema.json")
    for gap in gaps:
        Draft202012Validator(gap_schema).validate(gap)
    assert [gap["gap_class"] for gap in gaps] == [
        "configured-but-missing",
        "configured-but-unpopulated",
        "consumer-without-source",
        "inference-fallback",
    ]


def test_context_authority_changed_path_guardrail_maps_every_required_surface_once() -> None:
    from agentic_workspace.operating_decision import context_authority_changed_path_guardrail

    declarations = context_authority_declarations()
    selected = [{"surface": item["surface"]} for item in declarations if "start" in item["consumer"]]
    guardrail = context_authority_changed_path_guardrail(
        consumer="start",
        changed_paths=["src/agentic_workspace/runtime.py"],
        selected=selected,
        excluded=[],
    )

    expected = set(context_authority_coverage()["consumer_requirements"]["start"])
    mapped = [item["surface"] for item in guardrail["ownership"]]
    assert guardrail["status"] == "enforced"
    assert set(mapped) == expected
    assert len(mapped) == len(set(mapped))
    assert guardrail["missing_checker_surfaces"] == []
    assert set(guardrail["failure_matrix"]) == {
        "contradiction",
        "skill-registry-or-dependency-drift",
        "configured-empty",
        "stale-generated-projection",
        "wrong-source-edit",
        "renamed-canonical-source",
        "unrelated-path",
    }


def test_runtime_actionability_call_sites_resolve_live_revision_before_derivation() -> None:
    """Static guard for ordinary boundaries that would otherwise reuse stale typed actions."""

    production_sources = [
        path for path in Path("src/agentic_workspace").rglob("*.py") if path.name != "actionability.py" and "tests" not in path.parts
    ]
    call_sites: list[str] = []
    missing_live_revision: list[str] = []
    for path in production_sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if name != "derive_actionability":
                continue
            location = f"{path.as_posix()}:{node.lineno}"
            call_sites.append(location)
            if not any(keyword.arg == "current_input_revision" for keyword in node.keywords):
                missing_live_revision.append(location)

    assert call_sites
    assert missing_live_revision == []


def test_context_gap_derivation_rejects_caller_shaped_status_without_admitted_source() -> None:
    gaps = derive_context_gaps(
        declarations=context_authority_declarations(),
        selected_surfaces=[
            {
                "surface": "proof",
                "admitted_state": {
                    "requirement_status": "required",
                    "population_status": "missing",
                    "severity": "advisory",
                    "next_route": "caller-supplied route should not be trusted",
                },
            }
        ],
    )

    assert [gap["gap_class"] for gap in gaps] == ["coverage-gap"]
    assert gaps[0]["severity"] == "blocking"
    assert gaps[0]["owner"] == "context-authority-coverage"
    assert "canonical context-surface adapter" in gaps[0]["next_route"]


def test_context_authority_coverage_fails_when_required_consumer_source_is_missing() -> None:
    coverage = context_authority_coverage(
        declarations=[item for item in context_authority_declarations() if item["surface"] != "proof"],
        consumer_requirements={"proof": ["planning", "proof"]},
        observed_consumers=["proof"],
    )

    assert coverage["status"] == "coverage-gap"
    assert coverage["missing_required_sources"] == {"proof": ["proof"]}


def test_blocking_context_gap_prevents_primary_action() -> None:
    gaps = derive_context_gaps(
        declarations=context_authority_declarations(),
        selected_surfaces=[
            {
                "surface": "proof",
                "admitted_state": context_surface_admission(
                    surface="proof",
                    source_kind="proof-resolver",
                    source_id="proof.report",
                    source_revision="rev-proof",
                    authority_owner="verification and proof runtime",
                    requirement_status="required",
                    population_status="missing",
                ),
            }
        ],
    )
    decision = compile_operating_decision(
        inputs={
            "revisions": {"current_work": "rev-a"},
            "actionability": {
                "next_action": {"action": "run-proof", "operation_invocation": operation_invocation(operation_id="proof.report")}
            },
            "context_gaps": gaps,
        }
    )

    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "context-coverage-gap"
    assert decision["external_blocker"]["owner"] == "verification and proof runtime"
    assert decision["highest_impact_context_consequence"]["consequence"] == "block-now"


def test_context_findings_compile_to_one_stable_consequence_each() -> None:
    findings = [
        {
            "kind": "agentic-workspace/context-gap/v1",
            "id": "configured-but-unpopulated:memory",
            "gap_class": "configured-but-unpopulated",
            "severity": "material",
            "owner": "memory package",
            "next_route": "populate or disable the required Memory surface",
        },
        {
            "kind": "agentic-workspace/system-intent-finding/v1",
            "id": "intent-conflict:release-policy",
            "finding_class": "intent-conflict",
            "severity": "material",
            "owner": "maintainer",
            "next_route": "review conflicting intent evidence",
        },
        {
            "kind": "agentic-workspace/memory-freshness-finding/v1",
            "id": "stale-memory:runtime-boundary",
            "finding_class": "stale-memory",
            "severity": "material",
            "owner": "memory package",
            "safe_repair": {
                "operation_id": "memory.refresh-note",
                "expected_input_revision": "sha256:current",
                "idempotency_key": "memory.refresh-note:runtime-boundary",
            },
        },
        {
            "kind": "agentic-workspace/skill-finding/v1",
            "id": "missing-skill:review",
            "finding_class": "missing-skill-dependency",
            "severity": "material",
            "owner": "skill registry",
            "trigger": "before the next review task",
        },
        {
            "kind": "agentic-workspace/context-gap/v1",
            "id": "retired-gap",
            "gap_class": "coverage-gap",
            "severity": "blocking",
            "owner": "workspace",
            "lifecycle": "dismissed",
        },
        {
            "kind": "agentic-workspace/context-gap/v1",
            "id": "material-unrouted-gap",
            "gap_class": "coverage-gap",
            "severity": "material",
            "owner": "workspace",
        },
    ]

    first = derive_context_consequences(findings=findings, current_stage="implement")
    second = derive_context_consequences(findings=findings, current_stage="implement")

    assert first == second
    assert len(first) == len(findings)
    assert len({item["finding_id"] for item in first}) == len(findings)
    assert {item["consequence"] for item in first} == {
        "closeout-obligation",
        "route-durable-improvement",
        "require-review-now",
        "safe-typed-repair",
        "defer-with-owner",
        "terminal-disposition",
    }
    assert all(item["dedupe_key"] for item in first)
    assert next(item for item in first if item["finding_id"] == "retired-gap")["active"] is False


def test_context_consequences_enforce_review_narrowing_closeout_repair_and_durable_lifecycle() -> None:
    findings = [
        {
            "id": "review-conflict",
            "finding_class": "intent-conflict",
            "severity": "material",
            "owner": "maintainer",
            "next_route": "review intent",
        },
        {
            "id": "narrow-scope",
            "severity": "material",
            "owner": "planning",
            "current_task_effect": "narrow to docs-only",
        },
        {"id": "closeout-gap", "severity": "material", "owner": "verification"},
        {
            "id": "repairable-skill",
            "severity": "material",
            "owner": "skill registry",
            "safe_repair": {
                "operation_id": "workspace.skills.resolve-dependencies",
                "expected_input_revision": "sha256:current",
                "idempotency_key": "skills:current",
            },
        },
        {
            "id": "dogfooding-signal-not-checked",
            "severity": "material",
            "owner": "improvement intake",
            "next_route": "report --section dogfooding_signal_status",
            "trigger": "before broad closeout",
        },
    ]
    consequences = derive_context_consequences(findings=findings)
    effects = context_consequence_effects(consequences)

    assert effects["review_gate"] == {"status": "blocked-pending-review", "finding_refs": ["review-conflict"]}
    assert effects["action_narrowing"]["finding_refs"] == ["narrow-scope"]
    assert effects["blocked_claim_classes"] == [
        "unreviewed-context-change",
        "claims-outside-context-boundary",
        "full-intent-complete",
        "issue-closure",
    ]
    assert effects["closeout_obligations"][0]["finding_ref"] == "closeout-gap"
    assert effects["typed_repairs"][0]["operation_invocation"]["operation_id"] == "workspace.skills.resolve-dependencies"
    assert effects["durable_dispositions"] == [
        {
            "finding_ref": "dogfooding-signal-not-checked",
            "owner": "improvement intake",
            "route": "report --section dogfooding_signal_status",
            "reentry_trigger": "before broad closeout",
            "status": "deferred-with-owner",
            "dedupe_key": "dogfooding-signal-not-checked:implement:defer-with-owner",
        }
    ]

    repeated = context_consequence_effects(derive_context_consequences(findings=findings))
    assert repeated == effects

    terminal = context_consequence_effects(derive_context_consequences(findings=[{**findings[-1], "lifecycle": "resolved"}]))
    assert terminal["status"] == "quiet"
    assert terminal["durable_dispositions"] == []


def test_operating_decision_applies_context_review_and_claim_gates() -> None:
    decision = compile_operating_decision(
        inputs={
            "context_findings": [
                {
                    "id": "review-conflict",
                    "finding_class": "intent-conflict",
                    "severity": "material",
                    "owner": "maintainer",
                    "next_route": "review intent",
                },
                {"id": "closeout-gap", "severity": "material", "owner": "verification"},
            ]
        }
    )

    assert decision["status"] == "blocked"
    assert decision["external_blocker"] == {
        "kind": "agentic-workspace/operating-decision-blocker/v1",
        "reason_code": "conflicting-input",
        "owner": "maintainer",
        "repair": "review intent",
    }
    assert decision["blocked_claim_classes"] == [
        "unreviewed-context-change",
        "full-intent-complete",
        "issue-closure",
    ]


@pytest.mark.parametrize(
    ("case_id", "authorities", "blocker"),
    [
        (
            "unknown-no-safe-target",
            {"target": {"status": "unknown"}},
            {"reason_code": "missing-capability", "owner": "assignment target", "repair": "select a safe target"},
        ),
        (
            "disabled-manual-required-transport",
            {
                "assignment": {"status": "handoff-required", "handoff_admission_status": "admitted"},
                "manual_transport": {"status": "disabled"},
            },
            {},
        ),
        (
            "stale-worktree-baseline",
            {"mutation_baseline": {"revalidation_status": "rejected"}},
            {"reason_code": "stale-mutation-baseline", "owner": "mutation authority", "repair": "refresh baseline"},
        ),
        (
            "missing-evaluation",
            {"evaluation": {"freshness_status": "missing", "required": True}},
            {"reason_code": "context-coverage-gap", "owner": "evaluation", "repair": "register evaluation"},
        ),
        (
            "not-required-evaluation",
            {"evaluation": {"freshness_status": "not-required", "required": False}},
            {},
        ),
        (
            "superseded-evaluation",
            {"evaluation": {"freshness_status": "superseded"}},
            {"reason_code": "stale-revision", "owner": "evaluation", "repair": "rerun evaluation"},
        ),
        (
            "stale-planning-owner",
            {"planning_owner": {"freshness_status": "stale"}},
            {"reason_code": "stale-revision", "owner": "planning owner", "repair": "reselect owner"},
        ),
        (
            "invalid-receipt",
            {"proof": {"receipt_status": "invalid"}},
            {"reason_code": "stale-proof", "owner": "proof receipt", "repair": "rerun proof"},
        ),
        (
            "unavailable-rebound-executor",
            {"executor": {"availability": {"status": "unavailable"}}},
            {"reason_code": "missing-capability", "owner": "autopilot executor", "repair": "rebind executor"},
        ),
    ],
)
def test_operating_decision_context_gap_recovery_matrix_blocks_invalid_actions(
    case_id: str, authorities: dict, blocker: dict[str, str]
) -> None:
    invocation = operation_invocation(
        operation_id="implement",
        arguments={"target": ".", "task": case_id},
        effect_class="repo-mutation",
        authority_class="hard-gate",
        expected_transition="valid terminal recovery",
        preconditions={"case": case_id},
        owner_context_revision={"case": case_id, "owner_id": "owner-a"},
        mutation_boundary={"case": case_id, "writes_repo_state": True},
        proof_requirements=[{"command": "make typecheck", "case": case_id}],
    )

    decision = compile_operating_decision(
        inputs={
            "revisions": {"case": case_id, "owner": "rev-a"},
            "actionability": {"next_action": {"action": "recover-context-gap", "operation_invocation": invocation}},
            "authorities": authorities,
        }
    )

    expected_blockers = [] if not blocker else [blocker]
    assert derive_operating_blockers_from_authorities(authorities=authorities) == expected_blockers
    if blocker:
        assert decision["status"] == "blocked"
        assert decision["primary_action"] == {}
        assert decision["external_blocker"]["reason_code"] == blocker["reason_code"]
        assert decision["external_blocker"]["owner"] == blocker["owner"]
        assert decision["external_blocker"]["repair"] == blocker["repair"]
    else:
        assert decision["status"] == "blocked"
        assert decision["external_blocker"]["reason_code"] == "stale-revision"


def test_admitted_handoff_and_not_required_evaluation_can_reach_actionable_terminal_recovery() -> None:
    authorities = {
        "planning_owner": {"owner_id": "owner-a", "owner_revision": "rev-owner-a"},
        "assignment": {
            "status": "handoff-required",
            "handoff_admission_status": "admitted",
            "assignment_revision": "assign-a",
            "target_identity_ref": "target-a",
        },
        "manual_transport": {"status": "disabled", "handoff_admission_status": "admitted"},
        "mutation_baseline": _live_mutation_baseline(),
        "proof": {"proof_subject_fingerprint": "proof-a", "receipt_status": "fresh"},
        "evaluation": {"freshness_status": "not-required", "required": False},
        "executor": {"binding_fingerprint": "executor-a", "availability_status": "available"},
    }
    invocation = operation_invocation(
        operation_id="handoff.prepare",
        arguments={"target": ".", "format": "json"},
        effect_class="manual-handoff",
        authority_class="assignment-gate",
        expected_transition="handoff prepared",
    )
    bound_invocation = bind_operation_invocation_to_authorities(invocation=invocation, authorities=authorities)

    decision = compile_operating_decision(
        inputs={
            "actionability": {"next_action": {"action": "prepare-handoff", "operation_invocation": bound_invocation}},
            "authorities": authorities,
        }
    )

    assert derive_operating_blockers_from_authorities(authorities=authorities) == []
    assert decision["status"] == "actionable"
    assert decision["primary_action"]["operation_invocation"]["operation_id"] == "handoff.prepare"
    assert decision["canonical_decision_input_revision"] == bound_invocation["expected_input_revision"]


def test_repo_mutation_action_requires_live_mutation_baseline() -> None:
    invocation = operation_invocation(
        operation_id="implement.apply",
        arguments={"target": ".", "changed": ["src/app.py"]},
        effect_class="repo-mutation",
        authority_class="mutation-gate",
        mutation_boundary={"writes_repo_state": True, "allowed_paths": ["src/app.py"]},
    )

    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "actionability": {"next_action": {"action": "implement", "operation_invocation": invocation}},
            "authorities": {},
        }
    )

    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"]["reason_code"] == "stale-mutation-baseline"
    assert decision["external_blocker"]["repair"] == "resolve and revalidate a live mutation baseline before admitting this typed action"


def test_bound_repo_mutation_preserves_typed_action_identity() -> None:
    authorities = {"mutation_baseline": _live_mutation_baseline()}
    invocation = operation_invocation(
        operation_id="implement.apply",
        arguments={"target": ".", "changed": ["src/app.py"]},
        effect_class="repo-mutation",
        authority_class="mutation-gate",
        mutation_boundary={"writes_repo_state": True, "allowed_paths": ["src/app.py"]},
    )
    bound = bind_operation_invocation_to_authorities(invocation=invocation, authorities=authorities)

    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "actionability": {"next_action": {"action": "rendered text is not identity", "operation_invocation": bound}},
            "authorities": authorities,
        }
    )

    assert decision["status"] == "actionable"
    assert decision["primary_action"]["action"] == "rendered text is not identity"
    assert decision["action_identity"]["operation_invocation"]["operation_id"] == "implement.apply"
    assert decision["action_identity"]["requested_mutation_boundary"]["allowed_paths"] == ["src/app.py"]
    assert decision["action_identity"]["expected_input_revision"] == bound["expected_input_revision"]


def test_repo_mutation_rejects_planning_derived_placeholder_baseline() -> None:
    authorities = {
        "mutation_baseline": {
            "kind": "agentic-planning/mutation-baseline/v1",
            "status": "current",
            "baseline_id": "planning-revision-a",
            "source": "planning-revision-and-changed-paths",
            "changed_path_count": 1,
        }
    }
    invocation = operation_invocation(
        operation_id="implement.apply",
        arguments={"target": ".", "changed": ["src/app.py"]},
        effect_class="repo-mutation",
        authority_class="mutation-gate",
        mutation_boundary={"writes_repo_state": True, "allowed_paths": ["src/app.py"]},
    )
    bound = bind_operation_invocation_to_authorities(invocation=invocation, authorities=authorities)

    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "actionability": {"next_action": {"action": "implement", "operation_invocation": bound}},
            "authorities": authorities,
        }
    )

    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "stale-mutation-baseline"


def test_context_authority_projection_requires_live_records_for_start() -> None:
    projection = resolve_context_authority_projection(consumer="start", task="shape authority routing ownership skill guidance memory")

    assert projection["status"] == "repair-required"
    assert projection["registry_revision"].startswith("sha256:")
    assert set(projection["missing_required_surfaces"]) >= {
        "architecture-principles",
        "scoped-instructions",
        "ownership",
        "planning",
        "skills",
        "target-guidance",
    }
    repair = projection["repair_operation"]
    assert repair["status"] == "not-required"
    assert repair["blocked_claims"] == ["mutation", "proof-claim", "completion-claim"]
    planning = next(item for item in projection["currentness"]["decision_requirements"] if item["surface"] == "planning")
    assert planning["state"] == "missing-relevant-coverage"
    assert planning["disposition"] == "missing-relevant-coverage"
    assert planning["operation_id"] == ""


def test_context_currentness_never_repairs_semantic_ambiguity() -> None:
    from agentic_workspace.operating_decision import CONTEXT_AUTHORITY_REGISTRY

    planning = next(item for item in CONTEXT_AUTHORITY_REGISTRY if item["surface"] == "planning")
    currentness = classify_context_currentness(
        item=planning,
        record={
            "status": "stale",
            "applicable": True,
            "selected_required": True,
            "reason": "semantic-ambiguity",
        },
        owner_identity_valid=False,
    )

    assert currentness["state"] == "derivably-stale"
    assert currentness["disposition"] == "decision-required"
    assert currentness["operation_id"] == ""


def test_operating_decision_blocks_action_when_required_context_is_unadmitted() -> None:
    invocation = operation_invocation(operation_id="proof.report", arguments={})

    decision = compile_operating_decision(
        inputs={
            "consumer": "start",
            "task": "prove the context gate",
            "actionability": {"next_action": {"action": "run-proof", "operation_invocation": invocation}},
        }
    )

    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"]["reason_code"] == "context-coverage-gap"
    assert decision["external_blocker"]["owner"] != ""
    assert "source owner" in decision["external_blocker"]["repair"]


def _write_context_authority_sources(root: Path) -> None:
    (root / ".agentic-workspace/planning/execplans").mkdir(parents=True)
    (root / ".agentic-workspace/memory/repo").mkdir(parents=True)
    (root / ".agentic-workspace/skills/workspace-startup").mkdir(parents=True)
    (root / ".agentic-workspace/verification").mkdir(parents=True)
    (root / "src/agentic_workspace").mkdir(parents=True)
    (root / ".agentic-workspace").mkdir(exist_ok=True)
    (root / "SYSTEM_INTENT.md").write_text(
        "# System Intent\n\n## Purpose\n\nRuntime contract.\n\n## Governing intents\n\nGenerated runtime contract shape.\n",
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text(
        "Authority marker:\n\n<!-- agentic-workspace:workflow:start -->\nOrdinary route:\n<!-- agentic-workspace:workflow:end -->\n",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/config.toml").write_text(
        """
schema_version = 1

[modules]
enabled = ["planning", "memory", "verification"]

[workspace]
cli_invoke = "agentic-workspace"
""",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/OWNERSHIP.toml").write_text(
        """
schema_version = 1

[[managed_surfaces]]
module = "workspace"
path = ".agentic-workspace/OWNERSHIP.toml"

[[authority_surfaces]]
concern = "startup-instructions"
""",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/planning/state.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (root / ".agentic-workspace/planning/execplans/README.md").write_text("# Execplans\n", encoding="utf-8")
    (root / ".agentic-workspace/memory/repo/index.md").write_text("# Memory\n", encoding="utf-8")
    (root / ".agentic-workspace/memory/repo/manifest.toml").write_text(
        """
[[routes]]
id = "default"
routes_from = ["src/**"]

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
task_relevance = "required"
routes_from = ["src/**", ".agentic-workspace/memory/repo/**"]
routing_only = true
""",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/skills/workspace-startup/SKILL.md").write_text("# Startup\n", encoding="utf-8")
    (root / ".agentic-workspace/verification/manifest.toml").write_text(
        """
schema_version = 1

[[scenarios]]
id = "focused-proof"
command = "pytest tests/test_operating_decision.py"
""",
        encoding="utf-8",
    )
    (root / "src/agentic_workspace/evaluation.py").write_text(
        "def evaluation_collection_match():\n    return True\n\ndef record_evaluation_report_delivery_operation():\n    return None\n",
        encoding="utf-8",
    )
    (root / "src/agentic_workspace/workspace_runtime_primitives.py").write_text(
        "def delegated_worker_kernel():\n    return None\n\n"
        "def assignment_lifecycle():\n    return None\n\n"
        "def final_response():\n    return None\n\n"
        "terminal = object()\n",
        encoding="utf-8",
    )


def test_operating_decision_projects_selected_skill_reference_without_procedure_body(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    decision = compile_operating_decision(
        inputs={"consumer": "implement", "task": "review the routed skill procedure", "target_root": str(tmp_path)}
    )

    guidance = decision["source_guidance"]
    skill = next(item for item in guidance["contributions"] if item["surface"] == "skills")
    assert guidance["status"] == "projected"
    assert skill["decision_dimension"] == "governing-procedure"
    assert skill["source_ref"] == ".agentic-workspace/skills/workspace-startup/SKILL.md"
    assert skill["source_revision"].startswith("sha256:")
    assert skill["full_body_loaded"] is False
    assert decision["input_revisions"]["source_guidance_revision"] == guidance["revision"]


def test_operating_decision_omits_unselected_skill_guidance(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    decision = compile_operating_decision(inputs={"consumer": "implement", "task": "rename a local variable", "target_root": str(tmp_path)})

    assert decision["source_guidance"]["status"] == "not-applicable"
    assert decision["source_guidance"]["contributions"] == []
    assert "source_guidance_revision" not in decision["input_revisions"]


def test_operating_decision_projects_selected_architecture_guidance_from_owner_output(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    decision = compile_operating_decision(
        inputs={"consumer": "implement", "task": "follow the generated runtime contract architecture", "target_root": str(tmp_path)}
    )

    guidance = decision["source_guidance"]
    architecture = next(item for item in guidance["contributions"] if item["surface"] == "architecture-principles")
    assert guidance["status"] == "projected"
    assert architecture["decision_dimension"] == "durable-design-guidance"
    assert architecture["authority_class"] == "canonical"
    assert architecture["source_ref"] == "SYSTEM_INTENT.md"
    assert architecture["source_revision"].startswith("sha256:")
    assert architecture["full_body_loaded"] is False


def test_operating_decision_projects_memory_through_exactly_one_advisory_channel(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    contribution = {
        "kind": "agentic-memory/decision-contribution/v1",
        "status": "projected",
        "fact_id": "selected-owner-trap",
        "fact_revision": "sha256:" + "1" * 64,
        "source_revision": "sha256:" + "2" * 64,
        "freshness": "current",
        "owner": "memory",
        "authority_class": "advisory",
        "affected_decisions": ["planning-task-relation"],
        "guidance": "Check the structured Planning relation before proceeding.",
        "authority_boundary": "Planning owns relation correctness.",
    }
    decision = compile_operating_decision(
        inputs={
            "consumer": "implement",
            "task": "avoid the recorded memory rediscovery trap",
            "target_root": str(tmp_path),
            "memory_contributions": [contribution],
        }
    )

    projected = decision["memory_effectiveness"]["projected_contributions"]
    assert len(projected) == 1
    assert projected[0]["fact_id"] == "selected-owner-trap"
    assert projected[0]["authority_class"] == "advisory"
    assert not any(item["surface"] == "memory" for item in decision["source_guidance"]["contributions"])


def test_context_authority_projection_selects_repository_sources_and_ignores_forged_records(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    forged_records = {
        item["surface"]: {
            "status": "current",
            "source_id": "forged/source",
            "revision": "sha256:forged",
            "freshness": "current",
            "admission": {
                "registry_revision": "sha256:forged",
                "surface": item["surface"],
                "owner": item["owner"],
            },
        }
        for item in context_authority_declarations()
        if "start" in item["consumer"]
    }
    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
        source_records=forged_records,
    )

    assert projection["status"] == "admitted"
    assert projection["repair_operation"]["status"] == "not-required"
    skills = next(item for item in projection["authorities"] if item["surface"] == "skills")
    assert skills["source"]["id"] == ".agentic-workspace/skills/workspace-startup/SKILL.md"
    assert skills["source"]["revision"].startswith("sha256:")
    assert skills["source"]["admission"]["producer"] == "skill-registry-source-adapter"
    assert skills["source"]["admission"]["owner_admission"]["producer"] == (
        "agentic_workspace.workspace_runtime_core.skill_dependency_resolver"
    )
    assert skills["source"]["admission"]["owner_admission"]["result_kind"] == "agentic-workspace/skill-dependency-closure/v1"
    assert skills["source"]["source_adapter"] == "skill-registry-source-adapter"
    assert skills["source"]["freshness_enforcement"]["status"] == "active"
    assert skills["caller_record_status"] == "ignored"
    assert projection["excluded_authorities"] == [
        {
            "surface": "proof",
            "reason": "not-selected-by-task-or-path",
            "selected_required": False,
            "caller_record_status": "ignored",
        }
    ]


def test_context_authority_projection_curates_memory_from_manifest_routes(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/memory/repo/domains").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agentic-workspace/memory/repo/domains/runtime.md").write_text("Runtime note\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/memory/repo/manifest.toml").write_text(
        """
[[routes]]
id = "legacy-shape"
routes_from = ["ignored/**"]

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
task_relevance = "required"
routes_from = [".agentic-workspace/memory/repo/**/*.md"]
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/runtime.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/runtime.md"
authority = "advisory"
task_relevance = "conditional"
subsystems = ["workspace-runtime"]
surfaces = ["runtime"]
routes_from = ["src/agentic_workspace/**"]
stale_when = ["docs/runtime-source.md"]

[notes.".agentic-workspace/memory/repo/domains/unrelated.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/unrelated.md"
authority = "advisory"
task_relevance = "conditional"
subsystems = ["other"]
surfaces = ["other"]
routes_from = ["docs/private/**"]

[notes.".agentic-workspace/memory/repo/domains/review-only.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/review-only.md"
authority = "advisory"
task_relevance = "review-only"
subsystems = ["workspace-runtime"]
surfaces = ["runtime"]
routes_from = ["src/agentic_workspace/**"]
""",
        encoding="utf-8",
    )

    projection = resolve_context_authority_projection(
        consumer="start",
        task="fix runtime context",
        changed_paths=["src/agentic_workspace/workspace_runtime.py"],
        target_root=tmp_path,
    )

    memory = next(item for item in projection["authorities"] if item["surface"] == "memory")
    curation = memory["source"]["selection"]["memory_curation"]
    selected_paths = [item["path"] for item in curation["selected_notes"]]
    assert curation["status"] == "selected"
    assert ".agentic-workspace/memory/repo/index.md" in selected_paths
    assert ".agentic-workspace/memory/repo/domains/runtime.md" in selected_paths
    assert ".agentic-workspace/memory/repo/domains/unrelated.md" not in selected_paths
    assert ".agentic-workspace/memory/repo/domains/review-only.md" not in selected_paths
    assert curation["review_only_excluded_count"] == 1
    assert curation["context_budget"] == {"max_selected_notes": 12, "actual_selected_notes": 2}
    runtime_note = next(item for item in curation["selected_notes"] if item["path"].endswith("runtime.md"))
    assert runtime_note["stale_when_matched_paths"] == []
    owner_result = memory["source"]["admission"]["owner_result"]
    assert owner_result["kind"] == "agentic-workspace/memory-route-curation/v1"
    assert owner_result["producer"] == "agentic_memory.manifest"
    assert owner_result["status"] == "current"


def test_context_authority_projection_consumes_semantic_route_without_task_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/memory/repo/domains").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agentic-workspace/memory/repo/domains/issue-procedure.md").write_text("Issue procedure\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/memory/repo/manifest.toml").write_text(
        """
[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
task_relevance = "required"
routes_from = [".agentic-workspace/memory/repo/**/*.md"]
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/issue-procedure.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/issue-procedure.md"
authority = "advisory"
task_relevance = "conditional"
surfaces = ["generic"]
semantic_routes = ["github/issues/**"]
routes_from = []
""",
        encoding="utf-8",
    )
    route_fact = {
        "kind": "agentic-workspace/semantic-task-route-fact/v1",
        "status": "current",
        "posture": "selected",
        "routes": ["github/issues/create"],
        "current_work_id": "work-1",
        "source_revision": "sha256:" + "1" * 64,
        "authority_effect": "applicability-only",
    }
    monkeypatch.setattr("agentic_workspace.semantic_task_routes.current_semantic_task_route_fact", lambda _root: route_fact)

    projection = resolve_context_authority_projection(
        consumer="start", task="curate memory before the next external write", changed_paths=[], target_root=tmp_path
    )

    memory = next(item for item in projection["authorities"] if item["surface"] == "memory")
    curation = memory["source"]["selection"]["memory_curation"]
    routed = next(item for item in curation["selected_notes"] if item["path"].endswith("issue-procedure.md"))
    assert routed["matched_semantic_routes"] == ["github/issues/**"]
    assert routed["relevance_evidence"] == "semantic-task-route"
    assert curation["semantic_task_routes"]["authority_effect"] == "relevance-only"

    route_fact.update({"posture": "selected", "routes": ["workspace/ownership/audit"]})
    unrelated = resolve_context_authority_projection(
        consumer="start", task="curate memory where generic issue words still overlap", changed_paths=[], target_root=tmp_path
    )
    unrelated_memory = next(item for item in unrelated["authorities"] if item["surface"] == "memory")
    assert not any(
        item["path"].endswith("issue-procedure.md") for item in unrelated_memory["source"]["selection"]["memory_curation"]["selected_notes"]
    )


def test_repo_pr_review_route_surfaces_existing_recurring_failures_memory() -> None:
    root = Path(__file__).resolve().parents[1]
    route_fact = {
        "kind": "agentic-workspace/semantic-task-route-fact/v1",
        "status": "current",
        "posture": "selected",
        "routes": ["github/pr/review"],
        "current_work_id": "pr-review-fixture",
        "source_revision": "sha256:" + "1" * 64,
        "authority_effect": "applicability-only",
    }
    from repo_memory_bootstrap.context_authority_owner import _curate

    selected = _curate(root, task="neutral task wording", paths=[], semantic_route_fact=route_fact)["selected_notes"]
    anti_trap = next(item for item in selected if item["path"].endswith("mistakes/recurring-failures.md"))
    assert anti_trap["matched_semantic_routes"] == ["github/pr/review"]
    assert anti_trap["relevance_evidence"] == "semantic-task-route"
    assert (
        _curate(root, task="neutral task wording", paths=[], semantic_route_fact=route_fact)["semantic_task_routes"]["authority_effect"]
        == "relevance-only"
    )


def test_context_authority_projection_rejects_stale_memory_note_matches(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/memory/repo/domains").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agentic-workspace/memory/repo/domains/runtime.md").write_text("Runtime note\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/memory/repo/manifest.toml").write_text(
        """
[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
task_relevance = "required"
routes_from = [".agentic-workspace/memory/repo/**/*.md"]
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/runtime.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/runtime.md"
authority = "advisory"
task_relevance = "conditional"
subsystems = ["workspace-runtime"]
surfaces = ["runtime"]
routes_from = ["src/agentic_workspace/**"]
stale_when = ["src/agentic_workspace/**"]
""",
        encoding="utf-8",
    )

    projection = resolve_context_authority_projection(
        consumer="start",
        task="fix runtime context",
        changed_paths=["src/agentic_workspace/workspace_runtime.py"],
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    memory = next(item for item in projection["excluded_authorities"] if item["surface"] == "memory")
    assert memory["reason"] == "memory-curation-stale-review-required"
    currentness = next(item for item in projection["currentness"]["dispositions"] if item["surface"] == "memory")
    assert currentness["state"] == "derivably-stale"
    assert currentness["disposition"] == "decision-required"
    assert projection["repair_operation"]["status"] == "not-required"


def test_generated_projection_drift_fails_closed_without_dispatch_contract() -> None:
    from agentic_workspace.operating_decision import CONTEXT_AUTHORITY_REGISTRY

    generated = next(item for item in CONTEXT_AUTHORITY_REGISTRY if item["surface"] == "generated-references")
    currentness = classify_context_currentness(
        item=generated,
        record={
            "status": "stale",
            "applicable": True,
            "selected_required": True,
            "reason": "source-fingerprint-mismatch",
            "revision": "sha256:generated-source-r1",
        },
        owner_identity_valid=False,
    )

    assert currentness["state"] == "derivably-stale"
    assert currentness["disposition"] == "decision-required"
    assert currentness["operation_id"] == ""
    assert currentness["transition_mode"] == "unavailable"
    assert currentness["expected_registry_revision"].startswith("sha256:")
    assert currentness["expected_source_revision"] == "sha256:generated-source-r1"


def _refreshable_context_projection(
    *,
    surface: str = "planning",
    owner: str = "planning package",
    operation_id: str = "planning.summary.report",
) -> dict[str, object]:
    from agentic_workspace.operating_decision import _context_reconciliation_invocation

    currentness = {"operation_id": operation_id, "expected_source_revision": "sha256:source-r1"}
    invocation = _context_reconciliation_invocation(
        currentness=currentness,
        consumer="implement",
        task="refresh selected context",
        paths=["src/app.py"],
    )
    return {
        "kind": "agentic-workspace/context-authority-projection/v1",
        "status": "repair-required",
        "repair_operation": {"repairs": []},
        "refresh_operation": {
            "refreshes": [
                {
                    "surface": surface,
                    "owner": owner,
                    "reason_code": "source-revision-changed",
                    **invocation,
                }
            ]
        },
        "currentness": {"decision_requirements": []},
    }


def test_context_refresh_uses_contract_derived_read_only_typed_action() -> None:
    action = context_authority_repair_action(_refreshable_context_projection())

    invocation = action["operation_invocation"]
    assert action["action"] == "refresh-context-authority"
    assert invocation["operation_id"] == "planning.summary.report"
    assert invocation["preconditions"] == {"surface": "planning"}
    assert invocation["mutation_boundary"]["owner_operation_only"] is True
    assert invocation["mutation_boundary"]["writes_repo_state"] is False


@pytest.mark.parametrize(
    ("surface", "owner", "operation_id", "action_available"),
    [
        ("generated-references", "generated command package owner", "generated-command-packages.refresh", False),
        ("planning", "planning package", "planning.summary.report", True),
        ("proof", "verification and proof runtime", "verification.report.report", True),
        ("assignment", "workspace assignment gate", "assignment.resolve-target", False),
        ("memory", "memory package", "memory.route.report", True),
    ],
)
def test_independent_owner_classes_dispatch_or_fail_closed_by_contract(
    surface: str, owner: str, operation_id: str, action_available: bool
) -> None:
    projection = _refreshable_context_projection(surface=surface, owner=owner, operation_id=operation_id)
    action = context_authority_repair_action(projection)

    if not action_available:
        assert action == {}
        return
    assert action["surface"] == surface
    assert action["owner"] == owner
    assert action["operation_invocation"]["operation_id"] == operation_id
    assert action["operation_invocation"]["mutation_boundary"]["writes_repo_state"] is False
    assert action["quiet_after"].endswith("emits no repeated action")


def test_operating_decision_routes_read_only_context_refresh_without_mutation_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentic_workspace import operating_decision

    monkeypatch.setattr(operating_decision, "resolve_context_authority_projection", lambda **_kwargs: _refreshable_context_projection())
    live_authorities = {"mutation_baseline": _live_mutation_baseline()}

    actionable = compile_operating_decision(inputs={"consumer": "implement", "authorities": live_authorities})
    rejected = compile_operating_decision(
        inputs={"consumer": "implement", "authorities": {"mutation_baseline": {"revalidation_status": "rejected"}}}
    )

    assert actionable["status"] == "actionable"
    assert actionable["primary_action"]["operation_invocation"]["operation_id"] == "planning.summary.report"
    assert actionable["external_blocker"] == {}
    assert rejected["status"] == "actionable"
    assert rejected["primary_action"]["operation_invocation"]["requested_mutation_boundary"]["writes_repo_state"] is False
    assert rejected["external_blocker"] == {}


def _semantic_currentness_projection() -> dict[str, object]:
    return {
        "kind": "agentic-workspace/context-authority-projection/v1",
        "status": "repair-required",
        "repair_operation": {"repairs": []},
        "currentness": {
            "decision_requirements": [
                {
                    "surface": "scoped-instructions",
                    "owner": "scoped instruction owner",
                    "operation_id": "instructions.create",
                    "disposition": "decision-required",
                    "reason_code": "semantic-ambiguity",
                    "observed_change": "A moved API path may establish a new policy boundary.",
                    "why_semantic": "The move can mean either a rename or a distinct ownership boundary.",
                    "evidence_refs": ["src/api_v2/router.py", "review:ownership-question"],
                    "affected_effects": ["authority", "procedure"],
                    "expected_registry_revision": "sha256:registry-r1",
                    "expected_source_revision": "sha256:instruction-r1",
                    "proposed_delta": {
                        "action": "append_guidance",
                        "heading": "API v2 boundary",
                        "guidance": "Treat api_v2 as a distinct boundary.",
                        "positive_paths": ["src/api_v2/**"],
                        "negative_paths": ["docs/**"],
                    },
                }
            ]
        },
    }


def test_negative_drift_and_positive_coverage_reach_same_compact_decision_boundary() -> None:
    negative = compile_context_maintenance_decision(
        context_projection=_semantic_currentness_projection(),
        bounded_adaptations={"candidates": []},
    )
    positive = compile_operating_decision(
        inputs={"consumer": "unregistered-test-consumer", "coverage_observations": [_coverage_observation()]}
    )["maintenance_decision"]

    assert negative["kind"] == positive["kind"] == "agentic-workspace/context-maintenance-decision/v1"
    assert negative["case_kind"] == "negative-drift"
    assert positive["case_kind"] == "positive-coverage"
    assert negative["first_line"]["detail_selector"] == "maintenance_decision.detail"
    assert "evidence_refs" not in negative["first_line"]
    assert {item["id"] for item in negative["alternatives"]} == {"admit", "update", "retain", "dismiss"}
    assert all(item["apply_operation"]["operation_id"] == "instructions.create" for item in negative["alternatives"])
    assert all(item["apply_operation"]["preconditions"]["source_revision"] == "sha256:instruction-r1" for item in negative["alternatives"])


def test_semantic_maintenance_surfaces_as_ordinary_agent_action(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import operating_decision

    monkeypatch.setattr(operating_decision, "resolve_context_authority_projection", lambda **_kwargs: _semantic_currentness_projection())

    decision = compile_operating_decision(inputs={"consumer": "implement"})

    assert decision["status"] == "blocked"
    assert decision["primary_action"]["action"] == "request-context-maintenance-decision"
    assert decision["primary_action"]["human_decision"]["choice_ids"] == ["admit", "update", "retain", "dismiss"]
    assert decision["primary_action"]["detail_selector"] == "maintenance_decision"
    assert decision["external_blocker"]["reason_code"] == "conflicting-input"


def test_deterministic_repair_bypasses_human_decision_and_consequential_observation_cannot() -> None:
    deterministic = compile_context_maintenance_decision(
        context_projection=_refreshable_context_projection(),
        bounded_adaptations={"candidates": []},
    )
    consequential = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "coverage_observations": [_coverage_observation(owner_class="security", consequential=True, admission="deterministic")],
        }
    )["maintenance_decision"]

    assert deterministic["status"] == "not-required"
    assert consequential["status"] == "blocked-missing-owner-operation"
    assert consequential["owner"] == "security"
    assert consequential["operation_id"] == "instructions.create"


def test_deferred_semantic_decision_retains_exact_owner_trigger_without_blocking() -> None:
    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "coverage_observations": [_coverage_observation(defer_until="next src/api/** change")],
        }
    )

    assert decision["maintenance_decision"]["status"] == "deferred"
    assert decision["maintenance_decision"]["requires_response_now"] is False
    assert decision["maintenance_decision"]["defer_until"] == "next src/api/** change"
    assert decision["primary_action"] == {}
    assert decision["context_effects"]["blocked_claim_classes"] == []


def test_context_authority_projection_rejects_configured_empty_and_missing_required_sources(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/memory/repo/manifest.toml").unlink()
    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing memory context",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    memory = next(item for item in projection["excluded_authorities"] if item["surface"] == "memory")
    assert memory["reason"] == "canonical-source-missing"
    assert projection["repair_operation"]["status"] == "not-required"
    decision = next(item for item in projection["currentness"]["decision_requirements"] if item["surface"] == "memory")
    assert decision["disposition"] == "missing-relevant-coverage"


def test_context_authority_projection_excludes_irrelevant_memory_without_repair(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    projection = resolve_context_authority_projection(
        consumer="start",
        task="fix typo",
        changed_paths=["README.md"],
        target_root=tmp_path,
    )

    assert projection["status"] == "admitted"
    assert "memory" not in {item["surface"] for item in projection["authorities"]}
    memory = next(item for item in projection["excluded_authorities"] if item["surface"] == "memory")
    assert memory["reason"] == "not-selected-by-task-or-path"
    assert memory["selected_required"] is False
    assert projection["missing_required_surfaces"] == []
    assert projection["repair_operation"]["status"] == "not-required"
    currentness = next(item for item in projection["currentness"]["dispositions"] if item["surface"] == "memory")
    assert currentness["disposition"] == "outside-responsibility"
    assert currentness["task_effect"] == "quiet"


def test_context_authority_projection_rejects_skill_dependency_owner_diagnostics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_context_authority_sources(tmp_path)

    from agentic_workspace import workspace_runtime_core as runtime_core

    monkeypatch.setattr(
        runtime_core,
        "_skill_dependency_diagnostics",
        lambda *, target_root: [{"skill": "workspace-startup", "reason_code": "missing-dependency"}],
    )

    projection = resolve_context_authority_projection(
        consumer="skills",
        task="route workspace skill",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    skills = next(item for item in projection["excluded_authorities"] if item["surface"] == "skills")
    assert skills["reason"] == "skill-dependency-closure-unsatisfied"
    assert projection["repair_operation"]["status"] == "not-required"
    decision = next(item for item in projection["currentness"]["decision_requirements"] if item["surface"] == "skills")
    assert decision["operation_id"] == ""
    assert decision["transition_mode"] == "unavailable"


def test_context_currentness_invocations_conform_to_dispatch_contract_effects() -> None:
    from agentic_workspace.client import _argv, external_consumer_profile, operation_contract
    from agentic_workspace.operating_decision import (
        CONTEXT_AUTHORITY_REGISTRY,
        _context_reconciliation_invocation,
    )

    representative = {
        "planning": "planning.summary.report",
        "memory": "memory.route.report",
        "evaluation": "evaluation.status",
        "proof": "verification.report.report",
    }
    for surface, operation_id in representative.items():
        item = next(candidate for candidate in CONTEXT_AUTHORITY_REGISTRY if candidate["surface"] == surface)
        currentness = classify_context_currentness(
            item=item,
            record={"status": "stale", "selected_required": True, "reason": "source-revision-changed"},
            owner_identity_valid=False,
        )
        invocation = _context_reconciliation_invocation(
            currentness=currentness,
            consumer="implement",
            task="refresh selected context",
            paths=["src/app.py"],
        )
        contract = operation_contract(operation_id)
        assert contract is not None
        declared = {entry["name"] for entry in contract["inputs"]}
        assert currentness["disposition"] == "refreshable-derived"
        assert invocation["operation_id"] == operation_id
        assert set(invocation["arguments"]) <= declared
        assert invocation["contract_conformance"]["undeclared_arguments"] == []
        assert invocation["mutation_boundary"]["writes_repo_state"] is contract["effects"]["writes_repo_state"] is False
        assert "expected_registry_revision" not in invocation["arguments"]
        assert "expected_source_revision" not in invocation["arguments"]

        profile_entry = next(entry for entry in external_consumer_profile()["operations"] if entry["id"] == operation_id)
        package_name = profile_entry["operation_resources"]["python"]["package"]
        argv = _argv(contract, invocation["arguments"], Path.cwd(), package_name=package_name)
        program = str(contract["command_surface"].get("program") or "agentic-workspace")
        if program == "agentic-workspace":
            command = [sys.executable, "scripts/run_agentic_workspace.py", *argv]
        else:
            assert argv.pop(0) == program.removeprefix("agentic-")
            command = ["uv", "run", program, *argv]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env={key: value for key, value in os.environ.items() if not key.startswith("AW_SESSION_LOG_")},
        )
        assert completed.returncode == 0, completed.stderr
        assert isinstance(json.loads(completed.stdout), dict)

    generated = next(item for item in CONTEXT_AUTHORITY_REGISTRY if item["surface"] == "generated-references")
    generated_currentness = classify_context_currentness(
        item=generated,
        record={"status": "stale", "selected_required": True, "reason": "source-fingerprint-mismatch"},
        owner_identity_valid=False,
    )
    assert generated_currentness["disposition"] == "decision-required"


def test_unguarded_state_mutation_is_never_advertised_as_safe_repair() -> None:
    from agentic_workspace.operating_decision import CONTEXT_AUTHORITY_REGISTRY

    system_intent = next(item for item in CONTEXT_AUTHORITY_REGISTRY if item["surface"] == "system-intent")
    currentness = classify_context_currentness(
        item=system_intent,
        record={"status": "stale", "selected_required": True, "reason": "source-revision-changed"},
        owner_identity_valid=False,
    )

    assert currentness["transition_mode"] == "state-mutation"
    assert currentness["disposition"] == "decision-required"
    assert currentness["operation_id"] == ""


def test_context_authority_projection_rejects_consumer_local_runner_forgery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_context_authority_sources(tmp_path)

    from agentic_workspace import operating_decision

    def forged_skill_runner(**_kwargs):
        return {
            "kind": "agentic-workspace/skill-dependency-closure/v1",
            "producer": "forged.producer",
            "status": "current",
            "surface": "skills",
            "owner": "workspace skill registry",
            "source_id": ".agentic-workspace/skills/workspace-startup/SKILL.md",
            "source_revision": "sha256:forged-source",
            "git_head": "",
            "revision": "sha256:forged-skill-owner",
            "adapter_id": "skills.owner-result",
        }

    monkeypatch.setattr(operating_decision, "registered_context_owner_operation_runner", lambda _surface: forged_skill_runner)

    projection = resolve_context_authority_projection(
        consumer="skills",
        task="route workspace skill",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    skills = next(item for item in projection["excluded_authorities"] if item["surface"] == "skills")
    assert skills["reason"] in {"owner-operation-missing", "owner-result-identity-mismatch"}


def test_context_authority_owner_result_revisions_bind_selection_and_schema_backing(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    base = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )
    with_path = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        changed_paths=["AGENTS.md"],
        target_root=tmp_path,
    )

    base_scoped = next(item for item in base["authorities"] if item["surface"] == "scoped-instructions")
    path_scoped = next(item for item in with_path["authorities"] if item["surface"] == "scoped-instructions")
    assert base_scoped["source"]["admission"]["owner_result"]["revision"] != path_scoped["source"]["admission"]["owner_result"]["revision"]

    (tmp_path / "AGENTS.md").write_text(
        "Authority marker:\n\n<!-- agentic-workspace:workflow:start -->\nmissing route marker\n",
        encoding="utf-8",
    )
    invalid = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )
    scoped = next(item for item in invalid["excluded_authorities"] if item["surface"] == "scoped-instructions")
    assert scoped["reason"] == "owner-source-contract-marker-missing"


@pytest.mark.parametrize(
    "receipt_payload",
    [
        {},
        {
            "kind": "agentic-workspace/system-intent-mirror/v1",
            "producer": "agentic_workspace.system_intent",
            "status": "current",
            "surface": "system-intent",
            "source_id": "SYSTEM_INTENT.md",
            "source_revision": "sha256:caller-asserted",
            "git_head": "",
            "adapter_id": "system-intent.owner-result",
        },
    ],
)
def test_context_authority_ignores_checked_in_owner_result_receipts(
    tmp_path: Path,
    receipt_payload: dict[str, object],
) -> None:
    _write_context_authority_sources(tmp_path)
    receipt_path = tmp_path / ".agentic-workspace/context-authority/owner-results/system-intent.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )

    assert projection["status"] == "admitted"
    system_intent = next(item for item in projection["authorities"] if item["surface"] == "system-intent")
    assert system_intent["source"]["admission"]["owner_result"]["status"] == "current"
    assert system_intent["source"]["admission"]["owner_result"]["owner_operation"]["status"] == "executed"
    assert system_intent["source"]["admission"]["owner_result"]["owner_execution_receipt"]["current_state"] == "current"
    assert "owner_receipt_ref" not in system_intent["source"]["admission"]["owner_result"]


def test_context_authority_rejects_digest_only_consumer_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_context_authority_sources(tmp_path)
    from agentic_workspace import operating_decision

    def digest_only_runner(**kwargs):
        chosen = kwargs["chosen"]
        git_head = kwargs["git_head"]
        source_revision = "sha256:" + _fixture_source_revision(chosen)
        return {
            "kind": "agentic-workspace/system-intent-mirror/v1",
            "producer": "agentic_workspace.system_intent",
            "status": "current",
            "surface": "system-intent",
            "owner": "workspace-runtime",
            "source_id": "SYSTEM_INTENT.md",
            "source_revision": source_revision,
            "git_head": git_head,
            "revision": "sha256:caller-current",
            "adapter_id": "system-intent.owner-result",
            "owner_operation": {
                "kind": "agentic-workspace/context-authority-owner-operation/v1",
                "status": "executed",
                "operation_id": "context-authority.system-intent.refresh-source",
                "run_id": "sha256:" + operating_decision._digest({"source_revision": source_revision}),
                "receipt_id": "sha256:" + operating_decision._digest({"source_revision": source_revision, "receipt": True}),
                "producer": "agentic_workspace.system_intent",
                "surface": "system-intent",
                "source_id": "SYSTEM_INTENT.md",
                "source_revision": source_revision,
                "git_head": git_head,
                "adapter_id": "system-intent.owner-result",
            },
        }

    monkeypatch.setattr(operating_decision, "registered_context_owner_operation_runner", lambda _surface: digest_only_runner)

    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    system_intent = next(item for item in projection["excluded_authorities"] if item["surface"] == "system-intent")
    assert system_intent["reason"] in {"owner-operation-receipt-missing", "owner-operation-receipt-id-mismatch"}


def test_context_authority_owner_operation_receipt_currentness_is_recomputable_across_processes(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )

    system_intent = next(item for item in projection["authorities"] if item["surface"] == "system-intent")
    receipt = system_intent["source"]["admission"]["owner_result"]["owner_execution_receipt"]
    assert receipt["current_resolution"]["resolution_mode"] == "deterministic-source-revision"


def test_repeated_owner_resolution_is_quiet_across_representative_owner_classes(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    legacy_generated_manifest = json.dumps({"kind": "generated-cli-owner-source-manifest/v1", "owner": "command-generation"})
    for package in ("workspace", "planning", "memory", "verification"):
        (tmp_path / f"generated/{package}/.agentic-workspace-cli-fingerprint.json").write_text(
            legacy_generated_manifest,
            encoding="utf-8",
        )
    (tmp_path / "src/agentic_workspace/contracts/structured_file_inventory.json").write_text("{}\n", encoding="utf-8")

    first = resolve_context_authority_projection(
        consumer="implement",
        task="shape planning proof assignment memory and generated context",
        changed_paths=["src/agentic_workspace/operating_decision.py", "generated/workspace/python/cli.py"],
        target_root=tmp_path,
    )
    repeated = resolve_context_authority_projection(
        consumer="implement",
        task="shape planning proof assignment memory and generated context",
        changed_paths=["src/agentic_workspace/operating_decision.py", "generated/workspace/python/cli.py"],
        target_root=tmp_path,
    )
    first_generated = resolve_context_authority_projection(
        consumer="contract-checks",
        task="check generated references",
        changed_paths=["generated/workspace/python/cli.py"],
        target_root=tmp_path,
    )
    repeated_generated = resolve_context_authority_projection(
        consumer="contract-checks",
        task="check generated references",
        changed_paths=["generated/workspace/python/cli.py"],
        target_root=tmp_path,
    )

    representative = {"generated-references", "planning", "proof", "assignment", "memory"}
    first_by_surface = {item["surface"]: item for item in first["currentness"]["dispositions"]}
    repeated_by_surface = {item["surface"]: item for item in repeated["currentness"]["dispositions"]}
    first_by_surface.update({item["surface"]: item for item in first_generated["currentness"]["dispositions"]})
    repeated_by_surface.update({item["surface"]: item for item in repeated_generated["currentness"]["dispositions"]})
    assert representative <= set(first_by_surface)
    assert {surface: first_by_surface[surface]["disposition"] for surface in representative} == {
        surface: repeated_by_surface[surface]["disposition"] for surface in representative
    }
    assert all(repeated_by_surface[surface]["disposition"] in {"current", "outside-responsibility"} for surface in representative)
    assert repeated["repair_operation"]["status"] == "not-required"
    assert repeated["refresh_operation"]["status"] == "not-required"
    assert repeated_generated["repair_operation"]["status"] == "not-required"
    assert repeated_generated["refresh_operation"]["status"] == "not-required"


def test_context_authority_rejects_parseable_file_without_owner_boundary(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")

    projection = resolve_context_authority_projection(
        consumer="start",
        task="fix target guidance",
        target_root=tmp_path,
    )

    target_guidance = next(item for item in projection["excluded_authorities"] if item["surface"] == "target-guidance")
    assert target_guidance["reason"] == "owner-source-required-key-missing"


def test_context_authority_rejects_unknown_planning_and_mutation_statuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_context_authority_sources(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=tmp_path, check=True, capture_output=True)

    def unknown_planning(*, target_root, state_data):
        return {"kind": "agentic-workspace/planning-owner-admission/v1", "status": "blocked", "state_data": state_data}

    def unknown_baseline(*, target_root, changed_paths):
        return {"kind": "agentic-workspace/mutation-baseline/v1", "status": "superseded", "scope": {"allowed_paths": changed_paths}}

    monkeypatch.setattr("agentic_workspace.workspace_runtime_core._planning_owner_admission_payload", unknown_planning)
    monkeypatch.setattr("agentic_workspace.authority_envelope.mutation_baseline_payload", unknown_baseline)

    planning_projection = resolve_context_authority_projection(
        consumer="start",
        task="planning owner route",
        target_root=tmp_path,
    )
    planning = next(item for item in planning_projection["excluded_authorities"] if item["surface"] == "planning")
    assert planning["reason"] == "planning-owner-admission-blocked"

    mutation_projection = resolve_context_authority_projection(
        consumer="implement",
        task="implement mutation baseline",
        changed_paths=["src/app.py"],
        target_root=tmp_path,
    )
    mutation = next(item for item in mutation_projection["excluded_authorities"] if item["surface"] == "mutation-baseline")
    assert mutation["reason"] == "mutation-baseline-admission-superseded"


def test_context_authority_admits_dirty_scoped_mutation_baseline(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    readme = tmp_path / "README.md"
    readme.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=tmp_path, check=True, capture_output=True)
    readme.write_text("after\n", encoding="utf-8")

    projection = resolve_context_authority_projection(
        consumer="implement",
        task="implement direct scoped change",
        changed_paths=["README.md"],
        target_root=tmp_path,
    )

    mutation = next(item for item in projection["authorities"] if item["surface"] == "mutation-baseline")
    assert mutation["source"]["admission"]["owner_result"]["status"] == "current"
    assert projection["status"] == "admitted"


def test_context_authority_owner_results_are_semantic_adapter_dispatched() -> None:
    source = Path("src/agentic_workspace/operating_decision.py").read_text(encoding="utf-8")

    assert "def _execute_context_owner_operation(" not in source
    assert "def _context_owner_result(" not in source
    assert "def _file_backed_owner_result(" not in source
    assert "def _dispatch_registered_owner_operation(" not in source
    assert "def _run_registered_owner_operation(" not in source
    assert '"owner_adapter_receipt": {' not in source
    assert "CONTEXT_OWNER_RESULT_ADAPTERS" not in source
    assert "context_authority_owner_operations" in source
    assert "registered_context_owner_operation_runner(surface)" in source
    assert "parseability alone" not in source


def test_context_owner_operation_admission_does_not_accept_caller_semantic_payload() -> None:
    import agentic_workspace.context_authority_owner_operations as owner_operations

    operation_source = Path("src/agentic_workspace/context_authority_owner_operations.py").read_text(encoding="utf-8")
    resolver_source = Path("src/agentic_workspace/operating_decision.py").read_text(encoding="utf-8")

    assert not hasattr(owner_operations, "admit_context_owner_operation_result")
    assert not hasattr(owner_operations, "ContextOwnerAdapterResult")
    assert "_CONTEXT_OWNER_ADAPTER_TOKEN" not in operation_source
    assert "class ContextOwnerAdapterResult" not in operation_source
    assert "def admit_context_owner_operation_result(" not in operation_source
    assert "def _issue_context_owner_adapter_result(" not in operation_source
    assert "def _issue_context_owner_result(" not in operation_source
    assert "def _owner_operation_result_base(" not in resolver_source
    assert "def _admit_concrete_owner_adapter_result(" not in resolver_source
    assert "def _registered_owner_adapter_result(" not in resolver_source
    assert "def _owner_result_base(" not in resolver_source
    assert "def _finalize_owner_result(" not in resolver_source
    assert "def _run_registered_owner_operation(" not in resolver_source
    assert "_admit_context_owner_operation_result" not in resolver_source
    assert not hasattr(owner_operations, "run_context_owner_operation")
    assert "def run_context_owner_operation(" not in operation_source
    assert "registered_context_owner_operation_runner(surface)" in resolver_source
    assert "_CONTEXT_OWNER_OPERATION_RUNNERS" not in operation_source
    assert "_issue_owner_result" not in operation_source
    assert '"kind": "agentic-workspace/context-authority-producer-owner-state/v1"' not in operation_source
    assert "owner_execution_receipt =" not in operation_source
    assert "tomllib" not in operation_source
    assert "ast." not in operation_source
    assert "repo_planning_bootstrap.context_authority_owner" in operation_source
    assert "repo_memory_bootstrap.context_authority_owner" in operation_source
    assert "repo_verification_bootstrap.context_authority_owner" in operation_source
    assert "_CONTEXT_OWNER_ADAPTER_TOKEN" not in resolver_source
    assert "ContextOwnerAdapterResult" not in resolver_source


def test_context_authority_each_owner_family_uses_concrete_adapter_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.operating_decision as operating_decision

    _write_context_authority_sources(tmp_path)
    (tmp_path / "generated").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src/agentic_workspace/contracts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src/agentic_workspace/contracts/structured_file_inventory.json").write_text("{}\n", encoding="utf-8")
    for owner in ("workspace", "planning", "memory", "verification"):
        path = tmp_path / f"generated/{owner}/.agentic-workspace-cli-fingerprint.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"kind": "generated-cli-owner-source-manifest/v1", "owner": owner}), encoding="utf-8")
    monkeypatch.setattr(operating_decision, "_git_head", lambda _root: "f" * 40)
    monkeypatch.setattr(
        "agentic_workspace.authority_envelope.mutation_baseline_payload",
        lambda *, target_root, changed_paths: {
            "status": "current",
            "baseline_id": "baseline-1",
            "head": "f" * 40,
            "scope": {"paths": changed_paths},
            "identity": {"fingerprint": "baseline"},
        },
    )
    paths_by_surface = {
        "system-intent": ["SYSTEM_INTENT.md"],
        "architecture-principles": ["SYSTEM_INTENT.md"],
        "scoped-instructions": ["AGENTS.md"],
        "ownership": ["src/app.py"],
        "planning": [".agentic-workspace/planning/state.toml"],
        "memory": ["src/app.py"],
        "assignment": ["src/app.py"],
        "evaluation": ["src/agentic_workspace/evaluation.py"],
        "proof": ["tests/test_operating_decision.py"],
        "mutation-baseline": ["src/app.py"],
        "autopilot-executor": ["src/agentic_workspace/workspace_runtime_primitives.py"],
        "skills": [".agentic-workspace/skills/workspace-startup/SKILL.md"],
        "target-guidance": ["src/app.py"],
        "terminal-outcome": ["src/agentic_workspace/workspace_runtime_primitives.py"],
        "generated-references": ["generated/client.py"],
    }

    for item in context_authority_declarations():
        surface = item["surface"]
        consumer = str(item["consumer"]).split(",")[0].strip()
        record = _resolve_context_authority_source(
            item=item,
            target_root=tmp_path,
            consumer=consumer,
            task=f"exercise {surface} owner adapter",
            paths=paths_by_surface[surface],
        )

        assert record["status"] == "current", surface
        owner_result = record["admission"]["owner_result"]
        adapter_receipt = owner_result["owner_adapter_receipt"]
        source_owner_contract = owner_result["source_owner_contract"]
        operation = owner_result["owner_operation"]
        execution_receipt = owner_result["owner_execution_receipt"]
        assert adapter_receipt["kind"] == "agentic-workspace/context-authority-owner-adapter-result/v1"
        assert source_owner_contract["kind"] == "agentic-workspace/context-authority-source-owner-contract/v1"
        assert adapter_receipt["surface"] == operation["surface"] == execution_receipt["surface"] == surface
        assert "context_authority_owner_operations" not in execution_receipt["executor"]
        assert execution_receipt["executor"] == adapter_receipt["executor"]
        assert source_owner_contract["surface"] == surface
        assert source_owner_contract["schema"]["status"] in {"valid", "current"}
        assert source_owner_contract["lifecycle"]["status"] == "current"
        assert source_owner_contract["population"]["status"] == "present"
        assert source_owner_contract["supersession"]["status"] == "not-superseded"
        assert source_owner_contract["lifecycle"]["repair_operation_id"] == operation["operation_id"]
        assert operation["adapter_receipt_revision"] == execution_receipt["adapter_receipt_revision"]
        assert operation["source_owner_contract_revision"] == execution_receipt["source_owner_contract_revision"]
        assert adapter_receipt["source_owner_contract_revision"] == operation["source_owner_contract_revision"]
        assert owner_result["schema_backing"]
        assert owner_result["owner_boundary"]


def test_context_owner_operation_runner_rejects_caller_producer_identity(tmp_path: Path) -> None:
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_operation_runner

    _write_context_authority_sources(tmp_path)
    chosen = tmp_path / "SYSTEM_INTENT.md"
    selection = {"consumer": "start"}
    runner = registered_context_owner_operation_runner("system-intent")

    with pytest.raises(ValueError, match="must not carry caller-provided producer identity or receipts"):
        runner(
            owner="system-intent resolver",
            root=tmp_path,
            chosen=chosen,
            revision=_fixture_source_revision(chosen),
            git_head="",
            selection=selection,
            adapter_id="system-intent.owner-result",
            owner_evidence={
                "producer": "agentic_workspace.workspace_runtime_core.system_intent",
                "status": "current",
                "owner_boundary": "caller-built generic boundary",
                "schema_backing": {"source_format": "markdown", "parse_status": "valid"},
            },
        )


def test_mutation_baseline_owner_operation_produces_own_admission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_operation_runner

    _write_context_authority_sources(tmp_path)
    chosen = tmp_path / "src/agentic_workspace/operating_decision.py"
    chosen.parent.mkdir(parents=True, exist_ok=True)
    chosen.write_text("mutation baseline owner source\n", encoding="utf-8")
    observed_paths: list[str] = []

    def owned_baseline(*, target_root: Path, changed_paths: list[str]) -> dict[str, Any]:
        observed_paths.extend(changed_paths)
        return {
            "kind": "agentic-workspace/mutation-baseline/v1",
            "status": "current",
            "baseline_id": "baseline-owner-produced",
            "head": "a" * 40,
            "scope": {"allowed_paths": changed_paths},
            "identity": {"fingerprint": "owned"},
        }

    monkeypatch.setattr("agentic_workspace.authority_envelope.mutation_baseline_payload", owned_baseline)
    runner = registered_context_owner_operation_runner("mutation-baseline")

    result = runner(
        owner="mutation authority",
        root=tmp_path,
        chosen=chosen,
        revision=_fixture_source_revision(chosen),
        git_head="a" * 40,
        selection={"matched_paths": ["src/app.py"]},
        paths=["src/app.py"],
        task="mutation baseline",
        source_specific={},
    )

    assert result["status"] == "current"
    assert observed_paths == ["src/app.py"]
    admission = result["schema_backing"]["mutation_baseline_admission"]
    assert admission["baseline_id"] == "baseline-owner-produced"

    with pytest.raises(ValueError, match="derives semantic evidence from its canonical subsystem"):
        runner(
            owner="mutation authority",
            root=tmp_path,
            chosen=chosen,
            revision=_fixture_source_revision(chosen),
            git_head="a" * 40,
            selection={"matched_paths": ["src/app.py"]},
            paths=["src/app.py"],
            task="mutation baseline",
            source_specific={"mutation_baseline_admission": {"status": "current"}},
        )


@pytest.mark.parametrize(
    ("surface", "source_path", "source_specific"),
    [
        (
            "memory",
            ".agentic-workspace/memory/repo/manifest.toml",
            {"memory_curation": {"kind": "agentic-workspace/memory-route-curation/v1", "status": "selected"}},
        ),
        (
            "mutation-baseline",
            ".agentic-workspace/config.toml",
            {
                "mutation_baseline_admission": {
                    "kind": "agentic-workspace/context-authority-owner-admission/v1",
                    "status": "current",
                }
            },
        ),
        (
            "skills",
            ".agentic-workspace/skills/workspace-startup/SKILL.md",
            {"skill_dependency_closure": {"kind": "agentic-workspace/skill-dependency-closure/v1", "status": "satisfied"}},
        ),
    ],
)
def test_protected_context_owner_operations_reject_caller_source_specific_semantics(
    tmp_path: Path,
    surface: str,
    source_path: str,
    source_specific: dict[str, object],
) -> None:
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_operation_runner

    _write_context_authority_sources(tmp_path)
    chosen = tmp_path / source_path
    runner = registered_context_owner_operation_runner(surface)

    with pytest.raises(ValueError, match="derives semantic evidence from its canonical subsystem"):
        runner(
            owner=f"{surface} owner",
            root=tmp_path,
            chosen=chosen,
            revision=_fixture_source_revision(chosen),
            git_head="",
            selection={"consumer": "start", "matched_paths": ["src/app.py"]},
            task=f"exercise {surface}",
            paths=["src/app.py"],
            source_specific=source_specific,
        )


def test_context_owner_operation_admission_rejects_forged_owner_identity(tmp_path: Path) -> None:
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_receipt_status

    _write_context_authority_sources(tmp_path)
    admitted, reason = registered_context_owner_receipt_status(
        owner_operation={"receipt_id": "sha256:forged", "run_id": "sha256:forged"},
        receipt={
            "kind": "agentic-workspace/context-authority-owner-execution-receipt/v1",
            "status": "executed",
            "current_state": "current",
            "receipt_id": "sha256:forged",
            "run_id": "sha256:forged",
            "producer": "forged-producer",
            "current_resolution": {"status": "current", "resolution_mode": "deterministic-source-revision"},
        },
        result_revision="sha256:forged",
        root=tmp_path,
    )

    assert admitted is False
    assert reason in {"owner-operation-current-run-mismatch", "owner-operation-current-receipt-mismatch"}


def test_context_owner_operation_admission_rejects_tampered_producer_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import operating_decision
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_operation_runner

    _write_context_authority_sources(tmp_path)
    runner = registered_context_owner_operation_runner("system-intent")

    def tampered_runner(**kwargs):
        current = runner(**kwargs)
        return {
            **current,
            "producer_owner_state": {
                **current["producer_owner_state"],
                "revision": "sha256:forged",
            },
        }

    monkeypatch.setattr(operating_decision, "registered_context_owner_operation_runner", lambda _surface: tampered_runner)
    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    intent = next(item for item in projection["excluded_authorities"] if item["surface"] == "system-intent")
    assert intent["reason"] == "producer-owner-state-revision-mismatch"


def test_shared_context_composer_dispatches_the_registered_owner_operation() -> None:
    from agentic_workspace import context_authority_owner_operations as owner_operations

    assert owner_operations.registered_context_owner_operation_runner("system-intent").__module__ == (
        "agentic_workspace.context_authority_workspace_owners"
    )
    assert owner_operations.registered_context_owner_operation_runner("planning").__module__ == (
        "repo_planning_bootstrap.context_authority_owner"
    )
    assert owner_operations.registered_context_owner_operation_runner("memory").__module__ == (
        "repo_memory_bootstrap.context_authority_owner"
    )
    assert owner_operations.registered_context_owner_operation_runner("proof").__module__ == (
        "repo_verification_bootstrap.context_authority_owner"
    )
    assert not Path("src/agentic_workspace/context_authority_producer_operations.py").exists()


def test_owner_operations_reject_marker_and_symbol_mentions_without_canonical_structure(tmp_path: Path) -> None:
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_operation_runner

    intent = tmp_path / "SYSTEM_INTENT.md"
    intent.write_text(
        "This prose mentions # System Intent, ## Purpose, and ## Governing intents without declaring headings.\n",
        encoding="utf-8",
    )
    intent_result = registered_context_owner_operation_runner("system-intent")(
        owner="system-intent resolver",
        root=tmp_path,
        chosen=intent,
        revision=_fixture_source_revision(intent),
        git_head="",
        selection={"consumer": "start"},
    )
    assert intent_result["status"] == "invalid"
    assert intent_result["reason"] == "owner-source-contract-marker-missing"

    evaluation = tmp_path / "evaluation.py"
    evaluation.write_text(
        "# evaluation_collection_match\n# record_evaluation_report_delivery_operation\n",
        encoding="utf-8",
    )
    evaluation_result = registered_context_owner_operation_runner("evaluation")(
        owner="evaluation runtime",
        root=tmp_path,
        chosen=evaluation,
        revision=_fixture_source_revision(evaluation),
        git_head="",
        selection={"consumer": "start"},
    )
    assert evaluation_result["status"] == "invalid"
    assert evaluation_result["reason"] == "evaluation-owner-runtime-contract-missing"


def test_context_authority_resolver_rejects_stale_generated_projection(tmp_path: Path) -> None:
    (tmp_path / "generated").mkdir(parents=True)
    (tmp_path / "src/agentic_workspace/contracts").mkdir(parents=True)
    (tmp_path / "src/example.py").write_text("print('current')\n", encoding="utf-8")
    (tmp_path / "src/agentic_workspace/contracts/structured_file_inventory.json").write_text("{}\n", encoding="utf-8")
    for owner in ("workspace", "planning", "memory", "verification"):
        path = tmp_path / f"generated/{owner}/.agentic-workspace-cli-fingerprint.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"owner": owner, "source_hashes": {"src/example.py": "not-current"}}), encoding="utf-8")
    item = next(item for item in context_authority_declarations() if item["surface"] == "generated-references")

    record = _resolve_context_authority_source(item=item, target_root=tmp_path, task="", paths=["generated/client.py"])

    assert record["status"] == "stale"
    assert record["reason"] == "invalid-manifest"


def test_context_authority_resolver_rejects_mutation_baseline_without_git_head(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    item = next(item for item in context_authority_declarations() if item["surface"] == "mutation-baseline")

    record = _resolve_context_authority_source(item=item, target_root=tmp_path, task="", paths=["src/app.py"])

    assert record["status"] == "missing"
    assert record["reason"] == "git-head-unavailable"


def test_context_authority_coverage_fails_closed_for_duplicate_canonical_owner() -> None:
    declarations = context_authority_declarations()
    duplicate = next(item for item in declarations if item["surface"] == "architecture-principles")
    duplicate["owner"] = "system-intent resolver"

    coverage = context_authority_coverage(declarations=declarations)

    assert coverage["status"] == "coverage-gap"
    assert coverage["duplicate_canonical_owners"] == ["system-intent resolver"]


def test_operating_decision_identity_changes_with_terminal_blocker_and_claim_posture() -> None:
    base = compile_operating_decision(inputs={"revisions": {"planning": "same"}, "terminal_state": "continue"})
    terminal = compile_operating_decision(inputs={"revisions": {"planning": "same"}, "terminal_state": "complete"})
    blocked = compile_operating_decision(
        inputs={
            "revisions": {"planning": "same"},
            "terminal_state": "continue",
            "blockers": [{"reason_code": "missing-authority", "owner": "planning", "repair": "select owner"}],
        }
    )
    claims = compile_operating_decision(
        inputs={"revisions": {"planning": "same"}, "terminal_state": "continue", "blocked_claim_classes": ["completion"]}
    )

    assert len({base["decision_id"], terminal["decision_id"], blocked["decision_id"], claims["decision_id"]}) == 4
    assert all("decision_posture" in decision["input_revisions"] for decision in (base, terminal, blocked, claims))
