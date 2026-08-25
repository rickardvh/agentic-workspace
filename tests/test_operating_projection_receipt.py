from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic_workspace.operating_projection_receipt import build_operating_projection_receipt


def _owner_inputs(*, proof_status: str = "accepted", broad: bool = False) -> dict[str, Any]:
    proof_command = "pytest tests/test_widget.py -q"
    reconciliation = {
        "status": proof_status,
        "selected_proof_identity": {"id": "selected-proof:test"},
        "commands": [
            {
                "command": proof_command,
                "status": proof_status,
                "minimum_rerun_command": proof_command,
            }
        ],
    }
    return {
        "route": {"kind": "agentic-planning/route-decision/v1", "status": "current", "implementation_allowed": True},
        "verification": {"kind": "agentic-workspace/verification-report/v1", "status": "current", "configured": True},
        "proof_selection": {
            "proof_receipt_reconciliation": reconciliation,
            "required_commands": [proof_command],
            "proof_route_strategy_decision": {
                "outcome": "broad-escalated" if broad else "focused",
                "reason_code": "explicit-high-risk-change" if broad else "focused-route-covered",
                "broad_escalation": {"reason": "explicit high-risk change"} if broad else None,
            },
        },
        "closeout_trust": {"kind": "agentic-workspace/closeout-trust/v1", "status": "current", "trust": "high"},
        "runtime_mirror": {"kind": "agentic-workspace/runtime-mirror-consistency/v1", "status": "current"},
    }


def _revisions(*, changed: str = "changed-v1") -> dict[str, str]:
    return {
        "task": "task-v1",
        "selected_owner": "owner-v1",
        "planning": "planning-v1",
        "changed_paths": changed,
        "proof_subject": changed,
        "runtime_compatibility": "runtime-v1",
    }


def _build(tmp_path: Path, *, revisions: dict[str, str] | None = None, head: str = "head-1", **owners: Any) -> dict[str, Any]:
    return build_operating_projection_receipt(
        target_root=tmp_path,
        task_text="repair #2740",
        changed_paths=["src/widget.py"],
        admitted_revisions=revisions or _revisions(),
        stack_context={"branch": "feature", "head": head, "base": "base-1", "status": "current"},
        **owners,
    )


def test_receipt_reuses_constituents_when_only_observed_head_moves(tmp_path: Path) -> None:
    owners = _owner_inputs()
    first = _build(tmp_path, **owners)
    second = _build(tmp_path, head="head-2", **owners)

    assert first["freshness_delta"]["status"] == "invalidated"
    assert second["freshness_delta"]["status"] == "reused"
    assert set(second["freshness_delta"]["reused_constituents"]) == {
        "route",
        "verification",
        "selected_proof",
        "closeout_trust",
        "runtime_mirror",
    }
    for constituent in second["freshness_delta"]["constituents"].values():
        assert constituent["context_delta"] == [{"field": "head", "reason": "head-changed", "invalidates_constituent": False}]


def test_changed_path_delta_invalidates_only_dependent_constituents(tmp_path: Path) -> None:
    owners = _owner_inputs()
    _build(tmp_path, **owners)
    changed = _build(tmp_path, revisions=_revisions(changed="changed-v2"), **owners)

    assert changed["freshness_delta"]["status"] == "partially-invalidated"
    assert set(changed["freshness_delta"]["invalidated_constituents"]) == {
        "route",
        "verification",
        "selected_proof",
        "closeout_trust",
    }
    assert changed["freshness_delta"]["reused_constituents"] == ["runtime_mirror"]
    assert changed["freshness_delta"]["broad_rebuild_required"] is False


def test_stale_proof_is_never_current_and_routes_a_focused_rerun(tmp_path: Path) -> None:
    receipt = _build(tmp_path, **_owner_inputs(proof_status="subject-stale"))
    proof = receipt["owner_results"]["selected_proof"]

    assert receipt["status"] == "attention"
    assert proof["current"] is False
    assert proof["freshness"] == "stale"
    assert receipt["rerun_guidance"]["focused_commands"] == ["pytest tests/test_widget.py -q"]
    assert receipt["rerun_guidance"]["broad_required"] is False


def test_broad_rerun_requires_existing_explicit_escalation(tmp_path: Path) -> None:
    receipt = _build(tmp_path, **_owner_inputs(proof_status="not-recorded", broad=True))

    assert receipt["rerun_guidance"]["broad_required"] is True
    assert receipt["rerun_guidance"]["broad_escalation"] == {"reason": "explicit high-risk change"}
    assert receipt["reuse_index"]["stores_proof"] is False
