"""Prepare a copied harness fixture for configured-orchestration scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_workspace.workspace_runtime_core import (
    _assignment_identity_payload,
    _execution_posture_payload,
    _load_workspace_config,
)


def configure(target: Path, *, task: str) -> None:
    projection_cache = target / ".agentic-workspace" / "local" / "projection-cache"
    if projection_cache.is_dir():
        for cached_projection in projection_cache.glob("*.json"):
            cached_projection.unlink()
    config_path = target / ".agentic-workspace" / "config.local.toml"
    text = config_path.read_text(encoding="utf-8")
    marker = '[delegation]\nmode = "auto"'
    replacement = "\n".join(
        [
            "[delegation]",
            'mode = "auto"',
            'execution_role = "orchestrator"',
            'assignment_policy = "required-best-fit"',
            'current_target = "strong_planner"',
            'manual_transport_policy = "allowed"',
        ]
    )
    if marker not in text:
        raise SystemExit(f"expected configured fixture delegation block in {config_path}")
    config_path.write_text(text.replace(marker, replacement, 1), encoding="utf-8")

    plan_ref = ".agentic-workspace/planning/execplans/configured-orchestration-fixture.plan.json"
    plan = {
        "kind": "planning-execplan/v1",
        "id": "configured-orchestration-fixture",
        "title": "Configured orchestration fixture",
        "owner_level": "task",
        "lifecycle": "live",
        "phase": "implementation",
        "revision": 1,
        "intent": {
            "outcome": task,
            "non_goals": ["Do not let the current orchestrator implement a non-local selected worker slice."],
        },
        "scope": {
            "owned": ["README.md"],
            "effects": ["Exercise the ordinary configured-assignment action."],
        },
        "relationships": {
            "selection": {"state": "selected", "owner": "configured-orchestration-fixture"},
            "proof_posture": {"state": "pending", "refs": []},
            "external_posture": {"state": "unobserved", "refs": []},
            "delegation": {"state": "recorded", "route": "delegate-implementation"},
        },
        "references": [],
        "next_action": "Follow the canonical assignment action projected by ordinary startup.",
        "blockers": ["None."],
        "proof": {
            "claims": ["The projected assignment action is followed without local retention."],
            "requirements": ["Require a structured assignment operation receipt."],
            "refs": [],
        },
        "continuation": {"owner": "fixture orchestrator", "residual_intent": "Re-resolve after the assignment receipt."},
    }
    plan_path = target / plan_ref
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    state_path = target / ".agentic-workspace" / "planning" / "state.toml"
    state_path.write_text(
        "\n".join(
            [
                'kind = "agentic-planning-state"',
                'schema_version = "planning-state/v1"',
                "",
                "[todo]",
                "active_items = [",
                '  { id = "configured-orchestration-fixture", title = "Configured orchestration fixture", surface = "'
                + plan_ref
                + '", owner_role = "implementation", review_role = "validation", handoff_ready = true, '
                'next_action = "Follow the canonical assignment action projected by ordinary startup.", '
                'done_when = "The assignment operation receipt is present.", proof = "Structured assignment receipt.", '
                'status = "active", maturity = "active" },',
                "]",
                "queued_items = []",
                "",
                "[roadmap]",
                "lanes = []",
                "candidates = []",
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = _load_workspace_config(target_root=target)
    posture = _execution_posture_payload(config=config, changed_paths=["README.md"], task_text=task, target_root=target)
    assignment_gate = dict(posture["assignment_gate"])
    assignment_gate.update(
        {
            "plan_ref": plan_ref,
            "plan_revision": "fixture-plan-rev-1",
            "slice_id": "configured-orchestration-fixture",
            "slice_revision": "fixture-slice-rev-1",
            "role": "implementer",
            "allowed_effects": ["repo-write"],
            "allowed_paths": ["README.md"],
            "proof_obligation": {"id": "proof:configured-orchestration", "revision": "proof-rev-1"},
            "stop_conditions": ["scope-expanded", "assignment-revision-changed"],
            "mutation_baseline": "git:fixture-head",
        }
    )
    assignment_policy = posture["assignment_policy"]
    delegation_decision = dict(posture["delegation_decision"])
    delegation_next_step = dict(delegation_decision.get("delegation_next_step") or {})
    delegation_next_step.update(
        {
            "handoff_run_id": "configured-orchestration-run-1",
            "role": "implementer",
            "return_schema": "delegated-return/v1",
        }
    )
    delegation_decision["delegation_next_step"] = delegation_next_step
    identity = _assignment_identity_payload(
        assignment_gate=assignment_gate,
        assignment_policy=assignment_policy,
        delegation_decision=delegation_decision,
    )
    assignment_dir = target / ".agentic-workspace" / "planning" / "assignments"
    assignment_dir.mkdir(parents=True, exist_ok=True)
    proof_ref = ".agentic-workspace/proof/receipts/configured-orchestration.json"
    proof_path = target / proof_ref
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/assignment-structural-proof-receipt/v1",
                "result": "passed",
                "verified_by": "aw",
                "assignment_id": "configured-orchestration-assignment",
                "assignment_decision_revision": assignment_gate["assignment_decision_revision"],
                "assignment_revision": identity["revision"],
                "mutation_baseline": assignment_gate["mutation_baseline"],
                "claim_boundary": "assignment-identity-and-routing-only; task implementation and completion remain unproved",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    assignment = {
        "kind": "agentic-workspace/planning-assignment/v1",
        "assignment_id": "configured-orchestration-assignment",
        "current_revision": identity["revision"],
        "status": "current",
        "target_name": assignment_gate.get("selected_target"),
        "assignment_gate": assignment_gate,
        "assignment_policy": assignment_policy,
        "delegation_decision": delegation_decision,
        "structural_proof_receipt_ref": proof_ref,
        "current_attempt": {
            "run_id": "configured-orchestration-run-1",
            "owner": assignment_gate.get("selected_target"),
            "status": "selected",
        },
        "accepted_result_refs": [],
    }
    (assignment_dir / "configured-orchestration-assignment.assignment.json").write_text(
        json.dumps(assignment, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    configure(args.target.resolve(), task=args.task)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
