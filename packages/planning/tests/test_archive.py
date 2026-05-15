from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from planning_test_support import *


def test_archive_execplan_rejects_schema_invalid_json_record(tmp_path: Path) -> None:
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["surprise_machine_field"] = "not in the schema"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "manual review" and "planning-execplan.schema.json" in action.detail for action in result.actions)
    assert any(warning["warning_class"] == "archive_execplan_schema_drift" for warning in result.warnings)


def test_archive_execplan_removes_completed_plan_after_distillation(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")

    result = archive_execplan("plan-alpha", target=tmp_path)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"

    assert not archived_record_path.exists()
    assert not plan_path.exists()
    assert not record_path.exists()
    assert any(action.kind == "closed" and action.path == record_path for action in result.actions)
    assert any(
        action.kind == "closeout distillation" and "Memory" in action.detail and "docs" in action.detail for action in result.actions
    )


def test_archive_execplan_blocks_unfinished_larger_intent_without_continuation_surface(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "- This slice completes the larger intended outcome: yes", "- This slice completes the larger intended outcome: no"
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_intent_continuity" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Continuation surface" in action.detail for action in result.actions
    )


def test_archive_execplan_blocks_missing_required_follow_on_when_parent_intent_is_unfinished(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- This slice completes the larger intended outcome: yes", "- This slice completes the larger intended outcome: no")
        .replace("- Continuation surface: none", "- Continuation surface: `ROADMAP.md` candidate `next-slice`"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_required_follow_on" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Required Continuation" in action.detail
        for action in result.actions
    )


def test_archive_execplan_blocks_missing_execution_summary(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "- Outcome delivered: Added one bounded planning improvement.",
            "- Outcome delivered: not completed yet",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_execution_summary" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Execution Summary" in action.detail for action in result.actions
    )


def test_archive_execplan_requires_post_work_posterity_capture(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            (
                "- Post-work posterity capture: preserve the checker-boundary reminder in planning docs and route any durable subsystem "
                "learning to canonical docs or Memory only when that module is installed and is the right owner."
            ),
            "- Post-work posterity capture: pending",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_execution_summary" for warning in result.warnings)
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and "what should survive this slice and where it belongs" in action.detail
        for action in result.actions
    )


def test_archive_execplan_requires_durable_residue_routing(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    plan = _minimal_execplan(status="completed").split("\n## Durable Residue\n\n", 1)[0] + "\n"
    _write(plan_path, plan)

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_durable_residue" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "durable_residue.status" in action.detail
        for action in result.actions
    )


def test_archive_execplan_rejects_pending_durable_residue_status(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("- Status: evidence_only", "- Status: pending"))

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_durable_residue" for warning in result.warnings)
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and "durable_residue.status" in action.detail
        and "evidence_only" in action.detail
        and "pending" not in action.detail
        for action in result.actions
    )


def test_archive_execplan_rejects_future_residue_without_non_archive_owner(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- Status: evidence_only", "- Status: memory")
        .replace("- Canonical owner now: archive", "- Canonical owner now: archive"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_durable_residue" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "non-archive canonical owner" in action.detail
        for action in result.actions
    )


def test_archive_execplan_accepts_memory_routed_durable_residue(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace/memory/repo/index.md", "# Memory\n")
    _write(tmp_path / ".agentic-workspace/memory/repo/manifest.toml", "schema_version = 1\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- Status: evidence_only", "- Status: memory")
        .replace("- Canonical owner now: archive", "- Canonical owner now: .agentic-workspace/memory/repo/index.md")
        .replace("- Promotion trigger: none", "- Promotion trigger: when the motivation recurs in another closeout"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert result.warnings == []
    assert not plan_path.exists()
    assert not (tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json").exists()
    assert any(action.kind == "memory candidate" for action in result.actions)


def test_archive_execplan_blocks_memory_residue_when_memory_is_missing(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- Status: evidence_only", "- Status: memory")
        .replace("- Canonical owner now: archive", "- Canonical owner now: .agentic-workspace/memory/repo/index.md")
        .replace("- Promotion trigger: none", "- Promotion trigger: when the motivation recurs in another closeout"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_memory_destination_unavailable" for warning in result.warnings)


def test_archive_execplan_blocks_missing_proof_report(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    plan = _minimal_execplan(status="completed").split("\n## Proof Report\n\n", 1)[0] + "\n"
    _write(plan_path, plan)

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_proof_report" for warning in result.warnings)
    assert any(action.kind == "manual review" and action.path == plan_path and "Proof Report" in action.detail for action in result.actions)


def test_archive_execplan_blocks_incomplete_intent_satisfaction(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    completed = _minimal_execplan(status="completed")
    proof_section = completed.split("\n## Proof Report\n\n", 1)[1].split("\n## Intent Satisfaction\n\n", 1)[0]
    plan = (
        completed.split("\n## Proof Report\n\n", 1)[0]
        + "\n## Proof Report\n\n"
        + proof_section
        + "\n## Intent Satisfaction\n\n"
        + "- Original intent: Keep scope clear.\n"
        + "- Was original intent fully satisfied?: no\n"
        + "- Evidence of intent satisfaction: the lane still has open follow-on work.\n"
        + "- Unsolved intent passed to: .agentic-workspace/planning/execplans/local-only-residue-via-git-exclude.md\n"
        + "\n## Closure Check\n\n"
        + "- Slice status: bounded slice complete\n"
        + "- Larger-intent status: closed\n"
        + "- Closure decision: archive-and-close\n"
        + "- Why this decision is honest: placeholder contradiction for test coverage.\n"
        + "- Evidence carried forward: intent and proof sections remain present.\n"
        + "- Reopen trigger: none\n"
        + "\n"
    )
    _write(plan_path, plan)

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(
        warning["warning_class"] in {"archive_missing_intent_satisfaction", "archive_intent_not_fully_satisfied"}
        for warning in result.warnings
    )
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and ("Intent Satisfaction" in action.detail or "archive-and-close" in action.detail or "larger-intent closure" in action.detail)
        and (
            "intent_satisfaction.was original intent fully satisfied?" in action.detail
            or "closure_check.larger-intent status" in action.detail
        )
        for action in result.actions
    )


def test_archive_execplan_refusal_names_supported_closure_values(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- Slice status: bounded slice complete", "- Slice status: all bounded slices complete")
        .replace("- Closure decision: archive-and-close", "- Closure decision: close-lane"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_closure_check" for warning in result.warnings)
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and "closure_check.slice status" in action.detail
        and "complete" in action.detail
        and "completed" in action.detail
        and "bounded slice complete" in action.detail
        for action in result.actions
    )


def test_archive_execplan_refusal_names_supported_closure_decisions(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace("- Closure decision: archive-and-close", "- Closure decision: close-lane"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_closure_check" for warning in result.warnings)
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and "closure_check.closure decision" in action.detail
        and "archive-and-close" in action.detail
        and "archive-but-keep-lane-open" in action.detail
        and "Use `archive-and-close`" in action.detail
        for action in result.actions
    )


def test_archive_execplan_refusal_suggests_closed_for_satisfied_larger_intent(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace("- Larger-intent status: closed", "- Larger-intent status: satisfied"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_intent_not_fully_satisfied" for warning in result.warnings)
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and "closure_check.larger-intent status" in action.detail
        and "Use `closed`" in action.detail
        for action in result.actions
    )


def test_archive_plan_prepare_closeout_dry_run_returns_valid_patch(tmp_path: Path, capsys) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.pop("proof_report")
    record.pop("intent_satisfaction")
    record.pop("closure_check")
    record.pop("closeout_distillation", None)
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    assert (
        planning_cli.main(["archive-plan", "plan-alpha", "--target", str(tmp_path), "--prepare-closeout", "--dry-run", "--format", "json"])
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    text = json.dumps(payload)

    assert payload["warnings"] == []
    assert any(action["kind"] == "would update" and "prepared closeout patch" in action["detail"] for action in payload["actions"])
    assert "archive-and-close" in text
    assert "intent_satisfaction" in text
    assert "task_intent_promotion" in text
    assert "do-not-promote" in text
    assert "generated_closeout" in text
    assert "Generated closeout adapter; structured execplan fields are authoritative." in text
    assert "closeout_distillation" in text
    assert "next command" in text
    assert record_path.exists()
    assert "intent_satisfaction" not in json.loads(record_path.read_text(encoding="utf-8"))


def test_archive_plan_prepare_closeout_preserves_specific_closure_evidence(tmp_path: Path, capsys) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["closure_check"] = {
        "slice status": "bounded slice complete",
        "larger-intent status": "closed",
        "closure decision": "archive-and-close",
        "why this decision is honest": "The issue was closed after the runtime selector and tests passed.",
        "evidence carried forward": "operating_posture selector output",
        "reopen trigger": "Agents need disconnected posture reads again.",
    }
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    assert (
        planning_cli.main(
            [
                "archive-plan",
                "plan-alpha",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--apply-cleanup",
                "--retain-archive",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"
    archived = json.loads(archived_record_path.read_text(encoding="utf-8"))

    assert archived["closure_check"]["slice status"] == "bounded slice complete"
    assert archived["closure_check"]["why this decision is honest"] == "The issue was closed after the runtime selector and tests passed."
    assert archived["closure_check"]["evidence carried forward"] == "operating_posture selector output"
    assert archived["closure_check"]["reopen trigger"] == "Agents need disconnected posture reads again."


def test_archive_plan_prepare_closeout_archives_without_manual_json_repair(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "completed", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.pop("intent_satisfaction")
    record.pop("closure_check")
    record.pop("closeout_distillation", None)
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    assert (
        planning_cli.main(
            [
                "archive-plan",
                "plan-alpha",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--apply-cleanup",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"

    assert payload["warnings"] == []
    assert any(action["kind"] == "updated" and "prepared normalized closeout fields" in action["detail"] for action in payload["actions"])
    assert any(action["kind"] == "closed" for action in payload["actions"])
    assert any(action["kind"] == "closeout distillation" for action in payload["actions"])
    assert not archived_record_path.exists()
    assert not record_path.exists()


def test_archive_plan_prepare_closeout_handles_open_parent_lane(tmp_path: Path, capsys) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["intent_continuity"]["this slice completes the larger intended outcome"] = "no"
    record["intent_continuity"]["continuation surface"] = ".agentic-workspace/planning/state.toml"
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "owner surface": ".agentic-workspace/planning/state.toml",
        "activation trigger": "when fresh product-compression pressure appears",
    }
    record["intent_satisfaction"] = {
        "original intent": "Complete the child slice.",
        "was original intent fully satisfied?": "yes",
        "evidence of intent satisfaction": "Child slice validation passed.",
        "unsolved intent passed to": ".agentic-workspace/planning/state.toml",
    }
    record.pop("closure_check")
    record.pop("closeout_distillation", None)
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    assert (
        planning_cli.main(
            [
                "archive-plan",
                "plan-alpha",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--closure-decision",
                "archive-but-keep-lane-open",
                "--retain-archive",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"
    archived = json.loads(archived_record_path.read_text(encoding="utf-8"))

    assert payload["warnings"] == []
    assert archived["intent_satisfaction"]["original intent"] == "Complete the child slice."
    assert archived["intent_satisfaction"]["was original intent fully satisfied?"] == "yes"
    assert archived["intent_satisfaction"]["evidence of intent satisfaction"] == "Child slice validation passed."
    assert archived["intent_satisfaction"]["unsolved intent passed to"] == ".agentic-workspace/planning/state.toml"
    assert archived["closure_check"]["larger-intent status"] == "open"
    assert archived["closure_check"]["closure decision"] == "archive-but-keep-lane-open"
    assert "Archive decision: archive-but-keep-lane-open" in archived["generated_closeout"]["text"]
    assert "Follow-up: .agentic-workspace/planning/state.toml" in archived["generated_closeout"]["text"]
    assert archived["closeout_distillation"]["buckets"]["continuation"][0]["owner"] == ".agentic-workspace/planning/state.toml"


def test_archive_plan_parent_lane_closeout_creates_schema_valid_record_without_active_plan(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "parent-lane", type = "lane", title = "Parent Lane", maturity = "ready", status = "next", priority = "1", issues = ["EXT-1", "EXT-2"], outcome = "Child work has landed.", reason = "Parent evidence is complete.", promotion_signal = "none", suggested_first_slice = "none", durable_residue = "evidence_only" },
]

[active]
execplans = []

[todo]
active_items = []
queued_items = []
""",
    )

    assert (
        planning_cli.main(
            [
                "archive-plan",
                "--parent-lane-closeout",
                "parent-lane",
                "--target",
                str(tmp_path),
                "--intent-evidence",
                "EXT-1 and EXT-2 are complete.",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "parent-lane.plan.json"
    archived = json.loads(archived_record_path.read_text(encoding="utf-8"))
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))

    assert payload["warnings"] == []
    assert any(action["kind"] == "created" and action["path"].endswith("parent-lane.plan.json") for action in payload["actions"])
    assert archived["parent_lane"]["id"] == "parent-lane"
    assert archived["parent_acceptance_map"]["child_refs"] == ["EXT-1", "EXT-2"]
    assert archived["intent_satisfaction"]["was original intent fully satisfied?"] == "yes"
    assert archived["closure_check"]["closure decision"] == "archive-and-close"
    assert archived["proof_report"]["validation proof"] == "schema-backed writer validation"
    assert "EXT-1" in json.dumps(archived["references"])
    assert state["work_items"] == []
    assert planning_summary(target=tmp_path)["work_maturity"]["counts"]["closed_items"] == 0


def test_archive_plan_parent_lane_closeout_dry_run_does_not_mutate_state(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "parent-lane", type = "lane", title = "Parent Lane", maturity = "ready", status = "next", issues = ["EXT-1"], outcome = "Child work has landed.", reason = "Parent evidence is complete.", promotion_signal = "none", suggested_first_slice = "none" },
]
""",
    )

    assert (
        planning_cli.main(
            ["archive-plan", "--parent-lane-closeout", "parent-lane", "--target", str(tmp_path), "--dry-run", "--format", "json"]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert any(action["kind"] == "would create" for action in payload["actions"])
    assert any(action["kind"] == "would update" for action in payload["actions"])
    assert not (tmp_path / ".agentic-workspace/planning/execplans/archive/parent-lane.plan.json").exists()
    assert "parent-lane" in (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")


def test_archive_execplan_allows_partial_intent_when_continuation_is_explicit(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- This slice completes the larger intended outcome: yes", "- This slice completes the larger intended outcome: no")
        .replace("- Continuation surface: none", "- Continuation surface: .agentic-workspace/planning/state.toml")
        .replace("- Required follow-on for the larger intended outcome: no", "- Required follow-on for the larger intended outcome: yes")
        .replace("- Owner surface: none", "- Owner surface: .agentic-workspace/planning/state.toml")
        .replace("- Activation trigger: none", "- Activation trigger: when the next bounded slice for the lane is activated")
        .replace("- Was original intent fully satisfied?: yes", "- Was original intent fully satisfied?: no")
        .replace(
            "- Evidence of intent satisfaction: the bounded slice landed and the lane-level evidence was recorded.",
            "- Evidence of intent satisfaction: the bounded slice landed, but the larger lane still has required continuation.",
        )
        .replace("- Unsolved intent passed to: none", "- Unsolved intent passed to: .agentic-workspace/planning/state.toml")
        .replace("- Larger-intent status: closed", "- Larger-intent status: partial")
        .replace("- Closure decision: archive-and-close", "- Closure decision: archive-but-keep-lane-open")
        .replace(
            "- Why this decision is honest: the bounded slice and larger intent are both complete.",
            "- Why this decision is honest: the bounded slice is complete, but the larger lane remains open in checked-in planning.",
        )
        .replace(
            "- Evidence carried forward: proof and intent satisfaction both show the lane is closed.",
            "- Evidence carried forward: proof shows the slice is complete and the continuation owner is explicit.",
        )
        .replace(
            "- Reopen trigger: none",
            "- Reopen trigger: reopen when the next bounded lane slice is activated from .agentic-workspace/planning/state.toml",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"

    assert not archived_record_path.exists()
    assert not plan_path.exists()
    assert not result.warnings


def test_archive_execplan_blocks_missing_delegated_judgment(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "## Delegated Judgment\n\n"
            "- Requested outcome: Keep scope clear.\n"
            "- Hard constraints: Keep scope bounded to the promoted TODO item and its touched paths.\n"
            "- Agent may decide locally: Bounded decomposition, validation tightening, and plan-local residue routing.\n"
            "- Escalate when: The requested outcome, owned surface, time horizon, or meaningful validation story would change.\n\n",
            "",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_delegated_judgment" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Delegated Judgment" in action.detail for action in result.actions
    )


def test_archive_execplan_blocks_rename_like_work_without_reference_sweep(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _rename_like_execplan())

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_closure_check" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "stale-reference sweep" in action.detail
        for action in result.actions
    )


def test_archive_execplan_allows_rename_like_work_with_reference_sweep(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _rename_like_execplan(with_reference_sweep=True))

    result = archive_execplan("plan-alpha", target=tmp_path)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"

    assert not archived_record_path.exists()
    assert not plan_path.exists()
    assert any(action.kind == "closed" and action.path == plan_path for action in result.actions)


def test_archive_execplan_apply_cleanup_removes_active_execplan_without_closed_state_history(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = []

[active]
execplans = [
  { id = "plan-alpha", title = "Plan Alpha", maturity = "active", status = "active", path = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", source = "#501", owner_role = "implementation", review_role = "validation", handoff_ready = true },
]
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(plan_path, item_id="plan-alpha", status="completed")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["durable_residue"] = {
        "status": "planning",
        "learned constraint": "Closed work should not remain in live planning state.",
        "motivation worth preserving": "Later agents can inspect the archived execplan when historical evidence is needed.",
        "canonical owner now": ".agentic-workspace/planning/execplans/archive/plan-alpha.plan.json",
        "promotion trigger": "when selecting the next planning-state maturity slice",
        "retention after promotion": "shrink",
    }
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    result = archive_execplan("plan-alpha", target=tmp_path, apply_cleanup=True)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    summary = planning_summary(target=tmp_path)

    assert not archived_record_path.exists()
    assert "execplans = []" in state_text
    assert 'maturity = "closed"' not in state_text
    assert "durable_residue" not in state_text
    assert "residue_owner" not in state_text
    assert 'title = "Plan Alpha"' not in state_text
    assert 'closure = "archive-and-close"' not in state_text
    assert summary["work_maturity"]["closed_items"] == []
    assert summary["work_maturity"]["counts"]["residue_routing_needed"] == 0
    assert not any(
        warning["warning_class"] == "historical_work_in_live_planning_state" for warning in summary["planning_surface_health"]["warnings"]
    )
    assert summary["todo"]["queued_count"] == 0
    assert any("remove active execplan 'plan-alpha' from live planning state after archive" in action.detail for action in result.actions)


def test_archive_execplan_retain_archive_uses_unique_path_when_archive_is_stale(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[active]
execplans = [
  { id = "plan-alpha", title = "Plan Alpha", maturity = "active", status = "active", path = ".agentic-workspace/planning/execplans/plan-alpha.plan.json" },
]
""",
    )
    live_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    stale_archive_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"
    _write_execplan_record(live_path, item_id="plan-alpha", status="completed")
    _write_execplan_record(stale_archive_path, item_id="plan-alpha", status="completed")
    stale_archive = json.loads(stale_archive_path.read_text(encoding="utf-8"))
    stale_archive["proof_report"]["validation proof"] = "stale retained archive"
    installer_mod._write_execplan_record(record_path=stale_archive_path, record=stale_archive)

    live = json.loads(live_path.read_text(encoding="utf-8"))
    live["proof_report"]["validation proof"] = "fresh retained archive"
    installer_mod._write_execplan_record(record_path=live_path, record=live)

    result = archive_execplan("plan-alpha", target=tmp_path, apply_cleanup=True, retain_archive=True)
    unique_archive_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha-2.plan.json"
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    summary = planning_summary(target=tmp_path)

    assert result.warnings == []
    assert not live_path.exists()
    assert stale_archive_path.exists()
    assert unique_archive_path.exists()
    assert json.loads(stale_archive_path.read_text(encoding="utf-8"))["proof_report"]["validation proof"] == "stale retained archive"
    assert json.loads(unique_archive_path.read_text(encoding="utf-8"))["proof_report"]["validation proof"] == "fresh retained archive"
    assert "plan-alpha" not in state_text
    assert summary["execplans"].get("active_count", 0) == 0
    assert any(action.kind == "retention" and "unique retained archive path" in action.detail for action in result.actions)
    assert any(action.kind == "archived" and action.path == unique_archive_path for action in result.actions)


def test_archive_execplan_apply_cleanup_updates_completed_todo_and_roadmap(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: completed
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Plan alpha is the current active package pass.

## Next Candidate Queue

- Candidate beta: promote when a report signals follow-on work.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("plan-alpha", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "plan-alpha" not in todo_text
    assert "- No active work right now." in todo_text
    assert "- No active handoff right now." in roadmap_text
    assert any(action.kind == "updated" and action.path == tmp_path / ".agentic-workspace/planning/state.toml" for action in result.actions)
    assert any(action.kind == "updated" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)


def test_archive_execplan_apply_cleanup_removes_active_todo_pointer_to_same_plan(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Now

- ID: bounded-delegated-judgment-contract
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/bounded-delegated-judgment-contract-2026-04-09.md
  Why now: finish the bounded contract update.

## Action

- Complete `bounded-delegated-judgment-contract`, then archive it and return the active queue to empty.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "bounded-delegated-judgment-contract-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "bounded-delegated-judgment-contract"))

    result = archive_execplan("bounded-delegated-judgment-contract-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert "Surface: .agentic-workspace/planning/execplans/bounded-delegated-judgment-contract-2026-04-09.md" not in todo_text
    assert "- No active work right now." in todo_text
    assert (
        "Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation."
        in todo_text
    )
    assert any(
        action.kind == "updated"
        and action.path == tmp_path / ".agentic-workspace/planning/state.toml"
        and "remove TODO item 'bounded-delegated-judgment-contract'" in action.detail
        for action in result.actions
    )
    assert not (
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "bounded-delegated-judgment-contract-2026-04-09.plan.json"
    ).exists()


def test_archive_execplan_apply_cleanup_handles_active_todo_without_blank_before_action_heading(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Now

- ID: intent-continuity-across-slices
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/intent-continuity-across-slices-2026-04-09.md
  Why now: keep larger intent alive across bounded slices.
## Action

- Complete `intent-continuity-across-slices`, then archive it and return the active queue to empty.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "intent-continuity-across-slices-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "intent-continuity-across-slices"))

    archive_execplan("intent-continuity-across-slices-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert "## Action" in todo_text
    assert "- No active work right now." in todo_text
    assert "Complete `intent-continuity-across-slices`" not in todo_text


def test_archive_execplan_apply_cleanup_updates_compact_now_todo_shape(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Purpose

Repo-owned active queue for repository work.
Use `agentic-workspace summary --format json` first; keep this file as the repo-owned view of the active queue.

## Now
- front-door-defaults-tranche: Active - compress front-door docs and land the defaults contract.

## Action
- Execute `.agentic-workspace/planning/execplans/front-door-defaults-tranche-2026-04-09.md` and archive it once validation is complete.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "front-door-defaults-tranche-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "front-door-defaults-tranche"))

    result = archive_execplan("front-door-defaults-tranche-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert "front-door-defaults-tranche: Active" not in todo_text
    assert ".agentic-workspace/planning/execplans/front-door-defaults-tranche-2026-04-09.md" not in todo_text
    assert "- No active work right now." in todo_text
    assert (
        "Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation."
        in todo_text
    )
    assert any(action.kind == "updated" and action.path == tmp_path / ".agentic-workspace/planning/state.toml" for action in result.actions)


def test_archive_execplan_apply_cleanup_removes_compact_state_active_item_pointer(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "#257", surface = ".agentic-workspace/planning/execplans/intent-validation-and-dangling-debt-2026-04-22.md", why_now = "Ship vendor-agnostic intent validation." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "intent-validation-and-dangling-debt-2026-04-22.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "intent-validation-and-dangling-debt"))

    result = archive_execplan("intent-validation-and-dangling-debt-2026-04-22", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    archived_path = (
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "intent-validation-and-dangling-debt-2026-04-22.plan.json"
    )

    assert not archived_path.exists()
    assert not plan_path.exists()
    assert "intent-validation-and-dangling-debt-2026-04-22.md" not in state_text
    assert "active_items = []" in state_text
    assert any(action.kind == "updated" and "remove TODO item '#257'" in action.detail for action in result.actions)


def test_archive_execplan_apply_cleanup_removes_active_execplan_pointer(tmp_path: Path) -> None:
    plan_ref = ".agentic-workspace/planning/execplans/intent-validation-and-dangling-debt-2026-04-22.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = []

[active]
execplans = [
  {{ id = "#257", path = "{plan_ref}", maturity = "active", status = "active" }},
]
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / plan_ref
    _write_execplan_record(plan_path, item_id="intent-validation-and-dangling-debt", status="completed")

    result = archive_execplan("intent-validation-and-dangling-debt-2026-04-22", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    archived_path = (
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "intent-validation-and-dangling-debt-2026-04-22.plan.json"
    )

    assert not archived_path.exists()
    assert not plan_path.exists()
    assert "intent-validation-and-dangling-debt-2026-04-22" not in state_text
    assert "execplans = []" in state_text
    assert any(
        action.kind == "updated" and "remove active execplan '#257' from live planning state after archive" in action.detail
        for action in result.actions
    )


def test_archive_execplan_apply_cleanup_removes_active_execplan_and_work_item_pointer(tmp_path: Path) -> None:
    plan_ref = ".agentic-workspace/planning/execplans/current-lane.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  {{ id = "current-lane", type = "lane", maturity = "active", status = "active", path = "{plan_ref}" }},
]

[active]
execplans = [
  {{ id = "current-lane", path = "{plan_ref}", maturity = "active", status = "active" }},
]
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / plan_ref
    _write_execplan_record(plan_path, item_id="current-lane", status="completed")

    result = archive_execplan("current-lane", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    archived_path = tmp_path / ".agentic-workspace/planning/execplans/archive/current-lane.plan.json"

    assert not archived_path.exists()
    assert not plan_path.exists()
    assert "current-lane" not in state_text
    assert "work_items = []" in state_text
    assert "execplans = []" in state_text
    assert any(
        action.kind == "updated" and "remove active execplan 'current-lane' from live planning state after archive" in action.detail
        for action in result.actions
    )


def test_archive_execplan_apply_cleanup_removes_active_execplan_field_pointer(tmp_path: Path) -> None:
    plan_ref = ".agentic-workspace/planning/execplans/module-manifest-components.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = []

[todo]
active_items = [
  {{ id = "module-manifest-components-todo", execplan = "{plan_ref}", status = "active" }},
]
queued_items = []

[active]
execplans = [
  {{ id = "module-manifest-components", execplan = "{plan_ref}", maturity = "active", status = "active" }},
  {{ id = "unrelated-active-plan", execplan = ".agentic-workspace/planning/execplans/unrelated-active-plan.plan.json", maturity = "active", status = "active" }},
]
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / plan_ref
    unrelated_path = tmp_path / ".agentic-workspace/planning/execplans/unrelated-active-plan.plan.json"
    _write_execplan_record(plan_path, item_id="module-manifest-components", status="completed")
    _write_execplan_record(unrelated_path, item_id="unrelated-active-plan", status="active")

    result = archive_execplan("module-manifest-components", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    archived_path = tmp_path / ".agentic-workspace/planning/execplans/archive/module-manifest-components.plan.json"

    assert not archived_path.exists()
    assert not plan_path.exists()
    assert "module-manifest-components" not in state_text
    assert "active_items = []" in state_text
    assert "unrelated-active-plan" in state_text
    assert any(
        action.kind == "updated"
        and "remove active execplan 'module-manifest-components' from live planning state after archive" in action.detail
        for action in result.actions
    )


def test_archive_execplan_apply_cleanup_removes_work_item_and_string_execplan_pointer(tmp_path: Path) -> None:
    plan_ref = ".agentic-workspace/planning/execplans/repair-drift-recovery-lane.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  {{ id = "repair-drift-recovery-lane", maturity = "active", status = "active", execplan = "{plan_ref}" }},
]

[active]
execplans = [
  "{plan_ref}",
]

[todo]
active_items = [
  {{ id = "repair-drift-recovery-lane", surface = "{plan_ref}", status = "active" }},
]
queued_items = []
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / plan_ref
    _write_execplan_record(plan_path, item_id="repair-drift-recovery-lane", status="completed")

    result = archive_execplan("repair-drift-recovery-lane", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    archived_path = tmp_path / ".agentic-workspace/planning/execplans/archive/repair-drift-recovery-lane.plan.json"

    assert not archived_path.exists()
    assert not plan_path.exists()
    assert "repair-drift-recovery-lane" not in state_text
    assert "work_items = []" in state_text
    assert "execplans = []" in state_text
    assert any(action.kind == "updated" and "remove TODO item 'repair-drift-recovery-lane'" in action.detail for action in result.actions)


def test_archive_execplan_apply_cleanup_merges_compact_state_todo_and_roadmap_cleanup(tmp_path: Path) -> None:
    plan_ref = ".agentic-workspace/planning/execplans/planning-backed-dogfooding-guardrail.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
[todo]
active_items = [
  {{ id = "planning-backed-dogfooding-guardrail", status = "active", plan = "{plan_ref}" }},
]
queued_items = []

[roadmap]
lanes = [
  {{ id = "planning-backed-dogfooding-guardrail", title = "Planning backed dogfooding guardrail", priority = "first", issues = ["#322"] }},
  {{ id = "machine-first-planning-state", title = "Machine-first planning state and closeout hygiene", priority = "second", issues = ["#323", "#325"] }},
]
candidates = [
  {{ priority = "first", summary = "Planning backed dogfooding guardrail" }},
  {{ priority = "second", summary = "Machine-first planning state and closeout hygiene" }},
]
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / plan_ref
    _write_execplan_record(plan_path, item_id="planning-backed-dogfooding-guardrail", status="completed")

    result = archive_execplan("planning-backed-dogfooding-guardrail", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    archived_path = tmp_path / ".agentic-workspace/planning/execplans/archive/planning-backed-dogfooding-guardrail.plan.json"

    assert not archived_path.exists()
    assert not plan_path.exists()
    assert "active_items = []" in state_text
    assert "planning-backed-dogfooding-guardrail" not in state_text
    assert "Machine-first planning state and closeout hygiene" in state_text
    assert "machine-first-planning-state" in state_text
    assert any(action.kind == "updated" and "remove TODO item" in action.detail for action in result.actions)
    assert any(action.kind == "updated" and "roadmap lanes" in action.detail for action in result.actions)


def test_archive_execplan_cleanup_requires_all_stem_tokens_before_removing_state_lane(tmp_path: Path) -> None:
    plan_ref = ".agentic-workspace/planning/execplans/lower-trust-closeout-reconciliation-view.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
[todo]
active_items = [
  {{ id = "lower-trust-closeout-reconciliation-view", status = "active", plan = "{plan_ref}" }},
]
queued_items = []

[roadmap]
lanes = [
  {{ id = "machine-first-planning-state", title = "Machine-first planning state and closeout hygiene", priority = "first", issues = ["#323", "#325"] }},
  {{ id = "graceful-partial-compliance", title = "Graceful partial compliance and bypass trust", priority = "tenth", issues = ["#292"] }},
]
candidates = [
  {{ priority = "first", summary = "Machine-first planning state and closeout hygiene" }},
  {{ priority = "tenth", summary = "Graceful partial compliance and bypass trust" }},
]
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / plan_ref
    _write_execplan_record(plan_path, item_id="lower-trust-closeout-reconciliation-view", status="completed")

    archive_execplan("lower-trust-closeout-reconciliation-view", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert "active_items = []" in state_text
    assert "machine-first-planning-state" in state_text
    assert "Graceful partial compliance and bypass trust" in state_text


def test_archive_execplan_apply_cleanup_removes_matching_candidate_queue_entry(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: workspace-result-contract
  Status: completed
  Surface: .agentic-workspace/planning/execplans/workspace-result-contract-2026-04-05.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Workspace result contract docs are complete.

## Next Candidate Queue

- Workspace result contract: define a shared adapter or result protocol for
    orchestrated module actions and warnings when more module families land.
- Shared tooling extraction: evaluate a common checker core when repeated maintenance friction appears.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "workspace-result-contract-2026-04-05.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("workspace-result-contract-2026-04-05", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Workspace result contract:" not in roadmap_text
    assert "Shared tooling extraction:" in roadmap_text
    assert any(
        action.kind == "updated" and action.path == tmp_path / "ROADMAP.md" and "Next Candidate Queue" in action.detail
        for action in result.actions
    )


def test_archive_execplan_apply_cleanup_removes_matching_candidate_lane_entry(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: memory-trust-lane
  Status: completed
  Surface: .agentic-workspace/planning/execplans/memory-trust-lane-2026-04-17.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Memory trust, usefulness, and cleanup ergonomics
  ID: memory-trust-usefulness-cleanup
  Priority: second
  Issues: #96, #97, #98, #99, #100
  Outcome: make Memory cheaper to trust, inspect, and clean up.
  Why later: wait until the current planning tranche lands.
  Promotion signal: promote when the current planning tranche completes.
  Suggested first slice: start with evidence-backed note trust states.
- Lane: Separate lane
  ID: separate-lane
  Priority: third
  Issues: #999
  Outcome: keep another candidate lane.
  Why later: later.
  Promotion signal: promote when later.
  Suggested first slice: later slice.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "memory-trust-lane-2026-04-17.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "memory-trust-lane"))

    result = archive_execplan("memory-trust-lane-2026-04-17", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Memory trust, usefulness, and cleanup ergonomics" not in roadmap_text
    assert "Separate lane" in roadmap_text
    assert any(
        action.kind == "updated" and action.path == tmp_path / "ROADMAP.md" and "Candidate Lanes" in action.detail
        for action in result.actions
    )


def test_archive_execplan_cleanup_does_not_remove_unrelated_candidate_lane_from_generic_plan_stem(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: native-candidate-lanes
  Status: completed
  Surface: .agentic-workspace/planning/execplans/native-candidate-lanes-first-slice-2026-04-17.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Memory trust, usefulness, and cleanup ergonomics
  ID: memory-trust-usefulness-cleanup
  Priority: first
  Issues: #96, #97, #98, #99, #100
  Outcome: make Memory cheaper to trust, inspect, and clean up.
  Why now: Memory is the main remaining trust bottleneck.
  Promotion signal: promote when the next bounded slice is ready or when the candidate-lane slice lands.
  Suggested first slice: start with evidence-backed note trust states.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "native-candidate-lanes-first-slice-2026-04-17.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "native-candidate-lanes"))

    archive_execplan("native-candidate-lanes-first-slice-2026-04-17", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Memory trust, usefulness, and cleanup ergonomics" in roadmap_text


def test_archive_execplan_preserves_explicit_roadmap_continuation_candidate(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Intent continuity follow-through: promote when another larger user outcome
    needs multiple bounded slices so Planning can preserve unfinished parent
    intent across archival without re-explaining the purpose in chat.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "intent-continuity-across-slices-2026-04-09.md"
    plan_text = (
        _minimal_execplan(status="completed")
        .replace("plan-alpha", "intent-continuity-across-slices")
        .replace(
            "- Continuation surface: none",
            "- Continuation surface: `ROADMAP.md` candidate `Intent continuity follow-through`",
        )
        .replace(
            "- This slice completes the larger intended outcome: yes",
            "- This slice completes the larger intended outcome: no",
        )
    )
    _write(plan_path, plan_text)

    archive_execplan("intent-continuity-across-slices-2026-04-09", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Intent continuity follow-through:" in roadmap_text


def test_archive_execplan_without_cleanup_only_suggests_roadmap_followup(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Plan alpha is the current active package pass.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "suggested fix" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)
    assert any(warning["warning_class"] == "roadmap_archive_followup" for warning in result.warnings)


def test_archive_execplan_ignores_generic_roadmap_language(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- The initial package pass is complete.

## Promotion Rules

- Promote an epic only when it is ready for active execution.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "promotion-linkage-tuning-2026-04-05.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("promotion-linkage-tuning-2026-04-05", target=tmp_path)

    assert not any(action.kind == "suggested fix" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)
    assert not any(warning["warning_class"] == "roadmap_archive_followup" for warning in result.warnings)


def test_planning_summary_exposes_closure_evidence(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: expose closure evidence.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan(status="completed"))

    summary = planning_summary(target=tmp_path)

    completed_execplans = summary["execplans"]["completed_execplans"]
    assert summary["planning_record"]["status"] == "unavailable"
    assert len(completed_execplans) == 1
    assert completed_execplans[0]["proof_report"]["proof achieved now"] == "validation and closure checks passed for the bounded slice."
    assert completed_execplans[0]["intent_satisfaction"]["was original intent fully satisfied?"] == "yes"
    assert completed_execplans[0]["closure_check"]["closure decision"] == "archive-and-close"
    assert summary["planning_surface_health"]["status"] == "not-clean"
    assert summary["planning_surface_health"]["warnings"][0]["warning_class"] == "archive_accumulation_drift"
    assert summary["planning_surface_health"]["warnings"][0]["path"].endswith(".agentic-workspace/planning/execplans/plan-alpha.md")
    assert "archive-plan" in summary["planning_surface_health"]["recommended_next_action"]
    assert "intent_interpretation" in summary["schema"]["view_fields"]["planning_record"]
    assert "execution_run" in summary["schema"]["view_fields"]["planning_record"]
    assert "finished_run_review" in summary["schema"]["view_fields"]["planning_record"]
    assert "proof_report" in summary["schema"]["view_fields"]["planning_record"]
    assert "intent_satisfaction" in summary["schema"]["view_fields"]["planning_record"]
    assert "closure_check" in summary["schema"]["view_fields"]["planning_record"]


def test_planning_report_prints_closure_evidence(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: expose closure evidence.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan(status="completed"))

    exit_code = planning_cli.main(["report", "--target", str(tmp_path), "--verbose"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Completed execplans awaiting archive: 1" in out
    assert "Proof report: validation and closure checks passed for the bounded slice." in out
    assert "Intent satisfaction: yes" in out
    assert "Closure decision: archive-and-close" in out
