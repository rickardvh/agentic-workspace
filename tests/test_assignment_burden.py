from __future__ import annotations

import json

import pytest

from agentic_workspace.assignment_burden import assignment_attempt_burden
from agentic_workspace.contracts.python_primitive_support import _assignment_packet_integrity


def _attempt(root, run, previous=None, *, target="worker", mode="fresh", tokens=None):
    packet = {
        "assignment_id": "assignment",
        "assignment_revision": run + "-revision",
        "run_id": run,
        "target": target,
        "transport": "cli",
        "assignment_identity": {
            "slice_id": "work",
            "plan_revision": "semantic-revision",
            "plan_ref": "plan",
            "human_intent": "bounded work",
            "allowed_paths": ["a.py"],
            "dispatch_adapter": {
                "execution_configuration": {
                    "execution": {"comparison_context": target + "-config", "continuity": {"mode": mode, "reference": "opaque-id"}}
                }
            },
        },
    }
    if previous:
        packet["replacement"] = {
            "previous_run_id": previous["run_id"],
            "previous_revision": previous["assignment_revision"],
            "work": {"id": "work", "revision": "semantic-revision"},
        }
    packet["packet_integrity"] = _assignment_packet_integrity(packet)
    directory = root / ".agentic-workspace/local/assignment-runs" / run
    (directory / "export").mkdir(parents=True)
    (directory / "dispatch").mkdir()
    (directory / "export/packet.json").write_text(json.dumps(packet))
    (directory / "state.json").write_text(json.dumps({"assignment": packet, "current_state": "returned"}))
    receipt = {key: packet[key] for key in ("assignment_id", "assignment_revision", "run_id", "packet_integrity")}
    receipt["context_cost"] = {"effective_input_tokens": tokens}
    (directory / "dispatch/receipt.json").write_text(json.dumps(receipt))
    return packet, directory


def test_attempt_burden_retains_configuration_and_censored_cost_without_totals(tmp_path):
    first, first_dir = _attempt(tmp_path, "first", target="cheap", tokens=100)
    last, _ = _attempt(tmp_path, "last", first, target="strong", mode="resume", tokens=400)
    state = json.loads((first_dir / "state.json").read_text())
    state["repair_admission_ref"] = (first_dir / "repair.json").relative_to(tmp_path).as_posix()
    (first_dir / "state.json").write_text(json.dumps(state))
    (first_dir / "repair.json").write_text(
        json.dumps(
            {
                "status": "repair-requested",
                "repair_binding": {key: first[key] for key in ("assignment_id", "assignment_revision", "run_id", "packet_integrity")},
            }
        )
    )
    result = assignment_attempt_burden(tmp_path, last)
    assert result["status"] == "complete-observation-window"
    assert result["observed_attempt_count"] == 2
    assert result["admitted_repair_count"] == 1
    assert result["metric_totals"] is None
    assert [item["observed_metrics"] for item in result["attempts"]] == [{"effective_input_tokens": 400}, {"effective_input_tokens": 100}]
    assert [item["configuration_context"] for item in result["attempts"]] == ["strong-config", "cheap-config"]
    assert not any(item["target_quality_evidence_allowed"] for item in result["attempts"])
    assert "opaque-id" not in json.dumps(result)


def test_attempt_burden_unbound_receipt_is_unknown_and_missing_predecessor_is_partial(tmp_path):
    first, first_dir = _attempt(tmp_path, "first", tokens=100)
    last, last_dir = _attempt(tmp_path, "last", first)
    receipt = json.loads((last_dir / "dispatch/receipt.json").read_text())
    receipt["packet_integrity"] = "unrelated"
    (last_dir / "dispatch/receipt.json").write_text(json.dumps(receipt))
    (first_dir / "export/packet.json").write_text("{}")
    result = assignment_attempt_burden(tmp_path, last)
    assert result["status"] == "partial"
    assert result["stop_reason"] == "predecessor-unavailable-or-mismatched"
    assert result["attempts"][0]["observed_metrics"] == {}


def test_attempt_burden_excludes_different_semantics_even_with_valid_seal(tmp_path):
    first, directory = _attempt(tmp_path, "first")
    last, _ = _attempt(tmp_path, "last", first)
    first["assignment_identity"]["plan_revision"] = "other-semantics"
    first["packet_integrity"] = _assignment_packet_integrity(first)
    (directory / "export/packet.json").write_text(json.dumps(first))
    (directory / "state.json").write_text(json.dumps({"assignment": first}))
    result = assignment_attempt_burden(tmp_path, last)
    assert result["status"] == "partial"
    assert result["observed_attempt_count"] == 1
    assert result["stop_reason"] == "packet-or-work-binding-unavailable"


def test_attempt_burden_bounds_history_without_fabricating_omitted_count(tmp_path):
    last = None
    for index in range(22):
        last, _ = _attempt(tmp_path, f"run-{index}", last)
    result = assignment_attempt_burden(tmp_path, last)
    assert result["observed_attempt_count"] == 20
    assert result["stop_reason"] == "attempt-bound-reached"
    assert result["status"] == "partial"


@pytest.mark.parametrize("field", ["assignment_identity", "dispatch_adapter", "execution_configuration", "execution", "replacement"])
def test_attempt_burden_malformed_nested_packet_is_bounded(tmp_path, field):
    packet, directory = _attempt(tmp_path, "run")
    if field in {"assignment_identity", "replacement"}:
        packet[field] = "malformed"
    elif field == "dispatch_adapter":
        packet["assignment_identity"][field] = "malformed"
    elif field == "execution_configuration":
        packet["assignment_identity"]["dispatch_adapter"][field] = "malformed"
    else:
        packet["assignment_identity"]["dispatch_adapter"]["execution_configuration"][field] = "malformed"
    packet["packet_integrity"] = _assignment_packet_integrity(packet)
    (directory / "state.json").write_text(json.dumps({"assignment": packet}))
    result = assignment_attempt_burden(tmp_path, packet)
    if field in {"assignment_identity", "replacement"}:
        assert result["status"] == "partial"
    elif result["attempts"]:
        assert result["attempts"][0]["configuration_context"] is None


def test_attempt_burden_malformed_metric_and_cleanup_remain_unknown(tmp_path):
    packet, directory = _attempt(tmp_path, "run")
    receipt = json.loads((directory / "dispatch/receipt.json").read_text())
    receipt["context_cost"] = "malformed"
    (directory / "dispatch/receipt.json").write_text(json.dumps(receipt))
    (directory / "closeout").mkdir()
    (directory / "closeout/cleanup.json").write_text(json.dumps({"run_id": "run", "transport_cleanup": "malformed"}))
    result = assignment_attempt_burden(tmp_path, packet)
    assert result["attempts"][0]["observed_metrics"] == {}
    assert result["attempts"][0]["cleanup"] == {}
