"""Native diagnostic capture is bounded, local, and never workflow authority."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from tests.test_native_public_cli import native_cli as native_cli


def configured(target: Path, mode="redacted", detail="full"):
    source = target / ".agentic-workspace/config.local.toml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(f'[session_logging]\nenabled = true\npath_mode = "{mode}"\ndetail = "{detail}"\n', encoding="utf-8")


def call(binary: Path, target: Path, *, enabled=True, task="Inspect current sources", invoke=False, identity="private-session-secret"):
    env = dict(os.environ, AW_SESSION_LOGICAL_IDENTITY=identity)
    env.pop("AW_SESSION_LOGGING_DISABLE", None)
    if not enabled:
        env["AW_SESSION_LOGGING_DISABLE"] = "1"
    operation = "invoke" if invoke else "start"
    body = {"target": str(target), "task": task, "changed": [], "projection": "full"}
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
    active_result = json.loads(enabled.stdout)
    assert active_result.pop("session_capture") == {"status": "capturing", "detail": "full", "authoritative": False}
    assert active_result == json.loads(disabled.stdout)
    assert (enabled.returncode, enabled.stderr) == (disabled.returncode, disabled.stderr)
    rows = events(tmp_path)
    assert len(rows) == 1
    assert rows[0]["authoritative"] is False
    assert rows[0]["payload"]["entry"]["command"] == "agentic-workspace start"
    before = {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace/local").rglob("*") if p.is_file()}
    call(shared_core_binary, tmp_path, enabled=False, invoke=True)
    assert before == {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace/local").rglob("*") if p.is_file()}


def test_logging_effective_local_policy_preserves_privacy_and_source_failure(tmp_path, shared_core_binary):
    configured(tmp_path)
    shared = tmp_path / "shared.local.toml"
    shared.write_text('[session_logging]\nenabled=true\npath_mode="redacted"\n')
    local = tmp_path / ".agentic-workspace/config.local.toml"
    local.write_text('[workspace]\nshared_config_path="shared.local.toml"\n')
    assert json.loads(call(shared_core_binary, tmp_path).stdout)["session_capture"]["status"] == "capturing"
    assert events(tmp_path)[-1]["payload"]["entry"]["target"] == "<target>"
    local.write_text(local.read_text() + '[session_logging]\npath_mode="repo-relative"\n')
    call(shared_core_binary, tmp_path)
    assert events(tmp_path)[-1]["payload"]["entry"]["target"] == "."
    shared.unlink()
    failed = call(shared_core_binary, tmp_path)
    disabled = call(shared_core_binary, tmp_path, enabled=False)
    assert (failed.returncode, failed.stdout, failed.stderr) == (disabled.returncode, disabled.stdout, disabled.stderr)
    assert len(events(tmp_path)) == 2
    source_error = json.loads(failed.stderr)["error"]
    assert failed.returncode == 2 and source_error["code"] == "invalid-source-decision"
    assert "configured shared local source" in source_error["message"] and "missing" in source_error["message"]


@pytest.mark.parametrize("mode,expected", [("redacted", "<target>"), ("repo-relative", "."), ("absolute", None)])
def test_native_logging_paths_large_input_and_stable_identity(tmp_path, shared_core_binary, mode, expected):
    configured(tmp_path, mode)
    call(shared_core_binary, tmp_path)
    call(shared_core_binary, tmp_path, task="secret-argument-" * 100000, invoke=True)
    rows = events(tmp_path)
    assert len(rows) == 2
    assert [r["sequence"] for r in rows] == [1, 2]
    assert len({r["logical_session_id"] for r in rows}) == 1
    assert rows[1]["payload"]["entry"]["exit_status"] == 0
    assert rows[1]["payload"]["entry"]["effect_status"] == "rejected-before-effect"
    assert rows[1]["payload"]["entry"]["continuation_status"] == "reentry-required"
    assert rows[1]["payload"]["entry"]["request_bytes"] > 1000000
    text = json.dumps(rows)
    assert "secret-argument-" not in text and "private-session-secret" not in text
    assert all(len(json.dumps(r).encode()) < 8192 for r in rows)
    recorded = rows[0]["payload"]["entry"]["target"]
    assert recorded == expected if expected else str(tmp_path) in recorded
    assert rows[0]["payload"]["entry"]["omissions"]
    for row in rows:
        entry = row["payload"]["entry"]
        artifact = (tmp_path / entry["artifact"]["path"]).read_bytes()
        assert hashlib.sha256(artifact).hexdigest() == entry["artifact"]["sha256"]
        assert "private-session-secret" not in artifact.decode()
        if mode != "absolute":
            assert str(tmp_path) not in artifact.decode() and tmp_path.as_posix() not in artifact.decode()
    retained = json.loads((tmp_path / rows[1]["payload"]["entry"]["artifact"]["path"]).read_bytes())
    assert "secret-argument-" * 100000 in retained["request"]
    assert rows[1]["payload"]["entry"]["artifact"]["bytes"] > 1000000


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
    assert json.loads(result.stdout)["session_capture"] == {"status": "capture-failed", "authoritative": False}
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


def test_native_capture_remains_readable_by_maintainer_analysis(tmp_path, shared_core_binary, native_cli, monkeypatch):
    from aw_maintainer import session_diagnostics as session_logging

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
    assert json.loads(result.stdout)["session_capture"]["status"] == "capturing"
    # Thin bindings forward the advisory produced by the same native transport.
    from tests.test_native_public_cli import consume

    for surface in ["python", "typescript"]:
        value = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Inspect", "projection": "compact"})
        assert value["session_capture"] == {"status": "capturing", "detail": "full", "authoritative": False}
    assert len({row["logical_session_id"] for row in events(tmp_path)}) == 2
    state = session_logging.load_state_for_argv(["--target", str(tmp_path)])
    local = tmp_path / ".agentic-workspace/local"
    before = {p: p.read_bytes() for p in local.rglob("*") if p.is_file()}
    analysis = session_logging.analyze_session_log(state=state, origin_scope="all")
    assert analysis["status"] != "missing-log", analysis
    assert "agentic-workspace start" in json.dumps(analysis), analysis
    exported = session_logging.export_session_log(state=state, include_artifacts=False)
    assert exported["status"] == "exported", exported
    path = tmp_path / exported["path"]
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        content = stream.read()
    assert "command.completed" in content
    assert "private-session-secret" not in content
    assert "omissions" in content
    assert all(p.read_bytes() == original for p, original in before.items())
    for source, digest in exported["manifest"]["source_hashes"].items():
        assert hashlib.sha256((tmp_path / source).read_bytes()).hexdigest() == digest

    # The maintained entrypoint must behave like the formerly required disabled
    # capture recovery, including tree selection and normalized source records.
    script = Path(__file__).resolve().parents[1] / "src/tooling/maintainer/session_diagnostics.py"
    command = [sys.executable, str(script), "export", "--target", str(tmp_path), "--no-artifacts"]
    ordinary = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert ordinary.returncode == 0, ordinary.stderr
    ordinary_export = json.loads(ordinary.stdout)
    assert ordinary_export["status"] == "exported"
    with gzip.open(tmp_path / ordinary_export["path"], "rt", encoding="utf-8") as stream:
        ordinary_events = [json.loads(line) for line in stream]
    monkeypatch.setenv("AW_SESSION_LOGGING_DISABLE", "1")
    recovery = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert recovery.returncode == 0, recovery.stderr
    recovery_export = json.loads(recovery.stdout)
    with gzip.open(tmp_path / recovery_export["path"], "rt", encoding="utf-8") as stream:
        recovery_events = [json.loads(line) for line in stream]
    assert ordinary_events[1:] == recovery_events[1:]
    for field in ("source_hashes", "source_session_ids", "session_scope", "evidence_profile"):
        assert ordinary_export["manifest"][field] == recovery_export["manifest"][field]
    assert all(p.read_bytes() == original for p, original in before.items())

    monkeypatch.delenv("AW_SESSION_LOGGING_DISABLE")
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", "unknown-session")
    missing_before = {p: p.read_bytes() for p in local.rglob("*") if p.is_file()}
    missing = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert missing.returncode == 0, missing.stderr
    assert json.loads(missing.stdout)["status"] == "missing-log"
    assert missing_before == {p: p.read_bytes() for p in local.rglob("*") if p.is_file()}


def test_native_io_export_roundtrips_delivered_bytes_and_reports_gaps(tmp_path, shared_core_binary, monkeypatch):
    """Protect loss of diagnostic content at the native capture/export boundary."""
    from aw_maintainer import session_diagnostics as reader

    configured(tmp_path, "absolute")
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", "native-io-roundtrip")
    monkeypatch.delenv("AW_SESSION_LOGGING_DISABLE", raising=False)
    supplied = []
    for projection in ("full", "compact", "carried"):
        # The large request/result crosses both the event and old inline bound.
        task = "harmless-task-å-" * 6000 if projection == "compact" else f"Harmless {projection} task"
        request = {"start": {"target": str(tmp_path), "task": task, "projection": projection}}
        raw = (json.dumps(request, ensure_ascii=False, indent=2) + "\n").encode()
        result = subprocess.run([str(shared_core_binary)], input=raw, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr
        supplied.append((raw, result))
        if projection == "carried":
            delivered = json.loads(result.stdout)
            assert delivered["view"]["session_capture"]["detail"] == "full"
            assert "session_capture" not in json.dumps(delivered["carriage"])
    for request in (
        {
            "invoke": {
                "target": str(tmp_path),
                "task": "Harmless invoke argument",
                "invocation": {"operation_id": "distinctive-diagnostic-argument"},
            }
        },
        {"start": {"target": str(tmp_path), "task": "Harmless error task", "unexpected": True}},
    ):
        raw = json.dumps(request, ensure_ascii=False).encode()
        result = subprocess.run([str(shared_core_binary)], input=raw, capture_output=True, timeout=30)
        supplied.append((raw, result))
    assert supplied[-1][1].returncode == 2
    assert b"invalid-source-decision" in supplied[-1][1].stderr
    rows = events(tmp_path)
    assert len(rows) == len(supplied)
    assert any(len(result.stdout) > 65536 for _, result in supplied)
    for row, (raw, result) in zip(rows, supplied, strict=True):
        entry = row["payload"]["entry"]
        reference = entry["artifact"]
        artifact_bytes = (tmp_path / reference["path"]).read_bytes()
        assert len(artifact_bytes) == reference["bytes"]
        assert hashlib.sha256(artifact_bytes).hexdigest() == reference["sha256"]
        artifact = json.loads(artifact_bytes)
        assert artifact["request"].encode() == raw
        assert artifact["stdout"].encode() == result.stdout
        assert artifact["stderr"].encode() == result.stderr
        assert entry["output_digest"] == hashlib.sha256(result.stdout + result.stderr).hexdigest()
        config = json.loads(artifact["configuration"])
        assert config["effective_logging_policy"] == {"enabled": True, "detail": "full", "path_mode": "absolute"}
        assert config["local_sources"] and config["runtime"]["bundled_payload_revision"]

    state = reader.load_state_for_argv(["--target", str(tmp_path)])
    exported = reader.export_session_log(state=state)
    assert exported["manifest"]["diagnostic_content"]["content_complete_for_recorded_commands"]
    assert exported["artifact_count"] == len(rows)
    with gzip.open(tmp_path / exported["path"], "rt", encoding="utf-8") as stream:
        export_events = [json.loads(line) for line in stream]
    for row in rows:
        entry = row["payload"]["entry"]
        artifact = json.loads((tmp_path / entry["artifact"]["path"]).read_bytes())
        for name in ("request", "stdout", "stderr", "configuration"):
            chunks = [
                event["payload"]
                for event in export_events
                if event["event_type"] == "output.chunk"
                and event["payload"]["entry_id"] == entry["id"]
                and event["payload"]["stream"] == name
            ]
            chunks.sort(key=lambda chunk: chunk["chunk_index"])
            content = "".join(chunk["text"] for chunk in chunks)
            expected = reader._normalized_export_text(state=state, text=artifact[name])
            assert content == expected
            assert hashlib.sha256(content.encode()).hexdigest() == chunks[0]["stream_sha256"]
            assert hashlib.sha256(artifact[name].encode()).hexdigest() == chunks[0]["source_stream_sha256"]
            assert len(chunks) == chunks[0]["chunk_count"]
    # Explicit omission and damaged/missing blobs cannot look like full capture.
    omitted = reader.export_session_log(state=state, include_artifacts=False)
    assert not omitted["manifest"]["diagnostic_content"]["content_complete_for_recorded_commands"]
    artifact_path = tmp_path / rows[0]["payload"]["entry"]["artifact"]["path"]
    artifact_path.write_bytes(artifact_path.read_bytes() + b" ")
    damaged = reader.export_session_log(state=state)
    assert "damaged" in {entry["status"] for entry in damaged["manifest"]["artifact_coverage"]}
    assert not damaged["manifest"]["diagnostic_content"]["content_complete_for_recorded_commands"]
    artifact_path.write_bytes(b'{"interrupted":')
    malformed = reader.export_session_log(state=state)
    assert "damaged" in {entry["status"] for entry in malformed["manifest"]["artifact_coverage"]}
    artifact_path.unlink()
    missing = reader.export_session_log(state=state)
    assert "missing" in {entry["status"] for entry in missing["manifest"]["artifact_coverage"]}
    assert not missing["manifest"]["diagnostic_content"]["content_complete_for_recorded_commands"]


def test_full_capture_omits_ambient_config_secrets_but_keeps_provenance(tmp_path, shared_core_binary, monkeypatch):
    from aw_maintainer import session_diagnostics as reader

    configured(tmp_path, "absolute")
    secret = "synthetic-ambient-credential-7aab5f09"
    shared = tmp_path / ".agentic-workspace/config.toml"
    shared.write_text(
        f'''[workspace]
enabled = false
cli_invoke = "helper --token {secret}"
agent_instructions_file = "{secret}.md"
improvement_latitude = "conservative"
[modules]
enabled = ["memory"]
[modules.independent.example]
binding = "sha256:{"a" * 64}"
reads = ["{secret}.json"]
[modules.independent.example.settings]
api_key = "{secret}"
nested = {{ arbitrary = ["{secret}"] }}
[assurance]
default_level = "high"
strict_closeout = false
decision_record_target = "{secret}/"
[payload]
target_release = "{secret}"
minimum_capabilities = ["{secret}"]
policy = "advisory"
''',
        encoding="utf-8",
    )
    # A selected shared-local filename is also unconstrained configuration.
    selected_local = tmp_path / f"{secret}.toml"
    selected_local.write_text('[clarification]\nmode = "suggest"\n', encoding="utf-8")
    local = tmp_path / ".agentic-workspace/config.local.toml"
    local.write_text(local.read_text() + f'[workspace]\nshared_config_path = "{selected_local.name}"\n', encoding="utf-8")
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", "ambient-config-privacy")
    monkeypatch.delenv("AW_SESSION_LOGGING_DISABLE", raising=False)
    raw = json.dumps({"start": {"target": str(tmp_path), "task": "Inspect inactive configuration"}}).encode()
    result = subprocess.run([str(shared_core_binary)], input=raw, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "inactive"
    row = events(tmp_path)[0]
    artifact_bytes = (tmp_path / row["payload"]["entry"]["artifact"]["path"]).read_bytes()
    assert secret.encode() not in artifact_bytes
    artifact = json.loads(artifact_bytes)
    assert artifact["request"].encode() == raw
    assert artifact["stdout"].encode() == result.stdout
    assert artifact["stderr"].encode() == result.stderr
    config = json.loads(artifact["configuration"])
    assert config["effective_configuration"] == {
        "workspace": {"enabled": False, "improvement_latitude": "conservative"},
        "modules": {"enabled": ["memory"]},
        "assurance": {"default_level": "high", "strict_closeout": False},
        "payload": {"policy": "advisory"},
        "clarification": {"mode": "suggest"},
        "session_logging": {"enabled": True, "detail": "full", "path_mode": "absolute"},
    }
    assert config["repository_source"] == {
        "reference": ".agentic-workspace/config.toml",
        "status": "current",
        "revision": "sha256:" + hashlib.sha256(shared.read_bytes()).hexdigest(),
    }
    assert config["local_sources"] == [
        {
            "role": "shared-local",
            "status": "current-shared-local-source",
            "revision": "sha256:" + hashlib.sha256(selected_local.read_bytes()).hexdigest(),
        },
        {
            "role": "repository-local",
            "status": "current-local-source",
            "revision": "sha256:" + hashlib.sha256(local.read_bytes()).hexdigest(),
        },
    ]
    assert config["local_source_revision"] and config["runtime"]["bundled_payload_revision"]
    exported = reader.export_session_log(state=reader.load_state_for_argv(["--target", str(tmp_path)]))
    assert exported["manifest"]["diagnostic_content"]["content_complete_for_recorded_commands"]
    with gzip.open(tmp_path / exported["path"], "rt", encoding="utf-8") as stream:
        export_text = stream.read()
    assert secret not in export_text
    chunks = [
        event["payload"]
        for event in map(json.loads, export_text.splitlines())
        if event["event_type"] == "output.chunk" and event["payload"]["stream"] == "configuration"
    ]
    exported_config = json.loads("".join(chunk["text"] for chunk in sorted(chunks, key=lambda chunk: chunk["chunk_index"])))
    for field in ("effective_configuration", "repository_source", "local_sources", "local_source_revision", "runtime"):
        assert exported_config[field] == config[field]


def test_explicit_metadata_logging_discloses_omitted_bodies(tmp_path, shared_core_binary, monkeypatch):
    from aw_maintainer import session_diagnostics as reader

    configured(tmp_path, detail="metadata")
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", "private-session-secret")
    result = call(shared_core_binary, tmp_path, task="Harmless metadata omission")
    assert json.loads(result.stdout)["session_capture"] == {"status": "capturing", "detail": "metadata", "authoritative": False}
    entry = events(tmp_path)[0]["payload"]["entry"]
    assert entry["storage_mode"] == "metadata-only" and "artifact" not in entry
    assert "request body" in entry["omissions"]
    exported = reader.export_session_log(state=reader.load_state_for_argv(["--target", str(tmp_path)]))
    content = exported["manifest"]["diagnostic_content"]
    assert content["capture_levels"] == ["metadata"]
    assert content["body_omission_command_ids"] == [entry["id"]]
    assert not content["content_complete_for_recorded_commands"]


def test_export_preserves_legacy_artifact_text_digest_framing(tmp_path):
    from aw_maintainer import session_diagnostics as reader

    session = {"session_id": "legacy-fixture", "log_path": ".agentic-workspace/local/logs/aw-session-legacy-fixture/session.md"}
    path = Path(session["log_path"]).parent / "artifacts/legacy.json"
    absolute = tmp_path / path
    absolute.parent.mkdir(parents=True)
    payload = {"kind": "agentic-workspace/session-log-output-artifact/v1", "stdout": "Historical harmless output\n", "stderr": ""}
    text = json.dumps(payload, indent=2)
    # Established writer hashes text, then writes a terminal newline; Windows
    # text mode converts framing newlines. This must not damage valid old logs.
    body = (text.replace("\n", "\r\n") + "\r\n").encode()
    absolute.write_bytes(body)
    entry = {
        "id": "legacy-entry",
        "artifact": {"path": path.as_posix(), "bytes": len(text.encode()), "sha256": hashlib.sha256(text.encode()).hexdigest()},
    }
    chunks, coverage = reader._artifact_chunk_events(
        state=reader.SessionLoggingState(tmp_path), session=session, entries=[entry], include_artifacts=True
    )
    assert coverage[0]["status"] == "included-as-output-chunks"
    assert coverage[0]["integrity_basis"] == "legacy-json-text-framing"
    assert coverage[0]["observed_artifact_sha256"] == hashlib.sha256(body).hexdigest()
    assert "".join(event["payload"]["text"] for event in chunks if event["payload"]["stream"] == "stdout") == payload["stdout"]


def test_full_export_reads_rotated_and_child_artifacts_once(tmp_path, monkeypatch):
    """Existing logical-tree selection must retain every physical body's content."""
    from aw_maintainer import session_diagnostics as reader

    identity = "logical-tree-reader-fixture"
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", identity)
    key = hashlib.sha256(("fixture-salt\0" + identity).encode()).hexdigest()
    logical = "logical-" + key[:24]
    registry = {"kind": reader.SESSION_REGISTRY_KIND, "salt": "fixture-salt", "sessions": {}, "logical_sessions": {}}
    groups = {logical: [], "logical-child": []}
    streams = {logical: [], "logical-child": []}
    for index, (physical, owner) in enumerate((("first", logical), ("rotated", logical), ("child", "logical-child"))):
        session = {
            "kind": reader.SESSION_RECORD_KIND,
            "session_id": physical,
            "logical_session_id": owner,
            "parent_logical_session_id": logical if physical == "child" else "",
            "prior_session_id": "first" if physical == "rotated" else "",
            "created_at": f"2026-10-03T00:00:0{index}+00:00",
            "log_path": f".agentic-workspace/local/logs/aw-session-{physical}/session.md",
            "event_stream_path": f".agentic-workspace/local/session-logging/logical-sessions/{owner}/events.jsonl",
        }
        log = tmp_path / session["log_path"]
        log.parent.mkdir(parents=True)
        log.write_text("# Reader fixture\n")
        artifact = log.parent / "artifacts/io.json"
        artifact.parent.mkdir()
        body = json.dumps(
            {
                "kind": "agentic-workspace/session-command-io/v1",
                "request": f"Harmless {physical} request",
                "stdout": f"Harmless {physical} result",
                "stderr": "",
                "configuration": "{}",
            }
        ).encode()
        artifact.write_bytes(body)
        entry = {
            "id": physical,
            "detail": "full",
            "storage_mode": "raw-local-artifact",
            "artifact": {"path": artifact.relative_to(tmp_path).as_posix(), "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)},
        }
        event = reader._synthetic_export_event(
            session=session, event_type="command.completed", sequence=index + 1, timestamp=session["created_at"], payload={"entry": entry}
        )
        event.pop("recovered_from")
        streams[owner].append(event)
        groups[owner].append(session)
    registry["sessions"][key] = groups[logical][-1]
    for owner, sessions in groups.items():
        registry["logical_sessions"][key if owner == logical else "child-key"] = {
            "logical_session_id": owner,
            "parent_logical_session_id": logical if owner == "logical-child" else "",
            "sessions": sessions,
            "event_stream_path": sessions[0]["event_stream_path"],
        }
        stream = tmp_path / sessions[0]["event_stream_path"]
        stream.parent.mkdir(parents=True)
        stream.write_text("".join(json.dumps(event) + "\n" for event in streams[owner]))
    path = tmp_path / reader.SESSION_REGISTRY_PATH
    path.write_text(json.dumps(registry))
    exported = reader.export_session_log(state=reader.SessionLoggingState(tmp_path))
    assert set(exported["session_ids"]) == {"first", "rotated", "child"}
    assert exported["artifact_count"] == 3
    assert not exported["manifest"]["excluded_artifacts"]
    assert exported["manifest"]["diagnostic_content"]["content_complete_for_recorded_commands"]
    with gzip.open(tmp_path / exported["path"], "rt", encoding="utf-8") as handle:
        events_out = [json.loads(line) for line in handle]
    requests = [
        event["payload"]["text"]
        for event in events_out
        if event["event_type"] == "output.chunk" and event["payload"]["stream"] == "request"
    ]
    assert sorted(requests) == ["Harmless child request", "Harmless first request", "Harmless rotated request"]


@pytest.mark.parametrize(
    "settings,override,enabled,mode",
    [
        ({}, "", False, "absolute"),
        ({"enabled": True, "path_mode": "redacted"}, "", True, "redacted"),
        ({"enabled": True, "path_mode": "repo-relative"}, "1", False, "repo-relative"),
        ({"enabled": False}, "0", False, "absolute"),
    ],
)
def test_shared_logging_policy(settings, override, enabled, mode, shared_core_binary):
    from aw_maintainer.native_conformance import session_logging_policy

    result = session_logging_policy({"local": {"session_logging": settings}, "disable_override": override})
    assert result == {"enabled": enabled, "path_mode": mode, "detail": "full"}


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
        '[session_logging]\nenabled = "true"\n',
        '[session_logging]\nenabled = true\npath_mode = "unknown"\n',
        '[session_logging]\nenabled = true\ndetail = "unknown"\n',
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
    from aw_maintainer.session_diagnostics import _session_registry_lock

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


def test_capture_posture_recovers_prospectively_without_episode_residue(tmp_path, shared_core_binary):
    configured(tmp_path)
    expected = {"status": "identity-unavailable", "requirement": "AW_SESSION_LOGICAL_IDENTITY", "authoritative": False}
    baseline = call(shared_core_binary, tmp_path, enabled=False)
    for identity in ["", "  ", "x" * 8193, ""]:
        result = call(shared_core_binary, tmp_path, identity=identity)
        value = json.loads(result.stdout)
        assert value.pop("session_capture") == expected
        assert len(json.dumps(expected)) < 160
        assert value == json.loads(baseline.stdout)
        assert result.returncode == baseline.returncode
        assert result.stderr == ""
        assert not (tmp_path / ".agentic-workspace/local").exists()
    recovered = call(shared_core_binary, tmp_path)
    assert json.loads(recovered.stdout)["session_capture"]["status"] == "capturing"
    assert len(events(tmp_path)) == 1
    assert events(tmp_path)[0]["sequence"] == 1
    # Failure is another replaceable observation, including failed effect results.
    stream = next(tmp_path.glob(".agentic-workspace/local/session-logging/logical-sessions/*/events.jsonl"))
    original = stream.read_bytes()
    stream.write_bytes(original + b"{")
    baseline_failure = call(shared_core_binary, tmp_path, invoke=True, enabled=False)
    for _ in range(2):
        failed = call(shared_core_binary, tmp_path, invoke=True)
        value = json.loads(failed.stdout)
        assert value.pop("session_capture") == {"status": "capture-failed", "authoritative": False}
        assert value == json.loads(baseline_failure.stdout)
        assert failed.returncode == baseline_failure.returncode
        assert failed.stderr == ""
        assert stream.read_bytes() == original + b"{"
    stream.write_bytes(original)
    assert json.loads(call(shared_core_binary, tmp_path).stdout)["session_capture"]["status"] == "capturing"
    assert [row["sequence"] for row in events(tmp_path)] == [1, 2]
    # Even an invalid public request keeps its original error status and payload.
    import copy

    env = dict(os.environ, AW_SESSION_LOGICAL_IDENTITY="")
    env.pop("AW_SESSION_LOGGING_DISABLE", None)
    request = {"start": {"target": str(tmp_path), "unexpected": True}}
    bad = subprocess.run([str(shared_core_binary)], input=json.dumps(request), text=True, capture_output=True, env=env)
    disabled_env = copy.copy(env)
    disabled_env["AW_SESSION_LOGGING_DISABLE"] = "1"
    quiet = subprocess.run([str(shared_core_binary)], input=json.dumps(request), text=True, capture_output=True, env=disabled_env)
    error = json.loads(bad.stderr)
    assert error.pop("session_capture") == expected
    assert error == json.loads(quiet.stderr)
    assert bad.returncode == quiet.returncode == 2
