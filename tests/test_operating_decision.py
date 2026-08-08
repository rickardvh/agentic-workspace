from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace.actionability import (
    derive_actionability,
    invocation_decision_input_revision,
    operation_invocation,
    proposed_action_input_revision,
)
from agentic_workspace.operating_decision import (
    _resolve_context_authority_source,
    bind_operation_invocation_to_authorities,
    compile_operating_decision,
    context_authority_coverage,
    context_authority_declarations,
    context_surface_admission,
    derive_context_gaps,
    derive_operating_blockers_from_authorities,
    live_decision_input_revision,
    resolve_context_authority_projection,
)

SCHEMA_ROOT = Path("src/agentic_workspace/contracts/schemas")


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def _fixture_source_revision(path: Path) -> str:
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(child.relative_to(path).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(child.read_bytes()).hexdigest().encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _live_mutation_baseline(*, allowed_paths: list[str] | None = None) -> dict[str, object]:
    paths = allowed_paths or ["src/app.py"]
    return {
        "kind": "agentic-workspace/mutation-baseline/v1",
        "status": "clean-scope",
        "revalidation_status": "current",
        "baseline_id": "baseline-a",
        "head": "abc123",
        "scope": {"allowed_paths": paths, "path_count": len(paths), "comparison": "changed-path-scope"},
        "observation": {"ok": True},
        "observed_state": {"entry_count": 0, "enforcement_fingerprint": "fingerprint-a"},
        "boundary_enforcement": {"status": "fail-closed-contract"},
        "stale_revalidation": {"status": "required"},
        "ownership": {"owner": "current-agent-session"},
    }


def test_operating_decision_emits_one_typed_primary_action() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        effect_class="read-only-report",
        authority_class="verification-owned",
        expected_transition="proof status refreshed",
        preconditions={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        owner_context_revision={"owner_id": "owner-a", "target_identity_ref": "target-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report", "writes_repo_state": False},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json", "owner": "verification"}],
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
    assert decision["primary_action"]["operation_invocation"]["authority_class"] == "verification-owned"
    assert decision["primary_action"]["operation_invocation"]["preconditions"]["assignment_context_key"] == "ctx-a"
    assert decision["primary_action"]["operation_invocation"]["owner_context_revision"]["target_identity_ref"] == "target-a"
    assert decision["primary_action"]["operation_invocation"]["proof_requirements"][0]["owner"] == "verification"
    assert decision["canonical_decision_input_revision"] == invocation_decision_input_revision(invocation)
    assert decision["context_authority_coverage"]["status"] == "measured"
    assert "status" in decision["context_authority_coverage"]["ordinary_consumers"]
    assert decision["primary_action"]["operation_invocation"]["stale_action_rejection"]["status"] == "reject-on-input-revision-mismatch"
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


def test_caller_supplied_invocation_revision_is_ignored() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        effect_class="read-only-report",
        authority_class="verification-owned",
        input_revision="old-input-digest",
        expected_transition="proof status refreshed",
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )

    assert invocation["expected_input_revision"] == invocation_decision_input_revision(invocation)
    assert invocation["expected_input_revision"] != "old-input-digest"
    assert invocation["stale_action_rejection"]["caller_supplied_input_revision"] == "old-input-digest"
    assert invocation["stale_action_rejection"]["caller_revision_authority"] == "ignored"


def test_live_authority_revision_drift_is_rejected_before_execution() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        effect_class="read-only-report",
        authority_class="verification-owned",
        expected_transition="proof status refreshed",
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )
    live_authorities = {
        "planning_owner": {"owner_id": "owner-a", "owner_revision": "rev-owner-b"},
        "assignment": {"assignment_revision": "assign-b", "target_identity_ref": "target-a"},
        "mutation_baseline": {"baseline_id": "baseline-b", "revalidation_status": "fresh"},
        "proof": {"proof_subject_fingerprint": "proof-b", "receipt_status": "fresh"},
        "evaluation": {"freshness_status": "not-required", "required": False},
        "executor": {"binding_fingerprint": "executor-b", "availability_status": "available"},
    }
    proposed_next_action = {"action": "run-proof", "operation_invocation": invocation}
    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action=proposed_next_action,
        current_input_revision=live_decision_input_revision(invocation=invocation, authorities=live_authorities),
    )

    decision = compile_operating_decision(
        inputs={
            "revisions": {"current_work": "rev-a", "proof": "rev-proof"},
            "actionability": actionability,
            "authorities": live_authorities,
        }
    )

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["live_revision_checked"] is True
    assert actionability["progress_check"]["live_input_revision"] == live_decision_input_revision(
        invocation=invocation, authorities=live_authorities
    )
    assert actionability["progress_check"]["live_input_revision"] != invocation["expected_input_revision"]
    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"]["reason_code"] == "stale-revision"
    assert "refresh the operating decision" in decision["external_blocker"]["repair"]


def test_actionability_rejects_typed_action_against_live_revision_drift() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"baseline_id": "baseline-a"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )

    proposed_next_action = {
        "action": "run-proof",
        "operation_invocation": invocation,
    }
    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action=proposed_next_action,
        current_input_revision="sha256:live-authority-changed",
    )

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["live_revision_checked"] is True
    assert actionability["progress_check"]["live_input_revision"] == "sha256:live-authority-changed"
    assert actionability["next_action"]["action"] == "required-action-unavailable"


def test_actionability_rejects_typed_action_when_live_revision_is_missing() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"baseline_id": "baseline-a"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )

    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action={"action": "run-proof", "operation_invocation": invocation},
    )

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["live_revision_checked"] is False
    assert actionability["progress_check"]["live_revision_missing"] is True
    assert actionability["next_action"]["missing_precondition"] == (
        "live authority revision resolved immediately before actionability derivation"
    )


def test_missing_expected_revision_is_rejected_before_execution() -> None:
    invocation = operation_invocation(
        operation_id="proof.report",
        arguments={"target": ".", "format": "json"},
        owner_context_revision={"owner_id": "owner-a", "assignment_context_key": "ctx-a"},
        mutation_boundary={"effect": "read-only-report"},
        proof_requirements=[{"command": "agentic-workspace proof --target . --format json"}],
    )
    invocation.pop("expected_input_revision")
    proposed_next_action = {"action": "run-proof", "operation_invocation": invocation}
    actionability = derive_actionability(
        command_name="implement",
        health="attention-needed",
        warnings=[],
        repair_actions=[{"id": "proof-missing"}],
        manual_review_actions=[],
        proposed_next_action=proposed_next_action,
        current_input_revision=proposed_action_input_revision(proposed_next_action),
    )

    decision = compile_operating_decision(inputs={"actionability": actionability})

    assert actionability["progress_check"]["result"] == "rejected-stale-action"
    assert actionability["progress_check"]["expected_input_revision"] == ""
    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "stale-revision"


def test_context_authority_declarations_and_gap_classes_validate() -> None:
    declarations = context_authority_declarations()
    coverage = context_authority_coverage()
    registry_schema = _schema("context_authority_registry.schema.json")
    registry = json.loads(Path("src/agentic_workspace/contracts/context_authority_registry.json").read_text(encoding="utf-8"))
    Draft202012Validator(registry_schema).validate(registry)
    declaration_schema = _schema("context_authority_declaration.schema.json")
    for declaration in declarations:
        Draft202012Validator(declaration_schema).validate(declaration)

    assert "implement" in coverage["ordinary_consumers"]
    assert "autopilot-executor" in coverage["surfaces"]
    assert {"architecture-principles", "scoped-instructions", "ownership"}.issubset(set(coverage["surfaces"]))
    assert coverage["registry_authority"] == "versioned-contract"
    assert coverage["registry_source"] == "src/agentic_workspace/contracts/context_authority_registry.json"

    assert set(coverage["ordinary_consumers"]) == set(registry["ordinary_decision_consumers"])
    assert {"contract-checks", "skills"}.issubset(set(coverage["ordinary_consumers"]))
    assert coverage["missing_required_sources"] == {}
    for consumer in coverage["ordinary_consumers"]:
        assert set(coverage["consumer_requirements"][consumer]).issubset(set(coverage["consumer_to_surfaces"][consumer]))
    assert {"architecture-principles", "scoped-instructions", "ownership"}.issubset(set(coverage["consumer_requirements"]["start"]))
    assert all("source_owner_contract" in surface for surface in registry["surfaces"])
    gaps = derive_context_gaps(
        declarations=declarations,
        selected_surfaces=[
            {
                "surface": "memory",
                "admitted_state": context_surface_admission(
                    surface="memory",
                    source_kind="memory-route",
                    source_id="memory/repo/index.md",
                    source_revision="rev-memory",
                    authority_owner="memory package",
                    requirement_status="required",
                    population_status="missing",
                ),
                "affected_decisions": ["reuse"],
            },
            {
                "surface": "system-intent",
                "admitted_state": context_surface_admission(
                    surface="system-intent",
                    source_kind="system-intent",
                    source_id="intent.toml",
                    source_revision="rev-intent",
                    authority_owner="workspace-system-intent",
                    requirement_status="required",
                    population_status="below-minimum",
                ),
            },
            {
                "surface": "undiscovered-surface",
                "admitted_state": context_surface_admission(
                    surface="undiscovered-surface",
                    source_kind="test-fixture",
                    source_id="fixture",
                    source_revision="rev-undiscovered",
                    authority_owner="fixture",
                    requirement_status="required",
                    population_status="present",
                ),
            },
            {
                "surface": "proof",
                "admitted_state": context_surface_admission(
                    surface="proof",
                    source_kind="proof-resolver",
                    source_id="proof.report",
                    source_revision="rev-proof",
                    authority_owner="verification and proof runtime",
                    freshness_status="inference-fallback",
                ),
            },
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


def test_runtime_actionability_call_sites_resolve_live_revision_before_derivation() -> None:
    """Static guard for ordinary boundaries that would otherwise reuse stale typed actions."""

    production_sources = [
        path for path in Path("src/agentic_workspace").rglob("*.py") if path.name != "actionability.py" and "tests" not in path.parts
    ]
    call_sites: list[str] = []
    missing_live_revision: list[str] = []
    for path in production_sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if name != "derive_actionability":
                continue
            location = f"{path.as_posix()}:{node.lineno}"
            call_sites.append(location)
            if not any(keyword.arg == "current_input_revision" for keyword in node.keywords):
                missing_live_revision.append(location)

    assert call_sites
    assert missing_live_revision == []


def test_context_gap_derivation_rejects_caller_shaped_status_without_admitted_source() -> None:
    gaps = derive_context_gaps(
        declarations=context_authority_declarations(),
        selected_surfaces=[
            {
                "surface": "proof",
                "admitted_state": {
                    "requirement_status": "required",
                    "population_status": "missing",
                    "severity": "advisory",
                    "next_route": "caller-supplied route should not be trusted",
                },
            }
        ],
    )

    assert [gap["gap_class"] for gap in gaps] == ["coverage-gap"]
    assert gaps[0]["severity"] == "blocking"
    assert gaps[0]["owner"] == "context-authority-coverage"
    assert "canonical context-surface adapter" in gaps[0]["next_route"]


def test_context_authority_coverage_fails_when_required_consumer_source_is_missing() -> None:
    coverage = context_authority_coverage(
        declarations=[item for item in context_authority_declarations() if item["surface"] != "proof"],
        consumer_requirements={"proof": ["planning", "proof"]},
        observed_consumers=["proof"],
    )

    assert coverage["status"] == "coverage-gap"
    assert coverage["missing_required_sources"] == {"proof": ["proof"]}


def test_blocking_context_gap_prevents_primary_action() -> None:
    gaps = derive_context_gaps(
        declarations=context_authority_declarations(),
        selected_surfaces=[
            {
                "surface": "proof",
                "admitted_state": context_surface_admission(
                    surface="proof",
                    source_kind="proof-resolver",
                    source_id="proof.report",
                    source_revision="rev-proof",
                    authority_owner="verification and proof runtime",
                    requirement_status="required",
                    population_status="missing",
                ),
            }
        ],
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


@pytest.mark.parametrize(
    ("case_id", "authorities", "blocker"),
    [
        (
            "unknown-no-safe-target",
            {"target": {"status": "unknown"}},
            {"reason_code": "missing-capability", "owner": "assignment target", "repair": "select a safe target"},
        ),
        (
            "disabled-manual-required-transport",
            {
                "assignment": {"status": "handoff-required", "handoff_admission_status": "admitted"},
                "manual_transport": {"status": "disabled"},
            },
            {},
        ),
        (
            "stale-worktree-baseline",
            {"mutation_baseline": {"revalidation_status": "rejected"}},
            {"reason_code": "stale-mutation-baseline", "owner": "mutation authority", "repair": "refresh baseline"},
        ),
        (
            "missing-evaluation",
            {"evaluation": {"freshness_status": "missing", "required": True}},
            {"reason_code": "context-coverage-gap", "owner": "evaluation", "repair": "register evaluation"},
        ),
        (
            "not-required-evaluation",
            {"evaluation": {"freshness_status": "not-required", "required": False}},
            {},
        ),
        (
            "superseded-evaluation",
            {"evaluation": {"freshness_status": "superseded"}},
            {"reason_code": "stale-revision", "owner": "evaluation", "repair": "rerun evaluation"},
        ),
        (
            "stale-planning-owner",
            {"planning_owner": {"freshness_status": "stale"}},
            {"reason_code": "stale-revision", "owner": "planning owner", "repair": "reselect owner"},
        ),
        (
            "invalid-receipt",
            {"proof": {"receipt_status": "invalid"}},
            {"reason_code": "stale-proof", "owner": "proof receipt", "repair": "rerun proof"},
        ),
        (
            "unavailable-rebound-executor",
            {"executor": {"availability": {"status": "unavailable"}}},
            {"reason_code": "missing-capability", "owner": "autopilot executor", "repair": "rebind executor"},
        ),
    ],
)
def test_operating_decision_context_gap_recovery_matrix_blocks_invalid_actions(
    case_id: str, authorities: dict, blocker: dict[str, str]
) -> None:
    invocation = operation_invocation(
        operation_id="implement",
        arguments={"target": ".", "task": case_id},
        effect_class="repo-mutation",
        authority_class="hard-gate",
        expected_transition="valid terminal recovery",
        preconditions={"case": case_id},
        owner_context_revision={"case": case_id, "owner_id": "owner-a"},
        mutation_boundary={"case": case_id, "writes_repo_state": True},
        proof_requirements=[{"command": "make typecheck", "case": case_id}],
    )

    decision = compile_operating_decision(
        inputs={
            "revisions": {"case": case_id, "owner": "rev-a"},
            "actionability": {"next_action": {"action": "recover-context-gap", "operation_invocation": invocation}},
            "authorities": authorities,
        }
    )

    expected_blockers = [] if not blocker else [blocker]
    assert derive_operating_blockers_from_authorities(authorities=authorities) == expected_blockers
    if blocker:
        assert decision["status"] == "blocked"
        assert decision["primary_action"] == {}
        assert decision["external_blocker"]["reason_code"] == blocker["reason_code"]
        assert decision["external_blocker"]["owner"] == blocker["owner"]
        assert decision["external_blocker"]["repair"] == blocker["repair"]
    else:
        assert decision["status"] == "blocked"
        assert decision["external_blocker"]["reason_code"] == "stale-revision"


def test_admitted_handoff_and_not_required_evaluation_can_reach_actionable_terminal_recovery() -> None:
    authorities = {
        "planning_owner": {"owner_id": "owner-a", "owner_revision": "rev-owner-a"},
        "assignment": {
            "status": "handoff-required",
            "handoff_admission_status": "admitted",
            "assignment_revision": "assign-a",
            "target_identity_ref": "target-a",
        },
        "manual_transport": {"status": "disabled", "handoff_admission_status": "admitted"},
        "mutation_baseline": _live_mutation_baseline(),
        "proof": {"proof_subject_fingerprint": "proof-a", "receipt_status": "fresh"},
        "evaluation": {"freshness_status": "not-required", "required": False},
        "executor": {"binding_fingerprint": "executor-a", "availability_status": "available"},
    }
    invocation = operation_invocation(
        operation_id="handoff.prepare",
        arguments={"target": ".", "format": "json"},
        effect_class="manual-handoff",
        authority_class="assignment-gate",
        expected_transition="handoff prepared",
    )
    bound_invocation = bind_operation_invocation_to_authorities(invocation=invocation, authorities=authorities)

    decision = compile_operating_decision(
        inputs={
            "actionability": {"next_action": {"action": "prepare-handoff", "operation_invocation": bound_invocation}},
            "authorities": authorities,
        }
    )

    assert derive_operating_blockers_from_authorities(authorities=authorities) == []
    assert decision["status"] == "actionable"
    assert decision["primary_action"]["operation_invocation"]["operation_id"] == "handoff.prepare"
    assert decision["canonical_decision_input_revision"] == bound_invocation["expected_input_revision"]


def test_repo_mutation_action_requires_live_mutation_baseline() -> None:
    invocation = operation_invocation(
        operation_id="implement.apply",
        arguments={"target": ".", "changed": ["src/app.py"]},
        effect_class="repo-mutation",
        authority_class="mutation-gate",
        mutation_boundary={"writes_repo_state": True, "allowed_paths": ["src/app.py"]},
    )

    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "actionability": {"next_action": {"action": "implement", "operation_invocation": invocation}},
            "authorities": {},
        }
    )

    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"]["reason_code"] == "stale-mutation-baseline"
    assert decision["external_blocker"]["repair"] == "resolve and revalidate a live mutation baseline before admitting this typed action"


def test_bound_repo_mutation_preserves_typed_action_identity() -> None:
    authorities = {"mutation_baseline": _live_mutation_baseline()}
    invocation = operation_invocation(
        operation_id="implement.apply",
        arguments={"target": ".", "changed": ["src/app.py"]},
        effect_class="repo-mutation",
        authority_class="mutation-gate",
        mutation_boundary={"writes_repo_state": True, "allowed_paths": ["src/app.py"]},
    )
    bound = bind_operation_invocation_to_authorities(invocation=invocation, authorities=authorities)

    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "actionability": {"next_action": {"action": "rendered text is not identity", "operation_invocation": bound}},
            "authorities": authorities,
        }
    )

    assert decision["status"] == "actionable"
    assert decision["primary_action"]["action"] == "rendered text is not identity"
    assert decision["action_identity"]["operation_invocation"]["operation_id"] == "implement.apply"
    assert decision["action_identity"]["requested_mutation_boundary"]["allowed_paths"] == ["src/app.py"]
    assert decision["action_identity"]["expected_input_revision"] == bound["expected_input_revision"]


def test_repo_mutation_rejects_planning_derived_placeholder_baseline() -> None:
    authorities = {
        "mutation_baseline": {
            "kind": "agentic-planning/mutation-baseline/v1",
            "status": "current",
            "baseline_id": "planning-revision-a",
            "source": "planning-revision-and-changed-paths",
            "changed_path_count": 1,
        }
    }
    invocation = operation_invocation(
        operation_id="implement.apply",
        arguments={"target": ".", "changed": ["src/app.py"]},
        effect_class="repo-mutation",
        authority_class="mutation-gate",
        mutation_boundary={"writes_repo_state": True, "allowed_paths": ["src/app.py"]},
    )
    bound = bind_operation_invocation_to_authorities(invocation=invocation, authorities=authorities)

    decision = compile_operating_decision(
        inputs={
            "consumer": "unregistered-test-consumer",
            "actionability": {"next_action": {"action": "implement", "operation_invocation": bound}},
            "authorities": authorities,
        }
    )

    assert decision["status"] == "blocked"
    assert decision["external_blocker"]["reason_code"] == "stale-mutation-baseline"


def test_context_authority_projection_requires_live_records_for_start() -> None:
    projection = resolve_context_authority_projection(consumer="start", task="shape authority routing ownership skill guidance memory")

    assert projection["status"] == "repair-required"
    assert projection["registry_revision"].startswith("sha256:")
    assert set(projection["missing_required_surfaces"]) >= {
        "architecture-principles",
        "scoped-instructions",
        "ownership",
        "planning",
        "skills",
        "target-guidance",
    }
    repair = projection["repair_operation"]
    assert repair["status"] == "required"
    assert repair["blocked_claims"] == ["mutation", "proof-claim", "completion-claim"]
    planning = next(item for item in repair["repairs"] if item["surface"] == "planning")
    assert planning["owner"] == "planning package"
    assert planning["reason_code"] == "missing-target-root"
    assert planning["action"] == "context-authority.planning.refresh-source"
    assert planning["operation_id"] == "planning.summary.report"
    assert planning["repair_owner"] == "planning package"
    assert "source-owner admission result" in planning["required_record"]


def test_operating_decision_blocks_action_when_required_context_is_unadmitted() -> None:
    invocation = operation_invocation(operation_id="proof.report", arguments={})

    decision = compile_operating_decision(
        inputs={
            "consumer": "start",
            "task": "prove the context gate",
            "actionability": {"next_action": {"action": "run-proof", "operation_invocation": invocation}},
        }
    )

    assert decision["status"] == "blocked"
    assert decision["primary_action"] == {}
    assert decision["external_blocker"] == {
        "kind": "agentic-workspace/operating-decision-blocker/v1",
        "reason_code": "context-authority-unavailable",
        "owner": "context-authority-registry",
        "repair": "run the typed context-authority repair operation before retrying the decision",
    }


def _write_context_authority_sources(root: Path) -> None:
    (root / ".agentic-workspace/planning").mkdir(parents=True)
    (root / ".agentic-workspace/memory/repo").mkdir(parents=True)
    (root / ".agentic-workspace/skills/workspace-startup").mkdir(parents=True)
    (root / ".agentic-workspace/verification").mkdir(parents=True)
    (root / "src/agentic_workspace").mkdir(parents=True)
    (root / ".agentic-workspace").mkdir(exist_ok=True)
    (root / "SYSTEM_INTENT.md").write_text(
        "# System Intent\n\n## Purpose\n\nRuntime contract.\n\n## Governing intents\n\nGenerated runtime contract shape.\n",
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text(
        "Authority marker:\n\n<!-- agentic-workspace:workflow:start -->\nOrdinary route:\n<!-- agentic-workspace:workflow:end -->\n",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/config.toml").write_text(
        """
schema_version = 1

[modules]
enabled = ["planning", "memory", "verification"]

[workspace]
cli_invoke = "agentic-workspace"
""",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/OWNERSHIP.toml").write_text(
        """
schema_version = 1

[[managed_surfaces]]
module = "workspace"
path = ".agentic-workspace/OWNERSHIP.toml"

[[authority_surfaces]]
concern = "startup-instructions"
""",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/planning/state.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (root / ".agentic-workspace/memory/repo/index.md").write_text("# Memory\n", encoding="utf-8")
    (root / ".agentic-workspace/memory/repo/manifest.toml").write_text(
        """
[[routes]]
id = "default"
routes_from = ["src/**"]

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
task_relevance = "required"
routes_from = ["src/**", ".agentic-workspace/memory/repo/**"]
routing_only = true
""",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/skills/workspace-startup/SKILL.md").write_text("# Startup\n", encoding="utf-8")
    (root / ".agentic-workspace/verification/manifest.toml").write_text(
        """
schema_version = 1

[[scenarios]]
id = "focused-proof"
command = "pytest tests/test_operating_decision.py"
""",
        encoding="utf-8",
    )
    (root / "src/agentic_workspace/evaluation.py").write_text(
        "def evaluation_collection_match():\n    return True\n\ndef record_evaluation_report_delivery_operation():\n    return None\n",
        encoding="utf-8",
    )
    (root / "src/agentic_workspace/workspace_runtime_primitives.py").write_text(
        "def delegated_worker_kernel():\n    return None\n\n"
        "def assignment_lifecycle():\n    return None\n\n"
        "def final_response():\n    return None\n\n"
        "terminal = object()\n",
        encoding="utf-8",
    )


def test_context_authority_projection_selects_repository_sources_and_ignores_forged_records(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    forged_records = {
        item["surface"]: {
            "status": "current",
            "source_id": "forged/source",
            "revision": "sha256:forged",
            "freshness": "current",
            "admission": {
                "registry_revision": "sha256:forged",
                "surface": item["surface"],
                "owner": item["owner"],
            },
        }
        for item in context_authority_declarations()
        if "start" in item["consumer"]
    }
    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
        source_records=forged_records,
    )

    assert projection["status"] == "admitted"
    assert projection["repair_operation"]["status"] == "not-required"
    skills = next(item for item in projection["authorities"] if item["surface"] == "skills")
    assert skills["source"]["id"] == ".agentic-workspace/skills/workspace-startup/SKILL.md"
    assert skills["source"]["revision"].startswith("sha256:")
    assert skills["source"]["admission"]["producer"] == "skill-registry-source-adapter"
    assert skills["source"]["admission"]["owner_admission"]["producer"] == (
        "agentic_workspace.workspace_runtime_core.skill_dependency_resolver"
    )
    assert skills["source"]["admission"]["owner_admission"]["result_kind"] == "agentic-workspace/skill-dependency-closure/v1"
    assert skills["source"]["source_adapter"] == "skill-registry-source-adapter"
    assert skills["source"]["freshness_enforcement"]["status"] == "active"
    assert skills["caller_record_status"] == "ignored"
    assert projection["excluded_authorities"] == []


def test_context_authority_projection_curates_memory_from_manifest_routes(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/memory/repo/domains").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agentic-workspace/memory/repo/domains/runtime.md").write_text("Runtime note\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/memory/repo/manifest.toml").write_text(
        """
[[routes]]
id = "legacy-shape"
routes_from = ["ignored/**"]

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
task_relevance = "required"
routes_from = [".agentic-workspace/memory/repo/**/*.md"]
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/runtime.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/runtime.md"
authority = "advisory"
task_relevance = "conditional"
subsystems = ["workspace-runtime"]
surfaces = ["runtime"]
routes_from = ["src/agentic_workspace/**"]
stale_when = ["docs/runtime-source.md"]

[notes.".agentic-workspace/memory/repo/domains/unrelated.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/unrelated.md"
authority = "advisory"
task_relevance = "conditional"
subsystems = ["other"]
surfaces = ["other"]
routes_from = ["docs/private/**"]

[notes.".agentic-workspace/memory/repo/domains/review-only.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/review-only.md"
authority = "advisory"
task_relevance = "review-only"
subsystems = ["workspace-runtime"]
surfaces = ["runtime"]
routes_from = ["src/agentic_workspace/**"]
""",
        encoding="utf-8",
    )

    projection = resolve_context_authority_projection(
        consumer="start",
        task="fix runtime context",
        changed_paths=["src/agentic_workspace/workspace_runtime.py"],
        target_root=tmp_path,
    )

    memory = next(item for item in projection["authorities"] if item["surface"] == "memory")
    curation = memory["source"]["selection"]["memory_curation"]
    selected_paths = [item["path"] for item in curation["selected_notes"]]
    assert curation["status"] == "selected"
    assert ".agentic-workspace/memory/repo/index.md" in selected_paths
    assert ".agentic-workspace/memory/repo/domains/runtime.md" in selected_paths
    assert ".agentic-workspace/memory/repo/domains/unrelated.md" not in selected_paths
    assert ".agentic-workspace/memory/repo/domains/review-only.md" not in selected_paths
    assert curation["review_only_excluded_count"] == 1
    assert curation["context_budget"] == {"max_selected_notes": 12, "actual_selected_notes": 2}
    runtime_note = next(item for item in curation["selected_notes"] if item["path"].endswith("runtime.md"))
    assert runtime_note["stale_when_matched_paths"] == []
    owner_result = memory["source"]["admission"]["owner_result"]
    assert owner_result["kind"] == "agentic-workspace/memory-route-curation/v1"
    assert owner_result["producer"] == "agentic_memory.manifest"
    assert owner_result["status"] == "current"


def test_context_authority_projection_rejects_stale_memory_note_matches(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/memory/repo/domains").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agentic-workspace/memory/repo/domains/runtime.md").write_text("Runtime note\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/memory/repo/manifest.toml").write_text(
        """
[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
task_relevance = "required"
routes_from = [".agentic-workspace/memory/repo/**/*.md"]
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/runtime.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/runtime.md"
authority = "advisory"
task_relevance = "conditional"
subsystems = ["workspace-runtime"]
surfaces = ["runtime"]
routes_from = ["src/agentic_workspace/**"]
stale_when = ["src/agentic_workspace/**"]
""",
        encoding="utf-8",
    )

    projection = resolve_context_authority_projection(
        consumer="start",
        task="fix runtime context",
        changed_paths=["src/agentic_workspace/workspace_runtime.py"],
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    memory = next(item for item in projection["excluded_authorities"] if item["surface"] == "memory")
    assert memory["reason"] == "memory-stale-review-required"
    repair = next(item for item in projection["repair_operation"]["repairs"] if item["surface"] == "memory")
    assert repair["operation_id"] == "memory.route.report"


def test_context_authority_projection_rejects_configured_empty_and_missing_required_sources(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/memory/repo/manifest.toml").unlink()
    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing memory context",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    memory = next(item for item in projection["excluded_authorities"] if item["surface"] == "memory")
    assert memory["reason"] == "canonical-source-missing"
    repair = next(item for item in projection["repair_operation"]["repairs"] if item["surface"] == "memory")
    assert repair["action"] == "context-authority.memory.refresh-source"
    assert repair["operation_id"] == "memory.route.report"
    assert repair["repair_owner"] == "memory package"
    assert "source-specific schema/population check" in repair["required_record"]


def test_context_authority_projection_excludes_irrelevant_memory_without_repair(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    projection = resolve_context_authority_projection(
        consumer="start",
        task="fix typo",
        changed_paths=["README.md"],
        target_root=tmp_path,
    )

    assert projection["status"] == "admitted"
    assert "memory" not in {item["surface"] for item in projection["authorities"]}
    memory = next(item for item in projection["excluded_authorities"] if item["surface"] == "memory")
    assert memory["reason"] == "not-selected-by-task-or-path"
    assert memory["selected_required"] is False
    assert projection["missing_required_surfaces"] == []
    assert projection["repair_operation"]["status"] == "not-required"


def test_context_authority_projection_rejects_skill_dependency_owner_diagnostics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_context_authority_sources(tmp_path)

    from agentic_workspace import workspace_runtime_core as runtime_core

    monkeypatch.setattr(
        runtime_core,
        "_skill_dependency_diagnostics",
        lambda *, target_root: [{"skill": "workspace-startup", "reason_code": "missing-dependency"}],
    )

    projection = resolve_context_authority_projection(
        consumer="skills",
        task="route workspace skill",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    skills = next(item for item in projection["excluded_authorities"] if item["surface"] == "skills")
    assert skills["reason"] == "skill-dependency-unavailable"
    repair = next(item for item in projection["repair_operation"]["repairs"] if item["surface"] == "skills")
    assert repair["operation_id"] == "workspace.skills.resolve-dependencies"
    assert repair["repair_owner"] == "workspace skill registry"


def test_context_authority_projection_rejects_consumer_local_runner_forgery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_context_authority_sources(tmp_path)

    from agentic_workspace import operating_decision

    def forged_skill_runner(**_kwargs):
        return {
            "kind": "agentic-workspace/skill-dependency-closure/v1",
            "producer": "forged.producer",
            "status": "current",
            "surface": "skills",
            "owner": "workspace skill registry",
            "source_id": ".agentic-workspace/skills/workspace-startup/SKILL.md",
            "source_revision": "sha256:forged-source",
            "git_head": "",
            "revision": "sha256:forged-skill-owner",
            "adapter_id": "skills.owner-result",
        }

    monkeypatch.setattr(operating_decision, "registered_context_owner_operation_runner", lambda _surface: forged_skill_runner)

    projection = resolve_context_authority_projection(
        consumer="skills",
        task="route workspace skill",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    skills = next(item for item in projection["excluded_authorities"] if item["surface"] == "skills")
    assert skills["reason"] in {"owner-operation-missing", "owner-result-identity-mismatch"}


def test_context_authority_owner_result_revisions_bind_selection_and_schema_backing(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    base = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )
    with_path = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        changed_paths=["AGENTS.md"],
        target_root=tmp_path,
    )

    base_scoped = next(item for item in base["authorities"] if item["surface"] == "scoped-instructions")
    path_scoped = next(item for item in with_path["authorities"] if item["surface"] == "scoped-instructions")
    assert base_scoped["source"]["admission"]["owner_result"]["revision"] != path_scoped["source"]["admission"]["owner_result"]["revision"]

    (tmp_path / "AGENTS.md").write_text(
        "Authority marker:\n\n<!-- agentic-workspace:workflow:start -->\nmissing route marker\n",
        encoding="utf-8",
    )
    invalid = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )
    scoped = next(item for item in invalid["excluded_authorities"] if item["surface"] == "scoped-instructions")
    assert scoped["reason"] == "owner-source-contract-marker-missing"


@pytest.mark.parametrize(
    "receipt_payload",
    [
        {},
        {
            "kind": "agentic-workspace/system-intent-mirror/v1",
            "producer": "agentic_workspace.system_intent",
            "status": "current",
            "surface": "system-intent",
            "source_id": "SYSTEM_INTENT.md",
            "source_revision": "sha256:caller-asserted",
            "git_head": "",
            "adapter_id": "system-intent.owner-result",
        },
    ],
)
def test_context_authority_ignores_checked_in_owner_result_receipts(
    tmp_path: Path,
    receipt_payload: dict[str, object],
) -> None:
    _write_context_authority_sources(tmp_path)
    receipt_path = tmp_path / ".agentic-workspace/context-authority/owner-results/system-intent.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )

    assert projection["status"] == "admitted"
    system_intent = next(item for item in projection["authorities"] if item["surface"] == "system-intent")
    assert system_intent["source"]["admission"]["owner_result"]["status"] == "current"
    assert system_intent["source"]["admission"]["owner_result"]["owner_operation"]["status"] == "executed"
    assert system_intent["source"]["admission"]["owner_result"]["owner_execution_receipt"]["current_state"] == "current"
    assert "owner_receipt_ref" not in system_intent["source"]["admission"]["owner_result"]


def test_context_authority_rejects_digest_only_consumer_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_context_authority_sources(tmp_path)
    from agentic_workspace import operating_decision

    def digest_only_runner(**kwargs):
        chosen = kwargs["chosen"]
        git_head = kwargs["git_head"]
        source_revision = "sha256:" + _fixture_source_revision(chosen)
        return {
            "kind": "agentic-workspace/system-intent-mirror/v1",
            "producer": "agentic_workspace.system_intent",
            "status": "current",
            "surface": "system-intent",
            "owner": "workspace-runtime",
            "source_id": "SYSTEM_INTENT.md",
            "source_revision": source_revision,
            "git_head": git_head,
            "revision": "sha256:caller-current",
            "adapter_id": "system-intent.owner-result",
            "owner_operation": {
                "kind": "agentic-workspace/context-authority-owner-operation/v1",
                "status": "executed",
                "operation_id": "context-authority.system-intent.refresh-source",
                "run_id": "sha256:" + operating_decision._digest({"source_revision": source_revision}),
                "receipt_id": "sha256:" + operating_decision._digest({"source_revision": source_revision, "receipt": True}),
                "producer": "agentic_workspace.system_intent",
                "surface": "system-intent",
                "source_id": "SYSTEM_INTENT.md",
                "source_revision": source_revision,
                "git_head": git_head,
                "adapter_id": "system-intent.owner-result",
            },
        }

    monkeypatch.setattr(operating_decision, "registered_context_owner_operation_runner", lambda _surface: digest_only_runner)

    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    system_intent = next(item for item in projection["excluded_authorities"] if item["surface"] == "system-intent")
    assert system_intent["reason"] in {"owner-operation-receipt-missing", "owner-operation-receipt-id-mismatch"}


def test_context_authority_owner_operation_receipt_currentness_is_recomputable_across_processes(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)

    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing ownership skill guidance memory",
        target_root=tmp_path,
    )

    system_intent = next(item for item in projection["authorities"] if item["surface"] == "system-intent")
    receipt = system_intent["source"]["admission"]["owner_result"]["owner_execution_receipt"]
    assert receipt["current_resolution"]["resolution_mode"] == "deterministic-source-revision"


def test_context_authority_rejects_parseable_file_without_owner_boundary(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")

    projection = resolve_context_authority_projection(
        consumer="start",
        task="fix target guidance",
        target_root=tmp_path,
    )

    target_guidance = next(item for item in projection["excluded_authorities"] if item["surface"] == "target-guidance")
    assert target_guidance["reason"] == "owner-source-required-key-missing"


def test_context_authority_rejects_unknown_planning_and_mutation_statuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.operating_decision as operating_decision

    _write_context_authority_sources(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=tmp_path, check=True, capture_output=True)

    def unknown_planning(*, target_root, state_data):
        return {"kind": "agentic-workspace/planning-owner-admission/v1", "status": "blocked", "state_data": state_data}

    def unknown_baseline(*, target_root, changed_paths):
        return {"kind": "agentic-workspace/mutation-baseline/v1", "status": "superseded", "scope": {"allowed_paths": changed_paths}}

    monkeypatch.setattr("agentic_workspace.workspace_runtime_core._planning_owner_admission_payload", unknown_planning)
    monkeypatch.setattr("agentic_workspace.context_authority_owner_operations.mutation_baseline_payload", unknown_baseline)
    monkeypatch.setattr(operating_decision, "mutation_baseline_payload", unknown_baseline)

    planning_projection = resolve_context_authority_projection(
        consumer="start",
        task="planning owner route",
        target_root=tmp_path,
    )
    planning = next(item for item in planning_projection["excluded_authorities"] if item["surface"] == "planning")
    assert planning["reason"] == "planning-owner-admission-blocked"

    mutation_projection = resolve_context_authority_projection(
        consumer="implement",
        task="implement mutation baseline",
        changed_paths=["src/app.py"],
        target_root=tmp_path,
    )
    mutation = next(item for item in mutation_projection["excluded_authorities"] if item["surface"] == "mutation-baseline")
    assert mutation["reason"] == "mutation-baseline-admission-superseded"


def test_context_authority_owner_results_are_semantic_adapter_dispatched() -> None:
    source = Path("src/agentic_workspace/operating_decision.py").read_text(encoding="utf-8")

    assert "def _execute_context_owner_operation(" not in source
    assert "def _context_owner_result(" not in source
    assert "def _file_backed_owner_result(" not in source
    assert "def _dispatch_registered_owner_operation(" not in source
    assert "def _run_registered_owner_operation(" not in source
    assert '"owner_adapter_receipt": {' not in source
    assert "CONTEXT_OWNER_RESULT_ADAPTERS" not in source
    assert "context_authority_owner_operations" in source
    assert "registered_context_owner_operation_runner(surface)" in source
    assert "parseability alone" not in source


def test_context_owner_operation_admission_does_not_accept_caller_semantic_payload() -> None:
    import agentic_workspace.context_authority_owner_operations as owner_operations

    operation_source = Path("src/agentic_workspace/context_authority_owner_operations.py").read_text(encoding="utf-8")
    resolver_source = Path("src/agentic_workspace/operating_decision.py").read_text(encoding="utf-8")

    assert not hasattr(owner_operations, "admit_context_owner_operation_result")
    assert not hasattr(owner_operations, "ContextOwnerAdapterResult")
    assert "_CONTEXT_OWNER_ADAPTER_TOKEN" not in operation_source
    assert "class ContextOwnerAdapterResult" not in operation_source
    assert "def admit_context_owner_operation_result(" not in operation_source
    assert "def _issue_context_owner_adapter_result(" not in operation_source
    assert "def _issue_context_owner_result(" not in operation_source
    assert "def _owner_operation_result_base(" not in resolver_source
    assert "def _admit_concrete_owner_adapter_result(" not in resolver_source
    assert "def _registered_owner_adapter_result(" not in resolver_source
    assert "def _owner_result_base(" not in resolver_source
    assert "def _finalize_owner_result(" not in resolver_source
    assert "def _run_registered_owner_operation(" not in resolver_source
    assert "_admit_context_owner_operation_result" not in resolver_source
    assert not hasattr(owner_operations, "run_context_owner_operation")
    assert "def run_context_owner_operation(" not in operation_source
    assert "registered_context_owner_operation_runner(surface)" in resolver_source
    assert "_CONTEXT_OWNER_OPERATION_RUNNERS" in operation_source
    assert "_CONTEXT_OWNER_ADAPTER_TOKEN" not in resolver_source
    assert "ContextOwnerAdapterResult" not in resolver_source


def test_context_authority_each_owner_family_uses_concrete_adapter_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.context_authority_owner_operations as owner_operations
    import agentic_workspace.operating_decision as operating_decision

    _write_context_authority_sources(tmp_path)
    (tmp_path / "generated").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src/agentic_workspace/contracts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src/agentic_workspace/contracts/structured_file_inventory.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "generated/.agentic-workspace-cli-fingerprint.json").write_text(
        json.dumps({"kind": "generated-cli-source-manifest/v1", "source_hashes": {}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(operating_decision, "_generated_fingerprint_is_current", lambda _root: True)
    monkeypatch.setattr(operating_decision, "_git_head", lambda _root: "f" * 40)
    monkeypatch.setattr(
        owner_operations,
        "mutation_baseline_payload",
        lambda *, target_root, changed_paths: {
            "status": "current",
            "baseline_id": "baseline-1",
            "head": "f" * 40,
            "scope": {"paths": changed_paths},
            "identity": {"fingerprint": "baseline"},
        },
    )
    monkeypatch.setattr(
        operating_decision,
        "mutation_baseline_payload",
        lambda *, target_root, changed_paths: {
            "status": "current",
            "baseline_id": "baseline-1",
            "head": "f" * 40,
            "scope": {"paths": changed_paths},
            "identity": {"fingerprint": "baseline"},
        },
    )
    monkeypatch.setattr(
        "agentic_workspace.authority_envelope.mutation_baseline_payload",
        lambda *, target_root, changed_paths: {
            "status": "current",
            "baseline_id": "baseline-1",
            "head": "f" * 40,
            "scope": {"paths": changed_paths},
            "identity": {"fingerprint": "baseline"},
        },
    )
    paths_by_surface = {
        "system-intent": ["SYSTEM_INTENT.md"],
        "architecture-principles": ["SYSTEM_INTENT.md"],
        "scoped-instructions": ["AGENTS.md"],
        "ownership": ["src/app.py"],
        "planning": [".agentic-workspace/planning/state.toml"],
        "memory": ["src/app.py"],
        "assignment": ["src/app.py"],
        "evaluation": ["src/agentic_workspace/evaluation.py"],
        "proof": ["tests/test_operating_decision.py"],
        "mutation-baseline": ["src/app.py"],
        "autopilot-executor": ["src/agentic_workspace/workspace_runtime_primitives.py"],
        "skills": [".agentic-workspace/skills/workspace-startup/SKILL.md"],
        "target-guidance": ["src/app.py"],
        "terminal-outcome": ["src/agentic_workspace/workspace_runtime_primitives.py"],
        "generated-references": ["generated/client.py"],
    }

    for item in context_authority_declarations():
        surface = item["surface"]
        consumer = str(item["consumer"]).split(",")[0].strip()
        record = _resolve_context_authority_source(
            item=item,
            target_root=tmp_path,
            consumer=consumer,
            task=f"exercise {surface} owner adapter",
            paths=paths_by_surface[surface],
        )

        assert record["status"] == "current", surface
        owner_result = record["admission"]["owner_result"]
        adapter_receipt = owner_result["owner_adapter_receipt"]
        source_owner_contract = owner_result["source_owner_contract"]
        operation = owner_result["owner_operation"]
        execution_receipt = owner_result["owner_execution_receipt"]
        assert adapter_receipt["kind"] == "agentic-workspace/context-authority-owner-adapter-result/v1"
        assert source_owner_contract["kind"] == "agentic-workspace/context-authority-source-owner-contract/v1"
        assert adapter_receipt["surface"] == operation["surface"] == execution_receipt["surface"] == surface
        assert source_owner_contract["surface"] == surface
        assert source_owner_contract["schema"]["status"] in {"valid", "current"}
        assert source_owner_contract["lifecycle"]["status"] == "current"
        assert source_owner_contract["population"]["status"] == "present"
        assert source_owner_contract["supersession"]["status"] == "not-superseded"
        assert source_owner_contract["lifecycle"]["repair_operation_id"] == operation["operation_id"]
        assert operation["adapter_receipt_revision"] == execution_receipt["adapter_receipt_revision"]
        assert operation["source_owner_contract_revision"] == execution_receipt["source_owner_contract_revision"]
        assert adapter_receipt["source_owner_contract_revision"] == operation["source_owner_contract_revision"]
        assert owner_result["schema_backing"]
        assert owner_result["owner_boundary"]


def test_context_owner_operation_runner_rejects_caller_producer_identity(tmp_path: Path) -> None:
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_operation_runner

    _write_context_authority_sources(tmp_path)
    chosen = tmp_path / "SYSTEM_INTENT.md"
    selection = {"consumer": "start"}
    runner = registered_context_owner_operation_runner("system-intent")

    with pytest.raises(ValueError, match="must not carry caller-provided producer identity or receipts"):
        runner(
            owner="system-intent resolver",
            root=tmp_path,
            chosen=chosen,
            revision=_fixture_source_revision(chosen),
            git_head="",
            selection=selection,
            adapter_id="system-intent.owner-result",
            owner_evidence={
                "producer": "agentic_workspace.workspace_runtime_core.system_intent",
                "status": "current",
                "owner_boundary": "caller-built generic boundary",
                "schema_backing": {"source_format": "markdown", "parse_status": "valid"},
            },
        )


def test_mutation_baseline_owner_operation_produces_own_admission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_operation_runner

    _write_context_authority_sources(tmp_path)
    chosen = tmp_path / "src/agentic_workspace/operating_decision.py"
    chosen.parent.mkdir(parents=True, exist_ok=True)
    chosen.write_text("mutation baseline owner source\n", encoding="utf-8")
    observed_paths: list[str] = []

    def owned_baseline(*, target_root: Path, changed_paths: list[str]) -> dict[str, Any]:
        observed_paths.extend(changed_paths)
        return {
            "kind": "agentic-workspace/mutation-baseline/v1",
            "status": "current",
            "baseline_id": "baseline-owner-produced",
            "head": "a" * 40,
            "scope": {"allowed_paths": changed_paths},
            "identity": {"fingerprint": "owned"},
        }

    monkeypatch.setattr("agentic_workspace.context_authority_owner_operations.mutation_baseline_payload", owned_baseline)
    runner = registered_context_owner_operation_runner("mutation-baseline")

    result = runner(
        owner="mutation authority",
        root=tmp_path,
        chosen=chosen,
        revision=_fixture_source_revision(chosen),
        git_head="a" * 40,
        selection={"matched_paths": ["src/app.py"]},
        paths=["src/app.py"],
        task="mutation baseline",
        source_specific={},
    )

    assert result["status"] == "current"
    assert observed_paths == ["src/app.py"]
    admission = result["schema_backing"]["mutation_baseline_admission"]
    assert admission["baseline_id"] == "baseline-owner-produced"

    with pytest.raises(ValueError, match="derives semantic evidence from its canonical subsystem"):
        runner(
            owner="mutation authority",
            root=tmp_path,
            chosen=chosen,
            revision=_fixture_source_revision(chosen),
            git_head="a" * 40,
            selection={"matched_paths": ["src/app.py"]},
            paths=["src/app.py"],
            task="mutation baseline",
            source_specific={"mutation_baseline_admission": {"status": "current"}},
        )


@pytest.mark.parametrize(
    ("surface", "source_path", "source_specific"),
    [
        (
            "memory",
            ".agentic-workspace/memory/repo/manifest.toml",
            {"memory_curation": {"kind": "agentic-workspace/memory-route-curation/v1", "status": "selected"}},
        ),
        (
            "mutation-baseline",
            ".agentic-workspace/config.toml",
            {
                "mutation_baseline_admission": {
                    "kind": "agentic-workspace/context-authority-owner-admission/v1",
                    "status": "current",
                }
            },
        ),
        (
            "skills",
            ".agentic-workspace/skills/workspace-startup/SKILL.md",
            {"skill_dependency_closure": {"kind": "agentic-workspace/skill-dependency-closure/v1", "status": "satisfied"}},
        ),
    ],
)
def test_protected_context_owner_operations_reject_caller_source_specific_semantics(
    tmp_path: Path,
    surface: str,
    source_path: str,
    source_specific: dict[str, object],
) -> None:
    from agentic_workspace.context_authority_owner_operations import registered_context_owner_operation_runner

    _write_context_authority_sources(tmp_path)
    chosen = tmp_path / source_path
    runner = registered_context_owner_operation_runner(surface)

    with pytest.raises(ValueError, match="derives semantic evidence from its canonical subsystem"):
        runner(
            owner=f"{surface} owner",
            root=tmp_path,
            chosen=chosen,
            revision=_fixture_source_revision(chosen),
            git_head="",
            selection={"consumer": "start", "matched_paths": ["src/app.py"]},
            task=f"exercise {surface}",
            paths=["src/app.py"],
            source_specific=source_specific,
        )


def test_context_owner_operation_admission_rejects_forged_owner_identity(tmp_path: Path) -> None:
    from agentic_workspace.context_authority_owner_operations import _admit_context_owner_operation_result

    _write_context_authority_sources(tmp_path)
    chosen = tmp_path / "SYSTEM_INTENT.md"

    with pytest.raises(ValueError, match="producer does not match"):
        _admit_context_owner_operation_result(
            surface="system-intent",
            owner="workspace-runtime",
            root=tmp_path,
            chosen=chosen,
            source_revision="sha256:" + _fixture_source_revision(chosen),
            git_head="head",
            selection={"consumer": "start"},
            adapter_id="system-intent.owner-result",
            owner_result={
                "kind": "forged-kind",
                "producer": "forged-producer",
                "status": "current",
                "surface": "system-intent",
                "source_id": "SYSTEM_INTENT.md",
                "source_revision": "sha256:" + _fixture_source_revision(chosen),
                "git_head": "head",
                "adapter_id": "system-intent.owner-result",
                "revision": "sha256:forged",
                "owner_boundary": "forged",
                "schema_backing": {"source_format": "markdown"},
            },
        )


def test_context_owner_operation_admission_rejects_tampered_producer_state(tmp_path: Path) -> None:
    from agentic_workspace.context_authority_owner_operations import (
        _admit_context_owner_operation_result,
        registered_context_owner_operation_runner,
    )

    _write_context_authority_sources(tmp_path)
    chosen = tmp_path / "SYSTEM_INTENT.md"
    selection = {"consumer": "start"}
    runner = registered_context_owner_operation_runner("system-intent")
    current = runner(
        owner="system-intent resolver",
        root=tmp_path,
        chosen=chosen,
        revision=_fixture_source_revision(chosen),
        git_head="",
        selection=selection,
        task="",
        paths=[],
        source_specific={},
    )
    forged = {key: value for key, value in current.items() if key not in {"owner_operation", "owner_execution_receipt", "revision"}}
    forged["producer_owner_state"] = {
        **forged["producer_owner_state"],
        "lifecycle": {**forged["producer_owner_state"]["lifecycle"], "status": "current"},
        "revision": "sha256:forged",
    }
    forged["revision"] = "sha256:forged-result"

    with pytest.raises(ValueError, match="producer owner state revision does not match"):
        _admit_context_owner_operation_result(
            surface="system-intent",
            owner="system-intent resolver",
            root=tmp_path,
            chosen=chosen,
            source_revision="sha256:" + _fixture_source_revision(chosen),
            git_head="",
            selection=selection,
            adapter_id="system-intent.owner-result",
            owner_result=forged,
        )


def test_shared_context_composer_cannot_admit_a_caller_built_producer_result() -> None:
    from agentic_workspace.context_authority_producer_operations import admit_registered_producer_result

    forged = {
        "kind": "agentic-workspace/system-intent-mirror/v1",
        "producer": "agentic_workspace.workspace_runtime_core.system_intent",
        "status": "current",
        "producer_owner_state": {"status": "current"},
        "source_owner_contract": {"status": "admitted"},
    }

    with pytest.raises(ValueError, match="opaque registered producer result"):
        admit_registered_producer_result(forged)

    composer_source = Path("src/agentic_workspace/context_authority_owner_operations.py").read_text(encoding="utf-8")
    assert "registered_producer_operation_runner(surface)" in composer_source
    assert "admit_registered_producer_result(producer_runner(**kwargs))" in composer_source


def test_context_authority_resolver_rejects_stale_generated_projection(tmp_path: Path) -> None:
    (tmp_path / "generated").mkdir(parents=True)
    (tmp_path / "src/agentic_workspace/contracts").mkdir(parents=True)
    (tmp_path / "src/example.py").write_text("print('current')\n", encoding="utf-8")
    (tmp_path / "src/agentic_workspace/contracts/structured_file_inventory.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "generated/.agentic-workspace-cli-fingerprint.json").write_text(
        json.dumps({"source_hashes": {"src/example.py": "not-current"}}),
        encoding="utf-8",
    )
    item = next(item for item in context_authority_declarations() if item["surface"] == "generated-references")

    record = _resolve_context_authority_source(item=item, target_root=tmp_path, task="", paths=["generated/client.py"])

    assert record["status"] == "stale"
    assert record["reason"] == "stale-generated-projection"


def test_context_authority_resolver_rejects_mutation_baseline_without_git_head(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    item = next(item for item in context_authority_declarations() if item["surface"] == "mutation-baseline")

    record = _resolve_context_authority_source(item=item, target_root=tmp_path, task="", paths=["src/app.py"])

    assert record["status"] == "missing"
    assert record["reason"] == "git-head-unavailable"


def test_context_authority_coverage_fails_closed_for_duplicate_canonical_owner() -> None:
    declarations = context_authority_declarations()
    duplicate = next(item for item in declarations if item["surface"] == "architecture-principles")
    duplicate["owner"] = "system-intent resolver"

    coverage = context_authority_coverage(declarations=declarations)

    assert coverage["status"] == "coverage-gap"
    assert coverage["duplicate_canonical_owners"] == ["system-intent resolver"]
