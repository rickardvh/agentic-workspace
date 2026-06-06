from __future__ import annotations

import json
import tomllib
from pathlib import Path

from repo_planning_bootstrap.installer import (
    _build_execplan_record_from_todo_item,
    _write_execplan_record,
    activate_lane_record,
    archive_lane_record,
    close_lane_record,
    create_lane_record,
    doctor_bootstrap,
    install_bootstrap,
    planning_report,
    planning_summary,
    promote_decomposition_lane_to_lane_record,
)


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
    assert active_lane["current_slice"] == "slice-one"
    assert active_lane["execplan"] == ".agentic-workspace/planning/execplans/slice-one.plan.json"

    summary = planning_summary(target=tmp_path, profile="compact")
    warnings = summary["planning_surface_health"]["warnings"]
    assert not [warning for warning in warnings if warning["warning_class"] == "execplan_unregistered"]
    assert not [warning for warning in warnings if warning["warning_class"] == "historical_work_in_live_planning_state"]
    doctor = doctor_bootstrap(target=tmp_path)
    assert doctor.warnings == []


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
    assert any(warning["warning_class"] == "closed_lane_record_live_state" for warning in summary["planning_surface_health"]["warnings"])
    lane = summary["lanes"]["records"][0]
    assert lane["status"] == "closed"
    assert lane["proof_aggregation"]["status"] == "satisfied"
    assert lane["lane_to_epic_contribution"] == "lane artifacts now own strategy and proof aggregation"
    assert lane["parent_close_permission"] == "may-advance-parent"

    archive_result = archive_lane_record("closeable-lane", target=tmp_path)
    assert [action.kind for action in archive_result.actions] == ["archived", "updated", "proof", "proof"]
    assert not (tmp_path / ".agentic-workspace/planning/lanes/closeable-lane.lane.json").exists()
    assert (tmp_path / ".agentic-workspace/planning/lanes/archive/closeable-lane.lane.json").exists()
    post_archive = planning_summary(target=tmp_path, profile="compact")
    assert post_archive["planning_surface_health"]["status"] == "clean"
    assert post_archive["lanes"]["record_count"] == 0
    assert post_archive["lanes"]["archived_count"] == 1


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

    doctor = doctor_bootstrap(target=tmp_path)
    doctor_warning = next(warning for warning in doctor.warnings if warning["warning_class"] == "planning_lane_schema_invalid")
    assert doctor_warning["path"].endswith("invalid-lane.lane.json")
    assert "done_when" in doctor_warning["message"]


def test_planning_report_includes_lane_writer_helper_and_status(tmp_path: Path) -> None:
    create_lane_record(lane_id="report-lane", title="Report Lane", target=tmp_path)

    report = planning_report(target=tmp_path)

    assert report["status"]["lane_record_count"] == 1
    assert report["lanes"]["records"][0]["id"] == "report-lane"
    helpers = {helper["artifact"]: helper for helper in report["writer_helpers"]["helpers"]}
    assert "lane-create" in helpers["lane_record"]["command"]
