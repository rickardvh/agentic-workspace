"""Current Planning judgment outranks hints only within its admitted custody."""

import json
from pathlib import Path

import pytest
from repo_planning_bootstrap import installer as planning

from agentic_workspace import workspace_runtime_core as runtime
from agentic_workspace.config import load_workspace_config


@pytest.mark.parametrize("relation", ["current", "unrelated", "reentry", "stale-reentry"])
def test_assignment_consumes_only_current_owner_task_judgment(tmp_path: Path, monkeypatch, relation: str) -> None:
    root = tmp_path / ".agentic-workspace"
    root.mkdir()
    (root / "config.local.toml").write_text(
        "schema_version = 1\n[delegation_targets.worker]\n"
        'target_id = "host:worker"\ntarget_revision = "1"\nstrength = "weak"\n'
        'location = "external"\ntransports = [{kind="manual"}]\n'
    )
    task = "Check the bounded policy document links."
    record = planning._build_execplan_record_from_todo_item(
        title=task, item_id="links", status="in-progress", why_now=task, next_action=task, done_when="links checked"
    )
    record["capability_posture"] = {
        "execution class": "mechanical-follow-through",
        "recommended strength": "weak",
        "preferred location": "either",
        "delegation friendly": "yes",
        "strong external reasoning": "avoid",
        "why": "Exact link existence inspection is bounded.",
    }
    plan_ref = ".agentic-workspace/planning/execplans/links.plan.json"
    path = tmp_path / plan_ref
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record))
    (root / "planning/state.toml").write_text(
        f'[todo]\nactive_items = [{{id="links", status="in-progress", surface="{plan_ref}"}}]\nqueued_items = []\n'
    )
    captured = {}

    class ResolutionReached(Exception):
        pass

    def capture(*, config, capability_posture):
        captured.update(capability_posture)
        raise ResolutionReached

    monkeypatch.setattr(runtime, "_runtime_resolution_payload", capture)
    identity = None
    if relation.endswith("reentry"):
        binding = runtime._live_assignment_plan_binding(target_root=tmp_path, task_text=task, changed_paths=["docs/policy.md"])
        identity = {
            "task_class": "reasoning-heavy",
            "scope_class": "bounded",
            "slice_id": "links",
            "plan_ref": plan_ref,
            "plan_revision": binding["plan_revision"] if relation == "reentry" else "stale",
        }
    with pytest.raises(ResolutionReached):
        runtime._current_assignment_selection(
            config=load_workspace_config(target_root=tmp_path),
            changed_paths=["docs/policy.md"],
            task_text=task if relation != "unrelated" else "Inspect the separate runtime contract.",
            work_identity=identity,
        )
    assert (
        captured["execution class"]
        == {
            "current": "mechanical-follow-through",
            "unrelated": "boundary-shaping",
            "reentry": "reasoning-heavy",
            "stale-reentry": "reasoning-heavy",
        }[relation]
    )
    assert captured["recommended strength"] == ("strong" if relation in {"unrelated", "stale-reentry"} else "weak")


@pytest.mark.parametrize("language", ["python", "typescript"])
def test_direct_assignment_public_export_ignores_unrelated_owner(tmp_path: Path, language: str, capsys) -> None:
    from tests.test_external_operation_clients import _prepare_shared_worktree_assignment, _run_typescript_assignment

    from agentic_workspace.generated_operations import assignment_export

    _, invocation, _ = _prepare_shared_worktree_assignment(tmp_path, run_id="unrelated")
    (tmp_path / ".agentic-workspace/config.local.toml").write_text("""schema_version = 1
[delegation]
assignment_policy = "required-best-fit"
current_target = "orchestrator"
transport_authority = "manual"
[delegation_targets.orchestrator]
target_id = "host:orchestrator"
target_revision = "1"
strength = "strong"
location = "local"
transports = [{kind="internal"}]
[delegation_targets.worker]
target_id = "host:worker"
target_revision = "1"
strength = "strong"
location = "external"
transports = [{kind="manual"}]
""")
    owner_task = "Review the unrelated release policy."
    plan = planning._build_execplan_record_from_todo_item(
        title=owner_task, item_id="release", status="in-progress", why_now=owner_task, next_action=owner_task, done_when="reviewed"
    )
    plan_ref = ".agentic-workspace/planning/execplans/release.plan.json"
    plan_path = tmp_path / plan_ref
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(json.dumps(plan))
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[todo]\nactive_items = [{{id="release", status="in-progress", surface="{plan_ref}"}}]\nqueued_items = []\n'
    )
    task = "Inspect the bounded feature calculation."
    paths = ["src/feature.py"]
    binding = runtime._live_assignment_plan_binding(target_root=tmp_path, task_text=task, changed_paths=paths)
    assert binding["plan_ref"].startswith("direct-task:")
    assert binding["plan_record"] == {}
    assert runtime._live_assignment_plan_binding(target_root=tmp_path, task_text="", changed_paths=paths)["plan_ref"] == plan_ref

    def export(values):
        return (
            _run_typescript_assignment(tmp_path, "export", values)
            if language == "typescript"
            else assignment_export(values, target=tmp_path, invocation=invocation)
        )

    from agentic_workspace import cli

    assert cli.main(["start", "--target", str(tmp_path), "--task", task, "--format", "json"]) == 0
    startup = json.loads(capsys.readouterr().out)
    action = startup["decision_packet"]["action"]
    assert action["id"] == "resolve-current-task-requirements"
    assert startup["decision_packet"]["effects"]["implementation_allowed"] is False
    assert action["operation"]["operation_id"] == "assignment.export"
    missing = export({"task": task, "changed": paths, "dry_run": True})
    assert missing["status"] == "requirements-required"
    assert not missing["mutation_applied"]
    judgment = missing["preview"]["task_requirements"]["judgment_request"]["arguments"]
    judgment["required_result_classes"] = ["unapplied-patch"]
    encoded_judgment = json.dumps(judgment)
    preview = export({"task": task, "changed": paths, "dry_run": True, "task_judgment_json": encoded_judgment})
    assert preview["preview"]["task_requirements"]["status"] == "resolved", preview
    stale = json.loads(encoded_judgment)
    stale["task_identity"]["revision"] = "stale"
    rejected = export({"task": task, "changed": paths, "dry_run": True, "task_judgment_json": json.dumps(stale)})
    assert rejected["status"] == "requirements-required"
    evaluator = json.loads(encoded_judgment)
    evaluator["role"] = "evaluator"
    rejected = export({"task": task, "changed": paths, "dry_run": True, "task_judgment_json": json.dumps(evaluator)})
    assert rejected["status"] == "requirements-required"
    assert not rejected["mutation_applied"]
    offers = preview["preview"]["execution_configurations"]
    selected = next(row["configuration"] for row in offers["candidates"] if row["eligible"] and row["configuration"]["target"] == "worker")
    args = {
        "task": task,
        "changed": paths,
        "configuration_revision": offers["revision"],
        "task_judgment_json": encoded_judgment,
        "configuration_id": selected["id"],
        "transport": "manual",
    }
    exported = (
        _run_typescript_assignment(tmp_path, "export", args)
        if language == "typescript"
        else assignment_export(args, target=tmp_path, invocation=invocation)
    )
    assert exported["status"] == "handoff-prepared", exported
    packet = json.loads((tmp_path / next(ref for ref in exported["artifact_refs"] if ref.endswith("packet.json"))).read_text())
    assert packet["assignment_identity"]["task_judgment"] == judgment
    assert packet["assignment_identity"]["task_requirements_revision"] == preview["preview"]["task_requirements"]["revision"]
    assert packet["assignment_identity"]["plan_ref"] == binding["plan_ref"]
    assert packet["assignment_identity"]["plan_revision"] == binding["plan_revision"]
    assert (
        runtime._live_assignment_plan_binding(target_root=tmp_path, task_text=task + " Check rounding.", changed_paths=paths)[
            "plan_revision"
        ]
        != binding["plan_revision"]
    )
    assert (
        runtime._live_assignment_plan_binding(target_root=tmp_path, task_text=task, changed_paths=["src/other.py"])["plan_revision"]
        != binding["plan_revision"]
    )
    plan["updated_at"] = "later bookkeeping"
    plan_path.write_text(json.dumps(plan))
    assert (
        runtime._live_assignment_plan_binding(target_root=tmp_path, task_text=task, changed_paths=paths)["plan_revision"]
        == binding["plan_revision"]
    )

    carrier_path = tmp_path / f".agentic-workspace/planning/assignments/{packet['assignment_id']}.assignment.json"
    carrier = json.loads(carrier_path.read_text())
    carrier["assignment_gate"].pop("task_judgment")
    carrier["assignment_gate"].pop("task_requirements_revision")
    carrier_path.write_text(json.dumps(carrier))
    legacy_bytes = carrier_path.read_bytes()
    legacy = runtime._execution_posture_payload(
        config=load_workspace_config(target_root=tmp_path), target_root=tmp_path, task_text=task, changed_paths=paths
    )
    assert legacy["assignment_decision"]["task_requirements"]["status"] == "unresolved"
    assert legacy["implementation_allowed"] is False
    assert carrier_path.read_bytes() == legacy_bytes


def test_planning_semantic_binding_preserves_attempts_and_rejects_ambiguous_custody(tmp_path: Path, monkeypatch) -> None:
    projected = {
        "planning_record": {
            "status": "present",
            "task": {"surface": "planning://bounded"},
            "requested_outcome": "Check the calculation",
            "touched_scope": ["src/feature.py"],
            "proof_expectations": ["Verify the result"],
        },
        "planning_revision": {"active_execplan": "planning://bounded", "active_execplan_hash": "initial"},
    }
    route = {"task_relation": "continues-selected-owner", "owner_posture": "current", "required_transition": "none"}
    monkeypatch.setattr(planning, "planning_summary_query", lambda **_: {"status": "present", "payload": projected})
    monkeypatch.setattr(runtime, "_planning_safety_gate_payload", lambda **_: {"route_decision": route})

    def bind():
        return runtime._live_assignment_plan_binding(target_root=tmp_path, task_text="Check the calculation", changed_paths=[])

    first = bind()
    projected["planning_revision"]["active_execplan_hash"] = "after-return-bookkeeping"
    projected["planning_record"]["proof_report"] = {"status": "integration-pending"}
    projected["planning_record"]["attempt"] = {"number": 2}
    assert bind()["plan_revision"] == first["plan_revision"]
    projected["planning_record"]["proof_expectations"] = ["Independent domain judgment required"]
    assert bind()["plan_revision"] != first["plan_revision"]
    route["task_relation"] = "ambiguous"
    assert bind()["plan_ref"] == ""
    assert bind()["plan_record"] == {}
