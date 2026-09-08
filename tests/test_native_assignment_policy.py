"""Existing policy source precedence through independent native consumers."""

from __future__ import annotations

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

BASE = 'schema_version=1\n[delegation_targets.local]\nstrength="weak"\ntransports=[{kind="internal"}]\n'


def call(surface, core, cli, root, request=None):
    context = {"target": str(root), "task": "Inspect current source", "changed": []}
    if request is not None:
        context["request"] = request
    return consume(surface, core, cli, context)


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_legacy_source_and_canonical_alias_precedence_keep_binding(tmp_path, shared_core_binary, native_cli, surface):
    former = tmp_path / "agentic-workspace.local.toml"
    former.write_text(
        BASE
        + '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="automatic"\nmode="off"\nexecution_role="ordinary-executor"\n[safety]\nsafe_to_auto_run_commands=false\n'
    )
    before = former.read_bytes()
    result = call(surface, shared_core_binary, native_cli, tmp_path)
    policy = result["configuration"]["assignment_policy"]
    assert policy["binding"] is True and policy["enforceable"] is True
    assert policy["configured_mode"] == "auto" and policy["effective_mode"] == "suggest"
    assert policy["execution_permitted"] is False
    assert any(b["code"] == "current-binding-assignment-required" for b in result["decision_packet"]["blockers"])
    assert not any(
        r["field"] in ["delegation.mode", "delegation.execution_role", "delegation.assignment_policy"]
        for r in result["configuration"]["residuals"]
    )
    request = result["task_requirements"]["requests"][0]
    request["arguments"]["required_result_classes"] = ["read-only"]
    offered = call(surface, shared_core_binary, native_cli, tmp_path, request)
    assert offered["task_requirements"]["execution_configurations"]["gaps"] == []
    assert former.read_bytes() == before
    current = tmp_path / ".agentic-workspace/config.local.toml"
    current.parent.mkdir()
    current.write_text('schema_version=1\n[delegation]\nassignment_policy="local-preferred"\n')
    fresh = call(surface, shared_core_binary, native_cli, tmp_path)
    assert fresh["configuration"]["assignment_policy"]["binding"] is False
    assert any(
        s["reference"] == "agentic-workspace.local.toml" and s["status"] == "superseded-by-current-local-source"
        for s in fresh["configuration"]["sources"]
    )
    assert former.read_bytes() == before


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
    local.write_text(
        'schema_version=1\n[workspace]\nshared_config_path="../shared.local.toml"\n[safety]\nsafe_to_auto_run_commands=false\n'
    )
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


def test_existing_manual_owner_consumes_current_authority_over_deprecated_alias(tmp_path, monkeypatch):
    from agentic_workspace import native_transport
    from agentic_workspace.assignment_source import current_route_configurations
    from agentic_workspace.config import load_workspace_config

    monkeypatch.setattr(native_transport, "discovered_transports", lambda *args: [])
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        'schema_version=1\n[delegation]\ntransport_authority="manual"\nmanual_transport_policy="disabled"\n[delegation_targets.worker]\nstrength="strong"\ntransports=[{kind="manual"}]\n'
    )
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
