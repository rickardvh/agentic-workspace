from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from tests.workspace_cli_support import aw_subprocess_env

from agentic_workspace import cli as source_cli
from agentic_workspace import current_work_context, session_logging


@pytest.fixture(autouse=True)
def _capture_pytest_session_log_detail(monkeypatch) -> Iterator[None]:
    session_logging._declared_workspace_command_interfaces.cache_clear()
    for key in (
        "AW_SESSION_LOG_ORIGIN",
        "AW_SESSION_LOG_EXPECTED_FAILURE",
        "AW_SESSION_LOG_EXPECTED_EXIT",
        "AW_SESSION_LOG_EXPECTED_REASON_CLASS",
        "AW_SESSION_LOG_PARENT_COMMAND",
        "AW_SESSION_LOG_PARENT_CONTEXT",
        "AW_SESSION_LOG_PARENT_ENTRY_ID",
        "AW_SESSION_LOG_PARENT_LOGICAL_IDENTITY",
        "AW_SESSION_CORRELATION_ID",
        "AW_VALIDATION",
        "AW_VALIDATION_CONTEXT",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AW_SESSION_LOG_CAPTURE_DETAIL", "1")
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "pytest-logical-session")
    yield
    session_logging._declared_workspace_command_interfaces.cache_clear()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _target(tmp_path: Path) -> Path:
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n")
    (tmp_path / ".git").mkdir()
    return tmp_path


def _current_log(target: Path) -> Path:
    status = session_logging.status_payload(state=session_logging.load_state_for_argv(["--target", str(target)]))
    return target / status["path"]


def _current_index(target: Path) -> Path:
    status = session_logging.status_payload(state=session_logging.load_state_for_argv(["--target", str(target)]))
    return target / status["index_path"]


def _current_events(target: Path) -> Path:
    status = session_logging.status_payload(state=session_logging.load_state_for_argv(["--target", str(target)]))
    return target / status["event_stream_path"]


def _read_export(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_session_logging_disabled_does_not_create_log(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)

    assert source_cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"].startswith("agentic-workspace/config")
    assert not (target / ".agentic-workspace/local/logs").exists()


def test_session_logging_disabled_does_not_redirect_command_output(tmp_path: Path) -> None:
    target = _target(tmp_path)
    observed_stdout = None
    original_stdout = sys.stdout

    def runner(_argv: list[str]) -> int:
        nonlocal observed_stdout
        observed_stdout = sys.stdout
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0

    assert observed_stdout is original_stdout
    assert not (target / ".agentic-workspace/local/logs").exists()


def test_session_logging_mutes_pytest_origin_capture_by_default(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv("AW_SESSION_LOG_CAPTURE_DETAIL", raising=False)
    monkeypatch.delenv("AW_SESSION_LOG_PYTEST_CAPTURE", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_workspace_session_logging.py::test_example (call)")

    def runner(_argv: list[str]) -> int:
        print("visible stdout")
        print("visible stderr", file=sys.stderr)
        return 7

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 7

    output = capsys.readouterr()
    assert output.out == "visible stdout\n"
    assert output.err == "visible stderr\n"
    assert not (target / session_logging.SESSION_REGISTRY_PATH).exists()
    assert not (target / session_logging.SESSION_LOG_ROOT).exists()


def test_session_logging_default_pytest_capture_stays_bounded_across_many_commands(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv("AW_SESSION_LOG_CAPTURE_DETAIL", raising=False)
    monkeypatch.delenv("AW_SESSION_LOG_PYTEST_CAPTURE", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_workspace_session_logging.py::test_bounded (call)")

    for index in range(5):
        assert session_logging.run_with_session_logging(["summary", "--target", str(target)], lambda _argv: print(index) or 0) == 0

    assert capsys.readouterr().out == "0\n1\n2\n3\n4\n"
    assert not (target / session_logging.SESSION_REGISTRY_PATH).exists()
    assert not (target / session_logging.SESSION_LOG_ROOT).exists()


def test_session_logging_pytest_origin_full_capture_requires_explicit_opt_in(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_workspace_session_logging.py::test_captured (call)")
    monkeypatch.setenv("AW_SESSION_LOG_CAPTURE_DETAIL", "1")

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], lambda _argv: print("captured") or 0) == 0
    capsys.readouterr()

    payload = session_logging.analyze_session_log(
        state=session_logging.load_state_for_argv(["--target", str(target)]),
        origin_scope="test",
        detail="entries",
    )
    assert payload["summary"]["command_count"] == 1
    assert payload["origin_breakdown"] == {"pytest": 1}
    entry = payload["detail_page"]["items"][0]
    assert entry["origin"]["classification"] == "pytest"
    assert entry["parent"]["context"].startswith("tests/test_workspace_session_logging.py::test_captured")


def test_session_logging_explicit_live_agent_origin_captures_even_under_pytest(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv("AW_SESSION_LOG_CAPTURE_DETAIL", raising=False)
    monkeypatch.delenv("AW_SESSION_LOG_PYTEST_CAPTURE", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_workspace_session_logging.py::test_live_agent (call)")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: print("agent") or 0) == 0
    capsys.readouterr()

    payload = session_logging.analyze_session_log(state=session_logging.load_state_for_argv(["--target", str(target)]))
    assert payload["summary"]["command_count"] == 1
    assert payload["origin_breakdown"] == {"agent": 1}


def test_session_logging_mutes_nested_pytest_origin_capture_by_default(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv("AW_SESSION_LOG_CAPTURE_DETAIL", raising=False)
    monkeypatch.delenv("AW_SESSION_LOG_PYTEST_CAPTURE", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_workspace_session_logging.py::test_nested (call)")

    def outer(_argv: list[str]) -> int:
        return session_logging.run_with_session_logging(["summary", "--target", str(target)], lambda _inner: 0)

    assert session_logging.run_with_session_logging(["start", "--target", str(target)], outer) == 0

    assert not (target / session_logging.SESSION_REGISTRY_PATH).exists()
    assert not (target / session_logging.SESSION_LOG_ROOT).exists()


def test_session_logging_status_defaults_for_parent_command(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)

    assert source_cli.main(["session-log", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/session-logging-status/v1"
    assert payload["enabled"] is False
    assert not (target / ".agentic-workspace/local/logs").exists()


def test_session_logging_enabled_reuses_one_session_log_and_records_config_prelude(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

    assert source_cli.main(["config", "--target", str(target), "--select", "workspace.enabled", "--format", "json"]) == 0
    first_output = json.loads(capsys.readouterr().out)
    assert first_output["values"]["workspace.enabled"] is True
    first_log = _current_log(target)

    assert source_cli.main(["config", "--target", str(target), "--select", "workspace.enabled_source", "--format", "json"]) == 0
    capsys.readouterr()
    second_log = _current_log(target)

    assert first_log == second_log
    text = first_log.read_text(encoding="utf-8")
    assert "Agentic Workspace Session Log" in text
    assert '"enabled_modules"' in text
    assert '"session_logging"' in text
    assert '"enabled": true' in text
    assert text.count("## Command - ") == 2
    assert "agentic-workspace config --target" in text
    assert "- exit_status: `0`" in text
    assert "Output stored as local artifact:" in text
    assert "stdout summary:" in text
    assert "`json`" in text

    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    assert index["kind"] == "agentic-workspace/session-log-index/v2"
    assert index["session_header"]["session_id"] == index["session_id"]
    assert set(index["records"]) == {"contexts", "invocation_intents", "provenance", "segments"}
    assert len(index["entries"]) == 2
    assert index["entries"][0]["stdout"]["kind"] == "json"
    assert index["entries"][0]["artifact"]["path"].startswith(str(first_log.parent.relative_to(target)).replace("\\", "/") + "/artifacts/")
    snapshot = json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])
    boundary = snapshot["logging_policy"]["local_diagnostic_boundary"]
    assert boundary["scope"] == "package-owned local diagnostic state"
    assert boundary["manual_handoff"] == "outside-aw-logger-responsibility"
    assert "promotion_boundary" not in snapshot["logging_policy"]
    assert "share_safe" not in text


def test_session_logging_writes_canonical_monotonic_jsonl(tmp_path: Path) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], lambda _argv: 0) == 0
    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0

    events = [json.loads(line) for line in _current_events(target).read_text(encoding="utf-8").splitlines()]
    schema = json.loads(
        (Path(__file__).parents[1] / "src/agentic_workspace/contracts/schemas/session_log_event.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    for event in events:
        validator.validate(event)
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert [event["event_type"] for event in events] == [
        "session.started",
        "command.started",
        "command.completed",
        "command.started",
        "command.completed",
    ]
    started = [event for event in events if event["event_type"] == "command.started"]
    completed = [event for event in events if event["event_type"] == "command.completed"]
    assert [event["payload"]["entry_id"] for event in started] == [event["payload"]["entry"]["id"] for event in completed]
    assert len({event["event_id"] for event in events}) == len(events)
    assert all(event["logical_session_id"] and event["physical_session_id"] for event in events)


def test_session_logging_reuses_identity_across_interleaved_sessions(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setattr(session_logging, "DEFAULT_MAX_INLINE_OUTPUT_BYTES", 1)

    def run(identity: str) -> dict[str, str]:
        monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, identity)

        def runner(_argv: list[str]) -> int:
            print("session output")
            return 0

        assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0
        status = session_logging.status_payload(state=session_logging.load_state_for_argv(["--target", str(target)]))
        return {"session_id": status["session_id"], "log_path": status["path"]}

    session_a = run("host-session-a")
    session_b = run("host-session-b")
    session_a_again = run("host-session-a")

    assert session_a_again == session_a
    assert session_b["session_id"] != session_a["session_id"]
    assert (target / session_a["log_path"]).read_text(encoding="utf-8").count("## Command - ") == 2
    assert (target / session_b["log_path"]).read_text(encoding="utf-8").count("## Command - ") == 1
    for session in (session_a, session_b):
        session_dir = (target / session["log_path"]).parent
        index = json.loads((session_dir / "index.json").read_text(encoding="utf-8"))
        assert all(f"/{session_dir.name}/artifacts/" in f"/{entry['artifact']['path']}" for entry in index["entries"])
    registry = json.loads((target / session_logging.SESSION_REGISTRY_PATH).read_text(encoding="utf-8"))
    assert len(registry["sessions"]) == 2
    assert "host-session-a" not in json.dumps(registry)
    assert "host-session-b" not in json.dumps(registry)


def test_session_logging_concurrent_identity_resolution_converges(tmp_path: Path) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])

    with ThreadPoolExecutor(max_workers=8) as executor:
        sessions = list(executor.map(lambda _index: session_logging.ensure_session(state=state, logical_identity="shared"), range(16)))

    assert len({session["session_id"] for session in sessions}) == 1
    assert len(list((target / session_logging.SESSION_LOG_ROOT).glob("aw-session-*/session.md"))) == 1
    assert not (target / session_logging.SESSION_REGISTRY_LOCK_PATH).exists()


def test_session_logging_concurrent_event_appends_remain_valid_and_monotonic(tmp_path: Path) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    session = session_logging.ensure_session(state=state, logical_identity="shared")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(
            executor.map(
                lambda index: session_logging._append_event(
                    state=state,
                    session=session,
                    event_type="note.appended",
                    payload={"index": index},
                ),
                range(24),
            )
        )

    events, issues = session_logging._read_event_stream(target / session_logging._event_path_for_session(session))
    assert issues == []
    assert len(events) == 25
    assert [event["sequence"] for event in events] == list(range(1, 26))


def test_session_logging_serializes_overlapping_index_projection_updates(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    session = session_logging.ensure_session(state=state, logical_identity="shared")
    barrier = threading.Barrier(2)
    active_writes = 0
    maximum_active_writes = 0
    observation_lock = threading.Lock()
    original_write = session_logging._write_json_atomic

    def observed_write(path: Path, payload: dict[str, object]) -> None:
        nonlocal active_writes, maximum_active_writes
        if path.name != "index.json":
            original_write(path, payload)
            return
        with observation_lock:
            active_writes += 1
            maximum_active_writes = max(maximum_active_writes, active_writes)
        try:
            time.sleep(0.05)
            original_write(path, payload)
        finally:
            with observation_lock:
                active_writes -= 1

    monkeypatch.setattr(session_logging, "_write_json_atomic", observed_write)

    def append(index: int) -> str | None:
        barrier.wait()
        return session_logging.append_command_entry(
            state=state,
            session=session,
            entry_id=f"concurrent-command-{index}",
            argv=["session-log", "analyze", "--detail", "summary"],
            capture=session_logging.CommandCapture(exit_code=0, stdout='{"status":"analyzed"}\n', stderr=""),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        warnings = list(executor.map(append, range(2)))

    assert warnings == [None, None]
    assert maximum_active_writes == 1
    index = json.loads((target / session_logging._index_path_for_session(session)).read_text(encoding="utf-8"))
    entries = session_logging._entries_from_index(index)
    assert {entry["id"] for entry in entries} == {"concurrent-command-0", "concurrent-command-1"}
    events, issues = session_logging._read_event_stream(target / session_logging._event_path_for_session(session))
    assert issues == []
    completed = [event for event in events if event["event_type"] == "command.completed"]
    assert {event["payload"]["entry"]["id"] for event in completed} == {"concurrent-command-0", "concurrent-command-1"}
    assert len({event["event_id"] for event in events}) == len(events)
    assert not (target / session_logging._index_lock_path_for_session(session)).exists()


def test_session_logging_atomic_replace_retries_windows_access_denied(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "index.json"
    original_replace = Path.replace
    attempts = 0

    def replace_with_transient_access_denied(source: Path, target: Path) -> Path:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError(5, "Access denied", str(target))
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", replace_with_transient_access_denied)

    session_logging._write_json_atomic(path, {"kind": session_logging.SESSION_LOG_INDEX_KIND, "entries": []})

    assert attempts == 2
    assert json.loads(path.read_text(encoding="utf-8"))["kind"] == session_logging.SESSION_LOG_INDEX_KIND
    assert list(tmp_path.glob("index.json.*.tmp")) == []


def test_session_log_concurrent_analyzers_complete_without_index_warning(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], lambda _argv: 0) == 0
    state = session_logging.load_state_for_argv(["--target", str(target)])
    status = session_logging.status_payload(state=state)
    barrier_root = tmp_path / "analyzer-barrier"
    barrier_root.mkdir()
    release_path = barrier_root / "release"
    script = (
        "import os, sys, time\n"
        "from pathlib import Path\n"
        "from agentic_workspace import cli\n"
        "ready = Path(os.environ['AW_TEST_ANALYZER_READY'])\n"
        "release = Path(os.environ['AW_TEST_ANALYZER_RELEASE'])\n"
        "ready.write_text('ready', encoding='utf-8')\n"
        "deadline = time.monotonic() + 10\n"
        "while not release.exists():\n"
        "    if time.monotonic() >= deadline: raise SystemExit('analyzer barrier timed out')\n"
        "    time.sleep(0.01)\n"
        "raise SystemExit(cli.main(['session-log', '--target', sys.argv[1], 'analyze', '--detail', sys.argv[2], '--format', 'json']))\n"
    )
    processes = []
    for index, detail in enumerate(("summary", "candidates")):
        child_env = dict(os.environ)
        child_env["AW_TEST_ANALYZER_READY"] = str(barrier_root / f"ready-{index}")
        child_env["AW_TEST_ANALYZER_RELEASE"] = str(release_path)
        processes.append(
            subprocess.Popen(
                [sys.executable, "-c", script, str(target), detail],
                cwd=Path.cwd(),
                env=child_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
        )
    deadline = time.monotonic() + 10
    while len(list(barrier_root.glob("ready-*"))) != 2:
        if time.monotonic() >= deadline:
            for process in processes:
                process.kill()
            raise AssertionError("analyzer subprocesses did not reach the barrier")
        time.sleep(0.01)
    release_path.write_text("release", encoding="utf-8")
    results = [process.communicate(timeout=20) for process in processes]

    assert [process.returncode for process in processes] == [0, 0]
    assert all("AW session logging warning" not in stderr for _stdout, stderr in results)
    assert all(json.loads(stdout)["status"] == "analyzed" for stdout, _stderr in results)
    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    entries = session_logging._entries_from_index(index)
    assert len(entries) == 3
    assert len({entry["id"] for entry in entries}) == 3
    events, issues = session_logging._read_event_stream(_current_events(target))
    assert issues == []
    completed = [event for event in events if event["event_type"] == "command.completed"]
    assert len(completed) == 3
    assert len({event["payload"]["entry"]["id"] for event in completed}) == 3
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    analysis = session_logging.analyze_session_log(state=state, origin_scope="all")
    exported = session_logging.export_session_log(state=state, include_artifacts=False)
    assert analysis["index_status"] == "complete"
    assert analysis["summary"]["command_count"] == 3
    assert exported["logical_session_id"] == status["logical_session_id"]
    assert exported["manifest"]["evidence_profile"]["source_command_count"] == 3


def test_session_log_rotation_and_delegated_child_export_as_one_stream(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "root-session")
    first = session_logging.ensure_session(state=state)
    assert session_logging.run_with_session_logging(["start", "--target", str(target), "--task", "#2703 intake"], lambda _argv: 0) == 0
    second = session_logging.ensure_session(state=state, force_new=True)
    assert session_logging._event_path_for_session(first) == session_logging._event_path_for_session(second)
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(
            executor.map(
                lambda item: session_logging._append_event(
                    state=state,
                    session=item[1],
                    event_type="note.appended",
                    payload={"concurrent_rotation_index": item[0]},
                ),
                enumerate([first, second] * 8),
            )
        )
    root_events, root_issues = session_logging._read_event_stream(target / session_logging._event_path_for_session(first))
    assert root_issues == []
    assert [event["sequence"] for event in root_events] == list(range(1, len(root_events) + 1))
    assert {first["session_id"], second["session_id"]}.issubset({event["physical_session_id"] for event in root_events})
    assert (
        session_logging.run_with_session_logging(["implement", "--target", str(target), "--task", "#2703 implementation"], lambda _argv: 0)
        == 0
    )
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "child-session")
    monkeypatch.setenv(session_logging.PARENT_LOGICAL_SESSION_IDENTITY_ENV, "root-session")
    child = session_logging.ensure_session(state=state)
    assert (
        session_logging.run_with_session_logging(["proof", "--target", str(target), "--task", "#2703 delegated proof"], lambda _argv: 0)
        == 0
    )
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "root-session")
    monkeypatch.delenv(session_logging.PARENT_LOGICAL_SESSION_IDENTITY_ENV)
    assert (
        session_logging.run_with_session_logging(
            ["closeout", "--target", str(target), "--task", "#2703 blocked review repair"], lambda _argv: 0
        )
        == 0
    )
    assert (
        session_logging.run_with_session_logging(["start", "--target", str(target), "--task", "#2703 final recheck"], lambda _argv: 0) == 0
    )

    exported = session_logging.export_session_log(state=state, include_artifacts=False)
    events = _read_export(target / exported["path"])
    repeated_export = session_logging.export_session_log(state=state, include_artifacts=False)
    repeated_events = _read_export(target / repeated_export["path"])

    assert set(exported["session_ids"]) == {first["session_id"], second["session_id"], child["session_id"]}
    assert exported["session_scope"]["physical_session_count"] == 3
    assert exported["session_scope"]["includes_rotations"] is True
    assert exported["session_scope"]["includes_delegated_children"] is True
    assert exported["manifest"]["source_logical_stream_count"] == 2
    assert len(exported["manifest"]["source_event_stream_paths"]) == 2
    rotation = next(event for event in events if event["event_type"] == "session.rotated")
    assert rotation["payload"]["next_physical_session_id"] == second["session_id"]
    commands = [event["payload"]["entry"]["command"] for event in events if event["event_type"] == "command.completed"]
    assert all(
        marker in "\n".join(commands)
        for marker in ("intake", "implementation", "delegated proof", "blocked review repair", "final recheck")
    )
    transitions = [event["payload"]["surface"] for event in events if event["event_type"] == "workflow.transition"]
    assert transitions == ["start", "implement", "proof", "closeout", "start"]
    exported_event_ids = [event["event_id"] for event in events[1:]]
    assert len(exported_event_ids) == len(set(exported_event_ids))
    assert events[1:] == repeated_events[1:]


def test_session_log_recovers_after_partial_tail_and_discloses_gap(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    session = session_logging.ensure_session(state=state)
    with (target / session_logging._event_path_for_session(session)).open("ab") as handle:
        handle.write(b'{"partial":')

    session_logging._append_event(state=state, session=session, event_type="note.appended", payload={"text": "after"})
    events, issues = session_logging._read_event_stream(target / session_logging._event_path_for_session(session))

    assert issues and issues[0]["reason"] == "invalid-event"
    assert [event["event_type"] for event in events][-2:] == ["logging.gap", "note.appended"]
    exported = session_logging.export_session_log(state=state, include_artifacts=False)
    assert exported["gap_count"] >= 1


def test_session_log_exports_legacy_views_with_migration_gap(tmp_path: Path) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], lambda _argv: 0) == 0
    _current_events(target).unlink()

    exported = session_logging.export_session_log(
        state=session_logging.load_state_for_argv(["--target", str(target)]), include_artifacts=False
    )
    events = _read_export(target / exported["path"])

    assert any(event["event_type"] == "command.completed" and event.get("recovered_from") for event in events)
    assert any(event["event_type"] == "logging.gap" and event["payload"]["reason"] == "legacy-migration" for event in events)


def test_session_logging_without_host_identity_creates_no_session_state(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)
    state = session_logging.load_state_for_argv(["--target", str(target)])
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], lambda _argv: 0) == 0
    assert session_logging.status_payload(state=state)["status"] == "logical-session-identity-required"
    assert session_logging.analyze_session_log(state=state)["status"] == "logical-session-identity-required"
    assert session_logging.repair_session_log_index(state=state)["status"] == "logical-session-identity-required"
    assert session_logging.export_session_log(state=state)["status"] == "logical-session-identity-required"
    assert session_logging.append_note(state=state, text="not captured")["status"] == "logical-session-identity-required"
    assert session_logging.reset_session(state=state)["status"] == "logical-session-identity-required"
    with pytest.raises(ValueError, match=session_logging.LOGICAL_SESSION_IDENTITY_ENV):
        session_logging.ensure_session(state=state)
    assert not (target / session_logging.SESSION_REGISTRY_PATH).exists()
    assert not (target / session_logging.SESSION_LOG_ROOT).exists()


def test_enabled_missing_identity_emits_one_structured_gap_then_recovers(tmp_path: Path, monkeypatch, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)

    assert session_logging.run_with_session_logging(["start", "--target", str(target)], lambda _argv: 0) == 0
    first = capsys.readouterr()
    assert first.out == ""
    prefix = "AW session logging capture gap: "
    assert first.err.startswith(prefix)
    signal = json.loads(first.err.removeprefix(prefix))
    assert signal["status"] == "identity-required"
    assert signal["required_environment"] == session_logging.LOGICAL_SESSION_IDENTITY_ENV
    assert signal["local_only"] is True
    assert signal["authoritative"] is False

    assert session_logging.run_with_session_logging(["implement", "--target", str(target)], lambda _argv: 0) == 0
    assert capsys.readouterr().err == ""
    capture_path = target / session_logging.SESSION_CAPTURE_STATUS_PATH
    unresolved = json.loads(capture_path.read_text(encoding="utf-8"))
    assert unresolved["status"] == "identity-required"
    assert unresolved["missing_identity_invocation_count"] == 2
    assert unresolved["capture_effect"] == "command-not-captured"

    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "late-host-identity")
    assert session_logging.run_with_session_logging(["proof", "--target", str(target)], lambda _argv: 0) == 0
    assert capsys.readouterr().err == ""
    recovered = json.loads(capture_path.read_text(encoding="utf-8"))
    assert recovered["status"] == "recovered"
    assert recovered["missing_identity_invocation_count"] == 2
    assert recovered["recovery_rule"].startswith("Earlier commands remain classified as uncaptured")
    events = [json.loads(line) for line in _current_events(target).read_text(encoding="utf-8").splitlines()]
    completed = [event for event in events if event["event_type"] == "command.completed"]
    assert len(completed) == 1
    assert " proof " in f" {completed[0]['payload']['entry']['command']} "


def test_missing_identity_capture_status_write_failure_does_not_block_command(tmp_path: Path, monkeypatch, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)
    monkeypatch.setattr(session_logging, "_write_json_atomic", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("read only")))
    ran: list[list[str]] = []

    assert session_logging.run_with_session_logging(["start", "--target", str(target)], lambda argv: ran.append(argv) or 17) == 17

    assert ran == [["start", "--target", str(target)]]
    signal = json.loads(capsys.readouterr().err.removeprefix("AW session logging capture gap: "))
    assert signal["status"] == "identity-required"
    assert signal["diagnostic_persistence"] == "unavailable"


def test_capture_status_recovery_write_failure_does_not_block_command(tmp_path: Path, monkeypatch, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)
    assert session_logging.run_with_session_logging(["start", "--target", str(target)], lambda _argv: 0) == 0
    capsys.readouterr()
    capture_path = target / session_logging.SESSION_CAPTURE_STATUS_PATH
    original_write = session_logging._write_json_atomic

    def fail_capture_status(path: Path, payload: dict[str, object]) -> None:
        if path == capture_path:
            raise OSError("read only")
        original_write(path, payload)

    monkeypatch.setattr(session_logging, "_write_json_atomic", fail_capture_status)
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "late-host-identity")
    ran: list[list[str]] = []

    assert session_logging.run_with_session_logging(["proof", "--target", str(target)], lambda argv: ran.append(argv) or 19) == 19

    assert ran == [["proof", "--target", str(target)]]
    signal = json.loads(capsys.readouterr().err.removeprefix("AW session logging warning: "))
    assert signal["status"] == "recovery-persistence-unavailable"
    assert signal["capture_effect"] == "future-commands-captured"


def test_disabled_logging_overrides_stale_capture_status(tmp_path: Path, monkeypatch, capsys) -> None:
    target = _target(tmp_path)
    config_path = target / ".agentic-workspace/config.local.toml"
    _write(config_path, "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)
    assert session_logging.run_with_session_logging(["start", "--target", str(target)], lambda _argv: 0) == 0
    capsys.readouterr()
    _write(config_path, "schema_version = 1\n\n[session_logging]\nenabled = false\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])

    assert session_logging.status_payload(state=state)["capture_posture"] == {
        "kind": session_logging.SESSION_CAPTURE_STATUS_KIND,
        "status": "disabled",
    }


def test_missing_identity_warning_respects_pytest_capture_suppression(tmp_path: Path, monkeypatch, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)
    monkeypatch.delenv("AW_SESSION_LOG_CAPTURE_DETAIL", raising=False)
    monkeypatch.delenv("AW_SESSION_LOG_PYTEST_CAPTURE", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_workspace_session_logging.py::test_suppressed (call)")

    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0

    assert capsys.readouterr().err == ""
    assert not (target / session_logging.SESSION_CAPTURE_STATUS_PATH).exists()


@pytest.mark.parametrize(
    "continuity_env",
    [session_logging.PARENT_LOGICAL_SESSION_IDENTITY_ENV, session_logging.SESSION_CORRELATION_ID_ENV],
)
def test_missing_identity_records_gap_through_explicit_continuity(tmp_path: Path, monkeypatch, continuity_env: str) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    if continuity_env == session_logging.SESSION_CORRELATION_ID_ENV:
        monkeypatch.setenv(continuity_env, "shared-correlation")
    session = session_logging.ensure_session(state=state)
    registry_path = target / session_logging.SESSION_REGISTRY_PATH
    registry_before = registry_path.read_bytes()
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)
    if continuity_env == session_logging.PARENT_LOGICAL_SESSION_IDENTITY_ENV:
        monkeypatch.setenv(continuity_env, "pytest-logical-session")

    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0

    events, issues = session_logging._read_event_stream(target / session_logging._event_path_for_session(session))
    assert issues == []
    assert events[-1]["event_type"] == "logging.gap"
    assert events[-1]["payload"]["reason"] == "logical-identity-missing"
    assert events[-1]["payload"]["continuity_source"] == continuity_env
    assert registry_path.read_bytes() == registry_before


def test_unresolved_missing_identity_consumes_explicit_gap_on_next_identified_write(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)
    monkeypatch.setenv(session_logging.SESSION_GAP_REASON_ENV, "lost-correlation-window")

    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0
    assert not (target / session_logging.SESSION_REGISTRY_PATH).exists()
    assert not (target / session_logging.SESSION_LOG_ROOT).exists()

    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "restored-owner")
    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0
    events = [json.loads(line) for line in _current_events(target).read_text(encoding="utf-8").splitlines()]
    gaps = [event for event in events if event["event_type"] == "logging.gap"]
    assert len(gaps) == 1
    assert gaps[0]["payload"]["reason"] == "lost-correlation-window"
    assert session_logging.SESSION_GAP_REASON_ENV not in os.environ


def test_ambiguous_correlation_does_not_choose_an_arbitrary_logical_owner(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    monkeypatch.setenv(session_logging.SESSION_CORRELATION_ID_ENV, "shared-across-tree")
    first = session_logging.ensure_session(state=state)
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "second-logical-owner")
    second = session_logging.ensure_session(state=state)
    paths = [target / session_logging._event_path_for_session(item) for item in (first, second)]
    before = [path.read_bytes() for path in paths]
    monkeypatch.delenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV)

    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0

    assert [path.read_bytes() for path in paths] == before


def test_physical_event_streams_migrate_to_one_logical_stream(tmp_path: Path) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    session = session_logging.ensure_session(state=state)
    canonical_path = target / session_logging._event_path_for_session(session)
    legacy_path = (target / session["log_path"]).parent / session_logging.SESSION_LOG_EVENT_STREAM_NAME
    legacy_path.write_bytes(canonical_path.read_bytes())
    canonical_path.unlink()
    registry_path = target / session_logging.SESSION_REGISTRY_PATH
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for current in registry["sessions"].values():
        current.pop("event_stream_path", None)
    for group in registry["logical_sessions"].values():
        group.pop("event_stream_path", None)
        for physical in group["sessions"]:
            physical.pop("event_stream_path", None)
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    migrated = session_logging.ensure_session(state=state)
    migrated_path = target / session_logging._event_path_for_session(migrated)
    events, issues = session_logging._read_event_stream(migrated_path)

    assert migrated_path != legacy_path
    assert migrated_path.is_file()
    assert issues == []
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    refreshed = json.loads(registry_path.read_text(encoding="utf-8"))
    assert next(iter(refreshed["logical_sessions"].values()))["event_stream_path"] == migrated_path.relative_to(target).as_posix()


def test_session_logging_disabled_capture_is_an_explicit_gap_for_existing_session(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    session = session_logging.ensure_session(state=state)
    monkeypatch.setenv("AW_SESSION_LOGGING_DISABLE", "1")

    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0

    events, issues = session_logging._read_event_stream(target / session_logging._event_path_for_session(session))
    assert issues == []
    gap = events[-1]
    assert gap["event_type"] == "logging.gap"
    assert gap["payload"]["reason"] == "capture-disabled"
    assert "status" not in json.dumps(gap)


def test_session_logging_identity_is_private_and_caller_drilldowns_resolve_it(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    raw_identity = "vendor-thread-secret-123"
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, raw_identity)
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], lambda _argv: 0) == 0
    state = session_logging.load_state_for_argv(["--target", str(target)])
    status = session_logging.status_payload(state=state)
    analysis = session_logging.analyze_session_log(state=state)
    exported = session_logging.export_session_log(state=state, include_artifacts=False)
    assert status["local_diagnostic_boundary"]["non_authoritative_for"] == [
        "Planning",
        "Memory",
        "current owner",
        "proof",
        "closeout",
    ]
    assert analysis["local_diagnostic_boundary"]["manual_handoff"] == "outside-aw-logger-responsibility"
    assert exported["manifest"]["local_diagnostic_boundary"]["scope"] == "package-owned local diagnostic state"

    assert status["logical_session_resolution"] == "identity-registry"
    assert status["session_scope"]["kind"] == "distinct-logical-session"
    assert analysis["session_scope"]["kind"] == "distinct-logical-session"
    assert exported["session_scope"]["kind"] == "distinct-logical-session"
    assert analysis["path"] == status["path"]
    assert exported["session_id"] == status["session_id"]
    for path in (target / ".agentic-workspace/local").rglob("*"):
        if path.is_file():
            assert raw_identity.encode() not in path.read_bytes()


def test_session_logging_new_session_replaces_only_callers_identity_mapping(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    session_a = session_logging.ensure_session(state=state, logical_identity="a")
    session_b = session_logging.ensure_session(state=state, logical_identity="b")
    monkeypatch.setenv(session_logging.LOGICAL_SESSION_IDENTITY_ENV, "a")

    replacement_a = session_logging.reset_session(state=state)

    assert replacement_a["session_id"] != session_a["session_id"]
    assert session_logging.ensure_session(state=state, logical_identity="a")["session_id"] == replacement_a["session_id"]
    assert session_logging.ensure_session(state=state, logical_identity="b") == session_b


def test_session_logging_note_command_appends_optional_note(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

    assert source_cli.main(["config", "--target", str(target), "--select", "workspace.enabled", "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        source_cli.main(
            ["session-log", "--target", str(target), "--format", "json", "note", "--text", "This output changed the next action."]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "appended"
    text = _current_log(target).read_text(encoding="utf-8")
    assert "## Agent Note - " in text
    assert "This output changed the next action." in text


def test_session_logging_invalid_registry_path_is_replaced(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

    assert source_cli.main(["config", "--target", str(target), "--select", "workspace.enabled", "--format", "json"]) == 0
    capsys.readouterr()
    first_log = _current_log(target)
    registry_path = target / session_logging.SESSION_REGISTRY_PATH
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    session_key = next(iter(registry["sessions"]))
    registry["sessions"][session_key]["log_path"] = "../../outside-session-log.md"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    assert source_cli.main(["config", "--target", str(target), "--select", "workspace.enabled_source", "--format", "json"]) == 0
    capsys.readouterr()

    second_log = _current_log(target)
    assert second_log != first_log
    assert not (target.parent / "outside-session-log.md").exists()
    assert ".agentic-workspace/local/logs/" in second_log.as_posix()


def test_session_logging_large_output_uses_recoverable_artifact(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setattr(session_logging, "DEFAULT_MAX_INLINE_OUTPUT_BYTES", 12)

    def runner(_argv: list[str]) -> int:
        print("x" * 80)
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0
    assert "x" * 80 in capsys.readouterr().out

    log_text = _current_log(target).read_text(encoding="utf-8")
    assert "Output stored as local artifact:" in log_text
    artifact_line = next(line for line in log_text.splitlines() if "/artifacts/" in line and line.startswith("- path: `"))
    artifact_path = target / artifact_line.split("`", 2)[1]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["stdout"] == "x" * 80 + "\n"
    assert artifact["stderr"] == ""


def test_session_log_analyze_reports_counts_repeats_failures_artifacts_and_packets(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    def runner(_argv: list[str]) -> int:
        print(json.dumps({"kind": "agentic-workspace/example-packet/v1", "value": 1}))
        return 2

    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--format", "json"], runner) == 2
    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--format", "json"], runner) == 2
    capsys.readouterr()

    assert source_cli.main(["session-log", "--target", str(target), "analyze", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/session-log-analysis/v1"
    assert payload["status"] == "analyzed"
    assert payload["index_status"] == "complete"
    assert payload["coverage"]["markdown_command_count"] == 2
    assert payload["summary"]["live_agent_failure_count"] == 2
    assert payload["summary"]["command_count"] == 2
    assert payload["summary"]["failure_count"] == 2
    assert payload["summary"]["failed_count"] == 2
    assert payload["summary"]["repeated_failure_count"] == 1
    assert payload["summary"]["repeated_command_count"] == 1
    assert payload["summary"]["duplicate_output_count"] == 1
    assert payload["summary"]["artifact_count"] == 2
    assert payload["packet_kinds"]["agentic-workspace/example-packet/v1"] == 2
    assert payload["parsed_packet_kinds"]["agentic-workspace/example-packet/v1"] == 2
    assert payload["repeated_failures"][0]["count"] == 2
    candidates = session_logging.analyze_session_log(
        state=session_logging.load_state_for_argv(["--target", str(target)]), detail="candidates"
    )["detail_page"]["items"]
    assert {candidate["id"] for candidate in candidates} >= {
        "failed-command",
        "repeated-command",
        "duplicate-output",
    }
    repeated_signal = next(item["improvement_signal"] for item in candidates if item["id"] == "repeated-command")
    assert repeated_signal["kind"] == "workflow_cost"
    assert repeated_signal["evidence_classes"] == ["machine_observed"]
    assert repeated_signal["recurrence"] == "repeated"
    assert repeated_signal["occurrence_count"] == 2
    assert repeated_signal["suspected_owner"] == "operating-loop"
    assert repeated_signal["mutation_authorized"] is False

    state = session_logging.load_state_for_argv(["--target", str(target)])
    status = session_logging.status_payload(state=state)
    assert source_cli.main(["session-log", "--target", str(target), "analyze", "--id", status["session_id"], "--format", "json"]) == 0
    by_id = json.loads(capsys.readouterr().out)
    assert by_id["path"] == payload["path"]

    directory_id = f"aw-session-{status['session_id']}"
    assert source_cli.main(["session-log", "--target", str(target), "analyze", "--id", directory_id, "--format", "json"]) == 0
    by_directory_id = json.loads(capsys.readouterr().out)
    assert by_directory_id["path"] == payload["path"]


def test_session_log_analyze_markdown_fallback_extracts_inline_output_without_index(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    monkeypatch.setattr(session_logging, "DEFAULT_MAX_INLINE_OUTPUT_BYTES", 12)
    log_path = target / ".agentic-workspace/local/logs/aw-session-upload/session.md"
    modules_payload = json.dumps({"kind": "agentic-workspace/modules-report/v1", "items": ["x" * 40]})
    _write(
        log_path,
        f"""# Agentic Workspace Session Log

## Command - 2026-07-09T15:46:03+00:00

- id: `cmd-summry`
- exit_status: `2`

```sh
agentic-workspace summry --format json
```

stdout:
```text

```

stderr:
```text
usage: agentic-workspace
error: argument command: invalid choice: 'summry' (choose from 'summary')
Did you mean: summary?
```

## Command - 2026-07-09T15:46:04+00:00

- id: `cmd-selector`
- exit_status: `2`

```sh
agentic-workspace report --verbose --section agent_aids --format json
```

stdout:
```text

```

stderr:
```text
error: report detail selectors are mutually exclusive
```

## Command - 2026-07-09T15:46:05+00:00

- id: `cmd-modules-1`
- exit_status: `0`

```sh
agentic-workspace modules --verbose --format json
```

stdout:
```text
{modules_payload}
```

stderr:
```text

```

## Command - 2026-07-09T15:46:06+00:00

- id: `cmd-modules-2`
- exit_status: `0`

```sh
agentic-workspace modules --verbose --format json
```

stdout:
```text
{modules_payload}
```

stderr:
```text

```
""",
    )

    assert (
        source_cli.main(
            [
                "session-log",
                "--target",
                str(target),
                "analyze",
                "--path",
                log_path.relative_to(target).as_posix(),
                "--origin",
                "all",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["index_status"] == "missing"
    assert payload["index_presence"] == "markdown-fallback"
    assert payload["summary"]["command_count"] == 4
    assert payload["summary"]["failure_count"] == 2
    assert payload["summary"]["usage_mistake_count"] == 2
    assert payload["summary"]["repeated_command_count"] == 1
    assert payload["summary"]["duplicate_output_count"] == 1
    assert payload["packet_kinds"]["agentic-workspace/modules-report/v1"] == 2
    entries = session_logging.analyze_session_log(
        state=session_logging.load_state_for_argv(["--target", str(target)]),
        path=log_path.relative_to(target).as_posix(),
        origin_scope="all",
        detail="entries",
    )["detail_page"]["items"]
    failure_classes = {entry["failure_class"] for entry in entries if entry["failure_class"]}
    assert {"invalid-command", "selector-conflict"} <= failure_classes
    assert any(entry["command"] == "agentic-workspace modules --verbose --format json" for entry in entries)
    candidates = session_logging.analyze_session_log(
        state=session_logging.load_state_for_argv(["--target", str(target)]),
        path=log_path.relative_to(target).as_posix(),
        origin_scope="all",
        detail="candidates",
    )["detail_page"]["items"]
    assert {candidate["id"] for candidate in candidates} >= {
        "missing-index",
        "repeated-command",
        "duplicate-output",
        "large-output",
        "oversized-modules-output",
    }


def test_session_logging_reuses_duplicate_large_output_artifacts(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setattr(session_logging, "DEFAULT_MAX_INLINE_OUTPUT_BYTES", 12)

    def runner(_argv: list[str]) -> int:
        print("same output payload")
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0
    capsys.readouterr()

    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    artifacts = [entry["artifact"] for entry in index["entries"]]
    assert artifacts[0]["path"] == artifacts[1]["path"]
    assert artifacts[1]["duplicate_of"] == index["entries"][0]["id"]
    artifact_files = list(_current_log(target).parent.joinpath("artifacts").glob("*-output.json"))
    assert len(artifact_files) == 1


def test_session_logging_redacts_target_root_when_configured(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[session_logging]\nenabled = true\nredact_local_paths = true\n",
    )

    def runner(_argv: list[str]) -> int:
        print(f"local path: {target}")
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0
    assert str(target) in capsys.readouterr().out

    log_text = _current_log(target).read_text(encoding="utf-8")
    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    assert str(target) not in log_text
    assert target.as_posix() not in log_text
    assert "<target>" in log_text
    assert index["path_normalization"]["mode"] == "redacted"
    assert index["entries"][0]["target"] == "<target>"


def test_session_logging_path_mode_redacts_home_and_python_but_keeps_raw_artifact_local(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[session_logging]\nenabled = true\npath_mode = "redacted"\n',
    )
    monkeypatch.setattr(session_logging, "DEFAULT_MAX_INLINE_OUTPUT_BYTES", 12)

    def runner(_argv: list[str]) -> int:
        print(f"home={Path.home()} python={sys.executable} target={target}")
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0
    capsys.readouterr()

    log_text = _current_log(target).read_text(encoding="utf-8")
    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    assert str(Path.home()) not in log_text
    assert sys.executable not in log_text
    assert "<home>" in log_text
    assert "<python>" in log_text
    assert index["path_normalization"]["raw_artifact_recoverability"].startswith("raw output may remain")
    artifact_path = target / index["entries"][0]["artifact"]["path"]
    assert str(Path.home()).replace("\\", "\\\\") in artifact_path.read_text(encoding="utf-8")


def test_session_logging_path_mode_repo_relative_for_repo_contained_paths(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[session_logging]\nenabled = true\npath_mode = "repo-relative"\n',
    )

    def runner(_argv: list[str]) -> int:
        print(f"repo path: {target / 'src' / 'app.py'}")
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0
    capsys.readouterr()

    log_text = _current_log(target).read_text(encoding="utf-8")
    assert str(target) not in log_text
    assert "./src/app.py" in log_text or ".\\src\\app.py" in log_text


def test_session_logging_successful_system_exit_help_is_not_exception(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

    def runner(_argv: list[str]) -> int:
        print("usage: agentic-workspace config")
        raise SystemExit(0)

    try:
        session_logging.run_with_session_logging(["config", "--target", str(target), "--help"], runner)
    except SystemExit as exc:
        assert exc.code == 0

    capsys.readouterr()
    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    assert index["entries"][0]["exit_status"] == 0
    assert index["entries"][0]["exception"] == ""


def test_config_accepts_local_session_logging_without_unknown_field_warning(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[session_logging]\nenabled = true\nredact_local_paths = true\n",
    )

    assert source_cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert not any("session_logging" in warning for warning in payload["warnings"])

    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[session_logging]\nenabled = true\npath_mode = "repo-relative"\n',
    )
    assert source_cli.main(["config", "--target", str(target), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert not any("session_logging" in warning for warning in payload["warnings"])


def test_session_log_origins_expected_failures_and_nested_commands_are_separate(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

    def fail(_argv: list[str]) -> int:
        print("expected fixture error", file=sys.stderr)
        return 2

    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], fail) == 2
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "validation")
    monkeypatch.setenv("AW_SESSION_LOG_EXPECTED_FAILURE", "1")
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], fail) == 2
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], fail) == 2
    monkeypatch.delenv("AW_SESSION_LOG_ORIGIN")
    monkeypatch.delenv("AW_SESSION_LOG_EXPECTED_FAILURE")
    monkeypatch.delenv("PYTEST_CURRENT_TEST")

    def outer(_argv: list[str]) -> int:
        return session_logging.run_with_session_logging(["summary", "--target", str(target)], lambda _inner: 0)

    assert session_logging.run_with_session_logging(["start", "--target", str(target)], outer) == 0
    capsys.readouterr()
    payload = session_logging.analyze_session_log(state=session_logging.load_state_for_argv(["--target", str(target)]))
    assert payload["failures_by_origin"] == {"agent": 1, "validation": 2}
    assert payload["summary"]["failure_count"] == 1
    assert payload["summary"]["command_count"] == 2
    assert payload["summary"]["live_agent_failure_count"] == 1
    assert payload["summary"]["expected_failure_count"] == 0
    assert payload["origin_partitions"]["synthetic"]["failure_count"] == 2
    assert payload["repeated_failures_by_origin"]["validation"][0]["count"] == 2
    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    assert any(entry["origin"]["classification"] == "nested-aw" for entry in index["entries"])


def test_session_log_analysis_is_live_agent_first_for_mixed_pr_2166_bundle(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0
    capsys.readouterr()
    index_path = _current_index(target)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    template = index["entries"][0]
    entries = []
    for position in range(68):
        command = "summary --verbose --target ." if position == 0 else f"status --target . --select agent-{position}"
        if position == 1:
            command = "session-log analyze --target . --format json"
        entries.append(
            {
                **template,
                "id": f"agent-{position}",
                "command": command,
                "origin": {"classification": "agent", "source": "ordinary-cli", "detail": ""},
                "exit_status": 0,
                "output_bytes": 1_233_722 if position == 0 else 100,
                "output_digest": f"agent-digest-{position}",
            }
        )
    for position in range(35):
        entries.append(
            {
                **template,
                "id": f"pytest-{position}",
                "command": "summry --target ." if position < 15 else "modules --verbose --target .",
                "origin": {"classification": "pytest", "source": "PYTEST_CURRENT_TEST", "detail": ""},
                "invocation_intent": session_logging._invocation_intent(origin={"classification": "pytest"}, argv=("summry",)),
                "invocation_outcome": {},
                "parent_context": {"entry_id": "fixture-owner", "command": "pytest", "context": "test_session_fixture"},
                "exit_status": 2 if position < 15 else 0,
                "output_bytes": 200,
                "output_digest": f"pytest-digest-{position}",
            }
        )
    index["entries"] = entries
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    _current_events(target).unlink()
    state = session_logging.load_state_for_argv(["--target", str(target)])

    default = session_logging.analyze_session_log(state=state)
    assert default["analysis_scope"]["origin"] == "agent"
    assert default["summary"]["command_count"] == 68
    assert default["summary"]["failure_count"] == 0
    assert default["origin_breakdown"] == {"agent": 68, "pytest": 35}
    assert default["origin_partitions"]["test"]["command_count"] == 35
    assert default["origin_partitions"]["test"]["failure_count"] == 15
    test_entries = session_logging.analyze_session_log(state=state, origin_scope="test", detail="entries")["detail_page"]["items"]
    assert test_entries[0]["parent"]["entry_id"] == "fixture-owner"
    assert default["analyzer_overhead"]["command_count"] == 1
    default_candidates = session_logging.analyze_session_log(state=state, detail="candidates")["detail_page"]["items"]
    assert any("1233722 bytes" in item["summary"] for item in default_candidates)
    assert not any("summry" in item["summary"] or "session-log analyze" in item["summary"] for item in default_candidates)

    test_scope = session_logging.analyze_session_log(state=state, origin_scope="test")
    assert test_scope["summary"]["command_count"] == 35
    assert test_scope["summary"]["failure_count"] == 15
    test_candidates = session_logging.analyze_session_log(state=state, origin_scope="test", detail="candidates")["detail_page"]["items"]
    assert any("summry" in item["summary"] for item in test_candidates)
    all_scope = session_logging.analyze_session_log(state=state, origin_scope="all")
    assert all_scope["summary"]["command_count"] == 103
    assert all_scope["summary"]["failure_count"] == 15
    all_candidates = session_logging.analyze_session_log(state=state, origin_scope="all", detail="candidates")["detail_page"]["items"]
    assert any("summry" in item["summary"] for item in all_candidates)
    assert not any("summry" in item["summary"] for item in default_candidates)


def test_session_log_projects_parent_context_written_by_logger(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_PARENT_ENTRY_ID", "parent-entry")
    monkeypatch.setenv("AW_SESSION_LOG_PARENT_COMMAND", "pytest parent_test.py")
    monkeypatch.setenv("AW_SESSION_LOG_PARENT_CONTEXT", "fixture-parent")
    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0
    capsys.readouterr()

    payload = session_logging.analyze_session_log(
        state=session_logging.load_state_for_argv(["--target", str(target)]), origin_scope="test", detail="entries"
    )

    assert payload["detail_page"]["items"][0]["parent"] == {
        "entry_id": "parent-entry",
        "command": "pytest parent_test.py",
        "context": "fixture-parent",
    }


def test_session_log_origin_scopes_keep_synthetic_and_unknown_queryable(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    for origin in ("validation", "nested-aw", "unknown"):
        monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", origin)
        assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0
    capsys.readouterr()
    state = session_logging.load_state_for_argv(["--target", str(target)])
    assert session_logging.analyze_session_log(state=state)["summary"]["command_count"] == 0
    assert session_logging.analyze_session_log(state=state, origin_scope="synthetic")["summary"]["command_count"] == 2
    assert session_logging.analyze_session_log(state=state, origin_scope="unknown")["summary"]["command_count"] == 1


def test_session_log_preserves_producer_invocation_intent_and_matches_observed_outcomes(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "pytest")
    monkeypatch.setenv("AW_SESSION_LOG_PURPOSE_ID", "proof-negative-path")
    monkeypatch.setenv("AW_SESSION_LOG_SCENARIO_ID", "invalid-selector")
    monkeypatch.setenv("AW_SESSION_LOG_INVOCATION_CLASS", "negative-fixture")
    monkeypatch.setenv("AW_SESSION_LOG_EXPECTED_EXIT", "failure")
    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--select", "invalid"], lambda _: 2) == 2

    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    monkeypatch.setenv("AW_SESSION_LOG_PURPOSE_ID", "ordinary-config-read")
    monkeypatch.setenv("AW_SESSION_LOG_SCENARIO_ID", "config-success")
    monkeypatch.setenv("AW_SESSION_LOG_INVOCATION_CLASS", "product-operation")
    monkeypatch.setenv("AW_SESSION_LOG_EXPECTED_EXIT", "success")
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], lambda _: 2) == 2

    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "validation")
    monkeypatch.setenv("AW_SESSION_LOG_PURPOSE_ID", "validation-probe")
    monkeypatch.setenv("AW_SESSION_LOG_SCENARIO_ID", "config-readable")
    monkeypatch.setenv("AW_SESSION_LOG_INVOCATION_CLASS", "probe")
    monkeypatch.setenv("AW_SESSION_LOG_EXPECTED_EXIT", "success")
    assert session_logging.run_with_session_logging(["config", "--target", str(target)], lambda _: 0) == 0

    for name in (
        "AW_SESSION_LOG_PURPOSE_ID",
        "AW_SESSION_LOG_SCENARIO_ID",
        "AW_SESSION_LOG_INVOCATION_CLASS",
        "AW_SESSION_LOG_EXPECTED_EXIT",
    ):
        monkeypatch.delenv(name)
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    assert session_logging.run_with_session_logging(["summary", "--target", str(target)], lambda _: 0) == 0

    state = session_logging.load_state_for_argv(["--target", str(target)])
    analysis = session_logging.analyze_session_log(state=state, origin_scope="all")
    assert analysis["summary"]["matched_expectation_count"] == 3
    assert analysis["summary"]["unmatched_expectation_count"] == 1
    assert analysis["summary"]["unknown_expectation_count"] == 0
    assert analysis["summary"]["unexpected_failure_count"] == 1
    assert analysis["summary"]["live_agent_failure_count"] == 1
    entries = session_logging.analyze_session_log(state=state, origin_scope="all", detail="entries")["detail_page"]["items"]
    matched = [entry for entry in entries if entry["invocation_outcome"].get("match") == "matched"]
    unmatched = [entry for entry in entries if entry["invocation_outcome"].get("match") == "unmatched"]
    assert matched[0]["invocation_intent"]["invocation_class"] == "negative-fixture"
    assert unmatched[0]["invocation_outcome"]["observed"]["exit_class"] == "failure"
    assert not [entry for entry in entries if entry["invocation_outcome"].get("match") in {None, "", "unknown"}]
    assert analysis["summary"]["failed_count"] == 1
    observed_nonzero = [entry for entry in entries if entry["exit_status"] != 0]
    failed = [entry for entry in observed_nonzero if entry["invocation_outcome"].get("match") != "matched"]
    assert len(failed) == 1
    assert len(observed_nonzero) == 2
    assert matched[0] not in failed

    test_analysis = session_logging.analyze_session_log(state=state, origin_scope="test", detail="entries")
    assert test_analysis["summary"]["failed_count"] == 0
    test_entries = test_analysis["detail_page"]["items"]
    assert len([entry for entry in test_entries if entry["exit_status"] != 0]) == 1
    assert len([entry for entry in test_entries if entry["invocation_outcome"].get("match") == "matched"]) == 1

    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    negative = session_logging._entries_from_index(index)[0]
    assert negative["exit_status"] == 2
    assert negative["exit_class"] == "failure"
    assert negative["invocation_outcome"]["match"] == "matched"
    assert negative["invocation_outcome"]["expectation_provenance"]["source"] == "producer-environment+generated-command-package-ir"
    assert negative["invocation_outcome"]["observed"] != negative["invocation_outcome"]["expected"]


def test_lifecycle_typed_selector_failure_and_session_process_status_agree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace/config.local.toml",
        "schema_version = 1\n\n[session_logging]\nenabled = true\n",
    )
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    assert (
        source_cli.main(
            [
                "upgrade",
                "--target",
                str(target),
                "--dry-run",
                "--select",
                "actions",
                "--format",
                "json",
            ]
        )
        == 2
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selector-validation-error/v1"
    assert payload["exit_status"] == 2

    state = session_logging.load_state_for_argv(["--target", str(target)])
    entries = session_logging.analyze_session_log(state=state, origin_scope="all", detail="entries")["detail_page"]["items"]
    assert len(entries) == 1
    assert entries[0]["exit_status"] == payload["exit_status"] == 2
    assert entries[0]["exit_class"] == "failure"
    assert entries[0]["invocation_outcome"]["observed"]["exit_class"] == "failure"


def test_supported_workspace_commands_declare_generated_operation_purpose_without_producer_hints() -> None:
    expected_operations = {
        ("start",): "start.context",
        ("status",): "status.report",
        ("proof",): "proof.report",
        ("proof", "--record-receipt"): "proof.report",
        ("report",): "report.combined",
        ("reconcile",): "reconcile.report",
        ("planning", "reconcile"): "planning.front-door",
        ("session-log", "status"): "session-log.manage",
    }

    for argv, operation_id in expected_operations.items():
        intent = session_logging._invocation_intent(origin={"classification": "agent"}, argv=argv)
        assert intent["status"] == "declared"
        assert intent["invocation_class"] == "product-operation"
        assert intent["operation_id"] == operation_id
        assert intent["purpose_id"] == operation_id
        assert intent["purpose_summary"]
        assert intent["expected"]["exit_class"] == "success"
        assert intent["provenance"]["source"] == "generated-command-package-ir"

    unknown = session_logging._invocation_intent(origin={"classification": "agent"}, argv=("custom-helper",))
    assert unknown["status"] == "unknown"
    assert unknown["invocation_class"] == "unknown"
    assert unknown["operation_id"] == ""


def test_consequential_session_replay_emits_stable_material_candidates(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    commands = [
        *[["status", "--target", str(target)] for _ in range(3)],
        *[["proof", "--target", str(target)] for _ in range(2)],
        *[["proof", "--record-receipt", "--receipt-command", f"receipt-{index}", "--target", str(target)] for index in range(4)],
        ["start", "--target", str(target), "--task", "lane replay"],
        ["report", "--target", str(target)],
        ["reconcile", "--target", str(target)],
        ["session-log", "status", "--target", str(target)],
        ["config", "--target", str(target)],
    ]
    assert len(commands) == 14
    for argv in commands:
        assert session_logging.run_with_session_logging(argv, lambda _argv: print('{"status":"ok"}') or 0) == 0
    capsys.readouterr()

    state = session_logging.load_state_for_argv(["--target", str(target)])
    first = session_logging.analyze_session_log(state=state, detail="candidates")
    second = session_logging.analyze_session_log(state=state, detail="candidates")
    assert first["summary"]["command_count"] == 14
    assert first["summary"]["failure_count"] == 0
    assert first["summary"]["unknown_expectation_count"] == 0
    assert first["summary"]["matched_expectation_count"] == 14
    candidates = {item["id"]: item for item in first["detail_page"]["items"]}
    assert {"repeated-command", "duplicate-output", "receipt-choreography"} <= candidates.keys()
    assert candidates["receipt-choreography"]["improvement_signal"]["occurrence_count"] == 4
    assert candidates["receipt-choreography"]["improvement_signal"]["confidence"] == "high"
    first_fingerprints = {
        item["id"]: item["improvement_signal"]["evidence_fingerprint"]
        for item in first["detail_page"]["items"]
        if item.get("improvement_signal")
    }
    second_fingerprints = {
        item["id"]: item["improvement_signal"]["evidence_fingerprint"]
        for item in second["detail_page"]["items"]
        if item.get("improvement_signal")
    }
    assert first_fingerprints == second_fingerprints


def _run_logged_subprocess(target: Path, *, env: dict[str, str], return_code: int) -> subprocess.CompletedProcess[str]:
    child_env = dict(env)
    child_env["AW_TEST_RETURN_CODE"] = str(return_code)
    script = (
        "import os, sys\n"
        "from agentic_workspace import session_logging\n"
        "def runner(_argv):\n"
        "    return int(os.environ['AW_TEST_RETURN_CODE'])\n"
        "sys.exit(session_logging.run_with_session_logging(sys.argv[1:], runner))\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script, "config", "--target", str(target), "--format", "json"],
        cwd=Path.cwd(),
        env=child_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_pytest_subprocess_helper_combines_producer_and_generated_invocation_intent(tmp_path: Path) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    base_env = {key: value for key, value in os.environ.items() if not key.startswith("AW_SESSION_LOG_")}
    parent = {
        "parent_entry_id": "pytest-parent-entry",
        "parent_command": "pytest tests/test_workspace_session_logging.py",
        "parent_context": "test_pytest_subprocess_helper_declares_invocation_intent_without_inference",
    }

    assert _run_logged_subprocess(target, env=base_env, return_code=0).returncode == 0
    assert not (target / session_logging.SESSION_REGISTRY_PATH).exists()
    identified_env = {**base_env, session_logging.LOGICAL_SESSION_IDENTITY_ENV: "pytest-logical-session"}

    negative_env = aw_subprocess_env(
        purpose_id="proof-negative-path",
        scenario_id="invalid-selector",
        invocation_class="negative-fixture",
        expected_exit="failure",
        base_env=identified_env,
        **parent,
    )
    assert negative_env["AW_SESSION_LOG_CAPTURE_DETAIL"] == "1"
    assert _run_logged_subprocess(target, env=negative_env, return_code=2).returncode == 2

    product_env = aw_subprocess_env(
        purpose_id="ordinary-product-operation",
        scenario_id="status-success",
        invocation_class="product-operation",
        expected_exit="success",
        base_env=identified_env,
        **parent,
    )
    assert product_env["AW_SESSION_LOG_CAPTURE_DETAIL"] == "1"
    assert _run_logged_subprocess(target, env=product_env, return_code=0).returncode == 0

    failing_probe_env = aw_subprocess_env(
        purpose_id="probe-expected-success",
        scenario_id="probe-failed",
        invocation_class="probe",
        expected_exit="success",
        base_env=identified_env,
        **parent,
    )
    assert _run_logged_subprocess(target, env=failing_probe_env, return_code=2).returncode == 2

    unexpected_success_env = aw_subprocess_env(
        purpose_id="synthetic-expected-failure",
        scenario_id="synthetic-succeeded",
        invocation_class="synthetic-check",
        expected_exit="failure",
        base_env=identified_env,
        **parent,
    )
    assert _run_logged_subprocess(target, env=unexpected_success_env, return_code=0).returncode == 0

    undeclared_env = aw_subprocess_env(base_env=identified_env, **parent)
    assert _run_logged_subprocess(target, env=undeclared_env, return_code=0).returncode == 0

    state = session_logging.load_state_for_argv(["--target", str(target)])
    analysis = session_logging.analyze_session_log(state=state, origin_scope="all")
    assert analysis["summary"]["matched_expectation_count"] == 3
    assert analysis["summary"]["unmatched_expectation_count"] == 2
    assert analysis["summary"]["expected_success_failure_count"] == 1
    assert analysis["summary"]["expected_failure_success_count"] == 1
    assert analysis["summary"]["unknown_expectation_count"] == 0
    assert analysis["summary"]["unexpected_failure_count"] == 1
    entries = session_logging.analyze_session_log(state=state, origin_scope="all", detail="entries")["detail_page"]["items"]
    observed_nonzero = [entry for entry in entries if entry["exit_status"] != 0]
    failed_commands = [entry for entry in observed_nonzero if entry["invocation_outcome"].get("match") != "matched"]
    assert len(observed_nonzero) == 2
    assert len(failed_commands) == 1

    expected_success_failure = next(
        entry
        for entry in entries
        if entry["invocation_outcome"].get("match") == "unmatched" and entry["invocation_outcome"]["expected"]["exit_class"] == "success"
    )
    assert expected_success_failure["invocation_intent"]["scenario_id"] == "probe-failed"
    assert expected_success_failure["invocation_intent"]["invocation_class"] == "probe"
    assert expected_success_failure["invocation_outcome"]["expected"]["exit_class"] == "success"
    assert expected_success_failure["invocation_outcome"]["observed"]["exit_class"] == "failure"
    assert expected_success_failure["parent"]["entry_id"] == "pytest-parent-entry"
    assert expected_success_failure in failed_commands

    product_operation = [entry for entry in entries if entry["invocation_intent"]["scenario_id"] == "status-success"][0]
    assert product_operation["origin"]["classification"] == "pytest"
    assert product_operation["invocation_intent"]["invocation_class"] == "product-operation"
    assert product_operation["invocation_outcome"]["match"] == "matched"
    assert product_operation["parent"]["context"] == parent["parent_context"]

    expected_failure_success = next(
        entry
        for entry in entries
        if entry["invocation_outcome"].get("match") == "unmatched" and entry["invocation_outcome"]["expected"]["exit_class"] == "failure"
    )
    assert expected_failure_success["invocation_intent"]["scenario_id"] == "synthetic-succeeded"
    assert expected_failure_success["invocation_intent"]["invocation_class"] == "synthetic-check"
    assert expected_failure_success["invocation_outcome"]["expected"]["exit_class"] == "failure"
    assert expected_failure_success["invocation_outcome"]["observed"]["exit_class"] == "success"
    assert expected_failure_success not in failed_commands

    assert not [entry for entry in entries if entry["invocation_outcome"].get("match") in {None, "", "unknown"}]
    generated = [entry for entry in entries if entry["invocation_intent"]["operation_id"] == "config.report"][0]
    assert generated["invocation_intent"]["status"] == "declared"
    assert generated["invocation_intent"]["operation_id"] == "config.report"
    assert generated["invocation_outcome"]["match"] == "matched"


def test_session_log_reports_and_repairs_partial_index_without_losing_entries(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    def runner(argv: list[str]) -> int:
        print(json.dumps({"kind": "agentic-workspace/example/v1", "argv": argv}))
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--select", "one"], runner) == 0
    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--select", "two"], runner) == 0
    capsys.readouterr()
    index_path = _current_index(target)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    preserved = index["entries"][0]
    index["entries"] = [preserved]
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    state = session_logging.load_state_for_argv(["--target", str(target)])
    partial = session_logging.analyze_session_log(state=state)
    assert partial["index_status"] == "partial"
    assert partial["coverage"]["markdown_command_count"] == 2
    assert partial["coverage"]["indexed_command_count"] == 1
    stale_index = json.loads(index_path.read_text(encoding="utf-8"))
    ghost = {**preserved, "id": "cmd-not-in-markdown"}
    stale_index["entries"].append(ghost)
    stale_index["repair"] = {"status": "repaired"}
    index_path.write_text(json.dumps(stale_index, indent=2), encoding="utf-8")
    assert session_logging.analyze_session_log(state=state)["index_status"] == "stale"
    assert source_cli.main(["session-log", "--target", str(target), "repair", "--format", "json"]) == 0
    repaired = json.loads(capsys.readouterr().out)
    assert repaired["status"] == "repaired"
    assert repaired["added_entry_count"] == 1
    assert repaired["quarantined_entry_count"] == 1
    after = session_logging.analyze_session_log(state=state)
    assert after["index_status"] == "repaired"
    repaired_index = json.loads(index_path.read_text(encoding="utf-8"))
    assert repaired_index["entries"][0] == preserved
    assert repaired_index["entries"][0]["artifact"] == preserved["artifact"]
    assert not any(entry["id"] == "cmd-not-in-markdown" for entry in repaired_index["entries"])
    assert repaired_index["repair"]["quarantined_entry_ids"] == ["cmd-not-in-markdown"]
    assert [entry["id"] for entry in repaired_index["repair"]["quarantined_entries"]] == [ghost["id"]]
    assert session_logging.repair_session_log_index(state=state)["status"] == "already-covered"


def test_current_writer_reconciles_supported_partial_v1_index_before_append(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    def runner(argv: list[str]) -> int:
        print(json.dumps({"kind": "agentic-workspace/example/v1", "selector": argv[-1]}))
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--select", "one"], runner) == 0
    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--select", "two"], runner) == 0
    capsys.readouterr()
    index_path = _current_index(target)
    original = json.loads(index_path.read_text(encoding="utf-8"))
    first = session_logging._entries_from_index(original)[0]
    legacy_partial = {**original, "kind": "agentic-workspace/session-log-index/v1", "entries": original["entries"][:1]}
    index_path.write_text(json.dumps(legacy_partial, indent=2), encoding="utf-8")

    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--select", "three"], runner) == 0
    capsys.readouterr()

    state = session_logging.load_state_for_argv(["--target", str(target)])
    current = json.loads(index_path.read_text(encoding="utf-8"))
    indexed_entries = session_logging._entries_from_index(current)
    markdown_entries = session_logging._entries_from_markdown(target / current["log_path"])
    assert current["kind"] == session_logging.SESSION_LOG_INDEX_KIND
    assert [entry["id"] for entry in indexed_entries] == [entry["id"] for entry in markdown_entries]
    assert len(indexed_entries) == 3
    assert indexed_entries[0] == first
    assert session_logging.analyze_session_log(state=state)["index_status"] == "complete"


def test_session_log_segments_can_be_summarized_and_selected(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    assert (
        session_logging.run_with_session_logging(["start", "--target", str(target), "--task", "Implement issue #2144"], lambda _argv: 0)
        == 0
    )
    assert (
        session_logging.run_with_session_logging(["start", "--target", str(target), "--task", "Implement issue #2145"], lambda _argv: 0)
        == 0
    )
    assert (
        session_logging.run_with_session_logging(
            ["planning", "archive-plan", "--target", str(target), "example.plan.json"], lambda _argv: 0
        )
        == 0
    )
    state = session_logging.load_state_for_argv(["--target", str(target)])
    segments = session_logging.analyze_session_log(state=state, detail="segments")["detail_page"]["items"]
    assert len(segments) == 3
    assert {segment["task"] for segment in segments} == {"Implement issue #2144", "Implement issue #2145"}
    assert any(segment["closeout_status"] == "closed" for segment in segments)
    selected_id = segments[0]["id"]
    selected = session_logging.analyze_session_log(state=state, segment_id=selected_id)
    assert selected["selected_segment"] == selected_id
    assert selected["summary"]["command_count"] == 1


def test_context_record_identity_excludes_observation_time() -> None:
    first = {"kind": "agentic-workspace/current-work-context/v1", "freshness": {"resolved_at": "2026-01-01T00:00:00Z"}}
    second = {"kind": "agentic-workspace/current-work-context/v1", "freshness": {"resolved_at": "2026-01-01T00:00:03Z"}}

    assert session_logging._record_identity("context", first) == session_logging._record_identity("context", second)
    _, records = session_logging._normalized_index_entries([{"segment": {"work_context": first}}, {"segment": {"work_context": second}}])
    assert list(records["contexts"].values()) == [first]


def test_session_log_index_deduplicates_metadata_and_analysis_pages_episodes(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    monkeypatch.setenv("AW_SESSION_LOG_PURPOSE_ID", "implement-lane")
    monkeypatch.setenv("AW_SESSION_LOG_SCENARIO_ID", "focused-proof")
    monkeypatch.setenv("AW_SESSION_LOG_INVOCATION_CLASS", "product-operation")
    monkeypatch.setenv("AW_SESSION_LOG_EXPECTED_EXIT", "success")

    for _ in range(3):
        assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0

    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    assert len(index["entries"]) == 3
    assert len(index["records"]["provenance"]) == 1
    assert len(index["records"]["contexts"]) < len(index["entries"])
    assert len(index["records"]["segments"]) < len(index["entries"])
    assert len(index["records"]["invocation_intents"]) == 1
    assert all("provenance" not in entry and "segment" not in entry for entry in index["entries"])
    assert len({entry["segment_ref"] for entry in index["entries"]}) < len(index["entries"])
    hydrated = {**index, "records": {}, "entries": session_logging._entries_from_index(index)}
    assert len(json.dumps(index)) < len(json.dumps(hydrated))

    state = session_logging.load_state_for_argv(["--target", str(target)])
    summary = session_logging.analyze_session_log(state=state)
    episodes = session_logging.analyze_session_log(state=state, detail="episodes")["detail_page"]["items"]
    assert episodes[0]["purpose_id"] == "implement-lane"
    assert episodes[0]["scenario_id"] == "focused-proof"
    assert summary["detail"] == "summary"
    assert summary["detail_page"] is None
    page = session_logging.analyze_session_log(state=state, detail="entries", page=2, page_size=2)
    assert page["kind"] == "agentic-workspace/session-log-analysis-detail/v1"
    assert page["detail_page"]["total_count"] == 3
    assert page["detail_page"]["page"] == 2
    assert len(page["detail_page"]["items"]) == 1
    assert page["export_routing"]["artifact_class"] == "normalized-share-safe"
    assert page["full_analysis"]["status"] == "omitted"
    assert "failed_commands" not in page
    assert (
        source_cli.main(
            [
                "session-log",
                "--target",
                str(target),
                "analyze",
                "--detail",
                "episodes",
                "--page-size",
                "1",
                "--format",
                "json",
            ]
        )
        == 0
    )
    cli_page = json.loads(capsys.readouterr().out)
    assert cli_page["detail"] == "episodes"
    assert cli_page["detail_page"]["page_size"] == 1


def test_session_log_default_analysis_stays_bounded_for_long_multitask_session(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    for position in range(80):
        monkeypatch.setenv("AW_SESSION_LOG_PURPOSE_ID", f"lane-{position % 8}")
        monkeypatch.setenv("AW_SESSION_LOG_SCENARIO_ID", f"branch-{position % 12}")
        assert (
            session_logging.run_with_session_logging(["status", "--target", str(target), "--select", f"agent-{position}"], lambda _argv: 0)
            == 0
        )

    brief_calls = 0
    real_entry_brief = session_logging._entry_brief

    def counted_entry_brief(entry: dict[str, object]) -> dict[str, object]:
        nonlocal brief_calls
        brief_calls += 1
        return real_entry_brief(entry)

    monkeypatch.setattr(session_logging, "_entry_brief", counted_entry_brief)
    payload = session_logging.analyze_session_log(state=session_logging.load_state_for_argv(["--target", str(target)]))
    default_brief_calls = brief_calls
    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    hydrated_entries = session_logging._entries_from_index(index)
    hydrated_index = {**index, "records": {}, "entries": hydrated_entries}
    assert payload["summary"]["command_count"] == 80
    assert len(index["records"]["provenance"]) < len(index["entries"])
    assert len(index["records"]["contexts"]) < len(index["entries"])
    assert len(json.dumps(index).encode("utf-8")) < len(json.dumps(hydrated_index).encode("utf-8"))
    assert "segments" not in payload
    assert "episodes" not in payload
    assert "friction_candidates" not in payload
    assert payload["bounded_collections"]["full_detail_requires_selector"] is True
    assert default_brief_calls <= 1
    assert len(json.dumps(payload).encode("utf-8")) < 16_384
    assert len(json.dumps(payload).encode("utf-8")) <= session_logging.DEFAULT_ANALYSIS_SERIALIZATION_BUDGET_BYTES
    reconstructed = []
    state = session_logging.load_state_for_argv(["--target", str(target)])
    for page in range(1, 5):
        detail = session_logging.analyze_session_log(state=state, detail="entries", page=page, page_size=25)
        reconstructed.extend(detail["detail_page"]["items"])
    assert [item["id"] for item in reconstructed] == [item["id"] for item in hydrated_entries]


def test_session_index_cannot_satisfy_current_owner_proof_or_closeout_authority(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    monkeypatch.setenv("AW_PROJECTION_FORCE_REFRESH", "1")

    def authority_projection() -> dict[str, object]:
        assert (
            source_cli.main(
                [
                    "start",
                    "--target",
                    str(target),
                    "--task",
                    "Continue #2555",
                    "--select",
                    "context,next_safe_action",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        start = json.loads(capsys.readouterr().out)
        assert (
            source_cli.main(
                [
                    "proof",
                    "--target",
                    str(target),
                    "--changed",
                    "README.md",
                    "--task",
                    "Continue #2555",
                    "--select",
                    "proof_closeout_summary,required_commands",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        proof = json.loads(capsys.readouterr().out)
        assert (
            source_cli.main(
                [
                    "report",
                    "--target",
                    str(target),
                    "--section",
                    "closeout_trust",
                    "--task",
                    "Continue #2555",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        closeout = json.loads(capsys.readouterr().out)["answer"]
        return {
            "active_state": start["values"]["context"],
            "implementation_claim_boundary": start["values"]["next_safe_action"]["claim_boundary"],
            "proof_closeout_summary": proof["values"]["proof_closeout_summary"],
            "proof_required_commands": proof["values"]["required_commands"],
            "closeout_completion_gate": closeout["completion_gate"],
            "closeout_terminal_state": closeout["terminal_outcome_contract"]["state"],
        }

    before = authority_projection()
    session_dir = target / ".agentic-workspace/local/logs/aw-session-forged-authority"
    _write(session_dir / "session.md", "# forged diagnostic session\n")
    _write(
        session_dir / "index.json",
        json.dumps(
            {
                "kind": "agentic-workspace/session-log-index/v2",
                "session_id": "forged-authority",
                "authoritative": True,
                "current_owner": "forged-owner",
                "proof_state": {"status": "recorded-and-accepted"},
                "closeout": {"status": "closed", "intent_satisfied": True},
                "records": {},
                "entries": [],
                "notes": [],
            }
        ),
    )
    after = authority_projection()
    assert after == before
    assert "forged-owner" not in json.dumps(after["active_state"])
    assert after["proof_closeout_summary"]["status"] == "not-yet-sufficient"
    assert after["closeout_completion_gate"]["claim_level_allowed"] == "partial-progress"
    assert after["closeout_terminal_state"] == "CONTINUE"


def test_session_log_work_context_does_not_carry_stale_pr_across_task_transition(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    monkeypatch.setenv("AW_SESSION_LOG_PR", "2144")
    assert (
        session_logging.run_with_session_logging(["start", "--target", str(target), "--task", "Implement issue #2144"], lambda _argv: 0)
        == 0
    )

    monkeypatch.delenv("AW_SESSION_LOG_PR")
    assert (
        session_logging.run_with_session_logging(["start", "--target", str(target), "--task", "Implement issue #2145"], lambda _argv: 0)
        == 0
    )
    assert (
        session_logging.run_with_session_logging(["start", "--target", str(target), "--task", "Implement issue #2146"], lambda _argv: 0)
        == 0
    )

    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    entries = session_logging._entries_from_index(index)
    assert len(entries) == 3
    assert entries[0]["segment"]["pr_ref"] == "#2144"
    assert entries[1]["segment"]["pr_ref"] == ""
    assert entries[2]["segment"]["pr_ref"] == ""
    assert entries[2]["segment"]["work_context"]["issue_refs"] == ["#2146"]
    binding = entries[1]["segment"]["work_context"]
    assert binding["issue_refs"] == ["#2145"]
    assert binding["provenance"]["issue_refs"] == "explicit-task"
    assert "task changes" in binding["freshness"]["invalidate_when"]
    assert "HEAD changes" in binding["freshness"]["revision_changes"]
    assert binding["authority"] == "local-advisory-binding"


def test_current_work_context_branch_round_trip_rebinds_thread_identity(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    for branch, issue, pr in (
        ("branch-a", "#2175", "#2182"),
        ("branch-b", "#2180", "#2183"),
        ("branch-c", "#2177", "#2184"),
    ):
        _write(
            target / ".agentic-workspace" / "local" / "work-threads" / f"{branch}.json",
            json.dumps(
                {
                    "kind": "agentic-workspace/local-work-thread/v1",
                    "id": branch,
                    "refs": {"issues": [issue], "prs": [pr], "planning": []},
                    "observations": {"branch": {"value": branch}},
                }
            ),
        )
    live = {"branch": "branch-a"}
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: live["branch"] if args == ("branch", "--show-current") else f"head-{live['branch']}",
    )

    first = current_work_context.resolve_current_work_context(root=target)
    live["branch"] = "branch-b"
    second = current_work_context.resolve_current_work_context(root=target)
    live["branch"] = "branch-a"
    returned = current_work_context.resolve_current_work_context(root=target)

    assert (first["thread_id"], first["pr_ref"], first["issue_refs"]) == ("branch-a", "#2182", ["#2175"])
    assert (second["thread_id"], second["pr_ref"], second["issue_refs"]) == ("branch-b", "#2183", ["#2180"])
    assert returned["thread_id"] == "branch-a"
    assert returned["id"] == first["id"]


def test_current_work_context_same_branch_task_transition_drops_incompatible_thread_pr(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace/local/work-threads/current.json",
        json.dumps(
            {
                "id": "task-a",
                "refs": {"issues": ["#2175"], "prs": ["#2182"]},
                "observations": {"branch": {"value": "main"}, "head": {"value": "head-a"}},
            }
        ),
    )
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else "head-a",
    )

    task_a = current_work_context.resolve_current_work_context(root=target, task="Implement #2175")
    task_b = current_work_context.resolve_current_work_context(root=target, task="Implement #2180")

    assert task_a["pr_ref"] == "#2182"
    assert task_b["issue_refs"] == ["#2180"]
    assert task_b["pr_ref"] == ""
    assert task_b["status"] == "ambiguous"
    assert task_b["conflicts"] == ["task-thread-issue-conflict"]


def test_current_work_context_selected_thread_disambiguates_branch_matches(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    for thread_id, issue, pr in (("alpha", "#2175", "#2182"), ("beta", "#2180", "#2183")):
        _write(
            target / ".agentic-workspace/local/work-threads" / f"{thread_id}.json",
            json.dumps(
                {
                    "id": thread_id,
                    "refs": {"issues": [issue], "prs": [pr]},
                    "observations": {"branch": {"value": "main"}},
                }
            ),
        )
    _write(target / ".agentic-workspace/local/work-threads/index.json", json.dumps({"selected_thread_id": "beta"}))
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else "head-a",
    )

    binding = current_work_context.resolve_current_work_context(root=target)

    assert binding["status"] == "bound"
    assert binding["selected_thread_id"] == "beta"
    assert binding["thread_id"] == "beta"
    assert binding["issue_refs"] == ["#2180"]
    assert binding["pr_refs"] == ["#2183"]


def test_current_work_context_stale_thread_does_not_bind(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace/local/work-threads/stale.json",
        json.dumps(
            {
                "id": "stale",
                "status": "stale",
                "refs": {"issues": ["#2175"], "prs": ["#2182"]},
                "observations": {"branch": {"value": "main"}, "head": {"value": "old-head"}},
            }
        ),
    )
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else "new-head",
    )

    binding = current_work_context.resolve_current_work_context(root=target)

    assert binding["status"] == "ambiguous"
    assert binding["issue_refs"] == []
    assert binding["pr_ref"] == ""
    assert binding["thread_id"] == ""
    assert "thread-stale" in binding["conflicts"]


def test_current_work_context_explicit_pr_task_binds_pr_without_inventing_issue(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else "new-head",
    )

    binding = current_work_context.resolve_current_work_context(root=target, task="Review PR #2182")

    assert binding["issue_refs"] == []
    assert binding["pr_refs"] == ["#2182"]
    assert binding["pr_ref"] == "#2182"
    assert binding["provenance"]["pr_ref"] == "explicit-task"


def test_current_work_context_explicit_pr_stack_preserves_ordered_refs(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "review-stack" if args == ("branch", "--show-current") else "stack-head",
    )

    binding = current_work_context.resolve_current_work_context(root=target, task="Review PR #2203, PR #2204, and pull request #2206")

    assert binding["issue_refs"] == []
    assert binding["pr_refs"] == ["#2203", "#2204", "#2206"]
    assert binding["pr_ref"] == "#2203"
    assert binding["provenance"]["pr_refs"] == "explicit-task"


@pytest.mark.parametrize("task", ["Branch-sync #2474 into this branch", "Sync branch #2474 before continuing"])
def test_current_work_context_branch_sync_binds_pr_without_inventing_issue(tmp_path: Path, monkeypatch, task: str) -> None:
    target = _target(tmp_path)
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "repair-branch" if args == ("branch", "--show-current") else "repair-head",
    )

    binding = current_work_context.resolve_current_work_context(root=target, task=task)

    assert binding["issue_refs"] == []
    assert binding["pr_refs"] == ["#2474"]
    assert binding["provenance"]["pr_refs"] == "explicit-task"


@pytest.mark.parametrize(
    ("task", "issue_refs", "pr_refs"),
    [
        ("Review issue #123", ["#123"], []),
        ("Sync branch #2474 for issue #2481", ["#2481"], ["#2474"]),
        ("Review PR #2203 for issue #2204", ["#2204"], ["#2203"]),
    ],
)
def test_current_work_context_classifies_each_task_reference(
    tmp_path: Path,
    monkeypatch,
    task: str,
    issue_refs: list[str],
    pr_refs: list[str],
) -> None:
    target = _target(tmp_path)
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "mixed-refs" if args == ("branch", "--show-current") else "mixed-head",
    )

    binding = current_work_context.resolve_current_work_context(root=target, task=task)

    assert binding["issue_refs"] == issue_refs
    assert binding["pr_refs"] == pr_refs


def test_current_work_context_head_advance_does_not_alone_stale_active_thread(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace/local/work-threads/active.json",
        json.dumps(
            {
                "id": "active",
                "status": "active",
                "refs": {"issues": ["#2175"], "prs": ["#2182"]},
                "observations": {"branch": {"value": "main"}, "head": {"value": "old-head"}},
            }
        ),
    )
    live = {"head": "new-head"}
    monkeypatch.setattr(current_work_context, "_git", lambda _root, *args: "main" if args == ("branch", "--show-current") else live["head"])

    binding = current_work_context.resolve_current_work_context(root=target)
    first_id = binding["id"]
    live["head"] = "newer-head"
    advanced = current_work_context.resolve_current_work_context(root=target)

    assert binding["status"] == "bound"
    assert binding["thread_id"] == "active"
    assert binding["pr_ref"] == "#2182"
    assert binding["revision"]["head"] == "new-head"
    assert advanced["revision"]["head"] == "newer-head"
    assert advanced["id"] == first_id


def test_current_work_owner_binding_classifies_adoption_read_only_unrelated_transition_and_ambiguity(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace/planning/state.toml",
        'schema_version = 1\n[todo]\nactive_items = [{ id = "issue-2258", surface = ".agentic-workspace/planning/execplans/issue-2258.plan.json", refs = ["GitHub #2258"] }]\n',
    )
    _write(
        target / ".agentic-workspace/planning/execplans/issue-2258.plan.json",
        json.dumps({"kind": "planning-execplan/v1", "parent": {"owner_id": "issue-2279"}, "references": []}),
    )
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else "head-a",
    )

    cases = {
        ("Continue #2258", ""): ("plan-continuation", True, "issue-2258"),
        ("Execute the active child under #2279", ""): ("plan-continuation", True, "issue-2258"),
        ("Tighten #2258", "plan-mutation"): ("plan-mutation", True, "issue-2258"),
        ("Review #3100", "read-only"): ("read-only", False, ""),
        ("Implement #3100", ""): ("unrelated-bounded", False, ""),
        ("Switch branch then continue #2258", "provisional-transition"): ("provisional-transition", False, ""),
        ("Adopt the selected owner", ""): ("unrelated-bounded", False, ""),
    }
    for (task, relation_hint), expected in cases.items():
        binding = current_work_context.resolve_current_work_context(root=target, task=task, relation_hint=relation_hint)
        owner = binding["owner_binding"]
        assert (owner["relation"], owner["carry_eligible"], binding["plan_id"]) == expected


def test_current_work_owner_binding_counts_candidate_owners_not_matching_refs(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    owner_ref = ".agentic-workspace/planning/execplans/issue-2258.plan.json"
    _write(
        target / ".agentic-workspace/planning/state.toml",
        (f'schema_version = 1\n[todo]\nactive_items = [{{ id = "issue-2258", refs = ["#2258", "#2279"], surface = "{owner_ref}" }}]\n'),
    )
    _write(
        target / owner_ref,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "issue-2258",
                "lifecycle": "live",
                "phase": "implementation",
                "parent": {"owner_id": "issue-2279"},
                "references": [{"kind": "issue", "target": "#2258"}, {"kind": "issue", "target": "#2279"}],
            }
        ),
    )
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else "head-a",
    )

    binding = current_work_context.resolve_current_work_context(
        root=target,
        task="Continue child #2258 under parent #2279",
    )

    assert binding["status"] == "bound"
    assert binding["plan_id"] == "issue-2258"
    assert binding["owner_binding"]["relation"] == "plan-continuation"
    assert binding["owner_binding"]["carry_eligible"] is True


def test_local_owner_selection_drives_planning_queries_current_work_and_cache_identity(tmp_path: Path, monkeypatch) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    target = _target(tmp_path)
    planning_installer.install_bootstrap(target=target)
    for owner_id, activate in (("owner-a", True), ("owner-b", False), ("owner-c", False)):
        result = planning_installer.create_execplan_scaffold(
            plan_id=owner_id,
            title=owner_id.upper(),
            target=target,
            activate=activate,
        )
        assert not [action for action in result.actions if action.kind == "manual review"]
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else "head-a",
    )
    planning_installer._PLANNING_SELECTED_OWNER_CACHE.clear()

    planning_installer.select_existing_owner("owner-b", target=target, current_work_id="review-thread")
    owner_b_query = planning_installer.planning_summary_query(target=target, selectors=["planning_record"])
    owner_b_summary = planning_installer.planning_summary(target=target, profile="tiny")
    owner_b_binding = current_work_context.resolve_current_work_context(
        root=target,
        task="Continue selected work",
        relation_hint="plan-continuation",
    )
    owner_b_revision = planning_installer.planning_revision(target)

    planning_installer.select_existing_owner(
        "owner-c",
        target=target,
        current_work_id="review-thread",
        expected_planning_revision=owner_b_revision["revision_id"],
    )
    owner_c_query = planning_installer.planning_summary_query(target=target, selectors=["planning_record"])
    owner_c_summary = planning_installer.planning_summary(target=target, profile="tiny")
    owner_c_binding = current_work_context.resolve_current_work_context(
        root=target,
        task="Continue selected work",
        relation_hint="plan-continuation",
    )
    owner_c_revision = planning_installer.planning_revision(target)

    assert owner_b_query["payload"]["planning_record"]["task"]["id"] == "owner-b"
    assert owner_b_summary["todo"]["active_items"][0]["id"] == "owner-b"
    assert owner_b_binding["plan_id"] == "owner-b"
    assert owner_c_query["payload"]["planning_record"]["task"]["id"] == "owner-c"
    assert owner_c_summary["todo"]["active_items"][0]["id"] == "owner-c"
    assert owner_c_binding["plan_id"] == "owner-c"
    assert owner_c_query["query_diagnostics"]["cache"]["status"] == "miss"
    assert owner_b_revision["revision_id"] != owner_c_revision["revision_id"]
    assert owner_b_revision["selection_hash"] != owner_c_revision["selection_hash"]


def test_current_work_owner_identity_deduplicates_wording_and_head_revision(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace/planning/state.toml",
        'schema_version = 1\n[todo]\nactive_items = [{ id = "issue-2258", refs = ["#2258"] }]\n',
    )
    live = {"head": "head-a"}
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else live["head"],
    )

    first = current_work_context.resolve_current_work_context(root=target, task="Continue #2258")
    live["head"] = "head-b"
    reworded = current_work_context.resolve_current_work_context(root=target, task="Resume implementation of #2258")

    assert first["id"] == reworded["id"]
    assert first["revision"]["head"] != reworded["revision"]["head"]


def test_current_work_owner_identity_invalidates_on_branch_target_and_selected_owner(tmp_path: Path, monkeypatch) -> None:
    first_target = _target(tmp_path / "first")
    second_target = _target(tmp_path / "second")
    for target in (first_target, second_target):
        _write(
            target / ".agentic-workspace/planning/state.toml",
            'schema_version = 1\n[todo]\nactive_items = [{ id = "issue-2258", refs = ["#2258"] }]\n',
        )
    live = {"branch": "main", "head": "head-a"}
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: live["branch"] if args == ("branch", "--show-current") else live["head"],
    )

    first = current_work_context.resolve_current_work_context(root=first_target, task="Continue #2258")
    live["branch"] = "other"
    branch_changed = current_work_context.resolve_current_work_context(root=first_target, task="Continue #2258")
    target_changed = current_work_context.resolve_current_work_context(root=second_target, task="Continue #2258")
    _write(
        first_target / ".agentic-workspace/planning/state.toml",
        'schema_version = 1\n[todo]\nactive_items = [{ id = "issue-3100", refs = ["#3100"] }]\n',
    )
    owner_changed = current_work_context.resolve_current_work_context(root=first_target, task="Continue #3100")

    assert first["id"] != branch_changed["id"]
    assert branch_changed["id"] != target_changed["id"]
    assert branch_changed["id"] != owner_changed["id"]


def test_current_work_binding_fails_closed_for_multiple_live_owners_and_consumes_supported_selection(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    owner_a = ".agentic-workspace/planning/execplans/issue-2258.plan.json"
    owner_b = ".agentic-workspace/planning/execplans/issue-3100.plan.json"
    _write(
        target / ".agentic-workspace/planning/state.toml",
        (
            "schema_version = 1\n[todo]\nactive_items = ["
            f'{{ id = "issue-2258", refs = ["#2258"], surface = "{owner_a}" }}, '
            f'{{ id = "issue-3100", refs = ["#3100"], surface = "{owner_b}" }}'
            "]\n"
        ),
    )
    for owner_id, owner_ref in (("issue-2258", owner_a), ("issue-3100", owner_b)):
        _write(
            target / owner_ref,
            json.dumps(
                {
                    "kind": "planning-execplan/v1",
                    "id": owner_id,
                    "lifecycle": "live",
                    "phase": "implementation",
                    "references": [],
                }
            ),
        )
    monkeypatch.setattr(
        current_work_context,
        "_git",
        lambda _root, *args: "main" if args == ("branch", "--show-current") else "head-a",
    )

    ambiguous = current_work_context.resolve_current_work_context(root=target, task="Continue active work")
    exact = current_work_context.resolve_current_work_context(root=target, task="Continue #3100")
    _write(
        target / ".agentic-workspace/local/planning/owner-selection.json",
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "default",
                "selected_owner": {"id": "issue-3100", "ref": owner_b},
            }
        ),
    )
    unadopted = current_work_context.resolve_current_work_context(root=target, task="Continue the selected owner")
    selected = current_work_context.resolve_current_work_context(
        root=target,
        task="Continue the selected owner",
        relation_hint="plan-continuation",
    )

    assert ambiguous["status"] == "ambiguous"
    assert ambiguous["plan_id"] == ""
    assert exact["status"] == "bound"
    assert exact["plan_id"] == "issue-3100"
    assert unadopted["plan_id"] == ""
    assert unadopted["selected_plan_id"] == "issue-3100"
    assert unadopted["owner_binding"]["relation"] == "unrelated-bounded"
    assert unadopted["owner_binding"]["carry_eligible"] is False
    assert selected["status"] == "bound"
    assert selected["plan_id"] == "issue-3100"
    assert selected["owner_binding"]["relation"] == "plan-continuation"
    assert selected["provenance"]["plan_id"] == ".agentic-workspace/local/planning/owner-selection.json"


def test_session_log_segments_ignore_closeout_text_without_a_closeout_transition(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    commands = [
        ["report", "--target", str(target), "--section", "closeout_report"],
        ["skills", "--target", str(target), "--task", "closeout review"],
        ["planning", "closeout", "--target", str(target), "--dry-run"],
    ]
    for command in commands:
        assert session_logging.run_with_session_logging(command, lambda _argv: 0) == 0

    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    assert [entry["segment"]["closeout_status"] for entry in session_logging._entries_from_index(index)] == ["open", "open", "open"]


def test_session_log_provenance_and_kind_classes_are_recorded(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    def runner(_argv: list[str]) -> int:
        print(
            json.dumps(
                {
                    "kind": "agentic-workspace/top/v1",
                    "actions": [{"kind": "created"}],
                    "packet": {"kind": "agentic-workspace/nested/v2"},
                }
            )
        )
        return 0

    assert session_logging.run_with_session_logging(["summary", "--target", str(target)], runner) == 0
    index = json.loads(_current_index(target).read_text(encoding="utf-8"))
    entry = session_logging._entries_from_index(index)[0]
    assert entry["provenance"]["aw_version"]
    assert isinstance(entry["provenance"]["dirty"], bool)
    assert entry["duration_ms"] >= 0
    assert entry["top_level_kinds"] == ["agentic-workspace/top/v1"]
    assert entry["packet_kinds"] == ["agentic-workspace/nested/v2", "agentic-workspace/top/v1"]
    assert entry["domain_kinds"] == ["created"]
    payload = session_logging.analyze_session_log(state=session_logging.load_state_for_argv(["--target", str(target)]))
    assert payload["top_level_kinds"] == {"agentic-workspace/top/v1": 1}
    assert payload["domain_kinds"] == {"created": 1}
    assert "created" not in payload["packet_kinds"]


def test_session_log_slow_commands_surface_proof_route_friction(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")
    real_monotonic = session_logging.time.monotonic
    monotonic_values = iter([0.0, 125.0, 126.0, 126.1])
    monkeypatch.setattr(session_logging.time, "monotonic", lambda: next(monotonic_values))

    assert session_logging.run_with_session_logging(["make", "test-workspace", "--target", str(target)], lambda _argv: 0) == 0
    monkeypatch.setattr(session_logging.time, "monotonic", real_monotonic)
    capsys.readouterr()

    payload = session_logging.analyze_session_log(state=session_logging.load_state_for_argv(["--target", str(target)]), detail="candidates")
    slow = next(candidate for candidate in payload["detail_page"]["items"] if candidate["id"].startswith("slow-command:"))
    assert slow["owner"] == "proof-route-maintenance"
    assert slow["duration_ms"] == 125000
    assert slow["duration_ms_max"] == 125000
    assert slow["duration_ms_total"] == 125000
    assert slow["occurrence_count"] == 1
    assert slow["recurrence"] == "single-observation"
    assert slow["normalized_command_class"] == "validation-command"
    assert slow["route_identity"].startswith("proof-route-friction:")
    assert slow["treatment"] == "prefer focused proof; require structured escalation before promoting broad/high-cost proof"
    assert slow["lifecycle_status"] == "candidate-local-observation"
    assert slow["improvement_signal"]["kind"] == "validation_friction"
    assert slow["improvement_signal"]["state"] == "active"
    assert slow["improvement_signal"]["applicable_to_current_route"] is True
    assert slow["improvement_signal"]["applicable_live"] is False
    assert slow["improvement_signal"]["recurrence"] == "first_seen"
    assert slow["improvement_signal"]["evidence_classes"] == ["machine_observed"]
    assert slow["improvement_signal"]["expected_benefit"]
    assert slow["improvement_signal"]["mutation_authorized"] is False


def test_session_log_repeated_slow_commands_surface_recurring_proof_friction() -> None:
    slow = session_logging._slow_command_friction_candidates(
        [
            {
                "id": "cmd-1",
                "command": "agentic-workspace make test-workspace",
                "duration_ms": 125000,
                "started_at": "2026-07-16T10:00:00+00:00",
            },
            {
                "id": "cmd-2",
                "command": "agentic-workspace make test-workspace",
                "duration_ms": 130000,
                "started_at": "2026-07-16T10:10:00+00:00",
            },
        ]
    )[0]
    assert slow["occurrence_count"] == 2
    assert slow["recurrence"] == "recurring"
    assert slow["duration_ms_max"] == 130000
    assert slow["duration_ms_total"] == 255000
    assert slow["severity"] == "protective-action"
    assert slow["lifecycle_status"] == "live-applicable"
    assert slow["improvement_signal"]["applicable_live"] is True
    assert slow["improvement_signal"]["recurrence"] == "repeated"
    assert slow["improvement_signal"]["immediate_action"] == "route"
    assert len(slow["evidence_refs"]) == 2


def test_session_log_single_very_slow_command_remains_candidate_without_host_impact() -> None:
    slow = session_logging._slow_command_friction_candidates(
        [
            {
                "id": "cmd-1",
                "command": "make test-workspace",
                "duration_ms": session_logging.DEFAULT_SLOW_COMMAND_DURATION_MS * 5,
                "started_at": "2026-07-16T10:00:00+00:00",
            }
        ]
    )[0]
    assert slow["recurrence"] == "single-observation"
    assert slow["severity"] == "attention"
    assert slow["lifecycle_status"] == "candidate-local-observation"
    assert slow["improvement_signal"]["applicable_live"] is False
    assert slow["improvement_signal"]["recurrence"] == "first_seen"


def test_session_log_single_severe_host_impact_validation_command_is_live_applicable() -> None:
    slow = session_logging._slow_command_friction_candidates(
        [
            {
                "id": "cmd-1",
                "command": "make test-workspace",
                "duration_ms": 125000,
                "host_impact_class": "severe-host-impact",
                "started_at": "2026-07-16T10:00:00+00:00",
            }
        ]
    )[0]
    assert slow["recurrence"] == "single-observation"
    assert slow["host_impact_class"] == "severe-host-impact"
    assert slow["severity"] == "protective-action"
    assert slow["lifecycle_status"] == "live-applicable"
    assert slow["improvement_signal"]["applicable_live"] is True
    assert slow["improvement_signal"]["host_impact_class"] == "severe-host-impact"


def test_session_log_grouped_slow_command_applicability_uses_each_group_class() -> None:
    candidates = session_logging._slow_command_friction_candidates(
        [
            {
                "id": "validation-1",
                "command": "make test-workspace",
                "duration_ms": 125000,
                "started_at": "2026-07-16T10:00:00+00:00",
            },
            {
                "id": "validation-2",
                "command": "make test-workspace",
                "duration_ms": 130000,
                "started_at": "2026-07-16T10:10:00+00:00",
            },
            {
                "id": "docs-1",
                "command": "python scripts/render_docs.py",
                "duration_ms": 124000,
                "started_at": "2026-07-16T10:20:00+00:00",
            },
        ]
    )

    by_command = {candidate["command"]: candidate for candidate in candidates}
    validation = by_command["make test-workspace"]
    docs = by_command["python scripts/render_docs.py"]
    assert validation["normalized_command_class"] == "validation-command"
    assert validation["improvement_signal"]["applicability"] == "applicable-to-proof-route-maintenance"
    assert validation["improvement_signal"]["applicable_to_current_route"] is True
    assert docs["normalized_command_class"] == "command"
    assert docs["improvement_signal"]["applicability"] == "review-before-use"
    assert docs["improvement_signal"]["applicable_to_current_route"] is False


def test_session_log_classifies_structured_runtime_exception() -> None:
    capture = session_logging.CommandCapture(
        stdout=json.dumps(
            {
                "kind": "agentic-workspace/runtime-error/v1",
                "failure_class": "unexpected-runtime-exception",
            }
        ),
        stderr="",
        exit_code=1,
    )
    assert session_logging._failure_class(command_text="summary --format json", capture=capture) == "unexpected-runtime-exception"


def test_session_log_export_normalizes_local_paths_and_preserves_originals(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    def runner(_argv: list[str]) -> int:
        print(json.dumps({"kind": "agentic-workspace/path/v1", "target": str(target), "home": str(Path.home()), "python": sys.executable}))
        return 0

    assert session_logging.run_with_session_logging(["config", "--target", str(target)], runner) == 0
    capsys.readouterr()
    log_path = _current_log(target)
    index_path = _current_index(target)
    event_path = _current_events(target)
    original_log = log_path.read_bytes()
    original_index = index_path.read_bytes()
    original_events = event_path.read_bytes()
    state = session_logging.load_state_for_argv(["--target", str(target)])
    status = session_logging.status_payload(state=state)
    analysis = session_logging.analyze_session_log(state=state)
    assert status["session_scope"]["kind"] == "distinct-logical-session"
    assert status["session_scope"]["current_logical_session"] is True
    assert analysis["status"] == "analyzed"
    assert analysis["session_scope"]["kind"] == "distinct-logical-session"
    assert source_cli.main(["session-log", "--target", str(target), "export", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "exported"
    assert payload["session_scope"]["kind"] == "distinct-logical-session"
    export_path = target / payload["path"]
    assert export_path.name.endswith(".jsonl.gz")
    events = _read_export(export_path)
    combined = "\n".join(json.dumps(event, sort_keys=True) for event in events)
    assert str(target) not in combined
    assert target.as_posix() not in combined
    assert str(Path.home()) not in combined
    assert sys.executable not in combined
    assert "<target>" in combined
    assert "normalized-share-safe" in combined
    assert "promotion_boundary" not in combined
    assert "share_safe" not in combined
    assert events[0]["event_type"] == "export.manifest"
    manifest = events[0]["payload"]
    assert manifest["artifact_class"] == "normalized-share-safe-jsonl"
    assert manifest["source_artifact_class"] == "raw-local-diagnostic"
    assert manifest["originals_mutated"] is False
    assert manifest["path_normalization_mode"] == "known-local-paths"
    assert "transfer approval" in manifest["limitations"]
    assert manifest["transfer_review"]["status"] == "required"
    assert manifest["transfer_review"]["approval"] == "not-granted"
    assert manifest["evidence_profile"]["id"] == "complete-logical-session-with-output-chunks"
    assert manifest["evidence_profile"]["source_command_count"] == 1
    assert manifest["evidence_profile"]["exported_command_count"] == 1
    assert manifest["evidence_profile"]["canonical_event_stream_complete"] is True
    assert manifest["evidence_profile"]["command_selection"] == "all-logical-session-tree-commands"
    assert manifest["artifact_coverage"][0]["status"] == "included-as-output-chunks"
    assert any(event["event_type"] == "output.chunk" for event in events)
    assert [event["sequence"] for event in events] == list(range(len(events)))
    assert "Share this generated archive" not in combined
    assert manifest["local_diagnostic_boundary"]["manual_handoff"] == "outside-aw-logger-responsibility"
    assert payload["transfer_approval"] == "not-granted"
    assert "Share path" not in json.dumps(payload)
    assert log_path.read_bytes() == original_log
    assert index_path.read_bytes() == original_index
    assert event_path.read_bytes() == original_events

    assert (
        source_cli.main(
            ["session-log", "--target", str(target), "export", "--id", status["session_id"], "--no-artifacts", "--format", "json"]
        )
        == 0
    )
    by_id = json.loads(capsys.readouterr().out)
    assert by_id["artifact_count"] == 0
    assert by_id["session_scope"]["kind"] == "explicit-artifact"
    assert by_id["session_scope"]["current_logical_session"] is False
    assert by_id["manifest"]["evidence_profile"]["id"] == "complete-logical-session-summary"
    assert by_id["manifest"]["artifact_coverage"][0]["status"] == "digest-only"
    assert source_cli.main(["session-log", "--target", str(target), "export", "--path", status["path"], "--format", "json"]) == 0
    by_path = json.loads(capsys.readouterr().out)
    assert by_path["source_log_path"] == status["path"]
    assert by_path["session_scope"]["kind"] == "explicit-artifact"
    assert log_path.read_bytes() == original_log
    assert index_path.read_bytes() == original_index


def test_session_log_export_repairs_partial_source_index_in_export_only(tmp_path: Path, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_ORIGIN", "agent")

    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--select", "one"], lambda _argv: 0) == 0
    assert session_logging.run_with_session_logging(["config", "--target", str(target), "--select", "two"], lambda _argv: 0) == 0
    index_path = _current_index(target)
    original = json.loads(index_path.read_text(encoding="utf-8"))
    partial = {**original, "entries": original["entries"][:1]}
    index_path.write_text(json.dumps(partial, indent=2), encoding="utf-8")

    state = session_logging.load_state_for_argv(["--target", str(target)])
    exported = session_logging.export_session_log(state=state, include_artifacts=False)

    assert exported["manifest"]["evidence_profile"]["source_command_count"] == 2
    assert exported["manifest"]["evidence_profile"]["exported_command_count"] == 2
    assert exported["manifest"]["evidence_profile"]["canonical_event_stream_complete"] is True
    events = _read_export(target / exported["path"])
    assert sum(event["event_type"] == "command.completed" for event in events) == 2
    assert json.loads(index_path.read_text(encoding="utf-8")) == partial
