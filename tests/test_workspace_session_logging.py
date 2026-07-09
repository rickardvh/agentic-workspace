from __future__ import annotations

import json
import sys
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
    session_id = pointer["session_id"]
    return target / ".agentic-workspace/local/logs/indexes" / f"{session_id}.json"


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
    assert index["entries"][0]["artifact"]["path"].startswith(".agentic-workspace/local/logs/artifacts/")


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
    artifact_line = next(line for line in log_text.splitlines() if line.startswith("- path: `.agentic-workspace/local/logs/artifacts/"))
    artifact_path = target / artifact_line.split("`", 2)[1]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["stdout"] == "x" * 80 + "\n"
    assert artifact["stderr"] == ""


def test_session_log_analyze_reports_counts_repeats_failures_artifacts_and_packets(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(target / ".agentic-workspace" / "config.local.toml", "schema_version = 1\n\n[session_logging]\nenabled = true\n")

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
    assert payload["index_status"] == "present"
    assert payload["summary"]["command_count"] == 2
    assert payload["summary"]["failure_count"] == 2
    assert payload["summary"]["repeated_command_count"] == 1
    assert payload["summary"]["duplicate_output_count"] == 1
    assert payload["summary"]["artifact_count"] == 2
    assert payload["packet_kinds"]["agentic-workspace/example-packet/v1"] == 2
    assert {candidate["id"] for candidate in payload["friction_candidates"]} >= {
        "failed-command",
        "repeated-command",
        "duplicate-output",
    }


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
    assert index["path_redaction"]["local_paths"] == "target-root-normalized"
    assert index["entries"][0]["target"] == "<target>"


def test_config_accepts_local_session_logging_without_unknown_field_warning(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[session_logging]\nenabled = true\nredact_local_paths = true\n",
    )

    assert source_cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert not any("session_logging" in warning for warning in payload["warnings"])
