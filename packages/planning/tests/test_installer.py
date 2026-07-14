from __future__ import annotations

import sys as _sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path as _Path
from statistics import median

# ruff: noqa: F403,F405
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
    assert payload["detail_commands"]["full"] == "agentic-planning report --target . --verbose --format json"
    assert set(payload["health_dimensions"]) == {
        "integrity",
        "selection",
        "continuity",
        "external_reconciliation",
        "proof_readiness",
    }
    assert all(
        dimension["historical_sources_loaded"] is False
        for dimension in payload["health_dimensions"].values()
        if "historical_sources_loaded" in dimension
    )


def test_planning_report_verbose_audit_is_explicit_and_paginated(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    install_bootstrap(target=target)
    evidence_root = target / ".agentic-workspace/planning/closeout-evidence"
    for index in range(3):
        _write(
            evidence_root / f"closed-{index}.closeout.json",
            json.dumps({"kind": "planning-closeout-evidence/v1", "plan_id": f"closed-{index}", "claim_level": "slice"}),
        )

    assert planning_cli.main(["report", "--target", str(target), "--verbose", "--audit-page-size", "2", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["owner_audit"]["loaded_record_count"] == 2
    assert payload["owner_audit"]["has_more"] is True
    assert payload["owner_audit"]["next_cursor"]


def test_planning_report_tiny_text_uses_generated_output(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    install_bootstrap(target=target)

    def fail_source_output(*_args, **_kwargs) -> None:
        raise AssertionError("planning report tiny text should not fall back to package output")

    monkeypatch.setattr(runtime_projection, "emit_planning_operation_output", fail_source_output)

    assert planning_cli.main(["report", "--target", str(target), "--format", "text"]) == 0

    text = capsys.readouterr().out
    assert "Command: planning" in text
    assert "Health:" in text
    assert "Status:" in text
    assert "Next action:" in text


def test_reconcile_preview_is_history_independent_and_never_compiles_full_summary(tmp_path: Path, monkeypatch) -> None:
    install_bootstrap(target=tmp_path)
    installer_mod._PLANNING_SELECTED_OWNER_CACHE.clear()
    original_glob = Path.glob

    def reject_history_glob(path: Path, pattern: str):
        assert "closeout-evidence" not in path.as_posix(), "reconcile preview traversed closeout history"
        return original_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", reject_history_glob)
    monkeypatch.setattr(
        installer_mod,
        "planning_summary",
        lambda **_kwargs: pytest.fail("reconcile preview compiled the broad Planning summary"),
    )

    empty_history_samples = []
    for _ in range(7):
        installer_mod._PLANNING_SELECTED_OWNER_CACHE.clear()
        started = time.perf_counter()
        preview = planning_reconcile(target=tmp_path)
        empty_history_samples.append(time.perf_counter() - started)

    evidence_root = tmp_path / ".agentic-workspace/planning/closeout-evidence"
    for index in range(1000):
        _write(
            evidence_root / f"closed-{index}.closeout.json",
            json.dumps({"kind": "planning-closeout-evidence/v1", "plan_id": f"closed-{index}", "claim_level": "slice"}),
        )

    historical_samples = []
    for _ in range(7):
        installer_mod._PLANNING_SELECTED_OWNER_CACHE.clear()
        started = time.perf_counter()
        preview = planning_reconcile(target=tmp_path)
        historical_samples.append(time.perf_counter() - started)

    assert preview["dependency_scope"]["historical_sources_loaded"] is False
    assert preview["historical_audit_references"]["status"] == "not-loaded"
    empty_median = median(empty_history_samples)
    historical_median = median(historical_samples)
    assert historical_median <= max(empty_median * 1.2, empty_median + 0.010), (
        "reconciliation preview exceeded the 20% history-independence budget: "
        f"empty={empty_median:.6f}s history_1000={historical_median:.6f}s"
    )


def test_upgrade_bootstrap_is_idempotent_for_bundled_skills(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)
    install_bootstrap(target=tmp_path)

    second = upgrade_bootstrap(target=tmp_path)
    dry_run = upgrade_bootstrap(target=tmp_path, dry_run=True)

    second_updates = [
        action
        for action in second.actions
        if action.kind in {"overwritten", "would overwrite"} and ".agentic-workspace/planning/skills/" in action.path.as_posix()
    ]
    dry_run_updates = [
        action
        for action in dry_run.actions
        if action.kind in {"overwritten", "would overwrite"} and ".agentic-workspace/planning/skills/" in action.path.as_posix()
    ]
    assert second_updates == []
    assert dry_run_updates == []
    assert any(action.kind == "current" and "already matches managed planning skill" in action.detail for action in dry_run.actions)


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
        'Use `agentic-workspace start --task "<task>" --format json` before non-trivial work.' in item
        for item in manifest_payload["bootstrap"]["first_queries"]
    )
    assert any(
        "Read `agentic-workspace summary --format json` when the Startup Router or explicit task asks for planning recovery or ownership boundary review."
        in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any(
        "Read `agentic-workspace summary --format json` when the Startup Router or explicit task asks for planning recovery or ownership boundary review."
        in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any("prefer the Startup Router before broader prose" in item for item in manifest_payload["bootstrap"]["conditional_reads"])
    assert any("Ask the Startup Router first" in item for item in manifest_payload["bootstrap"]["tiny_safe_model"])
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
    assert completed["apply_available"] is True
    assert completed["apply_command"] == "agentic-planning reconcile --apply-safe-prune --format json"


def test_external_owner_observations_are_admitted_by_generic_relationship_freshness_and_authority(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/selected-owner.plan.json"
    plan = installer_mod._build_execplan_record_from_todo_item(
        title="Selected owner",
        item_id="selected-owner",
        status="active",
        why_now="Exercise provider-neutral observations.",
        next_action="Consume admitted generic posture.",
        done_when="Observation admission remains non-authoritative.",
    )
    plan["lifecycle"] = "live"
    plan["phase"] = "implementation"
    _write(plan_path, json.dumps(plan, indent=2))
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "selected-owner", title = "Selected owner", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/selected-owner.plan.json", why_now = "test", next_action = "test", done_when = "test" },
]
queued_items = []
""",
    )
    observed_at = datetime.now(UTC).replace(microsecond=0)

    def observation(
        system: str, external_id: str, status_class: str, *, binding: str = "explicit", freshness: str = "current"
    ) -> dict[str, object]:
        return {
            "system": system,
            "id": external_id,
            "title": external_id,
            "status": "closed" if status_class == "completed" else "open",
            "kind": "change-request",
            "observation_id": f"{system}:{external_id}:r1",
            "owner": {"id": external_id, "kind": "change-request", "locator": f"{system}://{external_id}"},
            "planning_relationship": {
                "binding": binding,
                "owner_id": "selected-owner" if binding == "explicit" else "",
                "owner_ref": ".agentic-workspace/planning/execplans/selected-owner.plan.json" if binding == "explicit" else "",
                "work_context_id": "default",
                "evidence_refs": [external_id],
            },
            "status_class": status_class,
            "external_revision": "r1",
            "observed_at": observed_at.isoformat(),
            "freshness": {
                "status": freshness,
                "observed_at": observed_at.isoformat(),
                "expires_at": (observed_at + timedelta(hours=24)).isoformat(),
                "max_age_seconds": 86400,
            },
            "blockers": (
                [{"code": "review", "summary": "Review required", "required_action": "approve"}] if status_class == "blocked" else []
            ),
            "evidence_refs": [f"{system}://{external_id}"],
            "provenance": {
                "provider_class": system,
                "resolver_id": f"{system}-fixture",
                "source_ref": f"{system}://{external_id}",
                "refresh_id": "fixture-refresh",
            },
            "refresh_route": f"refresh-{system}",
            "availability": "available",
            "contradictions": [],
            "provider_detail": {"opaque": system},
        }

    unavailable = observation("synthetic-review", "SYN-7", "current")
    unavailable["availability"] = "unavailable"
    contradicted = observation("synthetic-review", "SYN-8", "current")
    contradicted["contradictions"] = ["provider revision disagrees with admitted owner revision"]
    items = [
        observation("github", "GH-1", "completed"),
        observation("synthetic-review", "SYN-1", "completed"),
        observation("synthetic-review", "SYN-2", "blocked"),
        observation("synthetic-review", "SYN-3", "current", freshness="stale"),
        observation("synthetic-review", "SYN-4", "current", binding="ambiguous"),
        observation("synthetic-review", "SYN-5", "current", binding="unrelated"),
        observation("synthetic-review", "SYN-6", "failed"),
        unavailable,
        contradicted,
    ]
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json",
        items=items,
    )

    loaded = installer_mod._load_external_intent_evidence(tmp_path)
    by_id = {item["owner"]["id"]: item for item in loaded["items"]}

    assert (
        by_id["GH-1"]["admission"]
        == by_id["SYN-1"]["admission"]
        == {
            "state": "externally-completed-awaiting-admission",
            "reason_code": "external-completion-is-not-planning-proof-or-intent-satisfaction",
        }
    )
    assert by_id["SYN-2"]["admission"]["state"] == "externally-blocked"
    assert by_id["SYN-3"]["admission"]["state"] == "stale"
    assert by_id["SYN-4"]["admission"]["state"] == "ambiguous"
    assert by_id["SYN-5"]["admission"]["state"] == "unrelated"
    assert by_id["SYN-6"]["admission"]["state"] == "contradicted"
    assert by_id["SYN-7"]["admission"]["state"] == "unavailable"
    assert by_id["SYN-8"]["admission"]["state"] == "contradicted"
    assert loaded["relevant_observation_count"] == 7
    reconcile = planning_reconcile(target=tmp_path)
    inputs = reconcile["external_observation_inputs"]
    assert inputs["mutation_authority"] == "none"
    assert all("provider_detail" not in item for item in inputs["observations"])
    assert "#2262" in inputs["proof_boundary"]


def test_unmatched_external_backlog_stays_out_of_ordinary_planning_pressure(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    before_state = state_path.read_text(encoding="utf-8")
    items = [
        {
            "system": "synthetic-tracker",
            "id": f"EXT-{index}",
            "title": f"Unmatched {index}",
            "status": "open",
            "kind": "work-item",
        }
        for index in range(1000)
    ]
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/local/cache/external-intent-evidence.json",
        items=items,
    )

    summary = planning_summary(target=tmp_path, profile="full")
    current = summary["intent_validation_contract"]["current_external_work"]

    assert current["item_count"] == 1000
    assert current["relevant_observation_count"] == 0
    assert current["unmatched_backlog_count"] == 1000
    assert current["admitted_observations"] == []
    assert current["untracked_open_count"] == 0
    assert "EXT-999" not in json.dumps(current)
    assert len(json.dumps(current)) < 2500
    assert state_path.read_text(encoding="utf-8") == before_state

    reconcile = planning_reconcile(target=tmp_path)
    reconcile_external = reconcile["external_work_state"]
    assert reconcile["status"] == "clean"
    assert reconcile_external["item_count"] == 0
    assert reconcile_external["open_count"] == 0
    assert reconcile_external["untracked_open_count"] == 0
    assert reconcile_external["relevant_observation_count"] == 0
    assert reconcile_external["unmatched_backlog_count"] == 1000
    assert reconcile_external["backlog_metadata"] == {
        "total_item_count": 1000,
        "total_open_count": 1000,
        "total_closed_count": 0,
        "unmatched_count": 1000,
        "detail_only": True,
    }
    assert reconcile_external["admitted_observations"] == []
    assert reconcile["external_observation_inputs"]["observations"] == []
    assert reconcile["recommendations"] == ["No reconcile cleanup found from supplied provider-agnostic evidence."]
    assert "EXT-999" not in json.dumps(reconcile)
    assert len(json.dumps(reconcile)) < 8000


def test_planning_reconcile_applies_only_safe_prune_targets(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    decomposition_path = tmp_path / ".agentic-workspace/planning/decompositions/closed-migration.decomposition.json"
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
candidates = [
  { id = "closed-candidate", title = "Closed candidate", priority = "third", refs = "EXT-1", outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "None." },
]
""",
    )
    _write(
        decomposition_path,
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

    preview = planning_reconcile(target=tmp_path, apply_safe_prune=True, dry_run=True)

    assert preview["apply_result"]["dry_run"] is True
    assert preview["apply_result"]["applied_count"] == 3
    assert decomposition_path.exists()

    applied = planning_reconcile(target=tmp_path, apply_safe_prune=True)

    assert applied["apply_result"]["applied_count"] == 3
    assert applied["completed_work_reconciliation"]["cleanup_target_count"] == 0
    assert not decomposition_path.exists()
    state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    assert [lane["id"] for lane in state["roadmap"]["lanes"]] == ["open-lane"]
    assert state["roadmap"]["candidates"] == []


def test_planning_reconcile_syncs_stale_active_todo_projection(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/resume-lane.plan.json"
    record = installer_mod._build_execplan_record_from_todo_item(
        title="Resume Lane",
        item_id="resume-lane",
        status="active",
        why_now="Preserve the active intent.",
        next_action="Use the fresher execplan action.",
        done_when="The active intent is fully satisfied.",
    )
    _write(plan_path, json.dumps(record, indent=2))
    _write(
        state_path,
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "resume-lane", title = "Resume Lane", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/resume-lane.plan.json", why_now = "Old todo projection.", next_action = "Stale todo action.", done_when = "Old todo done text." },
]
queued_items = []
""",
    )

    reconcile = planning_reconcile(target=tmp_path)

    projection = reconcile["active_projection_reconciliation"]
    assert reconcile["status"] == "attention-needed"
    assert projection["status"] == "stale-projections"
    assert projection["safe_sync_count"] == 1
    assert projection["sync_targets"][0]["sync_action"] == "sync-active-todo-projection"
    assert projection["sync_targets"][0]["updated_fields"] == {"next_action": "Use the fresher execplan action."}

    preview = planning_reconcile(target=tmp_path, apply_safe_prune=True, dry_run=True)

    assert preview["apply_result"]["synced_count"] == 1
    assert tomllib.loads(state_path.read_text(encoding="utf-8"))["todo"]["active_items"][0]["next_action"] == "Stale todo action."

    applied = planning_reconcile(target=tmp_path, apply_safe_prune=True)

    assert applied["apply_result"]["synced_count"] == 1
    assert applied["active_projection_reconciliation"]["status"] == "clean"
    state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    assert state["todo"]["active_items"][0]["next_action"] == "Use the fresher execplan action."


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
