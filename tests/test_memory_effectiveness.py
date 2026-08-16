from __future__ import annotations

from pathlib import Path

import pytest

from agentic_workspace.memory_effectiveness import (
    compile_memory_effectiveness,
    memory_effectiveness_operation,
    project_memory_use,
)
from agentic_workspace.operating_decision import compile_operating_decision
from agentic_workspace.workspace_runtime_primitives import _memory_consult_payload, _memory_decision_packet_payload


def _manifest(root: Path, *, status: str = "active") -> None:
    path = root / ".agentic-workspace/memory/repo/manifest.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'''
version = 1

[durable_facts."selected-plan-owned-next-task"]
summary = "Rebind selected-owner work from the owner and task; keep old closeout residue separate."
owner = "planning-route-decision"
authority_class = "advisory"
route_keys = ["planning"]
touched_surfaces = ["planning"]
evidence = ["planning-contract.md"]
affected_decisions = ["planning-route"]
note_ref = "recurring-failures.md#selected-plan"
promotion = "Promote after deterministic recurrence."
demotion_or_expiry = "Retire after stronger proof."
promotion_target = "planning-route-decision"
promotion_trigger = "owned task classified unrelated"
preferred_remediation = "repair the structured route classifier"
elimination_target = "selected plan blocks its next owned task"
retention_after_promotion = "stub"
status = "{status}"
''',
        encoding="utf-8",
    )


def _route(*, durable: bool = True) -> dict[str, str]:
    return {
        "path": ".agentic-workspace/memory/repo/manifest.toml#durable_facts.selected-plan-owned-next-task"
        if durable
        else ".agentic-workspace/memory/repo/mistakes/recurring-failures.md",
        "match_source": "durable-fact" if durable else "routes_from",
    }


def _projected(root: Path) -> dict:
    _manifest(root)
    return project_memory_use(target_root=root, route_matches=[_route()])


def test_memory_use_distinguishes_no_match_candidate_and_projected(tmp_path: Path) -> None:
    _manifest(tmp_path)

    no_match = project_memory_use(target_root=tmp_path, route_matches=[])
    candidate = project_memory_use(target_root=tmp_path, route_matches=[_route(durable=False)])
    projected = project_memory_use(target_root=tmp_path, route_matches=[_route()])

    assert no_match["status"] == "no-match"
    assert candidate["status"] == "candidate-only"
    assert candidate["projected_count"] == 0
    assert candidate["agent_decision_required"] is True
    assert projected["status"] == "projected"
    assert projected["projected_count"] == 1
    contribution = projected["contributions"][0]
    assert contribution["fact_id"] == "selected-plan-owned-next-task"
    assert contribution["affected_decisions"] == ["planning-route"]
    assert contribution["authority_class"] == "advisory"
    assert contribution["drill_down_ref"].endswith("#selected-plan")


def test_deprecated_fact_is_stale_not_projected(tmp_path: Path) -> None:
    _manifest(tmp_path, status="deprecated")
    use = project_memory_use(target_root=tmp_path, route_matches=[_route()])
    assert use["status"] == "stale"
    assert use["projected_count"] == 0


def test_candidate_route_never_becomes_pulled_state() -> None:
    state = memory_effectiveness_operation(
        operation="operating-loop-state",
        packet={"pull": {"status": "relevant_notes_found"}, "use": {"status": "candidate-only"}},
    )
    assert state["state"] == "candidate"
    assert state["reason_code"] == "candidate_only"


def test_planning_changed_path_projects_real_durable_fact_before_decision() -> None:
    root = Path(__file__).resolve().parents[1]
    consult = _memory_consult_payload(
        target_root=root,
        changed_paths=["src/agentic_workspace/workspace_runtime_planning.py"],
        compact=True,
    )
    packet = _memory_decision_packet_payload(
        stage="implement",
        cli_invoke="agentic-workspace",
        memory_consult=consult,
        changed_paths=["src/agentic_workspace/workspace_runtime_planning.py"],
    )
    assert packet["use"]["status"] == "projected"
    assert packet["use"]["contributions"][0]["fact_id"] == "selected-plan-owned-next-task"
    assert packet["pull"]["agent_decision_required"] is True
    assert packet["use"]["agent_decision_required"] is False


def test_unrelated_log_packaging_path_receives_no_memory_contribution() -> None:
    root = Path(__file__).resolve().parents[1]
    consult = _memory_consult_payload(target_root=root, changed_paths=["scripts/log_packaging.py"], compact=True)
    assert consult["memory_use"]["status"] != "projected"
    assert consult["memory_use"]["contributions"] == []


def test_start_summary_and_implement_preserve_one_fact_identity() -> None:
    root = Path(__file__).resolve().parents[1]
    consult = _memory_consult_payload(target_root=root, structured_surfaces=["planning"], compact=True)
    identities = []
    for stage in ("startup", "summary", "implement"):
        packet = _memory_decision_packet_payload(
            stage=stage,
            cli_invoke="agentic-workspace",
            memory_consult=consult,
        )
        contribution = packet["use"]["contributions"][0]
        identities.append((contribution["fact_id"], contribution["fact_revision"]))
    assert len(set(identities)) == 1


def test_recurrence_without_projection_is_routing_miss_not_noncompliance() -> None:
    feedback = compile_memory_effectiveness(
        contributions=[],
        outcomes=[
            {
                "fact_id": "selected-plan-owned-next-task",
                "decision_id": "operating-decision:1234567890abcdef",
                "failure_identity": "same-route-failure",
                "outcome": "contradicted",
                "evidence_authority": "planning-route-receipt",
            }
        ],
    )
    assert feedback["evaluations"][0]["classification"] == "routing_projection_miss"
    assert feedback["findings"][0]["effectiveness_class"] == "routing_projection_miss"


def test_agent_self_report_cannot_establish_violation(tmp_path: Path) -> None:
    contribution = _projected(tmp_path)["contributions"][0]
    feedback = compile_memory_effectiveness(
        contributions=[contribution],
        outcomes=[
            {
                "fact_id": contribution["fact_id"],
                "fact_revision": contribution["fact_revision"],
                "decision_id": "operating-decision:1234567890abcdef",
                "outcome": "contradicted",
                "evidence_authority": "agent-self-report",
            }
        ],
    )
    assert feedback["evaluations"][0]["classification"] == "outcome_inconclusive"
    assert feedback["findings"] == []


@pytest.mark.parametrize(
    ("outcome", "classification"),
    [
        ("contradicted", "apparently_ignored_or_violated"),
        ("insufficient", "insufficient_or_incorrect_memory"),
        ("product-defect", "product_or_infrastructure_defect"),
        ("resolved-by-stronger-owner", "resolved_by_stronger_owner"),
        ("aligned", "no_material_follow_up"),
    ],
)
def test_authoritative_outcome_classes(tmp_path: Path, outcome: str, classification: str) -> None:
    contribution = _projected(tmp_path)["contributions"][0]
    feedback = compile_memory_effectiveness(
        contributions=[contribution],
        outcomes=[
            {
                "fact_id": contribution["fact_id"],
                "fact_revision": contribution["fact_revision"],
                "decision_id": "operating-decision:1234567890abcdef",
                "failure_identity": "route-replay",
                "outcome": outcome,
                "evidence_authority": "planning-route-receipt",
            }
        ],
    )
    assert feedback["evaluations"][0]["classification"] == classification


def test_newer_authority_marks_fact_stale(tmp_path: Path) -> None:
    contribution = _projected(tmp_path)["contributions"][0]
    feedback = compile_memory_effectiveness(
        contributions=[contribution],
        outcomes=[
            {
                "fact_id": contribution["fact_id"],
                "fact_revision": contribution["fact_revision"],
                "decision_id": "operating-decision:1234567890abcdef",
                "current_authority_status": "superseded",
                "evidence_authority": "canonical-planning-contract",
            }
        ],
    )
    assert feedback["evaluations"][0]["classification"] == "stale_or_superseded"


def test_material_recurrence_uses_existing_consequence_owner(tmp_path: Path) -> None:
    contribution = _projected(tmp_path)["contributions"][0]
    outcome = {
        "fact_id": contribution["fact_id"],
        "fact_revision": contribution["fact_revision"],
        "decision_id": "operating-decision:1234567890abcdef",
        "failure_identity": "route-replay",
        "outcome": "product-defect",
        "evidence_authority": "planning-route-receipt",
        "product_owner": "planning-route-decision",
    }
    decision = compile_operating_decision(
        inputs={"revisions": {"planning": "r1"}, "memory_contributions": [contribution], "memory_outcomes": [outcome]}
    )
    consequence = decision["context_consequences"][0]
    assert consequence["source_kind"] == "agentic-memory/effectiveness-finding/v1"
    assert consequence["consequence"] in {"defer-with-owner", "route-durable-improvement"}
    assert decision["memory_effectiveness"]["storage_posture"] == "sparse-existing-surfaces-only"


def test_stronger_owner_requires_proof_before_memory_stub(tmp_path: Path) -> None:
    contribution = _projected(tmp_path)["contributions"][0]
    base = {
        "fact_id": contribution["fact_id"],
        "fact_revision": contribution["fact_revision"],
        "decision_id": "operating-decision:1234567890abcdef",
        "outcome": "resolved-by-stronger-owner",
        "evidence_authority": "verification-receipt",
    }
    pending = compile_memory_effectiveness(contributions=[contribution], outcomes=[base])
    ready = compile_memory_effectiveness(contributions=[contribution], outcomes=[{**base, "stronger_owner_proof_status": "passed"}])
    assert pending["lifecycle_reviews"][0]["disposition"] == "retain"
    assert ready["lifecycle_reviews"][0]["disposition"] == "stub"
    assert ready["lifecycle_reviews"][0]["status"] == "ready"


def test_same_memory_input_has_same_canonical_decision_identity(tmp_path: Path) -> None:
    contribution = _projected(tmp_path)["contributions"][0]
    inputs = {"revisions": {"planning": "r1"}, "memory_contributions": [contribution]}
    first = compile_operating_decision(inputs=inputs)
    second = compile_operating_decision(inputs=inputs)
    assert first["decision_id"] == second["decision_id"]
    assert first["input_revisions"]["memory_effectiveness_revision"]
