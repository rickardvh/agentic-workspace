"""Hard provider-neutral guarantees precede optimization and remain sealed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.test_external_operation_clients import (
    _install_metadata_only_codex,
    _prepare_shared_worktree_assignment,
    _run_typescript_assignment,
)

from agentic_workspace import cli
from agentic_workspace.config import WorkspaceUsageError, load_workspace_config
from agentic_workspace.decision import execution_configurations
from agentic_workspace.generated_operations import assignment_export


@pytest.mark.parametrize("value", ["history.non-persisted", [""], [True], ["UPPER"], ["same", "same"], [f"fact.{i}" for i in range(33)]])
def test_guarantee_config_rejects_malformed_constraints(tmp_path: Path, value) -> None:
    root = tmp_path / ".agentic-workspace"
    root.mkdir()
    (root / "config.local.toml").write_text("schema_version = 1\n[delegation]\nrequired_execution_guarantees = " + json.dumps(value) + "\n")
    with pytest.raises(WorkspaceUsageError, match="required_execution_guarantees"):
        load_workspace_config(target_root=tmp_path)


def test_shared_guarantee_gate_is_extensible_and_revision_bound() -> None:
    candidate = {
        "id": "adapter:one",
        "target": "worker",
        "transport": "test",
        "capability_revision": "current",
        "current": True,
        "authorized": True,
        "safe": True,
        "constructible": True,
        "result_classes": [],
        "proof_classes": [],
        "independent_context": True,
        "concurrency_available": True,
        "execution_guarantees": ["history.non-persisted", "other-adapter.boundary"],
        "execution": {"provider_parameters": {"price": 0}},
    }
    context = {
        "work": {"id": "work", "revision": "one"},
        "required_result_classes": [],
        "required_proof_classes": [],
        "independent_context": False,
        "required_execution_guarantees": ["history.non-persisted"],
        "candidates": [candidate],
    }
    current = execution_configurations(context)
    assert current["candidates"][0]["eligible"] is True
    unknown = execution_configurations({**context, "required_execution_guarantees": ["history.never-visible"]})
    assert unknown["candidates"][0]["eligible"] is False
    assert unknown["candidates"][0]["reasons"] == ["required-execution-guarantee-unavailable"]
    assert (
        execution_configurations({**context, "required_execution_guarantees": ["other-adapter.boundary"]})["candidates"][0]["eligible"]
        is True
    )
    stale = execution_configurations(
        {**context, "required_execution_guarantees": [], "selection": {"revision": current["revision"], "candidate": candidate["id"]}}
    )
    assert stale["reason_code"] == "assignment-configuration-choice-stale"
    unknown_facts = execution_configurations(
        {**context, "candidates": [{k: v for k, v in candidate.items() if k != "execution_guarantees"}]}
    )
    assert unknown_facts["candidates"][0]["eligible"] is False
    unsafe = execution_configurations({**context, "candidates": [{**candidate, "safe": False}]})
    assert unsafe["candidates"][0]["eligible"] is False
    assert "independent-safety-ceiling" in unsafe["candidates"][0]["reasons"]


@pytest.mark.parametrize("runtime", ["python", "typescript"])
def test_public_history_requirement_filters_and_seals_parameterized_choice(tmp_path: Path, runtime: str, monkeypatch, capsys) -> None:
    _, invocation, _ = _prepare_shared_worktree_assignment(tmp_path, run_id="unrelated")
    audit = _install_metadata_only_codex(tmp_path, monkeypatch)
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.write_text("""schema_version = 1
[delegation]
assignment_policy = "required-best-fit"
current_target = "orchestrator"
transport_authority = "automatic"
required_execution_guarantees = ["history.non-persisted"]
[safety]
safe_to_auto_run_commands = true
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
provider = "openai"
model_family = "fixture-model"
transports = [{kind="manual"}]
""")
    from repo_planning_bootstrap import installer as planning

    task = "Repair the bounded calculation."
    plan = planning._build_execplan_record_from_todo_item(
        title=task, item_id="feature", status="in-progress", why_now=task, next_action=task, done_when="calculation verified"
    )
    plan_path = tmp_path / ".agentic-workspace/planning/execplans/feature.plan.json"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(json.dumps(plan))
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        '[todo]\nactive_items = [{id="feature", status="in-progress", surface=".agentic-workspace/planning/execplans/feature.plan.json"}]\nqueued_items = []\n'
    )

    def offers():
        assert (
            cli.main(
                [
                    "implement",
                    "--target",
                    str(tmp_path),
                    "--task",
                    task,
                    "--changed",
                    "src/feature.py",
                    "--select",
                    "context.delegation_decision",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        return json.loads(capsys.readouterr().out)["values"]["context.delegation_decision"]["execution_configurations"]

    def export(values):
        return (
            _run_typescript_assignment(tmp_path, "export", values)
            if runtime == "typescript"
            else assignment_export(values, target=tmp_path, invocation=invocation)
        )

    current = offers()
    eligible = [row["configuration"] for row in current["candidates"] if row["eligible"]]
    assert len(eligible) == 1
    chosen = eligible[0]
    assert chosen["execution_guarantees"] == ["history.non-persisted"]
    assert chosen["execution"]["history"]["persistence"] == "ephemeral"
    persisted = [row for row in current["candidates"] if row["configuration"].get("execution_guarantees") == ["history.provider-persisted"]]
    assert persisted and all(not row["eligible"] for row in persisted)
    assert all("required-execution-guarantee-unavailable" in row["reasons"] for row in current["candidates"] if not row["eligible"])
    values = {
        "task": task,
        "changed": ["src/feature.py"],
        "transport": "cli",
        "configuration_revision": current["revision"],
        "configuration_id": chosen["id"],
        "configuration_parameters_json": json.dumps({"reasoning_effort": "low", "timeout_seconds": 90}),
    }
    preview = export({**values, "dry_run": True})
    assert preview["status"] == "selection-preview"
    selected = preview["preview"]["selected_configuration"]
    assert selected["execution_guarantees"] == ["history.non-persisted"]
    exported = export(values)
    assert exported["status"] == "handoff-prepared", exported.get("failures")
    packet = json.loads((tmp_path / next(ref for ref in exported["artifact_refs"] if ref.endswith("packet.json"))).read_text())
    assert packet["assignment_identity"]["dispatch_adapter"]["execution_configuration"] == selected
    source.write_text(source.read_text().replace('"history.non-persisted"', '"history.never-visible"'))
    changed = offers()
    assert changed["revision"] != current["revision"]
    assert not any(row["eligible"] for row in changed["candidates"])
    from agentic_workspace.workspace_runtime_core import _execution_posture_payload

    posture = _execution_posture_payload(
        config=load_workspace_config(target_root=tmp_path), target_root=tmp_path, task_text=task, changed_paths=["src/feature.py"]
    )
    assert posture["implementation_allowed"] is False
    assert posture["assignment_gate"]["reason_code"] == "assignment-configuration-choice-stale"
    assert posture["assignment_gate"]["silent_local_fallback_allowed"] is False

    blocked = export(
        {
            "assignment_id": packet["assignment_id"],
            "assignment_revision": packet["assignment_revision"],
            "run_id": packet["run_id"],
            "target_name": "worker",
            "transport": "cli",
        }
    )
    assert blocked["status"] == "blocked"
    assert any(f["reason"] == "assignment-configuration-source-stale" for f in blocked["failures"])
    assert set(audit.read_text().splitlines()) <= {"version", "initialize", "initialized", "model/list", "config/read"}


def test_persisted_guarantee_requires_provider_confirmation_before_turn(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import native_transport as native

    calls = []

    class Connection:
        def __init__(self, executable):
            self.events = []

        def call(self, method, params):
            calls.append(method)
            assert method != "turn/start"
            return {"thread": {"id": "opaque"}}

        def close(self):
            pass

    monkeypatch.setattr(native, "CodexConnection", Connection)
    snapshot = {
        "revision": "current",
        "expires_at": native.time.time() + 900,
        "executable": "fixture",
        "modes": ["fresh"],
        "ephemeral_modes": ["fresh"],
        "parameters": ["model", "ephemeral"],
        "models": [{"model": "fixture"}],
    }
    selection = {"mode": "fresh", "parameters": {"model": "fixture", "ephemeral": False}, "capability_revision": "current"}
    with pytest.raises(native.ProviderError, match="provider-history-guarantee-unconfirmed"):
        native.execute(tmp_path, snapshot, selection, "unused", {}, timeout=1)
    assert "turn/start" not in calls
