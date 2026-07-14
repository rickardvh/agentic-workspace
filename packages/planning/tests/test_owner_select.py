from __future__ import annotations

import copy
import json
import tomllib
from pathlib import Path

import pytest

from repo_planning_bootstrap.installer import (
    OWNER_SELECTION_RECEIPT_SCHEMA_PATH,
    create_execplan_scaffold,
    create_lane_record,
    install_bootstrap,
    planning_revision,
    planning_summary,
    select_existing_owner,
)


def _create_owner(root: Path, owner_id: str, *, activate: bool = False) -> Path:
    result = create_execplan_scaffold(
        plan_id=owner_id,
        title=owner_id.replace("-", " ").title(),
        target=root,
        activate=activate,
    )
    assert not [action for action in result.actions if action.kind == "manual review"]
    return root / f".agentic-workspace/planning/execplans/{owner_id}.plan.json"


def test_owner_select_local_is_narrow_self_proving_and_idempotent(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_path = _create_owner(tmp_path, "existing-owner")
    unrelated_path = _create_owner(tmp_path, "unrelated-owner")
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    before = {
        "owner": owner_path.read_bytes(),
        "unrelated": unrelated_path.read_bytes(),
        "state": state_path.read_bytes(),
    }

    result = select_existing_owner(
        "existing-owner",
        target=tmp_path,
        current_work_id="thread-123",
        expected_planning_revision=planning_revision(tmp_path)["revision_id"],
    )

    assert [action.kind for action in result.actions] == ["updated", "receipt"]
    receipt = result.operation_receipt
    assert receipt["outcome"] == "selected"
    assert receipt["mode"] == "local"
    assert receipt["selected_owner"]["id"] == "existing-owner"
    assert receipt["changed_fields"] == ["local.current_work.selected_owner"]
    assert receipt["validation_outcome"] == "passed"
    assert not [action for action in result.actions if action.kind == "proof"]
    assert owner_path.read_bytes() == before["owner"]
    assert unrelated_path.read_bytes() == before["unrelated"]
    assert state_path.read_bytes() == before["state"]

    selection_path = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    receipt_path = tmp_path / ".agentic-workspace/local/planning/owner-selection-receipt.json"
    before_selection = selection_path.read_bytes()
    before_receipt = receipt_path.read_bytes()
    repeated = select_existing_owner("existing-owner", target=tmp_path, current_work_id="thread-123")
    assert [action.kind for action in repeated.actions] == ["no-op"]
    assert repeated.operation_receipt["outcome"] == "no-op"
    assert repeated.operation_receipt["changed_fields"] == []
    assert selection_path.read_bytes() == before_selection
    assert receipt_path.read_bytes() == before_receipt


def test_owner_select_dry_run_reports_exact_delta_without_writes(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _create_owner(tmp_path, "existing-owner")
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    result = select_existing_owner(
        owner_ref=".agentic-workspace/planning/execplans/existing-owner.plan.json", target=tmp_path, dry_run=True
    )

    assert result.operation_receipt["outcome"] == "dry-run"
    assert result.operation_receipt["changed_fields"] == ["local.current_work.selected_owner"]
    after = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_owner_select_shared_requires_reason_and_preserves_unrelated_state(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    selected_path = _create_owner(tmp_path, "selected-owner")
    active_path = _create_owner(tmp_path, "active-owner", activate=True)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_before = tomllib.loads(state_path.read_text(encoding="utf-8"))
    protected_before = copy.deepcopy(state_before.get("roadmap", {}))

    refused = select_existing_owner("selected-owner", target=tmp_path, mode="shared")
    assert refused.reason_code == "shared-selection-reason-required"
    assert tomllib.loads(state_path.read_text(encoding="utf-8")) == state_before

    result = select_existing_owner(
        "selected-owner",
        target=tmp_path,
        mode="shared",
        reason="shared CI continuation owner",
        expected_planning_revision=planning_revision(tmp_path)["revision_id"],
    )
    state_after = tomllib.loads(state_path.read_text(encoding="utf-8"))
    assert state_after["todo"]["active_items"][0]["id"] == "selected-owner"
    assert any(item["id"] == "active-owner" for item in state_after["todo"]["queued_items"])
    assert state_after.get("roadmap", {}) == protected_before
    assert selected_path.exists() and active_path.exists()
    assert result.operation_receipt["changed_fields"] == ["todo.active_items", "todo.queued_items"]
    assert set(result.operation_receipt["preserved_invariants"]) >= {"owner body", "roadmap", "decompositions"}


@pytest.mark.parametrize(
    ("owner", "expected_reason"),
    [("missing-owner", "owner-not-found"), ("duplicate-owner", "owner-ambiguous")],
)
def test_owner_select_absent_and_ambiguous_are_bounded(tmp_path: Path, owner: str, expected_reason: str) -> None:
    install_bootstrap(target=tmp_path)
    if owner == "duplicate-owner":
        first = _create_owner(tmp_path, "first")
        second = _create_owner(tmp_path, "second")
        for path in (first, second):
            record = json.loads(path.read_text(encoding="utf-8"))
            record["id"] = "duplicate-owner"
            path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    result = select_existing_owner(owner, target=tmp_path)
    assert result.reason_code == expected_reason
    assert len(result.actions) == 1
    assert result.recovery_command.endswith("--dry-run --format json")


def test_owner_select_rejects_closed_invalid_stale_and_lane_conflict(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    owner_path = _create_owner(tmp_path, "existing-owner")
    original = json.loads(owner_path.read_text(encoding="utf-8"))

    closed = copy.deepcopy(original)
    closed["lifecycle"] = "closed"
    owner_path.write_text(json.dumps(closed, indent=2) + "\n", encoding="utf-8")
    assert select_existing_owner("existing-owner", target=tmp_path).reason_code == "owner-not-selectable"

    invalid = copy.deepcopy(original)
    invalid.pop("title")
    owner_path.write_text(json.dumps(invalid, indent=2) + "\n", encoding="utf-8")
    assert select_existing_owner("existing-owner", target=tmp_path).reason_code == "owner-not-selectable"

    owner_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")
    stale = select_existing_owner("existing-owner", target=tmp_path, expected_planning_revision="stale")
    assert stale.reason_code == "planning-revision-mismatch"

    create_lane_record(lane_id="parent-lane", title="Parent Lane", target=tmp_path)
    linked = json.loads(owner_path.read_text(encoding="utf-8"))
    linked["parent"] = {"owner_id": "parent-lane", "contribution": "test", "closure_boundary": "slice"}
    owner_path.write_text(json.dumps(linked, indent=2) + "\n", encoding="utf-8")
    assert select_existing_owner("existing-owner", target=tmp_path).reason_code == "owner-not-selectable"


def test_owner_select_rolls_back_shared_state_when_receipt_validation_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_bootstrap(target=tmp_path)
    _create_owner(tmp_path, "selected-owner")
    _create_owner(tmp_path, "active-owner", activate=True)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    before = state_path.read_bytes()

    from repo_planning_bootstrap import installer

    original_findings = installer._json_schema_findings
    receipt_checks = 0

    def fail_second_receipt_check(*, payload: dict, schema_path: Path) -> list[str]:
        nonlocal receipt_checks
        if schema_path == OWNER_SELECTION_RECEIPT_SCHEMA_PATH:
            receipt_checks += 1
            if receipt_checks == 2:
                return ["injected receipt failure"]
        return original_findings(payload=payload, schema_path=schema_path)

    monkeypatch.setattr(installer, "_json_schema_findings", fail_second_receipt_check)
    result = select_existing_owner("selected-owner", target=tmp_path, mode="shared", reason="rollback proof")
    assert result.reason_code == "owner-selection-rolled-back"
    assert state_path.read_bytes() == before
    assert not (tmp_path / ".agentic-workspace/local/planning/owner-selection-receipt.json").exists()


def test_owner_select_stale_current_work_revision_and_unregistered_guidance(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _create_owner(tmp_path, "existing-owner")
    stale = select_existing_owner("existing-owner", target=tmp_path, expected_current_work_revision="stale")
    assert stale.reason_code == "stale-current-work-revision"
    assert stale.recovery_command.endswith("--dry-run --format json")

    warning = next(
        item
        for item in planning_summary(target=tmp_path, profile="compact")["planning_surface_health"]["warnings"]
        if item["warning_class"] == "execplan_unregistered"
    )
    assert "owner-select" in warning["suggested_fix"]
    assert "new-plan" not in warning["suggested_fix"]


def test_owner_selection_state_patch_is_reusable_by_reconciliation_without_writing(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    selected_path = _create_owner(tmp_path, "selected-owner")
    _create_owner(tmp_path, "active-owner", activate=True)
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    before = state_path.read_bytes()
    state = tomllib.loads(before.decode("utf-8"))
    selected_record = json.loads(selected_path.read_text(encoding="utf-8"))

    from repo_planning_bootstrap.installer import _owner_selection_state_patch

    proposal, changed_fields = _owner_selection_state_patch(tmp_path, state, owner_path=selected_path, owner_record=selected_record)
    proposal.setdefault("reconciliation", {})["proposal_id"] = "issue-2281-fixture"

    assert proposal["todo"]["active_items"][0]["id"] == "selected-owner"
    assert changed_fields == ["todo.active_items", "todo.queued_items"]
    assert proposal["reconciliation"]["proposal_id"] == "issue-2281-fixture"
    assert state_path.read_bytes() == before
