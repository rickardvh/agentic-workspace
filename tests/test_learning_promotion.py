from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace.learning_promotion import compile_learning_promotion
from agentic_workspace.operating_decision import compile_operating_decision


def _operation(operation_id: str = "proof-scaffold.apply") -> dict:
    return {
        "kind": "agentic-workspace/operation-invocation/v1",
        "operation_id": operation_id,
        "expected_input_revision": "sha256:current-owner",
        "mutation_boundary": {"effect_class": "write-requested-paths"},
    }


def _candidate(*, target_class: str = "scaffold-generator", effectiveness: str = "product_repo_interface_defect") -> dict:
    return {
        "candidate_id": "learning-7",
        "provisional_owner": "memory",
        "provisional_identity": {"fact_id": "proof-scaffold", "fact_revision": "r2"},
        "source_owner_revision": "r2",
        "target_class": target_class,
        "target_owner": "proof-scaffold",
        "target_owner_ref": "src/agentic_workspace/proof_scaffold.py",
        "scope_class": "shared-repo",
        "effectiveness_class": effectiveness,
        "material_evidence_count": 2,
        "evidence_authority": "verification-receipt",
        "owner_operations": {target_class: _operation()},
        "duplicate_owner_refs": ["memory:proof-scaffold", "guidance:proof-scaffold"],
    }


def test_deterministic_promotion_selects_existing_operation_and_replay_no_longer_needs_lesson() -> None:
    candidate = _candidate()
    ready = compile_learning_promotion([candidate], improvement_latitude="proactive")
    decision = ready["decisions"][0]

    assert decision["disposition"] == "promotion-ready"
    assert decision["operation_invocation"]["operation_id"] == "proof-scaffold.apply"
    assert ready["generic_mutation_operation_created"] is False

    completed_candidate = {
        **candidate,
        "operation_result": {
            "status": "succeeded",
            "operation_id": "proof-scaffold.apply",
            "expected_input_revision": "sha256:current-owner",
            "owner_revision": "sha256:new-scaffold",
        },
        "promotion_proof": {
            "status": "passed",
            "operation_id": "proof-scaffold.apply",
            "owner_revision": "sha256:new-scaffold",
            "evidence_refs": ["test:invalid-construction-rejected"],
        },
    }
    completed = compile_learning_promotion([completed_candidate], improvement_latitude="proactive")["decisions"][0]
    trace = json.loads(Path("docs/reviews/consequential-learning-promotion-2812.json").read_text())

    assert completed["disposition"] == "promoted-complete"
    assert completed["subtraction"]["disposition"] == "delete"
    assert completed["subtraction"]["remove_duplicate_refs"] == ["memory:proof-scaffold", "guidance:proof-scaffold"]
    assert trace["deterministic_replay"]["later_equivalent_work"]["provisional_lesson_required"] is False


def test_successful_aid_needs_demonstrated_effectiveness_before_procedural_promotion() -> None:
    one_off = _candidate(target_class="skill", effectiveness="successful_evidenced_reuse")
    one_off["material_evidence_count"] = 1
    one_off["owner_operations"] = {"skill": _operation("skill.install")}
    proven = {**one_off, "material_evidence_count": 3}

    retained = compile_learning_promotion([one_off], improvement_latitude="proactive")["decisions"][0]
    promoted = compile_learning_promotion([proven], improvement_latitude="proactive")["decisions"][0]

    assert retained["disposition"] == "refine-revalidate"
    assert promoted["disposition"] == "promotion-ready"
    assert promoted["operation_invocation"]["operation_id"] == "skill.install"


def test_human_owned_semantics_require_explicit_admission() -> None:
    candidate = _candidate(target_class="policy")
    candidate["owner_operations"] = {"policy": _operation("policy.update")}
    candidate["authority_owner"] = "security-maintainer"

    blocked = compile_learning_promotion([candidate], improvement_latitude="proactive")["decisions"][0]
    admitted = compile_learning_promotion(
        [{**candidate, "authority_admission": {"status": "admitted", "owner": "security-maintainer"}}],
        improvement_latitude="proactive",
    )["decisions"][0]

    assert blocked["disposition"] == "human-admission-required"
    assert blocked["requires_human_review"] is True
    assert admitted["disposition"] == "promotion-ready"


def test_target_specific_learning_stays_out_of_shared_repo_owners() -> None:
    candidate = _candidate(target_class="canonical-docs")
    candidate.update(scope_class="target-specific", target_owner="target-guidance:slow-agent")

    decision = compile_learning_promotion([candidate], improvement_latitude="proactive")["decisions"][0]

    assert decision["disposition"] == "keep-target-specific"
    assert decision["owner"] == "target-guidance:slow-agent"
    assert decision["operation_invocation"] == {}


def test_durable_advisory_can_remain_when_no_stronger_owner_removes_rediscovery_value() -> None:
    candidate = _candidate(target_class="")
    candidate["durable_anti_rediscovery_value"] = True

    decision = compile_learning_promotion([candidate], improvement_latitude="proactive")["decisions"][0]

    assert decision["disposition"] == "retain-provisional"
    assert "anti-rediscovery" in decision["reason"]


def test_revision_bound_proof_is_required_before_subtraction() -> None:
    candidate = _candidate()
    candidate["operation_result"] = {
        "status": "succeeded",
        "operation_id": "proof-scaffold.apply",
        "expected_input_revision": "sha256:stale-owner",
        "owner_revision": "sha256:new-scaffold",
    }
    candidate["promotion_proof"] = {
        "status": "passed",
        "operation_id": "proof-scaffold.apply",
        "owner_revision": "sha256:new-scaffold",
        "evidence_refs": ["test:passed"],
    }

    decision = compile_learning_promotion([candidate], improvement_latitude="proactive")["decisions"][0]

    assert decision["disposition"] == "promotion-ready"
    assert decision["subtraction"]["status"] == "not-ready"


def test_unsafe_or_cost_increasing_promotion_routes_to_human_review() -> None:
    candidate = _candidate()
    candidate["weakens_proof_or_security"] = True
    candidate["authority_owner"] = "proof-maintainer"

    result = compile_learning_promotion([candidate], improvement_latitude="proactive")

    assert result["decisions"][0]["disposition"] == "reject-or-human-review"
    assert result["findings"][0]["finding_class"] == "architecture-conflict"


def test_improvement_latitude_preserves_opportunity_without_unauthorized_mutation() -> None:
    candidate = _candidate()

    decision = compile_learning_promotion([candidate], improvement_latitude="conservative")["decisions"][0]

    assert decision["disposition"] == "route-repo-improvement"
    assert decision["owner"] == "repo-improvement"
    assert decision["operation_invocation"] == {}


def test_operating_decision_reuses_safe_typed_repair_and_schema() -> None:
    candidate = _candidate()
    decision = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "learning_promotion_candidates": [candidate],
            "improvement_latitude": "proactive",
        }
    )

    assert decision["learning_promotion"]["decisions"][0]["disposition"] == "promotion-ready"
    consequence = decision["context_consequences"][0]
    assert consequence["consequence"] == "safe-typed-repair"
    assert consequence["safe_repair"]["operation_id"] == "proof-scaffold.apply"
    schema = json.loads(Path("src/agentic_workspace/contracts/schemas/operating_decision.schema.json").read_text())
    Draft202012Validator(schema).validate(decision)


def test_absorbed_terminal_and_no_signal_paths_are_quiet() -> None:
    absorbed = _candidate()
    absorbed["stronger_owner"] = {"status": "current", "implements_behavior": True, "owner": "proof-scaffold"}
    result = compile_learning_promotion([absorbed], improvement_latitude="proactive")
    terminal = compile_learning_promotion([{**absorbed, "lifecycle": "completed"}], improvement_latitude="proactive")
    empty = compile_learning_promotion([], improvement_latitude="proactive")
    operating = compile_operating_decision(inputs={"revisions": {"planning": "r1"}})

    assert result["status"] == "quiet"
    assert result["decisions"][0]["subtraction"]["status"] == "ready"
    assert terminal["status"] == "quiet"
    assert empty["decisions"] == []
    assert "learning_promotion" not in operating
