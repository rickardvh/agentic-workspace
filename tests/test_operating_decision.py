from __future__ import annotations

import ast
import json
from pathlib import Path

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
    assert coverage["missing_required_sources"] == {}
    for consumer in coverage["ordinary_consumers"]:
        assert set(coverage["consumer_requirements"][consumer]).issubset(set(coverage["consumer_to_surfaces"][consumer]))
    assert {"architecture-principles", "scoped-instructions", "ownership"}.issubset(set(coverage["consumer_requirements"]["start"]))
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
        "mutation_baseline": {"baseline_id": "baseline-a", "revalidation_status": "fresh"},
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


def test_context_authority_projection_requires_live_records_for_start() -> None:
    projection = resolve_context_authority_projection(consumer="start", task="shape authority routing")

    assert projection["status"] == "repair-required"
    assert projection["registry_revision"].startswith("sha256:")
    assert set(projection["missing_required_surfaces"]) >= {
        "architecture-principles",
        "scoped-instructions",
        "ownership",
        "planning",
        "memory",
        "skills",
    }
    repair = projection["repair_operation"]
    assert repair["status"] == "required"
    assert repair["blocked_claims"] == ["mutation", "proof-claim", "completion-claim"]
    planning = next(item for item in repair["repairs"] if item["surface"] == "planning")
    assert planning["owner"] == "planning package"
    assert planning["reason_code"] == "missing-target-root"
    assert planning["action"] == "context-authority.planning.refresh-source"
    assert planning["repair_owner"] == "context-authority-source-adapter"


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
    (root / ".agentic-workspace").mkdir(exist_ok=True)
    (root / "SYSTEM_INTENT.md").write_text("Intent\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("Instructions\n", encoding="utf-8")
    (root / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (root / ".agentic-workspace/OWNERSHIP.toml").write_text("[paths]\n", encoding="utf-8")
    (root / ".agentic-workspace/planning/state.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (root / ".agentic-workspace/memory/repo/index.md").write_text("# Memory\n", encoding="utf-8")
    (root / ".agentic-workspace/memory/repo/manifest.toml").write_text(
        '[[routes]]\nid = "default"\nroutes_from = ["src/**"]\n', encoding="utf-8"
    )
    (root / ".agentic-workspace/skills/workspace-startup/SKILL.md").write_text("# Startup\n", encoding="utf-8")


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
        task="shape authority routing",
        target_root=tmp_path,
        source_records=forged_records,
    )

    assert projection["status"] == "admitted"
    assert projection["repair_operation"]["status"] == "not-required"
    skills = next(item for item in projection["authorities"] if item["surface"] == "skills")
    assert skills["source"]["id"] == ".agentic-workspace/skills/workspace-startup/SKILL.md"
    assert skills["source"]["revision"].startswith("sha256:")
    assert skills["source"]["admission"]["producer"] == "skill-registry-source-adapter"
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
stale_when = ["src/agentic_workspace/**"]

[notes.".agentic-workspace/memory/repo/domains/unrelated.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/unrelated.md"
authority = "advisory"
task_relevance = "conditional"
subsystems = ["other"]
surfaces = ["other"]
routes_from = ["docs/private/**"]
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
    runtime_note = next(item for item in curation["selected_notes"] if item["path"].endswith("runtime.md"))
    assert runtime_note["stale_when_matched_paths"] == ["src/agentic_workspace/workspace_runtime.py"]


def test_context_authority_projection_rejects_configured_empty_and_missing_required_sources(tmp_path: Path) -> None:
    _write_context_authority_sources(tmp_path)
    (tmp_path / ".agentic-workspace/memory/repo/manifest.toml").unlink()
    projection = resolve_context_authority_projection(
        consumer="start",
        task="shape authority routing",
        target_root=tmp_path,
    )

    assert projection["status"] == "repair-required"
    memory = next(item for item in projection["excluded_authorities"] if item["surface"] == "memory")
    assert memory["reason"] == "canonical-source-missing"
    repair = next(item for item in projection["repair_operation"]["repairs"] if item["surface"] == "memory")
    assert repair["action"] == "context-authority.memory.refresh-source"
    assert "source-specific schema/population check" in repair["required_record"]


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
