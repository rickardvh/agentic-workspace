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
    assert result["next_action"]["human_decision"] == "select a supported recovery route from the named owner"
    assert "operation_id" not in result["next_action"]


def test_residue_requires_exactly_one_owner() -> None:
    result = compile_reconciliation(
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied"},
            "residue": {"status": "capture"},
        }
    )

    assert "residue-owner-missing" in result["claim"]["reasons"]


def test_source_owned_future_context_blocks_terminal_claim_with_one_typed_owner_action() -> None:
    signal = {
        "kind": "agentic-workspace/future-context-signal/v1",
        "signal_id": "evaluation:finding-7",
        "source_class": "evaluation-finding",
        "authority_state": "owner-admitted",
        "status": "unresolved",
        "relevant": True,
        "owner": "evaluation",
        "required_decision": "admit-or-dismiss",
        "operation_invocation": {
            "operation_id": "evaluation.admit",
            "operation_path": "operations/evaluation.admit.json",
            "authority": "evaluation operation contract",
        },
    }
    result = compile_reconciliation(
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied"},
            "proof": {"status": "passed"},
            "future_context_signals": [signal],
        }
    )

    assert result["status"] == "continue"
    assert result["claim"]["reasons"] == ["future-context-unresolved"]
    assert result["next_action"]["operation_invocation"]["operation_id"] == "evaluation.admit"
    assert result["next_action"]["required_decision"] == "admit-or-dismiss"


def test_known_future_context_has_one_explicit_disposition_and_not_evaluated_is_not_none() -> None:
    base = {
        "kind": "agentic-workspace/future-context-signal/v1",
        "source_class": "planning-scope-effect",
        "authority_state": "agent-proposed",
        "relevant": True,
    }
    cases = [
        ("capture", "memory", "Reusable advisory guidance was admitted.", "disposed", True),
        ("update-existing", "docs", "Existing durable guidance was updated.", "disposed", True),
        ("route-stronger", "proof/code/test", "Maintained proof already enforces the invariant.", "disposed", False),
        ("already-absorbed", "config", "Current config is the canonical owner.", "disposed", False),
        ("dismiss", "none", "The observation is one-off and non-recurring.", "disposed", False),
        ("unresolved", "planning", "", "unresolved", True),
    ]
    signals = []
    for index, (outcome, owner, rationale, _, _) in enumerate(cases):
        disposition = {"outcome": outcome, "owner": owner, "rationale": rationale}
        if outcome == "unresolved":
            disposition["next_action"] = "select the smallest canonical owner"
        signals.append({**base, "signal_id": f"signal-{index}", "disposition": disposition})

    result = compile_reconciliation(
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied"},
            "proof": {"status": "passed"},
            "future_context_capture": {"status": "not_evaluated"},
            "future_context_signals": signals,
        }
    )
    reconciliation = result["future_context_reconciliation"]

    assert reconciliation["status"] == "unresolved"
    assert reconciliation["none_found_allowed"] is False
    assert reconciliation["capture_input_status"] == "not_evaluated"
    assert [item["status"] for item in reconciliation["dispositions"]] == [item[3] for item in cases]
    assert [item["duplicate_memory_record_required"] for item in reconciliation["dispositions"]] == [item[4] for item in cases]
    assert result["claim"]["reasons"] == ["future-context-unresolved"]


def test_future_context_custody_survives_partial_waiting_handoff_and_full_closeout() -> None:
    signal = {
        "signal_id": "agent:durable-lesson",
        "source_class": "agent-proposed-learning",
        "authority_state": "agent-proposed",
        "relevant": True,
        "disposition": {
            "outcome": "unresolved",
            "owner": "memory",
            "next_action": "admit or dismiss the advisory candidate",
        },
    }
    for status in ("partial", "waiting", "succeeded"):
        result = compile_reconciliation(
            {
                "result": {"status": status},
                "intent": {"status": "satisfied" if status == "succeeded" else "partial"},
                "future_context_signals": [signal],
                "continuation": {"status": "handoff", "owner": "next-session"},
            }
        )
        disposition = result["future_context_reconciliation"]["dispositions"][0]
        assert disposition["source_authority_state"] == "agent-proposed"
        assert disposition["authority_effect"] == "none"
        assert disposition["next_action"] == "admit or dismiss the advisory candidate"
        assert result["future_context_reconciliation"]["custody_transfer_safe"] is False


def test_admitted_memory_disposition_can_contribute_to_a_later_decision_without_authority_upgrade() -> None:
    contribution = {
        "kind": "agentic-memory/decision-contribution/v1",
        "status": "projected",
        "fact_id": "future-proof-guidance",
        "fact_revision": "sha256:fact",
        "source_revision": "sha256:memory",
        "freshness": "current",
        "owner": "memory",
        "authority_class": "advisory",
        "applicability_basis": ["explicit-owner-admission"],
        "affected_decisions": ["proof-route"],
        "guidance": "Keep proof publication observational.",
        "evidence_refs": ["planning-effect:proof-fixed-point"],
    }
    decision = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "future_context_signals": [
                {
                    "signal_id": "planning-effect:proof-fixed-point",
                    "source_class": "planning-scope-effect",
                    "authority_state": "owner-admitted",
                    "relevant": True,
                    "status": "captured",
                    "disposition": {
                        "outcome": "capture",
                        "owner": "memory",
                        "rationale": "No stronger owner covers this advisory routing lesson.",
                    },
                    "decision_contribution": contribution,
                }
            ],
        }
    )

    projected = decision["memory_effectiveness"]["projected_contributions"][0]
    assert projected["fact_id"] == "future-proof-guidance"
    assert projected["authority_class"] == "advisory"
    assert decision["context_effects"]["status"] == "quiet"


def test_no_future_context_signal_keeps_reconciliation_quiet_and_agent_candidate_stays_advisory() -> None:
    quiet = compile_operating_decision(inputs={"revisions": {"planning": "r1"}})
    candidate = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "future_context_signals": [
                {
                    "signal_id": "agent:proposal-1",
                    "source_class": "agent-proposed-learning",
                    "authority_state": "agent-proposed",
                    "status": "unresolved",
                    "relevant": True,
                    "owner": "memory",
                    "required_decision": "owner-review",
                }
            ],
        }
    )

    assert "future_context_signals" not in quiet
    assert quiet["context_effects"]["status"] == "quiet"
    assert candidate["future_context_signals"][0]["authority_state"] == "agent-proposed"
    assert candidate["context_effects"]["blocked_claim_classes"] == []
    assert candidate["context_effects"]["durable_dispositions"][0]["owner"] == "memory"

    unavailable = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "future_context_capture": {"status": "unavailable", "owner": "host", "reason": "feedback API unsupported"},
        }
    )
    assert unavailable["future_context_capture"]["status"] == "unavailable"
    assert unavailable["context_effects"]["status"] == "quiet"


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


def test_registered_typed_operation_is_preserved_as_constructible_continuation() -> None:
    next_action = {
        "kind": "agentic-workspace/reconciliation-action/v1",
        "operation_invocation": {
            "operation_id": "planning.front-door",
            "operation_path": "packages/planning/src/repo_planning_bootstrap/contracts/operations/planning.front-door.json",
            "authority": "agentic-planning/route-decision/v1",
        },
    }
    result = compile_reconciliation(
        {
            "result": {"status": "partial"},
            "intent": {"status": "partial", "owner": "planning"},
            "continuation": {"owner": "planning", "next_action": next_action},
        }
    )

    assert result["next_action"] == next_action


def test_command_or_unregistered_operation_cannot_become_a_reconciliation_action() -> None:
    for supplied in (
        {"command": "agentic-workspace start --target ."},
        {"operation_id": "workspace.reconcile.refresh"},
        {"operation_invocation": {"operation_id": "planning.front-door"}},
    ):
        result = compile_reconciliation(
            {
                "result": {"status": "partial"},
                "intent": {"status": "partial", "owner": "planning"},
                "continuation": {"owner": "planning", "next_action": supplied},
            }
        )
        assert result["next_action"]["kind"] == "agentic-workspace/reconciliation-human-decision/v1"
        assert "operation_id" not in result["next_action"]


def test_each_generic_blocker_has_an_explicit_human_owned_fallback() -> None:
    cases = [
        {"result": {"status": "failed", "owner": "action"}, "intent": {"status": "satisfied"}},
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied"},
            "proof": {"status": "failed", "owner": "verification"},
        },
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied"},
            "external_evidence": {"status": "stale", "owner": "planning"},
        },
        {"result": {"status": "succeeded"}, "intent": {"status": "partial", "owner": "intent"}},
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied", "parent_status": "active", "parent_owner": "lane"},
        },
        {
            "result": {"status": "succeeded"},
            "intent": {"status": "satisfied"},
            "residue": {"status": "capture"},
        },
    ]

    for inputs in cases:
        result = compile_reconciliation(inputs)
        assert result["status"] == "continue"
        assert result["next_action"]["kind"] == "agentic-workspace/reconciliation-human-decision/v1"
        assert result["next_action"]["owner"] == result["blockers"][0]["owner"]


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
