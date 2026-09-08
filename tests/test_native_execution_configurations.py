"""Actual local source and executable observations, no provider sessions."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def fixture(root: Path):
    (root / "a.txt").write_text("current")
    executable = root / ("worker.cmd" if os.name == "nt" else "worker")
    executable.write_text("echo never-run > marker.txt")
    executable.chmod(0o755)
    source = root / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        'schema_version=1\n[safety]\nsafe_to_auto_run_commands=true\n[delegation]\ntransport_authority="automatic"\ncurrent_target="local"\n[delegation_targets.local]\nstrength="weak"\ntransports=[{kind="internal"}]\n[delegation_targets.worker]\nstrength="strong"\ntransports=[{kind="process",command=['
        + json.dumps(str(executable))
        + "]}]\n"
    )
    return source, executable, {"target": str(root), "task": "Inspect current source", "changed": ["a.txt"]}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_configuration_choice_is_feasibility_not_assignment(tmp_path, shared_core_binary, native_cli, surface):
    source, executable, context = fixture(tmp_path)

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value)

    first = call(context)
    judgment = first["task_requirements"]["requests"][0]
    judgment["arguments"]["required_result_classes"] = ["read-only"]
    offered = call({**context, "request": judgment})["task_requirements"]["execution_configurations"]
    rows = {r["configuration"]["id"]: r for r in offered["configurations"]["candidates"]}
    assert rows["local:internal"]["eligible"] is True
    assert rows["worker:cli"]["eligible"] is True
    assert rows["worker:manual"]["eligible"] is True
    assert all(r["configuration"]["proof_classes"] == [] and r["configuration"]["independent_context"] is False for r in rows.values())
    request = next(r for r in offered["requests"] if r[-1]["arguments"]["candidate"] == "worker:cli")
    selected = call({**context, "request": request})
    assert selected["task_requirements"]["execution_configurations"]["configurations"]["selected"]["id"] == "worker:cli"
    assert selected["decision_packet"].get("primary_action") is None
    assert not (tmp_path / "marker.txt").exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()
    with pytest.raises(AssertionError, match="stale|changed"):
        call({**context, "task": "A different requested outcome", "request": request})
    executable.write_text("echo changed capability, still never run")
    stale = call({**context, "request": request})["task_requirements"]["execution_configurations"]["configurations"]
    assert stale["reason_code"] == "assignment-configuration-choice-stale"
    source.write_text(source.read_text().replace('transport_authority="automatic"', 'transport_authority="manual"'))
    with pytest.raises(AssertionError, match="stale|changed"):
        call({**context, "request": request})


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_missing_capability_safety_manual_and_former_source_preserved(tmp_path, shared_core_binary, native_cli, surface):
    source, executable, context = fixture(tmp_path)
    executable.unlink()

    def preview():
        first = consume(surface, shared_core_binary, native_cli, context)
        request = first["task_requirements"]["requests"][0]
        request["arguments"]["required_result_classes"] = ["read-only"]
        return consume(surface, shared_core_binary, native_cli, {**context, "request": request})["task_requirements"][
            "execution_configurations"
        ]

    rows = {r["configuration"]["id"]: r for r in preview()["configurations"]["candidates"]}
    assert "execution-return-unconstructible" in rows["worker:cli"]["reasons"]
    assert rows["worker:manual"]["eligible"] is True
    source.write_text(
        source.read_text()
        .replace('transport_authority="automatic"', 'transport_authority="automatic"\nmanual_transport_policy="disabled"')
        .replace("safe_to_auto_run_commands=true", "safe_to_auto_run_commands=false")
    )
    rows = {r["configuration"]["id"]: r for r in preview()["configurations"]["candidates"]}
    assert "worker:manual" not in rows
    assert "independent-safety-ceiling" in rows["worker:cli"]["reasons"]
    former = tmp_path / ".agentic-workspace/config.toml"
    former.write_text('schema_version=1\n[delegation]\nassignment_policy="required-best-fit"\n')
    before = former.read_bytes()
    pending = preview()
    assert "former-shared-assignment-source-reconciliation-required" in pending["gaps"]
    assert pending["requests"] == []
    assert former.read_bytes() == before


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_adapter_and_unknown_transport_do_not_become_capabilities(tmp_path, shared_core_binary, native_cli, surface):
    source, _, context = fixture(tmp_path)
    with source.open("a") as stream:
        stream.write(
            '[delegation_targets.native]\nstrength="strong"\ntransports=[{kind="native",adapter="provider-owned",parameters={}}]\n'
        )
    before = source.read_bytes()
    first = consume(surface, shared_core_binary, native_cli, context)
    request = first["task_requirements"]["requests"][0]
    request["arguments"]["required_result_classes"] = ["read-only"]
    result = consume(surface, shared_core_binary, native_cli, {**context, "request": request})["task_requirements"][
        "execution_configurations"
    ]
    assert any(row["gap"] == "native-provider-adapter-observation-unavailable" for row in result["unavailable_adapters"])
    assert source.read_bytes() == before
    assert not (tmp_path / "marker.txt").exists()

    with source.open("a") as stream:
        stream.write('[delegation_targets.invalid]\nstrength="weak"\ntransports=[{kind="process",command=["ignored"],invented=true}]\n')
    invalid_bytes = source.read_bytes()
    invalid = consume(surface, shared_core_binary, native_cli, context)
    assert invalid["task_requirements"]["requests"] == []
    assert any(row["code"].startswith("invalid-config:") for row in invalid["decision_packet"]["blockers"])
    assert source.read_bytes() == invalid_bytes
