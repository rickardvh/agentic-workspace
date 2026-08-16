from __future__ import annotations

from pathlib import Path

import pytest

from agentic_workspace.intent_feedback import (
    compile_intent_feedback,
    evaluate_intent_expectation,
    intent_expectation_from_principle,
    intent_recurrence_evidence,
    recurrence_promotion,
)
from agentic_workspace.operating_decision import (
    admit_projection_surface_decision_input,
    compile_operating_decision,
    consume_projection_surface_decision_input,
    finalize_projection_surface_operating_decision,
)
from agentic_workspace.workspace_runtime_core import _architecture_principles_payload


def _expectation(
    *,
    intent_id: str = "quiet-relevance",
    affected: tuple[str, ...] = ("routing",),
    enforcement: str = "evidence-and-review-backed",
    consumers: tuple[str, ...] = ("start", "implement", "closeout"),
) -> dict:
    return intent_expectation_from_principle(
        principle={
            "id": intent_id,
            "authority": "repo-system-intent",
            "owner": "workspace-runtime",
            "affected_decisions": list(affected),
            "summary": "Only material current facts should change the ordinary decision.",
            "proof_expectation": "Evidence must address the affected decision rather than report generic test success.",
            "enforcement_class": enforcement,
            "consumer_refs": list(consumers),
            "source": ".agentic-workspace/system-intent/intent.toml",
        },
        intent_revision="sha256:" + "1" * 64,
        applicability={"structured_basis": ["declared-path-glob:src/agentic_workspace/**"]},
    )


def _evidence(expectation: dict, *, outcome: str, authority: str = "independent-review", addresses=None) -> dict:
    return {
        "expectation_revision": expectation["expectation_revision"],
        "outcome": outcome,
        "authority_class": authority,
        "addresses": list(addresses or expectation["affected_decisions"]),
        "evidence_refs": ["tests/intent-case.json"],
    }


def test_expectation_requires_explicit_identity_and_structured_applicability() -> None:
    admitted = _expectation()
    rejected = intent_expectation_from_principle(
        principle={"id": "quiet-relevance", "affected_decisions": ["routing"]},
        intent_revision="sha256:" + "1" * 64,
        applicability={"structured_basis": []},
    )

    assert admitted["status"] == "applicable"
    assert admitted["applicability_basis"] == ["declared-path-glob:src/agentic_workspace/**"]
    assert admitted["expectation_revision"].startswith("sha256:")
    assert rejected["status"] == "non-applicable"


def test_passing_tests_do_not_preserve_review_backed_intent_without_addressing_it() -> None:
    expectation = _expectation()
    generic_test = _evidence(
        expectation,
        outcome="preserved",
        authority="mechanical-check",
        addresses=["unit-test-result"],
    )

    evaluation = evaluate_intent_expectation(expectation=expectation, evidence=generic_test)

    assert evaluation["posture"] == "unknown"
    assert "does not address" in evaluation["reason"]


def test_material_drift_enters_existing_operating_decision_consequence_path() -> None:
    expectation = _expectation(intent_id="host-agnostic-agent-judgment", affected=("routing", "skill-selection"))
    evidence = _evidence(expectation, outcome="contradicted", addresses=["skill-selection"])

    decision = compile_operating_decision(
        inputs={
            "consumer": "implement",
            "revisions": {"head": "abc"},
            "intent_expectations": [expectation],
            "intent_evidence": [evidence],
        }
    )

    assert decision["intent_feedback"]["status"] == "drift"
    finding = decision["intent_feedback"]["findings"][0]
    assert finding["kind"] == "agentic-workspace/system-intent-finding/v1"
    assert finding["expectation_revision"] == expectation["expectation_revision"]
    assert decision["context_consequences"][0]["finding_id"] == finding["id"]
    assert decision["context_consequences"][0]["consequence"] == "require-review-now"
    assert decision["status"] == "blocked"


def test_authorized_rescope_is_revision_bound_and_quiet() -> None:
    expectation = _expectation()
    resolution = {
        "status": "accepted-tradeoff",
        "expectation_revision": expectation["expectation_revision"],
        "authorized_by": "human-product-owner",
        "evidence_refs": ["decision:42"],
    }

    feedback = compile_intent_feedback(expectations=[expectation], resolutions=[resolution])

    assert feedback["evaluations"][0]["posture"] == "explicitly-rescoped"
    assert feedback["findings"] == []


def test_applicable_intent_without_consumer_becomes_existing_coverage_gap() -> None:
    expectation = _expectation(consumers=())

    feedback = compile_intent_feedback(expectations=[expectation])

    gap = feedback["findings"][0]
    assert gap["kind"] == "agentic-workspace/context-gap/v1"
    assert gap["gap_class"] == "unembodied-intent"
    assert "existing context-authority" in gap["next_route"]


@pytest.mark.parametrize(
    ("consumer", "intent_id", "affected", "observed", "evidence_refs"),
    [
        (
            "start",
            "phase-question-context-economy",
            ("routing",),
            {
                "planning_safety_gate": {
                    "route_decision": {
                        "kind": "agentic-planning/route-decision/v1",
                        "task_relation": "independent-pending-scope",
                        "owner_posture": "current",
                        "required_transition": "inspect-current-task-scope",
                        "implementation_allowed": False,
                        "action_identity": {"idempotency_key": "session:unrelated-log-packaging-gated"},
                    }
                }
            },
            ["session:unrelated-log-packaging-gated"],
        ),
        (
            "report",
            "total-successful-completion-cost",
            ("operating-cost",),
            {
                "successful_completion_cost": {
                    "evidence": {
                        "validation_execution": {
                            "kind": "agentic-workspace/validation-completion-cost-observations/v1",
                            "runs": [
                                {
                                    "evidence_ref": "measurement:closeout-rebuild:first",
                                    "constituent_id": "closeout_trust",
                                    "duration_seconds": 125.0,
                                    "rerun": True,
                                    "subject": {"pre_subject_revision": "same", "post_subject_revision": "same"},
                                },
                                {
                                    "evidence_ref": "measurement:closeout-rebuild:second",
                                    "constituent_id": "closeout_trust",
                                    "duration_seconds": 132.0,
                                    "rerun": True,
                                    "subject": {"pre_subject_revision": "same", "post_subject_revision": "same"},
                                },
                            ],
                        }
                    }
                }
            },
            ["measurement:closeout-rebuild:first", "measurement:closeout-rebuild:second"],
        ),
        (
            "implement",
            "host-agnostic-agent-judgment",
            ("skill-selection",),
            {
                "recommendations": [
                    {
                        "id": "github-issue-creation",
                        "activation_evidence_class": "lexical-candidate",
                        "recommendation_authority": "admitted",
                    }
                ]
            },
            ["skill-routing:github-issue-creation:lexical-candidate"],
        ),
    ],
)
def test_captured_sessions_derive_drift_from_ordinary_product_outputs(
    consumer: str, intent_id: str, affected: tuple[str, ...], observed: dict, evidence_refs: list[str]
) -> None:
    expectation = _expectation(intent_id=intent_id, affected=affected)

    payload, decision = _ordinary_surface_decision(consumer=consumer, expectation=expectation, observed=observed)
    feedback = decision["intent_feedback"]

    assert feedback["status"] == "drift"
    assert feedback["findings"][0]["intent_ref"] == intent_id
    assert feedback["findings"][0]["evidence_refs"] == evidence_refs
    assert decision["context_consequences"][0]["finding_id"] == feedback["findings"][0]["id"]
    assert payload["context"]["projection_decision_authority"]["intent_expectation_revisions"] == [expectation["expectation_revision"]]


def test_unrelated_bug_and_mature_aligned_path_create_no_ceremony() -> None:
    unrelated = compile_intent_feedback(expectations=[])
    expectation = _expectation()
    aligned = compile_intent_feedback(
        expectations=[expectation],
        evidence=[_evidence(expectation, outcome="preserved")],
    )

    assert unrelated["status"] == "quiet"
    assert unrelated["findings"] == []
    assert aligned["status"] == "preserved"
    assert aligned["findings"] == []


def test_deterministic_recurrence_promotes_existing_stronger_owner() -> None:
    expectation = _expectation(enforcement="mechanically-checkable")
    feedback = compile_intent_feedback(
        expectations=[expectation],
        evidence=[_evidence(expectation, outcome="contradicted", authority="mechanical-check")],
    )

    finding = feedback["findings"][0]
    recurrence = intent_recurrence_evidence(
        finding=finding,
        observations=[
            {"finding_id": finding["id"], "observation_ref": "run:first"},
            {"finding_id": finding["id"], "observation_ref": "run:second"},
        ],
        deterministic=True,
    )
    promotion = recurrence_promotion(
        finding=finding,
        recurrence=recurrence,
        promotion_target={"owner": "contract-checker", "proof_route": "pytest tests/test_guardrail.py"},
    )

    assert promotion["status"] == "promote-to-stronger-owner"
    assert promotion["stronger_owner"]["owner"] == "contract-checker"
    assert promotion["memory_or_issue_spam_allowed"] is False


def _ordinary_surface_decision(
    *, consumer: str, expectation: dict, evidence: dict | None = None, observed: dict | None = None
) -> tuple[dict, dict]:
    admitted = admit_projection_surface_decision_input(
        input_revisions={"planning": "planning-revision"},
        consumer=consumer,
    )
    payload = consume_projection_surface_decision_input(
        payload={
            "status": "continue",
            "intent_expectations": [expectation],
            "intent_evidence": [evidence] if evidence else [],
            **(observed or {}),
        },
        admitted_input=admitted,
        consumer=consumer,
    )
    return finalize_projection_surface_operating_decision(payload=payload, admitted_input=admitted, consumer=consumer)


@pytest.mark.parametrize("consumer", ["start", "summary", "implement", "proof", "report"])
def test_one_intent_revision_is_consumed_before_each_ordinary_surface_decision(consumer: str) -> None:
    expectation = _expectation()

    payload, decision = _ordinary_surface_decision(consumer=consumer, expectation=expectation)

    authority = payload["context"]["projection_decision_authority"]
    assert authority["status"] == "admitted"
    assert authority["consumer"] == consumer
    assert authority["intent_expectation_revisions"] == [expectation["expectation_revision"]]
    assert authority["intent_feedback_revision"] == decision["intent_feedback"]["input_revision"]
    assert decision["intent_feedback"]["evaluations"][0]["expectation_revision"] == expectation["expectation_revision"]


def test_non_applicable_intent_stays_absent_from_ordinary_decision_authority() -> None:
    expectation = _expectation()
    expectation["status"] = "non-applicable"

    payload, decision = _ordinary_surface_decision(consumer="start", expectation=expectation)

    assert payload["context"]["projection_decision_authority"]["intent_expectation_revisions"] == []
    assert decision["intent_feedback"]["applicable_expectations"] == []


def test_candidate_only_lexical_skill_result_is_observed_as_aligned_without_a_finding() -> None:
    expectation = _expectation(
        intent_id="host-agnostic-agent-judgment",
        affected=("skill-selection",),
        enforcement="mechanically-checkable",
    )
    _, decision = _ordinary_surface_decision(
        consumer="implement",
        expectation=expectation,
        observed={
            "recommendations": [
                {
                    "id": "github-issue-creation",
                    "activation_evidence_class": "lexical-candidate",
                    "recommendation_authority": "candidate-only",
                }
            ]
        },
    )

    assert decision["intent_feedback"]["status"] == "preserved"
    assert decision["intent_feedback"]["findings"] == []


def test_unrelated_slow_rerun_is_not_relabelled_as_closeout_intent_drift() -> None:
    expectation = _expectation(intent_id="total-successful-completion-cost", affected=("operating-cost",))
    _, decision = _ordinary_surface_decision(
        consumer="report",
        expectation=expectation,
        observed={
            "successful_completion_cost": {
                "evidence": {
                    "validation_execution": {
                        "runs": [
                            {
                                "evidence_ref": "measurement:unrelated-slow-test",
                                "constituent_id": "integration_export",
                                "duration_seconds": 240.0,
                                "rerun": True,
                                "subject": {"pre_subject_revision": "same", "post_subject_revision": "same"},
                            }
                        ]
                    }
                }
            }
        },
    )

    assert decision["intent_feedback"]["status"] == "unknown"
    assert decision["intent_feedback"]["findings"] == []


def test_architecture_projection_exposes_predecision_expectation_with_source_revision() -> None:
    root = Path(__file__).resolve().parents[1]

    projection = _architecture_principles_payload(
        target_root=root,
        changed_paths=["src/agentic_workspace/workspace_runtime_core.py"],
        cli_invoke="agentic-workspace",
        compact=True,
    )

    expectation = projection["intent_expectations"][0]
    assert projection["status"] == "attention"
    assert expectation["intent_id"] == "host-agnostic-agent-judgment"
    assert expectation["intent_revision"] == projection["intent_revision"]
    assert expectation["status"] == "applicable"


def test_same_expectation_and_evidence_produce_same_canonical_decision_identity() -> None:
    expectation = _expectation()
    inputs = {
        "consumer": "start",
        "revisions": {"head": "abc"},
        "intent_expectations": [expectation],
        "intent_evidence": [_evidence(expectation, outcome="preserved")],
    }

    first = compile_operating_decision(inputs=inputs)
    second = compile_operating_decision(inputs=inputs)

    assert first["decision_id"] == second["decision_id"]
    assert first["input_revisions"]["intent_feedback_revision"] == first["intent_feedback"]["input_revision"]
