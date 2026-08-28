from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace.learning_effectiveness import compile_learning_effectiveness
from agentic_workspace.operating_decision import compile_operating_decision


def _projection(destination: str, owner_identity: dict[str, str], **extra: object) -> dict:
    return {
        "kind": "agentic-workspace/projected-learning/v1",
        "destination": destination,
        "owner": f"{destination}-owner",
        "owner_identity": owner_identity,
        "decision_id": "operating-decision:1234567890abcdef",
        "lifecycle": "active",
        **extra,
    }


def _outcome(projection: dict, outcome: str, **extra: object) -> dict:
    return {
        "destination": projection["destination"],
        "owner_identity": projection["owner_identity"],
        "decision_id": projection["decision_id"],
        "failure_identity": "equivalent-route-v1",
        "outcome": outcome,
        "evidence_authority": "reviewer-finding",
        "evidence_refs": ["review:later-work"],
        **extra,
    }


def test_cross_owner_destinations_join_without_universal_learning_identity() -> None:
    projections = [
        _projection("memory", {"fact_id": "fact-7", "fact_revision": "r2"}),
        _projection("target-guidance", {"guidance_id": "guide-4", "guidance_revision": "r3"}),
        _projection("repo-improvement", {"candidate_id": "improvement-2", "candidate_revision": "r1"}),
        _projection("agent-aid", {"aid_id": "aid-9", "aid_revision": "r5"}),
    ]
    outcomes = [
        _outcome(projections[0], "insufficient"),
        _outcome(projections[1], "violated", guidance_was_surfaced=True),
        _outcome(projections[2], "product-defect"),
        _outcome(
            projections[3],
            "successful-reuse",
            actual_use_demonstrated=True,
            material_value="reduced",
            comparable_use_count=2,
        ),
    ]

    result = compile_learning_effectiveness(projections, outcomes)

    assert {item["destination"] for item in result["evaluations"]} == {
        "memory",
        "target-guidance",
        "repo-improvement",
        "agent-aid",
    }
    assert {item["classification"] for item in result["evaluations"]} == {
        "insufficient_or_incorrect_learning",
        "target_noncompliance_candidate",
        "product_repo_interface_defect",
        "successful_evidenced_reuse",
    }
    assert all("learning_id" not in item for item in result["evaluations"])
    assert result["persistent_use_ledger_created"] is False


@pytest.mark.parametrize(
    ("outcome", "extra", "expected"),
    [
        ("recurrence", {"projected": False}, "routing_projection_miss"),
        ("recurrence", {"evidence_authority": "agent-self-report"}, "outcome_inconclusive"),
        ("recurrence", {}, "insufficient_or_incorrect_learning"),
        ("violated", {"guidance_was_surfaced": True}, "target_noncompliance_candidate"),
        ("product-defect", {}, "product_repo_interface_defect"),
        ("no-material-follow-up", {}, "no_material_follow_up"),
    ],
)
def test_reviewed_effectiveness_matrix(outcome: str, extra: dict, expected: str) -> None:
    projection = _projection("target-guidance", {"guidance_id": "guide-4", "guidance_revision": "r3"})
    later = _outcome(projection, outcome)
    later.update(extra)

    result = compile_learning_effectiveness([projection], [later])

    assert result["evaluations"][0]["classification"] == expected


def test_new_owner_revision_supersedes_learning_instead_of_calling_it_recurrence() -> None:
    projection = _projection("memory", {"fact_id": "fact-7", "fact_revision": "r2"})
    later = _outcome(projection, "recurrence")
    later["owner_identity"] = {"fact_id": "fact-7", "fact_revision": "r3"}
    later["evidence_authority"] = "current-repo-authority"

    result = compile_learning_effectiveness([projection], [later])

    assert result["evaluations"][0]["classification"] == "stale_or_contradicted_learning"
    assert result["findings"][0]["owner"] == "memory-owner"


def test_correct_repeated_cost_routes_to_repo_improvement_not_louder_guidance() -> None:
    projection = _projection("target-guidance", {"guidance_id": "guide-4", "guidance_revision": "r3"})
    result = compile_learning_effectiveness(
        [projection],
        [_outcome(projection, "violated", guidance_correct=True, deterministic_cost_recurred=True)],
    )

    finding = result["findings"][0]
    assert finding["effectiveness_class"] == "product_repo_interface_defect"
    assert finding["owner"] == "repo-improvement"


def test_success_needs_independent_actual_reuse_and_more_than_one_comparison() -> None:
    projection = _projection("agent-aid", {"aid_id": "aid-9", "aid_revision": "r5"})
    base = _outcome(projection, "successful-reuse", actual_use_demonstrated=True, material_value="reduced")

    one_use = compile_learning_effectiveness([projection], [{**base, "comparable_use_count": 1}])
    self_report = compile_learning_effectiveness(
        [projection], [{**base, "comparable_use_count": 3, "evidence_authority": "agent-self-report"}]
    )
    proved = compile_learning_effectiveness([projection], [{**base, "comparable_use_count": 2}])

    assert one_use["evaluations"][0]["classification"] == "outcome_inconclusive"
    assert self_report["evaluations"][0]["classification"] == "outcome_inconclusive"
    assert proved["evaluations"][0]["classification"] == "successful_evidenced_reuse"
    assert proved["findings"][0]["owner"] == "agent-aid-owner"


def test_duplicate_material_findings_converge_and_terminal_learning_is_quiet() -> None:
    projection = _projection("repo-improvement", {"candidate_id": "improvement-2", "candidate_revision": "r1"})
    first = _outcome(projection, "product-defect", evidence_refs=["proof:a"])
    duplicate = _outcome(projection, "product-defect", evidence_refs=["proof:b"])

    result = compile_learning_effectiveness([projection], [first, duplicate])
    terminal = compile_learning_effectiveness([{**projection, "lifecycle": "promoted"}], [first])

    assert len(result["findings"]) == 1
    assert result["findings"][0]["evidence_refs"] == ["proof:a", "proof:b"]
    assert result["findings"][0]["duplicate_evidence_count"] == 2
    assert terminal["status"] == "quiet"
    assert terminal["findings"] == []


def test_operating_decision_reuses_existing_context_consequence_compiler() -> None:
    projection = _projection("target-guidance", {"guidance_id": "guide-4", "guidance_revision": "r3"})
    decision = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "learning_projections": [projection],
            "learning_outcomes": [_outcome(projection, "violated", guidance_was_surfaced=True)],
        }
    )

    assert decision["learning_effectiveness"]["status"] == "attention"
    consequence = decision["context_consequences"][0]
    assert consequence["source_kind"] == "agentic-workspace/learning-effectiveness-finding/v1"
    assert consequence["owner"] == "target-guidance-owner"
    assert consequence["consequence"] == "defer-with-owner"
    schema = json.loads(Path("src/agentic_workspace/contracts/schemas/operating_decision.schema.json").read_text())
    Draft202012Validator(schema).validate(decision)


def test_no_later_outcome_has_no_bookkeeping_or_first_line_projection() -> None:
    projection = _projection("memory", {"fact_id": "fact-7", "fact_revision": "r2"})
    result = compile_learning_effectiveness([projection], [])
    decision = compile_operating_decision(inputs={"revisions": {"planning": "r1"}, "learning_projections": [projection]})

    assert result["status"] == "quiet"
    assert result["evaluations"] == []
    assert result["input_revision"] == ""
    assert "learning_effectiveness" not in decision


def test_maintained_traces_show_cost_change_without_claiming_causality() -> None:
    traces = json.loads(Path("docs/reviews/consequential-learning-effectiveness-traces-2811.json").read_text())

    assert len(traces["traces"]) >= 2
    for trace in traces["traces"]:
        assert trace["before"]["material_cost"] > trace["later_equivalent_work"]["material_cost"]
        assert trace["attribution"] == "contributory-not-causal"
        assert trace["later_equivalent_work"]["decision_id"].startswith("operating-decision:")
