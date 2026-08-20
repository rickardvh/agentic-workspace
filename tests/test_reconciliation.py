from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace.control_inputs import compile_control_inputs
from agentic_workspace.operating_decision import compile_operating_decision
from agentic_workspace.reconciliation import compile_reconciliation


def _schema(name: str) -> dict:
    return json.loads((Path("src/agentic_workspace/contracts/schemas") / name).read_text(encoding="utf-8"))


def test_direct_success_reconciles_terminal_without_artifacts() -> None:
    result = compile_reconciliation(
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied", "owner_level": "direct"},
            "proof": {"status": "not-required"},
            "residue": {"status": "none"},
        }
    )

    assert result["status"] == "terminal"
    assert result["claim"]["permission"] == "allowed"
    assert result["next_action"] == {}


def test_local_success_does_not_close_unfinished_parent() -> None:
    result = compile_reconciliation(
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied", "owner_level": "slice", "parent_status": "active", "parent_owner": "lane-a"},
            "proof": {"status": "passed"},
        }
    )

    assert result["claim"]["permission"] == "bounded"
    assert result["claim"]["level"] == "slice"
    assert result["claim"]["parent_claim_allowed"] is False
    assert result["next_action"]["owner"] == "lane-a"


def test_stale_proof_and_external_evidence_lower_claim_with_recovery_owner() -> None:
    result = compile_reconciliation(
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied", "owner_level": "slice"},
            "proof": {"status": "stale", "owner": "verification"},
            "external_evidence": {"status": "unavailable", "owner": "planning"},
        }
    )

    assert result["claim"]["permission"] == "blocked"
    assert [item["reason_code"] for item in result["blockers"]] == ["proof-stale", "external-unavailable"]
    assert result["next_action"]["operation_id"] == "workspace.reconcile.refresh"


def test_residue_requires_exactly_one_owner() -> None:
    result = compile_reconciliation(
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied"},
            "residue": {"status": "capture"},
        }
    )

    assert "residue-owner-missing" in result["claim"]["reasons"]


def test_explicit_human_decision_is_constructible_continuation() -> None:
    result = compile_reconciliation(
        {
            "result": {"status": "partial"},
            "intent": {"status": "partial", "owner": "product"},
            "continuation": {
                "owner": "product",
                "next_action": {"human_decision": "choose retain or archive", "facts": ["external issue closed"]},
            },
        }
    )

    assert result["next_action"]["human_decision"] == "choose retain or archive"


def test_operating_decision_is_the_reconciliation_composition_owner() -> None:
    decision = compile_operating_decision(
        inputs={
            "revisions": {"current_work": "r1"},
            "reconciliation": {
                "result": {"status": "succeeded"},
                "intent": {"status": "satisfied", "owner_level": "direct"},
                "proof": {"status": "not-required"},
            },
        }
    )

    Draft202012Validator(_schema("operating_decision.schema.json")).validate(decision)
    assert decision["status"] == "terminal"
    assert decision["terminal_state"] == "COMPLETE"
    assert decision["reconciliation"]["claim"]["permission"] == "allowed"


def test_control_inputs_project_only_applicable_material_effects() -> None:
    result = compile_control_inputs(
        [
            {
                "id": "repo-proof",
                "source_class": "repo-shared",
                "authority_class": "repo-policy",
                "owner": "repo",
                "applies": True,
                "decision_dimension": "proof",
                "effects": ["run security check"],
            },
            {"id": "local-tone", "source_class": "local-runtime", "applies": True, "decision_dimension": "", "effects": []},
            {
                "id": "unused",
                "source_class": "repo-shared",
                "applies": False,
                "decision_dimension": "constraint",
                "effects": ["irrelevant"],
            },
            {
                "id": "module-claim",
                "source_class": "module",
                "applies": True,
                "decision_dimension": "claim",
                "effects": ["global completion"],
            },
        ]
    )

    assert [item["id"] for item in result["effects"]] == ["repo-proof"]
    assert {item["id"]: item["disposition"] for item in result["dispositions"]} == {
        "repo-proof": "retained",
        "local-tone": "demoted",
        "unused": "derived-or-unmatched",
        "module-claim": "module-local",
    }


def test_conflicting_authoritative_control_inputs_fail_closed() -> None:
    decision = compile_operating_decision(
        inputs={
            "revisions": {"config": "r1"},
            "control_inputs": [
                {
                    "id": "repo-a",
                    "source_class": "repo-shared",
                    "authority_class": "repo-policy",
                    "owner": "a",
                    "applies": True,
                    "decision_dimension": "constraint",
                    "effects": ["allow"],
                },
                {
                    "id": "repo-b",
                    "source_class": "repo-shared",
                    "authority_class": "repo-policy",
                    "owner": "b",
                    "applies": True,
                    "decision_dimension": "constraint",
                    "effects": ["deny"],
                },
            ],
        }
    )

    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "conflicting-input"
    assert decision["external_blocker"]["owner"] == "repository"
