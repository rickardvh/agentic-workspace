from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace.instruction_clause_ir import (
    compile_instruction_program,
    evaluate_predicate,
    instruction_program_from_existing_mechanisms,
    validate_instruction_program,
)
from agentic_workspace.operating_decision import _projection_instruction_mechanisms, compile_operating_decision


def _source(owner: str = "repo", revision: str = "r1", *, current: bool = True) -> dict[str, object]:
    return {"owner": owner, "revision": revision, "current": current}


def _fact(fact_id: str = "task:docs", value: object = True, *, current: bool = True) -> dict[str, object]:
    return {"id": fact_id, "type": "boolean", "value": value, "source": _source(current=current)}


def _clause(
    clause_id: str,
    kind: str,
    target: str,
    *,
    fact: str = "task:docs",
    satisfier: str = "",
) -> dict[str, object]:
    effect: dict[str, object] = {"kind": kind, "target": target}
    if satisfier:
        effect["satisfier"] = satisfier
    return {
        "id": clause_id,
        "source": _source(),
        "when": {"fact": fact, "operator": "is", "value": True},
        "effects": [effect],
        "authority": {"effects": [kind], "target_patterns": [target]},
    }


def _program(*, facts=None, clauses=None, capabilities=None, source_diagnostics=None) -> dict[str, object]:
    return {
        "kind": "agentic-workspace/instruction-program/v1",
        "facts": facts if facts is not None else [_fact()],
        "clauses": clauses if clauses is not None else [],
        "capabilities": capabilities if capabilities is not None else [],
        "source_diagnostics": source_diagnostics if source_diagnostics is not None else [],
    }


def test_instruction_contract_has_four_non_widening_effects() -> None:
    contract = json.loads(Path("src/agentic_workspace/contracts/instruction_clause_ir.json").read_text(encoding="utf-8"))

    assert contract["effect_kinds"] == ["surface", "prefer", "require", "restrict"]
    assert "allow" in contract["forbidden_effects"]
    assert contract["compiler_owner"] == "agentic_workspace.operating_decision.compile_operating_decision"


def test_program_schema_accepts_source_bound_program() -> None:
    schema = json.loads(Path("src/agentic_workspace/contracts/schemas/instruction_clause_program.schema.json").read_text(encoding="utf-8"))
    program = _program(clauses=[_clause("docs-surface", "surface", "surface:docs")])

    Draft202012Validator(schema).validate(program)


def test_bounded_predicates_are_three_valued_and_composable() -> None:
    facts = {"task:docs": _fact(), "branch": _fact("branch", "main")}

    assert evaluate_predicate({"fact": "task:docs", "operator": "present"}, facts)["result"] == "true"
    assert evaluate_predicate({"fact": "missing", "operator": "is", "value": True}, facts)["result"] == "unknown"
    assert (
        evaluate_predicate(
            {"all": [{"fact": "task:docs", "operator": "is", "value": True}, {"fact": "branch", "operator": "matches", "value": "ma*"}]},
            facts,
        )["result"]
        == "true"
    )


def test_all_four_effects_compose_deterministically() -> None:
    clauses = [
        _clause("surface", "surface", "surface:architecture"),
        _clause("surface-duplicate", "surface", "surface:architecture"),
        _clause("prefer", "prefer", "skill:review"),
        _clause("require", "require", "claim:complete", satisfier="evidence:tests"),
        _clause("restrict", "restrict", "claim:publish"),
    ]
    capabilities = [{"id": "evidence:tests", "kind": "evidence", "current": True, "source": _source("verification")}]

    projection = compile_instruction_program(_program(clauses=clauses, capabilities=capabilities))

    assert projection["status"] == "compiled"
    assert [item["target"] for item in projection["effects"]["surface"]] == ["surface:architecture"]
    assert projection["effects"]["prefer"][0]["target"] == "skill:review"
    assert projection["effects"]["require"][0]["satisfied"] is True
    assert projection["effects"]["restrict"][0]["target"] == "claim:publish"


def test_unknown_enforcing_applicability_blocks_only_matching_target() -> None:
    clause = _clause("unknown-gate", "restrict", "claim:publish", fact="missing")
    program = _program(clauses=[clause])

    unrelated = compile_instruction_program(program, current_targets=["operation:edit"])
    relevant = compile_instruction_program(program, current_targets=["claim:publish"])

    assert unrelated["blockers"] == []
    assert unrelated["evaluations"][0]["condition"]["result"] == "unknown"
    assert relevant["blockers"][0]["reason_code"] == "stale-revision"


def test_unknown_advisory_clause_is_quiet_and_diagnosable() -> None:
    projection = compile_instruction_program(
        _program(clauses=[_clause("unknown-preference", "prefer", "skill:review", fact="missing")]),
        current_targets=["skill:review"],
    )

    assert projection["status"] == "compiled"
    assert projection["effects"]["prefer"] == []
    assert projection["evaluations"][0]["condition"]["result"] == "unknown"


def test_authority_and_reference_conformance_fail_closed() -> None:
    clause = _clause("unauthorized", "restrict", "claim:publish")
    clause["authority"] = {"effects": ["surface"], "target_patterns": ["surface:*"]}

    diagnostics = validate_instruction_program(_program(clauses=[clause]))
    projection = compile_instruction_program(_program(clauses=[clause]), current_targets=["claim:publish"])

    assert {item["code"] for item in diagnostics} >= {"unauthorized-effect"}
    assert projection["status"] == "invalid"
    assert projection["effects"]["restrict"] == []


def test_conformance_rejects_invalid_predicate_type_and_effect_target() -> None:
    fact = {"id": "paths", "type": "string-set", "value": ["docs/a.md"], "source": _source()}
    clause = _clause("invalid-types", "surface", "claim:complete", fact="paths")

    diagnostics = validate_instruction_program(_program(facts=[fact], clauses=[clause]))

    assert {item["code"] for item in diagnostics} >= {"invalid-predicate-type", "incompatible-effect-target"}


def test_requirement_uses_current_source_owned_satisfier_without_obligation_state() -> None:
    clause = _clause("proof-gate", "require", "claim:complete", satisfier="evidence:tests")
    missing = compile_instruction_program(_program(clauses=[clause]), current_targets=["claim:complete"])
    present = compile_instruction_program(
        _program(
            clauses=[clause],
            capabilities=[{"id": "evidence:tests", "kind": "evidence", "current": True, "source": _source("verification")}],
        ),
        current_targets=["claim:complete"],
    )

    assert missing["blockers"][0]["reason_code"] == "missing-capability"
    assert present["blockers"] == []
    assert present["effects"]["require"][0]["satisfied"] is True


def test_stale_fact_and_requirement_restriction_conflict_have_typed_recovery() -> None:
    stale_fact = _fact(current=False)
    unknown = compile_instruction_program(
        _program(facts=[stale_fact], clauses=[_clause("stale", "restrict", "claim:publish")]),
        current_targets=["claim:publish"],
    )
    conflict = compile_instruction_program(
        _program(
            clauses=[
                _clause("required", "require", "claim:publish", satisfier="evidence:approval"),
                _clause("restricted", "restrict", "claim:publish"),
            ],
            capabilities=[{"id": "evidence:approval", "kind": "evidence", "current": True, "source": _source("human-review")}],
        )
    )

    assert unknown["blockers"][0]["reason_code"] == "stale-revision"
    assert any(item["reason_code"] == "conflicting-input" for item in conflict["blockers"])
    assert any(item["code"] == "requirement-restriction-conflict" for item in conflict["diagnostics"])


def test_existing_mechanism_adapters_cover_each_effect() -> None:
    mechanisms = {
        "scoped_instructions": [{"id": "docs", "owner": "instructions", "revision": "i1", "target": "surface:docs"}],
        "skill_routing": [{"id": "review", "owner": "skills", "revision": "s1", "target": "skill:review"}],
        "assurance_requirements": [
            {"id": "tests", "owner": "assurance", "revision": "a1", "target": "claim:complete", "satisfier": "evidence:tests"}
        ],
        "claim_restrictions": [{"id": "publish", "owner": "policy", "revision": "p1", "target": "claim:publish"}],
    }
    program = instruction_program_from_existing_mechanisms(
        {
            "instruction_mechanisms": mechanisms,
            "instruction_capabilities": [{"id": "evidence:tests", "kind": "evidence", "current": True, "source": _source("verification")}],
        }
    )
    projection = compile_instruction_program(program)

    assert {kind for kind, effects in projection["effects"].items() if effects} == {"surface", "prefer", "require", "restrict"}
    assert {item["source"]["owner"] for items in projection["effects"].values() for item in items} == {
        "instructions",
        "skills",
        "assurance",
        "policy",
    }


def test_workflow_obligations_compile_to_bounded_clause_effects_without_command_identity() -> None:
    mechanisms, capabilities = _projection_instruction_mechanisms(
        {
            "workflow_obligations": {
                "relevant_to_current_work": [
                    {
                        "id": "docs-review",
                        "force": "recommended",
                        "commands": ["arbitrary shell text is owner metadata"],
                    },
                    {
                        "id": "closeout-review",
                        "force": "required-before-closeout",
                        "commands": ["arbitrary shell text is not action identity"],
                    },
                ]
            }
        },
        {"blocked_claim_classes": []},
    )
    projection = compile_instruction_program(
        instruction_program_from_existing_mechanisms({"instruction_mechanisms": mechanisms, "instruction_capabilities": capabilities})
    )

    assert projection["effects"]["surface"][0]["target"] == "surface:workflow-obligation:docs-review"
    assert projection["effects"]["require"][0]["target"] == "claim:claim-work-complete"
    assert projection["effects"]["require"][0]["satisfier"] == "human:workflow-obligation-disposition:closeout-review"
    assert "arbitrary shell text" not in json.dumps(projection)


def test_assurance_adapter_requires_an_explicit_bounded_target() -> None:
    program = instruction_program_from_existing_mechanisms(
        {
            "instruction_mechanisms": {
                "assurance_requirements": [{"id": "tests", "owner": "assurance", "revision": "a1", "satisfier": "evidence:tests"}]
            }
        }
    )

    assert program["clauses"] == []
    assert program["source_diagnostics"] == [
        {
            "code": "missing-effect-target",
            "ref": "adapter:assurance_requirements:tests",
            "owner": "assurance",
            "repair": "derive the affected action, effect, operation, or claim target from assurance",
        }
    ]
    projection = compile_instruction_program(program)
    assert projection["status"] == "invalid"
    assert projection["blockers"][0]["reason_code"] == "missing-authority"
    assert projection["effects"]["require"] == []


def test_assurance_adapter_accepts_explicit_claim_and_action_targets() -> None:
    mechanisms = {
        "assurance_requirements": [
            {
                "id": "claim-tests",
                "owner": "assurance",
                "revision": "a1",
                "target": "claim:complete",
                "satisfier": "evidence:tests",
            },
            {
                "id": "publish-approval",
                "owner": "assurance",
                "revision": "a1",
                "target": "action:publish",
                "satisfier": "evidence:approval",
            },
        ]
    }
    capabilities = [
        {"id": "evidence:tests", "kind": "evidence", "current": True, "source": _source("verification")},
        {"id": "evidence:approval", "kind": "evidence", "current": True, "source": _source("review")},
    ]

    projection = compile_instruction_program(
        instruction_program_from_existing_mechanisms({"instruction_mechanisms": mechanisms, "instruction_capabilities": capabilities})
    )

    assert projection["status"] == "compiled"
    assert {item["target"] for item in projection["effects"]["require"]} == {"claim:complete", "action:publish"}


def test_requirement_without_satisfier_is_invalid_and_has_typed_recovery() -> None:
    projection = compile_instruction_program(
        _program(clauses=[_clause("proof-gate", "require", "claim:complete")]),
        current_targets=["claim:complete"],
    )

    assert projection["status"] == "invalid"
    assert any(item["code"] == "missing-satisfier" for item in projection["diagnostics"])
    assert projection["blockers"] == [
        {
            "reason_code": "missing-capability",
            "owner": "repo",
            "repair": "name the source-owned satisfier required before claim:complete",
            "clause_id": "proof-gate",
            "target": "claim:complete",
        }
    ]


def test_operating_decision_is_the_only_action_blocker_compiler() -> None:
    clause = _clause("proof-gate", "require", "claim:complete", satisfier="evidence:tests")
    decision = compile_operating_decision(
        inputs={"instruction_program": _program(clauses=[clause]), "instruction_targets": ["claim:complete"]}
    )

    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "missing-capability"
    assert decision["instruction_clause_projection"]["status"] == "blocked"
    assert decision["primary_action"] == {}


def test_claim_restriction_compatibility_projection_is_derived_from_ir() -> None:
    decision = compile_operating_decision(
        inputs={
            "instruction_program": _program(clauses=[_clause("publish-ceiling", "restrict", "claim:publish")]),
            "requested_claim_classes": [],
        }
    )

    assert decision["status"] == "terminal"
    assert decision["blocked_claim_classes"] == ["publish"]
    assert decision["instruction_clause_projection"]["effects"]["restrict"][0]["target"] == "claim:publish"


def test_ir_claim_restriction_preserves_pre_ir_claim_gate_semantics() -> None:
    legacy = compile_operating_decision(inputs={"blocked_claim_classes": ["publish"]})
    compiled = compile_operating_decision(
        inputs={"instruction_program": _program(clauses=[_clause("publish-ceiling", "restrict", "claim:publish")])}
    )

    assert compiled["status"] == legacy["status"]
    assert compiled["blocked_claim_classes"] == legacy["blocked_claim_classes"] == ["publish"]


def test_empty_program_preserves_existing_decision_identity_and_semantics() -> None:
    base = compile_operating_decision(inputs={"revisions": {"planning": "r1"}, "terminal_state": "continue"})
    empty = compile_operating_decision(
        inputs={"revisions": {"planning": "r1"}, "terminal_state": "continue", "instruction_program": _program(facts=[], clauses=[])}
    )

    assert empty["decision_id"] == base["decision_id"]
    assert empty["status"] == base["status"]
    assert empty["instruction_clause_projection"]["status"] == "not-requested"


def test_snapshot_revision_changes_when_source_revision_changes() -> None:
    first = compile_instruction_program(_program(clauses=[_clause("docs", "surface", "surface:docs")]))
    changed_fact = _fact()
    changed_fact["source"] = _source(revision="r2")
    second = compile_instruction_program(_program(facts=[changed_fact], clauses=[_clause("docs", "surface", "surface:docs")]))

    assert first["snapshot_revision"] != second["snapshot_revision"]


def test_named_repo_requirements_join_hard_evidence_and_advisory_preference() -> None:
    mechanisms = {
        "repo_requirements": [
            {
                "id": "typed-exit",
                "owner": "SYSTEM_INTENT.md",
                "revision": "intent-r1",
                "requirement_class": "invariant",
                "source_intent_ref": "SYSTEM_INTENT.md#trust",
                "source_intent_revision": "intent-r1",
                "source_intent_current": True,
                "target": "claim:claim-work-complete",
                "satisfier": "evidence:typed-exit",
                "evidence_owner": "verification:typed-exit",
                "evidence_state": "failed",
                "detail_route": "agentic-workspace proof --select typed-exit",
            },
            {
                "id": "query-shaped",
                "owner": "SYSTEM_INTENT.md",
                "revision": "intent-r1",
                "requirement_class": "guideline",
                "source_intent_ref": "SYSTEM_INTENT.md#query-shaped",
                "source_intent_revision": "intent-r1",
                "source_intent_current": True,
                "target": "operation:summary.selected",
                "evidence_state": "unknown",
            },
        ]
    }
    capabilities = [
        {
            "id": "evidence:typed-exit",
            "kind": "evidence",
            "current": False,
            "evidence_state": "failed",
            "detail_route": "agentic-workspace proof --select typed-exit",
            "source": _source("verification"),
        }
    ]

    projection = compile_instruction_program(
        instruction_program_from_existing_mechanisms({"instruction_mechanisms": mechanisms, "instruction_capabilities": capabilities}),
        current_targets=["claim:claim-work-complete", "operation:summary.selected"],
    )

    assert projection["status"] == "blocked"
    assert projection["blockers"][0]["reason_code"] == "failed-evidence"
    assert projection["blockers"][0]["repair"] == "agentic-workspace proof --select typed-exit"
    hard = projection["effects"]["require"][0]
    assert hard["requirement"]["source_intent_ref"] == "SYSTEM_INTENT.md#trust"
    assert projection["effects"]["prefer"][0]["target"] == "operation:summary.selected"


def test_named_repo_requirement_stale_intent_is_claim_scoped_and_invalid_contracts_fail_closed() -> None:
    stale = {
        "repo_requirements": [
            {
                "id": "stale-policy",
                "owner": "repo-policy",
                "revision": "r1",
                "requirement_class": "current-evidence",
                "source_intent_ref": "docs/requirements.md#old",
                "source_intent_revision": "r1",
                "source_intent_current": False,
                "target": "claim:claim-work-complete",
                "satisfier": "evidence:stale-policy",
                "evidence_state": "stale-intent",
                "detail_route": "review the superseded source requirement",
            }
        ]
    }
    capability = {
        "id": "evidence:stale-policy",
        "kind": "evidence",
        "current": False,
        "evidence_state": "stale-intent",
        "detail_route": "review the superseded source requirement",
        "source": _source("verification"),
    }
    program = instruction_program_from_existing_mechanisms({"instruction_mechanisms": stale, "instruction_capabilities": [capability]})

    unrelated = compile_instruction_program(program, current_targets=["operation:summary"])
    relevant = compile_instruction_program(program, current_targets=["claim:claim-work-complete"])

    assert unrelated["blockers"] == []
    assert relevant["blockers"][0]["reason_code"] == "stale-revision"
    assert relevant["blockers"][0]["repair"] == "review the superseded source requirement"

    invalid = instruction_program_from_existing_mechanisms(
        {
            "instruction_mechanisms": {
                "repo_requirements": [{"id": "bad", "owner": "repo", "revision": "r1", "requirement_class": "hard", "target": "claim:x"}]
            }
        }
    )
    invalid_projection = compile_instruction_program(invalid, current_targets=["claim:x"])
    assert invalid_projection["status"] == "invalid"
    assert invalid_projection["diagnostics"][0]["code"] == "invalid-repo-requirement"


def test_assurance_named_requirement_normalizes_into_the_existing_operating_decision() -> None:
    assurance = {
        "active": [
            {
                "id": "typed-exit",
                "requirement_class": "invariant",
                "source_intent_ref": "SYSTEM_INTENT.md#trust",
                "source_intent_revision": "intent-r1",
                "source_intent_current": True,
                "required_evidence": ["typed-exit-fixture"],
                "blocking_claims": ["claim-work-complete"],
                "evidence_owner": "verification:typed-exit",
                "detail_route": "agentic-workspace proof --select typed-exit",
            }
        ],
        "evidence_status": [{"requirement_id": "typed-exit", "evidence_label": "typed-exit-fixture", "status": "failed"}],
    }
    mechanisms, capabilities = _projection_instruction_mechanisms({"assurance_requirements": assurance}, {"blocked_claim_classes": []})
    decision = compile_operating_decision(
        inputs={
            "instruction_mechanisms": mechanisms,
            "instruction_capabilities": capabilities,
            "requested_claim_classes": ["claim-work-complete"],
        }
    )

    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "failed-evidence"
    effect = decision["instruction_clause_projection"]["effects"]["require"][0]
    assert effect["requirement"]["evidence_owner"] == "verification:typed-exit"
    assert decision["instruction_clause_projection"]["effects"]["restrict"] == []


def test_measurement_summary_flows_through_existing_claim_enforcement() -> None:
    measurement = {
        "kind": "agentic-workspace/measurement-evidence-summary/v1",
        "status": "failed",
        "metric": "selected-read-latency",
        "unit": "seconds",
        "observed_value": 2.4,
        "evaluated_value": 2.4,
        "comparator": "lte",
        "threshold": 2.0,
        "tolerance": 0,
        "aggregation": "median",
        "sample_count": 5,
        "subject": "planning-record-selected-read",
        "subject_revision": "fixture-r1",
        "environment": "maintained-ci",
        "source_revision": "benchmark-r1",
        "requirement_revision": "policy-r1",
        "detail_ref": "scratch/measurements/selected-read.json",
    }
    assurance = {
        "active": [
            {
                "id": "selected-latency",
                "requirement_class": "current-evidence",
                "source_intent_ref": "docs/requirements.md#selected-latency",
                "source_intent_revision": "policy-r1",
                "source_intent_current": True,
                "required_evidence": ["cold-median"],
                "blocking_claims": ["claim-work-complete"],
                "evidence_owner": "verification:selected-latency",
                "detail_route": "agentic-workspace proof --select selected-latency",
            }
        ],
        "evidence_status": [
            {
                "requirement_id": "selected-latency",
                "evidence_label": "cold-median",
                "state": "failed",
                "measurement": measurement,
            }
        ],
    }
    mechanisms, capabilities = _projection_instruction_mechanisms({"assurance_requirements": assurance}, {"blocked_claim_classes": []})
    decision = compile_operating_decision(
        inputs={
            "instruction_mechanisms": mechanisms,
            "instruction_capabilities": capabilities,
            "requested_claim_classes": ["claim-work-complete"],
        }
    )

    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "failed-evidence"
    effect = decision["instruction_clause_projection"]["effects"]["require"][0]
    assert effect["requirement"]["measurement"]["observed_value"] == 2.4
    assert effect["requirement"]["measurement"]["threshold"] == 2.0

    advisory_assurance = {
        "active": [
            {
                "id": "preferred-latency",
                "requirement_class": "guideline",
                "source_intent_ref": "docs/requirements.md#cost",
                "source_intent_revision": "policy-r1",
                "source_intent_current": True,
                "preference_target": "operation:summary.selected",
                "evidence_owner": "verification:selected-latency",
                "detail_route": "inspect preferred latency",
            }
        ],
        "evidence_status": [{"requirement_id": "preferred-latency", "state": "failed", "measurement": measurement}],
    }
    advisory_mechanisms, advisory_capabilities = _projection_instruction_mechanisms(
        {"assurance_requirements": advisory_assurance}, {"blocked_claim_classes": []}
    )
    advisory = compile_operating_decision(
        inputs={
            "instruction_mechanisms": advisory_mechanisms,
            "instruction_capabilities": advisory_capabilities,
            "requested_claim_classes": ["claim-work-complete"],
        }
    )
    assert advisory["status"] != "blocked"
    assert advisory["instruction_clause_projection"]["blockers"] == []
    assert advisory["instruction_clause_projection"]["effects"]["prefer"][0]["requirement"]["measurement"]["status"] == "failed"


def test_named_repo_requirement_preserves_distinct_evidence_states() -> None:
    expected = {
        "failed": "failed-evidence",
        "stale": "stale-revision",
        "unknown": "unresolved-evidence",
        "unavailable": "unavailable-evidence",
        "invalid": "invalid-evidence",
    }
    for evidence_state, reason_code in expected.items():
        mechanisms = {
            "repo_requirements": [
                {
                    "id": evidence_state,
                    "owner": "repo-policy",
                    "revision": "r1",
                    "requirement_class": "current-evidence",
                    "source_intent_ref": "docs/requirements.md#budget",
                    "source_intent_revision": "r1",
                    "source_intent_current": True,
                    "target": "claim:claim-work-complete",
                    "satisfier": f"evidence:{evidence_state}",
                    "evidence_state": evidence_state,
                }
            ]
        }
        capabilities = [
            {
                "id": f"evidence:{evidence_state}",
                "kind": "evidence",
                "current": False,
                "evidence_state": evidence_state,
                "source": _source("verification"),
            }
        ]
        projection = compile_instruction_program(
            instruction_program_from_existing_mechanisms({"instruction_mechanisms": mechanisms, "instruction_capabilities": capabilities}),
            current_targets=["claim:claim-work-complete"],
        )
        assert projection["blockers"][0]["reason_code"] == reason_code
