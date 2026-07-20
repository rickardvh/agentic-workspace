from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace.actionability import operation_invocation
from agentic_workspace.operating_decision import (
    compile_operating_decision,
    context_authority_declarations,
    derive_context_gaps,
)

SCHEMA_ROOT = Path("src/agentic_workspace/contracts/schemas")


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def test_operating_decision_emits_one_typed_primary_action() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        effect_class="read-only-report",
        expected_transition="proof status refreshed",
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


def test_context_authority_declarations_and_gap_classes_validate() -> None:
    declarations = context_authority_declarations()
    declaration_schema = _schema("context_authority_declaration.schema.json")
    for declaration in declarations:
        Draft202012Validator(declaration_schema).validate(declaration)

    gaps = derive_context_gaps(
        declarations=declarations,
        selected_surfaces=[
            {"surface": "memory", "required": True, "status": "missing", "affected_decisions": ["reuse"]},
            {"surface": "system-intent", "required": True, "status": "present", "minimum_useful": False},
            {"surface": "skills", "required": True, "status": "present"},
            {"surface": "proof", "required": False, "status": "present", "inference_fallback": True},
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
        selected_surfaces=[{"surface": "proof", "required": True, "status": "missing"}],
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
