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
    assert rows["worker:cli"]["configuration"]["result_classes"] == ["read-only"]
    assert rows["worker:manual"]["eligible"] is False
    assert "execution-return-unconstructible" in rows["worker:manual"]["reasons"]
    manual = offered["manual_targets"][0]
    assert manual["source_policy_eligible"] is True
    assert manual["handoff_constructible"] is False
    assert manual["automatic_invocation"] is False
    assert manual["gap"] == "native-manual-input-completeness-unresolved"
    assert manual["target_best_fit"] == "unresolved-not-rejected"
    assert all(r["configuration"]["proof_classes"] == [] and r["configuration"]["independent_context"] is False for r in rows.values())
    request = next(r for r in offered["requests"] if r[-1]["arguments"]["candidate"] == "worker:cli")
    judgment["arguments"]["required_result_classes"] = ["unapplied-patch"]
    mutation = call({**context, "request": judgment})["task_requirements"]["execution_configurations"]
    mutation_rows = {r["configuration"]["id"]: r for r in mutation["configurations"]["candidates"]}
    assert mutation_rows["local:internal"]["eligible"] is True
    assert mutation_rows["worker:cli"]["eligible"] is False
    assert "result-class-unavailable" in mutation_rows["worker:cli"]["reasons"]
    assert not any(r[-1]["arguments"]["candidate"] == "worker:cli" for r in mutation["requests"])
    selected = call({**context, "request": request})
    assert selected["task_requirements"]["execution_configurations"]["configurations"]["selected"]["id"] == "worker:cli"
    assert selected["decision_packet"].get("primary_action") is None
    assert any("effect:implementation" in row["affects"] for row in selected["decision_packet"]["blockers"])
    assert not (tmp_path / "marker.txt").exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()
    with pytest.raises(AssertionError, match="stale|changed"):
        call({**context, "task": "A different requested outcome", "request": request})
    before_stat = executable.stat()
    original = executable.read_bytes()
    replacement = original.replace(b"echo", b"ECHO", 1)
    assert replacement != original and len(replacement) == len(original)
    executable.write_bytes(replacement)
    os.utime(executable, ns=(before_stat.st_atime_ns, before_stat.st_mtime_ns))
    assert executable.stat().st_mtime_ns == before_stat.st_mtime_ns

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
    assert rows["worker:manual"]["eligible"] is False
    assert "execution-return-unconstructible" in rows["worker:manual"]["reasons"]
    source.write_text(
        source.read_text()
        .replace('transport_authority="automatic"', 'manual_transport_policy="disabled"')
        .replace("safe_to_auto_run_commands=true", "safe_to_auto_run_commands=false")
    )
    rows = {r["configuration"]["id"]: r for r in preview()["configurations"]["candidates"]}
    assert "worker:manual" not in rows
    assert "independent-safety-ceiling" in rows["worker:cli"]["reasons"]
    former = tmp_path / ".agentic-workspace/config.toml"
    former.write_text('schema_version=1\n[delegation]\nassignment_policy="required-best-fit"\n')
    before = former.read_bytes()
    preview()
    observed = consume(surface, shared_core_binary, native_cli, context)
    assert any(
        row["field"] == "delegation.assignment_policy" and row["source"] == ".agentic-workspace/config.toml"
        for row in observed["configuration"]["residuals"]
    )
    assert any("effect:implementation" in row["affects"] for row in observed["decision_packet"]["blockers"])
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

    # An executable is insufficient when the native return path is unsupported.
    for declaration in ('kind="api"', 'kind="process",output_mode="json-file"'):
        source.write_text(before.decode().replace('kind="process"', declaration), newline="")
        current = consume(surface, shared_core_binary, native_cli, context)
        request = current["task_requirements"]["requests"][0]
        request["arguments"]["required_result_classes"] = ["read-only"]
        current = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
        rows = current["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
        worker = next(r for r in rows if r["configuration"]["target"] == "worker" and r["configuration"]["transport"] != "manual")
        assert worker["eligible"] is False
        assert "execution-return-unconstructible" in worker["reasons"]
        assert not (tmp_path / "marker.txt").exists()
    source.write_bytes(before)

    with source.open("a") as stream:
        stream.write('[delegation_targets.invalid]\nstrength="weak"\ntransports=[{kind="process",command=["ignored"],invented=true}]\n')
    invalid_bytes = source.read_bytes()
    invalid = consume(surface, shared_core_binary, native_cli, context)
    assert invalid["task_requirements"]["requests"] == []
    assert any(row["code"].startswith("invalid-config:") for row in invalid["decision_packet"]["blockers"])
    assert source.read_bytes() == invalid_bytes


def test_oversized_executable_is_unavailable_without_reading_or_running(tmp_path, shared_core_binary, native_cli):
    _, executable, context = fixture(tmp_path)
    with executable.open("r+b") as stream:
        stream.truncate(134_217_729)
    first = consume("json", shared_core_binary, native_cli, context)
    request = first["task_requirements"]["requests"][0]
    request["arguments"]["required_result_classes"] = ["read-only"]
    result = consume("json", shared_core_binary, native_cli, {**context, "request": request})["task_requirements"][
        "execution_configurations"
    ]
    row = next(r for r in result["configurations"]["candidates"] if r["configuration"]["id"] == "worker:cli")
    assert row["configuration"]["constructible"] is False
    assert "execution-return-unconstructible" in row["reasons"]
    assert not (tmp_path / "marker.txt").exists()
