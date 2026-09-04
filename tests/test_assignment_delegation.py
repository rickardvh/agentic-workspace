from __future__ import annotations

import json
from pathlib import Path

from agentic_workspace.builtin_modules import planning_module
from agentic_workspace.orchestration import assignment_module
from agentic_workspace.workspace import Workspace


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _policy(root: Path, *, assignment_policy: str = "binding-best-fit", worker_cost: int = 2) -> None:
    _write(
        root / ".agentic-workspace/local/delegation.json",
        {
            "kind": "delegation-policy",
            "schema_version": 1,
            "applies": {"task_terms": ["review"]},
            "current_target": "local",
            "assignment_policy": assignment_policy,
            "transport_authority": "automatic",
            "override_owner": "maintainer",
            "required_capabilities": ["code-review"],
            "targets": [
                {
                    "id": "local",
                    "available": True,
                    "capabilities": ["code-review"],
                    "cost": 10,
                    "transport": {"kind": "local"},
                },
                {
                    "id": "worker",
                    "available": True,
                    "capabilities": ["code-review"],
                    "cost": worker_cost,
                    "transport": {"kind": "host-native", "ready": True, "topology": "shared-worktree"},
                },
                {
                    "id": "cheap-underfit",
                    "available": True,
                    "capabilities": [],
                    "cost": 0,
                    "transport": {"kind": "host-native", "ready": True},
                },
            ],
        },
    )


def test_no_keyword_binding_assignment_dispatches_and_shared_return_is_baseline_checked(tmp_path: Path) -> None:
    _policy(tmp_path)
    _write(tmp_path / "src/app.py", {"before": True})
    workspace = Workspace(tmp_path, modules=[assignment_module()])
    decision = workspace.start(task="Review the bounded change", changed_paths=["src/app.py"], claims=["complete"])
    assignment = decision["primary_action"]
    assert assignment["operation_id"] == "delegation.dispatch"
    assert assignment["arguments"]["target_id"] == "worker"
    dispatched = workspace.invoke(assignment)
    handoff = dispatched["value"]
    assert handoff["transport"]["topology"] == "shared-worktree"
    assert dispatched["next_decision"]["blockers"][0]["code"] == "assigned-work-in-flight"

    _write(tmp_path / "src/app.py", {"after": True})
    returned = workspace.start(
        task="Review the bounded change",
        changed_paths=["src/app.py"],
        claims=["complete"],
        intent={
            "delegation_return": {
                "attempt_id": handoff["id"],
                "assignment_revision": handoff["assignment_revision"],
                "delivery": "already-materialized",
                "changed_paths": ["src/app.py"],
                "result": {"outcome": "complete", "evidence": ["reviewed"]},
            }
        },
    )
    result = workspace.invoke(returned["primary_action"])
    assert result["status"] == "applied"
    assert result["next_decision"]["context"]["assignment"]["worker_result"]["outcome"] == "complete"
    assert result["next_decision"]["claim_boundary"]["blocked"] == ["complete"]


def test_assignment_separates_eligibility_ranking_evidence_and_retained_local_control(tmp_path: Path) -> None:
    _policy(tmp_path, assignment_policy="advisory-best-fit")
    workspace = Workspace(tmp_path, modules=[assignment_module()])
    decision = workspace.start(task="review implementation")
    assert decision["status"] == "terminal"
    assert decision["primary_action"] is None

    _policy(tmp_path, worker_cost=10)
    tied = workspace.start(task="review implementation")
    assert tied["status"] == "decision"
    assert {choice["id"] for choice in tied["decision_request"]["choices"]} == {"local", "worker"}
    assert "cheap-underfit" not in {choice["id"] for choice in tied["decision_request"]["choices"]}


def test_unrelated_work_does_not_surface_policy_or_create_state(tmp_path: Path) -> None:
    _policy(tmp_path)
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    decision = Workspace(tmp_path, modules=[assignment_module(), planning_module()]).start(task="edit documentation")
    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert decision["status"] == "direct"
    assert decision["relevant_owners"] == []
    assert before == after
