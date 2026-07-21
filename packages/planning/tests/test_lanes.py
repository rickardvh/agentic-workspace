from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_planning_bootstrap.installer import (
    _build_execplan_record_from_todo_item,
    _write_execplan_record,
    activate_lane_record,
    archive_lane_record,
    close_lane_record,
    create_decomposition_record,
    create_execplan_scaffold,
    create_lane_record,
    doctor_bootstrap,
    install_bootstrap,
    planning_reconcile,
    planning_report,
    planning_summary,
    promote_decomposition_lane_to_lane_record,
)


def _assert_live_reference_contract(contract: dict[str, Any], *, reason_code: str, surface_suffix: str) -> None:
    assert contract["kind"] == "agentic-planning/live-reference-repair-contract/v1"
    assert contract["status"] == "fail-closed"
    owner = contract["owner"]
    assert isinstance(owner, dict)
    assert str(owner["surface"]).endswith(surface_suffix)
    assert "planning reconcile --target . --format json" in str(owner["reconcile_command"])
    assert contract["reason_code"] == reason_code
    assert {"summary", "status", "start", "next", "implement", "closeout", "doctor", "report"} <= set(contract["consumers"])
    assert "target-identity-mismatch" in contract["reject_on"]
    assert "evaluation-result-replaced" in contract["reject_on"]
    assert "stacked-rebase-head-drift" in contract["reject_on"]
    assert contract["residue_policy"] == "leave-no-checked-in-residue-after-successful-reconcile"


def test_create_decomposition_record_writes_schema_valid_owner(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    result = create_decomposition_record(
        decomposition_id="epic-alpha", title="Epic Alpha", outcome="Deliver the whole epic", target=tmp_path
    )
    assert not result.warnings
    path = tmp_path / ".agentic-workspace/planning/decompositions/epic-alpha.decomposition.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["kind"] == "planning-decomposition/v1"
    assert payload["larger_intended_outcome"] == "Deliver the whole epic"
    assert payload["candidate_lanes"] == []


def _write_execplan_fixture(path: Path, *, item_id: str, status: str) -> None:
    record = _build_execplan_record_from_todo_item(
        title="Slice One",
        item_id=item_id,
        status=status,
        why_now="lane activation needs a registered slice execplan.",
        next_action="execute the slice.",
        done_when="slice proof passes.",
    )
    _write_execplan_record(record_path=path, record=record)


def _write_decomposition(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Planning hierarchy",
                "status": "ready-for-lane-promotion",
                "larger_intended_outcome": "Tie epic, lane, and slice artifacts together.",
                "parent_acceptance": {
                    "original_intent": "Tie epic, lane, and slice artifacts together.",
                    "acceptance_target": "Lane strategy and proof aggregation are durable before slices execute.",
                    "parent_proof_required": "Focused Planning and workspace tests pass.",
                },
                "non_goals": [],
                "candidate_lanes": [
                    {
                        "id": "lane-artifacts",
                        "title": "Lane artifacts",
                        "readiness": "ready",
                        "outcome": "Add first-class lane owner artifacts.",
                        "owner_surface": "",
                        "proof": "Lane summary and lifecycle tests pass.",
                        "slice_contribution_to_parent": "Creates the missing middle planning layer.",
                        "residual_parent_intent": "transition gates and reporting still need implementation.",
                        "parent_proof_boundary": "lane-only",
                        "human_confirmation_needed": [],
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Focused Planning tests pass."],
                "promotion_rule": "Promote ready lanes to lane records before slice execplans.",
                "references": [],
                "notes": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_lane_create_projects_first_class_lane_record(tmp_path: Path) -> None:
    result = create_lane_record(
        lane_id="planning-lane",
        title="Planning Lane",
        target=tmp_path,
        outcome="Represent lane strategy outside execplans.",
        purpose="Make the parent intent concrete before slices start.",
    )

    assert [action.kind for action in result.actions] == ["created", "updated", "proof", "proof"]
    lane_path = tmp_path / ".agentic-workspace" / "planning" / "lanes" / "planning-lane.lane.json"
    record = json.loads(lane_path.read_text(encoding="utf-8"))
    assert record["kind"] == "planning-lane/v1"
    assert record["lane_outcome"] == "Represent lane strategy outside execplans."
    assert record["slice_sequence"] == []

    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    assert state["roadmap"]["lanes"][0]["owner_surface"] == ".agentic-workspace/planning/lanes/planning-lane.lane.json"

    summary = planning_summary(target=tmp_path, profile="compact")
    assert summary["lanes"]["record_count"] == 1
    assert summary["lanes"]["records"][0]["id"] == "planning-lane"
    assert summary["lanes"]["migration"]["preferred_owner"] == ".agentic-workspace/planning/lanes/<id>.lane.json"
    assert "lanes" in summary["schema"]["shared_fields"]


def test_promote_decomposition_lane_creates_lane_owner_without_execplan(tmp_path: Path) -> None:
    decomposition_path = tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "parent.decomposition.json"
    _write_decomposition(decomposition_path)

    result = promote_decomposition_lane_to_lane_record("lane-artifacts", target=tmp_path)

    assert [action.kind for action in result.actions] == ["created", "updated", "updated", "proof", "proof"]
    lane_path = tmp_path / ".agentic-workspace/planning/lanes/lane-artifacts.lane.json"
    assert lane_path.exists()
    assert not (tmp_path / ".agentic-workspace/planning/execplans/lane-artifacts.plan.json").exists()
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    assert lane["parent_decomposition_ref"] == ".agentic-workspace/planning/decompositions/parent.decomposition.json"
    assert lane["parent_close_permission"] == "do-not-close-parent"
    assert lane["residual_lane_work"] == "transition gates and reporting still need implementation."

    decomposition = json.loads(decomposition_path.read_text(encoding="utf-8"))
    candidate = decomposition["candidate_lanes"][0]
    assert candidate["readiness"] == "promoted"
    assert candidate["owner_surface"] == ".agentic-workspace/planning/lanes/lane-artifacts.lane.json"


def test_promote_decomposition_lane_reuses_matching_owner(tmp_path: Path) -> None:
    decomposition_path = tmp_path / ".agentic-workspace/planning/decompositions/parent.decomposition.json"
    _write_decomposition(decomposition_path)
    promote_decomposition_lane_to_lane_record("lane-artifacts", target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    before_decomposition = decomposition_path.read_bytes()
    before_state = state_path.read_bytes()

    dry_run = promote_decomposition_lane_to_lane_record("lane-artifacts", target=tmp_path, dry_run=True)

    assert [action.kind for action in dry_run.actions] == ["would update", "would update", "proof", "proof"]
    assert decomposition_path.read_bytes() == before_decomposition
    assert state_path.read_bytes() == before_state

    result = promote_decomposition_lane_to_lane_record("lane-artifacts", target=tmp_path)

    assert [action.kind for action in result.actions] == ["updated", "updated", "proof", "proof"]
    warnings = planning_summary(target=tmp_path, profile="compact")["planning_surface_health"]["warnings"]
    assert not [warning for warning in warnings if warning["warning_class"] == "planning_state_v1_schema"]


def test_lane_create_rolls_back_when_state_write_fails(tmp_path: Path, monkeypatch) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    before_state = state_path.read_bytes()

    def fail_state_write(*_args, **_kwargs) -> None:
        raise OSError("injected state write failure")

    monkeypatch.setattr("repo_planning_bootstrap.installer._write_state_to_toml", fail_state_write)
    result = create_lane_record(lane_id="atomic-lane", title="Atomic Lane", target=tmp_path)

    assert [action.kind for action in result.actions] == ["manual review"]
    assert not (tmp_path / ".agentic-workspace/planning/lanes/atomic-lane.lane.json").exists()
    assert state_path.read_bytes() == before_state


def test_lane_promotion_rolls_back_every_surface_when_state_write_fails(tmp_path: Path, monkeypatch) -> None:
    decomposition_path = tmp_path / ".agentic-workspace/planning/decompositions/parent.decomposition.json"
    _write_decomposition(decomposition_path)
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    before_decomposition = decomposition_path.read_bytes()
    before_state = state_path.read_bytes()

    def fail_state_write(*_args, **_kwargs) -> None:
        raise OSError("injected state write failure")

    monkeypatch.setattr("repo_planning_bootstrap.installer._write_state_to_toml", fail_state_write)
    result = promote_decomposition_lane_to_lane_record("lane-artifacts", target=tmp_path)

    assert [action.kind for action in result.actions] == ["manual review"]
    assert not (tmp_path / ".agentic-workspace/planning/lanes/lane-artifacts.lane.json").exists()
    assert decomposition_path.read_bytes() == before_decomposition
    assert state_path.read_bytes() == before_state


def test_lane_promotion_rejects_incompatible_owner_without_mutating_it(tmp_path: Path) -> None:
    decomposition_path = tmp_path / ".agentic-workspace/planning/decompositions/parent.decomposition.json"
    _write_decomposition(decomposition_path)
    create_lane_record(lane_id="lane-artifacts", title="Different Owner", target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace/planning/lanes/lane-artifacts.lane.json"
    before_lane = lane_path.read_bytes()

    result = promote_decomposition_lane_to_lane_record("lane-artifacts", target=tmp_path)

    assert [action.kind for action in result.actions] == ["manual review"]
    assert result.conflict_owner == ".agentic-workspace/planning/lanes/lane-artifacts.lane.json"
    assert result.reason_code == "incompatible-parent-provenance"
    assert "--alternate-lane-id lane-artifacts-from-parent" in result.recovery_command
    assert lane_path.read_bytes() == before_lane
    candidate = json.loads(decomposition_path.read_text(encoding="utf-8"))["candidate_lanes"][0]
    assert candidate["readiness"] == "ready"
    assert candidate["owner_surface"] == ""

    recovered = promote_decomposition_lane_to_lane_record(
        "lane-artifacts",
        alternate_lane_id="lane-artifacts-from-parent",
        target=tmp_path,
    )

    assert [action.kind for action in recovered.actions] == ["created", "updated", "updated", "proof", "proof"]
    alternate_path = tmp_path / ".agentic-workspace/planning/lanes/lane-artifacts-from-parent.lane.json"
    assert alternate_path.exists()
    assert lane_path.read_bytes() == before_lane
    recovered_candidate = json.loads(decomposition_path.read_text(encoding="utf-8"))["candidate_lanes"][0]
    assert recovered_candidate["readiness"] == "promoted"
    assert recovered_candidate["owner_surface"] == ".agentic-workspace/planning/lanes/lane-artifacts-from-parent.lane.json"


def test_lane_activate_projects_current_slice_execplan_ref_and_keeps_summary_clean(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="activation-lane", title="Activation Lane", target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace/planning/lanes/activation-lane.lane.json"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["slice_sequence"] = [
        {
            "id": "slice-one",
            "title": "Slice One",
            "status": "ready",
            "execplan_ref": ".agentic-workspace/planning/execplans/slice-one.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Prove activation projects the slice execplan.",
        }
    ]
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")
    _write_execplan_fixture(
        tmp_path / ".agentic-workspace/planning/execplans/slice-one.plan.json",
        item_id="slice-one",
        status="planned",
    )

    result = activate_lane_record("activation-lane", target=tmp_path, current_slice="slice-one")

    assert [action.kind for action in result.actions] == ["updated", "updated", "proof", "proof"]
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    active_lane = state["roadmap"]["lanes"][0]
    assert active_lane["status"] == "active"
    assert active_lane["maturity"] == "active"
    assert active_lane["current_slice"] == "slice-one"
    assert active_lane["execplan"] == ".agentic-workspace/planning/execplans/slice-one.plan.json"
    assert active_lane["next_action"] == "execute the slice."
    assert active_lane["done_when"] == "slice proof passes."
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    assert lane["current_slice"] == "slice-one"
    assert lane["slice_sequence"][0]["execplan_ref"] == active_lane["execplan"]

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]
    assert not [warning for warning in warnings if warning["warning_class"] == "execplan_unregistered"]
    assert not [warning for warning in warnings if warning["warning_class"] == "historical_work_in_live_planning_state"]
    doctor = doctor_bootstrap(target=tmp_path)
    assert doctor.warnings == []


def test_lane_health_rejects_current_slice_missing_execplan(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="activation-lane", title="Activation Lane", target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace/planning/lanes/activation-lane.lane.json"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["status"] = "active"
    lane["current_slice"] = "slice-one"
    lane["slice_sequence"] = [
        {
            "id": "slice-one",
            "title": "Slice One",
            "status": "active",
            "execplan_ref": ".agentic-workspace/planning/execplans/missing-slice.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Expose missing live owner relations.",
        },
        {
            "id": "completed-slice",
            "title": "Completed Slice",
            "status": "completed",
            "execplan_ref": ".agentic-workspace/planning/execplans/completed-slice.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Completed non-current tombstone may omit execplan.",
        },
    ]
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")

    summary = planning_summary(target=tmp_path, profile="compact")
    health = summary["planning_surface_health"]

    assert health["status"] == "not-clean"
    warning = next(item for item in health["warnings"] if item["warning_class"] == "lane_current_slice_non_executable")
    assert warning["repair_affordance"]["relation"] == "lane.current_slice"
    assert warning["repair_affordance"]["reason_code"] == "current-slice-execplan-missing"
    assert warning["repair_affordance"]["current_slice"] == "slice-one"
    contract = warning["repair_affordance"]["repair_contract"]
    _assert_live_reference_contract(
        contract,
        reason_code="current-slice-execplan-missing",
        surface_suffix="activation-lane.lane.json",
    )
    assert health["live_reference_integrity"]["status"] == "fail-closed"
    assert health["live_reference_integrity"]["contracts"] == [contract]

    report = planning_report(target=tmp_path)
    report_warning = next(
        item for item in report["planning_surface_health"]["warnings"] if item["warning_class"] == "lane_current_slice_non_executable"
    )
    _assert_live_reference_contract(
        report_warning["repair_affordance"]["repair_contract"],
        reason_code="current-slice-execplan-missing",
        surface_suffix="activation-lane.lane.json",
    )

    doctor = doctor_bootstrap(target=tmp_path)
    doctor_warning = next(item for item in doctor.warnings if item["warning_class"] == "lane_current_slice_non_executable")
    _assert_live_reference_contract(
        doctor_warning["repair_affordance"]["repair_contract"],
        reason_code="current-slice-execplan-missing",
        surface_suffix="activation-lane.lane.json",
    )


def test_lane_activate_demotes_prior_active_slice_when_successor_becomes_current(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="activation-lane", title="Activation Lane", target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace/planning/lanes/activation-lane.lane.json"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["status"] = "active"
    lane["current_slice"] = "slice-one"
    lane["slice_sequence"] = [
        {
            "id": "slice-one",
            "title": "Slice One",
            "status": "active",
            "execplan_ref": ".agentic-workspace/planning/execplans/slice-one.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Prior slice.",
        },
        {
            "id": "slice-two",
            "title": "Slice Two",
            "status": "ready",
            "execplan_ref": ".agentic-workspace/planning/execplans/slice-two.plan.json",
            "depends_on": ["slice-one"],
            "purpose_for_lane": "Successor slice.",
        },
    ]
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")
    _write_execplan_fixture(tmp_path / ".agentic-workspace/planning/execplans/slice-one.plan.json", item_id="slice-one", status="completed")
    _write_execplan_fixture(tmp_path / ".agentic-workspace/planning/execplans/slice-two.plan.json", item_id="slice-two", status="planned")

    result = activate_lane_record("activation-lane", target=tmp_path, current_slice="slice-two")

    assert [action.kind for action in result.actions] == ["updated", "updated", "proof", "proof"]
    updated = json.loads(lane_path.read_text(encoding="utf-8"))
    assert updated["current_slice"] == "slice-two"
    statuses = {item["id"]: item["status"] for item in updated["slice_sequence"]}
    assert statuses == {"slice-one": "completed", "slice-two": "active"}
    warnings = planning_summary(target=tmp_path, profile="compact")["planning_surface_health"]["warnings"]
    assert not [item for item in warnings if item["warning_class"] == "lane_current_slice_non_executable"]


def test_lane_activate_infers_current_slice_execplan_when_slice_sequence_is_minimal(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="activation-lane", title="Activation Lane", target=tmp_path)
    _write_execplan_fixture(
        tmp_path / ".agentic-workspace/planning/execplans/slice-one.plan.json",
        item_id="slice-one",
        status="planned",
    )

    result = activate_lane_record("activation-lane", target=tmp_path, current_slice="slice-one")

    assert [action.kind for action in result.actions] == ["updated", "updated", "proof", "proof"]
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    active_lane = state["roadmap"]["lanes"][0]
    assert active_lane["status"] == "active"
    assert active_lane["current_slice"] == "slice-one"
    assert active_lane["execplan"] == ".agentic-workspace/planning/execplans/slice-one.plan.json"
    assert active_lane["next_action"] == "execute the slice."
    assert active_lane["done_when"] == "slice proof passes."
    lane = json.loads((tmp_path / ".agentic-workspace/planning/lanes/activation-lane.lane.json").read_text(encoding="utf-8"))
    assert lane["current_slice"] == "slice-one"
    assert lane["slice_sequence"] == [
        {
            "id": "slice-one",
            "title": "Slice One",
            "status": "active",
            "execplan_ref": active_lane["execplan"],
            "depends_on": [],
            "purpose_for_lane": lane["purpose_for_parent"],
        }
    ]

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]
    assert not [warning for warning in warnings if warning["warning_class"] == "execplan_unregistered"]
    doctor = doctor_bootstrap(target=tmp_path)
    assert doctor.warnings == []


def test_new_plan_attaches_first_execplan_to_already_active_lane(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="activation-lane", title="Activation Lane", target=tmp_path)

    result = create_execplan_scaffold(
        plan_id="slice-one",
        title="Slice One",
        target=tmp_path,
        activate=True,
        lane="activation-lane",
    )

    assert [action.kind for action in result.actions] == ["created", "updated", "updated", "updated", "next", "next"]
    assert any("attached execplan 'slice-one' to active lane 'activation-lane'" in action.detail for action in result.actions)
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    active_lane = state["roadmap"]["lanes"][0]
    assert active_lane["owner_surface"] == ".agentic-workspace/planning/lanes/activation-lane.lane.json"
    assert active_lane["execplan"] == ".agentic-workspace/planning/execplans/slice-one.plan.json"
    lane = json.loads((tmp_path / ".agentic-workspace/planning/lanes/activation-lane.lane.json").read_text(encoding="utf-8"))
    assert lane["status"] == "active"
    assert lane["current_slice"] == "slice-one"
    assert lane["slice_sequence"][0]["execplan_ref"] == active_lane["execplan"]

    summary = planning_summary(target=tmp_path, profile="compact")
    assert summary["planning_surface_health"]["warnings"] == []


def test_new_plan_does_not_attach_unrelated_plan_to_single_active_lane(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="activation-lane", title="Activation Lane", target=tmp_path)

    result = create_execplan_scaffold(plan_id="unrelated", title="Unrelated", target=tmp_path, activate=True)

    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    active_lane = state["roadmap"]["lanes"][0]
    assert "execplan" not in active_lane
    assert not any("attached execplan" in action.detail for action in result.actions)


def test_lane_activate_without_execplan_is_a_noop(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="activation-lane", title="Activation Lane", target=tmp_path)

    result = activate_lane_record("activation-lane", target=tmp_path)

    assert [action.kind for action in result.actions] == ["manual review"]
    lane = json.loads((tmp_path / ".agentic-workspace/planning/lanes/activation-lane.lane.json").read_text(encoding="utf-8"))
    assert lane["status"] == "ready"
    assert planning_summary(target=tmp_path, profile="compact")["planning_surface_health"]["warnings"] == []


def test_new_plan_does_not_guess_when_multiple_lanes_are_active(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    for lane_id in ("lane-one", "lane-two"):
        create_lane_record(lane_id=lane_id, title=lane_id, target=tmp_path)
        activate_lane_record(lane_id, target=tmp_path)

    create_execplan_scaffold(plan_id="slice-one", title="Slice One", target=tmp_path, activate=True)

    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))
    assert all("execplan" not in lane for lane in state["roadmap"]["lanes"])


def test_lane_close_and_archive_preserve_parent_contribution(tmp_path: Path) -> None:
    create_lane_record(lane_id="closeable-lane", title="Closeable Lane", target=tmp_path)
    activate_lane_record("closeable-lane", target=tmp_path)

    close_result = close_lane_record(
        "closeable-lane",
        target=tmp_path,
        proof="lane lifecycle tests passed",
        residual_work="none",
        parent_contribution="lane artifacts now own strategy and proof aggregation",
        parent_close_permission="may-advance-parent",
    )
    assert [action.kind for action in close_result.actions] == ["updated", "updated", "next safe action", "proof", "proof"]
    assert any("lane-archive closeable-lane" in action.detail for action in close_result.actions if action.kind == "next safe action")
    summary = planning_summary(target=tmp_path, profile="compact")
    assert summary["planning_surface_health"]["status"] == "not-clean"
    warning = next(
        warning for warning in summary["planning_surface_health"]["warnings"] if warning["warning_class"] == "closed_lane_record_live_state"
    )
    _assert_live_reference_contract(
        warning["repair_affordance"],
        reason_code="closed-lane-live-reference",
        surface_suffix="closeable-lane.lane.json",
    )
    assert summary["planning_surface_health"]["live_reference_integrity"]["contracts"] == [warning["repair_affordance"]]
    lane = summary["lanes"]["records"][0]
    assert lane["status"] == "closed"
    assert lane["proof_aggregation"]["status"] == "satisfied"
    assert lane["lane_to_epic_contribution"] == "lane artifacts now own strategy and proof aggregation"
    assert lane["parent_close_permission"] == "may-advance-parent"
    raw_lane = json.loads((tmp_path / ".agentic-workspace/planning/lanes/closeable-lane.lane.json").read_text(encoding="utf-8"))
    assert raw_lane["completion_gate"]["kind"] == "agentic-workspace/completion-gate/v1"
    assert raw_lane["completion_gate"]["status"] == "allowed"
    assert raw_lane["completion_gate"]["claim_level_requested"] == "lane-complete"
    assert raw_lane["completion_gate"]["claim_level_allowed"] == "lane-complete"
    assert "lane_complete" in raw_lane["completion_gate"]["claim_authorization"]["allowed_claim_classes"]
    assert "full_intent_complete" in raw_lane["completion_gate"]["claim_authorization"]["blocked_claim_classes"]

    archive_result = archive_lane_record("closeable-lane", target=tmp_path)
    assert [action.kind for action in archive_result.actions] == ["archived", "updated", "proof", "proof"]
    assert not (tmp_path / ".agentic-workspace/planning/lanes/closeable-lane.lane.json").exists()
    assert (tmp_path / ".agentic-workspace/planning/lanes/archive/closeable-lane.lane.json").exists()
    post_archive = planning_summary(target=tmp_path, profile="compact")
    assert post_archive["planning_surface_health"]["status"] == "clean"
    assert post_archive["lanes"]["record_count"] == 0
    assert post_archive["lanes"]["archived_count"] == 1


def test_lane_close_authorizes_full_parent_issue_closure_when_explicitly_permitted(tmp_path: Path) -> None:
    create_lane_record(lane_id="parent-closeable", title="Parent Closeable", target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace/planning/lanes/parent-closeable.lane.json"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["references"] = [
        {"kind": "external-work", "target": "GitHub #123", "label": "GitHub #123", "role": "parent", "locator": "GitHub #123"}
    ]
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")

    close_lane_record(
        "parent-closeable",
        target=tmp_path,
        proof="all child proof satisfied",
        residual_work="none",
        parent_contribution="the parent intent is fully satisfied",
        parent_close_permission="may-close-parent",
    )

    closed = json.loads(lane_path.read_text(encoding="utf-8"))
    gate = closed["completion_gate"]
    assert gate["claim_level_requested"] == "full-intent-complete"
    assert gate["claim_level_allowed"] == "full-intent-complete"
    assert "full_intent_complete" in gate["claim_authorization"]["allowed_claim_classes"]
    issue_action = next(action for action in gate["claim_authorization"]["closure_actions"] if action["target"] == "#123")
    assert issue_action["authorized"] is True


def test_summary_and_doctor_validate_invalid_active_lane_schema(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace" / "planning" / "lanes" / "invalid-lane.lane.json"
    lane_path.parent.mkdir(parents=True, exist_ok=True)
    lane_path.write_text(
        json.dumps(
            {
                "kind": "planning-lane/v1",
                "id": "invalid-lane",
                "title": "Invalid Lane",
                "status": "active",
                "parent_decomposition_ref": "",
                "lane_outcome": "Expose schema diagnostics before closeout.",
                "purpose_for_parent": "Prove diagnostics catch malformed slices.",
                "subsystems": [],
                "technical_strategy": "Use an intentionally malformed slice.",
                "slice_sequence": [
                    {
                        "id": "bad-slice",
                        "title": "Bad Slice",
                        "status": "active",
                        "execplan": ".agentic-workspace/planning/execplans/bad-slice.plan.json",
                        "done_when": "This key is not part of the lane slice schema.",
                    }
                ],
                "acceptance_boundary": "Diagnostics report the schema error.",
                "proof_strategy": "Summary and doctor warnings name the invalid record.",
                "proof_aggregation": {"status": "not-started", "evidence": [], "known_gaps": []},
                "residual_lane_work": "",
                "lane_to_epic_contribution": "",
                "parent_close_permission": "do-not-close-parent",
                "closeout_state": {"status": "open", "summary": "", "residual_work": "", "next_owner": ""},
                "references": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]
    assert summary["planning_surface_health"]["status"] == "not-clean"
    schema_warning = next(warning for warning in warnings if warning["warning_class"] == "planning_lane_schema_invalid")
    assert schema_warning["path"].endswith("invalid-lane.lane.json")
    assert "slice_sequence.0" in schema_warning["message"]
    assert "execplan_ref" in schema_warning["message"]
    affordance = schema_warning["repair_affordance"]
    assert affordance["kind"] == "planning-lane-schema-repair/v1"
    assert affordance["reference_shape"] == {"kind": "artifact", "path": "<repo-relative-path>", "role": "context"}
    assert affordance["slice_sequence_entry_shape"]["execplan_ref"].endswith("<slice>.plan.json")
    assert affordance["slice_sequence_entry_shape"]["depends_on"] == []
    assert "purpose_for_lane" in affordance["slice_sequence_entry_shape"]

    doctor = doctor_bootstrap(target=tmp_path)
    doctor_warning = next(warning for warning in doctor.warnings if warning["warning_class"] == "planning_lane_schema_invalid")
    assert doctor_warning["path"].endswith("invalid-lane.lane.json")
    assert "done_when" in doctor_warning["message"]


def test_summary_warns_when_invalid_lane_status_makes_record_unprojectable(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="review-lane", title="Review Lane", target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace" / "planning" / "lanes" / "review-lane.lane.json"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["slice_sequence"] = [
        {
            "id": "review-slice",
            "title": "Review Slice",
            "status": "ready-for-review",
            "execplan_ref": ".agentic-workspace/planning/execplans/review-slice.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Prove unsupported status values do not disappear silently.",
        }
    ]
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")

    summary = planning_summary(target=tmp_path, profile="tiny")

    assert summary["lanes"]["status"] == "attention"
    assert summary["lanes"]["record_count"] == 0
    assert summary["lanes"]["invalid_record_count"] == 1
    invalid = summary["lanes"]["invalid_records"][0]
    assert invalid["path"].endswith("review-lane.lane.json")
    status_detail = invalid["status_details"][0]
    assert status_detail["field"] == "slice_sequence.0.status"
    assert status_detail["value"] == "ready-for-review"
    assert "completed" in status_detail["accepted_values"]
    assert summary["planning_surface_health"]["status"] == "not-clean"
    warning = next(warning for warning in summary["planning_surface_health"]["warnings"] if warning["path"] == invalid["path"])
    assert warning["warning_class"] == "planning_lane_schema_invalid"
    assert "ready-for-review" in warning["message"]
    assert "accepted values" in warning["message"]


def test_summary_projects_lane_records_with_accepted_status_values(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    create_lane_record(lane_id="accepted-lane", title="Accepted Lane", target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace" / "planning" / "lanes" / "accepted-lane.lane.json"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["slice_sequence"] = [
        {
            "id": "accepted-slice",
            "title": "Accepted Slice",
            "status": "completed",
            "execplan_ref": ".agentic-workspace/planning/execplans/accepted-slice.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Prove accepted status values still project.",
        }
    ]
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")
    _write_execplan_fixture(
        tmp_path / ".agentic-workspace/planning/execplans/accepted-slice.plan.json",
        item_id="accepted-slice",
        status="planned",
    )

    summary = planning_summary(target=tmp_path, profile="tiny")

    assert summary["lanes"]["status"] == "present"
    assert summary["lanes"]["record_count"] == 1
    assert summary["lanes"]["invalid_record_count"] == 0
    assert not summary["lanes"].get("invalid_records")
    assert not [
        warning for warning in summary["planning_surface_health"]["warnings"] if warning["warning_class"] == "planning_lane_schema_invalid"
    ]


def test_lane_child_reconciliation_dry_run_apply_and_unknown_fail_closed(tmp_path: Path) -> None:
    create_lane_record(lane_id="trust-lane", title="Trust Lane", target=tmp_path)
    lane_path = tmp_path / ".agentic-workspace/planning/lanes/trust-lane.lane.json"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["children"] = [
        {
            "id": "landed",
            "issue_ref": "#1",
            "pr_ref": "#11",
            "outcome": "landed",
            "reason": "",
            "proof_ref": "PR #11 CI",
            "new_owner": "",
            "residual_intent": "",
        },
        {
            "id": "dismissed",
            "issue_ref": "#2",
            "pr_ref": "#12",
            "outcome": "dismissed-not-planned",
            "reason": "premise invalid",
            "proof_ref": "",
            "new_owner": "",
            "residual_intent": "",
            "outcome_authority": "human-reviewed",
        },
        {
            "id": "follow-up",
            "issue_ref": "#3",
            "pr_ref": "",
            "outcome": "unresolved",
            "reason": "",
            "proof_ref": "",
            "new_owner": "",
            "residual_intent": "follow-up remains",
        },
        {
            "id": "closed-pr",
            "issue_ref": "#4",
            "pr_ref": "#13",
            "outcome": "unresolved",
            "reason": "",
            "proof_ref": "",
            "new_owner": "",
            "residual_intent": "",
        },
        {
            "id": "rerouted",
            "issue_ref": "#5",
            "pr_ref": "",
            "outcome": "superseded-or-rerouted",
            "reason": "moved to #99",
            "proof_ref": "",
            "new_owner": "#99",
            "residual_intent": "owned by #99",
            "outcome_authority": "human-reviewed",
        },
        {
            "id": "reopened",
            "issue_ref": "#6",
            "pr_ref": "#14",
            "outcome": "landed",
            "reason": "",
            "proof_ref": "old proof",
            "new_owner": "",
            "residual_intent": "",
        },
        {
            "id": "missing",
            "issue_ref": "#7",
            "pr_ref": "#15",
            "outcome": "unresolved",
            "reason": "",
            "proof_ref": "old proof",
            "new_owner": "",
            "residual_intent": "",
        },
        {
            "id": "incomplete-reroute",
            "issue_ref": "#8",
            "pr_ref": "",
            "outcome": "superseded-or-rerouted",
            "reason": "moved somewhere else",
            "proof_ref": "",
            "new_owner": "#100",
            "residual_intent": "",
            "outcome_authority": "human-reviewed",
        },
    ]
    lane["slice_sequence"] = [
        {"id": "landed", "title": "Landed", "status": "active", "execplan_ref": "", "depends_on": [], "purpose_for_lane": "test"}
    ]
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")
    cache_path = tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json"
    cache_path.parent.mkdir(parents=True)
    refreshed_at = datetime.now(UTC).isoformat()
    cache_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refreshed_at": refreshed_at,
                "refresh_metadata": {"adapter": "github-gh-cli", "state": "all", "refreshed_at": refreshed_at},
                "items": [
                    {"system": "github", "id": "#1", "title": "one", "kind": "issue", "status": "closed"},
                    {"system": "github", "id": "#2", "title": "two", "kind": "issue", "status": "closed"},
                    {"system": "github", "id": "#3", "title": "three", "kind": "issue", "status": "open"},
                    {"system": "github", "id": "#4", "title": "four", "kind": "issue", "status": "closed"},
                    {"system": "github", "id": "#5", "title": "five", "kind": "issue", "status": "closed"},
                    {"system": "github", "id": "#6", "title": "six", "kind": "issue", "status": "open"},
                    {"system": "github", "id": "#8", "title": "eight", "kind": "issue", "status": "closed"},
                    {"system": "github", "id": "PR #11", "title": "merged", "kind": "pull-request", "status": "merged"},
                    {"system": "github", "id": "PR #12", "title": "closed", "kind": "pull-request", "status": "closed"},
                    {"system": "github", "id": "PR #13", "title": "closed", "kind": "pull-request", "status": "closed"},
                    {"system": "github", "id": "PR #14", "title": "merged", "kind": "pull-request", "status": "merged"},
                    {"system": "github", "id": "PR #15", "title": "merged", "kind": "pull-request", "status": "merged"},
                ],
            }
        ),
        encoding="utf-8",
    )
    before = lane_path.read_text(encoding="utf-8")

    dry_run = planning_reconcile(target=tmp_path, lane="trust-lane", apply_lane_reconcile=True, dry_run=True)["lane_child_reconciliation"]
    assert dry_run["unknown_count"] == 5
    assert dry_run["parent_auto_closed"] is False
    assert dry_run["applied"] is False
    assert lane_path.read_text(encoding="utf-8") == before

    applied = planning_reconcile(target=tmp_path, lane="trust-lane", apply_lane_reconcile=True)["lane_child_reconciliation"]
    record = json.loads(lane_path.read_text(encoding="utf-8"))
    assert applied["applied"] is True
    assert record["children"][0]["outcome"] == "landed"
    assert record["children"][1]["outcome"] == "dismissed-not-planned"
    assert record["children"][2]["outcome"] == "unresolved"
    assert record["children"][3]["outcome"] == "closed-without-merge"
    assert record["children"][4]["outcome"] == "superseded-or-rerouted"
    assert record["children"][5]["outcome"] == "unresolved"
    assert record["children"][6]["outcome"] == "unresolved"
    assert record["children"][7]["outcome"] == "unresolved"
    assert any("closed-pr" in gap for gap in record["proof_aggregation"]["known_gaps"])
    assert record["parent_close_permission"] == "do-not-close-parent"
    assert record["status"] == "ready"
    assert record["slice_sequence"][0]["status"] == "completed"
    assert applied["exact_delta"]["slice_sequence"]["before"] == lane["slice_sequence"]
    assert applied["exact_delta"]["slice_sequence"]["after"][0]["status"] == "completed"
    assert applied["external_state"]["authority"] == "provider-adapter-observation"

    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    cached["refreshed_at"] = "2020-01-01T00:00:00+00:00"
    cached["refresh_metadata"]["refreshed_at"] = cached["refreshed_at"]
    cache_path.write_text(json.dumps(cached), encoding="utf-8")
    stale = planning_reconcile(target=tmp_path, lane="trust-lane", apply_lane_reconcile=True)["lane_child_reconciliation"]
    assert stale["status"] == "blocked"
    assert stale["reason"] == "external-state-stale-or-insufficient"


def test_planning_report_includes_lane_writer_helper_and_status(tmp_path: Path) -> None:
    create_lane_record(lane_id="report-lane", title="Report Lane", target=tmp_path)

    report = planning_report(target=tmp_path)

    assert report["status"]["lane_record_count"] == 1
    assert report["lanes"]["records"][0]["id"] == "report-lane"
    helpers = {helper["artifact"]: helper for helper in report["writer_helpers"]["helpers"]}
    assert "lane-create" in helpers["lane_record"]["command"]
