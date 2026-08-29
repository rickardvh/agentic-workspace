from __future__ import annotations

# ruff: noqa: F403,F405
import copy
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from repo_planning_bootstrap import installer as planning_installer
from repo_verification_bootstrap import runtime_primitives as verification_runtime_primitives
from tests.workspace_cli_support import *

from agentic_workspace import module_contract as module_contract_runtime
from agentic_workspace import session_logging
from agentic_workspace.config import workspace_pointer_block
from agentic_workspace.module_contract import DiscoveredModule, validate_module_contract


def test_active_external_backed_owner_routes_refresh_then_reconciliation(tmp_path: Path) -> None:
    cache = tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json"
    active_summary = {
        "active_execplan": ".agentic-workspace/planning/execplans/external-owner.plan.json",
        "active_owner_refs": ["#42", "issue-42"],
    }
    config = SimpleNamespace(cli_invoke="uv run agentic-workspace")
    planning_revision = {"revision_id": "revision-42"}
    item = {
        "id": "#42",
        "status": "closed",
        "status_class": "completed",
        "observation_id": "github:issue:42:current",
        "external_revision": "current",
        "freshness": {"status": "current", "expires_at": "2099-01-01T00:00:00+00:00"},
    }
    _write(cache, json.dumps({"kind": "planning-external-intent-evidence/v1", "items": [item]}))

    current = workspace_runtime_planning._active_owner_external_reconciliation(
        target_root=tmp_path,
        active_summary=active_summary,
        config=config,
        planning_revision=planning_revision,
    )

    assert current["status"] == "reconciliation-required"
    assert current["reason_code"] == "external-owner-completed"
    assert "planning reconcile --target . --preview" in current["reconcile_command"]
    assert "--expect-planning-revision revision-42" in current["reconcile_command"]

    item["freshness"] = {"status": "current", "expires_at": "2000-01-01T00:00:00+00:00"}
    _write(cache, json.dumps({"kind": "planning-external-intent-evidence/v1", "items": [item]}))
    stale = workspace_runtime_planning._active_owner_external_reconciliation(
        target_root=tmp_path,
        active_summary=active_summary,
        config=config,
        planning_revision=planning_revision,
    )

    assert stale["status"] == "refresh-required"
    assert stale["reason_code"] == "external-observation-stale"
    assert stale["refresh_command"].startswith("uv run agentic-workspace external-intent refresh-github")
    assert "--issue #42" in stale["refresh_command"]
    assert "--apply-planning-candidates" in stale["refresh_command"]

    assert workspace_runtime_planning._active_owner_external_reconciliation(
        target_root=tmp_path,
        active_summary={"active_execplan": active_summary["active_execplan"], "active_owner_refs": []},
        config=config,
        planning_revision=planning_revision,
    ) == {"status": "not-applicable"}


def test_planning_route_decision_makes_external_owner_recovery_copyable() -> None:
    common = {
        "status": "external-observation-stale",
        "task_relation": "continues-selected-owner",
        "required_transition": "reconcile",
        "active_execplan": ".agentic-workspace/planning/execplans/owner.plan.json",
        "external_refresh_command": "aw external-intent refresh-github --target . --state all --storage cache --format json",
        "reconciliation_preview_command": "aw planning reconcile --target . --preview --expect-planning-revision rev-1 --format json",
        "route_inputs": {
            "task_binding": {"mode": "mutation", "identity": "task-1"},
            "owner": {"ref": ".agentic-workspace/planning/execplans/owner.plan.json", "lifecycle": "live"},
            "admitted_external_observation": {
                "status": "refresh-required",
                "matched_observation_ids": ["github:issue:42:old"],
                "external_revisions": ["old"],
            },
        },
    }
    stale = workspace_runtime_planning._planning_route_decision_payload(
        {**common, "owner_posture": "externally-stale"}, planning_revision={"revision_id": "rev-1"}
    )
    assert stale["next_safe_action"]["action"] == "refresh-external-evidence"
    assert stale["next_safe_action"]["command"] == common["external_refresh_command"]
    assert stale["implementation_allowed"] is False
    assert stale["action_identity"]["external_observation_revision"]

    changed = workspace_runtime_planning._planning_route_decision_payload(
        {
            **common,
            "status": "external-owner-completed",
            "owner_posture": "external-conflict",
            "route_inputs": {
                **common["route_inputs"],
                "admitted_external_observation": {
                    "status": "reconciliation-required",
                    "matched_observation_ids": ["github:issue:42:closed"],
                    "external_revisions": ["closed"],
                },
            },
        },
        planning_revision={"revision_id": "rev-1"},
    )
    assert changed["next_safe_action"]["action"] == "compile-planning-reconciliation-proposal"
    assert changed["next_safe_action"]["command"] == common["reconciliation_preview_command"]


def test_planning_route_decision_surfaces_exact_target_authority_transaction() -> None:
    preview_command = "aw planning reconcile --target . --preview --expect-planning-revision rev-2 --format json"
    transaction = {
        "status": "preview-available",
        "transaction_class": "target-authority-integration",
        "proposal_id": "proposal-2",
        "preview_command": preview_command,
        "current_target_authority_revision": "target-rev-2",
        "affected_owner_refs": [".agentic-workspace/planning/execplans/owner-2.plan.json"],
    }

    decision = workspace_runtime_planning._planning_route_decision_payload(
        {
            "status": "target-authority-reconciliation-stale",
            "task_relation": "continues-selected-owner",
            "owner_posture": "reconciliation-stale",
            "required_transition": "reconcile",
            "active_execplan": ".agentic-workspace/planning/execplans/owner-2.plan.json",
            "reconciliation_preview_command": preview_command,
            "reconciliation_transaction": transaction,
            "route_inputs": {
                "task_binding": {"mode": "mutation", "identity": "task-2"},
                "owner": {"ref": ".agentic-workspace/planning/execplans/owner-2.plan.json", "lifecycle": "live"},
            },
        },
        planning_revision={"revision_id": "rev-2"},
        reconciliation_proposal={"status": "stale", "proposal_id": "old-proposal"},
    )

    action = decision["next_safe_action"]
    assert action["action"] == "compile-planning-reconciliation-proposal"
    assert action["command"] == preview_command
    assert "affected owner: .agentic-workspace/planning/execplans/owner-2.plan.json" in action["required_inputs"]
    assert "target authority revision: target-rev-2" in action["required_inputs"]
    assert decision["reconciliation_transaction"] == transaction


def test_compiled_target_authority_reconciliation_surfaces_guarded_refresh_command(tmp_path: Path, monkeypatch) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    proposal_root = tmp_path / ".agentic-workspace/planning/integration-proposals"
    _write(proposal_root / "stale.integration-proposal.json", "{}\n")
    transaction = {
        "transaction_class": "target-authority-integration",
        "status": "blocked",
        "reason": "semantic-integration-conflict",
        "current_target_authority_revision": "target-rev-3",
        "semantic_conflicts": [
            {
                "proposal_id": "stale-proposal",
                "owner_ref": ".agentic-workspace/planning/execplans/stale.plan.json",
                "reason_code": "stale-integration-subject-revision",
                "proposal_revision": "proposal-rev-3",
                "expected_subject_revision": "old-subject-rev-3",
                "current_subject_revision": "subject-rev-3",
                "current_target_authority_revision": "target-rev-3",
            }
        ],
    }
    monkeypatch.setattr(planning_installer, "planning_reconcile", lambda **_kwargs: transaction)

    compiled = workspace_runtime_planning._compiled_target_authority_reconciliation(
        target_root=tmp_path,
        cli_invoke="uv run aw-dev",
    )

    assert compiled["semantic_conflicts"] == transaction["semantic_conflicts"]
    assert compiled["current_target_authority_revision"] == "target-rev-3"
    assert compiled["refresh_command"] == (
        "uv run aw-dev planning integration-propose --proposal-id stale-proposal --refresh-existing "
        "--expect-proposal-revision proposal-rev-3 --expect-subject-revision subject-rev-3 "
        "--expect-planning-revision target-rev-3 --target . --format json"
    )


def test_successful_completion_cost_discovers_manifest_indexed_custom_output_root(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    _write(tmp_path / "README.md", "fixture\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout.strip()
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout.strip()
    repository_identity = "sha256:" + hashlib.sha256(tmp_path.resolve().as_posix().lower().encode()).hexdigest()[:24]
    run_root = tmp_path / ".agentic-workspace" / "local" / "scratch" / "custom-name" / "suite-summary"
    _write(run_root / ".aw-scratch.toml", 'owner = "agentic-workspace"\nproducer = "model-cli-harness.run-suite"\n')
    _write(
        run_root / "summary.json",
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-result/v1",
                "adapter": "fixture",
                "model": "fixture",
                "result_count": 1,
                "results": [],
                "usage_summary": {"status": "present", "output_tokens": 4},
            }
        ),
    )
    index = tmp_path / ".agentic-workspace" / "local" / "model-cli-harness" / "evidence-index.jsonl"
    _write(
        index,
        json.dumps(
            {
                "kind": "agentic-workspace/model-cli-harness-evidence-index-entry/v1",
                "producer": "model-cli-harness.run-suite",
                "summary_ref": run_root.relative_to(tmp_path).as_posix() + "/summary.json",
                "manifest_ref": run_root.relative_to(tmp_path).as_posix() + "/.aw-scratch.toml",
                "subject": {
                    "repository_identity": repository_identity,
                    "repository_head": head,
                    "repository_tree": tree,
                    "dirty": False,
                },
            }
        )
        + "\n",
    )

    payload = workspace_runtime_core._successful_completion_cost_payload(target_root=tmp_path, cli_invoke="agentic-workspace")

    assert payload["status"] == "present"
    assert payload["evidence"]["producer_index"]["admitted_count"] == 1
    assert payload["recent_runs"][0]["adapter"] == "fixture"


def test_successful_completion_cost_rejections_have_bounded_examples(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    index = tmp_path / ".agentic-workspace/local/model-cli-harness/evidence-index.jsonl"
    _write(
        index,
        "".join(
            json.dumps(
                {
                    "kind": "agentic-workspace/model-cli-harness-evidence-index-entry/v1",
                    "producer": "foreign",
                    "summary_ref": f"private/run-{number}/summary.json",
                }
            )
            + "\n"
            for number in range(28)
        ),
    )

    _paths, admission = workspace_runtime_core._successful_completion_cost_indexed_summaries(target_root=tmp_path)

    assert admission["rejected_count"] == 28
    assert len(admission["rejected_examples"]) == 4
    assert admission["drill_down"]["example_limit"] == 4


def test_successful_completion_cost_reports_malformed_foreign_dirty_and_stale_reasons(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    _write(tmp_path / "README.md", "fixture\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout.strip()
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout.strip()
    identity = "sha256:" + hashlib.sha256(tmp_path.resolve().as_posix().lower().encode()).hexdigest()[:24]
    run = tmp_path / ".agentic-workspace/local/scratch/rejections"
    _write(run / ".aw-scratch.toml", 'owner = "agentic-workspace"\nproducer = "model-cli-harness.run-suite"\n')
    _write(run / "summary.json", "{}\n")
    base = {
        "kind": "agentic-workspace/model-cli-harness-evidence-index-entry/v1",
        "producer": "model-cli-harness.run-suite",
        "summary_ref": (run / "summary.json").relative_to(tmp_path).as_posix(),
        "manifest_ref": (run / ".aw-scratch.toml").relative_to(tmp_path).as_posix(),
        "subject": {"repository_identity": identity, "repository_head": head, "repository_tree": tree, "dirty": False},
    }
    records = [
        {"invalid": True},
        {**base, "producer": "foreign"},
        {**base, "subject": {**base["subject"], "dirty": True}},
        {**base, "subject": {**base["subject"], "repository_head": "stale"}},
    ]
    index = tmp_path / ".agentic-workspace/local/model-cli-harness/evidence-index.jsonl"
    _write(index, "".join(json.dumps(record) + "\n" for record in records))

    _paths, admission = workspace_runtime_core._successful_completion_cost_indexed_summaries(target_root=tmp_path)

    assert admission["rejection_reasons"] == {
        "foreign-producer": 1,
        "invalid-entry": 1,
        "recorded-subject-dirty": 1,
        "repository-subject-mismatch": 1,
    }


def test_successful_completion_cost_consumes_typed_run_attempt_and_subject_transition(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        verification_runtime_primitives,
        "validation_evidence_admissions",
        lambda _target: [
            {
                "admitted": True,
                "bundle": {
                    "proof_route_id": "test.workspace",
                    "executed_at": "2026-08-16T10:00:04+00:00",
                    "provenance": {
                        "result_path": "scratch/validation-results/run-1/test.workspace.json",
                        "run_id": "run-1",
                        "run_identity": {"provenance": "transported-child"},
                        "attempt_identity": {"attempt_id": "run-1:test.workspace:attempt-2", "attempt_index": 2},
                        "proof_operation": {"operation_id": "proof-op-1", "execution_class": "focused-local"},
                        "repository_head": "head-a",
                        "repository_tree": "tree-a",
                        "plan_graph": "plan-a",
                    },
                    "freshness": {
                        "subject_paths": ["src/example.py"],
                        "pre_subject_revision": "pre",
                        "post_subject_revision": "post",
                    },
                    "completion_cost": {"outcome": "passed", "duration_seconds": 4.5, "rerun": True},
                },
            }
        ],
    )

    observations = workspace_runtime_core._successful_completion_cost_validation_observations(target_root=tmp_path)

    assert observations["status"] == "present"
    run = observations["runs"][0]
    assert (run["run_id"], run["run_provenance"], run["attempt_index"]) == ("run-1", "transported-child", 2)
    assert (run["proof_operation_id"], run["execution_class"]) == ("proof-op-1", "focused-local")
    assert run["subject"] == {
        "repository_head": "head-a",
        "repository_tree": "tree-a",
        "plan_graph": "plan-a",
        "subject_paths": ["src/example.py"],
        "pre_subject_revision": "pre",
        "post_subject_revision": "post",
    }


def test_payload_scratch_exclusion_summary_is_bounded_and_preserves_unowned_scope(tmp_path: Path) -> None:
    index = tmp_path / ".agentic-workspace/local/model-cli-harness/evidence-index.jsonl"
    records = []
    for number in range(7):
        run = tmp_path / f".agentic-workspace/local/scratch/custom-{number}"
        _write(run / ".aw-scratch.toml", 'owner = "agentic-workspace"\nproducer = "model-cli-harness.run-suite"\n')
        records.append(
            json.dumps(
                {
                    "kind": "agentic-workspace/model-cli-harness-evidence-index-entry/v1",
                    "producer": "model-cli-harness.run-suite",
                    "manifest_ref": (run / ".aw-scratch.toml").relative_to(tmp_path).as_posix(),
                }
            )
        )
    _write(index, "\n".join(records) + "\n")

    summary = workspace_runtime_core._local_scratch_exclusion_summary(target_root=tmp_path)

    assert summary["excluded_root_count"] == 7
    assert len(summary["excluded_root_examples"]) == 4
    assert "unowned" in summary["preserved_scope"].lower()


def test_payload_scratch_nested_repo_scan_prunes_owned_and_preserves_unowned(tmp_path: Path) -> None:
    owned = tmp_path / ".agentic-workspace/local/scratch/owned"
    unowned = tmp_path / ".agentic-workspace/local/scratch/unowned"
    (owned / "repo/.git").mkdir(parents=True)
    (unowned / "repo/.git").mkdir(parents=True)
    _write(owned / ".aw-scratch.toml", 'owner = "agentic-workspace"\nproducer = "model-cli-harness.run-suite"\n')

    paths = workspace_runtime_core._local_scratch_nested_repo_paths(target_root=tmp_path)

    assert ".agentic-workspace/local/scratch/owned/repo" not in paths
    assert ".agentic-workspace/local/scratch/unowned/repo" in paths


def test_payload_scratch_exclusion_rejects_escape_and_linked_producer_roots(tmp_path: Path) -> None:
    scratch = tmp_path / ".agentic-workspace/local/scratch"
    contained = scratch / "contained"
    outside = tmp_path / "outside"
    _write(contained / ".aw-scratch.toml", 'owner = "agentic-workspace"\nproducer = "model-cli-harness.run-suite"\n')
    _write(outside / ".aw-scratch.toml", 'owner = "agentic-workspace"\nproducer = "model-cli-harness.run-suite"\n')
    linked = scratch / "linked"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        linked = None
    records = [
        {
            "producer": "model-cli-harness.run-suite",
            "manifest_ref": (contained / ".aw-scratch.toml").relative_to(tmp_path).as_posix(),
        },
        {
            "producer": "model-cli-harness.run-suite",
            "manifest_ref": (outside / ".aw-scratch.toml").relative_to(tmp_path).as_posix(),
        },
    ]
    if linked is not None:
        records.append(
            {
                "producer": "model-cli-harness.run-suite",
                "manifest_ref": (linked / ".aw-scratch.toml").relative_to(tmp_path).as_posix(),
            }
        )
    index = tmp_path / ".agentic-workspace/local/model-cli-harness/evidence-index.jsonl"
    _write(index, "".join(json.dumps(record) + "\n" for record in records))

    summary = workspace_runtime_core._local_scratch_exclusion_summary(target_root=tmp_path)

    assert summary["excluded_root_count"] == 1
    assert summary["excluded_root_examples"] == [".agentic-workspace/local/scratch/contained"]
    assert summary["rejected_index_entry_count"] == len(records) - 1


def test_payload_scratch_scale_collapses_owned_roots_into_one_bounded_packet(tmp_path: Path) -> None:
    records = []
    for number in range(28):
        owned = tmp_path / f".agentic-workspace/local/scratch/owned-{number}"
        (owned / "nested/.git").mkdir(parents=True)
        _write(owned / ".aw-scratch.toml", 'owner = "agentic-workspace"\nproducer = "model-cli-harness.run-suite"\n')
        records.append(
            {
                "producer": "model-cli-harness.run-suite",
                "manifest_ref": (owned / ".aw-scratch.toml").relative_to(tmp_path).as_posix(),
            }
        )
    unowned = tmp_path / ".agentic-workspace/local/scratch/unowned/nested"
    (unowned / ".git").mkdir(parents=True)
    index = tmp_path / ".agentic-workspace/local/model-cli-harness/evidence-index.jsonl"
    _write(index, "".join(json.dumps(record) + "\n" for record in records))

    plan = workspace_runtime_core._payload_doctor_closure_plan(
        command_name="doctor",
        target_root=tmp_path,
        selected_modules=[],
        installed_state_compatibility={"payload": {}, "action_state": {}},
        repair_actions=[],
        manual_review_actions=[],
        reports=[],
        cli_invoke="agentic-workspace",
    )
    scratch_surface = next(item for item in plan["surface_classes"] if item["id"] == "local_scratch_blockers")

    assert scratch_surface["nested_repo_paths"] == [".agentic-workspace/local/scratch/unowned/nested"]
    assert scratch_surface["exclusion_summary"]["excluded_root_count"] == 28
    assert len(scratch_surface["exclusion_summary"]["excluded_root_examples"]) == 4
    assert len([item for item in plan["surface_classes"] if item["id"] == "local_scratch_blockers"]) == 1


def _write_completed_child_reconciliation_fixture(target_root: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    ref = ".agentic-workspace/planning/execplans/merged-child.plan.json"
    _write(
        target_root / ".agentic-workspace/config.toml",
        "schema_version = 1\n\n[workspace]\nenabled = true\n",
    )
    _write(target_root / "README.md", "# Fixture\n")
    _write(
        target_root / ".agentic-workspace/planning/state.toml",
        f"""
[todo]
active_items = [
  {{ id = "merged-child", status = "active", surface = "{ref}" }},
]
queued_items = []

[roadmap]
lanes = ["parent-lane"]
candidates = []
""",
    )
    record = planning_installer._build_legacy_execplan_record_from_todo_item(
        title="Merged child",
        item_id="merged-child",
        status="active",
        why_now="The bounded child was merged externally.",
        next_action="Reconcile the stale completed owner.",
        done_when="The child is archived without closing the parent lane.",
    )
    record["intent_continuity"]["this slice completes the larger intended outcome"] = "no"
    record["intent_continuity"]["continuation surface"] = "external-review"
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "owner surface": "external-review",
        "activation trigger": "none",
    }
    record["intent_satisfaction"]["unsolved intent passed to"] = "external-review"
    planning_installer._write_execplan_record(record_path=target_root / ref, record=record)


def test_completed_child_reconciliation_is_cross_consumer_idempotent_and_fails_closed_without_proof(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    served = tmp_path / "served"
    _write_completed_child_reconciliation_fixture(served)
    state_path = served / ".agentic-workspace/planning/state.toml"
    state_before = state_path.read_bytes()
    closeout = {
        "target": served,
        "claim_level": "slice",
        "intent_status": "satisfied",
        "residue": "none",
        "proof_from": "GitHub PR merged after the recorded bounded proof passed.",
        "what_happened": "The bounded child merged after review.",
        "scope_touched": "bounded child scope",
        "changed_surfaces": "merged child PR",
        "review_summary": "The child is complete; the parent lane remains independently open.",
        "outcome_summary": "Reconciled the completed child owner.",
    }
    first = planning_installer.closeout_execplan("merged-child", **closeout)
    replay = planning_installer.closeout_execplan("merged-child", **closeout)
    assert not any(action.kind == "manual review" for action in first.actions)
    assert any(action.kind == "already closed" for action in replay.actions)

    planning = planning_installer.planning_summary(target=served)
    assert planning["planning_record"]["status"] == "unavailable"
    assert planning["work_maturity"]["status"] == "idle"
    assert state_path.read_bytes() == state_before

    assert cli.main(["start", "--target", str(served), "--task", "Review unrelated repository docs", "--format", "json"]) == 0
    started = json.loads(capsys.readouterr().out)
    assert started["decision_packet"]["action"]["id"] == "choose-smallest-workflow-shape"
    assert started["decision_packet"]["effects"]["implementation_allowed"] is True
    assert "module_slot" not in started["decision_packet"]["action"]
    assert "merged-child" not in json.dumps(started.get("context", {}).get("route_decision", {}))

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(served),
                "--changed",
                "README.md",
                "--task",
                "Fix an unrelated documentation typo",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    implemented = json.loads(capsys.readouterr().out)
    gate = implemented["values"]["planning_safety_gate"]
    assert gate["gate_result"] == "direct-work-allowed"

    assert cli.main(["start", "--target", str(served), "--task", "Review unrelated repository docs", "--format", "json"]) == 0
    next_start = json.loads(capsys.readouterr().out)
    assert next_start["decision_packet"]["action"]["id"] == "choose-smallest-workflow-shape"

    insufficient = tmp_path / "insufficient"
    _write_completed_child_reconciliation_fixture(insufficient)
    blocked_closeout = planning_installer.closeout_execplan(
        "merged-child",
        **{**closeout, "target": insufficient, "proof_from": "pending"},
    )
    manual = [action for action in blocked_closeout.actions if action.kind == "manual review"]
    assert len(manual) == 1
    assert "--proof-from" in manual[0].detail
    assert (insufficient / ".agentic-workspace/planning/execplans/merged-child.plan.json").exists()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(insufficient),
                "--task",
                "Fix unrelated docs typo",
                "--select",
                "planning_safety_gate,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    blocked_start = json.loads(capsys.readouterr().out)
    selected = blocked_start["values"]
    assert selected["next_safe_action"]["next_safe_action"] == "inspect-current-task"
    assert selected["next_safe_action"]["implementation_allowed"] is True
    route = selected["planning_safety_gate"]["route_decision"]
    assert route["required_transition"] == "none"
    assert "claim-active-plan-progress" in route["blocked_claims"]
    assert route["selected_owner"].endswith("merged-child.plan.json")
    assert route["owner_admission"]["repair_route"]["status"] == "available"


@pytest.mark.parametrize(("proof_state", "expected_status"), [("satisfied", "applied"), ("pending", "applied-with-semantic-blockers")])
def test_refreshed_external_owner_reconciliation_applies_only_with_semantic_authority(
    tmp_path: Path, proof_state: str, expected_status: str
) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write_completed_child_reconciliation_fixture(tmp_path)
    owner_path = tmp_path / ".agentic-workspace/planning/execplans/merged-child.plan.json"
    owner = planning_installer._load_execplan_record(owner_path)
    assert owner is not None
    owner.setdefault("relationships", {})["proof_posture"] = {"state": proof_state, "refs": ["proof:merged-child"]}
    owner.setdefault("references", []).append(
        {"kind": "issue", "target": "#42", "label": "GitHub #42", "role": "external-owner", "locator": ""}
    )
    planning_installer._write_execplan_record(record_path=owner_path, record=owner)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_before = state_path.read_bytes()
    _write(
        tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refreshed_at": "2026-08-25T12:00:00+00:00",
                "refresh_metadata": {"adapter": "fixture", "refreshed_at": "2026-08-25T12:00:00+00:00"},
                "items": [
                    {
                        "system": "github",
                        "id": "#42",
                        "status": "closed",
                        "kind": "issue",
                        "observation_id": "github:issue:42:merged",
                        "external_revision": "merged",
                        "observed_at": "2026-08-25T12:00:00+00:00",
                        "freshness": {
                            "status": "current",
                            "observed_at": "2026-08-25T12:00:00+00:00",
                            "expires_at": "2099-01-01T00:00:00+00:00",
                            "max_age_seconds": 86400,
                        },
                        "owner": {"id": "#42", "kind": "issue", "locator": "github:acme/project:issue:42"},
                        "status_class": "completed",
                        "blockers": [],
                        "evidence_refs": ["#42"],
                        "provenance": {
                            "provider_class": "github",
                            "resolver_id": "fixture",
                            "source_ref": "github:acme/project:issue:42",
                            "refresh_id": "merged",
                        },
                        "refresh_route": "fixture-refresh",
                        "availability": "available",
                        "contradictions": [],
                    }
                ],
            }
        ),
    )

    result = workspace_runtime_core._reconcile_external_active_owners_after_refresh(target_root=tmp_path, requested=True, dry_run=False)
    assert result["status"] == expected_status
    assert state_path.read_bytes() == state_before
    if proof_state == "satisfied":
        closed = planning_installer._load_execplan_record(owner_path)
        assert closed is not None and closed["lifecycle"] == "closed"
        assert result["receipt"]["closed_owner_ids"] == ["merged-child.plan"]
    else:
        retained = planning_installer._load_execplan_record(owner_path)
        assert retained is not None and planning_installer._execplan_lifecycle(retained) == "live"
        assert retained["next_action"] == (
            "Admit subject proof and decide semantic intent satisfaction before closing this externally completed owner."
        )
        assert result["blocked_owners"][0]["reason"] == "proof-admission-required"
        assert "did not satisfy" in result["claim_boundary"]


@pytest.mark.parametrize(
    ("argv", "blocked_command"),
    [
        (["start"], "start"),
        (["summary"], "summary"),
        (["report"], "report"),
        (["implement", "--task", "disabled workspace should not build implement context"], "implement"),
        (["proof"], "proof"),
        (["planning", "closeout"], "planning closeout"),
    ],
)
def test_workspace_disabled_state_blocks_ordinary_commands(tmp_path: Path, capsys, argv: list[str], blocked_command: str) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[workspace]\nenabled = false\n",
    )

    assert cli.main([*argv, "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/disabled-state/v1"
    assert payload["status"] == "disabled"
    assert payload["command"] == blocked_command
    assert payload["effective_config"] == {
        "field": "workspace.enabled",
        "value": False,
        "source": "local-override",
        "surface": ".agentic-workspace/config.local.toml",
    }
    assert payload["action_effect"]["normal_workflow_allowed"] is False
    assert payload["action_effect"]["diagnostics_allowed"] is True
    assert "config" in payload["allowed_diagnostics"]
    assert "workspace.enabled = true" in payload["re_enable"]["local_override"]


def test_json_payload_budget_failure_reports_largest_contributors() -> None:
    payload = {
        "small": "ok",
        "context": {
            "large": "x" * 80,
            "nested": {"medium": "y" * 40},
        },
        "items": [{"detail": "z" * 30}],
    }

    with pytest.raises(AssertionError) as excinfo:
        _assert_json_payload_under(payload, 50, label="example tiny payload")

    message = str(excinfo.value)
    assert "example tiny payload JSON payload is" in message
    assert "Largest JSON contributors:" in message
    assert "context" in message
    assert "context.large" in message


def test_archive_retention_policy_reports_versioned_host_budgets_and_migration_route(tmp_path: Path) -> None:
    archive_root = tmp_path / ".agentic-workspace/planning/execplans/archive"
    receipt_root = tmp_path / ".agentic-workspace/planning/closeout-evidence"
    archive_root.mkdir(parents=True)
    receipt_root.mkdir(parents=True)
    for index in range(101):
        _write(archive_root / f"plan-{index:03d}.plan.json", json.dumps({"title": str(index), "closeout_distillation": {}}))
    _write(receipt_root / "prior.closeout.json", json.dumps({"kind": "planning-closeout-evidence/v1"}))

    measure = workspace_runtime_core._archived_plan_distillation_measure(target=tmp_path)
    policy = workspace_runtime_core._archive_retention_policy(
        archived_distillation=measure,
        artifact_footprint={
            "classes": [
                {
                    "id": "archived_execplans",
                    "pressure": "attention",
                    "sample": [".agentic-workspace/planning/execplans/archive/plan-000.plan.json"],
                }
            ]
        },
    )

    assert policy["kind"] == "workspace-archive-retention-policy/v2"
    assert policy["policy_version"] == "planning-archive-retention/v2"
    assert policy["budget_status"] == "exceeded"
    assert policy["budgets"]["full_archive_file_count"] == {"actual": 101, "maximum": 100, "status": "exceeded"}
    assert policy["trend"]["compact_receipts"] == 1
    assert "--compact-retained --dry-run" in policy["dry_run_command"]
    assert policy["ordinary_route_exclusion"]["startup"] == "excluded"


def test_ordinary_start_does_not_read_or_emit_large_planning_archive_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    archive_root = tmp_path / ".agentic-workspace/planning/execplans/archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    for index in range(250):
        (archive_root / f"historical-{index:03d}.plan.json").write_text(
            json.dumps({"kind": "planning-execplan/v1", "id": f"historical-{index:03d}"}) + "\n", encoding="utf-8"
        )

    archive_reads: list[str] = []
    original_read_text = Path.read_text

    def observed_read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if "/planning/execplans/archive/" in path.as_posix():
            archive_reads.append(path.as_posix())
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", observed_read_text)
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect current routing", "--format", "json"]) == 0
    rendered = capsys.readouterr().out
    assert archive_reads == []
    assert "historical-000" not in rendered
    assert len(rendered.encode("utf-8")) < 64_000


def test_selector_validation_error_does_not_project_valid_values_or_build_full_inventory(monkeypatch) -> None:
    class ExplodingCopy:
        def __deepcopy__(self, memo: dict[int, object]) -> object:
            raise AssertionError("valid selector value must not be deep-copied when another selector is invalid")

    def fail_inventory(payload: dict[str, Any]) -> list[str]:
        raise AssertionError("invalid selector path must not build the full selector inventory")

    monkeypatch.setattr(cli, "_available_selectors_for_payload", fail_inventory)

    payload = {"valid": ExplodingCopy(), "context": {"known": "value"}}
    selected = cli._select_payload_fields(payload, select="valid,missing.field", source_command="start")

    assert selected["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert selected["unknown_selectors"] == ["missing.field"]
    assert "values" not in selected
    assert selected["selector_inventory"]["available_count"] == 3
    assert selected["selector_inventory"]["sample"] == ["valid", "context", "context.known"]
    assert (
        selected["selector_inventory"]["inventory_command"]
        == "agentic-workspace start --target . --select selector_inventory --format json"
    )
    assert "--verbose" not in selected["selector_inventory"]["inventory_command"]


def test_start_unknown_selector_fails_before_payload_construction(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_start_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("start payload must not be built for an unknown selector")

    monkeypatch.setattr(cli, "_selector_first_start_payload", fail_start_payload)
    monkeypatch.setattr(cli, "_start_payload", fail_start_payload)

    assert cli.main(["start", "--target", str(tmp_path), "--select", "not_a_selector", "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["unknown_selectors"] == ["not_a_selector"]
    assert (payload["exit_status"], payload["exit_class"], payload["mutation_occurred"]) == (
        2,
        "usage-or-validation-error",
        False,
    )
    assert (
        payload["selector_inventory"]["inventory_command"] == "agentic-workspace start --target . --select selector_inventory --format json"
    )


def test_start_nested_unknown_selector_fails_before_payload_construction(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_start_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("start payload must not be built for an unknown nested selector")

    monkeypatch.setattr(cli, "_selector_first_start_payload", fail_start_payload)
    monkeypatch.setattr(cli, "_start_payload", fail_start_payload)

    assert cli.main(["start", "--target", str(tmp_path), "--select", "context.not_a_real_field", "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["unknown_selectors"] == ["context.not_a_real_field"]
    assert payload["validation_rule"] == "Selector requests are exact: nested selectors must be declared before payload construction."


def test_start_selector_request_limits_fail_before_payload_construction(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_start_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("start payload must not be built for an oversized selector request")

    monkeypatch.setattr(cli, "_start_payload", fail_start_payload)
    selectors = ",".join(f"missing_{index}" for index in range(40))

    assert cli.main(["start", "--target", str(tmp_path), "--select", selectors, "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["status"] == "invalid-selector-request"
    assert payload["reason"] == "too-many-selectors"
    assert payload["selector_budget"]["max_selectors"] == 32
    assert len(json.dumps(payload)) <= 6000


@pytest.mark.parametrize(
    ("selector", "reason", "limit_contributor"),
    [
        ("x" * 257, "selector-too-long", "selector_bytes"),
        (",".join(f"missing_{index}" for index in range(40)), "too-many-selectors", "requested_selector_count"),
        (",".join(f"missing_{index}_" + ("x" * 40) for index in range(12)), "selector-request-too-large", "selector_request_bytes"),
    ],
)
def test_start_selector_budget_limits_have_bounded_attribution_before_payload_construction(
    tmp_path: Path, monkeypatch, capsys, selector: str, reason: str, limit_contributor: str
) -> None:
    _init_git_repo(tmp_path)

    def fail_start_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("start payload must not be built for invalid selector-budget requests")

    monkeypatch.setattr(cli, "_selector_first_start_payload", fail_start_payload)
    monkeypatch.setattr(cli, "_start_payload", fail_start_payload)

    assert cli.main(["start", "--target", str(tmp_path), "--select", selector, "--format", "json"]) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["status"] == "invalid-selector-request"
    assert payload["reason"] == reason
    assert payload["limit_contributor"] == limit_contributor
    assert payload["selector_budget"]["max_error_envelope_bytes"] == 6000
    assert len(json.dumps(payload)) <= 6000


def test_start_selector_inventory_route_is_executable(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["start", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    inventory = payload["values"]["selector_inventory"]
    assert inventory["kind"] == "agentic-workspace/selector-inventory/v1"
    assert inventory["source_command"] == "start"
    assert inventory["available_count"] > 8
    assert "context_router.rule" in inventory["selectors"]


def test_start_selector_inventory_does_not_build_start_payload(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_start_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("selector inventory must not build the startup payload")

    monkeypatch.setattr(cli, "_selector_first_start_payload", fail_start_payload)
    monkeypatch.setattr(cli, "_start_payload", fail_start_payload)

    assert cli.main(["start", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["values"]["selector_inventory"]["source_command"] == "start"


def test_default_start_defers_action_neutral_advisory_builders_without_changing_action_boundary(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _init_git_repo(tmp_path)
    args = [
        "start",
        "--target",
        str(tmp_path),
        "--task",
        "Fix selector latency for ordinary startup",
        "--format",
        "json",
    ]

    assert cli.main(args) == 0
    baseline = json.loads(capsys.readouterr().out)

    def unexpected_advisory_builder(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("default start must defer action-neutral advisory builders")

    monkeypatch.setattr(workspace_runtime_startup, "_local_work_threads_projection", unexpected_advisory_builder)
    monkeypatch.setattr(workspace_runtime_startup, "_session_improvement_pressure_payload", unexpected_advisory_builder)

    assert cli.main(args) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["decision_packet"] == baseline["decision_packet"]
    assert "work_threads" not in payload
    assert "task_posture_packet" not in payload


def test_implement_unknown_selector_fails_before_payload_construction(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_implement_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("implement payload must not be built for an unknown selector")

    monkeypatch.setattr(cli, "_implement_payload", fail_implement_payload)

    assert cli.main(["implement", "--target", str(tmp_path), "--select", "not_a_selector", "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["unknown_selectors"] == ["not_a_selector"]


def test_implement_nested_unknown_selector_fails_before_payload_construction(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_implement_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("implement payload must not be built for an unknown nested selector")

    monkeypatch.setattr(cli, "_implement_payload", fail_implement_payload)

    assert cli.main(["implement", "--target", str(tmp_path), "--select", "context.not_a_real_field", "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["unknown_selectors"] == ["context.not_a_real_field"]


def test_selector_contract_has_single_shared_host_authority() -> None:
    from agentic_workspace import workspace_selector_validation

    assert workspace_runtime_core._selector_tokens is workspace_selector_validation._selector_tokens
    assert workspace_runtime_core._selector_prevalidation_error is workspace_selector_validation._selector_prevalidation_error
    assert workspace_runtime_core._select_payload_fields is workspace_selector_validation._select_payload_fields
    assert workspace_runtime_primitives._selector_tokens is workspace_selector_validation._selector_tokens
    assert workspace_runtime_primitives._selector_prevalidation_error is workspace_selector_validation._selector_prevalidation_error
    assert workspace_runtime_primitives._select_payload_fields is workspace_selector_validation._select_payload_fields

    repo_root = Path(__file__).resolve().parents[1]
    for relative_path in (
        "src/agentic_workspace/workspace_runtime_core.py",
        "src/agentic_workspace/workspace_runtime_primitives.py",
    ):
        text = (repo_root / relative_path).read_text(encoding="utf-8")
        assert "_SELECTOR_DESCRIPTORS_BY_COMMAND" not in text
        assert "_MAX_SELECTOR_COUNT" not in text
        assert "def _selector_request(" not in text

    primitive_executor_text = (repo_root / "generated/workspace/python/primitives/primitive_executor.py").read_text(encoding="utf-8")

    def generated_constant(name: str) -> int:
        match = re.search(rf"^{name}\s*=\s*([0-9_]+)$", primitive_executor_text, flags=re.MULTILINE)
        assert match is not None
        return int(match.group(1).replace("_", ""))

    assert workspace_selector_validation._MAX_SELECTOR_COUNT == generated_constant("_MAX_PROJECTION_SELECTORS")
    assert workspace_selector_validation._MAX_SELECTOR_BYTES == generated_constant("_MAX_PROJECTION_SELECTOR_BYTES")
    assert workspace_selector_validation._MAX_SELECTOR_REQUEST_BYTES == generated_constant("_MAX_PROJECTION_SELECTOR_REQUEST_BYTES")
    assert workspace_selector_validation._MAX_SELECTOR_ERROR_ENVELOPE_BYTES == generated_constant("_MAX_SELECTOR_ERROR_ENVELOPE_BYTES")
    assert workspace_selector_validation._SELECTOR_SUGGESTION_LIMIT == generated_constant("_SELECTOR_SUGGESTION_LIMIT")


def test_deprecated_selector_reports_bounded_replacement_hint_before_projection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--target", str(tmp_path), "--select", "workspace.feature_tier", "--format", "json"]) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["unknown_selectors"] == ["workspace.feature_tier"]
    assert payload["deprecated_selectors"] == ["workspace.feature_tier"]
    assert payload["replacement_selectors"] == {"workspace.feature_tier": "workspace.enabled_modules"}
    assert len(json.dumps(payload)) <= 6000


def test_explicit_selector_inventory_and_prevalidation_share_declared_nested_selectors(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["start", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"]) == 0
    start_inventory = json.loads(capsys.readouterr().out)["values"]["selector_inventory"]
    assert "context_router.rule" in start_inventory["selectors"]

    assert cli.main(["start", "--target", str(tmp_path), "--select", "context_router.rule", "--format", "json"]) == 0
    start_projection = json.loads(capsys.readouterr().out)
    assert start_projection["kind"] == "agentic-workspace/selected-output/v1"
    assert "context_router.rule" in start_projection["values"]

    assert cli.main(["defaults", "--section", "root_cli_authority", "--select", "selector_inventory", "--format", "json"]) == 0
    defaults_inventory = json.loads(capsys.readouterr().out)["values"]["selector_inventory"]
    assert "answer.command" in defaults_inventory["selectors"]

    assert cli.main(["defaults", "--section", "root_cli_authority", "--select", "answer.command", "--format", "json"]) == 0
    defaults_projection = json.loads(capsys.readouterr().out)
    assert defaults_projection["kind"] == "agentic-workspace/selected-output/v1"
    assert defaults_projection["values"] == {"answer.command": "agentic-workspace defaults --section root_cli_authority --format json"}


def test_config_advertised_target_selectors_round_trip_through_the_emitting_surface(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"]) == 0
    inventory = json.loads(capsys.readouterr().out)["values"]["selector_inventory"]
    assert inventory["invocation"] == {
        "command": "agentic-workspace config --target . --select selector_inventory --format json",
        "surface": "config",
        "selector_option": "--select",
    }
    for selector in ("mixed_agent.target_identity", "mixed_agent.target_evidence"):
        assert selector in inventory["selectors"]
        assert cli.main(["config", "--target", str(tmp_path), "--select", selector, "--format", "json"]) == 0
        projection = json.loads(capsys.readouterr().out)
        assert projection["kind"] == "agentic-workspace/selected-output/v1"
        assert selector in projection["values"]

    generated_cli = Path(__file__).resolve().parents[1] / "generated/workspace/typescript/src/cli.mjs"
    generated = subprocess.run(
        [
            "node",
            str(generated_cli),
            "config",
            "--target",
            str(tmp_path),
            "--select",
            "mixed_agent.target_identity,mixed_agent.target_evidence",
            "--format",
            "json",
        ],
        capture_output=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stderr.decode("utf-8")
    generated_projection = json.loads(generated.stdout.decode("utf-8"))
    assert generated_projection["kind"] == "agentic-workspace/selected-output/v1"
    for selector in ("mixed_agent.target_identity", "mixed_agent.target_evidence"):
        value = generated_projection["values"][selector]
        assert value["status"] == "unavailable-in-generated-typescript-host"
        assert value["continuation"].endswith(f"--select {selector} --format json")


def test_generated_workspace_operations_prevalidate_before_payload_producers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from generated.workspace.python.commands import config_report, defaults_report

    _init_git_repo(tmp_path)

    def fail_payload_producer(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("generated operation must not run payload producer for an invalid selector")

    monkeypatch.setattr(workspace_runtime_primitives, "_config_payload", fail_payload_producer)
    monkeypatch.setattr(workspace_runtime_primitives, "_defaults_payload", fail_payload_producer)

    config_payload = config_report.invoke({"target": str(tmp_path), "select": "workspace.not_a_real_field", "format": "json"})
    assert isinstance(config_payload, dict)
    assert config_payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert config_payload["source_command"] == "config"

    defaults_payload = defaults_report.invoke({"select": "workspace.not_a_real_field", "format": "json"})
    assert isinstance(defaults_payload, dict)
    assert defaults_payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert defaults_payload["source_command"] == "defaults"


def _selector_contract_payload_bytes(payload: dict[str, Any]) -> int:
    rendered = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return len(rendered.encode("utf-8"))


def _generated_typescript_config_selector_payload(tmp_path: Path, selector: str) -> dict[str, Any]:
    cli_path = Path(__file__).resolve().parents[1] / "generated/workspace/typescript/src/cli.mjs"
    script = (
        "process.argv = [process.execPath, "
        f"{json.dumps(str(cli_path))}, 'config', '--target', '.', '--select', {json.dumps(selector)}, '--format', 'json'];"
        f" await import({json.dumps(cli_path.as_uri())});"
    )
    completed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            script,
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    return json.loads(completed.stdout.decode("utf-8"))


def _generated_python_config_selector_payload(tmp_path: Path, selector: str) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_text = str(repo_root)
    if repo_root_text not in sys.path:
        sys.path.insert(0, repo_root_text)
    from generated.workspace.python.commands import config_report

    payload = config_report.invoke({"target": str(tmp_path), "select": selector, "format": "json"})
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize(
    ("case_name", "selector", "expected"),
    [
        (
            "max_selector_count_unknowns",
            ",".join(f"u{index}" for index in range(32)),
            {"status": "invalid-selector", "requested_selector_count": 32, "unknown_selector_count": 32},
        ),
        (
            "selector_count_over_limit",
            ",".join(f"u{index}" for index in range(33)),
            {"status": "invalid-selector-request", "reason": "too-many-selectors", "limit_contributor": "requested_selector_count"},
        ),
        (
            "max_unicode_selector_bytes",
            chr(0xE9) * 128,
            {"status": "invalid-selector", "requested_selector_count": 1, "unknown_selector_count": 1},
        ),
        (
            "unicode_selector_bytes_over_limit",
            (chr(0xE9) * 128) + "a",
            {"status": "invalid-selector-request", "reason": "selector-too-long", "limit_contributor": "selector_bytes"},
        ),
        (
            "max_selector_request_bytes",
            f"{'a' * 256},{'b' * 256}",
            {"status": "invalid-selector", "requested_selector_count": 2, "unknown_selector_count": 2},
        ),
        (
            "selector_request_bytes_over_limit",
            f"{'a' * 255},{'b' * 255},ccc",
            {"status": "invalid-selector-request", "reason": "selector-request-too-large", "limit_contributor": "selector_request_bytes"},
        ),
        (
            "mixed_unknown_suggestions",
            "workspace.not_a_real_field,assurance.not_a_real_field",
            {"status": "invalid-selector", "requested_selector_count": 2, "unknown_selector_count": 2},
        ),
        (
            "deprecated_replacement",
            "workspace.feature_tier",
            {"status": "invalid-selector", "deprecated_selectors": ["workspace.feature_tier"]},
        ),
    ],
)
def test_generated_selector_validation_matches_host_contract_for_canonical_boundary_cases(
    tmp_path: Path, capsys, case_name: str, selector: str, expected: dict[str, Any]
) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--target", str(tmp_path), "--select", selector, "--format", "json"]) == 2
    host_payload = json.loads(capsys.readouterr().out)
    generated_python_payload = _generated_python_config_selector_payload(tmp_path, selector)
    generated_typescript_payload = _generated_typescript_config_selector_payload(tmp_path, selector)

    assert generated_python_payload == host_payload
    assert generated_typescript_payload == host_payload
    for key, value in expected.items():
        assert host_payload[key] == value

    assert host_payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert host_payload["source_command"] == "config"
    assert host_payload["exit_status"] == 2
    assert host_payload["safe_to_retry"] is True
    assert host_payload["mutation_occurred"] is False
    assert host_payload["selector_budget"] == {
        "max_selectors": 32,
        "max_selector_bytes": 256,
        "max_selector_request_bytes": 512,
        "max_error_envelope_bytes": 6000,
        "max_error_items": 8,
    }
    assert _selector_contract_payload_bytes(host_payload) <= 6000
    assert len(json.dumps(host_payload, indent=2).splitlines()) <= 70

    if host_payload["status"] == "invalid-selector":
        assert host_payload["requested_selector_omitted_count"] == max(0, host_payload["requested_selector_count"] - 8)
        assert host_payload["unknown_selector_omitted_count"] == max(0, host_payload["unknown_selector_count"] - 8)
        assert host_payload["selector_inventory"]["sample_limit"] == 8
        assert len(host_payload["selector_inventory"]["sample"]) == 8
    if case_name == "mixed_unknown_suggestions":
        assert host_payload["suggestions"] == {
            "workspace.not_a_real_field": ["workspace"],
            "assurance.not_a_real_field": ["assurance"],
        }
    if case_name == "deprecated_replacement":
        assert host_payload["replacement_selectors"] == {"workspace.feature_tier": "workspace.enabled_modules"}
        assert host_payload["replacement_rule"] == (
            "Deprecated selectors are rejected atomically with their exact current selector and copyable replacement command."
        )
        assert host_payload["replacement_command"] == (
            "agentic-workspace config --target . --select workspace.enabled_modules --format json"
        )


@pytest.mark.parametrize(
    ("argv", "source_command"),
    [
        (["defaults", "--select", "workspace.not_a_real_field", "--format", "json"], "defaults"),
        (["config", "--select", "workspace.not_a_real_field", "--format", "json"], "config"),
        (["summary", "--select", "planning_record.not_a_real_field", "--format", "json"], "summary"),
    ],
)
def test_generated_typescript_workspace_operations_use_host_selector_prevalidation(
    tmp_path: Path, argv: list[str], source_command: str
) -> None:
    _init_git_repo(tmp_path)

    completed = subprocess.run(
        ["node", str(Path(__file__).resolve().parents[1] / "generated/workspace/typescript/src/cli.mjs"), *argv],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["source_command"] == source_command
    assert payload["selector_budget"]["max_selector_bytes"] == 256
    assert payload["selector_budget"]["max_selector_request_bytes"] == 512
    assert payload["selector_budget"]["max_error_envelope_bytes"] == 6000


def test_generated_typescript_summary_selector_inventory_is_successful(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)

    completed = subprocess.run(
        [
            "node",
            str(Path(__file__).resolve().parents[1] / "generated/workspace/typescript/src/cli.mjs"),
            "summary",
            "--select",
            "selector_inventory",
            "--format",
            "json",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["values"]["selector_inventory"]["source_command"] == "summary"


def test_invalid_proof_selector_has_generated_exit_two_and_success_remains_zero(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    selector = "proof_obligations.not_a_real_field"
    assert cli.main(["proof", "--target", str(tmp_path), "--select", selector, "--format", "json"]) == 2
    host_payload = json.loads(capsys.readouterr().out)

    generated_cli = Path(__file__).resolve().parents[1] / "generated/workspace/typescript/src/cli.mjs"
    completed = subprocess.run(
        ["node", str(generated_cli), "proof", "--target", ".", "--select", selector, "--format", "json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    generated_payload = json.loads(completed.stdout)
    assert generated_payload == host_payload
    assert (host_payload["exit_status"], host_payload["mutation_occurred"]) == (2, False)

    assert cli.main(["proof", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"]) == 0
    success_payload = json.loads(capsys.readouterr().out)
    assert success_payload["kind"] == "agentic-workspace/selected-output/v1"


def test_start_optional_selector_root_is_exact_before_payload_construction(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["start", "--target", str(tmp_path), "--select", "issue_reference_intent", "--format", "json"]) == 0
    exact_root_payload = json.loads(capsys.readouterr().out)
    assert exact_root_payload["kind"] == "agentic-workspace/selected-output/v1"
    assert exact_root_payload["missing"] == ["issue_reference_intent"]

    def fail_start_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("start payload must not be built for an undeclared optional selector descendant")

    monkeypatch.setattr(cli, "_selector_first_start_payload", fail_start_payload)
    monkeypatch.setattr(cli, "_start_payload", fail_start_payload)

    assert cli.main(["start", "--target", str(tmp_path), "--select", "issue_reference_intent.not_a_real_field", "--format", "json"]) == 2
    nested_payload = json.loads(capsys.readouterr().out)
    assert nested_payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert nested_payload["unknown_selectors"] == ["issue_reference_intent.not_a_real_field"]


@pytest.mark.parametrize(
    ("argv", "source_command", "unknown_selector", "tripwire_attrs"),
    [
        (["start", "--target", "{target}"], "start", "context.not_a_real_field", ("_selector_first_start_payload", "_start_payload")),
        (["implement", "--target", "{target}"], "implement", "context.not_a_real_field", ("_implement_payload",)),
        (["summary", "--target", "{target}"], "summary", "planning_record.not_a_real_field", ("_load_workspace_config",)),
        (["config", "--target", "{target}"], "config", "workspace.not_a_real_field", ("_config_payload",)),
        (
            ["proof", "--target", "{target}", "--changed", "src/sample.py"],
            "proof",
            "proof_obligations.not_a_real_field",
            ("_proof_payload",),
        ),
        (["doctor", "--target", "{target}"], "doctor", "payload_closure_summary.not_a_real_field", ("_selected_runtime_context",)),
        (["status", "--target", "{target}"], "status", "payload_closure_summary.not_a_real_field", ("_selected_runtime_context",)),
        (["defaults"], "defaults", "workspace.not_a_real_field", ("_defaults_payload",)),
        (["report", "--target", "{target}"], "report", "answer.not_a_real_field", ("_selected_runtime_context",)),
    ],
)
def test_command_families_reject_nested_unknown_selectors_before_projection(
    tmp_path: Path,
    capsys,
    monkeypatch,
    argv: list[str],
    source_command: str,
    unknown_selector: str,
    tripwire_attrs: tuple[str, ...],
) -> None:
    _init_git_repo(tmp_path)
    command_argv = [str(tmp_path) if token == "{target}" else token for token in argv]

    def fail_payload_construction(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError(f"{source_command} payload/runtime builder must not run for an invalid nested selector")

    for attr in tripwire_attrs:
        monkeypatch.setattr(cli, attr, fail_payload_construction)

    assert cli.main([*command_argv, "--select", unknown_selector, "--format", "json"]) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["source_command"] == source_command
    assert payload["unknown_selectors"] == [unknown_selector]
    assert len(json.dumps(payload)) <= 6000
    assert payload["selector_budget"]["max_error_envelope_bytes"] == 6000
    assert payload["selector_inventory"]["inventory_command"].endswith("--select selector_inventory --format json")


def test_selector_error_size_measurements_stay_under_budget(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    cases = {
        "ordinary_typo": ["start", "--target", str(tmp_path), "--select", "not_a_selector", "--format", "json"],
        "nested_typo": ["start", "--target", str(tmp_path), "--select", "context.not_a_real_field", "--format", "json"],
        "oversized_request": [
            "start",
            "--target",
            str(tmp_path),
            "--select",
            ",".join(f"missing_{index}" for index in range(40)),
            "--format",
            "json",
        ],
        "explicit_inventory": ["start", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"],
    }
    measurements: dict[str, dict[str, int]] = {}

    for name, argv in cases.items():
        expected_exit = 0 if name == "explicit_inventory" else 2
        assert cli.main(argv) == expected_exit
        text = capsys.readouterr().out
        measurements[name] = {"bytes": len(text.encode("utf-8")), "lines": len(text.splitlines())}

    assert measurements["ordinary_typo"]["bytes"] < 2400
    assert measurements["nested_typo"]["bytes"] < 2600
    assert measurements["oversized_request"]["bytes"] < 2000
    assert measurements["explicit_inventory"]["bytes"] > measurements["nested_typo"]["bytes"]
    assert measurements["explicit_inventory"]["bytes"] < 25000


def test_implement_selector_inventory_route_is_executable(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--task",
                "check selector inventory",
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "selector_inventory",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    inventory = payload["values"]["selector_inventory"]
    assert inventory["kind"] == "agentic-workspace/selector-inventory/v1"
    assert inventory["source_command"] == "implement"
    assert inventory["available_count"] > 8
    assert "context.workflow_sufficiency" in inventory["selectors"]


def test_implement_selector_inventory_does_not_build_implement_payload(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_implement_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("selector inventory must not build the implement payload")

    monkeypatch.setattr(cli, "_implement_payload", fail_implement_payload)

    assert cli.main(["implement", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["values"]["selector_inventory"]["source_command"] == "implement"


def test_implement_select_next_does_not_build_full_implement_payload(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_implement_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("implement --select next must not build the full implement payload")

    def fail_runtime_diagnostics(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("implement --select next must not build runtime proof diagnostics")

    monkeypatch.setattr(cli, "_implement_payload", fail_implement_payload)
    monkeypatch.setattr(workspace_runtime_proof, "runtime_source_edit_review_for_changed_paths", fail_runtime_diagnostics)
    monkeypatch.setattr(workspace_runtime_proof, "runtime_symbol_working_set_for_changed_paths", fail_runtime_diagnostics)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--task",
                "fix selected next latency",
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "next",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    next_payload = payload["values"]["next"]
    assert next_payload["status"] == "changed-path-context"
    assert next_payload["action"]
    assert "commands" in next_payload


def _assert_implement_select_next_matches_tiny_payload(
    tmp_path: Path, capsys, *, changed_paths: list[str] | None = None, extra_args: list[str] | None = None
) -> None:
    changed_paths = changed_paths or []
    extra_args = extra_args or []
    base_args = ["implement", "--target", str(tmp_path), "--task", "fix selector next parity"]
    for path in changed_paths:
        base_args.extend(["--changed", path])

    assert cli.main([*base_args, *extra_args, "--format", "json"]) == 0
    ordinary = json.loads(capsys.readouterr().out)
    assert cli.main([*base_args, *extra_args, "--select", "next", "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)["values"]["next"]

    decision = ordinary["decision_packet"]
    assert decision["action"]["summary"] == selected["action"]
    if selected.get("command"):
        assert decision["action"]["command"] == selected["command"]
    assert "--select next" in decision["detail_routes"]["decision_detail"]
    assert ordinary.keys() == {"kind", "target", "decision_packet"}


def test_implement_select_next_matches_tiny_payload_for_normal_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src/sample_app/text.py", "VALUE = 1\n")

    _assert_implement_select_next_matches_tiny_payload(tmp_path, capsys, changed_paths=["src/sample_app/text.py"])


def test_implement_select_next_matches_tiny_payload_for_unknown_scope(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    _assert_implement_select_next_matches_tiny_payload(tmp_path, capsys)


def test_implement_select_next_matches_tiny_payload_for_path_attention(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src/sample_app/text.py", "VALUE = 1\n")

    def attention_boundary(path: str, *, agent_instructions_file: str) -> dict[str, Any]:
        return {
            "path": path,
            "authority": "requires-attention",
            "requires_attention": True,
            "warning": f"Inspect {agent_instructions_file} before editing.",
        }

    monkeypatch.setattr(cli, "_boundary_warning_for_path", attention_boundary)

    _assert_implement_select_next_matches_tiny_payload(tmp_path, capsys, changed_paths=["src/sample_app/text.py"])


def test_implement_select_next_matches_tiny_payload_for_planning_insufficient(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src/sample_app/text.py", "VALUE = 1\n")
    original_gate = workspace_runtime_planning._planning_safety_gate_payload

    def insufficient_gate(*args: Any, **kwargs: Any) -> dict[str, Any]:
        gate = copy.deepcopy(original_gate(*args, **kwargs))
        gate["workflow_sufficient"] = False
        gate["decision"] = "planning-required"
        gate["gate_result"] = "planning-required"
        gate["required_next_action"] = "Create or promote an active execplan before continuing implementation."
        return gate

    monkeypatch.setattr(cli, "_planning_safety_gate_payload", insufficient_gate)

    _assert_implement_select_next_matches_tiny_payload(tmp_path, capsys, changed_paths=["src/sample_app/text.py"])


def test_implement_select_next_matches_tiny_payload_for_proof_route_claim_blocking(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src/sample_app/text.py", "VALUE = 1\n")
    original_proof = workspace_runtime_proof._proof_selection_for_changed_paths

    def claim_blocking_proof(*args: Any, **kwargs: Any) -> dict[str, Any]:
        proof = copy.deepcopy(original_proof(*args, **kwargs))
        proof["proof_route_strategy_preservation"] = {
            "decision_id": "proof-route-test",
            "claim_effect": "claim-blocked",
            "selected_requirement": "focused-proof-required",
        }
        return proof

    monkeypatch.setattr(cli, "_proof_selection_for_changed_paths", claim_blocking_proof)

    _assert_implement_select_next_matches_tiny_payload(tmp_path, capsys, changed_paths=["src/sample_app/text.py"])


def test_implement_select_next_matches_tiny_payload_for_stale_startup_fingerprint(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src/sample_app/text.py", "VALUE = 1\n")
    original_principles = workspace_runtime_core._architecture_principles_payload

    def matched_principles(*args: Any, **kwargs: Any) -> dict[str, Any]:
        packet = copy.deepcopy(original_principles(*args, **kwargs))
        packet["matched_count"] = 1
        packet["matched_principles"] = [{"id": "selector-next-parity", "summary": "Exercise stale startup route checks."}]
        return packet

    def route_identity(*, root: Path, task: str) -> dict[str, Any]:
        return {"fingerprint": "actual-fingerprint", "observed": {"head": "new"}}

    def fingerprint_check(*, expected_fingerprint: str, root: Path, task: str) -> dict[str, Any]:
        return {
            "status": "mismatch",
            "expected": expected_fingerprint,
            "actual": {"fingerprint": "actual-fingerprint", "observed": {"head": "new"}},
        }

    monkeypatch.setattr(workspace_runtime_implement, "_architecture_principles_payload", matched_principles)
    monkeypatch.setattr(workspace_runtime_implement, "startup_route_identity", route_identity)
    monkeypatch.setattr(workspace_runtime_implement, "startup_route_fingerprint_check", fingerprint_check)

    _assert_implement_select_next_matches_tiny_payload(
        tmp_path,
        capsys,
        changed_paths=["src/sample_app/text.py"],
        extra_args=["--startup-route-fingerprint", "stale-fingerprint"],
    )


def test_implement_accepts_context_plan_delegation_packet_selector(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "requirement_grounding,context.delegation_decision,context.plan_delegation_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert "context.plan_delegation_packet" in payload["values"]
    assert "unknown_selectors" not in payload


def test_report_unknown_selector_fails_before_runtime_context(monkeypatch, capsys) -> None:
    def fail_runtime_context(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("report runtime context must not be assembled for an unknown selector")

    monkeypatch.setattr(cli, "_selected_runtime_context", fail_runtime_context)

    assert cli.main(["report", "--select", "not_a_selector", "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["unknown_selectors"] == ["not_a_selector"]


def test_report_selector_conflict_fails_before_runtime_context(monkeypatch, capsys) -> None:
    def fail_if_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("report runtime context must not be assembled for invalid selectors")

    monkeypatch.setattr(cli, "_selected_runtime_context", fail_if_called)

    with pytest.raises(SystemExit, match="2"):
        cli.main(["report", "--verbose", "--section", "agent_aids", "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["failure_class"] == "selector-conflict"
    assert "report detail selectors are mutually exclusive" in payload["message"]


def test_state_delta_packet_views_derive_from_shared_core() -> None:
    from agentic_workspace.reporting_support import (
        continuation_capsule_payload,
        current_decision_payload,
        evidence_bundle_payload,
        message_economy_payload,
        state_delta_core_payload,
        state_delta_replay_evidence_payload,
        visible_state_delta_response_payload,
        work_shape_study_comparison_evidence_payload,
    )

    decision_packet = {
        "kind": "agentic-workspace/ordinary-decision-packet/v1",
        "phase_question": "What changed?",
        "next_action": "Run the focused proof.",
        "claim_boundary": "partial-progress",
        "residue_owner": "planning",
        "required_commands": ["pytest tests/test_workspace_cli.py"],
        "detail_routes": {"proof_detail": "proof --select proof", "why_blocked": "start --select next_safe_action"},
    }
    contract = {
        "kind": "agentic-workspace/communication-contract/v1",
        "expand_when": ["stale_missing_or_failed_proof", "user_requests_detail"],
    }

    core = state_delta_core_payload(
        surface="startup",
        decision_packet=decision_packet,
        communication_contract=contract,
        evidence_basis=["decision_packet", "proof_route"],
    )
    current = current_decision_payload(surface="startup", decision_packet=decision_packet, state_delta_core=core)
    economy = message_economy_payload(surface="startup", communication_contract=contract, state_delta_core=core)
    capsule = continuation_capsule_payload(
        surface="startup",
        current_decision=current,
        message_economy=economy,
        preserved_intent="keep state compact",
        state_delta_core=core,
        work_shape_study={
            "status": "sufficient",
            "evidence": {"observed": ["#2162:kind=parent-lane"], "inferred": [], "missing": []},
            "decision": {
                "work_shape": "lane",
                "planning_artifact_route": "lane-planning",
                "next_safe_action": "create-or-promote-lane-owner",
            },
            "freshness": {"task_binding": ["#2162"], "intent_revision": "r1"},
            "consumption": {"state": "pending", "retain_after_consumption": False},
        },
    )
    bundle = evidence_bundle_payload(surface="startup", current_decision=current, state_delta_core=core)
    visible = visible_state_delta_response_payload(
        surface="startup",
        current_decision=current,
        message_economy=economy,
        evidence_bundle=bundle,
    )
    replay = state_delta_replay_evidence_payload()
    study_comparison = work_shape_study_comparison_evidence_payload()

    assert core["kind"] == "agentic-workspace/state-delta-core/v1"
    assert current["proof_boundary"] == core["boundary"]["proof"]
    assert capsule["proof_boundary"] == core["boundary"]["proof"]
    assert current["residue_owner"] == core["boundary"]["residue_owner"]
    assert capsule["unresolved_residue"] == core["boundary"]["residue_owner"]
    assert current["known_evidence"] == core["evidence"]["known"][:1]
    assert capsule["known_evidence"] == core["evidence"]["known"][:2]
    assert bundle["minimal_evidence_surfaces"][0]["id"] == core["evidence"]["route_ids"][0]
    assert current["next_action"] == core["decision"]["next_action"]
    assert capsule["next_safe_action"] == core["decision"]["next_action"]
    assert economy["expand_when"] == core["output_policy"]["expand_when"]
    assert current["avoid_repeat"] == core["output_policy"]["avoid"]
    assert capsule["do_not_repeat"] == core["output_policy"]["avoid"]
    assert capsule["work_shape_seed"]["selected_shape"] == "lane"
    assert capsule["work_shape_seed"]["observed"] == ["#2162:kind=parent-lane"]
    assert capsule["work_shape_seed"]["consumption"]["retain_after_consumption"] is False
    assert capsule["work_shape_seed"]["authority"].startswith("disposable seed")
    assert visible["kind"] == "agentic-workspace/visible-state-delta-response/v1"
    assert visible["parts"] == {
        "decision_or_finding": "What changed?",
        "evidence_or_proof_boundary": "partial-progress",
        "residue_or_claim_boundary": "planning",
        "next_safe_action": "Run the focused proof.",
    }
    assert visible["ownership_boundary"].endswith("not a new truth source.")
    assert visible["route_budget"] == {
        "status": "within-budget",
        "max_generated_next_actions": 1,
        "max_report_scans": 1,
        "max_visible_parts": 4,
        "generated_action_policy": "never-verbose-without-explicit-expansion",
        "snapshot_reuse": "revision-keyed",
    }
    assert visible["composed_closeout"]["requires_additional_report_scan"] is False

    assert replay["workflow_class_count"] >= 2
    assert replay["status"] == "admitted-ordinary-route-measurement"
    assert replay["ordinary_route_measurement"]["workflow_classes"] == ["startup", "implementation", "closeout"]
    assert [item["task_class"] for item in study_comparison["scenarios"]] == [
        "clear",
        "shape-uncertain",
        "apparent-uncertainty",
    ]
    assert study_comparison["scenarios"][0]["study_route"] == "skipped"
    assert study_comparison["scenarios"][1]["shape_after"] == "lane"
    assert study_comparison["scenarios"][2]["shape_after"] == "bounded"
    assert all("study_cost" in item and "downstream_savings" in item for item in study_comparison["scenarios"])
    assert {"review", "handoff", "closeout"} == {item["workflow_class"] for item in replay["examples"]}
    assert all("next_safe_action" in item["visible_parts"] for item in replay["examples"])
    assert all(item["composed_from_state"] is True for item in replay["examples"])
    assert all(item["observed_cost"]["report_scans"] == 1 for item in replay["examples"])
    assert replay["route_cost_budget"]["max_verbose_generated_actions"] == 0


def _assert_selector_inventory_omitted_from_compact_start(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload.get("decision_packet", {})
    if isinstance(decision, dict) and decision.get("kind") == "agentic-workspace/ordinary-start-decision/v1":
        assert "selector_inventory" in decision["detail_routes"]
        return {"status": "selector-routed", "available_count": 0, "sample": []}
    drill_down = payload["drill_down"]
    assert "available_selectors" not in drill_down
    inventory = drill_down["selector_inventory"]
    assert inventory["status"] == "omitted-from-compact-default"
    assert inventory["available_count"] > 0
    assert inventory["sample"]
    assert "start --target . --select <field[,field...]> --format json" in inventory["exact_select_command"]
    assert "start --target . --verbose --format json" in inventory["broad_diagnostics_command"]
    return inventory


def _write_cli_architecture_principles(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
kind = "agentic-workspace/system-intent/v1"
summary = "Portable host-neutral operating intent."
governing_intents = ["Keep package contracts portable across host repos."]
anti_intents = ["Do not let this repo's current language, tooling, structure, or agent preferences become hidden universal product assumptions."]
decision_tests = ["Favor work that improves portability by reducing accidental repo assumptions."]
confidence = "high"
needs_review = false

[[architecture_principles]]
id = "host-agnostic-agent-judgment"
title = "Preserve host-agnostic agent judgment"
authority = "repo-system-intent"
owner = "workspace-runtime"
summary = "AW provides infrastructure for agent judgment instead of package-owned host assumptions."
allowed_sources = ["explicit structured facts", "AW-owned enum labels", "configuration"]
forbidden_sources = ["package-owned assumptions about prose keywords", "package-owned assumptions about file names"]
affected_decisions = ["routing", "ownership", "proof-selection"]
path_globs = ["src/agentic_workspace/workspace_runtime*.py", "src/agentic_workspace/config.py"]
proof_expectation = "Closeout must state whether the principle was preserved or re-scoped."
""",
    )


def _write_decision_point_subsystem_intent(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace" / "OWNERSHIP.toml",
        """
schema_version = 1

[[subsystems]]
id = "workspace-cli-runtime"
paths = ["src/agentic_workspace/workspace_runtime*.py"]
owns = ["Workspace host-facing runtime"]

[[subsystems]]
id = "planning"
paths = ["packages/planning/src/example.py", "packages/planning/**", ".agentic-workspace/planning/**"]
owns = ["Planning state"]

[[subsystems]]
id = "configuration"
paths = ["src/agentic_workspace/config.py"]
owns = ["Workspace configuration contract"]
""",
    )
    _write(
        target_root / ".agentic-workspace" / "system-intent" / "subsystems.toml",
        """
schema_version = 1
kind = "agentic-workspace/subsystem-intent-set/v1"

[[subsystems]]
id = "workspace-cli-runtime"
scope = "Workspace host-facing CLI runtime"
status = "active"
summary = "Ordinary host-facing behavior belongs through the Workspace CLI; module CLIs remain internal/debug compatibility surfaces."
decision_tests = ["Is this implemented and proved through the ordinary Workspace front door?"]
confidence = "high"
needs_review = false
source_records = [{ source_type = "issue", ref = "#2180", summary = "Front-door regression." }]

[[subsystems]]
id = "planning"
scope = "Planning module"
status = "active"
summary = "Planning owns checked-in execution state and honest continuation."
decision_tests = ["Does the change preserve current execution intent?"]
confidence = "high"
needs_review = false
source_records = [{ source_type = "issue", ref = "#746", summary = "Planning intent." }]

[[subsystems]]
id = "configuration"
scope = "Workspace configuration contract"
status = "active"
summary = "Configuration changes preserve explicit precedence and source provenance."
decision_tests = ["Does the change preserve declared precedence and provenance?"]
confidence = "high"
needs_review = false
source_records = [{ source_type = "docs", ref = ".agentic-workspace/docs/lifecycle-and-config-contract.md", summary = "Configuration authority." }]
""",
    )


def test_repeated_module_flags_accumulate_module_selection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--modules", "memory", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["planning", "memory"]


def test_repeated_singular_module_alias_accumulates_module_selection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--module", "memory", "--module", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["planning", "memory"]


def test_lifecycle_guidance_uses_canonical_modules_option(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--modules", "planning,memory", "--target", str(tmp_path), "--dry-run", "--verbose", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    command_text = json.dumps(payload["lifecycle_plan"])
    assert "--modules planning,memory" in command_text
    assert "--module planning --module memory" not in command_text


def test_init_ordinary_footprint_omits_package_payload_and_writes_receipt(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--modules",
                "planning,memory",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["footprint_profile"] == "necessary-surfaces"
    assert payload["payload_mirror"] is False
    assert payload["bootstrap_footprint"]["status"] == "necessary-surfaces"
    assert not (tmp_path / ".agentic-workspace" / "planning" / "state.toml").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "execplans" / "README.md").exists()
    assert (tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md").exists()
    receipt = json.loads((tmp_path / ".agentic-workspace" / "adoption-receipt.json").read_text(encoding="utf-8"))
    assert receipt["kind"] == "agentic-workspace/adoption-receipt/v1"
    assert receipt["checked_in_rule"] == "necessary-surfaces-only"
    assert receipt["payload_mirror"] is False
    assert receipt["configuration_readiness"]["kind"] == "agentic-workspace/configuration-readiness/v1"
    assert receipt["configuration_readiness"]["status"] == "reconciliation-required"
    assert receipt["configuration_readiness"]["required_skill"] == "workspace-setup-jumpstart"
    assert "absolute-path provenance" in receipt["local_only"]
    assert not (tmp_path / ".agentic-workspace" / "payload-provenance.json").exists()
    assert not (tmp_path / ".agentic-workspace" / "AGENTS.md").exists()
    assert not (tmp_path / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml").exists()
    assert (tmp_path / ".agentic-workspace" / "skills" / "workspace-startup" / "SKILL.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "skills" / "REGISTRY.json").exists()
    assert (tmp_path / ".agentic-workspace" / "memory" / "skills" / "memory-router" / "SKILL.md").exists()
    assert ".agentic-workspace/package-payload" in payload["bootstrap_footprint"]["omitted_package_payload_paths"]
    assert payload["validation"] == ["agentic-workspace doctor --target .", "agentic-workspace status --target ."]


def test_fresh_bootstrap_routes_ordinary_start_to_exact_setup_continuation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Implement the requested change.", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    decision = payload["decision_packet"]
    readiness = decision["configuration_readiness"]
    action = decision["action"]
    assert readiness["status"] == "reconciliation-required"
    assert readiness["owner"] == "setup.guidance"
    assert readiness["required_skill"] == "workspace-setup-jumpstart"
    assert action["id"] == "reconcile-repository-configuration"
    assert action["command"].endswith("setup --target . --format json")
    assert action["skill"] == "workspace-setup-jumpstart"
    assert decision["effects"]["implementation_allowed"] is False
    assert "configured-workflow implementation" in " ".join(decision["effects"]["forbidden_actions"])


def test_current_or_legacy_adoption_receipt_keeps_ordinary_start_quiet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    receipt_path = tmp_path / ".agentic-workspace" / "adoption-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["configuration_readiness"]["status"] = "current"
    _write(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    current = json.loads(capsys.readouterr().out)
    assert "configuration_readiness" not in current["decision_packet"]
    assert current["decision_packet"]["action"]["id"] != "reconcile-repository-configuration"

    receipt.pop("configuration_readiness")
    _write(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    legacy = json.loads(capsys.readouterr().out)
    assert "configuration_readiness" not in legacy["decision_packet"]
    assert legacy["decision_packet"]["action"]["id"] != "reconcile-repository-configuration"


def test_stale_configuration_readiness_identity_routes_only_the_affected_claim(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    receipt_path = tmp_path / ".agentic-workspace" / "adoption-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["configuration_readiness"]["status"] = "current"
    receipt["configuration_readiness"]["identity"] = "obsolete-bootstrap-identity"
    _write(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Implement the requested change.", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    decision = payload["decision_packet"]
    readiness = decision["configuration_readiness"]
    assert readiness["status"] == "stale"
    assert readiness["identity"] == "obsolete-bootstrap-identity"
    assert decision["action"]["id"] == "reconcile-repository-configuration"
    assert decision["effects"]["read_only_allowed"] is True
    assert decision["effects"]["implementation_allowed"] is False


def test_init_adopts_local_state_and_uses_local_scratch_handoff(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "AGENTS.md", "# Existing instructions\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "state.toml", "active_items = []\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "existing.plan.json", "{}\n")
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md", "# Existing Memory\n")

    assert (
        cli.main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--modules",
                "planning,memory",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["footprint_profile"] == "necessary-surfaces"
    assert payload["payload_mirror"] is False
    assert payload["handoff_prompt_path"].endswith(".agentic-workspace/local/scratch/bootstrap-handoff.md")
    assert payload["handoff_record_path"].endswith(".agentic-workspace/local/scratch/bootstrap-handoff.json")
    assert payload["handoff_record"]["scope"]["target"] == "."
    receipt = json.loads((tmp_path / ".agentic-workspace" / "adoption-receipt.json").read_text(encoding="utf-8"))
    assert "planning/execplans" in "\n".join(receipt["adopted_state"])
    assert not (tmp_path / ".agentic-workspace" / "bootstrap-handoff.md").exists()
    assert not (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").exists()
    assert (tmp_path / ".agentic-workspace" / "local" / "scratch" / "bootstrap-handoff.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "execplans" / "existing.plan.json").exists()


def test_install_ordinary_footprint_omits_package_payload(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["install", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["payload_mirror"] is False
    assert payload["bootstrap_footprint"]["status"] == "necessary-surfaces"
    receipt = json.loads((tmp_path / ".agentic-workspace" / "adoption-receipt.json").read_text(encoding="utf-8"))
    assert receipt["payload_mirror"] is False
    assert not (tmp_path / ".agentic-workspace" / "payload-provenance.json").exists()
    assert (tmp_path / ".agentic-workspace" / "skills" / "workspace-startup" / "SKILL.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "skills" / "REGISTRY.json").exists()
    assert (tmp_path / ".agentic-workspace" / "memory" / "skills" / "memory-router" / "SKILL.md").exists()


def test_init_mirror_payload_writes_payload_and_receipt(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--modules",
                "planning,memory",
                "--mirror-payload",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["payload_mirror"] is True
    assert payload["bootstrap_footprint"]["status"] == "full-mirror"
    receipt = json.loads((tmp_path / ".agentic-workspace" / "adoption-receipt.json").read_text(encoding="utf-8"))
    assert receipt["payload_mirror"] is True
    assert (tmp_path / ".agentic-workspace" / "payload-provenance.json").exists()
    assert (tmp_path / ".agentic-workspace" / "AGENTS.md").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml").exists()


def test_doctor_requires_adoption_receipt_before_treating_missing_payload_as_healthy(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "adoption-receipt.json").unlink()

    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert "installed_state_compatibility" not in payload
    assert payload["installed_state_summary"]["provenance_drift"] == "missing-provenance"
    assert payload["installed_state_summary"]["action_required"] is True
    assert "installed_state_compatibility" in payload["diagnostic_detail"]["selectors"]

    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json", "--select", "installed_state_compatibility"]) == 0
    selected = json.loads(capsys.readouterr().out)
    assert selected["values"]["installed_state_compatibility"]["payload"]["provenance_drift"] == "missing-provenance"


@pytest.mark.parametrize(
    ("command", "missing_paths", "expected_warning"),
    [
        (
            "status",
            (".agentic-workspace/planning/execplans/README.md", ".agentic-workspace/planning/skills/REGISTRY.json"),
            "enabled module 'planning' is not installed",
        ),
        (
            "doctor",
            (".agentic-workspace/planning/execplans/README.md", ".agentic-workspace/planning/skills/REGISTRY.json"),
            "enabled module 'planning' is not installed",
        ),
        ("status", (".agentic-workspace/memory/repo/index.md",), "enabled module 'memory' is not installed"),
        ("doctor", (".agentic-workspace/memory/repo/index.md",), "enabled module 'memory' is not installed"),
    ],
)
def test_adoption_receipt_does_not_hide_missing_necessary_module_anchors(
    tmp_path: Path, capsys, command: str, missing_paths: tuple[str, ...], expected_warning: str
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    assert (tmp_path / ".agentic-workspace" / "adoption-receipt.json").is_file()
    for missing_path in missing_paths:
        (tmp_path / missing_path).unlink()

    assert cli.main([command, "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert expected_warning in payload["warnings"]


def test_bootstrap_footprint_defaults_to_necessary_surfaces_with_explicit_mirror_opt_in(tmp_path: Path) -> None:
    from agentic_workspace import workspace_runtime_core

    assert workspace_runtime_core._resolve_bootstrap_footprint_profile(target_root=tmp_path) == "necessary-surfaces"
    assert workspace_runtime_core._resolve_bootstrap_footprint_profile(target_root=tmp_path, mirror_payload=True) == "full-payload-mirror"


def test_setup_surfaces_host_orientation_candidates_for_jumpstarted_repo(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "README.md", "# Host Repo\n")
    _write(tmp_path / "docs" / "architecture.md", "# Architecture\n")
    _write(tmp_path / "pyproject.toml", "[project]\nname = 'host-repo'\nversion = '0.1.0'\n")
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_smoke.py", "def test_smoke():\n    assert True\n")

    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--non-interactive", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    host_orientation = payload["host_orientation"]
    assert host_orientation["status"] == "present"
    surfaces = {candidate["surface"] for candidate in host_orientation["candidates"]}
    assert {"README.md", "docs/architecture.md", "docs", "pyproject.toml", "src", "tests"} <= surfaces
    assert payload["analysis_input"]["status"] == "not-found"
    assert "must not seed Memory, Planning, assurance, or verification state" in host_orientation["rule"]
    assert not any("--target ./repo" in command for command in payload["next_action"]["commands"])
    assert payload["configuration_concerns"]["status"] == "zero-question-ready"
    assert any("system-intent --target . --sync" in command for command in payload["next_action"]["commands"])


def test_setup_infers_mature_repo_configuration_without_human_questions(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "README.md", "# Orders service\n\nProcesses customer orders.\n")
    _write(
        tmp_path / "pyproject.toml", "[project]\nname = 'orders'\nversion = '0.1.0'\n\n[tool.pytest.ini_options]\ntestpaths = ['tests']\n"
    )
    _write(tmp_path / ".github" / "CODEOWNERS", "/src/orders/ @orders-team\n")
    _write(tmp_path / ".github" / "workflows" / "ci.yml", "name: CI\non: [push]\njobs: {}\n")
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0

    concerns = json.loads(capsys.readouterr().out)["configuration_concerns"]
    by_id = {concern["id"]: concern for concern in concerns["concerns"]}
    assert concerns["status"] == "zero-question-ready"
    assert concerns["human_questions"] == []
    assert by_id["system-intent-source"]["status"] == "inference-ready"
    assert by_id["proof-route"]["status"] == "inference-ready"
    assert by_id["ownership-boundaries"]["status"] == "inference-ready"
    assert by_id["verification-capability"]["status"] == "inference-ready"
    inferred = concerns["inferred_configuration"]
    assert inferred["startup_adapter"] == "AGENTS.md"
    assert inferred["intent_source"] == "README.md"
    assert inferred["proof_command_candidates"] == ["pytest"]
    assert inferred["ownership_source"] == ".github/CODEOWNERS"
    assert inferred["capability_outcomes"] == ["Preserve repeatable CI-backed proof routes for future claims."]
    assert {action["owner"] for action in concerns["zero_interaction_actions"]} == {
        "system-intent.sync",
        "proof.selection",
        "ownership.report",
        "modules.reconcile",
    }
    assert all("verification" not in question["question"].lower() for question in concerns["human_questions"])


def test_setup_asks_plain_language_question_for_unresolved_human_policy(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[delegation]\nexecution_role = 'orchestrator'\n",
    )

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0

    concerns = json.loads(capsys.readouterr().out)["configuration_concerns"]
    question = concerns["human_questions"][0]
    assert concerns["status"] == "human-decision-required"
    assert question["answer_owner"] == "config.policy-apply"
    assert question["already_inferred"] == "Multi-agent orchestration is intended; the transfer policy is unresolved."
    assert "automatically" in question["question"]
    assert "assignment_policy" not in question["question"]
    assert all(choice["consequence"] for choice in question["alternatives"])
    assert all(choice["decision"]["scope"] == "local" for choice in question["alternatives"])
    assert "--expect-config-revision sha256:" in question["apply_command"]


def test_config_policy_apply_preserves_comments_unknown_fields_and_rejects_stale_revision(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.write_text(
        "schema_version = 1\n\n[modules]\nenabled = ['planning', 'memory']\n\n"
        "[workspace]\nimprovement_latitude = 'conservative' # keep this comment\n"
        "host_extension = 'preserve-me'\n",
        encoding="utf-8",
    )
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    concerns = json.loads(capsys.readouterr().out)["configuration_concerns"]
    context = concerns["mutation_context"]
    decision = {
        "kind": "agentic-workspace/config-policy-decision/v1",
        "concern_id": "improvement-latitude",
        "authority": "human-answer",
        "scope": "shared",
        "setup_identity": context["setup_identity"],
        "changes": {"workspace.improvement_latitude": "balanced"},
    }
    argv = [
        "config-policy",
        "--target",
        str(tmp_path),
        "--decision-json",
        json.dumps(decision),
        "--expect-config-revision",
        context["shared_config_revision"],
        "--expect-setup-identity",
        context["setup_identity"],
        "--format",
        "json",
    ]
    assert cli.main([*argv, "--dry-run"]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["status"] == "preview"
    assert "improvement_latitude = 'conservative'" in config_path.read_text(encoding="utf-8")
    assert cli.main(argv) == 0
    applied = json.loads(capsys.readouterr().out)
    text = config_path.read_text(encoding="utf-8")
    assert applied["outcome"] == "applied"
    assert 'improvement_latitude = "balanced" # keep this comment' in text
    assert "host_extension = 'preserve-me'" in text
    with pytest.raises(SystemExit) as stale_exit:
        cli.main(argv)
    assert stale_exit.value.code == 2
    assert "revision is stale" in capsys.readouterr().err
    assert config_path.read_text(encoding="utf-8") == text


def test_config_policy_apply_keeps_local_authority_and_completes_matching_readiness(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    context = json.loads(capsys.readouterr().out)["configuration_concerns"]["mutation_context"]
    decision = {
        "kind": "agentic-workspace/config-policy-decision/v1",
        "concern_id": "orchestration-posture",
        "authority": "human-answer",
        "scope": "local",
        "setup_identity": context["setup_identity"],
        "changes": {"delegation.assignment_policy": "best-fit-advisory"},
    }
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(decision),
                "--expect-config-revision",
                context["local_config_revision"],
                "--expect-setup-identity",
                context["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["path"] == ".agentic-workspace/config.local.toml"
    assert "assignment_policy" not in (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
    assert 'assignment_policy = "best-fit-advisory"' in (tmp_path / ".agentic-workspace" / "config.local.toml").read_text(encoding="utf-8")

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    context = json.loads(capsys.readouterr().out)["configuration_concerns"]["mutation_context"]
    completion = context["reconciliation_completion"]["decision"]
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(completion),
                "--expect-config-revision",
                context["local_config_revision"],
                "--expect-setup-identity",
                context["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    completed = json.loads(capsys.readouterr().out)
    receipt = json.loads((tmp_path / ".agentic-workspace" / "adoption-receipt.json").read_text(encoding="utf-8"))
    assert completed["readiness_status"] == "current"
    assert receipt["configuration_readiness"]["status"] == "current"


def test_setup_defers_locally_resumes_without_transcript_and_re_elevates_required_work(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[delegation]\nexecution_role = 'orchestrator'\n",
    )

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    concerns = json.loads(capsys.readouterr().out)["configuration_concerns"]
    continuation = concerns["continuation"]
    assert continuation["configuration_freshness"] == "required-for-affected-action"
    assert continuation["user_disposition"] == "active"
    assert continuation["unresolved_concern_ids"] == ["orchestration-posture"]
    assert continuation["required_concern_ids"] == ["orchestration-posture"]
    defer_decision = continuation["actions"]["defer"]["decision"]
    local_revision = concerns["mutation_context"]["local_config_revision"]
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(defer_decision),
                "--expect-config-revision",
                local_revision,
                "--expect-setup-identity",
                continuation["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    local_text = (tmp_path / ".agentic-workspace" / "config.local.toml").read_text(encoding="utf-8")
    assert "[setup]" in local_text
    assert 'prompt_disposition = "deferred"' in local_text
    assert 'unresolved_concerns = ["orchestration-posture"]' in local_text

    for _ in range(2):
        assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
        deferred = json.loads(capsys.readouterr().out)["decision_packet"]
        assert deferred["configuration_readiness"]["status"] == "follow-up-deferred"
        assert deferred["configuration_readiness"]["unresolved_concern_ids"] == ["orchestration-posture"]
        assert deferred["action"]["id"] != "reconcile-repository-configuration"

    second_checkout = tmp_path.parent / f"{tmp_path.name}-second-local-context"
    shutil.copytree(tmp_path, second_checkout)
    second_local_path = second_checkout / ".agentic-workspace" / "config.local.toml"
    second_local = re.sub(r"(?ms)^\[setup\]\s*\n.*?(?=^\[|\Z)", "", second_local_path.read_text(encoding="utf-8"))
    _write(second_local_path, second_local)
    assert cli.main(["start", "--target", str(second_checkout), "--task", "Inspect README.md.", "--format", "json"]) == 0
    independent = json.loads(capsys.readouterr().out)["decision_packet"]
    assert independent["configuration_readiness"]["status"] == "reconciliation-required"
    assert independent["action"]["id"] == "reconcile-repository-configuration"

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Delegate this change to another agent.", "--format", "json"]) == 0
    required = json.loads(capsys.readouterr().out)["decision_packet"]
    assert required["configuration_readiness"]["status"] == "action-required"
    assert required["action"]["id"] == "reconcile-repository-configuration"

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    resumed_concerns = json.loads(capsys.readouterr().out)["configuration_concerns"]
    assert resumed_concerns["continuation"]["user_disposition"] == "deferred"
    assert resumed_concerns["continuation"]["unresolved_concern_ids"] == ["orchestration-posture"]
    resume_decision = resumed_concerns["continuation"]["actions"]["resume"]["decision"]
    assert resume_decision["clear_setup_disposition"] is True
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(resume_decision),
                "--expect-config-revision",
                resumed_concerns["mutation_context"]["local_config_revision"],
                "--expect-setup-identity",
                resumed_concerns["continuation"]["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert "[setup]" not in (tmp_path / ".agentic-workspace" / "config.local.toml").read_text(encoding="utf-8")

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    suppress_concerns = json.loads(capsys.readouterr().out)["configuration_concerns"]
    suppress_decision = suppress_concerns["continuation"]["actions"]["suppress_optional"]["decision"]
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(suppress_decision),
                "--expect-config-revision",
                suppress_concerns["mutation_context"]["local_config_revision"],
                "--expect-setup-identity",
                suppress_concerns["continuation"]["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    suppressed = json.loads(capsys.readouterr().out)["decision_packet"]
    assert suppressed["configuration_readiness"]["status"] == "optional-prompts-suppressed"
    assert suppressed["action"]["id"] != "reconcile-repository-configuration"
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Delegate this work.", "--format", "json"]) == 0
    suppressed_required = json.loads(capsys.readouterr().out)["decision_packet"]
    assert suppressed_required["configuration_readiness"]["status"] == "action-required"


def test_setup_deferral_is_revision_bound_and_completion_retires_local_residue(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    _write(tmp_path / "pyproject.toml", "[project]\nname = 'multi'\nversion = '0.1.0'\n")
    _write(tmp_path / "package.json", '{"name":"multi-web"}\n')
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    concerns = json.loads(capsys.readouterr().out)["configuration_concerns"]
    defer_decision = concerns["continuation"]["actions"]["defer"]["decision"]
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(defer_decision),
                "--expect-config-revision",
                concerns["mutation_context"]["local_config_revision"],
                "--expect-setup-identity",
                concerns["continuation"]["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    _write(tmp_path / "README.md", "# New bounded source context\n")
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect the repository.", "--format", "json"]) == 0
    stale = json.loads(capsys.readouterr().out)["decision_packet"]["configuration_readiness"]
    assert stale["status"] == "reconciliation-required"
    assert stale["stale_local_disposition"]["status"] == "discard-and-re-resolve"

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    current = json.loads(capsys.readouterr().out)["configuration_concerns"]
    completion = current["mutation_context"]["reconciliation_completion"]["decision"]
    assert completion["scope"] == "local"
    assert completion["clear_setup_disposition"] is True
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(completion),
                "--expect-config-revision",
                current["mutation_context"]["local_config_revision"],
                "--expect-setup-identity",
                current["mutation_context"]["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert "[setup]" not in (tmp_path / ".agentic-workspace" / "config.local.toml").read_text(encoding="utf-8")
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    quiet = json.loads(capsys.readouterr().out)["decision_packet"]
    assert "configuration_readiness" not in quiet


def test_setup_reconciles_only_current_enabled_module_concern_delta(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()

    def apply_completion(concerns: dict[str, Any]) -> None:
        completion = concerns["mutation_context"]["reconciliation_completion"]["decision"]
        assert (
            cli.main(
                [
                    "config-policy",
                    "--target",
                    str(tmp_path),
                    "--decision-json",
                    json.dumps(completion),
                    "--expect-config-revision",
                    concerns["mutation_context"]["local_config_revision"],
                    "--expect-setup-identity",
                    concerns["mutation_context"]["setup_identity"],
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        capsys.readouterr()

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    initial = json.loads(capsys.readouterr().out)["configuration_concerns"]
    apply_completion(initial)

    original_descriptors = workspace_runtime_core._module_operations()

    def module_contract(*, semantic_revision: str, source_revision: str, status: str, description: str = "Signals") -> dict[str, Any]:
        return validate_module_contract(
            {
                "schema_version": "agentic-workspace/module-capability/v2",
                "name": "signals",
                "description": description,
                "compatibility": {
                    "reader_epoch": 1,
                    "required_capabilities": ["module-setup-concerns-v1"],
                },
                "ownership": {
                    "roots": [],
                    "effect_classes": [],
                    "authority_exclusions": ["cannot grant mutation, proof, or completion authority"],
                },
                "relevance": {"task_terms": [], "path_prefixes": []},
                "capabilities": {
                    "resources": [],
                    "skills": [],
                    "operations": [],
                    "setup_concerns": [
                        {
                            "id": "retention-policy",
                            "semantic_revision": semantic_revision,
                            "source_revision": source_revision,
                            "status": status,
                            "materiality": "recommended",
                            "owner": "signals.retention-policy",
                            "applicability": {"kind": "module-enabled"},
                            "route": {"kind": "human-decision", "id": "signals.retention-policy"},
                            "question": "How long should imported build signals be retained?",
                            "source_obligation": {
                                "semantic_need": "the repository-approved retention schedule",
                                "source_class": "retention policy",
                                "owner": "signals.retention-policy",
                                "status": "missing" if status == "human-decision-required" else "satisfied",
                                "candidates": [] if status == "human-decision-required" else ["docs/retention.md"],
                                "current_source": "" if status == "human-decision-required" else "docs/retention.md",
                                "auto_bind_safe": False,
                                "affected_claims": ["signals-retention-ready"],
                                "continuation": {"kind": "create-source", "id": "signals.retention-policy"},
                            },
                        }
                    ],
                },
                "result_semantics": {
                    "schema_version": "signals/result/v1",
                    "guaranteed_fields": [],
                    "effect_fields": [],
                    "warning_fields": [],
                },
            }
        )

    current_contract = module_contract(semantic_revision="retention/v1", source_revision="source-r1", status="human-decision-required")

    def install_contract(contract: dict[str, Any]) -> None:
        discovered = DiscoveredModule(name="signals", entry_point="fixture:signals", contract=contract, operations={}, status="available")
        descriptor = workspace_runtime_core._external_module_descriptor(discovered)

        def descriptors() -> dict[str, Any]:
            return {**original_descriptors, "signals": descriptor}

        monkeypatch.setattr(workspace_runtime_core, "_module_operations", descriptors)
        monkeypatch.setattr(workspace_runtime_startup, "_module_operations", descriptors)
        monkeypatch.setattr(module_contract_runtime, "discover_module_contracts", lambda: [discovered])

    install_contract(current_contract)
    shared_path = tmp_path / ".agentic-workspace" / "config.toml"
    shared_text = shared_path.read_text(encoding="utf-8")
    shared_text = re.sub(r"enabled\s*=\s*\[[^\]]*\]", 'enabled = ["planning", "memory", "signals"]', shared_text)
    _write(shared_path, shared_text)

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    enabled_start = json.loads(capsys.readouterr().out)["decision_packet"]
    assert enabled_start["action"]["id"] == "reconcile-repository-configuration"
    assert enabled_start["configuration_readiness"]["status"] == "stale"

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    enabled = json.loads(capsys.readouterr().out)["configuration_concerns"]
    assert [question["concern_id"] for question in enabled["human_questions"]] == ["module:signals:retention-policy"]
    assert enabled["source_obligations"][0]["source_class"] == "retention policy"
    assert enabled["delta"]["counts"]["newly-applicable"] == 1
    assert all(not concern["setup_pressure"] for concern in enabled["concerns"] if not concern["id"].startswith("module:"))

    install_contract(module_contract(semantic_revision="retention/v1", source_revision="source-r2", status="satisfied"))
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    reconciled = json.loads(capsys.readouterr().out)["configuration_concerns"]
    assert reconciled["human_questions"] == []
    apply_completion(reconciled)
    recorded_concern = json.loads((tmp_path / ".agentic-workspace" / "adoption-receipt.json").read_text(encoding="utf-8"))[
        "configuration_readiness"
    ]["concern_receipts"]["module:signals:retention-policy"]
    current_concern = workspace_runtime_core._module_setup_concern_payloads(
        selected_modules=["planning", "memory", "signals"], descriptors=workspace_runtime_core._module_operations()
    )[0]
    assert recorded_concern["semantic_revision"] == current_concern["semantic_revision"]
    assert recorded_concern["source_revision"] == current_concern["source_revision"]
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    current_start = json.loads(capsys.readouterr().out)["decision_packet"]
    assert "configuration_readiness" not in current_start, current_start.get("configuration_readiness")

    install_contract(
        module_contract(
            semantic_revision="retention/v1",
            source_revision="source-r2",
            status="satisfied",
            description="Cosmetically revised module docs",
        )
    )
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    assert "configuration_readiness" not in json.loads(capsys.readouterr().out)["decision_packet"]

    install_contract(module_contract(semantic_revision="retention/v3", source_revision="source-r7", status="human-decision-required"))
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    changed = json.loads(capsys.readouterr().out)["decision_packet"]["configuration_readiness"]
    assert changed["changed_concern_ids"] == ["module:signals:retention-policy"]
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    jumped = json.loads(capsys.readouterr().out)["configuration_concerns"]
    assert [question["concern_id"] for question in jumped["human_questions"]] == ["module:signals:retention-policy"]
    assert jumped["delta"]["counts"]["semantics-changed"] == 1

    shared_text = re.sub(r"enabled\s*=\s*\[[^\]]*\]", 'enabled = ["planning", "memory"]', shared_path.read_text(encoding="utf-8"))
    _write(shared_path, shared_text)
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect README.md.", "--format", "json"]) == 0
    disabled = json.loads(capsys.readouterr().out)["decision_packet"]
    assert "configuration_readiness" not in disabled


def test_setup_surfaces_config_derived_repo_source_obligations_with_selective_consequences(tmp_path: Path, capsys) -> None:
    scenario = json.loads((Path(__file__).parent / "fixtures" / "source_obligation_lifecycle_v1.json").read_text(encoding="utf-8"))
    assert scenario["version"] == 1
    assert [stage["id"] for stage in scenario["stages"]] == [
        "config-creates-obligation",
        "domain-wording-and-routing",
        "defer",
        "resolve",
        "quiet-subsequent-startup",
    ]

    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    _write(tmp_path / "docs" / "intent-a.md", "# Intent A\n")
    _write(tmp_path / "docs" / "intent-b.md", "# Intent B\n")
    _write(tmp_path / "scratch" / "classifier.md", "# Weak local note\n")
    _write(tmp_path / "RISK_NOTES.md", "# Filename-only weak match\n")

    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_text = config_path.read_text(encoding="utf-8")
    config_text += (
        '\n[assurance]\nclassification_owner = "repository-owned"\nclassification_source = "scratch/classifier.md"\n'
        'invariant_registry = "docs/invariants.md"\n'
        '\n[system_intent]\nsources = ["docs/intent-a.md"]\n'
    )
    _write(config_path, config_text)

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    auto_bind = json.loads(capsys.readouterr().out)["configuration_concerns"]
    auto_by_id = {item["id"]: item for item in auto_bind["concerns"]}
    assert auto_by_id["source:system-intent"]["source_obligation"]["status"] == "candidate-existing"
    assert auto_by_id["source:system-intent"]["source_obligation"]["auto_bind_safe"] is True
    assert auto_by_id["source:assurance-classifier"]["source_obligation"]["status"] == "insufficient-authority"
    assert auto_by_id["source:invariant-registry"]["source_obligation"]["status"] == "missing"
    assert auto_by_id["source:invariant-registry"]["source_obligation"]["candidates"] == []
    assert auto_by_id["source:invariant-registry"]["source_obligation"]["scaffold"] == {
        "allowed": True,
        "content_boundary": "Create headings and ownership metadata only; do not invent substantive policy or domain decisions.",
    }
    assert "RISK_NOTES.md" not in auto_bind["inspection_budget"]["inspected_sources"]

    config_text = config_text.replace(
        'sources = ["docs/intent-a.md"]',
        'sources = ["docs/intent-a.md", "docs/intent-b.md"]',
    )
    _write(config_path, config_text)
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    unresolved = json.loads(capsys.readouterr().out)["configuration_concerns"]
    unresolved_by_id = {item["id"]: item for item in unresolved["concerns"]}
    assert unresolved_by_id["source:system-intent"]["source_obligation"]["status"] == "ambiguous"
    invariant_obligation = unresolved_by_id["source:invariant-registry"]["source_obligation"]
    assert invariant_obligation["owner"] == "assurance.config"
    assert invariant_obligation["continuation"]["kind"] == "create-source"
    assert "repository-owned invariant registry" in unresolved_by_id["source:invariant-registry"]["human_decision"]["question"]
    assert unresolved_by_id["source:invariant-registry"]["apply_route"]["status"] == "awaiting-human"
    assert {item["concern_id"] for item in unresolved["human_questions"]} >= {
        "source:system-intent",
        "source:assurance-classifier",
        "source:invariant-registry",
    }

    completion = unresolved["mutation_context"]["reconciliation_completion"]["decision"]
    with pytest.raises(SystemExit) as incomplete_exit:
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(completion),
                "--expect-config-revision",
                unresolved["mutation_context"]["local_config_revision"],
                "--expect-setup-identity",
                unresolved["mutation_context"]["setup_identity"],
                "--format",
                "json",
            ]
        )
    assert incomplete_exit.value.code == 2
    assert "required repo-source obligations" in capsys.readouterr().err

    defer = unresolved["continuation"]["actions"]["defer"]["decision"]
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(defer),
                "--expect-config-revision",
                unresolved["mutation_context"]["local_config_revision"],
                "--expect-setup-identity",
                unresolved["mutation_context"]["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Update README wording.", "--format", "json"]) == 0
    unrelated = json.loads(capsys.readouterr().out)["decision_packet"]["configuration_readiness"]
    assert unrelated["status"] == "follow-up-deferred"
    assert (
        cli.main(["start", "--target", str(tmp_path), "--task", "Complete the high assurance invariant review.", "--format", "json"]) == 0
    )
    affected = json.loads(capsys.readouterr().out)["decision_packet"]["configuration_readiness"]
    assert affected["status"] == "action-required"

    _write(tmp_path / "tools" / "classify.py", "# Repository-owned classification rules.\n")
    _write(tmp_path / "docs" / "invariants.md", "# Invariants\n\n- Domain owner supplies these invariants.\n")
    config_text = config_text.replace('classification_source = "scratch/classifier.md"', 'classification_source = "tools/classify.py"')
    config_text = config_text.replace(
        'sources = ["docs/intent-a.md", "docs/intent-b.md"]',
        'sources = ["docs/intent-a.md", "docs/intent-b.md"]\npreferred_source = "docs/intent-a.md"',
    )
    _write(config_path, config_text)
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    resolved = json.loads(capsys.readouterr().out)["configuration_concerns"]
    resolved_sources = {item["id"]: item for item in resolved["concerns"] if item["id"].startswith("source:")}
    assert {item["source_obligation"]["status"] for item in resolved_sources.values()} == {"satisfied"}
    completion = resolved["mutation_context"]["reconciliation_completion"]["decision"]
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(completion),
                "--expect-config-revision",
                resolved["mutation_context"]["local_config_revision"],
                "--expect-setup-identity",
                resolved["mutation_context"]["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Update README wording.", "--format", "json"]) == 0
    assert "configuration_readiness" not in json.loads(capsys.readouterr().out)["decision_packet"]

    (tmp_path / "docs" / "invariants.md").unlink()
    assert (
        cli.main(["start", "--target", str(tmp_path), "--task", "Complete the high assurance invariant review.", "--format", "json"]) == 0
    )
    stale = json.loads(capsys.readouterr().out)["decision_packet"]["configuration_readiness"]
    assert "workspace:source:invariant-registry" in stale["changed_concern_ids"]


def test_config_policy_apply_rejects_secret_material_without_writes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    context = json.loads(capsys.readouterr().out)["configuration_concerns"]["mutation_context"]
    decision = {
        "kind": "agentic-workspace/config-policy-decision/v1",
        "concern_id": "local-invocation",
        "authority": "human-answer",
        "scope": "local",
        "setup_identity": context["setup_identity"],
        "changes": {"workspace.cli_invoke": "tool --password secret-value"},
    }
    local_path = tmp_path / ".agentic-workspace" / "config.local.toml"
    before = local_path.read_bytes() if local_path.exists() else None
    with pytest.raises(SystemExit) as secret_exit:
        cli.main(
            [
                "config-policy",
                "--target",
                str(tmp_path),
                "--decision-json",
                json.dumps(decision),
                "--expect-config-revision",
                context["local_config_revision"],
                "--expect-setup-identity",
                context["setup_identity"],
                "--format",
                "json",
            ]
        )
    assert secret_exit.value.code == 2
    assert "secret" in capsys.readouterr().err
    assert (local_path.read_bytes() if local_path.exists() else None) == before


def test_setup_rejects_weak_policy_signals_and_bounds_broad_repo_analysis(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "SECURITY.md", "# Security\nBe secure.\n")
    _write(tmp_path / "scratch" / "high-assurance-notes.md", "Enable everything.\n")
    _write(tmp_path / "pyproject.toml", "[project]\nname = 'multi'\nversion = '0.1.0'\n")
    _write(tmp_path / "package.json", '{"name":"multi-web","scripts":{"build":"vite build"}}\n')
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0

    concerns = json.loads(capsys.readouterr().out)["configuration_concerns"]
    by_id = {concern["id"]: concern for concern in concerns["concerns"]}
    inspected = concerns["inspection_budget"]["inspected_sources"]
    assert concerns["status"] == "bounded-route-required"
    assert by_id["ownership-boundaries"]["status"] == "not-applicable"
    assert by_id["proof-route"]["status"] == "not-applicable"
    assert by_id["cross-ecosystem-boundaries"]["owner"] == "planning"
    assert "SECURITY.md" not in inspected
    assert not any(source.startswith("scratch/") for source in inspected)
    assert concerns["human_questions"] == []


def test_setup_does_not_claim_an_idle_planning_queue_is_current_work(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--non-interactive", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    planning_candidates = payload["discovery"]["planning_candidates"]
    assert not planning_candidates
    assert payload["orientation"].get("reason") != "active queue carries the current work slice"


def test_start_context_adapter_routes_through_startup_owner_facade() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    start_command = (repo_root / "generated" / "workspace" / "python" / "commands" / "start_context.py").read_text(encoding="utf-8")
    startup_facade = (repo_root / "generated" / "workspace" / "python" / "primitives" / "workspace_startup_runtime.py").read_text(
        encoding="utf-8"
    )

    assert "from ..primitives.workspace_startup_runtime import _run_start_context_adapter" in start_command
    assert "from agentic_workspace.workspace_runtime_startup import _run_start_context_adapter" in startup_facade
    assert workspace_runtime_primitives._run_start_context_adapter is workspace_runtime_startup._run_start_context_adapter


def test_active_planning_record_helpers_route_through_planning_owner(tmp_path: Path) -> None:
    assert workspace_runtime_primitives._active_planning_record_for_report_section is (
        workspace_runtime_planning._active_planning_record_for_report_section
    )
    assert workspace_runtime_primitives._raw_active_planning_record_for_closeout is (
        workspace_runtime_planning._raw_active_planning_record_for_closeout
    )
    assert workspace_runtime_startup._active_planning_record_for_report_section is (
        workspace_runtime_planning._active_planning_record_for_report_section
    )
    assert workspace_runtime_implement._active_planning_record_for_report_section is (
        workspace_runtime_planning._active_planning_record_for_report_section
    )
    assert workspace_runtime_proof._active_planning_record_for_report_section is (
        workspace_runtime_planning._active_planning_record_for_report_section
    )
    assert workspace_runtime_core._active_planning_record_for_report_section(target_root=tmp_path) == {}


def test_reconcile_report_adapter_routes_through_planning_owner() -> None:
    assert workspace_runtime_primitives._run_reconcile_report_adapter is workspace_runtime_planning._run_reconcile_report_adapter
    assert workspace_runtime_core._run_reconcile_report_adapter is workspace_runtime_planning._run_reconcile_report_adapter


def test_workspace_planning_reconcile_interface_projects_canonical_planning_options() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = json.loads((repo_root / "src/agentic_workspace/contracts/command_package_ir.json").read_text(encoding="utf-8"))
    packages = {package["id"]: package for package in manifest["packages"]}
    front_door = next(command for command in packages["root-workspace"]["commands"] if command["adapter_id"] == "planning.front-door.cli")
    source_projection = next(item for item in front_door["interface"]["subcommands"] if item["name"] == "reconcile")
    canonical = next(
        command for command in packages["planning-bootstrap"]["commands"] if command["adapter_id"] == "planning.reconcile.cli"
    )["interface"]
    generated = json.loads((repo_root / "generated/workspace/python/adapter_commands.json").read_text(encoding="utf-8"))
    generated_front_door = next(command["interface"] for command in generated if command["adapter_id"] == "planning.front-door.cli")
    projected = next(item for item in generated_front_door["subcommands"] if item["name"] == "reconcile")

    assert front_door["command"]["manifest_ref"] == "package:planning:cli#projected:reconcile"
    assert source_projection["options"] == []
    assert projected["options"] == canonical["options"]
    assert "--apply-pending-integrations" in {flag for option in projected["options"] for flag in option["flags"]}
    assert projected["usage_error_hints"] == source_projection["usage_error_hints"]


def test_workspace_planning_reconcile_accepts_projected_option_and_forwards_semantics(monkeypatch, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    captured: dict[str, Any] = {}

    def fake_reconcile(**kwargs):
        captured.update(kwargs)
        return {"kind": "planning-reconcile/v1", "status": "dry-run"}

    monkeypatch.setattr(planning_installer, "planning_reconcile", fake_reconcile)
    monkeypatch.setattr(workspace_runtime_planning, "_ensure_external_intent_cache_if_available", lambda **_kwargs: None)

    repo_root = Path(__file__).resolve().parents[1]
    assert (
        cli.main(["planning", "reconcile", "--apply-pending-integrations", "--dry-run", "--target", str(repo_root), "--format", "json"])
        == 0
    )

    assert json.loads(capsys.readouterr().out)["status"] == "dry-run"
    assert captured["apply_pending_integrations"] is True
    assert captured["dry_run"] is True


def test_workspace_planning_reconcile_unknown_option_reports_exact_supported_route(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["planning", "reconcile", "--not-projected"])

    assert exc_info.value.code == 2
    error = capsys.readouterr().err
    assert "unrecognized arguments: --not-projected" in error
    assert error.endswith("Supported route: agentic-workspace planning reconcile --help\n")


def test_upgrade_preserves_host_owned_ownership_subsystems(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    ownership_path = target / ".agentic-workspace" / "OWNERSHIP.toml"
    ownership_path.write_text(
        ownership_path.read_text(encoding="utf-8").rstrip() + '\n\n[[subsystems]]\nid = "api"\npaths = ["api/**"]\nowns = ["host api"]\n',
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--target", str(target), "--modules", "planning,memory", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    ownership_text = ownership_path.read_text(encoding="utf-8")
    assert 'id = "api"' in ownership_text
    assert 'paths = ["api/**"]' in ownership_text
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    ownership_action = next(action for action in workspace_report["actions"] if action["path"] == ".agentic-workspace/OWNERSHIP.toml")
    assert "host-owned subsystem overlay" in ownership_action["detail"]


def test_upgrade_refreshes_module_upgrade_source_recorded_at(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--modules", "planning", "--target", str(target), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    source_path = target / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml"
    source_path.write_text(
        re.sub(r'recorded_at = "[^"]+"', 'recorded_at = "2025-01-01"', source_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert f'recorded_at = "{date.today().isoformat()}"' in source_path.read_text(encoding="utf-8")
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    action = next(action for action in workspace_report["actions"] if action["path"] == ".agentic-workspace/planning/UPGRADE-SOURCE.toml")
    assert "recorded_at after successful upgrade" in action["detail"]


def test_upgrade_is_idempotent_for_managed_planning_skills(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json", "--non-interactive"]) == 0
    capsys.readouterr()

    assert cli.main(["upgrade", "--target", str(target), "--format", "json", "--non-interactive"]) == 0
    capsys.readouterr()
    assert cli.main(["upgrade", "--target", str(target), "--format", "json", "--non-interactive"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert cli.main(["upgrade", "--target", str(target), "--dry-run", "--format", "json", "--non-interactive"]) == 0
    dry_run = json.loads(capsys.readouterr().out)

    assert second["updated_managed"] == []
    assert dry_run["updated_managed"] == []
    planning_report = next(report for report in dry_run["reports"] if report["module"] == "planning")
    assert any(
        action["kind"] == "current" and "already matches managed planning skill" in action["detail"]
        for action in planning_report["actions"]
    )


def test_upgrade_compacts_local_scratch_preservation_in_lifecycle_plan(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    scratch_dir = target / ".agentic-workspace" / "local" / "scratch" / "run"
    scratch_dir.mkdir(parents=True)
    for index in range(12):
        (scratch_dir / f"file-{index}.txt").write_text(f"scratch {index}\n", encoding="utf-8")

    assert cli.main(["upgrade", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    classifications = payload["lifecycle_plan"]["surface_classifications"]
    local_summary = classifications["local_only_preservation"]
    assert local_summary["status"] == "present"
    assert local_summary["total_file_count"] == 12
    assert local_summary["sample_limit"] == 5
    assert local_summary["omitted_file_count"] == 7
    assert local_summary["audit_command"] == "git ls-files --others --ignored --exclude-standard -- .agentic-workspace/local"
    assert local_summary["audit_commands"][0]["id"] == "ignored-local-only-files"
    assert local_summary["cleanup_dry_run_command"] == "git clean -ndx -- .agentic-workspace/local"
    local_entries = [entry for entry in classifications["entries"] if entry["reason_class"] == "local-only preserved"]
    assert len(local_entries) == 5
    assert all(entry["source"] == "local-only-scan-sample" for entry in local_entries)
    assert not any(path.endswith("file-11.txt") for path in payload["lifecycle_plan"]["preserved_files"])


def test_upgrade_compacts_ignored_aw_local_scratch_preservation_audit_routes(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    subprocess.run(["git", "init"], cwd=target, text=True, capture_output=True, check=True)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    (target / ".gitignore").write_text(".agentic-workspace/local/\nscratch/\n", encoding="utf-8")
    local_file = target / ".agentic-workspace" / "local" / "scratch" / "ignored-local.txt"
    root_scratch_file = target / "scratch" / "ignored-root.txt"
    local_file.write_text("local\n", encoding="utf-8")
    root_scratch_file.write_text("root\n", encoding="utf-8")

    assert cli.main(["upgrade", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    local_summary = payload["lifecycle_plan"]["surface_classifications"]["local_only_preservation"]
    assert local_summary["total_file_count"] == 1
    assert set(local_summary["sample_paths"]) == {
        ".agentic-workspace/local/scratch/ignored-local.txt",
    }
    assert "scratch" not in " ".join([local_summary["audit_command"], local_summary["cleanup_dry_run_command"]])
    audit = subprocess.run(local_summary["audit_command"].split(), cwd=target, text=True, capture_output=True, check=True)
    assert ".agentic-workspace/local/scratch/ignored-local.txt" in audit.stdout
    assert "scratch/ignored-root.txt" not in audit.stdout
    cleanup = subprocess.run(local_summary["cleanup_dry_run_command"].split(), cwd=target, text=True, capture_output=True, check=True)
    assert "Would remove .agentic-workspace/local/" in cleanup.stdout
    assert "Would remove scratch/" not in cleanup.stdout


def test_closeout_trust_labels_latest_cleanup_closeout_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    archive_path = target / ".agentic-workspace" / "planning" / "execplans" / "archive" / "older.plan.json"
    closeout_path = target / ".agentic-workspace" / "planning" / "closeout-evidence" / "latest.closeout.json"
    proof_report = {
        "validation proof": "passed",
        "proof achieved now": "yes",
        'evidence for "proof achieved" state': "focused proof passed",
    }
    closure_check = {
        "slice status": "completed",
        "larger-intent status": "closed",
        "closure decision": "archive-and-close",
    }
    _write(
        archive_path,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "title": "Older Archive",
                "proof_report": proof_report,
                "closure_check": closure_check,
            }
        ),
        encoding="utf-8",
    )
    _write(
        closeout_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "title": "Latest Cleanup",
                "plan_id": "latest",
                "created_at": "2026-06-29T20:00:00+00:00",
                "source_plan": ".agentic-workspace/planning/execplans/latest.plan.json",
                "intended_archive": ".agentic-workspace/planning/execplans/archive/latest.plan.json",
                "retention": {
                    "state": "cleanup-distilled-without-full-archive",
                    "reason": "completed-plan cleanup retained compact closeout evidence instead of a full execplan archive",
                    "canonical_evidence": "retained closeout evidence",
                },
                "proof_report": proof_report,
                "closure_check": closure_check,
            }
        ),
        encoding="utf-8",
    )
    os.utime(archive_path, (1000, 1000))
    os.utime(closeout_path, (2000, 2000))

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--task", "latest", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    evidence = answer["archived_slice_closeout_evidence"]
    assert evidence["trust"] == "normal"
    assert evidence["owner_surface"] == ".agentic-workspace/planning/closeout-evidence/latest.closeout.json"
    assert evidence["owner_kind"] == "retained-closeout-evidence"
    assert evidence["evidence_relationship"] == "latest-cleaned-plan-evidence"
    assert evidence["source_plan"] == ".agentic-workspace/planning/execplans/latest.plan.json"
    assert evidence["intended_archive"] == ".agentic-workspace/planning/execplans/archive/latest.plan.json"
    assert evidence["retention_state"] == "cleanup-distilled-without-full-archive"
    assert evidence["freshness"]["sort_mtime"] == 2000


def test_closeout_trust_accepts_command_writer_compact_tombstone(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    evidence_path = ".agentic-workspace/planning/closeout-evidence/compact-writer.closeout.json"
    _write(
        target / evidence_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "title": "Compact writer tombstone",
                "plan_id": "compact-writer",
                "source_plan": ".agentic-workspace/planning/execplans/compact-writer.plan.json",
                "intended_archive": ".agentic-workspace/planning/execplans/archive/compact-writer.plan.json",
                "retention": {"state": "cleanup-distilled-without-full-archive"},
                "evidence_refs": ["sha256:fixture-proof"],
                "active_milestone": {"status": "completed"},
                "proof_report": {"validation proof": "sha256:fixture-proof"},
                "closure_check": {
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
            }
        ),
        encoding="utf-8",
    )
    _write(
        target / ".agentic-workspace/local/planning-last-closeout.json",
        json.dumps(
            {
                "status": "retained-evidence",
                "plan_id": "compact-writer",
                "evidence_path": evidence_path,
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]) == 0

    evidence = json.loads(capsys.readouterr().out)["answer"]["archived_slice_closeout_evidence"]
    assert evidence["trust"] == "normal"
    assert evidence["proof_recorded"] is True
    assert evidence["slice_completed"] is True
    assert evidence["slice_status"] == "completed"
    assert evidence["retention_state"] == "cleanup-distilled-without-full-archive"


def test_closeout_trust_authorizes_explicit_issue_refs_from_satisfied_retained_slice(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "planning",
                "lane-create",
                "--id",
                "unrelated-live-lane",
                "--title",
                "Unrelated live lane",
                "--target",
                str(target),
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    evidence_path = ".agentic-workspace/planning/closeout-evidence/issue-batch.closeout.json"
    _write(
        target / evidence_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "title": "Completed issue batch",
                "plan_id": "issue-batch",
                "source_plan": ".agentic-workspace/planning/execplans/issue-batch.plan.json",
                "intended_archive": ".agentic-workspace/planning/execplans/archive/issue-batch.plan.json",
                "retention": {"state": "cleanup-distilled-without-full-archive"},
                "outcome": "Issues #3101 and #3102 acceptance criteria are implemented and verified",
                "evidence_refs": ["sha256:fixture-proof"],
                "active_milestone": {"status": "completed"},
                "proof_report": {"validation proof": "sha256:fixture-proof"},
                "intent_satisfaction": {
                    "was original intent fully satisfied?": "yes",
                    "unsolved intent passed to": "archive",
                },
                "closure_check": {
                    "slice status": "completed",
                    "larger-intent status": "closed",
                    "closure decision": "archive-and-close",
                },
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(target),
                "--section",
                "closeout_trust",
                "--task",
                "issue-batch",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    gate = answer["completion_gate"]
    assert gate["status"] == "allowed"
    assert gate["active_intent_satisfied"] is True
    assert "issue_closure" in gate["claim_authorization"]["allowed_claim_classes"]
    assert "lane_complete" in gate["claim_authorization"]["blocked_claim_classes"]
    assert "parent_complete" in gate["claim_authorization"]["blocked_claim_classes"]
    assert gate["claim_authorization"]["closure_actions"] == [
        {
            "kind": "issue_closure",
            "target": "#3101",
            "authorized": True,
            "reason": "issue closure requires full-intent completion authorization from the completion gate",
        },
        {
            "kind": "issue_closure",
            "target": "#3102",
            "authorized": True,
            "reason": "issue closure requires full-intent completion authorization from the completion gate",
        },
    ]


def test_closeout_trust_prefers_relevant_closeout_evidence_over_newer_unrelated_record(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    relevant_path = target / ".agentic-workspace" / "planning" / "closeout-evidence" / "issue-1891.closeout.json"
    unrelated_path = target / ".agentic-workspace" / "planning" / "closeout-evidence" / "unrelated.closeout.json"
    proof_report = {
        "validation proof": "passed",
        "proof achieved now": "yes",
        'evidence for "proof achieved" state': "focused proof passed",
    }
    closure_check = {
        "slice status": "completed",
        "larger-intent status": "closed",
        "closure decision": "archive-and-close",
    }
    retained_base = {
        "kind": "planning-closeout-evidence/v1",
        "created_at": "2026-06-29T20:00:00+00:00",
        "retention": {
            "state": "cleanup-distilled-without-full-archive",
            "reason": "completed-plan cleanup retained compact closeout evidence instead of a full execplan archive",
            "canonical_evidence": "retained closeout evidence",
        },
        "proof_report": proof_report,
        "closure_check": closure_check,
    }
    _write(
        relevant_path,
        json.dumps(
            retained_base
            | {
                "title": "Relevant Issue 1891",
                "plan_id": "issue-1891",
                "source_plan": ".agentic-workspace/planning/execplans/issue-1891.plan.json",
                "intended_archive": ".agentic-workspace/planning/execplans/archive/issue-1891.plan.json",
                "lineage": {"relationship": "same-lineage", "lineage_id": "issue-1891"},
            }
        ),
        encoding="utf-8",
    )
    _write(
        unrelated_path,
        json.dumps(
            retained_base
            | {
                "title": "Unrelated Newer Work",
                "plan_id": "unrelated",
                "source_plan": ".agentic-workspace/planning/execplans/unrelated.plan.json",
                "intended_archive": ".agentic-workspace/planning/execplans/archive/unrelated.plan.json",
                "lineage": {"relationship": "unrelated", "lineage_id": "unrelated"},
            }
        ),
        encoding="utf-8",
    )
    os.utime(relevant_path, (1000, 1000))
    os.utime(unrelated_path, (2000, 2000))
    _write(
        target / ".agentic-workspace/local/planning-last-closeout.json",
        json.dumps(
            {
                "kind": "planning-last-closeout-context/v1",
                "status": "evidence-retained",
                "plan_id": "unrelated",
                "evidence_path": ".agentic-workspace/planning/closeout-evidence/unrelated.closeout.json",
                "authority": "planning-terminal-command",
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--task", "#1891", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    evidence = answer["archived_slice_closeout_evidence"]
    assert evidence["trust"] == "normal"
    assert evidence["owner_surface"] == ".agentic-workspace/planning/closeout-evidence/issue-1891.closeout.json"
    assert evidence["evidence_relationship"] == "same-lineage"
    assert evidence["relevance"]["status"] == "relevant"
    assert evidence["relevance"]["relationship"] == "same-lineage"
    assert evidence["evidence_selection"]["basis"] == "explicit-task-provenance"
    assert evidence["freshness"]["sort_mtime"] == 1000


def test_closeout_trust_prefers_retained_closeout_evidence_over_newer_archive(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    archive_path = target / ".agentic-workspace" / "planning" / "execplans" / "archive" / "newer.plan.json"
    closeout_path = target / ".agentic-workspace" / "planning" / "closeout-evidence" / "issue-2049.closeout.json"
    proof_report = {
        "validation proof": "passed",
        "proof achieved now": "yes",
        'evidence for "proof achieved" state': "focused proof passed",
    }
    closure_check = {
        "slice status": "completed",
        "larger-intent status": "closed",
        "closure decision": "archive-and-close",
    }
    _write(
        archive_path,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "title": "Newer Archived Record",
                "proof_report": proof_report,
                "closure_check": closure_check,
            }
        ),
        encoding="utf-8",
    )
    _write(
        closeout_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "title": "Issue 2049 Retained Evidence",
                "plan_id": "issue-2049",
                "source_plan": ".agentic-workspace/planning/execplans/issue-2049.plan.json",
                "intended_archive": ".agentic-workspace/planning/execplans/archive/issue-2049.plan.json",
                "retention": {"state": "cleanup-distilled-without-full-archive"},
                "proof_report": proof_report,
                "closure_check": closure_check,
            }
        ),
        encoding="utf-8",
    )
    os.utime(closeout_path, (1000, 1000))
    os.utime(archive_path, (2000, 2000))

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--task", "#2049", "--format", "json"]) == 0

    evidence = json.loads(capsys.readouterr().out)["answer"]["archived_slice_closeout_evidence"]
    assert evidence["trust"] == "normal"
    assert evidence["owner_surface"] == ".agentic-workspace/planning/closeout-evidence/issue-2049.closeout.json"
    assert evidence["owner_kind"] == "retained-closeout-evidence"
    assert evidence["evidence_source_class"] == "explicit-task-selection"
    assert evidence["evidence_selection"]["basis"] == "explicit-task-provenance"
    assert evidence["freshness"]["sort_mtime"] == 1000


@pytest.mark.parametrize("plan_id", ["2143-package-output-friction", "2166-bounded-pre-study"])
def test_closeout_trust_uses_terminal_command_context_after_active_state_is_removed(tmp_path: Path, capsys, plan_id: str) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    evidence_root = target / ".agentic-workspace/planning/closeout-evidence"
    proof = {"validation proof": "passed", "proof achieved now": "yes"}
    closure = {"slice status": "completed", "larger-intent status": "closed", "closure decision": "archive-and-close"}
    _write(
        evidence_root / "dogfood-followup-1890-1891.closeout.json",
        json.dumps(
            {"kind": "planning-closeout-evidence/v1", "plan_id": "dogfood-followup-1890-1891", "proof_report": {}, "closure_check": {}}
        ),
        encoding="utf-8",
    )
    current = evidence_root / f"{plan_id}.closeout.json"
    source_plan = f".agentic-workspace/planning/execplans/{plan_id}.plan.json"
    evidence_path = f".agentic-workspace/planning/closeout-evidence/{plan_id}.closeout.json"
    _write(
        current,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "plan_id": plan_id,
                "source_plan": source_plan,
                "proof_report": proof,
                "closure_check": closure,
            }
        ),
        encoding="utf-8",
    )
    _write(
        target / ".agentic-workspace/local/planning-last-closeout.json",
        json.dumps(
            {
                "kind": "planning-last-closeout-context/v1",
                "plan_id": plan_id,
                "source_plan": source_plan,
                "evidence_path": evidence_path,
                "authority": "planning-terminal-command",
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]) == 0
    answer = json.loads(capsys.readouterr().out)["answer"]
    evidence = answer["archived_slice_closeout_evidence"]
    assert evidence["trust"] == "normal"
    assert evidence["owner_surface"] == evidence_path
    assert evidence["evidence_selection"]["basis"] == "planning-terminal-command-context"
    assert answer["terminal_action"]["blocking"] is False


@pytest.mark.parametrize("independent_gate", ["acceptance", "intent"])
def test_closeout_trust_preserves_independent_lower_trust_gates_with_relevant_retained_evidence(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch, independent_gate: str
) -> None:
    from agentic_workspace import workspace_runtime_core as runtime_module

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    plan_id = "current-plan"
    evidence_path = f".agentic-workspace/planning/closeout-evidence/{plan_id}.closeout.json"
    _write(
        target / evidence_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "plan_id": plan_id,
                "proof_report": {"validation proof": "passed", "proof achieved now": "yes"},
                "closure_check": {
                    "slice status": "completed",
                    "larger-intent status": "closed",
                    "closure decision": "archive-and-close",
                },
            }
        ),
        encoding="utf-8",
    )
    _write(
        target / ".agentic-workspace/local/planning-last-closeout.json",
        json.dumps(
            {
                "kind": "planning-last-closeout-context/v1",
                "status": "evidence-retained",
                "plan_id": plan_id,
                "evidence_path": evidence_path,
                "authority": "planning-terminal-command",
            }
        ),
        encoding="utf-8",
    )
    if independent_gate == "acceptance":
        monkeypatch.setattr(
            runtime_module,
            "_acceptance_criteria_reconciliation_payload",
            lambda **_: {"status": "needs-review", "trust": "lower-trust"},
        )
    else:
        monkeypatch.setattr(
            runtime_module,
            "_intent_satisfaction_check_payload",
            lambda **_: {"status": "follow-up-required", "trust": "follow-up-required"},
        )

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]) == 0
    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["archived_slice_closeout_evidence"]["trust"] == "normal"
    assert answer["trust"] == "lower-trust"
    assert answer["terminal_action"]["blocking"] is True


def test_planning_completion_gate_requires_carried_decision_point_confirmation() -> None:
    from repo_planning_bootstrap.installer import _planning_completion_gate_payload

    record = {
        "required_continuation": {"required follow-on for the larger intended outcome": "no"},
        "intent_continuity": {"continuation surface": "none"},
    }
    base_patch = {
        "intent_satisfaction": {"was original intent fully satisfied?": "yes", "unsolved intent passed to": "none"},
        "closure_check": {"closure decision": "archive-and-close", "larger-intent status": "closed"},
        "proof_report": {"validation proof": "focused proof passed"},
    }
    blocked = _planning_completion_gate_payload(
        record=record,
        patch={**base_patch, "decision_point_intent_confirmation": {"status": "unresolved"}},
    )
    assert blocked["status"] == "clarification-required"
    assert "issue_closure" in blocked["claim_authorization"]["blocked_claim_classes"]

    confirmed_patch = {
        **base_patch,
        "decision_point_intent_confirmation": {
            "status": "corrected",
            "forecast_digest": "forecast-1",
            "implementation_confirmation": {"forecast_digest": "forecast-1"},
            "proof_confirmation": {"forecast_digest": "forecast-1"},
        },
    }
    allowed = _planning_completion_gate_payload(record=record, patch=confirmed_patch)
    assert allowed["status"] == "allowed"


def test_closeout_trust_reports_bounded_ambiguity_for_multiple_task_matches(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    root = target / ".agentic-workspace/planning/closeout-evidence"
    for suffix in ("a", "b"):
        _write(
            root / f"issue-2166-{suffix}.closeout.json",
            json.dumps(
                {"kind": "planning-closeout-evidence/v1", "plan_id": f"issue-2166-{suffix}", "proof_report": {"validation proof": "passed"}}
            ),
            encoding="utf-8",
        )

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--task", "#2166", "--format", "json"]) == 0
    answer = json.loads(capsys.readouterr().out)["answer"]
    resolution = answer["archived_slice_closeout_evidence"]
    assert resolution["status"] == "ambiguous"
    assert resolution["trust"] == "not-applicable"
    assert len(resolution["candidates"]) == 2
    assert "--task" in resolution["recovery_command"]
    assert answer["trust"] == "normal"
    assert answer["terminal_action"]["blocking"] is False


def test_closeout_trust_does_not_turn_unrelated_history_into_a_blocker(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace/planning/closeout-evidence/unrelated.closeout.json",
        json.dumps({"kind": "planning-closeout-evidence/v1", "plan_id": "unrelated", "proof_report": {}}),
        encoding="utf-8",
    )
    _write(
        target / ".agentic-workspace/local/planning-last-closeout.json",
        json.dumps(
            {
                "kind": "planning-last-closeout-context/v1",
                "status": "no-retained-evidence",
                "plan_id": "current-without-evidence",
                "evidence_path": "",
                "authority": "planning-terminal-command",
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]) == 0
    answer = json.loads(capsys.readouterr().out)["answer"]
    resolution = answer["archived_slice_closeout_evidence"]
    assert resolution["status"] == "no-relevant-evidence"
    assert resolution["trust"] == "not-applicable"
    assert resolution["candidates"] == []
    assert resolution["selected_plan_id"] == "current-without-evidence"
    assert answer["trust"] == "normal"
    assert answer["terminal_action"]["blocking"] is False
    assert answer["completion_gate"]["continuation"]["created_or_required"] is False
    assert answer["terminal_action"]["recommended_next_action"] != "Create a follow-on planning item before closure."


def _write_issue_1981_closeout_fixture(
    target: Path,
    *,
    include_proof: bool,
    external_status: str = "closed",
    include_stale_task_posture_residue: bool = False,
    active_milestone_status: str = "active",
    terminal_phase: bool = False,
) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    issue_ref = "#1981"
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "issue-1981", title = "Issue 1981 state-delta shared core", status = "active", surface = ".agentic-workspace/planning/execplans/issue-1981.plan.json", next_action = "Close complete.", done_when = "Issue 1981 can honestly be closed." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Issue 1981 state-delta shared core",
        item_id="issue-1981",
        status="active",
        why_now="regress closeout trust alignment.",
        next_action="Close complete.",
        done_when="Issue 1981 can honestly be closed.",
    )
    record["references"] = [issue_ref]
    record["completion_criteria"] = ["summary and closeout trust agree on active execplan intent satisfaction"]
    record["active_milestone"] = {
        "id": "issue-1981",
        "status": active_milestone_status,
        "scope": "Keep this execution thread bounded to the promoted TODO item.",
        "ready": "ready",
        "blocked": "none",
    }
    if terminal_phase:
        record["phase"] = "complete"
    if include_stale_task_posture_residue:
        record["active_milestone"]["id"] = "task-posture-fixture"
    record["proof_expectations"] = [
        "uv run python scripts/run_agentic_workspace.py summary --target . --format json",
        "uv run python scripts/run_agentic_workspace.py report --target . --section closeout_trust --format json",
        "uv run pytest tests/test_workspace_cli.py -q",
    ]
    record["execution_run"] = {
        "handoff source": "synthetic regression fixture",
        "what happened": "The shared state-delta core was implemented.",
        "validations run": [
            "agentic-workspace summary passed",
            "agentic-workspace report --section closeout_trust passed",
            "pytest passed",
        ],
    }
    record["execution_summary"] = {
        "outcome delivered": "The shared state-delta core was implemented.",
        "validation confirmed": "agentic-workspace summary, closeout_trust, and pytest passed",
        "follow-on routed to": "none",
        "post-work posterity capture": "none",
        "knowledge promoted (Memory/Docs/Config)": "none",
        "resume from": "archive",
    }
    if include_proof:
        record["proof_report"] = {
            "validation proof": "uv run pytest tests/test_workspace_cli.py -q passed",
            "proof achieved now": "yes, proof passed for the requested behavior",
            'evidence for "proof achieved" state': "summary and closeout trust fixture covered the shared core closeout.",
        }
    else:
        record["proof_report"] = {}
    record["intent_satisfaction"] = {
        "original intent": "Implement #1981 by making state-delta packet views derive from one shared compact core.",
        "was original intent fully satisfied?": "yes",
        "evidence of intent satisfaction": "Summary payloads and closeout trust agree the requested behavior is complete.",
        "unsolved intent passed to": "none",
    }
    record["intent_continuity"] = {
        "larger intended outcome": "Implement #1981 by making state-delta packet views derive from one shared compact core.",
        "this slice completes the larger intended outcome": "yes",
        "continuation surface": "none",
    }
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "no",
        "owner surface": "none",
    }
    record["closure_check"] = {
        "slice status": "complete",
        "larger-intent status": "closed",
        "closure decision": "archive-and-close-after-pr-merge",
        "why this decision is honest": "#1981 acceptance criteria are satisfied by the fixture proof.",
        "evidence carried forward": "summary, closeout_trust, and pytest proof",
        "reopen trigger": "closeout_trust stops accepting active execplan closeout evidence",
    }
    record["durable_residue"] = {
        "status": "none",
        "learned constraint": "No reusable product constraint in this synthetic fixture.",
        "motivation worth preserving": "Only the closeout trust alignment behavior matters.",
        "canonical owner now": "none",
        "promotion trigger": "none",
        "retention after promotion": "retain",
    }
    planning_installer._write_execplan_record(
        record_path=target / ".agentic-workspace" / "planning" / "execplans" / "issue-1981.plan.json",
        record=record,
    )
    owner_ref = ".agentic-workspace/planning/execplans/issue-1981.plan.json"
    _write_json(
        target / ".agentic-workspace" / "local" / "planning" / "owner-selection.json",
        {
            "kind": "agentic-planning/owner-selection/v1",
            "mode": "local",
            "current_work_id": "default",
            "selected_owner": {"id": "issue-1981", "ref": owner_ref},
            "planning_revision": cli._planning_owner_selection_basis_revision(target_root=target, state_data={}),
        },
    )
    if include_stale_task_posture_residue:
        _write_json(
            target / ".agentic-workspace" / "planning" / "lanes" / "lane-1392-open-module-participation.lane.json",
            {
                "kind": "planning-lane/v1",
                "id": "lane-1392-open-module-participation",
                "slice_sequence": [
                    {
                        "id": "state-delta-packet-followthrough",
                        "title": "Task posture packet follow-through",
                        "status": "planned",
                        "purpose_for_lane": "Historical packet follow-through residue retained after the active slice completed.",
                    }
                ],
            },
        )
    _write_json(
        target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "refreshed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "items": [
                {
                    "system": "fixture",
                    "id": issue_ref,
                    "title": "Issue 1981 state-delta shared core",
                    "status": external_status,
                    "kind": "issue",
                },
            ],
        },
    )


def test_closeout_trust_derives_intent_proof_from_satisfied_active_execplan(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=True, active_milestone_status="completed")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "closeout_trust", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]

    assert payload["completion_gate"]["status"] == "allowed"
    assert payload["completion_gate"]["active_intent_satisfied"] is True
    assert payload["completion_gate"]["claim_level_allowed"] == "full-intent-complete"
    assert payload["checks"]["intent_proof"]["status"] == "sufficient_for_claim"
    claim_work = next(option for option in payload["completion_options"] if option["id"] == "claim-work-complete")
    assert claim_work["allowed"] is True
    assert "durable_residue" not in claim_work.get("blocking_fields", [])
    assert "planning.active.planning_record.proof_report.intent_proof.status" not in claim_work.get("blocking_fields", [])


def test_closeout_claim_boundary_returns_fast_claim_packet(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    import tests.workspace_cli_support as workspace_cli_support

    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=True, include_stale_task_posture_residue=True)

    def fail_full_closeout_trust(**_: Any) -> dict[str, Any]:
        raise AssertionError("closeout_claim_boundary must not build full closeout_trust")

    for runtime_module in (
        workspace_runtime_core,
        workspace_runtime_primitives,
        workspace_cli_support._generated_cli,
    ):
        if hasattr(runtime_module, "_report_closeout_trust_payload"):
            monkeypatch.setattr(runtime_module, "_report_closeout_trust_payload", fail_full_closeout_trust)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "closeout_claim_boundary", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]

    assert payload["kind"] == "agentic-workspace/closeout-claim-boundary/v1"
    assert payload["status"] == "allowed"
    assert payload["active_intent_satisfied"] is True
    assert payload["claim_level_allowed"] == "full-intent-complete"
    assert "full_intent_complete" in payload["claim_authorization"]["allowed_claim_classes"]
    assert payload["blocking_fields"] == []
    assert payload["residue_routing"]["required"] is False
    assert payload["proof_dependency"]["status"] == "satisfied"
    assert payload["proof_dependency"]["proof_status"] == "sufficient_for_claim"
    assert payload["proof_dependency"]["claim_boundary"] == "full-intent"
    terminal = payload["terminal_outcome_contract"]
    assert terminal["state"] == "DELIVERED"
    assert terminal["final_response_authorized"] is True
    assert terminal["safe_continuation_available"] is False
    assert payload["source_surface"] == "closeout_claim_boundary.direct"
    assert payload["computation"]["avoids_full_closeout_trust"] is True
    assert "--section closeout_trust" in payload["source_detail_command"]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "section_catalog", "--format", "json"]) == 0
    catalog = json.loads(capsys.readouterr().out)["answer"]
    section = next(item for item in catalog["lazy_sections"] if item["section"] == "closeout_claim_boundary")
    assert section["payload_is_lazy"] is True
    expected_target = Path(os.path.relpath(tmp_path.resolve(), Path.cwd().resolve())).as_posix()
    assert f"--target {expected_target} " in section["command"]


def test_closeout_trust_default_is_budgeted_before_optional_hydration(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=True, active_milestone_status="completed")

    def fail_optional_builder(**_: Any) -> dict[str, Any]:
        raise AssertionError("compact closeout_trust must not hydrate optional detail")

    for name in (
        "_knowledge_authority_review_payload",
        "_architecture_decision_closeout_payload",
        "_closeout_report_final_response_rendering_payload",
        "_memory_consult_payload",
        "_memory_decision_packet_payload",
        "_historical_review_artifacts_policy",
        "_closeout_protocol_payload",
    ):
        monkeypatch.setattr(workspace_runtime_core, name, fail_optional_builder)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "closeout_trust", "--format", "json"]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)["answer"]

    assert len(output.encode("utf-8")) < 65_536
    assert payload["completion_gate"]["status"] == "allowed"
    assert payload["terminal_outcome_contract"]["state"] == "DELIVERED"
    assert payload["computation"]["profile"] == "compact"
    assert payload["computation"]["optional_builders_avoided"] is True
    assert payload["knowledge_authority_review"]["status"] == "omitted"
    assert payload["closeout_protocol"]["selectors"] == ["closeout_trust --verbose", "closeout_report"]
    enforcement = payload["terminal_outcome_contract"]["final_response_enforcement"]
    assert enforcement["detail"]["omitted_fields"] == [
        "issue_2239_closure_evidence",
        "integrated_host_boundaries",
    ]


def test_closeout_trust_does_not_block_on_stale_satisfied_task_posture_residue(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=True, include_stale_task_posture_residue=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "closeout_trust", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]

    assert payload["completion_gate"]["status"] == "allowed"
    assert payload["completion_gate"]["active_intent_satisfied"] is True
    assert payload["completion_gate"]["task_posture_followthrough"]["status"] == "stale-satisfied"
    assert payload["completion_gate"]["task_posture_followthrough"]["blocking"] is False
    claim_work = next(option for option in payload["completion_options"] if option["id"] == "claim-work-complete")
    assert "completion_gate" not in claim_work.get("blocking_fields", [])


def test_closeout_trust_blocks_full_closeout_when_active_execplan_proof_is_missing(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=False)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "closeout_trust", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]

    assert payload["completion_gate"]["status"] in {"blocked", "continue-required"}
    assert payload["completion_gate"]["active_intent_satisfied"] is False
    terminal = payload["terminal_outcome_contract"]
    assert terminal["state"] == "CONTINUE"
    assert terminal["final_response_authorized"] is False
    assert "run-proof" in terminal["safe_continuation_option_ids"]
    enforcement = terminal["final_response_enforcement"]
    assert enforcement["status"] == "rejected_auto_resume"
    assert enforcement["terminal_final_rejected"] is True
    assert enforcement["progress_without_yield"] is True
    assert enforcement["multi_slice_continuation"]["status"] == "preserved"
    assert payload["checks"]["intent_proof"]["status"] == "not_recorded"
    claim_work = next(option for option in payload["completion_options"] if option["id"] == "claim-work-complete")
    assert claim_work["allowed"] is False
    assert "planning.active.planning_record.proof_report.intent_proof.status" in claim_work["blocking_fields"]
    assert "intent_proof" not in claim_work["blocking_fields"]
    rendering = payload["final_response_rendering"]
    assert rendering["status"] == "continue-not-finalizable"
    assert rendering["terminal_state"] == "CONTINUE"
    assert rendering["final_response_authorized"] is False
    assert rendering["selectors"] == ["closeout_trust --verbose", "closeout_report"]
    assert enforcement["host_boundary_integrated"] is True
    assert enforcement["ordinary_host_path_unavoidable"] is True
    assert enforcement["issue_2239_closure_ready"] is True
    assert enforcement["detail"]["status"] == "omitted"


def test_final_response_admit_rejects_final_runs_continuation_and_persists_resume_slices(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=False)

    command = [
        "final-response",
        "admit",
        "--target",
        str(tmp_path),
        "--attempt",
        "Done.",
        "--after-compaction",
        "--format",
        "json",
    ]
    assert cli.main(command) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["kind"] == "agentic-workspace/final-response-admission-result/v1"
    assert first["status"] == "rejected_auto_resumed"
    assert first["admission"]["terminal_final_rejected"] is True
    assert first["admission"]["resume_transition"]["status"] == "executed"
    assert first["continuation_operation"]["status"] == "executed"
    assert first["continuation_operation"]["invoked_operation"] == "proof.report"
    assert first["continuation_operation"]["exit_code"] == 0
    assert first["checkpoint_before"]["slice_count"] == 0
    assert first["checkpoint_after"]["slice_count"] == 1

    assert cli.main(command) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["checkpoint_before"]["slice_count"] == 1
    assert second["checkpoint_after"]["slice_count"] == 2

    checkpoint = json.loads((tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json").read_text())
    admission_checkpoint = checkpoint["final_response_admission"]
    assert admission_checkpoint["slice_count"] == 2
    assert len(admission_checkpoint["slices"]) == 2
    assert {item["continuation_operation"] for item in admission_checkpoint["slices"]} == {"proof.report"}
    assert admission_checkpoint["not_closure_evidence"] is True


def test_final_response_admit_accepts_only_authorized_bounded_report_during_continue(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    terminal = {
        "kind": "agentic-workspace/terminal-outcome-contract/v1",
        "state": "CONTINUE",
        "final_response_authorized": False,
        "allowed_claim_classes": ["partial_progress", "slice_complete"],
        "bounded_claim_authorizations": [
            {
                "id": "test-closeout:slice_complete",
                "claim_class": "slice_complete",
                "scope_kind": "slice",
                "source": "completion_gate.claim_authorization",
                "report": {
                    "kind": "agentic-workspace/bounded-progress-report/v1",
                    "scope_id": "test-closeout:slice_complete",
                    "claim_class": "slice_complete",
                    "scope_kind": "slice",
                    "scope_status": "complete",
                    "larger_intent": {"status": "open", "completion_authorized": False},
                    "continuation": {"owner": "#2371", "required_next_action": "continue-parent-lane"},
                    "residue": {"status": "routed", "owner": "#2371"},
                },
            }
        ],
        "required_next_action": "continue-parent-lane",
        "safe_continuation_option_ids": ["continue-parent-lane"],
        "blocker_qualification": {"status": "not_required"},
        "final_response_enforcement": {
            "status": "rejected_auto_resume",
            "terminal_final_rejected": True,
            "auto_resume_action": "continue-parent-lane",
            "progress_without_yield": True,
            "multi_slice_continuation": {"status": "preserved"},
        },
    }

    monkeypatch.setattr(
        cli, "_final_response_closeout_trust_for_admission", lambda *, target_root: ({"terminal_outcome_contract": terminal}, object())
    )

    def fail_continuation(**_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("an authorized bounded report must not invoke continuation")

    monkeypatch.setattr(cli, "_run_final_response_continuation_operation", fail_continuation)
    assert (
        cli.main(
            [
                "final-response",
                "admit",
                "--target",
                str(tmp_path),
                "--attempt",
                "Upgrade slice complete; package follow-up remains owned by #2371.",
                "--claim-class",
                "slice-complete",
                "--claim-scope-id",
                "test-closeout:slice_complete",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "accepted_bounded_report"
    assert payload["admission"]["bounded_report_authorized"] is True
    assert payload["admission"]["terminal_final_rejected"] is True
    assert payload["admission"]["attempt"]["claim_class"] == "slice_complete"
    assert payload["admission"]["attempt"]["claim_scope_id"] == "test-closeout:slice_complete"
    assert payload["admission"]["attempt"]["model_authored_text_admission"]["admitted"] is False
    assert payload["admission"]["authoritative_response"]["scope_id"] == "test-closeout:slice_complete"
    assert payload["admission"]["authoritative_response"]["larger_intent"]["completion_authorized"] is False
    assert payload["continuation_operation"]["status"] == "not_required"
    assert payload["terminal_outcome_contract"]["final_response_authorized"] is False


@pytest.mark.parametrize(
    ("claim_class", "scope_id", "claim", "expected_status"),
    [
        ("partial_progress", "test-closeout:partial_progress", "Progress recorded; proof remains.", "accepted_bounded_report"),
        ("slice_complete", "test-closeout:slice_complete", "Upgrade slice complete; parent remains open.", "accepted_bounded_report"),
        ("slice_complete", "test-closeout:slice_complete", "Nothing remains and the parent work is concluded.", "accepted_bounded_report"),
        ("slice_complete", "test-closeout:slice_complete", "The whole objective has reached its endpoint.", "accepted_bounded_report"),
        ("slice_complete", "test-closeout:slice_complete", "No further effort is necessary anywhere.", "accepted_bounded_report"),
        ("terminal_final", "", "Done.", "rejected_auto_resumed"),
    ],
)
def test_final_response_admit_requires_trusted_bounded_scope_and_quarantines_model_prose(
    tmp_path: Path,
    capsys,
    monkeypatch,
    claim_class: str,
    scope_id: str,
    claim: str,
    expected_status: str,
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    terminal = {
        "kind": "agentic-workspace/terminal-outcome-contract/v1",
        "state": "CONTINUE",
        "final_response_authorized": False,
        "allowed_claim_classes": ["partial_progress", "slice_complete"],
        "bounded_claim_authorizations": [
            {
                "id": "test-closeout:partial_progress",
                "claim_class": "partial_progress",
                "scope_kind": "progress",
                "report": {
                    "kind": "agentic-workspace/bounded-progress-report/v1",
                    "scope_id": "test-closeout:partial_progress",
                    "claim_class": "partial_progress",
                    "scope_kind": "progress",
                    "scope_status": "progress-recorded",
                    "larger_intent": {"status": "open", "completion_authorized": False},
                    "continuation": {"owner": "planning", "required_next_action": "continue-parent-lane"},
                    "residue": {"status": "routed", "owner": "planning"},
                },
            },
            {
                "id": "test-closeout:slice_complete",
                "claim_class": "slice_complete",
                "scope_kind": "slice",
                "report": {
                    "kind": "agentic-workspace/bounded-progress-report/v1",
                    "scope_id": "test-closeout:slice_complete",
                    "claim_class": "slice_complete",
                    "scope_kind": "slice",
                    "scope_status": "complete",
                    "larger_intent": {"status": "open", "completion_authorized": False},
                    "continuation": {"owner": "planning", "required_next_action": "continue-parent-lane"},
                    "residue": {"status": "routed", "owner": "planning"},
                },
            },
        ],
        "required_next_action": "continue-parent-lane",
        "safe_continuation_option_ids": ["continue-parent-lane"],
        "blocker_qualification": {"status": "not_required"},
        "final_response_enforcement": {
            "status": "rejected_auto_resume",
            "terminal_final_rejected": True,
            "auto_resume_action": "continue-parent-lane",
            "progress_without_yield": True,
            "multi_slice_continuation": {"status": "preserved"},
        },
    }
    monkeypatch.setattr(
        cli, "_final_response_closeout_trust_for_admission", lambda *, target_root: ({"terminal_outcome_contract": terminal}, object())
    )
    monkeypatch.setattr(
        cli,
        "_run_final_response_continuation_operation",
        lambda **_kwargs: {
            "kind": "agentic-workspace/final-response-resume-result/v1",
            "status": "executed",
            "invoked_operation": "proof.report",
            "exit_code": 0,
            "command": "agentic-workspace proof --target . --format json",
        },
    )

    command = [
        "final-response",
        "admit",
        "--target",
        str(tmp_path),
        "--attempt",
        claim,
        "--claim-class",
        claim_class.replace("_", "-"),
        "--format",
        "json",
    ]
    if scope_id:
        command[command.index("--format") : command.index("--format")] = ["--claim-scope-id", scope_id]
    assert cli.main(command) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == expected_status
    if expected_status == "accepted_bounded_report":
        assert payload["admission"]["attempt"]["model_authored_text_admission"] == {
            "status": "not-authoritative-decoration",
            "admitted": False,
            "rule": (
                "During CONTINUE, caller/model prose is never the admitted bounded artifact; the host emits only the "
                "closeout-owned structured report."
            ),
        }
        assert payload["admission"]["authoritative_response"]["claim_class"] == claim_class
        assert payload["admission"]["authoritative_response"]["larger_intent"]["completion_authorized"] is False


def test_final_response_admit_executor_command_reenters_until_delivered(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()

    contracts = [
        {
            "kind": "agentic-workspace/terminal-outcome-contract/v1",
            "state": "CONTINUE",
            "final_response_authorized": False,
            "required_next_action": "continue-current-work",
            "safe_continuation_option_ids": ["run-proof"],
            "blocker_qualification": {"status": "not_required"},
            "final_response_enforcement": {
                "status": "rejected_auto_resume",
                "terminal_final_rejected": True,
                "auto_resume_action": "continue-current-work",
                "progress_without_yield": True,
                "multi_slice_continuation": {"status": "preserved"},
            },
        },
        {
            "kind": "agentic-workspace/terminal-outcome-contract/v1",
            "state": "DELIVERED",
            "final_response_authorized": True,
            "required_next_action": "",
            "safe_continuation_option_ids": [],
            "blocker_qualification": {"status": "not_required"},
            "final_response_enforcement": {
                "status": "authorized",
                "terminal_final_rejected": False,
                "multi_slice_continuation": {"status": "not_required"},
            },
        },
    ]

    def fake_closeout_trust(*, target_root: Path) -> tuple[dict[str, Any], object]:
        assert target_root == tmp_path.resolve()
        return {"terminal_outcome_contract": contracts.pop(0)}, object()

    def fake_continuation(*, target_root: Path, terminal_outcome_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        assert target_root == tmp_path.resolve()
        assert terminal_outcome_contract["state"] == "CONTINUE"
        assert request["terminal_final_rejected"] is True
        return {
            "kind": "agentic-workspace/final-response-resume-result/v1",
            "status": "executed",
            "invoked_operation": "proof.report",
            "invoked_action": "continue-current-work",
            "command": "agentic-workspace proof --target . --format json",
            "exit_code": 0,
            "custody": "agent",
            "after_state_patch": {
                "required_next_action": "continue-current-work",
                "custody_owner": "agent",
                "continuation_slice": "post-admission-resume",
            },
        }

    monkeypatch.setattr(cli, "_final_response_closeout_trust_for_admission", fake_closeout_trust)
    monkeypatch.setattr(cli, "_run_final_response_continuation_operation", fake_continuation)

    attempt_log = tmp_path / "attempts.log"
    monkeypatch.setenv("ATTEMPT_LOG", str(attempt_log))
    executor_script = tmp_path / "emit_final_attempt.py"
    executor_script.write_text(
        """
import os
from pathlib import Path

slice_no = os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_SLICE"]
assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_CUSTODY"] == "agent"
log = Path(os.environ["ATTEMPT_LOG"])
log.write_text((log.read_text() if log.exists() else "") + slice_no + "\\n")
if slice_no == "1":
    print("Done too early.")
elif int(slice_no) > 3:
    raise SystemExit("autopilot admission did not observe the executor's delivered repository state")
else:
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_PREVIOUS_ADMISSION"]
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_CONTINUATION"]
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_CONTINUATION_STATE"]
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_ACTIVE_OBJECTIVE"] == "continue-current-work"
    print("Actually delivered.")
""".strip(),
        encoding="utf-8",
    )

    command = [
        "final-response",
        "admit",
        "--target",
        str(tmp_path),
        "--executor-command",
        subprocess.list2cmdline([sys.executable, str(executor_script)]),
        "--format",
        "json",
    ]
    assert cli.main(command) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "accepted_terminal_final"
    loop = payload["ordinary_execution_loop"]
    assert loop["vendor_neutral"] is True
    assert loop["depends_on_codex_goal_mode"] is False
    assert loop["depends_on_model_cli_harness"] is False
    assert "AGENTIC_WORKSPACE_FINAL_RESPONSE_ACTIVE_OBJECTIVE" in loop["preserved_state_fields"]
    assert loop["slice_count"] == 2
    assert loop["slices"][0]["admission_status"] == "rejected_auto_resumed"
    assert loop["slices"][1]["admission_status"] == "accepted_terminal_final"
    assert payload["admission"]["attempt"]["claim"] == "Actually delivered."
    assert attempt_log.read_text(encoding="utf-8").splitlines() == ["1", "2"]
    checkpoint = json.loads((tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json").read_text())
    admission_checkpoint = checkpoint["final_response_admission"]
    assert admission_checkpoint["slice_count"] == 2
    assert admission_checkpoint["slices"][0]["ordinary_execution_slice"] == 1
    assert admission_checkpoint["slices"][1]["ordinary_execution_slice"] == 2


def test_autopilot_ordinary_route_admits_executor_and_real_repo_state_transition(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=False)

    def fake_continuation(*, target_root: Path, terminal_outcome_contract: dict, request: dict) -> dict:
        assert target_root == tmp_path
        assert terminal_outcome_contract["state"] == "CONTINUE"
        return {
            "kind": "agentic-workspace/final-response-resume-result/v1",
            "status": "executed",
            "invoked_action": request["auto_resume_action"],
            "invoked_operation": "proof.report",
            "command": "proof --target <fixture> --format json",
            "exit_code": 0,
            "custody": "agent",
            "after_state_patch": {
                "required_next_action": request["auto_resume_action"],
                "custody_owner": "agent",
                "continuation_operation": "proof.report",
                "continuation_exit_code": 0,
            },
        }

    monkeypatch.setattr(cli, "_run_final_response_continuation_operation", fake_continuation)

    def dynamic_autopilot_context(**_: Any) -> dict[str, Any]:
        return _autopilot_authoritative_context_fixture(
            target_root=tmp_path,
            proof={
                "status": "accepted",
                "receipt_status": "fresh",
                "proof_subject_fingerprint": "proof-owner-a",
                "commands": ["make proof-owner-a"],
            },
        )

    monkeypatch.setattr(cli, "resolve_current_work_context", dynamic_autopilot_context)
    monkeypatch.setattr(cli, "_proof_receipt_reconciliation_payload", lambda **_: _accepted_autopilot_proof_reconciliation())
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    attempt_log = tmp_path / "attempts.log"
    monkeypatch.setenv("ATTEMPT_LOG", str(attempt_log))
    assignment_dir = tmp_path / ".agentic-workspace" / "planning" / "assignments"
    assignment_dir.mkdir(parents=True, exist_ok=True)
    (assignment_dir / "issue-1981.assignment.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/planning-assignment/v1",
                "assignment_id": "assign-1981",
                "current_revision": "assign-rev-1981",
                "status": "current",
                "target_name": "local-codex",
                "assignment_gate": {
                    "role": "implementer",
                    "selected_target": "local-codex",
                    "allowed_effects": ["repo-write"],
                    "allowed_paths": [".agentic-workspace/planning/execplans/issue-1981.plan.json"],
                    "proof_obligation": {"id": "proof:issue-1981", "revision": "proof-owner-a"},
                    "stop_conditions": ["scope-expanded", "proof-stale"],
                    "mutation_baseline": "baseline-issue-1981",
                },
                "delegation_decision": {"delegation_next_step": {"handoff_run_id": "run-1981", "return_schema": "delegated-return/v1"}},
                "current_attempt": {"run_id": "run-1981", "owner": "local-codex", "status": "handoff-prepared"},
            }
        ),
        encoding="utf-8",
    )
    executor_script = tmp_path / "autopilot_executor.py"
    executor_script.write_text(
        """
import json
import os
from pathlib import Path

slice_no = os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_SLICE"]
assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_CUSTODY"] == "agent"
kernel = json.loads(os.environ["AGENTIC_WORKSPACE_DELEGATED_WORKER_KERNEL"])
assert kernel["status"] == "assignment-bound"
assert kernel["assignment"]["assignment_id"] == "assign-1981"
assert kernel["assignment"]["run_id"] == "run-1981"
assert kernel["scope"]["allowed_paths"] == [".agentic-workspace/planning/execplans/issue-1981.plan.json"]
assert kernel["admission"]["return_schema"] == "delegated-return/v1"
log = Path(os.environ["ATTEMPT_LOG"])
log.write_text((log.read_text() if log.exists() else "") + slice_no + "\\n")
plan_path = Path(".agentic-workspace/planning/execplans/issue-1981.plan.json")
if slice_no == "1":
    print("Done too early.")
elif int(slice_no) > 3:
    raise SystemExit("autopilot admission did not observe the executor's delivered repository state")
else:
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_PREVIOUS_ADMISSION"]
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_CONTINUATION_STATE"]
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["proof_report"] = {
        "validation proof": "autopilot executor wrote real repo proof",
        "proof achieved now": "yes, proof passed for the requested behavior",
        "evidence for \\"proof achieved\\" state": "autopilot route mutated the active execplan before final admission.",
    }
    record["active_milestone"]["status"] = "completed"
    plan_path.write_text(json.dumps(record, indent=2) + "\\n", encoding="utf-8")
print("Actually delivered.")
""".strip(),
        encoding="utf-8",
    )
    registry = json.loads((tmp_path / ".agentic-workspace/planning/skills/REGISTRY.json").read_text(encoding="utf-8"))
    autopilot_skill = next(entry for entry in registry["skills"] if entry["id"] == "planning-autopilot")
    host_entrypoint = autopilot_skill["host_entrypoint"]
    assert host_entrypoint["operation_id"] == "autopilot.run"
    assert host_entrypoint["required"] is True
    assert host_entrypoint["ordinary_path_unavoidable"] is True
    command = [
        (
            str(value)
            .replace("{target}", str(tmp_path))
            .replace("{executor_command}", subprocess.list2cmdline([sys.executable, str(executor_script)]))
        )
        for value in host_entrypoint["argv_template"]
    ]

    assert cli.main(command) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/final-response-admission-result/v1"
    assert payload["status"] == "accepted_terminal_final"
    assert payload["ordinary_autopilot_route"]["status"] == "entered"
    assert payload["ordinary_autopilot_route"]["ordinary_host_path_unavoidable"] is True
    assert payload["ordinary_autopilot_route"]["depends_on_codex_goal_mode"] is False
    assert payload["ordinary_autopilot_route"]["depends_on_model_cli_harness"] is False
    assert payload["delegated_worker_kernel"]["status"] == "assignment-bound"
    assert payload["delegated_worker_kernel"]["route_consumers"]["implement"].startswith("must keep mutations within assignment")
    loop = payload["ordinary_execution_loop"]
    assert loop["slice_count"] == 2
    assert loop["slices"][0]["admission_status"] == "rejected_auto_resumed"
    assert loop["slices"][1]["admission_status"] == "accepted_terminal_final"
    assert payload["admission"]["attempt"]["claim"] == "Actually delivered."
    assert attempt_log.read_text(encoding="utf-8").splitlines() == ["1", "2"]
    record = json.loads((tmp_path / ".agentic-workspace/planning/execplans/issue-1981.plan.json").read_text())
    assert record["proof_report"]["validation proof"] == "autopilot executor wrote real repo proof"


def test_delegated_worker_kernel_blocks_stale_assignment_and_preserves_direct_work(tmp_path: Path) -> None:
    direct_kernel = cli._delegated_worker_kernel_payload(target_root=tmp_path)
    assert direct_kernel["status"] == "direct-compatible"
    assert direct_kernel["assignment"]["state"] == "not-applicable"

    assignment_dir = tmp_path / ".agentic-workspace" / "planning" / "assignments"
    assignment_dir.mkdir(parents=True)
    (assignment_dir / "stale.assignment.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/planning-assignment/v1",
                "assignment_id": "assign-stale",
                "current_revision": "assign-rev-stale",
                "status": "current",
                "target_name": "worker",
                "assignment_gate": {
                    "role": "implementer",
                    "selected_target": "worker",
                    "allowed_effects": ["repo-write"],
                    "allowed_paths": ["src/feature.py"],
                    "proof_obligation": {"id": "proof:feature", "revision": "proof-rev-1"},
                    "stop_conditions": ["scope-expanded"],
                    "mutation_baseline": "baseline-1",
                },
                "delegation_decision": {"delegation_next_step": {"handoff_run_id": "run-stale", "return_schema": "delegated-return/v1"}},
                "current_attempt": {"run_id": "run-stale", "owner": "worker", "status": "integrated"},
            }
        ),
        encoding="utf-8",
    )

    stale_kernel = cli._delegated_worker_kernel_payload(target_root=tmp_path)
    assert stale_kernel["status"] == "blocked-stale-assignment"
    assert stale_kernel["admission"]["status"] == "blocked"
    assert stale_kernel["admission"]["reason_code"] == "stale-or-terminal-assignment"
    assert stale_kernel["route_consumers"]["skills"].startswith("must bind assignment skills")


def _autopilot_executor_binding_fixture(*, owner: str, slice_number: int, target_root: Path) -> dict[str, Any]:
    binding = {
        "kind": "agentic-workspace/autopilot-executor-binding/v1",
        "status": "bound",
        "slice": slice_number,
        "owner_id": owner,
        "owner_ref": f".agentic-workspace/planning/execplans/{owner}.plan.json",
        "owner_refs": [f"#{owner[-1]}"],
        "issue_refs": [f"#{owner[-1]}"],
        "current_work_id": f"work-{owner}",
        "owner_identity": {
            "owner_id": owner,
            "owner_ref": f".agentic-workspace/planning/execplans/{owner}.plan.json",
            "owner_relation": "plan-continuation",
            "current_work_id": f"work-{owner}",
        },
        "target_identity": {
            "target_root": str(target_root),
            "target_identity_ref": "target-local",
            "target_identity_status": "current",
            "head": "fixture-head",
            "selected_target": "local-codex",
            "execution_methods": ["cli"],
            "capability_classes": ["mechanical-follow-through"],
        },
        "assignment": {
            "status": "keep-local",
            "selected_target": "local-codex",
            "target_identity_ref": "target-local",
            "context_key": f"work-{owner}",
            "implementation_allowed": True,
            "assignment_revision": f"assignment-{owner}",
            "allowed_effects": ["edit", "test"],
            "allowed_paths": ["."],
            "stop_conditions": ["blocked-authority"],
        },
        "evaluation": {"status": "not-required", "freshness_status": "not-required", "reason": "no-registered-evaluations"},
        "proof_obligation": {"status": "accepted", "receipt_status": "fresh", "proof_subject_fingerprint": f"proof-{owner}"},
        "mutation_baseline": {
            "baseline_id": f"autopilot:work-{owner}",
            "head": "fixture-head",
            "revalidation_status": "fresh",
        },
        "external_intent": {"status": "not-applicable", "reason": "fixture-no-external-issue-ref"},
        "availability": {"status": "available", "execution_methods": ["cli"]},
        "input_revision": {"head": "fixture-head", "resolved_at": "2026-07-20T00:00:00+00:00"},
        "validity": {"status": "accepted"},
    }
    binding["binding_fingerprint"] = cli._executor_binding_fingerprint(cli._executor_binding_fingerprint_payload(binding))
    return binding


def _accepted_autopilot_proof_reconciliation(*, fingerprint: str = "proof-owner-a") -> dict[str, Any]:
    return {
        "status": "accepted",
        "selected_proof_identity": {"owner_id": "owner-a", "proof_subject_fingerprint": fingerprint},
        "commands": [{"command": "make proof-owner-a", "evidence_state": "accepted"}],
        "receipt": {"result": "passed", "verified_by": "aw"},
    }


def _write_external_intent_evidence(
    target_root: Path,
    *,
    issue_ref: str = "#84",
    title: str = "Implement child issue B only",
    revision: str = "2026-07-22T00:00:00Z",
) -> None:
    path = target_root / cli.EXTERNAL_INTENT_CACHE_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/external-intent-evidence/v1",
                "refreshed_at": revision,
                "items": [
                    {
                        "system": "github",
                        "id": issue_ref,
                        "title": title,
                        "status": "open",
                        "kind": "slice",
                        "parent_id": "#80",
                        "url": f"https://github.example.test/repo/issues/{issue_ref.lstrip('#')}",
                        "source_repository": "owner/repo",
                        "external_revision": revision,
                        "observed_at": revision,
                        "freshness": {
                            "status": "current",
                            "observed_at": revision,
                            "expires_at": "2099-01-01T00:00:00+00:00",
                        },
                        "negative_invariants": ["Do not implement sibling issue C."],
                        "owner": {"id": issue_ref, "kind": "issue"},
                        "provider_detail": {"repository": "owner/repo"},
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _ensure_autopilot_fixture_git_head(target_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=target_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=target_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=target_root, check=True, capture_output=True, text=True)
    head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=target_root, capture_output=True, text=True)
    if head.returncode == 0:
        return
    subprocess.run(["git", "add", "-A"], cwd=target_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "fixture baseline"], cwd=target_root, check=True, capture_output=True, text=True)


def _autopilot_authoritative_context_fixture(*, target_root: Path, proof: dict[str, Any] | None = None) -> dict[str, Any]:
    from agentic_workspace.authority_envelope import mutation_baseline_payload

    _ensure_autopilot_fixture_git_head(target_root)
    baseline = mutation_baseline_payload(
        target_root=target_root,
        changed_paths=[],
        assignment_target_identity_ref="target-local",
    )
    context = {
        "selected_plan_id": "owner-a",
        "id": "work-owner-a",
        "owner_binding": {"owner_id": "owner-a", "relation": "plan-continuation"},
        "provenance": {"plan_id": ".agentic-workspace/planning/execplans/owner-a.plan.json"},
        "revision": {"head": baseline["head"]},
        "freshness": {"resolved_at": "2026-07-20T00:00:00+00:00"},
        "execution_posture": {
            "assignment_policy": {"manual_transport_policy": {"value": "allowed"}},
            "assignment_gate": {
                "status": "keep-local",
                "implementation_allowed": True,
                "selected_target": "local-codex",
                "target_identity_ref": "target-local",
                "target_revision": "target-rev-1",
                "task_class": "implementation",
                "scope_class": "bounded",
                "slice_id": "work-owner-a",
                "slice_revision": "slice-rev-1",
                "assignment_policy": "local-preferred",
                "assignment_decision_revision": "assignment-decision-rev-1",
                "allowed_effects": ["edit", "test"],
                "allowed_paths": [],
                "stop_conditions": ["blocked-authority"],
                "mutation_baseline": baseline,
            },
            "delegation_decision": {"decision": "stay-local", "delegation_next_step": {"execution_methods": ["cli"]}},
            "selected_target": {
                "name": "local-codex",
                "execution_methods": ["cli"],
                "capability_classes": ["mechanical-follow-through"],
                "location": "local",
                "strength": "standard",
            },
        },
        "evaluation": {"status": "not-required", "freshness_status": "not-required", "reason": "no-registered-evaluations"},
        "expected_mutation_baseline": baseline,
    }
    if proof is not None:
        context["proof_obligation"] = proof
        context["proof_receipt_reconciliation"] = {
            "status": "accepted",
            "selected_proof_identity": {
                "owner_id": "owner-a",
                "proof_subject_fingerprint": proof.get("proof_subject_fingerprint"),
            },
            "commands": [{"command": command} for command in proof.get("commands", ["make proof-owner-a"])],
            "reason": "accepted-current-proof-receipt",
        }
    return context


def test_active_executor_binding_consumes_authoritative_context_and_revalidates_baseline(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(cli, "_proof_receipt_reconciliation_payload", lambda **_: _accepted_autopilot_proof_reconciliation())
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "accepted"
    assert binding["availability"]["status"] == "available"
    assert binding["assignment"]["assignment_revision"].startswith("sha256:")
    assert binding["mutation_baseline"]["revalidation_status"] == "fresh"
    assert binding["proof_obligation"]["proof_subject_fingerprint"] == "proof-owner-a"
    invocation = binding["executor_invocation"]
    assert invocation["kind"] == "agentic-workspace/autopilot-executor-invocation/v1"
    assert invocation["role"] == "ordinary-executor"
    assert invocation["binding_fingerprint"] == binding["binding_fingerprint"]
    assert invocation["return_schema"] == "agentic-workspace/terminal-outcome-contract/v1"
    assert invocation["allowed_effects"] == ["edit", "test"]


def test_active_executor_binding_renders_invocation_from_external_intent_child(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    _write_external_intent_evidence(
        tmp_path,
        issue_ref="#84",
        title="Implement child B without touching child C",
        revision="2026-07-22T00:00:00Z",
    )
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    context["issue_refs"] = ["#84"]
    context["task"] = "Generic stack continuation text that must not scope the executor."
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(cli, "_proof_receipt_reconciliation_payload", lambda **_: _accepted_autopilot_proof_reconciliation())
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "accepted"
    assert binding["external_intent"]["status"] == "accepted"
    assert binding["external_intent"]["item_id"] == "#84"
    assert binding["executor_invocation"]["task_scope"] == "Implement child B without touching child C"
    assert binding["executor_invocation"]["external_intent"]["bounded_task"]["constraints"] == ["Do not implement sibling issue C."]


def test_active_executor_binding_rejects_stale_external_intent_revision(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    _write_external_intent_evidence(
        tmp_path,
        issue_ref="#84",
        title="Implement child B",
        revision="2026-07-22T00:00:00Z",
    )
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    context["issue_refs"] = ["#84"]
    context["external_intent"] = {"item_id": "#84", "external_revision": "2026-07-21T00:00:00Z"}
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(cli, "_proof_receipt_reconciliation_payload", lambda **_: _accepted_autopilot_proof_reconciliation())
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "rejected"
    assert binding["validity"]["reason"] == "external-intent-authority-changed"


def test_active_executor_binding_rejects_missing_authoritative_proof(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    context = _autopilot_authoritative_context_fixture(target_root=tmp_path, proof=None)
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "rejected"
    assert binding["validity"]["reason"] == "missing-selected-proof-obligation"
    assert binding["proof_obligation"]["receipt_status"] == "missing"


def test_active_executor_binding_rejects_injected_proof_without_live_reconciliation(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    context.pop("proof_receipt_reconciliation")
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "rejected"
    assert binding["validity"]["reason"] == "missing-live-proof-reconciliation"
    assert binding["proof_obligation"]["source"] == "live_proof_receipt_reconciliation"


def test_active_executor_binding_rejects_context_projected_accepted_proof_without_live_receipt(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(
        cli,
        "_proof_receipt_reconciliation_payload",
        lambda **_: {
            "status": "not-recorded",
            "selected_proof_identity": {"owner_id": "owner-a", "proof_subject_fingerprint": "proof-owner-a"},
            "commands": [{"command": "make proof-owner-a", "evidence_state": "not-run-or-not-recorded"}],
        },
    )
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "rejected"
    assert binding["validity"]["reason"] == "missing-live-proof-reconciliation"
    assert binding["proof_obligation"]["expected_reconciliation"]["status"] == "accepted"
    assert binding["proof_obligation"]["live_reconciliation"]["status"] == "not-recorded"


def test_active_executor_binding_rejects_stale_authoritative_evaluation(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    context["evaluation"] = {"evaluation_id": "eval-owner-a"}
    execution_posture = context["execution_posture"]
    expected_assignment_revision = cli._assignment_identity_payload(
        assignment_gate=execution_posture["assignment_gate"],
        assignment_policy=execution_posture["assignment_policy"],
        delegation_decision=execution_posture["delegation_decision"],
    )["revision"]
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(cli, "_proof_receipt_reconciliation_payload", lambda **_: _accepted_autopilot_proof_reconciliation())
    monkeypatch.setattr(
        cli,
        "evaluation_summary",
        lambda **_: {
            "summaries": [
                {
                    "evaluation_id": "eval-owner-a",
                    "revision": 1,
                    "owner": {"id": "owner-a"},
                    "fresh_result_admission": {
                        "status": "stale-bound",
                        "current_result_identity": {
                            "status": "stale-bound",
                            "target_identity_ref": "target-local",
                            "assignment_revision": expected_assignment_revision,
                        },
                    },
                    "conclusion_readiness": {"ready": False, "reason_code": "stale-evaluation-result"},
                }
            ]
        },
    )
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "rejected"
    assert binding["validity"]["reason"] == "stale-evaluation-result"


def test_active_executor_binding_rejects_missing_required_evaluation_summary(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    context["evaluation"] = {"status": "required", "evaluation_id": "eval-owner-a"}
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(cli, "_proof_receipt_reconciliation_payload", lambda **_: _accepted_autopilot_proof_reconciliation())
    monkeypatch.setattr(cli, "evaluation_summary", lambda **_: {"summaries": []})
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "rejected"
    assert binding["validity"]["reason"] == "missing-required-evaluation-summary"
    assert binding["evaluation"]["required"] is True


def test_active_executor_binding_rejects_required_evaluation_missing_join_identity(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    context["evaluation"] = {"status": "required", "evaluation_id": "eval-owner-a"}
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(cli, "_proof_receipt_reconciliation_payload", lambda **_: _accepted_autopilot_proof_reconciliation())
    monkeypatch.setattr(
        cli,
        "evaluation_summary",
        lambda **_: {
            "summaries": [
                {
                    "evaluation_id": "eval-owner-a",
                    "revision": 1,
                    "owner": {"id": "owner-a"},
                    "fresh_result_admission": {
                        "status": "fresh-bound",
                        "current_result_identity": {"status": "fresh-bound"},
                    },
                    "conclusion_readiness": {"ready": True},
                }
            ]
        },
    )
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "rejected"
    assert binding["validity"]["reason"] == "missing-relevant-evaluation"


def test_active_executor_binding_ignores_unrelated_stale_evaluation(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    context = _autopilot_authoritative_context_fixture(
        target_root=tmp_path,
        proof={
            "status": "accepted",
            "receipt_status": "fresh",
            "proof_subject_fingerprint": "proof-owner-a",
            "commands": ["make proof-owner-a"],
        },
    )
    monkeypatch.setattr(cli, "resolve_current_work_context", lambda **_: context)
    monkeypatch.setattr(cli, "_proof_receipt_reconciliation_payload", lambda **_: _accepted_autopilot_proof_reconciliation())
    monkeypatch.setattr(
        cli,
        "evaluation_summary",
        lambda **_: {
            "summaries": [
                {
                    "evaluation_id": "eval-other-owner",
                    "revision": 1,
                    "owner": {"id": "other-owner"},
                    "fresh_result_admission": {
                        "status": "stale-bound",
                        "current_result_identity": {"status": "missing"},
                    },
                    "conclusion_readiness": {"ready": False, "reason_code": "stale-evaluation-result"},
                }
            ]
        },
    )
    monkeypatch.setattr(
        cli,
        "target_identity_posture",
        lambda **_: {
            "current_target": "local-codex",
            "current_target_identity": {"status": "current", "subject": {"stable_target_id": "target-local"}},
        },
    )

    binding = cli._active_executor_binding(target_root=tmp_path.resolve(), slice_number=1)

    assert binding["validity"]["status"] == "accepted"
    assert binding["evaluation"]["freshness_status"] == "not-required"
    assert binding["evaluation"]["ignored_evaluation_count"] == 1


def test_autopilot_rebinds_executor_with_current_binding_fingerprint_after_active_owner_changes(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()

    contracts = [
        {
            "kind": "agentic-workspace/terminal-outcome-contract/v1",
            "state": "CONTINUE",
            "final_response_authorized": False,
            "required_next_action": "continue-current-work",
            "safe_continuation_option_ids": ["run-proof"],
            "blocker_qualification": {"status": "not_required"},
            "final_response_enforcement": {
                "status": "rejected_auto_resume",
                "terminal_final_rejected": True,
                "auto_resume_action": "continue-current-work",
                "progress_without_yield": True,
                "multi_slice_continuation": {"status": "preserved"},
            },
        },
        {
            "kind": "agentic-workspace/terminal-outcome-contract/v1",
            "state": "DELIVERED",
            "final_response_authorized": True,
            "required_next_action": "",
            "safe_continuation_option_ids": [],
            "blocker_qualification": {"status": "not_required"},
            "final_response_enforcement": {"status": "authorized", "terminal_final_rejected": False},
        },
    ]

    def fake_closeout_trust(*, target_root: Path) -> tuple[dict[str, Any], object]:
        assert target_root == tmp_path.resolve()
        return {"terminal_outcome_contract": contracts.pop(0)}, object()

    def fake_continuation(*, target_root: Path, terminal_outcome_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        return {
            "kind": "agentic-workspace/final-response-resume-result/v1",
            "status": "executed",
            "invoked_action": request["auto_resume_action"],
            "invoked_operation": "planning.admit-child",
            "command": "agentic-planning lane-activate parent --current-slice owner-b --format json",
            "exit_code": 0,
            "custody": "agent",
            "after_state_patch": {"required_next_action": request["auto_resume_action"], "custody_owner": "agent"},
        }

    def fake_binding(*, target_root: Path, slice_number: int) -> dict[str, Any]:
        owner = "owner-a" if slice_number == 1 else "owner-b"
        return _autopilot_executor_binding_fixture(owner=owner, slice_number=slice_number, target_root=target_root)

    monkeypatch.setattr(cli, "_final_response_closeout_trust_for_admission", fake_closeout_trust)
    monkeypatch.setattr(cli, "_run_final_response_continuation_operation", fake_continuation)
    monkeypatch.setattr(cli, "_active_executor_binding", fake_binding)
    binding_log = tmp_path / "binding.log"
    monkeypatch.setenv("BINDING_LOG", str(binding_log))
    executor_script = tmp_path / "generic_autopilot_executor.py"
    executor_script.write_text(
        """
import json
import os
from pathlib import Path

binding = json.loads(os.environ["AGENTIC_WORKSPACE_AUTOPILOT_EXECUTOR_BINDING"])
guard = json.loads(os.environ["AGENTIC_WORKSPACE_AUTOPILOT_EXECUTOR_BINDING_GUARD"])
Path(os.environ["BINDING_LOG"]).write_text(
    (Path(os.environ["BINDING_LOG"]).read_text() if Path(os.environ["BINDING_LOG"]).exists() else "")
    + binding["owner_id"] + ":" + guard["status"] + "\\n"
)
print("Done too early." if binding["owner_id"] == "owner-a" else "Actually delivered for owner-b.")
""".strip(),
        encoding="utf-8",
    )

    owner_b_fingerprint = fake_binding(target_root=tmp_path.resolve(), slice_number=2)["binding_fingerprint"]
    assert (
        cli.main(
            [
                "autopilot",
                "--target",
                str(tmp_path),
                "--executor-command",
                subprocess.list2cmdline([sys.executable, str(executor_script), "--binding-fingerprint", owner_b_fingerprint]),
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "accepted_terminal_final"
    assert binding_log.read_text(encoding="utf-8").splitlines() == ["owner-a:valid", "owner-b:rebound"]
    loop = payload["ordinary_execution_loop"]
    assert loop["latest_executor_binding"]["owner_id"] == "owner-b"
    assert loop["latest_executor_binding_guard"]["status"] == "rebound"
    assert [item["executor_binding"]["owner_id"] for item in loop["slices"]] == ["owner-a", "owner-b"]


def test_autopilot_rejects_stale_slice_specific_executor_after_owner_changes(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()

    def fake_closeout_trust(*, target_root: Path) -> tuple[dict[str, Any], object]:
        return {
            "terminal_outcome_contract": {
                "kind": "agentic-workspace/terminal-outcome-contract/v1",
                "state": "CONTINUE",
                "final_response_authorized": False,
                "required_next_action": "continue-current-work",
                "safe_continuation_option_ids": ["run-proof"],
                "blocker_qualification": {"status": "not_required"},
                "final_response_enforcement": {
                    "status": "rejected_auto_resume",
                    "terminal_final_rejected": True,
                    "auto_resume_action": "continue-current-work",
                    "progress_without_yield": True,
                    "multi_slice_continuation": {"status": "preserved"},
                },
            }
        }, object()

    def fake_continuation(*, target_root: Path, terminal_outcome_contract: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        return {
            "kind": "agentic-workspace/final-response-resume-result/v1",
            "status": "executed",
            "invoked_action": request["auto_resume_action"],
            "invoked_operation": "planning.admit-child",
            "command": "agentic-planning lane-activate parent --current-slice owner-b --format json",
            "exit_code": 0,
            "custody": "agent",
            "after_state_patch": {"required_next_action": request["auto_resume_action"], "custody_owner": "agent"},
        }

    def fake_binding(*, target_root: Path, slice_number: int) -> dict[str, Any]:
        owner = "owner-a" if slice_number == 1 else "owner-b"
        return _autopilot_executor_binding_fixture(owner=owner, slice_number=slice_number, target_root=target_root)

    monkeypatch.setattr(cli, "_final_response_closeout_trust_for_admission", fake_closeout_trust)
    monkeypatch.setattr(cli, "_run_final_response_continuation_operation", fake_continuation)
    monkeypatch.setattr(cli, "_active_executor_binding", fake_binding)
    attempt_log = tmp_path / "attempts.log"
    monkeypatch.setenv("ATTEMPT_LOG", str(attempt_log))
    executor_script = tmp_path / "owner_a_executor.py"
    executor_script.write_text(
        """
import os
from pathlib import Path

Path(os.environ["ATTEMPT_LOG"]).write_text(
    (Path(os.environ["ATTEMPT_LOG"]).read_text() if Path(os.environ["ATTEMPT_LOG"]).exists() else "") + "ran\\n"
)
print("Done too early.")
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as error:
        cli.main(
            [
                "autopilot",
                "--target",
                str(tmp_path),
                "--executor-command",
                subprocess.list2cmdline([sys.executable, str(executor_script), "--owner", "owner-a"]),
                "--format",
                "json",
            ]
        )

    assert error.value.code == 2
    assert "invalid executor binding" in capsys.readouterr().err
    assert attempt_log.read_text(encoding="utf-8").splitlines() == ["ran"]


@pytest.mark.parametrize(
    ("invalid_patch", "expected_reason"),
    [
        ({"status": "unbound", "availability": {"status": "unavailable", "reason": "no-live-owner-binding"}}, "no-live-owner-binding"),
        ({"availability": {"status": "unavailable", "reason": "executor-unavailable"}}, "executor-unavailable"),
        ({"assignment": {"status": "handoff-required", "reason": "required-best-fit-handoff"}}, "required-best-fit-handoff"),
        ({"evaluation": {"freshness_status": "stale", "reason": "stale-evaluation-result"}}, "stale-evaluation-result"),
        ({"proof_obligation": {"receipt_status": "stale", "reason": "stale-proof-receipt"}}, "stale-proof-receipt"),
        ({"mutation_baseline": {"revalidation_status": "stale", "reason": "baseline-head-changed"}}, "baseline-head-changed"),
        ({"validity": {"status": "rejected", "reason": "lane-superseded"}}, "lane-superseded"),
    ],
)
def test_autopilot_stops_before_executor_when_live_binding_invalid(
    tmp_path: Path, capsys, monkeypatch, invalid_patch: dict[str, Any], expected_reason: str
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()

    def fake_binding(*, target_root: Path, slice_number: int) -> dict[str, Any]:
        binding = {
            "kind": "agentic-workspace/autopilot-executor-binding/v1",
            "status": "bound",
            "slice": slice_number,
            "owner_id": "owner-a",
            "owner_ref": ".agentic-workspace/planning/execplans/owner-a.plan.json",
            "owner_refs": ["#1"],
            "issue_refs": ["#1"],
            "current_work_id": "work-owner-a",
            "owner_identity": {
                "owner_id": "owner-a",
                "owner_ref": ".agentic-workspace/planning/execplans/owner-a.plan.json",
                "owner_relation": "plan-continuation",
                "current_work_id": "work-owner-a",
            },
            "target_identity": {
                "target_root": str(tmp_path),
                "worktree": ".",
                "branch": "agent/p1-autopilot-executor-binding",
                "head": "fixture-head",
                "current_target": "local",
                "target_identity_ref": "target-local",
                "target_identity_status": "known",
            },
            "assignment": {
                "status": "keep-local",
                "policy": "local-preferred",
                "selected_target": "local",
                "target_identity_ref": "target-local",
                "context_key": "work-owner-a",
            },
            "evaluation": {
                "status": "accepted",
                "freshness_status": "fresh",
                "owner_id": "owner-a",
                "target_identity_ref": "target-local",
            },
            "proof_obligation": {
                "status": "accepted",
                "receipt_status": "fresh",
                "proof_subject_fingerprint": "proof-fresh",
            },
            "mutation_baseline": {
                "baseline_id": "autopilot:work-owner-a",
                "head": "fixture-head",
                "revalidation_status": "fresh",
            },
            "external_intent": {"status": "not-applicable", "reason": "fixture-no-external-issue-ref"},
            "availability": {"status": "available"},
            "validity": {"status": "accepted"},
            "input_revision": {"head": "fixture-head", "resolved_at": "2026-07-20T00:00:00+00:00"},
        }
        for key, value in invalid_patch.items():
            if isinstance(value, dict) and isinstance(binding.get(key), dict):
                binding[key] = {**binding[key], **value}
            else:
                binding[key] = value
        return binding

    monkeypatch.setattr(cli, "_active_executor_binding", fake_binding)
    attempt_log = tmp_path / "attempts.log"
    monkeypatch.setenv("ATTEMPT_LOG", str(attempt_log))
    executor_script = tmp_path / "should_not_run.py"
    executor_script.write_text(
        """
import os
from pathlib import Path

Path(os.environ["ATTEMPT_LOG"]).write_text("ran\\n")
print("Should not run.")
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as error:
        cli.main(
            [
                "autopilot",
                "--target",
                str(tmp_path),
                "--executor-command",
                subprocess.list2cmdline([sys.executable, str(executor_script)]),
                "--format",
                "json",
            ]
        )

    assert error.value.code == 2
    assert expected_reason in capsys.readouterr().err
    assert not attempt_log.exists()


def test_autopilot_rejects_repeated_weak_finals_across_compaction_review_reconciliation_until_delivered(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()

    fixture_path = tmp_path / ".agentic-workspace" / "local" / "terminal-custody-fixture.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(
            {
                "objective": "finish PR #2236 and #2237 review follow-through",
                "selected_review_threads": [
                    {"pr": 2236, "thread": "thread-a", "status": "unresolved"},
                    {"pr": 2237, "thread": "thread-b", "status": "unresolved"},
                ],
                "completed_slices": [],
                "proof_state": "missing",
                "progress_events": [],
                "waiting_for_user": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def terminal_contract(state: str, *, action: str = "") -> dict[str, Any]:
        authorized = state in {"DELIVERED", "BLOCKED", "USER_PAUSED"}
        return {
            "kind": "agentic-workspace/terminal-outcome-contract/v1",
            "state": state,
            "final_response_authorized": authorized,
            "required_next_action": "" if authorized else action,
            "safe_continuation_option_ids": [] if authorized else ["address-review-thread", "run-proof"],
            "blocker_qualification": {"status": "not_required"},
            "final_response_enforcement": {
                "status": "authorized" if authorized else "rejected_auto_resume",
                "terminal_final_rejected": not authorized,
                "auto_resume_action": "" if authorized else action,
                "progress_without_yield": not authorized,
                "compaction_resume_safe": not authorized,
                "multi_slice_continuation": {
                    "status": "not_required" if authorized else "preserved",
                    "resume_fields": [
                        "objective",
                        "completed_slices",
                        "selected_review_threads",
                        "proof_state",
                        "required_next_action",
                    ],
                },
            },
        }

    closeout_observations: list[dict[str, Any]] = []

    def fake_closeout_trust(*, target_root: Path) -> tuple[dict[str, Any], object]:
        state = json.loads(fixture_path.read_text(encoding="utf-8"))
        closeout_observations.append(state)
        unresolved = [thread for thread in state["selected_review_threads"] if thread["status"] != "addressed"]
        if unresolved:
            contract = terminal_contract("CONTINUE", action=f"address-pr-{unresolved[0]['pr']}-{unresolved[0]['thread']}")
        elif state["proof_state"] != "complete":
            contract = terminal_contract("CONTINUE", action="run-review-stack-proof")
        else:
            contract = terminal_contract("DELIVERED")
        return {"terminal_outcome_contract": contract}, object()

    continuation_events: list[dict[str, Any]] = []

    def fake_continuation(*, target_root: Path, terminal_outcome_contract: dict, request: dict) -> dict:
        assert target_root == tmp_path.resolve()
        assert terminal_outcome_contract["state"] == "CONTINUE"
        assert request["terminal_final_rejected"] is True
        event = {
            "action": request["auto_resume_action"],
            "after_compaction": request["after_compaction"],
            "custody": "agent",
        }
        continuation_events.append(event)
        return {
            "kind": "agentic-workspace/final-response-resume-result/v1",
            "status": "executed",
            "invoked_action": request["auto_resume_action"],
            "invoked_operation": "review-stack.follow-through",
            "command": "review-stack follow-through --fixture",
            "exit_code": 0,
            "custody": "agent",
            "after_state_patch": {
                "required_next_action": request["auto_resume_action"],
                "custody_owner": "agent",
                "continuation_slice": f"slice-{len(continuation_events)}-post-compaction",
                "selected_review_threads": "preserved",
                "proof_state": "preserved",
            },
        }

    monkeypatch.setattr(cli, "_final_response_closeout_trust_for_admission", fake_closeout_trust)
    monkeypatch.setattr(cli, "_run_final_response_continuation_operation", fake_continuation)
    monkeypatch.setenv("FIXTURE_PATH", str(fixture_path))

    def fake_binding(*, target_root: Path, slice_number: int) -> dict[str, Any]:
        return {
            "kind": "agentic-workspace/autopilot-executor-binding/v1",
            "status": "bound",
            "slice": slice_number,
            "owner_id": "review-stack-owner",
            "owner_ref": ".agentic-workspace/planning/execplans/review-stack-owner.plan.json",
            "current_work_id": "review-stack-work",
            "owner_identity": {
                "owner_id": "review-stack-owner",
                "owner_ref": ".agentic-workspace/planning/execplans/review-stack-owner.plan.json",
                "owner_relation": "plan-continuation",
                "current_work_id": "review-stack-work",
            },
            "target_identity": {
                "target_root": str(tmp_path),
                "target_identity_ref": "target-local",
                "head": "fixture-head",
            },
            "assignment": {"status": "keep-local", "target_identity_ref": "target-local", "context_key": "review-stack-work"},
            "evaluation": {"freshness_status": "fresh"},
            "proof_obligation": {"receipt_status": "fresh", "proof_subject_fingerprint": "review-stack-proof"},
            "mutation_baseline": {"baseline_id": "autopilot:review-stack-work", "head": "fixture-head", "revalidation_status": "fresh"},
            "external_intent": {"status": "not-applicable", "reason": "fixture-no-external-issue-ref"},
            "availability": {"status": "available"},
            "validity": {"status": "accepted"},
        }

    monkeypatch.setattr(cli, "_active_executor_binding", fake_binding)

    executor_script = tmp_path / "weak_review_executor.py"
    executor_script.write_text(
        """
import json
import os
from pathlib import Path

slice_no = int(os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_SLICE"])
assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_CUSTODY"] == "agent"
path = Path(os.environ["FIXTURE_PATH"])
state = json.loads(path.read_text(encoding="utf-8"))
if slice_no > 1:
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_PREVIOUS_ADMISSION"]
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_CONTINUATION"]
    continuation_state = json.loads(os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_CONTINUATION_STATE"])
    assert continuation_state["custody_owner"] == "agent"
    assert os.environ["AGENTIC_WORKSPACE_FINAL_RESPONSE_ACTIVE_OBJECTIVE"]
if slice_no == 1:
    state["selected_review_threads"][0]["status"] = "addressed"
    state["completed_slices"].append("pr-2236-thread-a")
    state["progress_events"].append({"slice": slice_no, "message": "PR #2236 thread-a addressed; more review work remains."})
    print("Progress: first review slice done; work remains. Done.")
elif slice_no == 2:
    state["selected_review_threads"][1]["status"] = "addressed"
    state["completed_slices"].append("pr-2237-thread-b")
    state["progress_events"].append({"slice": slice_no, "message": "All threads addressed; proof remains."})
    print("Progress: review comments addressed; proof remains. Done.")
elif slice_no == 3:
    state["proof_state"] = "complete"
    state["completed_slices"].append("review-stack-proof")
    print("Delivered: PR #2236 and #2237 review threads and proof reconciled.")
else:
    raise SystemExit("autopilot should have delivered by slice 3")
state["waiting_for_user"] = False
path.write_text(json.dumps(state, indent=2) + "\\n", encoding="utf-8")
""".strip(),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "autopilot",
                "--target",
                str(tmp_path),
                "--executor-command",
                subprocess.list2cmdline([sys.executable, str(executor_script)]),
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "accepted_terminal_final"
    assert payload["admission"]["attempt"]["claim"] == "Delivered: PR #2236 and #2237 review threads and proof reconciled."
    loop = payload["ordinary_execution_loop"]
    assert loop["slice_count"] == 3
    assert [item["admission_status"] for item in loop["slices"]] == [
        "rejected_auto_resumed",
        "rejected_auto_resumed",
        "accepted_terminal_final",
    ]
    assert [item["terminal_state"] for item in loop["slices"]] == ["CONTINUE", "CONTINUE", "DELIVERED"]
    assert len(continuation_events) == 2
    assert continuation_events[0]["action"] == "address-pr-2237-thread-b"
    assert continuation_events[1]["action"] == "run-review-stack-proof"
    assert continuation_events[0]["after_compaction"] is False
    assert continuation_events[1]["after_compaction"] is True
    final_state = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert final_state["waiting_for_user"] is False
    assert final_state["proof_state"] == "complete"
    assert {thread["status"] for thread in final_state["selected_review_threads"]} == {"addressed"}
    assert [event["slice"] for event in final_state["progress_events"]] == [1, 2]
    checkpoint = json.loads((tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json").read_text())
    admission_checkpoint = checkpoint["final_response_admission"]
    assert admission_checkpoint["slice_count"] == 3
    assert admission_checkpoint["slices"][0]["terminal_state"] == "CONTINUE"
    assert admission_checkpoint["slices"][1]["after_compaction"] is True
    assert closeout_observations[0]["selected_review_threads"][1]["status"] == "unresolved"
    assert closeout_observations[-1]["proof_state"] == "complete"


@pytest.mark.parametrize(
    ("terminal_state", "custody_owner"),
    [
        ("BLOCKED", "external-or-human-action"),
        ("USER_PAUSED", "user"),
    ],
)
def test_final_response_executor_boundary_accepts_genuine_blocked_and_user_paused(
    tmp_path: Path, capsys, monkeypatch, terminal_state: str, custody_owner: str
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()

    def fake_closeout_trust(*, target_root: Path) -> tuple[dict[str, Any], object]:
        return {
            "terminal_outcome_contract": {
                "kind": "agentic-workspace/terminal-outcome-contract/v1",
                "state": terminal_state,
                "final_response_authorized": True,
                "custody_owner": custody_owner,
                "required_next_action": "",
                "safe_continuation_option_ids": [],
                "blocker_qualification": {
                    "status": "qualified_external_blocker" if terminal_state == "BLOCKED" else "not_required",
                    "qualified_blockers": [
                        {
                            "id": "missing-credential",
                            "type": "credential",
                            "evidence": "The fixture withholds the required credential.",
                            "recovery": "Ask the user for the credential.",
                            "no_safe_continuation": True,
                        }
                    ]
                    if terminal_state == "BLOCKED"
                    else [],
                },
                "final_response_enforcement": {
                    "status": "authorized",
                    "terminal_final_rejected": False,
                    "progress_without_yield": False,
                    "multi_slice_continuation": {"status": "not_required"},
                },
            }
        }, object()

    def fail_continuation(**_: Any) -> dict[str, Any]:
        raise AssertionError("authorized terminal states must not run continuation")

    monkeypatch.setattr(cli, "_final_response_closeout_trust_for_admission", fake_closeout_trust)
    monkeypatch.setattr(cli, "_run_final_response_continuation_operation", fail_continuation)
    executor_script = tmp_path / "terminal_executor.py"
    executor_script.write_text('print("Terminal state accepted by host boundary.")\n', encoding="utf-8")

    assert (
        cli.main(
            [
                "final-response",
                "admit",
                "--target",
                str(tmp_path),
                "--executor-command",
                subprocess.list2cmdline([sys.executable, str(executor_script)]),
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "accepted_terminal_final"
    assert payload["terminal_outcome_contract"]["state"] == terminal_state
    assert payload["admission"]["terminal_final_rejected"] is False
    assert payload["ordinary_execution_loop"]["slice_count"] == 1
    assert payload["ordinary_execution_loop"]["custody"] == "completed-outcome"


def test_executor_mode_operation_contracts_are_conservative() -> None:
    for operation_name in ("final-response.admit", "autopilot.run"):
        contract = json.loads((Path("src/agentic_workspace/contracts/operations") / f"{operation_name}.json").read_text())
        assert contract["effects"] == {
            "read_only": False,
            "destructive": True,
            "idempotent": False,
            "writes_repo_state": True,
            "requires_preflight_gate": True,
        }
        assert contract["locality"] == {
            "requires_repo": False,
            "network": "allowed",
            "outside_repo_writes": "allowed",
        }


def test_closeout_trust_names_external_intent_evidence_blocker_for_open_issue(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=True, external_status="open")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "closeout_trust", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]

    assert payload["checks"]["intent_proof"]["status"] == "sufficient_for_claim"
    claim_work = next(option for option in payload["completion_options"] if option["id"] == "claim-work-complete")
    assert claim_work["allowed"] is False
    assert "intent_satisfaction.closure_scope.external_intent_evidence" in claim_work["blocking_fields"]
    assert "intent_satisfaction.required_follow_on" not in claim_work["blocking_fields"]


def test_closeout_trust_scopes_unrelated_active_plan_residue_to_repo_wide_closeout(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
strict_closeout = true
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Unrelated active plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Unrelated active plan",
        item_id="active-plan",
        status="active",
        why_now="regress task-scoped closeout trust with unrelated active planning residue.",
        next_action="Continue unrelated active plan later.",
        done_when="The unrelated active plan is complete.",
    )
    planning_installer._write_execplan_record(
        record_path=tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        record=record,
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "closeout_trust",
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement issue #3000 parser cache cleanup",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["answer"]

    assert payload["strict_closeout_gate"]["blocking"] is True
    current = payload["current_task_closeout"]
    assert current["status"] == "active"
    assert current["scope"]["relationship"] == "bounded-current-task"
    assert current["scope"]["planning_safety_gate"]["gate_result"] == "mutation-baseline-required"
    switch = current["scope"]["planning_safety_gate"]["task_switch_reconciliation"]
    assert switch["status"] == "current-task-route-acknowledged"
    assert switch["route_acknowledgement"]["status"] == "acknowledged"
    assert current["strict_closeout_gate"]["blocking"] is False
    assert current["strict_closeout_gate"]["current_task_blocking"] is False
    assert current["operating_loop"]["planning"]["state"] == "unrelated_active_plan"
    assert current["operating_loop"]["planning"]["blocks_full_closure"] is False
    assert current["operating_loop"]["verification"]["state"] == "proof_missing"
    assert current["operating_loop"]["required_before_full_closure"] == ["run_or_refresh_proof"]
    claim_slice = next(option for option in current["completion_options"] if option["id"] == "claim-slice-complete")
    assert claim_slice["allowed"] is False
    assert "intent_satisfaction.closure_scope.validation_proof" in claim_slice["blocking_fields"]
    assert "strict_closeout_gate" not in claim_slice["blocking_fields"]
    assert "durable_residue" not in claim_slice["blocking_fields"]
    assert "completion_gate" not in claim_slice["blocking_fields"]


def test_closeout_trust_composes_current_task_closeout_for_ordinary_changed_scope(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")
    capsys.readouterr()

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "closeout_trust",
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Implement a focused runtime report fix",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["answer"]

    current = payload["current_task_closeout"]
    assert current["status"] == "active"
    assert current["scope"]["relationship"] == "bounded-current-task"
    assert current["bounded_claim_classes"] == ["local_pr_complete", "slice_complete"]
    assert current["allowed_claim_classes"] == []
    assert "leaf_issue_complete" in current["blocked_claim_classes"]
    assert "parent_issue_complete" in current["blocked_claim_classes"]
    assert "full_intent_complete" in current["blocked_claim_classes"]
    assert "issue_closure" in current["blocked_claim_classes"]
    claim_slice = next(option for option in current["completion_options"] if option["id"] == "claim-slice-complete")
    assert claim_slice["allowed"] is False
    assert claim_slice["required_claim_class"] == "local_pr_complete"
    assert claim_slice["bounded_claim_classes"] == ["local_pr_complete", "slice_complete"]
    assert "intent_satisfaction.closure_scope.validation_proof" in claim_slice["blocking_fields"]
    proof_state = current["proof_state"]
    assert proof_state["status"] == "not-run-or-not-recorded"
    assert proof_state["proof_execution_status"] == "not-run-or-not-recorded"
    assert proof_state["state_model"] == ["selected", "run", "passed", "failed", "skipped", "unavailable", "waived", "missing"]
    assert "expected_commands" in proof_state
    assert proof_state["manual_verification_expected"] is True
    assert proof_state["manual_verification"]["status"] == "required"
    assert proof_state["receipt_reconciliation_status"] in {"missing", "partial", "accepted", "not-recorded", "unavailable"}
    assert proof_state["receipt_bridge"]["status"] in {"action-required", "complete", "unavailable"}
    assert "do not authorize active-plan progress, leaf issue completion" in current["rule"]


def test_closeout_handoff_projects_the_planning_route_decision(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Unrelated active plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        json.dumps({"id": "active-plan", "title": "Unrelated active plan"}),
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")
    capsys.readouterr()

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "closeout_trust",
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Implement a focused runtime report fix",
                "--format",
                "json",
            ]
        )
        == 0
    )
    route = json.loads(capsys.readouterr().out)["answer"]["current_task_closeout"]["scope"]["route_decision"]

    assert route["kind"] == "agentic-planning/route-decision/v1"
    assert (route["task_relation"], route["owner_posture"], route["required_transition"]) == (
        "bounded-independent",
        "current",
        "refresh-mutation-baseline",
    )
    assert route["mutation_authority"] == "none"
    assert route["next_safe_action"]["action"] == "refresh-mutation-baseline"
    closeout_projection = route["consumer_projections"]["closeout"]
    assert closeout_projection["decision_id"] == route["decision_id"]
    assert closeout_projection["input_revision"] == route["input_revision"]
    assert closeout_projection["action_identity"] == route["action_identity"]
    assert closeout_projection["blocked_claims"] == route["blocked_claims"]


def test_closeout_trust_preserves_current_task_manual_proof_obligations(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.workspace_runtime_core as runtime_core

    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")
    capsys.readouterr()

    original_proof_selection = runtime_core._proof_selection_for_changed_paths

    def proof_selection_with_manual_obligation(*args: Any, **kwargs: Any) -> dict[str, Any]:
        payload = original_proof_selection(*args, **kwargs)
        payload["proof_obligations"] = {
            "kind": "agentic-workspace/proof-obligations/v1",
            "required_proof": {
                "status": "required",
                "manual_verification_required": True,
                "manual_obligation_count": 1,
                "manual_obligations": [
                    {
                        "id": "verification:manual-review",
                        "status": "missing-evidence",
                        "missing_evidence": ["manual_review"],
                        "claim_boundary": "completion-claims-qualified-until-manual-evidence-recorded-or-waived",
                    }
                ],
            },
        }
        return payload

    monkeypatch.setattr(runtime_core, "_proof_selection_for_changed_paths", proof_selection_with_manual_obligation)

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "closeout_trust",
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Implement a focused runtime report fix",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["answer"]

    proof_state = payload["current_task_closeout"]["proof_state"]
    assert proof_state["manual_verification_expected"] is True
    assert proof_state["manual_verification"]["status"] == "required"
    assert proof_state["manual_verification"]["manual_verification_required"] is True
    assert proof_state["manual_verification"]["manual_obligation_count"] == 1


def test_closeout_trust_scopes_pr_comment_repair_to_feedback_claim(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")
    capsys.readouterr()

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "closeout_trust",
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Address PR review comments",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["answer"]

    current = payload["current_task_closeout"]
    assert current["status"] == "active"
    assert current["scope"]["relationship"] == "bounded-pr-comment-repair"
    assert "does not authorize issue, lane, parent, or full-intent completion" in current["scope"]["rule"]
    claim_feedback = next(option for option in current["completion_options"] if option["id"] == "claim-slice-complete")
    assert claim_feedback["required_claim_class"] == "pr_feedback_addressed"
    assert claim_feedback["bounded_claim_class"] == "pr_feedback_addressed"
    assert "PR feedback-addressed claim" in claim_feedback["why"]
    claim_work = next(option for option in current["completion_options"] if option["id"] == "claim-work-complete")
    close_parent = next(option for option in current["completion_options"] if option["id"] == "close-parent-lane")
    assert claim_work["allowed"] is False
    assert close_parent["allowed"] is False


def test_verbose_aliases_full_diagnostic_output_for_major_workspace_commands(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()

    cases = [
        (["defaults", "--verbose", "--format", "json"], lambda payload: "startup" in payload),
        (["modules", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: "terminology" in payload),
        (["summary", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["profile"] == "full"),
        (["report", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["kind"] == "workspace-report/v1"),
        (["config", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["target"] == tmp_path.as_posix()),
        (
            ["preflight", "--target", str(tmp_path), "--verbose", "--format", "json"],
            lambda payload: payload["mode"] == "full-takeover-context",
        ),
        (["proof", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: "default_routes" in payload),
        (
            ["implement", "--target", str(tmp_path), "--verbose", "--changed", "README.md", "--format", "json"],
            lambda payload: payload["kind"] == "implementer-context/v1",
        ),
        (["status", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["health"] == "healthy"),
        (["doctor", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["health"] == "healthy"),
    ]

    for argv, assertion in cases:
        assert cli.main(argv) == 0
        payload = json.loads(capsys.readouterr().out)
        assert assertion(payload), argv


def test_defaults_text_uses_tiny_router_payload(capsys) -> None:
    assert cli.main(["defaults"]) == 0

    output = capsys.readouterr().out
    assert "Default-route contract sections are available on demand" in output
    assert "Common sections:" in output
    assert "- startup" in output
    assert "agentic-workspace defaults --verbose --format json" in output
    repo_root = Path(__file__).resolve().parents[1]
    view_contract = json.loads((repo_root / "src/agentic_workspace/contracts/workspace_output_views.json").read_text(encoding="utf-8"))
    assert any(view["id"] == "defaults-router.text" for view in view_contract["views"])


def test_planning_front_door_preserves_integration_propose_contract(monkeypatch, tmp_path: Path, capsys) -> None:
    forwarded: list[list[str]] = []

    def fake_planning_main(argv: list[str]) -> int:
        forwarded.append(argv)
        print(json.dumps({"argv": argv}))
        return 0

    monkeypatch.setattr("repo_planning_bootstrap.cli.main", fake_planning_main)
    expected = [
        "integration-propose",
        "--proposal-id",
        "archive-owner-2496",
        "--owner",
        "owner-2496",
        "--owner-ref",
        ".agentic-workspace/planning/execplans/owner-2496.plan.json",
        "--issue",
        "#2496",
        "--external-ref",
        "github:#2496",
        "--requested-transition",
        "archive-owner",
        "--proof",
        "checks:passing,review:approved",
        "--parent-boundary",
        "lane remains independently open",
        "--invariant",
        "parent-current-slice,issue-relation",
        "--expect-subject-revision",
        "subject-revision",
        "--expect-target-revision",
        "target-revision",
        "--record-feature-completion",
        "--refresh-existing",
        "--expect-proposal-revision",
        "proposal-revision",
        "--target",
        str(tmp_path),
        "--expect-planning-revision",
        "planning-revision",
        "--dry-run",
        "--format",
        "json",
    ]

    assert cli.main(["planning", *expected]) == 0

    actual = json.loads(capsys.readouterr().out)["argv"]
    assert actual[0] == "integration-propose"
    for option in [
        "--proposal-id",
        "--owner",
        "--owner-ref",
        "--issue",
        "--external-ref",
        "--requested-transition",
        "--proof",
        "--parent-boundary",
        "--invariant",
        "--expect-subject-revision",
        "--expect-target-revision",
        "--expect-proposal-revision",
        "--target",
        "--expect-planning-revision",
        "--format",
    ]:
        assert actual[actual.index(option) + 1] == expected[expected.index(option) + 1]
    assert "--refresh-existing" in actual
    assert "--record-feature-completion" in actual
    assert "--dry-run" in actual
    assert forwarded == [actual]


def test_planning_front_door_forwards_integration_apply_proposal(monkeypatch, tmp_path: Path, capsys) -> None:
    forwarded: list[list[str]] = []

    def fake_planning_main(argv: list[str]) -> int:
        forwarded.append(argv)
        print(json.dumps({"argv": argv}))
        return 0

    monkeypatch.setattr("repo_planning_bootstrap.cli.main", fake_planning_main)

    assert (
        cli.main(
            [
                "planning",
                "integration-apply",
                "--proposal",
                "archive-owner-2590",
                "--target",
                str(tmp_path),
                "--expect-planning-revision",
                "planning-revision",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )

    actual = json.loads(capsys.readouterr().out)["argv"]
    assert actual[0] == "integration-apply"
    assert actual[actual.index("--proposal") + 1] == "archive-owner-2590"
    assert actual[actual.index("--target") + 1] == str(tmp_path)
    assert actual[actual.index("--expect-planning-revision") + 1] == "planning-revision"
    assert "--dry-run" in actual
    assert actual[actual.index("--format") + 1] == "json"
    assert forwarded == [actual]


def test_planning_front_door_forwards_targeted_owner_write(monkeypatch, tmp_path: Path, capsys) -> None:
    forwarded: list[list[str]] = []

    def fake_planning_main(argv: list[str]) -> int:
        forwarded.append(argv)
        print(json.dumps({"argv": argv}))
        return 0

    monkeypatch.setattr("repo_planning_bootstrap.cli.main", fake_planning_main)
    patch = json.dumps({"touched_paths": ["src/example.py"]}, separators=(",", ":"))

    assert (
        cli.main(
            [
                "planning",
                "targeted-write",
                "--plan",
                "example-owner",
                "--patch",
                patch,
                "--expect-planning-revision",
                "planning-revision",
                "--expect-owner-revision",
                "3",
                "--target",
                str(tmp_path),
                "--apply",
                "--format",
                "json",
            ]
        )
        == 0
    )

    actual = json.loads(capsys.readouterr().out)["argv"]
    assert actual[0] == "targeted-write"
    for option, value in {
        "--plan": "example-owner",
        "--patch": patch,
        "--target": str(tmp_path),
        "--expect-planning-revision": "planning-revision",
        "--expect-owner-revision": "3",
        "--format": "json",
    }.items():
        assert actual[actual.index(option) + 1] == value
    assert "--apply" in actual
    assert forwarded == [actual]


def test_planning_front_door_matches_direct_integration_propose_semantics(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    repo_root = Path(__file__).resolve().parents[1]
    workspace_target = tmp_path / "workspace-front-door"
    direct_target = tmp_path / "direct-planning"
    workspace_target.mkdir()
    direct_target.mkdir()

    def invoke(program: str, argv: list[str]) -> dict[str, Any]:
        executable = shutil.which(program)
        assert executable is not None
        completed = subprocess.run(
            [executable, *argv],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)

    def integration_args(*, target: Path, planning_revision: str | None = None) -> list[str]:
        argv = [
            "integration-propose",
            "--proposal-id",
            "archive-owner-2479",
            "--owner",
            "owner-2479",
            "--owner-ref",
            ".agentic-workspace/planning/execplans/owner-2479.plan.json",
            "--issue",
            "#2479",
            "--external-ref",
            "github:#2479",
            "--requested-transition",
            "archive-owner",
            "--proof",
            "checks:passing,review:approved",
            "--parent-boundary",
            "lane remains independently open",
            "--invariant",
            "parent-current-slice,issue-relation",
            "--expect-subject-revision",
            "subject-revision",
            "--expect-target-revision",
            "target-revision",
            "--target",
            str(target),
        ]
        if planning_revision:
            argv.extend(["--expect-planning-revision", planning_revision])
        return [*argv, "--format", "json"]

    workspace_default = invoke(
        "agentic-workspace",
        ["planning", "integration-propose", "--owner", "default-owner", "--target", str(workspace_target), "--dry-run", "--format", "json"],
    )
    direct_default = invoke(
        "agentic-planning",
        ["integration-propose", "--owner", "default-owner", "--target", str(direct_target), "--dry-run", "--format", "json"],
    )

    for payload in (workspace_default, direct_default):
        receipt = payload["operation_receipt"]
        assert payload["message"] == "Propose Planning integration transition 'default-owner-mark-integrated'"
        assert receipt["proposal_id"] == "default-owner-mark-integrated"
        assert receipt["preserved_invariants"] == [
            "feature branch does not select current work",
            "feature branch does not rewrite aggregate Planning indexes",
            "feature branch does not close parent/lane lifecycle truth",
            "integration apply is target-branch authoritative",
        ]
    assert workspace_default["operation_receipt"] == direct_default["operation_receipt"]
    assert workspace_default["planning_revision"] == direct_default["planning_revision"]

    planning_revision = workspace_default["planning_revision"]["revision_id"]
    workspace_result = invoke(
        "agentic-workspace",
        ["planning", *integration_args(target=workspace_target, planning_revision=planning_revision)],
    )
    direct_result = invoke(
        "agentic-planning",
        integration_args(target=direct_target, planning_revision=planning_revision),
    )

    assert workspace_result["outcome"] == direct_result["outcome"] == "applied"
    proposal_relative = Path(".agentic-workspace/planning/integration-proposals/archive-owner-2479.integration-proposal.json")
    workspace_proposal = json.loads((workspace_target / proposal_relative).read_text(encoding="utf-8"))
    direct_proposal = json.loads((direct_target / proposal_relative).read_text(encoding="utf-8"))
    semantic_fields = (
        "id",
        "status",
        "phase",
        "requested_transition",
        "owner",
        "external_ref",
        "proof_refs",
        "parent_boundary",
        "preserved_invariants",
        "expected_subject_revision",
        "expected_planning_revision",
    )
    workspace_semantics = {field: workspace_proposal[field] for field in semantic_fields}
    direct_semantics = {field: direct_proposal[field] for field in semantic_fields}

    assert workspace_semantics == direct_semantics
    assert workspace_semantics == {
        "id": "archive-owner-2479",
        "status": "pending",
        "phase": "integration-pending",
        "requested_transition": "archive-owner",
        "owner": {"id": "owner-2479", "ref": ".agentic-workspace/planning/execplans/owner-2479.plan.json"},
        "external_ref": "github:#2479",
        "proof_refs": ["checks:passing", "review:approved"],
        "parent_boundary": "lane remains independently open",
        "preserved_invariants": ["parent-current-slice", "issue-relation"],
        "expected_subject_revision": "subject-revision",
        "expected_planning_revision": planning_revision,
    }

    external_target = tmp_path / "workspace-refresh"
    external_target.mkdir()
    invoke(
        "agentic-workspace",
        [
            "planning",
            "integration-propose",
            "--proposal-id",
            "keep-open-2479",
            "--external-ref",
            "2479",
            "--requested-transition",
            "keep-open",
            "--target",
            str(external_target),
            "--format",
            "json",
        ],
    )
    external_proposal_path = external_target / ".agentic-workspace/planning/integration-proposals/keep-open-2479.integration-proposal.json"
    external_before = json.loads(external_proposal_path.read_text(encoding="utf-8"))
    planning_installer.shape_issue_relation(issue="2479", lane="refresh", priority="p1", target=external_target)
    current_subject_revision = planning_installer._integration_subject_revision(
        target_root=external_target,
        owner_ref="",
        external_ref="2479",
    )
    current_target_revision = planning_installer.planning_revision(external_target)["target_authority_revision"]

    refreshed = invoke(
        "agentic-workspace",
        [
            "planning",
            "integration-propose",
            "--proposal-id",
            "keep-open-2479",
            "--refresh-existing",
            "--expect-proposal-revision",
            external_before["proposal_revision"],
            "--expect-subject-revision",
            current_subject_revision,
            "--expect-planning-revision",
            current_target_revision,
            "--target",
            str(external_target),
            "--format",
            "json",
        ],
    )

    external_after = json.loads(external_proposal_path.read_text(encoding="utf-8"))
    assert "operation_receipt" in refreshed, refreshed
    assert refreshed["operation_receipt"]["outcome"] == "refreshed"
    assert external_after["requested_transition"] == external_before["requested_transition"] == "keep-open"
    assert external_after["external_ref"] == external_before["external_ref"] == "2479"
    assert external_after["expected_subject_revision"] == current_subject_revision
    assert external_after["expected_planning_revision"] == current_target_revision


def test_planning_front_door_integration_archive_closeout_is_transactional_and_idempotent(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    def managed_snapshot(target: Path) -> dict[str, bytes]:
        root = target / ".agentic-workspace/planning"
        return {path.relative_to(target).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    def arrange(target: Path) -> Path:
        target.mkdir()
        _init_git_repo(target)
        assert cli.main(["init", "--target", str(target), "--modules", "planning", "--format", "json"]) == 0
        capsys.readouterr()
        owner_ref = Path(".agentic-workspace/planning/execplans/plan-alpha.plan.json")
        _write(
            target / ".agentic-workspace/planning/state.toml",
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
        record = planning_installer._build_legacy_execplan_record_from_todo_item(
            title="Plan alpha",
            item_id="plan-alpha",
            status="completed",
            why_now="Prove the public integration closeout transaction.",
            next_action="Apply the admitted integration and close out.",
            done_when="The owner is archived exactly once.",
        )
        record["execution_run"] = {
            "run status": "completed",
            "executor": "public Planning front door",
            "handoff source": "planning integration-apply",
            "what happened": "applied the bounded owner integration.",
            "scope touched": owner_ref.as_posix(),
            "changed surfaces": owner_ref.as_posix(),
            "validations run": "focused public-path behavior proof",
            "result for continuation": "no further execution is required.",
            "next step": "archive the plan.",
        }
        record["finished_run_review"] = {
            "review status": "completed",
            "scope respected": "yes",
            "proof status": "satisfied",
            "intent served": "yes",
            "config compliance": "yes",
            "misinterpretation risk": "low",
            "follow-on decision": "archive-and-close",
        }
        record["proof_report"] = {"integration proof": "display-only integration evidence"}
        record["execution_summary"]["outcome delivered"] = "Public integration and closeout behavior is ready for archive."
        record["execution_summary"]["validation confirmed"] = "Focused public-path behavior proof passed."
        record["execution_summary"]["follow-on routed to"] = "none"
        record["execution_summary"]["post-work posterity capture"] = "none"
        record["execution_summary"]["resume from"] = "archive"
        record["intent_satisfaction"] = {
            "original intent": "Prove public integration closeout.",
            "was original intent fully satisfied?": "yes",
            "evidence of intent satisfaction": "The public-path assertions observe the requested lifecycle effects.",
            "unsolved intent passed to": "none",
        }
        record["closure_check"] = {
            "slice status": "bounded slice complete",
            "larger-intent status": "closed",
            "closure decision": "archive-and-close",
            "why this decision is honest": "The integration carries admitted subject proof and the public closeout validates it.",
            "evidence carried forward": "integration receipt plus public-path behavior assertions",
            "reopen trigger": "new contradictory evidence",
        }
        record["intent_continuity"]["continuation surface"] = "#stale-continuation"
        record["required_continuation"] = {
            "required follow-on for the larger intended outcome": "yes",
            "owner surface": "#stale-continuation",
            "activation trigger": "after integration",
        }
        record["continuation"] = {"owner": "#stale-continuation", "residual_intent": "stale"}
        planning_installer._write_execplan_record(record_path=target / owner_ref, record=record)
        return owner_ref

    def propose_and_apply(target: Path, owner_ref: Path, *, proof: str) -> dict[str, Any]:
        argv = [
            "planning",
            "integration-propose",
            "--proposal-id",
            "plan-alpha-archive",
            "--owner",
            "plan-alpha",
            "--owner-ref",
            owner_ref.as_posix(),
            "--requested-transition",
            "archive-owner",
            "--target",
            str(target),
            "--format",
            "json",
        ]
        if proof:
            argv[argv.index("--target") : argv.index("--target")] = ["--proof", proof]
        assert cli.main(argv) == 0
        proposed = json.loads(capsys.readouterr().out)
        assert proposed["outcome"] == "applied"
        assert (
            cli.main(["planning", "integration-apply", "--proposal", "plan-alpha-archive", "--target", str(target), "--format", "json"])
            == 0
        )
        applied = json.loads(capsys.readouterr().out)
        assert "operation_receipt" in applied, applied
        return applied

    target = tmp_path / "admitted"
    owner_ref = arrange(target)
    owner_path = target / owner_ref
    owner_record = json.loads(owner_path.read_text(encoding="utf-8"))
    owner_record["proof"] = {"refs": ["sha256:admitted-subject-proof"]}
    planning_installer._write_execplan_record(record_path=owner_path, record=owner_record)
    applied = propose_and_apply(target, owner_ref, proof="")
    assert applied["operation_receipt"]["proof_refs"] == ["sha256:admitted-subject-proof"]
    closeout_args = [
        "planning",
        "archive-plan",
        "--plan",
        "plan-alpha",
        "--target",
        str(target),
        "--prepare-closeout",
        "--apply-cleanup",
        "--retain-archive",
        "--closure-decision",
        "archive-and-close",
        "--unsolved-intent",
        "none",
        "--format",
        "json",
    ]
    assert cli.main(closeout_args) == 0
    closed = json.loads(capsys.readouterr().out)
    assert not closed["warnings"], closed["warnings"]
    assert any(action["kind"] == "archived" for action in closed["actions"]), closed
    archived_path = target / ".agentic-workspace/planning/execplans/archive/plan-alpha.plan.json"
    archived = json.loads(archived_path.read_text(encoding="utf-8"))
    assert archived["proof_report"]["proof achieved now"] == "yes; admitted archive-owner integration receipt"
    assert archived["proof_report"]['evidence for "proof achieved" state'] == "sha256:admitted-subject-proof"
    assert archived["intent_satisfaction"]["unsolved intent passed to"] == "none"
    assert archived["required_continuation"]["owner surface"] == "none"
    assert archived["continuation"] == {"owner": "none", "residual_intent": "none"}
    after_closeout = managed_snapshot(target)
    assert cli.main(closeout_args) == 0
    replay = json.loads(capsys.readouterr().out)
    assert any(action["kind"] in {"already-current", "current"} for action in replay["actions"])
    assert managed_snapshot(target) == after_closeout

    rejected_target = tmp_path / "missing-subject-proof"
    rejected_owner_ref = arrange(rejected_target)
    rejected_apply = propose_and_apply(rejected_target, rejected_owner_ref, proof="")
    assert rejected_apply["operation_receipt"]["proof_refs"] == []
    before_rejected_closeout = managed_snapshot(rejected_target)
    rejected_args = [*closeout_args]
    rejected_args[rejected_args.index(str(target))] = str(rejected_target)
    assert cli.main(rejected_args) == 0
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["reason_code"] == "integration-closeout-proof-insufficient"
    assert managed_snapshot(rejected_target) == before_rejected_closeout

    def closeout_for(target_override: Path, *extra: str) -> dict[str, Any]:
        args = [*closeout_args]
        args[args.index(str(target))] = str(target_override)
        if extra:
            for option in ("--intent-satisfied", "--closure-decision", "--unsolved-intent"):
                if option in args:
                    option_index = args.index(option)
                    del args[option_index : option_index + 2]
            args[args.index("--format") : args.index("--format")] = list(extra)
        assert cli.main(args) == 0
        return json.loads(capsys.readouterr().out)

    stale_target = tmp_path / "stale-proof-receipt"
    stale_owner_ref = arrange(stale_target)
    propose_and_apply(stale_target, stale_owner_ref, proof="sha256:admitted-subject-proof")
    stale_record = json.loads((stale_target / stale_owner_ref).read_text(encoding="utf-8"))
    stale_receipt_path = stale_target / stale_record["relationships"]["integration"]["receipt_ref"]
    stale_receipt = json.loads(stale_receipt_path.read_text(encoding="utf-8"))
    stale_receipt["proof_refs"].append("sha256:receipt-changed-after-admission")
    stale_receipt_path.write_text(json.dumps(stale_receipt, indent=2) + "\n", encoding="utf-8")
    before_stale_closeout = managed_snapshot(stale_target)
    stale = closeout_for(stale_target)
    assert stale["reason_code"] == "integration-closeout-receipt-revision-mismatch"
    assert managed_snapshot(stale_target) == before_stale_closeout

    mismatch_target = tmp_path / "mismatched-proof-reference"
    mismatch_owner_ref = arrange(mismatch_target)
    propose_and_apply(mismatch_target, mismatch_owner_ref, proof="sha256:admitted-subject-proof")
    mismatch_record_path = mismatch_target / mismatch_owner_ref
    mismatch_record = json.loads(mismatch_record_path.read_text(encoding="utf-8"))
    mismatch_record["relationships"]["integration"]["proof_refs"] = ["sha256:different-subject-proof"]
    planning_installer._write_execplan_record(record_path=mismatch_record_path, record=mismatch_record)
    before_mismatch_closeout = managed_snapshot(mismatch_target)
    mismatch = closeout_for(mismatch_target)
    assert mismatch["reason_code"] == "integration-closeout-proof-mismatch"
    assert managed_snapshot(mismatch_target) == before_mismatch_closeout

    unsatisfied_target = tmp_path / "unsatisfied-intent"
    unsatisfied_owner_ref = arrange(unsatisfied_target)
    propose_and_apply(unsatisfied_target, unsatisfied_owner_ref, proof="sha256:admitted-subject-proof")
    before_unsatisfied_closeout = managed_snapshot(unsatisfied_target)
    unsatisfied = closeout_for(
        unsatisfied_target,
        "--closure-decision",
        "archive-and-close",
        "--intent-satisfied",
        "no",
        "--unsolved-intent",
        "none",
    )
    assert any(action["kind"] in {"manual review", "blocked-with-reason", "rolled back"} for action in unsatisfied["actions"])
    assert not any(action["kind"] == "archived" for action in unsatisfied["actions"])
    assert managed_snapshot(unsatisfied_target) == before_unsatisfied_closeout

    continued_target = tmp_path / "retained-intent"
    continued_owner_ref = arrange(continued_target)
    propose_and_apply(continued_target, continued_owner_ref, proof="sha256:admitted-subject-proof")
    continued = closeout_for(
        continued_target,
        "--closure-decision",
        "archive-but-keep-lane-open",
        "--intent-satisfied",
        "no",
        "--unsolved-intent",
        "GitHub #next-owner",
    )
    assert any(action["kind"] == "archived" for action in continued["actions"]), continued
    continued_archive = json.loads(
        (continued_target / ".agentic-workspace/planning/execplans/archive/plan-alpha.plan.json").read_text(encoding="utf-8")
    )
    assert continued_archive["intent_satisfaction"]["unsolved intent passed to"] == "GitHub #next-owner"
    assert continued_archive["required_continuation"]["owner surface"] == "GitHub #next-owner"
    assert continued_archive["continuation"]["owner"] == "GitHub #next-owner"
    assert cli.main(["planning", "report", "--target", str(continued_target), "--verbose", "--format", "json"]) == 0
    planning_report = json.loads(capsys.readouterr().out)
    inspection = planning_report["finished_work_inspection"]["inspections"][0]
    assert inspection["classification"] == "unowned_partial"
    assert inspection["unsolved_intent"] == "GitHub #next-owner"


def test_planning_front_door_forwards_lane_lifecycle_positionals(monkeypatch, tmp_path: Path, capsys) -> None:
    forwarded: list[list[str]] = []

    def fake_planning_main(argv: list[str]) -> int:
        forwarded.append(argv)
        print(json.dumps({"argv": argv}))
        return 0

    def option_value(argv: list[str], option: str) -> str:
        return argv[argv.index(option) + 1]

    monkeypatch.setattr("repo_planning_bootstrap.cli.main", fake_planning_main)

    assert (
        cli.main(
            [
                "planning",
                "lane-promote",
                "lane-artifacts",
                "--alternate-lane-id",
                "lane-artifacts-from-parent",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    forwarded_promote = json.loads(capsys.readouterr().out)["argv"]
    assert forwarded_promote[:2] == ["lane-promote", "lane-artifacts"]
    assert option_value(forwarded_promote, "--alternate-lane-id") == "lane-artifacts-from-parent"
    assert option_value(forwarded_promote, "--target") == str(tmp_path)
    assert option_value(forwarded_promote, "--format") == "json"

    assert (
        cli.main(
            [
                "planning",
                "lane-activate",
                "lane-alpha",
                "--current-slice",
                "slice-one",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["argv"] == [
        "lane-activate",
        "lane-alpha",
        "--target",
        str(tmp_path),
        "--current-slice",
        "slice-one",
        "--format",
        "json",
    ]

    assert cli.main(["planning", "lane-close", "lane-alpha", "--proof", "proof passed", "--format", "json"]) == 0
    forwarded_close = json.loads(capsys.readouterr().out)["argv"]
    assert forwarded_close[:2] == ["lane-close", "lane-alpha"]
    assert option_value(forwarded_close, "--proof") == "proof passed"
    assert option_value(forwarded_close, "--format") == "json"

    assert cli.main(["planning", "lane-archive", "lane-alpha", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["argv"] == ["lane-archive", "lane-alpha", "--format", "json"]


def test_planning_front_door_lane_activation_recovery_does_not_fabricate_plan(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "planning",
                "lane-create",
                "--id",
                "lane-alpha",
                "--title",
                "Lane Alpha",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["planning", "lane-activate", "lane-alpha", "--target", str(tmp_path), "--format", "json"]) == 0
    activation = json.loads(capsys.readouterr().out)
    assert activation["reason_code"] == "lane-execplan-required"
    assert "new-plan" not in activation["recovery_command"]
    recovery_args = shlex.split(activation["recovery_command"])
    planning_index = recovery_args.index("planning")
    monkeypatch.chdir(tmp_path)

    assert cli.main(recovery_args[planning_index:]) == 0
    payload = json.loads(capsys.readouterr().out)

    blocked_reconcile = payload["lane_current_slice_reconciliation"]
    assert blocked_reconcile["status"] == "human-selection-required"
    assert blocked_reconcile["reason_code"] == "human-owner-selection-required"
    assert blocked_reconcile["decision"] == "no-write"
    assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    lane = json.loads((tmp_path / ".agentic-workspace/planning/lanes/lane-alpha.lane.json").read_text(encoding="utf-8"))
    assert lane["status"] != "active"
    assert not any("execplan_ref" in item for item in lane.get("slice_sequence", []) if isinstance(item, dict))

    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "lane-alpha-slice",
                "--title",
                "Lane Alpha Slice",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    lane["status"] = "active"
    lane["current_slice"] = "lane-alpha-slice"
    lane["slice_sequence"] = [
        {
            "id": "lane-alpha-slice",
            "title": "Lane Alpha Slice",
            "status": "active",
            "execplan_ref": "",
            "depends_on": [],
            "purpose_for_lane": "Malformed existing relation repaired by guarded reconciliation.",
        }
    ]
    (tmp_path / ".agentic-workspace/planning/lanes/lane-alpha.lane.json").write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")

    preview_args = [
        "planning",
        "reconcile",
        "--lane",
        "lane-alpha",
        "--transition",
        "relink",
        "--expected-execplan",
        ".agentic-workspace/planning/execplans/lane-alpha-slice.plan.json",
        "--target",
        str(tmp_path),
        "--format",
        "json",
    ]
    assert cli.main(preview_args) == 0
    preview_payload = json.loads(capsys.readouterr().out)
    preview_reconcile = preview_payload["lane_current_slice_reconciliation"]
    assert preview_reconcile["status"] == "preview"
    apply_args = [
        *preview_args,
        "--apply-lane-current-slice-reconcile",
        "--owner-surface",
        preview_reconcile["owner_surface"],
        "--relation-identity",
        preview_reconcile["relation_identity"],
        "--subject",
        preview_reconcile["subject_id"],
        "--expect-lane-revision",
        preview_reconcile["current_lane_revision"],
        "--expect-planning-revision",
        preview_reconcile["current_planning_revision"],
    ]
    assert cli.main(apply_args) == 0
    payload = json.loads(capsys.readouterr().out)
    restored_reconcile = payload["lane_current_slice_reconciliation"]

    assert restored_reconcile["status"] == "applied"
    assert restored_reconcile["transition"] == "relink"
    assert restored_reconcile["expected_lane_revision"]
    assert restored_reconcile["receipt"]["planning_revision_before"] == preview_reconcile["current_planning_revision"]
    assert restored_reconcile["receipt"]["changed_fields"]["lane"] == ["slice_sequence"]
    assert any(
        "relink lane current-slice relation 'lane-alpha-slice' on lane 'lane-alpha'" in action["detail"]
        for action in restored_reconcile["actions"]
    )
    assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    lane = json.loads((tmp_path / ".agentic-workspace/planning/lanes/lane-alpha.lane.json").read_text(encoding="utf-8"))
    assert lane["status"] == "active"
    assert lane["current_slice"] == "lane-alpha-slice"
    assert lane["slice_sequence"][0]["execplan_ref"] == ".agentic-workspace/planning/execplans/lane-alpha-slice.plan.json"
    assert cli.main(apply_args) == 0
    replay = json.loads(capsys.readouterr().out)["lane_current_slice_reconciliation"]
    assert replay["status"] == "already-applied"
    assert replay["reason_code"] == "idempotent-replay"

    assert cli.main(["summary", "--target", str(tmp_path), "--select", "lanes", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)["values"]
    assert summary["lanes"]["record_count"] == 1

    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    doctor_text = json.dumps(doctor)
    assert "execplan_unregistered" not in doctor_text
    assert "planning_lane_schema_invalid" not in doctor_text

    assert cli.main(["start", "--target", str(tmp_path), "--task", "fresh lane startup", "--format", "json"]) == 0
    startup = json.loads(capsys.readouterr().out)
    startup_text = json.dumps(startup)
    assert "execplan_unregistered" not in startup_text
    assert "planning_lane_schema_invalid" not in startup_text


def test_missing_current_slice_repair_commands_replay_unchanged(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "planning",
                "lane-create",
                "--id",
                "lane-alpha",
                "--title",
                "Lane Alpha",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "slice-one",
                "--title",
                "Slice One",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    lane_path = tmp_path / ".agentic-workspace/planning/lanes/lane-alpha.lane.json"
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    lane["status"] = "active"
    lane["current_slice"] = ""
    lane["slice_sequence"] = [
        {
            "id": "slice-one",
            "title": "Slice One",
            "status": "active",
            "execplan_ref": ".agentic-workspace/planning/execplans/slice-one.plan.json",
            "depends_on": [],
            "purpose_for_lane": "Executable replacement.",
        }
    ]
    lane_path.write_text(json.dumps(lane, indent=2) + "\n", encoding="utf-8")

    assert cli.main(["summary", "--target", str(tmp_path), "--select", "planning_surface_health", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)["values"]
    warning = next(
        item
        for item in summary["planning_surface_health"]["warnings"]
        if item["repair_affordance"]["reason_code"] == "active-lane-current-slice-missing"
    )
    option = next(item for item in warning["repair_affordance"]["repair_options"] if item["action"] == "supersede-absent-relation")

    monkeypatch.chdir(tmp_path)
    preview_args = shlex.split(option["preview_command"])
    preview_args = preview_args[preview_args.index("planning") :]
    assert cli.main(preview_args) == 0
    preview = json.loads(capsys.readouterr().out)["lane_current_slice_reconciliation"]
    assert preview["status"] == "preview", preview
    assert preview["relation_identity"] == "lane:lane-alpha:current_slice:__absent__"
    assert preview["subject_id"] == "__absent__"

    apply_args = shlex.split(option["apply_command"])
    apply_args = apply_args[apply_args.index("planning") :]
    assert cli.main(apply_args) == 0
    applied = json.loads(capsys.readouterr().out)["lane_current_slice_reconciliation"]
    assert applied["status"] == "applied"
    assert json.loads(lane_path.read_text(encoding="utf-8"))["current_slice"] == "slice-one"

    assert cli.main(apply_args) == 0
    replay = json.loads(capsys.readouterr().out)["lane_current_slice_reconciliation"]
    assert replay["status"] == "already-applied"
    assert replay["reason_code"] == "idempotent-replay"

    assert cli.main(["summary", "--target", str(tmp_path), "--select", "planning_surface_health", "--format", "json"]) == 0
    post_summary = json.loads(capsys.readouterr().out)["values"]
    assert not [
        item
        for item in post_summary["planning_surface_health"]["warnings"]
        if item.get("repair_affordance", {}).get("reason_code") == "active-lane-current-slice-missing"
    ]


def test_summary_and_config_support_exact_field_selectors(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["summary", "--target", str(tmp_path), "--select", "target_root,todo.active_count", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["kind"] == "agentic-workspace/selected-output/v1"
    assert summary["source_command"] == "summary"
    assert summary["selection_cost"]["profile_loaded"] == "tiny"
    assert summary["selection_cost"]["fallback_profile_loaded"] is False
    assert Path(summary["values"]["target_root"]) == tmp_path
    assert summary["values"]["todo.active_count"] == 0
    assert "missing" not in summary

    assert cli.main(["summary", "--target", str(tmp_path), "--select", "planning_record", "--format", "json"]) == 0
    summary_full_field = json.loads(capsys.readouterr().out)
    assert summary_full_field["selection_cost"]["profile_loaded"] == "query-shaped-direct"
    assert summary_full_field["selection_cost"]["fallback_profile_loaded"] is False
    assert summary_full_field["selection_cost"]["historical_sources_loaded"] is False
    assert "planning_record" in summary_full_field["values"]

    assert (
        cli.main(
            [
                "config",
                "--target",
                str(tmp_path),
                "--select",
                "workspace.enabled_modules,mixed_agent.runtime_resolution",
                "--format",
                "json",
            ]
        )
        == 0
    )
    config = json.loads(capsys.readouterr().out)
    assert config["kind"] == "agentic-workspace/selected-output/v1"
    assert config["source_command"] == "config"
    assert config["values"]["workspace.enabled_modules"] == ["planning", "memory"]
    assert "recommendation" in config["values"]["mixed_agent.runtime_resolution"]
    assert "missing" not in config


def test_summary_fresh_session_digest_is_selector_backed(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    evidence_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "#1680",
                        "system": "github",
                        "status": "open",
                        "kind": "issue",
                        "title": "[Workspace]: Reduce AW-induced completion cost",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #1680 lane",
                "--changed",
                "docs/reviews/example.md",
                "--select",
                "fresh_session_digest",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    digest = payload["values"]["fresh_session_digest"]

    assert payload["selection_cost"]["profile_loaded"] == "tiny"
    assert digest["kind"] == "agentic-workspace/fresh-session-digest/v1"
    assert digest["issue_refs"] == ["#1680"]
    assert digest["issue_evidence"]["status"] == "available"
    assert digest["issue_evidence"]["items"][0]["title"] == "[Workspace]: Reduce AW-induced completion cost"
    assert digest["changed_paths"] == ["docs/reviews/example.md"]
    assert digest["source_artifacts"] == [
        ".agentic-workspace/local/cache/external-intent-evidence.json",
        "docs/reviews/example.md",
        "GitHub issue refs listed in issue_refs",
    ]
    assert digest["closure_boundary"]["may_claim_parent_closure"] is False
    assert "cannot close issues" in digest["closure_boundary"]["rule"]
    assert digest["safe_next_command"].endswith('start --target . --task "<next task>" --format json')
    assert "refresh_issue_evidence" in digest["detail_commands"]


def test_summary_fresh_session_digest_omits_unrelated_lane_artifacts(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    evidence_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "#42",
                        "system": "github",
                        "status": "open",
                        "kind": "issue",
                        "title": "Unrelated docs task",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #42 docs lane",
                "--changed",
                "docs/notes/unrelated.md",
                "--select",
                "fresh_session_digest",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload_text = capsys.readouterr().out
    digest = json.loads(payload_text)["values"]["fresh_session_digest"]

    assert digest["issue_refs"] == ["#42"]
    assert digest["source_artifacts"] == [
        ".agentic-workspace/local/cache/external-intent-evidence.json",
        "docs/notes/unrelated.md",
        "GitHub issue refs listed in issue_refs",
    ]
    assert "#1680" not in payload_text
    assert "aw-completion-cost-session-log-analysis-2026-06-23.md" not in payload_text


def test_start_exposes_workflow_sufficiency_and_continuation_selectors(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix one docs typo",
                "--select",
                "workflow_sufficiency,continuation_state",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["values"]["workflow_sufficiency"]["kind"] == "agentic-workspace/workflow-sufficiency/v1"
    assert payload["values"]["workflow_sufficiency"]["sufficiency_result"] == "enough-for-first-contact-routing"
    assert payload["values"]["workflow_sufficiency"]["required_next_action"] == "choose-smallest-workflow-shape"
    continuation = payload["values"]["continuation_state"]
    assert continuation["kind"] == "agentic-workspace/compact-continuation-state/v1"
    assert continuation["fields"] == [
        "goal",
        "current_branch_or_state",
        "files_touched",
        "known_failing_tests",
        "next_intended_step",
        "open_questions",
    ]


def test_start_default_routes_memory_and_installed_state_detail_behind_selectors(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert "memory_decision_packet" not in payload
    assert "installed_state_compatibility" not in payload
    assert set(payload) == {"kind", "target", "decision_packet", "task_assignment_disposition"}
    assert "--select <field[,field...]>" in payload["decision_packet"]["detail_routes"]["select"]

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--select",
                "memory_decision_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)
    assert "memory_decision_packet" in selected["values"]


def test_start_defers_local_footprint_scan_until_selector_requests_it(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[local_scratch_retention]\nwarn_total_bytes = 1\nlocal_aw_warn_bytes = 1\n",
    )
    _write(tmp_path / ".agentic-workspace" / "local" / "scratch" / "legacy" / "artifact.txt", "legacy\n")

    original_local_footprint = cli._local_footprint_payload

    def fail_default_scan(**_kwargs: object) -> dict[str, object]:
        raise AssertionError("default startup must not scan local footprint")

    monkeypatch.setattr(cli, "_local_footprint_payload", fail_default_scan)
    assert cli.main(["start", "--target", str(tmp_path), "--task", "inspect repo", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert "local_footprint" not in payload

    monkeypatch.setattr(cli, "_local_footprint_payload", original_local_footprint)
    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_footprint", "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)["values"]["local_footprint"]
    assert selected["status"] == "attention"
    assert selected["scratch_retention"]["legacy_entry_count"] == 1
    assert "--target ./repo" not in selected["detail_command"]
    assert "report --target " in selected["detail_command"]
    assert "--section local_footprint --format json" in selected["detail_command"]


def test_start_exposes_communication_contract_through_selector(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix one docs typo",
                "--select",
                "communication_contract,message_economy,current_decision,evidence_bundle",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)["values"]
    contract = payload["communication_contract"]
    assert contract["kind"] == "agentic-workspace/communication-contract/v1"
    assert contract["default_posture"] == "decision_first_state_backed"
    assert contract["narration_budget"] == "minimal"
    assert "startup" in contract["phase_ids"]
    assert "stale_missing_or_failed_proof" in contract["expand_when"]
    assert contract["cost_evaluation"]["preserve"] == [
        "evidence",
        "proof_boundary",
        "unresolved_residue",
        "next_safe_action",
    ]
    message_economy = payload["message_economy"]
    assert message_economy["kind"] == "agentic-workspace/message-economy/v1"
    assert message_economy["surface"] == "startup"
    assert "decision_changed" in message_economy["speak_when"]
    assert "state_unchanged" in message_economy["stay_compact_when"]
    assert "stale_missing_or_failed_proof" in message_economy["expand_when"]
    assert "proof_boundary" in message_economy["preserve"]
    assert "residue_or_claim_boundary" in message_economy["preserve"]
    assert "user_requests_detail" in message_economy["expand_when"]
    current_decision = payload["current_decision"]
    assert current_decision["kind"] == "agentic-workspace/current-decision/v1"
    assert current_decision["surface"] == "startup"
    assert current_decision["decision_question"] == "Startup posture?"
    assert current_decision["response_shape"] == [
        "decision_or_finding",
        "evidence_or_proof_boundary",
        "residue_or_claim_boundary",
        "next_safe_action",
    ]
    assert "repeated_context_reconstruction" in current_decision["avoid_repeat"]
    assert current_decision["state_backed"] is True
    assert "continuation_capsule" not in payload
    bundle = payload["evidence_bundle"]
    assert bundle["kind"] == "agentic-workspace/evidence-bundle/v1"
    assert bundle["surface"] == "startup"
    assert bundle["supports_decision"] == "Startup posture?"
    assert bundle["minimal_evidence_surfaces"][0]["id"] == "why_blocked"
    assert "residue owner is unresolved" in bundle["escalate_when"]


def test_start_select_surfaces_state_delta_packets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix one docs typo",
                "--select",
                "current_decision,message_economy,evidence_bundle,visible_state_delta_response",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    values = payload["values"]
    assert payload.get("missing", []) == []
    assert values["current_decision"]["kind"] == "agentic-workspace/current-decision/v1"
    assert values["current_decision"]["decision_question"] == "Startup posture?"
    assert values["current_decision"]["known_evidence"] == ["next_safe_action"]
    assert values["current_decision"]["response_shape"] == [
        "decision_or_finding",
        "evidence_or_proof_boundary",
        "residue_or_claim_boundary",
        "next_safe_action",
    ]
    assert values["current_decision"]["state_backed"] is True
    assert values["message_economy"]["surface"] == "startup"
    assert values["message_economy"]["state_backed"] is True
    assert "repeated_state_recaps" in values["message_economy"]["discourage"]
    assert values["evidence_bundle"]["supports_decision"] == "Startup posture?"
    assert values["evidence_bundle"]["minimal_evidence_surfaces"][0]["id"] == "why_blocked"
    assert values["evidence_bundle"]["state_backed"] is True
    visible = values["visible_state_delta_response"]
    assert visible["status"] == "ready"
    assert visible["route_budget"]["max_report_scans"] == 1
    assert visible["route_budget"]["generated_action_policy"] == "never-verbose-without-explicit-expansion"
    assert visible["observed_cost"] == {
        "generated_next_actions": 1,
        "report_scans": 1,
        "verbose_generated_actions": 0,
        "visible_part_count": 4,
        "snapshot_loads": 1,
        "snapshot_reused": True,
    }
    assert visible["composed_closeout"]["requires_additional_report_scan"] is False

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/example.md",
                "--select",
                "visible_state_delta_response",
                "--format",
                "json",
            ]
        )
        == 0
    )
    implementation_visible = json.loads(capsys.readouterr().out)["values"]["visible_state_delta_response"]
    assert implementation_visible["route_budget"]["status"] == "within-budget"
    assert implementation_visible["observed_cost"]["generated_next_actions"] == 1
    assert implementation_visible["observed_cost"]["report_scans"] == 1
    assert implementation_visible["observed_cost"]["snapshot_loads"] == 1
    assert implementation_visible["observed_cost"]["snapshot_reused"] is True
    assert implementation_visible["observed_cost"]["verbose_generated_actions"] == 0
    assert implementation_visible["observed_cost"]["visible_part_count"] == 4

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--select",
                "closeout_trust_inspection",
                "--format",
                "json",
            ]
        )
        == 0
    )
    closeout = json.loads(capsys.readouterr().out)["values"]["closeout_trust_inspection"]
    measurement = closeout["state_delta_measurement"]
    assert measurement["workflow_class"] == "closeout"
    assert measurement["source"] == "ordinary closeout planning_report load boundary"
    assert measurement["observed_cost"]["report_scans"] == 1
    assert measurement["observed_cost"]["snapshot_loads"] == 1
    assert measurement["observed_cost"]["snapshot_reused"] is True


def test_start_exposes_continuation_capsule_when_active_planning_exists(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "capsule-plan",
                "--title",
                "Capsule plan",
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

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Capsule plan",
                "--select",
                "continuation_capsule,current_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    values = payload["values"]

    capsule = values["continuation_capsule"]
    assert capsule["kind"] == "agentic-workspace/continuation-capsule/v1"
    assert capsule["surface"] == "startup"
    assert capsule["current_decision"]["question"] == "Startup posture?"
    assert capsule["proof_boundary"] == values["current_decision"]["proof_boundary"]
    assert capsule["known_evidence"][0] == values["current_decision"]["known_evidence"][0]
    assert capsule["do_not_repeat"] == values["current_decision"]["avoid_repeat"]


def test_start_embeds_active_planning_orientation_without_immediate_summary_rerun(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "orientation-plan",
                "--title",
                "Orientation plan",
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

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Orientation plan", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    active_plan_route = payload["decision_packet"]["detail_routes"]["owner_detail"]
    assert "summary --target . --select continuation_view" in active_plan_route
    assert "start --target . --select active_state_summary,continuation_view" not in active_plan_route
    from agentic_workspace.workspace_runtime_startup import _startup_detail_routes
    from agentic_workspace.workspace_selector_validation import _detail_route_command_validation

    default_route = _startup_detail_routes(cli_invoke="agentic-workspace", active_planning=True)["active_plan"]
    for route in (active_plan_route, default_route):
        validation = _detail_route_command_validation(route)
        argv = shlex.split(route)[validation["command_index"] :]
        argv[argv.index("--target") + 1] = str(tmp_path)
        assert cli.main(argv) == 0
        selected = json.loads(capsys.readouterr().out)
        assert selected["kind"] == "agentic-workspace/selected-output/v1"
        assert selected["values"]["continuation_view"]["status"]


@pytest.mark.parametrize("active_planning", [False, True])
@pytest.mark.parametrize("cli_invoke", ["agentic-workspace", "uv run --active python scripts/run_agentic_workspace.py"])
def test_startup_detail_routes_follow_authoritative_selector_ownership(cli_invoke: str, active_planning: bool) -> None:
    from agentic_workspace.workspace_runtime_startup import _startup_detail_routes
    from agentic_workspace.workspace_selector_validation import _detail_route_command_validation

    routes = _startup_detail_routes(cli_invoke=cli_invoke, active_planning=active_planning)

    assert set(routes) == {"why_blocked", "active_plan", "proof_detail"}
    validations = {route_id: _detail_route_command_validation(command) for route_id, command in routes.items()}
    assert all(validation["status"] == "valid" for validation in validations.values())
    assert validations["active_plan"]["source_command"] == "summary"
    assert validations["active_plan"]["selectors"] == (["continuation_view"] if active_planning else [])
    assert validations["why_blocked"]["executable"] is True
    assert validations["active_plan"]["executable"] is True
    assert validations["proof_detail"]["executable"] is False


def test_detail_route_validation_rejects_cross_command_selector() -> None:
    from agentic_workspace.workspace_selector_validation import _detail_route_command_validation, _validated_detail_route_command

    invalid_route = "agentic-workspace start --target . --select active_state_summary,continuation_view --format json"
    validation = _detail_route_command_validation(invalid_route)

    assert validation["status"] == "invalid"
    assert validation["reason"] == "selector-owner-mismatch"
    assert validation["unknown_selectors"] == ["continuation_view"]
    with pytest.raises(ValueError, match="selector-owner-mismatch"):
        _validated_detail_route_command(invalid_route)


def test_start_surfaces_configured_pre_test_guardrail_without_universal_bug_keyword(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.requirements.test_evidence_change_decision]
level = "high"
applies_to_paths = ["tests/**"]
applies_to_task_markers = ["regression test"]
required_evidence = ["verification_proof_decision_review"]
proof_profile = "test_evidence_change"
force = "required-before-closeout"
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix the runtime issue by adding a regression test",
                "--select",
                "pre_test_evidence_guardrail,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    payload = payload["values"]
    guardrail = payload["pre_test_evidence_guardrail"]
    assert guardrail["status"] == "advisory"
    assert guardrail["blocking"] is False
    assert guardrail["source_boundary"]["no_universal_task_keyword_policy"] is True
    assert any("task marker matched regression test" in source for source in guardrail["trigger_sources"])
    assert "package-local-behavior" in guardrail["evidence_owner_options"]
    assert "convert-to-conformance" in guardrail["proof_decision_options"]
    assert any("trust question" in question for question in guardrail["pre_test_decision_questions"])

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix a bug in the README",
                "--select",
                "pre_test_evidence_guardrail,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    quiet_payload = json.loads(capsys.readouterr().out)["values"]
    assert "pre_test_evidence_guardrail" not in quiet_payload


def test_start_default_compacts_noncompatible_installed_state_signal(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert "installed_state_compatibility" not in payload
    assert "installed_state_compatibility=payload-upgrade-required" in {item["signal"] for item in payload["decision_packet"]["attention"]}
    assert any(item["detail_selector"] == "installed_state_compatibility" for item in payload["decision_packet"]["attention"])

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)
    full = selected["values"]["installed_state_compatibility"]
    assert full["status"] == "payload-upgrade-required"
    assert full["action_state"]["state"] == "safe_payload_sync_available"
    assert full["action_state"]["repair_mechanism"] == "upgrade"
    assert full["action_state"]["safe_to_apply"] is True
    assert full["action_state"]["mutates_on_start"] is False
    assert "agentic-workspace upgrade" in full["action_state"]["dry_run_command"]
    assert full["payload"]["provenance"]["status"] == "invalid"
    assert full["action_effect"]["force"] == "required_before_claim"
    assert full["action_effect"]["allowed_now"] == "continue-bounded-work-with-compatible-claim-limits"
    assert full["action_effect"]["blocked_until_reconciled"] == [
        "claim-installed-state-fresh",
        "claim-payload-synced",
        "claim-generated-surfaces-current",
    ]
    assert full["action_effect"]["resolution_selector"] == "installed_state_compatibility"
    assert "agentic-workspace upgrade" in full["action_effect"]["resolution_command"]
    assert full["adapter_contracts"]

    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    setup_payload = json.loads(capsys.readouterr().out)
    assert setup_payload["installed_state_attention"]["status"] == "payload-upgrade-required"
    assert setup_payload["installed_state_attention"]["selector"] == "installed_state_compatibility"
    assert "start --target . --select installed_state_compatibility" in setup_payload["installed_state_attention"]["detail_command"]
    assert setup_payload["installed_state_compatibility"]["action_state"]["state"] == "safe_payload_sync_available"
    assert setup_payload["next_action"]["summary"].startswith("Resolve installed-state compatibility")


def test_start_installed_state_treats_stale_compatible_provenance_as_no_repair_needed(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    provenance_path = tmp_path / ".agentic-workspace" / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["release_identity"]["version"] = "0.0.1"
    provenance["release_identity"]["tag"] = "v0.0.1"
    provenance["installed_by"]["version"] = "0.0.1"
    provenance["installed_by"]["source_class"] = "source-checkout"
    provenance["installed_by"]["source"] = "local-source"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]

    assert compatibility["status"] == "compatible"
    assert compatibility["payload"]["status"] == "observed-compatible"
    assert compatibility["payload"]["provenance_drift"] == "payload-installed-by-older-aw"
    assert compatibility["action_state"]["state"] == "no_repair_needed"
    assert compatibility["action_state"]["compatibility_basis"]["version_match_required"] is False
    assert compatibility["repair_route"]["status"] == "not-required"
    assert compatibility["action_effect"]["blocked_until_reconciled"] == []


def test_payload_target_required_before_work_blocks_start_until_target_sync(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        "schema_version = 1\n\n"
        "[payload]\n"
        'target_release = "source-current"\n'
        'minimum_capabilities = ["installed-state-sync-v2"]\n'
        'policy = "required-before-work"\n'
        "dogfood_latest = true\n",
        encoding="utf-8",
    )
    provenance_path = workspace / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("payload_capabilities", None)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Do ordinary work", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    decision = payload["decision_packet"]
    assert decision["action"]["id"] == "run-installed-payload-target-upgrade"
    assert decision["effects"]["implementation_allowed"] is False
    assert "--to-payload-target --dry-run" in decision["action"]["command"]
    assert "installed_state_compatibility=payload-upgrade-required" in {item["signal"] for item in decision["attention"]}

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    assert compatibility["payload"]["target"]["status"] == "target-mismatch"
    assert compatibility["payload"]["target"]["policy"] == "required-before-work"
    assert compatibility["action_state"]["repair_mechanism"] == "payload-target-upgrade"
    assert compatibility["action_state"]["mutates_on_start"] is False
    assert "--to-payload-target --dry-run" in compatibility["action_state"]["dry_run_command"]
    assert compatibility["action_effect"]["force"] == "required_before_execution"
    assert compatibility["action_effect"]["allowed_now"] == "run-payload-target-upgrade-before-ordinary-work"
    attention_plan = compatibility["payload_upgrade_attention_plan"]
    assert attention_plan["kind"] == "agentic-workspace/payload-upgrade-attention-plan/v1"
    assert attention_plan["status"] == "explicit_apply_required"
    assert attention_plan["strategy"] == "converge-to-current-contract"
    assert attention_plan["release_instruction_policy"]["uses_release_history"] is False
    assert attention_plan["category_counts"]["auto_applied"] >= 1
    assert attention_plan["action_semantics"]["safe_explicit_apply"] is True
    assert attention_plan["action_semantics"]["manual_review_required"] is False
    assert attention_plan["command_boundary"]["reportable_commands"]["dry_run"].startswith("agentic-workspace upgrade --target .")

    assert tmp_path.as_posix() in attention_plan["command_boundary"]["machine_commands"]["dry_run"]
    assert all("release" not in item["required_action"].lower() for item in attention_plan["attention_items"])
    assert compatibility["payload_surface_manifest"]["kind"] == "agentic-workspace/payload-surface-manifest/v1"

    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert "installed_state_compatibility" not in doctor_payload
    assert doctor_payload["installed_state_summary"]["target_status"] == "target-mismatch"
    assert doctor_payload["installed_state_summary"]["action_effect"]["force"] == "required_before_execution"
    assert doctor_payload["installed_state_summary"]["action_required"] is True
    assert "installed_state_compatibility" in doctor_payload["diagnostic_detail"]["selectors"]

    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json", "--select", "installed_state_compatibility"]) == 0
    selected_doctor = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    assert selected_doctor["payload"]["target"]["status"] == "target-mismatch"
    assert selected_doctor["action_effect"]["force"] == "required_before_execution"
    selected_plan = selected_doctor["payload_upgrade_attention_plan"]
    assert selected_plan["status"] in {"explicit_apply_required", "manual_attention_required"}
    if selected_plan["status"] == "manual_attention_required":
        assert selected_plan["action_semantics"]["manual_review_required"] is True

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    report_payload = json.loads(capsys.readouterr().out)
    assert report_payload["answer"]["payload"]["target"]["status"] == "target-mismatch"
    assert report_payload["answer"]["action_state"]["recheck_command"]
    assert report_payload["answer"]["payload_upgrade_attention_plan"]["status"] == attention_plan["status"]


def test_payload_target_drift_keeps_unrelated_read_only_start_actionable(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        "schema_version = 1\n\n"
        "[payload]\n"
        'target_release = "source-current"\n'
        'minimum_capabilities = ["installed-state-sync-v2"]\n'
        'policy = "required-before-work"\n'
        "dogfood_latest = true\n",
        encoding="utf-8",
    )
    provenance_path = workspace / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("payload_capabilities", None)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    task = "Review recent Agentic Workspace dogfooding experience and identify remaining problems"
    assert cli.main(["start", "--target", str(tmp_path), "--task", task, "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    decision = payload["decision_packet"]
    assert decision["action"]["id"] == "continue-read-only-source-evidence-review"
    assert decision["effects"]["implementation_allowed"] is False
    assert decision["effects"]["read_only_allowed"] is True
    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                task,
                "--select",
                "installed_state_read_only_scope",
                "--format",
                "json",
            ]
        )
        == 0
    )
    scope = json.loads(capsys.readouterr().out)["values"]["installed_state_read_only_scope"]
    assert scope["repair_deferred"] is True
    assert "--to-payload-target --dry-run" in scope["repair_command"]
    assert "installed runtime behavior" in scope["blocked_conclusions"]
    assert "installed_state_compatibility=payload-upgrade-required" in {item["signal"] for item in decision["attention"]}
    assert len(json.dumps(payload, separators=(",", ":")).encode()) <= 10_000


def test_upgrade_to_payload_target_forces_provenance_capability_sync(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        "schema_version = 1\n\n"
        "[payload]\n"
        'target_release = "source-current"\n'
        'minimum_capabilities = ["installed-state-sync-v2"]\n'
        'policy = "required-before-claim"\n',
        encoding="utf-8",
    )
    provenance_path = workspace / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("payload_capabilities", None)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-payload-target", "--dry-run", "--format", "json"]) == 0
    compact_payload = json.loads(capsys.readouterr().out)
    assert compact_payload["kind"] == "agentic-workspace/lifecycle-mutation-summary/v1"
    assert set(("status", "changed_count", "manual_attention_count", "safe_explicit_apply", "next_action")) <= compact_payload.keys()
    assert len(json.dumps(compact_payload)) < 4_000
    assert compact_payload["detail_commands"]["verbose"].endswith(
        f"upgrade --target {tmp_path.as_posix()} --to-payload-target --verbose --format json"
    )
    assert compact_payload["detail_commands"]["select"].endswith(
        f"upgrade --target {tmp_path.as_posix()} --to-payload-target "
        "--dry-run --select changed_count,changed_paths,manual_attention_count,manual_attention_paths --format json"
    )

    provenance_before_select = provenance_path.read_bytes()
    detail_command = compact_payload["detail_commands"]["select"]
    detail_argv = shlex.split(detail_command.split("agentic-workspace ", 1)[1])
    assert cli.main(detail_argv) == 0
    selected_payload = json.loads(capsys.readouterr().out)
    assert selected_payload["kind"] == "agentic-workspace/selected-output/v1"
    assert selected_payload["values"]["changed_count"] >= 1
    assert ".agentic-workspace/payload-provenance.json" in selected_payload["values"]["changed_paths"]
    assert selected_payload["values"]["manual_attention_count"] == len(selected_payload["values"]["manual_attention_paths"])
    assert provenance_path.read_bytes() == provenance_before_select

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-payload-target", "--dry-run", "--verbose", "--format", "json"]) == 0
    dry_run_payload = json.loads(capsys.readouterr().out)
    dry_run_plan = dry_run_payload["installed_state_compatibility"]["payload_upgrade_attention_plan"]
    assert dry_run_plan["strategy"] == "converge-to-current-contract"
    assert dry_run_plan["release_instruction_policy"]["uses_release_history"] is False
    assert dry_run_plan["category_counts"]["auto_applied"] >= 1
    dry_run_workspace_report = next(report for report in dry_run_payload["reports"] if report["module"] == "workspace")
    dry_run_action = next(
        action for action in dry_run_workspace_report["actions"] if action["path"] == ".agentic-workspace/payload-provenance.json"
    )
    assert dry_run_action["kind"] == "would update"
    assert "payload_capabilities" not in json.loads(provenance_path.read_text(encoding="utf-8"))

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-payload-target", "--format", "json"]) == 0
    capsys.readouterr()
    updated = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert "installed-state-sync-v2" in updated["payload_capabilities"]

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    assert compatibility["status"] == "compatible"
    assert compatibility["payload"]["target"]["status"] == "satisfied"

    assert cli.main(["upgrade", "--target", str(tmp_path), "--dry-run", "--verbose", "--format", "json"]) == 0
    ordinary_dry_run_payload = json.loads(capsys.readouterr().out)
    ordinary_workspace_report = next(report for report in ordinary_dry_run_payload["reports"] if report["module"] == "workspace")
    ordinary_action = next(
        action for action in ordinary_workspace_report["actions"] if action["path"] == ".agentic-workspace/payload-provenance.json"
    )
    assert ordinary_action["kind"] == "current"


def test_report_bootstrap_footprint_recommends_legacy_payload_migration(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "adoption-receipt.json").unlink()
    _write(workspace / "planning" / "state.toml", 'kind = "agentic-workspace/planning-state"\n')
    _write(workspace / "memory" / "repo" / "decisions" / "kept.md", "# Kept decision\n")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "bootstrap_footprint", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    plan = payload["answer"]

    assert plan["kind"] == "agentic-workspace/necessary-surface-migration/v1"
    assert plan["status"] == "safe-apply-available"
    assert plan["safe_to_apply"] is True
    assert "--to-necessary-surfaces --dry-run" in plan["dry_run_command"]
    assert not any(action["kind"] == "would remove" and action["path"] == ".agentic-workspace/skills" for action in plan["actions"])
    assert any(
        action["kind"] == "preserve" and action["path"] == ".agentic-workspace/skills" and action["class"] == "required-skill-surface"
        for action in plan["actions"]
    )
    assert any(
        action["kind"] == "preserve"
        and action["path"] == ".agentic-workspace/planning/state.toml"
        and action["class"] == "adopted-durable-state"
        for action in plan["actions"]
    )
    assert any(action["path"] == ".agentic-workspace/adoption-receipt.json" for action in plan["actions"])


def test_upgrade_to_necessary_surfaces_preserves_durable_state_and_uses_package_skills(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "adoption-receipt.json").unlink()
    _write(workspace / "planning" / "state.toml", 'kind = "agentic-workspace/planning-state"\n')
    _write(workspace / "planning" / "execplans" / "active.plan.json", '{"kind":"planning-execplan/v1"}\n')
    _write(workspace / "memory" / "repo" / "decisions" / "decision.md", "# Durable decision\n")
    package_seed_paths = [
        workspace / "planning" / "execplans" / "TEMPLATE.plan.json",
        workspace / "planning" / "execplans" / "README.md",
        workspace / "planning" / "execplans" / "archive" / "README.md",
        workspace / "memory" / "repo" / "templates",
        workspace / "memory" / "repo" / "decisions" / "README.md",
        workspace / "memory" / "repo" / "domains" / "README.md",
        workspace / "memory" / "repo" / "invariants" / "README.md",
        workspace / "memory" / "repo" / "runbooks" / "README.md",
    ]

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--dry-run", "--format", "json"]) == 0
    dry_run = json.loads(capsys.readouterr().out)["migration"]
    assert dry_run["status"] == "safe-apply-available"
    remove_actions = {action["path"]: action for action in dry_run["actions"] if action["kind"] == "would remove"}
    for path in package_seed_paths:
        relative = path.relative_to(tmp_path).as_posix()
        assert remove_actions[relative]["class"] == "removable-package-owned-payload"
    assert (workspace / "skills" / "workspace-operating-loop" / "SKILL.md").exists()
    assert (workspace / "memory" / "repo" / "decisions" / "decision.md").exists()

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    applied = json.loads(capsys.readouterr().out)["migration"]
    assert applied["status"] == "applied"
    assert (workspace / "skills" / "workspace-operating-loop" / "SKILL.md").exists()
    assert (workspace / "docs" / "module-map.md").exists()
    assert (workspace / "docs" / "workspace-config-contract.md").exists()
    assert (workspace / "planning" / "skills" / "planning-reporting" / "SKILL.md").exists()
    assert (workspace / "memory" / "skills" / "memory-router" / "SKILL.md").exists()
    assert not (workspace / "payload-provenance.json").exists()
    for path in package_seed_paths:
        assert not path.exists()
    assert (workspace / "planning" / "state.toml").exists()
    assert (workspace / "planning" / "execplans" / "active.plan.json").exists()
    assert (workspace / "memory" / "repo" / "decisions" / "decision.md").exists()
    receipt = json.loads((workspace / "adoption-receipt.json").read_text(encoding="utf-8"))
    assert receipt["payload_mirror"] is False
    assert "planning/state.toml" in receipt["adopted_state"]
    assert any(path.startswith("memory/repo/decisions/decision.md") for path in receipt["adopted_state"])

    assert cli.main(["skills", "--target", str(tmp_path), "--format", "json"]) == 0
    skills_payload = json.loads(capsys.readouterr().out)
    skill_ids = {entry["id"] for entry in skills_payload["skills"]}
    assert "workspace-operating-loop" in skill_ids
    assert "memory-router" in skill_ids

    assert cli.main(["status", "--target", str(tmp_path), "--format", "json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert "necessary surfaces" not in json.dumps(status_payload).lower()


def test_upgrade_to_necessary_surfaces_fails_closed_for_tracked_source_checkout_payload(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    workspace = tmp_path / ".agentic-workspace"
    (workspace / "adoption-receipt.json").unlink()
    _write(tmp_path / "pyproject.toml", '[project]\nname = "agentic-workspace"\nversion = "0.0.0"\n')
    _write(tmp_path / "src" / "agentic_workspace" / "__init__.py", "")
    _write(tmp_path / "AGENTS.md", "# Source checkout authority\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    protected_path = workspace / "planning" / "schemas"
    assert protected_path.exists()

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--dry-run", "--format", "json"]) == 0
    dry_run = json.loads(capsys.readouterr().out)["migration"]

    assert dry_run["status"] == "review-required"
    assert dry_run["safe_to_apply"] is False
    assert dry_run["next_action"] == "inspect-deletion-impact"
    impact = dry_run["deletion_impact"]
    assert impact["source_development_posture"] == "package-source-checkout"
    assert impact["tracked_file_count"] > dry_run["summary"]["remove_count"]
    assert impact["protected_file_count"] == impact["tracked_file_count"]
    assert "source-checkout-protected-surface" in impact["review_reasons"]
    assert dry_run["needs_review"][0]["detail_selector"] == "migration.deletion_impact"

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    apply = json.loads(capsys.readouterr().out)["migration"]
    assert apply["status"] == "review-required"
    assert apply["safe_to_apply"] is False
    assert protected_path.exists()
    assert not any(action["kind"] == "removed" for action in apply["actions"])


def test_necessary_surface_deletion_impact_fails_closed_when_git_enumeration_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".git").mkdir()

    def failed_git(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args[0], 128, stdout=b"", stderr=b"fixture failure")

    monkeypatch.setattr(workspace_runtime_core.subprocess, "run", failed_git)
    impact = workspace_runtime_core._necessary_surface_deletion_impact(
        target_root=tmp_path,
        remove_candidates=[".agentic-workspace/docs"],
    )

    assert impact["status"] == "review-required"
    assert impact["tracked_file_enumeration"]["status"] == "failed"
    assert "tracked-file-enumeration-failed" in impact["review_reasons"]


def test_necessary_surface_apply_revalidates_link_state_after_safe_dry_run(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "adoption-receipt.json").unlink()

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--dry-run", "--format", "json"]) == 0
    dry_run = json.loads(capsys.readouterr().out)["migration"]
    assert dry_run["status"] == "safe-apply-available"
    remove_root = next(
        tmp_path / action["path"]
        for action in dry_run["actions"]
        if action["kind"] == "would remove" and (tmp_path / action["path"]).is_dir()
    )

    outside = tmp_path / "outside-after-dry-run"
    outside.mkdir()
    link = remove_root / "late-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        if os.name != "nt":
            pytest.skip(f"directory symlinks unavailable: {exc}")
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            pytest.skip(f"directory link creation unavailable: {completed.stderr or completed.stdout}")

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    apply = json.loads(capsys.readouterr().out)["migration"]
    assert apply["status"] == "review-required"
    assert apply["safe_to_apply"] is False
    assert "symlink-or-reparse-point-ambiguity" in apply["deletion_impact"]["review_reasons"]
    assert link.is_symlink() or bool(getattr(link, "is_junction", lambda: False)())
    assert not any(action["kind"] == "removed" for action in apply["actions"])


def test_necessary_surface_deletion_impact_rejects_path_escape(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    impact = workspace_runtime_core._necessary_surface_deletion_impact(
        target_root=tmp_path,
        remove_candidates=[".agentic-workspace/../outside"],
    )

    assert impact["status"] == "review-required"
    assert impact["escaped_path_sample"] == [".agentic-workspace/../outside"]
    assert "path-containment-failure" in impact["review_reasons"]


@pytest.mark.skipif(os.name != "nt", reason="Windows junction proof")
def test_necessary_surface_deletion_impact_rejects_junction(tmp_path: Path) -> None:
    docs = tmp_path / ".agentic-workspace" / "docs"
    docs.mkdir(parents=True)
    outside = tmp_path / "junction-target"
    outside.mkdir()
    junction = docs / "linked-directory"
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip(f"junction creation unavailable: {completed.stderr or completed.stdout}")

    impact = workspace_runtime_core._necessary_surface_deletion_impact(
        target_root=tmp_path,
        remove_candidates=[".agentic-workspace/docs"],
    )

    assert impact["status"] == "review-required"
    assert ".agentic-workspace/docs/linked-directory" in impact["ambiguous_path_sample"]
    assert "symlink-or-reparse-point-ambiguity" in impact["review_reasons"]


def test_necessary_surface_deletion_impact_rejects_broad_tracked_deletion(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    docs = tmp_path / ".agentic-workspace" / "docs"
    for index in range(100):
        _write(docs / f"fixture-{index:03d}.md", "tracked fixture\n")
    subprocess.run(["git", "add", ".agentic-workspace/docs"], cwd=tmp_path, check=True)

    impact = workspace_runtime_core._necessary_surface_deletion_impact(
        target_root=tmp_path,
        remove_candidates=[".agentic-workspace/docs"],
    )

    assert impact["tracked_file_count"] == impact["broad_deletion_threshold"] == 100
    assert impact["status"] == "review-required"
    assert "broad-tracked-deletion-impact" in impact["review_reasons"]


def test_payload_target_read_only_gate_consumes_compiled_drift_triage(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        "schema_version = 1\n\n"
        "[payload]\n"
        'target_release = "source-current"\n'
        'minimum_capabilities = ["installed-state-sync-v2"]\n'
        'policy = "required-before-work"\n'
        "dogfood_latest = true\n",
        encoding="utf-8",
    )
    provenance_path = workspace / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("payload_capabilities", None)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for unrelated in (
        "Prepare a read-only review of repository issue evidence",
        "Summarize the current source-owned issue records without changing files",
        "Give me a status report from checked-in documentation",
    ):
        assert (
            cli.main(
                [
                    "start",
                    "--target",
                    str(tmp_path),
                    "--task",
                    unrelated,
                    "--select",
                    "installed_state_read_only_scope,installed_state_drift_triage,next_safe_action",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        allowed = json.loads(capsys.readouterr().out)["values"]
        assert allowed["installed_state_read_only_scope"]["decision_authority"] == (
            "installed_state_drift_triage.claim_effect_authority.installed_payload_dependency"
        )
        authority = allowed["installed_state_drift_triage"]["claim_effect_authority"]
        assert authority["installed_payload_dependency"] == "independent"
        assert authority["authority"] == "planning_safety_gate.route_decision"
        assert authority["decision_id"].startswith("planning-route:")
        assert allowed["next_safe_action"]["next_safe_action"] == "continue-read-only-source-evidence-review"

    for dependent in (
        "Prepare a read-only review of how the public command behaves after installation",
        "Inspect whether the installed runtime produces the documented result",
        "Audit payload drift and upgrade readiness",
        "Verify the packaged CLI behavior as proof for closeout",
    ):
        assert (
            cli.main(
                [
                    "start",
                    "--target",
                    str(tmp_path),
                    "--task",
                    dependent,
                    "--select",
                    "installed_state_read_only_scope,installed_state_drift_triage,next_safe_action",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        blocked = json.loads(capsys.readouterr().out)["values"]
        assert "installed_state_read_only_scope" not in blocked
        assert blocked["installed_state_drift_triage"]["claim_effect_authority"]["installed_payload_dependency"] == "dependent"
        assert blocked["next_safe_action"]["next_safe_action"] == "run-installed-payload-target-upgrade"

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/change.md",
                "--task",
                "Implement the requested documentation change",
                "--select",
                "installed_state_drift_triage,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    mutation = json.loads(capsys.readouterr().out)["values"]
    assert mutation["installed_state_drift_triage"]["claim_effect_authority"]["effect_class"] == "repo-mutation"
    assert mutation["next_safe_action"]["next_safe_action"] == "run-installed-payload-target-upgrade"


def test_upgrade_to_necessary_surfaces_keeps_current_memory_skill_eof_stable(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "memory", "--format", "json"]) == 0
    capsys.readouterr()

    package_root = tmp_path / "memory-package-payload"
    package_skills = package_root / ".agentic-workspace" / "memory" / "skills"
    cases = {
        Path("REGISTRY.json"): b'{\n  "skills": []\n}\n',
        Path("memory-refresh") / "SKILL.md": b"---\nname: memory-refresh\n---\n\n# Memory Refresh\n",
        Path("memory-upgrade") / "agents" / "openai.yaml": b"instructions: keep stable\n",
    }
    for relative, canonical in cases.items():
        source = package_skills / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(canonical + b"\n")
        target = workspace / "memory" / "skills" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical)

    import repo_memory_bootstrap._installer_paths as memory_paths

    monkeypatch.setattr(memory_paths, "payload_root", lambda: package_root)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    migration = json.loads(capsys.readouterr().out)["migration"]

    actions_by_path = {action["path"]: action for action in migration["actions"]}
    checked_paths = []
    for relative, canonical in cases.items():
        installed = workspace / "memory" / "skills" / relative
        assert installed.read_bytes() == canonical
        installed_relative = installed.relative_to(tmp_path).as_posix()
        checked_paths.append(installed_relative)
        assert actions_by_path[installed_relative]["kind"] == "current"

    diff_check = subprocess.run(["git", "diff", "--check"], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert diff_check.returncode == 0, diff_check.stdout + diff_check.stderr
    skill_diff = subprocess.run(
        ["git", "diff", "--name-only", "--", *checked_paths],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert skill_diff.returncode == 0
    assert skill_diff.stdout == ""


def test_upgrade_to_necessary_surfaces_leaves_doctor_healthy_after_apply(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "adoption-receipt.json").unlink()

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    applied = json.loads(capsys.readouterr().out)["migration"]
    assert applied["status"] == "applied"

    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["health"] == "healthy"
    assert doctor_payload["needs_review"] == []
    assert doctor_payload["warnings"] == []


def test_upgrade_replay_preserves_context_through_proof_and_bounded_closeout(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    task = "Upgrade the installed workspace without losing the active task"
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "adoption-receipt.json").unlink()

    manifest_path = tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    repo_owned_manifest = manifest_path.read_bytes() + b'\n[notes."docs/upgrade.md"]\nnote_type = "runbook"\n'
    manifest_path.write_bytes(repo_owned_manifest)
    _write(tmp_path / "docs" / "upgrade.md", "# Upgrade replay\n")
    _write(tmp_path / "pyproject.toml", '[project]\nname = "upgrade-replay"\nversion = "0.0.0"\n')
    _write(tmp_path / "Makefile", "test:\n\tpython -m pytest tests/test_upgrade_replay.py -q\n")
    _write(tmp_path / "tests" / "test_upgrade_replay.py", "def test_upgrade_replay():\n    assert True\n")
    changed_paths = ["docs/upgrade.md", "tests/test_upgrade_replay.py"]
    execplan_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans"

    def live_execplans() -> list[Path]:
        return [path for path in execplan_dir.glob("*.plan.json") if path.name != "TEMPLATE.plan.json"]

    assert live_execplans() == []

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["migration"]["status"] == "applied"
    assert manifest_path.read_bytes() == repo_owned_manifest

    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["health"] == "healthy", {
        "needs_review": doctor_payload.get("needs_review"),
        "warnings": doctor_payload.get("warnings"),
        "issues": doctor_payload.get("issues"),
    }
    assert cli.main(["status", "--target", str(tmp_path), "--format", "json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert "necessary surfaces" not in json.dumps(status_payload).lower()

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "closeout_trust",
                "--task",
                task,
                "--changed",
                *changed_paths,
                "--format",
                "json",
            ]
        )
        == 0
    )
    unproved_closeout = json.loads(capsys.readouterr().out)["answer"]
    assert unproved_closeout["current_task_closeout"]["proof_state"]["status"] != "recorded-and-accepted"
    assert (
        cli._direct_task_terminal_outcome_contract(
            closeout_trust=unproved_closeout,
            residue_kind="issue",
            residue_owner="GitHub issue #2371",
        )
        == {}
    ), "structured caller inputs cannot replace accepted product-owned proof"
    assert live_execplans() == []

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--task",
                task,
                "--format",
                "json",
            ]
        )
        == 0
    )
    proof_selection = json.loads(capsys.readouterr().out)
    selected_next_command = str(proof_selection.get("next", {}).get("command") or "").strip()
    required_commands = proof_selection.get("required_commands") or ([selected_next_command] if selected_next_command else [])
    assert required_commands, proof_selection
    for command in required_commands:
        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    *changed_paths,
                    "--record-receipt",
                    "--receipt-command",
                    command,
                    "--receipt-result",
                    "passed",
                    "--receipt-claim-sufficiency",
                    "sufficient",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        direct_proof = json.loads(capsys.readouterr().out)
        assert direct_proof["receipt"]["result"] == "passed"
    assert live_execplans() == [], "direct upgrade/proof must not synthesize Planning state"

    residue_owner = "GitHub issue #2371"
    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "closeout_trust",
                "--task",
                task,
                "--changed",
                *changed_paths,
                "--format",
                "json",
            ]
        )
        == 0
    )
    closeout_answer = json.loads(capsys.readouterr().out)["answer"]
    direct_closeout = closeout_answer["current_task_closeout"]
    assert direct_closeout["status"] == "active"
    assert direct_closeout["scope"]["relationship"] == "bounded-current-task"
    assert direct_closeout["scope"]["changed_paths"] == changed_paths
    assert direct_closeout["proof_state"]["status"] == "recorded-and-accepted", direct_closeout["proof_state"]
    direct_terminal = cli._direct_task_terminal_outcome_contract(
        closeout_trust=closeout_answer, residue_kind="issue", residue_owner=residue_owner
    )
    assert direct_terminal.get("direct_task_closeout"), direct_terminal
    assert live_execplans() == []

    assert (
        cli.main(
            [
                "final-response",
                "admit",
                "--target",
                str(tmp_path),
                "--attempt",
                "The whole objective has reached its endpoint.",
                "--claim-class",
                "slice-complete",
                "--claim-scope-id",
                "direct_task_closeout:slice_complete",
                "--task",
                task,
                "--changed",
                *changed_paths,
                "--residue",
                "issue",
                "--residue-owner",
                residue_owner,
                "--format",
                "json",
            ]
        )
        == 0
    )
    bounded = json.loads(capsys.readouterr().out)
    assert "direct_task_closeout" in bounded["terminal_outcome_contract"], bounded["terminal_outcome_contract"]
    assert bounded["status"] == "accepted_bounded_report", bounded
    report = bounded["admission"]["authoritative_response"]
    assert report["claim_class"] == "slice_complete"
    assert report["larger_intent"]["completion_authorized"] is False
    assert report["residue"] == {"kind": "issue", "status": "routed", "owner": residue_owner}
    assert report["proof"]["status"] == "recorded-and-accepted"
    assert bounded["admission"]["attempt"]["model_authored_text_admission"]["admitted"] is False
    assert bounded["terminal_outcome_contract"]["direct_task_closeout"]["planning_record_required"] is False
    assert live_execplans() == [], "direct closeout/final-response admission must remain plan-free"

    terminal = bounded["terminal_outcome_contract"]
    rejected = cli._terminal_final_response_admission(
        terminal_outcome_contract=terminal,
        final_response_attempt={
            "claim": "Nothing remains and the parent work is concluded.",
            "claim_class": "full_intent_complete",
            "claim_scope_id": "closeout_trust:slice_complete",
        },
        resume_executor=lambda _request: {"status": "executed", "invoked_operation": "continue-routed-residue"},
    )
    assert rejected["status"] == "rejected_auto_resumed"
    assert rejected["authoritative_response"] == {}


def test_upgrade_to_necessary_surfaces_repairs_missing_required_skills(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    shutil.rmtree(workspace / "skills")
    shutil.rmtree(workspace / "planning" / "skills")
    shutil.rmtree(workspace / "memory" / "skills")

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    applied = json.loads(capsys.readouterr().out)["migration"]

    assert applied["status"] == "applied"
    assert (workspace / "skills" / "workspace-startup" / "SKILL.md").exists()
    assert (workspace / "planning" / "skills" / "planning-reporting" / "SKILL.md").exists()
    assert (workspace / "memory" / "skills" / "memory-router" / "SKILL.md").exists()


def test_upgrade_to_necessary_surfaces_preserves_verification_state(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory", "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "adoption-receipt.json").unlink()
    _write(workspace / "verification" / "manifest.toml", "schema_version = 1\n")

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    capsys.readouterr()

    assert (workspace / "verification" / "manifest.toml").exists()


def test_upgrade_to_necessary_surfaces_respects_explicit_mirror_receipt(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--dry-run", "--format", "json"]) == 0
    dry_run = json.loads(capsys.readouterr().out)["migration"]
    assert dry_run["status"] == "mirror-intent-present"
    assert dry_run["safe_to_apply"] is False
    assert not any(action["kind"] == "would remove" for action in dry_run["actions"])

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-necessary-surfaces", "--format", "json"]) == 0
    applied = json.loads(capsys.readouterr().out)["migration"]
    assert applied["status"] == "mirror-intent-present"
    assert (workspace / "skills" / "workspace-operating-loop" / "SKILL.md").exists()
    receipt = json.loads((workspace / "adoption-receipt.json").read_text(encoding="utf-8"))
    assert receipt["payload_mirror"] is True


def test_doctor_surfaces_legacy_bootstrap_footprint_migration(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "adoption-receipt.json").unlink()

    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["health"] == "healthy"
    assert payload["warnings"] == []


def test_payload_upgrade_attention_plan_classifies_repo_surfaces(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,verification", "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / "AGENTS.md").write_text("Repo-owned instructions without a managed workflow fence.\n", encoding="utf-8")
    verification_manifest = workspace / "verification" / "manifest.toml"
    if verification_manifest.exists():
        verification_manifest.unlink()
    planning_state = workspace / "planning" / "state.toml"
    planning_state.parent.mkdir(parents=True, exist_ok=True)
    planning_state.write_text('kind = "agentic-workspace/planning-state"\n', encoding="utf-8")
    (tmp_path / "llms.txt").write_text("legacy model-facing instructions\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    plan = compatibility["payload_upgrade_attention_plan"]
    by_category = {item["category"]: item for item in plan["attention_items"]}

    assert by_category["agent_review_required"]["surface"] == "AGENTS.md"
    assert by_category["agent_populate_required"]["surface"] == ".agentic-workspace/verification/manifest.toml"
    assert by_category["deprecated_surface"]["surface"] == "llms.txt"
    assert by_category["machine_migration_required"]["surface"] == ".agentic-workspace/planning/state.toml"
    assert plan["status"] == "manual_attention_required"
    assert plan["release_instruction_policy"]["uses_release_history"] is False


def test_payload_upgrade_attention_plan_routes_unsupported_long_hop(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    provenance_path = tmp_path / ".agentic-workspace" / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["payload_schema"] = "agentic-workspace/payload/v0"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    plan = compatibility["payload_upgrade_attention_plan"]
    unsupported_items = [item for item in plan["attention_items"] if item["category"] == "unsupported_long_hop"]

    assert unsupported_items
    assert unsupported_items[0]["surface"] == ".agentic-workspace/payload-provenance.json"
    assert unsupported_items[0]["blocking"] is True
    assert plan["release_instruction_policy"]["uses_release_history"] is False


def test_payload_target_required_before_claim_limits_claims_without_blocking_work(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        "schema_version = 1\n\n"
        "[payload]\n"
        'target_release = "source-current"\n'
        'minimum_capabilities = ["installed-state-sync-v2"]\n'
        'policy = "required-before-claim"\n',
        encoding="utf-8",
    )
    provenance_path = workspace / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("payload_capabilities", None)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--select",
                "installed_state_compatibility,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)["values"]
    compatibility = selected["installed_state_compatibility"]
    assert compatibility["payload"]["target"]["status"] == "target-mismatch"
    assert compatibility["action_effect"]["force"] == "required_before_claim"
    assert "claim-payload-target-satisfied" in compatibility["action_effect"]["blocked_until_reconciled"]
    assert selected["next_safe_action"]["implementation_allowed"] is True


def test_payload_target_required_before_work_exposes_repair_subflow(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        "schema_version = 1\n\n"
        "[payload]\n"
        'target_release = "source-current"\n'
        'minimum_capabilities = ["installed-state-sync-v2"]\n'
        'policy = "required-before-work"\n',
        encoding="utf-8",
    )
    provenance_path = workspace / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("payload_capabilities", None)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--select",
                "installed_state_compatibility,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)["values"]
    compatibility = selected["installed_state_compatibility"]
    subflow = compatibility["payload_repair_subflow"]

    assert compatibility["status"] == "payload-upgrade-required"
    assert compatibility["payload_repair_subflow"] == subflow
    assert subflow["kind"] == "agentic-workspace/payload-repair-subflow/v1"
    assert subflow["status"] == "safe-explicit-apply"
    assert subflow["safe_explicit_apply"] is True
    assert subflow["manual_review_required"] is False
    assert subflow["start_mutates"] is False
    assert [step["id"] for step in subflow["steps"]] == ["dry_run", "apply", "recheck"]
    assert all(step["reportable_command"].startswith("agentic-workspace ") for step in subflow["steps"])
    assert subflow["reportable_commands"]["dry_run"] == "agentic-workspace upgrade --target . --to-payload-target --dry-run --format json"
    assert "--to-payload-target --dry-run" in subflow["machine_commands"]["dry_run"]
    assert selected["next_safe_action"]["next_safe_action"] == "run-installed-payload-target-upgrade"


def test_payload_target_blocks_when_invoked_cli_cannot_satisfy_explicit_target(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        'schema_version = 1\n\n[payload]\ntarget_release = "999.0.0"\npolicy = "required-before-work"\n',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]

    assert compatibility["status"] == "blocking-drift"
    assert compatibility["payload"]["target"]["status"] == "compatible-cli-required"
    assert compatibility["payload"]["target"]["invoked_cli_can_satisfy"] is False
    assert compatibility["action_state"]["state"] == "blocking_incompatible"
    assert compatibility["action_state"]["safe_to_apply"] is False
    assert "--to-payload-target" not in compatibility["action_state"]["command"]

    assert cli.main(["upgrade", "--target", str(tmp_path), "--to-payload-target", "--dry-run", "--format", "json"]) == 0
    compact_upgrade = json.loads(capsys.readouterr().out)
    assert compact_upgrade["status"] == "blocking-drift"
    assert compact_upgrade["safe_explicit_apply"] is False


def test_compact_payload_upgrade_projects_authoritative_unsafe_action_without_manual_attention(tmp_path: Path, capsys) -> None:
    from types import SimpleNamespace

    args = SimpleNamespace(
        command="upgrade",
        select=None,
        to_payload_target=True,
        verbose=False,
        dry_run=True,
        format="json",
    )
    payload = {
        "installed_state_compatibility": {
            "status": "blocking-drift",
            "action_state": {
                "state": "blocking_incompatible",
                "safe_to_apply": False,
                "apply_command": "",
            },
        },
        "warnings": [],
        "needs_review": [],
    }

    cli._emit_lifecycle_mutation_result(
        args=args,
        payload=payload,
        target_root=tmp_path,
        config=SimpleNamespace(cli_invoke="agentic-workspace"),
    )

    compact = json.loads(capsys.readouterr().out)
    assert compact["manual_attention_count"] == 0
    assert compact["safe_explicit_apply"] is False


def test_workspace_config_rejects_invalid_payload_target_policy(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[payload]\ntarget_release = "source-current"\npolicy = "sometimes"\n',
    )

    with pytest.raises(cli.WorkspaceUsageError, match="policy must be one of"):
        cli._load_workspace_config(target_root=tmp_path)


def test_start_installed_state_blocks_newer_repo_payload_instead_of_downgrading(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    provenance_path = tmp_path / ".agentic-workspace" / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["release_identity"]["version"] = "999.0.0"
    provenance["release_identity"]["tag"] = "v999.0.0"
    provenance["installed_by"]["version"] = "999.0.0"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]

    assert compatibility["status"] == "blocking-drift"
    assert compatibility["payload"]["status"] == "incompatible"
    assert compatibility["payload"]["provenance_drift"] == "executable-too-old"
    assert compatibility["action_state"]["state"] == "blocking_incompatible"
    assert compatibility["action_state"]["safe_to_apply"] is False
    assert compatibility["repair_route"]["status"] == "blocking"
    assert compatibility["repair_route"]["waiver"]["allowed"] is False
    assert "upgrade --target" not in compatibility["action_state"]["command"]


def test_upgrade_dry_run_does_not_rewrite_valid_provenance_for_identity_only_drift(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    provenance_path = tmp_path / ".agentic-workspace" / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["release_identity"]["version"] = "0.0.1"
    provenance["release_identity"]["tag"] = "v0.0.1"
    provenance["installed_by"]["version"] = "0.0.1"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert cli.main(["upgrade", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    provenance_action = next(
        action for action in workspace_report["actions"] if action["path"] == ".agentic-workspace/payload-provenance.json"
    )
    assert provenance_action["kind"] == "current"
    assert "installer identity drift does not require rewrite" in provenance_action["detail"]


def test_upgrade_dry_run_repairs_structurally_invalid_provenance_with_matching_file_set(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    provenance_path = tmp_path / ".agentic-workspace" / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.pop("release_identity")
    provenance.pop("installed_by")
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    assert compatibility["status"] == "payload-upgrade-required"
    assert compatibility["payload"]["provenance"]["status"] == "invalid"
    assert compatibility["action_state"]["state"] == "safe_payload_sync_available"

    assert cli.main(["upgrade", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    provenance_action = next(
        action for action in workspace_report["actions"] if action["path"] == ".agentic-workspace/payload-provenance.json"
    )
    assert provenance_action["kind"] == "would update"


def test_payload_provenance_payload_uses_portable_path_identities(tmp_path: Path) -> None:
    payload = cli._payload_provenance_payload(target_root=tmp_path)
    encoded = json.dumps(payload, sort_keys=True)

    assert not re.search(r"[A-Za-z]:/|/(?:Users|home|tmp)/", encoded)
    assert payload["installed_by"]["module_path"]
    assert payload["installed_by"]["python_executable"]
    assert payload["command_generation"]["source_identity"]


def test_start_select_installed_state_blocking_drift_blocks_execution(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "blocking"\nexact_version = "999.0.0"\n',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]

    assert compatibility["status"] == "blocking-drift"
    assert compatibility["action_state"]["state"] == "blocking_incompatible"
    assert compatibility["repair_route"]["status"] == "blocking"
    assert compatibility["executable"]["classification"] == "executable-too-old-or-wrong-version"
    assert compatibility["action_effect"]["force"] == "required_before_execution"
    assert compatibility["action_effect"]["allowed_now"] == "switch-to-compatible-invocation-before-running-workspace-actions"
    assert compatibility["action_effect"]["blocked_until_reconciled"] == [
        "run-workspace-action",
        "claim-installed-state-compatible",
    ]
    assert (
        compatibility["action_effect"]["claim_boundary"]
        == "do-not-trust-workspace-action-output-until-the-effective-cli-invocation-is-compatible"
    )


def test_start_select_installed_state_advisory_drift_limits_currentness_claims(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "advisory"\nexact_version = "999.0.0"\n',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]

    assert compatibility["status"] == "upgrade-recommended"
    assert compatibility["action_state"]["state"] == "manual_review_required"
    assert compatibility["repair_route"]["status"] == "manual-review-required"
    assert compatibility["action_effect"]["force"] == "advisory"
    assert compatibility["action_effect"]["allowed_now"] == "continue-bounded-work-with-compatible-claim-limits"
    assert compatibility["action_effect"]["blocked_until_reconciled"] == [
        "claim-installed-state-current",
        "claim-cli-fully-current",
    ]
    assert (
        compatibility["action_effect"]["claim_boundary"]
        == "advisory-cli-drift-does-not-block-ordinary-work-but-limits-strong-compatibility-claims"
    )


def test_start_select_installed_contract_pair_uses_frozen_non_mutating_resolution(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_run = workspace_runtime_core.subprocess.run

    def clean_source_status(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[:3] == ["git", "status", "--porcelain=v1"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        return original_run(command, **kwargs)

    monkeypatch.setattr(workspace_runtime_core.subprocess, "run", clean_source_status)
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'cli_invoke = "uv run --frozen --active python scripts/run_agentic_workspace.py"\n\n'
        "[cli_compatibility]\n"
        'contract_schema = "agentic-workspace/installed-state-compatibility/v1"\n'
        'required_capabilities = ["installed-state-sync-v2"]\n'
        'required_resources = ["agentic_workspace:contracts/context_authority_registry.json"]\n'
        'resolution_policy = "frozen"\n',
        encoding="utf-8",
    )
    script = tmp_path / "scripts" / "run_agentic_workspace.py"
    script.parent.mkdir()
    script.write_text("from agentic_workspace.cli import main\nraise SystemExit(main())\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "agentic-workspace"\nversion = "' + cli.__version__ + '"\n',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    pair = compatibility["contract_pair"]
    resolution = compatibility["invocation_resolution"]

    assert pair["status"] == "compatible"
    assert pair["mutation_gate"] == "allow"
    assert pair["expected"]["provenance"] == "repo-config"
    resource = pair["actual"]["resources"][0]
    assert resource["resource"] == "agentic_workspace:contracts/context_authority_registry.json"
    assert resource["available"] is True
    assert resource["resolution"] == "package-resource"
    assert resource["resolver"] == "installed-contract-pair.package-resource"
    assert resource["receipt_id"].startswith("package-resource:")
    assert resolution["environment_manager_adapter"] == "uv"
    assert resolution["posture"] == "frozen"
    assert resolution["preflight_mutates_dependency_state"] is False
    assert resolution["resolution_status"] == "resolved"
    assert resolution["lock_resolution"]["runtime_version_matches"] is True
    assert resolution["selected_distribution"]["status"] == "resolved"
    assert resolution["repair_command"] == ""
    assert pair["transition_owner"]["operation_id"] == "workspace.install-upgrade-sync"
    assert pair["transition_owner"]["operation_contract"].endswith("workspace.install-upgrade-sync.json")
    assert pair["transition_owner"]["executor"].endswith("execute_workspace_install_upgrade_sync")
    assert pair["transition_owner"]["before_identity_digest"].startswith("sha256:")
    assert pair["transition_owner"]["ordinary_surfaces_mutate_dependency_state"] is False
    matrix = pair["conformance_matrix"]
    parity = next(item for item in matrix["scenarios"] if item["id"] == "consumer-identity-parity")
    assert len(set(parity["consumers"].values())) == 1
    assert set(parity["consumers"]) == {"startup", "skills", "doctor"}
    source_checkout = pair["actual"]["source_checkout"]
    assert source_checkout["classification"] == "local-source-non-release"
    assert re.fullmatch(r"git:[0-9a-f]{12}", source_checkout["revision"])
    assert source_checkout["dirty"] is False
    assert source_checkout["generated_parity"] in {"current", "stale"}
    assert not re.search(r"[A-Za-z]:/|/(?:Users|home|tmp)/", json.dumps(pair, sort_keys=True))


def test_install_upgrade_sync_is_the_production_dependency_identity_transition_boundary(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "upgrade",
                "--target",
                str(tmp_path),
                "--to-payload-target",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    receipt = payload["installed_identity_transition"]

    assert receipt["status"] == "admitted"
    assert receipt["mutation_owner"] == "execute_workspace_install_upgrade_sync"
    assert receipt["transition_result"]["command"] == "upgrade"
    assert receipt["before_identity"]["payload_mirror"]["status"] == "missing"
    assert receipt["after_identity"]["payload_mirror"]["status"] == "present"
    assert receipt["before_identity_digest"] != receipt["after_identity_digest"]


def test_installed_contract_necessary_surface_clone_is_consumer_stable(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    assert not (tmp_path / ".agentic-workspace" / "payload-provenance.json").exists()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed contract",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    startup = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]["contract_pair"]
    assert cli.main(["doctor", "--target", str(tmp_path), "--select", "installed_state_compatibility", "--format", "json"]) == 0
    doctor = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]["contract_pair"]
    assert cli.main(["skills", "--target", str(tmp_path), "--select", "installed_contract,skills", "--format", "json"]) == 0
    skills = json.loads(capsys.readouterr().out)["values"]

    digests = {
        startup["conformance_matrix"]["identity_digest"],
        doctor["conformance_matrix"]["identity_digest"],
        skills["installed_contract"]["identity_digest"],
    }
    assert len(digests) == 1
    assert startup["actual"]["resources"] == doctor["actual"]["resources"] == skills["installed_contract"]["contract_resources"]
    package_receipts = [
        receipt
        for skill in skills["skills"]
        for receipt in skill["resource_resolution_receipts"]
        if receipt["selected_owner"] == "package-owned"
    ]
    assert package_receipts
    assert all(receipt["resolver"] == "installed-contract-pair.package-resource" for receipt in package_receipts)
    assert not (tmp_path / ".agentic-workspace" / "package-payload").exists()


@pytest.mark.parametrize(
    ("scenario_id", "source_class", "posture", "resolution_status", "vcs_revision", "mirror_payload", "expected_status", "repair_action"),
    [
        ("released-package", "released-package", "locked", "resolved", "", False, "admitted", "none"),
        ("locked-vcs", "installed-distribution", "locked", "resolved", "abc123", False, "admitted", "none"),
        ("mutable-or-unlocked-vcs", "installed-distribution", "mutable", "resolved", "", False, "blocked", "lock-dependency-resolution"),
        (
            "incompatible-or-missing-runtime",
            "installed-distribution",
            "locked",
            "missing",
            "",
            False,
            "blocked",
            "install-or-select-compatible-runtime",
        ),
        ("payload-mirror", "installed-distribution", "locked", "resolved", "", True, "admitted", "none"),
        ("local-source-drift", "source-checkout", "locked", "resolved", "", False, "blocked", "clean-or-commit-local-source"),
    ],
)
def test_installed_contract_scenarios_use_black_box_start_and_exact_repair_routes(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
    scenario_id: str,
    source_class: str,
    posture: str,
    resolution_status: str,
    vcs_revision: str,
    mirror_payload: bool,
    expected_status: str,
    repair_action: str,
) -> None:
    _init_git_repo(tmp_path)
    init_args = ["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]
    if mirror_payload:
        init_args.insert(-2, "--mirror-payload")
    assert cli.main(init_args) == 0
    capsys.readouterr()
    if source_class == "source-checkout":
        source_root = tmp_path / "aw-source"
        source_root.mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=source_root, check=True)
        tracked = source_root / "tracked.txt"
        tracked.write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=source_root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "-m", "initial"], cwd=source_root, check=True
        )
        tracked.write_text("after\n", encoding="utf-8")
        monkeypatch.setattr(workspace_runtime_core, "_agentic_workspace_package_root", lambda: source_root)
    monkeypatch.setattr(
        workspace_runtime_core,
        "_payload_installer_identity",
        lambda **_kwargs: {
            "package": "agentic-workspace",
            "version": "1.0.0",
            "source": "local-source" if source_class == "source-checkout" else "released-wheel",
            "source_class": source_class,
            "source_identity": "git:abc123" if source_class == "source-checkout" else "site-packages:agentic_workspace",
            "module_path": "agentic_workspace",
            "python_executable": "python",
        },
    )
    direct_url = {
        "url_scheme": "https" if vcs_revision or posture == "mutable" else "",
        "url_fingerprint": "sha256:fixture" if vcs_revision or posture == "mutable" else "",
        "vcs_info": {"vcs": "git", **({"commit_id": vcs_revision} if vcs_revision else {})} if vcs_revision or posture == "mutable" else {},
    }
    monkeypatch.setattr(
        workspace_runtime_core,
        "_invocation_resolution_payload",
        lambda **_kwargs: {
            "posture": posture,
            "resolution_status": resolution_status,
            "policy_satisfied": posture == "locked",
            "selected_distribution": {"direct_url": direct_url},
            "preflight_mutates_dependency_state": posture == "mutable",
            "preflight_status": "unsafe-mutable-resolution" if posture == "mutable" else "non-mutating",
            "repair_command": "uv run --frozen agentic-workspace",
        },
    )

    assert cli.main(["start", "--target", str(tmp_path), "--select", "installed_state_compatibility", "--format", "json"]) == 0
    pair = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]["contract_pair"]
    scenario = next(item for item in pair["conformance_matrix"]["scenarios"] if item["id"] == scenario_id)

    assert scenario["status"] == expected_status
    assert pair["repair_route"]["action"] == repair_action
    assert pair["status"] == ("incompatible" if expected_status == "blocked" else "compatible")


def test_installed_contract_generated_parity_blocks_through_black_box_doctor(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    original_summarise = workspace_runtime_core._summarise_reports

    def stale_summary(**kwargs: Any) -> dict[str, Any]:
        summary = original_summarise(**kwargs)
        summary["stale_generated_surfaces"] = ["generated/example.py"]
        return summary

    monkeypatch.setattr(workspace_runtime_core, "_summarise_reports", stale_summary)
    monkeypatch.setattr(
        workspace_runtime_core,
        "_payload_installer_identity",
        lambda **_kwargs: {
            "package": "agentic-workspace",
            "version": "1.0.0",
            "source": "released-wheel",
            "source_class": "released-package",
            "source_identity": "site-packages:agentic_workspace",
            "module_path": "agentic_workspace",
            "python_executable": "python",
        },
    )
    assert cli.main(["doctor", "--target", str(tmp_path), "--select", "installed_state_compatibility", "--format", "json"]) == 0
    pair = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]["contract_pair"]
    generated = next(item for item in pair["conformance_matrix"]["scenarios"] if item["id"] == "generated-parity")

    assert generated["status"] == "blocked"
    assert pair["status"] == "incompatible"
    assert pair["repair_route"] == {
        "status": "required",
        "action": "regenerate-managed-surfaces",
        "command": "uv run python scripts/generate/generate_command_packages.py",
    }


def test_ordinary_identity_consumers_cannot_execute_dependency_transition(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    def reject_transition(**_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("ordinary consumers must not cross the dependency transition boundary")

    monkeypatch.setattr(workspace_runtime_core, "execute_workspace_install_upgrade_sync", reject_transition)
    assert cli.main(["start", "--target", str(tmp_path), "--task", "inspect", "--format", "json"]) == 0
    capsys.readouterr()
    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert cli.main(["skills", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()


def test_start_select_installed_contract_pair_blocks_mutable_resolution(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'cli_invoke = "uv run --active python scripts/run_agentic_workspace.py"\n\n'
        "[cli_compatibility]\n"
        'resolution_policy = "frozen"\n',
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--select", "installed_state_compatibility", "--format", "json"]) == 0
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    resolution = compatibility["invocation_resolution"]

    assert compatibility["status"] == "blocking-drift"
    assert compatibility["contract_pair"]["status"] == "incompatible"
    assert compatibility["contract_pair"]["mutation_gate"] == "block-managed-mutation"
    assert resolution["posture"] == "mutable"
    assert resolution["preflight_status"] == "unsafe-mutable-resolution"
    assert resolution["preflight_mutates_dependency_state"] is True
    assert "uv run --frozen" in resolution["repair_command"]


def test_start_select_installed_contract_pair_blocks_missing_package_resource(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        'schema_version = 1\n\n[cli_compatibility]\nrequired_resources = ["agentic_workspace:contracts/missing-contract.json"]\n',
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--select", "installed_state_compatibility", "--format", "json"]) == 0
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]
    pair = compatibility["contract_pair"]

    assert compatibility["status"] == "blocking-drift"
    assert pair["status"] == "incompatible"
    assert pair["mutation_gate"] == "block-managed-mutation"
    assert pair["missing_resources"] == ["agentic_workspace:contracts/missing-contract.json"]


@pytest.mark.parametrize(
    ("recipe", "expected_posture", "expected_policy"),
    [
        ("pipx run agentic-workspace@git+https://example.test/agentic-workspace@abc123", "locked", True),
        ("pipx run agentic-workspace", "mutable", False),
    ],
)
def test_invocation_resolution_distinguishes_locked_and_mutable_pipx_vcs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recipe: str,
    expected_posture: str,
    expected_policy: bool,
) -> None:
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text(
        f'schema_version = 1\n\n[workspace]\ncli_invoke = "{recipe}"\n\n[cli_compatibility]\nresolution_policy = "locked"\n',
        encoding="utf-8",
    )
    pipx_list = {
        "venvs": {
            "agentic-workspace": {
                "metadata": {
                    "main_package": {
                        "package": "agentic-workspace",
                        "package_version": cli.__version__,
                        "package_or_url": "git+https://example.test/agentic-workspace@abc123",
                    }
                }
            }
        }
    }
    monkeypatch.setattr(workspace_runtime_core.shutil, "which", lambda _name: "tools/pipx.exe")
    monkeypatch.setattr(
        workspace_runtime_core.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, json.dumps(pipx_list), ""),
    )

    config = workspace_runtime_core._load_workspace_config(target_root=tmp_path)
    resolution = workspace_runtime_core._invocation_resolution_payload(config=config)

    assert resolution["environment_manager_adapter"] == "pipx"
    assert resolution["posture"] == expected_posture
    assert resolution["policy_satisfied"] is expected_policy
    assert resolution["manager_probe"]["selected_package"]["name"] == "agentic-workspace"


def test_invocation_resolution_reads_poetry_environment_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text(
        'schema_version = 1\n\n[workspace]\ncli_invoke = "poetry run agentic-workspace"\n\n'
        '[cli_compatibility]\nresolution_policy = "locked"\n',
        encoding="utf-8",
    )
    (tmp_path / "poetry.lock").write_text(
        '[[package]]\nname = "agentic-workspace"\nversion = "' + cli.__version__ + '"\n', encoding="utf-8"
    )
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[1:4] == ["env", "info", "--executable"]:
            return subprocess.CompletedProcess(command, 0, sys.executable + "\n", "")
        identity = {"name": "agentic-workspace", "version": cli.__version__, "direct_url": {}}
        return subprocess.CompletedProcess(command, 0, json.dumps(identity), "")

    monkeypatch.setattr(workspace_runtime_core.shutil, "which", lambda _name: "tools/poetry.exe")
    monkeypatch.setattr(workspace_runtime_core.subprocess, "run", fake_run)

    config = workspace_runtime_core._load_workspace_config(target_root=tmp_path)
    resolution = workspace_runtime_core._invocation_resolution_payload(config=config)

    assert resolution["policy_satisfied"] is True
    assert resolution["selected_distribution"]["version"] == cli.__version__
    assert len(calls) == 2


def test_invocation_resolution_blocks_missing_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text('schema_version = 1\n\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8")
    monkeypatch.setattr(workspace_runtime_core.shutil, "which", lambda _name: None)

    config = workspace_runtime_core._load_workspace_config(target_root=tmp_path)
    resolution = workspace_runtime_core._invocation_resolution_payload(config=config)

    assert resolution["resolution_status"] == "unresolved"
    assert resolution["policy_satisfied"] is False
    assert resolution["selected_executable"]["path_fingerprint"] == ""


def test_start_default_stays_under_tiny_output_budget_for_docs_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    mark_configuration_readiness_current(tmp_path)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix one docs typo",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 10_000, label="start tiny docs-task payload", sort_keys=False)
    assert payload["decision_packet"]["action"]["id"] == "choose-smallest-workflow-shape"
    assert "memory_decision_packet" not in payload
    assert "installed_state_compatibility" not in payload
    assert "planning_safety_gate" not in payload
    assert "selector_inventory" in payload["decision_packet"]["detail_routes"]
    assert payload["decision_packet"]["effects"]["workflow_required"] is True


def _recursive_json_field_count(value: object) -> int:
    if isinstance(value, dict):
        return len(value) + sum(_recursive_json_field_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_recursive_json_field_count(item) for item in value)
    return 0


def _assert_versioned_output_budget(payload: dict[str, object], budget: dict[str, object]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert len(encoded) <= int(budget["max_json_bytes"])
    assert _recursive_json_field_count(payload) <= int(budget["max_field_count"])
    assert (len(encoded) + 3) // 4 <= int(budget["max_estimated_tokens"])


def _startup_output_measurement(payload: dict[str, object]) -> dict[str, int]:
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    pretty = json.dumps(payload, ensure_ascii=False, indent=2)
    return {
        "json_bytes": len(compact),
        "human_lines": len(pretty.splitlines()),
        "field_count": _recursive_json_field_count(payload),
    }


def test_generated_ordinary_guidance_is_executable_from_default_decision_packet_for_weak_agent(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "protected-owner",
                "--title",
                "Protected owner",
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

    guidance = workspace_pointer_block(cli_invoke="agentic-workspace")
    ordinary_route = guidance.split("Ordinary route:", 1)[1].split("Boundaries:", 1)[0]
    assert "authoritative `decision_packet`" in ordinary_route
    assert "do not omit `--format json`" in ordinary_route
    assert "do not open raw config files to rediscover it" in guidance
    assert "`communication_contract` as optional selector-backed" in ordinary_route
    assert "Use the returned `communication_contract`" not in ordinary_route
    assert "--select communication_contract" not in ordinary_route

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement an unrelated parser cache eviction",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert set(payload) == {"kind", "target", "decision_packet", "task_assignment_disposition"}
    assert "communication_contract" not in payload
    decision = payload["decision_packet"]
    action = decision["action"]
    effects = decision["effects"]
    assert action["id"] == "inspect-current-task"
    assert action["id"] in effects["allowed_next_actions"]
    assert action["id"] not in effects["forbidden_actions"]
    assert effects["blocked_claims"] == [
        "claim-active-plan-progress",
        "claim-active-plan-complete",
        "silently-abandon-active-plan",
    ]
    assert decision["claim_boundary"]
    assert decision["owner"]["non_interference"]["status"] == "protected"
    assert decision["owner"]["non_interference"]["restriction"]
    assert set(decision["detail_routes"]) >= {"select", "verbose", "proof_detail", "owner_detail"}
    assert all(".agentic-workspace/" not in route for route in decision["detail_routes"].values())


def test_start_default_compresses_representative_first_contact_without_losing_decision_safety(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    def start(*extra: str) -> dict[str, object]:
        assert cli.main(["start", "--target", str(tmp_path), *extra, "--format", "json"]) == 0
        return json.loads(capsys.readouterr().out)

    payloads = {
        "direct": start("--task", "Fix one docs typo"),
        "module_rich": start("--task", "Shape a workflow issue"),
        "proof_sensitive": start("--changed", "AGENTS.md", "--task", "Review AGENTS.md"),
    }
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "compression-plan",
                "--title",
                "Compression plan",
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
    payloads["planning"] = start("--task", "Compression plan")
    payloads["recovery"] = start("--task", "Implement unrelated parser cache eviction")

    master_baselines = {
        "direct": {"json_bytes": 9332, "human_lines": 361, "field_count": 214},
        "module_rich": {"json_bytes": 25843, "human_lines": 891, "field_count": 524},
        "proof_sensitive": {"json_bytes": 4198, "human_lines": 179, "field_count": 94},
        "planning": {"json_bytes": 14733, "human_lines": 547, "field_count": 318},
        "recovery": {"json_bytes": 10130, "human_lines": 358, "field_count": 228},
    }
    measurements = {name: _startup_output_measurement(payload) for name, payload in payloads.items()}
    for name, measurement in measurements.items():
        baseline = master_baselines[name]
        assert measurement["json_bytes"] <= baseline["json_bytes"] * 0.5 + 64  # explicit assignment outcome envelope
        assert measurement["human_lines"] <= baseline["human_lines"] * 0.5
        assert measurement["field_count"] <= baseline["field_count"] * 0.5 + 2
        assert set(payloads[name]) == {"kind", "target", "decision_packet", "task_assignment_disposition"}
        decision = payloads[name]["decision_packet"]
        assert isinstance(decision, dict)
        assert decision["identity"]["revision"]
        assert decision["action"]["id"]
        assert set(decision["effects"]) >= {
            "workflow_required",
            "implementation_allowed",
            "read_only_allowed",
            "proof_required",
            "completion_claim_allowed",
            "allowed_next_actions",
            "forbidden_actions",
        }
        assert decision["claim_boundary"]
        assert decision["residue_owner"]
        assert decision["reasons"]
        assert set(decision["detail_routes"]) >= {"selector_inventory", "select", "verbose", "skills", "proof_detail"}

    assert measurements["module_rich"]["json_bytes"] <= measurements["direct"]["json_bytes"] + 700
    assert payloads["proof_sensitive"]["decision_packet"]["effects"]["proof_required"] is True
    recovery_owner = payloads["recovery"]["decision_packet"]["owner"]
    assert recovery_owner["non_interference"]["restriction"]
    assert payloads["recovery"]["decision_packet"]["action"]["required_inputs"] == [
        "current task",
        "selected owner identity",
        "non-interference boundary",
    ]


def test_lifecycle_defaults_obey_versioned_output_budgets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0
    cold_init = json.loads(capsys.readouterr().out)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    applied_init = json.loads(capsys.readouterr().out)
    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0
    warm_init = json.loads(capsys.readouterr().out)
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--format", "json"]) == 0
    start = json.loads(capsys.readouterr().out)
    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert cli.main(["doctor", "--target", str(tmp_path), "--format", "json"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert cli.main(["report", "--target", str(tmp_path), "--section", "operational_compression", "--format", "json"]) == 0
    measures = json.loads(capsys.readouterr().out)["answer"]["measures"]
    budget_contract = measures["ordinary_default_output_budget"]
    budgets = {item["surface"]: item for item in budget_contract["representative_surfaces"]}

    assert budget_contract["schema_version"] == "workspace-output-profile-budgets/v2"
    for required_dimension in ("json_bytes", "field_count", "estimated_tokens", "human_lines"):
        assert required_dimension in budget_contract["measurement"]
    for payload in (cold_init, applied_init, warm_init):
        _assert_versioned_output_budget(payload, budgets["init"])
        assert payload["kind"] == "agentic-workspace/lifecycle-decision-envelope/v1"
        assert payload["profile"] == "decision-envelope/v1"
        assert "--verbose" in payload["detail"]["verbose_command"]
        assert "module_reports" not in payload
        assert "config" not in payload
    _assert_versioned_output_budget(start, budgets["start"])
    _assert_versioned_output_budget(report, budgets["report"])
    _assert_versioned_output_budget(doctor, budgets["doctor"])
    assert cold_init.keys() == warm_init.keys()
    assert cold_init["decision"]["mutation"] == "planned-only"
    assert applied_init["decision"]["mutation"] == "applied"

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--verbose", "--format", "json"]) == 0
    verbose_init = json.loads(capsys.readouterr().out)
    assert "module_reports" in verbose_init
    assert "config" in verbose_init

    text_commands = [
        ["init", "--target", str(tmp_path), "--dry-run"],
        ["start", "--target", str(tmp_path), "--task", "Fix one docs typo"],
        ["report", "--target", str(tmp_path)],
        ["doctor", "--target", str(tmp_path)],
    ]
    for argv, surface in zip(text_commands, ("init", "start", "report", "doctor"), strict=True):
        assert cli.main(argv) == 0
        human_lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
        assert len(human_lines) <= int(budgets[surface]["max_human_lines"])


def test_init_default_skips_verbose_config_projection(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    original = workspace_runtime_core._config_payload
    calls: list[object] = []

    def recording_config_payload(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(workspace_runtime_core, "_config_payload", recording_config_payload)

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0
    compact = json.loads(capsys.readouterr().out)
    assert compact["profile"] == "decision-envelope/v1"
    assert calls == []

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--verbose", "--format", "json"]) == 0
    verbose = json.loads(capsys.readouterr().out)
    assert calls
    assert "config" in verbose


def test_operational_compression_surfaces_checked_default_output_budget(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(tmp_path), "--section", "operational_compression", "--format", "json"]) == 0

    measures = json.loads(capsys.readouterr().out)["answer"]["measures"]
    budget = measures["ordinary_default_output_budget"]
    inventory = measures["ordinary_output_shape_inventory"]
    surfaces = {item["surface"]: item for item in budget["representative_surfaces"]}

    assert budget["status"] == "checked"
    assert budget["kind"] == "workspace-ordinary-default-output-budget/v2"
    assert budget["schema_version"] == "workspace-output-profile-budgets/v2"
    assert budget["advisory_only"] is False
    assert inventory["status"] == "checked"
    assert inventory["budget_proven_count"] >= 2
    assert {surface for surface in ("start", "implement", "summary", "report", "proof") if surface in surfaces} == {
        "start",
        "implement",
        "summary",
        "report",
        "proof",
    }
    assert surfaces["start"]["status"] == "budget-proven"
    assert surfaces["init"]["status"] == "budget-proven"
    assert surfaces["doctor"]["status"] == "budget-proven"
    assert all(
        key in surfaces["init"]
        for key in ("max_json_bytes", "max_field_count", "max_estimated_tokens", "max_human_lines", "expansion_trigger")
    )
    assert surfaces["summary"]["status"] == "budget-proven"
    assert budget["selector_relocations"][0]["default_state"] == "selector-routed"


def test_strict_health_classifies_current_state_and_ignores_archive_history() -> None:
    findings = [
        {
            "reason_code": "planning.live-owner-invalid",
            "severity": "warning",
            "module": "planning",
            "path": ".agentic-workspace/planning/execplans/live.plan.json",
            "message": "Live execplan file is not registered in planning state or TODO linkage.",
        },
        {
            "reason_code": "memory.fixture-failed",
            "severity": "warning",
            "module": "memory",
            "path": "tests/fixtures/routing/required.json",
            "message": "fixture 'required memory route' fails; missing expected: memory.md",
        },
        {
            "reason_code": "planning.live-owner-invalid",
            "severity": "warning",
            "module": "planning",
            "path": ".agentic-workspace/planning/execplans/broken-relation.plan.json",
            "message": "Live Planning relation is invalid for the selected owner.",
        },
        {
            "reason_code": "planning.archive-history",
            "severity": "warning",
            "module": "planning",
            "path": ".agentic-workspace/planning/execplans/archive/closed.plan.json",
            "message": "Archived closeout left larger intent open.",
        },
        {
            "reason_code": "maintenance.debt",
            "severity": "warning",
            "module": "workspace",
            "path": ".agentic-workspace",
            "message": "legacy checked-in payload can be reduced",
        },
    ]

    assertion = workspace_runtime_core._strict_health_assertion_payload(
        target_root=Path("."), selected_modules=["planning", "memory"], findings=findings, cli_invoke="agentic-workspace"
    )

    assert assertion["status"] == "failed"
    assert assertion["exit_code"] == 1
    assert assertion["blocking_count"] == 3
    assert assertion["counts_by_class"] == {
        "current-executable-state": 2,
        "current-installed-config-state": 1,
        "actionable-maintenance-debt": 1,
        "historical-informational-state": 1,
    }
    assert {item["owner"] for item in assertion["blockers"]} == {"planning", "memory"}
    assert all(item["action"]["command"] for item in assertion["blockers"])
    assert assertion["proof_receipt"]["policy_fingerprint"] == assertion["policy"]["fingerprint"]
    assert assertion["proof_receipt"]["subject_fingerprint"] == assertion["subject"]["fingerprint"]
    _assert_json_payload_under(assertion, 8_000, label="strict health failure receipt", sort_keys=False)

    archive_only = workspace_runtime_core._strict_health_assertion_payload(
        target_root=Path("."), selected_modules=["planning"], findings=[findings[3]], cli_invoke="agentic-workspace"
    )
    assert archive_only["status"] == "passed"
    assert archive_only["exit_code"] == 0
    assert archive_only["blocking_count"] == 0
    assert archive_only["historical_count"] == 1

    untyped_warning = workspace_runtime_core._strict_health_assertion_payload(
        target_root=Path("."),
        selected_modules=["workspace"],
        findings=[{"severity": "warning", "module": "workspace", "message": "legacy warning without a health class"}],
        cli_invoke="agentic-workspace",
    )
    assert untyped_warning["status"] == "passed"
    assert untyped_warning["maintenance_debt_count"] == 1


def test_report_fail_on_strict_health_has_deterministic_exit_semantics(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    findings = [
        {
            "reason_code": "planning.live-owner-invalid",
            "severity": "warning",
            "module": "planning",
            "path": ".agentic-workspace/planning/execplans/unregistered.plan.json",
            "message": "Live execplan file is not registered in planning state or TODO linkage.",
        }
    ]

    monkeypatch.setattr(workspace_runtime_core, "_run_report_command", lambda **_kwargs: {"findings": findings})
    assert cli.main(["report", "--target", str(tmp_path), "--fail-on", "strict-current", "--format", "json"]) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["status"] == "failed"
    assert failed["blocking_count"] == 1

    findings[0] = {
        "reason_code": "planning.archive-history",
        "severity": "info",
        "module": "planning",
        "path": ".agentic-workspace/planning/execplans/archive/closed.plan.json",
        "message": "Archived closeout remains queryable.",
    }
    assert cli.main(["report", "--target", str(tmp_path), "--fail-on", "strict-current", "--format", "json"]) == 0
    passed = json.loads(capsys.readouterr().out)
    assert passed["status"] == "passed"
    assert passed["historical_count"] == 1


def test_release_promotion_requires_exact_current_passing_strict_health_receipt() -> None:
    receipt = {
        "kind": "agentic-workspace/health-policy-proof-receipt/v1",
        "outcome": "passed",
        "policy_fingerprint": "policy-current",
        "subject_fingerprint": "subject-current",
        "blocking_count": 0,
    }
    accepted = workspace_runtime_core._strict_health_promotion_input(
        receipt=receipt,
        expected_policy_fingerprint="policy-current",
        expected_subject_fingerprint="subject-current",
    )
    assert accepted["status"] == "accepted"
    assert accepted["receipt"] is receipt

    cases = (
        (None, "missing-strict-health-receipt"),
        ({**receipt, "policy_fingerprint": "stale"}, "stale-strict-health-policy"),
        ({**receipt, "subject_fingerprint": "stale"}, "stale-strict-health-subject"),
        ({**receipt, "outcome": "failed", "blocking_count": 1}, "strict-health-failed"),
    )
    for candidate, reason in cases:
        blocked = workspace_runtime_core._strict_health_promotion_input(
            receipt=candidate,
            expected_policy_fingerprint="policy-current",
            expected_subject_fingerprint="subject-current",
        )
        assert blocked["status"] == "blocked"
        assert blocked["reason"] == reason
        assert blocked["receipt"] is None


def test_strict_health_accepts_only_branch_admitted_pending_integration(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _set_git_branch(tmp_path, current="feature/health", default="master")
    owner_ref = ".agentic-workspace/planning/execplans/completed.plan.json"
    proposal = {
        "kind": "planning-integration-proposal/v1",
        "status": "pending",
        "phase": "integration-pending",
        "requested_transition": "mark-integrated",
        "id": "completed-mark-integrated",
        "expected_subject_revision": "subject-current",
        "expected_planning_revision": "planning-current",
        "owner": {"id": "completed", "ref": owner_ref},
        "authority_boundary": {"branch_admission": {"phase": "feature", "branch": "feature/health"}},
    }
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "integration-proposals" / "completed.integration-proposal.json",
        json.dumps(proposal),
    )
    finding = {
        "reason_code": "planning.integration-pending",
        "integration_proposal_id": "completed-mark-integrated",
        "expected_subject_revision": "subject-current",
        "expected_planning_revision": "planning-current",
        "severity": "warning",
        "module": "planning",
        "path": owner_ref,
        "message": "Completed execplan remains in the live execplans directory.",
    }

    feature_assertion = workspace_runtime_core._strict_health_assertion_payload(
        target_root=tmp_path, selected_modules=["planning"], findings=[finding], cli_invoke="agentic-workspace"
    )
    assert feature_assertion["status"] == "passed"
    assert feature_assertion["maintenance_debt_count"] == 1

    for field, bad_value in (
        ("integration_proposal_id", "wrong"),
        ("expected_subject_revision", "stale"),
        ("expected_planning_revision", "stale"),
        ("reason_code", "planning.live-owner-invalid"),
    ):
        malformed = {**finding, field: bad_value}
        rejected = workspace_runtime_core._strict_health_assertion_payload(
            target_root=tmp_path, selected_modules=["planning"], findings=[malformed], cli_invoke="agentic-workspace"
        )
        assert rejected["status"] == "failed"

    proposal_path = tmp_path / ".agentic-workspace" / "planning" / "integration-proposals" / "completed.integration-proposal.json"
    for field, bad_value in (
        ("requested_transition", "unrelated-transition"),
        ("expected_subject_revision", ""),
        ("expected_planning_revision", ""),
    ):
        malformed_proposal = {**proposal, field: bad_value}
        _write(proposal_path, json.dumps(malformed_proposal))
        rejected = workspace_runtime_core._strict_health_assertion_payload(
            target_root=tmp_path, selected_modules=["planning"], findings=[finding], cli_invoke="agentic-workspace"
        )
        assert rejected["status"] == "failed"
    _write(proposal_path, json.dumps(proposal))

    _set_git_branch(tmp_path, current="master", default="master")
    default_assertion = workspace_runtime_core._strict_health_assertion_payload(
        target_root=tmp_path, selected_modules=["planning"], findings=[finding], cli_invoke="agentic-workspace"
    )
    assert default_assertion["status"] == "failed"
    assert default_assertion["blocking_count"] == 1


def test_start_routes_high_assurance_milestone_to_planning_before_implementation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    mark_configuration_readiness_current(tmp_path)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement an entire high-assurance milestone",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    decision = payload["decision_packet"]
    assert decision["effects"]["workflow_required"] is True
    assert decision["action"]["id"] == "create-or-promote-active-execplan"
    assert decision["effects"]["implementation_allowed"] is False
    assert "continue implementation without active planning ownership" in decision["effects"]["forbidden_actions"]


def test_start_reconciles_unrelated_active_plan_with_bounded_reflection_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "active-plan",
            "title": "Unrelated active plan",
            "post_decomposition_delegation": {"status": "ready"},
        },
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Unrelated active plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Estimate AW net effect on this thread",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["decision_packet"]["action"]["id"] == "produce-bounded-reflection-report"
    assert payload["decision_packet"]["effects"]["implementation_allowed"] is True
    assert payload["decision_packet"]["effects"]["proof_required"] is False
    _assert_json_payload_under(payload, 9_000, label="active-plan reflection start payload", sort_keys=False)
    decision = payload["decision_packet"]
    assert decision["owner"]["task_relation"] == "bounded-independent"
    assert decision["owner"]["owner_posture"] == "current"
    assert decision["owner"]["required_transition"] == "none"
    assert "claim-active-plan-complete" in decision["effects"]["blocked_claims"]


def test_start_reconciles_unrelated_active_plan_for_dogfooding_issue_shaping(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "active-plan",
            "title": "Unrelated active plan",
            "post_decomposition_delegation": {"status": "ready"},
        },
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Unrelated active plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Create concrete AW dogfooding feedback issues from this thread",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    decision = payload["decision_packet"]

    _assert_json_payload_under(payload, 9_000, label="dogfooding issue-shaping start payload", sort_keys=False)
    assert decision["action"]["id"] == "produce-bounded-reflection-report"
    assert decision["owner"]["task_relation"] == "bounded-independent"
    assert "claim-active-plan-progress" in decision["effects"]["blocked_claims"]


def test_start_routes_established_mixed_issue_work_as_bounded_independent(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "active-plan",
            "title": "Unrelated active plan",
            "post_decomposition_delegation": {"status": "ready"},
        },
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Unrelated active plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Create concrete AW dogfooding feedback issues and change the runtime",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    decision = payload["decision_packet"]

    assert decision["action"]["id"] == "inspect-current-task"
    assert decision["owner"]["task_relation"] == "bounded-independent"
    assert decision["owner"]["required_transition"] == "none"
    assert decision["effects"]["implementation_allowed"] is True
    assert "claim-active-plan-progress" in decision["effects"]["blocked_claims"]


def test_start_reconciles_unrelated_active_plan_with_new_issue_implementation_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Unrelated active plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        json.dumps({"id": "active-plan", "title": "Unrelated active plan"}),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement parser cache eviction for issue routing",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 12_000, label="active-plan issue start payload", sort_keys=False)
    assert payload["decision_packet"]["action"]["id"] == "inspect-current-task"
    assert payload["decision_packet"]["owner"]["non_interference"]["status"] == "protected"
    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement parser cache eviction for issue routing",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]
    start_route = route
    assert route["task_relation"] == "bounded-independent"
    assert route["required_transition"] == "none"
    assert route["implementation_allowed"] is True
    assert payload["decision_packet"]["effects"]["implementation_allowed"] is True
    assert route["next_safe_action"]["action"] == "inspect-current-task"
    assert route["non_interference_boundary"]["restriction"]

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--task",
                "Implement parser cache eviction for issue routing",
                "--select",
                "planning_route_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)
    route = selected["values"]["planning_route_decision"]
    assert route["task_relation"] == "bounded-independent"
    assert route["required_transition"] == "none"
    assert route["implementation_allowed"] is True
    assert route["consumer_contract"] == start_route["consumer_contract"]
    assert route["identity_effects"] == start_route["identity_effects"]
    assert route["non_interference_boundary"] == start_route["non_interference_boundary"]


def test_start_blocks_independent_task_that_overlaps_active_owner_scope(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Unrelated active plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "active-plan",
            "title": "Unrelated active plan",
            "scope": {"owned": ["src/owned.py"]},
        },
    )
    _write(tmp_path / "src" / "owned.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement parser cache eviction for issue routing",
                "--changed",
                "src/owned.py",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]

    assert route["task_relation"] == "ambiguous"
    assert route["implementation_allowed"] is False
    assert route["non_interference_boundary"]["status"] == "overlap-blocked"
    assert route["non_interference_boundary"]["overlap_paths"] == ["src/owned.py"]


def test_start_allows_selected_owner_to_mutate_its_declared_scope(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Implement parser cache eviction for issue routing", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "active-plan",
            "title": "Implement parser cache eviction for issue routing",
            "scope": {"owned": ["src/owned.py"]},
        },
    )
    _write(tmp_path / "src" / "owned.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement parser cache eviction for issue routing",
                "--changed",
                "src/owned.py",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]

    assert route["task_relation"] == "continues-selected-owner"
    assert route["required_transition"] == "none"
    assert route["implementation_allowed"] is True
    assert "non_interference_boundary" not in route


def test_target_authority_reconciliation_ignores_empty_preview(tmp_path: Path, monkeypatch) -> None:
    proposal_root = tmp_path / ".agentic-workspace" / "planning" / "integration-proposals"
    proposal_root.mkdir(parents=True)
    _write_json(proposal_root / "integrated.integration-proposal.json", {"status": "integrated"})
    monkeypatch.setattr(
        planning_installer,
        "planning_reconcile",
        lambda **_: {
            "transaction_class": "target-authority-integration",
            "status": "preview",
            "proposal": {
                "proposal_id": "empty-preview",
                "source": {"planning_revision": "planning-a"},
                "operations": [],
                "eligible_proposals": [],
                "refreshed_proposals": [],
            },
        },
    )

    result = workspace_runtime_planning._compiled_target_authority_reconciliation(target_root=tmp_path, cli_invoke="agentic-workspace")

    assert result == {"status": "absent", "reason": "no-target-authority-reconciliation-work"}


def test_current_reconciliation_proposal_ignores_noop_current_and_stale_cache(tmp_path: Path) -> None:
    proposal_root = tmp_path / ".agentic-workspace" / "local" / "planning" / "reconciliation-proposals"
    proposal_root.mkdir(parents=True)
    for proposal_id, revision in (("current-noop", "planning-a"), ("stale-noop", "planning-old")):
        _write_json(
            proposal_root / f"{proposal_id}.json",
            {
                "proposal_id": proposal_id,
                "source": {"planning_revision": revision},
                "apply_command": f"agentic-workspace planning reconcile --apply --proposal {proposal_id}",
                "operations": [],
                "owner_transitions": [{"owner_id": "owner", "transition": "remain-live"}],
            },
        )
    _write_json(
        proposal_root / "stale-target-authority.json",
        {
            "proposal_id": "stale-target-authority",
            "transaction_class": "target-authority-integration",
            "source": {"planning_revision": "planning-old"},
            "apply_command": "agentic-workspace planning reconcile --apply --proposal stale-target-authority",
            "operations": [{"operation": "apply-current-proposal"}],
        },
    )

    result = workspace_runtime_planning._current_reconciliation_proposal(
        target_root=tmp_path, planning_revision={"revision_id": "planning-a"}
    )

    assert result == {"status": "absent"}


def test_current_reconciliation_proposal_preserves_actionable_stale_cache(tmp_path: Path) -> None:
    proposal_root = tmp_path / ".agentic-workspace" / "local" / "planning" / "reconciliation-proposals"
    proposal_root.mkdir(parents=True)
    _write_json(
        proposal_root / "stale-actionable.json",
        {
            "proposal_id": "stale-actionable",
            "source": {"planning_revision": "planning-old"},
            "apply_command": "agentic-workspace planning reconcile --apply --proposal stale-actionable",
            "operations": [{"operation": "archive-owner"}],
        },
    )

    result = workspace_runtime_planning._current_reconciliation_proposal(
        target_root=tmp_path, planning_revision={"revision_id": "planning-a"}
    )

    assert result == {"status": "stale", "freshness": "stale", "proposal_id": "stale-actionable"}


def test_target_authority_reconciliation_preserves_actionable_preview(tmp_path: Path, monkeypatch) -> None:
    proposal_root = tmp_path / ".agentic-workspace" / "planning" / "integration-proposals"
    proposal_root.mkdir(parents=True)
    _write_json(proposal_root / "pending.integration-proposal.json", {"status": "pending"})
    monkeypatch.setattr(
        planning_installer,
        "planning_reconcile",
        lambda **_: {
            "transaction_class": "target-authority-integration",
            "status": "preview",
            "proposal": {
                "proposal_id": "actionable-preview",
                "source": {"planning_revision": "planning-a"},
                "preview_command": "agentic-workspace planning reconcile --preview",
                "apply_command": "agentic-workspace planning reconcile --apply",
                "current_target_authority_revision": "target-a",
                "affected_owner_refs": ["owner.plan.json"],
                "operations": [{"operation": "apply-current-proposal"}],
                "eligible_proposals": ["pending"],
                "refreshed_proposals": [],
            },
        },
    )

    result = workspace_runtime_planning._compiled_target_authority_reconciliation(target_root=tmp_path, cli_invoke="agentic-workspace")

    assert result["status"] == "preview-available"
    assert result["operations"] == [{"operation": "apply-current-proposal"}]
    assert result["eligible_proposals"] == ["pending"]


def test_start_routes_completed_active_plan_to_archive_before_new_reflection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(
        tmp_path,
        include_proof=True,
        active_milestone_status="completed",
        terminal_phase=True,
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Estimate AW net effect on this thread",
                "--select",
                "planning_safety_gate,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    selected = payload["values"]
    route = selected["planning_safety_gate"]["route_decision"]
    admission = route["owner_admission"]

    assert selected["next_safe_action"]["next_safe_action"] != "archive-or-retire-completed-plan"
    assert admission["status"] == "rejected"
    assert admission["rejected_candidates"][0]["ref"] == ".agentic-workspace/planning/execplans/issue-1981.plan.json"
    assert admission["rejected_candidates"][0]["reason"] == "owner-phase-terminal"
    assert admission["repair_route"]["status"] == "available"
    assert admission["admission_contract"]["consumers"] == [
        "start",
        "next",
        "implement",
        "autopilot",
        "proof",
        "closeout",
        "archive",
        "status",
        "doctor",
        "report",
    ]
    assert admission["action_effect"]["force"] == "required_before_action"
    assert "closeout" in admission["action_effect"]["blocked_until_reconciled"]
    assert "archive" in admission["action_effect"]["blocked_until_reconciled"]
    assert route.get("selected_owner_identity", {}).get("ref", "") == ""

    assert (
        cli.main(
            [
                "planning",
                "archive-plan",
                "--plan",
                "issue-1981",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--retain-archive",
                "--apply-cleanup",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Estimate AW net effect on this thread",
                "--format",
                "json",
            ]
        )
        == 0
    )
    after = json.loads(capsys.readouterr().out)

    assert after["decision_packet"]["action"]["id"] != "archive-or-retire-completed-plan"


def test_implement_routes_post_closeout_archive_residue_as_verification(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=True, active_milestone_status="completed")
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "planning",
                "archive-plan",
                "--plan",
                "issue-1981",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--retain-archive",
                "--apply-cleanup",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    changed = [
        "src/agentic_workspace/workspace_runtime_core.py",
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/archive/issue-1981.plan.json",
    ]
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                *changed,
                "--task",
                "Final post-closeout verification for #1981",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    gate = payload["values"]["planning_safety_gate"]

    assert gate["gate_result"] == "post-closeout-verification"
    assert gate["workflow_sufficient"] is True
    assert gate["required_next_action"] == "run-post-closeout-verification"
    assert gate["changed_path_facts"]["dirty_shape"] == "implementation-with-archived-planning-residue"
    assert gate["changed_path_facts"]["archived_planning_residue"]["status"] == "completed-closeout-residue"


def test_start_reconciles_current_external_completion_before_independent_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_issue_1981_closeout_fixture(tmp_path, include_proof=False)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement unrelated parser cleanup",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    decision = payload["decision_packet"]

    assert decision["action"]["id"] == "compile-planning-reconciliation-proposal"
    assert "planning reconcile --target . --preview" in decision["action"]["command"]
    assert decision["owner"]["task_relation"] == "bounded-independent"
    assert decision["owner"]["owner_posture"] == "external-conflict"
    assert decision["owner"]["required_transition"] == "reconcile"
    assert decision["effects"]["implementation_allowed"] is False
    assert "claim-active-plan-progress" in decision["effects"]["blocked_claims"]


def test_implement_acknowledges_current_task_switch_with_return_and_cleanup_routes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", title = "Unrelated active plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-plan.plan.json",
        {"kind": "planning-execplan/v1", "id": "active-plan", "title": "Unrelated active plan"},
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--task",
                "Implement unrelated parser cleanup",
                "--select",
                "context",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]
    route = payload["context"]["planning_safety_gate"]["route_decision"]

    assert route["task_relation"] == "bounded-independent"
    assert route["required_transition"] == "refresh-mutation-baseline"
    assert route["next_safe_action"]["action"] == "refresh-mutation-baseline"
    assert "claim-active-plan-progress" in route["blocked_claims"]


def test_implement_allows_proven_ignored_transient_cleanup_outside_active_plan(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    _write(tmp_path / ".gitignore", ".agentic-workspace/local/\n.pytest_cache/\n")
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """schema_version = 1

[todo]
active_items = [{ id = "active-plan", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json" }]
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json",
        {"kind": "planning-execplan/v1", "id": "active-plan", "lifecycle": "live"},
    )
    _write(tmp_path / ".agentic-workspace/local/tmp.txt", "transient\n")
    _write(tmp_path / ".pytest_cache/v/cache/nodeids", "[]\n")
    before = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/local/tmp.txt",
                ".pytest_cache/v/cache/nodeids",
                "--task",
                "Delete only ignored transient cleanup residue; preserve tracked files, meaningful untracked work, .venv, and .agentic-workspace/config.local.toml",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    route = gate["route_decision"]
    effect_scope = route["structured_inputs"]["task_binding"]["effect_scope"]

    assert effect_scope["status"] == "proven-local-transient"
    assert route["task_relation"] == "bounded-independent"
    assert route["required_transition"] == "none"
    assert route["implementation_allowed"] is True
    assert route["mutation_authority"] == "current-task"
    assert route["structured_inputs"]["task_binding"]["mode"] == "local-transient-cleanup"
    assert route["structured_inputs"]["task_binding"]["effect_scope"]["claim_authority"] == "none-for-active-planning"
    assert "claim-active-plan-progress" in route["blocked_claims"]
    assert (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8") == before


def test_transient_cleanup_scope_fails_closed_for_durable_paths(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / ".gitignore", ".agentic-workspace/local/\n")
    _write(tmp_path / ".agentic-workspace/config.local.toml", "[workspace]\n")

    facts = cli._planning_safety_path_classification(
        [".agentic-workspace/config.local.toml"],
        target_root=tmp_path,
        task_text="Delete cleanup files; preserve tracked files, meaningful untracked work, .venv, and .agentic-workspace/config.local.toml",
    )

    assert facts["effect_scope"]["status"] == "not-proven"
    assert facts["effect_scope"]["protected_paths"] == [".agentic-workspace/config.local.toml"]
    assert facts["effect_scope"]["constructible_next_action"]["command"] == "git status --short --ignored"


def test_start_treats_shared_issue_ref_as_active_plan_continuation(tmp_path: Path, capsys) -> None:
    from types import SimpleNamespace

    from agentic_workspace.workspace_runtime_planning import _task_switch_reconciliation_payload

    switch = _task_switch_reconciliation_payload(
        active_planning_present=True,
        active_plan_reliance={"status": "not-needed-for-current-task"},
        active_summary={
            "active_execplan": ".agentic-workspace/planning/execplans/issue-2046-lane.plan.json",
            "active_item_id": "issue-2046-lane",
            "planning_status": "active",
        },
        task_text="Implement the whole #2046 lane",
        config=SimpleNamespace(cli_invoke="agentic-workspace"),
        planning_revision={"status": "clean", "revision": "fixture"},
    )

    assert switch["status"] == "issue-matched-continuation"
    assert switch["recommended_next_action"] == "continue-active-plan"
    assert switch["intent_conflict_state"] == "explicit-reference-continuation"
    assert "issue-2046" in switch["mismatch_evidence"]["shared_refs"]
    assert (
        switch["rule"]
        == "Exact task/owner-intent identity or structured ref overlap is continuation evidence; arbitrary prose keyword overlap is not."
    )

    plural_lane_switch = _task_switch_reconciliation_payload(
        active_planning_present=True,
        active_plan_reliance={"status": "not-needed-for-current-task"},
        active_summary={
            "active_execplan": ".agentic-workspace/planning/execplans/issues-2045-2047-followups.plan.json",
            "active_item_id": "issues-2045-2047-followups",
            "planning_status": "active",
        },
        task_text="Finish issue comments for #2045",
        config=SimpleNamespace(cli_invoke="agentic-workspace"),
        planning_revision={"status": "clean", "revision": "fixture"},
    )
    assert plural_lane_switch["status"] == "issue-matched-continuation"
    assert "issue-2045" in plural_lane_switch["mismatch_evidence"]["shared_refs"]


def test_active_owner_refs_ignore_non_authoritative_plan_history(tmp_path: Path) -> None:
    owner_ref = ".agentic-workspace/planning/execplans/issue-2258.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f'''schema_version = 1

[todo]
active_items = [{{ id = "issue-2258", status = "active", surface = "{owner_ref}", refs = ["#2258"] }}]
''',
    )
    _write(
        tmp_path / owner_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2258",
                "title": "Implement #2258",
                "lifecycle": "live",
                "phase": "implementation",
                "intent": {"outcome": "Complete issue #2258", "non_goals": ["Do not absorb #9001"]},
                "dependencies": ["#9002"],
                "relationships": {"related": ["#9003"]},
                "proof": {"refs": ["#9004"]},
                "execution_summary": {"completed follow-up": "#9005"},
                "references": [
                    {"kind": "issue", "target": "#2258", "role": "intake"},
                    {"kind": "issue", "target": "#9006", "role": "supporting-evidence"},
                ],
            }
        ),
    )

    summary = cli._fast_planning_active_summary(target_root=tmp_path)

    assert summary["active_owner_refs"] == ["#2258", "issue-2258"]
    for unrelated_ref in ("#9001", "#9002", "#9003", "#9004", "#9005", "#9006"):
        mismatch = cli._task_switch_mismatch_evidence(active_summary=summary, task_text=f"Continue {unrelated_ref}")
        assert mismatch["shared_refs"] == []
        assert mismatch["overlap_signal"] == "low-overlap-explicit-task"


def test_fast_planning_summary_uses_local_owner_without_legacy_state(tmp_path: Path) -> None:
    selected_ref = ".agentic-workspace/planning/execplans/owner-a.plan.json"
    other_ref = ".agentic-workspace/planning/execplans/owner-b.plan.json"
    for owner_ref, owner_id in ((selected_ref, "owner-a"), (other_ref, "owner-b")):
        _write(
            tmp_path / owner_ref,
            json.dumps(
                {
                    "kind": "planning-execplan/v1",
                    "id": owner_id,
                    "title": owner_id,
                    "lifecycle": "live",
                    "phase": "implementation",
                    "intent": {"outcome": f"Complete {owner_id}"},
                }
            ),
        )
    planning_revision = cli._planning_owner_selection_basis_revision(target_root=tmp_path, state_data={})
    _write(
        tmp_path / ".agentic-workspace/local/planning/owner-selection.json",
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "default",
                "selected_owner": {"id": "owner-a", "ref": selected_ref},
                "planning_revision": planning_revision,
            }
        ),
    )

    summary = cli._fast_planning_active_summary(target_root=tmp_path)

    assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    assert summary["active_execplan"] == selected_ref
    assert summary["todo_active_count"] == 1
    assert summary["planning_status"] == "present"


def test_planning_module_detector_accepts_owner_scoped_install_without_legacy_state(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    planning_installer.install_bootstrap(target=tmp_path)

    planning = workspace_runtime_core._module_operations()["planning"]

    assert planning.detector(tmp_path) is True
    assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()


def test_start_route_rejects_local_selected_owner_from_other_work_context(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    shared_ref = ".agentic-workspace/planning/execplans/issue-2290.plan.json"
    selected_ref = ".agentic-workspace/planning/execplans/issue-2281.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """schema_version = 1

[todo]
active_items = [{ id = "issue-2290", status = "active", surface = ".agentic-workspace/planning/execplans/issue-2290.plan.json", refs = ["#2290"] }]
""",
    )
    _write(
        tmp_path / shared_ref,
        json.dumps({"kind": "planning-execplan/v1", "id": "issue-2290", "lifecycle": "live", "phase": "implementation"}),
    )
    _write(
        tmp_path / selected_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2281",
                "lifecycle": "live",
                "phase": "implementation",
                "references": [{"kind": "issue", "target": "#2281"}],
            }
        ),
    )
    _write(
        tmp_path / ".agentic-workspace/local/planning/owner-selection.json",
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "isolated-stack",
                "selected_owner": {"id": "issue-2281", "ref": selected_ref},
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2281 reconciliation",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    gate = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]
    route = gate["route_decision"]
    assert route["selected_owner"] == shared_ref
    assert route["task_relation"] == "bounded-independent"
    assert route["required_transition"] == "none"
    assert route["implementation_allowed"] is True
    assert "claim-active-plan-progress" in route["blocked_claims"]
    assert route["owner_admission"]["rejected_candidates"][0]["ref"] == selected_ref
    assert route["owner_admission"]["rejected_candidates"][0]["reason"] == "local-selection-current-work-mismatch"
    assert gate["owner_admission"] == route["owner_admission"]
    assert route["binding"]["identity"]["observed"]["selected_owner"]["ref"] == shared_ref
    assert route["binding"]["adoption_guard"]["on_mismatch"] == "reject-stale-projection-and-re-resolve"

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2281 reconciliation",
                "--format",
                "json",
            ]
        )
        == 0
    )
    default_payload = json.loads(capsys.readouterr().out)
    assert default_payload["decision_packet"]["owner"]["identity"]["ref"] == shared_ref
    assert "owner_admission" not in default_payload["decision_packet"]["owner"]

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2281 reconciliation",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )
    verbose_payload = json.loads(capsys.readouterr().out)
    verbose_admission = verbose_payload["active_state_summary"]["owner_admission"]
    assert verbose_admission["rejected_candidates"][0]["reason"] == route["owner_admission"]["rejected_candidates"][0]["reason"]


def test_start_route_honors_explicit_residual_selected_owner(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap.installer import planning_revision

    _init_git_repo(tmp_path)
    shared_ref = ".agentic-workspace/planning/execplans/issue-2290.plan.json"
    selected_ref = ".agentic-workspace/planning/execplans/issue-2281.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """schema_version = 1

[todo]
active_items = [{ id = "issue-2290", status = "active", surface = ".agentic-workspace/planning/execplans/issue-2290.plan.json", refs = ["#2290"] }]
""",
    )
    _write(
        tmp_path / shared_ref,
        json.dumps({"kind": "planning-execplan/v1", "id": "issue-2290", "lifecycle": "live", "phase": "implementation"}),
    )
    _write(
        tmp_path / selected_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2281",
                "lifecycle": "live",
                "phase": "implementation",
                "assignment_target_identity_ref": "assignment-target:issue-2281",
                "assignment_revision": "assignment-rev-1",
                "evaluation_result_identity": "evaluation-result:issue-2281:passed",
                "proof_obligation_revision": "proof-obligation-rev-1",
                "mutation_baseline_id": "mutation-baseline-1",
                "integration_revision": "integration-rev-1",
                "relationships": {"selection": {"state": "explicit-residual", "admission": "explicit"}},
                "references": [{"kind": "issue", "target": "#2281"}],
            }
        ),
    )
    revision_id = planning_revision(tmp_path)["revision_id"]
    _write(
        tmp_path / ".agentic-workspace/local/work-threads/index.json",
        json.dumps({"kind": "agentic-workspace/local-work-thread-index/v1", "selected_thread_id": "isolated-stack"}),
    )
    _write(
        tmp_path / ".agentic-workspace/local/planning/owner-selection.json",
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "isolated-stack",
                "selected_owner": {"id": "issue-2281", "ref": selected_ref},
                "planning_revision": revision_id,
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2281 reconciliation",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]
    assert route["selected_owner"] == selected_ref
    assert route["task_relation"] == "continues-selected-owner"
    assert route["owner_admission"]["selected_owner"]["reason"] == "explicit-residual-owner"
    assert "proof" in route["owner_admission"]["admission_contract"]["consumers"]
    assert "closeout" in route["owner_admission"]["admission_contract"]["consumers"]
    assert "archive" in route["owner_admission"]["admission_contract"]["consumers"]
    reference_identity = route["owner_admission"]["selected_owner"]["reference_identity"]
    assert reference_identity["owner_ref"] == selected_ref
    assert reference_identity["owner_id"] == "issue-2281"
    assert reference_identity["current_planning_revision"]


def test_start_route_accepts_owner_scoped_local_selection_despite_aggregate_revision_change(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap.installer import planning_revision

    _init_git_repo(tmp_path)
    selected_ref = ".agentic-workspace/planning/execplans/issue-2290.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """schema_version = 1

[todo]
active_items = [{ id = "issue-2290", status = "active", surface = ".agentic-workspace/planning/execplans/issue-2290.plan.json", refs = ["#2290"] }]
""",
    )
    _write(
        tmp_path / selected_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2290",
                "lifecycle": "live",
                "phase": "implementation",
                "assignment_target_identity_ref": "assignment-target:issue-2290",
                "assignment_revision": "assignment-rev-1",
                "evaluation_result_identity": "evaluation-result:issue-2290:passed",
                "proof_obligation_revision": "proof-obligation-rev-1",
                "mutation_baseline_id": "mutation-baseline-1",
                "integration_revision": "integration-rev-1",
            }
        ),
    )
    assert planning_revision(tmp_path)["revision_id"] != "stale-revision"
    _write(
        tmp_path / ".agentic-workspace/local/planning/owner-selection.json",
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "default",
                "selected_owner": {"id": "issue-2290", "ref": selected_ref},
                "planning_revision": "stale-revision",
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2290",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]
    admission = route["owner_admission"]
    assert route["selected_owner"] == selected_ref
    assert admission["rejected_candidates"] == []
    assert admission["selected_owner"]["source"] == ".agentic-workspace/local/planning/owner-selection.json"


def test_start_route_rejects_local_selection_from_another_current_work(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap.installer import planning_revision

    _init_git_repo(tmp_path)
    selected_ref = ".agentic-workspace/planning/execplans/issue-2281.plan.json"
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "schema_version = 1\n\n[todo]\nactive_items = []\n")
    _write(
        tmp_path / selected_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2281",
                "lifecycle": "live",
                "phase": "implementation",
                "relationships": {"selection": {"state": "explicit-residual", "admission": "explicit"}},
            }
        ),
    )
    revision_id = planning_revision(tmp_path)["revision_id"]
    _write(
        tmp_path / ".agentic-workspace/local/work-threads/index.json",
        json.dumps({"kind": "agentic-workspace/local-work-thread-index/v1", "selected_thread_id": "current-thread"}),
    )
    _write(
        tmp_path / ".agentic-workspace/local/planning/owner-selection.json",
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "other-thread",
                "selected_owner": {"id": "issue-2281", "ref": selected_ref},
                "planning_revision": revision_id,
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2281",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]
    assert route["selected_owner"] == ""
    rejected = route["owner_admission"]["rejected_candidates"][0]
    assert rejected["reason"] == "local-selection-current-work-mismatch"
    assert rejected["expected_current_work_id"] == "current-thread"
    assert rejected["selection_current_work_id"] == "other-thread"


def test_start_route_rejects_local_selection_from_another_target(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap.installer import planning_revision

    _init_git_repo(tmp_path)
    selected_ref = ".agentic-workspace/planning/execplans/issue-2281.plan.json"
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "schema_version = 1\n\n[todo]\nactive_items = []\n")
    _write(
        tmp_path / selected_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2281",
                "lifecycle": "live",
                "phase": "implementation",
                "relationships": {"selection": {"state": "explicit-residual", "admission": "explicit"}},
            }
        ),
    )
    _write(
        tmp_path / ".agentic-workspace/local/planning/owner-selection.json",
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "default",
                "target_root": str(tmp_path / "other-worktree"),
                "selected_owner": {"id": "issue-2281", "ref": selected_ref},
                "planning_revision": planning_revision(tmp_path)["revision_id"],
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2281",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]
    assert route["selected_owner"] == ""
    assert route["owner_admission"]["rejected_candidates"][0]["reason"] == "local-selection-target-mismatch"


def test_start_route_accepts_active_execplans_owner_through_shared_admission(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    selected_ref = ".agentic-workspace/planning/execplans/issue-2290.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """schema_version = 1

[todo]
active_items = []

[active]
execplans = [{ id = "issue-2290", path = ".agentic-workspace/planning/execplans/issue-2290.plan.json" }]
""",
    )
    _write(
        tmp_path / selected_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2290",
                "lifecycle": "live",
                "phase": "implementation",
                "revision": "owner-rev-1",
                "assignment_target_identity_ref": "assignment-target:issue-2290",
                "assignment_revision": "assignment-rev-1",
                "evaluation_result_identity": "evaluation-result:issue-2290:passed",
                "proof_obligation_revision": "proof-obligation-rev-1",
                "mutation_baseline_id": "mutation-baseline-1",
                "integration_revision": "integration-rev-1",
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2290",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]
    assert route["selected_owner"] == selected_ref
    assert route["owner_admission"]["selected_owner"]["source"] == ".agentic-workspace/planning/state.toml:active.execplans"
    reference_identity = route["owner_admission"]["selected_owner"]["reference_identity"]
    assert reference_identity["owner_ref"] == selected_ref
    assert reference_identity["owner_id"] == "issue-2290"
    assert reference_identity["record_revision"] == "owner-rev-1"
    assert reference_identity["assignment_target_identity_ref"] == "assignment-target:issue-2290"
    assert reference_identity["assignment_revision"] == "assignment-rev-1"
    assert reference_identity["evaluation_result_identity"] == "evaluation-result:issue-2290:passed"
    assert reference_identity["proof_obligation_revision"] == "proof-obligation-rev-1"
    assert reference_identity["mutation_baseline_id"] == "mutation-baseline-1"
    assert reference_identity["integration_revision"] == "integration-rev-1"
    assert reference_identity["identity_completeness"] == "complete"
    assert reference_identity["missing_required_fields"] == []


def test_start_route_rejects_active_execplan_missing_required_authority_identity(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    selected_ref = ".agentic-workspace/planning/execplans/issue-2290.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """schema_version = 1

[todo]
active_items = []

[active]
execplans = [{ id = "issue-2290", path = ".agentic-workspace/planning/execplans/issue-2290.plan.json" }]
""",
    )
    _write(
        tmp_path / selected_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2290",
                "lifecycle": "live",
                "phase": "implementation",
                "revision": "owner-rev-1",
                "assignment_target_identity_ref": "assignment-target:issue-2290",
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #2290",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]
    assert route["selected_owner"] == ""
    rejected = route["owner_admission"]["rejected_candidates"][0]
    assert rejected["reason"] == "required-authority-identity-missing"
    assert "assignment_revision" in rejected["missing_required_fields"]


def test_start_route_replays_stale_2290_local_selection_without_claim_constraints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    selected_ref = ".agentic-workspace/planning/execplans/issue-2290.plan.json"
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "schema_version = 1\n\n[todo]\nactive_items = []\n")
    _write(
        tmp_path / selected_ref,
        json.dumps({"kind": "planning-execplan/v1", "id": "issue-2290", "lifecycle": "live", "phase": "implementation"}),
    )
    _write(
        tmp_path / ".agentic-workspace/local/planning/owner-selection.json",
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "stale-2290-thread",
                "selected_owner": {"id": "issue-2290", "ref": selected_ref},
                "planning_revision": "stale-revision",
            }
        ),
    )

    before_files = sorted(path.relative_to(tmp_path).as_posix() for path in (tmp_path / ".agentic-workspace").rglob("*") if path.is_file())
    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement unrelated issue #3000",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    after_files = sorted(path.relative_to(tmp_path).as_posix() for path in (tmp_path / ".agentic-workspace").rglob("*") if path.is_file())
    route = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]["route_decision"]
    assert before_files == after_files
    assert route["selected_owner"] == ""
    assert route["task_relation"] == "not-applicable"
    assert route["owner_admission"]["status"] == "rejected"
    assert route["owner_admission"]["rejected_candidates"][0]["reason"] == "local-selection-current-work-mismatch"
    assert "claim-active-plan-progress" not in route.get("blocked_claims", [])


def test_route_decision_keeps_relation_posture_and_transition_separate() -> None:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    decision = _planning_route_decision_payload(
        {
            "status": "issue-matched-continuation",
            "active_execplan": ".agentic-workspace/planning/execplans/issue-2046-lane.plan.json",
            "intent_conflict_state": "explicit-reference-continuation",
            "implementation_allowed": True,
            "active_plan_protection": {"blocked_claims": ["silently-close-active-plan"]},
            "next_action_packet": {"action": "continue-active-plan", "next_proof": "run focused proof"},
        }
    )

    assert decision["task_relation"] == "continues-selected-owner"
    assert decision["owner_posture"] == "current"
    assert decision["required_transition"] == "none"
    assert decision["next_safe_action"]["action"] == "continue-active-plan"
    assert decision["input_provenance"]["required_transition"].endswith("planning reconcile")
    assert decision["selected_owner_identity"]["ref"].endswith("issue-2046-lane.plan.json")
    consumers = decision["consumer_contract"]
    assert consumers["ordinary_consumers"] == [
        "startup",
        "implement",
        "preflight",
        "summary",
        "actionability",
        "skills",
        "SkillSpec",
        "Planning handoff",
        "proof",
        "closeout",
        "generated targets",
        "external consumers",
        "no-CLI fallback",
    ]
    assert consumers["inventory_ref"] == "docs/maintainer/planning-route-consumer-inventory.json"
    assert consumers["profiles"] == ["tiny", "compact", "full"]
    assert consumers["parallel_classification"] == "backgrounded-diagnostic-only"
    assert consumers["degraded_recovery"] == {
        "status": "typed",
        "missing_owner": "select-owner",
        "stale_binding": "refresh-planning-route-decision",
        "projection_drift": "repair-projection",
        "external_conflict": "reconcile",
    }
    assert decision["identity_effects"][0]["effect"] == "invalidate-and-rebind-before-action"
    assert decision["identity_effects"][0]["residue_policy"] == "do-not-persist-orienting-read-state"


def test_route_decision_consumer_profiles_share_one_authority_and_recovery_matrix() -> None:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    base = {
        "task_relation": "continues-selected-owner",
        "owner_posture": "projection-drifted",
        "route_inputs": {"owner": {"ref": "owner-a", "revision": "revision-a", "projection_status": "drifted"}},
    }
    decisions = [
        _planning_route_decision_payload({**base, "consumer_profile": profile}, planning_revision={"revision_id": "planning-a"})
        for profile in ("tiny", "compact", "full")
    ]

    authoritative = [
        (
            item["task_relation"],
            item["owner_posture"],
            item["required_transition"],
            item["next_safe_action"]["action"],
            item["consumer_contract"],
        )
        for item in decisions
    ]
    assert authoritative[0] == authoritative[1] == authoritative[2]
    assert decisions[0]["required_transition"] == "repair-projection"
    assert decisions[0]["consumer_contract"]["freshness_inputs"] == [
        "planning_revision",
        "selected_owner_revision",
        "selected_owner_lifecycle",
        "selected_owner_projection_status",
        "external_observation_revision",
        "task_binding_identity",
        "mutation_baseline_id",
        "reconciliation_proposal_revision",
    ]


def test_every_declared_route_consumer_is_a_no_divergence_projection() -> None:
    from agentic_workspace.workspace_runtime_planning import (
        _planning_route_decision_payload,
        planning_route_consumer_projection,
    )

    decision = _planning_route_decision_payload(
        {
            "task_relation": "bounded-independent",
            "owner_posture": "current",
            "route_inputs": {"task_binding": {"mode": "read-only"}},
        },
        planning_revision={"revision_id": "planning-current"},
    )
    projections = [
        planning_route_consumer_projection(route_decision=decision, consumer=consumer)
        for consumer in decision["consumer_contract"]["ordinary_consumers"]
    ]
    identity = {
        (
            item["decision_id"],
            item["input_revision"],
            json.dumps(item["action_identity"], sort_keys=True),
            item["required_transition"],
            tuple(item["blocked_claims"]),
            item["state_update_policy"],
        )
        for item in projections
    }
    assert len(identity) == 1
    assert all(item["authority"] == "planning_safety_gate.route_decision" for item in projections)
    assert decision["consumer_projections"] == {item["consumer"]: item for item in projections}
    with pytest.raises(ValueError, match="unsupported Planning route consumer"):
        planning_route_consumer_projection(route_decision=decision, consumer="parallel-classifier")


def test_executable_child_adoption_projects_one_authoritative_route_decision(tmp_path: Path, capsys) -> None:
    from agentic_workspace.workspace_runtime_planning import validate_planning_route_action_invocation

    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    owner_ref = ".agentic-workspace/planning/execplans/umbrella.plan.json"
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        f'''kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  {{ id = "umbrella", title = "Umbrella owner", status = "active", surface = "{owner_ref}" }},
]
queued_items = []

[roadmap]
lanes = []
candidates = []
''',
    )
    _write(
        tmp_path / owner_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "umbrella",
                "title": "Umbrella owner",
                "lifecycle": "live",
                "revision": 7,
                "intent": {"outcome": "Deliver the umbrella lane"},
                "references": [{"role": "intake", "target": "GitHub #4321"}],
            }
        ),
    )
    _write(tmp_path / "src" / "example.py", "VALUE = 1\n")
    capsys.readouterr()

    task = "Apply the bounded child fix for GitHub #4321"
    changed = "src/example.py"
    commands = [
        ["start", "--select", "planning_route_decision"],
        ["implement", "--select", "planning_route_decision"],
        ["proof", "--select", "planning_route_decision"],
    ]
    routes: list[dict[str, Any]] = []
    for command in commands:
        assert cli.main([*command, "--target", str(tmp_path), "--task", task, "--changed", changed, "--format", "json"]) == 0
        routes.append(json.loads(capsys.readouterr().out)["values"]["planning_route_decision"])

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "closeout_trust",
                "--task",
                task,
                "--changed",
                changed,
                "--format",
                "json",
            ]
        )
        == 0
    )
    routes.append(json.loads(capsys.readouterr().out)["answer"]["current_task_closeout"]["scope"]["route_decision"])

    decision_ids = {route["decision_id"] for route in routes}
    input_revisions = {route["input_revision"] for route in routes}
    owner_revisions = {route["action_identity"]["selected_owner_revision"] for route in routes}
    task_binding_ids = {route["action_identity"]["task_binding_identity"] for route in routes}
    admitted_actions = {route["next_safe_action"]["action"] for route in routes}
    route_identities = [(route["decision_id"], route["input_revision"], route["action_identity"]) for route in routes]
    assert routes[0]["action_identity"] == routes[1]["action_identity"]
    assert len(decision_ids) == len(input_revisions) == len(owner_revisions) == len(task_binding_ids) == 1, route_identities
    assert next(iter(owner_revisions))
    assert next(iter(task_binding_ids)).startswith("bounded-child:")
    assert admitted_actions == {"continue-active-plan"}
    assert all(route["structured_inputs"]["task_binding"]["parent_owner_ref"] == owner_ref for route in routes)
    for route in routes:
        invocation = route["next_safe_action"]["operation_invocation"]
        assert validate_planning_route_action_invocation(invocation=invocation, live_route_decision=route)["status"] == "admitted"


def test_startup_claim_effect_projection_preserves_canonical_route_identity_and_boundary() -> None:
    from agentic_workspace.operating_decision import project_startup_claim_effect_authority
    from agentic_workspace.workspace_runtime_core import _installed_state_drift_triage_payload
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    boundaries = (
        {
            "effect_class": "read-only-inspection",
            "installed_payload_dependency": "independent",
            "claim_classes": ["checked-in-source-evidence"],
        },
        {
            "effect_class": "read-only-inspection",
            "installed_payload_dependency": "dependent",
            "claim_classes": ["installed-payload-behavior"],
        },
        {
            "effect_class": "planned-repo-mutation",
            "installed_payload_dependency": "dependent",
            "claim_classes": ["installed-payload-freshness"],
        },
        {"effect_class": "repo-mutation", "installed_payload_dependency": "independent", "claim_classes": ["checked-in-source-evidence"]},
    )
    for boundary in boundaries:
        decision = _planning_route_decision_payload(
            {
                "task_relation": "bounded-independent",
                "owner_posture": "current",
                "route_inputs": {
                    "task_binding": {"mode": "read-only"},
                    "claim_effect_boundary": boundary,
                },
            },
            planning_revision={"revision_id": "planning-current"},
        )
        projection = project_startup_claim_effect_authority(route_decision=decision)
        triage = _installed_state_drift_triage_payload(
            installed_state={"status": "upgrade-recommended", "action_state": {"state": "manual_review_required"}},
            claim_effect_authority=projection,
            changed_paths=[],
            cli_invoke="agentic-workspace",
        )
        triage_projection = triage["claim_effect_authority"]

        assert decision["claim_effect_boundary"] == boundary
        assert decision["action_identity"]["claim_effect_boundary"] == boundary
        assert projection["decision_id"] == triage_projection["decision_id"] == decision["decision_id"]
        assert projection["input_revision"] == triage_projection["input_revision"] == decision["input_revision"]
        assert projection["action_identity"] == triage_projection["action_identity"] == decision["action_identity"]
        assert {key: projection[key] for key in boundary} == boundary
        assert {key: triage_projection[key] for key in boundary} == boundary
        assert projection["authority"] == triage_projection["authority"] == "planning_safety_gate.route_decision"


def test_route_decision_fails_closed_for_genuine_ambiguity() -> None:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    decision = _planning_route_decision_payload(
        {
            "status": "active",
            "implementation_allowed": True,
            "blocked_claims": ["claim-active-plan-progress", "silently-abandon-active-plan"],
            "next_action_packet": {"action": "choose-task-switch-route", "next_proof": "route decision evidence"},
        }
    )
    assert decision["required_transition"] == "ask-for-route-decision"
    assert decision["implementation_allowed"] is False
    assert decision["mutation_authority"] == "none"
    assert decision["blocked_claims"] == [
        "claim-active-plan-progress",
        "claim-active-plan-complete",
        "silently-abandon-active-plan",
    ]


def test_route_safety_projection_ignores_legacy_task_switch_status() -> None:
    from agentic_workspace.workspace_runtime_planning import _route_safety_outcome

    outcome = _route_safety_outcome(
        {
            # This legacy label intentionally conflicts with the canonical
            # route contract.  Gate consumers must use the latter.
            "legacy_status": "active",
            "task_relation": "bounded-independent",
            "owner_posture": "current",
            "required_transition": "none",
            "selected_owner_identity": {"ref": "current-task", "revision": "owner-a"},
            "state_update_policy": "no-active-plan-state-update",
            "next_safe_action": {"action": "prove-current-task"},
            "mutation_baseline_admission": {
                "status": "current",
                "source": "canonical-route-decision",
                "baseline_id": "baseline-a",
                "reason": "current live mutation baseline admitted into the canonical route decision",
            },
            "structured_inputs": {
                "task_binding": {"mode": "mutation", "allowed_paths": ["README.md"]},
                "mutation_baseline": {
                    "kind": "agentic-workspace/mutation-baseline/v1",
                    "status": "clean-scope",
                    "revalidation_status": "current",
                    "baseline_id": "baseline-a",
                    "head": "abc123",
                    "scope": {"allowed_paths": ["README.md"]},
                    "observation": {"ok": True},
                    "observed_state": {"enforcement_fingerprint": "fingerprint-a", "entry_count": 0},
                    "boundary_enforcement": {"status": "fail-closed-contract"},
                    "stale_revalidation": {"status": "required"},
                    "ownership": {"owner": "current-agent-session"},
                },
            },
        }
    )

    assert outcome["status"] == "satisfied"
    assert outcome["decision"] == "current-task-route-acknowledged"
    assert outcome["action_safety"]["effect_scope"] == ["README.md"]
    assert outcome["action_safety"]["mutation_baseline"]["baseline_id"] == "baseline-a"


def test_route_safety_projection_fails_closed_for_unbaselined_bounded_mutation() -> None:
    from agentic_workspace.workspace_runtime_planning import _route_safety_outcome

    outcome = _route_safety_outcome(
        {
            "task_relation": "bounded-independent",
            "owner_posture": "current",
            "required_transition": "none",
            "selected_owner_identity": {"ref": "current-task", "revision": "owner-a"},
            "state_update_policy": "no-active-plan-state-update",
            "next_safe_action": {"action": "prove-current-task"},
            "structured_inputs": {"task_binding": {"mode": "mutation", "allowed_paths": ["README.md"]}},
        }
    )

    assert outcome["status"] == "blocked"
    assert outcome["workflow_sufficient"] is False
    assert outcome["decision"] == "route-authority-inconsistent"
    assert outcome["required_next_action"] == "refresh-planning-route-decision"


def test_route_safety_projection_fails_closed_for_unsupported_transition() -> None:
    from agentic_workspace.workspace_runtime_planning import _route_safety_outcome

    outcome = _route_safety_outcome(
        {
            "task_relation": "continues-selected-owner",
            "owner_posture": "current",
            "required_transition": "reconcile",
            "selected_owner_identity": {"ref": "issue-1", "revision": "owner-a"},
            "state_update_policy": "fresh-reconciliation-proposal-required",
            "next_safe_action": {"action": "refresh-proposal"},
        }
    )

    assert outcome["status"] == "attention"
    assert outcome["decision"] == "route-transition-required"
    assert outcome["action_safety"]["repair_owner"] == "planning-route-decision"


def test_route_decision_uses_current_reconciliation_proposal_without_recompiling_it() -> None:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    decision = _planning_route_decision_payload(
        {"status": "issue-matched-continuation", "next_action_packet": {"action": "continue-active-plan"}},
        reconciliation_proposal={
            "status": "current",
            "proposal_id": "a" * 20,
            "apply_command": "agentic-workspace planning reconcile --apply --proposal " + "a" * 20,
        },
    )

    assert decision["required_transition"] == "reconcile"
    assert decision["mutation_authority"] == "reconciliation-proposal"
    assert decision["owner_posture"] == "reconciliation-pending"
    assert decision["reconciliation_proposal"]["proposal_id"] == "a" * 20
    assert decision["next_safe_action"]["command"].endswith("a" * 20)


def test_route_decision_preserves_proposal_transition_and_posture() -> None:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    decision = _planning_route_decision_payload(
        {"task_relation": "bounded-independent", "owner_posture": "current", "implementation_allowed": True},
        reconciliation_proposal={
            "status": "current",
            "freshness": "current",
            "proposal_id": "b" * 20,
            "apply_command": "agentic-workspace planning reconcile --apply --proposal " + "b" * 20,
            "required_transition": "repair-projection",
            "owner_posture": "projection-drifted",
        },
    )

    assert decision["task_relation"] == "bounded-independent"
    assert decision["owner_posture"] == "projection-drifted"
    assert decision["required_transition"] == "repair-projection"
    assert decision["reconciliation_proposal"]["freshness"] == "current"


def test_route_decision_requires_fresh_proposal_instead_of_applying_stale_one() -> None:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    decision = _planning_route_decision_payload(
        {"task_relation": "continues-selected-owner", "owner_posture": "current", "implementation_allowed": True},
        reconciliation_proposal={"status": "stale", "freshness": "stale", "proposal_id": "c" * 20},
    )

    assert decision["owner_posture"] == "reconciliation-stale"
    assert decision["required_transition"] == "reconcile"
    assert decision["implementation_allowed"] is False
    assert decision["mutation_authority"] == "none"


def test_planning_route_action_admission_rejects_stale_authority_inputs() -> None:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload, validate_planning_route_action_invocation

    route_evidence = {
        "task_relation": "bounded-independent",
        "owner_posture": "current",
        "active_execplan": ".agentic-workspace/planning/execplans/active.plan.json",
        "implementation_allowed": True,
        "route_inputs": {
            "task_binding": {"mode": "mutation", "identity": "task-a", "allowed_paths": ["README.md"]},
            "owner": {
                "ref": ".agentic-workspace/planning/execplans/active.plan.json",
                "revision": "owner-a",
                "lifecycle": "active",
                "projection_status": "clean",
            },
            "mutation_baseline": {
                "baseline_id": "baseline-a",
                "scope": {"allowed_paths": ["README.md"]},
                "allowed_effects": ["repo-mutation"],
                "overlap_claim": {"status": "scoped-to-requested-paths", "allowed_paths": ["README.md"]},
            },
            "reconciliation_proposal": {"status": "absent"},
        },
    }
    live = _planning_route_decision_payload(
        route_evidence,
        planning_revision={"revision_id": "planning-a"},
        reconciliation_proposal={"status": "current", "proposal_id": "proposal-a", "revision": "proposal-rev-a"},
    )
    invocation = live["next_safe_action"]["operation_invocation"]

    admitted = validate_planning_route_action_invocation(invocation=invocation, live_route_decision=live)
    assert admitted["status"] == "admitted"
    assert invocation["operation_path"] == "packages/planning/src/repo_planning_bootstrap/contracts/operations/planning.front-door.json"
    identity = invocation["input_identity"]
    assert identity["selected_owner_lifecycle"] == "active"
    assert identity["selected_owner_projection_status"] == "clean"
    assert identity["task_binding_mode"] == "mutation"
    assert identity["implementation_allowed"] is False
    assert identity["mutation_authority"] == "reconciliation-proposal"
    assert identity["state_update_policy"] == "reconciliation-apply-required"
    assert identity["allowed_claims"] == []
    assert identity["blocked_claims"] == [
        "claim-active-plan-progress",
        "claim-active-plan-complete",
        "silently-abandon-active-plan",
        "claim-route-transition-complete-without-receipt",
    ]
    assert identity["allowed_claims"] == live["allowed_claims"]
    assert identity["blocked_claims"] == live["blocked_claims"]
    assert identity["mutation_allowed_paths_digest"]
    assert identity["allowed_effects_digest"]
    assert identity["overlap_claim_digest"]

    for field, route_patch, proposal_patch in [
        ("selected_owner_revision", {"route_inputs": {"owner": {"revision": "owner-b"}}}, {}),
        ("selected_owner_lifecycle", {"route_inputs": {"owner": {"lifecycle": "archived"}}}, {}),
        ("selected_owner_projection_status", {"route_inputs": {"owner": {"projection_status": "drifted"}}}, {}),
        ("task_binding_identity", {"route_inputs": {"task_binding": {"identity": "task-b"}}}, {}),
        ("task_binding_mode", {"route_inputs": {"task_binding": {"mode": "read-only"}}}, {}),
        ("mutation_baseline_id", {"route_inputs": {"mutation_baseline": {"baseline_id": "baseline-b"}}}, {}),
        ("mutation_allowed_paths_digest", {"route_inputs": {"task_binding": {"allowed_paths": ["src/app.py"]}}}, {}),
        ("allowed_effects_digest", {"route_inputs": {"mutation_baseline": {"allowed_effects": ["planning-transition"]}}}, {}),
        ("overlap_claim_digest", {"route_inputs": {"mutation_baseline": {"overlap_claim": {"status": "overlap-drift"}}}}, {}),
        ("reconciliation_proposal_revision", {}, {"revision": "proposal-rev-b"}),
    ]:
        changed = json.loads(json.dumps(route_evidence))
        for group, values in route_patch.get("route_inputs", {}).items():
            changed["route_inputs"][group].update(values)
        stale_live = _planning_route_decision_payload(
            changed,
            planning_revision={"revision_id": "planning-a"},
            reconciliation_proposal={"status": "current", "proposal_id": "proposal-a", "revision": "proposal-rev-a", **proposal_patch},
        )

        rejected = validate_planning_route_action_invocation(invocation=invocation, live_route_decision=stale_live)

        assert rejected["status"] == "rejected"
        assert field in rejected["changed_authority_fields"]
        assert rejected["rejection"]["status"] == "reject-on-input-revision-mismatch"


def test_planning_route_front_door_admits_finite_route_action_matrix() -> None:
    from agentic_workspace.workspace_runtime_planning import (
        _planning_front_door_projection_outcome,
        _planning_route_decision_payload,
        validate_planning_route_action_invocation,
    )

    cases = [
        (
            "continuation",
            {"task_relation": "continues-selected-owner", "owner_posture": "current"},
            {},
            "continue-active-plan",
            "no-op",
        ),
        (
            "bounded-read-only",
            {"task_relation": "bounded-independent", "owner_posture": "current", "route_inputs": {"task_binding": {"mode": "read-only"}}},
            {},
            "prove-current-task",
            "no-op",
        ),
        (
            "bounded-mutation-baseline",
            {"task_relation": "bounded-independent", "owner_posture": "current", "route_inputs": {"task_binding": {"mode": "mutation"}}},
            {},
            "refresh-mutation-baseline",
            "host-action-required",
        ),
        (
            "completed-residue",
            {"task_relation": "bounded-independent", "owner_posture": "completed-residue"},
            {},
            "archive-or-retire-completed-plan",
            "host-action-required",
        ),
        (
            "external-conflict",
            {"task_relation": "continues-selected-owner", "owner_posture": "external-conflict"},
            {},
            "refresh-planning-reconciliation-proposal",
            "host-action-required",
        ),
        (
            "projection-drift",
            {"task_relation": "continues-selected-owner", "owner_posture": "projection-drifted"},
            {},
            "repair-planning-projection",
            "host-action-required",
        ),
        (
            "proof-incomplete",
            {"task_relation": "continues-selected-owner", "owner_posture": "proof-incomplete"},
            {},
            "complete-selected-proof",
            "host-action-required",
        ),
        (
            "promotion",
            {"task_relation": "owner-promotion-required", "owner_posture": "missing"},
            {},
            "promote-or-create-planning-owner",
            "host-action-required",
        ),
        (
            "missing-owner",
            {"task_relation": "continues-selected-owner", "owner_posture": "missing"},
            {},
            "select-planning-owner",
            "host-action-required",
        ),
        (
            "ambiguous",
            {"task_relation": "ambiguous", "owner_posture": "current"},
            {},
            "choose-task-switch-route",
            "blocked",
        ),
        (
            "current-proposal",
            {"task_relation": "continues-selected-owner", "owner_posture": "external-conflict"},
            {"status": "current", "proposal_id": "proposal-a", "revision": "proposal-rev-a"},
            "apply-planning-reconciliation-proposal",
            "applied-by-specialized-transaction",
        ),
    ]

    for name, evidence, proposal, route_action, mutation_outcome in cases:
        decision = _planning_route_decision_payload(
            {"implementation_allowed": True, "route_inputs": {"owner": {"ref": f"owner-{name}", "revision": "owner-a"}}, **evidence},
            planning_revision={"revision_id": "planning-a"},
            reconciliation_proposal=proposal,
        )
        invocation = decision["next_safe_action"]["operation_invocation"]

        admitted = validate_planning_route_action_invocation(invocation=invocation, live_route_decision=decision)

        assert admitted["status"] == "admitted", name
        assert invocation["operation_id"] == "planning.front-door"
        assert invocation["input_identity"]["route_action"] == route_action
        if route_action != "apply-planning-reconciliation-proposal":
            outcome = _planning_front_door_projection_outcome(
                route_action,
                invocation["input_identity"],
                target_root=Path(".").resolve(),
                task_text=f"exercise {name}",
                changed_paths=["src/example.py"],
            )
            assert outcome["mutation_outcome"] == mutation_outcome
            assert outcome["route_transition"]["route_action"] == route_action
            assert outcome["route_transition"]["status"] != "unsupported-route-action"
            if mutation_outcome == "host-action-required":
                host_invocation = outcome["host_action_invocation"]
                assert host_invocation["status"] == "ready"
                assert host_invocation["operation_id"]
                assert host_invocation["idempotency_key"] == invocation["input_identity"]["idempotency_key"]
                assert host_invocation["operation_contract_revision"].startswith("sha256:")
                assert host_invocation["operation_schema_version"] == "agentic-workspace/operation/v1"
                assert "command" not in host_invocation
                assert outcome["route_transition"]["dispatch_status"] == "ready"


def test_planning_front_door_executes_and_admits_only_destination_issued_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_planning as planning_runtime

    operation_path = "src/agentic_workspace/contracts/operations/proof.report.json"
    destination = {
        "schema_version": "agentic-workspace/operation/v1",
        "id": "proof.report",
        "command_surface": {"command": "proof", "format_option": "format"},
    }
    destination_path = tmp_path / operation_path
    destination_path.parent.mkdir(parents=True)
    destination_path.write_text(json.dumps(destination), encoding="utf-8")
    adapter = tmp_path / "configured_operation_adapter.py"
    adapter.write_text(
        "import json, sys\nprint(json.dumps({'status': 'passed', 'argv': sys.argv[1:]}))\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("agentic_workspace.client.resolve_invocation", lambda _target: [sys.executable, str(adapter)])
    monkeypatch.setattr(
        planning_runtime,
        "_planning_revision_payload",
        lambda *, target_root: {"revision_id": "planning-before"},
    )
    identity = {
        "route_action": "complete-selected-proof",
        "front_door_operation_id": "planning.front-door",
        "front_door_contract_revision": "sha256:front-door",
        "operation_id": "proof.report",
        "operation_path": operation_path,
        "operation_contract_revision": "sha256:" + planning_runtime._stable_revision(destination),
        "operation_schema_version": "agentic-workspace/operation/v1",
        "arguments": {"target": tmp_path.as_posix(), "changed": ["src/example.py"], "format": "json"},
        "route_input_revision": "sha256:route-input",
        "planning_revision": "planning-before",
        "selected_owner_revision": "owner-before",
        "idempotency_key": "route-once",
        "result_admission": {
            "kind": "agentic-planning/front-door-host-action-result/v1",
            "accepted_statuses": ["passed", "already-passed", "no-op"],
        },
    }
    invocation = {
        "kind": "agentic-planning/front-door-host-action-invocation/v1",
        "status": "ready",
        **identity,
        "invocation_revision": "sha256:" + planning_runtime._stable_revision(identity),
    }

    execute_host_action = planning_runtime._execute_planning_front_door_host_action
    executed = execute_host_action(invocation=invocation)
    admitted = planning_runtime.admit_planning_front_door_host_action_result(invocation=invocation, result=executed)

    assert admitted["status"] == "admitted"
    assert admitted["receipt"]["producer"] == "agentic-workspace.configured-operation-executor"
    assert admitted["receipt"]["postcondition_status"] == "verified"
    assert executed.payload["result"]["argv"] == [
        "proof",
        "--target",
        tmp_path.as_posix(),
        "--changed",
        "src/example.py",
        "--format",
        "json",
    ]
    forged_mapping = copy.deepcopy(executed.payload)
    assert planning_runtime.admit_planning_front_door_host_action_result(invocation=invocation, result=forged_mapping)["failures"] == [
        "producer-owned-result"
    ]

    def reseal(payload: dict[str, Any]) -> object:
        receipt = payload["receipt"]
        receipt["receipt_id"] = "sha256:" + planning_runtime._stable_revision(
            {key: value for key, value in receipt.items() if key not in {"kind", "receipt_id"}}
        )
        return planning_runtime._ExecutedPlanningHostActionResult(payload=payload, seal=executed.seal)

    for field, value in [
        ("producer", "caller"),
        ("executor_revision", "sha256:stale-runtime"),
        ("idempotency_key", "replayed-key"),
        ("postcondition_status", "failed"),
    ]:
        tampered = copy.deepcopy(executed.payload)
        tampered["receipt"][field] = value
        assert (
            planning_runtime.admit_planning_front_door_host_action_result(invocation=invocation, result=reseal(tampered))["status"]
            == "rejected"
        )

    decision = planning_runtime._planning_route_decision_payload(
        {
            "task_relation": "continues-selected-owner",
            "owner_posture": "proof-incomplete",
            "implementation_allowed": False,
            "route_inputs": {"owner": {"ref": "owner-a", "revision": "owner-before"}},
        },
        planning_revision={"revision_id": "planning-before"},
    )
    route_invocation = decision["next_safe_action"]["operation_invocation"]
    monkeypatch.setattr(planning_runtime, "_planning_safety_gate_payload", lambda **_kwargs: {"route_decision": decision})
    monkeypatch.setattr(
        planning_runtime,
        "_planning_front_door_projection_outcome",
        lambda *_args, **_kwargs: {
            "mutation_outcome": "host-action-required",
            "claim_outcome": "blocked",
            "host_action_invocation": invocation,
            "route_transition": {"status": "complete-selected-proof", "dispatch_status": "ready"},
        },
    )
    execution_count = 0

    def execute_bound_destination(*, invocation: dict[str, Any]) -> object:
        nonlocal execution_count
        execution_count += 1
        return executed

    monkeypatch.setattr(planning_runtime, "_execute_planning_front_door_host_action", execute_bound_destination)
    routed = planning_runtime.execute_planning_front_door_route_action(
        {
            "target": tmp_path.as_posix(),
            "task": "complete selected proof",
            "changed_paths": ["src/example.py"],
            "operation_invocation": route_invocation,
            "host_action_result": forged_mapping,
        }
    )
    assert execution_count == 1
    assert routed["claim_outcome"] == "available-after-proof"
    assert routed["mutation_receipt"]["producer"] == "agentic-workspace.configured-operation-executor"

    destination_path.write_text(json.dumps({**destination, "summary": "changed"}), encoding="utf-8")
    stale = execute_host_action(invocation=invocation)
    assert stale.payload["reason"] == "destination-operation-contract-stale"
    assert planning_runtime.admit_planning_front_door_host_action_result(invocation=invocation, result=stale)["status"] == "rejected"


def test_structured_route_inputs_cover_bounded_work_owner_lifecycle_and_missing_owner(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_planning import _structured_route_inputs

    active = {
        "active_execplan": ".agentic-workspace/planning/execplans/issue-2046-lane.plan.json",
        "active_item_id": "issue-2046-lane",
    }
    read_only = _structured_route_inputs(
        target_root=tmp_path,
        active_summary=active,
        task_text="Report a bounded result",
        changed_paths=[],
        route_evidence={"current_task_class": "bounded-reflection-reporting"},
        planning_revision={"status": "clean"},
        proposal={"status": "absent"},
    )
    mutation = _structured_route_inputs(
        target_root=tmp_path,
        active_summary=active,
        task_text="Fix a bounded defect",
        changed_paths=["src/example.py"],
        route_evidence={"status": "current-task-route-acknowledged", "current_task_class": "current-task"},
        planning_revision={"status": "clean"},
        proposal={"status": "absent"},
    )
    missing = _structured_route_inputs(
        target_root=tmp_path,
        active_summary={},
        task_text="Implement a bounded task",
        changed_paths=["src/example.py"],
        route_evidence={},
        planning_revision={"status": "clean"},
        proposal={"status": "absent"},
    )

    assert (read_only["task_relation"], read_only["owner_posture"]) == ("bounded-independent", "current")
    assert mutation["route_inputs"]["task_binding"]["mutation_scope_acknowledged"] is True
    assert mutation["route_inputs"]["mutation_baseline"]["source"] == "authority-envelope-live-observation"
    assert mutation["route_inputs"]["mutation_baseline"]["kind"] == "agentic-workspace/mutation-baseline/v1"
    assert mutation["route_inputs"]["mutation_baseline"].get("baseline_id") != "planning-revision-a"
    assert (missing["task_relation"], missing["owner_posture"]) == ("not-applicable", "not-applicable")


def test_route_decision_transition_matrix_is_compositional() -> None:
    from agentic_workspace.workspace_runtime_planning import _planning_route_decision_payload

    cases = [
        ("continuation", {"task_relation": "continues-selected-owner", "owner_posture": "current"}, {}, "none", "current"),
        (
            "bounded-read-only",
            {"task_relation": "bounded-independent", "owner_posture": "current", "route_inputs": {"task_binding": {"mode": "read-only"}}},
            {},
            "none",
            "current",
        ),
        (
            "bounded-mutation",
            {"task_relation": "bounded-independent", "owner_posture": "current", "route_inputs": {"task_binding": {"mode": "mutation"}}},
            {},
            "refresh-mutation-baseline",
            "current",
        ),
        (
            "completed-residue",
            {"task_relation": "bounded-independent", "owner_posture": "completed-residue"},
            {},
            "closeout-or-archive",
            "completed-residue",
        ),
        (
            "external-conflict",
            {"task_relation": "continues-selected-owner", "owner_posture": "external-conflict"},
            {},
            "reconcile",
            "external-conflict",
        ),
        (
            "projection-drift",
            {"task_relation": "continues-selected-owner", "owner_posture": "projection-drifted"},
            {},
            "repair-projection",
            "projection-drifted",
        ),
        ("promotion", {"task_relation": "owner-promotion-required", "owner_posture": "missing"}, {}, "promote-or-create-owner", "missing"),
        ("ambiguity", {"task_relation": "ambiguous", "owner_posture": "current"}, {}, "ask-for-route-decision", "current"),
    ]

    for _name, evidence, proposal, transition, posture in cases:
        decision = _planning_route_decision_payload({"implementation_allowed": True, **evidence}, reconciliation_proposal=proposal)
        assert (decision["required_transition"], decision["owner_posture"]) == (transition, posture)

    read_only = _planning_route_decision_payload(
        {
            "implementation_allowed": True,
            "task_relation": "bounded-independent",
            "owner_posture": "current",
            "route_inputs": {"task_binding": {"mode": "read-only"}},
        }
    )
    mutation = _planning_route_decision_payload(
        {
            "implementation_allowed": True,
            "task_relation": "bounded-independent",
            "owner_posture": "current",
            "route_inputs": {"task_binding": {"mode": "mutation"}},
        }
    )
    mutation_current = _planning_route_decision_payload(
        {
            "implementation_allowed": True,
            "task_relation": "bounded-independent",
            "owner_posture": "current",
            "route_inputs": {
                "task_binding": {"mode": "mutation", "allowed_paths": ["README.md"]},
                "mutation_baseline": {
                    "kind": "agentic-workspace/mutation-baseline/v1",
                    "status": "clean-scope",
                    "revalidation_status": "current",
                    "baseline_id": "baseline-a",
                    "head": "abc123",
                    "scope": {"allowed_paths": ["README.md"]},
                    "observation": {"ok": True},
                    "observed_state": {"enforcement_fingerprint": "fingerprint-a"},
                    "boundary_enforcement": {"status": "fail-closed-contract"},
                    "stale_revalidation": {"status": "required"},
                    "ownership": {"owner": "current-agent-session"},
                },
            },
        }
    )
    assert read_only["mutation_authority"] == "none"
    assert mutation["mutation_authority"] == "none"
    assert mutation_current["mutation_authority"] == "current-task"


def test_selector_first_gate_projects_authoritative_route_decision() -> None:
    from agentic_workspace.workspace_runtime_primitives import _selector_first_planning_safety_gate

    selected = _selector_first_planning_safety_gate(
        {
            "kind": "agentic-workspace/planning-safety-gate/v1",
            "status": "satisfied",
            "workflow_sufficient": True,
            "route_decision": {
                "kind": "agentic-planning/route-decision/v1",
                "task_relation": "bounded-independent",
                "owner_posture": "current",
                "required_transition": "none",
                "allowed_claims": ["bounded-task-progress"],
                "blocked_claims": ["active-plan-progress"],
                "mutation_authority": "current-task",
                "reconciliation_proposal": {"status": "current", "proposal_id": "a" * 20},
                "proof_expectation": "focused proof",
                "state_update_policy": "read-only",
                "next_safe_action": {"action": "perform-bounded-task"},
            },
        }
    )
    assert selected["route_decision"] == {
        "kind": "agentic-planning/route-decision/v1",
        "task_relation": "bounded-independent",
        "owner_posture": "current",
        "required_transition": "none",
        "allowed_claims": ["bounded-task-progress"],
        "blocked_claims": ["active-plan-progress"],
        "mutation_authority": "current-task",
        "reconciliation_proposal": {"status": "current", "proposal_id": "a" * 20},
        "proof_expectation": "focused proof",
        "state_update_policy": "read-only",
        "next_safe_action": {"action": "perform-bounded-task"},
    }


def test_startup_route_binding_is_provisional_before_identity_transition(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_startup import _startup_route_binding

    _init_git_repo(tmp_path)
    binding_args = {"target_root": tmp_path, "task_text": "Continue #2281", "cli_invoke": "agentic-workspace"}

    assert (
        _startup_route_binding(
            route_decision={"required_transition": "none", "next_safe_action": {"action": "continue-active-plan"}}, **binding_args
        )["status"]
        == "bound"
    )
    binding = _startup_route_binding(route_decision={"required_transition": "none", "identity_effects": ["branch"]}, **binding_args)
    assert binding["status"] == "provisional"
    assert binding["state_commit"] == "none"
    assert binding["reason"] == "structured-identity-transition"
    assert binding["adoption_guard"]["status"] == "required"
    assert binding["adoption_guard"]["expected_fingerprint"] == binding["identity"]["fingerprint"]
    assert (
        _startup_route_binding(
            route_decision={"required_transition": "none", "next_safe_action": {"command": "git switch feature/reconcile"}}, **binding_args
        )["status"]
        == "bound"
    )


def test_startup_route_identity_rejects_head_change_before_adoption(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import current_work_context

    _init_git_repo(tmp_path)
    head = {"value": "a" * 40}

    def fake_git(_root: Path, *args: str) -> str:
        return "main" if args == ("branch", "--show-current") else head["value"] if args == ("rev-parse", "HEAD") else ""

    monkeypatch.setattr(current_work_context, "_git", fake_git)
    expected = current_work_context.startup_route_identity(root=tmp_path, task="Continue #2281")
    head["value"] = "b" * 40

    check = current_work_context.startup_route_identity_check(expected=expected, root=tmp_path, task="Continue #2281")

    assert check["status"] == "stale-projection-rejected"
    assert check["action"] == "re-resolve-route"
    assert check["changed_fields"] == ["head"]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("branch", "feature/other"),
        ("worktree", "../other-worktree"),
        ("repository", "/repositories/other.git"),
        ("target", "/targets/other"),
        ("current_work", "other-current-work"),
        ("selected_owner", {"id": "other-owner", "ref": "plans/other.json"}),
    ],
)
def test_startup_route_identity_transition_matrix_rejects_and_leaves_no_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, replacement: object
) -> None:
    from agentic_workspace import current_work_context

    observed = {
        "target": "/targets/current",
        "repository": "/repositories/current.git",
        "worktree": ".",
        "branch": "main",
        "head": "a" * 40,
        "current_work": "current-work",
        "selected_owner": {"id": "owner", "ref": "plans/owner.json"},
    }
    expected = {
        "kind": "agentic-workspace/startup-route-identity/v1",
        "fingerprint": "expected",
        "observed": observed,
    }
    changed = {**observed, field: replacement}
    monkeypatch.setattr(
        current_work_context,
        "startup_route_identity",
        lambda **_kwargs: {
            "kind": "agentic-workspace/startup-route-identity/v1",
            "fingerprint": "actual",
            "observed": changed,
            "comparison_fields": list(observed),
        },
    )
    before = list(tmp_path.rglob("*"))

    check = current_work_context.startup_route_identity_check(expected=expected, root=tmp_path, task="continue")

    assert check["status"] == "stale-projection-rejected"
    assert check["changed_fields"] == [field]
    assert check["action"] == "re-resolve-route"
    assert list(tmp_path.rglob("*")) == before


def test_ordinary_planning_consumers_project_one_route_authority_without_orientation_residue(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    planning_anchor = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "README.md"
    anchor_before = planning_anchor.read_bytes()
    task = "Inspect the current Planning route"
    commands = [
        ["start", "--select", "planning_route_decision"],
        ["implement", "--select", "planning_route_decision"],
        ["summary", "--select", "planning_route_decision"],
        ["skills", "--select", "planning_route_decision"],
    ]
    routes = []
    for command in commands:
        assert cli.main([*command, "--target", str(tmp_path), "--task", task, "--format", "json"]) == 0
        selected = json.loads(capsys.readouterr().out)
        routes.append(selected["values"]["planning_route_decision"])

    authoritative = [
        (
            route["task_relation"],
            route["owner_posture"],
            route["required_transition"],
            route["implementation_allowed"],
            route["mutation_authority"],
            route["next_safe_action"]["action"],
        )
        for route in routes
    ]
    assert authoritative[0] == authoritative[1] == authoritative[2] == authoritative[3]
    assert len({route["decision_id"] for route in routes}) == 1
    assert len({route["input_revision"] for route in routes}) == 1
    assert len({json.dumps(route["action_identity"], sort_keys=True) for route in routes}) == 1
    expanded_routes = [route for route in routes if "consumer_contract" in route]
    assert expanded_routes
    assert all(route["consumer_contract"]["authority"] == "planning_safety_gate.route_decision" for route in expanded_routes)
    for route in routes:
        assert set(route["consumer_projections"]) == set(route["consumer_contract"]["ordinary_consumers"])
        assert {
            (
                projection["decision_id"],
                projection["input_revision"],
                json.dumps(projection["action_identity"], sort_keys=True),
                projection["required_transition"],
                tuple(projection["blocked_claims"]),
            )
            for projection in route["consumer_projections"].values()
        } == {
            (
                route["decision_id"],
                route["input_revision"],
                json.dumps(route["action_identity"], sort_keys=True),
                route["required_transition"],
                tuple(route["blocked_claims"]),
            )
        }
    assert planning_anchor.read_bytes() == anchor_before
    assert not (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    assert not (tmp_path / ".agentic-workspace" / "local" / "planning-carry.json").exists()


def test_planning_route_consumer_inventory_and_degraded_capsule_are_closed_and_current() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    inventory = json.loads((repo_root / "docs/maintainer/planning-route-consumer-inventory.json").read_text(encoding="utf-8"))
    required = {
        "startup",
        "implement",
        "preflight",
        "summary",
        "actionability",
        "skills",
        "SkillSpec",
        "Planning handoff",
        "proof",
        "closeout",
        "generated targets",
        "external consumers",
        "no-CLI fallback",
    }
    assert set(inventory["consumers"]) == required
    assert all(entry["projection"] != "independent" for entry in inventory["consumers"].values())
    assert inventory["compatibility_removal"]

    policy_path = repo_root / "src/agentic_workspace/_payload/.agentic-workspace/fallback/no-cli-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    expected = policy.pop("contract_digest")
    actual = "sha256:" + hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert expected == actual
    assert policy["authority"]["decision_source"] == inventory["authority"]
    assert {"managed-state-mutation", "external-write", "destructive-action"}.issubset(policy["forbidden_effects"])
    assert {"proof-complete", "issue-closeable", "task-complete"}.issubset(policy["forbidden_claims"])
    assert policy["restoration"]["action"] == "restore-configured-cli-and-rerun-start"

    workflow = (repo_root / ".agentic-workspace/WORKFLOW.md").read_text(encoding="utf-8")
    installed_workflow = (repo_root / "src/agentic_workspace/_payload/.agentic-workspace/WORKFLOW.md").read_text(encoding="utf-8")
    assert workflow == installed_workflow
    assert len(workflow.encode()) < 4_000
    assert "python .agentic-workspace/fallback/no_cli_startup.py" in workflow
    assert "Fallback Work Shape" not in workflow
    assert "do not reconstruct work shape" in workflow

    startup_skill = (repo_root / ".agentic-workspace/skills/workspace-startup/SKILL.md").read_text(encoding="utf-8")
    installed_startup_skill = (repo_root / "src/agentic_workspace/_payload/.agentic-workspace/skills/workspace-startup/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert startup_skill == installed_startup_skill
    assert "planning_route_decision" in startup_skill
    assert "Do not reclassify the task" in startup_skill


def test_startup_profiles_and_skill_projection_share_current_planning_route(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "issue-2275", title = "Planning route parity", status = "active", surface = ".agentic-workspace/planning/execplans/issue-2275.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "issue-2275.plan.json",
        json.dumps({"id": "issue-2275", "title": "Planning route parity", "refs": ["#2275"]}),
    )
    task = "Continue #2275"
    invocations = [
        ["start"],
        ["start", "--verbose"],
        ["start", "--select", "planning_safety_gate"],
        ["start", "--select", "planning_route_decision"],
        ["skills", "--select", "planning_route_decision"],
    ]
    routes = []
    for invocation in invocations:
        assert cli.main([*invocation, "--target", str(tmp_path), "--task", task, "--format", "json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        if invocation[-1] == "planning_route_decision":
            route = payload["values"]["planning_route_decision"]
        elif invocation[-1] == "planning_safety_gate":
            route = payload["values"]["planning_safety_gate"]["route_decision"]
        else:
            route = payload.get("route_decision")
            if not route:
                owner = payload.get("decision_packet", {}).get("owner", {})
                route = {
                    "task_relation": owner.get("task_relation"),
                    "owner_posture": owner.get("owner_posture"),
                    "required_transition": owner.get("required_transition"),
                }
            assert route
        routes.append(route)

    dimensions = [(route["task_relation"], route["owner_posture"], route["required_transition"]) for route in routes]
    assert len(set(dimensions)) == 1
    assert dimensions[0] == ("continues-selected-owner", "current", "none")
    expanded_routes = [route for route in routes if "consumer_contract" in route]
    assert expanded_routes
    assert all(route["consumer_contract"]["authority"] == "planning_safety_gate.route_decision" for route in expanded_routes)


def test_decision_point_carry_rejects_stale_startup_route_before_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import current_work_context
    from agentic_workspace.workspace_runtime_core import _persist_decision_point_forecast

    _init_git_repo(tmp_path)
    head = {"value": "a" * 40}

    def fake_git(_root: Path, *args: str) -> str:
        return "main" if args == ("branch", "--show-current") else head["value"] if args == ("rev-parse", "HEAD") else ""

    monkeypatch.setattr(current_work_context, "_git", fake_git)
    expected = current_work_context.startup_route_identity(root=tmp_path, task="Continue #2281")
    head["value"] = "b" * 40

    result = _persist_decision_point_forecast(
        target_root=tmp_path,
        task_text="Continue #2281",
        expected_route_identity=expected,
        forecast={"forecast_identity": {"system_principle_ids": ["workspace-runtime"], "authoritative_sources": []}},
    )

    assert result["status"] == "not-created"
    assert result["reason_code"] == "stale-startup-route-identity"
    assert result["route_identity_check"]["changed_fields"] == ["head"]
    assert not (tmp_path / ".agentic-workspace/local/decision-point-intent").exists()


def test_implement_rejects_stale_startup_fingerprint_before_any_state_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace import current_work_context

    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    _write_cli_architecture_principles(tmp_path)
    _write_decision_point_subsystem_intent(tmp_path)
    changed_path = "src/agentic_workspace/workspace_runtime_implement.py"
    _write(tmp_path / changed_path, "VALUE = 1\n")
    head = {"value": "a" * 40}

    def fake_git(_root: Path, *args: str) -> str:
        return "main" if args == ("branch", "--show-current") else head["value"] if args == ("rev-parse", "HEAD") else ""

    monkeypatch.setattr(current_work_context, "_git", fake_git)
    task = f"Update {changed_path}"
    assert cli.main(["start", "--target", str(tmp_path), "--task", task, "--select", "planning_safety_gate", "--format", "json"]) == 0
    startup = json.loads(capsys.readouterr().out)
    fingerprint = startup["values"]["planning_safety_gate"]["route_decision"]["binding"]["identity"]["fingerprint"]
    head["value"] = "b" * 40

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                changed_path,
                "--task",
                task,
                "--startup-route-fingerprint",
                fingerprint,
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    rebind = payload["startup_route_rebind"]
    assert rebind["status"] == "stale-projection-rejected"
    assert rebind["route_identity_check"]["actual"]["observed"]["head"] == "b" * 40
    assert rebind["authoritative_route"]["kind"] == "agentic-planning/route-decision/v1"
    assert "Rerun start" in rebind["safe_recovery"]
    assert "Rerun start" in payload["next_allowed_action"]
    assert not (tmp_path / ".agentic-workspace/local/decision-point-intent").exists()


def test_compact_start_route_decision_preserves_contract_and_binding() -> None:
    from agentic_workspace.workspace_runtime_startup import _compact_start_route_decision

    route = _compact_start_route_decision(
        {
            "kind": "agentic-planning/route-decision/v1",
            "task_relation": "bounded-independent",
            "owner_posture": "current",
            "required_transition": "none",
            "allowed_claims": ["bounded-task-progress"],
            "blocked_claims": ["active-plan-progress"],
            "mutation_authority": "current-task",
            "reconciliation_proposal": {"status": "current", "proposal_id": "a" * 20},
            "proof_expectation": "focused proof",
            "state_update_policy": "read-only",
            "next_safe_action": {"action": "perform-bounded-task"},
            "binding": {"status": "bound", "state_commit": "none"},
        }
    )
    assert route["task_relation"] == "bounded-independent"
    assert route["mutation_authority"] == "current-task"
    assert route["reconciliation_proposal"]["proposal_id"] == "a" * 20
    assert route["next_safe_action"] == {"action": "perform-bounded-task"}
    assert route["binding"] == {"status": "bound", "state_commit": "none"}


def test_start_low_risk_docs_task_keeps_checkpoint_detail_selector_only(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #1700 checkpoint slice",
                "--issue",
                "#1700",
                "--durable-source",
                "docs/reference/local-chat-checkpoints.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 10_000, label="start tiny docs-task payload with checkpoint", sort_keys=False)
    assert "local_chat_checkpoint" not in payload
    assert "local_chat_checkpoint=present" not in {item["signal"] for item in payload["decision_packet"].get("attention", [])}
    _assert_selector_inventory_omitted_from_compact_start(payload)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Resume checkpoint slice",
                "--select",
                "local_chat_checkpoint",
                "--format",
                "json",
            ]
        )
        == 0
    )
    resume_payload = json.loads(capsys.readouterr().out)["values"]
    assert resume_payload["local_chat_checkpoint"]["status"] == "present"


def test_selector_first_output_policy_note_documents_visibility_tiers() -> None:
    note = Path("docs/reviews/selector-first-output-policy-2026-06-28.md").read_text(encoding="utf-8")
    assert "Always First Packet" in note
    assert "Selector-Only by Default" in note
    assert "Escalates Into First Packet" in note
    assert "local_chat_checkpoint" in note
    assert "dogfooding_signal_status" in note
    assert "pr_comment_attention" in note


def test_start_keeps_planned_and_release_closeout_signals_visible(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue planned lane in stacked PR sequence",
                "--select",
                "dogfooding_signal_status,closeout_obligations,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    planned = json.loads(capsys.readouterr().out)["values"]
    assert planned["dogfooding_signal_status"]["status"] == "not_checked"
    ordinary_route = planned["closeout_obligations"]["ordinary_closeout_route"]
    assert ordinary_route["status"] == "mandatory-before-completion-claim"
    assert "--section closeout_trust" in ordinary_route["first_inspection"]
    assert "--section closeout_report" in ordinary_route["substitute_command"]
    assert ordinary_route["top_level_closeout_command"] == "not-available"

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Diagnose release recovery after failed semver release",
                "--select",
                "dogfooding_signal_status,closeout_obligations,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    release = json.loads(capsys.readouterr().out)["values"]
    assert release["dogfooding_signal_status"]["status"] == "not_checked"
    release_route = release["closeout_obligations"]["ordinary_closeout_route"]
    assert release_route["status"] == "mandatory-before-completion-claim"
    assert release_route["top_level_closeout_command"] == "not-available"


def test_start_surfaces_unresolved_dogfooding_signal_outcome(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "dogfooding-signal-status.json"
    cache_path.write_text(
        json.dumps({"status": "unresolved", "signals": ["diagnostic did not change routing"]}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue planned lane in stacked PR sequence",
                "--select",
                "dogfooding_signal_status",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    status = payload["dogfooding_signal_status"]
    assert status["status"] == "unresolved"
    assert status["closeout_blocked"] is True
    assert status["durable_residue"] is True


def test_start_compiles_session_improvement_pressure_into_task_posture(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "dogfooding-signal-status.json"
    cache_path.write_text(
        json.dumps({"status": "unresolved", "signals": ["improvement diagnostics did not change next action"]}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue planned lane in stacked PR sequence",
                "--select",
                "task_posture_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    packet = payload["values"]["task_posture_packet"]

    assert packet["improvement_pressure_evaluation"]["status"] == "active"
    assert packet["improvement_pressure_evaluation"]["source_intake"] == "session_improvement_intake"
    assert packet["improvement_pressure_evaluation"]["active_obligation_count"] == 1
    consequence = packet["improvement_pressure_evaluation"]["primary_consequence"]
    assert consequence["consequence"] == "create-task-posture-obligation"
    assert consequence["claim_effect"] == "blocks"
    assert consequence["next_allowed_action"] == "route active improvement pressure or record accepted-risk"
    assert packet["improvement_obligations"][0]["source"] == "improvement-pressure"
    assert packet["improvement_pressure_records"][0]["state"] == "active"
    assert packet["improvement_pressure_records"][0]["scope_relation"] == "current-scope"
    assert packet["next_allowed_action"] == "route active improvement pressure or record accepted-risk"
    assert "claim improvement pressure resolved without owner, dismissal, or accepted-risk state" in packet["forbidden_actions"]


def test_start_operational_effectiveness_matrix_covers_2046_lane_signals(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workspace]
optimization_bias = "agent-efficiency"

[workflow_obligations.dogfood_closeout]
summary = "Classify dogfooding pressure before closeout."
stage = "before-claiming-completion"
force = "required-before-closeout"
scope_tags = ["dogfooding", "self-improvement", "planning"]
commands = ["agentic-workspace report --section dogfooding_signal_status --format json"]
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement the whole #2046 dogfooding self-improvement lane",
                "--select",
                "task_posture_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["task_posture_packet"]
    effectiveness = packet["operational_effectiveness"]
    by_signal = {record["signal"]: record for record in effectiveness["records"]}

    assert effectiveness["summary"]["behavior_changing_count"] >= 3
    assert by_signal["session_dogfooding"]["status"] == "behavior-changing"
    assert by_signal["workflow_obligations"]["status"] == "behavior-changing"
    assert by_signal["workspace_optimization"]["status"] == "behavior-changing"
    assert by_signal["planning"]["status"] == "behavior-changing"
    assert by_signal["memory"]["status"] == "advisory"
    assert by_signal["verification"]["status"] == "advisory"
    assert packet["dogfooding_obligations"][0]["id"] == "session-dogfooding-disposition"
    assert packet["workflow_obligation_effects"][0]["diagnostic_command_alone_satisfies"] is False
    assert packet["optimization_effect"]["enforced_effects"][0]["id"] == "compact-router-first"
    assert any("agent-efficiency: emit compact router state first" in item for item in packet["output_shape_requirements"])


def test_start_report_meta_task_keeps_routine_context_selector_only_with_background_drift(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Give me an in-chat dogfooding report about this session",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 10_000, label="start report/meta compact payload", sort_keys=False)
    assert "routine_work_context" not in payload
    _assert_selector_inventory_omitted_from_compact_start(payload)
    assert "installed_state_compatibility" not in payload
    assert "installed_state_drift_triage=background_advisory" in {item["signal"] for item in payload["decision_packet"]["attention"]}


def test_start_broad_question_words_do_not_trigger_meta_report_compaction(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "How should we implement the runtime proof selector?",
                "--select",
                "routine_work_context,installed_state_drift_triage,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    assert "routine_work_context" in payload
    authority = payload["installed_state_drift_triage"]["claim_effect_authority"]
    assert authority["effect_class"] == "planned-repo-mutation"
    assert authority["installed_payload_dependency"] == "dependent"


def test_start_narrow_source_work_qualifies_unrelated_installed_state_drift(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert "installed_state_drift_triage=waived_for_narrow_work" in {item["signal"] for item in payload["decision_packet"]["attention"]}


def test_start_unrelated_changed_path_does_not_make_payload_drift_actionable(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/typo.md",
                "--task",
                "Fix one docs typo",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert "installed_state_drift_triage=waived_for_narrow_work" in {item["signal"] for item in payload["decision_packet"]["attention"]}


def test_start_installed_state_drift_triage_is_actionable_for_payload_claims(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Verify payload freshness before release",
                "--select",
                "installed_state_drift_triage,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    triage = payload["installed_state_drift_triage"]
    assert triage["status"] == "actionable_now"
    assert triage["action_state"]["state"] == "safe_payload_sync_available"
    assert triage["action_state"]["repair_mechanism"] == "upgrade"
    assert triage["action_state"]["mutates_on_start"] is False
    assert triage["claim_relevant"] is True
    assert "agentic-workspace upgrade" in triage["repair_command"]


def test_start_treats_named_path_question_as_conceptual_reference(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Are you actively applying the dogfooding instructions in AGENTS.md?",
                "--select",
                "task_path_references,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    assert payload["next_safe_action"]["next_safe_action"] == "choose-smallest-workflow-shape"
    path_refs = payload["task_path_references"]
    assert path_refs["path_reference_kind"] == "conceptual-reference"
    assert path_refs["detected_paths"] == ["AGENTS.md"]
    assert path_refs["path_scoped_paths"] == []
    assert path_refs["agent_decision_required"] is True
    assert "implement --changed AGENTS.md" not in json.dumps(payload)


def test_start_path_scoped_task_text_uses_known_path_inspection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Review AGENTS.md",
                "--select",
                "task_path_references,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    assert payload["next_safe_action"]["next_safe_action"] == "inspect-known-task-paths"
    assert payload["next_safe_action"]["preferred_cli"].endswith('implement --changed AGENTS.md --task "Review AGENTS.md" --format json')
    path_refs = payload["task_path_references"]
    assert path_refs["path_reference_kind"] == "path-scoped-work"
    assert path_refs["path_scoped_paths"] == ["AGENTS.md"]
    assert path_refs["matched_action_terms"] == ["review"]


def test_start_forecasts_architecture_principle_for_path_scoped_task_before_edits(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_cli_architecture_principles(tmp_path)
    _write_decision_point_subsystem_intent(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_startup.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Update src/agentic_workspace/workspace_runtime_startup.py",
                "--select",
                "architecture_principles_forecast",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    forecast = payload["architecture_principles_forecast"]
    assert forecast["status"] == "provisional-match"
    assert forecast["forecast_state"] == "provisional"
    assert forecast["planned_scope"] == {
        "source": "task_path_references.path_scoped_paths",
        "paths": ["src/agentic_workspace/workspace_runtime_startup.py"],
    }
    assert forecast["architecture_principles"]["matched_principles"][0]["id"] == "host-agnostic-agent-judgment"
    assert forecast["architecture_principles"]["matched_principles"][0]["matcher"]["kind"] == "path_glob"
    assert "does not classify arbitrary task prose" in forecast["rule"]
    assert "implement --changed src/agentic_workspace/workspace_runtime_startup.py" in forecast["verification"]["command"]
    assert "--select architecture_principles" in forecast["verification"]["command"]
    assert forecast["decision_maturity"]["level"] == "evidence_seeking"
    intent = forecast["relevant_intent"]
    assert intent["phase"] == "pre-implementation"
    assert intent["subsystem_intents"][0]["id"] == "workspace-cli-runtime"
    assert "Workspace CLI" in intent["subsystem_intents"][0]["summary"]
    assert intent["relevance_basis"] == ["structured planned paths", "declared ownership path patterns"]
    assert intent["applicability_maturity"] == "provisional-until-changed-path-confirmation"
    assert "--select architecture_principles" in intent["confirmation"]["command"]


def test_start_surfaces_distinct_configuration_subsystem_intent(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_cli_architecture_principles(tmp_path)
    _write_decision_point_subsystem_intent(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "config.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Update src/agentic_workspace/config.py",
                "--select",
                "architecture_principles_forecast",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    forecast = payload["architecture_principles_forecast"]
    assert forecast["status"] == "provisional-match"
    intent = forecast["relevant_intent"]
    assert intent["subsystem_intents"][0]["id"] == "configuration"
    assert "precedence" in intent["subsystem_intents"][0]["summary"]


def test_start_surfaces_architecture_principle_scope_probe_when_planned_scope_missing(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_cli_architecture_principles(tmp_path)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement the architecture principle forecast update",
                "--select",
                "architecture_principles_forecast",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    forecast = payload["architecture_principles_forecast"]
    assert forecast["status"] == "needs-planned-scope"
    assert forecast["planned_scope"] == {"source": "missing_planned_scope", "paths": []}
    assert forecast["decision_maturity"]["level"] == "evidence_seeking"
    assert forecast["decision_maturity"]["missing_evidence"] == ["planned paths or changed paths"]
    assert "implement --changed <paths>" in forecast["decision_maturity"]["safe_probe"]
    assert "--select architecture_principles" in forecast["decision_maturity"]["safe_probe"]
    assert "does not classify arbitrary task prose" in forecast["rule"]


def test_start_keeps_architecture_principle_scope_probe_quiet_when_not_configured(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement the architecture principle forecast update",
                "--select",
                "architecture_principles_forecast",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert "architecture_principles_forecast" in payload["missing"]


def test_start_forecasts_architecture_principle_from_active_plan_scope_before_edits(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    _write_cli_architecture_principles(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_startup.py", "VALUE = 1\n")
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--target",
                str(tmp_path),
                "--id",
                "runtime-forecast-plan",
                "--title",
                "Runtime forecast plan",
                "--activate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "runtime-forecast-plan.plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    planned_paths = ["src/agentic_workspace/workspace_runtime_startup.py"]
    plan["scope"]["owned"] = planned_paths
    _write(plan_path, json.dumps(plan, indent=2) + "\n")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue the active plan",
                "--select",
                "architecture_principles_forecast",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    forecast = payload["architecture_principles_forecast"]
    assert forecast["status"] == "provisional-match"
    assert forecast["planned_scope"] == {
        "source": "active_planning_record.touched_scope",
        "paths": planned_paths,
    }
    assert forecast["architecture_principles"]["matched_principles"][0]["matcher"]["kind"] == "path_glob"


def test_start_keeps_architecture_principle_forecast_quiet_for_unmatched_path(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_cli_architecture_principles(tmp_path)
    _write(tmp_path / "README.md", "# Notes\n")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Review README.md",
                "--select",
                "task_path_references,architecture_principles_forecast",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["values"]["task_path_references"]["path_reference_kind"] == "path-scoped-work"
    assert "architecture_principles_forecast" in payload["missing"]


def test_start_explicit_changed_path_still_uses_changed_path_startup(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                "AGENTS.md",
                "--task",
                "Review AGENTS.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["decision_packet"]["action"]["id"] == "select-changed-path-proof"
    assert payload["decision_packet"]["action"]["command"] == "agentic-workspace proof --changed AGENTS.md --format json"
    assert payload["decision_packet"]["effects"]["proof_required"] is True


def test_start_context_authority_projection_fails_closed_for_missing_scoped_instruction_source(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / "AGENTS.md").unlink()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                "src/example.py",
                "--task",
                "Use the scoped instructions and skills before editing",
                "--select",
                "context_authority_projection",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]
    projection = payload["context_authority_projection"]

    assert projection["status"] == "repair-required"
    assert "scoped-instructions" in projection["missing_required_surfaces"]
    decision = next(item for item in projection["currentness"]["decision_requirements"] if item["surface"] == "scoped-instructions")
    assert decision["state"] == "missing-relevant-coverage"
    assert decision["task_effect"] == "material"
    assert decision["operation_id"] == ""
    assert projection["repair_operation"]["status"] == "not-required"
    assert projection["repair_operation"]["repairs"] == []


def test_local_chat_checkpoint_write_creates_valid_local_record_and_startup_packet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Implement #1700 checkpoint slice",
                "--issue",
                "#1700",
                "--pr",
                "1705",
                "--durable-source",
                "docs/reference/local-chat-checkpoints.md",
                "--last-proof",
                "uv run pytest tests/test_workspace_cli.py",
                "--next-safe-command",
                "uv run python scripts/run_agentic_workspace.py start --target . --format json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    written = json.loads(capsys.readouterr().out)
    assert written["status"] == "written"
    assert written["path"] == ".agentic-workspace/local/chat-checkpoint.json"
    assert written["durable_sources"] == ["docs/reference/local-chat-checkpoints.md"]
    write_result_schema = json.loads(
        Path("src/agentic_workspace/contracts/schemas/local_chat_checkpoint_write_result.schema.json").read_text(encoding="utf-8")
    )
    write_result_errors = sorted(Draft202012Validator(write_result_schema).iter_errors(written), key=lambda error: list(error.path))
    assert [error.message for error in write_result_errors] == []

    checkpoint_path = tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    schema = json.loads(Path("src/agentic_workspace/contracts/schemas/local_chat_checkpoint.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(checkpoint), key=lambda error: list(error.path))
    assert [error.message for error in errors] == []
    assert checkpoint["kind"] == "agentic-workspace/local-chat-checkpoint/v2"
    assert checkpoint["limits"]["not_closure_evidence"] is True
    assert "durable_sources" in checkpoint["resume_rule"]
    assert "fresh local/remote truth" in checkpoint["resume_rule"]
    assert checkpoint["volatile_observations"]["repo_root"]["value"] == tmp_path.resolve().as_posix()
    assert checkpoint["volatile_observations"]["branch"]["source"] == "git branch at checkpoint write"
    assert checkpoint["volatile_observations"]["head_commit"]["source"] == "git rev-parse HEAD at checkpoint write"
    assert checkpoint["volatile_observations"]["head_commit"]["observed_at"] == checkpoint["updated_at"]
    assert checkpoint["volatile_observations"]["current_pr"]["value"] == "1705"
    assert checkpoint["volatile_observations"]["current_pr"]["observed_at"] == checkpoint["updated_at"]
    assert checkpoint["volatile_observations"]["remote_comments"]["value"]["status"] == "not-checked-by-local-checkpoint-writer"
    assert checkpoint["volatile_observations"]["ci_state"]["value"]["status"] == "not-checked-by-local-checkpoint-writer"
    assert checkpoint["volatile_observations"]["dependency_state"]["value"]["status"] == "not-checked-by-local-checkpoint-writer"
    assert checkpoint["local_notes"]["task"] == "Implement #1700 checkpoint slice"
    assert checkpoint["local_notes"]["source"] == "local checkpoint write input; advisory only"
    assert checkpoint["proof_state"]["status"] == "historical-local-summary"
    assert checkpoint["proof_state"]["last_proof"] == ["uv run pytest tests/test_workspace_cli.py"]
    assert "new review or issue comments" in checkpoint["proof_state"]["valid_until_change"]
    assert any("PR or issue comments changed" in item for item in checkpoint["proof_state"]["stale_if"])
    assert "current completion evidence" in checkpoint["proof_state"]["rule"]
    resume_actions = [item["action"] for item in checkpoint["resume_checklist"]]
    assert "fetch latest PR comments and issue comments" in resume_actions
    assert "inspect git status and compare local HEAD with PR head" in resume_actions

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Resume checkpoint slice",
                "--select",
                "local_chat_checkpoint,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    startup = json.loads(capsys.readouterr().out)["values"]
    packet = startup["local_chat_checkpoint"]
    assert packet["status"] == "present"
    assert packet["durable_source_count"] == 1
    assert packet["durable_sources"] == ["docs/reference/local-chat-checkpoints.md"]
    assert packet["volatile_observations"]["head_commit"]["observed_at"] == checkpoint["updated_at"]
    assert packet["volatile_observations"]["current_pr"]["observed_at"] == checkpoint["updated_at"]
    assert packet["proof_state"]["status"] == "historical-local-summary"
    assert any(item["action"].startswith("re-run or re-evaluate proof") for item in packet["resume_checklist"])


def test_local_chat_checkpoint_surfaces_matching_planning_candidate_routes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1700-local-checkpoints", kind = "lane", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1700", title = "Local checkpoints", outcome = "Experiment with checkpoints.", promotion_signal = "Promote before parent closeout.", suggested_first_slice = "Shape checkpoint work." },
  { id = "github-1704-checkpoint-dogfood", kind = "slice", parent_id = "#1700", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #1704", title = "Checkpoint dogfood", outcome = "Dogfood checkpoint resume.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Run checkpoint dogfood." },
  { id = "github-9999-unrelated", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #9999", title = "Unrelated", outcome = "Do something else." },
]
""",
    )

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Dogfood #1700 checkpoint resume",
                "--issue",
                "#1700",
                "--issue",
                "#1704",
                "--durable-source",
                "https://github.com/rickardvh/agentic-workspace/issues/1704",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    routes = selected["planning_candidate_routes"]
    assert routes["status"] == "matched"
    assert routes["issue_refs"] == ["#1700", "#1704"]
    assert routes["candidate_ids"] == ["github-1700-local-checkpoints", "github-1704-checkpoint-dogfood"]
    assert routes["matched_candidate_count"] == 2
    assert routes["route_options"][0]["id"] == "github-1700-local-checkpoints"
    assert routes["route_options"][0]["title"] == "Local checkpoints"
    assert routes["route_options"][0]["matched_issue_refs"] == ["#1700"]
    assert routes["route_options"][0]["route_kind"] == "parent-lane"
    assert routes["route_options"][0]["next_action"] == "promote-roadmap-candidate-to-durable-planning-owner"
    assert routes["route_options"][1]["route_kind"] == "child-slice"
    assert routes["route_options"][1]["parent_id"] == "#1700"
    assert "planning promote-to-plan --item-id github-1700-local-checkpoints" in routes["route_options"][0]["command"]
    assert "--expect-planning-revision" in routes["route_options"][0]["command"]
    assert "github-9999-unrelated" not in json.dumps(routes)
    assert routes["authority"] == "advisory-from-local-checkpoint-and-checked-in-planning"
    assert "Verify checkpoint refs against durable sources" in routes["claim_boundary"]

    assert routes["route_options"][1]["id"] == "github-1704-checkpoint-dogfood"


def test_local_chat_checkpoint_omits_route_suggestions_when_no_candidate_matches(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1700-local-checkpoints", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1700", title = "Local checkpoints" },
]
""",
    )

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Resume unrelated checkpoint",
                "--issue",
                "#1801",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert selected["status"] == "present"
    assert "planning_candidate_routes" not in selected

    assert "planning_candidate_routes" not in selected


def test_local_chat_checkpoint_write_preserves_and_replaces_values(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "First",
                "--durable-source",
                "docs/first.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Second",
                "--durable-source",
                "docs/second.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    checkpoint_path = tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json"
    preserved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert preserved["durable_sources"] == ["docs/first.md", "docs/second.md"]
    assert preserved["task"] == "Second"

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Replacement",
                "--durable-source",
                "docs/replacement.md",
                "--replace",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    replaced = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert replaced["durable_sources"] == ["docs/replacement.md"]
    assert replaced["task"] == "Replacement"


def test_local_chat_checkpoint_startup_reports_absent_stale_and_unreadable(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    absent = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert absent["status"] == "absent"

    checkpoint_path = tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json"
    checkpoint_path.write_text(json.dumps({"kind": "old-kind", "durable_sources": ["docs/source.md"]}), encoding="utf-8")
    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    stale = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert stale["status"] == "stale"
    assert stale["durable_sources"] == ["docs/source.md"]

    checkpoint_path.write_text(
        json.dumps({"kind": "agentic-workspace/local-chat-checkpoint/v1", "durable_sources": ["docs/source.md"]}),
        encoding="utf-8",
    )
    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    stale_v1 = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert stale_v1["status"] == "stale"
    assert stale_v1["checkpoint_kind"] == "agentic-workspace/local-chat-checkpoint/v1"
    assert stale_v1["durable_sources"] == ["docs/source.md"]

    checkpoint_path.write_text("{not json", encoding="utf-8")
    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    unreadable = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert unreadable["status"] == "unreadable"


def test_mismatched_checkpoint_is_history_and_does_not_loop_selected_owner_start(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    mark_configuration_readiness_current(tmp_path)
    subprocess.run(["git", "checkout", "-b", "feature/old-checkpoint"], cwd=tmp_path, check=True, capture_output=True)
    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Old checkpoint task",
                "--pr",
                "2703",
                "--durable-source",
                "docs/old.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    subprocess.run(["git", "checkout", "-b", "feature/current-owner"], cwd=tmp_path, check=True, capture_output=True)
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "current-owner",
                "--title",
                "Current owner task",
                "--target",
                str(tmp_path),
                "--activate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    owner_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "current-owner.plan.json"
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["phase"] = "implementation"
    owner["next_action"] = "Implement the current owner task."
    owner["implementation_blockers"] = []
    owner["intent_satisfaction"] = {
        "original intent": "Current owner task",
        "was original intent fully satisfied?": "no; implementation is in progress",
        "evidence of intent satisfaction": "The current owner is selected and ready for implementation.",
        "unsolved intent passed to": "this active execplan",
    }
    owner_path.write_text(json.dumps(owner, indent=2) + "\n", encoding="utf-8")
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Current owner task", "--format", "json"]) == 0
    decision = json.loads(capsys.readouterr().out)["decision_packet"]
    assert decision["owner"]["task_relation"] == "continues-selected-owner"
    assert decision["action"]["id"] != "continue-active-planning-record"
    assert decision["effects"]["implementation_allowed"] is True

    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    checkpoint = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert checkpoint["current_work_control"]["relation"] == "historical-mismatch"
    assert checkpoint["current_work_control"]["control_allowed"] is False
    assert "branch" in checkpoint["current_work_control"]["mismatched_fields"]


def test_same_work_stale_checkpoint_names_exact_refresh_route(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Same work",
                "--durable-source",
                "docs/same.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    _write(tmp_path / "later.txt", "later\n")
    subprocess.run(["git", "add", "later.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "later"], cwd=tmp_path, check=True, capture_output=True)
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    checkpoint = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    control = checkpoint["current_work_control"]
    assert control["relation"] == "stale-same-work"
    assert control["control_allowed"] is True
    assert control["required_action"] == "refresh-checkpoint"
    assert "checkpoint write" in control["command"] and "--replace" in control["command"]


def _init_real_git_repo_with_commit(target: Path) -> None:
    subprocess.run(["git", "init"], cwd=target, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=target, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=target, text=True, capture_output=True, check=True)
    _write(target / "README.md", "# Host\n")
    subprocess.run(["git", "add", "README.md"], cwd=target, text=True, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=target, text=True, capture_output=True, check=True)


def _git_value(target: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=target, text=True, capture_output=True, check=True).stdout.strip()


def _write_local_work_thread(
    target: Path,
    *,
    thread_id: str,
    label: str,
    issue: str = "#1987",
    branch: str | None = None,
    head: str | None = None,
    updated_at: str | None = None,
) -> Path:
    branch = branch if branch is not None else _git_value(target, "branch", "--show-current")
    head = head if head is not None else _git_value(target, "rev-parse", "HEAD")
    updated_at = updated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    record = {
        "kind": "agentic-workspace/local-work-thread/v1",
        "id": thread_id,
        "label": label,
        "created_at": updated_at,
        "updated_at": updated_at,
        "refs": {
            "issues": [issue],
            "prs": [],
            "planning": [".agentic-workspace/planning/execplans/issue-1987-work-threads.plan.json"],
        },
        "durable_sources": [f"https://github.com/rickardvh/agentic-workspace/issues/{issue.lstrip('#')}"],
        "observations": {
            "branch": {"value": branch, "source": "test fixture", "observed_at": updated_at},
            "worktree": {"value": target.resolve().as_posix(), "source": "test fixture", "observed_at": updated_at},
            "head_commit": {"value": head, "source": "test fixture", "observed_at": updated_at},
        },
        "proof_state": {
            "status": "historical-local-summary",
            "last_proof": ["uv run pytest tests/test_workspace_cli.py"],
            "stale_if": ["HEAD changed after observed_at"],
            "rule": "Do not treat local proof as closure evidence; re-run proof before completion claims.",
        },
        "next_safe_action": {
            "command": "uv run python scripts/run_agentic_workspace.py start --target . --select work_threads --format json",
            "selector": "work_threads",
        },
        "limits": {
            "local_only": True,
            "gitignored": True,
            "advisory": True,
            "not_closure_evidence": True,
            "no_raw_transcripts": True,
            "no_secrets": True,
            "no_priority_status_assignment": True,
            "durable_decisions_require_durable_source": True,
        },
    }
    path = target / ".agentic-workspace" / "local" / "work-threads" / f"{thread_id}.json"
    _write_json(path, record)
    return path


def test_local_work_thread_schema_and_startup_clear_match(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    thread_path = _write_local_work_thread(tmp_path, thread_id="issue-1987-main", label="Issue 1987 lane")

    schema = json.loads(Path("src/agentic_workspace/contracts/schemas/local_work_thread.schema.json").read_text(encoding="utf-8"))
    record = json.loads(thread_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(record), key=lambda error: list(error.path))
    assert [error.message for error in errors] == []
    assert record["limits"]["no_priority_status_assignment"] is True

    assert (
        cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987 lane", "--select", "work_threads", "--format", "json"]) == 0
    )
    packet = json.loads(capsys.readouterr().out)["values"]["work_threads"]

    assert packet["status"] == "clear-match"
    assert packet["selected_thread"]["id"] == "issue-1987-main"
    assert packet["selected_thread"]["match_reasons"] == ["branch-match", "head-match", "task-ref-match"]
    assert packet["selected_thread"]["planning_owner_boundary"]["status"] == "reread-required"
    assert packet["claim_boundary"].startswith("Local work threads are continuation handles")
    assert packet["limits"]["not_closure_evidence"] is True

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987 lane", "--format", "json"]) == 0
    startup = json.loads(capsys.readouterr().out)
    assert "work_threads" not in startup
    assert "work_threads=clear-match" in {item["signal"] for item in startup["decision_packet"]["attention"]}


def test_local_work_threads_warn_when_planning_owner_changed(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    thread_time = datetime.now(timezone.utc).replace(microsecond=0).timestamp() - 60
    updated_at = datetime.fromtimestamp(thread_time, timezone.utc).replace(microsecond=0).isoformat()
    _write_local_work_thread(
        tmp_path,
        thread_id="issue-1991-local-cursor",
        label="Issue 1991 local cursor",
        issue="#1991",
        updated_at=updated_at,
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "issue-1987-work-threads.plan.json"
    _write_json(plan_path, {"kind": "planning-execplan/v1", "id": "issue-1987-work-threads", "references": ["#1987"]})
    owner_time = thread_time + 30
    os.utime(plan_path, (owner_time, owner_time))

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1991", "--select", "work_threads", "--format", "json"]) == 0
    packet = json.loads(capsys.readouterr().out)["values"]["work_threads"]

    assert packet["status"] == "stale"
    stale = packet["stale_threads"][0]
    assert stale["id"] == "issue-1991-local-cursor"
    assert "planning-owner-changed" in stale["stale_reasons"]
    assert stale["planning_owner_boundary"]["status"] == "changed-owner"
    assert stale["planning_owner_boundary"]["changed_owner_refs"] == [
        {
            "path": ".agentic-workspace/planning/execplans/issue-1987-work-threads.plan.json",
            "last_modified": datetime.fromtimestamp(owner_time, timezone.utc).replace(microsecond=0).isoformat(),
            "thread_updated_at": updated_at,
            "reason": "planning-owner-newer-than-local-thread",
        }
    ]
    assert packet["cleanup"]["status"] == "none"
    assert packet["cleanup"]["prune_candidates"] == []


def test_local_work_threads_resume_after_branch_switch_round_trip(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_local_work_thread(tmp_path, thread_id="issue-1987-master", label="Issue 1987 master")

    subprocess.run(["git", "switch", "-c", "branch-b"], cwd=tmp_path, text=True, capture_output=True, check=True)
    _write(tmp_path / "branch-b.txt", "b\n")
    subprocess.run(["git", "add", "branch-b.txt"], cwd=tmp_path, text=True, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "branch b"], cwd=tmp_path, text=True, capture_output=True, check=True)

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987", "--select", "work_threads", "--format", "json"]) == 0
    away = json.loads(capsys.readouterr().out)["values"]["work_threads"]
    assert away["status"] == "stale"
    assert away["stale_threads"][0]["id"] == "issue-1987-master"
    assert "different-branch" in away["stale_threads"][0]["stale_reasons"]
    assert away["cleanup"]["status"] == "none"
    assert away["cleanup"]["prune_candidates"] == []

    subprocess.run(["git", "switch", "master"], cwd=tmp_path, text=True, capture_output=True, check=True)

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987", "--select", "work_threads", "--format", "json"]) == 0
    returned = json.loads(capsys.readouterr().out)["values"]["work_threads"]
    assert returned["status"] == "clear-match"
    assert returned["selected_thread"]["id"] == "issue-1987-master"
    assert returned["selected_thread"]["match_reasons"] == ["branch-match", "head-match", "task-ref-match"]


def test_local_work_threads_deleted_recorded_branch_is_prunable(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    subprocess.run(["git", "switch", "-c", "obsolete-lane"], cwd=tmp_path, text=True, capture_output=True, check=True)
    _write(tmp_path / "obsolete.txt", "obsolete\n")
    subprocess.run(["git", "add", "obsolete.txt"], cwd=tmp_path, text=True, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "obsolete lane"], cwd=tmp_path, text=True, capture_output=True, check=True)
    _write_local_work_thread(tmp_path, thread_id="issue-2001-deleted-branch", label="Issue 2001 deleted branch")

    subprocess.run(["git", "switch", "master"], cwd=tmp_path, text=True, capture_output=True, check=True)
    subprocess.run(["git", "branch", "-D", "obsolete-lane"], cwd=tmp_path, text=True, capture_output=True, check=True)

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987", "--select", "work_threads", "--format", "json"]) == 0
    packet = json.loads(capsys.readouterr().out)["values"]["work_threads"]

    assert packet["status"] == "stale"
    stale = packet["stale_threads"][0]
    assert stale["id"] == "issue-2001-deleted-branch"
    assert stale["observations"]["recorded_branch_exists"] is False
    assert {"different-branch", "branch-missing", "head-drift", "proof-invalidated"} <= set(stale["stale_reasons"])
    assert packet["cleanup"]["status"] == "available"
    assert packet["cleanup"]["prune_candidates"][0]["stale_reasons"] == stale["stale_reasons"]
    assert "branch-missing" in packet["cleanup"]["prune_candidates"][0]["stale_reasons"]


def test_local_work_threads_report_ambiguity_and_checkpoint_bridge(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_local_work_thread(tmp_path, thread_id="issue-1987-alpha", label="Issue 1987 alpha")
    _write_local_work_thread(tmp_path, thread_id="issue-1987-beta", label="Issue 1987 beta")

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Resume #1987 checkpoint fallback",
                "--issue",
                "#1987",
                "--durable-source",
                "https://github.com/rickardvh/agentic-workspace/issues/1987",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987", "--select", "work_threads", "--format", "json"]) == 0
    packet = json.loads(capsys.readouterr().out)["values"]["work_threads"]

    assert packet["status"] == "ambiguous"
    assert packet["current_match_count"] == 2
    assert {thread["id"] for thread in packet["current_matches"]} == {
        "issue-1987-alpha",
        "issue-1987-beta",
    }
    assert packet["checkpoint_bridge"]["status"] == "available-fallback"
    assert packet["checkpoint_bridge"]["source_selector"] == "local_chat_checkpoint"
    forbidden_task_fields = {"priority", "assignee", "assignment", "canonical_status", "estimate", "dependencies"}
    assert all(not forbidden_task_fields.intersection(thread) for thread in packet["current_matches"])
    alpha = next(thread for thread in packet["current_matches"] if thread["id"] == "issue-1987-alpha")
    beta = next(thread for thread in packet["current_matches"] if thread["id"] == "issue-1987-beta")
    assert alpha["selection_actions"]["select"]["operation"] == "work-thread.select"
    assert alpha["selection_actions"]["select"]["command"].endswith(
        "work-thread select --thread-id issue-1987-alpha --target . --format json"
    )
    assert alpha["selection_actions"]["restore"]["status"] == "not-needed"
    assert alpha["selection_actions"]["proceed"]["selector"] == "work_threads"

    _write_json(
        tmp_path / ".agentic-workspace" / "local" / "work-threads" / "index.json",
        {"kind": "agentic-workspace/local-work-thread-index/v1", "note": "preserve-me"},
    )
    assert cli.main(["work-thread", "select", "--thread-id", "issue-1987-alpha", "--target", str(tmp_path), "--format", "json"]) == 0
    selected_payload = json.loads(capsys.readouterr().out)
    assert selected_payload["kind"] == "agentic-workspace/local-work-thread-select/v1"
    assert selected_payload["thread_id"] == "issue-1987-alpha"
    assert selected_payload["previous_thread_id"] == ""
    assert selected_payload["preserved_keys"] == ["kind", "note"]
    assert cli.main(["work-thread", "select", "--thread-id", "issue-1987-beta", "--target", str(tmp_path), "--format", "json"]) == 0
    beta_payload = json.loads(capsys.readouterr().out)
    assert beta_payload["thread_id"] == "issue-1987-beta"
    assert beta_payload["previous_thread_id"] == "issue-1987-alpha"
    assert beta["selection_actions"]["select"]["command"].endswith(
        "work-thread select --thread-id issue-1987-beta --target . --format json"
    )
    assert cli.main(["work-thread", "select", "--thread-id", "issue-1987-alpha", "--target", str(tmp_path), "--format", "json"]) == 0
    alpha_again_payload = json.loads(capsys.readouterr().out)
    assert alpha_again_payload["thread_id"] == "issue-1987-alpha"
    assert alpha_again_payload["previous_thread_id"] == "issue-1987-beta"
    index_payload = json.loads((tmp_path / ".agentic-workspace" / "local" / "work-threads" / "index.json").read_text(encoding="utf-8"))
    assert index_payload["note"] == "preserve-me"
    assert index_payload["selected_thread_id"] == "issue-1987-alpha"
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987", "--select", "work_threads", "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)["values"]["work_threads"]
    assert selected["status"] == "clear-match"
    assert selected["index"]["selected_thread_id"] == "issue-1987-alpha"
    assert selected["selected_thread"]["id"] == "issue-1987-alpha"
    assert selected["selection_routes"]["selected_index_path"] == ".agentic-workspace/local/work-threads/index.json"


def test_local_work_threads_checkpoint_fallback_does_not_compete_with_registry_match(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write_local_work_thread(tmp_path, thread_id="issue-1987-main", label="Issue 1987 main")

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Resume #1987 checkpoint fallback",
                "--issue",
                "#1987",
                "--durable-source",
                "https://github.com/rickardvh/agentic-workspace/issues/1987",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987", "--select", "work_threads", "--format", "json"]) == 0
    packet = json.loads(capsys.readouterr().out)["values"]["work_threads"]

    assert packet["status"] == "clear-match"
    assert packet["current_match_count"] == 1
    assert packet["selected_thread"]["id"] == "issue-1987-main"
    assert packet["checkpoint_bridge"]["status"] == "available-fallback"
    assert {thread["id"] for thread in packet["current_matches"]} == {"issue-1987-main"}


def test_local_work_threads_classify_stale_and_selected_missing(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    old_head = _git_value(tmp_path, "rev-parse", "HEAD")
    subprocess.run(["git", "switch", "-c", "branch-b"], cwd=tmp_path, text=True, capture_output=True, check=True)
    _write(tmp_path / "branch-b.txt", "b\n")
    subprocess.run(["git", "add", "branch-b.txt"], cwd=tmp_path, text=True, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "branch b"], cwd=tmp_path, text=True, capture_output=True, check=True)
    _write_local_work_thread(
        tmp_path,
        thread_id="issue-1987-stale",
        label="Issue 1987 stale",
        branch="master",
        head=old_head,
        updated_at="2026-01-01T00:00:00+00:00",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume #1987", "--select", "work_threads", "--format", "json"]) == 0
    stale_packet = json.loads(capsys.readouterr().out)["values"]["work_threads"]

    assert stale_packet["status"] == "stale"
    stale = stale_packet["stale_threads"][0]
    assert stale["id"] == "issue-1987-stale"
    assert {"different-branch", "head-drift", "old-unused-thread", "proof-invalidated"} <= set(stale["stale_reasons"])
    assert stale_packet["cleanup"]["status"] == "available"
    assert stale_packet["cleanup"]["prune_candidates"][0]["safe_to_forget"] is True
    assert stale_packet["cleanup"]["safe_local_only"] is True

    _write_json(
        tmp_path / ".agentic-workspace" / "local" / "work-threads" / "index.json",
        {"selected_thread_id": "missing-thread"},
    )
    assert cli.main(["start", "--target", str(tmp_path), "--select", "work_threads", "--format", "json"]) == 0
    selected_missing = json.loads(capsys.readouterr().out)["values"]["work_threads"]
    assert selected_missing["status"] == "selected-missing"
    assert selected_missing["index"]["selected_thread_id"] == "missing-thread"


def test_local_work_threads_prune_removes_only_safe_local_candidates(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    old_head = _git_value(tmp_path, "rev-parse", "HEAD")
    subprocess.run(["git", "switch", "-c", "branch-b"], cwd=tmp_path, text=True, capture_output=True, check=True)
    _write(tmp_path / "branch-b.txt", "b\n")
    subprocess.run(["git", "add", "branch-b.txt"], cwd=tmp_path, text=True, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "branch b"], cwd=tmp_path, text=True, capture_output=True, check=True)
    stale_path = _write_local_work_thread(
        tmp_path,
        thread_id="issue-1992-stale",
        label="Issue 1992 stale",
        issue="#1992",
        branch="master",
        head=old_head,
        updated_at="2026-01-01T00:00:00+00:00",
    )
    readme = tmp_path / "README.md"

    assert (
        cli.main(
            [
                "work-thread",
                "prune",
                "--target",
                str(tmp_path),
                "--thread-id",
                "issue-1992-stale",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["status"] == "dry-run"
    assert dry_run["pruned_thread_ids"] == ["issue-1992-stale"]
    assert stale_path.exists()
    assert readme.exists()

    assert (
        cli.main(
            [
                "work-thread",
                "prune",
                "--target",
                str(tmp_path),
                "--thread-id",
                "issue-1992-stale",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    schema = json.loads(
        Path("src/agentic_workspace/contracts/schemas/local_work_thread_prune_result.schema.json").read_text(encoding="utf-8")
    )
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.path))
    assert [error.message for error in errors] == []
    assert payload["status"] == "pruned"
    assert payload["pruned_thread_ids"] == ["issue-1992-stale"]
    assert payload["pruned_paths"] == [stale_path.relative_to(tmp_path).as_posix()]
    assert payload["skipped"] == []
    assert not stale_path.exists()
    assert readme.exists()

    assert (
        cli.main(
            [
                "work-thread",
                "prune",
                "--target",
                str(tmp_path),
                "--all-candidates",
                "--format",
                "json",
            ]
        )
        == 0
    )
    repeated = json.loads(capsys.readouterr().out)
    assert repeated["status"] == "nothing-to-prune"
    assert repeated["requested_thread_ids"] == []
    assert repeated["pruned_thread_ids"] == []
    assert repeated["skipped"] == []

    assert cli.main(["start", "--target", str(tmp_path), "--select", "work_threads", "--format", "json"]) == 0
    after = json.loads(capsys.readouterr().out)["values"]["work_threads"]
    assert after["thread_count"] == 0
    assert after["cleanup"]["prune_candidates"] == []


def test_decision_point_carry_inspect_select_prune_is_exact_and_preserves_other_contexts(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    carry_dir = tmp_path / ".agentic-workspace" / "local" / "decision-point-intent"
    carry_dir.mkdir(parents=True)

    def write_carry(key: str, context_id: str, owner_id: str) -> Path:
        path = carry_dir / f"{key}.json"
        _write_json(
            path,
            {
                "kind": "agentic-workspace/decision-point-intent-carry/v1",
                "status": "active",
                "work_binding": {
                    "key": key,
                    "context_id": context_id,
                    "owner_binding": {
                        "relation": "plan-continuation",
                        "owner_id": owner_id,
                    },
                },
                "lifecycle": {
                    "state": "active",
                    "created_at": "2026-07-14T00:00:00+00:00",
                    "updated_at": "2026-07-14T00:00:00+00:00",
                },
            },
        )
        return path

    selected_path = write_carry("carry-a", "context-a", "issue-2258")
    preserved_path = write_carry("carry-b", "context-b", "issue-3100")

    assert cli.main(["work-thread", "carry-inspect", "--target", str(tmp_path), "--format", "json"]) == 0
    inspected = json.loads(capsys.readouterr().out)
    inspect_schema = json.loads(
        Path("src/agentic_workspace/contracts/schemas/decision_point_carry_inspect_result.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(inspect_schema).iter_errors(inspected)) == []
    assert inspected["active_count"] == 2
    assert {record["key"] for record in inspected["records"]} == {"carry-a", "carry-b"}
    assert "archive" not in inspected["safe_recovery"]["prune"]

    assert cli.main(["work-thread", "carry-select", "--key", "carry-a", "--target", str(tmp_path), "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)
    select_schema = json.loads(
        Path("src/agentic_workspace/contracts/schemas/decision_point_carry_select_result.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(select_schema).iter_errors(selected)) == []
    assert selected["context_id"] == "context-a"

    prune_argv = [
        "work-thread",
        "carry-prune",
        "--key",
        "carry-a",
        "--expect-context-id",
        "context-a",
        "--reason",
        "owner context was superseded by an explicit transition",
        "--target",
        str(tmp_path),
        "--format",
        "json",
    ]
    assert cli.main([*prune_argv, "--dry-run"]) == 0
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["status"] == "dry-run"
    assert json.loads(selected_path.read_text(encoding="utf-8"))["lifecycle"]["state"] == "active"

    assert cli.main(prune_argv) == 0
    pruned = json.loads(capsys.readouterr().out)
    prune_schema = json.loads(
        Path("src/agentic_workspace/contracts/schemas/decision_point_carry_prune_result.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(prune_schema).iter_errors(pruned)) == []
    assert pruned["status"] == "pruned"
    assert json.loads(selected_path.read_text(encoding="utf-8"))["lifecycle"]["state"] == "stale"
    assert json.loads(preserved_path.read_text(encoding="utf-8"))["lifecycle"]["state"] == "active"
    assert not (carry_dir / "selection.json").exists()


def test_decision_point_binding_status_agrees_across_start_summary_and_doctor(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        'schema_version = 1\n[todo]\nactive_items = [{ id = "issue-2258", refs = ["#2258"] }]\n',
    )
    task = "Continue #2258"

    assert cli.main(["start", "--target", str(tmp_path), "--task", task, "--select", "work_threads", "--format", "json"]) == 0
    start_status = json.loads(capsys.readouterr().out)["values"]["work_threads"]["decision_point_carry_status"]

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--task",
                task,
                "--select",
                "decision_point_carry_status",
                "--format",
                "json",
            ]
        )
        == 0
    )
    summary_status = json.loads(capsys.readouterr().out)["values"]["decision_point_carry_status"]

    assert cli.main(["doctor", "--target", str(tmp_path), "--select", "decision_point_carry_status", "--format", "json"]) == 0
    doctor_status = json.loads(capsys.readouterr().out)["values"]["decision_point_carry_status"]

    assert start_status == summary_status
    assert start_status["relation"] == "plan-continuation"
    assert start_status["reason_code"] == "plan-continuation"
    assert start_status["commit_state"] == "commit-on-use"
    assert doctor_status["active_total"] == start_status["active_total"]
    assert doctor_status["capacity_blocked_total"] == start_status["capacity_blocked_total"]
    assert doctor_status["lifecycle_operation"] == start_status["lifecycle_operation"]


def test_local_work_threads_prune_can_remove_stale_checkpoint_fallback(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    old_head = _git_value(tmp_path, "rev-parse", "HEAD")
    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #1992 old branch",
                "--issue",
                "#1992",
                "--durable-source",
                "https://github.com/rickardvh/agentic-workspace/issues/1992",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    checkpoint_path = tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["volatile_observations"]["branch"]["value"] = "deleted-branch"
    checkpoint["volatile_observations"]["head_commit"]["value"] = old_head
    checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")

    assert cli.main(["start", "--target", str(tmp_path), "--select", "work_threads", "--format", "json"]) == 0
    projected = json.loads(capsys.readouterr().out)["values"]["work_threads"]
    candidate = projected["cleanup"]["prune_candidates"][0]
    assert candidate["id"] == "checkpoint-default"
    assert candidate["source"] == "local_chat_checkpoint"
    assert candidate["path"] == ".agentic-workspace/local/chat-checkpoint.json"
    assert "branch-missing" in candidate["stale_reasons"]

    assert (
        cli.main(
            [
                "work-thread",
                "prune",
                "--target",
                str(tmp_path),
                "--thread-id",
                "checkpoint-default",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["status"] == "dry-run"
    assert dry_run["pruned_paths"] == [".agentic-workspace/local/chat-checkpoint.json"]
    assert checkpoint_path.exists()

    assert (
        cli.main(
            [
                "work-thread",
                "prune",
                "--target",
                str(tmp_path),
                "--thread-id",
                "checkpoint-default",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pruned"
    assert payload["pruned_thread_ids"] == ["checkpoint-default"]
    assert payload["pruned_paths"] == [".agentic-workspace/local/chat-checkpoint.json"]
    assert not checkpoint_path.exists()


def test_local_work_threads_prune_skips_current_non_candidate(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    current_path = _write_local_work_thread(tmp_path, thread_id="issue-1992-current", label="Issue 1992 current", issue="#1992")

    assert (
        cli.main(
            [
                "work-thread",
                "prune",
                "--target",
                str(tmp_path),
                "--thread-id",
                "issue-1992-current",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "nothing-to-prune"
    assert payload["pruned_thread_ids"] == []
    assert payload["skipped"] == [{"id": "issue-1992-current", "reason": "not-current-prune-candidate"}]
    assert current_path.exists()


def test_stale_cleanup_report_separates_local_and_checked_in_planning_cleanup(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    local_thread = _write_local_work_thread(
        tmp_path,
        thread_id="issue-2001-local",
        label="Issue 2001 local thread",
        issue="#44",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[active]
execplans = [
  ".agentic-workspace/planning/execplans/active-selector.plan.json",
]

[todo]
active_items = [
  { id = "issue-44-active", title = "Closed upstream active", status = "active", surface = ".agentic-workspace/planning/execplans/issue-44-active.plan.json", next_action = "Review stale owner.", done_when = "Proof and residue are reconciled." },
]
queued_items = [
  { id = "issue-45-queued", title = "Merged PR queued", status = "next", surface = ".agentic-workspace/planning/execplans/issue-45-queued.plan.json" },
]

[roadmap]
lanes = []
candidates = [
  { id = "issue-46-open", maturity = "candidate", status = "next", refs = "GitHub #46", title = "Open upstream candidate", outcome = "Keep.", reason = "Open.", promotion_signal = "When selected.", suggested_first_slice = "Inspect." },
]
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "issue-44-active.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "issue-44-active",
            "title": "Closed upstream active",
            "references": ["#44"],
            "proof_report": {"status": "missing"},
        },
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "active-selector.plan.json",
        {
            "kind": "planning-execplan/v1",
            "id": "active-selector",
            "title": "Closed active selector",
            "references": ["#47"],
            "proof_report": {"status": "missing"},
        },
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "refreshed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "items": [
                {"system": "fixture", "id": "#44", "title": "Closed upstream active", "status": "closed", "kind": "issue"},
                {"system": "fixture", "id": "#45", "title": "Merged queued PR", "status": "merged", "kind": "pull_request"},
                {"system": "fixture", "id": "#46", "title": "Open upstream candidate", "status": "open", "kind": "issue"},
                {"system": "fixture", "id": "#47", "title": "Closed active selector", "status": "closed", "kind": "issue"},
            ],
        },
    )

    assert cli.main(["start", "--target", str(tmp_path), "--select", "work_threads", "--format", "json"]) == 0
    work_threads = json.loads(capsys.readouterr().out)["values"]["work_threads"]
    assert work_threads["cleanup"]["status"] == "available"
    assert work_threads["cleanup"]["prune_candidates"][0]["id"] == "issue-2001-local"
    assert "external-owner-closed" in work_threads["stale_threads"][0]["stale_reasons"]
    assert local_thread.exists()

    assert cli.main(["report", "--target", str(tmp_path), "--section", "stale_cleanup", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]

    assert payload["kind"] == "agentic-workspace/stale-cleanup/v1"
    assert payload["status"] == "review-required"
    assert payload["local_only_cleanup"]["status"] == "available"
    assert payload["local_only_cleanup"]["candidates"][0]["id"] == "issue-2001-local"
    assert payload["checked_in_planning_cleanup"]["status"] == "review-required"
    planning_candidates = payload["checked_in_planning_cleanup"]["candidates"]
    assert {candidate["section"] for candidate in planning_candidates} >= {
        "active.execplans",
        "todo.active_items",
        "todo.queued_items",
        "planning.execplans",
    }
    active_selector = next(candidate for candidate in planning_candidates if candidate["section"] == "active.execplans")
    assert active_selector["cleanup_kind"] == "checked-in-active-selector-review"
    assert active_selector["closed_refs"] == ["#47"]
    assert all(candidate["review_required"] is True for candidate in planning_candidates)
    assert "PR or issue closure alone is not completion proof" in payload["checked_in_planning_cleanup"]["rule"]
    assert payload["residue_promotion"]["status"] == "required-before-checked-in-cleanup"


def test_stale_cleanup_report_stays_quiet_when_no_cleanup_is_actionable(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "issue-46-open", maturity = "candidate", status = "next", refs = "GitHub #46", title = "Open upstream candidate", outcome = "Keep.", reason = "Open.", promotion_signal = "When selected.", suggested_first_slice = "Inspect." },
]
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "refreshed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "items": [
                {"system": "fixture", "id": "#46", "title": "Open upstream candidate", "status": "open", "kind": "issue"},
            ],
        },
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "stale_cleanup", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]

    assert payload["status"] == "none"
    assert payload["local_only_cleanup"]["status"] == "none"
    assert payload["checked_in_planning_cleanup"]["status"] == "none"
    assert payload["startup_visibility"]["status"] == "quiet-unless-actionable"


def test_start_pr_reference_wording_does_not_route_as_unknown_issue_scope(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Address the reviews on #103",
                "--select",
                "planning_safety_gate,issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    gate = payload["values"]["planning_safety_gate"]
    assert gate["issue_refs"] == []
    assert gate["pr_context"]["status"] == "pr-context-detected"
    assert gate["pr_context"]["refs"] == ["#103"]
    assert payload.get("missing") == ["issue_reference_intent"]


@pytest.mark.parametrize("task", ["Branch-sync #2474 into this branch", "Sync branch #2474 before continuing"])
def test_start_branch_sync_reference_does_not_route_as_unknown_issue_scope(tmp_path: Path, capsys, task: str) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                task,
                "--select",
                "planning_safety_gate,issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    gate = payload["values"]["planning_safety_gate"]
    assert gate["issue_refs"] == []
    assert gate["pr_context"]["refs"] == ["#2474"]
    assert payload.get("missing") == ["issue_reference_intent"]


@pytest.mark.parametrize(
    ("task", "issue_refs", "pr_refs"),
    [
        ("Review issue #123", ["#123"], []),
        ("Sync branch #2474 for issue #2481", ["#2481"], ["#2474"]),
        ("Review PR #2474 for issue #2481", ["#2481"], ["#2474"]),
    ],
)
def test_start_classifies_mixed_issue_and_pr_references_per_reference(
    tmp_path: Path,
    capsys,
    task: str,
    issue_refs: list[str],
    pr_refs: list[str],
) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                task,
                "--select",
                "planning_safety_gate,issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    gate = payload["values"]["planning_safety_gate"]
    assert gate["issue_refs"] == issue_refs
    assert gate["pr_context"]["refs"] == pr_refs


def test_start_github_comment_report_correction_does_not_force_planning(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Correct the #1942 follow-up report format after PR #1950 review fix",
                "--select",
                "planning_safety_gate,issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    gate = payload["values"]["planning_safety_gate"]

    assert gate["workflow_sufficient"] is True
    assert gate["decision"] != "planning-escalation-required"
    assert gate["issue_refs"] == ["#1942"]
    assert gate["pr_context"]["refs"] == ["#1950"]
    assert payload["values"]["issue_reference_intent"]["issue_refs"] == ["#1942"]
    assert "external_reporting_context" not in gate


def test_start_mixed_issue_implementation_and_report_target_does_not_force_planning(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #1951 and make a better report on #1942",
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    gate = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]

    assert gate["workflow_sufficient"] is True
    assert gate["decision"] != "planning-escalation-required"
    assert gate["issue_refs"] == ["#1942", "#1951"]
    assert "external_reporting_context" not in gate


@pytest.mark.parametrize("task", ["Work on #1951", "Fix bug in #1951", "Implement changes in #1951"])
def test_start_bare_preposition_issue_refs_remain_implementation_scope(tmp_path: Path, capsys, task: str) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                task,
                "--select",
                "planning_safety_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    gate = json.loads(capsys.readouterr().out)["values"]["planning_safety_gate"]

    assert gate["issue_refs"] == ["#1951"]
    assert "external_reporting_context" not in gate


def test_start_issue_reference_wording_keeps_issue_scope_warning(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #103",
                "--select",
                "planning_safety_gate,issue_reference_intent,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]
    assert payload["next_safe_action"]["next_safe_action"] == "refresh-external-issue-intent"
    gate = payload["planning_safety_gate"]
    assert gate["decision_maturity"]["level"] == "evidence_seeking"
    assert gate["decision_maturity"]["missing_evidence"] == ["external issue intent evidence"]
    assert gate["decision_maturity"]["safe_probe"] == "refresh-external-intent-or-state-bounded-slice"
    assert payload["issue_reference_intent"]["issue_refs"] == ["#103"]
    effect = payload["issue_reference_intent"]["action_effect"]
    assert effect["force"] == "required_before_claim"
    assert effect["allowed_now"] == "read-review-and-state-bounded-slice"
    assert effect["blocked_until_reconciled"] == ["claim-external-issue-scope-confirmed", "claim-task-complete"]
    assert effect["resolution_selector"] == "context.issue_reference_intent"
    assert "external-intent refresh-github" in effect["resolution_command"]
    assert "--issue 103" in effect["resolution_command"]
    assert "--state all" not in effect["resolution_command"]


def test_external_intent_issue_scoped_refresh_satisfies_issue_reference_intent(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #103",
                "--select",
                "issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    before = json.loads(capsys.readouterr().out)["values"]["issue_reference_intent"]
    assert before["status"] == "details-needed"
    assert "--issue 103" in before["next_command"]

    class Result:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    calls: list[list[str]] = []
    real_run = cli.subprocess.run

    def fake_run(command, *args, **kwargs):
        calls.append(command)
        if command[:1] != ["gh"]:
            return real_run(command, *args, **kwargs)
        if command[:3] == ["gh", "repo", "view"]:
            return Result(json.dumps({"nameWithOwner": "acme/project"}))
        if command[:3] == ["gh", "pr", "view"]:
            return Result("null")
        assert command[:3] == ["gh", "issue", "view"]
        assert command[3] == "103"
        return Result(
            json.dumps(
                {
                    "number": 103,
                    "title": "Issue-scoped evidence",
                    "state": "OPEN",
                    "url": "https://github.com/acme/project/issues/103",
                    "labels": [{"name": "workflow"}],
                    "createdAt": "2026-07-08T00:00:00Z",
                    "updatedAt": "2026-07-08T01:00:00Z",
                    "closedAt": "",
                    "body": "## Problem\nDurable issue body.",
                    "comments": [{"body": "Review comment"}],
                }
            )
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(tmp_path),
                "--issue",
                "103",
                "--format",
                "json",
            ]
        )
        == 0
    )
    refresh = json.loads(capsys.readouterr().out)
    assert refresh["fetch_mode"] == "issue-view"
    assert refresh["issue_refs"] == ["#103"]
    assert refresh["refreshed_items"][0]["id"] == "#103"
    assert "planning_candidate_suggestions" not in refresh
    assert "stale_planning_candidate_reconciliation" not in refresh
    assert not any(call[:3] == ["gh", "issue", "list"] for call in calls)

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(tmp_path),
                "--issue",
                "103",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )
    verbose_refresh = json.loads(capsys.readouterr().out)
    assert verbose_refresh["item_count"] == 1
    assert "planning_candidate_suggestions" in verbose_refresh

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #103",
                "--select",
                "issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    after = json.loads(capsys.readouterr().out)["values"]["issue_reference_intent"]
    assert after["status"] == "evidence-available"
    assert after["action_effect"]["blocked_until_reconciled"] == []


def test_github_pr_evidence_fetches_exact_declared_lane_refs_without_bulk_history(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import workspace_runtime_core as runtime_module

    lane_path = tmp_path / ".agentic-workspace/planning/lanes/old-pr.lane.json"
    _write(
        lane_path,
        json.dumps(
            {
                "children": [
                    {"id": "old", "pr_ref": "#42"},
                    {"id": "newer", "pr_ref": "PR #9001"},
                    {"id": "duplicate", "pr_ref": "#42"},
                    {"id": "none", "pr_ref": ""},
                ]
            }
        ),
    )
    calls: list[list[str]] = []

    def fake_gh_json(arguments, *, cwd):
        calls.append(arguments)
        assert arguments[:2] == ["pr", "view"]
        number = int(arguments[2])
        return {
            "number": number,
            "title": f"PR {number}",
            "state": "MERGED" if number == 42 else "CLOSED",
            "url": f"https://github.com/acme/project/pull/{number}",
            "updatedAt": "2026-07-14T10:00:00Z",
            "mergedAt": "2026-07-14T09:00:00Z" if number == 42 else None,
            "closedAt": "2026-07-14T09:00:00Z",
        }

    monkeypatch.setattr(runtime_module, "_run_gh_json", fake_gh_json)
    evidence = runtime_module._github_current_pull_request_evidence(target_root=tmp_path, repo="acme/project")

    assert [item["number"] for item in evidence] == [42, 9001]
    assert [item["state"] for item in evidence] == ["merged", "closed"]
    assert calls == [
        [
            "pr",
            "view",
            "42",
            "--repo",
            "acme/project",
            "--json",
            "number,title,state,url,updatedAt,mergedAt,closedAt",
        ],
        [
            "pr",
            "view",
            "9001",
            "--repo",
            "acme/project",
            "--json",
            "number,title,state,url,updatedAt,mergedAt,closedAt",
        ],
    ]
    assert all("list" not in call for call in calls)


def test_start_open_issue_intake_routes_refresh_and_grouping(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    evidence_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refreshed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "refresh_metadata": {"adapter": "fixture", "open_count": 4, "closed_count": 0},
                "items": [
                    {"id": "#1739", "system": "github", "status": "open", "kind": "lane", "title": "Dogfooding friction lane"},
                    {
                        "id": "#1804",
                        "system": "github",
                        "status": "open",
                        "kind": "slice",
                        "parent_id": "#1739",
                        "title": "Warn on unsupported lane status",
                    },
                    {
                        "id": "#1803",
                        "system": "github",
                        "status": "open",
                        "kind": "slice",
                        "parent_id": "#1739",
                        "title": "Repair affordances",
                    },
                    {"id": "#1802", "system": "github", "status": "open", "kind": "issue", "title": "Open issue intake"},
                ],
            }
        ),
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1739-dogfooding", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1739", title = "Dogfooding friction lane", promotion_signal = "Promote first.", suggested_first_slice = "Review child slices." },
  { id = "github-1802-open-issue-intake", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #1802", title = "Open issue intake", promotion_signal = "Promote when selected.", suggested_first_slice = "Add intake routing." },
]
""",
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Ingest and prioritise open issues",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["decision_packet"]["action"]["id"] == "refresh-open-issue-intake"

    assert cli.main(["start", "--target", str(tmp_path), "--select", "open_issue_intake", "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)
    selected_intake = selected["values"]["open_issue_intake"]
    assert selected.get("missing", []) == []
    assert selected_intake["trigger"] == "explicit-selector"
    assert selected_intake["status"] == "ready-to-review"
    assert "external-intent refresh-github" in selected_intake["command_owned_intake"]
    assert selected_intake["counts"]["open_issue_count"] == 4
    assert selected_intake["grouping_hints"]["parent_lanes"][0]["id"] == "#1739"
    assert "explicit open_issue_intake selector requested" in selected_intake["authority_boundary"]["observed_by_aw"]

    stale_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    stale_payload["refreshed_at"] = (datetime.now(timezone.utc) - timedelta(hours=25)).replace(microsecond=0).isoformat()
    evidence_path.write_text(json.dumps(stale_payload), encoding="utf-8")
    assert cli.main(["start", "--target", str(tmp_path), "--select", "open_issue_intake", "--format", "json"]) == 0
    stale_intake = json.loads(capsys.readouterr().out)["values"]["open_issue_intake"]
    assert stale_intake["freshness"]["status"] == "stale-refresh-recommended"
    assert stale_intake["recommended_next_action"] == "refresh-apply-intake"


def test_start_cached_issue_reference_intent_is_advisory(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    evidence_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "#103",
                        "system": "github",
                        "status": "open",
                        "kind": "issue",
                        "title": "Cached issue-backed intent",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #103",
                "--select",
                "issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    intent = payload["values"]["issue_reference_intent"]
    assert intent["status"] == "evidence-available"
    effect = intent["action_effect"]
    assert effect["force"] == "advisory"
    assert effect["allowed_now"] == "continue-with-cached-issue-intent"
    assert effect["blocked_until_reconciled"] == []
    assert effect["resolution_selector"] == "context.issue_reference_intent"
    assert effect["resolution_command"] == ""


def test_start_ambiguous_numeric_ref_stays_advisory_without_blocking_read_work(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Look at #103",
                "--select",
                "issue_reference_intent,planning_safety_gate,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]
    assert payload["next_safe_action"]["read_only_allowed"] is True
    assert payload["issue_reference_intent"]["status"] == "details-needed"
    assert payload["issue_reference_intent"]["action_effect"]["force"] == "required_before_claim"
    assert payload["planning_safety_gate"]["workflow_sufficient"] is True


def test_start_default_keeps_skill_catalog_breakdown_behind_command(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert "skills" not in payload
    assert "agentic-workspace skills" in payload["decision_packet"]["detail_routes"]["skills"]


def test_compact_skill_catalog_marks_malformed_payload_unavailable() -> None:
    catalog = workspace_runtime_primitives._compact_startup_skill_catalog_summary({"skills": "bad", "warnings": "bad"})

    assert catalog["available"] is False
    assert catalog["catalog_command_available"] is True
    assert catalog["total_count"] == 0
    assert catalog["warning_count"] == 0


def test_start_required_skill_projection_survives_compact_catalog(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    mark_configuration_readiness_current(tmp_path)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #1680 lane",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision_packet"]["action"]["skill"] == "planning-reporting"
    assert payload["decision_packet"]["action"]["skill_route"] == {
        "id": "planning-reporting",
        "path": ".agentic-workspace/planning/skills/planning-reporting/SKILL.md",
        "owner": "agentic-planning",
        "module": "planning",
    }
    assert "agentic-workspace skills" in payload["decision_packet"]["detail_routes"]["skills"]


def test_start_surfaces_transport_auto_without_binding_best_fit(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                'execution_role = "ordinary-executor"',
                'assignment_policy = "local-preferred"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
            ]
        ),
        encoding="utf-8",
    )
    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0
    config_payload = json.loads(capsys.readouterr().out)
    assert config_payload["mixed_agent"]["effective_orchestration"]["status"] == "transport-auto-local-assignment"

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix a typo", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "effective_orchestration" in payload, payload.keys()
    posture = payload["effective_orchestration"]
    assert posture["status"] == "transport-auto-local-assignment"
    assert "binding best-fit orchestration is not enabled" in posture["summary"]
    assert posture["assignment"] == {
        "execution_role": "ordinary-executor",
        "policy": "local-preferred",
        "authority": "local",
    }


def test_start_select_surfaces_memory_decision_packet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--select",
                "memory_decision_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    packet = payload["values"]["memory_decision_packet"]

    assert packet["kind"] == "agentic-workspace/memory-decision-packet/v1"
    assert packet["stage"] == "startup"
    assert packet["pull"]["status"] in {"not_checked", "baseline_only"}
    assert "memory route" in packet["pull"]["recommended_command"]
    assert "--stage startup" in packet["pull"]["recommended_command"]
    assert packet["authority_boundary"]["agent_owns"]
    assert "No keyword-triggered Memory requirement." in packet["limits"]


def test_known_task_path_routes_relevant_durable_context_into_ordinary_decision(tmp_path: Path, capsys) -> None:
    fixture = Path("tools/model-cli-harness/fixtures/aw-memory-host-repo")
    shutil.copytree(fixture, tmp_path, dirs_exist_ok=True)
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Make one small edit to README.md so a new contributor can run the tests.",
                "--format",
                "json",
            ]
        )
        == 0
    )
    started = json.loads(capsys.readouterr().out)
    assert "implement --changed README.md" in started["decision_packet"]["action"]["command"]

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Make one small edit to README.md so a new contributor can run the tests.",
                "--format",
                "json",
            ]
        )
        == 0
    )
    decision = json.loads(capsys.readouterr().out)["decision_packet"]
    assert decision["action"]["read_first"] == [".agentic-workspace/memory/repo/testing-and-packaging.md"]
    assert decision["attention"][0]["signal"] == "relevant durable context matched the working set"


def test_ordinary_decision_stays_quiet_without_route_matched_durable_context(tmp_path: Path, capsys) -> None:
    fixture = Path("tools/model-cli-harness/fixtures/aw-minimal-host-repo")
    shutil.copytree(fixture, tmp_path, dirs_exist_ok=True)
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Make one small edit to README.md.",
                "--format",
                "json",
            ]
        )
        == 0
    )
    decision = json.loads(capsys.readouterr().out)["decision_packet"]
    assert "read_first" not in decision["action"]
    assert not any(item.get("signal") == "relevant durable context matched the working set" for item in decision.get("attention", []))


def test_start_select_surfaces_installed_state_compatibility(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    compatibility = payload["values"]["installed_state_compatibility"]

    assert compatibility["kind"] == "agentic-workspace/installed-state-compatibility/v1"
    assert compatibility["authority"] == "repo-state-authoritative"
    assert compatibility["executable"]["classification"]
    assert compatibility["payload"]["status"]
    assert compatibility["status"] == "compatible"
    assert compatibility["action_effect"]["force"] == "advisory"
    assert compatibility["action_effect"]["allowed_now"] == "continue-ordinary-work"
    assert compatibility["action_effect"]["blocked_until_reconciled"] == []
    assert (
        compatibility["action_effect"]["claim_boundary"]
        == "installed-state-compatible-does-not-replace-task-proof-or-acceptance-reconciliation"
    )


def test_report_release_recovery_section_exposes_payload_and_semver_recovery_routes(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(
        cli,
        "_release_recovery_live_state",
        lambda **kwargs: {
            "release_ci_failure": {
                "kind": "agentic-workspace/release-ci-failure-summary/v1",
                "status": "failed-release-run",
                "workflow": "Release",
                "run_url": "https://github.com/example/repo/actions/runs/1",
                "failed_job": "release",
                "failed_step": "Run proof",
                "error_summary": ["ERROR release proof failed"],
                "freshness": {"status": "active_failed_release"},
            },
            "release_publication_state": {
                "status": "failed-release-unpublished",
                "failed_run_url": "https://github.com/example/repo/actions/runs/1",
                "publisher_retry": {
                    "status": "ready",
                    "command": 'gh workflow run release.yml --ref master -f tag="v0.34.1" -f source_commit="abc123"',
                },
            },
        },
    )

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(repo_root),
                "--section",
                "release_recovery",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    recovery = payload["answer"]

    assert recovery["kind"] == "agentic-workspace/release-recovery/v1"
    assert recovery["release_model"] == "coordinated-workspace"
    assert recovery["semver_release_action"]["status"] == "not-fetched"
    assert recovery["release_ci_failure"]["status"] == "failed-release-run"
    assert recovery["release_ci_failure"]["failed_step"] == "Run proof"
    assert recovery["release_publication_state"]["status"] == "failed-release-unpublished"
    assert recovery["release_publication_state"]["publisher_retry"]["status"] == "ready"
    assert "release_recovery_status.py" in recovery["semver_release_action"]["command"]
    assert "repair_route" in recovery["payload_drift"]
    assert recovery["coordinated_recovery"]["status"] == "required"
    assert "required_version_paths" in recovery["coordinated_recovery"]["pr_shape"]


def test_report_release_recovery_requires_unresolved_publication_state(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(
        cli,
        "_release_recovery_live_state",
        lambda **kwargs: {
            "release_ci_failure": {
                "kind": "agentic-workspace/release-ci-failure-summary/v1",
                "status": "no-failed-release-run",
                "workflow": "Release",
                "latest_run": {
                    "run_id": "29765337976",
                    "run_url": "https://github.com/example/repo/actions/runs/29765337976",
                    "conclusion": "success",
                },
                "freshness": {"status": "clear", "source": "gh-run-list"},
            },
            "release_publication_state": {
                "status": "unresolved-version-publication-debt",
                "publication": {
                    "kind": "agentic-workspace/release-publication-state/v1",
                    "status": "unresolved-version-publication-debt",
                    "recovery_required": True,
                    "reason": "version-not-newer-than-existing-tag-floor-v0.34.0",
                },
            },
        },
    )

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(repo_root),
                "--section",
                "release_recovery",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    recovery = payload["answer"]

    assert recovery["release_ci_failure"]["status"] == "no-failed-release-run"
    assert recovery["release_publication_state"]["status"] == "unresolved-version-publication-debt"
    assert recovery["coordinated_recovery"]["status"] == "required"
    assert "successful no-op workflow runs do not clear" in recovery["coordinated_recovery"]["next_action"]


@pytest.mark.parametrize("status", ["publication-observation-failed", "github-release-unpublished"])
def test_report_release_recovery_requires_fail_closed_publication_state(monkeypatch: pytest.MonkeyPatch, capsys, status: str) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(
        cli,
        "_release_recovery_live_state",
        lambda **kwargs: {
            "release_ci_failure": {"status": "no-failed-release-run", "workflow": "Release"},
            "release_publication_state": {
                "status": status,
                "publication": {"status": status, "recovery_required": True},
            },
        },
    )

    assert cli.main(["report", "--target", str(repo_root), "--section", "release_recovery", "--format", "json"]) == 0
    recovery = json.loads(capsys.readouterr().out)["answer"]

    assert recovery["release_publication_state"]["status"] == status
    assert recovery["coordinated_recovery"]["status"] == "required"


def test_start_surfaces_pr_comment_attention_only_for_pr_context(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--format", "json"]) == 0
    quiet_payload = json.loads(capsys.readouterr().out)
    assert "pr_comment_attention" not in {item["detail_selector"] for item in quiet_payload["decision_packet"].get("attention", [])}

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue PR #1831 review fixes",
                "--select",
                "pr_comment_attention,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    attention = payload["pr_comment_attention"]
    assert attention["status"] == "pr_comment_status_unavailable"
    assert attention["comment_state"] == "cache_miss"
    assert attention["pr_number"] == "1831"
    assert "pr_comment_delta.py" in attention["recommended_command"]
    assert "--pr 1831" in attention["recommended_command"]
    assert "report --target . --section pr_comment_attention --format json" in attention["cache_selector_command"]
    assert attention["live_inspection"]["status"] == "live_inspection_available"
    assert attention["pr_resolution"]["status"] == "known"
    assert attention["write_safety"]["github_writes_performed"] is False
    assert attention["absence_states"]["thread_level_comments"] == "hidden_behind_detail_route"
    assert "pr_comment_delta.py" in attention["detail_route"]


def test_report_pr_comment_attention_cache_miss_routes_to_live_inspection_for_branch_pr(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    branch = "codex/2030-proof-receipt-bridge-actions"
    monkeypatch.setattr(cli, "_current_git_branch", lambda target_root: branch)
    monkeypatch.setattr(cli, "_github_repo_from_origin", lambda target_root: "rickardvh/agentic-workspace")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "pr_comment_attention", "--format", "json"]) == 0

    attention = json.loads(capsys.readouterr().out)["answer"]
    assert attention["status"] == "pr_comment_status_unavailable"
    assert attention["comment_state"] == "cache_miss"
    assert attention["repository"] == "rickardvh/agentic-workspace"
    assert attention["branch"] == branch
    assert attention["pr_number"] == ""
    assert "scripts/github/pr_topology.py" in attention["recommended_command"]
    assert '--branch "codex/2030-proof-receipt-bridge-actions"' in attention["recommended_command"]
    assert "report --target . --section pr_comment_attention --format json" in attention["cache_selector_command"]
    assert attention["live_inspection"]["status"] == "pr_resolution_required"
    assert attention["live_inspection"]["recommended_command"] == attention["recommended_command"]
    assert attention["live_inspection"]["connector_route"].endswith("#<resolved-pr-number>")
    assert attention["pr_resolution"]["status"] == "required"
    assert attention["pr_resolution"]["command"] == attention["recommended_command"]
    assert "gh pr list" in attention["pr_resolution"]["provider_probe_command"]
    assert attention["write_safety"]["github_writes_performed"] is False
    assert "resolve_thread" in attention["write_safety"]["forbidden_actions_without_user_request"]
    assert attention["comment_addressing"]["status"] == "review_comment_evidence_unavailable"
    assert attention["comment_addressing"]["write_safety"]["github_writes_performed"] is False
    assert "Thread-level PR comment state is unverified." in attention["unverified_context"]

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Address review comments on this PR",
                "--select",
                "pr_comment_attention",
                "--format",
                "json",
            ]
        )
        == 0
    )
    start_attention = json.loads(capsys.readouterr().out)["values"]["pr_comment_attention"]
    assert start_attention["comment_state"] == "cache_miss"
    assert start_attention["recommended_command"] == attention["recommended_command"]
    assert start_attention["live_inspection"]["status"] == "pr_resolution_required"
    assert start_attention["pr_resolution"]["status"] == "required"
    assert start_attention["write_safety"]["github_writes_performed"] is False


def test_report_pr_comment_attention_reads_cached_actionable_and_empty_deltas(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "pr-comment-delta.json"
    cache_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/pr-comment-delta/v1",
                "repository": "rickardvh/agentic-workspace",
                "pr_number": 1831,
                "pr_url": "https://github.com/rickardvh/agentic-workspace/pull/1831",
                "new_comment_count": 1,
                "category_counts": {
                    "actionable_code_doc_body_change": 1,
                    "pr_metadata_body_only_change": 0,
                    "ci_label_only_issue": 0,
                    "ambiguous_needs_human": 1,
                    "informational_no_local_change": 2,
                },
                "items": [
                    {
                        "kind": "review_thread_comment",
                        "category": "actionable_code_doc_body_change",
                        "path": "src/app.py",
                        "line": 12,
                        "url": "https://example.test/pr#thread",
                        "proof_hint": "Run focused tests.",
                    },
                    {
                        "kind": "issue_comment",
                        "category": "ambiguous_needs_human",
                        "url": "https://example.test/pr#question",
                        "body_excerpt": "Which behavior should win here?",
                        "proof_hint": "Ask or draft a response before editing.",
                    },
                    {
                        "kind": "review_thread_comment",
                        "category": "informational_no_local_change",
                        "path": "README.md",
                        "url": "https://example.test/pr#resolved",
                        "is_resolved": True,
                        "proof_hint": "No local proof unless the thread is reopened.",
                    },
                    {
                        "kind": "review_thread_comment",
                        "category": "informational_no_local_change",
                        "path": "docs/old.md",
                        "url": "https://example.test/pr#outdated",
                        "is_outdated": True,
                        "proof_hint": "No local proof unless the thread is reopened.",
                    },
                ],
                "baseline": {"since": "2026-06-28T00:00:00Z"},
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "pr_comment_attention", "--format", "json"]) == 0
    actionable = json.loads(capsys.readouterr().out)["answer"]
    assert actionable["status"] == "actionable_pr_comments_present"
    assert actionable["comment_state"] == "comments_requiring_action"
    assert actionable["actionable_count"] == 2
    assert actionable["sample"][0]["path"] == "src/app.py"
    assert actionable["thread_inspection"]["status"] == "available"
    assert "report --target . --section pr_comment_attention --format json" in actionable["recommended_command"]
    assert "pr_comment_delta.py" in actionable["thread_inspection"]["source_checkout_helper"]["command"]
    addressing = actionable["comment_addressing"]
    assert addressing["kind"] == "agentic-workspace/pr-comment-addressing/v1"
    assert addressing["status"] == "unresolved_review_feedback_present"
    assert addressing["bucket_counts"] == {
        "unresolved_action": 1,
        "reply_only": 1,
        "already_addressed": 1,
        "outdated": 1,
        "informational": 0,
    }
    assert addressing["buckets"]["unresolved_action"][0]["path"] == "src/app.py"
    assert addressing["buckets"]["reply_only"][0]["url"].endswith("#question")
    assert addressing["source_availability"]["inspected_surfaces"] == ["cached_delta_items"]
    assert addressing["source_availability"]["unavailable_surfaces"] == ["thread_surface_completeness"]
    assert addressing["closeout"]["addressed_comments"][0]["url"].endswith("#resolved")
    assert addressing["closeout"]["outdated_comments"][0]["url"].endswith("#outdated")
    assert [item["url"] for item in addressing["closeout"]["intentionally_open_comments"]] == [
        "https://example.test/pr#thread",
        "https://example.test/pr#question",
    ]
    assert addressing["write_safety"]["github_writes_performed"] is False

    # Legacy empty caches are not enough to support readiness claims because they
    # do not prove which PR head was observed.
    cache_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/pr-comment-delta/v1",
                "repository": "rickardvh/agentic-workspace",
                "pr_number": 1831,
                "new_comment_count": 0,
                "category_counts": {
                    "actionable_code_doc_body_change": 0,
                    "pr_metadata_body_only_change": 0,
                    "ci_label_only_issue": 0,
                    "ambiguous_needs_human": 0,
                    "informational_no_local_change": 0,
                },
                "items": [],
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "pr_comment_attention", "--format", "json"]) == 0
    stale_empty = json.loads(capsys.readouterr().out)["answer"]
    assert stale_empty["status"] == "pr_comment_status_unavailable"
    assert stale_empty["comment_state"] == "stale_or_unknown"
    assert stale_empty["cached_status"] == "no_actionable_pr_comments_detected"
    assert stale_empty["degraded_explicitly"] is True
    assert stale_empty["comment_addressing"]["status"] == "stale_or_unverified"
    assert stale_empty["comment_addressing"]["closeout"]["status"] == "blocked_until_refreshed"
    assert "Current PR head is unverified." in stale_empty["unverified_context"]

    cache_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/pr-comment-delta/v1",
                "repository": "rickardvh/agentic-workspace",
                "pr_number": 1831,
                "new_comment_count": 0,
                "category_counts": {
                    "actionable_code_doc_body_change": 0,
                    "pr_metadata_body_only_change": 0,
                    "ci_label_only_issue": 0,
                    "ambiguous_needs_human": 0,
                    "informational_no_local_change": 0,
                },
                "items": [],
                "freshness": {
                    "status": "current_at_observed_head",
                    "pr_head_sha": "abc123",
                    "observed_at": "2026-06-28T00:00:00Z",
                },
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "pr_comment_attention", "--format", "json"]) == 0
    fresh_empty = json.loads(capsys.readouterr().out)["answer"]
    assert fresh_empty["status"] == "no_actionable_pr_comments_detected"
    assert fresh_empty["comment_state"] == "no_comments_requiring_action"
    assert fresh_empty["actionable_count"] == 0
    assert fresh_empty["freshness"]["pr_head_sha"] == "abc123"
    assert fresh_empty["comment_addressing"]["status"] == "review_feedback_closed"
    assert fresh_empty["comment_addressing"]["closeout"]["status"] == "ready_if_fresh"
    assert fresh_empty["unverified_context"] == []


def _init_committed_pr_topology_repo(target: Path, *, branch: str) -> str:
    subprocess.run(["git", "init", "-q"], cwd=target, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=target, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=target, check=True, capture_output=True)
    _write(target / "README.md", "fixture\n")
    subprocess.run(["git", "add", "README.md"], cwd=target, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=target, check=True, capture_output=True)
    subprocess.run(["git", "switch", "-q", "-c", branch], cwd=target, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/example/project.git"],
        cwd=target,
        check=True,
        capture_output=True,
    )
    return _git_value(target, "rev-parse", "HEAD")


def test_live_pr_topology_admission_populates_continuity_without_claiming_thread_freshness(tmp_path: Path, capsys) -> None:
    head_sha = _init_committed_pr_topology_repo(tmp_path, branch="codex/live-topology")
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue the current stacked PR",
                "--select",
                "pr_comment_attention",
                "--format",
                "json",
            ]
        )
        == 0
    )
    unavailable = json.loads(capsys.readouterr().out)["values"]["pr_comment_attention"]
    assert unavailable["absence_states"]["stack_membership"] == "unavailable"
    assert "scripts/github/pr_topology.py" in unavailable["pr_resolution"]["command"]

    provider_fixture = tmp_path / "github-prs.json"
    _write(
        provider_fixture,
        json.dumps(
            [
                {
                    "number": 41,
                    "state": "OPEN",
                    "headRefName": "codex/foundation",
                    "baseRefName": "main",
                    "headRefOid": "a" * 40,
                },
                {
                    "number": 42,
                    "state": "OPEN",
                    "headRefName": "codex/live-topology",
                    "baseRefName": "codex/foundation",
                    "headRefOid": head_sha,
                },
            ]
        ),
    )
    adapter = subprocess.run(
        [
            sys.executable,
            "scripts/github/pr_topology.py",
            "--repo",
            "example/project",
            "--branch",
            "codex/live-topology",
            "--target",
            str(tmp_path),
            "--input",
            str(provider_fixture),
            "--format",
            "json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert adapter.returncode == 0, adapter.stderr
    admitted = json.loads(adapter.stdout)
    assert admitted["status"] == "admitted"
    assert admitted["dependency_order"] == ["41", "42"]
    assert admitted["thread_comment_state"] == "unverified"
    full_attention = workspace_runtime_core._pr_comment_attention_payload(
        target_root=tmp_path,
        task_text="Continue the current stacked PR",
        cli_invoke="agentic-workspace",
    )
    assert full_attention["stack"]["stack_members"][1]["comment_addressing"]["status"] == "review_comment_evidence_unavailable"

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue the current stacked PR",
                "--select",
                "pr_comment_attention",
                "--format",
                "json",
            ]
        )
        == 0
    )
    attention = json.loads(capsys.readouterr().out)["values"]["pr_comment_attention"]
    assert attention["status"] == "stack_comment_status_unavailable"
    assert attention["stack_discovery"]["status"] == "admitted-live-topology"
    assert attention["absence_states"] == {
        "stack_membership": "known",
        "thread_level_comments": "hidden_behind_detail_route",
    }
    continuity = attention["review_stack_continuity"]
    assert continuity["current_pr_number"] == "42"
    assert [item["pr_number"] for item in continuity["dependency_order"]] == ["41", "42"]
    assert continuity["phase"] == "review-state-refresh"
    assert continuity["closeout_route"]["status"] == "blocked"


def test_pr_topology_admission_rejects_mismatched_ambiguous_and_stale_observations(tmp_path: Path) -> None:
    from agentic_workspace.review_stack_topology import TopologyAdmissionError, admit_pr_topology_observation

    head_sha = _init_committed_pr_topology_repo(tmp_path, branch="codex/live-topology")
    member = {
        "pr_number": 42,
        "pr_state": "open",
        "branch": "codex/live-topology",
        "base_branch": "main",
        "head_sha": head_sha,
    }
    observations = [
        {"repository": "other/project", "branch": "codex/live-topology", "head_sha": head_sha, "members": [member]},
        {"repository": "example/project", "branch": "codex/other", "head_sha": head_sha, "members": [member]},
        {"repository": "example/project", "branch": "codex/live-topology", "head_sha": "b" * 40, "members": [member]},
        {
            "repository": "example/project",
            "branch": "codex/live-topology",
            "head_sha": head_sha,
            "members": [{**member, "pr_state": "closed"}],
        },
        {
            "repository": "example/project",
            "branch": "codex/live-topology",
            "head_sha": head_sha,
            "members": [member, {**member, "pr_number": 43}],
        },
        {
            "repository": "example/project",
            "branch": "codex/live-topology",
            "head_sha": head_sha,
            "members": [{**member, "head_sha": "c" * 40}],
        },
        {
            "repository": "example/project",
            "branch": "codex/live-topology",
            "head_sha": head_sha,
            "members": [{key: value for key, value in member.items() if key != "base_branch"}],
        },
        {
            "repository": "example/project",
            "branch": "codex/live-topology",
            "head_sha": head_sha,
            "members": [
                member,
                {
                    "pr_number": 43,
                    "branch": "codex/disconnected",
                    "base_branch": "main",
                    "head_sha": "d" * 40,
                },
            ],
        },
    ]
    for observation in observations:
        with pytest.raises(TopologyAdmissionError):
            admit_pr_topology_observation(
                target_root=tmp_path,
                observation=observation,
                expected_repository="example/project",
                expected_branch="codex/live-topology",
            )
    assert not (tmp_path / ".agentic-workspace/local/cache/pr-comment-stack.json").exists()


def test_github_pr_topology_adapter_selects_only_the_current_linear_stack() -> None:
    from scripts.github.pr_topology import github_topology_observation

    from agentic_workspace.review_stack_topology import TopologyAdmissionError

    pull_requests = [
        {"number": 41, "state": "OPEN", "headRefName": "codex/foundation", "baseRefName": "main", "headRefOid": "a" * 40},
        {
            "number": 40,
            "state": "CLOSED",
            "headRefName": "codex/foundation",
            "baseRefName": "main",
            "headRefOid": "z" * 40,
        },
        {
            "number": 42,
            "state": "OPEN",
            "headRefName": "codex/live-topology",
            "baseRefName": "codex/foundation",
            "headRefOid": "b" * 40,
        },
        {
            "number": 43,
            "state": "MERGED",
            "headRefName": "codex/live-topology",
            "baseRefName": "codex/foundation",
            "headRefOid": "d" * 40,
        },
        {"number": 99, "state": "OPEN", "headRefName": "codex/unrelated", "baseRefName": "main", "headRefOid": "c" * 40},
    ]
    observation = github_topology_observation(
        repository="example/project",
        branch="codex/live-topology",
        head_sha="b" * 40,
        pull_requests=pull_requests,
    )
    assert [member["number"] for member in observation["members"]] == [41, 42]
    assert observation["provider"] == "github-gh-read-only"

    with pytest.raises(TopologyAdmissionError, match="no open pull request"):
        github_topology_observation(
            repository="example/project",
            branch="codex/missing",
            head_sha="d" * 40,
            pull_requests=pull_requests,
        )
    with pytest.raises(TopologyAdmissionError, match="no open pull request"):
        github_topology_observation(
            repository="example/project",
            branch="codex/closed-only",
            head_sha="d" * 40,
            pull_requests=[
                *pull_requests,
                {
                    "number": 44,
                    "state": "CLOSED",
                    "headRefName": "codex/closed-only",
                    "baseRefName": "main",
                    "headRefOid": "d" * 40,
                },
            ],
        )
    with pytest.raises(TopologyAdmissionError, match="multiple open pull requests"):
        github_topology_observation(
            repository="example/project",
            branch="codex/live-topology",
            head_sha="b" * 40,
            pull_requests=[*pull_requests, dict(pull_requests[2])],
        )


def test_github_pr_topology_adapter_fails_closed_when_provider_is_unavailable(monkeypatch) -> None:
    from scripts.github import pr_topology

    def unavailable(*args, **kwargs):
        raise OSError("gh unavailable")

    monkeypatch.setattr(pr_topology.subprocess, "run", unavailable)
    with pytest.raises(pr_topology.TopologyAdmissionError, match="provider is unavailable"):
        pr_topology._github_pull_requests(repository="example/project")


def test_github_pr_topology_adapter_fails_closed_for_provider_errors_and_incomplete_records(monkeypatch) -> None:
    from scripts.github import pr_topology

    monkeypatch.setattr(
        pr_topology.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="unauthorized"),
    )
    with pytest.raises(pr_topology.TopologyAdmissionError, match="provider read failed"):
        pr_topology._github_pull_requests(repository="example/project")

    with pytest.raises(pr_topology.TopologyAdmissionError, match="incomplete PR record"):
        pr_topology.github_topology_observation(
            repository="example/project",
            branch="codex/live-topology",
            head_sha="a" * 40,
            pull_requests=[
                {
                    "number": 42,
                    "state": "OPEN",
                    "headRefName": "codex/live-topology",
                    "baseRefName": "main",
                }
            ],
        )


def test_admitted_pr_topology_is_rejected_after_head_changes(tmp_path: Path, capsys) -> None:
    from agentic_workspace.review_stack_topology import admit_pr_topology_observation

    head_sha = _init_committed_pr_topology_repo(tmp_path, branch="codex/live-topology")
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    admit_pr_topology_observation(
        target_root=tmp_path,
        expected_repository="example/project",
        expected_branch="codex/live-topology",
        observation={
            "repository": "example/project",
            "branch": "codex/live-topology",
            "head_sha": head_sha,
            "members": [
                {
                    "pr_number": 42,
                    "pr_state": "open",
                    "branch": "codex/live-topology",
                    "base_branch": "main",
                    "head_sha": head_sha,
                }
            ],
        },
    )
    _write(tmp_path / "head-change.txt", "changed\n")
    subprocess.run(["git", "add", "head-change.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "head change"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue the current stacked PR",
                "--select",
                "pr_comment_attention",
                "--format",
                "json",
            ]
        )
        == 0
    )
    attention = json.loads(capsys.readouterr().out)["values"]["pr_comment_attention"]
    assert attention["stack_member_count"] == 0
    assert attention["stack_discovery"]["status"] == "rejected"
    assert attention["stack_discovery"]["reason"] == "topology-head-stale"
    assert attention["absence_states"]["stack_membership"] == "unavailable"


def test_unrelated_startup_does_not_execute_live_pr_provider(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    real_run = subprocess.run
    observed_commands: list[list[str]] = []

    def guarded_run(command, *args, **kwargs):
        if isinstance(command, list):
            observed_commands.append([str(item) for item in command])
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(workspace_runtime_core.subprocess, "run", guarded_run)
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one local typo", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "pr_comment_attention" not in {item["detail_selector"] for item in payload["decision_packet"].get("attention", [])}
    assert not any(command and command[0] == "gh" for command in observed_commands)


def test_start_pr_comment_attention_reads_stack_cache_with_concrete_refresh_commands(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace import review_stack_topology, review_stack_transitions

    _init_real_git_repo_with_commit(tmp_path)
    subprocess.run(["git", "branch", "codex/stack-comments"], cwd=tmp_path, check=True, capture_output=True)
    _set_git_branch(tmp_path, current="codex/stack-comments", default="main")
    monkeypatch.setattr(review_stack_topology, "current_git_head_sha", lambda _target_root: "bbb222")
    monkeypatch.setattr(workspace_runtime_core, "_current_git_branch", lambda _target_root: "codex/stack-comments")
    monkeypatch.setattr(workspace_runtime_core, "_github_repo_from_origin", lambda _target_root: "rickardvh/agentic-workspace")
    monkeypatch.setattr(review_stack_transitions, "_current_branch", lambda _target_root: "codex/stack-comments")
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "planning",
                "new-plan",
                "--id",
                "stack-review-plan",
                "--title",
                "Stack review plan",
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
    review_owner_identity = review_stack_topology.current_review_owner_identity(tmp_path)
    assert review_owner_identity is not None
    monkeypatch.setattr(
        review_stack_transitions,
        "current_provider_pr_identity",
        lambda **_kwargs: {
            "pr_number": "1841",
            "pr_state": "open",
            "branch": "codex/stack-comments",
            "head_sha": "bbb222",
        },
    )
    monkeypatch.setattr(
        review_stack_transitions,
        "current_review_owner_identity",
        lambda _target_root: review_owner_identity,
    )
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "pr-comment-stack.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    changed_path = tmp_path / "src" / "app.py"
    changed_path.parent.mkdir(parents=True, exist_ok=True)
    changed_path.write_text("VALUE = 1\n", encoding="utf-8")
    test_path = tmp_path / "tests" / "test_app.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text("def test_app():\n    assert True\n", encoding="utf-8")
    proof_reuse_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "proof-reuse.json"
    assignment_context = tmp_path / ".agentic-workspace" / "local" / "assignment-context.json"
    assignment_context.parent.mkdir(parents=True, exist_ok=True)
    assignment_context.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/assignment-context/v1",
                "status": "current",
                "revision": "assign-review-stack-1",
                "target_context": {
                    "delegation_target": "fast_worker",
                    "task_class": "mechanical-follow-through",
                    "scope_class": "narrow-code-change",
                },
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--select",
                "pr_comment_attention,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    unavailable = json.loads(capsys.readouterr().out)["values"]
    unavailable_attention = unavailable["pr_comment_attention"]
    assert unavailable_attention["status"] == "stack_comment_status_unavailable"
    assert unavailable_attention["comment_state"] == "stack_discovery_unavailable"
    assert unavailable_attention["absence_states"]["stack_membership"] == "unavailable"
    assert unavailable_attention["stack_member_count"] == 0
    assert unavailable_attention["absence_states"]["thread_level_comments"] == "hidden_behind_detail_route"

    current_head = "bbb222"
    stack_members = [
        {
            "pr_number": 1840,
            "pr_state": "open",
            "branch": "codex/proof-reuse",
            "base_branch": "main",
            "head_sha": "aaa111",
            "delta": {
                "category_counts": {
                    "actionable_code_doc_body_change": 0,
                    "pr_metadata_body_only_change": 0,
                    "ci_label_only_issue": 0,
                    "ambiguous_needs_human": 0,
                },
                "freshness": {"status": "current_at_observed_head", "pr_head_sha": "aaa111"},
            },
        },
        {
            "pr_number": 1841,
            "pr_state": "open",
            "branch": "codex/stack-comments",
            "base_branch": "codex/proof-reuse",
            "head_sha": current_head,
            "changed_paths": ["src/app.py", "tests/test_app.py"],
            "proof_hints": ["Run changed-effect proof."],
            "delta": {
                "category_counts": {
                    "actionable_code_doc_body_change": 0,
                    "pr_metadata_body_only_change": 0,
                    "ci_label_only_issue": 0,
                    "ambiguous_needs_human": 0,
                },
                "freshness": {"status": "current_at_observed_head", "pr_head_sha": current_head},
            },
        },
    ]
    topology_observation = {
        "kind": "agentic-workspace/pr-topology-observation/v1",
        "status": "admitted",
        "provider": "fixture",
        "repository": "rickardvh/agentic-workspace",
        "current_branch": "codex/stack-comments",
        "current_head_sha": current_head,
        "current_pr_number": "1841",
        "current_pr_state": "open",
        "review_owner_identity": review_owner_identity,
        "members": copy.deepcopy(stack_members),
    }
    topology_observation["observation_digest"] = review_stack_topology._observation_digest(topology_observation)
    fresh_stack = {
        "kind": "agentic-workspace/pr-comment-stack/v2",
        "repository": "rickardvh/agentic-workspace",
        "topology_observation": topology_observation,
        "stack_members": stack_members,
    }
    cache_path.write_text(json.dumps(fresh_stack), encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--select",
                "pr_comment_attention,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    current = json.loads(capsys.readouterr().out)["values"]
    assert current["pr_comment_attention"]["status"] == "stack_comments_current"
    assert current["pr_comment_attention"]["comment_state"] == "stack_current_no_actionable_comments"
    assert current["pr_comment_attention"]["pr_number"] == "1841"
    assert current["pr_comment_attention"]["stack_member_count"] == 2
    assert current["pr_comment_attention"]["absence_states"]["thread_level_comments"] == "hidden_behind_detail_route"
    current_continuity = current["pr_comment_attention"]["review_stack_continuity"]
    assert current_continuity["phase"] == "review-proof"
    assert current_continuity["current_pr_number"] == "1841"
    assert [member["pr_number"] for member in current_continuity["dependency_order"]] == ["1840", "1841"]
    assert current_continuity["affected_slice"]["pr_number"] == "1841"
    assert current_continuity["affected_slice"]["paths"] == ["src/app.py", "tests/test_app.py"]
    assert current_continuity["incremental_proof_manifest"]["status"] == "focused_proof_required"
    assert current_continuity["incremental_proof_manifest"]["path_source"] == "stack_member_changed_effect_paths"
    assert current_continuity["next_action"]["id"] == "run-focused-proof"
    assert "proof --changed src/app.py tests/test_app.py --format json" in current_continuity["next_action"]["command"]

    actionable_for_transition = copy.deepcopy(fresh_stack)
    actionable_for_transition["stack_members"][1]["delta"]["category_counts"]["actionable_code_doc_body_change"] = 1
    actionable_for_transition["stack_members"][1]["delta"]["items"] = [
        {
            "kind": "review_thread_comment",
            "category": "actionable_code_doc_body_change",
            "path": "src/app.py",
            "proof_hint": "Run changed-effect proof.",
        }
    ]
    cache_path.write_text(json.dumps(actionable_for_transition), encoding="utf-8")
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/app.py",
                "tests/test_app.py",
                "--task",
                "Stack review plan",
                "--format",
                "json",
            ]
        )
        == 0
    )
    implement_decision = json.loads(capsys.readouterr().out)["decision_packet"]
    derived = implement_decision["effects"]["derived"]
    assert derived["phase"] == "pre-mutation-admission"
    assert derived["status"] == "applied"
    assert derived["effects"][0]["owner"] == "review-stack.lifecycle"
    assert derived["effects"][0]["persistence"] == "repository-persistent"
    assert derived["effects"][0]["decision"] == "allow"
    assert derived["actual_written_paths"] == [derived["effects"][0]["path"]]
    correction = implement_decision["transition"]
    assert correction["status"] == "written"
    assert correction["phase_after"] == "review-proof"
    admissions = correction["calibration_admissions"]
    assert [item["producer_class"] for item in admissions] == ["human-review", "retry-outcome"]
    assert [item["status"] for item in admissions] == ["recorded", "recorded"]
    human_review_ref = admissions[0]["source_ref"]
    retry_ref = admissions[1]["source_ref"]
    human_review_receipt_id = human_review_ref.rsplit("/", 1)[-1]
    retry_receipt_id = retry_ref.rsplit("/", 1)[-1]
    human_review_receipt = json.loads(
        (tmp_path / ".agentic-workspace" / "reviews" / "receipts" / f"{human_review_receipt_id}.json").read_text(encoding="utf-8")
    )
    retry_receipt = json.loads(
        (tmp_path / ".agentic-workspace" / "local" / "retry-receipts" / f"{retry_receipt_id}.json").read_text(encoding="utf-8")
    )
    assert (
        human_review_receipt["target_context"]
        == retry_receipt["target_context"]
        == {
            "delegation_target": "fast_worker",
            "task_class": "mechanical-follow-through",
            "scope_class": "narrow-code-change",
        }
    )
    assert human_review_receipt["authority"] == "human-review"
    assert human_review_receipt["result"] == "changes-requested"
    assert retry_receipt["authority"] == "local-outcome-ledger"
    assert retry_receipt["result"] == "passed"

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/app.py",
                "tests/test_app.py",
                "--record-receipt",
                "--receipt-command",
                "uv run pytest tests/test_app.py -q",
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["review_stack_transition"]["status"] == "updated"
    assert receipt["review_stack_transition"]["phase_after"] == "review-closeout-ready"
    assert receipt["review_stack_transition"]["proof_receipt_path"] == ".agentic-workspace/local/proof-receipts/last.json"
    assert receipt["proof_reuse_cache"]["status"] == "written"
    assert receipt["proof_reuse_cache"]["path"] == ".agentic-workspace/local/cache/proof-reuse.json"
    proof_reuse = json.loads(proof_reuse_path.read_text(encoding="utf-8"))
    assert proof_reuse["source"] == "proof --record-receipt"
    assert proof_reuse["path_fingerprints"] == {
        "src/app.py": hashlib.sha256(changed_path.read_bytes()).hexdigest(),
        "tests/test_app.py": hashlib.sha256(test_path.read_bytes()).hexdigest(),
    }
    cache_path.write_text(json.dumps(fresh_stack), encoding="utf-8")
    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--select",
                "pr_comment_attention,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    reusable = json.loads(capsys.readouterr().out)["values"]
    reusable_continuity = reusable["pr_comment_attention"]["review_stack_continuity"]
    assert reusable_continuity["phase"] == "review-closeout-ready"
    assert reusable_continuity["incremental_proof_manifest"]["proof_reuse_status"] == "reuse_safe_with_evidence"
    assert reusable_continuity["incremental_proof_manifest"]["reusable_groups"][0]["command"] == "uv run pytest tests/test_app.py -q"
    assert reusable_continuity["next_action"]["id"] == "closeout-with-reused-proof-receipt"
    assert reusable_continuity["closeout_route"]["status"] == "ready_after_recording_reuse_rationale"
    assert reusable_continuity["planning_owner"]["phase_source"] == "planning_lifecycle_transition"
    assert reusable_continuity["planning_owner"]["transition_records"] == [correction["path"]]
    assert reusable_continuity["workflow_trace"]["status"] == "executed_transition_trace"
    assert reusable_continuity["workflow_trace"]["transition_source"] == "planning_lifecycle_transition"
    assert reusable_continuity["workflow_trace"]["interaction_cost"]["ordinary_rerun_count"] == 1
    assert reusable_continuity["workflow_trace"]["interaction_cost"]["executed_transition_count"] == 2
    assert reusable_continuity["workflow_trace"]["interaction_cost"]["manual_transition_record_count"] == 0
    assert reusable_continuity["workflow_trace"]["interaction_cost"]["avoided_manual_transition_records"] == 2
    assert reusable_continuity["workflow_trace"]["interaction_cost"]["evidence_source"] == "planning_lifecycle_transition"
    assert [event["phase_after"] for event in reusable_continuity["workflow_trace"]["executed_events"]] == [
        "review-proof",
        "review-closeout-ready",
    ]
    proof_event = reusable_continuity["workflow_trace"]["executed_events"][1]
    assert proof_event["proof_receipt_path"] == ".agentic-workspace/local/proof-receipts/last.json"
    assert proof_event["proof_receipt_result"] == "passed"
    assert proof_event["command_exit_code"] == 0
    assert (
        cli.main(
            [
                "planning",
                "closeout",
                "--target",
                str(tmp_path),
                "--claim-level",
                "slice",
                "--intent-status",
                "satisfied",
                "--residue",
                "none",
                "--proof-from",
                "last",
                "--what-happened",
                "Review stack comments addressed.",
                "--scope-touched",
                "src/app.py tests/test_app.py",
                "--changed-surfaces",
                "src/app.py tests/test_app.py",
                "--review-summary",
                "Review blockers addressed.",
                "--outcome-summary",
                "Ready to close review stack slice.",
                "--format",
                "json",
            ]
        )
        == 0
    )
    closeout = json.loads(capsys.readouterr().out)
    assert closeout["review_stack_transition"]["status"] == "updated"
    assert closeout["review_stack_transition"]["phase"] == "review-closeout-ready"
    assert closeout["review_stack_transition"]["phase_after"] == "review-closed"
    assert closeout["review_stack_transition"]["command_exit_code"] == 0
    assert [item["producer_class"] for item in closeout["calibration_admissions"]] == ["closeout-outcome", "handoff-outcome"]
    assert [item["status"] for item in closeout["calibration_admissions"]] == ["recorded", "recorded"]
    closeout_ref = closeout["calibration_admissions"][0]["source_ref"]
    handoff_ref = closeout["calibration_admissions"][1]["source_ref"]
    closeout_receipt_id = closeout_ref.rsplit("/", 1)[-1]
    handoff_receipt_id = handoff_ref.rsplit("/", 1)[-1]
    closeout_receipt = json.loads(
        (tmp_path / ".agentic-workspace" / "local" / "closeout-receipts" / f"{closeout_receipt_id}.json").read_text(encoding="utf-8")
    )
    handoff_receipt = json.loads(
        (tmp_path / ".agentic-workspace" / "local" / "handoff-receipts" / f"{handoff_receipt_id}.json").read_text(encoding="utf-8")
    )
    assert (
        closeout_receipt["target_context"]
        == handoff_receipt["target_context"]
        == {
            "delegation_target": "fast_worker",
            "task_class": "mechanical-follow-through",
            "scope_class": "narrow-code-change",
        }
    )
    assert closeout_receipt["result"] == "accepted"
    assert handoff_receipt["result"] == "accepted"

    from agentic_workspace.config import load_delegation_outcomes

    _, _, records = load_delegation_outcomes(target_root=tmp_path)
    assert [record.producer_class for record in records if record.producer_class != "aw-proof"] == [
        "human-review",
        "retry-outcome",
        "closeout-outcome",
        "handoff-outcome",
    ]

    actionable_stack = copy.deepcopy(fresh_stack)
    actionable_stack["stack_members"][1]["delta"]["category_counts"]["actionable_code_doc_body_change"] = 1
    actionable_stack["stack_members"][1]["delta"]["new_comment_count"] = 1
    actionable_stack["stack_members"][1]["delta"]["items"] = [
        {
            "kind": "review_thread_comment",
            "category": "actionable_code_doc_body_change",
            "path": "docs/comment-anchor.md",
            "line": 12,
            "url": "https://example.test/pr#thread",
            "author": "reviewer",
            "proof_hint": "Comment-local hint should not replace changed-effect proof.",
        }
    ]
    cache_path.write_text(
        json.dumps(actionable_stack),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--select",
                "pr_comment_attention,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]

    attention = payload["pr_comment_attention"]
    assert attention["status"] == "actionable_stack_comments_present"
    assert attention["comment_state"] == "stack_comments_requiring_action"
    assert attention["stack_member_count"] == 2
    assert attention["comment_addressing"]["kind"] == "agentic-workspace/pr-comment-stack-addressing/v1"
    assert attention["comment_addressing"]["status"] == "open_feedback_present"
    assert "--section pr_comment_attention --format json" in attention["detail_route"]
    assert attention["absence_states"]["thread_level_comments"] == "hidden_behind_detail_route"
    continuity = attention["review_stack_continuity"]
    assert continuity["phase"] == "review-correction"
    assert continuity["affected_slice"]["status"] == "review_findings_present"
    assert continuity["affected_slice"]["pr_number"] == "1841"
    assert continuity["affected_slice"]["paths"] == ["src/app.py", "tests/test_app.py"]
    assert continuity["affected_slice"]["proof_hints"] == ["Run changed-effect proof."]
    assert continuity["affected_slice"]["path_source"] == "stack_member_changed_effect_paths"
    assert continuity["review_findings"]["actionable_pr_numbers"] == ["1841"]
    assert continuity["review_findings"]["owner"]["status"] == "bound_to_active_planning_owner"
    assert continuity["review_findings"]["owner"]["surface"].endswith("stack-review-plan.plan.json")
    assert continuity["incremental_proof_manifest"]["status"] == "pending_after_correction"
    assert continuity["incremental_proof_manifest"]["changed_effect_paths"] == ["src/app.py", "tests/test_app.py"]
    assert (
        "proof --changed src/app.py tests/test_app.py --format json"
        in continuity["incremental_proof_manifest"]["proof_selection_command_template"]
    )
    assert continuity["next_action"]["id"] == "run-review-correction-workflow"
    assert "implement --changed src/app.py tests/test_app.py" in continuity["next_action"]["command"]
    assert continuity["closeout_route"]["status"] == "blocked"
    assert continuity["planning_owner"]["status"] == "bound_to_active_planning_owner"
    assert continuity["workflow_trace"]["status"] == "executed_transition_trace"
    assert continuity["workflow_trace"]["transition_source"] == "planning_lifecycle_transition"
    assert continuity["workflow_trace"]["interaction_cost"]["ordinary_rerun_count"] == 1
    assert continuity["workflow_trace"]["interaction_cost"]["executed_transition_count"] == 3
    assert continuity["workflow_trace"]["interaction_cost"]["manual_transition_record_count"] == 0
    assert continuity["workflow_trace"]["interaction_cost"]["avoided_manual_transition_records"] == 3
    assert continuity["workflow_trace"]["interaction_cost"]["evidence_source"] == "planning_lifecycle_transition"
    assert [event["phase_after"] for event in continuity["workflow_trace"]["executed_events"]] == [
        "review-proof",
        "review-closeout-ready",
        "review-closed",
    ]
    assert "review_stack_continuity.next_action.command" in continuity["workflow_trace"]["interaction_cost"]["resume_inputs_after_packet"]

    stale_stack = copy.deepcopy(fresh_stack)
    stale_stack["stack_members"][0]["delta"].pop("freshness")
    cache_path.write_text(json.dumps(stale_stack), encoding="utf-8")
    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--select",
                "pr_comment_attention,action_signals",
                "--format",
                "json",
            ]
        )
        == 0
    )
    stale = json.loads(capsys.readouterr().out)["values"]
    assert stale["pr_comment_attention"]["status"] == "stack_comment_status_unavailable"
    assert stale["pr_comment_attention"]["comment_state"] == "stack_stale_or_unknown"
    assert stale["pr_comment_attention"]["absence_states"]["thread_level_comments"] == "hidden_behind_detail_route"
    assert "--section pr_comment_attention --format json" in stale["pr_comment_attention"]["detail_route"]
    stale_continuity = stale["pr_comment_attention"]["review_stack_continuity"]
    assert stale_continuity["phase"] == "review-state-refresh"
    assert stale_continuity["review_findings"]["stale_or_unverified_pr_numbers"] == ["1840"]
    assert stale_continuity["next_action"]["id"] == "refresh-stack-review-state"


def test_report_proof_reuse_guidance_classifies_safe_and_stale_receipts(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    changed_path = tmp_path / "src" / "app.py"
    changed_path.parent.mkdir(parents=True, exist_ok=True)
    changed_path.write_text("VALUE = 1\n", encoding="utf-8")
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "proof-reuse.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    unknown = json.loads(capsys.readouterr().out)["answer"]
    assert unknown["status"] == "reuse_unknown"

    minimal_receipt = {
        "prior_head": "abc123",
        "prior_base": "base123",
        "changed_paths": ["src/app.py"],
        "path_fingerprints": {"src/app.py": hashlib.sha256(changed_path.read_bytes()).hexdigest()},
        "proof_groups": [{"command": "uv run pytest tests/test_app.py -q", "status": "passed"}],
    }
    cache_path.write_text(json.dumps(minimal_receipt), encoding="utf-8")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    under_evidenced = json.loads(capsys.readouterr().out)["answer"]
    assert under_evidenced["status"] == "reuse_unknown"
    assert "parent_proof_reference" in under_evidenced["missing_reuse_evidence"]
    assert "command_identity" in under_evidenced["proof_groups"][0]["missing_reuse_evidence"]

    safe_receipt = {
        **minimal_receipt,
        "parent_proof_reference": "proof-receipt:abc123",
        "proof_selection_fingerprint": "selection:runtime-tests",
        "dependency_config_fingerprint": "deps:locked",
        "generated_surface_freshness": {"status": "verified"},
        "proof_groups": [
            {
                "command": "uv run pytest tests/test_app.py -q",
                "command_fingerprint": "cmd:test-app",
                "status": "passed",
            }
        ],
    }
    cache_path.write_text(json.dumps(safe_receipt), encoding="utf-8")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    safe = json.loads(capsys.readouterr().out)["answer"]
    assert safe["status"] == "reuse_safe_with_evidence"
    assert safe["proof_groups"][0]["classification"] == "reuse_safe_with_evidence"

    cache_path.write_text(
        json.dumps(
            {
                **safe_receipt,
                "changed_paths": ["src/app.py"],
                "path_fingerprints": {"src/app.py": hashlib.sha256(changed_path.read_bytes()).hexdigest()},
                "proof_groups": [
                    {
                        "command": "uv run pytest tests/test_app.py -q",
                        "command_fingerprint": "cmd:test-app",
                        "status": "passed",
                    },
                    {"command": "make lint-workspace", "command_fingerprint": "cmd:lint", "status": "failed"},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    partial = json.loads(capsys.readouterr().out)["answer"]
    assert partial["status"] == "focused_rerun_required"
    assert partial["proof_groups"][1]["classification"] == "rerun_required"

    changed_path.write_text("VALUE = 2\n", encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    stale = json.loads(capsys.readouterr().out)["answer"]
    assert stale["status"] == "rerun_required"
    assert stale["changed_fingerprints"] == ["src/app.py"]


def test_proof_reuse_v2_reuses_unrelated_descendants_and_rejects_exact_identity_drift(tmp_path: Path) -> None:
    import agentic_workspace.workspace_runtime_core as runtime_core

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    _write(tmp_path / "docs" / "unrelated.md", "one\n")
    _write(tmp_path / "pyproject.toml", "[project]\nname='fixture'\nversion='0.1.0'\n")
    _write(tmp_path / "uv.lock", "version = 1\n")
    _write(tmp_path / "Makefile", "test:\n\t@echo ok\n")
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "subject"], cwd=tmp_path, capture_output=True, check=True)

    runtime_core._write_proof_reuse_cache_from_receipt(
        target_root=tmp_path,
        command="uv run pytest tests/test_app.py -q",
        result="passed",
        changed_paths=["src/app.py"],
        receipt={"recorded_at": "2026-08-22T10:00:00+00:00"},
    )
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "proof-reuse.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cache["dependency_subject_identity"]

    _write(tmp_path / "docs" / "unrelated.md", "two\n")
    subprocess.run(["git", "add", "docs/unrelated.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "unrelated"], cwd=tmp_path, capture_output=True, check=True)
    reused = runtime_core._proof_reuse_guidance_payload(target_root=tmp_path, cli_invoke="agentic-workspace")
    assert reused["status"] == "reuse_safe_with_evidence"
    assert reused["head_transition"] == "unrelated-descendant"
    assert reused["pre_execution_summary"]["reused"] == ["uv run pytest tests/test_app.py -q"]
    assert reused["pre_execution_summary"]["focused_local"] == ["uv run pytest tests/test_app.py -q"]

    _write(tmp_path / "pyproject.toml", "[project]\nname='fixture'\nversion='0.2.0'\n")
    dependency_changed = runtime_core._proof_reuse_guidance_payload(target_root=tmp_path, cli_invoke="agentic-workspace")
    assert dependency_changed["status"] == "rerun_required"
    assert dependency_changed["identity_failures"] == ["dependency-config-changed"]
    assert dependency_changed["dependency_config_changed"] == ["pyproject.toml"]
    assert dependency_changed["proof_groups"][0]["execution_decision"] == "rerun-required"

    _write(tmp_path / "pyproject.toml", "[project]\nname='fixture'\nversion='0.1.0'\n")
    cache["runtime_identity"]["python"] = "0.0"
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    wrong_runtime = runtime_core._proof_reuse_guidance_payload(target_root=tmp_path, cli_invoke="agentic-workspace")
    assert wrong_runtime["identity_failures"] == ["wrong-runtime"]

    cache["runtime_identity"] = {
        "executable": str(Path(sys.executable).resolve()),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
    cache["prior_head"] = "not-a-commit"
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    wrong_head = runtime_core._proof_reuse_guidance_payload(target_root=tmp_path, cli_invoke="agentic-workspace")
    assert wrong_head["identity_failures"] == ["wrong-head"]


def test_report_operating_projection_receipt_is_lazy_and_task_scoped(tmp_path: Path, capsys) -> None:
    _init_real_git_repo_with_commit(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "operating_projection_receipt",
                "--task",
                "repair #2740",
                "--changed",
                "src/widget.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)["answer"]

    assert receipt["kind"] == "agentic-workspace/operating-projection-receipt/v1"
    assert receipt["scope"] == {"task": "repair #2740", "changed_paths": ["src/widget.py"]}
    assert set(receipt["owner_results"]) == {
        "route",
        "verification",
        "selected_proof",
        "closeout_trust",
        "runtime_mirror",
    }
    assert receipt["reuse_index"]["stores_proof"] is False
    assert receipt["construction_profile"]["owner_result_construction_count"] == 5

    _write(tmp_path / "unrelated.txt", "restacked\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "head-only restack"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--section",
                "operating_projection_receipt",
                "--task",
                "repair #2740",
                "--changed",
                "src/widget.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    warm_receipt = json.loads(capsys.readouterr().out)["answer"]
    assert warm_receipt["construction_profile"]["owner_result_construction_count"] == 0
    assert warm_receipt["construction_profile"]["owner_result_reuse_count"] == 5
    assert warm_receipt["construction_profile"]["duplicate_reconstruction_eliminated"] is True


def test_report_runtime_mirror_consistency_detects_missing_and_mismatched_shapes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    core = tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py"
    primitives = tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py"
    core.parent.mkdir(parents=True, exist_ok=True)
    core.write_text(
        """
def _pr_comment_attention_payload():
    return {"kind": "agentic-workspace/pr-comment-attention/v1", "status": "present", "extra": True}

def _dogfooding_signal_status_payload():
    return {"kind": "agentic-workspace/dogfooding-signal-status/v1", "status": "present"}
""",
        encoding="utf-8",
    )
    primitives.write_text(
        """
def _pr_comment_attention_payload():
    return {"kind": "agentic-workspace/pr-comment-attention/v1", "status": "present"}
""",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "runtime_mirror_consistency", "--format", "json"]) == 0
    mirror = json.loads(capsys.readouterr().out)["answer"]

    assert mirror["status"] == "shape_mismatch"
    by_surface = {record["mirrored_surface"]: record for record in mirror["records"]}
    assert by_surface["pr_comment_attention"]["status"] == "shape_mismatch"
    assert by_surface["dogfooding_signal_status"]["status"] == "mirror_missing"

    primitives.write_text(core.read_text(encoding="utf-8"), encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "runtime_mirror_consistency", "--format", "json"]) == 0
    in_sync = json.loads(capsys.readouterr().out)["answer"]
    assert in_sync["status"] == "shape_in_sync"
    assert in_sync["proof_strength"] == "return-key-shape-plus-selector-ownership"
    assert in_sync["semantic_equivalence_checked"] is False


def test_report_runtime_mirror_consistency_surfaces_active_selector_shadowing(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    core = tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py"
    primitives = tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py"
    core.parent.mkdir(parents=True, exist_ok=True)
    shared_helpers = """
def _pr_comment_attention_payload():
    return {"kind": "agentic-workspace/pr-comment-attention/v1", "status": "present"}

def _dogfooding_signal_status_payload():
    return {"kind": "agentic-workspace/dogfooding-signal-status/v1", "status": "present"}

def _installed_state_drift_triage_payload():
    return {"kind": "agentic-workspace/installed-state-drift-triage/v1", "status": "present"}

def _proof_reuse_guidance_payload():
    return {"kind": "agentic-workspace/proof-reuse-guidance/v1", "status": "present"}

def _runtime_mirror_surface_consistency_payload():
    return {"kind": "agentic-workspace/runtime-mirror-surface-consistency/v1", "status": "present"}

def _run_report_command():
    return {}

def _run_report_router_command():
    return {}
"""
    core.write_text(
        shared_helpers
        + """
def _run_lazy_report_section_command(normalized):
    if normalized == "current_work":
        return {}
    return {}
""",
        encoding="utf-8",
    )
    primitives.write_text(
        shared_helpers
        + """
def _run_lazy_report_section_command(normalized):
    if normalized == "current_work":
        return {}
    if normalized == "reasoning_economy":
        return {}
    return {}

_run_report_command = _workspace_runtime_core._run_report_command
_run_report_router_command = _workspace_runtime_core._run_report_router_command
_run_lazy_report_section_command = _workspace_runtime_core._run_lazy_report_section_command
""",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "runtime_mirror_consistency", "--format", "json"]) == 0
    mirror = json.loads(capsys.readouterr().out)["answer"]

    assert mirror["status"] == "shadow_mismatch"
    shadowing = mirror["report_runtime_shadowing"]
    assert shadowing["status"] == "selector_branch_mismatch"
    selectors = shadowing["selector_branch_consistency"]
    assert selectors["active_owner"] == "src/agentic_workspace/workspace_runtime_core.py"
    assert selectors["missing_from_active_core"] == ["reasoning_economy"]
    by_symbol = {item["symbol"]: item for item in shadowing["symbols"]}
    assert by_symbol["_run_lazy_report_section_command"]["primitive_aliases_core"] is True
    assert by_symbol["_run_lazy_report_section_command"]["active_owner"] == "src/agentic_workspace/workspace_runtime_core.py"


def test_report_dogfooding_signal_status_covers_closeout_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "dogfooding-signal-status.json"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    not_checked = json.loads(capsys.readouterr().out)["answer"]
    assert not_checked["status"] == "not_checked"
    assert not_checked["outcome"] == "not_checked"
    assert not_checked["closeout_blocked"] is False
    assert "session_improvement_intake" in not_checked["detail_command"]
    assert "--target ./repo" not in not_checked["detail_command"]
    assert not_checked["capture_routes"]["status"] == "available"
    assert "--target ./repo" not in json.dumps(not_checked["capture_routes"])
    assert any(route["outcome"] == "routed_to_memory" for route in not_checked["capture_routes"]["ordinary_routes"])
    assert not_checked["disposition"]["diagnostic_command_alone_satisfies"] is False

    cache_path.write_text(json.dumps({"status": "checked_none", "reason": "reviewed; no durable signal"}), encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    no_signal = json.loads(capsys.readouterr().out)["answer"]
    assert no_signal["status"] == "checked_none"
    assert no_signal["durable_residue"] is False

    cache_path.write_text(
        json.dumps({"status": "recorded_chat_only", "signals": ["in-chat dogfooding note"]}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    chat_only = json.loads(capsys.readouterr().out)["answer"]
    assert chat_only["status"] == "recorded_chat_only"
    assert chat_only["durability"] == "local_chat_only"
    assert chat_only["canonical_repo_history"] is False

    cache_path.write_text(
        json.dumps({"status": "recorded_session_only", "signals": ["temporary validation friction"]}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    session_only = json.loads(capsys.readouterr().out)["answer"]
    assert session_only["status"] == "recorded_session_only"
    assert session_only["durability"] == "local_session_only"

    cache_path.write_text(
        json.dumps({"status": "routed_to_issue", "signals": ["startup missed PR comments"], "destinations": ["#1831"]}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    routed = json.loads(capsys.readouterr().out)["answer"]
    assert routed["status"] == "routed_to_issue"
    assert routed["destinations"] == ["#1831"]
    assert routed["closeout_blocked"] is False
    assert routed["durable_residue"] is True

    cache_path.write_text(
        json.dumps({"status": "deferred_to_roadmap", "signals": ["larger design concern"], "deferred_reason": "roadmap batch"}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    deferred = json.loads(capsys.readouterr().out)["answer"]
    assert deferred["status"] == "deferred_to_roadmap"
    assert deferred["durability"] == "roadmap_or_future_work"

    cache_path.write_text(
        json.dumps(
            {
                "status": "dismissed_with_reason",
                "signals": ["one-off shell typo"],
                "dismissal_reason": "operator typo, not product friction",
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    dismissed = json.loads(capsys.readouterr().out)["answer"]
    assert dismissed["status"] == "dismissed_with_reason"
    assert dismissed["dismissal_reason"] == "operator typo, not product friction"
    assert dismissed["closeout_blocked"] is False

    cache_path.write_text(
        json.dumps({"status": "fixed", "signals": ["receipt choreography"], "reason": "proof execution now reconciles receipts"}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    fixed = json.loads(capsys.readouterr().out)["answer"]
    assert fixed["status"] == "fixed"
    assert fixed["closeout_blocked"] is False
    assert fixed["durable_residue"] is False

    cache_path.write_text(
        json.dumps({"status": "accepted-risk", "signals": ["bounded repeat"], "accepted_risk_reason": "bounded maintenance cost"}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    accepted = json.loads(capsys.readouterr().out)["answer"]
    assert accepted["status"] == "accepted-risk"
    assert accepted["closeout_blocked"] is False
    assert accepted["accepted_risk_reason"] == "bounded maintenance cost"

    cache_path.write_text(json.dumps({"signals": ["unrouted friction"]}), encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    blocked = json.loads(capsys.readouterr().out)["answer"]
    assert blocked["status"] == "unresolved"
    assert blocked["closeout_blocked"] is True
    assert blocked["durable_residue"] is True


def test_session_improvement_intake_separates_session_and_repo_wide_scopes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "dogfooding-signal-status.json"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "session_improvement_intake", "--format", "json"]) == 0
    unavailable = json.loads(capsys.readouterr().out)["answer"]
    assert unavailable["status"] == "unavailable"
    assert unavailable["session_signal_source"]["status"] == "missing"
    assert unavailable["capture_routes"]["status"] == "available"
    assert unavailable["operational_effect"]["status"] == "capture-route-available"
    assert unavailable["repo_wide_existing"]["included_by_default"] is False
    assert unavailable["repo_wide_existing"]["status"] == "bounded_index_available"
    assert "defaults --section improvement_intake --format json" in unavailable["repo_wide_existing"]["command"]
    assert "--target ./repo" not in unavailable["repo_wide_existing"]["full_scan_command"]
    assert "report --target " in unavailable["repo_wide_existing"]["full_scan_command"]
    assert "--section improvement_intake --format json" in unavailable["repo_wide_existing"]["full_scan_command"]
    assert "large_file" not in json.dumps(unavailable)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "improvement_intake", "--format", "json"]) == 0
    missing_cache_intake = json.loads(capsys.readouterr().out)["answer"]
    assert missing_cache_intake["session_admission"] == {
        "status": "unavailable",
        "candidate_count": 0,
        "missing_cache": True,
        "decision": "not-a-candidate-until-session-evidence-is-captured",
    }

    cache_path.write_text(
        json.dumps(
            {
                "status": "unresolved",
                "signals": ["improvement diagnostics did not change next action"],
                "routing_decision": "route_now",
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "session_improvement_intake", "--format", "json"]) == 0
    session = json.loads(capsys.readouterr().out)["answer"]
    assert session["status"] == "session_observed"
    assert session["session_observed_signals"][0]["outcome"] == "unresolved"
    assert session["routing_decisions"][0]["decision"] == "route_now"
    assert session["routing_decisions"][0]["closeout_blocked"] is True
    assert session["operational_effect"]["status"] == "closeout-blocking"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "improvement_intake", "--format", "json"]) == 0
    repo_wide = json.loads(capsys.readouterr().out)["answer"]
    assert repo_wide["intake_scope"]["status"] == "explicit_repo_wide_requested"
    assert "repo_wide_existing_candidates" in repo_wide
    assert repo_wide["session_admission"]["status"] == "session_observed"
    assert repo_wide["session_admission"]["candidate_count"] == 1
    assert any(
        item["source"] == "session_improvement_intake.session_observed_signals" and item["routing_decision"]["status"] == "candidate"
        for item in repo_wide["candidate_sample"]
    )

    cache_path.write_text(
        json.dumps(
            {
                "status": "unresolved",
                "signals": ["The opaque proof run exceeded 12 minutes without progress reporting"],
                "routing_decision": "route_now",
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "improvement_intake", "--format", "json"]) == 0
    long_proof = json.loads(capsys.readouterr().out)["answer"]
    decision = next(item for item in long_proof["candidate_sample"] if "12 minutes" in item["symptom"])
    assert decision["routing_decision"]["status"] == "candidate"
    assert decision["routing_decision"]["owner"] == "workspace"
    assert decision["routing_decision"]["confidence"] == "high"


def test_session_log_signal_captures_strengthens_and_routes_structured_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    rejected_argv = [
        "session-log",
        "signal",
        "--target",
        str(tmp_path),
        "--kind",
        "opportunity",
        "--symptom",
        "A helper might be cleaner",
        "--cost",
        "No concrete cost is established",
        "--format",
        "json",
    ]
    assert cli.main(rejected_argv) == 0
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["status"] == "rejected"
    assert rejected["mutation_authorized"] is False
    assert not (tmp_path / ".agentic-workspace/local/cache/dogfooding-signal-status.json").exists()

    base_argv = [
        "session-log",
        "signal",
        "--target",
        str(tmp_path),
        "--kind",
        "opportunity",
        "--symptom",
        "Release proof repeatedly selects unrelated Planning suites",
        "--cost",
        "Two unrelated runs add 171.6 seconds",
        "--expected-benefit",
        "Select only release-owned proof dependencies",
        "--owner-hint",
        "src/agentic_workspace/workspace_runtime_proof.py",
        "--scope-relation",
        "adjacent-scope",
        "--likely-remediation",
        "validation",
        "--evidence-ref",
        "proof://before-release-route",
        "--format",
        "json",
    ]
    assert cli.main(base_argv) == 0
    captured = json.loads(capsys.readouterr().out)
    assert captured["status"] == "captured"
    assert captured["candidate_only"] is True
    assert captured["mutation_authorized"] is False

    confirmed_argv = [
        *base_argv[:-2],
        "--evidence-class",
        "human_confirmed",
        "--evidence-ref",
        "review://release-route-confirmation",
        "--format",
        "json",
    ]
    assert cli.main(confirmed_argv) == 0
    strengthened = json.loads(capsys.readouterr().out)
    assert strengthened["status"] == "strengthened"
    assert strengthened["occurrence_count"] == 2
    assert strengthened["recurrence"] == "human_confirmed"
    assert strengthened["evidence_classes"] == ["agent_observed", "human_confirmed"]

    reviewed_argv = [
        *base_argv[:-2],
        "--evidence-class",
        "review_derived",
        "--evidence-ref",
        "review://bounded-finding",
        "--format",
        "json",
    ]
    assert cli.main(reviewed_argv) == 0
    reviewed = json.loads(capsys.readouterr().out)
    assert reviewed["status"] == "strengthened"
    assert reviewed["occurrence_count"] == 3
    assert reviewed["evidence_classes"] == ["agent_observed", "human_confirmed", "review_derived"]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "improvement_intake", "--format", "json"]) == 0
    intake = json.loads(capsys.readouterr().out)["answer"]
    candidate = next(item for item in intake["candidate_sample"] if item["kind"] == "improvement_opportunity")
    assert candidate["expected_benefit"] == "Select only release-owned proof dependencies"
    assert candidate["scope_relation"] == "adjacent-scope"
    assert candidate["occurrence_count"] == 3
    assert candidate["recurrence"] == "human_confirmed"
    assert candidate["confidence"] == "high"
    assert candidate["mutation_authorized"] is False
    assert candidate["evidence_refs"] == [
        "proof://before-release-route",
        "review://bounded-finding",
        "review://release-route-confirmation",
    ]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "session_improvement_intake", "--format", "json"]) == 0
    session = json.loads(capsys.readouterr().out)["answer"]
    assert session["operational_effect"]["status"] == "closeout-blocking"
    assert session["routing_decisions"][0]["closeout_blocked"] is True


def test_session_improvement_intake_self_admits_material_index_as_pending_disposition(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(tmp_path / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "session-improvement-intake-test")
    for _ in range(2):
        assert session_logging.run_with_session_logging(["status", "--target", str(tmp_path)], lambda _argv: 0) == 0

    assert cli.main(["report", "--target", str(tmp_path), "--section", "session_improvement_intake", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]
    assert payload["status"] == "session_observed"
    assert payload["session_signal_source"]["status"] == "complete-index"
    signal = payload["session_observed_signals"][0]
    assert signal["outcome"] == "pending_disposition"
    assert signal["reviewed"] is True
    assert len(signal["fingerprint"]) == 20
    assert payload["routing_decisions"][0]["closeout_blocked"] is True
    assert payload["operational_effect"]["status"] == "closeout-blocking"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    status = json.loads(capsys.readouterr().out)["answer"]
    assert status["status"] == "pending_disposition"
    assert status["closeout_blocked"] is True
    assert "dismissal_reason" not in status
    assert "deferred_reason" not in status
    assert status["next_action"]["id"] == "capture-material-session-signal"
    assert "session-log signal" in status["next_action"]["command"]
    assert status["next_action"]["evidence_fingerprint"] == signal["evidence_fingerprint"]


def test_session_log_download_intent_routes_to_export_without_transfer_approval(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Package the current AW session logs for download",
                "--select",
                "session_log_export_route,next_safe_action",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)["values"]
    route = payload["session_log_export_route"]
    assert route["operation"] == "session-log.export"
    assert route["command"].endswith("session-log export --target . --format json")
    assert route["result_path"] == "session-log export result.path"
    assert route["transfer_approval"] == "not-granted"
    assert payload["next_safe_action"]["next_safe_action"] == "run-session-log-export"


def test_session_index_intake_deduplicates_stable_material_candidates_before_disposition(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    config = workspace_runtime_core._load_workspace_config(target_root=tmp_path)
    candidate = {
        "id": "same",
        "summary": "Repeated session signal",
        "count": 2,
        "improvement_signal": {
            "kind": "workflow_cost",
            "symptom": "Status was repeated in one session.",
            "cost": "Repeated routing work.",
            "suspected_owner": "operating-loop",
            "confidence": "medium",
            "recurrence": "repeated",
            "occurrence_count": 2,
            "evidence_fingerprint": "stable-material-id",
        },
    }
    monkeypatch.setattr(
        session_logging,
        "analyze_session_log",
        lambda **_kwargs: {
            "kind": "agentic-workspace/session-log-analysis/v1",
            "status": "analyzed",
            "index_status": "complete",
            "index_path": ".agentic-workspace/local/session-logging/index.json",
            "detail_page": {"items": [candidate, copy.deepcopy(candidate)]},
        },
    )

    first = workspace_runtime_core._session_index_improvement_intake(target_root=tmp_path, config=config)
    second = workspace_runtime_core._session_index_improvement_intake(target_root=tmp_path, config=config)
    assert first is not None and second is not None
    assert len(first["signals"]) == len(first["routing_decisions"]) == 1
    assert first["signals"][0]["fingerprint"] == second["signals"][0]["fingerprint"]
    assert first["signals"][0]["reviewed"] is True
    assert first["routing_decisions"][0]["destinations"] == []
    assert first["routing_decisions"][0]["closeout_blocked"] is True


def test_session_index_intake_selects_one_strongest_material_candidate(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    config = workspace_runtime_core._load_workspace_config(target_root=tmp_path)

    def candidate(candidate_id: str, *, confidence: str, count: int) -> dict[str, object]:
        return {
            "id": candidate_id,
            "summary": candidate_id,
            "improvement_signal": {
                "kind": "workflow_cost",
                "symptom": candidate_id,
                "confidence": confidence,
                "recurrence": "repeated",
                "occurrence_count": count,
                "evidence_fingerprint": f"fingerprint-{candidate_id}",
            },
        }

    monkeypatch.setattr(
        session_logging,
        "analyze_session_log",
        lambda **_kwargs: {
            "kind": "agentic-workspace/session-log-analysis/v1",
            "status": "analyzed",
            "index_status": "complete",
            "index_path": ".agentic-workspace/local/session-logging/index.json",
            "detail_page": {
                "items": [
                    candidate("repeated-command", confidence="medium", count=3),
                    candidate("duplicate-output", confidence="medium", count=14),
                    candidate("receipt-choreography", confidence="high", count=4),
                ]
            },
        },
    )

    intake = workspace_runtime_core._session_index_improvement_intake(target_root=tmp_path, config=config)
    assert intake is not None
    assert len(intake["signals"]) == len(intake["routing_decisions"]) == 1
    assert intake["signals"][0]["signal"] == "receipt-choreography"
    assert intake["signals"][0]["fingerprint"] == "fingerprint-receipt-choreography"


def test_selected_dogfooding_report_sections_stay_compact(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    large_doc = tmp_path / "docs" / "large-concept.md"
    large_doc.parent.mkdir(parents=True, exist_ok=True)
    large_doc.write_text("\n".join(f"line {index}" for index in range(260)) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "docs/large-concept.md"], cwd=tmp_path, check=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "improvement_intake", "--format", "json"]) == 0
    intake = json.loads(capsys.readouterr().out)
    _assert_json_payload_under(intake, 8_000, label="selected improvement_intake compact report", sort_keys=False)
    assert intake["answer"]["detail_selector"] == "improvement_intake"
    assert "detail_command" in intake["answer"]
    assert intake["answer"]["rule"].startswith("Selected dogfooding report sections return compact")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "repo_friction", "--format", "json"]) == 0
    friction = json.loads(capsys.readouterr().out)
    _assert_json_payload_under(friction, 8_000, label="selected repo_friction compact report", sort_keys=False)
    assert friction["answer"]["detail_selector"] == "repo_friction"
    assert friction["answer"]["large_file_hotspots"]["sample"] == []
    assert friction["answer"]["concept_surface_hotspots"]["count"] >= 1


def test_repo_friction_prioritizes_tracked_source_and_explains_deduplicated_intake(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    tracked_files = {
        "src/agentic_workspace/workspace_runtime_core.py": 520,
        "src/agentic_workspace/workspace_runtime_primitives.py": 510,
        "packages/planning/src/repo_planning_bootstrap/installer.py": 500,
    }
    for relative, line_count in tracked_files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(f"def symbol_{index}(): pass" for index in range(line_count)) + "\n", encoding="utf-8")
    cache = tmp_path / ".agentic-workspace/local/cache/projection.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text("\n".join("cache" for _ in range(900)) + "\n", encoding="utf-8")
    generated = tmp_path / "generated/workspace/python/large.py"
    generated.parent.mkdir(parents=True, exist_ok=True)
    generated.write_text("\n".join("generated" for _ in range(800)) + "\n", encoding="utf-8")
    makefile = tmp_path / "Makefile"
    makefile.write_text("check: test-workspace lint-workspace\n\ntest-workspace:\n\nlint-workspace:\n", encoding="utf-8")
    setup_findings = tmp_path / "tools/setup-findings.json"
    setup_findings.parent.mkdir(parents=True, exist_ok=True)
    setup_findings.write_text(
        json.dumps(
            {
                "kind": "workspace-setup-findings/v1",
                "findings": [
                    {
                        "class": "repo_friction_evidence",
                        "summary": f"Validation run #{issue} collided with run id 123456",
                        "confidence": 0.95,
                        "refs": [f"#{issue}"],
                        "observed_during": "proof",
                        "cost": "rerun",
                        "suspected_owner": "validation runtime",
                        "signal_kind": "validation_friction",
                        "likely_remediation": "validation",
                        "recurrence": "repeated",
                        "issue_ref": f"#{issue}",
                    }
                    for issue in (2443, 2444)
                ],
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", *tracked_files, "Makefile", "tools/setup-findings.json"], cwd=tmp_path, check=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "repo_friction", "--format", "json"]) == 0
    friction = json.loads(capsys.readouterr().out)["answer"]
    hotspot_paths = [item["path"] for item in friction["large_file_hotspots"]["sample"]]
    assert hotspot_paths == list(tracked_files)
    assert all(item["source_domain"] == "tracked-source" for item in friction["large_file_hotspots"]["sample"])
    assert friction["large_file_hotspots"]["sample"][0]["source_metrics"]["duplication_cluster"] == "workspace-runtime-mirror"
    assert friction["regenerable_cache_hotspots"]["status"] == "excluded-from-primary-ranking"
    assert generated.relative_to(tmp_path).as_posix() not in json.dumps(friction["large_file_hotspots"])
    assert friction["proof_route_completeness"]["status"] == "complete"
    assert friction["proof_route_completeness"]["classification"] == "declared-dependency-closure"
    assert friction["scan_budget"]["elapsed_ms"] < friction["scan_budget"]["default_elapsed_budget_ms"]
    assert friction["scan_budget"]["history_strategy"].startswith("one bulk git history query")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "improvement_intake", "--format", "json"]) == 0
    intake = json.loads(capsys.readouterr().out)["answer"]
    assert intake["candidate_count"] == 4
    assert all(item["evidence_fingerprint"] for item in intake["candidate_sample"])
    assert all(item["routing_decision"]["reason"] for item in intake["candidate_sample"])
    assert all(item["routing_decision"]["owner"] for item in intake["candidate_sample"])

    existing_owner = next(
        item for item in intake["candidate_sample"] if item["routing_decision"].get("equivalent_issue_refs") == ["#2443", "#2444"]
    )
    assert existing_owner["equivalent_evidence_count"] == 2
    assert existing_owner["routing_decision"]["equivalent_issue_refs"] == ["#2443", "#2444"]

    makefile.write_text("check: missing-proof-target\n", encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "repo_friction", "--format", "json"]) == 0
    incomplete = json.loads(capsys.readouterr().out)["answer"]["proof_route_completeness"]
    assert incomplete["status"] == "incomplete"
    assert incomplete["missing_constituent_ids"] == ["missing-proof-target"]

    findings = workspace_runtime_core._structured_findings_payload(
        source_payload={
            "findings": [
                {"id": "archive-1", "kind": "archived-closeout-residue", "message": "Archived residue for issue #101"},
                {"id": "archive-2", "kind": "archived-closeout-residue", "message": "Archived residue for issue #102"},
            ]
        },
        external_evidence_safety={},
        verification={},
    )
    assert findings["entry_count"] == 1
    assert findings["underlying_record_count"] == 2
    assert findings["entries"][0]["record_count"] == 2
    assert len(findings["entries"][0]["exemplars"]) == 2
    assert findings["aggregation"]["full_records_selector"] == "structured_findings.underlying_records"


def test_chat_agent_default_outputs_stay_bounded_without_selector_inventories(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--format", "json"]) == 0
    start = json.loads(capsys.readouterr().out)
    _assert_json_payload_under(start, 10_000, label="compact start chat-agent output", sort_keys=False)
    _assert_selector_inventory_omitted_from_compact_start(start)

    assert cli.main(["summary", "--target", str(tmp_path), "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    _assert_json_payload_under(summary, 20_000, label="compact summary chat-agent output", sort_keys=False)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    proof = json.loads(capsys.readouterr().out)
    _assert_json_payload_under(proof, 12_000, label="compact proof chat-agent output", sort_keys=False)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "repo_friction", "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    _assert_json_payload_under(report, 8_000, label="selected report chat-agent output", sort_keys=False)

    for label, payload in (("start", start), ("summary", summary), ("proof", proof), ("report", report)):
        encoded = json.dumps(payload)
        assert "available_selectors" not in encoded, label
        assert "selector_schema" not in encoded, label


def test_start_missing_selector_returns_bounded_inventory(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--select", "not_a_selector", "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 2_000, label="start missing selector fallback", sort_keys=False)
    assert payload["status"] == "invalid-selector"
    assert payload["unknown_selectors"] == ["not_a_selector"]
    inventory = payload["selector_inventory"]
    assert inventory["status"] == "omitted-from-validation-error"
    assert inventory["available_count"] > len(inventory["sample"])
    assert len(inventory["sample"]) <= 8
    assert inventory["absence_state"] == "hidden_behind_detail_route"
    encoded = json.dumps(payload)
    assert "available_selectors" not in encoded
    assert "selector_schema" not in encoded


def test_start_surfaces_recovery_for_obsolete_default_preset(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[workspace]",
                'default_preset = "planning"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/start-recovery/v1"
    assert payload["status"] == "recovery-required"
    assert payload["problem"]["obsolete_field"] == "workspace.default_preset"
    assert payload["problem"]["replacement"] == "[modules] enabled = [...]"
    assert payload["problem"]["config_valid"] is False
    assert payload["automated_repair"]["safe"] is False
    assert payload["next_safe_action"]["implementation_allowed"] is False
    assert payload["recovery_packet"]["next_safe_command"] == "agentic-workspace config --target . --format json"


def test_start_recovery_for_obsolete_default_preset_uses_configured_cli_invoke(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[workspace]",
                'cli_invoke = "uv run aw-dev"',
                'default_preset = "planning"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/start-recovery/v1"
    assert payload["recovery_packet"]["next_safe_command"] == "uv run aw-dev config --target . --format json"


def test_proof_supports_exact_field_selectors_for_sufficiency(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--select",
                "sufficiency,next,proof_route_strategy_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "proof"
    assert payload["values"]["sufficiency"]["sufficiency_result"] == "required-proof-selected"
    assert payload["values"]["next"]["action"] == "route-refinement-required"
    assert payload["values"]["next"]["command"] is None
    assert payload["values"]["proof_route_strategy_decision"]["outcome"] == "broad-escalation-required"
    assert payload["values"]["proof_route_strategy_decision"]["claim_effect"] == "claim-blocked"
    assert "missing" not in payload


def test_proof_selector_inventory_is_bounded_and_names_receipt_selectors(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)

    def fail_proof_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("proof selector inventory must not build the full proof payload")

    monkeypatch.setattr(cli, "_proof_payload", fail_proof_payload)

    assert cli.main(["proof", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    inventory = payload["values"]["selector_inventory"]
    assert inventory["source_command"] == "proof"
    assert "proof_receipt_reconciliation" in inventory["selectors"]
    assert "proof_receipt_bridge" in inventory["selectors"]


def test_proof_route_strategy_identity_is_preserved_by_start_and_implement(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    start_args = [
        "start",
        "--target",
        str(tmp_path),
        "--changed",
        "generated/workspace/python/cli.py",
        "--select",
        "proof_route_strategy_preservation,proof_route_strategy_consumer_gate,next_safe_action",
        "--format",
        "json",
    ]
    assert cli.main(start_args) == 0
    start_values = json.loads(capsys.readouterr().out)["values"]

    implement_args = [
        "implement",
        "--target",
        str(tmp_path),
        "--changed",
        "generated/workspace/python/cli.py",
        "--select",
        "proof_route_strategy_preservation,proof_route_strategy_consumer_gate,next",
        "--format",
        "json",
    ]
    assert cli.main(implement_args) == 0
    implement_values = json.loads(capsys.readouterr().out)["values"]

    start_preservation = start_values["proof_route_strategy_preservation"]
    implement_preservation = implement_values["proof_route_strategy_preservation"]
    assert start_preservation["decision_id"] == implement_preservation["decision_id"]
    assert start_preservation["claim_effect"] == "claim-blocked"
    assert implement_preservation["claim_effect"] == "claim-blocked"
    assert start_values["proof_route_strategy_consumer_gate"]["route_health_id"] == start_preservation["route_health_id"]
    assert implement_values["proof_route_strategy_consumer_gate"]["route_health_id"] == implement_preservation["route_health_id"]
    assert start_values["proof_route_strategy_consumer_gate"]["mismatch_effect"] == "claim-blocked"
    assert start_values["next_safe_action"]["next_safe_action"] == "route-refinement-required"
    assert implement_values["next"]["action"] == "Resolve proof-route refinement or structured escalation before closeout."


def test_proof_compact_surfaces_narrowness_for_bounded_package_change(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(
        tmp_path / "Makefile",
        "test-planning:\n\t@echo ok\nlint-planning:\n\t@echo ok\ntypecheck-planning:\n\t@echo ok\n",
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    narrowness = payload["route"]["narrowness"]
    assert narrowness["status"] == "narrow_required"
    assert narrowness["required_reason_sample"]["acceptance_boundary"] is True
    assert "package-local planning source" in narrowness["required_reason_sample"]["why_required"]
    assert narrowness["broad_suite_boundary_status"] == "not_required_acceptance_boundary"


def test_proof_narrowness_marks_generated_surface_broad_proof_required(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(tmp_path / "Makefile", "test-workspace:\n\t@echo ok\nlint-workspace:\n\t@echo ok\n")
    _write(tmp_path / "scripts" / "run_agentic_workspace.py", "print('ok')\n")
    _write(tmp_path / "scripts" / "check" / "check_generated_command_packages.py", "print('ok')\n")
    _write(tmp_path / "scripts" / "check" / "run_operation_conformance_tests.py", "print('ok')\n")
    _write(tmp_path / "tests" / "test_workspace_cli.py", "def test_ok():\n    assert True\n")
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_narrowness",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    narrowness = payload["values"]["proof_narrowness"]
    assert narrowness["status"] == "narrow_required"
    assert narrowness["broad_suite_boundary"]["status"] == "explicit-escalation-required"
    assert narrowness["broad_suite_boundary"]["requires_explicit_escalation"] is True
    assert narrowness["broad_suite_boundary"]["withheld_generic_broad_lanes"][0]["lane"] == "workspace_cli"
    assert all(item["acceptance_boundary"] is False for item in narrowness["optional_confidence_checks"])
    assert "optional checks as confidence" in narrowness["final_report_rule"]


def test_report_sections_expose_authority_and_compliance_boundaries(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(tmp_path), "--section", "authority_hierarchy", "--format", "json"]) == 0
    authority = json.loads(capsys.readouterr().out)["answer"]
    assert authority["kind"] == "agentic-workspace/authority-hierarchy/v1"
    assert authority["ordered_authority"][-1]["authority"] == "disposable-or-audit-only-unless-promoted"
    assert "generated_summary" in authority["promotion_paths"]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "compliance_economics", "--format", "json"]) == 0
    compliance = json.loads(capsys.readouterr().out)["answer"]
    assert compliance["kind"] == "agentic-workspace/compliance-economics/v1"
    assert "cannot force" in compliance["boundary"]
    strengths = {entry["level"]: entry["strength"] for entry in compliance["enforcement_levels"]}
    assert strengths["prompt_instruction"] == "weak"
    assert strengths["schema_validity"] == "strong"


def test_report_exposes_configuration_projection_without_expanding_config_detail(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0

    router = json.loads(capsys.readouterr().out)
    assert "configuration_projection" not in router["context"]
    assert router["context"]["absence_states"]["configuration_projection"] == "detail_omitted"
    assert router["drill_down"]["section_hints"]["status"] == "omitted-from-compact-default"
    assert "--section <section> --format json" in router["drill_down"]["section_hints"]["detail_route"]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "configuration_projection", "--format", "json"]) == 0

    selected = json.loads(capsys.readouterr().out)
    assert selected["selector"] == {"section": "configuration_projection"}
    answer = selected["answer"]
    assert answer["kind"] == "agentic-workspace/configuration-projection/v1"
    assert answer["unprojected_fields"] == []
    assert any(item["owner_boundary"] == "local-human-owned" for item in answer["facts"])
    assert answer["verification"]["non_applicable_suppression"][0]["id"] == "ordinary-report-keeps-detail-sectioned"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "selective_surfacing_evaluation", "--format", "json"]) == 0

    selected_eval = json.loads(capsys.readouterr().out)
    assert selected_eval["selector"] == {"section": "selective_surfacing_evaluation"}
    assert selected_eval["answer"]["kind"] == "agentic-workspace/selective-surfacing-evaluation/v1"
    assert selected_eval["answer"]["status"] == "pass"
    assert selected_eval["answer"]["metrics"]["compact_json_size"] <= 1400
    relevance = {item["id"]: item for item in selected_eval["answer"]["relevance_scenarios"]}
    assert relevance["changed-path-ownership"]["basis_source_type"] == "explicit-state-and-contract"
    assert relevance["active-planning-task-switch"]["projection_fact_id"] == "planning:active-state-obligations"
    assert relevance["configured-proof-closeout"]["shown_because"] == ["contract.verification_manifest", "state.proof_route_selected"]


def test_local_overlay_report_section_and_projection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"
""",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_overlay", "--format", "json"]) == 0
    absent = json.loads(capsys.readouterr().out)["answer"]
    assert absent["status"] == "absent"

    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[local_overlay.guidance.local_cli]
signal = "local-tool-availability"
category = "tooling"
applies_to_paths = ["tools/**"]
guidance = "Use the checkout-local CLI."
required_commands = ["python -c \\"print('tool ok')\\""]
impact = "advisory"

[local_overlay.high_risk.guardrails.fixtures]
applies_to_paths = ["tests/fixtures/**"]
sensitive_data = ["real customer email"]
synthetic_fixture_guidance = ["Use example.com addresses."]
impact = "claim-limiting"
unsupported_policy_override = true
""",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_overlay", "--format", "json"]) == 0
    configured = json.loads(capsys.readouterr().out)["answer"]
    assert configured["status"] == "configured"
    assert configured["configured_count"] == 2
    assert configured["ordinary_guidance_count"] == 1
    assert configured["high_risk_profile_count"] == 1
    assert configured["ordinary_guidance"][0]["source_layer"] == "repo-local-override"
    assert configured["high_risk_profile"]["detail_selector"] == "local_high_risk_overlay"
    assert "unsupported_policy_override" in configured["warnings"][0]
    assert "checked-in host policy" in configured["authority_boundary"]["rule"]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_high_risk_overlay", "--format", "json"]) == 0
    high_risk = json.loads(capsys.readouterr().out)["answer"]
    assert high_risk["configured_count"] == 1
    assert high_risk["sections"]["guardrails"][0]["source_layer"] == "repo-local-override"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "configuration_projection", "--format", "json"]) == 0
    projection = json.loads(capsys.readouterr().out)["answer"]
    overlay_row = next(row for row in projection["facts"] if row["field"] == "local_overlay.*")
    assert overlay_row["projection_status"] in {"active", "selector-backed"}
    assert "local_overlay" in overlay_row["ordinary_path_routes"][0]


def test_local_overlay_ordinary_guidance_projects_without_high_risk(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[local_overlay.guidance.local_cli]
signal = "local-tool-availability"
category = "tooling"
applies_to_paths = ["tools/**"]
guidance = "Use the checkout-local CLI."
required_commands = ["python -c \\"print('tool ok')\\""]
impact = "advisory"

[local_overlay.guidance.stack]
signal = "branch-stack-convention"
category = "workflow"
applies_to_task_markers = ["stacked pr"]
guidance = "Keep local stack order when preparing PRs."
impact = "claim-limiting"
""",
    )
    _write(tmp_path / "tools" / "run.py", "print('ok')\n")

    assert (
        cli.main(["proof", "--target", str(tmp_path), "--changed", "tools/run.py", "--task", "Validate the local tool", "--format", "json"])
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["identity"]["proof_subject"]["changed_paths"] == ["tools/run.py"]
    local_guidance = payload["guidance"]["local_overlay"]
    assert local_guidance["status"] == "active"
    assert local_guidance["ordinary_guidance_count"] == 1
    assert local_guidance["guidance"] == [
        {
            "id": "local_cli",
            "signal": "local-tool-availability",
            "category": "tooling",
            "guidance": "Use the checkout-local CLI.",
            "required_commands": ["python -c \"print('tool ok')\""],
            "impact": "advisory",
        }
    ]
    assert payload.get("high_risk_overlay") is None


def test_report_ordinary_agent_path_is_phase_question_first(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0

    router = json.loads(capsys.readouterr().out)
    _assert_json_payload_under(router, 12_000, label="report ordinary compact payload", sort_keys=False)
    decision = router["decision_packet"]
    assert decision["surface"] == "report"
    assert decision["phase_question"] == "Which report fact changes the next action?"
    assert decision["absence_states"]["high_volume_sections"] == "detail_omitted"
    ordinary_path = router["context"]["report_profile"]["ordinary_agent_path"]
    assert ordinary_path["primary_design_unit"] == "phase_question"
    assert ordinary_path["rule"] == "Answer the current phase question first; commands are routed affordances, not the workflow."
    assert [item["phase"] for item in ordinary_path["phase_questions"]] == [
        "startup",
        "work_shaping",
        "governing_knowledge",
        "implementation_context",
        "proof",
        "closeout",
        "continuation",
    ]
    assert ordinary_path["phase_questions"][0]["question"] == "What is the smallest safe context before acting?"
    assert ordinary_path["phase_questions"][3]["phase"] == "implementation_context"
    assert ordinary_path["phase_questions"][6]["question"] == "How can a future agent resume without replaying chat?"
    assert ordinary_path["lane_completion_model"]["detail_section"] == "report_profile"


def test_report_defaults_use_router_without_full_report_or_local_footprint(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)

    def _unexpected(*args, **kwargs):
        raise AssertionError("ordinary report must not run full report or local-footprint diagnostics")

    monkeypatch.setattr(cli, "_run_report_command", _unexpected)
    monkeypatch.setattr(cli, "_local_footprint_payload", _unexpected)

    assert cli.main(["report", "--target", str(tmp_path)]) == 0

    output = capsys.readouterr().out
    assert "Command: report" in output

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision_packet"]["surface"] == "report"


def test_report_router_and_findings_section_do_not_construct_module_lifecycle_reports(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)

    def _unexpected(*args, **kwargs):
        raise AssertionError("bounded report routes must not construct module lifecycle reports")

    monkeypatch.setattr(workspace_runtime_core, "_run_lifecycle_command", _unexpected)
    monkeypatch.setattr(workspace_runtime_core, "_selected_module_reports", _unexpected)

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0
    router = json.loads(capsys.readouterr().out)
    assert router["decision_packet"]["surface"] == "report"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "findings", "--format", "json"]) == 0
    findings = json.loads(capsys.readouterr().out)["answer"]
    assert findings["kind"] == "agentic-workspace/findings-projection/v1"
    assert findings["construction_boundary"]["full_report_constructed"] is False
    assert findings["construction_boundary"]["module_reports_constructed"] is False


def test_selected_start_decision_route_is_narrow_and_preserves_claim_and_assignment_identity(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)

    def _unexpected(*args, **kwargs):
        raise AssertionError("selected decision route must not construct the broad start payload")

    monkeypatch.setattr(workspace_runtime_startup, "_start_payload", _unexpected)
    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Summarize current dogfooding signals",
                "--select",
                "dogfooding_signal_status,action_signals,task_assignment_disposition",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    signals = payload["values"]["action_signals"]
    assert signals["construction_profile"]["broad_start_payload_constructed"] is False
    assert "blocked_claims" in signals["claim_boundary"]
    disposition = payload["values"]["task_assignment_disposition"]
    assert disposition["evaluation_state"] in {"evaluated-local", "delegated", "transport-blocked", "unevaluated"}
    assert disposition["assignment_decision_revision"]


def test_task_assignment_disposition_distinguishes_deliberate_local_and_external_action() -> None:
    local = workspace_runtime_core._task_assignment_disposition_payload(
        assignment_decision={
            "selected_target": "current",
            "current_target": "current",
            "assignment_decision_revision": "sha256:local",
            "candidate_scores": [{"target": "current", "ranking_components": {}, "eligibility": {}}],
        },
        assignment_gate={"implementation_allowed": True, "required_next_action": "continue"},
        assignment_action={"status": "direct-current-target", "selected_target": "current", "action": "continue"},
        effective_orchestration={"transport": {"effective_mode": "auto"}},
    )
    assert local["outcome"] == "execute-here"
    assert local["current_target_deliberately_retained"] is True
    assert local["external_receipt"]["required"] is False

    delegated = workspace_runtime_core._task_assignment_disposition_payload(
        assignment_decision={
            "selected_target": "worker",
            "current_target": "current",
            "assignment_decision_revision": "sha256:external",
            "candidate_scores": [{"target": "worker", "ranking_components": {}, "eligibility": {}}],
        },
        assignment_gate={"implementation_allowed": False, "required_next_action": "dispatch"},
        assignment_action={
            "status": "ready",
            "selected_target": "worker",
            "action": "dispatch",
            "operation_invocation": {"operation_id": "assignment.export"},
        },
        effective_orchestration={"transport": {"effective_mode": "auto"}},
    )
    assert delegated["outcome"] == "delegate-bounded-slice"
    assert delegated["next_action"]["operation_invocation"]["operation_id"] == "assignment.export"
    assert delegated["external_receipt"]["required"] is True


def test_report_selector_bypasses_projection_dependency_discovery(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)

    def _unexpected(*args, **kwargs):
        raise AssertionError("selected report output must not pay the broad projection dependency digest")

    monkeypatch.setattr(cli, "lookup_projection_reuse", _unexpected)

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(tmp_path),
                "--select",
                "decision_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["values"]["decision_packet"]["surface"] == "report"


def test_local_footprint_tree_scan_reports_truncation_at_its_entry_budget(tmp_path: Path) -> None:
    from agentic_workspace import workspace_runtime_core

    root = tmp_path / ".agentic-workspace" / "local"
    for index in range(10):
        _write(root / f"artifact-{index}.txt", "evidence\n")

    payload = workspace_runtime_core._tree_size_payload(
        path=root,
        target_root=tmp_path,
        max_entries=3,
        time_budget_seconds=1.0,
    )

    assert payload["scan_status"] == "truncated"
    assert payload["truncated"] is True
    assert payload["file_count"] <= 3
    assert payload["scan_limits"] == {"max_entries": 3, "time_budget_seconds": 1.0}


def test_local_footprint_git_probe_timeout_is_reported_as_unavailable(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import workspace_runtime_core

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(workspace_runtime_core.subprocess, "run", _timeout)

    status, detail = workspace_runtime_core._git_lines(target_root=tmp_path, args=["status", "--short"])

    assert status == "unavailable"
    assert "timed out" in detail[0]


def test_report_exposes_communication_contract_in_router_and_output_contract(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0

    router = json.loads(capsys.readouterr().out)
    contract = router["communication_contract"]
    assert contract["kind"] == "agentic-workspace/communication-contract/v1"
    assert contract["surface"] == "report"
    assert contract["default_posture"] == "decision_first_state_backed"
    assert "handoff_review" in contract["phase_ids"]
    assert "current_decision" not in router
    assert "message_economy" not in router
    assert cli.main(["report", "--target", str(tmp_path), "--section", "output_contract", "--format", "json"]) == 0

    selected = json.loads(capsys.readouterr().out)["answer"]
    assert selected["communication_contract"]["phase_expectations"]["handoff_review"]["include"] == [
        "finding_or_change",
        "evidence_ref",
        "risk_or_residue",
        "next_owner",
    ]
    assert selected["communication_contract"]["required_order"] == [
        "decision_or_finding",
        "why_it_matters",
        "evidence_or_proof_route",
        "residue_or_boundary",
        "next_safe_action",
    ]


def test_report_exposes_reasoning_economy_evidence_section(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "reasoning_economy", "--format", "json"]) == 0

    selected = json.loads(capsys.readouterr().out)
    answer = selected["answer"]
    assert answer["kind"] == "agentic-workspace/reasoning-economy-evidence/v1"
    assert answer["scope"] == "visible_external_artifacts_only"
    assert answer["evidence_class_ids"] == ["direct", "adjacent", "none"]
    assert answer["required_visible_fields"] == [
        "decision_or_finding",
        "proof_boundary",
        "residue_or_boundary",
        "next_action_or_closure_status",
    ]
    assert answer["visible_response_compiler"]["kind"] == "agentic-workspace/visible-state-delta-response/v1"
    assert answer["visible_response_compiler"]["parts"]["next_safe_action"] == "Use the compact visible-state-delta response parts."
    assert answer["state_delta_replay_evidence"]["kind"] == "agentic-workspace/state-delta-replay-evidence/v1"
    assert answer["state_delta_replay_evidence"]["workflow_class_count"] >= 2
    assert "review-rereview" in answer["state_delta_replay_evidence"]["example_ids"]
    assert answer["ledger_refs"] == []
    assert "PR #1955" not in json.dumps(answer)
    fixture_results = {item["id"]: item for item in answer["fixture_results"]}
    assert fixture_results["visible-closeout-artifact"]["result"] == "pass"
    assert fixture_results["tool-chronology-without-claim-boundary"]["result"] == "flag"
    assert fixture_results["tool-chronology-without-claim-boundary"]["negative_signal_detected"] == "low_value_tool_chronology"
    assert "hidden chain-of-thought grading" in answer["non_goals"]

    assert cli.main(["report", "--target", str(tmp_path), "--verbose", "--format", "json"]) == 0
    full = json.loads(capsys.readouterr().out)
    assert full["reasoning_economy"]["evidence_classes"]["direct"]["definition"].startswith("A visible PR")
    assert full["reasoning_economy"]["behavior_check"]["applies_to"] == [
        "PR body",
        "review closeout",
        "report section",
        "closeout_report",
        "handoff summary",
    ]
    assert full["reasoning_economy"]["evidence_ledger_source"]["status"] == "absent"
    assert full["reasoning_economy"]["visible_response_compiler"]["source_packets"] == [
        "current_decision",
        "message_economy",
        "evidence_bundle",
    ]
    replay_examples = {item["id"]: item for item in full["reasoning_economy"]["state_delta_replay_evidence"]["examples"]}
    assert replay_examples["handoff-continuation"]["workflow_class"] == "handoff"
    assert all(item["observed_cost"]["snapshot_loads"] == 1 for item in replay_examples.values())
    assert all(item["observed_cost"]["snapshot_reused"] is True for item in replay_examples.values())
    assert "proof boundary remains visible" in full["reasoning_economy"]["state_delta_replay_evidence"]["safety_preserved"]


def test_report_reasoning_economy_reads_repo_owned_evidence_ledger(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    ledger_path = tmp_path / ".agentic-workspace" / "verification" / "reasoning-economy-evidence.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/reasoning-economy-evidence-ledger/v1",
                "owner": "test-repo",
                "entries": [
                    {
                        "ref": "PR #1955",
                        "evidence_class": "direct",
                        "visible_artifact_signal": "Visible closeout preserved proof and residue.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "reasoning_economy", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["ledger_refs"] == ["PR #1955"]
    assert answer["detail_selector"] == "reasoning_economy"

    assert cli.main(["report", "--target", str(tmp_path), "--verbose", "--format", "json"]) == 0
    full = json.loads(capsys.readouterr().out)
    source = full["reasoning_economy"]["evidence_ledger_source"]
    assert source["status"] == "loaded"
    assert source["path"] == ".agentic-workspace/verification/reasoning-economy-evidence.json"
    assert full["reasoning_economy"]["evidence_ledger"][0]["ref"] == "PR #1955"


def test_report_ordinary_agent_path_carries_lane_completion_model(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0

    router = json.loads(capsys.readouterr().out)
    ordinary_path = router["context"]["report_profile"]["ordinary_agent_path"]
    lane_model = ordinary_path["lane_completion_model"]
    assert lane_model["kind"] == "agentic-workspace/ordinary-lane-completion-model/v1"
    assert lane_model["visibility_question"].startswith("Does this surface change")
    assert "claim_boundary" in lane_model["minimal_survivor_shape"]
    assert lane_model["restart_scenario_ids"] == [
        "direct-work",
        "known-changed-paths",
        "active-lane-continuation",
        "takeover-or-recovery",
        "parent-lane-closeout",
    ]
    assert lane_model["affordance_first_rule_count"] == 7
    assert lane_model["detail_section"] == "report_profile"
    assert lane_model["absence_state"] == "full_model_hidden_behind_detail_route"


def test_selective_surfacing_evaluation_fails_on_missing_guidance_or_compact_noise(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    config = cli._load_workspace_config(target_root=tmp_path)
    projection = cli._configuration_projection_payload(config=config)
    compact = cli._compact_configuration_projection_payload(projection)

    noisy_compact = {**compact, "facts": projection["facts"]}
    noisy_evaluation = cli._selective_surfacing_evaluation_payload(
        projection_payload=projection,
        compact_projection=noisy_compact,
        cli_invoke=config.cli_invoke,
    )
    noisy_checks = {check["id"]: check for check in noisy_evaluation["checks"]}
    assert noisy_checks["irrelevant-guidance-suppressed-from-compact-output"]["result"] == "fail"
    assert noisy_evaluation["status"] == "fail"

    broken_projection = {**projection, "facts": [{"id": "broken:row", "projection_status": "active"}]}
    missing_evaluation = cli._selective_surfacing_evaluation_payload(
        projection_payload=broken_projection,
        compact_projection=compact,
        cli_invoke=config.cli_invoke,
    )
    missing_checks = {check["id"]: check for check in missing_evaluation["checks"]}
    assert missing_checks["required-guidance-present"]["result"] == "fail"
    assert missing_checks["required-guidance-present"]["evidence"] == ["broken:row"]
    assert missing_checks["typed-relevance-basis-present"]["result"] == "fail"
    assert missing_evaluation["finding_routing"]["rule"].startswith("Route failed checks")


def test_improvement_intake_includes_repair_recurrence_subtype(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--section", "improvement_intake", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    subtypes = {item["id"]: item for item in payload["answer"]["payload"]["subtypes"]}
    repair = subtypes["repair_recurrence"]
    assert repair["source"] == "doctor.repair_actions or doctor.manual_review_actions"
    assert repair["selector"] == "agentic-workspace defaults --section repair_recovery --format json"
    assert "affordance" in repair["correct_by_design_remedies"]


def test_summary_task_scoped_profile_omits_historical_audit_detail(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(target),
                "--task",
                "Implement adaptive read action routing",
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"kind", "target_root", "continuation_view", "projection_reuse"}
    assert payload["kind"] == "planning-summary/v1"
    assert "select" in payload["continuation_view"]["detail_routes"]
    assert "verbose" in payload["continuation_view"]["detail_routes"]
    assert "detail_commands" not in payload
    assert "task_scope" not in payload
    assert "historical_audit_pressure" not in json.dumps(payload)


def test_adaptive_assurance_end_to_end_closeout_flow(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(tmp_path / "tests" / "test_access_control.py", "def test_access_control_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
strict_closeout = true

[assurance.proof_profiles.access_control]
required_commands = ["uv run pytest tests/test_access_control.py"]
optional_commands = ["uv run pytest tests/test_auth_integration.py"]
review_aids = [".agentic-workspace/agent-aids/access-control.md"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "high-assurance", status = "in-progress", surface = ".agentic-workspace/planning/execplans/high-assurance.plan.json", why_now = "dogfood assurance closeout.", next_action = "run proof selection.", done_when = "closeout gates are proved." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    def completed_record(item_id: str, title: str, status: str = "completed") -> dict[str, object]:
        record = planning_installer._build_execplan_record_from_todo_item(
            title=title,
            item_id=item_id,
            status=status,
            why_now="dogfood assurance flow.",
            next_action="archive the plan.",
            done_when="archive gate is satisfied.",
        )
        record["delegated_judgment"] = {
            "requested outcome": "prove the assurance workflow",
            "hard constraints": "keep this synthetic and generic",
            "agent may decide locally": "fixture details",
            "escalate when": "closeout gates are unclear",
        }
        record["execution_summary"] = {
            "outcome delivered": "Synthetic assurance flow proved.",
            "validation confirmed": "uv run pytest tests/test_workspace_cli.py",
            "follow-on routed to": "none; issue closeout can proceed",
            "post-work posterity capture": "the test preserves the workflow contract",
            "resume from": "no further action",
        }
        record["proof_report"] = {
            "validation proof": "uv run pytest tests/test_workspace_cli.py",
            "proof achieved now": "proof and archive gates passed",
            'evidence for "proof achieved" state': "synthetic fixture exercised the flow",
        }
        record["intent_satisfaction"] = {
            "original intent": "prove adaptive assurance end to end",
            "was original intent fully satisfied?": "yes",
            "evidence of intent satisfaction": "summary, proof, and archive gate were exercised",
            "unsolved intent passed to": "none",
        }
        record["closure_check"] = {
            "slice status": "bounded slice complete",
            "larger-intent status": "closed",
            "closure decision": "archive-and-close",
            "why this decision is honest": "all synthetic acceptance signals passed",
            "evidence carried forward": "this regression test",
            "reopen trigger": "assurance output stops blocking missing gates",
        }
        record["active_milestone"] = {
            "id": item_id,
            "status": status,
            "scope": "Keep this synthetic assurance fixture bounded.",
            "ready": "ready",
            "blocked": "none",
        }
        return record

    high_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "high-assurance.plan.json"
    high = completed_record("high-assurance", "High Assurance", status="in-progress")
    high["adaptive_assurance"] = {
        "level": "high",
        "reason": "synthetic access-control slice",
        "agent_may_escalate": True,
        "agent_may_deescalate": False,
        "strict_closeout": True,
        "required_refs": ["security_refs"],
        "proof_profiles": ["access_control"],
        "required_gates": ["security-review"],
    }
    high["traceability_refs"] = {"security_refs": []}
    high["control_gates"] = [{"id": "security-review", "status": "pending", "blocking": True, "evidence": []}]
    high["implementation_blockers"] = [{"id": "policy", "status": "blocked", "do_not_implement": True}]
    planning_installer._write_execplan_record(record_path=high_path, record=high)

    low_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "low-assurance.plan.json"
    low = completed_record("low-assurance", "Low Assurance")
    planning_installer._write_execplan_record(record_path=low_path, record=low)

    summary = planning_installer.planning_summary(target=tmp_path, profile="compact")
    assert summary["planning_record"]["adaptive_assurance"]["level"] == "high"

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )
    proof_answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_access_control.py" in proof_answer["required_commands"]
    assert proof_answer["planning_assurance"]["closeout_status"] == "blocked"
    assert proof_answer["planning_assurance"]["missing_required_refs"] == ["security_refs"]
    assert proof_answer["planning_assurance"]["pending_blocking_gates"][0]["id"] == "security-review"

    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "high-assurance", status = "completed", surface = ".agentic-workspace/planning/execplans/high-assurance.plan.json", why_now = "dogfood assurance closeout.", next_action = "archive after gate.", done_when = "closeout gates are proved." },
  { id = "low-assurance", status = "completed", surface = ".agentic-workspace/planning/execplans/low-assurance.plan.json", why_now = "prove low ceremony.", next_action = "archive directly.", done_when = "low ceremony remains cheap." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    high["active_milestone"]["status"] = "completed"
    high["lifecycle"] = "closed"
    high["phase"] = "complete"
    planning_installer._write_execplan_record(record_path=high_path, record=high)

    blocked = planning_installer.archive_execplan("high-assurance", target=tmp_path, dry_run=True)
    assert any(warning["warning_class"] == "archive_adaptive_assurance_blocked" for warning in blocked.warnings), blocked.warnings

    high["traceability_refs"] = {"security_refs": ["SEC-1"]}
    high["control_gates"] = [{"id": "security-review", "status": "waived", "blocking": True, "evidence": ["waiver:SEC-1"]}]
    high["implementation_blockers"] = [{"id": "policy", "status": "waived", "do_not_implement": True}]
    planning_installer._write_execplan_record(record_path=high_path, record=high)

    satisfied = planning_installer.archive_execplan("high-assurance", target=tmp_path, dry_run=True)
    assert not [warning for warning in satisfied.warnings if warning["warning_class"] == "archive_adaptive_assurance_blocked"]
    assert any(action.kind == "would remove" for action in satisfied.actions)

    low_result = planning_installer.archive_execplan("low-assurance", target=tmp_path, dry_run=True)
    assert not [warning for warning in low_result.warnings if warning["warning_class"] == "archive_adaptive_assurance_blocked"]
    assert any(action.kind == "would remove" for action in low_result.actions)


def test_summary_uses_immediate_next_action_and_warns_on_duplicate_drift(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "drifted", title = "Drifted", maturity = "active", status = "active", path = ".agentic-workspace/planning/execplans/drifted.plan.json", durable_residue = "pending", residue_owner = "this-execplan", residue_promotion_trigger = "closeout" },
]

[active]
execplans = [
  ".agentic-workspace/planning/execplans/drifted.plan.json",
]

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Drifted",
        item_id="drifted",
        status="active",
        why_now="prove next action drift.",
        next_action="legacy markdown-like next action.",
        done_when="summary uses the machine next step.",
    )
    record["canonical_core"] = {"next_action": "canonical core next action."}
    record["machine_readable_contract"] = {
        "execution": {
            "next_step": "canonical machine next action.",
        }
    }
    planning_installer._write_execplan_record(
        record_path=tmp_path / ".agentic-workspace" / "planning" / "execplans" / "drifted.plan.json",
        record=record,
    )

    summary = planning_installer.planning_summary(target=tmp_path, profile="compact")

    assert summary["planning_record"]["next_action"] == "legacy markdown-like next action."
    assert summary["resumable_contract"]["current_next_action_source"] == "next_action"
    assert any(
        warning["warning_class"] == "execplan_canonical_projection_drift" for warning in summary["planning_surface_health"]["warnings"]
    )


def test_archive_plan_reports_exact_required_traceability_ref_paths(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    record = planning_installer._build_execplan_record_from_todo_item(
        title="Missing Traceability",
        item_id="missing-traceability",
        status="completed",
        why_now="prove closeout field paths.",
        next_action="archive after proof.",
        done_when="archive warning is actionable.",
    )
    record.update(
        {
            "delegated_judgment": {
                "requested outcome": "prove strict closeout paths",
                "hard constraints": "synthetic only",
                "agent may decide locally": "fixture shape",
                "escalate when": "paths are ambiguous",
            },
            "execution_summary": {
                "outcome delivered": "Synthetic strict closeout path proved.",
                "validation confirmed": "pytest",
                "follow-on routed to": "none",
                "post-work posterity capture": "test",
                "resume from": "none",
            },
            "proof_report": {
                "validation proof": "pytest",
                "proof achieved now": "yes",
                'evidence for "proof achieved" state': "test",
            },
            "intent_satisfaction": {
                "original intent": "prove strict closeout paths",
                "was original intent fully satisfied?": "yes",
                "evidence of intent satisfaction": "test",
                "unsolved intent passed to": "none",
            },
            "closure_check": {
                "slice status": "complete",
                "larger-intent status": "closed",
                "closure decision": "archive-and-close",
                "why this decision is honest": "synthetic proof exists",
                "evidence carried forward": "test",
                "reopen trigger": "warning loses field paths",
            },
            "adaptive_assurance": {
                "strict_closeout": True,
                "required_refs": ["security_refs"],
            },
            "traceability_refs": {
                "requirement_refs": ["#1"],
            },
            "durable_residue": {
                "status": "none",
                "learned constraint": "No reusable product constraint in this synthetic fixture.",
                "motivation worth preserving": "Only the archive-size guardrail behavior matters.",
                "canonical owner now": "none",
                "promotion trigger": "none",
                "retention after promotion": "retain",
            },
        }
    )
    planning_installer._write_execplan_record(
        record_path=tmp_path / ".agentic-workspace" / "planning" / "execplans" / "missing-traceability.plan.json",
        record=record,
    )

    result = planning_installer.archive_execplan("missing-traceability", target=tmp_path, dry_run=True)

    warning = next(warning for warning in result.warnings if warning["warning_class"] == "archive_adaptive_assurance_blocked")
    assert "traceability_refs.security_refs" in warning["message"]
    assert "adaptive_assurance.required_refs names traceability_refs field names" in warning["message"]


def test_archive_plan_blocks_oversized_archive_before_write(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / "src" / "agentic_workspace" / "contracts" / "structured_file_inventory.json",
        """
{
  "entries": [
    {
      "pattern": ".agentic-workspace/planning/execplans/archive/*.plan.json",
      "guardrails": {
        "max_bytes": 300
      }
    }
  ]
}
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Too Large",
        item_id="too-large",
        status="completed",
        why_now="prove archive guardrail.",
        next_action="archive after distillation.",
        done_when="archive refuses oversized records.",
    )
    record.update(
        {
            "goal": ["x" * 600],
            "delegated_judgment": {
                "requested outcome": "prove archive size guardrail",
                "hard constraints": "synthetic only",
                "agent may decide locally": "fixture shape",
                "escalate when": "archive writes too early",
            },
            "execution_summary": {
                "outcome delivered": "Synthetic archive size guardrail proved.",
                "validation confirmed": "pytest",
                "follow-on routed to": "none",
                "post-work posterity capture": "test",
                "resume from": "none",
            },
            "proof_report": {
                "validation proof": "pytest",
                "proof achieved now": "yes",
                'evidence for "proof achieved" state': "test",
            },
            "intent_satisfaction": {
                "original intent": "prove archive size guardrail",
                "was original intent fully satisfied?": "yes",
                "evidence of intent satisfaction": "test",
                "unsolved intent passed to": "none",
            },
            "closure_check": {
                "slice status": "complete",
                "larger-intent status": "closed",
                "closure decision": "archive-and-close",
                "why this decision is honest": "synthetic proof exists",
                "evidence carried forward": "test",
                "reopen trigger": "archive writes oversized record",
            },
            "durable_residue": {
                "status": "none",
                "learned constraint": "No reusable product constraint in this synthetic fixture.",
                "motivation worth preserving": "Only the archive-size guardrail behavior matters.",
                "canonical owner now": "none",
                "promotion trigger": "none",
                "retention after promotion": "retain",
            },
        }
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "too-large.plan.json"
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    result = planning_installer.archive_execplan("too-large", target=tmp_path, dry_run=True, retain_archive=True)

    assert record_path.exists()
    assert not (tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "too-large.plan.json").exists()
    warning = next(warning for warning in result.warnings if warning["warning_class"] == "archive_size_guardrail_blocked")
    assert "max_bytes=300" in warning["message"]
    assert any(action.kind == "manual review" for action in result.actions)


def test_summary_surfaces_broad_work_planning_guard_for_narrow_direct_state(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = []

[active]
execplans = []

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    summary = planning_installer.planning_summary(target=tmp_path, profile="compact")

    guard = summary["execution_readiness"]["broad_work_planning_guard"]
    assert guard["status"] == "available-if-work-widens"
    assert "high-assurance" in guard["applies_to"]
    assert "repo-visible durable state" in guard["durable_state_rule"]
    assert ".agentic-workspace/planning/execplans/<id>.plan.json" in guard["canonical_durable_state_surfaces"]
    assert "new-plan" in guard["new_plan_command"]
    assert "do not create product" in guard["planning_only_rule"]
    assert "do not stop at a proposal" in guard["prep_only_route"]["required_action"]
    assert any("planning/records" in item for item in guard["prep_only_route"]["do_not_do"])
    assert any("HANDOFF" in item and "package" in item for item in guard["prep_only_route"]["do_not_do"])
    assert summary["execution_readiness"]["direct_work_allowed"] is True
