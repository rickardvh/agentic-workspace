from __future__ import annotations

import json
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from agentic_workspace import cli as source_cli
from agentic_workspace import session_logging


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _target(tmp_path: Path) -> Path:
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n")
    (tmp_path / ".git").mkdir()
    return tmp_path


def _current_log(target: Path) -> Path:
    pointer = json.loads((target / ".agentic-workspace/local/session-logging/current.json").read_text(encoding="utf-8"))
    return target / pointer["log_path"]


def _current_index(target: Path) -> Path:
    pointer = json.loads((target / ".agentic-workspace/local/session-logging/current.json").read_text(encoding="utf-8"))
    return target / Path(pointer["log_path"]).parent / "index.json"


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
    assert index["kind"] == "agentic-workspace/session-log-index/v1"
    assert len(index["entries"]) == 2
    assert index["entries"][0]["stdout"]["kind"] == "json"
    assert index["entries"][0]["artifact"]["path"].startswith(str(first_log.parent.relative_to(target)).replace("\\", "/") + "/artifacts/")


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
        pointer = json.loads((target / session_logging.SESSION_POINTER_PATH).read_text(encoding="utf-8"))
        return {"session_id": pointer["session_id"], "log_path": pointer["log_path"]}

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


def test_session_logging_preserves_legacy_default_bucket_when_identity_registry_starts(tmp_path: Path) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    legacy = session_logging.ensure_session(state=state)
    (target / session_logging.SESSION_REGISTRY_PATH).unlink()

    identified = session_logging.ensure_session(state=state, logical_identity="new-host-session")
    default_again = session_logging.ensure_session(state=state, logical_identity="")

    assert identified["session_id"] != legacy["session_id"]
    assert default_again == legacy
    registry = json.loads((target / session_logging.SESSION_REGISTRY_PATH).read_text(encoding="utf-8"))
    assert registry["sessions"]["default"] == legacy


def test_session_logging_identityless_default_never_adopts_identified_pointer(tmp_path: Path) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    state = session_logging.load_state_for_argv(["--target", str(target)])
    session_a = session_logging.ensure_session(state=state, logical_identity="a")
    session_b = session_logging.ensure_session(state=state, logical_identity="b")

    assert session_logging.status_payload(state=state)["session_id"] == ""
    default_session = session_logging.ensure_session(state=state, logical_identity="")
    default_again = session_logging.ensure_session(state=state, logical_identity="")

    assert default_again == default_session
    assert default_session["session_id"] not in {session_a["session_id"], session_b["session_id"]}
    registry = json.loads((target / session_logging.SESSION_REGISTRY_PATH).read_text(encoding="utf-8"))
    assert registry["sessions"]["default"] == default_session


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

    assert status["logical_session_resolution"] == "identity-registry"
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


def test_session_logging_invalid_pointer_path_is_ignored(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

    assert source_cli.main(["config", "--target", str(target), "--select", "workspace.enabled", "--format", "json"]) == 0
    capsys.readouterr()
    first_log = _current_log(target)
    pointer_path = target / ".agentic-workspace/local/session-logging/current.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    pointer["log_path"] = "../../outside-session-log.md"
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")

    assert source_cli.main(["config", "--target", str(target), "--select", "workspace.enabled_source", "--format", "json"]) == 0
    capsys.readouterr()

    second_log = _current_log(target)
    assert second_log == first_log
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
    assert {candidate["id"] for candidate in payload["friction_candidates"]} >= {
        "failed-command",
        "repeated-command",
        "duplicate-output",
    }

    pointer = json.loads((target / ".agentic-workspace/local/session-logging/current.json").read_text(encoding="utf-8"))
    assert source_cli.main(["session-log", "--target", str(target), "analyze", "--id", pointer["session_id"], "--format", "json"]) == 0
    by_id = json.loads(capsys.readouterr().out)
    assert by_id["path"] == payload["path"]

    directory_id = f"aw-session-{pointer['session_id']}"
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
    assert payload["usage_mistakes"][0]["failure_class"] == "invalid-command"
    assert payload["usage_mistakes"][1]["failure_class"] == "selector-conflict"
    assert any(entry["command"] == "agentic-workspace modules --verbose --format json" for entry in payload["largest_outputs"])
    assert {candidate["id"] for candidate in payload["friction_candidates"]} >= {
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
    assert index["path_redaction"]["mode"] == "redacted"
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
    assert index["path_redaction"]["raw_artifact_recoverability"].startswith("raw output may remain")
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
                "parent_context": {"entry_id": "fixture-owner", "command": "pytest", "context": "test_session_fixture"},
                "exit_status": 2 if position < 15 else 0,
                "output_bytes": 200,
                "output_digest": f"pytest-digest-{position}",
            }
        )
    index["entries"] = entries
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    state = session_logging.load_state_for_argv(["--target", str(target)])

    default = session_logging.analyze_session_log(state=state)
    assert default["analysis_scope"]["origin"] == "agent"
    assert default["summary"]["command_count"] == 68
    assert default["summary"]["failure_count"] == 0
    assert default["origin_breakdown"] == {"agent": 68, "pytest": 35}
    assert default["origin_partitions"]["test"]["command_count"] == 35
    assert default["origin_partitions"]["test"]["failure_count"] == 15
    assert default["origin_partitions"]["test"]["entries"][0]["parent"]["entry_id"] == "fixture-owner"
    assert default["analyzer_overhead"]["command_count"] == 1
    assert any("1233722 bytes" in item["summary"] for item in default["friction_candidates"])
    assert not any("summry" in item["summary"] or "session-log analyze" in item["summary"] for item in default["friction_candidates"])

    test_scope = session_logging.analyze_session_log(state=state, origin_scope="test")
    assert test_scope["summary"]["command_count"] == 35
    assert test_scope["summary"]["failure_count"] == 15
    assert any("summry" in item["summary"] for item in test_scope["friction_candidates"])
    all_scope = session_logging.analyze_session_log(state=state, origin_scope="all")
    assert all_scope["summary"]["command_count"] == 103
    assert all_scope["summary"]["failure_count"] == 15
    assert any("summry" in item["summary"] for item in all_scope["friction_candidates"])
    assert not any("summry" in item["summary"] for item in default["friction_candidates"])


def test_session_log_projects_parent_context_written_by_logger(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace/config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")
    monkeypatch.setenv("AW_SESSION_LOG_PARENT_ENTRY_ID", "parent-entry")
    monkeypatch.setenv("AW_SESSION_LOG_PARENT_COMMAND", "pytest parent_test.py")
    monkeypatch.setenv("AW_SESSION_LOG_PARENT_CONTEXT", "fixture-parent")
    assert session_logging.run_with_session_logging(["status", "--target", str(target)], lambda _argv: 0) == 0
    capsys.readouterr()

    payload = session_logging.analyze_session_log(state=session_logging.load_state_for_argv(["--target", str(target)]), origin_scope="test")

    assert payload["origin_partitions"]["test"]["entries"][0]["parent"] == {
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
    assert repaired_index["repair"]["quarantined_entries"] == [ghost]
    assert session_logging.repair_session_log_index(state=state)["status"] == "already-covered"


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
    payload = session_logging.analyze_session_log(state=state)
    assert len(payload["segments"]) == 3
    assert {segment["task"] for segment in payload["segments"]} == {"Implement issue #2144", "Implement issue #2145"}
    assert any(segment["closeout_status"] == "closed" for segment in payload["segments"])
    selected_id = payload["segments"][0]["id"]
    selected = session_logging.analyze_session_log(state=state, segment_id=selected_id)
    assert selected["selected_segment"] == selected_id
    assert selected["summary"]["command_count"] == 1


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
    assert [entry["segment"]["closeout_status"] for entry in index["entries"]] == ["open", "open", "open"]


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
    entry = index["entries"][0]
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


def test_session_log_share_safe_export_redacts_all_surfaces_and_preserves_originals(tmp_path: Path, capsys, monkeypatch) -> None:
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
    original_log = log_path.read_bytes()
    original_index = index_path.read_bytes()
    assert source_cli.main(["session-log", "--target", str(target), "export", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "exported"
    export_path = target / payload["path"]
    with zipfile.ZipFile(export_path) as archive:
        names = set(archive.namelist())
        assert {"session.md", "index.json", "manifest.json"}.issubset(names)
        assert any(name.startswith("artifacts/") for name in names)
        combined = b"\n".join(archive.read(name) for name in names).decode("utf-8")
        assert str(target) not in combined
        assert target.as_posix() not in combined
        assert str(Path.home()) not in combined
        assert sys.executable not in combined
        assert "<target>" in combined
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["originals_mutated"] is False
        assert "arbitrary secrets" in manifest["limitations"]
    assert log_path.read_bytes() == original_log
    assert index_path.read_bytes() == original_index

    pointer = json.loads((target / ".agentic-workspace/local/session-logging/current.json").read_text(encoding="utf-8"))
    assert (
        source_cli.main(
            ["session-log", "--target", str(target), "export", "--id", pointer["session_id"], "--no-artifacts", "--format", "json"]
        )
        == 0
    )
    by_id = json.loads(capsys.readouterr().out)
    assert by_id["artifact_count"] == 0
    assert source_cli.main(["session-log", "--target", str(target), "export", "--path", pointer["log_path"], "--format", "json"]) == 0
    by_path = json.loads(capsys.readouterr().out)
    assert by_path["source_log_path"] == pointer["log_path"]
    assert log_path.read_bytes() == original_log
    assert index_path.read_bytes() == original_index
