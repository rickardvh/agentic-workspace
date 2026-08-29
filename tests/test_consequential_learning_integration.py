from __future__ import annotations

import json
from pathlib import Path

from agentic_workspace.future_learning import compile_future_learning
from agentic_workspace.learning_promotion import compile_learning_promotion
from agentic_workspace.operating_decision import compile_operating_decision


def _contribution(identity: str) -> dict:
    return {
        "kind": "agentic-memory/use-contribution/v1",
        "fact_id": identity,
        "fact_revision": "r1",
        "owner": "memory",
        "affected_decisions": ["proof-route"],
        "lifecycle": {
            "promotion_target": "proof-scaffold",
            "preferred_remediation": "make invalid construction impossible",
            "promotion_trigger": "equivalent proof trap recurs",
            "retention_after_promotion": "stub",
        },
    }


def _evidence(source_class: str, identity: str, *, status: str = "material", semantic: bool = False) -> dict:
    return {
        "evidence_id": f"{source_class}:{identity}",
        "source_class": source_class,
        "source_owner": source_class,
        "source_revision": "sha256:source",
        "source_ref": f"evidence:{source_class}:{identity}",
        "authority_state": "owner-admitted",
        "potential_future_value": True,
        "applicability": {"task_classes": ["proof-maintenance"], "surfaces": ["proof-route"]},
        "assessment": {
            "status": status,
            "semantic_judgment_required": semantic,
            "future_decision": "Use the owner-provided proof scaffold before changing proof state.",
            "related_identity": identity,
            "disposition": {"outcome": "capture", "owner": "memory"},
            "decision_contribution": _contribution(identity),
        },
    }


def _promotion_candidate(effectiveness_class: str, *, completed: bool = False) -> dict:
    candidate = {
        "candidate_id": "proof-scaffold-learning",
        "provisional_owner": "memory",
        "provisional_identity": {"fact_id": "proof-scaffold", "fact_revision": "r1"},
        "source_owner_revision": "r1",
        "target_class": "scaffold-generator",
        "target_owner": "proof-scaffold",
        "target_owner_ref": "src/agentic_workspace/proof_scaffold.py",
        "scope_class": "shared-repo",
        "effectiveness_class": effectiveness_class,
        "material_evidence_count": 2,
        "evidence_authority": "verification-receipt",
        "owner_operations": {
            "scaffold-generator": {
                "operation_id": "proof-scaffold.apply",
                "expected_input_revision": "sha256:current-owner",
                "mutation_boundary": {"effect_class": "write-requested-paths"},
            }
        },
        "duplicate_owner_refs": ["memory:proof-scaffold"],
    }
    if completed:
        candidate.update(
            operation_result={
                "status": "succeeded",
                "operation_id": "proof-scaffold.apply",
                "expected_input_revision": "sha256:current-owner",
                "owner_revision": "sha256:new-scaffold",
            },
            promotion_proof={
                "status": "passed",
                "operation_id": "proof-scaffold.apply",
                "owner_revision": "sha256:new-scaffold",
                "evidence_refs": ["test:invalid-construction-rejected"],
            },
        )
    return candidate


def test_human_correction_reaches_later_decision_then_routes_product_defect_without_learning_prompt() -> None:
    first = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "task": "Repair the proof route",
            "outcome_evidence": [_evidence("human-correction", "proof-scaffold")],
        }
    )
    signal = first["future_context_signals"][0]
    later = compile_operating_decision(
        inputs={"revisions": {"planning": "r2"}, "task": "Update proof scaffolding", "future_context_signals": [signal]}
    )
    contribution = later["memory_effectiveness"]["projected_contributions"][0]
    recurrence = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r3"},
            "task": "Update proof scaffolding",
            "future_context_signals": [signal],
            "memory_outcomes": [
                {
                    "fact_id": contribution["fact_id"],
                    "fact_revision": contribution["fact_revision"],
                    "decision_id": later["decision_id"],
                    "failure_identity": "proof-route-repeated",
                    "outcome": "product-defect",
                    "evidence_authority": "verification-receipt",
                    "product_owner": "proof-scaffold",
                }
            ],
        }
    )

    assert signal["evidence_authority_state"] == "owner-admitted"
    assert signal["authority_state"] == "owner-admitted"
    assert contribution["fact_id"] == "proof-scaffold"
    assert later["decision_id"].startswith("operating-decision:")
    assert recurrence["memory_effectiveness"]["evaluations"][0]["classification"] == "product_or_infrastructure_defect"
    assert recurrence["context_consequences"][0]["owner"] == "proof-scaffold"


def test_review_and_validation_sources_preserve_patch_specific_noise_and_promote_repeated_trap() -> None:
    patch_specific = compile_future_learning([_evidence("reviewer-finding", "patch-only", status="one-off")])
    repeated = compile_operating_decision(
        inputs={
            "revisions": {"proof": "r1"},
            "task": "Repair proof scaffolding",
            "outcome_evidence": [_evidence("validation-result", "proof-scaffold")],
        }
    )
    promotion = compile_learning_promotion(
        [_promotion_candidate("product_repo_interface_defect", completed=True)], improvement_latitude="proactive"
    )["decisions"][0]

    assert patch_specific["dismissed_count"] == 1
    assert patch_specific["persistent_store_created"] is False
    assert repeated["future_context_signals"][0]["source_class"] == "validation-result"
    assert promotion["disposition"] == "promoted-complete"
    assert promotion["subtraction"]["disposition"] == "delete"
    assert promotion["subtraction"]["remove_duplicate_refs"] == ["memory:proof-scaffold"]


def test_successful_shortcut_stays_provisional_once_then_promotes_and_retires_after_evidenced_reuse() -> None:
    one_use = _promotion_candidate("successful_evidenced_reuse")
    one_use.update(target_class="skill", material_evidence_count=1)
    one_use["owner_operations"] = {"skill": {"operation_id": "aid.install", "expected_input_revision": "sha256:aid"}}
    three_uses = {**one_use, "material_evidence_count": 3}
    completed = {
        **three_uses,
        "operation_result": {
            "status": "succeeded",
            "operation_id": "aid.install",
            "expected_input_revision": "sha256:aid",
            "owner_revision": "sha256:skill",
        },
        "promotion_proof": {
            "status": "passed",
            "operation_id": "aid.install",
            "owner_revision": "sha256:skill",
            "evidence_refs": ["review:reuse-2", "proof:reuse-3"],
        },
        "discovery_stub_required": True,
    }

    once = compile_learning_promotion([one_use], improvement_latitude="proactive")["decisions"][0]
    ready = compile_learning_promotion([three_uses], improvement_latitude="proactive")["decisions"][0]
    done = compile_learning_promotion([completed], improvement_latitude="proactive")["decisions"][0]

    assert once["disposition"] == "refine-revalidate"
    assert ready["disposition"] == "promotion-ready"
    assert done["disposition"] == "promoted-complete"
    assert done["subtraction"]["disposition"] == "stub"


def test_target_specific_durable_advisory_self_report_and_projection_miss_keep_honest_boundaries() -> None:
    target_specific = _promotion_candidate("insufficient_or_incorrect_learning")
    target_specific.update(scope_class="target-specific", target_owner="target-guidance:agent-a")
    durable = _promotion_candidate("insufficient_or_incorrect_learning")
    durable.update(target_class="", durable_anti_rediscovery_value=True)
    projection_miss = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "learning_outcomes": [
                {
                    "destination": "target-guidance",
                    "owner_identity": {"guidance_id": "target-a", "guidance_revision": "r1"},
                    "decision_id": "operating-decision:1234567890abcdef",
                    "failure_identity": "missed-route",
                    "outcome": "violated",
                    "evidence_authority": "reviewer-finding",
                    "projected": False,
                }
            ],
        }
    )
    self_report = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r1"},
            "learning_projections": [
                {
                    "destination": "target-guidance",
                    "owner_identity": {"guidance_id": "target-a", "guidance_revision": "r1"},
                    "decision_id": "operating-decision:1234567890abcdef",
                }
            ],
            "learning_outcomes": [
                {
                    "destination": "target-guidance",
                    "owner_identity": {"guidance_id": "target-a", "guidance_revision": "r1"},
                    "outcome": "violated",
                    "evidence_authority": "agent-self-report",
                }
            ],
        }
    )

    assert (
        compile_learning_promotion([target_specific], improvement_latitude="proactive")["decisions"][0]["disposition"]
        == "keep-target-specific"
    )
    assert compile_learning_promotion([durable], improvement_latitude="proactive")["decisions"][0]["disposition"] == "retain-provisional"
    assert projection_miss["learning_effectiveness"]["evaluations"][0]["classification"] == "routing_projection_miss"
    assert self_report["learning_effectiveness"]["evaluations"][0]["classification"] == "outcome_inconclusive"


def test_unrelated_weak_host_unavailable_host_and_direct_work_controls_stay_compact() -> None:
    signal = compile_operating_decision(
        inputs={"revisions": {"planning": "r1"}, "outcome_evidence": [_evidence("human-correction", "proof-scaffold")]}
    )["future_context_signals"][0]
    unrelated = compile_operating_decision(
        inputs={"revisions": {"planning": "r2"}, "task": "Format unrelated docs", "future_context_signals": [{**signal, "relevant": False}]}
    )
    weak_host = compile_operating_decision(
        inputs={
            "revisions": {"planning": "r2"},
            "outcome_evidence": [{"evidence_id": "host-result", "source_owner": "host", "potential_future_value": True}],
        }
    )
    unavailable = compile_operating_decision(
        inputs={"revisions": {"planning": "r2"}, "future_context_capture": {"status": "unavailable", "owner": "host"}}
    )
    direct = compile_operating_decision(inputs={"revisions": {"planning": "r2"}, "task": "Format docs"})

    assert "future_context_signals" not in unrelated
    assert unrelated["memory_effectiveness"]["projected_contributions"] == []
    assert weak_host["future_learning"]["unassessed_count"] == 1
    assert unavailable["future_context_capture"]["status"] == "unavailable"
    assert all(key not in direct for key in ("future_learning", "future_context_signals", "learning_effectiveness", "learning_promotion"))


def test_current_integration_review_has_two_producer_classes_cost_reduction_and_satisfied_conclusion() -> None:
    review = json.loads(Path("docs/reviews/consequential-learning-integration-2813.json").read_text())
    disposition = json.loads(Path(".agentic-workspace/evaluations/issue-2813-disposition.json").read_text())

    assert {item["producer_class"] for item in review["maintained_sequences"]} >= {"human-correction", "validation-result"}
    assert (
        sum(
            item["before"]["successful_completion_cost"] > item["later"]["successful_completion_cost"]
            for item in review["maintained_sequences"]
        )
        >= 2
    )
    assert review["no_signal_control"]["first_line_learning_fields"] == 0
    assert review["subtraction_review"]["parallel_learning_workflow"] is False
    assert disposition["evaluation_disposition"]["lifecycle"] == "satisfied"
    assert disposition["implementation_disposition"]["convergence"]["status"] == "satisfied"
