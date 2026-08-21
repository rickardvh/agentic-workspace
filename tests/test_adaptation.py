from __future__ import annotations

from copy import deepcopy

from agentic_workspace.adaptation import bounded_adaptation_projection, simulate_adaptation
from agentic_workspace.workspace_runtime_core import _improvement_intake_payload


def _signal(*, owner_class: str = "proof-route", disposition: str = "active") -> dict[str, object]:
    source_owner = (
        ".github/release-ownership.json" if owner_class == "proof-route" else ".agentic-workspace/instructions/workspace-dogfooding.md"
    )
    return {
        "symptom": "The broad route took 420 seconds for an unrelated release change.",
        "cost": "Repeated unrelated package proof dominates successful-completion cost.",
        "source": "proof_route_maintenance.route_health",
        "observed_during": "proof --changed pyproject.toml",
        "recurrence": "repeated",
        "evidence_fingerprint": "evidence-one",
        "adaptation": {
            "owner_class": owner_class,
            "source_owner": source_owner,
            "proposed_delta": "Narrow applicability to the exact dependency subject.",
            "authority_requirement": {
                "mode": "existing-typed-operation" if owner_class == "proof-route" else "explicit-owner-admission",
                "operation_id": "proof-route-repair.apply" if owner_class == "proof-route" else "instructions.create",
                "expected_owner_revision": "owner-r1",
                "current_owner_revision": "owner-r1",
            },
            "risk_class": "low" if owner_class == "proof-route" else "consequential",
            "expected_effect": {"summed_work_seconds": "lower", "required_coverage": "preserved"},
            "validation_route": ["proof --changed pyproject.toml", "pytest tests/test_release_workflows.py -q"],
            "rollback": {"operation": "restore-owner-revision", "revision": "owner-r1"},
            "retire_when": "later equivalent proof selects no unrelated package suite",
            "disposition": disposition,
            "simulation": {
                "required_behaviors": ["release-authority", "changed-package-proof"],
                "preserved_behaviors": ["release-authority", "changed-package-proof"],
                "authority_delta": "none",
                "allowed_owner_paths": [source_owner],
                "before_cost": 420,
                "after_cost": 95,
                "before_precision": 0.5,
                "after_precision": 1.0,
            },
        },
    }


def test_bounded_adaptation_deduplicates_and_routes_to_existing_owner_operation() -> None:
    repeated = _signal()
    repeated["symptom"] = "The broad route took 510 seconds for an unrelated release change."
    repeated["evidence_fingerprint"] = "evidence-two"

    projection = bounded_adaptation_projection([_signal(), repeated])

    assert projection["status"] == "attention"
    assert projection["candidate_count"] == 1
    candidate = projection["candidates"][0]
    assert candidate["equivalent_signal_count"] == 2
    assert candidate["status"] == "promotion-ready"
    assert candidate["promotion"] == {
        "status": "existing-operation-ready",
        "operation_id": "proof-route-repair.apply",
        "revision_guard": "matched",
        "canonical_source_only": True,
        "learned_override_created": False,
    }
    assert candidate["simulation_result"]["cost_delta"] == -325


def test_bounded_adaptation_keeps_consequential_instruction_change_owner_bound() -> None:
    projection = bounded_adaptation_projection([_signal(owner_class="scoped-instruction")])

    candidate = projection["candidates"][0]
    assert candidate["status"] == "owner-review-required"
    assert candidate["promotion"]["status"] == "owner-admission-required"
    assert candidate["promotion"]["operation_id"] == "instructions.create"


def test_adaptation_simulation_rejects_removed_behavior_authority_widening_and_cost_regression() -> None:
    candidate = deepcopy(_signal()["adaptation"])
    candidate["simulation"].update(
        {
            "preserved_behaviors": ["release-authority"],
            "authority_delta": "widened",
            "after_cost": 500,
            "after_precision": 0.25,
        }
    )

    result = simulate_adaptation(candidate)

    assert result["status"] == "rejected"
    assert result["reason_codes"] == [
        "required-behavior-removed",
        "authority-widened",
        "cost-boundary-worsened",
        "precision-boundary-worsened",
    ]


def test_fixed_adaptation_becomes_quiet_without_first_line_cost() -> None:
    projection = bounded_adaptation_projection([_signal(disposition="fixed")])

    assert projection["status"] == "quiet"
    assert projection["active_candidate_count"] == 0
    assert projection["first_line_cost"] == "none"
    assert projection["candidates"][0]["status"] == "quiet"


def test_improvement_intake_derives_adaptation_without_a_second_store() -> None:
    signal = _signal()
    repo_friction = {
        "external_evidence": [
            {
                "kind": "setup-findings",
                "items": [
                    {
                        "signal_kind": "workflow_cost",
                        "symptom": signal["symptom"],
                        "cost": signal["cost"],
                        "suspected_owner": ".github/release-ownership.json",
                        "likely_remediation": "validation",
                        "confidence": 0.9,
                        "recurrence": "repeated",
                        "adaptation": signal["adaptation"],
                    }
                ],
            }
        ]
    }

    payload = _improvement_intake_payload(repo_friction=repo_friction)

    assert payload["candidate_count"] == 1
    assert payload["bounded_adaptations"]["candidate_count"] == 1
    assert payload["bounded_adaptations"]["candidates"][0]["promotion"]["operation_id"] == "proof-route-repair.apply"
