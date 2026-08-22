from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from agentic_workspace.adaptation import (
    adaptation_signal_from_proof_route_finding,
    admit_bounded_adaptation,
    bounded_adaptation_projection,
    execute_bounded_adaptation,
    simulate_adaptation,
)
from agentic_workspace.scoped_instructions import read_instruction
from agentic_workspace.workspace_runtime_core import _improvement_intake_payload


def _signal(*, owner_class: str = "proof-route", disposition: str = "active") -> dict[str, object]:
    source_owner = (
        ".agentic-workspace/config.toml" if owner_class == "proof-route" else ".agentic-workspace/instructions/workspace-dogfooding.md"
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
                "operation_id": "proof.report" if owner_class == "proof-route" else "instructions.create",
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
        "operation_id": "proof.report",
        "operation_registered": True,
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
    assert candidate["promotion"]["operation_registered"] is True
    assert "owner_admission" not in candidate


def _instruction_candidate(tmp_path: Path, *, negative_paths: list[str] | None = None) -> tuple[dict[str, object], Path]:
    instruction = tmp_path / ".agentic-workspace/instructions/example.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\npaths:\n  - src/**\n---\n\n# Example\n\nKeep existing guidance.\n", encoding="utf-8")
    revision = read_instruction(instruction, root=tmp_path).revision
    signal = _signal(owner_class="scoped-instruction")
    signal["adaptation"]["source_owner"] = ".agentic-workspace/instructions/example.md"
    signal["adaptation"]["proposed_delta"] = {
        "action": "append_guidance",
        "heading": "Focused follow-through",
        "guidance": "Use the focused check after changing an applicable source path.",
        "positive_paths": ["src/example.py"],
        "negative_paths": negative_paths or ["docs/example.md"],
    }
    signal["adaptation"]["authority_requirement"].update({"expected_owner_revision": revision, "current_owner_revision": revision})
    signal["adaptation"]["simulation"]["allowed_owner_paths"] = [".agentic-workspace/instructions/example.md"]
    return bounded_adaptation_projection([signal])["candidates"][0], instruction


def test_scoped_instruction_adaptation_requires_admission_then_mutates_validates_and_quiets(tmp_path: Path) -> None:
    candidate, instruction = _instruction_candidate(tmp_path)

    assert candidate["status"] == "owner-review-required"
    admitted = admit_bounded_adaptation(candidate, admitted_by="maintainer@example")
    execution = execute_bounded_adaptation(admitted, target_root=tmp_path)

    assert admitted["promotion"]["automatic"] is False
    assert execution["status"] == "quiet"
    assert execution["automatic_promotion"] is False
    assert execution["validation_status"] == "passed"
    assert execution["operation_result"]["mutation_applied"] is True
    assert execution["post_owner_revision"] != execution["expected_owner_revision"]
    assert "## Focused follow-through" in instruction.read_text(encoding="utf-8")


def test_scoped_instruction_adaptation_stale_revision_is_superseded_without_mutation(tmp_path: Path) -> None:
    candidate, instruction = _instruction_candidate(tmp_path)
    admitted = admit_bounded_adaptation(candidate, admitted_by="instruction-owner")
    instruction.write_text(instruction.read_text(encoding="utf-8") + "\nConcurrent edit.\n", encoding="utf-8")
    concurrent = instruction.read_bytes()

    execution = execute_bounded_adaptation(admitted, target_root=tmp_path)

    assert execution["status"] == "superseded"
    assert execution["disposition"] == "superseded"
    assert execution["operation_result"]["mutation_applied"] is False
    assert instruction.read_bytes() == concurrent


def test_scoped_instruction_adaptation_rejects_unsafe_delta(tmp_path: Path) -> None:
    candidate, instruction = _instruction_candidate(tmp_path)
    candidate["proposed_delta"]["guidance"] = "---\npaths:\n  - **"
    admitted = admit_bounded_adaptation(candidate, admitted_by="instruction-owner")
    previous = instruction.read_bytes()

    execution = execute_bounded_adaptation(admitted, target_root=tmp_path)

    assert execution["status"] == "blocked"
    assert execution["operation_result"]["reason_code"] == "instruction-operation-rejected"
    assert instruction.read_bytes() == previous


def test_scoped_instruction_adaptation_rolls_back_failed_applicability_validation(tmp_path: Path) -> None:
    candidate, instruction = _instruction_candidate(tmp_path, negative_paths=["src/unexpected.py"])
    admitted = admit_bounded_adaptation(candidate, admitted_by="instruction-owner")
    previous = instruction.read_bytes()

    execution = execute_bounded_adaptation(admitted, target_root=tmp_path)

    assert execution["status"] == "blocked"
    assert execution["validation_status"] == "failed"
    assert execution["rollback"]["restored_pre_apply_bytes"] is True
    assert execution["operation_result"]["mutation_applied"] is False
    assert instruction.read_bytes() == previous


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
    assert payload["bounded_adaptations"]["candidates"][0]["promotion"]["operation_id"] == "proof.report"


def test_unregistered_operation_cannot_be_labeled_promotion_ready() -> None:
    signal = _signal()
    signal["adaptation"]["authority_requirement"]["operation_id"] = "proof-route-repair.apply"

    candidate = bounded_adaptation_projection([signal])["candidates"][0]

    assert candidate["status"] == "owner-review-required"
    assert candidate["promotion"]["status"] == "owner-admission-required"
    assert candidate["promotion"]["operation_registered"] is False


def test_real_route_health_signal_executes_registered_owner_operation(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import workspace_runtime_proof

    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("schema_version = 1\n", encoding="utf-8")
    changed_paths = ["src/example.py"]
    health = workspace_runtime_proof._proof_route_health_payload(
        selected_commands=[
            {
                "command": "make test-planning",
                "command_identity": "planning-timing-suite",
                "route_id": "legacy-proof",
                "lane": "legacy-proof",
                "selected_from": "live-confirmed-proof-rule",
                "route_authority": "package-seed-or-default-route",
                "authority_surface": "package proof defaults",
                "proof_kind": "full-test",
                "subject_contract": {
                    "changed_paths": changed_paths,
                    "declared_dependencies": [],
                    "dependency_binding": "implicit",
                    "requirement": "",
                    "distinct_claim": "",
                },
            }
        ],
        stale_hints=[],
        invalid_hints=[],
        manual_missing=[],
        changed_paths=changed_paths,
        target_root=tmp_path,
        cli_invoke="agentic-workspace",
        focused_route_coverage_audit={},
        route_refinement_required={},
        unavailable_commands=[],
        proof_execution_evidence={},
    )
    finding = next(item for item in health["findings"] if item["finding_class"] == "excessive_breadth_cost")
    delta = {
        "action": "upsert_domain_lane",
        "lane_id": "example_focused",
        "lane": {
            "purpose": "Focused proof for the example source.",
            "applies_to_paths": changed_paths,
            "commands": ["python -c \"print('candidate ok')\""],
        },
    }
    signal = adaptation_signal_from_proof_route_finding(
        finding,
        semantic_delta=delta,
        expected_effect={"summed_work_seconds": "lower", "required_coverage": "preserved"},
        simulation={
            "required_behaviors": ["changed-path-proof"],
            "preserved_behaviors": ["changed-path-proof"],
            "authority_delta": "none",
            "allowed_owner_paths": [".agentic-workspace/config.toml"],
            "before_cost": 420,
            "after_cost": 2,
            "before_precision": 0.25,
            "after_precision": 1.0,
        },
    )
    candidate = bounded_adaptation_projection([signal])["candidates"][0]
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (["python -c \"print('independent ok')\""], "test-independent-validation-owner"),
    )

    execution = execute_bounded_adaptation(candidate, target_root=tmp_path)

    assert execution["status"] == "quiet"
    assert execution["operation_id"] == "proof.report"
    assert execution["validation_status"] == "passed"
    assert execution["post_owner_revision"] != execution["expected_owner_revision"]
    assert execution["operation_result"]["semantic_delta"]["lane_id"] == "example_focused"
    contract = json.loads(Path("src/agentic_workspace/contracts/operations/proof.report.json").read_text(encoding="utf-8"))
    assert execution["operation_result"]["authority_path"] in {item["surface"].split(" [", 1)[0] for item in contract["writes"]}
    assert (
        json.loads((tmp_path / ".agentic-workspace/local/proof-route-repairs/history.jsonl").read_text().splitlines()[0])["status"]
        == "applied"
    )
