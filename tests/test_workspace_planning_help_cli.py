from __future__ import annotations

import json

import pytest
from command_generation.generated_package_loader import load_generated_command_module_for_entrypoint

cli = load_generated_command_module_for_entrypoint("agentic-workspace", "cli.py")


def test_invalid_command_shows_preflight_fallback_hint(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["prefliht"])

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert "Did you mean: preflight?" in stderr
    assert 'agentic-workspace start --task "<task>" --format json' in stderr
    assert "agentic-workspace preflight --format json" in stderr


def test_planning_help_command_returns_lifecycle_guidance(capsys) -> None:
    assert cli.main(["planning", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/planning-help/v1"
    assert any("new-plan" in command for command in payload["lifecycle_commands"])
    assert any("lane-create" in command for command in payload["lifecycle_commands"])
    assert any("lane-promote" in command for command in payload["lifecycle_commands"])
    assert any("lane-close" in command for command in payload["lifecycle_commands"])
    assert all("agentic-planning" not in command for command in payload["lifecycle_commands"])
    assert any(command.startswith("agentic-workspace planning new-plan") for command in payload["lifecycle_commands"])
    assert payload["planning_hierarchy"]["direct"]["artifact"] == "none"
    assert payload["planning_hierarchy"]["lane"]["artifact"] == ".agentic-workspace/planning/lanes/<id>.lane.json"
    assert "proof aggregation" in payload["planning_hierarchy"]["lane"]["owns"]
    assert "Do not solve lane-shaped work" in payload["planning_hierarchy"]["rule"]
    assert "schema-valid scaffold" in payload["post_new_plan_tightening"]["rule"]
    assert "execution_bounds" in payload["post_new_plan_tightening"]["tighten_before_implementation"]
    assert "--verbose" in payload["post_new_plan_tightening"]["after_write"]
    assert "one lane at a time" in payload["sequential_lane_execution"]["rule"]
    assert "unrelated lanes" in payload["sequential_lane_execution"]["do_not"]
    assert "new-plan" in payload["durable_state_bridge"]["preferred_command"]
    assert "--prep-only" in payload["durable_state_bridge"]["prep_only_route"]["preferred_command"]
    assert "PLAN.md" in payload["durable_state_bridge"]["must_not_create"]
    assert "do not create product source" in payload["durable_state_bridge"]["planning_only_rule"]
    prep_route = payload["durable_state_bridge"]["prep_only_route"]
    assert "Create or continue canonical checked-in Planning state" in prep_route["required_action"]
    assert "then stop" in prep_route["required_action"]
    assert "new-plan --prep-only exits successfully" in prep_route["minimal_success_criteria"]
    assert "Do not manually tighten" in prep_route["tightening_policy"]
    assert any("summary reports a blocking Planning problem" in item for item in prep_route["allowed_after_new_plan"])
    assert any("planning/records" in item for item in prep_route["do_not_do"])
    assert any("HANDOFF" in item and "package" in item for item in prep_route["do_not_do"])
    assert any("ad hoc shell snippets" in item for item in prep_route["do_not_do"])
    assert "reference_validity_rule" in payload["durable_state_bridge"]
    assert "proposed/future" in payload["durable_state_bridge"]["reference_validity_rule"]
    assert any("Do not invent" in rule for rule in payload["rules"])
    assert any("blocking Planning problem" in rule for rule in payload["rules"])
    assert any("one lane at a time" in rule for rule in payload["rules"])
    assert any("WORKFLOW.md as task state" in rule for rule in payload["rules"])
    assert any("architecture assumptions" in rule for rule in payload["rules"])
    assert any("verify it, and stop" in rule for rule in payload["rules"])
    assert payload["runtime_native_bridge"]["status"] == "allowed-as-local-aid"
    assert "not repo-shared execution authority" in payload["runtime_native_bridge"]["rule"]
    assert "do not invent reset flags" in payload["unsafe_state_recovery"]["manual_fallback"]


def test_planning_help_text_is_actionable(capsys) -> None:
    assert cli.main(["planning"]) == 0
    output = capsys.readouterr().out

    assert "Planning lifecycle" in output
    assert "Planning hierarchy" in output
    assert "Durable repo-visible state bridge" in output
    assert "Prep-only" in output
    assert "Reference validity" in output
    assert "agentic-workspace planning new-plan" in output
    assert "agentic-workspace planning lane-create" in output
    assert "planning/lanes/<id>.lane.json" in output
    assert "agentic-planning new-plan" not in output
    assert "After new-plan" in output
    assert "Ordered lanes" in output
    assert "planning-execplan/v1" in output
    assert "Runtime-native planning bridge" in output
    assert "Unsafe-state recovery" in output


def test_memory_help_command_returns_workspace_front_door_guidance(capsys) -> None:
    assert cli.main(["memory", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/memory-help/v1"
    assert any(command.startswith("agentic-workspace memory route") for command in payload["commands"])
    assert any(command.startswith("agentic-workspace memory capture-note") for command in payload["commands"])
    assert all("agentic-memory" not in command for command in payload["commands"])


def test_planning_front_door_runs_package_operation(tmp_path, capsys) -> None:
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "front-door-plan",
                "--title",
                "Front door plan",
                "--target",
                str(tmp_path),
                "--activate",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["message"] == "Create execplan scaffold 'front-door-plan'"
    assert payload["dry_run"] is True
    assert payload["lifecycle_plan"]["next_safe_command"].startswith("agentic-workspace planning new-plan")


def test_planning_front_door_runs_lane_create_operation(tmp_path, capsys) -> None:
    assert (
        cli.main(
            [
                "planning",
                "lane-create",
                "--id",
                "front-door-lane",
                "--title",
                "Front door lane",
                "--target",
                str(tmp_path),
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["message"] == "Create lane record 'front-door-lane'"
    assert payload["dry_run"] is True
    assert payload["lifecycle_plan"]["next_safe_command"] == (
        "Review actions and rerun the same command without --dry-run only if the plan matches intent."
    )


def test_planning_front_door_rewrites_closeout_summary_action_to_top_level(tmp_path, capsys) -> None:
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "closeout-command",
                "--title",
                "Closeout command",
                "--target",
                str(tmp_path),
                "--activate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "closeout-command.plan.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["active_milestone"]["status"] = "completed"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "planning",
                "closeout",
                "closeout-command",
                "--target",
                str(tmp_path),
                "--proof-from",
                "front-door closeout proof passed",
                "--what-happened",
                "closed the front-door closeout command wording",
                "--scope-touched",
                "workspace planning front door",
                "--changed-surfaces",
                "planning closeout action output",
                "--review-summary",
                "scope respected",
                "--outcome-summary",
                "summary action points at the top-level workspace summary router",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    next_actions = [action["detail"] for action in payload["actions"] if action["kind"] == "next safe action"]

    assert "agentic-workspace summary --target . --format json" in next_actions
    assert all("agentic-workspace planning summary" not in detail for detail in next_actions)
    assert all("agentic-planning summary" not in detail for detail in next_actions)


def test_memory_front_door_runs_package_operation(tmp_path, capsys) -> None:
    assert cli.main(["memory", "route", "--target", str(tmp_path), "--files", "src/example.py", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["target_root"] == str(tmp_path)
