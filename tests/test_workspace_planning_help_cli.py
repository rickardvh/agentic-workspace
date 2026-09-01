from __future__ import annotations

import importlib
import json

import pytest
from command_generation.generated_package_loader import (
    load_generated_command_module_for_entrypoint,
    load_generated_command_package_for_entrypoint,
)

generated_workspace = load_generated_command_package_for_entrypoint("agentic-workspace")
cli = load_generated_command_module_for_entrypoint("agentic-workspace", "cli.py")
planning_front_door = importlib.import_module(f"{generated_workspace.__name__}.commands.planning_front_door")


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


def test_planning_reconcile_help_names_transition_specific_expected_execplan_requirements(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["planning", "reconcile", "--help"])

    assert excinfo.value.code == 0
    output = " ".join(capsys.readouterr().out.split())
    assert "required for relink/supersede" in output
    assert "optional for restore" in output
    assert "not used by cancel/human" in output


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


def test_planning_front_door_forwards_issue_shape_semantics(tmp_path, capsys) -> None:
    assert (
        cli.main(
            [
                "planning",
                "issue-shape",
                "--issue",
                "42",
                "--external-ref",
                "github:example/repo#42",
                "--lane",
                "currentness",
                "--priority",
                "p1",
                "--depends-on",
                "github:example/repo#40,github:example/repo#41",
                "--rationale",
                "owner-bound currentness",
                "--maturity",
                "shaped",
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

    assert payload["operation_receipt"]["semantic_delta"] == {
        "depends_on": ["github:example/repo#40", "github:example/repo#41"],
        "external_ref": "github:example/repo#42",
        "lane_id": "currentness",
        "maturity": "shaped",
        "priority": "p1",
        "rationale": "owner-bound currentness",
    }


def test_planning_front_door_invoke_enforces_live_route_action_admission(tmp_path) -> None:
    from agentic_workspace import config as config_lib
    from agentic_workspace.workspace_runtime_planning import _planning_safety_gate_payload

    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n',
        encoding="utf-8",
    )
    config = config_lib.load_workspace_config(target_root=tmp_path)
    gate = _planning_safety_gate_payload(
        target_root=tmp_path,
        config=config,
        changed_paths=["README.md"],
        task_text="fix readme",
        execution_posture={},
    )
    invocation = gate["route_decision"]["next_safe_action"]["operation_invocation"]

    admitted = planning_front_door.invoke(
        {"target": str(tmp_path), "task": "fix readme", "changed_paths": ["README.md"], "operation_invocation": invocation}
    )

    assert admitted["status"] == "admitted"
    assert admitted["operation_action"] == "route-decision-next-action"
    assert admitted["admission"]["status"] == "admitted"
    assert admitted["mutation_outcome"] in {"no-op", "applied"}

    stale_invocation = json.loads(json.dumps(invocation))
    stale_invocation["input_revision"] = "sha256:stale-route-action"
    rejected = planning_front_door.invoke(
        {"target": str(tmp_path), "task": "fix readme", "changed_paths": ["README.md"], "operation_invocation": stale_invocation}
    )

    assert rejected["status"] == "rejected"
    assert rejected["mutation_outcome"] == "rejected"
    assert "input_revision" in rejected["admission"]["revision_failures"]


def _current_reconciliation_front_door_decision() -> dict:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    return _planning_route_decision_payload(
        {
            "task_relation": "continues-selected-owner",
            "owner_posture": "external-conflict",
            "active_execplan": ".agentic-workspace/planning/execplans/active.plan.json",
            "route_inputs": {
                "task_binding": {"mode": "mutation", "identity": "task-a", "allowed_paths": ["README.md"]},
                "owner": {
                    "ref": ".agentic-workspace/planning/execplans/active.plan.json",
                    "revision": "owner-a",
                    "lifecycle": "active",
                    "projection_status": "clean",
                },
                "mutation_baseline": {"baseline_id": "baseline-a", "scope": {"allowed_paths": ["README.md"]}},
            },
        },
        planning_revision={"revision_id": "planning-a"},
        reconciliation_proposal={
            "status": "current",
            "proposal_id": "a" * 20,
            "revision": "proposal-rev-a",
            "apply_command": "agentic-workspace planning reconcile --apply --proposal " + "a" * 20,
        },
    )


def test_planning_front_door_applies_current_reconciliation_through_cas(tmp_path, monkeypatch) -> None:
    import repo_planning_bootstrap.installer as planning_installer

    import agentic_workspace.workspace_runtime_planning as runtime_planning

    decision = _current_reconciliation_front_door_decision()
    invocation = decision["next_safe_action"]["operation_invocation"]
    calls = []

    monkeypatch.setattr(runtime_planning, "_planning_safety_gate_payload", lambda **_kwargs: {"route_decision": decision})

    def fake_reconcile(**kwargs):
        calls.append(kwargs)
        return {
            "kind": "agentic-planning/reconciliation-transaction/v1",
            "status": "applied",
            "receipt": {
                "kind": "agentic-planning/reconciliation-receipt/v1",
                "proposal_id": kwargs["proposal"],
                "planning_revision_before": kwargs["expected_planning_revision"],
            },
        }

    monkeypatch.setattr(planning_installer, "planning_reconcile", fake_reconcile)

    result = planning_front_door.invoke(
        {"target": str(tmp_path), "task": "apply proposal", "changed_paths": ["README.md"], "operation_invocation": invocation}
    )

    assert result["status"] == "admitted"
    assert result["route_action"] == "apply-planning-reconciliation-proposal"
    assert result["mutation_outcome"] == "applied"
    assert result["claim_outcome"] == "available-after-proof"
    assert result["mutation_receipt"]["proposal_id"] == "a" * 20
    assert result["reconciliation_apply"]["status"] == "applied"
    assert calls == [{"target": tmp_path.resolve(), "apply": True, "proposal": "a" * 20, "expected_planning_revision": "planning-a"}]


def test_planning_front_door_does_not_report_blocked_reconciliation_as_applied(tmp_path, monkeypatch) -> None:
    import repo_planning_bootstrap.installer as planning_installer

    import agentic_workspace.workspace_runtime_planning as runtime_planning

    decision = _current_reconciliation_front_door_decision()
    invocation = decision["next_safe_action"]["operation_invocation"]

    monkeypatch.setattr(runtime_planning, "_planning_safety_gate_payload", lambda **_kwargs: {"route_decision": decision})
    monkeypatch.setattr(
        planning_installer,
        "planning_reconcile",
        lambda **_kwargs: {
            "kind": "agentic-planning/reconciliation-transaction/v1",
            "status": "blocked",
            "reason": "planning-revision-mismatch",
        },
    )

    result = planning_front_door.invoke(
        {"target": str(tmp_path), "task": "apply proposal", "changed_paths": ["README.md"], "operation_invocation": invocation}
    )

    assert result["status"] == "admitted"
    assert result["mutation_outcome"] == "blocked"
    assert result["claim_outcome"] == "blocked"
    assert result["mutation_receipt"] == {}
    assert result["reconciliation_apply"]["status"] == "blocked"
    assert result["reconciliation_apply"]["reason"] == "planning-revision-mismatch"


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
    assert payload["lifecycle_plan"]["next_safe_guidance"] == (
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
    record["lifecycle"] = "closed"
    record["phase"] = "complete"
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
