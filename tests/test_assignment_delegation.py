from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentic_workspace import orchestration
from agentic_workspace.builtin_modules import planning_module
from agentic_workspace.operations import StaleInvocationError
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
                    "proof_claims": ["complete"],
                    "allowed_scope": ["**"],
                    "constraints": [],
                    "honors_stops": True,
                    "trust": "maintainer",
                    "human_authority": True,
                    "cost": 10,
                    "transport": {"kind": "local"},
                },
                {
                    "id": "worker",
                    "available": True,
                    "capabilities": ["code-review"],
                    "proof_claims": ["complete"],
                    "allowed_scope": ["**"],
                    "constraints": [],
                    "honors_stops": True,
                    "trust": "maintainer",
                    "human_authority": True,
                    "cost": worker_cost,
                    "transport": {"kind": "host-native", "ready": True, "topology": "shared-worktree"},
                },
                {
                    "id": "cheap-underfit",
                    "available": True,
                    "capabilities": [],
                    "proof_claims": ["complete"],
                    "allowed_scope": ["**"],
                    "constraints": [],
                    "honors_stops": True,
                    "trust": "maintainer",
                    "human_authority": True,
                    "cost": 0,
                    "transport": {"kind": "host-native", "ready": True},
                },
            ],
        },
    )


def _retired_policy(
    root: Path, *, assignment_policy: str = "required-best-fit", transports: str = "[{kind='internal'}]"
) -> bytes:
    content = (
        "# Preserve this retired source exactly.\r\n"
        "[delegation]\r\n"
        f"assignment_policy = '{assignment_policy}'\r\n"
        "transport_authority = 'automatic'\r\n"
        "current_target = 'local-profile'\r\n"
        "human_override_policy = 'explicit-only'\r\n\r\n"
        "[delegation_targets.local-profile]\r\n"
        "strength = 'strong'\r\n"
        "target_id = 'local'\r\n"
        "identity_status = 'active'\r\n"
        "capability_classes = ['reasoning-heavy']\r\n"
        f"transports = {transports}\r\n"
    ).encode()
    path = root / ".agentic-workspace/config.local.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


def test_retired_canonical_delegation_transfers_through_assignment_and_preserves_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    retired = _retired_policy(tmp_path)
    workspace = Workspace(tmp_path, modules=[assignment_module()])
    decision = workspace.start(task="ordinary work")
    action = decision["primary_action"]
    assert action["operation_id"] == "assignment.transfer-retired-policy"
    assert action["authority"] == "assignment-inference"

    result = workspace.invoke(action)
    assert result["status"] == "applied"
    assert result["value"]["disposition"] == "transferred"
    assert (tmp_path / ".agentic-workspace/config.local.toml").read_bytes() == retired
    current_path = tmp_path / ".agentic-workspace/local/delegation.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    assert current["assignment_policy"] == "binding-best-fit"
    assert current["transport_authority"] == "automatic"
    assert current["current_target"] == "local"
    assert current["human_override_policy"] == "explicit-only"
    assert current["override_owner"] == "human"
    receipt = current["retired_source_reconciliation"]
    assert receipt["retired_revision"] == action["arguments"]["retired_revision"]
    assert receipt["disposition"] == "transferred"
    assert current["targets"] == [
        {
            "id": "local",
            "available": True,
            "capabilities": ["reasoning-heavy"],
            "transport": {"kind": "local"},
        }
    ]

    current["choice"] = "local"
    _write(current_path, current)
    before = current_path.read_bytes()
    monkeypatch.setattr(
        orchestration.tomllib,
        "loads",
        lambda *_args, **_kwargs: pytest.fail("reconciled retired TOML was reparsed"),
    )
    represented = Workspace(tmp_path, modules=[assignment_module()]).start(task="ordinary work")
    assert represented["status"] == "terminal"
    assert represented["primary_action"] is None
    assert current_path.read_bytes() == before
    assert (tmp_path / ".agentic-workspace/config.local.toml").read_bytes() == retired


def test_changed_retired_revision_is_reconciled_once_without_duplicate_policy(tmp_path: Path) -> None:
    original = _retired_policy(tmp_path)
    workspace = Workspace(tmp_path, modules=[assignment_module()])
    first = workspace.start(task="ordinary work")["primary_action"]
    workspace.invoke(first)
    current_path = tmp_path / ".agentic-workspace/local/delegation.json"
    before = json.loads(current_path.read_text(encoding="utf-8"))

    retired_path = tmp_path / ".agentic-workspace/config.local.toml"
    retired_path.write_bytes(original + b"# same canonical intent, new retired revision\r\n")
    changed = Workspace(tmp_path, modules=[assignment_module()]).start(task="ordinary work")
    assert changed["primary_action"]["operation_id"] == "assignment.transfer-retired-policy"
    reconciled = Workspace(tmp_path, modules=[assignment_module()]).invoke(changed["primary_action"])
    assert reconciled["status"] == "applied"
    assert reconciled["value"]["disposition"] == "already-represented"

    after = json.loads(current_path.read_text(encoding="utf-8"))
    assert after["targets"] == before["targets"]
    assert (
        after["retired_source_reconciliation"]["retired_revision"]
        != before["retired_source_reconciliation"]["retired_revision"]
    )
    settled = Workspace(tmp_path, modules=[assignment_module()]).start(task="ordinary work")
    assert settled["status"] == "terminal"
    assert settled["primary_action"] is None


def test_retired_delegation_conflict_and_ambiguous_transport_fail_closed(tmp_path: Path) -> None:
    _retired_policy(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/local/delegation.json",
        {
            "kind": "delegation-policy",
            "schema_version": 1,
            "applies": {},
            "assignment_policy": "advisory-best-fit",
            "targets": [],
        },
    )
    conflict = Workspace(tmp_path, modules=[assignment_module()]).start(task="ordinary work")
    assert conflict["status"] == "blocked"
    assert conflict["blockers"][0]["code"] == "retired-delegation-conflict"
    assert "assignment_policy" in conflict["blockers"][0]["message"]

    ambiguous_root = tmp_path / "ambiguous"
    _retired_policy(ambiguous_root, transports="[{kind='internal'}, {kind='manual'}]")
    ambiguous = Workspace(ambiguous_root, modules=[assignment_module()]).start(task="ordinary work")
    assert ambiguous["status"] == "blocked"
    assert ambiguous["blockers"][0]["code"] == "retired-delegation-ambiguous"
    assert not (ambiguous_root / ".agentic-workspace/local/delegation.json").exists()


def test_retired_delegation_completes_partial_current_state_and_rejects_stale_source(tmp_path: Path) -> None:
    _retired_policy(tmp_path)
    current_path = tmp_path / ".agentic-workspace/local/delegation.json"
    _write(
        current_path,
        {
            "kind": "delegation-policy",
            "schema_version": 1,
            "applies": {},
            "current_target": "local",
            "targets": [],
        },
    )
    workspace = Workspace(tmp_path, modules=[assignment_module()])
    action = workspace.start(task="ordinary work")["primary_action"]
    assert action["operation_id"] == "assignment.transfer-retired-policy"
    assert workspace.invoke(action)["status"] == "applied"
    completed = json.loads(current_path.read_text(encoding="utf-8"))
    assert completed["assignment_policy"] == "binding-best-fit"
    assert completed["targets"][0]["id"] == "local"

    stale_root = tmp_path / "stale"
    _retired_policy(stale_root)
    stale_workspace = Workspace(stale_root, modules=[assignment_module()])
    stale_action = stale_workspace.start(task="ordinary work")["primary_action"]
    retired_path = stale_root / ".agentic-workspace/config.local.toml"
    retired_path.write_bytes(retired_path.read_bytes() + b"# changed\n")
    with pytest.raises(StaleInvocationError):
        stale_workspace.invoke(stale_action)
    assert not (stale_root / ".agentic-workspace/local/delegation.json").exists()


def test_deprecated_only_retired_delegation_and_absent_source_have_no_transition_tax(tmp_path: Path) -> None:
    retired = tmp_path / ".agentic-workspace/config.local.toml"
    retired.parent.mkdir(parents=True)
    retired.write_text(
        "[delegation]\nmode='auto'\nexecution_role='orchestrator'\nunderfit_behavior='require-delegation'\n"
        "down_routing_behavior='when-cheaper-safe-target-exists'\n\n"
        "[delegation_targets.legacy]\nstrength='strong'\nexecution_methods=['internal']\n",
        encoding="utf-8",
    )
    deprecated = Workspace(tmp_path, modules=[assignment_module()]).start(task="ordinary work")
    assert deprecated["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace/local/delegation.json").exists()

    clean_root = tmp_path / "clean"
    clean = Workspace(clean_root, modules=[assignment_module()]).start(task="ordinary work")
    assert clean["status"] == "direct"
    assert not (clean_root / ".agentic-workspace").exists()


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
    assert handoff["status"] == "prepared-manual"
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


def test_automatic_process_transport_executes_and_failure_remains_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _policy(tmp_path)
    policy_path = tmp_path / ".agentic-workspace/local/delegation.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    worker = next(target for target in policy["targets"] if target["id"] == "worker")
    worker["transport"] = {
        "kind": "process",
        "ready": True,
        "command": [sys.executable, "-c", "from pathlib import Path; Path('transport-ran').write_text('yes')"],
    }
    _write(policy_path, policy)
    workspace = Workspace(tmp_path, modules=[assignment_module()])
    dispatched = workspace.invoke(workspace.start(task="review implementation")["primary_action"])
    assert dispatched["value"]["status"] == "in-flight"
    assert (tmp_path / "transport-ran").read_text(encoding="utf-8") == "yes"

    policy["targets"][1]["transport"]["command"] = [sys.executable, "-c", "raise SystemExit(3)"]
    policy["targets"][1]["cost"] = 1
    _write(policy_path, policy)
    failed_workspace = Workspace(tmp_path / "failure", modules=[assignment_module()])
    _write(tmp_path / "failure" / policy_path.relative_to(tmp_path), policy)
    monkeypatch.setattr(
        "agentic_workspace.orchestration.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 3, stdout="", stderr="failed"),
    )
    failed = failed_workspace.invoke(failed_workspace.start(task="review implementation")["primary_action"])
    assert failed["value"]["status"] == "failed"
    assert failed["next_decision"]["blockers"][0]["recovery"] == failed["value"]["id"]


def test_unapplied_delta_recovers_partial_apply_once_then_enters_planning_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _policy(tmp_path)
    workspace = Workspace(tmp_path, modules=[assignment_module(), planning_module()])
    workspace.invoke(
        workspace.start(
            intent={
                "planning": {
                    "operation": "set",
                    "item": "review-work",
                    "status": "in-progress",
                    "scope": ["src/*"],
                    "proof_claims": ["complete"],
                }
            }
        )["primary_action"]
    )
    path = tmp_path / "src/app.py"
    second_path = tmp_path / "src/other.py"
    path.parent.mkdir(parents=True)
    path.write_text("before", encoding="utf-8")
    second_path.write_text("other-before", encoding="utf-8")
    dispatch = workspace.start(
        task="review implementation", changed_paths=["src/app.py", "src/other.py"], claims=["complete"]
    )
    attempt = workspace.invoke(dispatch["primary_action"])["value"]
    content = "after"
    returned = workspace.start(
        task="review implementation",
        changed_paths=["src/app.py"],
        claims=["complete"],
        intent={
            "delegation_return": {
                "attempt_id": attempt["id"],
                "assignment_revision": attempt["assignment_revision"],
                "delivery": "unapplied-delta",
                "changed_paths": ["src/app.py", "src/other.py"],
                "artifacts": [
                    {
                        "path": "src/app.py",
                        "before_sha256": "sha256:" + hashlib.sha256(b"before").hexdigest(),
                        "after_sha256": "sha256:" + hashlib.sha256(content.encode()).hexdigest(),
                        "content": content,
                    },
                    {
                        "path": "src/other.py",
                        "before_sha256": "sha256:" + hashlib.sha256(b"other-before").hexdigest(),
                        "after_sha256": "sha256:" + hashlib.sha256(b"other-after").hexdigest(),
                        "content": "other-after",
                    },
                ],
                "result": {"outcome": "complete", "evidence": ["reviewed"]},
            }
        },
    )
    returned_result = workspace.invoke(returned["primary_action"])
    integration = returned_result["next_decision"]["primary_action"]
    assert integration["operation_id"] == "delegation.integrate"
    original_replace = orchestration._replace_artifact
    replacements = 0

    def interrupt_second_artifact(source: Path, destination: Path) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("interrupted artifact integration")
        original_replace(source, destination)

    monkeypatch.setattr(orchestration, "_replace_artifact", interrupt_second_artifact)
    with pytest.raises(OSError, match="interrupted artifact integration"):
        workspace.invoke(integration)
    monkeypatch.setattr(orchestration, "_replace_artifact", original_replace)
    integrated = Workspace(tmp_path, modules=[assignment_module(), planning_module()]).invoke(integration)
    assert path.read_text(encoding="utf-8") == content
    assert second_path.read_text(encoding="utf-8") == "other-after"
    assert integrated["next_decision"]["primary_action"]["operation_id"] == "planning.record-attempt"
    assert workspace.invoke(integration) == integrated
    reconciled = workspace.invoke(integrated["next_decision"]["primary_action"])
    assert reconciled["next_decision"]["decision_request"]["response_operation_id"] == "planning.reconcile"


def test_hard_eligibility_precedes_cost_and_evidence_ranking(tmp_path: Path) -> None:
    _policy(tmp_path)
    policy_path = tmp_path / ".agentic-workspace/local/delegation.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["targets"][0]["available"] = False
    worker = policy["targets"][1]
    worker["proof_claims"] = []
    worker["cost"] = -100
    _write(policy_path, policy)
    planning = Workspace(tmp_path, modules=[planning_module()])
    planning.invoke(
        planning.start(
            intent={
                "planning": {
                    "operation": "set",
                    "item": "review",
                    "status": "in-progress",
                    "scope": ["src/app.py"],
                    "constraints": ["signed"],
                    "stops": ["proof-fails"],
                    "proof_claims": ["complete"],
                }
            }
        )["primary_action"]
    )
    decision = Workspace(tmp_path, modules=[assignment_module()]).start(task="review implementation")
    assert decision["status"] == "blocked"
    candidate = next(
        item for item in decision["context"]["assignment"]["assignment"]["candidates"] if item["id"] == "worker"
    )
    assert "proof-incompatible" in candidate["exclusions"]
    assert "constraint-incompatible" in candidate["exclusions"]


def test_only_current_authoritative_context_evidence_changes_ranking(tmp_path: Path) -> None:
    _policy(tmp_path, worker_cost=20)
    workspace = Workspace(tmp_path, modules=[assignment_module()])
    base = {
        "id": "worker-success",
        "target_id": "worker",
        "source": "review-receipt",
        "authority": "verification",
        "outcome": "success",
        "context_class": "general",
        "currentness": "current",
        "confidence": 90,
        "success_credit": 15,
        "repair_cost": 0,
        "review_cost": 0,
        "context_cost": 0,
        "retry_cost": 0,
    }
    record = workspace.start(
        task="review evidence", intent={"assignment": {"operation": "record-evidence", "record": base}}
    )
    assert workspace.invoke(record["primary_action"])["status"] == "applied"
    selected = workspace.start(task="review implementation")
    assert selected["primary_action"]["arguments"]["target_id"] == "worker"

    stale = {**base, "id": "stale", "currentness": "stale", "success_credit": 100}
    workspace.invoke(
        workspace.start(
            task="review evidence", intent={"assignment": {"operation": "record-evidence", "record": stale}}
        )["primary_action"]
    )
    assert workspace.start(task="review implementation")["primary_action"]["arguments"]["target_id"] == "worker"
    disputed = {
        **base,
        "id": "disputed",
        "disputed": True,
        "supersedes": [base["id"]],
        "success_credit": 100,
    }
    workspace.invoke(
        workspace.start(
            task="review evidence",
            intent={"assignment": {"operation": "record-evidence", "record": disputed}},
        )["primary_action"]
    )
    local = workspace.start(task="review implementation")
    assert local["primary_action"] is None
    assert local["context"]["assignment"]["assignment"]["selected_target"] == "local"
    self_report = {**base, "id": "self", "authority": "worker-self-report"}
    rejected = workspace.invoke(
        workspace.start(
            task="review evidence",
            intent={"assignment": {"operation": "record-evidence", "record": self_report}},
        )["primary_action"]
    )
    assert rejected["status"] == "rejected"
