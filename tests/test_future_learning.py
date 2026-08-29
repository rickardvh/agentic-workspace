from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace.future_learning import compile_future_learning
from agentic_workspace.operating_decision import compile_operating_decision


def _evidence(
    evidence_id: str,
    source_class: str,
    *,
    status: str = "material",
    semantic: bool = True,
    related_identity: str = "",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_class": source_class,
        "source_owner": source_class,
        "source_revision": "sha256:source",
        "source_ref": f"{source_class}:{evidence_id}",
        "authority_state": "owner-admitted",
        "direction": "negative" if source_class != "successful-aid" else "positive",
        "applicability": {
            "task_classes": ["proof-maintenance"],
            "surfaces": ["proof-selection"],
            "basis": ["source-owner-classification"],
        },
        "assessment": {
            "status": status,
            "future_decision": "Use the owner-provided proof route before changing proof state.",
            "confidence": "bounded",
            "semantic_judgment_required": semantic,
            "rationale": "Equivalent proof work otherwise repeats the same repair.",
            "owner_candidates": ["memory", "proof-check"],
            "related_identity": related_identity,
        },
    }


def test_heterogeneous_source_owned_outcomes_share_one_candidate_seam() -> None:
    evidence = [
        _evidence("correction-1", "trusted-correction"),
        _evidence("finding-1", "evaluation-finding"),
        _evidence("repair-1", "validation-result", semantic=False),
        _evidence("aid-1", "successful-aid"),
    ]

    result = compile_future_learning(evidence)

    assert result["status"] == "candidates-produced"
    assert result["produced_count"] == 4
    assert result["persistent_store_created"] is False
    assert {item["source_class"] for item in result["signals"]} == {
        "trusted-correction",
        "evaluation-finding",
        "validation-result",
        "successful-aid",
    }
    assert result["signals"][0]["authority_state"] == "agent-proposed"
    assert result["signals"][0]["evidence_authority_state"] == "owner-admitted"
    assert result["signals"][2]["authority_state"] == "owner-admitted"


def test_one_off_and_already_absorbed_evidence_are_explicit_without_durable_residue() -> None:
    one_off = _evidence("typo", "validation-result", status="one-off", semantic=False)
    absorbed = _evidence("configured", "evaluation-finding", status="already-absorbed")
    absorbed["assessment"]["owner"] = "proof-check"

    result = compile_future_learning([one_off, absorbed])

    assert result["dismissed_count"] == 1
    assert result["absorbed_count"] == 1
    assert [item["disposition"]["outcome"] for item in result["signals"]] == [
        "dismiss",
        "already-absorbed",
    ]
    assert result["persistent_store_created"] is False


def test_known_potential_value_cannot_masquerade_as_none_found_when_assessment_is_skipped() -> None:
    result = compile_future_learning(
        [
            {
                "evidence_id": "host-finding",
                "source_class": "host-result",
                "source_owner": "host",
                "potential_future_value": True,
            }
        ]
    )

    assert result["status"] == "candidates-produced"
    assert result["none_found_allowed"] is False
    signal = result["signals"][0]
    assert signal["assessment_status"] == "not-evaluated"
    assert signal["disposition"]["outcome"] == "unresolved"


def test_unassessed_known_evidence_blocks_closeout_even_without_a_materiality_hint() -> None:
    decision = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "outcome_evidence": [{"evidence_id": "host-result", "source_owner": "host"}],
            "reconciliation": {
                "result": {"status": "succeeded"},
                "intent": {"status": "satisfied"},
                "proof": {"status": "passed"},
            },
        }
    )

    assert decision["future_learning"]["status"] == "not-evaluated"
    assert decision["future_context_capture"]["status"] == "not-evaluated"
    assert decision["reconciliation"]["claim"]["reasons"] == ["future-context-assessment-required"]
    assert decision["reconciliation"]["future_context_reconciliation"]["none_found_allowed"] is False


def test_absent_host_observation_stays_quiet_and_artifact_free() -> None:
    result = compile_future_learning([])
    decision = compile_operating_decision(inputs={"revisions": {"planning": "r1"}})

    assert result["status"] == "quiet"
    assert result["signals"] == []
    assert "future_learning" not in decision
    assert "future_context_signals" not in decision


def test_related_owner_identity_attaches_evidence_without_duplicate_signal() -> None:
    existing = {
        "signal_id": "correction:17",
        "source_class": "trusted-correction",
        "authority_state": "owner-admitted",
        "relevant": True,
        "disposition": {"outcome": "unresolved", "owner": "agent-guidance", "next_action": "admit or dismiss"},
    }
    evidence = _evidence("review-repeat", "evaluation-finding", related_identity="correction:17")

    result = compile_future_learning([evidence], existing_signals=[existing])

    assert result["attached_count"] == 1
    assert result["produced_count"] == 0
    assert len(result["signals"]) == 1
    assert result["signals"][0]["deduplication"]["status"] == "attached-existing-owner"
    assert result["signals"][0]["attached_evidence_refs"] == ["evaluation-finding:review-repeat"]


def test_operating_decision_automatically_carries_known_candidate_into_reconciliation() -> None:
    evidence = _evidence("repair-2", "validation-result")
    decision = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "outcome_evidence": [evidence],
            "reconciliation": {
                "result": {"status": "succeeded"},
                "intent": {"status": "satisfied", "owner_level": "slice"},
                "proof": {"status": "passed"},
            },
        }
    )

    assert decision["future_learning"]["produced_count"] == 1
    assert decision["reconciliation"]["status"] == "continue"
    assert decision["reconciliation"]["claim"]["reasons"] == ["future-context-unresolved"]
    assert decision["reconciliation"]["future_context_reconciliation"]["custody_transfer_safe"] is False
    assert decision["future_context_signals"][0]["applicability"]["task_classes"] == ["proof-maintenance"]
    schema = json.loads(Path("src/agentic_workspace/contracts/schemas/operating_decision.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(decision)
