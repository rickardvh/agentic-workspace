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
        "proof_evidence": "proof-receipts-v1",
        "closeout_evidence": "closeout-v1",
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


def _counted_owner_inputs(counters: dict[str, int], *, proof_status: str = "accepted") -> dict[str, Any]:
    owners = _owner_inputs(proof_status=proof_status)

    def source(name: str) -> Any:
        def build() -> dict[str, Any]:
            counters[name] = counters.get(name, 0) + 1
            return owners[name]

        return build

    return {name: source(name) for name in owners}


def test_unchanged_replay_reuses_admitted_owner_results_without_reconstruction(tmp_path: Path) -> None:
    counters: dict[str, int] = {}
    first = _build(tmp_path, **_counted_owner_inputs(counters))
    second = _build(tmp_path, **_counted_owner_inputs(counters))
    restacked = _build(tmp_path, head="head-2", **_counted_owner_inputs(counters))

    assert first["construction_profile"]["owner_result_construction_count"] == 5
    assert first["construction_profile"]["owner_result_reuse_count"] == 0
    assert second["construction_profile"] == {
        "cache_reads": 1,
        "semantic_evidence_reads": 3,
        "owner_result_construction_count": 0,
        "owner_result_reuse_count": 5,
        "constructed_constituents": [],
        "reused_constituents": ["route", "verification", "selected_proof", "closeout_trust", "runtime_mirror"],
        "duplicate_reconstruction_eliminated": True,
        "rule": "Counters measure deterministic owner-builder invocations; warm unchanged calls read one derived cache and invoke no owner builders.",
    }
    assert restacked["construction_profile"]["owner_result_construction_count"] == 0
    assert counters == {name: 1 for name in _owner_inputs()}
    assert second["owner_results"] == first["owner_results"] == restacked["owner_results"]


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


def test_review_fix_delta_rebuilds_only_affected_results_with_focused_guidance(tmp_path: Path) -> None:
    _build(tmp_path, **_owner_inputs())
    counters: dict[str, int] = {}
    changed = _build(
        tmp_path,
        revisions=_revisions(changed="changed-v2"),
        **_counted_owner_inputs(counters, proof_status="subject-stale"),
    )

    assert changed["construction_profile"]["constructed_constituents"] == [
        "route",
        "verification",
        "selected_proof",
        "closeout_trust",
    ]
    assert changed["construction_profile"]["reused_constituents"] == ["runtime_mirror"]
    assert counters == {"route": 1, "verification": 1, "proof_selection": 1, "closeout_trust": 1}
    assert changed["rerun_guidance"]["focused_commands"] == ["pytest tests/test_widget.py -q"]
    assert changed["rerun_guidance"]["broad_required"] is False


def test_canonical_proof_receipt_delta_invalidates_only_proof_consumers(tmp_path: Path) -> None:
    _build(tmp_path, **_owner_inputs())
    counters: dict[str, int] = {}
    revisions = _revisions()
    revisions["proof_evidence"] = "proof-receipts-v2"
    changed = _build(tmp_path, revisions=revisions, **_counted_owner_inputs(counters))

    assert changed["construction_profile"]["constructed_constituents"] == ["selected_proof", "closeout_trust"]
    assert counters == {"proof_selection": 1, "closeout_trust": 1}


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


def test_missing_semantic_identity_is_conservative_and_never_reused(tmp_path: Path) -> None:
    _build(tmp_path, **_owner_inputs())
    counters: dict[str, int] = {}
    revisions = _revisions()
    revisions["planning"] = "unavailable"
    receipt = _build(tmp_path, revisions=revisions, **_counted_owner_inputs(counters))

    assert receipt["status"] == "attention"
    assert set(receipt["freshness_delta"]["unknown_constituents"]) == {"route", "closeout_trust"}
    assert set(receipt["rerun_guidance"]["identity_attention_constituents"]) == {"route", "closeout_trust"}
    assert counters == {"route": 1, "closeout_trust": 1}
    assert receipt["rerun_guidance"]["broad_required"] is False
