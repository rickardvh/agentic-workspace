from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from repo_planning_bootstrap import installer as planning

from agentic_workspace import workspace_runtime_core as workspace


def test_applicable_intent_source_dedupes_structural_evidence() -> None:
    sources: list[dict[str, object]] = []

    for evidence in (["path:a", "path:a", "owner:b"], ["ignored-second-append"]):
        workspace._append_applicable_intent_source(
            sources=sources,
            source_id="intent-a",
            source_type="system-intent",
            owner_surface="intent.toml",
            authority_class="configured",
            evidence_anchor="intent.toml#principles",
            match_evidence=evidence,
        )

    assert len(sources) == 1
    assert sources[0]["structural_match_evidence"] == ["path:a", "owner:b"]


def test_proof_receipt_input_and_result_boundaries() -> None:
    assert workspace._validated_proof_receipt_inputs(command=" make test ", result=" passed ") == ("make test", "passed")
    with pytest.raises(workspace.WorkspaceUsageError):
        workspace._validated_proof_receipt_inputs(command="", result="passed")

    payload = workspace._proof_receipt_write_result(
        dry_run=False,
        receipt={"id": "receipt-a"},
        producer_receipt_ref="producer-a",
        calibration_admission={"status": "admitted"},
        proof_reuse_cache={"status": "written"},
        review_stack_transition={"status": "skipped"},
        repair_retry_ladder={"status": "available"},
        failure_summary=None,
    )

    assert payload["status"] == "written"
    assert "review_stack_transition" not in payload
    assert payload["repair_retry_ladder"] == {"status": "available"}


def test_planning_summary_work_item_precedence_and_schema_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = {"todo": {"active_items": [{"id": "canonical"}]}}
    monkeypatch.setattr(planning, "_read_state_from_toml", lambda _root: state)
    monkeypatch.setattr(planning, "_state_active_items", lambda _state: [{"id": "canonical"}])
    monkeypatch.setattr(planning, "_state_queued_items", lambda _state: [{"id": "queued"}])
    monkeypatch.setattr(planning, "_state_roadmap_lanes", lambda _state: [])
    monkeypatch.setattr(planning, "_state_roadmap_candidates", lambda _state: [])
    monkeypatch.setattr(planning, "_read_todo_items", lambda _path: pytest.fail("legacy reader ran despite canonical state"))

    items = planning._planning_summary_work_items(
        target_root=tmp_path,
        todo_path=tmp_path / "TODO.md",
        legacy_todo_path=tmp_path / "legacy.md",
        roadmap_path=tmp_path / "ROADMAP.md",
    )

    assert items["active_items"] == [{"id": "canonical"}]
    first = planning._planning_summary_schema()
    first["canonical_docs"].append("mutated")
    assert "mutated" not in planning._planning_summary_schema()["canonical_docs"]


def test_planning_summary_legacy_source_precedes_todo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.md"
    todo = tmp_path / "TODO.md"
    monkeypatch.setattr(planning, "_read_state_from_toml", lambda _root: {})
    monkeypatch.setattr(
        planning,
        "_read_todo_items",
        lambda path: (
            (["legacy"], [SimpleNamespace(fields={"id": "legacy", "status": "active", "surface": "plan"})])
            if path == legacy
            else (["todo"], [SimpleNamespace(fields={"id": "todo", "status": "active", "surface": "plan"})])
        ),
    )
    monkeypatch.setattr(planning, "_roadmap_candidate_lanes", lambda _path: [])
    monkeypatch.setattr(planning, "_roadmap_candidates", lambda _path: [])

    items = planning._planning_summary_work_items(
        target_root=tmp_path,
        todo_path=todo,
        legacy_todo_path=legacy,
        roadmap_path=tmp_path / "ROADMAP.md",
    )

    assert items["active_items"] == [{"id": "legacy", "surface": "plan", "why_now": ""}]


def test_reconciliation_prior_apply_rejects_invalid_and_reuses_receipt(tmp_path: Path) -> None:
    assert planning._reconciliation_prior_apply_result(target_root=tmp_path, apply=True, proposal_id="invalid") == {
        "kind": "agentic-planning/reconciliation-transaction/v1",
        "status": "blocked",
        "reason": "invalid-proposal-id",
    }
    proposal_id = "a" * 20
    receipt_path = tmp_path / planning.PLANNING_RECONCILIATION_RECEIPT_ROOT / f"{proposal_id}.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps({"id": proposal_id}), encoding="utf-8")

    result = planning._reconciliation_prior_apply_result(target_root=tmp_path, apply=True, proposal_id=proposal_id)

    assert result is not None and result["status"] == "already-applied"
    assert result["receipt"] == {"id": proposal_id}


def test_invalid_external_evidence_signal_is_bounded() -> None:
    assert planning._invalid_external_evidence_signals({"status": "present"}) == []
    signals = planning._invalid_external_evidence_signals({"status": "invalid", "path": "evidence.json", "reason": "invalid schema"})
    assert signals == [
        {
            "kind": "external_evidence_invalid",
            "severity": "warning",
            "path": "evidence.json",
            "message": "invalid schema",
            "refs": ["evidence.json"],
        }
    ]


@pytest.mark.parametrize(
    ("patch", "expected"),
    [({"phase": "proof"}, {"phase": "proof"}), ('{"phase":"proof"}', {"phase": "proof"}), ("[]", None), ("bad", None)],
)
def test_targeted_patch_parser(patch, expected) -> None:
    assert planning._parse_targeted_execplan_patch(patch) == expected


def test_integration_record_writer_preserves_owner_proposal_receipt_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    writes: list[tuple[Path, dict[str, object], Path]] = []
    monkeypatch.setattr(
        planning,
        "_write_schema_backed_planning_record",
        lambda *, record_path, record, schema_path: writes.append((record_path, record, schema_path)),
    )
    owner_path = tmp_path / "owner.json"
    proposal_path = tmp_path / "proposal.json"
    receipt_path = tmp_path / "receipt.json"

    planning._write_integration_records(
        updated_owner={"id": "owner"},
        owner_path=owner_path,
        owner_changed_fields=["phase"],
        owner_schema_path=Path("owner.schema.json"),
        proposal_path=proposal_path,
        updated_record={"id": "proposal"},
        receipt_path=receipt_path,
        receipt={"id": "receipt"},
    )

    assert [path for path, _record, _schema in writes] == [owner_path, proposal_path, receipt_path]


def test_pending_integration_finalization_dry_run_has_no_write_effect(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(planning, "_planning_target_authority_revision", lambda *_args, **_kwargs: {"revision_id": "after"})
    monkeypatch.setattr(planning, "_json_schema_findings", lambda **_kwargs: [])
    monkeypatch.setattr(planning, "_apply_planning_writes_atomically", lambda *_args, **_kwargs: pytest.fail("dry run wrote"))
    result = planning.InstallResult(target_root=tmp_path, message="fixture", dry_run=True)
    receipt = {"id": "receipt", "revisions": {}}

    payload = planning._finalize_pending_integration_batch(
        target_root=tmp_path,
        result=result,
        writes=[(tmp_path / "receipt.json", receipt, planning.INTEGRATION_RECEIPT_SCHEMA_PATH)],
        owner_overrides={},
        proposals_applied=["proposal"],
        receipts=[receipt],
        proposal_dir=tmp_path / "proposals",
        current_target_id="before",
        dry_run=True,
    )

    assert payload["status"] == "dry-run"
    assert payload["target_authority_after"] == "after"
