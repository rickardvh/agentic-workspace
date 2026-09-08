"""Native diagnostic capture is bounded, local, and never workflow authority."""

from __future__ import annotations

import gzip
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from tests.test_native_public_cli import native_cli as native_cli


def configured(target: Path, mode="redacted"):
    source = target / ".agentic-workspace/config.local.toml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(f'schema_version = 1\n[session_logging]\nenabled = true\npath_mode = "{mode}"\n', encoding="utf-8")


def call(binary: Path, target: Path, *, enabled=True, task="Inspect current sources", invoke=False, identity="private-session-secret"):
    env = dict(os.environ, AW_SESSION_LOGICAL_IDENTITY=identity)
    env.pop("AW_SESSION_LOGGING_DISABLE", None)
    if not enabled:
        env["AW_SESSION_LOGGING_DISABLE"] = "1"
    operation = "invoke" if invoke else "start"
    body = {"target": str(target), "task": task, "changed": []}
    if invoke:
        body["invocation"] = {}
    return subprocess.run([str(binary)], input=json.dumps({operation: body}), text=True, capture_output=True, env=env, timeout=30)


def events(target: Path):
    return [
        json.loads(line)
        for path in target.glob(".agentic-workspace/local/session-logging/logical-sessions/*/events.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def test_native_logging_default_disable_and_result_noninterference(tmp_path, shared_core_binary):
    first = call(shared_core_binary, tmp_path)
    assert first.returncode == 0
    assert not (tmp_path / ".agentic-workspace").exists()
    configured(tmp_path)
    disabled = call(shared_core_binary, tmp_path, enabled=False)
    assert not (tmp_path / ".agentic-workspace/local").exists()
    enabled = call(shared_core_binary, tmp_path)
    assert not any(row["field"].startswith("session_logging.") for row in json.loads(enabled.stdout)["configuration"]["residuals"])
    assert (enabled.returncode, enabled.stdout, enabled.stderr) == (disabled.returncode, disabled.stdout, disabled.stderr)
    rows = events(tmp_path)
    assert len(rows) == 1
    assert rows[0]["authoritative"] is False
    assert rows[0]["payload"]["entry"]["command"] == "agentic-workspace start"
    before = {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace/local").rglob("*") if p.is_file()}
    call(shared_core_binary, tmp_path, enabled=False, invoke=True)
    assert before == {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace/local").rglob("*") if p.is_file()}


@pytest.mark.parametrize("mode,expected", [("redacted", "<target>"), ("repo-relative", "."), ("absolute", None)])
def test_native_logging_paths_large_input_and_stable_identity(tmp_path, shared_core_binary, mode, expected):
    configured(tmp_path, mode)
    call(shared_core_binary, tmp_path)
    call(shared_core_binary, tmp_path, task="secret-argument-" * 100000, invoke=True)
    rows = events(tmp_path)
    assert len(rows) == 2
    assert [r["sequence"] for r in rows] == [1, 2]
    assert len({r["logical_session_id"] for r in rows}) == 1
    assert rows[1]["payload"]["entry"]["exit_status"] == 2
    assert rows[1]["payload"]["entry"]["request_bytes"] > 1000000
    text = json.dumps(rows)
    assert "secret-argument-" not in text and "private-session-secret" not in text
    assert all(len(json.dumps(r).encode()) < 8192 for r in rows)
    recorded = rows[0]["payload"]["entry"]["target"]
    assert recorded == expected if expected else str(tmp_path) in recorded
    assert rows[0]["payload"]["entry"]["omissions"]


@pytest.mark.parametrize("damage", ["registry", "stream", "lock", "historical", "body", "custody"])
def test_native_logging_preserves_unknown_or_torn_existing_state(tmp_path, shared_core_binary, damage):
    configured(tmp_path)
    call(shared_core_binary, tmp_path)
    local = tmp_path / ".agentic-workspace/local"
    if damage == "registry":
        (local / "session-logging/sessions.json").write_bytes(b'{"unowned":')
    if damage in {"body", "custody"}:
        path = local / "session-logging/sessions.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        if damage == "body":
            value["salt"] = "changed-salt"
        else:
            value["native_registration_custody"]["custody"]["attempt"]["revision"] = "sha256:" + "0" * 64
        path.write_text(json.dumps(value), encoding="utf-8")
    if damage == "historical":
        path = local / "session-logging/sessions.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value.pop("native_registration_custody")
        path.write_text(json.dumps(value), encoding="utf-8")
    if damage == "stream":
        next(local.glob("session-logging/logical-sessions/*/events.jsonl")).write_bytes(b'{"partial":')
    if damage == "lock":
        (local / "session-logging/.sessions.lock").mkdir()
    before = {p: p.read_bytes() for p in local.rglob("*") if p.is_file()}
    result = call(shared_core_binary, tmp_path, identity="private-session-secret")
    assert result.returncode == 0
    assert before == {p: p.read_bytes() for p in local.rglob("*") if p.is_file()}


def test_native_logging_concurrent_append_preserves_valid_sequence(tmp_path, shared_core_binary):
    configured(tmp_path)
    call(shared_core_binary, tmp_path)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: call(shared_core_binary, tmp_path), range(2)))
    assert all(result.returncode == 0 for result in results)
    rows = events(tmp_path)
    assert 2 <= len(rows) <= 3  # Contended diagnostics may be omitted, never corrupt commands.
    assert [r["sequence"] for r in rows] == list(range(1, len(rows) + 1))


def test_native_logging_public_analysis_export_and_native_cli(tmp_path, shared_core_binary, native_cli, monkeypatch, capsys):
    from agentic_workspace import cli as source_cli

    configured(tmp_path)
    assert call(shared_core_binary, tmp_path, identity="prior-registered-session").returncode == 0
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", "private-session-secret")
    monkeypatch.delenv("AW_SESSION_LOGGING_DISABLE", raising=False)
    result = subprocess.run(
        [str(native_cli), "start", "--target", str(tmp_path), "--task", "Inspect", "--format", "json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert len({row["logical_session_id"] for row in events(tmp_path)}) == 2
    monkeypatch.setenv("AW_SESSION_LOGGING_DISABLE", "1")
    assert source_cli.main(["session-log", "--target", str(tmp_path), "analyze", "--origin", "all", "--format", "json"]) == 0
    analysis = json.loads(capsys.readouterr().out)
    assert analysis["status"] != "missing-log", analysis
    assert "agentic-workspace start" in json.dumps(analysis), analysis
    assert source_cli.main(["session-log", "--target", str(tmp_path), "export", "--no-artifacts", "--format", "json"]) == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["status"] == "exported", exported
    path = tmp_path / exported["path"]
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        content = stream.read()
    assert "command.completed" in content
    assert "private-session-secret" not in content
    assert "omissions" in content


@pytest.mark.parametrize(
    "settings,override,enabled,mode",
    [
        ({}, "", False, "absolute"),
        ({"enabled": True, "redact_local_paths": True}, "", True, "redacted"),
        ({"enabled": True, "path_mode": "repo-relative"}, "1", False, "repo-relative"),
        ({"enabled": False}, "0", False, "absolute"),
    ],
)
def test_shared_logging_policy(settings, override, enabled, mode, shared_core_binary):
    from agentic_workspace.decision import session_logging_policy

    result = session_logging_policy({"local": {"schema_version": 1, "session_logging": settings}, "disable_override": override})
    assert result == {"enabled": enabled, "path_mode": mode}


def test_native_logging_disabled_overhead_is_measured_without_residue(tmp_path, shared_core_binary):
    import statistics
    import time

    configured(tmp_path)
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.write_text(source.read_text(encoding="utf-8").replace("enabled = true", "enabled = false"), encoding="utf-8")
    times = {False: [], True: []}
    for _ in range(5):
        for native_check in [False, True]:
            started = time.perf_counter()
            assert call(shared_core_binary, tmp_path, enabled=native_check).returncode == 0
            times[native_check].append(time.perf_counter() - started)
    baseline = statistics.median(times[False])
    configured_disabled = statistics.median(times[True])
    print(
        json.dumps(
            {
                "disabled_override_seconds": baseline,
                "disabled_local_seconds": configured_disabled,
                "observed_delta_seconds": configured_disabled - baseline,
            }
        )
    )
    assert configured_disabled <= baseline + 0.05
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize(
    "source",
    [
        'schema_version = 1\n[session_logging]\nenabled = "true"\n',
        'schema_version = 1\n[session_logging]\nenabled = true\npath_mode = "unknown"\n',
        "malformed = [",
    ],
)
def test_native_logging_invalid_local_source_stays_failure_isolated(tmp_path, shared_core_binary, source):
    configured(tmp_path)
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(source, encoding="utf-8")
    disabled = call(shared_core_binary, tmp_path, enabled=False)
    enabled = call(shared_core_binary, tmp_path)
    assert (enabled.returncode, enabled.stdout, enabled.stderr) == (disabled.returncode, disabled.stdout, disabled.stderr)
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_native_logging_correlation_uses_existing_salted_identity(tmp_path, shared_core_binary, monkeypatch):
    import hashlib

    configured(tmp_path)
    monkeypatch.setenv("AW_SESSION_LOG_PARENT_LOGICAL_IDENTITY", " secret-parent ")
    monkeypatch.setenv("AW_SESSION_LOG_CORRELATION_ID", " secret-correlation ")
    call(shared_core_binary, tmp_path, identity="\x1c private-session-secret \x1f")
    call(shared_core_binary, tmp_path)
    registry = json.loads((tmp_path / ".agentic-workspace/local/session-logging/sessions.json").read_text(encoding="utf-8"))
    rows = events(tmp_path)
    assert len(rows) == 2
    for field, value, prefix in [
        ("parent_logical_session_id", "secret-parent", "logical"),
        ("correlation_id", "secret-correlation", "correlation"),
    ]:
        expected = prefix + "-" + hashlib.sha256((registry["salt"] + "\0" + value).encode()).hexdigest()[:24]
        assert all(row[field] == expected for row in rows)
        assert value not in json.dumps(rows)


def test_native_logging_new_identity_registration_replay_and_legacy_refusal(tmp_path, shared_core_binary, monkeypatch):
    from agentic_workspace.session_logging import _session_registry_lock

    configured(tmp_path)
    assert call(shared_core_binary, tmp_path, identity="first").returncode == 0
    registry_path = tmp_path / ".agentic-workspace/local/session-logging/sessions.json"
    first = json.loads(registry_path.read_text(encoding="utf-8"))
    assert call(shared_core_binary, tmp_path, identity="second").returncode == 0
    current_bytes = registry_path.read_bytes()
    current = json.loads(current_bytes)
    assert len(current["sessions"]) == 2
    assert current["salt"] == first["salt"]
    assert all(current["sessions"][key] == value for key, value in first["sessions"].items())
    assert current["native_registration_custody"] != first["native_registration_custody"]
    assert call(shared_core_binary, tmp_path, identity="second").returncode == 0
    assert registry_path.read_bytes() == current_bytes
    assert len(events(tmp_path)) == 3
    with pytest.raises(RuntimeError, match="current owner"):
        with _session_registry_lock(target_root=tmp_path):
            pytest.fail("legacy write must remain unavailable")
    assert registry_path.read_bytes() == current_bytes


def test_native_logging_concurrent_registration_preserves_existing_identities(tmp_path, shared_core_binary):
    configured(tmp_path)
    assert call(shared_core_binary, tmp_path, identity="incumbent").returncode == 0
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda identity: call(shared_core_binary, tmp_path, identity=identity), ["new-a", "new-b"]))
    assert all(result.returncode == 0 for result in results)
    # Diagnostic contention may omit a capture. A subsequent independent command
    # registers the omitted identity without replaying any task effect.
    for identity in ["new-a", "new-b"]:
        assert call(shared_core_binary, tmp_path, identity=identity).returncode == 0
    registry = json.loads((tmp_path / ".agentic-workspace/local/session-logging/sessions.json").read_text(encoding="utf-8"))
    assert len(registry["sessions"]) == 3
    assert len({row["logical_session_id"] for row in events(tmp_path)}) == 3
