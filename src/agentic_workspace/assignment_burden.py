"""Bounded assignment-owned attempt observations; never target calibration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def assignment_attempt_burden(root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    from agentic_workspace.contracts.python_primitive_support import _assignment_packet_integrity

    run_root = root / ".agentic-workspace/local/assignment-runs"

    def mapping(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def read(path: Path) -> dict[str, Any]:
        try:
            if (
                not run_root.resolve().is_relative_to(root.resolve())
                or not path.resolve().is_relative_to(run_root.resolve())
                or path.is_symlink()
            ):
                return {}
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def binding(item: dict[str, Any]) -> dict[str, Any]:
        return {key: item.get(key) for key in ("assignment_id", "assignment_revision", "run_id", "packet_integrity")}

    def work(item: dict[str, Any]) -> dict[str, Any]:
        identity = mapping(item.get("assignment_identity"))
        return {key: identity.get(key) for key in ("slice_id", "plan_revision", "plan_ref", "human_intent", "allowed_paths")}

    initial_work = work(packet)
    current = packet
    attempts = []
    seen = set()
    stop = "complete"
    for _ in range(20):
        run_id = current.get("run_id")
        if not isinstance(run_id, str) or not run_id or any(not (char.isalnum() or char in "-_") for char in run_id):
            stop = "invalid-run-identity"
            break
        if run_id in seen:
            stop = "cyclic-lineage"
            break
        seen.add(run_id)
        if (
            not current.get("packet_integrity")
            or current["packet_integrity"] != _assignment_packet_integrity(current)
            or current.get("assignment_id") != packet.get("assignment_id")
            or work(current) != initial_work
            or not initial_work.get("slice_id")
            or not initial_work.get("plan_revision")
        ):
            stop = "packet-or-work-binding-unavailable"
            break
        directory = run_root / run_id
        state = read(directory / "state.json")
        if binding(mapping(state.get("assignment"))) != binding(current):
            stop = "attempt-custody-unavailable"
            break
        dispatch = read(directory / "dispatch/receipt.json")
        dispatch_bound = binding(dispatch) == binding(current)
        configuration = mapping(mapping(mapping(current.get("assignment_identity")).get("dispatch_adapter")).get("execution_configuration"))
        execution = mapping(configuration.get("execution"))
        cost = mapping(dispatch.get("context_cost")) if dispatch_bound else {}
        metrics = {
            key: value
            for key, value in cost.items()
            if key
            in {
                "assignment_packet_bytes",
                "rendered_prompt_bytes",
                "effective_input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "elapsed_ms",
                "orientation_command_count",
                "retry_count",
                "repair_loop_count",
            }
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
        }
        repair_ref = state.get("repair_admission_ref")
        repair = read(root / repair_ref) if isinstance(repair_ref, str) else {}
        repair_admitted = repair.get("repair_binding") == binding(current) and repair.get("status") == "repair-requested"
        cleanup = read(directory / "closeout/cleanup.json")
        cleanup_observation = mapping(cleanup.get("transport_cleanup")) if cleanup.get("run_id") == run_id else {}
        attempts.append(
            {
                **binding(current),
                "target": current.get("target"),
                "transport": current.get("transport"),
                "configuration_context": execution.get("comparison_context"),
                "continuity_mode": mapping(execution.get("continuity")).get("mode"),
                "lifecycle_state": state.get("current_state", "unknown"),
                "dispatch_observation": "bound" if dispatch_bound else "unavailable-or-unbound",
                "observed_metrics": metrics,
                "repair_admitted": repair_admitted,
                "cleanup": {key: cleanup_observation[key] for key in ("status", "elapsed_ms") if key in cleanup_observation},
                "causal_attribution": "unassessed",
                "target_quality_evidence_allowed": False,
            }
        )
        replacement = current.get("replacement")
        if not replacement:
            break
        if not isinstance(replacement, dict):
            stop = "invalid-replacement"
            break
        if replacement.get("work") != {"id": initial_work["slice_id"], "revision": initial_work["plan_revision"]}:
            stop = "replacement-work-mismatch"
            break
        previous = replacement.get("previous_run_id")
        if not isinstance(previous, str) or not previous or any(not (char.isalnum() or char in "-_") for char in previous):
            stop = "invalid-predecessor"
            break
        predecessor = read(run_root / previous / "export/packet.json")
        if predecessor.get("run_id") != previous or predecessor.get("assignment_revision") != replacement.get("previous_revision"):
            stop = "predecessor-unavailable-or-mismatched"
            break
        current = predecessor
    else:
        stop = "attempt-bound-reached"
    return {
        "kind": "agentic-workspace/assignment-attempt-burden/v1",
        "owner": "assignment-lifecycle",
        "status": "complete-observation-window" if stop == "complete" else "partial",
        "stop_reason": stop,
        "attempt_limit": 20,
        "observed_attempt_count": len(attempts),
        "admitted_repair_count": sum(item["repair_admitted"] for item in attempts),
        "attempts": attempts,
        "metric_totals": None,
        "claim_boundary": "Sparse owner-bound observations only; missing metrics and attribution remain unknown. No cumulative token sums, task-success inference, or target-ranking update.",
    }
