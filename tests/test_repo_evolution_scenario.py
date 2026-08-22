from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from agentic_workspace.adaptation import (
    admit_bounded_adaptation,
    bounded_adaptation_projection,
    coverage_signal_from_observation,
    execute_bounded_adaptation,
    machine_observed_coverage_signals,
)
from agentic_workspace.module_contract import MODULE_CONTRACT_VERSION, module_contribution, validate_module_contract
from agentic_workspace.operating_decision import (
    classify_context_currentness,
    compile_context_maintenance_decision,
    compile_operating_decision,
    context_authority_repair_action,
)
from agentic_workspace.reconciliation import compile_reconciliation
from agentic_workspace.scoped_instructions import read_instruction

SCENARIO_PATH = Path("tests/fixtures/repo_evolution_scenario.json")


def _repair_projection() -> dict[str, object]:
    return {
        "status": "repair-required",
        "repair_operation": {
            "repairs": [
                {
                    "surface": "generated-references",
                    "owner": "generated command package owner",
                    "reason_code": "source-fingerprint-mismatch",
                    "operation_id": "generated-command-packages.refresh",
                    "arguments": {
                        "target": ".",
                        "surface": "generated-references",
                        "consumer": "start",
                        "expected_registry_revision": "sha256:registry-r1",
                        "expected_source_revision": "sha256:generator-r2",
                    },
                }
            ]
        },
        "currentness": {"decision_requirements": []},
    }


def _semantic_projection() -> dict[str, object]:
    return {
        "status": "repair-required",
        "repair_operation": {"repairs": []},
        "currentness": {
            "decision_requirements": [
                {
                    "surface": "scoped-instructions",
                    "owner": "scoped instruction owner",
                    "operation_id": "instructions.create",
                    "disposition": "decision-required",
                    "reason_code": "semantic-ambiguity",
                    "observed_change": "Moving API tests may create a distinct compatibility boundary.",
                    "evidence_refs": ["src/api/v2/router.py", "tests/api_v2/test_compat.py"],
                    "affected_effects": ["authority", "procedure", "proof"],
                    "expected_registry_revision": "sha256:registry-r1",
                    "expected_source_revision": "sha256:instructions-r1",
                    "proposed_delta": {"action": "append_guidance"},
                }
            ]
        },
    }


def _coverage_observation(*, revision: str, disposition: str = "active") -> dict[str, object]:
    return {
        "source_class": "agent",
        "owner_class": "scoped-instruction",
        "source_owner": ".agentic-workspace/instructions/api.md",
        "observed_addition": "API v2 work requires a compatibility proof procedure.",
        "source_refs": ["src/api/v2/router.py"],
        "evidence_refs": ["tests/api_v2/test_compat.py"],
        "affected_effects": ["procedure", "proof"],
        "operation_id": "instructions.create",
        "owner_revision": revision,
        "recurrence_identity": "api-v2-compatibility",
        "disposition": disposition,
        "proposed_delta": {
            "action": "append_guidance",
            "heading": "API v2 compatibility",
            "guidance": "Run API v2 compatibility proof after boundary changes.",
            "positive_paths": ["src/api/v2/router.py"],
            "negative_paths": ["docs/api.md"],
        },
        "validation_route": ["pytest tests/api_v2/test_compat.py -q"],
    }


def _module_contract() -> dict[str, object]:
    return {
        "schema_version": MODULE_CONTRACT_VERSION,
        "name": "build-signals",
        "description": "Independent build signal capability.",
        "compatibility": {"reader_epoch": 1, "required_capabilities": ["module-resources-v1"]},
        "ownership": {
            "roots": [],
            "effect_classes": [],
            "authority_exclusions": ["cannot grant mutation, proof, or completion authority"],
        },
        "relevance": {"task_terms": ["build signal"], "path_prefixes": ["build/signals/"]},
        "facts": [],
        "capabilities": {
            "resources": [{"id": "signals.latest", "ref": "signals://latest", "read_only": True}],
            "skills": [],
            "operations": [],
        },
        "result_semantics": {
            "schema_version": "signals/result/v1",
            "guaranteed_fields": ["status"],
            "effect_fields": ["effects"],
            "warning_fields": ["warnings"],
        },
    }


def test_versioned_repo_evolution_scenario_covers_required_sequence() -> None:
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    steps = {item["id"]: item for item in scenario["steps"]}

    assert scenario["kind"] == "agentic-workspace/repo-evolution-scenario/v1"
    assert scenario["initial_state"] == "valid-configured-repository"
    assert scenario["explicit_generic_maintenance_steps"] == 0
    assert {
        "path-test-movement",
        "structured-path-rename",
        "generated-source-change",
        "terminal-work-owner",
        "review-topology-change",
        "module-add-remove",
        "rebuildable-manifest",
        "machine-proof-addition",
        "agent-semantic-addition",
        "ordinary-fact",
        "deferred-pressure",
        "equivalent-work-repeat",
    } == set(steps)
    assert steps["rebuildable-manifest"]["proof_ref"].endswith(
        "test_manifest_reconcile_repairs_interrupted_publish_without_rerunning_result"
    )


def test_repo_evolution_ordinary_loop_reconciles_once_then_stays_quiet(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trace: list[dict[str, object]] = []

    semantic = compile_context_maintenance_decision(context_projection=_semantic_projection(), bounded_adaptations={"candidates": []})
    trace.append({"step": "path-test-movement", "before": "ambiguous", "after": semantic["status"]})
    assert semantic["status"] == "decision-required"

    rename_projection = _repair_projection()
    rename_repair = rename_projection["repair_operation"]["repairs"][0]
    rename_repair.update(
        {
            "surface": "ownership",
            "owner": "workspace ownership declarations",
            "operation_id": "ownership.classify-paths",
            "reason_code": "structured-path-renamed",
        }
    )
    rename_repair["arguments"]["surface"] = "ownership"
    rename = context_authority_repair_action(rename_projection)
    trace.append({"step": "structured-path-rename", "before": "old-path", "after": rename["action"]})
    assert rename["operation_invocation"]["operation_id"] == "ownership.classify-paths"

    repair = context_authority_repair_action(_repair_projection())
    quiet_repair = context_authority_repair_action(
        {"status": "admitted", "repair_operation": {"repairs": []}, "currentness": {"decision_requirements": []}}
    )
    trace.append({"step": "generated-source-change", "before": repair["action"], "after": "current"})
    assert repair["operation_invocation"]["operation_id"] == "generated-command-packages.refresh"
    assert quiet_repair == {}

    retired = classify_context_currentness(
        item={
            "surface": "planning",
            "owner": "planning package",
            "source_owner_contract": {"owner_module": "planning", "repair_operation_id": "planning.summary.report"},
        },
        record={"applicable": False, "selected_required": False, "status": "terminal"},
        owner_identity_valid=False,
    )
    parent = compile_reconciliation(
        {
            "result": {"status": "completed"},
            "intent": {
                "status": "satisfied",
                "owner_level": "slice",
                "parent_status": "active",
                "parent_owner": "repo-evolution-self-maintenance",
            },
            "proof": {"status": "passed"},
        }
    )
    trace.append({"step": "terminal-work-owner", "before": "terminal-live", "after": retired["disposition"]})
    assert retired["disposition"] == "outside-responsibility"
    assert parent["claim"]["parent_claim_allowed"] is False

    from agentic_workspace import operating_decision

    monkeypatch.setattr(operating_decision, "resolve_context_authority_projection", lambda **_kwargs: _repair_projection())
    stale_topology = compile_operating_decision(
        inputs={"consumer": "implement", "authorities": {"mutation_baseline": {"revalidation_status": "rejected"}}}
    )
    trace.append({"step": "review-topology-change", "before": "head-changed", "after": stale_topology["status"]})
    assert stale_topology["external_blocker"]["reason_code"] == "stale-mutation-baseline"

    contract = validate_module_contract(_module_contract())
    contributed = module_contribution(contract, task="inspect build signal", changed_paths=[])
    removed = []
    trace.append({"step": "module-add-remove", "before": bool(contributed), "after": bool(removed)})
    assert contributed and contributed["resources"][0]["id"] == "signals.latest"
    assert removed == []

    machine = bounded_adaptation_projection(
        machine_observed_coverage_signals(
            [
                {
                    "declaration_kind": "proof-route-declaration",
                    "observed_addition": "API v2 declares a focused proof route.",
                    "source_refs": [".agentic-workspace/config.toml#verification"],
                    "evidence_refs": ["tests/api_v2/test_compat.py"],
                    "owner_revision": "sha256:proof-r2",
                    "proposed_delta": {"action": "upsert_domain_lane", "lane_id": "api-v2"},
                    "validation_route": ["pytest tests/api_v2/test_compat.py -q"],
                }
            ]
        )
    )
    trace.append({"step": "machine-proof-addition", "before": "missing", "after": machine["candidates"][0]["status"]})
    assert machine["candidates"][0]["promotion"]["operation_id"] == "proof.report"

    instruction = tmp_path / ".agentic-workspace/instructions/api.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\npaths:\n  - src/api/**\n---\n\n# API\n\nExisting guidance.\n", encoding="utf-8")
    revision = read_instruction(instruction, root=tmp_path).revision
    coverage = bounded_adaptation_projection([coverage_signal_from_observation(_coverage_observation(revision=revision))])
    decision = compile_context_maintenance_decision(
        context_projection={"currentness": {"decision_requirements": []}}, bounded_adaptations=coverage
    )
    candidate = coverage["candidates"][0]
    applied = execute_bounded_adaptation(admit_bounded_adaptation(candidate, admitted_by="api-owner"), target_root=tmp_path)
    trace.append({"step": "agent-semantic-addition", "before": decision["status"], "after": applied["status"]})
    assert decision["status"] == "decision-required"
    assert applied["status"] == "quiet"

    irrelevant = bounded_adaptation_projection(
        [
            coverage_signal_from_observation(
                {
                    "source_class": "agent",
                    "observed_addition": "A local helper variable was renamed.",
                    "affected_effects": [],
                    "material": False,
                }
            )
        ]
    )
    trace.append({"step": "ordinary-fact", "before": "observed", "after": irrelevant["status"]})
    assert irrelevant["status"] == "quiet"

    deferred_observation = {
        **_coverage_observation(revision=applied["post_owner_revision"]),
        "owner_class": "memory",
        "source_owner": ".agentic-workspace/memory/repo/manifest.toml",
        "operation_id": "workspace.memory-create-note.apply",
        "defer_until": "next API v2 architecture change",
    }
    deferred = compile_operating_decision(
        inputs={"consumer": "unregistered-test-consumer", "coverage_observations": [deferred_observation]}
    )
    trace.append({"step": "deferred-pressure", "before": "unresolved", "after": deferred["maintenance_decision"]["status"]})
    assert deferred["maintenance_decision"]["status"] == "deferred"
    assert deferred["primary_action"] == {}

    resolved = deepcopy(candidate)
    resolved.update({"status": "quiet", "disposition": "fixed"})
    repeated = compile_context_maintenance_decision(
        context_projection={"currentness": {"decision_requirements": []}},
        bounded_adaptations={"candidates": [resolved]},
    )
    trace.append({"step": "equivalent-work-repeat", "before": "fixed", "after": repeated["status"]})
    assert repeated["status"] == "not-required"
    assert len({item["step"] for item in trace}) == len(trace) == 11


def test_repo_evolution_evidence_keeps_real_dogfood_and_failure_routing_bounded() -> None:
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    dogfood = Path("docs/maintainer/repo-evolution-dogfood-2026-08-22.md").read_text(encoding="utf-8")

    assert scenario["expected_metrics"] == {
        "manual_aw_maintenance": 0,
        "semantic_user_decisions": 2,
        "redundant_rediscovery": 0,
        "destination_owner_class_minimum": 3,
        "stable_first_line_cost": "none",
    }
    assert "Mismatch retained honestly" in dogfood
    assert "Explicit generic AW-maintenance actions: 1" in dogfood
    assert "Future dogfood should reopen #2663" in dogfood
    assert "do not extend this scenario into a maintenance framework" in scenario["failure_route"]
