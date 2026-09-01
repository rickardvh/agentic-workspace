from __future__ import annotations

import hashlib
import json
import tomllib
from copy import deepcopy
from pathlib import Path

import pytest

from agentic_workspace.adaptation import (
    adaptation_signal_from_proof_route_finding,
    admit_bounded_adaptation,
    bounded_adaptation_projection,
    coverage_candidate_findings,
    coverage_signal_from_observation,
    execute_bounded_adaptation,
    machine_observed_coverage_signals,
    simulate_adaptation,
)
from agentic_workspace.operating_decision import compile_context_maintenance_decision
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
        "operation_runtime_consumed": True,
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
    assert candidate["promotion"]["operation_runtime_consumed"] is True
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
    assert candidate["promotion"]["operation_runtime_consumed"] is False


def test_machine_observed_proof_and_generated_additions_become_owner_bound_candidates() -> None:
    signals = machine_observed_coverage_signals(
        [
            {
                "declaration_kind": "proof-route-declaration",
                "observed_addition": "A declared focused proof route now covers src/api/**.",
                "source_refs": [".agentic-workspace/config.toml#verification"],
                "evidence_refs": ["tests/test_api.py"],
                "owner_revision": "owner-r1",
                "proposed_delta": {"action": "upsert_domain_lane", "lane_id": "api"},
                "validation_route": ["pytest tests/test_api.py -q"],
            },
            {
                "declaration_kind": "generated-surface-declaration",
                "observed_addition": "A declared generator now owns generated/api/**.",
                "source_refs": ["src/generator/api.json"],
                "evidence_refs": ["generated/api/manifest.json"],
                "owner_revision": "owner-r2",
                "proposed_delta": {"action": "refresh_generated_projection"},
                "validation_route": ["python scripts/generate.py --check"],
            },
        ]
    )

    projection = bounded_adaptation_projection(signals)

    assert projection["candidate_count"] == 2
    by_owner = {candidate["owner_class"]: candidate for candidate in projection["candidates"]}
    assert by_owner["proof-route"]["coverage"]["source_class"] == "machine"
    assert by_owner["proof-route"]["coverage"]["affected_effects"] == ["claim", "proof"]
    assert by_owner["proof-route"]["promotion"]["operation_id"] == "proof.report"
    assert by_owner["generated-projection"]["promotion"]["operation_id"] == "generated-command-packages.refresh"
    assert by_owner["generated-projection"]["promotion"]["canonical_source_only"] is True


def test_agent_observation_is_evidence_not_automatic_authority_and_deduplicates() -> None:
    observation = {
        "source_class": "agent",
        "owner_class": "scoped-instruction",
        "source_owner": ".agentic-workspace/instructions/api.md",
        "observed_addition": "API changes repeatedly require a focused compatibility check.",
        "source_refs": ["src/api/router.py"],
        "evidence_refs": ["tests/test_api_compat.py"],
        "affected_effects": ["procedure", "proof"],
        "confidence": "advisory",
        "recurrence_identity": "api-compatibility-procedure",
        "admission": "deterministic",
        "operation_id": "instructions.create",
        "owner_revision": "owner-r1",
        "proposed_delta": {"action": "append_guidance"},
        "validation_route": ["pytest tests/test_api_compat.py -q"],
    }
    repeated = {**observation, "observed_addition": "The same API compatibility procedure was encountered again."}

    candidate = bounded_adaptation_projection([coverage_signal_from_observation(observation), coverage_signal_from_observation(repeated)])[
        "candidates"
    ][0]

    assert candidate["equivalent_signal_count"] == 2
    assert candidate["status"] == "owner-review-required"
    assert candidate["coverage"]["authority"] == "evidence"
    assert candidate["coverage"]["admission"] == "decision-required"


def test_non_operating_repository_fact_is_quiet_and_creates_no_finding() -> None:
    signal = coverage_signal_from_observation(
        {
            "source_class": "agent",
            "observed_addition": "A helper variable was renamed.",
            "affected_effects": [],
            "material": False,
        }
    )

    projection = bounded_adaptation_projection([signal])

    assert projection["status"] == "quiet"
    assert projection["first_line_cost"] == "none"
    assert coverage_candidate_findings(projection) == []


def test_material_coverage_candidate_becomes_existing_closeout_finding() -> None:
    signal = coverage_signal_from_observation(
        {
            "source_class": "review",
            "owner_class": "memory",
            "source_owner": ".agentic-workspace/memory/repo/manifest.toml",
            "observed_addition": "A recurring runtime trap is not represented in routed Memory.",
            "source_refs": ["src/runtime.py"],
            "evidence_refs": ["review:runtime-trap"],
            "affected_effects": ["procedure"],
            "operation_id": "workspace.memory-create-note.apply",
            "owner_revision": "owner-r1",
            "proposed_delta": {"action": "create_memory_note", "slug": "runtime-trap"},
            "validation_route": ["agentic-workspace memory route --target . --format json"],
        }
    )

    projection = bounded_adaptation_projection([signal])
    findings = coverage_candidate_findings(projection)

    assert len(findings) == 1
    assert findings[0]["finding_class"] == "coverage-gap"
    assert findings[0]["current_task_effect"] == "requires disposition before broad clean closeout"


def test_memory_coverage_admission_uses_canonical_writer_and_revision_guard(tmp_path: Path) -> None:
    from repo_memory_bootstrap import installer as memory_installer

    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    memory_installer.install_bootstrap(target=target)
    manifest = target / ".agentic-workspace/memory/repo/manifest.toml"
    revision = "sha256:" + hashlib.sha256(manifest.read_bytes()).hexdigest()
    signal = coverage_signal_from_observation(
        {
            "source_class": "agent",
            "owner_class": "memory",
            "source_owner": ".agentic-workspace/memory/repo/manifest.toml",
            "observed_addition": "The API routing trap recurs across ordinary work.",
            "source_refs": ["src/api/router.py"],
            "evidence_refs": ["tests/test_api.py"],
            "affected_effects": ["procedure", "continuation"],
            "operation_id": "workspace.memory-create-note.apply",
            "owner_revision": revision,
            "proposed_delta": {
                "action": "create_memory_note",
                "slug": "api-routing-trap",
                "summary": "Remember the recurring API routing trap.",
                "applies_to": ["src/api/**"],
                "evidence": ["tests/test_api.py"],
            },
            "validation_route": ["agentic-workspace memory route --target . --format json"],
        }
    )
    candidate = bounded_adaptation_projection([signal])["candidates"][0]
    admitted = admit_bounded_adaptation(candidate, admitted_by="memory-owner")

    execution = execute_bounded_adaptation(admitted, target_root=target)

    assert execution["status"] == "quiet"
    assert execution["mutation_applied"] is True
    assert execution["post_owner_revision"] != revision
    assert (target / ".agentic-workspace/memory/repo/domains/api-routing-trap.md").exists()

    stale_target = tmp_path / "stale-repo"
    (stale_target / ".git").mkdir(parents=True)
    memory_installer.install_bootstrap(target=stale_target)
    stale_manifest = stale_target / ".agentic-workspace/memory/repo/manifest.toml"
    stale_manifest.write_text(stale_manifest.read_text(encoding="utf-8") + "\n# concurrent\n", encoding="utf-8")
    stale_execution = execute_bounded_adaptation(admitted, target_root=stale_target)
    assert stale_execution["status"] == "superseded"
    assert stale_execution["mutation_applied"] is False


@pytest.mark.parametrize("choice", ["admit", "update", "retain", "dismiss"])
def test_every_advertised_semantic_choice_persists_and_reactivates_on_source_change(tmp_path: Path, choice: str) -> None:
    case_root = tmp_path / choice
    instruction = case_root / ".agentic-workspace/instructions/api.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\npaths:\n  - src/api/**\n---\n\n# API\n\nKeep current guidance.\n", encoding="utf-8")

    def observation(*, owner_revision: str) -> dict[str, object]:
        return {
            "source_class": "agent",
            "owner_class": "scoped-instruction",
            "source_owner": ".agentic-workspace/instructions/api.md",
            "observed_addition": "The moved API boundary needs an explicit compatibility procedure.",
            "source_refs": ["src/api/v2/router.py"],
            "evidence_refs": ["review:api-boundary"],
            "affected_effects": ["authority", "procedure", "proof"],
            "operation_id": "instructions.create",
            "owner_revision": owner_revision,
            "recurrence_identity": "api-v2-boundary",
            "proposed_delta": {
                "action": "append_guidance",
                "heading": "API v2 compatibility",
                "guidance": "Run the compatibility proof for API v2 boundary changes.",
                "positive_paths": ["src/api/v2/router.py"],
                "negative_paths": ["docs/api.md"],
            },
            "validation_route": ["pytest tests/test_api.py -q"],
        }

    revision = read_instruction(instruction, root=case_root).revision
    signal = coverage_signal_from_observation(observation(owner_revision=revision))
    projection = bounded_adaptation_projection([signal], target_root=case_root)
    candidate = projection["candidates"][0]
    decision = compile_context_maintenance_decision(
        context_projection={"currentness": {"decision_requirements": []}}, bounded_adaptations=projection
    )
    alternatives = {item["id"]: item for item in decision["alternatives"]}
    assert set(alternatives) == {"admit", "update", "retain", "dismiss"}
    assert alternatives[choice]["apply_operation"]["operation_id"] == "instructions.create"
    assert set(alternatives[choice]["apply_operation"]["arguments"]) <= {
        item["name"]
        for item in json.loads(Path("src/agentic_workspace/contracts/operations/instructions.create.json").read_text(encoding="utf-8"))[
            "inputs"
        ]
    }

    execution = execute_bounded_adaptation(
        admit_bounded_adaptation(
            candidate,
            admitted_by="instruction-owner",
            choice=choice,
            decision_revision=decision["decision_revision"],
        ),
        target_root=case_root,
    )
    assert execution["status"] == "quiet"
    assert execution["mutation_applied"] is True

    fresh_signal = coverage_signal_from_observation(observation(owner_revision=execution["post_owner_revision"]))
    fresh = bounded_adaptation_projection([fresh_signal], target_root=case_root)
    assert fresh["status"] == "quiet"
    assert fresh["candidates"][0]["persisted_disposition"]["status"] == "current"
    assert (
        compile_context_maintenance_decision(context_projection={"currentness": {"decision_requirements": []}}, bounded_adaptations=fresh)[
            "status"
        ]
        == "not-required"
    )

    instruction.write_text(instruction.read_text(encoding="utf-8") + "\nSource semantics changed.\n", encoding="utf-8")
    changed_revision = read_instruction(instruction, root=case_root).revision
    stale = bounded_adaptation_projection(
        [coverage_signal_from_observation(observation(owner_revision=changed_revision))], target_root=case_root
    )
    assert stale["candidates"][0]["status"] == "owner-review-required"
    assert stale["candidates"][0]["persisted_disposition"]["status"] == "stale"


def test_defer_choice_persists_until_reentry_trigger_changes(tmp_path: Path) -> None:
    instruction = tmp_path / ".agentic-workspace/instructions/api.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\npaths:\n  - src/api/**\n---\n\n# API\n\nKeep current guidance.\n", encoding="utf-8")
    revision = read_instruction(instruction, root=tmp_path).revision

    def signal(trigger: str, owner_revision: str):
        return coverage_signal_from_observation(
            {
                "source_class": "agent",
                "owner_class": "scoped-instruction",
                "source_owner": ".agentic-workspace/instructions/api.md",
                "observed_addition": "API v2 compatibility may need guidance.",
                "source_refs": ["src/api/v2/router.py"],
                "evidence_refs": ["review:api-boundary"],
                "affected_effects": ["procedure"],
                "operation_id": "instructions.create",
                "owner_revision": owner_revision,
                "recurrence_identity": "api-v2-defer",
                "defer_until": trigger,
                "proposed_delta": {
                    "action": "append_guidance",
                    "heading": "API v2 compatibility",
                    "guidance": "Run compatibility proof.",
                    "positive_paths": ["src/api/v2/router.py"],
                    "negative_paths": ["docs/api.md"],
                },
                "validation_route": ["pytest tests/test_api.py -q"],
            }
        )

    projection = bounded_adaptation_projection([signal("next API v2 change", revision)], target_root=tmp_path)
    candidate = projection["candidates"][0]
    decision = compile_context_maintenance_decision(
        context_projection={"currentness": {"decision_requirements": []}}, bounded_adaptations=projection
    )
    assert "defer" in {item["id"] for item in decision["alternatives"]}
    execution = execute_bounded_adaptation(
        admit_bounded_adaptation(
            candidate,
            admitted_by="instruction-owner",
            choice="defer",
            decision_revision=decision["decision_revision"],
            defer_until="next API v2 change",
        ),
        target_root=tmp_path,
    )
    assert execution["status"] == "deferred"
    fresh = bounded_adaptation_projection([signal("next API v2 change", execution["post_owner_revision"])], target_root=tmp_path)
    assert fresh["status"] == "quiet"
    changed_trigger = bounded_adaptation_projection([signal("next API v3 change", execution["post_owner_revision"])], target_root=tmp_path)
    assert changed_trigger["candidates"][0]["status"] == "owner-review-required"
    assert changed_trigger["candidates"][0]["persisted_disposition"]["status"] == "stale-trigger-changed"


def test_draft_operation_cannot_be_labeled_or_executed_as_automatic_authority(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import adaptation

    operation_root = tmp_path / "operations"
    operation_root.mkdir()
    contract = json.loads(Path("src/agentic_workspace/contracts/operations/proof.report.json").read_text(encoding="utf-8"))
    contract["migration_status"] = "draft-contract-only"
    (operation_root / "proof.report.json").write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(adaptation, "_OPERATION_CONTRACT_ROOT", operation_root)

    candidate = bounded_adaptation_projection([_signal()])["candidates"][0]

    assert candidate["status"] == "owner-review-required"
    assert candidate["promotion"]["operation_registered"] is True
    assert candidate["promotion"]["operation_runtime_consumed"] is False
    candidate["status"] = "promotion-ready"
    with pytest.raises(ValueError, match="not runtime-consumed authority"):
        execute_bounded_adaptation(candidate, target_root=tmp_path)


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


def test_route_health_constructs_bounded_candidate_only_from_safe_refinement_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace import workspace_runtime_proof

    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("schema_version = 1\n", encoding="utf-8")
    changed_paths = ["src/example.py"]
    test_path = tmp_path / "tests" / "test_example.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("def test_example():\n    assert True\n", encoding="utf-8")
    common = {
        "command": "make test-workspace",
        "lane": "domain:example",
        "route_id": "domain:example",
        "route_refinement_evidence": {
            "classification": "subsumed",
            "subsumed_by": "pytest tests/test_example.py -q",
            "distinct_evidence": "none beyond the focused owner test",
            "semantic_delta": {
                "action": "upsert_domain_lane",
                "lane_id": "example",
                "lane": {
                    "purpose": "Focused example proof.",
                    "applies_to_paths": changed_paths,
                    "commands": ["pytest tests/test_example.py -q"],
                },
            },
            "simulation": {
                "required_behaviors": ["example-owner-claim"],
                "preserved_behaviors": ["example-owner-claim"],
                "authority_delta": "none",
                "allowed_owner_paths": [".agentic-workspace/config.toml"],
                "before_cost": 600,
                "after_cost": 20,
                "before_precision": 0.2,
                "after_precision": 1.0,
            },
            "expected_effect": {"required_coverage": "preserved", "summed_work_seconds": "lower"},
        },
    }
    focused = {
        "command": "pytest tests/test_example.py -q",
        "lane": "domain:example",
        "route_id": "domain:example",
        "claim_boundary": "example-owner-claim",
    }
    health = workspace_runtime_proof._proof_route_health_payload(
        selected_commands=[common, focused],
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

    healthy_health = workspace_runtime_proof._proof_route_health_payload(
        selected_commands=[focused],
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
    healthy_projection = bounded_adaptation_projection(
        [item["bounded_adaptation_signal"] for item in healthy_health["findings"] if item.get("bounded_adaptation_signal")]
    )
    assert healthy_health["status"] == "quiet"
    assert healthy_health["repair_packets"] == []
    assert healthy_projection["candidate_count"] == 0
    assert healthy_projection["first_line_cost"] == "none"
    assert [item["command"] for item in [focused]] == ["pytest tests/test_example.py -q"]
    assert not (tmp_path / ".agentic-workspace/local/proof-route-repairs/history.jsonl").exists()

    finding = next(item for item in health["findings"] if item.get("bounded_adaptation_signal"))
    candidate = bounded_adaptation_projection([finding["bounded_adaptation_signal"]])["candidates"][0]
    assert candidate["status"] == "promotion-ready"
    assert candidate["proposed_delta"]["lane"]["commands"] == ["pytest tests/test_example.py -q"]
    assert candidate["authority_requirement"]["expected_owner_revision"] == finding["route_authority_revision"]
    assert len([common, focused]) == 2
    assert candidate["simulation"]["required_behaviors"] == candidate["simulation"]["preserved_behaviors"]

    previous_config = config_path.read_bytes()
    stale_candidate = deepcopy(candidate)
    stale_candidate["authority_requirement"]["expected_owner_revision"] = "stale-route-authority"
    stale_execution = execute_bounded_adaptation(stale_candidate, target_root=tmp_path)
    assert stale_execution["status"] == "superseded"
    assert stale_execution["operation_result"]["status"] == "blocked-stale-authority-revision"
    assert config_path.read_bytes() == previous_config
    assert candidate["simulation"]["required_behaviors"] == candidate["simulation"]["preserved_behaviors"]

    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (['python -c "import sys; sys.exit(1)"'], "test-independent-validation-owner"),
    )
    with pytest.raises(workspace_runtime_proof.WorkspaceUsageError, match="validation command failed"):
        execute_bounded_adaptation(candidate, target_root=tmp_path)
    assert config_path.read_bytes() == previous_config
    assert not (tmp_path / ".agentic-workspace/local/proof-route-repairs/history.jsonl").exists()

    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (["python -c \"print('independent ok')\""], "test-independent-validation-owner"),
    )
    execution = execute_bounded_adaptation(candidate, target_root=tmp_path)
    assert execution["status"] == "quiet"
    assert execution["operation_id"] == "proof.report"
    assert execution["validation_status"] == "passed"
    assert execution["operation_result"]["apply_receipt"]["validation_authority"] == "test-independent-validation-owner"

    replay_candidate = deepcopy(candidate)
    replay_candidate["authority_requirement"]["expected_owner_revision"] = execution["post_owner_revision"]
    replay_candidate["authority_requirement"]["current_owner_revision"] = execution["post_owner_revision"]
    idempotent_execution = execute_bounded_adaptation(replay_candidate, target_root=tmp_path)
    assert idempotent_execution["status"] == "quiet"
    assert idempotent_execution["operation_result"]["status"] == "already-applied"
    assert idempotent_execution["operation_result"]["apply_receipt"] == execution["operation_result"]["apply_receipt"]

    canonical = tomllib.loads(config_path.read_text(encoding="utf-8"))
    canonical_lane = canonical["assurance"]["domain_proof_lanes"]["example"]
    later_commands = [
        {
            "command": command,
            "lane": "domain:example",
            "route_id": "domain:example",
            "claim_boundary": "example-owner-claim",
        }
        for command in canonical_lane["commands"]
    ]
    later_health = workspace_runtime_proof._proof_route_health_payload(
        selected_commands=later_commands,
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
    assert [item["command"] for item in later_commands] == ["pytest tests/test_example.py -q"]
    assert len(later_commands) < 2
    assert not any(item.get("bounded_adaptation_signal") for item in later_health["findings"])
    assert all(item.get("command") != "make test-workspace" for item in later_commands)

    ambiguous = deepcopy(common)
    ambiguous["route_refinement_evidence"] = {"classification": "ambiguous"}
    ambiguous_health = workspace_runtime_proof._proof_route_health_payload(
        selected_commands=[ambiguous],
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
    assert not any(item.get("bounded_adaptation_signal") for item in ambiguous_health["findings"])
    assert ambiguous_health["findings"][-1]["consequence"] == "proof-owner-decision-required"
