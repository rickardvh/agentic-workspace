from __future__ import annotations

import json
import tomllib
from pathlib import Path

from repo_planning_bootstrap.installer import install_bootstrap

from command_generation.generated_package_loader import load_generated_cli_module_for_entrypoint

cli = load_generated_cli_module_for_entrypoint("agentic-workspace", "workspace_runtime_cli")


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
    assert "candidate_lanes" not in payload["roadmap"]


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

    assert cli.main(["summary", "--target", str(tmp_path), "--task", "Can this lane be considered done?", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    closeout = payload["closeout_trust_inspection"]
    assert closeout["status"] == "required"
    assert closeout["trust"] == "lower-trust"
    assert closeout["strict_closeout_gate"]["status"] == "blocked"
    assert closeout["intent_satisfaction"]["trust"] == "follow-up-required"
    assert closeout["required_next_inspection"] == "agentic-workspace report --target ./repo --section closeout_trust --format json"


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
