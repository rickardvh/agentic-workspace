from __future__ import annotations

import json
import os
import subprocess
import time
import tomllib
from pathlib import Path

import pytest
from repo_planning_bootstrap.installer import install_bootstrap
from tests.workspace_cli_support import cli

from agentic_workspace import workspace_runtime_core
from agentic_workspace.workspace_runtime_primitives import _memory_decision_packet_payload, _operating_loop_decision_payload


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_execplan() -> str:
    return (
        "# Plan Alpha\n\n"
        "## Goal\n\n"
        "- Requested outcome: Keep scope clear.\n\n"
        "## Next Action\n\n"
        "- Add one checker.\n\n"
        "## Completion Criteria\n\n"
        "- Warning classes are emitted for known drift.\n\n"
        "## Proof\n\n"
        "- uv run pytest tests/test_check_planning_surfaces.py\n\n"
        "## Milestone Status\n\n"
        "- Status: active\n"
    )


def test_workspace_summary_json_defaults_to_tiny_profile(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "keep compact startup cheap." }
]
queued_items = []

[roadmap]
lanes = [
  { id = "tracked-lane", title = "Tracked lane", priority = "first", issues = ["EXT-1"], outcome = "Keep tracked.", reason = "Needed.", promotion_signal = "Promote when needed.", suggested_first_slice = "Do the thing." },
]
candidates = [
  { priority = "first", summary = "Tracked lane" },
]
""",
    )
    _write(tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.md", _minimal_execplan())

    exit_code = cli.main(["summary", "--target", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["profile"] == "tiny"
    assert payload["schema"]["schema_version"] == "planning-summary-tiny-schema/v1"
    assert payload["schema"]["select_command"] == "agentic-workspace summary --select <field.path> --format json"
    assert payload["schema"]["verbose_command"] == "agentic-workspace summary --verbose --format json"
    assert set(payload) <= {
        "kind",
        "profile",
        "schema",
        "target_root",
        "todo",
        "execplans",
        "planning_surface_health",
        "execution_readiness",
        "current_execution_pressure",
        "decision_packet",
        "continuation_view",
        "decomposition",
        "lanes",
        "residue_governance",
        "roadmap",
        "detail_commands",
        "selector_inventory",
        "warning_count",
        "memory_consult",
    }
    assert payload["selector_inventory"]["status"] == "omitted-from-compact-default"
    assert payload["selector_inventory"]["available_count"] == 9
    assert payload["selector_inventory"]["exact_select_command"] == "agentic-workspace summary --select <field.path> --format json"
    assert "candidate_lanes" not in payload["roadmap"]


def test_workspace_summary_quiet_default_packet_stays_within_four_kib(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    assert cli.main(["summary", "--target", str(tmp_path), "--format", "json"]) == 0
    output = capsys.readouterr().out

    assert len(output.encode("utf-8")) <= 4096


def test_report_closeout_trust_surfaces_memory_decision_packet(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "closeout_trust", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    closeout = payload["answer"]
    packet = closeout["memory_decision_packet"]

    assert packet["kind"] == "agentic-workspace/memory-decision-packet/v1"
    assert packet["stage"] == "closeout"
    assert packet["force"] == "not_applicable"
    assert packet["capture"]["status"] == "none_found"
    assert "planning" in packet["capture"]["candidate_owner_surfaces"]
    assert "repo_memory" in packet["capture"]["candidate_owner_surfaces"]
    assert "local_memory" in packet["capture"]["candidate_owner_surfaces"]
    assert packet["capture"]["agent_decision_required"] is False
    loop = closeout["operating_loop"]
    assert loop["kind"] == "agentic-workspace/operating-loop-decision/v1"
    assert loop["memory"]["state"] in {"dismissed", "not_applicable", "pulled"}
    assert loop["verification"]["state"] in {"proof_not_required", "proof_passed"}
    assert loop["safe_claim"] in {"full", "partial", "blocked", "none"}


def _closeout_report_with_installed_state(tmp_path: Path, *, changed_surfaces: str, requested_outcome: str) -> dict[str, object]:
    config = workspace_runtime_core._load_workspace_config(target_root=tmp_path)
    installed_state = {
        "status": "payload-upgrade-required",
        "action_effect": {
            "force": "required_before_claim",
            "resolution_command": "agentic-workspace upgrade --target . --dry-run --format json",
            "claim_boundary": "do not claim installed payload freshness",
        },
    }
    active_record = {
        "execution_run": {
            "what happened": "Finished the slice.",
            "changed surfaces": changed_surfaces,
        },
        "delegated_judgment": {"requested outcome": requested_outcome},
        "proof_report": {
            "validation proof": "uv run pytest tests/test_workspace_summary_cli.py",
            "proof achieved now": "yes",
        },
        "closure_check": {"closure decision": "archive-and-close"},
    }
    return workspace_runtime_core._derived_continuation_projection_payloads(
        target_root=tmp_path,
        config=config,
        source_payload={
            "closeout_trust": {},
            "installed_state_compatibility": installed_state,
            "architecture_principles": {},
        },
        active_planning_record=active_record,
        assurance_requirements={},
        verification={},
        external_work_delta={"status": "not-evaluated"},
        external_work_reconciliation={"status": "not-evaluated"},
    )["closeout_report"]


def test_closeout_report_routes_unrelated_installed_state_drift_as_residue(tmp_path: Path) -> None:
    report = _closeout_report_with_installed_state(
        tmp_path,
        changed_surfaces="docs/typo.md",
        requested_outcome="Fix one docs typo.",
    )

    residue = report["installed_state_residue"]
    assert residue["status"] == "separate_maintenance_residue"
    assert residue["current_task_proof_effect"] == "not_blocking_narrow_task_proof"
    assert residue["residue"]["owner"] == "installed-payload-sync"
    assert residue["triage"]["status"] == "waived_for_narrow_work"
    assert report["gaps_and_residual_risk"]["installed_state_residue"]["status"] == "separate_maintenance_residue"


def test_closeout_report_keeps_installed_state_drift_blocking_for_owned_surfaces(tmp_path: Path) -> None:
    report = _closeout_report_with_installed_state(
        tmp_path,
        changed_surfaces="src/agentic_workspace/workspace_runtime_core.py",
        requested_outcome="Verify payload freshness before release.",
    )

    residue = report["installed_state_residue"]
    assert residue["status"] == "current_task_blocking"
    assert residue["current_task_proof_effect"] == "blocking"
    assert residue["triage"]["claim_relevant"] is True
    assert residue["changed_paths_considered"] == ["src/agentic_workspace/workspace_runtime_core.py"]


def test_closeout_report_composes_closeout_ready_phase_answer(tmp_path: Path) -> None:
    report = _closeout_report_with_installed_state(
        tmp_path,
        changed_surfaces="src/agentic_workspace/workspace_runtime_core.py",
        requested_outcome="Verify payload freshness before release.",
    )

    ready = report["closeout_ready"]
    remaining_by_id = {item["id"]: item for item in ready["remaining_actions"]}

    assert ready["kind"] == "agentic-workspace/closeout-ready-phase-answer/v1"
    assert ready["status"] == "blocked"
    assert ready["proof_status"]["state"] == "satisfied"
    assert ready["planning_owner"]["state"] == "active"
    assert ready["payload_status"]["status"] == "current_task_blocking"
    assert ready["dogfooding_status"]["status"] == "not-inspected"
    assert ready["claim_authorization"]["blocked_claim_classes"]
    assert "payload" in remaining_by_id
    assert "dogfooding" in remaining_by_id
    assert "dogfooding_signal_status" in ready["drilldowns"]
    assert "Unknown, stale, or omitted evidence" in ready["conservative_unknown_rule"]


def test_closeout_ready_phase_answer_surfaces_unsafe_closure_actions() -> None:
    from agentic_workspace.workspace_runtime_proof import _closeout_ready_phase_answer_payload

    ready = _closeout_ready_phase_answer_payload(
        completion_gate={
            "status": "blocked",
            "claim_authorization": {
                "allowed_claim_classes": ["slice_complete"],
                "blocked_claim_classes": ["full_intent_complete", "issue_closure"],
                "closure_actions": [
                    {
                        "kind": "issue_closure",
                        "target": "#2113",
                        "authorized": False,
                        "reason": "parent issue closure requires full-intent completion",
                    }
                ],
                "closure_keyword_guard": {
                    "rule": "Use safe references unless issue closure is authorized.",
                    "targets": [
                        {
                            "target": "#2113",
                            "status": "blocked",
                            "unsafe_examples": ["Closes #2113"],
                            "safe_reference": "Refs #2113; does not close.",
                        }
                    ],
                },
            },
        },
        proof_execution={"status": "recorded", "proof": "pytest"},
        planning_evidence={"state": "archived", "authority": "archived-planning-evidence"},
        installed_state_residue={"status": "separate_maintenance_residue", "current_task_proof_effect": "not_blocking_narrow_task_proof"},
        workflow_compliance_summary={"status": "clear"},
        detail_commands={},
    )

    assert ready["status"] == "blocked"
    assert ready["strongest_safe_claim"] == "slice_complete"
    assert {item["kind"] for item in ready["unsafe_closure_actions"]} == {"issue_closure", "closure_keyword"}
    assert any(item["id"] == "closure_actions" for item in ready["remaining_actions"])


def test_closeout_report_section_reads_installed_state_residue(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install_bootstrap(target=tmp_path)

    def fake_installed_state_compatibility(**_: object) -> dict[str, object]:
        return {
            "status": "payload-upgrade-required",
            "action_effect": {
                "force": "required_before_claim",
                "resolution_command": "agentic-workspace upgrade --target . --dry-run --format json",
                "claim_boundary": "do not claim installed payload freshness",
            },
        }

    monkeypatch.setattr(workspace_runtime_core, "_installed_state_compatibility_payload", fake_installed_state_compatibility)
    monkeypatch.setattr(
        workspace_runtime_core,
        "_active_planning_record_for_report_section",
        lambda target_root: {
            "execution_run": {
                "what happened": "Finished the docs slice.",
                "changed surfaces": "docs/typo.md",
            },
            "delegated_judgment": {"requested outcome": "Fix one docs typo."},
            "proof_report": {"validation proof": "uv run pytest tests/test_workspace_summary_cli.py"},
        },
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "closeout_report", "--format", "json"]) == 0

    report = json.loads(capsys.readouterr().out)["answer"]
    residue = report["installed_state_residue"]
    assert residue["status"] == "separate_maintenance_residue"
    assert residue["current_task_proof_effect"] == "not_blocking_narrow_task_proof"
    assert residue["residue"]["owner"] == "installed-payload-sync"


def test_report_local_aw_state_classifies_ignored_policy_and_cache(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    _write(tmp_path / ".gitignore", ".agentic-workspace/local/\n.agentic-workspace/verification/\n")
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n")
    _write(tmp_path / ".agentic-workspace" / "local" / "cache" / "proof.json", "{}\n")
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "manifest.toml",
        'schema_version = "agentic-workspace/verification-manifest/v1"\n',
    )
    subprocess.run(["git", "add", ".gitignore", ".agentic-workspace/config.toml"], cwd=tmp_path, check=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_aw_state", "--format", "json"]) == 0

    packet = json.loads(capsys.readouterr().out)["answer"]
    assert packet["kind"] == "agentic-workspace/local-aw-state/v1"
    assert packet["ordinary_payload_presence"]["warning"] is False
    assert packet["role_counts"]["Verification/proof"] == 1
    assert packet["role_counts"]["cache/scratch"] == 1
    assert packet["state_counts"]["ignored"] == 2
    assert any(sample["role"] == "Verification/proof" for sample in packet["meaningful_samples"])


def test_report_local_aw_state_keeps_ignored_payload_only_state_quiet(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    _write(tmp_path / ".gitignore", ".agentic-workspace/planning/\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "state.toml", 'kind = "agentic-planning-state"\n')
    subprocess.run(["git", "add", ".gitignore"], cwd=tmp_path, check=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_aw_state", "--format", "json"]) == 0

    packet = json.loads(capsys.readouterr().out)["answer"]
    assert packet["status"] == "quiet"
    assert packet["ordinary_payload_presence"]["count"] == 1
    assert packet["ordinary_payload_presence"]["warning"] is False
    assert packet["meaningful_samples"] == []


def test_report_local_aw_state_surfaces_ignored_generated_proof_artifact(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    _write(tmp_path / ".gitignore", ".agentic-workspace/proof/\n")
    _write(tmp_path / ".agentic-workspace" / "proof" / "generated" / "result.json", "{}\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=tmp_path, check=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_aw_state", "--format", "json"]) == 0

    packet = json.loads(capsys.readouterr().out)["answer"]
    assert packet["status"] == "attention"
    assert packet["role_counts"]["generated artifact"] == 1
    assert packet["state_counts"]["ignored"] == 1
    assert packet["meaningful_samples"][0]["role"] == "generated artifact"


def test_report_local_aw_state_degrades_without_git(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_aw_state", "--format", "json"]) == 0

    packet = json.loads(capsys.readouterr().out)["answer"]
    assert packet["status"] == "unavailable"
    assert packet["degraded"] is True


def test_report_local_footprint_splits_managed_and_legacy_scratch(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    _write(tmp_path / ".gitignore", ".agentic-workspace/local/\nscratch/\n")
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[local_scratch_retention]\nmax_age_hours = 1\nwarn_total_bytes = 1\nlocal_aw_warn_bytes = 1\n",
    )
    run = tmp_path / ".agentic-workspace" / "local" / "scratch" / "runs" / "old-run"
    _write(
        run / ".aw-scratch.toml",
        'owner = "agentic-workspace"\ncreated_at = "2020-01-01T00:00:00+00:00"\npurpose = "test"\nproducer = "pytest"\nretention = "ephemeral"\n',
    )
    _write(run / "artifact.txt", "old\n")
    _write(tmp_path / ".agentic-workspace" / "local" / "scratch" / "legacy" / "artifact.txt", "legacy\n")
    _write(tmp_path / "scratch" / "host-owned.txt", "host\n")
    subprocess.run(["git", "add", ".gitignore", ".agentic-workspace/config.toml"], cwd=tmp_path, check=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_footprint", "--format", "json"]) == 0

    packet = json.loads(capsys.readouterr().out)["answer"]
    assert packet["kind"] == "agentic-workspace/local-footprint/v1"
    assert packet["status"] == "attention"
    scratch = packet["scratch_retention"]
    assert scratch["managed_run_count"] == 1
    assert scratch["legacy_entry_count"] == 1
    assert scratch["eligible_prune_paths"] == [".agentic-workspace/local/scratch/runs/old-run"]
    assert scratch["legacy_entries"][0]["classification"] == "legacy-aw-local-scratch"
    assert "largest_files" not in scratch["legacy_entries"][0]
    assert not any("scratch/host-owned" in json.dumps(item) for item in packet["largest_local_offenders"])
    assert packet["policy"]["source"] == ".agentic-workspace/config.local.toml"
    assert packet["next_action"]["legacy_cleanup"]["status"] == "available"
    assert " --legacy-scratch-cleanup --dry-run " in packet["next_action"]["legacy_cleanup"]["dry_run"]
    assert " --apply-legacy-scratch-cleanup " in packet["next_action"]["legacy_cleanup"]["apply_after_review"]
    assert "subtrees" not in packet
    assert " --section local_footprint --verbose --format json" in packet["detail_command"]


def test_upgrade_prunes_manifest_backed_scratch_but_preserves_legacy_and_protected(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[local_scratch_retention]\nmax_age_hours = 1\nprotected_max_age_hours = 1000000\nmax_total_bytes = 100000\n",
    )
    old_run = target / ".agentic-workspace" / "local" / "scratch" / "runs" / "old-run"
    protected_run = target / ".agentic-workspace" / "local" / "scratch" / "runs" / "protected-run"
    _write(
        old_run / ".aw-scratch.toml",
        'owner = "agentic-workspace"\ncreated_at = "2020-01-01T00:00:00+00:00"\npurpose = "test old"\nproducer = "pytest"\nretention = "ephemeral"\n',
    )
    _write(old_run / "artifact.txt", "old\n")
    _write(
        protected_run / ".aw-scratch.toml",
        'owner = "agentic-workspace"\ncreated_at = "2020-01-01T00:00:00+00:00"\npurpose = "test protected"\nproducer = "pytest"\nretention = "protected"\nprotect_until = "2999-01-01T00:00:00+00:00"\n',
    )
    _write(protected_run / "artifact.txt", "protected\n")
    legacy = target / ".agentic-workspace" / "local" / "scratch" / "legacy" / "artifact.txt"
    _write(legacy, "legacy\n")

    assert cli.main(["upgrade", "--target", str(target), "--dry-run", "--format", "json"]) == 0
    dry_run_payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in dry_run_payload["reports"] if report["module"] == "workspace")
    assert any(action["kind"] == "would remove" and action["path"].endswith("old-run") for action in workspace_report["actions"])
    assert old_run.exists()

    assert cli.main(["upgrade", "--target", str(target), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")

    assert any(action["kind"] == "removed" and action["path"].endswith("old-run") for action in workspace_report["actions"])
    assert not old_run.exists()
    assert protected_run.exists()
    assert legacy.exists()


def test_upgrade_legacy_scratch_cleanup_has_explicit_dry_run_and_apply(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    legacy_run = target / ".agentic-workspace" / "local" / "scratch" / "runs" / "legacy-run"
    legacy_top = target / ".agentic-workspace" / "local" / "scratch" / "legacy" / "deep" / "path"
    managed_run = target / ".agentic-workspace" / "local" / "scratch" / "runs" / "managed-run"
    host_scratch = target / "scratch" / "host-owned.txt"
    _write(legacy_run / "artifact.txt", "legacy run\n")
    _write(legacy_top / "artifact.txt", "legacy top\n")
    _write(
        managed_run / ".aw-scratch.toml",
        'owner = "agentic-workspace"\ncreated_at = "2999-01-01T00:00:00+00:00"\npurpose = "managed"\nproducer = "pytest"\nretention = "ephemeral"\n',
    )
    _write(managed_run / "artifact.txt", "managed\n")
    _write(host_scratch, "host\n")

    assert cli.main(["upgrade", "--target", str(target), "--legacy-scratch-cleanup", "--dry-run", "--format", "json"]) == 0
    dry_run_payload = json.loads(capsys.readouterr().out)
    workspace_report = dry_run_payload["reports"][0]
    assert dry_run_payload["cleanup_mode"] == "legacy-scratch"
    assert dry_run_payload["dry_run"] is True
    assert {action["kind"] for action in workspace_report["actions"]} == {"would remove"}
    assert {action["path"] for action in workspace_report["actions"]} == {
        ".agentic-workspace/local/scratch/legacy",
        ".agentic-workspace/local/scratch/runs/legacy-run",
    }
    assert legacy_run.exists()
    assert legacy_top.exists()

    assert (
        cli.main(
            [
                "upgrade",
                "--target",
                str(target),
                "--legacy-scratch-cleanup",
                "--apply-legacy-scratch-cleanup",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    workspace_report = payload["reports"][0]
    assert payload["dry_run"] is False
    assert {action["kind"] for action in workspace_report["actions"]} == {"removed"}
    assert not legacy_run.exists()
    assert not (target / ".agentic-workspace" / "local" / "scratch" / "legacy").exists()
    assert managed_run.exists()
    assert host_scratch.exists()


def test_legacy_scratch_cleanup_rejects_path_escape_candidates(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    outside = tmp_path / "outside-legacy"
    _write(outside / "artifact.txt", "do not delete\n")
    monkeypatch.setattr(
        workspace_runtime_core,
        "_local_scratch_runs_payload",
        lambda *, target_root, policy, **kwargs: {
            "kind": "agentic-workspace/local-scratch-runs/v1",
            "legacy_entries": [{"path": "../outside-legacy"}],
        },
    )

    result = workspace_runtime_core._cleanup_legacy_local_scratch(
        target_root=target,
        dry_run=False,
        policy=workspace_runtime_core._local_scratch_policy_payload(target_root=target),
    )

    assert outside.exists()
    assert result["actions"] == []
    assert result["warnings"][0]["message"] == "legacy scratch cleanup skipped; candidate failed path or manifest guard"


def test_legacy_scratch_cleanup_rejects_symlinked_runs_root(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    outside = tmp_path / "outside-runs"
    runs = target / ".agentic-workspace" / "local" / "scratch" / "runs"
    outside.mkdir(parents=True)
    runs.parent.mkdir(parents=True)
    try:
        runs.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    _write(outside / "legacy-run" / "artifact.txt", "legacy\n")

    result = workspace_runtime_core._cleanup_legacy_local_scratch(
        target_root=target,
        dry_run=False,
        policy=workspace_runtime_core._local_scratch_policy_payload(target_root=target),
    )

    assert (outside / "legacy-run").exists()
    assert result["actions"] == []
    assert result["warnings"][0]["message"] == "legacy scratch cleanup skipped; scratch root or runs root is a symlink"


def test_scratch_size_budget_subtracts_already_eligible_runs(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[local_scratch_retention]\nmax_age_hours = 1\nmax_total_bytes = 512\n",
    )
    old_run = target / ".agentic-workspace" / "local" / "scratch" / "runs" / "old-run"
    current_run = target / ".agentic-workspace" / "local" / "scratch" / "runs" / "current-run"
    _write(
        old_run / ".aw-scratch.toml",
        'owner = "agentic-workspace"\ncreated_at = "2020-01-01T00:00:00+00:00"\npurpose = "old"\nproducer = "pytest"\nretention = "ephemeral"\n',
    )
    _write(old_run / "artifact.bin", "x" * 600)
    _write(
        current_run / ".aw-scratch.toml",
        'owner = "agentic-workspace"\ncreated_at = "2999-01-01T00:00:00+00:00"\npurpose = "current"\nproducer = "pytest"\nretention = "ephemeral"\n',
    )
    _write(current_run / "artifact.bin", "y" * 100)

    assert cli.main(["report", "--target", str(target), "--section", "local_footprint", "--format", "json"]) == 0

    scratch = json.loads(capsys.readouterr().out)["answer"]["scratch_retention"]
    assert scratch["eligible_prune_paths"] == [".agentic-workspace/local/scratch/runs/old-run"]


def test_scratch_prune_rejects_path_escape_candidates(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    outside = tmp_path / "outside-run"
    _write(
        outside / ".aw-scratch.toml",
        'owner = "agentic-workspace"\ncreated_at = "2020-01-01T00:00:00+00:00"\npurpose = "escape"\nproducer = "pytest"\nretention = "ephemeral"\n',
    )
    _write(outside / "artifact.txt", "do not delete\n")
    monkeypatch.setattr(
        workspace_runtime_core,
        "_local_scratch_runs_payload",
        lambda *, target_root, policy: {
            "kind": "agentic-workspace/local-scratch-runs/v1",
            "eligible_prune_paths": ["../outside-run"],
        },
    )

    result = workspace_runtime_core._prune_local_scratch_runs(
        target_root=target,
        dry_run=False,
        policy=workspace_runtime_core._local_scratch_policy_payload(target_root=target),
    )

    assert outside.exists()
    assert result["actions"] == []
    assert result["warnings"][0]["message"] == "scratch prune skipped; candidate failed path or manifest guard"


def test_scratch_prune_rejects_symlinked_runs_root(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    outside = tmp_path / "outside-runs"
    runs = target / ".agentic-workspace" / "local" / "scratch" / "runs"
    outside.mkdir(parents=True)
    runs.parent.mkdir(parents=True)
    try:
        runs.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    _write(
        outside / "old-run" / ".aw-scratch.toml",
        'owner = "agentic-workspace"\ncreated_at = "2020-01-01T00:00:00+00:00"\npurpose = "escape"\nproducer = "pytest"\nretention = "ephemeral"\n',
    )

    result = workspace_runtime_core._prune_local_scratch_runs(
        target_root=target,
        dry_run=False,
        policy=workspace_runtime_core._local_scratch_policy_payload(target_root=target),
    )

    assert (outside / "old-run").exists()
    assert result["actions"] == []
    assert result["warnings"][0]["message"] == "scratch prune skipped; scratch root or runs root is a symlink"


def test_memory_decision_packet_closeout_states_are_pressure_driven() -> None:
    base = {
        "stage": "closeout",
        "cli_invoke": "agentic-workspace",
        "memory_consult": {"status": "not-recommended", "route_inspection_state": "not_checked"},
    }

    clean = _memory_decision_packet_payload(
        **base,
        closeout_trust={"trust": "normal", "lower_trust_closeout_count": 0},
    )
    dismissed = _memory_decision_packet_payload(
        **base,
        closeout_trust={
            "trust": "lower-trust",
            "lower_trust_closeout_count": 1,
            "durable_residue_action": {"action": "dismissed"},
        },
    )
    capture = _memory_decision_packet_payload(
        **base,
        closeout_trust={"trust": "lower-trust", "lower_trust_closeout_count": 1, "promotion_candidate_count": 1},
    )
    routed_packets = [
        _memory_decision_packet_payload(
            **base,
            closeout_trust={
                "trust": "lower-trust",
                "lower_trust_closeout_count": 1,
                "durable_residue_action": {"action": "route-durable-residue", "owner": owner},
            },
        )
        for owner in ["planning", "docs", "tests", "contracts", "config", "review", "issue"]
    ]
    local_memory = _memory_decision_packet_payload(
        **base,
        closeout_trust={
            "trust": "lower-trust",
            "lower_trust_closeout_count": 1,
            "durable_residue_action": {"action": "route-durable-residue", "owner": "local_memory"},
        },
    )
    follow_up = _memory_decision_packet_payload(
        **base,
        closeout_trust={"trust": "lower-trust", "lower_trust_closeout_count": 1},
    )

    assert clean["force"] == "not_applicable"
    assert clean["capture"]["status"] == "none_found"
    assert dismissed["capture"]["status"] == "dismissed"
    assert capture["capture"]["status"] == "capture_candidate"
    assert {packet["capture"]["status"] for packet in routed_packets} == {"routed_elsewhere"}
    assert local_memory["capture"]["status"] == "follow_up_required"
    assert follow_up["force"] == "required_at_closeout"
    assert follow_up["capture"]["status"] == "follow_up_required"


def test_completion_gate_claim_authorization_surfaces_closure_keyword_guard() -> None:
    from agentic_workspace.workspace_runtime_primitives import _completion_gate_claim_authorization

    authorization = _completion_gate_claim_authorization(
        status="continue-required",
        active_intent_satisfied=False,
        human_accepted_partial=False,
        claim_level_requested="full-intent-complete",
        proof_status="representative",
        issue_refs={"#2113"},
    )

    guard = authorization["closure_keyword_guard"]
    assert "issue_closure" in authorization["blocked_claim_classes"]
    assert guard["status"] == "blocked"
    assert guard["severity"] == "strong-warning"
    assert guard["targets"][0]["safe_reference"] == "Refs #2113; does not close."
    assert "Closes #2113" in guard["targets"][0]["unsafe_examples"]


def test_terminal_outcome_contract_distinguishes_continue_blocked_and_user_paused() -> None:
    from agentic_workspace.workspace_runtime_primitives import (
        _terminal_final_response_admission,
        _terminal_outcome_contract_payload,
    )

    continue_contract = _terminal_outcome_contract_payload(
        completion_gate={
            "status": "blocked",
            "active_intent_satisfied": False,
            "claim_authorization": {"allowed_claim_classes": ["partial_progress"]},
        },
        completion_options=[
            {"id": "run-proof", "allowed": True},
            {"id": "stop-with-status", "allowed": True},
        ],
    )
    assert continue_contract["state"] == "CONTINUE"
    assert continue_contract["final_response_authorized"] is False
    assert continue_contract["custody_owner"] == "agent"
    assert "context-pressure" in continue_contract["invalid_pseudo_blockers"]

    weak_final_contract = _terminal_outcome_contract_payload(
        completion_gate={"status": "clarification-required", "required_next_action": "ask-human"},
        completion_options=[{"id": "request-review", "allowed": True}],
    )
    assert weak_final_contract["state"] == "CONTINUE"
    assert weak_final_contract["final_response_authorized"] is False
    assert weak_final_contract["blocker_qualification"]["status"] == "missing_typed_external_blocker"
    assert "qualify-terminal-blocker" in weak_final_contract["safe_continuation_option_ids"]
    assert weak_final_contract["final_response_enforcement"]["status"] == "rejected_auto_resume"
    assert weak_final_contract["final_response_enforcement"]["terminal_final_rejected"] is True
    assert weak_final_contract["final_response_enforcement"]["progress_without_yield"] is True
    assert weak_final_contract["final_response_enforcement"]["enforcement_maturity"] == "host-integrated"
    assert weak_final_contract["final_response_enforcement"]["ordinary_host_path_unavoidable"] is True
    assert weak_final_contract["final_response_enforcement"]["host_boundary_integrated"] is True
    assert weak_final_contract["final_response_enforcement"]["issue_2239_closure_ready"] is False
    assert "Broader unattended end-to-end evidence" in weak_final_contract["final_response_enforcement"]["issue_2239_closure_gap"]
    assert weak_final_contract["final_response_enforcement"]["integrated_host_boundaries"][0]["id"] == "agentic-workspace.autopilot"
    assert weak_final_contract["final_response_enforcement"]["integrated_host_boundaries"][1]["id"] == "model-cli-harness.codex-sbx"
    assert weak_final_contract["final_response_enforcement"]["multi_slice_continuation"]["status"] == "preserved"
    assert (
        weak_final_contract["final_response_enforcement"]["weak_model_regression"] == "terminal-final-rejected-while-continuation-remains"
    )
    admission = _terminal_final_response_admission(
        terminal_outcome_contract=weak_final_contract,
        final_response_attempt={
            "source": "weak-model-fixture",
            "claim": "Done.",
            "after_compaction": True,
        },
        resume_state={"slice": "pre-compaction"},
    )
    assert admission["status"] == "rejected_auto_resumed"
    assert admission["terminal_final_rejected"] is True
    assert admission["resume_transition"]["status"] == "executed"
    assert admission["resume_transition"]["auto_resume_action"] == "ask-human"
    assert admission["resume_transition"]["compaction_boundary_crossed"] is True
    assert admission["resume_transition"]["after_state"]["required_next_action"] == "ask-human"
    assert admission["progress_without_yield"] is True

    blocked_contract = _terminal_outcome_contract_payload(
        completion_gate={
            "status": "clarification-required",
            "required_next_action": "ask-human",
            "external_blockers": [
                {
                    "id": "missing-user-secret",
                    "type": "human_action",
                    "evidence": "The required secret is unavailable to the agent.",
                    "recovery": "Ask the user to provide the secret or approve a different path.",
                    "no_safe_continuation": True,
                }
            ],
        },
        completion_options=[{"id": "request-review", "allowed": True}],
    )
    assert blocked_contract["state"] == "BLOCKED"
    assert blocked_contract["final_response_authorized"] is True
    assert blocked_contract["blocker_qualification"]["status"] == "qualified_external_blocker"
    assert blocked_contract["blocker_qualification"]["qualified_blockers"][0]["id"] == "missing-user-secret"

    paused_contract = _terminal_outcome_contract_payload(
        completion_gate={"status": "human-accepted-partial", "human_accepted_partial": True},
        completion_options=[],
    )
    assert paused_contract["state"] == "USER_PAUSED"
    assert paused_contract["custody_owner"] == "user"


def test_final_response_admission_rejects_non_compliant_final_and_resumes_through_compaction() -> None:
    from agentic_workspace.workspace_runtime_primitives import (
        _terminal_final_response_admission,
        _terminal_outcome_contract_payload,
    )

    contract = _terminal_outcome_contract_payload(
        completion_gate={
            "status": "continue-required",
            "required_next_action": "run-focused-proof",
            "active_intent_satisfied": False,
            "claim_authorization": {"allowed_claim_classes": ["partial_progress"]},
        },
        completion_options=[{"id": "run-proof", "allowed": True}],
    )
    invoked_requests = []

    def execute_resume(request: dict[str, object]) -> dict[str, object]:
        invoked_requests.append(request)
        assert request["auto_resume_action"] == "run-focused-proof"
        assert request["terminal_final_rejected"] is True
        assert request["after_compaction"] is True
        return {
            "kind": "agentic-workspace/final-response-resume-result/v1",
            "status": "executed",
            "invoked_action": request["auto_resume_action"],
            "after_state_patch": {
                "continuation_slice": "slice-2-post-compaction",
                "required_next_action": request["auto_resume_action"],
                "custody_owner": "agent",
                "resume_count": 1,
            },
        }

    admission = _terminal_final_response_admission(
        terminal_outcome_contract=contract,
        final_response_attempt={
            "source": "simulated-2236-2237-non-compliance",
            "claim": "Done.",
            "after_compaction": True,
        },
        resume_state={"continuation_slice": "slice-1-pre-compaction", "resume_count": 0},
        resume_executor=execute_resume,
    )

    assert len(invoked_requests) == 1
    assert admission["status"] == "rejected_auto_resumed"
    assert admission["host_admission_boundary"]["status"] == "rejected-and-resumed"
    assert admission["host_admission_boundary"]["invoked_resume_executor"] is True
    assert admission["host_admission_boundary"]["rejects_model_obedience_only"] is True
    transition = admission["resume_transition"]
    assert transition["status"] == "executed"
    assert transition["auto_resume_action"] == "run-focused-proof"
    assert transition["compaction_boundary_crossed"] is True
    assert transition["executor_result"]["status"] == "executed"
    assert transition["executor_result"]["invoked_action"] == "run-focused-proof"
    assert transition["after_state"]["continuation_slice"] == "slice-2-post-compaction"
    assert transition["after_state"]["custody_owner"] == "agent"
    assert admission["progress_without_yield"] is True


def test_memory_decision_packet_pull_statuses_distinguish_route_inspection() -> None:
    baseline_only = _memory_decision_packet_payload(
        stage="implement",
        cli_invoke="agentic-workspace",
        memory_consult={
            "status": "recommended",
            "route_inspection_state": "checked",
            "route_signal_count": 0,
            "read_first": [".agentic-workspace/memory/repo/index.md"],
            "route_matches": [{"path": ".agentic-workspace/memory/repo/index.md", "match_source": "routing-baseline"}],
        },
        changed_paths=["src/example.py"],
    )
    checked_none = _memory_decision_packet_payload(
        stage="implement",
        cli_invoke="agentic-workspace",
        memory_consult={
            "status": "recommended",
            "route_inspection_state": "checked",
            "route_signal_count": 0,
            "route_matches": [],
        },
        changed_paths=["docs/example.md"],
    )
    relevant = _memory_decision_packet_payload(
        stage="implement",
        cli_invoke="agentic-workspace",
        memory_consult={
            "status": "recommended",
            "route_inspection_state": "checked",
            "route_signal_count": 1,
            "route_matches": [{"path": ".agentic-workspace/memory/repo/domains/api.md", "match_source": "routes_from"}],
        },
        changed_paths=["src/api.py"],
    )
    hinted_only = _memory_decision_packet_payload(
        stage="startup",
        cli_invoke="agentic-workspace",
        memory_consult={
            "status": "recommended",
            "route_inspection_state": "not_checked",
            "read_first": [".agentic-workspace/memory/repo/index.md"],
        },
        task_text="memory memory memory",
    )

    assert baseline_only["pull"]["status"] == "baseline_only"
    assert checked_none["pull"]["status"] == "checked_none"
    assert relevant["pull"]["status"] == "relevant_notes_found"
    assert hinted_only["pull"]["status"] == "not_checked"
    assert baseline_only["capture"]["allowed_outcomes"] == [
        "capture",
        "update_existing",
        "route_elsewhere",
        "dismiss",
        "follow_up_required",
    ]


def test_operating_loop_projection_keeps_task_prose_from_changing_state() -> None:
    base = _operating_loop_decision_payload()
    repeated_words = _operating_loop_decision_payload(
        memory_decision_packet={
            "pull": {"status": "not_checked", "candidate_routes": []},
            "capture": {"status": "not_evaluated"},
        },
        proof={},
        planning_safety_gate={},
    )

    assert base["memory"] == repeated_words["memory"]
    assert base["planning"] == repeated_words["planning"]
    assert base["verification"] == repeated_words["verification"]
    assert base["closeout_state"] == "no_closeout_needed"
    assert base["safe_claim"] == "none"


def test_operating_loop_projection_ready_for_full_closure_requires_closeout_context() -> None:
    implement = _operating_loop_decision_payload(proof={"status": "passed"})
    closeout = _operating_loop_decision_payload(claim_context="closeout", proof={"status": "passed"})

    assert implement["closeout_state"] == "no_closeout_needed"
    assert implement["safe_claim"] == "none"
    assert closeout["verification"]["state"] == "proof_passed"
    assert closeout["closeout_state"] == "ready_for_full_closure"
    assert closeout["safe_claim"] == "full"
    assert closeout["residue_owner"] == "none"


def test_operating_loop_projection_blocks_active_planning() -> None:
    packet = _operating_loop_decision_payload(
        claim_context="closeout",
        planning_safety_gate={
            "workflow_sufficient": False,
            "active_plan_reliance": {
                "status": "active-plan-present",
                "active_execplan": ".agentic-workspace/planning/execplans/current.md",
            },
        },
    )

    assert packet["planning"]["state"] == "active"
    assert packet["closeout_state"] == "blocked_active_planning"
    assert packet["safe_claim"] == "blocked"
    assert packet["residue_owner"] == "planning"
    assert "continue_or_close_plan" in packet["required_before_full_closure"]


def test_operating_loop_projection_keeps_unrelated_task_switch_plan_as_residue() -> None:
    packet = _operating_loop_decision_payload(
        claim_context="closeout",
        planning_safety_gate={
            "gate_result": "active-plan-task-switch",
            "workflow_sufficient": True,
            "task_switch_reconciliation": {"status": "active"},
            "active_plan_reliance": {
                "status": "active-plan-present",
                "active_execplan": ".agentic-workspace/planning/execplans/current.md",
            },
        },
        proof={"status": "passed"},
    )

    assert packet["planning"]["state"] == "unrelated_active_plan"
    assert packet["planning"]["plan_ref"] == ".agentic-workspace/planning/execplans/current.md"
    assert packet["planning"]["blocks_full_closure"] is False
    assert packet["closeout_state"] == "ready_for_full_closure"
    assert packet["safe_claim"] == "full"
    assert "continue_or_close_plan" not in packet["required_before_full_closure"]


def test_operating_loop_projection_maps_planning_continuation_to_partial_claim() -> None:
    packet = _operating_loop_decision_payload(
        claim_context="closeout",
        active_plan_reliance={
            "status": "continuation",
            "active_execplan": ".agentic-workspace/planning/execplans/current.md",
        },
    )

    assert packet["planning"]["state"] == "continuation"
    assert packet["closeout_state"] == "partial_claim_only"
    assert packet["safe_claim"] == "partial"
    assert packet["residue_owner"] == "planning"


def test_operating_loop_projection_blocks_negative_proof_states() -> None:
    expected = {
        "stale": "proof_stale",
        "skipped": "proof_skipped",
        "failed": "proof_failed",
    }

    for proof_status, verification_state in expected.items():
        packet = _operating_loop_decision_payload(
            claim_context="closeout",
            proof={"status": proof_status, "required_commands": ["make test-workspace"]},
        )

        assert packet["verification"]["state"] == verification_state
        assert packet["closeout_state"] == "blocked_missing_proof"
        assert packet["safe_claim"] == "blocked"
        assert packet["residue_owner"] == "verification"
        assert "run_or_refresh_proof" in packet["required_before_full_closure"]


def test_operating_loop_projection_maps_memory_capture_residue() -> None:
    packet = _operating_loop_decision_payload(
        memory_decision_packet={
            "pull": {"status": "checked_none", "candidate_routes": []},
            "capture": {"status": "follow_up_required"},
        }
    )

    assert packet["memory"]["capture"] == "required"
    assert packet["residue_owner"] == "memory"
    assert packet["closeout_state"] == "residue_routing_required"
    assert "route_memory_residue" in packet["required_before_full_closure"]


def test_workspace_summary_json_warns_on_closed_lanes_in_live_state(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "done-lane", type = "lane", title = "Done lane", maturity = "closed", status = "done", priority = "first", issues = ["#1"], outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "", closure = "archive-and-close", durable_residue = "planning" },
]

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "also-done", title = "Also done", maturity = "closed", status = "done", priority = "second", issues = ["#2"], outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "", closure = "archive-and-close", durable_residue = "planning" },
]
candidates = [
  { priority = "first", summary = "Done lane" },
  { priority = "second", summary = "Also done" },
]
""",
    )

    exit_code = cli.main(["summary", "--target", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["roadmap"]["lane_count"] == 0
    assert payload["roadmap"]["candidate_count"] == 0
    assert payload["planning_surface_health"]["status"] == "not-clean"
    assert any(
        warning["warning_class"] == "historical_work_in_live_planning_state" for warning in payload["planning_surface_health"]["warnings"]
    )
    assert payload["execution_readiness"]["status"] == "narrow-direct-ready"
    assert payload["schema"]["select_command"] == "agentic-workspace summary --select <field.path> --format json"


def test_workspace_summary_planning_revision_selector_stays_tiny(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    exit_code = cli.main(["summary", "--target", str(tmp_path), "--select", "planning_revision", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["values"]["planning_revision"]["kind"] == "planning-revision/v1"
    assert payload["selection_cost"]["profile_loaded"] == "tiny-direct"
    assert payload["selection_cost"]["fallback_profile_loaded"] is False


def test_workspace_summary_planning_record_selector_uses_direct_owner_query(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    from repo_planning_bootstrap import installer as planning_installer

    record_path = tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.plan.json"
    record = planning_installer._build_legacy_execplan_record_from_todo_item(
        title="Plan Alpha",
        item_id="plan-alpha",
        status="in-progress",
        why_now="keep selected reads cheap.",
        next_action="run focused proof.",
        done_when="the selected read stays query-shaped.",
    )
    _write(record_path, json.dumps(record, indent=2) + "\n")
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "active", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    for index in range(1000):
        _write(
            tmp_path / f".agentic-workspace/planning/closeout-evidence/closed-{index}.closeout.json",
            json.dumps({"kind": "planning-closeout-evidence/v1", "plan_id": f"closed-{index}"}),
        )

    started = time.perf_counter()
    exit_code = cli.main(
        [
            "summary",
            "--target",
            str(tmp_path),
            "--select",
            "planning_revision,planning_record,continuation_view",
            "--format",
            "json",
        ]
    )
    elapsed = time.perf_counter() - started
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["values"]["planning_revision"]["kind"] == "planning-revision/v1"
    assert payload["values"]["planning_record"]["status"] == "present"
    assert payload["values"]["continuation_view"]["status"] == "present"
    assert payload["selection_cost"]["profile_loaded"] == "query-shaped-direct"
    assert payload["selection_cost"]["fallback_profile_loaded"] is False
    assert payload["selection_cost"]["historical_sources_loaded"] is False
    assert "execplan-archive" in payload["selection_cost"]["omitted_sources"]
    assert elapsed < 2.0


def test_workspace_summary_completion_task_surfaces_closeout_trust(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n[assurance]\nstrict_closeout = true\n",
    )
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
  { id = "epic-continuation", maturity = "candidate", status = "next", priority = "P1", refs = "package-owned-only", title = "Continue epic", outcome = "Finish the original epic intent.", reason = "A completed lane did not satisfy the larger intent.", promotion_signal = "Promote before closeout.", suggested_first_slice = "Promote the next lane." },
]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "epic-continuation.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Epic continuation",
                "outcome": "Finish the original epic intent.",
                "status": "ready-for-lane-promotion",
                "lanes": [
                    {
                        "id": "next-lane",
                        "title": "Next lane",
                        "readiness": "ready",
                        "owner_surface": ".agentic-workspace/planning/state.toml",
                    }
                ],
            },
            indent=2,
        ),
    )

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--task",
                "Can this lane be considered done?",
                "--select",
                "closeout_trust_inspection",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)["values"]
    closeout = payload["closeout_trust_inspection"]
    assert closeout["status"] == "required"
    assert closeout["trust"] == "lower-trust"
    effect = closeout["action_effect"]
    assert effect["force"] == "required_before_claim"
    assert effect["allowed_now"] == "inspect-closeout-trust-before-broad-status-claim"
    assert effect["blocked_until_reconciled"] == [
        "claim-broad-work-complete",
        "claim-lane-closeable",
        "claim-issue-closure-safe",
    ]
    assert effect["resolution_selector"] == "closeout_trust_inspection"
    assert closeout["strict_closeout_gate"]["status"] == "blocked"
    assert closeout["intent_satisfaction"]["trust"] == "follow-up-required"
    protocol = closeout["closeout_protocol"]
    assert protocol["protocol"] == "Completion Honesty / Residue Routing"
    assert protocol["status"] == "action-required"
    assert protocol["residue_routing"]["required"] is True
    assert "issue_closure" in protocol["claim_boundary"]["blocked_claim_classes"]
    assert "promotion-required" in protocol["knowledge_route_states"]["state_vocabulary"]
    relative_target = os.path.relpath(tmp_path.resolve(), Path.cwd().resolve()).replace("\\", "/")
    assert closeout["required_next_inspection"] == (
        f"agentic-workspace report --target {relative_target} --section closeout_trust --format json"
    )


def test_workspace_summary_closeout_trust_inspection_clear_is_advisory(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
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
candidates = []
""",
    )

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--task",
                "Is the direct docs update closeable?",
                "--select",
                "closeout_trust_inspection",
                "--format",
                "json",
            ]
        )
        == 0
    )

    closeout = json.loads(capsys.readouterr().out)["values"]["closeout_trust_inspection"]
    assert closeout["status"] == "clear"
    assert closeout["action_effect"]["force"] == "advisory"
    assert closeout["action_effect"]["allowed_now"] == "continue-closeout-status-answer"
    assert closeout["action_effect"]["blocked_until_reconciled"] == []
    assert closeout["action_effect"]["claim_boundary"] == "closeout-trust-clear-does-not-replace-proof-and-acceptance-reconciliation"
    assert closeout["action_effect"]["resolution_selector"] == "closeout_trust_inspection"


def test_workspace_summary_json_accepts_verbose_detail(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")

    exit_code = cli.main(["summary", "--target", str(tmp_path), "--format", "json", "--verbose"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["profile"] == "full"
    assert payload["schema"]["schema_version"] == "planning-summary-schema/v1"


def test_workspace_summary_warns_for_unsupported_active_execplan_strings(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[active]
execplans = ["lane.plan.json"]

[todo]
active_items = []
queued_items = []
""",
    )
    _write(tmp_path / ".agentic-workspace/planning/execplans/lane.plan.json", json.dumps({"kind": "planning-execplan/v1"}))

    exit_code = cli.main(["summary", "--target", str(tmp_path), "--format", "json", "--verbose"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    warnings = payload["planning_surface_health"]["warnings"]
    assert any(warning["warning_class"] == "planning_state_unsupported_activation_shape" for warning in warnings)
    assert payload["planning_surface_health"]["status"] == "not-clean"
    assert payload["planning_surface_health"]["recovery_required"] is True
    assert "resolve planning-surface health" in payload["planning_surface_health"]["unsafe_to_continue_reason"]
    warning_text = json.dumps(payload["planning_surface_health"])
    assert "do not delete state.toml" in warning_text.lower()
    assert "recovery_sequence" in payload["planning_surface_health"]["authoring_affordances"]


def test_workspace_reconcile_json_exposes_provider_agnostic_planning_state(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "closed-lane", title = "Closed lane", priority = "first", issues = ["EXT-1"], outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "None." },
]
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "EXT-1",
                        "title": "Closed elsewhere",
                        "status": "resolved",
                        "kind": "lane",
                        "planning_residue_expected": "optional",
                    }
                ],
            },
            indent=2,
        ),
    )

    exit_code = cli.main(["reconcile", "--target", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["kind"] == "planning-reconcile/v1"
    assert payload["external_work_state"]["closed_count"] == 1
    assert payload["stale_forward_state"]["closed_roadmap_lanes"][0]["id"] == "closed-lane"
    assert payload["completed_work_reconciliation"]["apply_available"] is True
    assert payload["completed_work_reconciliation"]["apply_command"] == "agentic-workspace reconcile --apply-safe-prune --format json"


def test_workspace_reconcile_apply_safe_prune_removes_exact_closed_items(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    _write(
        state_path,
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "closed-lane", title = "Closed lane", priority = "first", issues = ["EXT-1"], outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "None." },
  { id = "open-lane", title = "Open lane", priority = "second", issues = ["EXT-2"], outcome = "Open.", reason = "Open.", promotion_signal = "None.", suggested_first_slice = "None." },
]
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "EXT-1",
                        "title": "Closed elsewhere",
                        "status": "resolved",
                        "kind": "lane",
                        "planning_residue_expected": "optional",
                    },
                    {
                        "system": "manual",
                        "id": "EXT-2",
                        "title": "Open elsewhere",
                        "status": "in_progress",
                        "kind": "lane",
                        "planning_residue_expected": "optional",
                    },
                ],
            },
            indent=2,
        ),
    )

    exit_code = cli.main(["reconcile", "--target", str(tmp_path), "--apply-safe-prune", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["apply_result"]["applied_count"] == 1
    assert payload["completed_work_reconciliation"]["cleanup_target_count"] == 0
    state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    assert [lane["id"] for lane in state["roadmap"]["lanes"]] == ["open-lane"]


def test_workspace_reconcile_reconstructs_external_cache_when_gh_is_available(tmp_path: Path, monkeypatch, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    class Result:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, cwd, capture_output, text, encoding, check):
        if command[:3] == ["gh", "repo", "view"]:
            return Result(json.dumps({"nameWithOwner": "acme/project"}))
        if command[:3] == ["gh", "issue", "view"]:
            number = int(command[3])
            titles = {10: "Stale upstream", 11: "Parent intake lane", 12: "Child intake slice"}
            bodies = {10: "", 11: "## Issue kind\nlane\n", 12: "## Issue kind\nslice\n\nParent: #11\n"}
            return Result(
                json.dumps(
                    {
                        "number": number,
                        "title": titles[number],
                        "state": "CLOSED" if number == 10 else "OPEN",
                        "url": f"https://github.com/acme/project/issues/{number}",
                        "labels": [{"name": "priority/high" if number == 11 else "priority/medium"}],
                        "createdAt": "2026-04-28T00:00:00Z",
                        "updatedAt": "2026-05-20T00:00:00Z",
                        "closedAt": "2026-05-20T00:00:00Z" if number == 10 else "",
                        "body": bodies[number],
                        "comments": 0,
                    }
                )
            )
        assert command[:3] == ["gh", "issue", "list"]
        assert command[command.index("--state") + 1] == "all"
        return Result(
            json.dumps(
                [
                    {
                        "number": 7,
                        "title": "Open external work",
                        "state": "OPEN",
                        "url": "https://github.com/acme/project/issues/7",
                        "labels": [],
                        "createdAt": "2026-04-28T00:00:00Z",
                        "updatedAt": "2026-04-28T00:00:00Z",
                        "body": "",
                        "comments": 0,
                    }
                ]
            )
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    exit_code = cli.main(["reconcile", "--target", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["external_work_state"]["open_count"] == 1
    cache_path = tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json"
    assert cache_path.exists()
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cache_payload["refresh_metadata"]["state"] == "all"


def test_external_intent_refresh_applies_stale_candidate_reconciliation_and_preserves_delta(tmp_path: Path, monkeypatch, capsys) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    _write(
        state_path,
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-10-stale", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #10", title = "Stale upstream", outcome = "Route upstream issue.", reason = "Open issue.", promotion_signal = "Promote when selected.", suggested_first_slice = "Inspect issue." },
]
""",
    )
    cache_path = tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json"
    _write(
        cache_path,
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "github",
                        "id": "#10",
                        "title": "Stale upstream",
                        "status": "open",
                        "kind": "issue",
                        "planning_residue_expected": "optional",
                    }
                ],
            },
            indent=2,
        ),
    )

    class Result:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, cwd, capture_output, text, encoding, check):
        if command[:3] == ["gh", "repo", "view"]:
            return Result(json.dumps({"nameWithOwner": "acme/project"}))
        if command[:3] == ["gh", "issue", "view"]:
            number = int(command[3])
            titles = {10: "Stale upstream", 11: "Parent intake lane", 12: "Child intake slice"}
            bodies = {10: "", 11: "## Issue kind\nlane\n", 12: "## Issue kind\nslice\n\nParent: #11\n"}
            return Result(
                json.dumps(
                    {
                        "number": number,
                        "title": titles[number],
                        "state": "CLOSED" if number == 10 else "OPEN",
                        "url": f"https://github.com/acme/project/issues/{number}",
                        "labels": [{"name": "priority/high" if number == 11 else "priority/medium"}],
                        "createdAt": "2026-04-28T00:00:00Z",
                        "updatedAt": "2026-05-20T00:00:00Z",
                        "closedAt": "2026-05-20T00:00:00Z" if number == 10 else "",
                        "body": bodies[number],
                        "comments": 0,
                    }
                )
            )
        assert command[:3] == ["gh", "issue", "list"]
        return Result(
            json.dumps(
                [
                    {
                        "number": 10,
                        "title": "Stale upstream",
                        "state": "CLOSED",
                        "url": "https://github.com/acme/project/issues/10",
                        "labels": [{"name": "priority/medium"}],
                        "createdAt": "2026-04-28T00:00:00Z",
                        "updatedAt": "2026-05-20T00:00:00Z",
                        "closedAt": "2026-05-20T00:00:00Z",
                        "body": "",
                        "comments": 0,
                    },
                    {
                        "number": 11,
                        "title": "Parent intake lane",
                        "state": "OPEN",
                        "url": "https://github.com/acme/project/issues/11",
                        "labels": [{"name": "priority/high"}],
                        "createdAt": "2026-04-28T00:00:00Z",
                        "updatedAt": "2026-05-20T00:00:00Z",
                        "closedAt": "",
                        "body": "## Issue kind\nlane\n",
                        "comments": 0,
                    },
                    {
                        "number": 12,
                        "title": "Child intake slice",
                        "state": "OPEN",
                        "url": "https://github.com/acme/project/issues/12",
                        "labels": [{"name": "priority/medium"}],
                        "createdAt": "2026-04-28T00:00:00Z",
                        "updatedAt": "2026-05-20T00:00:00Z",
                        "closedAt": "",
                        "body": "## Issue kind\nslice\n\nParent: #11\n",
                        "comments": 0,
                    },
                ]
            )
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    dry_run_exit_code = cli.main(
        [
            "external-intent",
            "refresh-github",
            "--target",
            str(tmp_path),
            "--state",
            "all",
            "--storage",
            "cache",
            "--dry-run",
            "--format",
            "json",
        ]
    )
    dry_run_payload = json.loads(capsys.readouterr().out)

    assert dry_run_exit_code == 0
    grouping = dry_run_payload["planning_candidate_grouping"]
    assert grouping["parent_lanes"][0]["id"] == "#11"
    assert grouping["child_issue_clusters"][0]["parent_id"] == "#11"
    assert grouping["child_issue_clusters"][0]["child_count"] == 1
    stale_candidate = dry_run_payload["stale_planning_candidate_reconciliation"]["stale_candidates"][0]
    assert stale_candidate["id"] == "github-10-stale"
    assert stale_candidate["reconcile_command"] == (
        "uv run agentic-workspace external-intent refresh-github --target . --state closed --storage cache "
        "--apply-planning-candidates --format json"
    )

    exit_code = cli.main(
        [
            "external-intent",
            "refresh-github",
            "--target",
            str(tmp_path),
            "--state",
            "all",
            "--storage",
            "cache",
            "--apply-planning-candidates",
            "--issue",
            "#10",
            "--issue",
            "#11",
            "--issue",
            "#12",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    reconciliation = payload["stale_planning_candidate_reconciliation"]
    assert reconciliation["status"] == "applied"
    assert reconciliation["stale_candidates"][0]["id"] == "github-10-stale"
    state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    candidate_ids = {candidate["id"] for candidate in state["roadmap"]["candidates"]}
    assert "github-10-stale" not in candidate_ids
    assert candidate_ids == {"github-11-parent-intake-lane", "github-12-child-intake-slice"}
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "previous_items" not in cache_payload
    assert all("observation_id" in item for item in cache_payload["items"])

    assert cli.main(["report", "--target", str(tmp_path), "--section", "external_work_delta", "--format", "json"]) == 0
    delta = json.loads(capsys.readouterr().out)
    assert delta["answer"]["status"] == "snapshot-only"
    assert delta["answer"]["item_count"] == 3


def test_external_intent_refresh_requires_explicit_refs_before_candidate_promotion(tmp_path: Path, monkeypatch, capsys) -> None:
    install_bootstrap(target=tmp_path)

    class Result:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, cwd, capture_output, text, encoding, check):
        if command[:3] == ["gh", "repo", "view"]:
            return Result(json.dumps({"nameWithOwner": "acme/project"}))
        assert command[:3] == ["gh", "issue", "list"]
        return Result(
            json.dumps(
                [
                    {
                        "number": 77,
                        "title": "Unselected work",
                        "state": "OPEN",
                        "url": "https://github.com/acme/project/issues/77",
                        "labels": [{"name": "planning"}],
                        "createdAt": "2026-07-14T00:00:00Z",
                        "updatedAt": "2026-07-14T00:00:00Z",
                        "closedAt": "",
                        "body": "",
                        "comments": 0,
                    }
                ]
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
                "--state",
                "all",
                "--apply-planning-candidates",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    state = tomllib.loads((tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8"))

    assert payload["planning_candidate_apply"]["status"] == "explicit-selection-required"
    assert "--issue" in payload["planning_candidate_apply"]["reason"]
    assert state.get("roadmap", {}).get("candidates", []) == []


def test_workspace_summary_json_surfaces_external_work_reconciliation(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json",
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refreshed_at": "2026-04-27T12:00:00+00:00",
                "refresh_metadata": {"adapter": "manual-fixture", "item_count": 1, "open_count": 1, "closed_count": 0},
                "items": [
                    {
                        "system": "manual",
                        "id": "EXT-1",
                        "title": "Open elsewhere",
                        "status": "open",
                        "kind": "task",
                        "planning_residue_expected": "optional",
                    }
                ],
            },
            indent=2,
        ),
    )

    exit_code = cli.main(["summary", "--target", str(tmp_path), "--verbose", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    reconciliation = payload["intent_validation_contract"]["external_work_reconciliation"]
    assert reconciliation["kind"] == "planning-external-work-reconciliation/v1"
    assert reconciliation["freshness"]["fresh_enough_to_trust"] is True
    assert reconciliation["freshness"]["trust_scope"] == "snapshot"
    assert reconciliation["freshness"]["refresh_after_mutation"] is True
    assert "external-intent refresh-github" in reconciliation["freshness"]["refresh_command"]
    assert reconciliation["freshness"]["refresh_metadata"]["adapter"] == "manual-fixture"
    assert reconciliation["freshness"]["path"] == ".agentic-workspace/local/cache/external-intent-evidence.json"
    assert reconciliation["external_work_state"]["open_count"] == 1
    routine = reconciliation["routine_reconciliation"]
    assert routine["status"] == "available"
    assert "issue created or updated" in routine["after_events"]
    assert "external-intent refresh-github" in routine["command"]
    assert "checked-in planning remains the primary owner" in routine["rule"]
