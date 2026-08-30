from __future__ import annotations

import shutil as _shutil
import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from planning_test_support import *
from repo_planning_bootstrap import cli as planning_cli


def _forged_timestamp_preflight_token() -> str:
    return "preflight-v1:4102444800"


def _write_live_execplan_state(tmp_path: Path, *, item_id: str, surface: str | None = None) -> None:
    surface = surface or f".agentic-workspace/planning/execplans/{item_id}.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  {{ id = "{item_id}", maturity = "active", status = "active", surface = "{surface}", why_now = "prove targeted execplan writer projection.", next_action = "continue implementation" }},
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )


def test_planning_summary_does_not_treat_legacy_handoff_metadata_as_authority(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json", why_now = "prove handoff role metadata is queryable.", decision_owner = "human", strategy_role = "product/architecture", owner_role = "implementation", delivery_role = "implementation", review_role = "validation", knowledge_owner = "planning/docs", handoff_ready = true },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_execplan_record(
        tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json",
        item_id="active-plan",
        status="in-progress",
    )

    summary = planning_summary(target=tmp_path)
    compact = planning_summary(target=tmp_path, profile="compact")
    handoff = planning_handoff(target=tmp_path)

    expected_role_metadata = {}
    assert summary["planning_revision"]["revision_id"]
    assert compact["planning_revision"]["revision_id"]
    assert summary["active_contract"]["role_metadata"] == expected_role_metadata
    assert summary["active_contract"]["next_role_needed"] == ""
    assert summary["planning_record"]["role_metadata"] == expected_role_metadata
    assert summary["handoff_contract"]["role_metadata"] == expected_role_metadata
    assert summary["handoff_contract"]["next_role_needed"] == ""
    assert "role_metadata" not in compact["handoff_contract"]
    assert compact["handoff_contract"]["ready_worker_prompt"]["status"] == "present"
    assert compact["handoff_contract"]["ready_worker_prompt"]["plan_path"] == ".agentic-workspace/planning/execplans/active-plan.plan.json"
    assert handoff["handoff_contract"]["role_metadata"] == expected_role_metadata


def test_delegation_decision_records_route_on_active_plan(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json", why_now = "prove delegation decision recording." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = installer_mod._build_execplan_record_from_todo_item(
        title="Active Plan",
        item_id="active-plan",
        status="in-progress",
        why_now="prove delegation decision recording.",
        next_action="record the bounded route.",
        done_when="the route is represented as a typed relationship.",
    )
    installer_mod._write_execplan_record(record_path=plan_path, record=record)

    result = record_delegation_decision(
        target=tmp_path,
        route="keep-local",
        skipped_reason="tightly coupled root routing and package checker change",
        expected_savings="low",
        actual_friction="none",
    )

    assert any(action.kind == "updated" and action.path == plan_path for action in result.actions)
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    assert record["relationships"]["delegation"]["state"] == "recorded"
    assert record["relationships"]["delegation"]["route"] == "keep-local"
    assert record["relationships"]["delegation"]["reason"] == "tightly coupled root routing and package checker change"
    assert record["specialist_contracts"][0]["kind"] == "planning-delegation/v1"


def test_delegation_decision_requires_skip_reason_for_keep_local(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")

    result = record_delegation_decision(target=tmp_path, plan="active-plan", route="keep-local")

    assert any(action.kind == "manual review" and "--skipped-reason" in action.detail for action in result.actions)


def test_delegation_decision_rejects_stale_expected_planning_revision(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "active-plan", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/active-plan.plan.json", why_now = "prove stale revision protection." },
]
queued_items = []
""",
    )
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    expected_revision = planning_revision(tmp_path)["revision_id"]

    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["drift_log"].append("External planning edit after the read surface.")
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    result = record_delegation_decision(
        target=tmp_path,
        route="keep-local",
        skipped_reason="would otherwise rely on stale planning state",
        expected_planning_revision=expected_revision,
    )

    assert any(warning["warning_class"] == "planning_revision_mismatch" for warning in result.warnings)
    assert any(action.kind == "manual review" and "revision changed" in action.detail for action in result.actions)
    stale_record = json.loads(plan_path.read_text(encoding="utf-8"))
    assert stale_record.get("post_decomposition_delegation", {}).get("status") != "recorded"


def test_targeted_execplan_writer_previews_applies_and_rejects_stale_owner(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    # Older compatibility fixtures do not carry the canonical owner revision.
    # The targeted writer deliberately requires it, so make this fixture a
    # canonical live owner instead of weakening the production guard.
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    planning_before = planning_revision(tmp_path)["revision_id"]
    lane_path = next((tmp_path / ".agentic-workspace/planning/lanes").glob("*.lane.json"))
    lane_revision = installer_mod._record_revision(json.loads(lane_path.read_text(encoding="utf-8")))

    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"next_action": "run the focused proof"},
        expected_planning_revision=planning_before,
        expected_owner_revision=record["revision"],
        expected_lane_revision=lane_revision,
    )

    assert preview["status"] == "preview"
    assert preview["changes"]["next_action"]["after"] == "run the focused proof"
    assert json.loads(plan_path.read_text(encoding="utf-8")).get("next_action") != "run the focused proof"

    applied = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"next_action": "run the focused proof"},
        expected_planning_revision=planning_before,
        expected_owner_revision=record["revision"],
        expected_lane_revision=lane_revision,
        apply=True,
    )
    assert applied["status"] == "applied"
    assert applied["projection_effects"]["state"]["todo.active_items.active-plan"]["after"]["next_action"] == "run the focused proof"
    updated = json.loads(plan_path.read_text(encoding="utf-8"))
    assert updated["next_action"] == "run the focused proof"
    assert updated["title"] == record["title"]
    receipt = json.loads((tmp_path / applied["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["result"]["state_revision_after"] == applied["state_revision_after"]
    assert receipt["result"]["lane_revision_after"] == applied["lane_revision_after"]
    assert receipt["result"]["postcondition"]["owner_revision"] == updated["revision"]
    replay = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"next_action": "run the focused proof"},
        expected_planning_revision=planning_before,
        expected_owner_revision=record["revision"],
        expected_lane_revision=lane_revision,
        apply=True,
    )
    assert replay["status"] == "already-applied"
    assert replay["receipt"]["result"]["state_revision_after"] == applied["state_revision_after"]
    assert json.loads(plan_path.read_text(encoding="utf-8"))["revision"] == updated["revision"]

    stale = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"next_action": "should not write"},
        expected_planning_revision=planning_revision(tmp_path)["revision_id"],
        expected_owner_revision=record["revision"],
        expected_lane_revision=lane_revision,
        apply=True,
    )
    assert stale["status"] == "stale-owner-revision"
    assert json.loads(plan_path.read_text(encoding="utf-8"))["next_action"] == "run the focused proof"


def test_targeted_execplan_writer_requires_both_revision_guards(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    result = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"next_action": "must not write"},
        expected_planning_revision="",
        expected_owner_revision="",
        apply=True,
    )

    assert result == {
        "kind": "agentic-planning/targeted-execplan-write/v1",
        "status": "missing-revision-guard",
        "required": ["expected_planning_revision", "expected_owner_revision"],
    }


def test_targeted_execplan_writer_replay_rejects_invalidated_postcondition(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    revision = planning_revision(tmp_path)["revision_id"]
    patch = {"next_action": "recorded result"}
    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
    )
    assert preview["status"] == "preview"
    applied = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )
    assert applied["status"] == "applied"

    externally_changed = json.loads(plan_path.read_text(encoding="utf-8"))
    externally_changed["revision"] += 1
    externally_changed["next_action"] = "external owner mutation"
    plan_path.write_text(json.dumps(externally_changed, indent=2) + "\n", encoding="utf-8")
    replay = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )

    assert replay["status"] == "stale-applied-receipt"
    assert set(replay["postcondition_admission"]["reasons"]) >= {
        "owner-revision",
        "owner-fields",
        "planning-revision",
    }
    assert json.loads(plan_path.read_text(encoding="utf-8"))["next_action"] == "external owner mutation"


def test_targeted_execplan_writer_apply_runs_internal_preflight_without_bearer_token(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    planning_before = planning_revision(tmp_path)["revision_id"]

    result = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"next_action": "must not write"},
        expected_planning_revision=planning_before,
        expected_owner_revision=1,
        apply=True,
    )

    assert result["status"] == "applied"
    assert result["preflight_admission"]["status"] == "admitted"
    assert result["preflight_admission"]["authority"] == "sealed-internal-preflight-result"


def test_targeted_execplan_writer_rejects_forged_timestamp_preflight_token(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    revision = planning_revision(tmp_path)["revision_id"]

    result = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"next_action": "must not write"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
        preflight_token=_forged_timestamp_preflight_token(),
    )

    assert result["status"] == "caller-preflight-token-rejected"
    assert json.loads(plan_path.read_text(encoding="utf-8"))["revision"] == 1


def test_targeted_execplan_writer_rejects_caller_constructed_internal_preflight_result(tmp_path: Path) -> None:
    request = {
        "owner": ".agentic-workspace/planning/execplans/active-plan.plan.json",
        "patch": {"next_action": "must not write"},
        "planning_revision": "planning-revision",
        "owner_revision": 1,
        "lane_revision": "",
    }
    admission = installer_mod._admit_targeted_write_preflight(
        result={"kind": "agentic-planning/targeted-write-preflight-receipt/v1", "status": "issued"},
        target_root=tmp_path,
        request=request,
        owner_ref=request["owner"],
        owner_revision=1,
        lane_ref="",
        lane_revision="",
    )
    with pytest.raises(TypeError, match="issued only by the internal preflight operation"):
        installer_mod._TargetedWritePreflightResult(facts={}, issuer=object())

    assert admission["status"] == "unadmitted-preflight-result"


def test_targeted_execplan_writer_rejects_cross_target_preview_mapping_as_authority(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    other_root = tmp_path / "other"
    install_bootstrap(target=source_root)
    plan_path = source_root / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(source_root, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    revision = planning_revision(source_root)["revision_id"]
    preview = installer_mod.targeted_execplan_write(
        target=source_root,
        plan="active-plan",
        patch={"next_action": "target-bound"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
    )
    request = {
        "owner": ".agentic-workspace/planning/execplans/active-plan.plan.json",
        "patch": {"next_action": "target-bound"},
        "planning_revision": revision,
        "owner_revision": 1,
        "lane_revision": "",
    }
    sealed = installer_mod._run_targeted_write_preflight(
        target_root=source_root,
        request=request,
        owner_ref=request["owner"],
        owner_revision=1,
        lane_ref="",
        lane_revision="",
        preflight_max_age_seconds=900,
    )

    _shutil.copytree(source_root / ".agentic-workspace", other_root / ".agentic-workspace")
    cross_target_admission = installer_mod._admit_targeted_write_preflight(
        result=sealed,
        target_root=other_root,
        request=request,
        owner_ref=request["owner"],
        owner_revision=1,
        lane_ref="",
        lane_revision="",
    )
    result = installer_mod.targeted_execplan_write(
        target=other_root,
        plan="active-plan",
        patch={"next_action": "target-bound"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
        preflight_token=json.dumps(preview),
    )

    assert result["status"] == "caller-preflight-token-rejected"
    assert cross_target_admission["status"] == "stale-preflight-result"
    assert "target_root" in cross_target_admission["stale_fields"]
    other_plan = other_root / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    assert json.loads(other_plan.read_text(encoding="utf-8"))["revision"] == 1


def test_targeted_execplan_writer_rejects_missing_or_stale_lane_guard(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/lane-plan.plan.json"
    _write_execplan_record(plan_path, item_id="lane-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    lane_path = next((tmp_path / ".agentic-workspace/planning/lanes").glob("*.lane.json"))
    lane_record = json.loads(lane_path.read_text(encoding="utf-8"))
    lane_record["current_slice"] = "lane-plan"
    installer_mod._write_lane_record(record_path=lane_path, record=lane_record)
    lane_revision = installer_mod._record_revision(json.loads(lane_path.read_text(encoding="utf-8")))
    revision = planning_revision(tmp_path)["revision_id"]

    missing = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"next_action": "prove"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )
    stale = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"next_action": "prove"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        expected_lane_revision=f"stale-{lane_revision}",
        apply=True,
    )

    assert missing["status"] == "missing-lane-revision-guard"
    assert stale["status"] == "stale-lane-revision"
    assert json.loads(plan_path.read_text(encoding="utf-8"))["revision"] == 1


@pytest.mark.parametrize("mutation_owner", ["owner", "lane"])
def test_targeted_execplan_writer_rejects_owner_or_lane_mutation_after_preview(tmp_path: Path, mutation_owner: str) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/lane-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="lane-plan")
    _write_execplan_record(plan_path, item_id="lane-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    lane_path = next((tmp_path / ".agentic-workspace/planning/lanes").glob("*.lane.json"))
    lane_record = json.loads(lane_path.read_text(encoding="utf-8"))
    lane_record["current_slice"] = "lane-plan"
    installer_mod._write_lane_record(record_path=lane_path, record=lane_record)
    lane_revision = installer_mod._record_revision(json.loads(lane_path.read_text(encoding="utf-8")))
    revision = planning_revision(tmp_path)["revision_id"]
    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"next_action": "must be preview-bound"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        expected_lane_revision=lane_revision,
    )
    assert preview["status"] == "preview"

    if mutation_owner == "owner":
        mutated = json.loads(plan_path.read_text(encoding="utf-8"))
        mutated["revision"] = 2
        mutated["next_action"] = "external owner change"
        plan_path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
    else:
        mutated_lane = json.loads(lane_path.read_text(encoding="utf-8"))
        mutated_lane["title"] = "external lane change"
        installer_mod._write_lane_record(record_path=lane_path, record=mutated_lane)

    result = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"next_action": "must be preview-bound"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        expected_lane_revision=lane_revision,
        apply=True,
    )

    assert result["status"] in {"stale-planning-revision", "stale-owner-revision", "stale-lane-revision"}
    assert json.loads(plan_path.read_text(encoding="utf-8")).get("next_action") != "must be preview-bound"


def test_targeted_execplan_writer_cli_preview_apply_and_projection_effects(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    unrelated_path = tmp_path / ".agentic-workspace/planning/execplans/unrelated-plan.plan.json"
    completed_path = tmp_path / ".agentic-workspace/planning/archive/completed-plan.plan.json"
    template_path = tmp_path / ".agentic-workspace/planning/templates/default.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    _write_execplan_record(unrelated_path, item_id="unrelated-plan", status="in-progress")
    _write_execplan_record(completed_path, item_id="completed-plan", status="done")
    _write(template_path, '{"kind":"agentic-planning-template","template_id":"default","body":"do not touch"}')
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    unrelated_before = unrelated_path.read_bytes()
    completed_before = completed_path.read_bytes()
    template_before = template_path.read_bytes()
    revision = planning_revision(tmp_path)["revision_id"]

    assert (
        planning_cli.main(
            [
                "targeted-write",
                "active-plan",
                "--target",
                str(tmp_path),
                "--patch",
                json.dumps({"next_action": "run generated CLI proof"}),
                "--expect-planning-revision",
                revision,
                "--expect-owner-revision",
                "1",
                "--format",
                "json",
            ]
        )
        == 0
    )
    preview = json.loads(capsys.readouterr().out)
    assert preview["status"] == "preview"
    assert preview["changes"]["next_action"]["after"] == "run generated CLI proof"
    assert json.loads(plan_path.read_text(encoding="utf-8")).get("next_action") != "run generated CLI proof"
    assert unrelated_path.read_bytes() == unrelated_before
    assert completed_path.read_bytes() == completed_before
    assert template_path.read_bytes() == template_before

    assert (
        planning_cli.main(
            [
                "targeted-write",
                "active-plan",
                "--target",
                str(tmp_path),
                "--patch",
                json.dumps({"next_action": "run generated CLI proof"}),
                "--expect-planning-revision",
                revision,
                "--expect-owner-revision",
                "1",
                "--apply",
                "--format",
                "json",
            ]
        )
        == 0
    )
    applied = json.loads(capsys.readouterr().out)
    assert applied["status"] == "applied"
    assert applied["projection_effects"]["state"]["todo.active_items.active-plan"]["after"]["next_action"] == "run generated CLI proof"
    assert json.loads(plan_path.read_text(encoding="utf-8"))["next_action"] == "run generated CLI proof"
    assert unrelated_path.read_bytes() == unrelated_before
    assert completed_path.read_bytes() == completed_before
    assert template_path.read_bytes() == template_before

    replay_revision = planning_revision(tmp_path)["revision_id"]
    assert (
        planning_cli.main(
            [
                "targeted-write",
                "active-plan",
                "--target",
                str(tmp_path),
                "--patch",
                json.dumps({"next_action": "run generated CLI proof"}),
                "--expect-planning-revision",
                replay_revision,
                "--expect-owner-revision",
                "2",
                "--format",
                "json",
            ]
        )
        == 0
    )
    replay_preview = json.loads(capsys.readouterr().out)
    assert replay_preview["apply_preflight"]["mode"] == "composed-internal-preflight"
    assert (
        planning_cli.main(
            [
                "targeted-write",
                "active-plan",
                "--target",
                str(tmp_path),
                "--patch",
                json.dumps({"next_action": "run generated CLI proof"}),
                "--expect-planning-revision",
                replay_revision,
                "--expect-owner-revision",
                "2",
                "--apply",
                "--format",
                "json",
            ]
        )
        == 0
    )
    replay = json.loads(capsys.readouterr().out)
    assert replay["status"] == "no-op"
    assert unrelated_path.read_bytes() == unrelated_before
    assert completed_path.read_bytes() == completed_before
    assert template_path.read_bytes() == template_before


def test_targeted_execplan_writer_lifecycle_updates_lane_projection(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/lane-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="lane-plan")
    _write_execplan_record(plan_path, item_id="lane-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    lane_path = next((tmp_path / ".agentic-workspace/planning/lanes").glob("*.lane.json"))
    lane_record = json.loads(lane_path.read_text(encoding="utf-8"))
    lane_record["current_slice"] = "lane-plan"
    lane_record["slice_sequence"][0]["status"] = "active"
    lane_record["slice_sequence"][0]["execplan_ref"] = ".agentic-workspace/planning/execplans/lane-plan.plan.json"
    installer_mod._write_lane_record(record_path=lane_path, record=lane_record)
    lane_revision = installer_mod._record_revision(json.loads(lane_path.read_text(encoding="utf-8")))
    revision = planning_revision(tmp_path)["revision_id"]
    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"lifecycle": "closed", "phase": "complete"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        expected_lane_revision=lane_revision,
    )
    assert preview["status"] == "preview"
    applied = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"lifecycle": "closed", "phase": "complete"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        expected_lane_revision=lane_revision,
        apply=True,
    )

    assert applied["status"] == "applied"
    assert applied["projection_effects"]["state"]["todo.active_items.lane-plan"]["after"] is None
    assert applied["projection_effects"]["lane"]["current_slice"] == {"before": "lane-plan", "after": ""}
    assert applied["projection_effects"]["lane"]["slice_sequence[0]"]["after"]["status"] == "completed"
    assert json.loads(lane_path.read_text(encoding="utf-8"))["current_slice"] == ""
    state = installer_mod._read_state_from_toml(tmp_path)
    assert state["todo"]["active_items"][0]["id"] == "lane-plan"
    receipt = json.loads((tmp_path / applied["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["result"]["postcondition"]["terminal_owner_absent_from_active_state"] is True


def test_targeted_execplan_writer_rejects_phase_only_terminal_projection(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/lane-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="lane-plan")
    _write_execplan_record(plan_path, item_id="lane-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    lane_path = next((tmp_path / ".agentic-workspace/planning/lanes").glob("*.lane.json"))
    lane_record = json.loads(lane_path.read_text(encoding="utf-8"))
    lane_record["current_slice"] = "lane-plan"
    lane_record["slice_sequence"][0]["status"] = "active"
    lane_record["slice_sequence"][0]["execplan_ref"] = ".agentic-workspace/planning/execplans/lane-plan.plan.json"
    installer_mod._write_lane_record(record_path=lane_path, record=lane_record)
    lane_revision = installer_mod._record_revision(json.loads(lane_path.read_text(encoding="utf-8")))

    result = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"phase": "complete"},
        expected_planning_revision=planning_revision(tmp_path)["revision_id"],
        expected_owner_revision=1,
        expected_lane_revision=lane_revision,
        apply=True,
    )

    assert result["status"] == "unsupported-projection-patch"
    assert result["unsupported_fields"] == ["phase"]
    assert installer_mod._execplan_lifecycle(json.loads(plan_path.read_text(encoding="utf-8"))) == "live"
    assert json.loads(lane_path.read_text(encoding="utf-8"))["current_slice"] == "lane-plan"
    state = installer_mod._read_state_from_toml(tmp_path)
    assert state["todo"]["active_items"][0]["id"] == "lane-plan"


def test_targeted_execplan_writer_allows_live_phase_reconciliation(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    record["phase"] = "shaping"
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    revision = planning_revision(tmp_path)["revision_id"]

    applied = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={
            "phase": "validation",
            "next_action": "await independent review",
            "proof": {"summary": "Implementation revision abc123; independent review pending."},
        },
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )

    assert applied["status"] == "applied"
    updated = json.loads(plan_path.read_text(encoding="utf-8"))
    assert installer_mod._execplan_lifecycle(updated) == "live"
    assert updated["phase"] == "validation"
    assert updated["canonical_core"]["next_action"] == "await independent review"
    state = installer_mod._read_state_from_toml(tmp_path)
    assert state["todo"]["active_items"][0]["status"] == "active"
    assert "phase" not in state["todo"]["active_items"][0]
    assert state["todo"]["active_items"][0]["next_action"] == "continue implementation"
    assert "proof" not in state["todo"]["active_items"][0]


def test_targeted_execplan_writer_rejects_unsupported_parent_projection(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    result = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"parent": {"id": "new-parent"}},
        expected_planning_revision=planning_revision(tmp_path)["revision_id"],
        expected_owner_revision=1,
        apply=True,
    )

    assert result["status"] == "unsupported-projection-patch"
    assert result["unsupported_fields"] == ["parent"]
    assert json.loads(plan_path.read_text(encoding="utf-8"))["revision"] == 1


def test_targeted_execplan_writer_migrates_supported_fields_and_preserves_unrelated_bytes(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    unrelated_path = tmp_path / ".agentic-workspace/planning/execplans/unrelated.plan.json"
    template_path = tmp_path / ".agentic-workspace/planning/execplans/TEMPLATE.md"
    history_path = tmp_path / ".agentic-workspace/planning/archive/completed-history.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    _write_execplan_record(unrelated_path, item_id="unrelated", status="queued")
    _write_execplan_record(history_path, item_id="completed-history", status="completed")
    template_path.write_text("# template\n\nleave this byte-identical\n", encoding="utf-8", newline="\n")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    record["relationships"] = {"external": {"issue": "#2283"}}
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    unrelated_before = unrelated_path.read_bytes()
    template_before = template_path.read_bytes()
    history_before = history_path.read_bytes()
    revision = planning_revision(tmp_path)["revision_id"]
    patch = {
        "intent": {"outcome": "Tightened outcome", "non_goals": ["Do not widen scope."]},
        "scope": {"owned": ["packages/planning"], "effects": ["bounded targeted writer migration"]},
        "blockers": ["proof cleared"],
        "next_action": "run targeted writer proof",
        "proof": {"claims": ["Writer preserves unspecified fields."], "requirements": ["make test-planning"], "refs": []},
        "continuation": {"owner": "none", "residual_intent": "none"},
    }
    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
    )
    assert preview["status"] == "preview"

    applied = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )

    assert applied["status"] == "applied"
    updated = json.loads(plan_path.read_text(encoding="utf-8"))
    for key, value in patch.items():
        assert updated[key] == value
    assert updated["relationships"] == {"external": {"issue": "#2283"}}
    assert unrelated_path.read_bytes() == unrelated_before
    assert template_path.read_bytes() == template_before
    assert history_path.read_bytes() == history_before
    noop_revision = planning_revision(tmp_path)["revision_id"]
    noop_preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=noop_revision,
        expected_owner_revision=updated["revision"],
    )
    assert noop_preview["status"] == "preview"
    noop = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=noop_revision,
        expected_owner_revision=updated["revision"],
        apply=True,
    )
    assert noop["status"] == "no-op"
    assert json.loads(plan_path.read_text(encoding="utf-8"))["revision"] == updated["revision"]
    replay = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )
    assert replay["status"] == "already-applied"
    assert replay["receipt"]["request"]["owner_revision"] == 1


def test_targeted_execplan_writer_reconciles_only_external_posture_relationship(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    record["relationships"] = {
        "proof_posture": {"state": "accepted", "refs": ["proof://accepted"]},
        "external_posture": {"state": "unobserved", "refs": []},
        "integration": {"status": "feature-complete-integration-pending", "proposal_id": "active-plan-archive"},
    }
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    relationships = json.loads(json.dumps(record["relationships"]))
    relationships["external_posture"] = {"state": "observed", "refs": ["github:pr#2871", "github:pr#2872"]}
    revision = planning_revision(tmp_path)["revision_id"]

    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"relationships": relationships},
        expected_planning_revision=revision,
        expected_owner_revision=1,
    )
    assert preview["status"] == "preview"
    assert set(preview["changes"]) == {"relationships"}

    applied = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"relationships": relationships},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )
    assert applied["status"] == "applied"
    updated = json.loads(plan_path.read_text(encoding="utf-8"))
    assert updated["relationships"] == relationships

    unauthorized = json.loads(json.dumps(relationships))
    unauthorized["proof_posture"] = {"state": "unobserved", "refs": []}
    rejected = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch={"relationships": unauthorized},
        expected_planning_revision=planning_revision(tmp_path)["revision_id"],
        expected_owner_revision=updated["revision"],
    )
    assert rejected["status"] == "unsupported-relationships-patch"
    assert rejected["changed_relationships"] == ["proof_posture"]


def test_targeted_execplan_writer_preview_delta_matches_apply_delta(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    revision = planning_revision(tmp_path)["revision_id"]
    patch = {"next_action": "prove preview/apply equivalence"}

    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=False,
    )
    applied = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )

    assert preview["status"] == "preview"
    assert applied["status"] == "applied"
    assert applied["changes"] == preview["changes"]
    assert applied["projection_effects"] == preview["projection_effects"]


def test_targeted_execplan_writer_handles_missing_ambiguous_and_unbound_owners(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    missing = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="missing-plan",
        patch={"next_action": "x"},
        expected_planning_revision="rev",
        expected_owner_revision=1,
        apply=True,
    )
    assert missing["status"] == "ambiguous-or-missing-owner"

    plan_path = tmp_path / ".agentic-workspace/planning/execplans/unbound.plan.json"
    _write_execplan_record(plan_path, item_id="unbound", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    revision = planning_revision(tmp_path)["revision_id"]
    unbound_preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="unbound",
        patch={"next_action": "supported without a lane relation"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
    )
    assert unbound_preview["status"] == "preview"
    unbound = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="unbound",
        patch={"next_action": "supported without a lane relation"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )
    assert unbound["status"] == "applied"
    assert unbound["lane_revision"] is None

    lane_dir = tmp_path / ".agentic-workspace/planning/lanes"
    lane_paths = sorted(lane_dir.glob("*.lane.json"))
    first = json.loads(lane_paths[0].read_text(encoding="utf-8"))
    first["current_slice"] = "unbound"
    installer_mod._write_lane_record(record_path=lane_paths[0], record=first)
    second = {**first, "id": "duplicate-lane", "current_slice": "unbound"}
    duplicate_path = lane_dir / "duplicate-lane.lane.json"
    installer_mod._write_lane_record(record_path=duplicate_path, record=second)
    ambiguous = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="unbound",
        patch={"next_action": "must not apply"},
        expected_planning_revision=planning_revision(tmp_path)["revision_id"],
        expected_owner_revision=2,
        apply=True,
    )
    assert ambiguous["status"] == "ambiguous-lane-relation"


def test_targeted_execplan_writer_rolls_back_late_lane_write_failure(tmp_path: Path, monkeypatch) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/lane-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="lane-plan")
    _write_execplan_record(plan_path, item_id="lane-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    lane_path = next((tmp_path / ".agentic-workspace/planning/lanes").glob("*.lane.json"))
    lane_record = json.loads(lane_path.read_text(encoding="utf-8"))
    lane_record["current_slice"] = "lane-plan"
    lane_record["slice_sequence"][0]["status"] = "active"
    lane_record["slice_sequence"][0]["execplan_ref"] = ".agentic-workspace/planning/execplans/lane-plan.plan.json"
    installer_mod._write_lane_record(record_path=lane_path, record=lane_record)
    lane_revision = installer_mod._record_revision(json.loads(lane_path.read_text(encoding="utf-8")))
    revision = planning_revision(tmp_path)["revision_id"]
    owner_before = plan_path.read_bytes()
    state_before = (tmp_path / ".agentic-workspace/planning/state.toml").read_bytes()
    lane_before = lane_path.read_bytes()
    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"lifecycle": "archived", "phase": "complete"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        expected_lane_revision=lane_revision,
    )
    assert preview["status"] == "preview"

    original_write_lane = installer_mod._write_lane_record

    def fail_lane_write(*, record_path: Path, record: dict) -> None:
        if record_path == lane_path:
            raise OSError("injected lane write failure")
        original_write_lane(record_path=record_path, record=record)

    monkeypatch.setattr(installer_mod, "_write_lane_record", fail_lane_write)

    result = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="lane-plan",
        patch={"lifecycle": "archived", "phase": "complete"},
        expected_planning_revision=revision,
        expected_owner_revision=1,
        expected_lane_revision=lane_revision,
        apply=True,
    )

    assert result["status"] == "rolled-back"
    assert plan_path.read_bytes() == owner_before
    assert (tmp_path / ".agentic-workspace/planning/state.toml").read_bytes() == state_before
    assert lane_path.read_bytes() == lane_before
    assert not list((tmp_path / ".agentic-workspace/local/planning/targeted-execplan-receipts").glob("*.json"))


@pytest.mark.parametrize("failure_boundary", ["owner", "state", "receipt"])
def test_targeted_execplan_writer_rolls_back_each_write_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_boundary: str
) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/active-plan.plan.json"
    _write_live_execplan_state(tmp_path, item_id="active-plan")
    _write_execplan_record(plan_path, item_id="active-plan", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["revision"] = 1
    plan_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    owner_before = plan_path.read_bytes()
    state_before = state_path.read_bytes()
    revision = planning_revision(tmp_path)["revision_id"]
    receipt_dir = tmp_path / ".agentic-workspace/local/planning/targeted-execplan-receipts"
    patch = {"next_action": f"would fail at {failure_boundary}"}
    preview = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
    )
    assert preview["status"] == "preview"

    if failure_boundary == "owner":
        original_write_execplan = installer_mod._write_execplan_record

        def fail_owner_write(*, record_path: Path, record: dict, render_markdown: bool = False) -> None:
            if record_path == plan_path:
                raise OSError("injected owner write failure")
            original_write_execplan(record_path=record_path, record=record, render_markdown=render_markdown)

        monkeypatch.setattr(installer_mod, "_write_execplan_record", fail_owner_write)
    elif failure_boundary == "state":
        original_write_state = installer_mod._write_state_to_toml

        def fail_state_write(target_root: Path, state: dict) -> None:
            raise OSError("injected state write failure")

        monkeypatch.setattr(installer_mod, "_write_state_to_toml", fail_state_write)
        assert original_write_state
    else:
        original_write_text = Path.write_text

        def fail_receipt_write(self: Path, data: str, *args, **kwargs) -> int:
            if self.parent == receipt_dir:
                raise OSError("injected receipt write failure")
            return original_write_text(self, data, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", fail_receipt_write)

    result = installer_mod.targeted_execplan_write(
        target=tmp_path,
        plan="active-plan",
        patch=patch,
        expected_planning_revision=revision,
        expected_owner_revision=1,
        apply=True,
    )

    assert result["status"] == "rolled-back"
    assert plan_path.read_bytes() == owner_before
    assert state_path.read_bytes() == state_before
    assert not list(receipt_dir.glob("*.json"))


def test_planning_summary_and_handoff_expose_structured_execplan_references(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: keep explicit references queryable for continuation and handoff.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        references=[
            {
                "kind": "issue",
                "target": "#280",
                "role": "related-work",
                "label": "Structured references",
            },
            {
                "kind": "file",
                "target": "packages/planning/src/repo_planning_bootstrap/installer.py",
                "role": "implementation-target",
                "locator": "L2000-L2100",
            },
        ],
    )

    summary = planning_summary(target=tmp_path)
    handoff = planning_handoff(target=tmp_path)

    assert summary["planning_record"]["references"] == [
        {
            "kind": "issue",
            "target": "#280",
            "role": "related-work",
            "label": "Structured references",
        },
        {
            "kind": "file",
            "target": "packages/planning/src/repo_planning_bootstrap/installer.py",
            "role": "implementation-target",
            "locator": "L2000-L2100",
        },
    ]
    assert "#280" in summary["active_contract"]["minimal_refs"]
    assert "packages/planning/src/repo_planning_bootstrap/installer.py" in summary["active_contract"]["minimal_refs"]
    assert handoff["handoff_contract"]["references"][0]["target"] == "#280"
    assert handoff["handoff_contract"]["references"][1]["role"] == "implementation-target"


def test_planning_summary_and_handoff_project_review_residue_from_structured_references(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: keep review residue queryable without rereading full review artifacts.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        references=[
            {
                "kind": "review",
                "target": ".agentic-workspace/planning/reviews/review-alpha.review.json",
                "role": "review-target",
                "label": "Review Alpha",
            }
        ],
    )
    _write_review_record(tmp_path / ".agentic-workspace" / "planning" / "reviews" / "review-alpha.review.json")

    summary = planning_summary(target=tmp_path)
    handoff = planning_handoff(target=tmp_path)

    assert summary["planning_record"]["review_residue"] == [
        {
            "kind": "review",
            "target": ".agentic-workspace/planning/reviews/review-alpha.review.json",
            "role": "review-target",
            "label": "Review Alpha",
            "title": "Review Alpha",
            "finding_count": 1,
            "finding_titles": ["stale residue"],
            "promotion_targets": [".agentic-workspace/planning/state.toml (roadmap)"],
            "recommendation": {
                "promote": "yes",
                "defer": "no",
                "dismiss": "no",
            },
            "retention": {
                "closeout shape": "shrink",
                "trigger": "after the finding is promoted into planning state",
                "proof surface": "canonical review record plus promoted planning residue",
            },
        }
    ]
    assert handoff["handoff_contract"]["review_residue"][0]["target"] == ".agentic-workspace/planning/reviews/review-alpha.review.json"
    assert handoff["handoff_contract"]["review_residue"][0]["finding_titles"] == ["stale residue"]
    assert handoff["handoff_contract"]["review_residue"][0]["retention"]["closeout shape"] == "shrink"


def test_planning_handoff_schema_names_required_worker_packet_fields(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")

    handoff = planning_handoff(target=tmp_path)

    assert handoff["handoff_contract"]["status"] == "unavailable"
    assert handoff["schema"]["required_worker_packet_fields"] == [
        "intent",
        "constraints",
        "read_first_refs",
        "owned_scope",
        "proof_expectations",
        "stop_conditions",
        "return_contract",
        "target_posture",
    ]
    assert handoff["schema"]["ready_worker_prompt_field"] == "handoff_contract.ready_worker_prompt"
    assert "bounded execplan" in handoff["schema"]["unavailable_fallback"]


def test_planning_handoff_derives_compact_worker_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    handoff = planning_handoff(target=tmp_path)

    assert handoff["kind"] == "planning-handoff/v1"
    assert handoff["schema"]["schema_version"] == "planning-handoff-schema/v1"
    assert handoff["schema"]["canonical_doc"] == ".agentic-workspace/docs/execution-flow-contract.md"
    assert handoff["handoff_contract"]["status"] == "present"
    assert handoff["handoff_contract"]["next_action"] == "Add one checker."
    assert handoff["handoff_contract"]["capability_posture"]["execution class"] == "mechanical-follow-through"
    assert handoff["handoff_contract"]["capability_posture"]["recommended strength"] == "weak"
    assert handoff["handoff_contract"]["post_decomposition_delegation"]["status"] == "evaluated"
    assert "delegate-exploration" in handoff["handoff_contract"]["post_decomposition_delegation"]["route candidates"]
    assert handoff["handoff_contract"]["delegation_outcome_feedback"]["route chosen"] == "keep-local"
    assert handoff["handoff_contract"]["context_budget"]["status"] == "present"
    assert handoff["handoff_contract"]["intent_interpretation"]["status"] == "present"
    assert handoff["handoff_contract"]["execution_bounds"]["allowed paths"] == "scripts/check/check_planning_surfaces.py"
    assert handoff["handoff_contract"]["stop_conditions"]["stop when"].startswith("the work needs broader")
    assert handoff["handoff_contract"]["return_with"]["execution_summary_fields"][3] == "post-work posterity capture"
    assert handoff["handoff_contract"]["return_with"]["finished_run_review_fields"][0] == "review status"
    assert handoff["handoff_contract"]["return_with"]["finished_run_review_fields"][4] == "config compliance"
    assert handoff["handoff_contract"]["return_with"]["delegation_outcome_feedback_fields"] == [
        "route chosen",
        "route skipped reason",
        "expected savings",
        "actual friction",
        "proof result",
        "quality concern",
        "decomposition adjustment",
    ]
    assert handoff["handoff_contract"]["return_with"]["prose_templates"]["handoff_or_closeout"]["sections"] == [
        "Intent",
        "What changed",
        "Proof",
        "Remaining risk",
        "Durable residue",
        "Next owner",
    ]
    assert handoff["handoff_contract"]["worker_contract"]["allowed_execution_methods"][1] == "read-only exploration"
    assert handoff["handoff_contract"]["worker_contract"]["worker_owns_by_default"][0] == (
        "read-only exploration for one explicit question when assigned"
    )
    assert handoff["handoff_contract"]["worker_contract"]["worker_must_not_own_by_default"][0] == "roadmap routing"
    prompt = handoff["handoff_contract"]["ready_worker_prompt"]
    assert prompt["kind"] == "planning-ready-worker-prompt/v1"
    assert prompt["status"] == "present"
    assert prompt["source"] == "planning-handoff-contract"
    assert "Implement the active plan in `.agentic-workspace/planning/execplans/plan-alpha.md`." in prompt["copy_paste"]
    assert "Return using this template:" in prompt["copy_paste"]
    assert "- changed files / changed surfaces:" in prompt["copy_paste"]
    assert "scripts/check/check_planning_surfaces.py" in prompt["copy_paste"]
    assert prompt["return_template"]["fields"]["execution_run"][5] == "changed surfaces"
    assert prompt["return_template"]["fields"]["finished_run_review"][0] == "review status"
    assert prompt["return_template"]["fields"]["delegation_outcome_feedback"][0] == "route chosen"
    assert "Do not broaden beyond the plan's owned write scope." in prompt["constraints"]


def test_planning_handoff_includes_manual_external_relay_prompt_for_epic_intent_shaping(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "product-epic", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/product-epic.plan.json", why_now = "shape product intent before implementation." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = installer_mod._build_execplan_record_from_todo_item(
        title="Product Epic",
        item_id="product-epic",
        status="in-progress",
        why_now="shape product intent before implementation.",
        next_action="Clarify the product intent and user policy boundaries before implementation.",
        done_when="first implementation slice can be shaped safely.",
    )
    record["specialist_contracts"] = [{"kind": "planning-epic/v1", "target": "GitHub #product-epic", "revision": 1}]
    record["intent"]["outcome"] = "Clarify product intent and user policy boundaries before implementation."
    installer_mod._write_execplan_record(
        record_path=tmp_path / ".agentic-workspace/planning/execplans/product-epic.plan.json",
        record=record,
    )

    handoff = planning_handoff(target=tmp_path)

    relay = handoff["manual_external_relay"]
    assert relay["status"] == "appropriate"
    assert relay["interrupt_cost"] == "human-relay-required"
    assert "not asked to code" in relay["ready_to_forward_prompt"]["copy_paste"]
    assert "Do not write code" in relay["ready_to_forward_prompt"]["constraints"][0]


def test_planning_handoff_command_emits_json(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    exit_code = planning_cli.main(["handoff", "--target", str(tmp_path), "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "planning-handoff/v1"
    assert payload["profile"] == "decision-envelope"
    assert payload["handoff_contract"]["status"] == "present"
    assert payload["construction"]["historical_sources_loaded"] is False
    assert payload["detail_routes"]["exact_contract"].endswith("--select handoff_contract --format json")
