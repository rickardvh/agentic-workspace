"""Existing policy source precedence through independent native consumers."""

from __future__ import annotations

import json

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

BASE = '[delegation_targets.local]\ntransports=[{kind="internal"}]\n'


@pytest.mark.parametrize("external", ["expert", "alternate"])
def test_repository_posture_narrows_before_preferences(tmp_path, shared_core_binary, native_cli, external):
    from agentic_workspace.config import load_workspace_config

    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "work", "semantic_routes": ["custom/design", "custom/edit"]}]}))
    root = tmp_path / ".agentic-workspace"
    root.mkdir()
    shared = root / "config.toml"
    shared.write_text(
        '[execution_posture."custom/design"]\nrequired_execution_guarantees=["reasoning.general"]\npreferred_execution_guarantees=["cost.bounded"]\n[execution_posture."custom/edit"]\npreferred_execution_guarantees=["cost.bounded"]\n'
    )
    (root / "config.local.toml").write_text(
        '[delegation]\ncurrent_target="local"\nassignment_policy="required-best-fit"\n[delegation_targets.local]\nexecution_guarantees=["cost.bounded"]\ntransports=[{kind="internal"}]\n[delegation_targets.expert]\nexecution_guarantees=["reasoning.general"]\ntransports=[{kind="manual"}]\n'.replace(
            "delegation_targets.expert", f"delegation_targets.{external}"
        )
    )

    def resolve(request=None):
        return call("native", shared_core_binary, native_cli, tmp_path, request)

    initial = resolve()
    profiles = load_workspace_config(target_root=tmp_path).local_override.delegation_targets
    assert all(profile.strength == "unknown" for profile in profiles)
    assert next(profile for profile in profiles if profile.name == "local").execution_guarantees == ("cost.bounded",)
    route = next(r for r in initial["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/select/v1")
    route["arguments"].update(posture="selected", routes=["custom/design"])
    selected = resolve(route)
    task = selected["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    result = resolve([route, task])["task_requirements"]
    assert result["result"]["requirements"]["required_execution_guarantees"] == ["reasoning.general"]
    local = next(r for r in result["execution_configurations"]["configurations"]["candidates"] if r["configuration"]["target"] == "local")
    assert not local["eligible"]
    assert "required-execution-guarantee-unavailable" in local["reasons"]
    assert "execution_posture" not in initial["task_requirements"]["result"]
    inputs = result["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"].update(input_refs=[], complete=False, reason="The current task itself is the complete bounded input.")
    inputs = resolve([route, *inputs])["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"]["complete"] = True
    offered = resolve([route, *inputs])["task_requirements"]
    choice = next(r for r in offered["execution_configurations"]["requests"] if r[-1]["arguments"]["candidate"] == external + ":manual")
    assessment = resolve([route, *choice])["task_requirements"]["assignment"]["requests"][0]
    assessment[-1]["arguments"].update(alternative=external + ":manual", reason="The stronger manual target satisfies the hard posture.")
    assigned = resolve(assessment)["task_requirements"]["assignment"]["result"]
    assert assigned["selected"]["target"] == external
    assert assigned["status"] == "assigned-nonlocal-handoff-required"

    shared.write_text(
        shared.read_text().replace(
            '[execution_posture."custom/edit"]\npreferred_execution_guarantees=["cost.bounded"]',
            '[execution_posture."custom/edit"]\npreferred_execution_guarantees=["other"]',
        )
    )
    assert resolve([route, task])["task_requirements"]["result"] == result["result"]
    shared.write_text(
        shared.read_text().replace(
            'required_execution_guarantees=["reasoning.general"]', 'required_execution_guarantees=["reasoning.specialist"]'
        )
    )
    with pytest.raises(AssertionError, match="changed|stale"):
        resolve([route, task])

    route["arguments"]["routes"] = ["custom/edit"]
    task = resolve(route)["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    candidates = resolve([route, task])["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
    assert next(row for row in candidates if row["configuration"]["target"] == "local")["eligible"]
    shared.write_text(
        shared.read_text().replace('[execution_posture."custom/edit"]', '[execution_posture."custom/edit"]\nindependent_context=true')
    )
    task = resolve(route)["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    candidates = resolve([route, task])["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
    assert not any(row["eligible"] for row in candidates)


def call(surface, core, cli, root, request=None):
    context = {"target": str(root), "task": "Inspect current source", "changed": []}
    if request is not None:
        context["request"] = request
    return consume(surface, core, cli, context)


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_declared_shared_local_overlay_is_current_and_missing_never_absent(tmp_path, shared_core_binary, native_cli, surface):
    root = tmp_path / "repo"
    root.mkdir()
    shared = tmp_path / "shared.local.toml"
    shared.write_text(
        BASE
        + '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="automatic"\n[safety]\nsafe_to_auto_run_commands=true\n'
    )
    local = root / ".agentic-workspace/config.local.toml"
    local.parent.mkdir()
    local.write_text('[workspace]\nshared_config_path="../shared.local.toml"\n[safety]\nsafe_to_auto_run_commands=false\n')
    first = call(surface, shared_core_binary, native_cli, root)
    policy = first["configuration"]["assignment_policy"]
    assert policy["binding"] is True and policy["execution_permitted"] is False
    assert first["task_requirements"]["requests"]
    request = first["task_requirements"]["requests"][0]
    request["arguments"]["required_result_classes"] = ["read-only"]
    shared.write_text(shared.read_text().replace('current_target="local"', 'current_target="missing"'))
    with pytest.raises(AssertionError, match="stale|changed"):
        call(surface, shared_core_binary, native_cli, root, request)
    fresh = call(surface, shared_core_binary, native_cli, root)
    assert fresh["configuration"]["assignment_policy"]["enforceable"] is False
    shared.unlink()
    missing = call(surface, shared_core_binary, native_cli, root)
    assert any(b["code"] == "assignment-policy-source-unresolved" for b in missing["decision_packet"]["blockers"])
    assert missing["configuration"]["assignment_policy"] is None
    assert not (root / ".agentic-workspace/local").exists()


def test_manual_owner_consumes_current_transport_authority(tmp_path, monkeypatch):
    from agentic_workspace import native_transport
    from agentic_workspace.assignment_source import current_route_configurations
    from agentic_workspace.config import load_workspace_config

    monkeypatch.setattr(native_transport, "discovered_transports", lambda *args: [])
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text('[delegation]\ntransport_authority="manual"\n[delegation_targets.worker]\ntransports=[{kind="manual"}]\n')
    config = load_workspace_config(target_root=tmp_path)
    profile = config.local_override.delegation_targets[0]
    result = current_route_configurations(
        tmp_path,
        [{"name": profile.name, "transports": list(profile.transports)}],
        config.local_override,
        {"id": "task", "revision": "1"},
        requirements={"required_result_classes": ["read-only"], "required_proof_classes": [], "independent_context": False},
    )
    row = next(row for row in result["candidates"] if row["configuration"]["id"] == "worker:manual")
    assert row["eligible"] is True
