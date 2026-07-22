from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace.actionability import derive_actionability, invocation_decision_input_revision, operation_invocation
from agentic_workspace.operating_decision import (
    bind_operation_invocation_to_authorities,
    compile_operating_decision,
    context_authority_coverage,
    context_authority_declarations,
    derive_context_gaps,
    derive_operating_blockers_from_authorities,
    live_decision_input_revision,
)

SCHEMA_ROOT = Path("src/agentic_workspace/contracts/schemas")


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


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
    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action={"action": "run-proof", "operation_invocation": invocation},
    )

    decision = compile_operating_decision(
        inputs={
            "revisions": {"current_work": "rev-a", "proof": "rev-proof"},
            "actionability": actionability,
            "authorities": live_authorities,
        }
    )

    assert actionability["progress_check"]["result"] == "progress-making"
    assert decision["canonical_decision_input_revision"] == live_decision_input_revision(
        invocation=invocation, authorities=live_authorities
    )
    assert decision["canonical_decision_input_revision"] != invocation["expected_input_revision"]
    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"]["reason_code"] == "stale-revision"
    assert "refresh the operating decision" in decision["external_blocker"]["repair"]


def test_missing_expected_revision_is_rejected_before_execution() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )
    invocation.pop("expected_input_revision")
    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action={"action": "run-proof", "operation_invocation": invocation},
    )

    decision = compile_operating_decision(inputs={"actionability": actionability})

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["expected_input_revision"] == ""
    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "stale-revision"


def test_context_authority_declarations_and_gap_classes_validate() -> None:
    declarations = context_authority_declarations()
    coverage = context_authority_coverage()
    declaration_schema = _schema("context_authority_declaration.schema.json")
    for declaration in declarations:
        Draft202012Validator(declaration_schema).validate(declaration)

    assert "implement" in coverage["ordinary_consumers"]
    assert "autopilot-executor" in coverage["surfaces"]
    gaps = derive_context_gaps(
        declarations=declarations,
        selected_surfaces=[
            {
                "surface": "memory",
                "admitted_state": {"requirement_status": "required", "population_status": "missing"},
                "affected_decisions": ["reuse"],
            },
            {
                "surface": "system-intent",
                "admitted_state": {"requirement_status": "required", "population_status": "below-minimum"},
            },
            {"surface": "skills", "admitted_state": {"requirement_status": "required", "population_status": "present"}},
            {"surface": "proof", "admitted_state": {"freshness_status": "inference-fallback"}},
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


def test_blocking_context_gap_prevents_primary_action() -> None:
    gaps = derive_context_gaps(
        declarations=context_authority_declarations(),
        selected_surfaces=[{"surface": "proof", "admitted_state": {"requirement_status": "required", "population_status": "missing"}}],
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
        "mutation_baseline": {"baseline_id": "baseline-a", "revalidation_status": "fresh"},
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
