from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from planning_test_support import *


def test_planning_report_defaults_to_tiny_profile(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    install_bootstrap(target=target)

    assert planning_cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "tiny"
    assert "finished_work_inspection" not in payload
    assert payload["detail_commands"]["full"] == "agentic-planning report --target . --profile full --format json"


def test_planning_readme_and_bootstrap_agents_describe_required_follow_on_routing() -> None:
    readme_text = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    bootstrap_agents_text = (installer_mod.payload_root() / "AGENTS.template.md").read_text(encoding="utf-8")
    execplans_readme_text = (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "execplans" / "README.md").read_text(
        encoding="utf-8"
    )
    manifest_payload = json.loads(
        (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "agent-manifest.json").read_text(encoding="utf-8")
    )
    quickstart_text = render_module.render_quickstart(manifest_payload)
    routing_text = render_module.render_routing(manifest_payload)

    assert "Execplans now treat four fields as first-class" in readme_text
    assert "clear the matched queue residue in the same pass" in readme_text
    assert "`Required Continuation`" in readme_text
    assert "`Iterative Follow-Through`" in readme_text
    assert "`Execution Summary`" in readme_text
    assert "Required continuation for an unfinished larger intended outcome" in readme_text
    assert "Keep this file thin." in bootstrap_agents_text
    assert '<effective-cli> start --task "<task>" --format json' in bootstrap_agents_text
    assert "<effective-cli> preflight --format json" in bootstrap_agents_text
    assert "<effective-cli> summary --format json" in bootstrap_agents_text
    assert "<effective-cli> defaults --section startup --format json" in bootstrap_agents_text
    assert (
        "Use `<effective-cli> config --target . --format json` when the configured entrypoint, posture, or workflow obligations matter; add `--select <field[,field...]>` for exact detail."
        in bootstrap_agents_text
    )
    assert "do not substitute bare `agentic-workspace`" in bootstrap_agents_text
    assert "Read package-local `AGENTS.md` only for the package being edited." in bootstrap_agents_text
    assert "## When Needed" not in bootstrap_agents_text
    assert "remove or archive the matched queue residue in the same pass" in execplans_readme_text
    assert "## Authority Table" not in quickstart_text
    assert "## Escalation Table" not in quickstart_text
    assert "Generated, non-authoritative helper" in quickstart_text
    assert 'agentic-workspace start --task "<task>" --format json' in quickstart_text
    assert "agentic-workspace preflight --format json" in quickstart_text
    assert "## Routing Table" not in routing_text
    assert "Secondary generated adapter" in routing_text
    assert "## Use" in routing_text
    assert "## Compact Queries" not in routing_text
    assert "agentic-workspace preflight --format json" not in routing_text
    assert 'agentic-workspace start --task "<task>" --format json' in routing_text
    assert "Iterative carry-forward belongs under `## Iterative Follow-Through`" in execplans_readme_text
    assert any(
        "Use `agentic-workspace summary --format json` first when active planning recovery or compact ownership state is the question."
        in item
        for item in manifest_payload["bootstrap"]["first_queries"]
    )
    assert any(
        "Read `agentic-workspace summary --format json` first when planning recovery or ownership boundary review is the question." in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any(
        "Read `agentic-workspace summary --format json` first when planning recovery or ownership boundary review is the question." in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any(
        "prefer `agentic-workspace defaults --section startup --format json` and `agentic-workspace config --target ./repo --format json` before broader prose"
        in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any("Ask compact startup queries first" in item for item in manifest_payload["bootstrap"]["tiny_safe_model"])
    assert manifest_payload["bootstrap"]["boundary_triggered_escalation"][0]["boundary"] == "workspace"
    assert manifest_payload["bootstrap"]["top_level_capabilities"][1]["module"] == "planning"
    assert any("clear the matched queue residue in the same pass" in item for item in manifest_payload["bootstrap"]["completion_reminders"])
    assert "generated static adapter" in quickstart_text
    assert "Do not bulk-read all planning surfaces" in quickstart_text
    assert "clear the matched queue residue in the same pass" not in quickstart_text


def test_planning_reconcile_reports_stale_state_from_provider_agnostic_evidence(tmp_path: Path) -> None:
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
  { id = "mixed-lane", title = "Mixed lane", priority = "second", issues = ["EXT-1", "EXT-2"], outcome = "Mixed.", reason = "Mixed.", promotion_signal = "None.", suggested_first_slice = "None." },
]
candidates = [
  { id = "closed-candidate", title = "Closed candidate", priority = "third", refs = "EXT-1", outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "None." },
]
""",
    )
    _write(
        tmp_path / ".agentic-workspace/planning/decompositions/closed-migration.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Closed migration EXT-1",
                "status": "complete",
                "larger_intended_outcome": "Complete EXT-1",
                "non_goals": [],
                "candidate_lanes": [],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": [],
                "promotion_rule": "",
                "references": [{"kind": "issue", "target": "EXT-1", "role": "related-work"}],
                "notes": "",
            },
            indent=2,
        ),
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Closed elsewhere",
                "status": "resolved",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
            {
                "system": "manual",
                "id": "EXT-2",
                "title": "Still open elsewhere",
                "status": "in_progress",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
        ],
    )

    reconcile = planning_reconcile(target=tmp_path)

    assert reconcile["kind"] == "planning-reconcile/v1"
    assert reconcile["status"] == "attention-needed"
    assert "provider-agnostic" in reconcile["schema"]["provider_rule"]
    assert reconcile["external_work_state"]["open_count"] == 1
    assert reconcile["external_work_state"]["closed_count"] == 1
    closed_lanes = reconcile["stale_forward_state"]["closed_roadmap_lanes"]
    assert [lane["id"] for lane in closed_lanes] == ["closed-lane"]
    assert closed_lanes[0]["refs"] == ["EXT-1"]
    closed_candidates = reconcile["stale_forward_state"]["closed_roadmap_candidates"]
    assert [candidate["id"] for candidate in closed_candidates] == ["closed-candidate"]
    closed_decompositions = reconcile["stale_forward_state"]["closed_decomposition_records"]
    assert [record["id"] for record in closed_decompositions] == ["closed-migration"]
    completed = reconcile["completed_work_reconciliation"]
    assert completed["status"] == "stale-artifacts"
    assert completed["stale_artifact_count"] == 3
    cleanup_targets = completed["cleanup_targets"]
    assert [target["cleanup_action"] for target in cleanup_targets] == [
        "remove-roadmap-lane",
        "remove-roadmap-candidate",
        "remove-decomposition-record",
    ]
    assert all(target["safe_to_prune"] is True for target in cleanup_targets)


def test_planning_cli_reconcile_outputs_provider_agnostic_state(tmp_path: Path, capsys) -> None:
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
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Closed elsewhere",
                "status": "done",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            }
        ],
    )

    assert planning_cli.main(["reconcile", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"]["schema_version"] == "planning-reconcile-schema/v1"
    assert payload["external_work_state"]["closed_count"] == 1
    assert payload["stale_forward_state"]["closed_roadmap_lanes"][0]["id"] == "closed-lane"
